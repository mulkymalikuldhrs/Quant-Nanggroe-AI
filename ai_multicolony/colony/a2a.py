"""Agent-to-Agent (A2A) protocol coordinator.

The A2A coordinator enables agents to communicate directly with each other
using a structured protocol.  Features:

* Structured message format (version, sender, recipient, type, payload, context)
* Message types: task_delegation, query, result, heartbeat, capability_ad, error
* Handshake sequence (init → ack → complete)
* Capability registry and discovery
* Result tracking (correlation IDs)
* Error handling with typed error messages
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set

from ..types import (
    A2AMessage,
    A2AMessageType,
    A2AHandshake,
    A2ACapabilityAd,
    HandType,
)

logger = logging.getLogger(__name__)


class A2ACoordinator:
    """Agent-to-Agent communication coordinator.

    Manages:
    * Agent registration / deregistration
    * Capability advertisement and discovery
    * Message routing (direct, broadcast, colony-scoped)
    * Handshake sequences
    * Result tracking via correlation IDs
    * Error propagation
    """

    def __init__(self):
        # Agent registry: agent_id → metadata
        self._agents: Dict[str, Dict[str, Any]] = {}

        # Capability index: capability → set of agent_ids
        self._capability_index: Dict[str, Set[str]] = {}

        # Per-agent capability list: agent_id → list of capability strings
        self._capabilities: Dict[str, List[str]] = {}

        # Message store
        self._messages: List[A2AMessage] = []

        # Per-agent mailbox: agent_id → list of messages
        self._mailboxes: Dict[str, List[A2AMessage]] = {}

        # Handshake tracking: (initiator, responder) → A2AHandshake
        self._handshakes: Dict[str, A2AHandshake] = {}

        # Result tracking: correlation_id → A2AMessage
        self._results: Dict[str, A2AMessage] = {}

        # Pending queries awaiting responses: correlation_id → original message
        self._pending_queries: Dict[str, A2AMessage] = {}

        # Error callbacks
        self._error_handlers: List[Callable[[A2AMessage], Coroutine[Any, Any, None]]] = []

    # ── Agent registration ─────────────────────────────────────────────────

    def register_agent(
        self,
        agent_id: str,
        colony_id: str,
        capabilities: Optional[List[str]] = None,
        hand_type: Optional[HandType] = None,
    ) -> None:
        """Register an agent with the A2A coordinator.

        Parameters
        ----------
        agent_id : str
            Unique agent identifier.
        colony_id : str
            Colony the agent belongs to.
        capabilities : list[str], optional
            List of capability strings this agent advertises.
        hand_type : HandType, optional
            The hand type the agent belongs to.
        """
        caps = capabilities or []
        self._agents[agent_id] = {
            "agent_id": agent_id,
            "colony_id": colony_id,
            "hand_type": hand_type.value if hand_type else None,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }
        self._capabilities[agent_id] = caps
        self._mailboxes[agent_id] = []

        # Update capability index
        for cap in caps:
            if cap not in self._capability_index:
                self._capability_index[cap] = set()
            self._capability_index[cap].add(agent_id)

        # Broadcast capability ad
        self._broadcast_capability_ad(agent_id, colony_id, caps, hand_type)

        logger.debug("Agent %s registered with A2A (colony=%s, caps=%s)", agent_id, colony_id, caps)

    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent from the A2A coordinator."""
        # Remove from capability index
        for cap in self._capabilities.pop(agent_id, []):
            cap_set = self._capability_index.get(cap)
            if cap_set:
                cap_set.discard(agent_id)
                if not cap_set:
                    del self._capability_index[cap]

        self._agents.pop(agent_id, None)
        self._mailboxes.pop(agent_id, None)
        logger.debug("Agent %s unregistered from A2A", agent_id)

    # ── Capability discovery ───────────────────────────────────────────────

    def discover_agents(
        self,
        capability: str,
        colony_id: Optional[str] = None,
        available_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """Find agents that advertise a specific capability.

        Parameters
        ----------
        capability : str
            Capability string to search for.
        colony_id : str, optional
            Restrict to agents in this colony.
        available_only : bool
            If True, only return agents with no pending messages (heuristic).
        """
        agent_ids = self._capability_index.get(capability, set())
        results = []
        for aid in agent_ids:
            info = self._agents.get(aid)
            if info is None:
                continue
            if colony_id and info.get("colony_id") != colony_id:
                continue
            if available_only and len(self._mailboxes.get(aid, [])) > 10:
                continue
            results.append({
                **info,
                "capabilities": self._capabilities.get(aid, []),
                "pending_messages": len(self._mailboxes.get(aid, [])),
            })
        return results

    def get_agent_capabilities(self, agent_id: str) -> List[str]:
        """Return an agent's advertised capabilities."""
        return list(self._capabilities.get(agent_id, []))

    def update_capabilities(self, agent_id: str, capabilities: List[str]) -> None:
        """Update an agent's capability advertisements."""
        # Remove old caps from index
        for cap in self._capabilities.pop(agent_id, []):
            cap_set = self._capability_index.get(cap)
            if cap_set:
                cap_set.discard(agent_id)

        # Set new caps
        self._capabilities[agent_id] = capabilities
        for cap in capabilities:
            if cap not in self._capability_index:
                self._capability_index[cap] = set()
            self._capability_index[cap].add(agent_id)

    def _broadcast_capability_ad(
        self, agent_id: str, colony_id: str, caps: List[str], hand_type: Optional[HandType]
    ) -> None:
        """Broadcast a capability advertisement to the colony."""
        ad = A2ACapabilityAd(
            agent_id=agent_id,
            colony_id=colony_id,
            hand_type=hand_type,
            capabilities=caps,
        )
        msg = A2AMessage(
            sender={"agent_id": agent_id, "colony_id": colony_id},
            recipient={"type": "broadcast", "colony_id": colony_id},
            message_type=A2AMessageType.CAPABILITY_AD,
            payload=ad.model_dump(mode="json"),
        )
        self._messages.append(msg)
        # Deliver to colony members
        for aid, info in self._agents.items():
            if aid != agent_id and info.get("colony_id") == colony_id:
                self._mailboxes.setdefault(aid, []).append(msg)

    # ── Message sending ────────────────────────────────────────────────────

    async def send_message(self, message: A2AMessage) -> str:
        """Send an A2A message.

        The message is delivered to the recipient's mailbox if they are
        registered, and stored in the global message log.

        Returns the message_id.
        """
        self._messages.append(message)

        # Route to recipient mailbox
        recipient_id = message.recipient.get("agent_id")
        if recipient_id and recipient_id in self._mailboxes:
            self._mailboxes[recipient_id].append(message)

        # Track queries awaiting responses
        correlation_id = message.context.get("correlation_id")
        if message.message_type == A2AMessageType.QUERY and correlation_id:
            self._pending_queries[correlation_id] = message

        # Track results
        if message.message_type == A2AMessageType.RESULT and correlation_id:
            self._results[correlation_id] = message
            self._pending_queries.pop(correlation_id, None)

        # Error handling
        if message.message_type == A2AMessageType.ERROR:
            await self._handle_error(message)

        logger.debug(
            "A2A message %s: %s → %s [%s]",
            message.message_id,
            message.sender.get("agent_id", "?"),
            message.recipient.get("agent_id", message.recipient.get("type", "?")),
            message.message_type.value,
        )
        return message.message_id

    async def send_task_delegation(
        self,
        sender_id: str,
        sender_colony: str,
        recipient_id: str,
        task_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Convenience method: delegate a task to another agent."""
        msg = A2AMessage(
            sender={"agent_id": sender_id, "colony_id": sender_colony},
            recipient={"agent_id": recipient_id},
            message_type=A2AMessageType.TASK_DELEGATION,
            payload=task_data,
            context=context or {},
        )
        return await self.send_message(msg)

    async def send_query(
        self,
        sender_id: str,
        sender_colony: str,
        recipient_id: str,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Convenience method: send a query to another agent."""
        import uuid
        correlation_id = context.get("correlation_id") if context else None or uuid.uuid4().hex[:12]
        msg = A2AMessage(
            sender={"agent_id": sender_id, "colony_id": sender_colony},
            recipient={"agent_id": recipient_id},
            message_type=A2AMessageType.QUERY,
            payload={"query": query},
            context={**(context or {}), "correlation_id": correlation_id},
        )
        return await self.send_message(msg)

    async def send_result(
        self,
        sender_id: str,
        sender_colony: str,
        recipient_id: str,
        result_data: Dict[str, Any],
        correlation_id: str,
    ) -> str:
        """Convenience method: send a result back for a query."""
        msg = A2AMessage(
            sender={"agent_id": sender_id, "colony_id": sender_colony},
            recipient={"agent_id": recipient_id},
            message_type=A2AMessageType.RESULT,
            payload=result_data,
            context={"correlation_id": correlation_id},
        )
        return await self.send_message(msg)

    async def broadcast(
        self,
        sender_id: str,
        colony_id: str,
        message_type: A2AMessageType,
        payload: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Broadcast a message to all agents in a colony."""
        msg = A2AMessage(
            sender={"agent_id": sender_id, "colony_id": colony_id},
            recipient={"type": "broadcast", "colony_id": colony_id},
            message_type=message_type,
            payload=payload,
            context=context or {},
        )
        self._messages.append(msg)

        # Deliver to all colony members
        for aid, info in self._agents.items():
            if aid != sender_id and info.get("colony_id") == colony_id:
                self._mailboxes.setdefault(aid, []).append(msg)

        return msg.message_id

    # ── Mailbox ────────────────────────────────────────────────────────────

    def get_messages(self, agent_id: Optional[str] = None, limit: int = 100) -> List[A2AMessage]:
        """Get messages, optionally filtered by agent (from mailbox)."""
        if agent_id:
            mailbox = self._mailboxes.get(agent_id, [])
            return mailbox[-limit:]
        return self._messages[-limit:]

    def get_unread_count(self, agent_id: str) -> int:
        """Return the number of pending messages in an agent's mailbox."""
        return len(self._mailboxes.get(agent_id, []))

    def clear_mailbox(self, agent_id: str) -> int:
        """Clear an agent's mailbox. Returns the number of messages cleared."""
        count = len(self._mailboxes.get(agent_id, []))
        self._mailboxes[agent_id] = []
        return count

    # ── Handshake ──────────────────────────────────────────────────────────

    async def initiate_handshake(
        self,
        initiator_id: str,
        initiator_colony: str,
        responder_id: str,
        initiator_capabilities: Optional[List[str]] = None,
    ) -> A2AHandshake:
        """Initiate an A2A handshake with another agent.

        The handshake sequence:
        1. init → initiator sends a handshake_init message
        2. ack  → responder replies with handshake_ack + its capabilities
        3. complete → both agents agree on protocol version

        Returns the handshake object (may not be complete yet).
        """
        key = f"{initiator_id}:{responder_id}"
        handshake = A2AHandshake(
            initiator_id=initiator_id,
            responder_id=responder_id,
            state="init",
            initiator_capabilities=initiator_capabilities or [],
        )
        self._handshakes[key] = handshake

        # Send handshake_init message
        msg = A2AMessage(
            sender={"agent_id": initiator_id, "colony_id": initiator_colony},
            recipient={"agent_id": responder_id},
            message_type=A2AMessageType.HANDSHAKE_INIT,
            payload={
                "protocol_version": "1.0",
                "capabilities": initiator_capabilities or [],
            },
            context={"handshake_key": key},
        )
        await self.send_message(msg)
        return handshake

    async def acknowledge_handshake(
        self,
        responder_id: str,
        responder_colony: str,
        initiator_id: str,
        responder_capabilities: Optional[List[str]] = None,
    ) -> A2AHandshake:
        """Acknowledge a handshake request (step 2 of the sequence)."""
        key = f"{initiator_id}:{responder_id}"
        handshake = self._handshakes.get(key)
        if handshake is None:
            raise ValueError(f"No pending handshake for key {key}")

        handshake.state = "ack"
        handshake.responder_capabilities = responder_capabilities or []

        msg = A2AMessage(
            sender={"agent_id": responder_id, "colony_id": responder_colony},
            recipient={"agent_id": initiator_id},
            message_type=A2AMessageType.HANDSHAKE_ACK,
            payload={
                "protocol_version": "1.0",
                "capabilities": responder_capabilities or [],
            },
            context={"handshake_key": key},
        )
        await self.send_message(msg)
        return handshake

    async def complete_handshake(self, initiator_id: str, responder_id: str) -> A2AHandshake:
        """Complete a handshake (step 3 of the sequence)."""
        key = f"{initiator_id}:{responder_id}"
        handshake = self._handshakes.get(key)
        if handshake is None:
            raise ValueError(f"No pending handshake for key {key}")

        handshake.state = "complete"
        handshake.completed_at = datetime.now(timezone.utc)

        msg = A2AMessage(
            sender={"agent_id": initiator_id},
            recipient={"agent_id": responder_id},
            message_type=A2AMessageType.HANDSHAKE_COMPLETE,
            payload={"status": "established"},
            context={"handshake_key": key},
        )
        await self.send_message(msg)
        return handshake

    def get_handshake(self, initiator_id: str, responder_id: str) -> Optional[A2AHandshake]:
        """Retrieve a handshake by participant IDs."""
        return self._handshakes.get(f"{initiator_id}:{responder_id}")

    # ── Result tracking ────────────────────────────────────────────────────

    def get_result(self, correlation_id: str) -> Optional[A2AMessage]:
        """Retrieve a result message by its correlation ID."""
        return self._results.get(correlation_id)

    def get_pending_queries(self, agent_id: Optional[str] = None) -> Dict[str, A2AMessage]:
        """Return queries that haven't been answered yet.

        Optionally filter by the querying agent's ID.
        """
        if agent_id:
            return {
                cid: msg
                for cid, msg in self._pending_queries.items()
                if msg.sender.get("agent_id") == agent_id
            }
        return dict(self._pending_queries)

    # ── Error handling ─────────────────────────────────────────────────────

    def register_error_handler(self, handler: Callable[[A2AMessage], Coroutine[Any, Any, None]]) -> None:
        """Register an async callback for A2A error messages."""
        self._error_handlers.append(handler)

    async def _handle_error(self, message: A2AMessage) -> None:
        """Invoke registered error handlers for an error message."""
        for handler in self._error_handlers:
            try:
                await handler(message)
            except Exception as exc:
                logger.warning("Error handler raised: %s", exc)

    # ── Heartbeat ──────────────────────────────────────────────────────────

    async def send_heartbeat(self, agent_id: str, colony_id: str, status: Dict[str, Any]) -> str:
        """Send a heartbeat message to the colony."""
        msg = A2AMessage(
            sender={"agent_id": agent_id, "colony_id": colony_id},
            recipient={"type": "broadcast", "colony_id": colony_id},
            message_type=A2AMessageType.HEARTBEAT,
            payload=status,
        )
        return await self.send_message(msg)

    # ── Properties ─────────────────────────────────────────────────────────

    @property
    def agent_count(self) -> int:
        return len(self._agents)

    @property
    def message_count(self) -> int:
        return len(self._messages)

    @property
    def capability_count(self) -> int:
        return len(self._capability_index)

    def get_stats(self) -> Dict[str, Any]:
        """Return A2A coordinator statistics."""
        return {
            "registered_agents": self.agent_count,
            "total_messages": self.message_count,
            "unique_capabilities": self.capability_count,
            "pending_queries": len(self._pending_queries),
            "completed_results": len(self._results),
            "active_handshakes": sum(1 for h in self._handshakes.values() if h.state != "complete"),
        }
