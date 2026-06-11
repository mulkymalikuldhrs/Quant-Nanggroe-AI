"""Bybit Exchange Client — Bybit V5 REST API."""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any, Dict, List, Optional

from quant_nanggroe.exchange.clients.base_rest_client import (
    BaseRestClient,
    BalanceInfo,
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


class BybitClient(BaseRestClient):
    """Bybit V5 REST API client.

    Supports Spot, Linear Futures, and Inverse Futures.
    Uses the unified V5 API endpoints.
    """

    exchange_id = "bybit"
    capabilities = (
        ExchangeCapability.SPOT
        | ExchangeCapability.FUTURES
        | ExchangeCapability.PERPETUALS
        | ExchangeCapability.WEBSOCKET
    )

    BASE_URL = "https://api.bybit.com"
    TESTNET_URL = "https://api-testnet.bybit.com"

    def __init__(self, config: RestClientConfig) -> None:
        config.base_url = config.base_url or self.BASE_URL
        super().__init__(config)
        self._base_url = self.TESTNET_URL if config.testnet else self.BASE_URL

    def _sign_v5(self, params: Dict[str, Any], timestamp: int) -> Dict[str, str]:
        """Sign request using Bybit V5 auth method."""
        recv_window = "5000"
        param_str = str(timestamp) + self._config.api_key + recv_window + "&".join(
            f"{k}={v}" for k, v in sorted(params.items())
        )
        signature = hmac.new(
            self._config.api_secret.encode(),
            param_str.encode(),
            hashlib.sha256,
        ).hexdigest()

        return {
            "X-BAPI-API-KEY": self._config.api_key,
            "X-BAPI-SIGN": signature,
            "X-BAPI-SIGN-TYPE": "2",
            "X-BAPI-TIMESTAMP": str(timestamp),
            "X-BAPI-RECV-WINDOW": recv_window,
        }

    async def _v5_request(
        self, method: str, endpoint: str, params: Optional[Dict] = None, signed: bool = False
    ) -> Dict[str, Any]:
        """Make a V5 API request."""
        import httpx

        await self._rate_limit()
        params = params or {}
        url = f"{self._base_url}{endpoint}"

        headers: Dict[str, str] = {}
        if signed and self._config.api_key:
            timestamp = int(time.time() * 1000)
            headers = self._sign_v5(params, timestamp)

        async with httpx.AsyncClient(timeout=self._config.timeout) as client:
            fn = getattr(client, method.lower())
            if method.upper() == "GET":
                response = await fn(url, params=params, headers=headers)
            else:
                response = await fn(url, json=params, headers=headers)
            response.raise_for_status()
            data = response.json()

            if data.get("retCode", 0) != 0:
                raise ValueError(f"Bybit error: {data.get('retMsg', 'unknown')}")

            return data.get("result", {})

    async def place_order(self, order: OrderRequest) -> OrderResult:
        """Place order on Bybit V5."""
        params: Dict[str, Any] = {
            "category": "linear" if self._is_futures_symbol(order.symbol) else "spot",
            "symbol": order.symbol,
            "side": order.side.capitalize(),
            "orderType": order.order_type.capitalize(),
            "qty": str(order.quantity),
        }

        if order.price:
            params["price"] = str(order.price)
        if order.stop_price:
            params["triggerPrice"] = str(order.stop_price)
        if order.time_in_force:
            params["timeInForce"] = order.time_in_force
        if order.reduce_only:
            params["reduceOnly"] = True
        if order.leverage:
            # Set leverage first
            try:
                await self._v5_request(
                    "POST", "/v5/position/set-leverage",
                    params={"category": "linear", "symbol": order.symbol, "buyLeverage": str(order.leverage), "sellLeverage": str(order.leverage)},
                    signed=True,
                )
            except Exception:
                logger.exception("unhandled_error")
                pass

        data = await self._v5_request("POST", "/v5/order/create", params=params, signed=True)

        return OrderResult(
            order_id=str(data.get("orderId", "")),
            client_order_id=data.get("orderLinkId", ""),
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            status="NEW",
            price=order.price or 0.0,
            quantity=order.quantity,
        )

    def _is_futures_symbol(self, symbol: str) -> bool:
        return not "/" in symbol and symbol.endswith("USDT")

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel order on Bybit."""
        try:
            await self._v5_request(
                "POST", "/v5/order/cancel",
                params={"category": "linear", "symbol": symbol, "orderId": order_id},
                signed=True,
            )
            return True
        except Exception as exc:
            logger.warning("Bybit cancel failed: %s", exc)
            return False

    async def get_balance(self, asset: Optional[str] = None) -> List[BalanceInfo]:
        """Get account balance from Bybit."""
        params: Dict[str, Any] = {"accountType": "UNIFIED"}
        data = await self._v5_request("GET", "/v5/account/wallet-balance", params=params, signed=True)

        balances = []
        for account in data.get("account", []):
            for coin in account.get("coin", []):
                free = float(coin.get("availableToWithdraw", 0) or 0)
                used = float(coin.get("locked", 0) or 0)
                if asset and coin.get("coin") != asset:
                    continue
                if free > 0 or used > 0:
                    balances.append(BalanceInfo(
                        asset=coin.get("coin", ""),
                        free=free,
                        used=used,
                        total=float(coin.get("walletBalance", 0) or 0),
                    ))
        return balances

    async def get_positions(self, symbol: Optional[str] = None) -> List[PositionInfo]:
        """Get positions from Bybit."""
        params: Dict[str, Any] = {"category": "linear", "settleCoin": "USDT"}
        if symbol:
            params["symbol"] = symbol

        data = await self._v5_request("GET", "/v5/position/list", params=params, signed=True)

        positions = []
        for p in data.get("list", []):
            qty = float(p.get("size", 0))
            if qty == 0:
                continue
            positions.append(PositionInfo(
                symbol=p.get("symbol", ""),
                side=p.get("side", ""),
                quantity=qty,
                entry_price=float(p.get("avgPrice", 0)),
                unrealized_pnl=float(p.get("unrealisedPnl", 0)),
                leverage=int(float(p.get("leverage", 1))),
                liquidation_price=float(p.get("liqPrice", 0)),
            ))
        return positions

    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderbookData:
        """Get order book from Bybit."""
        category = "linear" if self._is_futures_symbol(symbol) else "spot"
        data = await self._v5_request(
            "GET", "/v5/market/orderbook",
            params={"category": category, "symbol": symbol, "limit": limit},
        )

        return OrderbookData(
            symbol=symbol,
            bids=[OrderbookEntry(price=float(b[0]), quantity=float(b[1])) for b in data.get("b", [])],
            asks=[OrderbookEntry(price=float(a[0]), quantity=float(a[1])) for a in data.get("a", [])],
        )

    async def get_klines(self, symbol: str, interval: str = "60", limit: int = 100) -> List[KlineBar]:
        """Get klines from Bybit."""
        category = "linear" if self._is_futures_symbol(symbol) else "spot"
        data = await self._v5_request(
            "GET", "/v5/market/kline",
            params={"category": category, "symbol": symbol, "interval": interval, "limit": limit},
        )

        from datetime import datetime, timezone
        bars = []
        for k in data.get("list", []):
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


__all__ = ["BybitClient"]
