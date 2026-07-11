"""OKX Exchange Client — OKX V5 REST API."""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import time
from typing import Any, Dict, List, Optional

from quant_nanggroe.exchange.clients.base_rest_client import (
    BalanceInfo,
    BaseRestClient,
    ExchangeCapability,
    KlineBar,
    OrderbookData,
    OrderbookEntry,
    OrderRequest,
    OrderResult,
    PositionInfo,
    RestClientConfig,
)

logger = logging.getLogger(__name__)


class OKXClient(BaseRestClient):
    """OKX V5 REST API client.

    Supports Spot, Futures, Perpetuals, Options, and Margin trading.
    Uses the unified V5 API endpoints.
    """

    exchange_id = "okx"
    capabilities = (
        ExchangeCapability.SPOT
        | ExchangeCapability.FUTURES
        | ExchangeCapability.PERPETUALS
        | ExchangeCapability.MARGIN
        | ExchangeCapability.WEBSOCKET
    )

    BASE_URL = "https://www.okx.com"
    TESTNET_URL = "https://www.okx.com"  # OKX uses same URL with flag

    def __init__(self, config: RestClientConfig) -> None:
        config.base_url = config.base_url or self.BASE_URL
        super().__init__(config)

    def _sign_okx(self, timestamp: str, method: str, path: str, body: str = "") -> str:
        """Sign OKX request with HMAC-SHA256 + Base64."""
        message = timestamp + method + path + body
        mac = hmac.new(
            self._config.api_secret.encode(),
            message.encode(),
            hashlib.sha256,
        )
        return base64.b64encode(mac.digest()).decode()

    def _get_headers(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        """Get signed headers for OKX API."""
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
        sign = self._sign_okx(timestamp, method, path, body)

        return {
            "OK-ACCESS-KEY": self._config.api_key,
            "OK-ACCESS-SIGN": sign,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self._config.passphrase,
            "Content-Type": "application/json",
        }

    async def _okx_request(
        self, method: str, endpoint: str, params: Optional[Dict] = None, signed: bool = False
    ) -> Any:
        """Make an OKX V5 API request."""
        import httpx

        await self._rate_limit()
        params = params or {}
        url = f"{self._config.base_url}{endpoint}"

        headers: Dict[str, str] = {"Content-Type": "application/json"}

        if method.upper() == "GET":
            query = "&".join(f"{k}={v}" for k, v in params.items())
            path = f"{endpoint}?{query}" if query else endpoint
            if signed:
                headers = self._get_headers("GET", path)
            async with httpx.AsyncClient(timeout=self._config.timeout) as client:
                response = await client.get(url, params=params, headers=headers)
        else:
            import json
            body = json.dumps(params) if params else ""
            if signed:
                headers = self._get_headers("POST", endpoint, body)
            async with httpx.AsyncClient(timeout=self._config.timeout) as client:
                response = await client.post(url, content=body, headers=headers)

        response.raise_for_status()
        data = response.json()

        if data.get("code", "0") != "0":
            raise ValueError(f"OKX error: {data.get('msg', 'unknown')}")

        return data.get("data", [])

    def _get_inst_type(self, symbol: str) -> str:
        """Determine instrument type from symbol."""
        if "-" in symbol:
            return "SWAP" if "SWAP" in symbol.upper() else "FUTURES"
        return "SPOT"

    async def place_order(self, order: OrderRequest) -> OrderResult:
        """Place order on OKX."""
        inst_type = self._get_inst_type(order.symbol)
        params: Dict[str, Any] = {
            "instId": order.symbol,
            "tdMode": "cross" if inst_type != "SPOT" else "cash",
            "side": order.side.lower(),
            "ordType": order.order_type.lower(),
            "sz": str(order.quantity),
        }

        if order.price:
            params["px"] = str(order.price)
        if order.client_order_id:
            params["clOrdId"] = order.client_order_id

        data = await self._okx_request("POST", "/api/v5/trade/order", params=params, signed=True)

        if data:
            return OrderResult(
                order_id=data[0].get("ordId", ""),
                client_order_id=data[0].get("clOrdId", ""),
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                status="NEW",
                price=order.price or 0.0,
                quantity=order.quantity,
            )

        return OrderResult(symbol=order.symbol, side=order.side)

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel order on OKX."""
        try:
            await self._okx_request(
                "POST", "/api/v5/trade/cancel-order",
                params={"instId": symbol, "ordId": order_id},
                signed=True,
            )
            return True
        except Exception as exc:
            logger.warning("OKX cancel failed: %s", exc)
            return False

    async def get_balance(self, asset: Optional[str] = None) -> List[BalanceInfo]:
        """Get account balance from OKX."""
        data = await self._okx_request("GET", "/api/v5/account/balance", signed=True)

        balances = []
        for account in data:
            for detail in account.get("details", []):
                ccy = detail.get("ccy", "")
                if asset and ccy != asset:
                    continue
                free = float(detail.get("availBal", 0) or 0)
                used = float(detail.get("frozenBal", 0) or 0)
                if free > 0 or used > 0:
                    balances.append(BalanceInfo(
                        asset=ccy,
                        free=free,
                        used=used,
                        total=float(detail.get("eq", 0) or 0),
                    ))
        return balances

    async def get_positions(self, symbol: Optional[str] = None) -> List[PositionInfo]:
        """Get positions from OKX."""
        params: Dict[str, Any] = {}
        if symbol:
            params["instId"] = symbol

        data = await self._okx_request("GET", "/api/v5/account/positions", params=params, signed=True)

        positions = []
        for p in data:
            qty = float(p.get("pos", 0))
            if qty == 0:
                continue
            positions.append(PositionInfo(
                symbol=p.get("instId", ""),
                side="LONG" if qty > 0 else "SHORT",
                quantity=abs(qty),
                entry_price=float(p.get("avgPx", 0)),
                unrealized_pnl=float(p.get("upl", 0)),
                leverage=int(float(p.get("lever", 1))),
                liquidation_price=float(p.get("liqPx", 0)),
            ))
        return positions

    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderbookData:
        """Get order book from OKX."""
        data = await self._okx_request(
            "GET", "/api/v5/market/books",
            params={"instId": symbol, "sz": str(limit)},
        )

        if not data:
            return OrderbookData(symbol=symbol)

        book = data[0]
        return OrderbookData(
            symbol=symbol,
            bids=[OrderbookEntry(price=float(b[0]), quantity=float(b[1])) for b in book.get("bids", [])],
            asks=[OrderbookEntry(price=float(a[0]), quantity=float(a[1])) for a in book.get("asks", [])],
        )

    async def get_klines(self, symbol: str, interval: str = "1H", limit: int = 100) -> List[KlineBar]:
        """Get klines from OKX."""
        data = await self._okx_request(
            "GET", "/api/v5/market/candles",
            params={"instId": symbol, "bar": interval, "limit": str(limit)},
        )

        from datetime import datetime, timezone
        bars = []
        for k in data:
            if len(k) >= 6:
                bars.append(KlineBar(
                    timestamp=datetime.fromtimestamp(int(k[0]) / 1000, tz=timezone.utc).isoformat(),
                    open=float(k[1]),
                    high=float(k[2]),
                    low=float(k[3]),
                    close=float(k[4]),
                    volume=float(k[5]),
                ))
        return bars


__all__ = ["OKXClient"]
