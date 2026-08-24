"""Candle-close event bus — bridges CandleScheduler (thread) → WebSocket (async).

Thread-safe pub/sub with a bounded queue per subscriber plus a small ring
buffer so REST endpoints can serve recent events without a WS connection.
Publishers never block and never raise into the trading loop.
"""
from __future__ import annotations

import logging
import queue
import threading
from collections import deque
from typing import Any, Deque, Dict, List

logger = logging.getLogger("QNA.CandleEvents")

_RING_SIZE = 200
_ring: Deque[Dict[str, Any]] = deque(maxlen=_RING_SIZE)
_subs_lock = threading.Lock()
_subscribers: List["queue.Queue[Dict[str, Any]]"] = []


def publish_candle_event(event: Dict[str, Any]) -> None:
    """Publish a candle-close event. Never raises, never blocks."""
    try:
        _ring.append(event)
        with _subs_lock:
            subs = list(_subscribers)
        for q in subs:
            try:
                q.put_nowait(event)
            except queue.Full:
                pass  # slow consumer — drop rather than block the scheduler
    except Exception as exc:
        logger.debug("candle event publish failed: %s", exc)


def subscribe() -> "queue.Queue[Dict[str, Any]]":
    """Register a subscriber queue. Caller must eventually unsubscribe()."""
    q: "queue.Queue[Dict[str, Any]]" = queue.Queue(maxsize=500)
    with _subs_lock:
        _subscribers.append(q)
    return q


def unsubscribe(q: "queue.Queue[Dict[str, Any]]") -> None:
    with _subs_lock:
        try:
            _subscribers.remove(q)
        except ValueError:
            pass


def recent_events(limit: int = 50) -> List[Dict[str, Any]]:
    """Most recent events, newest first (for REST fallback)."""
    items = list(_ring)
    return list(reversed(items[-limit:]))
