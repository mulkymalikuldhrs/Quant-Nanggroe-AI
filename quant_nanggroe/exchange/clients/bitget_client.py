"""Bitget REST Client — V2 Mix API (Spot + USDT Futures).

Supports Bitget V2 API with HMAC-SHA256 + Base64 request signing
for both spot and USDT-margined perpetual markets.

API docs: https://bitgetlimited.github.io/apidoc/en/
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

from quant_nanggroe.exchange.base import ExchangeConfig, ExchangeError, OrderError
from quant_nanggroe.exchange.clients.base_rest_client import (
    BaseRestClient,
    ClientCapabilities,
)
from quant_nanggroe.types.market import OrderBook, OrderBookLevel
from quant_nanggroe.types.orders import Order, OrderSide, OrderStatus, OrderType
from quant_nanggroe.types.positions import Position, PositionSide

logger = logging.getLogger(__name__)


class BitgetClient(BaseRestClient):
    """Bitget V2 Mix REST client for spot and USDT futures.

    Signing:
    - ACCESS-SIGN = base64(hmac_sha256(secret, timestamp + method + request_path + body))
    """

    _default_base_url = "https://api.bitget.com"

    def __init__(self, config: ExchangeConfig) -> None:
        super().__init__(config)
        self._default_base_url = config.options.get(
            "base_url", "https://api.bitget.com"
        )
        self._api_key = config.api_key or ""
        self._api_secret = config.api_secret or ""
        self._passphrase = config.passphrase or ""
        self._product_type = config.options.get("product_type", "USDT-FUTURES")

    @property
    def name(self) -> str:
        return "bitget"

    @property
    def capabilities(self) -> ClientCapabilities:
        return ClientCapabilities(
            spot=True,
            futures=True,
            perps=True,
            margin=True,
            websocket=True,
            max_leverage=125.0,
            requires_passphrase=True,
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
        ts_ms = str(self._now_ms())
        qs = ""
        if params:
            norm = {str(k): "" if v is None else str(v) for k, v in params.items()}
            qs = urlencode(sorted(norm.items()), doseq=True)
        signed_path = f"{path}?{qs}" if qs else path
        prehash = f"{ts_ms}{method.upper()}{signed_path}{body or ''}"
        mac = hmac.new(
            self._api_secret.encode("utf-8"),
            prehash.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        sign = base64.b64encode(mac).decode("utf-8")

        h = dict(headers or {})
        h.update({
            "ACCESS-KEY": self._api_key,
            "ACCESS-SIGN": sign,
            "ACCESS-TIMESTAMP": ts_ms,
            "ACCESS-PASSPHRASE": self._passphrase,
            "Content-Type": "application/json",
        })
        return h, params, body

    def _handle_error_response(self, status_code: int, data: Dict[str, Any], text: str) -> None:
        if status_code >= 400:
            raise ExchangeError(f"Bitget HTTP {status_code}: {text[:300]}", exchange=self.name)
        if isinstance(data, dict):
            c = str(data.get("code") or "")
            if c and c not in ("00000", "0"):
                raise ExchangeError(f"Bitget API error: {data}", exchange=self.name)

    # ----- Helpers -----

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        return symbol.replace("/", "").upper()

    def _is_futures(self) -> bool:
        return self._product_type in ("USDT-FUTURES", "COIN-FUTURES", "USDC-FUTURES")

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
        sym = self._normalize_symbol(symbol)
        sd = side.value.lower()

        if self._is_futures():
            body: Dict[str, Any] = {
                "symbol": sym,
                "productType": self._product_type,
                "marginCoin": "USDT",
                "marginMode": "crossed",
                "side": sd,
                "size": str(quantity),
            }
            if order_type == OrderType.MARKET:
                body["orderType"] = "market"
            else:
                body["orderType"] = "limit"
                body["price"] = str(price or 0)
            if client_order_id:
                body["clientOid"] = client_order_id
            path = "/api/v2/mix/order/place-order"
        else:
            body = {
                "symbol": sym,
                "side": sd,
                "orderType": "market" if order_type == OrderType.MARKET else "limit",
                "size": str(quantity),
            }
            if order_type == OrderType.LIMIT and price:
                body["price"] = str(price)
            if client_order_id:
                body["clientOid"] = client_order_id
            path = "/api/v2/spot/trade/place-order"

        try:
            raw = await self._request("POST", path, json_body=body, signed=True)
        except ExchangeError as exc:
            raise OrderError(str(exc), exchange=self.name, original=exc)

        data = raw.get("data", {}) if isinstance(raw, dict) else {}
        order_id = str(data.get("orderId", "")) if isinstance(data, dict) else ""

        return Order(
            id=order_id,
            client_order_id=client_order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            status=OrderStatus.SUBMITTED,
            broker_id="bitget",
            broker_order_id=order_id,
            strategy_name=strategy_name,
            agent_name=agent_name,
            notes=notes,
        )

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        sym = self._normalize_symbol(symbol or "")
        if self._is_futures():
            body = {"symbol": sym, "productType": self._product_type, "marginCoin": "USDT", "orderId": order_id}
            path = "/api/v2/mix/order/cancel-order"
        else:
            body = {"symbol": sym, "orderId": order_id}
            path = "/api/v2/spot/trade/cancel-order"

        await self._request("POST", path, json_body=body, signed=True)
        return Order(
            id=order_id, symbol=symbol or "",
            side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=0.0,
            status=OrderStatus.CANCELED, broker_id="bitget", broker_order_id=order_id,
        )

    async def get_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        sym = self._normalize_symbol(symbol or "")
        if self._is_futures():
            params = {"symbol": sym, "productType": self._product_type, "orderId": order_id}
            path = "/api/v2/mix/order/detail"
        else:
            params = {"symbol": sym, "orderId": order_id}
            path = "/api/v2/spot/trade/orderInfo"

        raw = await self._request("GET", path, params=params, signed=True)
        data = raw.get("data", {}) if isinstance(raw, dict) else {}
        od = data if isinstance(data, dict) else {}

        status_map = {
            "init": OrderStatus.SUBMITTED, "live": OrderStatus.SUBMITTED,
            "partially_filled": OrderStatus.PARTIALLY_FILLED,
            "filled": OrderStatus.FILLED, "cancelled": OrderStatus.CANCELED,
        }
        side_map = {"buy": OrderSide.BUY, "sell": OrderSide.SELL}

        return Order(
            id=str(od.get("orderId", order_id)),
            symbol=symbol or "",
            side=side_map.get(str(od.get("side", "")).lower(), OrderSide.BUY),
            order_type=OrderType.MARKET,
            quantity=float(od.get("size", 0)),
            price=float(od.get("price", 0)) or None,
            status=status_map.get(str(od.get("state", "")), OrderStatus.SUBMITTED),
            filled_quantity=float(od.get("baseVolume", 0)),
            broker_id="bitget",
            broker_order_id=str(od.get("orderId", order_id)),
        )

    # ----- Account -----

    async def get_balance(self) -> Dict[str, float]:
        if self._is_futures():
            params = {"productType": self._product_type}
            raw = await self._request("GET", "/api/v2/mix/account/accounts", params=params, signed=True)
        else:
            raw = await self._request("GET", "/api/v2/spot/account/assets", signed=True)

        result: Dict[str, float] = {}
        data = raw.get("data", []) if isinstance(raw, dict) else []
        if isinstance(data, list):
            for acct in data:
                if isinstance(acct, dict):
                    coin = str(acct.get("coin", acct.get("marginCoin", "")))
                    avail = float(acct.get("available", acct.get("availableBalance", 0)))
                    if avail > 0 and coin:
                        result[coin] = avail
        return result

    async def get_positions(self) -> List[Position]:
        if not self._is_futures():
            return []
        params = {"productType": self._product_type}
        raw = await self._request("GET", "/api/v2/mix/position/all-position", params=params, signed=True)
        positions: List[Position] = []
        data = raw.get("data", []) if isinstance(raw, dict) else []
        if isinstance(data, list):
            for p in data:
                if not isinstance(p, dict):
                    continue
                qty = float(p.get("total", 0))
                if qty <= 0:
                    continue
                hold_side = str(p.get("holdSide", "")).lower()
                side = PositionSide.LONG if hold_side == "long" else PositionSide.SHORT
                entry = float(p.get("averageOpenPrice", 0))
                mark = float(p.get("markPrice", 0))
                positions.append(Position(
                    symbol=str(p.get("symbol", "")),
                    side=side,
                    quantity=qty,
                    entry_price=entry,
                    current_price=mark,
                    cost_basis=qty * entry,
                    unrealized_pnl=float(p.get("unrealizedPL", 0)),
                    broker_id="bitget",
                ))
        return positions

    # ----- Market data -----

    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
        sym = self._normalize_symbol(symbol)
        if self._is_futures():
            params = {"symbol": sym, "productType": self._product_type, "limit": str(limit)}
            path = "/api/v2/mix/market/depth"
        else:
            params = {"symbol": sym, "limit": str(limit)}
            path = "/api/v2/spot/market/orderbook"

        raw = await self._request("GET", path, params=params, signed=False)
        data = raw.get("data", {}) if isinstance(raw, dict) else {}
        asks_list = data.get("asks", [])
        bids_list = data.get("bids", [])

        bids = [
            OrderBookLevel(price=float(b[0]), quantity=float(b[1]))
            for b in bids_list if len(b) >= 2
        ]
        asks = [
            OrderBookLevel(price=float(a[0]), quantity=float(a[1]))
            for a in asks_list if len(a) >= 2
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
        sym = self._normalize_symbol(symbol)
        if self._is_futures():
            params: Dict[str, Any] = {"symbol": sym, "productType": self._product_type, "granularity": interval}
            path = "/api/v2/mix/market/candles"
        else:
            params = {"symbol": sym, "granularity": interval}
            path = "/api/v2/spot/market/candles"

        if before_time:
            params["endTime"] = str(before_time * 1000)
        params["limit"] = str(limit)

        raw = await self._request("GET", path, params=params, signed=False)
        data = raw.get("data", []) if isinstance(raw, dict) else []

        klines: List[Dict[str, Any]] = []
        if isinstance(data, list):
            for candle in data:
                if not isinstance(candle, list) or len(candle) < 6:
                    continue
                klines.append({
                    "time": int(candle[0]) // 1000,
                    "open": float(candle[1]),
                    "high": float(candle[2]),
                    "low": float(candle[3]),
                    "close": float(candle[4]),
                    "volume": float(candle[5]),
                })
        klines.sort(key=lambda x: x["time"])
        return klines

    async def health_check(self) -> bool:
        try:
            data = await self._request("GET", "/api/v2/public/time", signed=False)
            return isinstance(data, dict)
        except Exception:
            return False
