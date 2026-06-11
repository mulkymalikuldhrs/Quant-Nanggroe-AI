"""
Tests for Event Bus System
==========================
Tests the async pub/sub event bus in in-memory mode
(no Redis dependency required).
"""

from __future__ import annotations

import asyncio
import pytest

from quant_nanggroe_ai.engine.event_bus import (
    EventBusEngine,
    Event,
    EventType,
    EventPriority,
    MarketDataEvent,
    AgentSignalEvent,
    ExecutionCommandEvent,
    RiskAlertEvent,
    DeadLetterEntry,
    EventHandler,
)


# ══════════════════════════════════════════════════════════════════════
# PYDANTIC MODEL TESTS
# ══════════════════════════════════════════════════════════════════════


class TestEventModel:
    """Test Event Pydantic model."""

    def test_default_creation(self) -> None:
        event = Event()
        assert event.event_id  # UUID auto-generated
        assert event.event_type == EventType.SYSTEM
        assert event.priority == EventPriority.NORMAL
        assert event.payload == {}

    def test_custom_creation(self) -> None:
        event = Event(
            event_type=EventType.MARKET_DATA,
            channel="market_data",
            priority=EventPriority.HIGH,
            source="test",
            payload={"symbol": "EURUSD", "price": 1.1000},
        )
        assert event.event_type == EventType.MARKET_DATA
        assert event.priority == EventPriority.HIGH
        assert event.source == "test"

    def test_serialization_roundtrip(self) -> None:
        event = Event(
            event_type=EventType.AGENT_SIGNALS,
            channel="agent_signals",
            payload={"signal": "BUY"},
            correlation_id="corr-123",
        )
        json_str = event.serialize()
        restored = Event.deserialize(json_str)
        assert restored.event_id == event.event_id
        assert restored.event_type == EventType.AGENT_SIGNALS
        assert restored.payload == {"signal": "BUY"}
        assert restored.correlation_id == "corr-123"


class TestMarketDataEvent:
    def test_creation(self) -> None:
        mde = MarketDataEvent(symbol="XAUUSD", price=2000.0)
        assert mde.event_type == EventType.MARKET_DATA
        assert mde.channel == "market_data"
        assert mde.symbol == "XAUUSD"
        assert mde.price == 2000.0

    def test_to_event(self) -> None:
        mde = MarketDataEvent(
            symbol="BTCUSDT", price=50000.0,
            volume=100.0, change_pct=0.05,
        )
        event = mde.to_event()
        assert event.event_type == EventType.MARKET_DATA
        assert event.channel == "market_data"
        assert event.payload["symbol"] == "BTCUSDT"
        assert event.payload["price"] == 50000.0


class TestAgentSignalEvent:
    def test_creation(self) -> None:
        ase = AgentSignalEvent(
            agent_name="strategist", signal_type="BUY",
            symbol="EURUSD", confidence=0.85,
        )
        assert ase.event_type == EventType.AGENT_SIGNALS
        assert ase.confidence == 0.85

    def test_confidence_bounds(self) -> None:
        AgentSignalEvent(agent_name="test", signal_type="BUY", confidence=0.0)
        AgentSignalEvent(agent_name="test", signal_type="BUY", confidence=1.0)
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            AgentSignalEvent(agent_name="test", signal_type="BUY", confidence=1.5)

    def test_to_event(self) -> None:
        ase = AgentSignalEvent(
            agent_name="risk_mgr", signal_type="RISK_ALERT",
        )
        event = ase.to_event()
        assert event.event_type == EventType.AGENT_SIGNALS
        assert event.payload["signal_type"] == "RISK_ALERT"


class TestExecutionCommandEvent:
    def test_creation(self) -> None:
        ece = ExecutionCommandEvent(action="BUY", symbol="AAPL")
        assert ece.event_type == EventType.EXECUTION_COMMANDS
        assert ece.channel == "execution_commands"
        assert ece.order_type == "MARKET"

    def test_to_event(self) -> None:
        ece = ExecutionCommandEvent(
            action="SELL", symbol="MSFT",
            quantity=100.0, order_type="LIMIT", price=380.0,
        )
        event = ece.to_event()
        assert event.event_type == EventType.EXECUTION_COMMANDS
        assert event.payload["action"] == "SELL"


