"""
A2A Protocol — Agent-to-Agent Communication
=============================================
Enables inter-agent message passing and coordination within the
Quant-Nanggroe-AI trading system.

The A2A protocol provides a publish-subscribe message bus that allows
agents to communicate without direct coupling. Agents register with
the bus, send directed or broadcast messages, and receive callbacks
when messages arrive.

Core components:
  - A2AMessage: Typed, prioritised message envelope
  - A2ABus: Async message bus with routing and delivery
  - A2AAgent: Base class for agents that communicate via the bus
  - TradingA2AAgent: Specialised agent for trading-domain messages

Message types for the trading domain:
  - SIGNAL:        Trading signal (BUY/SELL/HOLD) from strategy agents
  - RISK_ALERT:    Risk threshold breach or veto notification
  - REGIME_CHANGE: Market regime transition detected
  - EXECUTION_REPORT: Trade execution outcome (fill, reject, cancel)
  - RESEARCH:      Research findings and data updates
  - COORDINATION:  General coordination / handoff between agents

All message delivery is async. The bus supports both callback-based
and polling-based consumption patterns.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum, IntEnum
from typing import Any, Callable, Coroutine

from pydantic import BaseModel, Field

from quant_nanggroe_ai.exceptions import AgentError

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# A2A Message Types
# ══════════════════════════════════════════════════════════════════════


class A2AMessageType(str, Enum):
    """
    Standard message types for inter-agent communication.

    Each type carries specific semantic meaning:
      - SIGNAL: A trading signal from a strategy or analysis agent.
      - RISK_ALERT: A risk-related warning or veto notification.
      - REGIME_CHANGE: Notification that the market regime has changed.
      - EXECUTION_REPORT: Outcome of a trade execution attempt.
      - RESEARCH: Research findings, data updates, or memory results.
      - COORDINATION: General coordination, handoff, or control flow.
    """

    SIGNAL = "SIGNAL"
    RISK_ALERT = "RISK_ALERT"
    REGIME_CHANGE = "REGIME_CHANGE"
    EXECUTION_REPORT = "EXECUTION_REPORT"
    RESEARCH = "RESEARCH"
    COORDINATION = "COORDINATION"


class A2APriority(IntEnum):
    """
    Message priority levels (0 = highest, 5 = lowest).

    The bus uses priority to order message delivery when multiple
    messages are queued for the same agent.
    """

    CRITICAL = 0  # Kill switch, emergency stop
    HIGH = 1  # Risk veto, regime change
    NORMAL = 2  # Trading signals, execution reports
    LOW = 3  # Research updates, analytics
    INFO = 4  # Status updates, heartbeats
    DEBUG = 5  # Debug / trace messages


class A2AMessage(BaseModel):
    """
    Message envelope for inter-agent communication.

    Every message carries a unique ID, sender/recipient identifiers,
    a typed payload, and a priority level. Messages are immutable
    value objects — construct a new message to "modify" an existing one.

    Attributes:
        id: Unique message identifier (auto-generated UUID4).
        sender: Agent ID of the sender.
        recipient: Agent ID of the intended recipient, or "broadcast"
            to deliver to all registered agents except the sender.
        message_type: Semantic type of the message (SIGNAL, RISK_ALERT, etc.).
        payload: Arbitrary dict carrying the message data.
        timestamp: UTC datetime when the message was created.
        priority: Delivery priority (0–5, default NORMAL).
        correlation_id: Optional ID linking this message to a prior
            message (for request/response patterns).
        metadata: Optional dict for tracing, routing hints, etc.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender: str
    recipient: str  # "broadcast" for pub/sub
    message_type: A2AMessageType
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    priority: A2APriority = A2APriority.NORMAL
    correlation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def is_broadcast(self) -> bool:
        """Check if this message is intended for all agents."""
        return self.recipient == "broadcast"

    def reply(
        self,
        sender_id: str,
        message_type: A2AMessageType | None = None,
        payload: dict[str, Any] | None = None,
    ) -> A2AMessage:
        """
        Create a reply message addressed back to the original sender.

        The reply inherits the original message's correlation_id for
        request/response tracking.

        Args:
            sender_id: Agent ID of the replier.
            message_type: Override message type (defaults to same type).
            payload: Reply payload data.

        Returns:
            New A2AMessage addressed from *sender_id* to the original sender.
        """
        return A2AMessage(
            sender=sender_id,
            recipient=self.sender,
            message_type=message_type or self.message_type,
            payload=payload or {},
            priority=self.priority,
            correlation_id=self.id,
        )


