"""
WebSocket Routes — Real-time market data streaming
===================================================
Implements subscription-based real-time streaming for:
- Live price updates
- Regime change notifications
- Risk status alerts

Uses a publish/subscribe pattern where clients subscribe to
symbols and channels, and the server pushes updates.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = structlog.get_logger(__name__)

router = APIRouter()

# Active WebSocket connections and their subscriptions
_connections: dict[WebSocket, dict[str, Any]] = {}


class MarketDataStreamer:
    """
    Manages real-time market data streaming to WebSocket clients.

    Supports:
    - Per-client symbol subscriptions
    - Multiple channels: price, regime, risk
    - Heartbeat / ping-pong for connection health
    - Graceful cleanup on disconnect
    """

    def __init__(self) -> None:
        self.connections: dict[WebSocket, dict[str, Any]] = {}
        self._broadcast_task: asyncio.Task | None = None

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.connections[websocket] = {
            "connected_at": datetime.now().isoformat(),
            "symbols": set(),
            "channels": {"price"},  # Default channel
            "last_ping": time.monotonic(),
        }
        logger.info("ws_client_connected", total_clients=len(self.connections))

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        self.connections.pop(websocket, None)
        logger.info("ws_client_disconnected", total_clients=len(self.connections))

    def subscribe(self, websocket: WebSocket, symbols: list[str], channels: list[str]) -> None:
        """Subscribe a client to symbols and channels."""
        if websocket in self.connections:
            self.connections[websocket]["symbols"].update(s.upper() for s in symbols)
            self.connections[websocket]["channels"].update(channels)

    def unsubscribe(self, websocket: WebSocket, symbols: list[str], channels: list[str]) -> None:
        """Unsubscribe a client from symbols and channels."""
        if websocket in self.connections:
            self.connections[websocket]["symbols"] -= set(s.upper() for s in symbols)
            if channels:
                self.connections[websocket]["channels"] -= set(channels)

    async def broadcast_price(self, symbol: str, price: float, volume: float = 0.0) -> int:
        """
        Broadcast a price update to all subscribed clients.

        Returns:
            Number of clients that received the update.
        """
        message = json.dumps({
            "type": "market_data",
            "symbol": symbol,
            "price": price,
            "volume": volume,
            "timestamp": datetime.now().isoformat(),
        })

        sent = 0
        dead = []
        for ws, info in self.connections.items():
            if symbol in info["symbols"] and "price" in info["channels"]:
                try:
                    await ws.send_text(message)
                    sent += 1
                except Exception:
                    dead.append(ws)

        for ws in dead:
            self.disconnect(ws)

        return sent

    async def broadcast_regime_change(
        self, symbol: str, regime: str, trade_allowed: bool
    ) -> int:
        """
        Broadcast a regime change to all subscribed clients.

        Returns:
            Number of clients that received the update.
        """
        message = json.dumps({
            "type": "regime_change",
            "symbol": symbol,
            "regime": regime,
            "trade_allowed": trade_allowed,
            "timestamp": datetime.now().isoformat(),
        })

        sent = 0
        dead = []
        for ws, info in self.connections.items():
            if symbol in info["symbols"] and "regime" in info["channels"]:
                try:
                    await ws.send_text(message)
                    sent += 1
                except Exception:
                    dead.append(ws)

        for ws in dead:
            self.disconnect(ws)

        return sent

    async def broadcast_risk_alert(self, alert: dict[str, Any]) -> int:
        """
        Broadcast a risk alert to all clients subscribed to the risk channel.

        Returns:
            Number of clients that received the alert.
        """
        message = json.dumps({
            "type": "risk_alert",
            **alert,
            "timestamp": datetime.now().isoformat(),
        })

        sent = 0
        dead = []
        for ws, info in self.connections.items():
            if "risk" in info["channels"]:
                try:
                    await ws.send_text(message)
                    sent += 1
                except Exception:
                    dead.append(ws)

        for ws in dead:
            self.disconnect(ws)

        return sent

    async def start_price_simulator(self) -> None:
        """
        Start a simulated price feed for demo/testing.

        Generates random price ticks for subscribed symbols
        and broadcasts them to connected clients.
        """
        import random

        while self.connections:
            # Collect all subscribed symbols
            all_symbols: set[str] = set()
            for info in self.connections.values():
                all_symbols.update(info["symbols"])

            for symbol in all_symbols:
                # Simulate price tick
                base_prices = {
                    "EURUSD": 1.0850,
                    "GBPUSD": 1.2650,
                    "XAUUSD": 2035.0,
                    "BTCUSDT": 67500.0,
                    "SPY": 510.0,
                }
                base = base_prices.get(symbol, 100.0)
                change = random.gauss(0, base * 0.0002)
                new_price = round(base + change, 5)
                volume = round(random.uniform(100, 10000), 2)

                await self.broadcast_price(symbol, new_price, volume)

            await asyncio.sleep(1.0)  # 1 tick per second


# Singleton streamer
_streamer = MarketDataStreamer()


@router.websocket("/stream")
async def websocket_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time data streaming.

    Protocol:
    - Client connects and receives a welcome message
    - Client sends JSON commands:
        {"action": "subscribe", "symbols": ["EURUSD", "XAUUSD"], "channels": ["price", "regime"]}
        {"action": "unsubscribe", "symbols": ["EURUSD"]}
        {"action": "ping"}
    - Server pushes updates as JSON messages:
        {"type": "market_data", "symbol": "EURUSD", "price": 1.0851, ...}
        {"type": "regime_change", "symbol": "XAUUSD", "regime": "TRENDING_UP", ...}
        {"type": "risk_alert", ...}
        {"type": "pong"}
    """
    await _streamer.connect(websocket)

    # Send welcome message
    await websocket.send_json({
        "type": "welcome",
        "message": "Connected to Quant-Nanggroe-AI real-time feed",
        "available_channels": ["price", "regime", "risk"],
        "timestamp": datetime.now().isoformat(),
    })

    # Start price simulator if not already running
    if _streamer._broadcast_task is None or _streamer._broadcast_task.done():
        _streamer._broadcast_task = asyncio.create_task(
            _streamer.start_price_simulator()
        )

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                command = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON command",
                })
                continue

            action = command.get("action", "").lower()
            symbols = command.get("symbols", [])
            channels = command.get("channels", [])

            if action == "subscribe":
                _streamer.subscribe(websocket, symbols, channels)
                await websocket.send_json({
                    "type": "subscription",
                    "status": "confirmed",
                    "symbols": list(_streamer.connections.get(websocket, {}).get("symbols", set())),
                    "channels": list(_streamer.connections.get(websocket, {}).get("channels", set())),
                    "message": f"Subscribed to {len(symbols)} symbol(s)",
                })
                logger.info("ws_subscribe", symbols=symbols, channels=channels)

            elif action == "unsubscribe":
                _streamer.unsubscribe(websocket, symbols, channels)
                await websocket.send_json({
                    "type": "subscription",
                    "status": "confirmed",
                    "symbols": list(_streamer.connections.get(websocket, {}).get("symbols", set())),
                    "channels": list(_streamer.connections.get(websocket, {}).get("channels", set())),
                    "message": f"Unsubscribed from {len(symbols)} symbol(s)",
                })
                logger.info("ws_unsubscribe", symbols=symbols, channels=channels)

            elif action == "ping":
                _streamer.connections[websocket]["last_ping"] = time.monotonic()
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat(),
                })

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown action: '{action}'. Use subscribe, unsubscribe, or ping.",
                })

    except WebSocketDisconnect:
        _streamer.disconnect(websocket)
        logger.info("ws_client_disconnected_cleanly")
    except Exception as exc:
        _streamer.disconnect(websocket)
        logger.error("ws_error", error=str(exc))


