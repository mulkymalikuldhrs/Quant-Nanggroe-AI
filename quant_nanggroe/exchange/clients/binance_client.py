"""Binance Exchange Client — Binance Spot + Futures REST API."""

from __future__ import annotations

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


class BinanceClient(BaseRestClient):
    """Binance REST API client.

    Supports both Spot and Futures trading on Binance.
    Capabilities: SPOT, FUTURES, PERPETUALS, WEBSOCKET.
    """

    exchange_id = "binance"
    capabilities = (
        ExchangeCapability.SPOT
        | ExchangeCapability.FUTURES
        | ExchangeCapability.PERPETUALS
        | ExchangeCapability.WEBSOCKET
    )

    SPOT_URL = "https://api.binance.com"
    FUTURES_URL = "https://fapi.binance.com"
    TESTNET_SPOT_URL = "https://testnet.binance.vision"
    TESTNET_FUTURES_URL = "https://testnet.binancefuture.com"

    def __init__(self, config: RestClientConfig) -> None:
        config.base_url = config.base_url or self.SPOT_URL
        super().__init__(config)
        self._spot_url = self.TESTNET_SPOT_URL if config.testnet else self.SPOT_URL
        self._futures_url = self.TESTNET_FUTURES_URL if config.testnet else self.FUTURES_URL

    def _is_futures_symbol(self, symbol: str) -> bool:
        """Check if symbol is a futures contract."""
        return symbol.endswith("USDT") and not symbol.startswith(".")

    def _get_base_url(self, symbol: str) -> str:
        """Get base URL based on symbol type."""
        return self._futures_url if self._is_futures_symbol(symbol) else self._spot_url

    async def place_order(self, order: OrderRequest) -> OrderResult:
        """Place order on Binance."""
        base_url = self._get_base_url(order.symbol)
        endpoint = "/fapi/v1/order" if self._is_futures_symbol(order.symbol) else "/api/v3/order"

        params: Dict[str, Any] = {
            "symbol": order.symbol,
            "side": order.side.upper(),
            "type": order.order_type.upper(),
            "quantity": str(order.quantity),
        }

        if order.price:
            params["price"] = str(order.price)
        if order.stop_price:
            params["stopPrice"] = str(order.stop_price)
        if order.time_in_force:
            params["timeInForce"] = order.time_in_force
        if order.reduce_only:
            params["reduceOnly"] = "true"
        if order.leverage:
            # Set leverage first for futures
            try:
                await self._request(
                    "POST",
                    f"{self._futures_url}/fapi/v1/leverage",
                    params={"symbol": order.symbol, "leverage": str(order.leverage)},
                    signed=True,
                )
            except Exception:
                logger.exception("unhandled_error")
                pass
        if order.client_order_id:
            params["newClientOrderId"] = order.client_order_id

        data = await self._request("POST", f"{base_url}{endpoint}", params=params, signed=True)

        return OrderResult(
            order_id=str(data.get("orderId", "")),
            client_order_id=data.get("clientOrderId", ""),
            symbol=data.get("symbol", order.symbol),
            side=data.get("side", order.side),
            order_type=data.get("type", order.order_type),
            status=data.get("status", ""),
            price=float(data.get("price", 0)),
            quantity=float(data.get("origQty", 0)),
            filled_quantity=float(data.get("executedQty", 0)),
            timestamp=str(data.get("transactTime", "")),
        )

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel order on Binance."""
        base_url = self._get_base_url(symbol)
        endpoint = "/fapi/v1/order" if self._is_futures_symbol(symbol) else "/api/v3/order"

        try:
            await self._request(
                "DELETE",
                f"{base_url}{endpoint}",
                params={"symbol": symbol, "orderId": order_id},
                signed=True,
            )
            return True
        except Exception as exc:
            logger.warning("Binance cancel order failed: %s", exc)
            return False

    async def get_balance(self, asset: Optional[str] = None) -> List[BalanceInfo]:
        """Get account balance from Binance."""
        # Spot balance
        spot_data = await self._request(
            "GET", f"{self._spot_url}/api/v3/account", signed=True
        )

        balances = []
        for b in spot_data.get("balances", []):
            free = float(b.get("free", 0))
            used = float(b.get("locked", 0))
            if asset and b["asset"] != asset:
                continue
            if free > 0 or used > 0:
                balances.append(BalanceInfo(
                    asset=b["asset"],
                    free=free,
                    used=used,
                    total=free + used,
                ))

        # Futures balance
        try:
            futures_data = await self._request(
                "GET", f"{self._futures_url}/fapi/v2/balance", signed=True
            )
            for b in futures_data if isinstance(futures_data, list) else []:
                free = float(b.get("availableBalance", 0))
                if asset and b.get("asset") != asset:
                    continue
                if free > 0:
                    balances.append(BalanceInfo(
                        asset=b.get("asset", "USDT"),
                        free=free,
                        used=float(b.get("balance", 0)) - free,
                        total=float(b.get("balance", 0)),
                    ))
        except Exception:
            logger.exception("unhandled_error")
            pass

        return balances

    async def get_positions(self, symbol: Optional[str] = None) -> List[PositionInfo]:
        """Get futures positions from Binance."""
        params: Dict[str, Any] = {}
        if symbol:
            params["symbol"] = symbol

        data = await self._request(
            "GET", f"{self._futures_url}/fapi/v2/positionRisk", params=params, signed=True
        )

        positions = []
        for p in data if isinstance(data, list) else []:
            qty = float(p.get("positionAmt", 0))
            if qty == 0:
                continue
            positions.append(PositionInfo(
                symbol=p.get("symbol", ""),
                side="LONG" if qty > 0 else "SHORT",
                quantity=abs(qty),
                entry_price=float(p.get("entryPrice", 0)),
                unrealized_pnl=float(p.get("unRealizedProfit", 0)),
                leverage=int(float(p.get("leverage", 1))),
                liquidation_price=float(p.get("liquidationPrice", 0)),
            ))
        return positions

    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderbookData:
        """Get order book from Binance."""
        base_url = self._get_base_url(symbol)
        endpoint = "/fapi/v1/depth" if self._is_futures_symbol(symbol) else "/api/v3/depth"

        data = await self._request(
            "GET", f"{base_url}{endpoint}", params={"symbol": symbol, "limit": limit}
        )

        return OrderbookData(
            symbol=symbol,
            bids=[OrderbookEntry(price=float(b[0]), quantity=float(b[1])) for b in data.get("bids", [])],
            asks=[OrderbookEntry(price=float(a[0]), quantity=float(a[1])) for a in data.get("asks", [])],
            timestamp=str(int(time.time() * 1000)),
        )

    async def get_klines(
        self, symbol: str, interval: str = "1h", limit: int = 100
    ) -> List[KlineBar]:
        """Get klines from Binance."""
        base_url = self._get_base_url(symbol)
        endpoint = "/fapi/v1/klines" if self._is_futures_symbol(symbol) else "/api/v3/klines"

        data = await self._request(
            "GET", f"{base_url}{endpoint}",
            params={"symbol": symbol, "interval": interval, "limit": limit},
        )

        bars = []
        for k in data if isinstance(data, list) else []:
            if len(k) >= 6:
                from datetime import datetime, timezone
                bars.append(KlineBar(
                    timestamp=datetime.fromtimestamp(k[0] / 1000, tz=timezone.utc).isoformat(),
                    open=float(k[1]),
                    high=float(k[2]),
                    low=float(k[3]),
                    close=float(k[4]),
                    volume=float(k[5]),
                ))
        return bars


__all__ = ["BinanceClient"]
