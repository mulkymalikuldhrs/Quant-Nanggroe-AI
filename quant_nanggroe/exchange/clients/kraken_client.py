"""Kraken REST Client — Spot + Futures.

Supports Kraken spot trading with HMAC-SHA512 request signing
and optional Kraken Futures (Deribit) support.

API docs: https://docs.kraken.com/rest/
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


class KrakenClient(BaseRestClient):
    """Kraken Spot REST client.

    Auth:
    - API-Key: api key string
    - API-Sign: base64(hmac_sha512(base64_decode(secret), uri_path + sha256(nonce + postdata)))
    """

    _default_base_url = "https://api.kraken.com"

    def __init__(self, config: ExchangeConfig) -> None:
        super().__init__(config)
        self._default_base_url = config.options.get(
            "base_url", "https://api.kraken.com"
        )
        self._api_key = config.api_key or ""
        self._api_secret = config.api_secret or ""
        try:
            self._secret_bytes = base64.b64decode(self._api_secret) if self._api_secret else b""
        except Exception:
            self._secret_bytes = b""

    @property
    def name(self) -> str:
        return "kraken"

    @property
    def capabilities(self) -> ClientCapabilities:
        return ClientCapabilities(
            spot=True,
            futures=True,
            perps=False,
            margin=True,
            websocket=True,
            max_leverage=50.0,
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
        nonce = str(int(time.time() * 1000))
        post_data = body or ""
        # Prepend nonce to body for signing
        if post_data:
            post_data = f"nonce={nonce}&{post_data}"
        else:
            post_data = f"nonce={nonce}"

        sha = hashlib.sha256((nonce + post_data).encode("utf-8")).digest()
        mac = hmac.new(
            self._secret_bytes,
            path.encode("utf-8") + sha,
            hashlib.sha512,
        ).digest()
        sign = base64.b64encode(mac).decode("utf-8")

        h = dict(headers or {})
        h.update({
            "API-Key": self._api_key,
            "API-Sign": sign,
            "Content-Type": "application/x-www-form-urlencoded",
        })
        return h, params, post_data

    def _handle_error_response(self, status_code: int, data: Dict[str, Any], text: str) -> None:
        if status_code >= 400:
            raise ExchangeError(f"Kraken HTTP {status_code}: {text[:300]}", exchange=self.name)
        if isinstance(data, dict):
            errs = data.get("error")
            if isinstance(errs, list) and errs:
                raise ExchangeError(f"Kraken API error: {errs}", exchange=self.name)

    # ----- Helpers -----

    @staticmethod
    def _normalize_pair(symbol: str) -> str:
        return symbol.replace("/", "").replace("-", "").upper()

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
        pair = self._normalize_pair(symbol)
        sd = side.value.lower()
        ot = "market" if order_type == OrderType.MARKET else "limit"

        body_parts = [
            f"pair={pair}",
            f"type={sd}",
            f"ordertype={ot}",
            f"volume={quantity}",
        ]
        if ot == "limit" and price:
            body_parts.append(f"price={price}")
        if client_order_id:
            digits = "".join(c for c in str(client_order_id) if c.isdigit())[:9]
            if digits:
                body_parts.append(f"userref={digits}")

        body_str = "&".join(body_parts)

        try:
            raw = await self._request(
                "POST", "/0/private/AddOrder", body=body_str, signed=True,
            )
        except ExchangeError as exc:
            raise OrderError(str(exc), exchange=self.name, original=exc)

        txid = ""
        result = raw.get("result", {}) if isinstance(raw, dict) else {}
        tx = result.get("txid", [])
        if isinstance(tx, list) and tx:
            txid = str(tx[0])

        return Order(
            id=txid,
            client_order_id=client_order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            status=OrderStatus.SUBMITTED,
            broker_id="kraken",
            broker_order_id=txid,
            strategy_name=strategy_name,
            agent_name=agent_name,
            notes=notes,
        )

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        body_str = f"txid={order_id}"
        await self._request("POST", "/0/private/CancelOrder", body=body_str, signed=True)
        return Order(
            id=order_id, symbol=symbol or "",
            side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=0.0,
            status=OrderStatus.CANCELED, broker_id="kraken", broker_order_id=order_id,
        )

    async def get_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        body_str = f"txid={order_id}"
        raw = await self._request("POST", "/0/private/QueryOrders", body=body_str, signed=True)
        result = raw.get("result", {}) if isinstance(raw, dict) else {}
        od = result.get(str(order_id), {}) if isinstance(result, dict) else {}

        status_map = {
            "open": OrderStatus.SUBMITTED, "closed": OrderStatus.FILLED,
            "canceled": OrderStatus.CANCELED, "expired": OrderStatus.EXPIRED,
        }
        side_map = {"buy": OrderSide.BUY, "sell": OrderSide.SELL}

        return Order(
            id=order_id,
            symbol=symbol or "",
            side=side_map.get(str(od.get("descr", {}).get("type", "")).lower(), OrderSide.BUY),
            order_type=OrderType.MARKET,
            quantity=float(od.get("vol", 0)),
            price=float(od.get("descr", {}).get("price", 0)) or None,
            status=status_map.get(str(od.get("status", "")), OrderStatus.SUBMITTED),
            filled_quantity=float(od.get("vol_exec", 0)),
            broker_id="kraken",
            broker_order_id=order_id,
        )

    # ----- Account -----

    async def get_balance(self) -> Dict[str, float]:
        raw = await self._request("POST", "/0/private/Balance", body="", signed=True)
        result = raw.get("result", {}) if isinstance(raw, dict) else {}
        balances: Dict[str, float] = {}
        if isinstance(result, dict):
            for asset, bal in result.items():
                try:
                    val = float(bal)
                    if val > 0:
                        balances[asset] = val
                except (ValueError, TypeError):
                    pass
        return balances

    async def get_positions(self) -> List[Position]:
        # Kraken spot doesn't have traditional positions
        return []

    # ----- Market data -----

    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
        pair = self._normalize_pair(symbol)
        params = {"pair": pair, "count": limit}
        raw = await self._request("GET", "/0/public/Depth", params=params, signed=False)

        result = raw.get("result", {}) if isinstance(raw, dict) else {}
        # Kraken wraps result with the pair name
        pair_data = result.get(pair, result) if isinstance(result, dict) else {}

        bids = [
            OrderBookLevel(price=float(b[0]), quantity=float(b[1]))
            for b in pair_data.get("bids", []) if len(b) >= 2
        ]
        asks = [
            OrderBookLevel(price=float(a[0]), quantity=float(a[1]))
            for a in pair_data.get("asks", []) if len(a) >= 2
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
        pair = self._normalize_pair(symbol)
        interval_map = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440, "1w": 10080}
        minutes = interval_map.get(interval, 60)

        params: Dict[str, Any] = {"pair": pair, "interval": minutes}
        if before_time:
            params["since"] = before_time
        if limit:
            params["count"] = limit

        raw = await self._request("GET", "/0/public/OHLC", params=params, signed=False)
        result = raw.get("result", {}) if isinstance(raw, dict) else {}
        pair_data = result.get(pair, result) if isinstance(result, dict) else {}

        klines: List[Dict[str, Any]] = []
        if isinstance(pair_data, list):
            for candle in pair_data:
                if not isinstance(candle, list) or len(candle) < 7:
                    continue
                klines.append({
                    "time": int(candle[0]),
                    "open": float(candle[1]),
                    "high": float(candle[2]),
                    "low": float(candle[3]),
                    "close": float(candle[4]),
                    "volume": float(candle[6]),
                })
        klines.sort(key=lambda x: x["time"])
        return klines

    async def health_check(self) -> bool:
        try:
            data = await self._request("GET", "/0/public/Time", signed=False)
            errs = data.get("error") if isinstance(data, dict) else []
            return isinstance(errs, list) and len(errs) == 0
        except Exception:
            return False
