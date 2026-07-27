"""Coinbase Exchange REST Client.

Supports Coinbase Exchange (pro/advanced) with HMAC-SHA256 + Base64
request signing including passphrase.

API docs: https://docs.cloud.coinbase.com/exchange/reference/
"""

from __future__ import annotations

import base64
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
from quant_nanggroe.types.positions import Position

logger = logging.getLogger(__name__)


class CoinbaseClient(BaseRestClient):
    """Coinbase Exchange REST client.

    Auth headers:
    - CB-ACCESS-KEY
    - CB-ACCESS-SIGN = base64(hmac_sha256(base64_decode(secret), timestamp + method + path + body))
    - CB-ACCESS-TIMESTAMP (seconds)
    - CB-ACCESS-PASSPHRASE
    """

    _default_base_url = "https://api.exchange.coinbase.com"

    def __init__(self, config: ExchangeConfig) -> None:
        super().__init__(config)
        self._default_base_url = config.options.get(
            "base_url", "https://api.exchange.coinbase.com"
        )
        self._api_key = config.api_key or ""
        self._api_secret = config.api_secret or ""
        self._passphrase = config.passphrase or ""
        try:
            self._secret_bytes = base64.b64decode(self._api_secret) if self._api_secret else b""
        except Exception:
            self._secret_bytes = b""

    @property
    def name(self) -> str:
        return "coinbase"

    @property
    def capabilities(self) -> ClientCapabilities:
        return ClientCapabilities(
            spot=True,
            futures=True,
            perps=False,
            margin=False,
            websocket=True,
            max_leverage=3.0,
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
        ts = str(int(time.time()))
        signed_path = path
        if params:
            items = []
            for k in sorted(params.keys()):
                v = params.get(k)
                if v is not None:
                    items.append(f"{k}={v}")
            if items:
                signed_path = f"{path}?{'&'.join(items)}"
        prehash = f"{ts}{method.upper()}{signed_path}{body or ''}"
        mac = hmac.new(self._secret_bytes, prehash.encode("utf-8"), hashlib.sha256).digest()
        sign = base64.b64encode(mac).decode("utf-8")

        h = dict(headers or {})
        h.update({
            "CB-ACCESS-KEY": self._api_key,
            "CB-ACCESS-SIGN": sign,
            "CB-ACCESS-TIMESTAMP": ts,
            "CB-ACCESS-PASSPHRASE": self._passphrase,
            "Content-Type": "application/json",
        })
        return h, params, body

    # ----- Helpers -----

    @staticmethod
    def _normalize_product_id(symbol: str) -> str:
        parts = symbol.replace("-", "/").split("/")
        if len(parts) == 2:
            return f"{parts[0].upper()}-{parts[1].upper()}"
        return symbol.upper()

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
        product_id = self._normalize_product_id(symbol)
        sd = side.value.lower()

        body: Dict[str, Any] = {
            "product_id": product_id,
            "side": sd,
            "type": "market" if order_type == OrderType.MARKET else "limit",
            "size": str(quantity),
        }
        if order_type == OrderType.LIMIT and price:
            body["price"] = str(price)
            body["time_in_force"] = "GTC"
        if client_order_id:
            body["client_oid"] = client_order_id

        try:
            raw = await self._request("POST", "/orders", json_body=body, signed=True)
        except ExchangeError as exc:
            raise OrderError(str(exc), exchange=self.name, original=exc)

        order_id = str(raw.get("id", "")) if isinstance(raw, dict) else ""

        return Order(
            id=order_id,
            client_order_id=client_order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            status=OrderStatus.SUBMITTED,
            broker_id="coinbase",
            broker_order_id=order_id,
            strategy_name=strategy_name,
            agent_name=agent_name,
            notes=notes,
        )

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        await self._request("DELETE", f"/orders/{order_id}", signed=True)
        return Order(
            id=order_id, symbol=symbol or "",
            side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=0.0,
            status=OrderStatus.CANCELED, broker_id="coinbase", broker_order_id=order_id,
        )

    async def get_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        raw = await self._request("GET", f"/orders/{order_id}", signed=True)
        od = raw if isinstance(raw, dict) else {}

        status_map = {
            "pending": OrderStatus.SUBMITTED, "open": OrderStatus.SUBMITTED,
            "filled": OrderStatus.FILLED, "done": OrderStatus.FILLED,
            "canceled": OrderStatus.CANCELED, "cancelled": OrderStatus.CANCELED,
        }
        side_map = {"buy": OrderSide.BUY, "sell": OrderSide.SELL}

        return Order(
            id=str(od.get("id", order_id)),
            symbol=str(od.get("product_id", symbol or "")),
            side=side_map.get(str(od.get("side", "")).lower(), OrderSide.BUY),
            order_type=OrderType.MARKET,
            quantity=float(od.get("size", 0)),
            price=float(od.get("price", 0)) or None,
            status=status_map.get(str(od.get("status", "")), OrderStatus.SUBMITTED),
            filled_quantity=float(od.get("filled_size", 0)),
            broker_id="coinbase",
            broker_order_id=str(od.get("id", order_id)),
        )

    # ----- Account -----

    async def get_balance(self) -> Dict[str, float]:
        raw = await self._request("GET", "/accounts", signed=True)
        result: Dict[str, float] = {}
        if isinstance(raw, list):
            for acct in raw:
                if isinstance(acct, dict):
                    ccy = str(acct.get("currency", ""))
                    avail = float(acct.get("available", 0))
                    if avail > 0:
                        result[ccy] = avail
        return result

    async def get_positions(self) -> List[Position]:
        # Coinbase spot doesn't have traditional positions
        return []

    # ----- Market data -----

    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
        product_id = self._normalize_product_id(symbol)
        params = {"level": 2}
        raw = await self._request("GET", f"/products/{product_id}/book", params=params, signed=False)

        bids = [
            OrderBookLevel(price=float(b[0]), quantity=float(b[1]))
            for b in raw.get("bids", []) if len(b) >= 2
        ]
        asks = [
            OrderBookLevel(price=float(a[0]), quantity=float(a[1]))
            for a in raw.get("asks", []) if len(a) >= 2
        ]
        spread = (asks[0].price - bids[0].price) if bids and asks else None
        mid = ((bids[0].price + asks[0].price) / 2) if bids and asks else None

        return OrderBook(
            symbol=symbol, timestamp=datetime.now(),
            bids=bids[:limit], asks=asks[:limit], spread=spread, mid_price=mid,
        )

    async def get_klines(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 100,
        before_time: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        product_id = self._normalize_product_id(symbol)
        granularity_map = {
            "1m": 60, "5m": 300, "15m": 900, "1h": 3600,
            "6h": 21600, "1d": 86400,
        }
        granularity = granularity_map.get(interval, 3600)

        params: Dict[str, Any] = {"granularity": granularity}
        if before_time:
            params["end"] = str(before_time)

        raw = await self._request("GET", f"/products/{product_id}/candles", params=params, signed=False)

        klines: List[Dict[str, Any]] = []
        if isinstance(raw, list):
            for candle in raw:
                if not isinstance(candle, list) or len(candle) < 6:
                    continue
                klines.append({
                    "time": int(candle[0]),
                    "open": float(candle[3]),
                    "high": float(candle[2]),
                    "low": float(candle[1]),
                    "close": float(candle[4]),
                    "volume": float(candle[5]),
                })
        klines.sort(key=lambda x: x["time"])
        return klines[:limit]

    async def health_check(self) -> bool:
        try:
            await self._request("GET", "/time", signed=False)
            return True
        except Exception:
            return False