# ══════════════════════════════════════════════════════════════════════
# REST endpoints for WebSocket management
# ══════════════════════════════════════════════════════════════════════

@router.get("/connections")
async def get_active_connections():
    """
    Get count and details of active WebSocket connections.

    Returns:
        Connection count and subscription summary.
    """
    return {
        "total_connections": len(_streamer.connections),
        "connections": [
            {
                "connected_at": info["connected_at"],
                "symbols": list(info["symbols"]),
                "channels": list(info["channels"]),
            }
            for info in _streamer.connections.values()
        ],
    }


@router.post("/broadcast")
async def manual_broadcast(
    message_type: str = "risk_alert",
    symbol: str = "",
    data: dict[str, Any] | None = None,
):
    """
    Manual broadcast endpoint for testing.

    Allows sending a test message to all connected WebSocket clients.
    """
    if message_type == "price" and symbol:
        sent = await _streamer.broadcast_price(
            symbol=symbol,
            price=data.get("price", 0.0) if data else 0.0,
            volume=data.get("volume", 0.0) if data else 0.0,
        )
        return {"type": "price", "symbol": symbol, "sent_to": sent}

    elif message_type == "regime" and symbol:
        sent = await _streamer.broadcast_regime_change(
            symbol=symbol,
            regime=data.get("regime", "UNKNOWN") if data else "UNKNOWN",
            trade_allowed=data.get("trade_allowed", False) if data else False,
        )
        return {"type": "regime", "symbol": symbol, "sent_to": sent}

    elif message_type == "risk_alert":
        sent = await _streamer.broadcast_risk_alert(data or {})
        return {"type": "risk_alert", "sent_to": sent}

    return {"error": "Invalid message_type or missing parameters"}
