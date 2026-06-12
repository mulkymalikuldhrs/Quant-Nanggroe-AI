"""WebSocket API routes with rate limiting.

Rate Limiting
-------------
- **Connection limit**: max 10 concurrent connections per client IP.
- **Message limit**: max 60 messages per minute per connection.

Both limits are enforced with pure asyncio-based bookkeeping — no
external dependencies required.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Rate-limiting helpers
# ---------------------------------------------------------------------------

# ── Connection limiter (max concurrent connections per IP) ─────────────────

_MAX_CONNECTIONS_PER_IP: int = 10

# ip → set of active WebSocket objects
_active_connections_by_ip: dict[str, set[WebSocket]] = defaultdict(set)


def _client_ip(websocket: WebSocket) -> str:
    """Extract the client IP from a WebSocket connection."""
    # When behind a reverse proxy the real IP is in X-Forwarded-For.
    forwarded = websocket.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = websocket.client
    return client.host if client else "unknown"


def _can_connect(ip: str) -> bool:
    """Return True if the IP is below the concurrent-connection limit."""
    return len(_active_connections_by_ip[ip]) < _MAX_CONNECTIONS_PER_IP


def _register_connection(ip: str, ws: WebSocket) -> None:
    """Track a new connection for the given IP."""
    _active_connections_by_ip[ip].add(ws)


def _unregister_connection(ip: str, ws: WebSocket) -> None:
    """Remove a connection for the given IP."""
    conns = _active_connections_by_ip.get(ip)
    if conns:
        conns.discard(ws)
        if not conns:
            del _active_connections_by_ip[ip]


# ── Message rate limiter (sliding-window, per connection) ──────────────────

_MAX_MESSAGES_PER_MINUTE: int = 60
_WINDOW_SECONDS: int = 60


class MessageRateLimiter:
    """Sliding-window rate limiter for WebSocket messages.

    Tracks timestamps of recent messages per connection and rejects
    messages that exceed the configured rate.

    Parameters
    ----------
    max_messages:
        Maximum messages allowed in the sliding window.
    window_seconds:
        Duration of the sliding window in seconds.
    """

    def __init__(
        self,
        max_messages: int = _MAX_MESSAGES_PER_MINUTE,
        window_seconds: int = _WINDOW_SECONDS,
    ) -> None:
        self._max_messages = max_messages
        self._window_seconds = window_seconds
        # connection-id → list of timestamps
        self._timestamps: dict[int, list[float]] = defaultdict(list)

    def is_allowed(self, ws_id: int) -> bool:
        """Check if a message from the given connection is allowed.

        Evicts expired entries before checking.
        """
        now = time.monotonic()
        cutoff = now - self._window_seconds
        ts_list = self._timestamps[ws_id]

        # Prune old timestamps
        while ts_list and ts_list[0] < cutoff:
            ts_list.pop(0)

        if len(ts_list) >= self._max_messages:
            return False

        ts_list.append(now)
        return True

    def cleanup(self, ws_id: int) -> None:
        """Remove tracking data for a disconnected connection."""
        self._timestamps.pop(ws_id, None)


# Module-level rate limiter instance
_message_limiter = MessageRateLimiter()


# ---------------------------------------------------------------------------
# Connection Manager
# ---------------------------------------------------------------------------


class ConnectionManager:
    """Manages WebSocket connections for real-time data streaming."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------


@router.websocket("/stream")
async def websocket_stream(websocket: WebSocket) -> None:
    """Main WebSocket endpoint for real-time market data streaming.

    Clients can subscribe to channels (price, regime, risk) and
    receive real-time updates.

    Protocol:
    - Client sends JSON: {"action": "subscribe", "channels": ["price", "regime"]}
    - Server sends JSON: {"type": "market_data", "symbol": "AAPL", "price": 150.0}

    Rate Limits:
    - Max 10 concurrent connections per client IP.
    - Max 60 messages per minute per connection.
    """
    ip = _client_ip(websocket)

    # ── Connection limit check ─────────────────────────────────────────
    if not _can_connect(ip):
        await websocket.accept()
        await websocket.send_json({
            "type": "error",
            "code": "CONNECTION_LIMIT",
            "message": f"Max {_MAX_CONNECTIONS_PER_IP} concurrent connections per IP exceeded.",
        })
        await websocket.close(code=1008, reason="Connection limit exceeded")
        logger.warning("ws_connection_rejected ip=%s", ip)
        return

    await manager.connect(websocket)
    _register_connection(ip, websocket)
    ws_id = id(websocket)

    try:
        while True:
            data = await websocket.receive_json()

            # ── Message rate limit check ───────────────────────────────
            if not _message_limiter.is_allowed(ws_id):
                await websocket.send_json({
                    "type": "error",
                    "code": "RATE_LIMIT",
                    "message": f"Max {_MAX_MESSAGES_PER_MINUTE} messages per minute exceeded.",
                })
                continue  # don't process the message, but keep connection

            action = data.get("action", "")

            if action == "ping":
                await websocket.send_json({"type": "pong"})
            elif action == "subscribe":
                channels = data.get("channels", [])
                symbols = data.get("symbols", [])
                await websocket.send_json({
                    "type": "subscription",
                    "status": "confirmed",
                    "channels": channels,
                    "symbols": symbols,
                })
            elif action == "unsubscribe":
                await websocket.send_json({
                    "type": "subscription",
                    "status": "unsubscribed",
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("websocket_client_disconnected ip=%s", ip)
    except Exception as exc:
        manager.disconnect(websocket)
        logger.error("websocket_error", extra={"error": str(exc), "ip": ip})
    finally:
        _unregister_connection(ip, websocket)
        _message_limiter.cleanup(ws_id)
