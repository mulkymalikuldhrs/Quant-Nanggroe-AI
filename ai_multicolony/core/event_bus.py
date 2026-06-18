"""Event/Message bus for the AI MultiColony Ecosystem.

Merges Nanobot MessageBus with InboundMessage/OutboundMessage patterns
and OpenHands EventStream with Action/Observation pattern. Provides:
- Publish/subscribe pattern for events
- Direct and broadcast messaging
- Channel-based routing
- Priority-based message ordering
- Action/Observation pairing (from OpenHands)
- InboundMessage/OutboundMessage routing (from Nanobot)
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import defaultdict
from typing import Any, Callable, Coroutine, Optional

from ai_multicolony.config.logging_config import get_logger
from ai_multicolony.exceptions import EventBusError
from ai_multicolony.types.events import Action, Event, EventType, Observation
from ai_multicolony.types.messages import BusMessage, BusMessagePriority, MessageType

logger = get_logger(__name__)

# Type aliases for event handlers
EventHandler = Callable[[Event], Coroutine[Any, Any, None]]
MessageHandler = Callable[[BusMessage], Coroutine[Any, Any, None]]


class EventBus:
    """Asynchronous event bus for agent communication.

    Supports:
    - Publish/subscribe pattern for events
    - Direct and broadcast messaging
    - Channel-based routing
    - Priority-based message ordering
    - Action/Observation pairing (from OpenHands)
    - InboundMessage/OutboundMessage routing (from Nanobot)
    """

    _instance: Optional[EventBus] = None

    def __init__(self, max_history: int = 1000) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._message_handlers: dict[str, list[MessageHandler]] = defaultdict(list)
        self._channel_subscribers: dict[str, list[MessageHandler]] = defaultdict(list)
        self._history: list[Event] = []
        self._message_history: list[BusMessage] = []
        self._max_history = max_history
        self._pending_observations: dict[str, asyncio.Future[Observation]] = {}
        self._lock = asyncio.Lock()
        self._running = False
        self._event_count = 0
        self._message_count = 0

    @classmethod
    def get_instance(cls) -> EventBus:
        """Get the global singleton event bus."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the global event bus (for testing)."""
        cls._instance = None

    async def start(self) -> None:
        """Start the event bus."""
        self._running = True
        logger.info("event_bus_started")

    async def stop(self) -> None:
        """Stop the event bus and cancel pending observations."""
        self._running = False
        for future in self._pending_observations.values():
            if not future.done():
                future.cancel()
        self._pending_observations.clear()
        logger.info("event_bus_stopped", events_processed=self._event_count, messages_processed=self._message_count)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def event_count(self) -> int:
        """Total number of events published."""
        return self._event_count

    @property
    def message_count(self) -> int:
        """Total number of messages sent."""
        return self._message_count

    # === Event Publishing (OpenHands EventStream pattern) ===

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe to events of a specific type.

        Args:
            event_type: The type of event to subscribe to ("action", "observation", or custom).
            handler: Async callback function for the event.
        """
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Unsubscribe from events of a specific type.

        Args:
            event_type: The event type.
            handler: The handler to remove.
        """
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                h for h in self._subscribers[event_type] if h != handler
            ]

    async def publish_event(self, event: Event) -> None:
        """Publish an event to all subscribers.

        Args:
            event: The event to publish.
        """
        self._event_count += 1

        if not self._running:
            logger.warning("event_bus_not_running", event_id=event.id)
            return

        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        handlers = self._subscribers.get(event.event_type.value if isinstance(event.event_type, EventType) else event.event_type, [])
        handlers += self._subscribers.get("*", [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error("event_handler_error", handler=str(handler), error=str(e))

    async def publish_action(self, action: Action) -> None:
        """Publish an action event.

        Args:
            action: The action to publish.
        """
        event = Event(
            event_type=EventType.ACTION,
            source=action.agent_id,
            action=action,
            data={"action_type": action.action_type.value},
        )
        await self.publish_event(event)

    async def publish_observation(self, observation: Observation) -> None:
        """Publish an observation event and resolve any pending futures.

        Args:
            observation: The observation to publish.
        """
        event = Event(
            event_type=EventType.OBSERVATION,
            source=observation.agent_id,
            observation=observation,
            data={"observation_type": observation.observation_type.value},
        )
        await self.publish_event(event)

        # Resolve pending observation futures
        action_id = observation.action_id
        if action_id in self._pending_observations:
            future = self._pending_observations.pop(action_id)
            if not future.done():
                future.set_result(observation)

    async def wait_for_observation(self, action_id: str, timeout: float = 60.0) -> Observation:
        """Wait for an observation in response to an action.

        Args:
            action_id: The action ID to wait for.
            timeout: Timeout in seconds.

        Returns:
            The observation response.

        Raises:
            EventBusError: If the wait times out.
        """
        if action_id in self._pending_observations:
            raise EventBusError(f"Already waiting for action {action_id}")

        loop = asyncio.get_event_loop()
        future: asyncio.Future[Observation] = loop.create_future()
        self._pending_observations[action_id] = future

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending_observations.pop(action_id, None)
            raise EventBusError(f"Timeout waiting for observation for action {action_id}")

    # === Message Bus (Nanobot MessageBus pattern) ===

    def subscribe_channel(self, channel: str, handler: MessageHandler) -> None:
        """Subscribe to messages on a specific channel.

        Args:
            channel: The channel name.
            handler: Async callback for messages.
        """
        self._channel_subscribers[channel].append(handler)

    def unsubscribe_channel(self, channel: str, handler: MessageHandler) -> None:
        """Unsubscribe from a channel.

        Args:
            channel: The channel name.
            handler: The handler to remove.
        """
        if channel in self._channel_subscribers:
            self._channel_subscribers[channel] = [
                h for h in self._channel_subscribers[channel] if h != handler
            ]

    def subscribe_messages(self, message_type: str, handler: MessageHandler) -> None:
        """Subscribe to messages of a specific type.

        Args:
            message_type: The message type to listen for.
            handler: Async callback for messages.
        """
        self._message_handlers[message_type].append(handler)

    async def send_message(self, message: BusMessage) -> None:
        """Send a message on the bus.

        If recipient is specified, it's a direct message.
        If recipient is None, it's a broadcast.

        Args:
            message: The message to send.
        """
        self._message_count += 1

        if not self._running:
            logger.warning("event_bus_not_running_message", message_id=message.id)
            return

        self._message_history.append(message)
        if len(self._message_history) > self._max_history:
            self._message_history = self._message_history[-self._max_history:]

        # Route to channel subscribers
        channel_handlers = self._channel_subscribers.get(message.channel, [])
        channel_handlers += self._channel_subscribers.get("*", [])
        for handler in channel_handlers:
            try:
                await handler(message)
            except Exception as e:
                logger.error("message_handler_error", handler=str(handler), error=str(e))

        # Route to general message handlers
        msg_type = message.message_type.value if isinstance(message.message_type, MessageType) else str(message.message_type)
        for handler in self._message_handlers.get(msg_type, []):
            try:
                await handler(message)
            except Exception as e:
                logger.error("message_type_handler_error", error=str(e))

    async def broadcast(self, sender: str, channel: str, content: dict[str, Any], message_type: MessageType = MessageType.BROADCAST) -> BusMessage:
        """Broadcast a message to all subscribers on a channel.

        Args:
            sender: Sender agent ID.
            channel: Channel name.
            content: Message content.
            message_type: Message type.

        Returns:
            The broadcast message.
        """
        message = BusMessage(
            sender=sender,
            recipient=None,
            channel=channel,
            message_type=message_type,
            content=content,
            priority=BusMessagePriority.NORMAL,
        )
        await self.send_message(message)
        return message

    async def send_direct(
        self,
        sender: str,
        recipient: str,
        channel: str,
        content: dict[str, Any],
        message_type: MessageType = MessageType.REQUEST,
        correlation_id: Optional[str] = None,
    ) -> BusMessage:
        """Send a direct message to a specific recipient.

        Args:
            sender: Sender agent ID.
            recipient: Recipient agent ID.
            channel: Channel name.
            content: Message content.
            message_type: Message type.
            correlation_id: Optional correlation ID for request-response.

        Returns:
            The sent message.
        """
        message = BusMessage(
            sender=sender,
            recipient=recipient,
            channel=channel,
            message_type=message_type,
            content=content,
            correlation_id=correlation_id,
        )
        await self.send_message(message)
        return message

    # === History and query ===

    def get_event_history(
        self,
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 100,
    ) -> list[Event]:
        """Get event history with optional filtering.

        Args:
            event_type: Filter by event type.
            source: Filter by source agent ID.
            limit: Maximum number of events to return.

        Returns:
            Filtered list of events.
        """
        events = self._history
        if event_type:
            events = [e for e in events if (e.event_type.value if isinstance(e.event_type, EventType) else e.event_type) == event_type]
        if source:
            events = [e for e in events if e.source == source]
        return events[-limit:]

    def get_message_history(
        self,
        channel: Optional[str] = None,
        sender: Optional[str] = None,
        limit: int = 100,
    ) -> list[BusMessage]:
        """Get message history with optional filtering.

        Args:
            channel: Filter by channel.
            sender: Filter by sender.
            limit: Maximum number of messages.

        Returns:
            Filtered list of messages.
        """
        messages = self._message_history
        if channel:
            messages = [m for m in messages if m.channel == channel]
        if sender:
            messages = [m for m in messages if m.sender == sender]
        return messages[-limit:]

    def get_stats(self) -> dict[str, Any]:
        """Get bus statistics."""
        return {
            "running": self._running,
            "total_events": self._event_count,
            "total_messages": self._message_count,
            "history_size": len(self._history),
            "message_history_size": len(self._message_history),
            "subscriber_count": sum(len(v) for v in self._subscribers.values()),
            "channel_subscriber_count": sum(len(v) for v in self._channel_subscribers.values()),
            "pending_observations": len(self._pending_observations),
        }

    def clear_history(self) -> None:
        """Clear all history."""
        self._history.clear()
        self._message_history.clear()