# ══════════════════════════════════════════════════════════════════════
# A2ABus — Message bus for agent communication
# ══════════════════════════════════════════════════════════════════════

# Type alias for the callback signature
A2ACallback = Callable[[A2AMessage], Coroutine[Any, Any, None]]


class _MessageQueue:
    """
    Priority-aware async message queue for a single agent.

    Messages are sorted by priority on insertion so that the highest-
    priority message is always consumed first.
    """

    def __init__(self, max_size: int = 1000) -> None:
        self._messages: list[A2AMessage] = []
        self._max_size = max_size
        self._event: asyncio.Event = asyncio.Event()

    def push(self, message: A2AMessage) -> None:
        """Add a message to the queue, maintaining priority order."""
        # Evict oldest lowest-priority message if at capacity
        if len(self._messages) >= self._max_size:
            # Remove the lowest-priority (highest numeric value) message
            if self._messages:
                worst_idx = max(
                    range(len(self._messages)),
                    key=lambda i: self._messages[i].priority,
                )
                self._messages.pop(worst_idx)

        # Insert in priority order (binary insertion for efficiency)
        inserted = False
        for i, existing in enumerate(self._messages):
            if message.priority < existing.priority:
                self._messages.insert(i, message)
                inserted = True
                break
        if not inserted:
            self._messages.append(message)

        self._event.set()

    async def pop(self, timeout: float | None = None) -> A2AMessage | None:
        """
        Pop the highest-priority message from the queue.

        Args:
            timeout: Maximum seconds to wait. None = wait forever.

        Returns:
            The highest-priority A2AMessage, or None on timeout.
        """
        if self._messages:
            return self._messages.pop(0)

        # Wait for a new message
        try:
            if timeout is not None:
                await asyncio.wait_for(self._event.wait(), timeout=timeout)
            else:
                await self._event.wait()
        except asyncio.TimeoutError:
            return None

        self._event.clear()
        if self._messages:
            return self._messages.pop(0)
        return None

    def peek_all(self) -> list[A2AMessage]:
        """Return a snapshot of all queued messages without removing them."""
        return list(self._messages)

    @property
    def size(self) -> int:
        """Current number of messages in the queue."""
        return len(self._messages)


