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
_dropped_events: int = 0
_drop_log_interval: int = 50  # log every N drops to avoid spam


def publish_candle_event(event: Dict[str, Any]) -> None:
    """Publish a candle-close event. Never raises, never blocks."""
    global _dropped_events
    try:
        _ring.append(event)
        with _subs_lock:
            subs = list(_subscribers)
        for q in subs:
            try:
                q.put_nowait(event)
            except queue.Full:
                _dropped_events += 1
                if _dropped_events % _drop_log_interval == 1:
                    logger.warning(
                        "Candle event queue full — %d events dropped (slow consumer)",
                        _dropped_events,
                    )
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


def get_dropped_count() -> int:
    """Total events dropped due to full subscriber queues."""
    return _dropped_events
