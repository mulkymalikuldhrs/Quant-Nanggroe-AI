"""Binance data provider.

Uses the ccxt library for Binance market data access and direct Binance
REST API for futures-specific data (funding rates, open interest).
Supports crypto spot and futures markets. No API key needed for public data.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import ccxt.async_support as ccxt
import httpx

from quant_nanggroe.data.providers.base import DataProvider
from quant_nanggroe.types.market import OHLCV, OrderBook, OrderBookLevel, Ticker, TimeFrame

logger = logging.getLogger(__name__)

TIMEFRAME_MAP = {
    TimeFrame.M1: "1m",
    TimeFrame.M5: "5m",
    TimeFrame.M15: "15m",
    TimeFrame.M30: "30m",
    TimeFrame.H1: "1h",
    TimeFrame.H4: "4h",
    TimeFrame.D1: "1d",
    TimeFrame.W1: "1w",
    TimeFrame.MO1: "1M",
}

# Binance API base URLs
BINANCE_SPOT_API = "https://api.binance.com"
BINANCE_FUTURES_API = "https://fapi.binance.com"


class BinanceProvider(DataProvider):
    """Binance data provider using ccxt + direct REST API.

    Provides real-time and historical data for crypto markets.
    Requires API key for private endpoints; public data works without key.
    Priority: 1 (primary for crypto).

    Features:
    - Real OHLCV data via ccxt
    - Real order book depth via ccxt
    - Real ticker prices via ccxt
    - Real 24h volume data
    - Real funding rates for futures (direct API)
    - Real open interest data (direct API)
    - Auto rate-limit handling
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: bool = False,
        **kwargs,
    ):
        super().__init__(name="binance", priority=1, **kwargs)
        self._exchange = ccxt.binance({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        })
        if testnet:
            self._exchange.set_sandbox_mode(True)
        self._http_client: Optional[httpx.AsyncClient] = None
        self._last_request_time: float = 0.0
        self._rate_limit_interval: float = 0.1  # 100ms = 10 req/s

    def _get_http_client(self) -> httpx.AsyncClient:
        """Lazy-initialize the HTTP client for direct API calls."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def _rate_limited_get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make a rate-limited GET request to Binance API.

        Args:
            url: Full URL to request.
            params: Optional query parameters.

        Returns:
            Parsed JSON response.
        """
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self._rate_limit_interval:
            await asyncio.sleep(self._rate_limit_interval - elapsed)

        client = self._get_http_client()
        self._last_request_time = time.monotonic()

        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.D1,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[OHLCV]:
        """Fetch OHLCV data from Binance via ccxt."""
        try:
            interval = TIMEFRAME_MAP.get(timeframe, "1d")
            since = int(start.timestamp() * 1000) if start else None
            ohlcv_data = await self._exchange.fetch_ohlcv(
                symbol, interval, since=since, limit=limit
            )

            # Filter by end date if specified
            end_ms = int(end.timestamp() * 1000) if end else None

            result = []
            for candle in ohlcv_data:
                if end_ms and candle[0] > end_ms:
                    continue
                ohlcv = OHLCV(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(candle[0] / 1000),
                    open=float(candle[1]),
                    high=float(candle[2]),
                    low=float(candle[3]),
                    close=float(candle[4]),
                    volume=float(candle[5]),
                )
                result.append(ohlcv)

            self.mark_success()
            return result

        except Exception as e:
            self.mark_error(str(e))
            logger.warning(f"Binance OHLCV error for {symbol}: {e}")
            return []

    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Fetch current ticker from Binance via ccxt."""
        try:
            data = await self._exchange.fetch_ticker(symbol)
            t = Ticker(
                symbol=symbol,
                timestamp=datetime.now(),
                last_price=float(data.get("last", 0)),
                bid=float(data["bid"]) if data.get("bid") else None,
                ask=float(data["ask"]) if data.get("ask") else None,
                high_24h=float(data["high"]) if data.get("high") else None,
                low_24h=float(data["low"]) if data.get("low") else None,
                volume_24h=float(data["baseVolume"]) if data.get("baseVolume") else None,
                change_pct_24h=float(data["percentage"]) if data.get("percentage") else None,
                vwap=float(data["vwap"]) if data.get("vwap") else None,
            )
            self.mark_success()
            return t

        except Exception as e:
            self.mark_error(str(e))
            logger.warning(f"Binance ticker error for {symbol}: {e}")
            return None

    async def get_orderbook(self, symbol: str, limit: int = 20) -> Optional[OrderBook]:
        """Fetch order book from Binance via ccxt."""
        try:
            data = await self._exchange.fetch_order_book(symbol, limit=limit)
            bids = [OrderBookLevel(price=float(b[0]), quantity=float(b[1])) for b in data["bids"]]
            asks = [OrderBookLevel(price=float(a[0]), quantity=float(a[1])) for a in data["asks"]]

            spread = None
            mid_price = None
            if bids and asks:
                spread = asks[0].price - bids[0].price
                mid_price = (asks[0].price + bids[0].price) / 2

            ob = OrderBook(
                symbol=symbol,
                timestamp=datetime.now(),
                bids=bids,
                asks=asks,
                spread=spread,
                mid_price=mid_price,
            )
            self.mark_success()
            return ob

        except Exception as e:
            self.mark_error(str(e))
            logger.warning(f"Binance orderbook error for {symbol}: {e}")
            return None

    async def get_24h_tickers(self) -> Dict[str, Any]:
        """Fetch 24h price change statistics for all symbols.

        Returns:
            Dict mapping symbol to 24h ticker data (price, volume, change).
        """
        try:
            url = f"{BINANCE_SPOT_API}/api/v3/ticker/24hr"
            data = await self._rate_limited_get(url)
            self.mark_success()
            return {item["symbol"]: item for item in data}
        except Exception as e:
            self.mark_error(str(e))
            logger.warning(f"Binance 24h tickers error: {e}")
            return {}

    async def get_funding_rate(
        self,
        symbol: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Fetch funding rate history for a futures symbol.

        Uses the Binance Futures API directly. No API key required.

        Args:
            symbol: Futures symbol (e.g., 'BTCUSDT').
            start: Start datetime.
            end: End datetime.
            limit: Maximum number of records (max 1000).

        Returns:
            List of funding rate dicts with symbol, fundingRate, fundingTime.
        """
        try:
            url = f"{BINANCE_FUTURES_API}/fapi/v1/fundingRate"
            params: Dict[str, Any] = {
                "symbol": symbol,
                "limit": min(limit, 1000),
            }
            if start:
                params["startTime"] = int(start.timestamp() * 1000)
            if end:
                params["endTime"] = int(end.timestamp() * 1000)

            data = await self._rate_limited_get(url, params=params)

            result = []
            for item in data:
                result.append({
                    "symbol": item.get("symbol", ""),
                    "funding_rate": float(item.get("fundingRate", 0)),
                    "funding_time": datetime.fromtimestamp(item.get("fundingTime", 0) / 1000).isoformat(),
                    "mark_price": float(item.get("markPrice", 0)) if item.get("markPrice") else None,
                })

            self.mark_success()
            return result

        except Exception as e:
            self.mark_error(str(e))
            logger.warning(f"Binance funding rate error for {symbol}: {e}")
            return []

    async def get_open_interest(
        self,
        symbol: str,
    ) -> Dict[str, Any]:
        """Fetch current open interest for a futures symbol.

        Uses the Binance Futures API directly. No API key required.

        Args:
            symbol: Futures symbol (e.g., 'BTCUSDT').

        Returns:
            Dict with openInterest, symbol, time.
        """
        try:
            url = f"{BINANCE_FUTURES_API}/fapi/v1/openInterest"
            params: Dict[str, Any] = {"symbol": symbol}

            data = await self._rate_limited_get(url, params=params)

            result = {
                "symbol": data.get("symbol", ""),
                "open_interest": float(data.get("openInterest", 0)),
                "time": data.get("time", ""),
            }

            self.mark_success()
            return result

        except Exception as e:
            self.mark_error(str(e))
            logger.warning(f"Binance open interest error for {symbol}: {e}")
            return {}

    async def get_open_interest_hist(
        self,
        symbol: str,
        period: str = "5m",
        limit: int = 30,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch open interest history for a futures symbol.

        Args:
            symbol: Futures symbol (e.g., 'BTCUSDT').
            period: "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d".
            limit: Maximum number of records (max 500).
            start: Start datetime.
            end: End datetime.

        Returns:
            List of open interest history records.
        """
        try:
            url = f"{BINANCE_FUTURES_API}/futures/data/openInterestHist"
            params: Dict[str, Any] = {
                "symbol": symbol,
                "period": period,
                "limit": min(limit, 500),
            }
            if start:
                params["startTime"] = int(start.timestamp() * 1000)
            if end:
                params["endTime"] = int(end.timestamp() * 1000)

            data = await self._rate_limited_get(url, params=params)

            result = []
            for item in data:
                result.append({
                    "symbol": item.get("symbol", ""),
                    "sum_open_interest": float(item.get("sumOpenInterest", 0)),
                    "sum_open_interest_value": float(item.get("sumOpenInterestValue", 0)),
                    "timestamp": datetime.fromtimestamp(item.get("timestamp", 0) / 1000).isoformat(),
                })

            self.mark_success()
            return result

        except Exception as e:
            self.mark_error(str(e))
            logger.warning(f"Binance open interest history error for {symbol}: {e}")
            return []

    async def get_mark_price(
        self,
        symbol: str,
    ) -> Dict[str, Any]:
        """Fetch mark price and funding rate for a futures symbol.

        Args:
            symbol: Futures symbol (e.g., 'BTCUSDT').

        Returns:
            Dict with markPrice, indexPrice, estimatedSettlePrice,
            lastFundingRate, nextFundingTime, interestRate, time.
        """
        try:
            url = f"{BINANCE_FUTURES_API}/fapi/v1/premiumIndex"
            params: Dict[str, Any] = {"symbol": symbol}

            data = await self._rate_limited_get(url, params=params)

            result = {
                "symbol": data.get("symbol", ""),
                "mark_price": float(data.get("markPrice", 0)),
                "index_price": float(data.get("indexPrice", 0)),
                "estimated_settle_price": float(data.get("estimatedSettlePrice", 0)) if data.get("estimatedSettlePrice") else None,
                "last_funding_rate": float(data.get("lastFundingRate", 0)),
                "next_funding_time": datetime.fromtimestamp(data.get("nextFundingTime", 0) / 1000).isoformat() if data.get("nextFundingTime") else None,
                "interest_rate": float(data.get("interestRate", 0)) if data.get("interestRate") else None,
                "time": datetime.fromtimestamp(data.get("time", 0) / 1000).isoformat() if data.get("time") else None,
            }

            self.mark_success()
            return result

        except Exception as e:
            self.mark_error(str(e))
            logger.warning(f"Binance mark price error for {symbol}: {e}")
            return {}

    async def get_taker_ratio(
        self,
        symbol: str,
        period: str = "5m",
        limit: int = 1,
    ) -> Dict[str, Any]:
        """Fetch taker buy/sell ratio for a futures symbol.

        Uses the Binance Futures API directly. No API key required.

        Args:
            symbol: Futures symbol (e.g., 'BTCUSDT').
            period: "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d".
            limit: Maximum number of records.

        Returns:
            Dict with buySellRatio, buyVol, sellVol, timestamp.
        """
        try:
            url = f"{BINANCE_FUTURES_API}/futures/data/takerlongshortRatio"
            params: Dict[str, Any] = {
                "symbol": symbol,
                "period": period,
                "limit": min(limit, 500),
            }

            data = await self._rate_limited_get(url, params=params)

            if isinstance(data, list) and data:
                item = data[0]
                result = {
                    "symbol": item.get("symbol", ""),
                    "taker_ratio": float(item.get("buySellRatio", 0)),
                    "buy_vol": float(item.get("buyVol", 0)),
                    "sell_vol": float(item.get("sellVol", 0)),
                    "timestamp": datetime.fromtimestamp(item.get("timestamp", 0) / 1000).isoformat() if item.get("timestamp") else None,
                }
            else:
                result = {}

            self.mark_success()
            return result

        except Exception as e:
            self.mark_error(str(e))
            logger.warning(f"Binance taker ratio error for {symbol}: {e}")
            return {}

    async def get_long_short_ratio(
        self,
        symbol: str,
        period: str = "5m",
        limit: int = 1,
    ) -> Dict[str, Any]:
        """Fetch global/top long/short account ratio for a futures symbol.

        Args:
            symbol: Futures symbol (e.g., 'BTCUSDT').
            period: "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d".
            limit: Maximum number of records.

        Returns:
            Dict with global_long_short_ratio, top_long_short_ratio.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                global_task = client.get(
                    f"{BINANCE_FUTURES_API}/futures/data/globalLongShortAccountRatio",
                    params={"symbol": symbol, "period": period, "limit": limit}
                )
                top_task = client.get(
                    f"{BINANCE_FUTURES_API}/futures/data/topLongShortPositionRatio",
                    params={"symbol": symbol, "period": period, "limit": limit}
                )
                global_res, top_res = await asyncio.gather(global_task, top_task)

            result = {}
            if global_res.status_code == 200 and isinstance(global_res.json(), list):
                gls = global_res.json()[0]
                result["global_ls_ratio"] = float(gls.get("longShortRatio", 0))
            if top_res.status_code == 200 and isinstance(top_res.json(), list):
                tls = top_res.json()[0]
                result["top_ls_ratio"] = float(tls.get("longShortRatio", 0))

            self.mark_success()
            return result

        except Exception as e:
            self.mark_error(str(e))
            logger.warning(f"Binance long/short ratio error for {symbol}: {e}")
            return {}

    async def get_derivatives_data(
        self,
        symbols: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Fetch comprehensive derivatives data for crypto symbols.

        Aggregates funding rate, open interest, mark price, taker ratio,
        and long/short ratios for each symbol.

        Args:
            symbols: List of futures symbols. Defaults to BTCUSDT, ETHUSDT, SOLUSDT.

        Returns:
            Dict mapping symbol to derivatives data dict.
        """
        if symbols is None:
            symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

        results = {}

        for sym in symbols:
            try:
                funding, oi, mark, taker, ls = await asyncio.gather(
                    self.get_funding_rate(sym, limit=1),
                    self.get_open_interest(sym),
                    self.get_mark_price(sym),
                    self.get_taker_ratio(sym),
                    self.get_long_short_ratio(sym),
                )

                # Extract latest funding rate
                latest_funding = funding[0].get("funding_rate") if funding else None
                next_funding = funding[0].get("funding_time") if funding else None
                mark_price = mark.get("mark_price")
                funding_annual = round(latest_funding * 3 * 365 * 100, 1) if latest_funding is not None else None

                # Funding state classification
                funding_state = "neutral"
                if funding_annual is not None:
                    if funding_annual > 30:
                        funding_state = "longs_crowded"
                    elif funding_annual > 10:
                        funding_state = "longs_lean"
                    elif funding_annual < -30:
                        funding_state = "shorts_crowded"
                    elif funding_annual < -10:
                        funding_state = "shorts_lean"

                # OI value calculation
                oi_qty = oi.get("open_interest", 0)
                oi_value = oi_qty * mark_price if oi_qty and mark_price else None

                results[sym] = {
                    "symbol": sym,
                    "mark_price": mark_price,
                    "funding_rate": latest_funding,
                    "funding_annual_pct": funding_annual,
                    "funding_state": funding_state,
                    "next_funding_time": next_funding,
                    "open_interest": oi_qty,
                    "oi_value": oi_value,
                    "taker_ratio": taker.get("taker_ratio"),
                    "global_ls_ratio": ls.get("global_ls_ratio"),
                    "top_ls_ratio": ls.get("top_ls_ratio"),
                    "timestamp": datetime.now().isoformat(),
                }

            except Exception as e:
                logger.warning(f"Binance derivatives data error for {sym}: {e}")
                results[sym] = {"symbol": sym, "error": str(e)}

        return results

    async def get_klines(
        self,
        symbol: str,
        interval: str = "1d",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        """Fetch kline/candlestick data directly from Binance REST API.

        More reliable than ccxt for some use cases.

        Args:
            symbol: Trading pair (e.g., 'BTCUSDT').
            interval: Kline interval (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h,
                      6h, 8h, 12h, 1d, 3d, 1w, 1M).
            start: Start datetime.
            end: End datetime.
            limit: Maximum number of klines (max 1000).

        Returns:
            List of kline dicts with OHLCV + additional data.
        """
        try:
            url = f"{BINANCE_SPOT_API}/api/v3/klines"
            params: Dict[str, Any] = {
                "symbol": symbol,
                "interval": interval,
                "limit": min(limit, 1000),
            }
            if start:
                params["startTime"] = int(start.timestamp() * 1000)
            if end:
                params["endTime"] = int(end.timestamp() * 1000)

            data = await self._rate_limited_get(url, params=params)

            result = []
            for k in data:
                result.append({
                    "open_time": datetime.fromtimestamp(k[0] / 1000).isoformat(),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                    "close_time": datetime.fromtimestamp(k[6] / 1000).isoformat(),
                    "quote_volume": float(k[7]),
                    "trades": int(k[8]),
                    "taker_buy_base_volume": float(k[9]),
                    "taker_buy_quote_volume": float(k[10]),
                })

            self.mark_success()
            return result

        except Exception as e:
            self.mark_error(str(e))
            logger.warning(f"Binance klines error for {symbol}: {e}")
            return []

    async def health_check(self) -> bool:
        """Check Binance connectivity."""
        try:
            await self._exchange.fetch_time()
            self._is_available = True
            return True
        except Exception as e:
            self._is_available = False
            self._last_error = str(e)
            return False

    async def close(self) -> None:
        """Close the exchange connection and HTTP client."""
        try:
            await self._exchange.close()
        except Exception:
            pass
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
