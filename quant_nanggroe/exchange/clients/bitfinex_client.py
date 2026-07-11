"""Bitfinex REST Client — V2 API (Spot + Derivatives).

Supports Bitfinex V2 API with HMAC-SHA384 request signing
for spot exchange orders and derivatives.

API docs: https://docs.bitfinex.com/docs
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


class BitfinexClient(BaseRestClient):
    """Bitfinex V2 REST client for spot and derivatives.

    Auth headers:
    - bfx-apikey
    - bfx-nonce
    - bfx-signature = hex(hmac_sha384(secret, "/api/v2" + path + nonce + body))
    """

    _default_base_url = "https://api.bitfinex.com"

    def __init__(self, config: ExchangeConfig) -> None:
        super().__init__(config)
        self._default_base_url = config.options.get(
            "base_url", "https://api.bitfinex.com"
        )
        self._api_key = config.api_key or ""
        self._api_secret = config.api_secret or ""
        self._market_type = config.options.get("market_type", "spot")

    @property
    def name(self) -> str:
        return "bitfinex"

    @property
    def capabilities(self) -> ClientCapabilities:
        return ClientCapabilities(
            spot=True,
            futures=True,
            perps=True,
            margin=True,
            websocket=True,
            max_leverage=10.0,
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
        nonce = str(self._now_ms())
        payload = f"/api/v2{path}{nonce}{body or ''}"
        sign = hmac.new(
            self._api_secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha384,
        ).hexdigest()

        h = dict(headers or {})
        h.update({
            "bfx-apikey": self._api_key,
            "bfx-nonce": nonce,
            "bfx-signature": sign,
            "content-type": "application/json",
        })
        return h, params, body

    # ----- Helpers -----

    @staticmethod
    def _normalize_symbol(symbol: str, market_type: str = "spot") -> str:
        parts = symbol.replace("-", "/").split("/")
        if len(parts) == 2:
            base, quote = parts[0].upper(), parts[1].upper()
            if market_type == "perps":
                return f"t{base}F0:{quote}F0"
            return f"t{base}{quote}"
        return f"t{symbol.upper()}"

    def _is_spot(self) -> bool:
        return self._market_type == "spot"

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
        sym = self._normalize_symbol(symbol, self._market_type)
        sd = side.value.lower()
        amt = quantity if sd == "buy" else -quantity

        order_type_str = "EXCHANGE MARKET" if (self._is_spot() and order_type == OrderType.MARKET) else \
                         "EXCHANGE LIMIT" if (self._is_spot() and order_type == OrderType.LIMIT) else \
                         "MARKET" if order_type == OrderType.MARKET else "LIMIT"

        body: Dict[str, Any] = {
            "type": order_type_str,
            "symbol": sym,
            "amount": str(amt),
        }
        if order_type == OrderType.LIMIT and price:
            body["price"] = str(price)
        elif order_type == OrderType.MARKET:
            body["price"] = "0"

        if client_order_id:
            try:
                cid = int("".join(c for c in str(client_order_id) if c.isdigit())[:18] or "0")
                if cid > 0:
                    body["cid"] = cid
            except Exception:
                pass

        try:
            raw = await self._request("POST", "/v2/auth/w/order/submit", json_body=body, signed=True)
        except ExchangeError as exc:
            raise OrderError(str(exc), exchange=self.name, original=exc)

        order_id = ""
        try:
            if isinstance(raw, list) and len(raw) >= 4 and isinstance(raw[3], list) and raw[3]:
                order = raw[3][0]
                if isinstance(order, list) and order:
                    order_id = str(order[0])
        except Exception:
            order_id = ""

        return Order(
            id=order_id,
            client_order_id=client_order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            status=OrderStatus.SUBMITTED,
            broker_id="bitfinex",
            broker_order_id=order_id,
            strategy_name=strategy_name,
            agent_name=agent_name,
            notes=notes,
        )

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        try:
            oid = int(float(order_id))
        except Exception:
            raise OrderError("Invalid Bitfinex order_id", exchange=self.name)
        body: Dict[str, Any] = {"id": oid}
        await self._request("POST", "/v2/auth/w/order/cancel", json_body=body, signed=True)
        return Order(
            id=order_id, symbol=symbol or "",
            side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=0.0,
            status=OrderStatus.CANCELED, broker_id="bitfinex", broker_order_id=order_id,
        )

    async def get_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        try:
            oid = int(float(order_id))
        except Exception:
            raise OrderError("Invalid Bitfinex order_id", exchange=self.name)
        raw = await self._request("POST", f"/v2/auth/r/order/{oid}", json_body={}, signed=True)

        status = ""
        filled = 0.0
        avg_price = 0.0
        try:
            if isinstance(raw, list) and len(raw) >= 15:
                status = str(raw[13] or "")
                amount_orig = float(raw[7] or 0)
                amount_remaining = float(raw[6] or 0)
                filled = abs(amount_orig - amount_remaining)
                avg_price = float(raw[14] or 0)
        except Exception:
            pass

        return Order(
            id=order_id, symbol=symbol or "",
            side=OrderSide.BUY, order_type=OrderType.MARKET,
            quantity=0.0, status=OrderStatus.SUBMITTED,
            filled_quantity=filled,
            average_fill_price=avg_price if avg_price > 0 else None,
            broker_id="bitfinex", broker_order_id=order_id,
        )

    # ----- Account -----

    async def get_balance(self) -> Dict[str, float]:
        raw = await self._request("POST", "/v2/auth/r/wallets", json_body={}, signed=True)
        result: Dict[str, float] = {}
        if isinstance(raw, list):
            for w in raw:
                if isinstance(w, list) and len(w) >= 4:
                    ccy = str(w[1])
                    avail = float(w[4] if len(w) > 4 else w[2])
                    if avail > 0:
                        result[ccy] = avail
        return result

    async def get_positions(self) -> List[Position]:
        raw = await self._request("POST", "/v2/auth/r/positions", json_body={}, signed=True)
        positions: List[Position] = []
        if isinstance(raw, list):
            for p in raw:
                if not isinstance(p, list) or len(p) < 6:
                    continue
                amt = float(p[2] or 0)
                if amt == 0:
                    continue
                side = PositionSide.LONG if amt > 0 else PositionSide.SHORT
                entry = float(p[3] or 0)
                positions.append(Position(
                    symbol=str(p[1] or ""),
                    side=side,
                    quantity=abs(amt),
                    entry_price=entry,
                    current_price=entry,
                    cost_basis=abs(amt) * entry,
                    unrealized_pnl=float(p[4] or 0),
                    broker_id="bitfinex",
                ))
        return positions

    # ----- Market data -----

    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
        sym = self._normalize_symbol(symbol, self._market_type)
        params = {"limit": limit}
        raw = await self._request("GET", f"/v2/book/{sym}/P0", params=params, signed=False)

        bids = []
        asks = []
        if isinstance(raw, list):
            for entry in raw:
                if not isinstance(entry, list) or len(entry) < 3:
                    continue
                price, count, amount = float(entry[0]), float(entry[1]), float(entry[2])
                level = OrderBookLevel(price=price, quantity=abs(amount))
                if amount > 0:
                    bids.append(level)
                else:
                    asks.append(level)
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
        sym = self._normalize_symbol(symbol, self._market_type)
        # Bitfinex candle periods: 1m, 5m, 15m, 30m, 1h, 3h, 6h, 12h, 1D, 1W, 14D, 1M
        section = "hist"
        params: Dict[str, Any] = {"limit": limit}
        if before_time:
            params["end"] = before_time * 1000

        raw = await self._request(
            "GET", f"/v2/candles/trade:{interval}:{sym}/{section}",
            params=params, signed=False,
        )

        klines: List[Dict[str, Any]] = []
        if isinstance(raw, list):
            for candle in raw:
                if not isinstance(candle, list) or len(candle) < 6:
                    continue
                klines.append({
                    "time": int(candle[0]) // 1000,
                    "open": float(candle[1]),
                    "high": float(candle[3]),
                    "low": float(candle[4]),
                    "close": float(candle[2]),
                    "volume": float(candle[5]),
                })
        klines.sort(key=lambda x: x["time"])
        return klines

    async def health_check(self) -> bool:
        try:
            data = await self._request("GET", "/v2/platform/status", signed=False)
            return isinstance(data, list) and data and int(data[0]) == 1
        except Exception:
            return False
