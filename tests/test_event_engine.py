"""Tests: EventEngine — LEAN-inspired event-driven pipeline."""
from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from quant_nanggroe.engine.event_engine import Event, EventEngine, EventType


class TestEventType(unittest.TestCase):
    def test_values(self):
        self.assertEqual(EventType.TICK.value, "tick")
        self.assertEqual(EventType.BAR.value, "bar")
        self.assertEqual(EventType.ORDER_FILL.value, "order_fill")
        self.assertEqual(EventType.ORDER_REJECT.value, "order_reject")
        self.assertEqual(EventType.SIGNAL.value, "signal")
        self.assertEqual(EventType.RISK_ALERT.value, "risk_alert")
        self.assertEqual(EventType.REGIME_CHANGE.value, "regime_change")


class TestEvent(unittest.TestCase):
    def test_default_data_is_empty_dict(self):
        now = datetime.utcnow()
        e = Event(timestamp=now, event_type=EventType.TICK)
        self.assertEqual(e.data, {})

    def test_default_priority_is_zero(self):
        now = datetime.utcnow()
        e = Event(timestamp=now, event_type=EventType.TICK)
        self.assertEqual(e.priority, 0)

    def test_custom_data(self):
        now = datetime.utcnow()
        e = Event(timestamp=now, event_type=EventType.SIGNAL, data={"symbol": "BTC", "score": 0.8})
        self.assertEqual(e.data["symbol"], "BTC")
        self.assertEqual(e.data["score"], 0.8)

    def test_custom_priority(self):
        now = datetime.utcnow()
        e = Event(timestamp=now, event_type=EventType.RISK_ALERT, priority=1)
        self.assertEqual(e.priority, 1)


class TestEventEngine(unittest.TestCase):
    def setUp(self):
        self.engine = EventEngine()
        self.events_seen: list[Event] = []

    def handler(self, event: Event):
        self.events_seen.append(event)

    def test_init_queue_empty(self):
        self.assertEqual(self.engine.queue_size, 0)

    def test_init_not_running(self):
        self.assertFalse(self.engine._running)

    def test_register_handler(self):
        self.engine.register_handler(EventType.TICK, self.handler)
        self.assertIn(EventType.TICK, self.engine._handlers)
        self.assertEqual(len(self.engine._handlers[EventType.TICK]), 1)

    def test_register_multiple_handlers_same_type(self):
        def h1(e): pass
        def h2(e): pass
        self.engine.register_handler(EventType.BAR, h1)
        self.engine.register_handler(EventType.BAR, h2)
        self.assertEqual(len(self.engine._handlers[EventType.BAR]), 2)

    def test_push_increases_queue_size(self):
        now = datetime.utcnow()
        self.engine.push(Event(timestamp=now, event_type=EventType.TICK))
        self.assertEqual(self.engine.queue_size, 1)

    def test_push_multiple(self):
        now = datetime.utcnow()
        for i in range(5):
            self.engine.push(Event(timestamp=now + timedelta(seconds=i), event_type=EventType.TICK))
        self.assertEqual(self.engine.queue_size, 5)

    def test_process_executes_handler(self):
        self.engine.register_handler(EventType.SIGNAL, self.handler)
        now = datetime.utcnow()
        self.engine.push(Event(timestamp=now, event_type=EventType.SIGNAL, data={"sym": "ETH"}))
        count = self.engine.process()
        self.assertEqual(count, 1)
        self.assertEqual(len(self.events_seen), 1)
        self.assertEqual(self.events_seen[0].data["sym"], "ETH")

    def test_process_empty_queue(self):
        count = self.engine.process()
        self.assertEqual(count, 0)

    def test_process_clears_queue(self):
        now = datetime.utcnow()
        self.engine.push(Event(timestamp=now, event_type=EventType.TICK))
        self.engine.register_handler(EventType.TICK, self.handler)
        self.engine.process()
        self.assertEqual(self.engine.queue_size, 0)

    def test_process_all_events(self):
        self.engine.register_handler(EventType.TICK, self.handler)
        now = datetime.utcnow()
        for i in range(3):
            self.engine.push(Event(timestamp=now + timedelta(seconds=i), event_type=EventType.TICK))
        count = self.engine.process()
        self.assertEqual(count, 3)
        self.assertEqual(len(self.events_seen), 3)

    def test_event_priority_ordering(self):
        results: list[str] = []
        def recorder(e: Event):
            results.append(e.data.get("label", ""))

        self.engine.register_handler(EventType.TICK, recorder)
        now = datetime.utcnow()
        self.engine.push(Event(timestamp=now, event_type=EventType.TICK, data={"label": "low"}, priority=5))
        self.engine.push(Event(timestamp=now, event_type=EventType.TICK, data={"label": "high"}, priority=0))
        self.engine.push(Event(timestamp=now, event_type=EventType.TICK, data={"label": "mid"}, priority=2))
        self.engine.process()
        self.assertEqual(results, ["high", "mid", "low"])

    def test_handler_only_called_for_registered_type(self):
        self.engine.register_handler(EventType.RISK_ALERT, self.handler)
        now = datetime.utcnow()
        self.engine.push(Event(timestamp=now, event_type=EventType.TICK))
        self.engine.push(Event(timestamp=now, event_type=EventType.RISK_ALERT))
        self.engine.process()
        self.assertEqual(len(self.events_seen), 1)
        self.assertEqual(self.events_seen[0].event_type, EventType.RISK_ALERT)

    def test_multiple_handlers_same_event(self):
        results: list[int] = []
        def h1(e): results.append(1)
        def h2(e): results.append(2)

        self.engine.register_handler(EventType.BAR, h1)
        self.engine.register_handler(EventType.BAR, h2)
        now = datetime.utcnow()
        self.engine.push(Event(timestamp=now, event_type=EventType.BAR))
        self.engine.process()
        self.assertEqual(results, [1, 2])


if __name__ == "__main__":
    unittest.main(verbosity=2)