class A2ABus:
    """
    Async message bus for inter-agent communication.

    The bus manages agent registration, message routing, and delivery.
    It supports both callback-based (push) and polling-based (pull)
    consumption patterns.

    Routing rules:
      - Directed messages: delivered to the specific recipient's queue
        and callback.
      - Broadcast messages: delivered to all registered agents *except*
        the sender.
      - Unknown recipient: the message is dropped with a warning.

    The bus is designed to run within an asyncio event loop. All public
    methods are safe to call from any coroutine.

    Usage::

        bus = A2ABus()

        # Register agents
        bus.register_agent("researcher", on_researcher_msg)
        bus.register_agent("analyst", on_analyst_msg)

        # Send directed message
        msg = A2AMessage(
            sender="researcher",
            recipient="analyst",
            message_type=A2AMessageType.RESEARCH,
            payload={"symbol": "AAPL", "data": {...}},
        )
        await bus.send_message(msg)

        # Broadcast
        await bus.broadcast(A2AMessage(
            sender="risk_manager",
            recipient="broadcast",
            message_type=A2AMessageType.RISK_ALERT,
            payload={"alert": "daily_limit_80pct"},
            priority=A2APriority.HIGH,
        ))
    """

    def __init__(
        self,
        queue_max_size: int = 1000,
        max_history: int = 500,
    ) -> None:
        """
        Initialize the A2A message bus.

        Args:
            queue_max_size: Maximum messages per agent queue before eviction.
            max_history: Maximum broadcast/delivery history records to retain.
        """
        self._agents: dict[str, A2ACallback] = {}
        self._queues: dict[str, _MessageQueue] = {}
        self._queue_max_size = queue_max_size
        self._history: list[dict[str, Any]] = []
        self._max_history = max_history
        self._lock = asyncio.Lock()

    # ── Agent registration ───────────────────────────────────────────

    def register_agent(
        self,
        agent_id: str,
        callback: A2ACallback,
    ) -> None:
        """
        Register an agent with the bus.

        The callback is invoked asynchronously whenever a message is
        delivered to the agent. If the agent is already registered, the
        callback is replaced.

        Args:
            agent_id: Unique identifier for the agent.
            callback: Async callable that receives an A2AMessage.

        Raises:
            ValueError: If *agent_id* is empty or "broadcast".
        """
        if not agent_id or agent_id == "broadcast":
            raise ValueError("agent_id cannot be empty or 'broadcast'")

        self._agents[agent_id] = callback
        self._queues[agent_id] = _MessageQueue(max_size=self._queue_max_size)
        logger.info("A2A agent registered: %s", agent_id)

    def unregister_agent(self, agent_id: str) -> bool:
        """
        Remove an agent from the bus.

        Any undelivered messages in the agent's queue are discarded.

        Args:
            agent_id: The agent to remove.

        Returns:
            True if the agent was found and removed, False otherwise.
        """
        if agent_id in self._agents:
            del self._agents[agent_id]
            self._queues.pop(agent_id, None)
            logger.info("A2A agent unregistered: %s", agent_id)
            return True
        return False

    def is_registered(self, agent_id: str) -> bool:
        """Check if an agent is currently registered."""
        return agent_id in self._agents

    def list_agents(self) -> list[str]:
        """Return sorted list of registered agent IDs."""
        return sorted(self._agents.keys())

    # ── Message delivery ─────────────────────────────────────────────

    async def send_message(self, msg: A2AMessage) -> dict[str, Any]:
        """
        Deliver a directed message to its recipient.

        If the recipient is "broadcast", delegates to ``broadcast()``.

        Args:
            msg: The A2AMessage to deliver.

        Returns:
            Delivery status dict with 'delivered' (bool), 'recipient',
            and 'message_id'.

        Raises:
            AgentError: If the sender is not registered.
        """
        if msg.is_broadcast():
            return await self.broadcast(msg)

        if msg.sender not in self._agents and msg.sender != "system":
            raise AgentError(f"Sender '{msg.sender}' is not registered on the A2A bus")

        if msg.recipient not in self._agents:
            logger.warning(
                "A2A message %s: recipient '%s' not registered — dropped",
                msg.id, msg.recipient,
            )
            self._record_history(msg, delivered=False, reason="recipient_not_found")
            return {
                "delivered": False,
                "recipient": msg.recipient,
                "message_id": msg.id,
                "reason": "recipient_not_registered",
            }

        # Enqueue and callback
        self._queues[msg.recipient].push(msg)
        callback = self._agents[msg.recipient]
        try:
            await callback(msg)
        except Exception as exc:
            logger.error(
                "A2A callback error for agent %s: %s", msg.recipient, exc
            )

        self._record_history(msg, delivered=True)
        return {
            "delivered": True,
            "recipient": msg.recipient,
            "message_id": msg.id,
        }

    async def broadcast(self, msg: A2AMessage) -> dict[str, Any]:
        """
        Deliver a broadcast message to all registered agents except the sender.

        Args:
            msg: The A2AMessage with recipient="broadcast".

        Returns:
            Delivery summary dict with 'delivered_count', 'failed_count',
            'recipients', and 'message_id'.
        """
        if not msg.is_broadcast():
            raise AgentError("Message recipient must be 'broadcast' for broadcast()")

        delivered_count = 0
        failed_count = 0
        recipients: list[str] = []

        for agent_id, callback in self._agents.items():
            if agent_id == msg.sender:
                continue  # Don't send to self

            self._queues[agent_id].push(msg)
            try:
                await callback(msg)
                delivered_count += 1
                recipients.append(agent_id)
            except Exception as exc:
                failed_count += 1
                logger.error(
                    "A2A broadcast callback error for agent %s: %s",
                    agent_id, exc,
                )

        self._record_history(msg, delivered=True, broadcast=True)
        return {
            "delivered_count": delivered_count,
            "failed_count": failed_count,
            "recipients": recipients,
            "message_id": msg.id,
        }

    # ── Polling-based consumption ────────────────────────────────────

    async def get_messages(
        self,
        agent_id: str,
        timeout: float | None = None,
    ) -> list[A2AMessage]:
        """
        Retrieve all pending messages for an agent (polling mode).

        If *timeout* is provided, waits up to that many seconds for at
        least one message to arrive. Returns immediately if messages are
        already queued.

        Args:
            agent_id: The agent whose messages to retrieve.
            timeout: Seconds to wait for a message (None = wait forever).

        Returns:
            List of A2AMessage objects (may be empty on timeout).

        Raises:
            AgentError: If the agent is not registered.
        """
        if agent_id not in self._queues:
            raise AgentError(f"Agent '{agent_id}' is not registered on the A2A bus")

        queue = self._queues[agent_id]
        messages = queue.peek_all()

        if messages:
            # Drain all available messages
            result: list[A2AMessage] = []
            while queue.size > 0:
                msg = await queue.pop(timeout=0)
                if msg is not None:
                    result.append(msg)
            return result

        # Wait for at least one message
        first = await queue.pop(timeout=timeout)
        if first is None:
            return []

        result = [first]
        # Drain any additional messages that arrived
        while queue.size > 0:
            msg = await queue.pop(timeout=0)
            if msg is not None:
                result.append(msg)
        return result

    async def get_one_message(
        self,
        agent_id: str,
        timeout: float | None = None,
    ) -> A2AMessage | None:
        """
        Retrieve a single message for an agent.

        Args:
            agent_id: The agent whose message to retrieve.
            timeout: Seconds to wait (None = wait forever).

        Returns:
            The highest-priority A2AMessage, or None on timeout.

        Raises:
            AgentError: If the agent is not registered.
        """
        if agent_id not in self._queues:
            raise AgentError(f"Agent '{agent_id}' is not registered on the A2A bus")

        return await self._queues[agent_id].pop(timeout=timeout)

    # ── History and diagnostics ──────────────────────────────────────

    def _record_history(
        self,
        msg: A2AMessage,
        delivered: bool,
        broadcast: bool = False,
        reason: str | None = None,
    ) -> None:
        """Record a message delivery event in the history log."""
        record = {
            "message_id": msg.id,
            "sender": msg.sender,
            "recipient": msg.recipient,
            "message_type": msg.message_type.value,
            "priority": msg.priority,
            "delivered": delivered,
            "broadcast": broadcast,
            "reason": reason,
            "timestamp": msg.timestamp.isoformat(),
        }
        self._history.append(record)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    def get_history(
        self,
        message_type: A2AMessageType | None = None,
        agent_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Query the message delivery history.

        Args:
            message_type: Filter by message type (optional).
            agent_id: Filter by sender or recipient (optional).
            limit: Maximum records to return (most recent first).

        Returns:
            List of delivery record dicts.
        """
        records = self._history
        if message_type is not None:
            records = [r for r in records if r["message_type"] == message_type.value]
        if agent_id is not None:
            records = [
                r for r in records
                if r["sender"] == agent_id or r["recipient"] == agent_id
            ]
        return list(reversed(records[-limit:]))

    def get_queue_depths(self) -> dict[str, int]:
        """
        Return the number of pending messages per agent.

        Returns:
            Dict mapping agent_id → queue depth.
        """
        return {aid: q.size for aid, q in self._queues.items()}

    def get_stats(self) -> dict[str, Any]:
        """
        Return bus statistics for monitoring.

        Returns:
            Dict with agent count, total history, queue depths, etc.
        """
        return {
            "registered_agents": len(self._agents),
            "agents": self.list_agents(),
            "total_history_records": len(self._history),
            "queue_depths": self.get_queue_depths(),
            "total_queued": sum(q.size for q in self._queues.values()),
        }


# ══════════════════════════════════════════════════════════════════════
# A2AAgent — Base class for A2A-capable agents
# ══════════════════════════════════════════════════════════════════════


class A2AAgent:
    """
    Base class for agents that communicate via the A2A message bus.

    Subclasses override ``on_message`` to handle incoming messages and
    use ``send_to`` / ``broadcast`` to emit messages.

    The agent auto-registers with the bus on construction and unregisters
    when ``shutdown`` is called.

    Usage::

        class MyAgent(A2AAgent):
            async def on_message(self, msg: A2AMessage) -> None:
                if msg.message_type == A2AMessageType.SIGNAL:
                    await self.process_signal(msg)

            async def process_signal(self, msg: A2AMessage) -> None:
                # ... do work ...
                await self.send_to(
                    "risk_manager",
                    A2AMessageType.RISK_ALERT,
                    {"alert": "signal_processed"},
                )
    """

    def __init__(
        self,
        agent_id: str,
        bus: A2ABus | None = None,
    ) -> None:
        """
        Initialize the A2A agent.

        Args:
            agent_id: Unique identifier for this agent.
            bus: The A2ABus to connect to. If None, the default bus
                is used (see ``get_default_bus``).
        """
        self.agent_id = agent_id
        self._bus = bus or get_default_a2a_bus()
        self._bus.register_agent(agent_id, self.on_message)
        self._running = True
        logger.info("A2AAgent '%s' initialized and registered", agent_id)

    # ── Abstract message handler ─────────────────────────────────────

    async def on_message(self, msg: A2AMessage) -> None:
        """
        Handle an incoming message from the bus.

        Subclasses must override this method to implement their
        message-processing logic. The default implementation logs
        the message and discards it.

        Args:
            msg: The received A2AMessage.
        """
        logger.debug(
            "A2AAgent '%s' received %s message from '%s'",
            self.agent_id, msg.message_type.value, msg.sender,
        )

    # ── Send helpers ─────────────────────────────────────────────────

    async def send_to(
        self,
        recipient: str,
        msg_type: A2AMessageType,
        payload: dict[str, Any],
        priority: A2APriority = A2APriority.NORMAL,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Send a directed message to another agent.

        Args:
            recipient: The target agent's ID.
            msg_type: Semantic message type.
            payload: Message data.
            priority: Delivery priority (default NORMAL).
            correlation_id: Optional ID linking to a previous message.

        Returns:
            Delivery status dict from the bus.
        """
        msg = A2AMessage(
            sender=self.agent_id,
            recipient=recipient,
            message_type=msg_type,
            payload=payload,
            priority=priority,
            correlation_id=correlation_id,
        )
        return await self._bus.send_message(msg)

    async def broadcast(
        self,
        msg_type: A2AMessageType,
        payload: dict[str, Any],
        priority: A2APriority = A2APriority.NORMAL,
    ) -> dict[str, Any]:
        """
        Broadcast a message to all other agents on the bus.

        Args:
            msg_type: Semantic message type.
            payload: Message data.
            priority: Delivery priority (default NORMAL).

        Returns:
            Delivery summary dict from the bus.
        """
        msg = A2AMessage(
            sender=self.agent_id,
            recipient="broadcast",
            message_type=msg_type,
            payload=payload,
            priority=priority,
        )
        return await self._bus.broadcast(msg)

    # ── Lifecycle ────────────────────────────────────────────────────

    async def poll_messages(self, timeout: float = 1.0) -> list[A2AMessage]:
        """
        Poll for pending messages (pull-based consumption).

        Useful when the agent runs in its own loop rather than relying
        solely on the callback mechanism.

        Args:
            timeout: Seconds to wait for a message.

        Returns:
            List of A2AMessage objects.
        """
        return await self._bus.get_messages(self.agent_id, timeout=timeout)

    def shutdown(self) -> None:
        """
        Unregister the agent from the bus.

        After shutdown, the agent will no longer receive messages.
        """
        self._running = False
        self._bus.unregister_agent(self.agent_id)
        logger.info("A2AAgent '%s' shut down", self.agent_id)

    @property
    def bus(self) -> A2ABus:
        """The A2ABus this agent is connected to."""
        return self._bus


# ══════════════════════════════════════════════════════════════════════
# TradingA2AAgent — Specialized A2A agent for the trading domain
# ══════════════════════════════════════════════════════════════════════


class TradingA2AAgent(A2AAgent):
    """
    Specialized A2A agent for trading-domain message handling.

    Extends ``A2AAgent`` with:
      - Convenience methods for trading-specific message types
        (send_signal, send_risk_alert, send_regime_change, send_execution_report)
      - Typed payload validation for common message types
      - Default message routing for common trading workflows

    The agent auto-handles RISK_ALERT and REGIME_CHANGE messages at
    elevated priority and provides structured payload builders.

    Usage::

        agent = TradingA2AAgent("strategist", bus=my_bus)

        # Send a trading signal
        await agent.send_signal(
            symbol="AAPL",
            direction="BUY",
            confidence=0.85,
            entry_price=150.0,
            stop_loss=147.0,
            take_profit=[156.0, 162.0],
        )

        # Send a risk alert
        await agent.send_risk_alert(
            alert_type="daily_limit_warning",
            current_pct=0.008,
            limit_pct=0.01,
        )
    """

    def __init__(
        self,
        agent_id: str,
        bus: A2ABus | None = None,
        role: str = "general",
    ) -> None:
        """
        Initialize a TradingA2AAgent.

        Args:
            agent_id: Unique identifier for this agent.
            bus: The A2ABus to connect to. Defaults to the shared bus.
            role: Agent role label (e.g. 'researcher', 'risk_manager').
        """
        super().__init__(agent_id=agent_id, bus=bus)
        self.role = role

    # ── Trading-specific send methods ────────────────────────────────

    async def send_signal(
        self,
        symbol: str,
        direction: str,
        confidence: float,
        entry_price: float | None = None,
        stop_loss: float | None = None,
        take_profit: list[float] | None = None,
        position_size: float | None = None,
        recipient: str = "risk_manager",
        strategy_name: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Send a trading signal message.

        Args:
            symbol: Ticker symbol.
            direction: "BUY", "SELL", or "HOLD".
            confidence: Signal confidence (0.0–1.0).
            entry_price: Suggested entry price.
            stop_loss: Stop-loss price.
            take_profit: List of take-profit levels.
            position_size: Suggested position size.
            recipient: Target agent (default 'risk_manager').
            strategy_name: Name of the originating strategy.
            correlation_id: Optional correlation ID.

        Returns:
            Delivery status dict.
        """
        payload: dict[str, Any] = {
            "symbol": symbol,
            "direction": direction.upper(),
            "confidence": round(max(0.0, min(1.0, confidence)), 4),
        }
        if entry_price is not None:
            payload["entry_price"] = entry_price
        if stop_loss is not None:
            payload["stop_loss"] = stop_loss
        if take_profit is not None:
            payload["take_profit"] = take_profit
        if position_size is not None:
            payload["position_size"] = position_size
        if strategy_name is not None:
            payload["strategy_name"] = strategy_name

        return await self.send_to(
            recipient=recipient,
            msg_type=A2AMessageType.SIGNAL,
            payload=payload,
            priority=A2APriority.NORMAL,
            correlation_id=correlation_id,
        )

    async def send_risk_alert(
        self,
        alert_type: str,
        recipient: str = "broadcast",
        **details: Any,
    ) -> dict[str, Any]:
        """
        Send a risk alert message.

        Risk alerts are sent at HIGH priority by default.

        Args:
            alert_type: Type of risk alert (e.g. 'daily_limit_warning',
                'kill_switch_engaged', 'veto_issued').
            recipient: Target agent (default 'broadcast').
            **details: Additional alert details.

        Returns:
            Delivery status dict.
        """
        payload: dict[str, Any] = {
            "alert_type": alert_type,
            "source_agent": self.agent_id,
            **details,
        }
        return await self.send_to(
            recipient=recipient,
            msg_type=A2AMessageType.RISK_ALERT,
            payload=payload,
            priority=A2APriority.HIGH,
        )

    async def send_regime_change(
        self,
        from_regime: str,
        to_regime: str,
        recipient: str = "broadcast",
        **details: Any,
    ) -> dict[str, Any]:
        """
        Send a regime change notification.

        Regime changes are sent at HIGH priority.

        Args:
            from_regime: Previous market regime.
            to_regime: New market regime.
            recipient: Target agent (default 'broadcast').
            **details: Additional context (volatility, liquidity, etc.).

        Returns:
            Delivery status dict.
        """
        payload: dict[str, Any] = {
            "from_regime": from_regime,
            "to_regime": to_regime,
            "source_agent": self.agent_id,
            **details,
        }
        return await self.send_to(
            recipient=recipient,
            msg_type=A2AMessageType.REGIME_CHANGE,
            payload=payload,
            priority=A2APriority.HIGH,
        )

    async def send_execution_report(
        self,
        symbol: str,
        side: str,
        status: str,
        recipient: str = "portfolio_manager",
        order_id: str | None = None,
        execution_price: float | None = None,
        slippage: float | None = None,
        commission: float | None = None,
        quantity: float | None = None,
        error: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Send an execution report message.

        Args:
            symbol: Ticker symbol.
            side: Order side ("BUY" / "SELL").
            status: Execution status ("FILLED", "REJECTED", "CANCELLED", "PENDING").
            recipient: Target agent (default 'portfolio_manager').
            order_id: Order identifier.
            execution_price: Fill price.
            slippage: Execution slippage.
            commission: Commission charged.
            quantity: Executed quantity.
            error: Error message if status is REJECTED or CANCELLED.
            correlation_id: Optional correlation ID.

        Returns:
            Delivery status dict.
        """
        payload: dict[str, Any] = {
            "symbol": symbol,
            "side": side.upper(),
            "status": status.upper(),
            "source_agent": self.agent_id,
        }
        if order_id is not None:
            payload["order_id"] = order_id
        if execution_price is not None:
            payload["execution_price"] = execution_price
        if slippage is not None:
            payload["slippage"] = slippage
        if commission is not None:
            payload["commission"] = commission
        if quantity is not None:
            payload["quantity"] = quantity
        if error is not None:
            payload["error"] = error

        priority = A2APriority.HIGH if status in ("REJECTED", "CANCELLED") else A2APriority.NORMAL
        return await self.send_to(
            recipient=recipient,
            msg_type=A2AMessageType.EXECUTION_REPORT,
            payload=payload,
            priority=priority,
            correlation_id=correlation_id,
        )

    async def send_research(
        self,
        symbol: str,
        research_type: str,
        data: dict[str, Any],
        recipient: str = "analyst",
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Send a research message.

        Args:
            symbol: Ticker symbol.
            research_type: Type of research ('sentiment', 'ohlcv', 'macro', etc.).
            data: Research data payload.
            recipient: Target agent (default 'analyst').
            correlation_id: Optional correlation ID.

        Returns:
            Delivery status dict.
        """
        payload: dict[str, Any] = {
            "symbol": symbol,
            "research_type": research_type,
            "data": data,
            "source_agent": self.agent_id,
        }
        return await self.send_to(
            recipient=recipient,
            msg_type=A2AMessageType.RESEARCH,
            payload=payload,
            priority=A2APriority.LOW,
            correlation_id=correlation_id,
        )

    # ── Convenience: broadcast versions ──────────────────────────────

    async def broadcast_signal(self, **kwargs: Any) -> dict[str, Any]:
        """Broadcast a signal to all agents."""
        kwargs.setdefault("recipient", "broadcast")
        return await self.send_signal(**kwargs)

    async def broadcast_risk_alert(self, **kwargs: Any) -> dict[str, Any]:
        """Broadcast a risk alert to all agents."""
        kwargs.setdefault("recipient", "broadcast")
        return await self.send_risk_alert(**kwargs)

    async def broadcast_execution_report(self, **kwargs: Any) -> dict[str, Any]:
        """Broadcast an execution report to all agents."""
        kwargs.setdefault("recipient", "broadcast")
        return await self.send_execution_report(**kwargs)


# ══════════════════════════════════════════════════════════════════════
# Module-level helpers
# ══════════════════════════════════════════════════════════════════════

_default_bus: A2ABus | None = None


def get_default_a2a_bus() -> A2ABus:
    """
    Return the module-level A2ABus singleton.

    Lazily creates the bus on first access.

    Returns:
        The shared A2ABus instance.
    """
    global _default_bus
    if _default_bus is None:
        _default_bus = A2ABus()
    return _default_bus


def reset_default_a2a_bus() -> None:
    """Reset the module-level A2ABus singleton (useful for testing)."""
    global _default_bus
    _default_bus = None
