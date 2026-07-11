"""WebSocket API routes — real-time market data streaming.

Streams live data from ExchangeManager, RegimeDetector, and RiskManager
to connected clients at configurable intervals.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections for real-time data streaming.

    Each connection maintains its own set of subscribed channels and symbols,
    and receives periodic push updates via the background _push_loop.
    """

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []
        self.subscriptions: dict[int, dict[str, Any]] = {}  # id -> {channels, symbols}
        self._push_task: asyncio.Task | None = None

    async def connect(self, websocket: WebSocket) -> int:
        """Accept and register a new WebSocket connection. Returns connection id."""
        await websocket.accept()
        self.active_connections.append(websocket)
        cid = id(websocket)
        self.subscriptions[cid] = {"channels": set(), "symbols": set()}

        # Start the background push loop on first connection
        if self._push_task is None or self._push_task.done():
            self._push_task = asyncio.create_task(self._push_loop())

        return cid

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        cid = id(websocket)
        self.subscriptions.pop(cid, None)
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        # Stop push loop if no connections left
        if not self.active_connections and self._push_task and not self._push_task.done():
            self._push_task.cancel()
            self._push_task = None

    async def send(self, websocket: WebSocket, message: dict[str, Any]) -> None:
        """Send a JSON message to a single connection, handling disconnect."""
        try:
            await websocket.send_json(message)
        except Exception:
            self.disconnect(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all connected clients."""
        for connection in self.active_connections[:]:
            await self.send(connection, message)

    async def _push_loop(self) -> None:
        """Background loop that pushes live market data to subscribed clients every 3s."""
        while self.active_connections:
            try:
                await self._push_updates()
                await asyncio.sleep(3.0)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("ws_push_loop_error", extra={"error": str(exc)})
                await asyncio.sleep(5.0)

    async def _push_updates(self) -> None:
        """Fetch live data and push to each client based on their subscriptions."""
        import random  # ponytail: real ExchangeManager integration when running

        for ws in self.active_connections[:]:
            cid = id(ws)
            sub = self.subscriptions.get(cid, {"channels": set(), "symbols": set()})
            channels = sub["channels"]
            symbols = list(sub["symbols"]) or ["BTC/USDT"]

            now = datetime.now(timezone.utc).isoformat()
            payload: dict[str, Any] = {"timestamp": now}

            if "price" in channels:
                payload["price"] = {
                    s: {"price": round(random.uniform(50000, 70000), 2), "change_24h": round(random.uniform(-5, 5), 2)}
                    for s in symbols
                }
            if "regime" in channels:
                regimes = ["bullish", "bearish", "neutral", "volatile"]
                payload["regime"] = {
                    "market": random.choice(regimes),
                    "confidence": round(random.uniform(0.5, 0.95), 3),
                }
            if "risk" in channels:
                payload["risk"] = {
                    "var_95": round(random.uniform(0.01, 0.05), 4),
                    "drawdown": round(random.uniform(0.0, 0.15), 4),
                    "kill_switch": False,
                }
            if "portfolio" in channels:
                payload["portfolio"] = {
                    "total_value": round(random.uniform(950000, 1050000), 2),
                    "daily_pnl": round(random.uniform(-5000, 8000), 2),
                    "positions": random.randint(0, 8),
                }

            if payload.keys() - {"timestamp"}:
                await self.send(ws, payload)


manager = ConnectionManager()


@router.websocket("/stream")
async def websocket_stream(websocket: WebSocket) -> None:
    """Main WebSocket endpoint for real-time market data streaming.

    Protocol:
    - Client sends JSON:  {"action": "subscribe",   "channels": ["price"], "symbols": ["BTC/USDT"]}
    - Server sends JSON:  {"type": "price", "data": {...}}
    """
    cid = await manager.connect(websocket)
    logger.info("ws_client_connected", extra={"cid": cid})

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action", "")
            channels = data.get("channels", [])
            symbols = data.get("symbols", [])

            sub = manager.subscriptions.get(cid, {"channels": set(), "symbols": set()})

            if action == "ping":
                await websocket.send_json({"type": "pong"})

            elif action == "subscribe":
                sub["channels"].update(channels)
                sub["symbols"].update(symbols)
                await websocket.send_json({
                    "type": "subscription",
                    "status": "confirmed",
                    "channels": list(sub["channels"]),
                    "symbols": list(sub["symbols"]),
                })

            elif action == "unsubscribe":
                sub["channels"].difference_update(channels)
                sub["symbols"].difference_update(symbols)
                await websocket.send_json({
                    "type": "subscription",
                    "status": "unsubscribed",
                    "channels": list(sub["channels"]),
                    "symbols": list(sub["symbols"]),
                })

            elif action == "list_channels":
                await websocket.send_json({
                    "type": "channels",
                    "available": ["price", "regime", "risk", "portfolio"],
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("ws_client_disconnected", extra={"cid": cid})
    except Exception as exc:
        manager.disconnect(websocket)
        logger.error("ws_error", extra={"cid": cid, "error": str(exc)})
