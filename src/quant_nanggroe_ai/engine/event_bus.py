"""
Event Bus System
=================
From Quant-Nanggroe-AI — Async pub/sub event system for real-time communication.

Provides a unified event bus for inter-component communication:
  - Redis pub/sub integration for distributed systems
  - In-memory fallback when Redis is unavailable
  - Async event publishing and subscription
  - Pydantic-serialized event schemas
  - Dead letter queue for failed event processing
  - Event types: market_data, agent_signals, execution_commands, risk_alerts

The event bus follows a topic-based pub/sub pattern where publishers
emit events to named channels and subscribers receive all events on
their subscribed channels.

Event flow:
    Publisher → EventBus.publish(channel, event) → Subscribers → callback(event)

Failed events are routed to the dead letter queue for inspection and
reprocessing.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Awaitable

from pydantic import BaseModel, Field

from quant_nanggroe_ai.config import RedisSettings
from quant_nanggroe_ai.exceptions import EngineError
from quant_nanggroe_ai.logging import get_logger

logger = get_logger(__name__)

# Try importing Redis — graceful fallback if unavailable
try:
    import redis.asyncio as aioredis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis_not_available", message="Falling back to in-memory event bus")


# ══════════════════════════════════════════════════════════════════════
# EVENT TYPE DEFINITIONS
# ══════════════════════════════════════════════════════════════════════


class EventType(str, Enum):
    """Classification of event types in the system."""

    MARKET_DATA = "market_data"
    AGENT_SIGNALS = "agent_signals"
    EXECUTION_COMMANDS = "execution_commands"
    RISK_ALERTS = "risk_alerts"
    SYSTEM = "system"
    REGIME_CHANGE = "regime_change"
    STRATEGY_LIFECYCLE = "strategy_lifecycle"
    AUDIT = "audit"


class EventPriority(str, Enum):
    """Event priority levels for processing ordering."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


# ══════════════════════════════════════════════════════════════════════
# PYDANTIC EVENT SCHEMAS
# ══════════════════════════════════════════════════════════════════════


class Event(BaseModel):
    """Base event model with serialization support."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = EventType.SYSTEM
    channel: str = ""
    priority: EventPriority = EventPriority.NORMAL
    source: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    correlation_id: str | None = Field(
        default=None,
        description="ID for tracking related events across services",
    )

    def serialize(self) -> str:
        """Serialize event to JSON string for transmission."""
        return self.model_dump_json()

    @classmethod
    def deserialize(cls, data: str) -> Event:
        """Deserialize event from JSON string."""
        return cls.model_validate_json(data)


class MarketDataEvent(BaseModel):
    """Event for market data updates."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = EventType.MARKET_DATA
    channel: str = "market_data"
    source: str = ""
    symbol: str
    price: float
    volume: float = 0.0
    change_pct: float = 0.0
    bid: float | None = None
    ask: float | None = None
    timestamp: datetime = Field(default_factory=datetime.now)

    def to_event(self) -> Event:
        """Convert to generic Event for bus transmission."""
        return Event(
            event_id=self.event_id,
            event_type=self.event_type,
            channel=self.channel,
            source=self.source,
            payload=self.model_dump(exclude={"event_id", "event_type", "channel", "source", "timestamp"}),
            timestamp=self.timestamp,
        )


class AgentSignalEvent(BaseModel):
    """Event for agent-generated trading signals."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = EventType.AGENT_SIGNALS
    channel: str = "agent_signals"
    source: str = ""
    agent_name: str
    signal_type: str  # e.g., "BUY", "SELL", "HOLD", "RISK_ALERT"
    symbol: str = ""
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    reasoning: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)

    def to_event(self) -> Event:
        """Convert to generic Event for bus transmission."""
        return Event(
            event_id=self.event_id,
            event_type=self.event_type,
            channel=self.channel,
            source=self.source,
            payload=self.model_dump(exclude={"event_id", "event_type", "channel", "source", "timestamp"}),
            timestamp=self.timestamp,
        )


class ExecutionCommandEvent(BaseModel):
    """Event for trade execution commands."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = EventType.EXECUTION_COMMANDS
    channel: str = "execution_commands"
    source: str = ""
    action: str  # "BUY", "SELL", "CLOSE", "MODIFY"
    symbol: str
    quantity: float = 0.0
    order_type: str = "MARKET"  # MARKET, LIMIT, STOP
    price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    timestamp: datetime = Field(default_factory=datetime.now)

    def to_event(self) -> Event:
        """Convert to generic Event for bus transmission."""
        return Event(
            event_id=self.event_id,
            event_type=self.event_type,
            channel=self.channel,
            source=self.source,
            payload=self.model_dump(exclude={"event_id", "event_type", "channel", "source", "timestamp"}),
            timestamp=self.timestamp,
        )


