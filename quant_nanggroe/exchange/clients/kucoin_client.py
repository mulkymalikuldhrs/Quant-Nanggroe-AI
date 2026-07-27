"""KuCoin REST Client — Spot + USDT Futures.

Supports KuCoin V2 API with HMAC-SHA256 + Base64 request signing
(including signed passphrase) for both spot and futures markets.

API docs: https://www.kucoin.com/docs-rest/
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


class KuCoinClient(BaseRestClient):
    """KuCoin Spot + Futures REST client.

    Signing (V2):
    - KC-API-SIGN = base64(hmac_sha256(secret, timestamp + method + requestPath + body))
    - KC-API-PASSPHRASE = base64(hmac_sha256(secret, passphrase))
    """

    _default_base_url = "https://api.kucoin.com"

    def __init__(self, config: ExchangeConfig) -> None:
        super().__init__(config)
        self._market_type = config.options.get("market_type", "spot")
        if self._market_type == "futures":
            self._default_base_url = config.options.get(
                "base_url", "https://api-futures.kucoin.com"
            )
        else:
            self._default_base_url = config.options.get(
                "base_url", "https://api.kucoin.com"
            )
        self._api_key = config.api_key or ""
        self._api_secret = config.api_secret or ""
        self._passphrase = config.passphrase or ""

    @property
    def name(self) -> str:
        return "kucoin"

    @property
    def capabilities(self) -> ClientCapabilities:
        return ClientCapabilities(
            spot=True,
            futures=True,
            perps=True,
            margin=True,
            websocket=True,
            max_leverage=100.0,
            requires_passphrase=True,
        )

    # ----- Signing -----

    def _b64_hmac_sha256(self, key: str, msg: str) -> str:
        mac = hmac.new(key.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).digest()
        return base64.b64encode(mac).decode("utf-8")

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
        sign = self._b64_hmac_sha256(self._api_secret, prehash)
        passphrase_signed = self._b64_hmac_sha256(self._api_secret, self._passphrase)

        h = dict(headers or {})
        h.update({
            "KC-API-KEY": self._api_key,
            "KC-API-SIGN": sign,
            "KC-API-TIMESTAMP": ts_ms,
            "KC-API-PASSPHRASE": passphrase_signed,
            "KC-API-KEY-VERSION": "2",
            "Content-Type": "application/json",
        })
        return h, params, body

    def _handle_error_response(self, status_code: int, data: Dict[str, Any], text: str) -> None:
        if status_code >= 400:
            code = data.get("code", "") if isinstance(data, dict) else ""
            msg = data.get("msg", "") if isinstance(data, dict) else ""
            raise ExchangeError(
                f"KuCoin HTTP {status_code} (code={code}): {msg or text[:300]}",
                exchange=self.name,
            )

    # ----- Helpers -----

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        return symbol.replace("/", "-").upper()

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
        sym = self._normalize_symbol(symbol)
        sd = side.value.lower()
        cid = client_order_id or str(self._now_ms())

        body: Dict[str, Any] = {
            "clientOid": cid,
            "side": sd,
            "symbol": sym,
            "type": "market" if order_type == OrderType.MARKET else "limit",
        }

        if order_type == OrderType.MARKET:
            if sd == "buy":
                body["funds"] = str(quantity)
            else:
                body["size"] = str(quantity)
        else:
            body["size"] = str(quantity)
            body["price"] = str(price or 0)
            body["timeInForce"] = "GTC"

        path = "/api/v1/orders"

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
            broker_id="kucoin",
            broker_order_id=order_id,
            strategy_name=strategy_name,
            agent_name=agent_name,
            notes=notes,
        )

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        path = f"/api/v1/orders/{order_id}"
        await self._request("DELETE", path, signed=True)
        return Order(
            id=order_id, symbol=symbol or "",
            side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=0.0,
            status=OrderStatus.CANCELED, broker_id="kucoin", broker_order_id=order_id,
        )

    async def get_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        path = f"/api/v1/orders/{order_id}"
        raw = await self._request("GET", path, signed=True)
        data = raw.get("data", {}) if isinstance(raw, dict) else {}
        od = data if isinstance(data, dict) else {}

        status_map = {
            "active": OrderStatus.SUBMITTED, "done": OrderStatus.FILLED,
            "canceled": OrderStatus.CANCELED, "cancelled": OrderStatus.CANCELED,
        }
        side_map = {"buy": OrderSide.BUY, "sell": OrderSide.SELL}

        is_active = od.get("isActive")
        status = OrderStatus.SUBMITTED if is_active else OrderStatus.FILLED

        return Order(
            id=str(od.get("id", order_id)),
            symbol=str(od.get("symbol", symbol or "")),
            side=side_map.get(str(od.get("side", "")).lower(), OrderSide.BUY),
            order_type=OrderType.MARKET,
            quantity=float(od.get("size", 0)),
            price=float(od.get("price", 0)) or None,
            status=status_map.get(str(od.get("status", "")), status),
            filled_quantity=float(od.get("dealSize", 0)),
            broker_id="kucoin",
            broker_order_id=str(od.get("id", order_id)),
        )

    # ----- Account -----

    async def get_balance(self) -> Dict[str, float]:
        if self._is_futures():
            raw = await self._request(
                "GET", "/api/v1/account-overview",
                params={"currency": "USDT"}, signed=True,
            )
            data = raw.get("data", {}) if isinstance(raw, dict) else {}
            balances: Dict[str, float] = {}
            if isinstance(data, dict):
                avail = float(data.get("availableBalance", 0))
                if avail > 0:
                    balances["USDT"] = avail
            return balances

        raw = await self._request("GET", "/api/v1/accounts", signed=True)
        data = raw.get("data", []) if isinstance(raw, dict) else []
        balances: Dict[str, float] = {}
        if isinstance(data, list):
            for acct in data:
                if isinstance(acct, dict):
                    ccy = str(acct.get("currency", ""))
                    avail = float(acct.get("available", 0))
                    if avail > 0:
                        balances[ccy] = avail
        return balances

    async def get_positions(self) -> List[Position]:
        if not self._is_futures():
            return []
        raw = await self._request("GET", "/api/v1/positions", signed=True)
        data = raw.get("data", []) if isinstance(raw, dict) else []
        positions: List[Position] = []
        if isinstance(data, list):
            for p in data:
                if not isinstance(p, dict):
                    continue
                qty = float(p.get("currentQty", 0))
                if qty == 0:
                    continue
                side = PositionSide.LONG if qty > 0 else PositionSide.SHORT
                entry = float(p.get("avgEntryPrice", 0))
                mark = float(p.get("markPrice", 0))
                positions.append(Position(
                    symbol=str(p.get("symbol", "")),
                    side=side,
                    quantity=abs(qty),
                    entry_price=entry,
                    current_price=mark,
                    cost_basis=abs(qty) * entry,
                    unrealized_pnl=float(p.get("unrealisedPnl", 0)),
                    broker_id="kucoin",
                ))
        return positions

    # ----- Market data -----

    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
        sym = self._normalize_symbol(symbol)
        params = {"symbol": sym, "limit": limit}
        raw = await self._request("GET", "/api/v1/market/orderbook/level2_20", params=params, signed=False)

        data = raw.get("data", {}) if isinstance(raw, dict) else {}
        bids = [
            OrderBookLevel(price=float(b[0]), quantity=float(b[1]))
            for b in data.get("bids", []) if len(b) >= 2
        ]
        asks = [
            OrderBookLevel(price=float(a[0]), quantity=float(a[1]))
            for a in data.get("asks", []) if len(a) >= 2
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
        params: Dict[str, Any] = {"symbol": sym, "type": interval}
        if before_time:
            params["endAt"] = before_time
        params["limit"] = min(limit, 200)

        raw = await self._request("GET", "/api/v1/market/candles", params=params, signed=False)
        data = raw.get("data", []) if isinstance(raw, dict) else []

        klines: List[Dict[str, Any]] = []
        if isinstance(data, list):
            for candle in data:
                if not isinstance(candle, list) or len(candle) < 7:
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
            data = await self._request("GET", "/api/v1/timestamp", signed=False)
            code = str(data.get("code", "")) if isinstance(data, dict) else ""
            return code in ("200000", "0", "")
        except Exception:
            return False