class TestRiskAlertEvent:
    def test_creation(self) -> None:
        rae = RiskAlertEvent(
            alert_type="DAILY_LIMIT", message="Daily loss exceeded",
        )
        assert rae.event_type == EventType.RISK_ALERTS
        assert rae.channel == "risk_alerts"
        assert rae.severity == "WARNING"

    def test_to_event(self) -> None:
        rae = RiskAlertEvent(
            alert_type="KILL_SWITCH",
            severity="CRITICAL",
            message="Kill switch activated",
        )
        event = rae.to_event()
        assert event.event_type == EventType.RISK_ALERTS
        assert event.payload["alert_type"] == "KILL_SWITCH"


class TestEventType:
    def test_all_types(self) -> None:
        expected = {
            "market_data", "agent_signals", "execution_commands",
            "risk_alerts", "system", "regime_change",
            "strategy_lifecycle", "audit",
        }
        assert {e.value for e in EventType} == expected


class TestEventPriority:
    def test_all_priorities(self) -> None:
        expected = {"CRITICAL", "HIGH", "NORMAL", "LOW"}
        assert {e.value for e in EventPriority} == expected


class TestDeadLetterEntry:
    def test_creation(self) -> None:
        event = Event(event_type=EventType.SYSTEM, payload={"test": True})
        entry = DeadLetterEntry(
            event=event, error="handler crashed", channel="test",
        )
        assert entry.retry_count == 0
        assert entry.max_retries == 3


# ══════════════════════════════════════════════════════════════════════
# EVENT BUS ENGINE TESTS (IN-MEMORY MODE)
# ══════════════════════════════════════════════════════════════════════


@pytest.fixture
def bus() -> EventBusEngine:
    """EventBusEngine in in-memory mode (no Redis)."""
    return EventBusEngine(use_redis=False)