class RiskAlertEvent(BaseModel):
    """Event for risk management alerts."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = EventType.RISK_ALERTS
    channel: str = "risk_alerts"
    source: str = ""
    alert_type: str  # "DAILY_LIMIT", "KILL_SWITCH", "CORRELATION", "DRAWDOWN"
    severity: str = "WARNING"  # INFO, WARNING, CRITICAL
    message: str
    symbol: str = ""
    current_value: float | None = None
    threshold: float | None = None
    timestamp: datetime = Field(default_factory=datetime.now)

    def to_event(self) -> Event:
        """Convert to generic Event for bus transmission."""
        return Event(
            event_id=self.event_id,
            event_type=self.event_type,
            channel=self.channel,
            source=self.source,
            payload=self.model_dump(exclude={"event_id", "event_type", "channel", "source", "timestamp"}),
            timestamp=self.timestamp,
        )


class DeadLetterEntry(BaseModel):
    """Entry in the dead letter queue for failed events."""

    event: Event
    error: str
    channel: str
    retry_count: int = 0
    max_retries: int = 3
    first_failed_at: datetime = Field(default_factory=datetime.now)
    last_failed_at: datetime = Field(default_factory=datetime.now)


# ══════════════════════════════════════════════════════════════════════
# CALLBACK TYPE
# ══════════════════════════════════════════════════════════════════════

EventHandler = Callable[[Event], Awaitable[None]]


# ══════════════════════════════════════════════════════════════════════
# EVENT BUS ENGINE
# ══════════════════════════════════════════════════════════════════════


class EventBusEngine:
    """
    Async event bus with Redis pub/sub integration and in-memory fallback.

    Features:
    - Redis pub/sub for distributed event distribution
    - In-memory bus fallback when Redis unavailable
    - Async event publishing and subscription
    - Pydantic-serialized event schemas
    - Dead letter queue for failed events
    - Automatic retry of failed events
    - Event type filtering
    - Correlation ID tracking for distributed tracing

    The bus supports two modes:
    1. Redis mode: Events are published to Redis channels, enabling
       multi-process and multi-service communication.
    2. In-memory mode: Events are dispatched to local subscribers,
       suitable for single-process deployments or testing.

    Example:
        bus = EventBusEngine()
        await bus.start()

        # Subscribe
        async def on_market_data(event: Event):
            print(f"Got market data: {event.payload}")

        await bus.subscribe("market_data", on_market_data)

        # Publish
        event = MarketDataEvent(symbol="XAUUSD", price=2000.0).to_event()
        await bus.publish("market_data", event)

        # Stop
        await bus.stop()
    """

    MAX_DEAD_LETER_ENTRIES = 1000
    MAX_SUBSCRIBERS_PER_CHANNEL = 50

    def __init__(
        self,
        redis_url: str | None = None,
        use_redis: bool = True,
    ) -> None:
        """
        Initialize the event bus.

        Args:
            redis_url: Redis connection URL. If None, reads from config.
            use_redis: Whether to attempt Redis connection. If False,
                always uses in-memory mode.
        """
        self._redis_url = redis_url or RedisSettings().url
        self._use_redis = use_redis and REDIS_AVAILABLE
        self._redis: aioredis.Redis | None = None
        self._is_running = False

        # In-memory subscribers: channel -> list of callbacks
        self._subscribers: dict[str, list[EventHandler]] = {}

        # Redis pub/sub task
        self._redis_subscriber_task: asyncio.Task | None = None
        self._redis_pubsub: aioredis.client.PubSub | None = None

        # Dead letter queue
        self._dead_letter_queue: list[DeadLetterEntry] = []

        # Event statistics
        self._stats: dict[str, Any] = {
            "published": 0,
            "delivered": 0,
            "failed": 0,
            "dead_lettered": 0,
            "by_channel": {},
            "by_type": {},
        }

    @property
    def is_running(self) -> bool:
        """Whether the event bus is currently running."""
        return self._is_running

    @property
    def is_redis_mode(self) -> bool:
        """Whether the bus is using Redis for distribution."""
        return self._redis is not None and self._is_running

    @property
    def mode(self) -> str:
        """Current bus mode: 'redis' or 'in_memory'."""
        return "redis" if self.is_redis_mode else "in_memory"

    # ══════════════════════════════════════════════════════════════════
    # Lifecycle
    # ══════════════════════════════════════════════════════════════════

    async def start(self) -> dict[str, Any]:
        """
        Start the event bus.

        Attempts to connect to Redis if configured. Falls back to
        in-memory mode if Redis is unavailable.

        Returns:
            Dict with startup status
        """
        if self._is_running:
            return {"status": "ALREADY_RUNNING", "mode": self.mode}

        if self._use_redis:
            try:
                self._redis = aioredis.from_url(
                    self._redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                )
                # Test connection
                await self._redis.ping()
                self._is_running = True

                logger.info(
                    "event_bus_started",
                    mode="redis",
                    redis_url=self._redis_url,
                )

                return {"status": "STARTED", "mode": "redis"}

            except Exception as e:
                logger.warning(
                    "redis_connection_failed",
                    error=str(e),
                    fallback="in_memory",
                )
                self._redis = None

        # In-memory mode
        self._is_running = True

        logger.info("event_bus_started", mode="in_memory")

        return {"status": "STARTED", "mode": "in_memory"}

    async def stop(self) -> dict[str, Any]:
        """
        Stop the event bus.

        Closes Redis connections and cancels subscriber tasks.

        Returns:
            Dict with shutdown status
        """
        if not self._is_running:
            return {"status": "NOT_RUNNING"}

        # Cancel Redis subscriber task
        if self._redis_subscriber_task is not None:
            self._redis_subscriber_task.cancel()
            try:
                await self._redis_subscriber_task
            except asyncio.CancelledError:
                pass
            self._redis_subscriber_task = None

        # Close Redis connection
        if self._redis is not None:
            try:
                if self._redis_pubsub is not None:
                    await self._redis_pubsub.unsubscribe()
                    await self._redis_pubsub.close()
                    self._redis_pubsub = None
                await self._redis.close()
            except Exception as e:
                logger.warning("redis_close_error", error=str(e))
            self._redis = None

        self._is_running = False

        logger.info("event_bus_stopped", mode=self.mode)

        return {
            "status": "STOPPED",
            "stats": self._stats,
        }

    # ══════════════════════════════════════════════════════════════════
    # Publishing
    # ══════════════════════════════════════════════════════════════════

    async def publish(self, channel: str, event: Event) -> dict[str, Any]:
        """
        Publish an event to a channel.

        In Redis mode, the event is published to the Redis channel.
        In in-memory mode, the event is dispatched to local subscribers.

        Args:
            channel: Channel name to publish to
            event: Event to publish

        Returns:
            Dict with publish result
        """
        if not self._is_running:
            raise EngineError("Event bus is not running. Call start() first.")

        # Update event channel
        event.channel = channel

        # Track statistics
        self._stats["published"] += 1
        self._stats["by_channel"][channel] = self._stats["by_channel"].get(channel, 0) + 1
        event_type_key = event.event_type.value
        self._stats["by_type"][event_type_key] = self._stats["by_type"].get(event_type_key, 0) + 1

        # Redis publish
        if self._redis is not None:
            try:
                message = event.serialize()
                num_receivers = await self._redis.publish(channel, message)

                logger.debug(
                    "event_published_redis",
                    channel=channel,
                    event_id=event.event_id,
                    event_type=event.event_type.value,
                    num_receivers=num_receivers,
                )

                # Also deliver to local subscribers
                await self._dispatch_local(channel, event)

                return {
                    "status": "PUBLISHED",
                    "channel": channel,
                    "event_id": event.event_id,
                    "redis_receivers": num_receivers,
                    "local_subscribers": len(self._subscribers.get(channel, [])),
                }

            except Exception as e:
                logger.warning(
                    "redis_publish_failed",
                    channel=channel,
                    error=str(e),
                    fallback="local",
                )
                # Fall through to local dispatch

        # In-memory dispatch
        await self._dispatch_local(channel, event)

        return {
            "status": "PUBLISHED",
            "channel": channel,
            "event_id": event.event_id,
            "mode": "in_memory",
            "local_subscribers": len(self._subscribers.get(channel, [])),
        }

    async def publish_typed(self, event: BaseModel) -> dict[str, Any]:
        """
        Publish a typed event (MarketDataEvent, AgentSignalEvent, etc.).

        Automatically converts the typed event to a generic Event
        and publishes to the appropriate channel.

        Args:
            event: Typed event with to_event() method

        Returns:
            Dict with publish result
        """
        if hasattr(event, "to_event"):
            generic_event = event.to_event()  # type: ignore[union-attr]
            channel = generic_event.channel or "unknown"
            return await self.publish(channel, generic_event)

        raise EngineError(f"Event type {type(event)} does not have to_event() method")

    # ══════════════════════════════════════════════════════════════════
    # Subscription
    # ══════════════════════════════════════════════════════════════════

    async def subscribe(
        self,
        channel: str,
        handler: EventHandler,
    ) -> dict[str, Any]:
        """
        Subscribe to events on a channel.

        In Redis mode, also subscribes to the Redis channel.
        Multiple handlers can be registered per channel.

        Args:
            channel: Channel name to subscribe to
            handler: Async callback function that receives Event objects

        Returns:
            Dict with subscription result
        """
        # Add to local subscribers
        if channel not in self._subscribers:
            self._subscribers[channel] = []

        if len(self._subscribers[channel]) >= self.MAX_SUBSCRIBERS_PER_CHANNEL:
            raise EngineError(
                f"Max subscribers ({self.MAX_SUBSCRIBERS_PER_CHANNEL}) "
                f"reached for channel '{channel}'"
            )

        self._subscribers[channel].append(handler)

        # Subscribe to Redis channel if in Redis mode
        if self._redis is not None and self._redis_pubsub is None:
            try:
                self._redis_pubsub = self._redis.pubsub()
                await self._redis_pubsub.subscribe(channel)

                # Start Redis subscriber task
                self._redis_subscriber_task = asyncio.create_task(
                    self._redis_subscriber_loop()
                )

            except Exception as e:
                logger.warning(
                    "redis_subscribe_failed",
                    channel=channel,
                    error=str(e),
                )

        elif self._redis is not None and self._redis_pubsub is not None:
            try:
                await self._redis_pubsub.subscribe(channel)
            except Exception as e:
                logger.warning(
                    "redis_subscribe_add_failed",
                    channel=channel,
                    error=str(e),
                )

        logger.info(
            "subscribed",
            channel=channel,
            handler_count=len(self._subscribers[channel]),
            mode=self.mode,
        )

        return {
            "status": "SUBSCRIBED",
            "channel": channel,
            "handler_count": len(self._subscribers[channel]),
            "mode": self.mode,
        }

    async def unsubscribe(
        self,
        channel: str,
        handler: EventHandler | None = None,
    ) -> dict[str, Any]:
        """
        Unsubscribe from a channel.

        If handler is provided, removes only that handler.
        If handler is None, removes all handlers from the channel.

        Args:
            channel: Channel to unsubscribe from
            handler: Optional specific handler to remove

        Returns:
            Dict with unsubscription result
        """
        if channel not in self._subscribers:
            return {"status": "NOT_SUBSCRIBED", "channel": channel}

        if handler is None:
            # Remove all handlers
            del self._subscribers[channel]
        else:
            self._subscribers[channel] = [
                h for h in self._subscribers[channel] if h != handler
            ]
            if not self._subscribers[channel]:
                del self._subscribers[channel]

        # Unsubscribe from Redis
        if self._redis is not None and self._redis_pubsub is not None:
            if channel not in self._subscribers:
                try:
                    await self._redis_pubsub.unsubscribe(channel)
                except Exception as e:
                    logger.warning("redis_unsubscribe_failed", channel=channel, error=str(e))

        return {
            "status": "UNSUBSCRIBED",
            "channel": channel,
            "remaining_handlers": len(self._subscribers.get(channel, [])),
        }

    # ══════════════════════════════════════════════════════════════════
    # Dead Letter Queue
    # ══════════════════════════════════════════════════════════════════

    async def retry_dead_letter(self, event_id: str | None = None) -> dict[str, Any]:
        """
        Retry events from the dead letter queue.

        If event_id is provided, retries only that specific event.
        Otherwise, retries all eligible events (retry_count < max_retries).

        Args:
            event_id: Optional specific event ID to retry

        Returns:
            Dict with retry results
        """
        retried = 0
        still_failed = 0

        entries_to_retry = [
            e for e in self._dead_letter_queue
            if (event_id is None or e.event.event_id == event_id)
            and e.retry_count < e.max_retries
        ]

        for entry in entries_to_retry:
            try:
                await self._dispatch_local(entry.channel, entry.event)
                self._dead_letter_queue.remove(entry)
                retried += 1
            except Exception as e:
                entry.retry_count += 1
                entry.last_failed_at = datetime.now()
                still_failed += 1

        return {
            "retried": retried,
            "still_failed": still_failed,
            "dead_letter_count": len(self._dead_letter_queue),
        }

    def get_dead_letter_queue(
        self,
        channel: str | None = None,
        limit: int = 50,
    ) -> list[DeadLetterEntry]:
        """
        Get entries from the dead letter queue.

        Args:
            channel: Optional channel filter
            limit: Maximum entries to return

        Returns:
            List of DeadLetterEntry objects
        """
        entries = self._dead_letter_queue
        if channel:
            entries = [e for e in entries if e.channel == channel]
        return entries[-limit:]

    def purge_dead_letter_queue(self) -> int:
        """
        Clear all entries from the dead letter queue.

        Returns:
            Number of entries purged
        """
        count = len(self._dead_letter_queue)
        self._dead_letter_queue = []
        return count

    # ══════════════════════════════════════════════════════════════════
    # Internal Methods
    # ══════════════════════════════════════════════════════════════════

    async def _dispatch_local(self, channel: str, event: Event) -> None:
        """
        Dispatch event to local in-memory subscribers.

        Args:
            channel: Target channel
            event: Event to dispatch
        """
        handlers = self._subscribers.get(channel, [])
        if not handlers:
            return

        for handler in handlers:
            try:
                await handler(event)
                self._stats["delivered"] += 1
            except Exception as e:
                self._stats["failed"] += 1
                logger.warning(
                    "event_handler_failed",
                    channel=channel,
                    event_id=event.event_id,
                    handler=str(handler),
                    error=str(e),
                )

                # Add to dead letter queue
                self._add_to_dead_letter(event, str(e), channel)

    async def _redis_subscriber_loop(self) -> None:
        """
        Background task that listens for Redis pub/sub messages.

        Runs continuously until cancelled, dispatching received
        messages to local subscribers.
        """
        if self._redis_pubsub is None:
            return

        try:
            async for message in self._redis_pubsub.listen():
                if message["type"] == "message":
                    try:
                        channel = message["channel"]
                        data = message["data"]
                        event = Event.deserialize(data)
                        await self._dispatch_local(channel, event)
                    except Exception as e:
                        logger.warning(
                            "redis_message_dispatch_failed",
                            error=str(e),
                        )
                        self._stats["failed"] += 1

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("redis_subscriber_loop_error", error=str(e))

    def _add_to_dead_letter(
        self,
        event: Event,
        error: str,
        channel: str,
    ) -> None:
        """
        Add a failed event to the dead letter queue.

        Args:
            event: The failed event
            error: Error message from the failure
            channel: The channel the event was on
        """
        # Check if already in DLQ
        for entry in self._dead_letter_queue:
            if entry.event.event_id == event.event_id:
                entry.retry_count += 1
                entry.last_failed_at = datetime.now()
                return

        entry = DeadLetterEntry(
            event=event,
            error=error[:500],  # Truncate long errors
            channel=channel,
        )

        self._dead_letter_queue.append(entry)
        self._stats["dead_lettered"] += 1

        # Trim if over max
        if len(self._dead_letter_queue) > self.MAX_DEAD_LETER_ENTRIES:
            self._dead_letter_queue = self._dead_letter_queue[-self.MAX_DEAD_LETER_ENTRIES:]

    # ══════════════════════════════════════════════════════════════════
    # Status and Introspection
    # ══════════════════════════════════════════════════════════════════

    def status(self) -> dict[str, Any]:
        """Get current event bus status."""
        return {
            "is_running": self._is_running,
            "mode": self.mode,
            "redis_available": REDIS_AVAILABLE,
            "redis_connected": self._redis is not None,
            "channels": {
                channel: len(handlers)
                for channel, handlers in self._subscribers.items()
            },
            "total_subscriptions": sum(
                len(handlers) for handlers in self._subscribers.values()
            ),
            "dead_letter_count": len(self._dead_letter_queue),
            "stats": self._stats,
            "timestamp": datetime.now().isoformat(),
        }

    def get_stats(self) -> dict[str, Any]:
        """Get detailed event bus statistics."""
        return {
            "published": self._stats["published"],
            "delivered": self._stats["delivered"],
            "failed": self._stats["failed"],
            "dead_lettered": self._stats["dead_lettered"],
            "delivery_rate": (
                round(self._stats["delivered"] / self._stats["published"], 4)
                if self._stats["published"] > 0
                else 0.0
            ),
            "by_channel": self._stats["by_channel"],
            "by_type": self._stats["by_type"],
        }
