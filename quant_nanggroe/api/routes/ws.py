"""WebSocket API routes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()


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


@router.websocket("/stream")
async def websocket_stream(websocket: WebSocket) -> None:
    """Main WebSocket endpoint for real-time market data streaming.

    Clients can subscribe to channels (price, regime, risk) and
    receive real-time updates.

    Protocol:
    - Client sends JSON: {"action": "subscribe", "channels": ["price", "regime"]}
    - Server sends JSON: {"type": "market_data", "symbol": "AAPL", "price": 150.0}
    """
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
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
        logger.info("websocket_client_disconnected")
    except Exception as exc:
        manager.disconnect(websocket)
        logger.error("websocket_error", extra={"error": str(exc)})
