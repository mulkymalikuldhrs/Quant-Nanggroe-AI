"""Gate.io REST Client — V4 API (Spot + USDT Futures).

Supports Gate.io V4 API with HMAC-SHA512 request signing
for both spot and USDT-margined perpetual markets.

API docs: https://www.gate.io/docs/developers/apiv4/
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from datetime import datetime
from decimal import ROUND_DOWN, Decimal
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


class GateClient(BaseRestClient):
    """Gate.io V4 REST client for spot and USDT futures.

    Signing (V4):
    SIGN = hex(hmac_sha512(secret, method + "\\n" + url + "\\n" + query + "\\n" + body + "\\n" + timestamp))
    """

    _default_base_url = "https://api.gateio.ws"

    def __init__(self, config: ExchangeConfig) -> None:
        super().__init__(config)
        self._api_key = config.api_key or ""
        self._api_secret = config.api_secret or ""
        self._market_type = config.options.get("market_type", "spot")

    @property
    def name(self) -> str:
        return "gate"

    @property
    def capabilities(self) -> ClientCapabilities:
        return ClientCapabilities(
            spot=True,
            futures=True,
            perps=True,
            margin=True,
            websocket=True,
            max_leverage=100.0,
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
        qs = ""
        if params:
            norm = {str(k): "" if v is None else str(v) for k, v in params.items()}
            qs = urlencode(sorted(norm.items()), doseq=True)
        msg = f"{method.upper()}\n{path}\n{qs}\n{body or ''}\n{ts}"
        sign = hmac.new(
            self._api_secret.encode("utf-8"),
            msg.encode("utf-8"),
            hashlib.sha512,
        ).hexdigest()

        h = dict(headers or {})
        h.update({
            "KEY": self._api_key,
            "Timestamp": ts,
            "SIGN": sign,
            "Content-Type": "application/json",
        })
        return h, params, body

    # ----- Helpers -----

    @staticmethod
    def _normalize_currency_pair(symbol: str) -> str:
        return symbol.replace("/", "_").replace("-", "_").upper()

    def _is_futures(self) -> bool:
        return self._market_type in ("futures", "perps", "swap")

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
        if self._is_futures():
            return await self._place_futures_order(
                symbol, side, order_type, quantity, price, client_order_id,
                strategy_name, agent_name, notes,
            )
        return await self._place_spot_order(
            symbol, side, order_type, quantity, price, client_order_id,
            strategy_name, agent_name, notes,
        )

    async def _place_spot_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float] = None,
        client_order_id: Optional[str] = None,
        strategy_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Order:
        pair = self._normalize_currency_pair(symbol)
        sd = side.value.lower()
        body: Dict[str, Any] = {
            "currency_pair": pair,
            "side": sd,
            "type": "market" if order_type == OrderType.MARKET else "limit",
            "amount": str(quantity),
        }
        if order_type == OrderType.LIMIT and price:
            body["price"] = str(price)
            body["time_in_force"] = "gtc"
        if client_order_id:
            body["text"] = str(client_order_id)

        try:
            raw = await self._request("POST", "/api/v4/spot/orders", json_body=body, signed=True)
        except ExchangeError as exc:
            raise OrderError(str(exc), exchange=self.name, original=exc)

        order_id = str(raw.get("id", "")) if isinstance(raw, dict) else ""

        return Order(
            id=order_id, client_order_id=client_order_id,
            symbol=symbol, side=side, order_type=order_type,
            quantity=quantity, price=price,
            status=OrderStatus.SUBMITTED,
            broker_id="gate", broker_order_id=order_id,
            strategy_name=strategy_name, agent_name=agent_name, notes=notes,
        )

    async def _place_futures_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float] = None,
        client_order_id: Optional[str] = None,
        strategy_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Order:
        contract = self._normalize_currency_pair(symbol)
        sd = side.value.lower()
        signed_size = int(quantity) if sd == "buy" else -int(quantity)

        body: Dict[str, Any] = {
            "contract": contract,
            "size": signed_size,
            "price": "0" if order_type == OrderType.MARKET else str(price or 0),
            "tif": "ioc" if order_type == OrderType.MARKET else "gtc",
        }
        if client_order_id:
            body["text"] = str(client_order_id)

        try:
            raw = await self._request("POST", "/api/v4/futures/usdt/orders", json_body=body, signed=True)
        except ExchangeError as exc:
            raise OrderError(str(exc), exchange=self.name, original=exc)

        order_id = str(raw.get("id", "")) if isinstance(raw, dict) else ""

        return Order(
            id=order_id, client_order_id=client_order_id,
            symbol=symbol, side=side, order_type=order_type,
            quantity=quantity, price=price,
            status=OrderStatus.SUBMITTED,
            broker_id="gate", broker_order_id=order_id,
            strategy_name=strategy_name, agent_name=agent_name, notes=notes,
        )

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        if self._is_futures():
            await self._request("DELETE", f"/api/v4/futures/usdt/orders/{order_id}", signed=True)
        else:
            await self._request("DELETE", f"/api/v4/spot/orders/{order_id}", signed=True)
        return Order(
            id=order_id, symbol=symbol or "",
            side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=0.0,
            status=OrderStatus.CANCELED, broker_id="gate", broker_order_id=order_id,
        )

    async def get_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        if self._is_futures():
            raw = await self._request("GET", f"/api/v4/futures/usdt/orders/{order_id}", signed=True)
        else:
            raw = await self._request("GET", f"/api/v4/spot/orders/{order_id}", signed=True)

        od = raw if isinstance(raw, dict) else {}
        status_map = {
            "open": OrderStatus.SUBMITTED, "finished": OrderStatus.FILLED,
            "cancelled": OrderStatus.CANCELED, "canceled": OrderStatus.CANCELED,
        }
        side_map = {"buy": OrderSide.BUY, "sell": OrderSide.SELL}

        return Order(
            id=str(od.get("id", order_id)),
            symbol=symbol or "",
            side=side_map.get(str(od.get("side", "")).lower(), OrderSide.BUY),
            order_type=OrderType.MARKET,
            quantity=float(od.get("amount", od.get("size", 0))),
            price=float(od.get("price", 0)) or None,
            status=status_map.get(str(od.get("status", "")), OrderStatus.SUBMITTED),
            filled_quantity=float(od.get("filled_amount", od.get("filled_size", 0))),
            broker_id="gate",
            broker_order_id=str(od.get("id", order_id)),
        )

    # ----- Account -----

    async def get_balance(self) -> Dict[str, float]:
        if self._is_futures():
            raw = await self._request("GET", "/api/v4/futures/usdt/accounts", signed=True)
            result: Dict[str, float] = {}
            if isinstance(raw, dict):
                avail = float(raw.get("available", 0))
                total = float(raw.get("total", 0))
                if total > 0:
                    result["USDT"] = avail
            return result

        raw = await self._request("GET", "/api/v4/spot/accounts", signed=True)
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
        if not self._is_futures():
            return []
        raw = await self._request("GET", "/api/v4/futures/usdt/positions", signed=True)
        positions: List[Position] = []
        if isinstance(raw, list):
            for p in raw:
                if not isinstance(p, dict):
                    continue
                qty = float(p.get("size", 0))
                if qty == 0:
                    continue
                side = PositionSide.LONG if qty > 0 else PositionSide.SHORT
                entry = float(p.get("entry_price", 0))
                mark = float(p.get("mark_price", 0))
                positions.append(Position(
                    symbol=str(p.get("contract", "")),
                    side=side,
                    quantity=abs(qty),
                    entry_price=entry,
                    current_price=mark,
                    cost_basis=abs(qty) * entry,
                    unrealized_pnl=float(p.get("unrealised_pnl", 0)),
                    broker_id="gate",
                ))
        return positions

    # ----- Market data -----

    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
        if self._is_futures():
            contract = self._normalize_currency_pair(symbol)
            params = {"contract": contract, "limit": limit}
            raw = await self._request("GET", "/api/v4/futures/usdt/order_book", params=params, signed=False)
        else:
            pair = self._normalize_currency_pair(symbol)
            params = {"currency_pair": pair, "limit": limit}
            raw = await self._request("GET", "/api/v4/spot/order_book", params=params, signed=False)

        bids = [
            OrderBookLevel(price=float(b[0]), quantity=float(b[1]))
            for b in raw.get("bids", raw.get("asks", [])) if len(b) >= 2
        ]
        # Re-fetch asks properly
        asks = [
            OrderBookLevel(price=float(a[0]), quantity=float(a[1]))
            for a in raw.get("asks", []) if len(a) >= 2
        ]
        # Fix bids - use 'bids' key
        bids = [
            OrderBookLevel(price=float(b[0]), quantity=float(b[1]))
            for b in raw.get("bids", []) if len(b) >= 2
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
        if self._is_futures():
            contract = self._normalize_currency_pair(symbol)
            params: Dict[str, Any] = {"contract": contract, "interval": interval, "limit": limit}
            if before_time:
                params["to"] = before_time
            raw = await self._request("GET", "/api/v4/futures/usdt/candlesticks", params=params, signed=False)
        else:
            pair = self._normalize_currency_pair(symbol)
            params = {"currency_pair": pair, "interval": interval, "limit": limit}
            if before_time:
                params["to"] = before_time
            raw = await self._request("GET", "/api/v4/spot/candlesticks", params=params, signed=False)

        klines: List[Dict[str, Any]] = []
        if isinstance(raw, list):
            for candle in raw:
                if not isinstance(candle, dict):
                    continue
                klines.append({
                    "time": int(candle.get("t", candle.get("timestamp", 0))),
                    "open": float(candle.get("o", candle.get("open", 0))),
                    "high": float(candle.get("h", candle.get("high", 0))),
                    "low": float(candle.get("l", candle.get("low", 0))),
                    "close": float(candle.get("c", candle.get("close", 0))),
                    "volume": float(candle.get("v", candle.get("volume", 0))),
                })
        klines.sort(key=lambda x: x["time"])
        return klines[:limit]

    async def health_check(self) -> bool:
        try:
            if self._is_futures():
                await self._request("GET", "/api/v4/futures/usdt/time", signed=False)
            else:
                await self._request("GET", "/api/v4/spot/time", signed=False)
            return True
        except Exception:
            return False
