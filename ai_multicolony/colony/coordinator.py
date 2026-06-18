"""Inter-colony coordination with A2A protocol.

Provides coordination between multiple colonies, including
task delegation, resource sharing, and A2A (Agent-to-Agent) protocol.
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Optional

from ai_multicolony.config.logging_config import get_logger
from ai_multicolony.core.event_bus import EventBus
from ai_multicolony.types.colony import ColonyTask
from ai_multicolony.types.messages import BusMessage

logger = get_logger(__name__)


class A2AMessageType(str, Enum):
    """A2A protocol message types."""

    TASK_REQUEST = "a2a.task_request"
    TASK_RESPONSE = "a2a.task_response"
    CAPABILITY_QUERY = "a2a.capability_query"
    CAPABILITY_RESPONSE = "a2a.capability_response"
    RESOURCE_REQUEST = "a2a.resource_request"
    RESOURCE_RESPONSE = "a2a.resource_response"
    STATUS_UPDATE = "a2a.status_update"
    HEARTBEAT = "a2a.heartbeat"
    BROADCAST = "a2a.broadcast"


class A2AMessage:
    """A2A protocol message."""

    def __init__(self, **kwargs: Any) -> None:
        self.id: str = kwargs.get("id", str(uuid.uuid4()))
        self.message_type: A2AMessageType = kwargs.get("message_type", A2AMessageType.HEARTBEAT)
        self.sender_colony: str = kwargs.get("sender_colony", "")
        self.recipient_colony: str = kwargs.get("recipient_colony", "")
        self.payload: dict[str, Any] = kwargs.get("payload", {})
        self.timestamp: float = kwargs.get("timestamp", time.time())
        self.correlation_id: Optional[str] = kwargs.get("correlation_id")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "message_type": self.message_type.value,
            "sender_colony": self.sender_colony,
            "recipient_colony": self.recipient_colony,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
        }


class ColonyCoordinator:
    """Coordinates activities between multiple colonies.

    Features:
    - Inter-colony communication via A2A protocol
    - Task delegation between colonies
    - Resource sharing and capability discovery
    - Conflict resolution
    - Heartbeat monitoring
    """

    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self._event_bus = event_bus or EventBus.get_instance()
        self._colonies: dict[str, dict[str, Any]] = {}
        self._delegated_tasks: dict[str, dict[str, ColonyTask]] = {}
        self._a2a_handlers: dict[A2AMessageType, list[Any]] = {}
        self._heartbeat_interval = 30.0
        self._last_heartbeat: dict[str, float] = {}

    def register_colony(self, colony_id: str, capabilities: Optional[list[str]] = None) -> None:
        """Register a colony with the coordinator.

        Args:
            colony_id: The colony ID.
            capabilities: Optional list of colony capabilities.
        """
        self._colonies[colony_id] = {
            "id": colony_id,
            "capabilities": capabilities or [],
            "status": "active",
            "registered_at": time.time(),
        }
        self._delegated_tasks[colony_id] = {}
        self._last_heartbeat[colony_id] = time.time()
        logger.info("colony_registered", colony_id=colony_id, capabilities=capabilities)

    def unregister_colony(self, colony_id: str) -> None:
        """Unregister a colony.

        Args:
            colony_id: The colony ID.
        """
        self._colonies.pop(colony_id, None)
        self._delegated_tasks.pop(colony_id, None)
        self._last_heartbeat.pop(colony_id, None)

    async def delegate_task(
        self,
        from_colony: str,
        to_colony: str,
        task: ColonyTask,
    ) -> bool:
        """Delegate a task from one colony to another using A2A protocol.

        Args:
            from_colony: Source colony ID.
            to_colony: Target colony ID.
            task: The task to delegate.

        Returns:
            True if delegation was successful.
        """
        if to_colony not in self._colonies:
            logger.error("delegation_target_not_found", target=to_colony)
            return False

        # Send A2A task request
        message = A2AMessage(
            message_type=A2AMessageType.TASK_REQUEST,
            sender_colony=from_colony,
            recipient_colony=to_colony,
            payload={
                "task_id": task.id,
                "task_title": task.title,
                "task_description": task.description,
                "task_priority": task.priority,
                "task_dependencies": task.dependencies,
            },
        )

        await self._send_a2a_message(message)

        self._delegated_tasks[to_colony][task.id] = task
        logger.info("task_delegated", from_colony=from_colony, to_colony=to_colony, task_id=task.id)
        return True

    async def broadcast_to_colonies(self, from_colony: str, message: str) -> None:
        """Broadcast a message to all colonies.

        Args:
            from_colony: Source colony ID.
            message: Message content.
        """
        a2a_msg = A2AMessage(
            message_type=A2AMessageType.BROADCAST,
            sender_colony=from_colony,
            payload={"message": message},
        )
        await self._send_a2a_message(a2a_msg)

        # Also use event bus for backward compatibility
        await self._event_bus.broadcast(
            sender=from_colony,
            channel="colony_coordination",
            content={"message": message},
            message_type="broadcast",
        )

    async def query_capabilities(self, from_colony: str, capability: str) -> list[dict[str, Any]]:
        """Query colonies for a specific capability.

        Args:
            from_colony: Source colony ID.
            capability: The capability to query.

        Returns:
            List of colonies with the capability.
        """
        results = []
        for colony_id, info in self._colonies.items():
            if colony_id == from_colony:
                continue
            if capability in info.get("capabilities", []):
                results.append({
                    "colony_id": colony_id,
                    "capability": capability,
                    "status": info.get("status", "unknown"),
                })

        # Send A2A capability query
        message = A2AMessage(
            message_type=A2AMessageType.CAPABILITY_QUERY,
            sender_colony=from_colony,
            payload={"capability": capability},
        )
        await self._send_a2a_message(message)

        return results

    def find_capable_colony(self, capability: str) -> Optional[str]:
        """Find a colony with a specific capability.

        Args:
            capability: The required capability.

        Returns:
            Colony ID with the capability, or None.
        """
        for colony_id, info in self._colonies.items():
            if capability in info.get("capabilities", []):
                return colony_id
        return None

    async def request_resource(
        self,
        from_colony: str,
        to_colony: str,
        resource_type: str,
        amount: float = 1.0,
    ) -> dict[str, Any]:
        """Request a resource from another colony.

        Args:
            from_colony: Source colony ID.
            to_colony: Target colony ID.
            resource_type: Type of resource.
            amount: Amount requested.

        Returns:
            Resource request result.
        """
        message = A2AMessage(
            message_type=A2AMessageType.RESOURCE_REQUEST,
            sender_colony=from_colony,
            recipient_colony=to_colony,
            payload={
                "resource_type": resource_type,
                "amount": amount,
            },
        )
        await self._send_a2a_message(message)

        return {
            "status": "requested",
            "from": from_colony,
            "to": to_colony,
            "resource_type": resource_type,
            "amount": amount,
        }

    def update_heartbeat(self, colony_id: str) -> None:
        """Update the heartbeat for a colony.

        Args:
            colony_id: The colony ID.
        """
        self._last_heartbeat[colony_id] = time.time()

    def get_inactive_colonies(self, timeout: float = 60.0) -> list[str]:
        """Get colonies that haven't sent a heartbeat recently.

        Args:
            timeout: Timeout in seconds.

        Returns:
            List of inactive colony IDs.
        """
        now = time.time()
        return [
            colony_id for colony_id, last_hb in self._last_heartbeat.items()
            if now - last_hb > timeout
        ]

    async def _send_a2a_message(self, message: A2AMessage) -> None:
        """Send an A2A protocol message via the event bus.

        Args:
            message: The A2A message.
        """
        try:
            if message.recipient_colony:
                await self._event_bus.send_direct(
                    sender=message.sender_colony,
                    recipient=message.recipient_colony,
                    channel="a2a",
                    content=message.to_dict(),
                    message_type=message.message_type.value,
                )
            else:
                await self._event_bus.broadcast(
                    sender=message.sender_colony,
                    channel="a2a",
                    content=message.to_dict(),
                    message_type=message.message_type.value,
                )
        except Exception as e:
            logger.warning("a2a_message_error", error=str(e))

        # Call registered handlers
        handlers = self._a2a_handlers.get(message.message_type, [])
        for handler in handlers:
            try:
                if hasattr(handler, '__call__'):
                    import asyncio
                    if asyncio.iscoroutinefunction(handler):
                        await handler(message)
                    else:
                        handler(message)
            except Exception as e:
                logger.warning("a2a_handler_error", error=str(e))

    def register_a2a_handler(self, message_type: A2AMessageType, handler: Any) -> None:
        """Register a handler for A2A messages.

        Args:
            message_type: The message type to handle.
            handler: The handler function.
        """
        if message_type not in self._a2a_handlers:
            self._a2a_handlers[message_type] = []
        self._a2a_handlers[message_type].append(handler)

    def get_status(self) -> dict[str, Any]:
        """Get coordination status."""
        return {
            "registered_colonies": len(self._colonies),
            "delegated_tasks": {
                cid: len(tasks) for cid, tasks in self._delegated_tasks.items()
            },
            "inactive_colonies": len(self.get_inactive_colonies()),
            "a2a_handlers": {
                mt.value: len(handlers) for mt, handlers in self._a2a_handlers.items()
            },
        }
