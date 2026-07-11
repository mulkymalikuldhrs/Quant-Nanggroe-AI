"""Longbridge REST Client — Stock & Options Trading.

Supports Longbridge Securities API for stock and options trading
on US, HK, and CN markets. Ported from OpenAlice IBKR patterns.

API docs: https://open.longportapp.com/en/docs
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from quant_nanggroe.exchange.base import ExchangeConfig, ExchangeError, OrderError
from quant_nanggroe.exchange.clients.base_rest_client import (
    BaseRestClient,
    ClientCapabilities,
)
from quant_nanggroe.types.market import OrderBook, OrderBookLevel
from quant_nanggroe.types.orders import Order, OrderSide, OrderStatus, OrderType
from quant_nanggroe.types.positions import Position, PositionSide

logger = logging.getLogger(__name__)


class LongbridgeClient(BaseRestClient):
    """Longbridge Securities REST client for stock and options trading.

    Supports US, HK, and CN stock markets via the Longbridge OpenAPI.

    Signing:
    - X-Api-Signature = hex(hmac_sha256(secret, timestamp + method + path + body))
    - X-Api-Key: API key
    - X-Timestamp: Unix seconds
    """

    _default_base_url = "https://openapi.longportapp.com"

    def __init__(self, config: ExchangeConfig) -> None:
        super().__init__(config)
        self._default_base_url = config.options.get(
            "base_url", "https://openapi.longportapp.com"
        )
        self._api_key = config.api_key or ""
        self._api_secret = config.api_secret or ""
        self._app_key = config.options.get("app_key", config.passphrase or "")

    @property
    def name(self) -> str:
        return "longbridge"

    @property
    def capabilities(self) -> ClientCapabilities:
        return ClientCapabilities(
            spot=True,
            futures=False,
            perps=False,
            margin=True,
            websocket=True,
            max_leverage=1.0,
            requires_passphrase=False,
        )

    # ----- Signing -----

    def _sign_request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[Dict[str, str], Optional[Dict[str, Any]], Optional[str]]:
        ts = str(int(time.time()))
        prehash = f"{ts}{method.upper()}{path}{body or ''}"
        sign = hmac.new(
            self._api_secret.encode("utf-8"),
            prehash.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        h = dict(headers or {})
        h.update({
            "X-Api-Key": self._api_key,
            "X-Api-Signature": sign,
            "X-Timestamp": ts,
            "Content-Type": "application/json",
        })
        if self._app_key:
            h["X-App-Key"] = self._app_key
        return h, params, body

    # ----- Order management -----

    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        client_order_id: Optional[str] = None,
        strategy_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Order:
        sd = side.value.upper()
        quantity_int = int(quantity)

        body: Dict[str, Any] = {
            "symbol": symbol,
            "side": sd,
            "quantity": quantity_int,
        }

        if order_type == OrderType.MARKET:
            body["order_type"] = "MO"
        elif order_type == OrderType.LIMIT:
            body["order_type"] = "LO"
            if price:
                body["price"] = str(price)
        elif order_type == OrderType.STOP:
            body["order_type"] = "STO"
            if stop_price:
                body["trigger_price"] = str(stop_price)
        elif order_type == OrderType.STOP_LIMIT:
            body["order_type"] = "STL"
            if price:
                body["price"] = str(price)
            if stop_price:
                body["trigger_price"] = str(stop_price)
        else:
            body["order_type"] = "MO"

        if client_order_id:
            body["client_order_id"] = client_order_id

        try:
            raw = await self._request("POST", "/v1/trade/order", json_body=body, signed=True)
        except ExchangeError as exc:
            raise OrderError(str(exc), exchange=self.name, original=exc)

        data = raw.get("data", raw) if isinstance(raw, dict) else {}
        order_id = str(data.get("order_id", "")) if isinstance(data, dict) else ""

        return Order(
            id=order_id,
            client_order_id=client_order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            status=OrderStatus.SUBMITTED,
            broker_id="longbridge",
            broker_order_id=order_id,
            strategy_name=strategy_name,
            agent_name=agent_name,
            notes=notes,
        )

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        body: Dict[str, Any] = {"order_id": order_id}
        await self._request("POST", "/v1/trade/order/cancel", json_body=body, signed=True)
        return Order(
            id=order_id, symbol=symbol or "",
            side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=0.0,
            status=OrderStatus.CANCELED, broker_id="longbridge", broker_order_id=order_id,
        )

    async def get_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        params = {"order_id": order_id}
        raw = await self._request("GET", "/v1/trade/order", params=params, signed=True)
        data = raw.get("data", raw) if isinstance(raw, dict) else {}
        od = data if isinstance(data, dict) else {}

        status_map = {
            "NotReported": OrderStatus.SUBMITTED, "ReplacedNotReported": OrderStatus.SUBMITTED,
            "ProtectedNotReported": OrderStatus.SUBMITTED, "VarietiesNotReported": OrderStatus.SUBMITTED,
            "Filled": OrderStatus.FILLED, "WaitToNew": OrderStatus.SUBMITTED,
            "New": OrderStatus.SUBMITTED, "WaitToReplace": OrderStatus.SUBMITTED,
            "PendingReplace": OrderStatus.SUBMITTED, "Replaced": OrderStatus.SUBMITTED,
            "PartialFilled": OrderStatus.PARTIALLY_FILLED,
            "WaitToCancel": OrderStatus.SUBMITTED, "PendingCancel": OrderStatus.SUBMITTED,
            "Rejected": OrderStatus.REJECTED, "Canceled": OrderStatus.CANCELED,
            "Expired": OrderStatus.EXPIRED, "PartialWithdrawal": OrderStatus.CANCELED,
        }
        side_map = {"BUY": OrderSide.BUY, "SELL": OrderSide.SELL}

        return Order(
            id=str(od.get("order_id", order_id)),
            symbol=str(od.get("symbol", symbol or "")),
            side=side_map.get(str(od.get("side", "")).upper(), OrderSide.BUY),
            order_type=OrderType.MARKET,
            quantity=float(od.get("quantity", 0)),
            price=float(od.get("price", 0)) or None,
            status=status_map.get(str(od.get("status", "")), OrderStatus.SUBMITTED),
            filled_quantity=float(od.get("executed_quantity", 0)),
            broker_id="longbridge",
            broker_order_id=str(od.get("order_id", order_id)),
        )

    # ----- Account -----

    async def get_balance(self) -> Dict[str, float]:
        raw = await self._request("GET", "/v1/asset/account", signed=True)
        result: Dict[str, float] = {}
        data = raw.get("data", raw) if isinstance(raw, dict) else {}
        if isinstance(data, dict):
            cash = data.get("cash", {})
            if isinstance(cash, dict):
                for ccy, val in cash.items():
                    try:
                        result[ccy.upper()] = float(val)
                    except (ValueError, TypeError):
                        pass
            # Also check for total_assets
            total = data.get("total_assets", 0)
            if total and "USD" not in result:
                try:
                    result["USD"] = float(total)
                except (ValueError, TypeError):
                    pass
        return result

    async def get_positions(self) -> List[Position]:
        raw = await self._request("GET", "/v1/asset/stock/positions", signed=True)
        positions: List[Position] = []
        data = raw.get("data", {}).get("channels", []) if isinstance(raw, dict) else []
        if isinstance(data, list):
            for channel in data:
                if not isinstance(channel, dict):
                    continue
                for p in channel.get("positions", []):
                    if not isinstance(p, dict):
                        continue
                    qty = float(p.get("quantity", 0))
                    if qty <= 0:
                        continue
                    entry = float(p.get("cost_price", 0))
                    mark = float(p.get("market_price", 0))
                    positions.append(Position(
                        symbol=str(p.get("symbol", "")),
                        side=PositionSide.LONG,
                        quantity=qty,
                        entry_price=entry,
                        current_price=mark,
                        cost_basis=qty * entry,
                        unrealized_pnl=float(p.get("unrealized_pnl", 0)),
                        broker_id="longbridge",
                    ))
        return positions

    # ----- Market data -----

    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
        params = {"symbol": symbol, "limit": limit}
        raw = await self._request("GET", "/v1/quote/depth", params=params, signed=False)

        data = raw.get("data", raw) if isinstance(raw, dict) else {}
        asks_list = data.get("asks", [])
        bids_list = data.get("bids", [])

        bids = [
            OrderBookLevel(price=float(b.get("price", 0)), quantity=float(b.get("volume", 0)))
            for b in bids_list if isinstance(b, dict) and b.get("price")
        ]
        asks = [
            OrderBookLevel(price=float(a.get("price", 0)), quantity=float(a.get("volume", 0)))
            for a in asks_list if isinstance(a, dict) and a.get("price")
        ]
        spread = (asks[0].price - bids[0].price) if bids and asks else None
        mid = ((bids[0].price + asks[0].price) / 2) if bids and asks else None

        return OrderBook(
            symbol=symbol, timestamp=datetime.now(),
            bids=bids, asks=asks, spread=spread, mid_price=mid,
        )

    async def get_klines(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 100,
        before_time: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        period_map = {
            "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
            "1h": "60m", "4h": "60m", "1d": "1d", "1w": "1w", "1M": "1M",
        }
        period = period_map.get(interval, "60m")

        params: Dict[str, Any] = {"symbol": symbol, "period": period, "count": limit}
        if before_time:
            params["to"] = before_time

        raw = await self._request("GET", "/v1/quote/candlestick", params=params, signed=False)
        data = raw.get("data", []) if isinstance(raw, dict) else []

        klines: List[Dict[str, Any]] = []
        if isinstance(data, list):
            for candle in data:
                if not isinstance(candle, dict):
                    continue
                klines.append({
                    "time": int(candle.get("timestamp", 0)),
                    "open": float(candle.get("open", 0)),
                    "high": float(candle.get("high", 0)),
                    "low": float(candle.get("low", 0)),
                    "close": float(candle.get("close", 0)),
                    "volume": float(candle.get("volume", 0)),
                })
        klines.sort(key=lambda x: x["time"])
        return klines[:limit]

    async def health_check(self) -> bool:
        try:
            await self._request("GET", "/v1/quote/ping", signed=False)
            return True
        except Exception:
            try:
                balance = await self.get_balance()
                return isinstance(balance, dict)
            except Exception:
                return False
