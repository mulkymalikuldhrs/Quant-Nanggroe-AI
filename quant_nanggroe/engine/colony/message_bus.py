"""Async message bus for worker communication.

Thin pub/sub over asyncio.Queue — workers publish results / signals
and subscribe by topic. One shared bus per colony.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Set


@dataclass
class Message:
    topic: str
    payload: Any
    sender: str = ""


class MessageBus:
    """Simple topic-based pub/sub bus backed by an asyncio.Queue."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[Message] = asyncio.Queue()
        self._subscribers: Dict[str, Set[asyncio.Queue[Message]]] = {}

    def subscribe(self, topic: str) -> asyncio.Queue[Message]:
        """Return a per-subscriber queue for the given topic."""
        q: asyncio.Queue[Message] = asyncio.Queue()
        self._subscribers.setdefault(topic, set()).add(q)
        return q

    def unsubscribe(self, topic: str, q: asyncio.Queue[Message]) -> None:
        self._subscribers.get(topic, set()).discard(q)

    async def publish(self, msg: Message) -> None:
        """Publish a message — delivers to subscribers + the shared backlog."""
        await self._queue.put(msg)  # shared backlog for late consumers
        for q in self._subscribers.get(msg.topic, set()):
            await q.put(msg)

    async def consume(self) -> Message:
        """Read next message from the shared backlog."""
        return await self._queue.get()
