"""WebSocket endpoint for real-time agent communication.

Message types:
* task_update – task status change notifications
* heartbeat   – periodic agent health updates
* alert       – security or system alerts
* log         – streaming log entries
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set

from ..schemas import WSMessage, WSTaskUpdate, WSHeartbeat, WSAlert, WSLog

logger = logging.getLogger(__name__)


class WebSocketHandler:
    """WebSocket connection manager for real-time communication.

    Manages connections, broadcasts, and message routing.

    Usage::

        handler = WebSocketHandler()
        # On new connection:
        await handler.on_connect(websocket, client_id)
        # On message:
        await handler.on_message(client_id, raw_text)
        # On disconnect:
        await handler.on_disconnect(client_id)
        # Broadcast:
        await handler.broadcast_task_update(task_id, status, agent_id)
    """

    def __init__(self, heartbeat_interval_s: int = 30):
        self.heartbeat_interval_s = heartbeat_interval_s
        self._connections: Dict[str, Any] = {}  # client_id → websocket
        self._subscriptions: Dict[str, Set[str]] = {}  # client_id → set of topics
        self._message_handlers: Dict[str, List[Callable[..., Coroutine[Any, Any, None]]]] = {
            "task_update": [],
            "heartbeat": [],
            "alert": [],
            "log": [],
        }
        self._message_log: List[WSMessage] = []
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None

    # ── Connection lifecycle ───────────────────────────────────────────────

    async def on_connect(self, websocket: Any, client_id: str) -> None:
        """Handle a new WebSocket connection."""
        self._connections[client_id] = websocket
        self._subscriptions[client_id] = {"task_update", "heartbeat", "alert"}
        logger.info("WebSocket client connected: %s", client_id)

        # Send welcome message
        welcome = WSMessage(
            type="heartbeat",
            payload={"status": "connected", "client_id": client_id},
            source="server",
        )
        await self._send(client_id, welcome)

    async def on_disconnect(self, client_id: str) -> None:
        """Handle a WebSocket disconnection."""
        self._connections.pop(client_id, None)
        self._subscriptions.pop(client_id, None)
        logger.info("WebSocket client disconnected: %s", client_id)

    async def on_message(self, client_id: str, raw: str) -> None:
        """Process an incoming message from a client.

        Parameters
        ----------
        client_id : str
            The sending client's ID.
        raw : str
            Raw message text (expected JSON).
        """
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            await self._send_error(client_id, "Invalid JSON")
            return

        msg_type = data.get("type", "")
        payload = data.get("payload", {})

        ws_msg = WSMessage(
            type=msg_type,
            payload=payload,
            source=client_id,
        )
        self._message_log.append(ws_msg)

        # Dispatch to type-specific handlers
        handlers = self._message_handlers.get(msg_type, [])
        for handler in handlers:
            try:
                await handler(ws_msg)
            except Exception as exc:
                logger.error("WS handler error for type %s: %s", msg_type, exc)

    # ── Sending ────────────────────────────────────────────────────────────

    async def _send(self, client_id: str, message: WSMessage) -> bool:
        """Send a message to a specific client.

        Returns True if sent successfully.
        """
        ws = self._connections.get(client_id)
        if ws is None:
            return False

        try:
            text = message.model_dump_json()
            if hasattr(ws, "send_text"):
                await ws.send_text(text)
            elif hasattr(ws, "send"):
                await ws.send(text)
            return True
        except Exception as exc:
            logger.warning("Failed to send WS message to %s: %s", client_id, exc)
            # Remove broken connection
            self._connections.pop(client_id, None)
            return False

    async def _send_error(self, client_id: str, error: str) -> None:
        """Send an error message to a client."""
        msg = WSMessage(
            type="error",
            payload={"error": error},
            source="server",
        )
        await self._send(client_id, msg)

    # ── Broadcasting ───────────────────────────────────────────────────────

    async def broadcast(self, message: WSMessage, topic: Optional[str] = None) -> int:
        """Broadcast a message to all subscribed clients.

        Parameters
        ----------
        message : WSMessage
            The message to broadcast.
        topic : str, optional
            If specified, only clients subscribed to this topic receive it.

        Returns
        -------
        int – number of clients that received the message.
        """
        sent = 0
        for client_id, topics in list(self._subscriptions.items()):
            if topic and topic not in topics:
                continue
            if await self._send(client_id, message):
                sent += 1
        return sent

    async def broadcast_task_update(
        self,
        task_id: str,
        status: str,
        agent_id: Optional[str] = None,
        progress: float = 0.0,
        message: str = "",
    ) -> int:
        """Convenience: broadcast a task update."""
        update = WSTaskUpdate(
            task_id=task_id,
            status=status,
            agent_id=agent_id,
            progress=progress,
            message=message,
        )
        ws_msg = WSMessage(
            type="task_update",
            payload=update.model_dump(mode="json"),
            source="server",
        )
        return await self.broadcast(ws_msg, topic="task_update")

    async def broadcast_heartbeat(
        self,
        agent_id: str,
        health_score: float = 1.0,
        active_tasks: int = 0,
    ) -> int:
        """Convenience: broadcast an agent heartbeat."""
        hb = WSHeartbeat(
            agent_id=agent_id,
            health_score=health_score,
            active_tasks=active_tasks,
        )
        ws_msg = WSMessage(
            type="heartbeat",
            payload=hb.model_dump(mode="json"),
            source=agent_id,
        )
        return await self.broadcast(ws_msg, topic="heartbeat")

    async def broadcast_alert(
        self,
        level: str,
        source: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Convenience: broadcast an alert."""
        alert = WSAlert(
            level=level,
            source=source,
            message=message,
            details=details or {},
        )
        ws_msg = WSMessage(
            type="alert",
            payload=alert.model_dump(mode="json"),
            source=source,
        )
        return await self.broadcast(ws_msg, topic="alert")

    async def broadcast_log(
        self,
        level: str,
        message: str,
        agent_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Convenience: broadcast a log entry."""
        log_entry = WSLog(
            level=level,
            agent_id=agent_id,
            message=message,
            data=data or {},
        )
        ws_msg = WSMessage(
            type="log",
            payload=log_entry.model_dump(mode="json"),
            source=agent_id or "server",
        )
        return await self.broadcast(ws_msg, topic="log")

    # ── Subscriptions ──────────────────────────────────────────────────────

    def subscribe(self, client_id: str, topic: str) -> None:
        """Subscribe a client to a topic."""
        if client_id in self._subscriptions:
            self._subscriptions[client_id].add(topic)

    def unsubscribe(self, client_id: str, topic: str) -> None:
        """Unsubscribe a client from a topic."""
        if client_id in self._subscriptions:
            self._subscriptions[client_id].discard(topic)

    # ── Handler registration ───────────────────────────────────────────────

    def register_handler(
        self,
        message_type: str,
        handler: Callable[..., Coroutine[Any, Any, None]],
    ) -> None:
        """Register a handler for a specific message type."""
        if message_type not in self._message_handlers:
            self._message_handlers[message_type] = []
        self._message_handlers[message_type].append(handler)

    # ── Heartbeat loop ─────────────────────────────────────────────────────

    async def start_heartbeat_loop(self) -> None:
        """Start the periodic heartbeat broadcast."""
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def stop_heartbeat_loop(self) -> None:
        """Stop the heartbeat broadcast."""
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None

    async def _heartbeat_loop(self) -> None:
        """Periodically send server heartbeats to all clients."""
        while self._running:
            try:
                ws_msg = WSMessage(
                    type="heartbeat",
                    payload={"server_time": datetime.now(timezone.utc).isoformat()},
                    source="server",
                )
                await self.broadcast(ws_msg, topic="heartbeat")
                await asyncio.sleep(self.heartbeat_interval_s)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("WS heartbeat loop error: %s", exc)
                await asyncio.sleep(self.heartbeat_interval_s)

    # ── Properties ─────────────────────────────────────────────────────────

    @property
    def connection_count(self) -> int:
        return len(self._connections)

    @property
    def total_messages(self) -> int:
        return len(self._message_log)

    def get_stats(self) -> Dict[str, Any]:
        """Return WebSocket handler statistics."""
        return {
            "connections": self.connection_count,
            "total_messages": self.total_messages,
            "topics": list(
                set(t for topics in self._subscriptions.values() for t in topics)
            ),
        }
