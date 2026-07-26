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
        self._app: Any = None  # FastAPI app ref, set on first connect

    async def connect(self, websocket: WebSocket) -> int:
        """Accept and register a new WebSocket connection. Returns connection id."""
        await websocket.accept()
        self.active_connections.append(websocket)
        cid = id(websocket)
        self.subscriptions[cid] = {"channels": set(), "symbols": set()}

        # Store app ref for live data access
        if self._app is None:
            self._app = getattr(websocket, "app", None)

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

    # ------------------------------------------------------------------ #
    # Data source access
    # ------------------------------------------------------------------ #

    @property
    def _services(self) -> dict[str, Any]:
        """Return app.state._services dict, or empty if no app reference."""
        if self._app is None:
            return {}
        return getattr(getattr(self._app, "state", None), "_services", {})

    # ------------------------------------------------------------------ #
    # Price channel
    # ------------------------------------------------------------------ #

    async def _get_prices(self, symbols: list[str]) -> dict[str, dict[str, float]]:
        """Fetch real prices from ExchangeManager. Raises RuntimeError if unavailable."""
        exchange_mgr = self._services.get("exchange_manager")
        result: dict[str, dict[str, float]] = {}

        for s in symbols:
            price = 0.0
            change_24h = 0.0
            volume = 0.0
            used_fallback = False

            if exchange_mgr is not None:
                try:
                    ticker = await asyncio.wait_for(
                        exchange_mgr.get_ticker(s), timeout=5.0
                    )
                    price = ticker.last_price
                    change_24h = ticker.change_pct_24h or 0.0
                    volume = ticker.volume_24h or 0.0
                except Exception as exc:
                    used_fallback = True
                    logger.warning(
                        "ws_fallback_price",
                        extra={"symbol": s, "error": str(exc)},
                    )
            else:
                used_fallback = True
                logger.warning(
                    "ws_fallback_price",
                    extra={"symbol": s, "error": "no exchange manager"},
                )

            if used_fallback:
                raise RuntimeError(
                    f"No real price data for {s} — exchange manager unavailable or failed. "
                    "Cannot generate simulated prices. Failing closed."
                )

            result[s] = {
                "price": round(price, 2),
                "change_24h": round(change_24h, 2),
                "volume": round(volume, 0),
            }

        return result

    # ------------------------------------------------------------------ #
    # Regime channel
    # ------------------------------------------------------------------ #

    def _get_regime(self) -> dict[str, Any]:
        """Get market regime from MarketStateEngine / RiskManager, with fallback."""
        market_engine = self._services.get("market_engine")
        risk_mgr = self._services.get("risk_manager")

        regime_str = "neutral"
        regime_score = 0.5

        if market_engine is not None:
            try:
                result = market_engine.detect_regime()
                raw = result.get("regime", "UNKNOWN")
                regime_str = self._map_regime(raw)
                regime_score = 0.75 if raw != "UNKNOWN" else 0.3
            except Exception as exc:
                logger.warning("ws_fallback_regime", extra={"error": str(exc)})
                if risk_mgr is not None:
                    regime_str, regime_score = self._risk_regime(risk_mgr)
        elif risk_mgr is not None:
            regime_str, regime_score = self._risk_regime(risk_mgr)
        else:
            logger.warning(
                "ws_fallback_regime", extra={"error": "no data source"}
            )

        return {"market": regime_str, "regime_score": round(regime_score, 2)}

    @staticmethod
    def _map_regime(raw: str) -> str:
        """Map internal regime names to simple WS-facing labels."""
        mapping = {
            "TRENDING_UP": "bullish",
            "TRENDING_DOWN": "bearish",
            "TRENDING": "bullish",
            "RANGING": "neutral",
            "MEAN_REVERT": "neutral",
            "VOLATILE": "volatile",
            "CRISIS": "volatile",
            "PANIC": "volatile",
            "RISK_OFF": "bearish",
            "NO_TRADE": "volatile",
            "RECOVERY": "bullish",
            "UNKNOWN": "neutral",
        }
        return mapping.get(raw, "neutral")

    @staticmethod
    def _risk_regime(risk_mgr: Any) -> tuple[str, float]:
        """Extract regime label/score from RiskManager's correlation regime."""
        try:
            status = risk_mgr.status()
            corr = status.get("correlation_regime", {})
            name = corr.get("regime", "normal_corr")
            mapping = {
                "crisis_corr": "volatile",
                "high_corr": "volatile",
                "normal_corr": "neutral",
                "low_corr": "neutral",
            }
            scores = {
                "crisis_corr": 0.85,
                "high_corr": 0.70,
                "normal_corr": 0.50,
                "low_corr": 0.30,
            }
            return mapping.get(name, "neutral"), scores.get(name, 0.5)
        except Exception:
            return "neutral", 0.5

    # ------------------------------------------------------------------ #
    # Risk channel
    # ------------------------------------------------------------------ #

    def _get_risk(self) -> dict[str, Any]:
        """Get risk snapshot from KillSwitch and RiskManager, with fallback."""
        risk_mgr = self._services.get("risk_manager")
        ks = self._services.get("kill_switch")

        kill_switch_active = False
        daily_pnl = 0.0
        drawdown = 0.0

        if risk_mgr is not None:
            try:
                status = risk_mgr.status()
                daily_pnl = float(status.get("daily_pnl", 0.0) or 0.0)
                dd_info = status.get("drawdown", {})
                if isinstance(dd_info, dict):
                    raw = dd_info.get("current_drawdown", "0.0")
                    drawdown = float(raw) if raw else 0.0
                ks_info = status.get("kill_switch", {})
                if isinstance(ks_info, dict):
                    kill_switch_active = bool(
                        ks_info.get("is_active", False)
                    )
            except Exception as exc:
                logger.warning("ws_fallback_risk", extra={"error": str(exc)})

        if ks is not None and risk_mgr is None:
            try:
                kill_switch_active = bool(
                    ks.status().get("is_active", False)
                )
            except Exception:
                pass

        return {
            "kill_switch_active": kill_switch_active,
            "daily_pnl": round(daily_pnl, 2),
            "drawdown": round(drawdown, 4),
        }

    # ------------------------------------------------------------------ #
    # Portfolio channel
    # ------------------------------------------------------------------ #

    async def _get_portfolio(self) -> dict[str, Any]:
        """Get portfolio snapshot from ExchangeManager, with fallback."""
        exchange_mgr = self._services.get("exchange_manager")

        if exchange_mgr is not None:
            try:
                pf = await asyncio.wait_for(
                    exchange_mgr.get_aggregated_portfolio(), timeout=5.0
                )
                return {
                    "total_value": round(pf.total_value, 2),
                    "position_count": len(pf.positions),
                    "unrealized_pnl": round(pf.total_unrealized_pnl, 2),
                }
            except Exception as exc:
                logger.warning(
                    "ws_fallback_portfolio", extra={"error": str(exc)}
                )
        else:
            logger.warning(
                "ws_fallback_portfolio",
                extra={"error": "no exchange manager"},
            )

        raise RuntimeError(
            "No real portfolio data — exchange manager unavailable or failed. "
            "Cannot generate simulated portfolio. Failing closed."
        )

    # ------------------------------------------------------------------ #
    # Main push loop body
    # ------------------------------------------------------------------ #

    async def _push_updates(self) -> None:
        """Fetch live data and push to each client based on their subscriptions."""
        # Collect unique symbols across all clients
        all_symbols: set[str] = set()
        for ws in self.active_connections[:]:
            sub = self.subscriptions.get(
                id(ws), {"channels": set(), "symbols": set()}
            )
            if sub["channels"]:
                all_symbols.update(sub["symbols"] or ["BTC/USDT"])

        # Fetch global data once per push cycle
        prices = (
            await self._get_prices(list(all_symbols)) if all_symbols else {}
        )
        regime = self._get_regime()
        risk = self._get_risk()
        portfolio = await self._get_portfolio()
        now = datetime.now(timezone.utc).isoformat()

        for ws in self.active_connections[:]:
            cid = id(ws)
            sub = self.subscriptions.get(
                cid, {"channels": set(), "symbols": set()}
            )
            channels = sub["channels"]
            symbols = list(sub["symbols"]) or ["BTC/USDT"]

            payload: dict[str, Any] = {"timestamp": now}

            if "price" in channels:
                payload["price"] = {
                    s: prices.get(s, prices.get("BTC/USDT", {}))
                    for s in symbols
                }
            if "regime" in channels:
                payload["regime"] = regime
            if "risk" in channels:
                payload["risk"] = risk
            if "portfolio" in channels:
                payload["portfolio"] = portfolio

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
    # FIX S2: Require auth token on WebSocket connections
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing auth token")
        return
    try:
        from quant_nanggroe.security.auth import JWTAuth
        import os
        secret = os.environ.get("QNAI_JWT_SECRET", "")
        if not secret:
            await websocket.close(code=4001, reason="Server auth not configured")
            return
        jwt_auth = JWTAuth(secret_key=secret)
        jwt_auth.validate_token(token)
    except Exception:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

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