class TestEventBusLifecycle:
    """Test bus start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_in_memory(self, bus: EventBusEngine) -> None:
        result = await bus.start()
        assert result["status"] == "STARTED"
        assert result["mode"] == "in_memory"
        assert bus.is_running is True
        assert bus.mode == "in_memory"
        await bus.stop()

    @pytest.mark.asyncio
    async def test_start_when_already_running(self, bus: EventBusEngine) -> None:
        await bus.start()
        result = await bus.start()
        assert result["status"] == "ALREADY_RUNNING"
        await bus.stop()

    @pytest.mark.asyncio
    async def test_stop(self, bus: EventBusEngine) -> None:
        await bus.start()
        result = await bus.stop()
        assert result["status"] == "STOPPED"
        assert bus.is_running is False
        assert "stats" in result

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self, bus: EventBusEngine) -> None:
        result = await bus.stop()
        assert result["status"] == "NOT_RUNNING"


class TestEventBusPublishing:
    """Test event publishing and delivery."""

    @pytest.mark.asyncio
    async def test_publish_to_channel(self, bus: EventBusEngine) -> None:
        await bus.start()
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        await bus.subscribe("test_channel", handler)
        event = Event(payload={"msg": "hello"})
        result = await bus.publish("test_channel", event)

        assert result["status"] == "PUBLISHED"
        assert result["channel"] == "test_channel"
        assert len(received) == 1
        assert received[0].payload["msg"] == "hello"
        await bus.stop()

    @pytest.mark.asyncio
    async def test_publish_without_start_raises(self, bus: EventBusEngine) -> None:
        from quant_nanggroe_ai.exceptions import EngineError
        event = Event()
        with pytest.raises(EngineError, match="not running"):
            await bus.publish("test", event)

    @pytest.mark.asyncio
    async def test_publish_with_no_subscribers(self, bus: EventBusEngine) -> None:
        await bus.start()
        event = Event()
        result = await bus.publish("no_subs", event)
        assert result["status"] == "PUBLISHED"
        assert result["local_subscribers"] == 0
        await bus.stop()

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, bus: EventBusEngine) -> None:
        await bus.start()
        received_a: list[Event] = []
        received_b: list[Event] = []

        async def handler_a(event: Event) -> None:
            received_a.append(event)

        async def handler_b(event: Event) -> None:
            received_b.append(event)

        await bus.subscribe("multi", handler_a)
        await bus.subscribe("multi", handler_b)

        event = Event(payload={"test": True})
        await bus.publish("multi", event)

        assert len(received_a) == 1
        assert len(received_b) == 1
        await bus.stop()

    @pytest.mark.asyncio
    async def test_channel_isolation(self, bus: EventBusEngine) -> None:
        await bus.start()
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        await bus.subscribe("channel_a", handler)

        event = Event(payload={"ch": "b"})
        await bus.publish("channel_b", event)

        assert len(received) == 0
        await bus.stop()

    @pytest.mark.asyncio
    async def test_publish_typed_market_data(self, bus: EventBusEngine) -> None:
        await bus.start()
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        await bus.subscribe("market_data", handler)

        mde = MarketDataEvent(symbol="AAPL", price=180.0)
        result = await bus.publish_typed(mde)

        assert result["status"] == "PUBLISHED"
        assert len(received) == 1
        assert received[0].event_type == EventType.MARKET_DATA
        await bus.stop()

    @pytest.mark.asyncio
    async def test_publish_typed_risk_alert(self, bus: EventBusEngine) -> None:
        await bus.start()
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        await bus.subscribe("risk_alerts", handler)

        rae = RiskAlertEvent(alert_type="DRAWDOWN", message="Max drawdown hit")
        await bus.publish_typed(rae)

        assert len(received) == 1
        assert received[0].event_type == EventType.RISK_ALERTS
        await bus.stop()

    @pytest.mark.asyncio
    async def test_publish_typed_invalid_event(self, bus: EventBusEngine) -> None:
        """publish_typed with non-typed event should raise EngineError."""
        await bus.start()
        from quant_nanggroe_ai.exceptions import EngineError
        with pytest.raises(EngineError, match="to_event"):
            await bus.publish_typed("not_an_event")  # type: ignore
        await bus.stop()


class TestEventBusSubscription:
    """Test subscribe/unsubscribe."""

    @pytest.mark.asyncio
    async def test_subscribe(self, bus: EventBusEngine) -> None:
        await bus.start()

        async def handler(event: Event) -> None:
            pass

        result = await bus.subscribe("test", handler)
        assert result["status"] == "SUBSCRIBED"
        assert result["handler_count"] == 1
        await bus.stop()

    @pytest.mark.asyncio
    async def test_unsubscribe_specific_handler(self, bus: EventBusEngine) -> None:
        await bus.start()

        async def handler(event: Event) -> None:
            pass

        await bus.subscribe("test", handler)
        result = await bus.unsubscribe("test", handler)
        assert result["status"] == "UNSUBSCRIBED"
        assert result["remaining_handlers"] == 0
        await bus.stop()

    @pytest.mark.asyncio
    async def test_unsubscribe_all_handlers(self, bus: EventBusEngine) -> None:
        await bus.start()

        async def handler_a(event: Event) -> None:
            pass

        async def handler_b(event: Event) -> None:
            pass

        await bus.subscribe("test", handler_a)
        await bus.subscribe("test", handler_b)
        result = await bus.unsubscribe("test")
        assert result["status"] == "UNSUBSCRIBED"
        assert result["remaining_handlers"] == 0
        await bus.stop()

    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent_channel(self, bus: EventBusEngine) -> None:
        await bus.start()
        result = await bus.unsubscribe("nonexistent")
        assert result["status"] == "NOT_SUBSCRIBED"
        await bus.stop()

    @pytest.mark.asyncio
    async def test_max_subscribers_per_channel(self, bus: EventBusEngine) -> None:
        await bus.start()

        async def handler(event: Event) -> None:
            pass

        for i in range(bus.MAX_SUBSCRIBERS_PER_CHANNEL):
            await bus.subscribe("max_test", handler)

        from quant_nanggroe_ai.exceptions import EngineError
        with pytest.raises(EngineError, match="Max subscribers"):
            await bus.subscribe("max_test", handler)
        await bus.stop()


class TestEventBusDeadLetterQueue:
    """Test dead letter queue functionality."""

    @pytest.mark.asyncio
    async def test_failed_handler_creates_dlq_entry(self, bus: EventBusEngine) -> None:
        await bus.start()

        async def bad_handler(event: Event) -> None:
            raise RuntimeError("handler failed")

        await bus.subscribe("dlq_test", bad_handler)
        event = Event(payload={"test": True})
        await bus.publish("dlq_test", event)

        dlq = bus.get_dead_letter_queue()
        assert len(dlq) == 1
        assert dlq[0].error == "handler failed"
        assert dlq[0].channel == "dlq_test"
        await bus.stop()

    @pytest.mark.asyncio
    async def test_retry_dead_letter_succeeds(self, bus: EventBusEngine) -> None:
        await bus.start()
        call_count = 0

        # First, create a DLQ entry
        async def fail_handler(event: Event) -> None:
            raise RuntimeError("fail")

        await bus.subscribe("retry_test", fail_handler)
        event = Event(payload={"retry": True})
        await bus.publish("retry_test", event)

        # Remove the failing handler, add a good one
        await bus.unsubscribe("retry_test")

        async def good_handler(event: Event) -> None:
            nonlocal call_count
            call_count += 1

        await bus.subscribe("retry_test", good_handler)

        # Retry
        result = await bus.retry_dead_letter()
        assert result["retried"] == 1
        assert result["still_failed"] == 0
        assert call_count == 1
        await bus.stop()

    @pytest.mark.asyncio
    async def test_retry_dead_letter_still_fails(self, bus: EventBusEngine) -> None:
        """Retrying a DLQ entry with a still-broken handler: retry removes the
        old entry and the re-dispatch failure re-adds it (same event_id gets
        its retry_count incremented in place, then the original reference is
        removed). The net effect is the entry is consumed from the DLQ."""
        await bus.start()

        async def always_fail(event: Event) -> None:
            raise RuntimeError("always fails")

        await bus.subscribe("fail_test", always_fail)
        event = Event(payload={"fail": True})
        await bus.publish("fail_test", event)

        assert len(bus.get_dead_letter_queue()) == 1
        result = await bus.retry_dead_letter()
        # The retry consumes the entry from the DLQ (retried=1)
        assert result["retried"] == 1
        # The underlying handler is still broken so stats should show failures
        stats = bus.get_stats()
        assert stats["failed"] >= 2  # Original + retry
        await bus.stop()

    @pytest.mark.asyncio
    async def test_purge_dead_letter_queue(self, bus: EventBusEngine) -> None:
        await bus.start()

        async def fail_handler(event: Event) -> None:
            raise RuntimeError("fail")

        await bus.subscribe("purge_test", fail_handler)
        await bus.publish("purge_test", Event())
        await bus.publish("purge_test", Event())

        count = bus.purge_dead_letter_queue()
        assert count >= 2
        assert len(bus.get_dead_letter_queue()) == 0
        await bus.stop()

    def test_get_dead_letter_queue_empty(self, bus: EventBusEngine) -> None:
        dlq = bus.get_dead_letter_queue()
        assert dlq == []

    @pytest.mark.asyncio
    async def test_get_dead_letter_queue_with_channel_filter(
        self, bus: EventBusEngine
    ) -> None:
        await bus.start()

        async def fail_handler(event: Event) -> None:
            raise RuntimeError("fail")

        await bus.subscribe("ch_a", fail_handler)
        await bus.publish("ch_a", Event(payload={"a": 1}))

        dlq = bus.get_dead_letter_queue(channel="ch_a")
        assert all(e.channel == "ch_a" for e in dlq)
        await bus.stop()


class TestEventBusStatistics:
    """Test statistics tracking."""

    @pytest.mark.asyncio
    async def test_stats_tracking(self, bus: EventBusEngine) -> None:
        await bus.start()

        async def handler(event: Event) -> None:
            pass

        await bus.subscribe("stats_test", handler)

        event = Event(event_type=EventType.SYSTEM, payload={"n": 1})
        await bus.publish("stats_test", event)

        stats = bus.get_stats()
        assert stats["published"] == 1
        assert stats["delivered"] == 1
        assert stats["failed"] == 0
        assert stats["delivery_rate"] == 1.0
        assert "stats_test" in stats["by_channel"]
        await bus.stop()

    @pytest.mark.asyncio
    async def test_status_report(self, bus: EventBusEngine) -> None:
        await bus.start()

        async def handler(event: Event) -> None:
            pass

        await bus.subscribe("status_test", handler)

        status = bus.status()
        assert status["is_running"] is True
        assert status["mode"] == "in_memory"
        assert "channels" in status
        assert status["channels"]["status_test"] == 1
        await bus.stop()

    @pytest.mark.asyncio
    async def test_delivery_rate_zero_when_nothing_published(
        self, bus: EventBusEngine
    ) -> None:
        await bus.start()
        stats = bus.get_stats()
        assert stats["delivery_rate"] == 0.0
        await bus.stop()
