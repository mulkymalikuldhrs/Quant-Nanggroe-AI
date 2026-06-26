"""LEAN-inspired event-driven trading engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List
from enum import Enum
import heapq
from datetime import datetime


class EventType(Enum):
    TICK = "tick"
    BAR = "bar"
    ORDER_FILL = "order_fill"
    ORDER_REJECT = "order_reject"
    SIGNAL = "signal"
    RISK_ALERT = "risk_alert"
    REGIME_CHANGE = "regime_change"


@dataclass(order=True)
class Event:
    timestamp: datetime
    event_type: EventType
    data: Dict[str, Any] = field(default_factory=dict, compare=False)
    priority: int = 0  # lower = higher priority


class EventEngine:
    def __init__(self):
        self._queue: List[Event] = []
        self._handlers: Dict[EventType, List[Callable]] = {}
        self._running = False

    def register_handler(self, event_type: EventType, handler: Callable):
        self._handlers.setdefault(event_type, []).append(handler)

    def push(self, event: Event):
        heapq.heappush(self._queue, event)

    def process(self) -> int:
        count = 0
        while self._queue:
            event = heapq.heappop(self._queue)
            for handler in self._handlers.get(event.event_type, []):
                handler(event)
            count += 1
        return count

    @property
    def queue_size(self) -> int:
        return len(self._queue)
