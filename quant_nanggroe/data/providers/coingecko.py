"""CoinGecko data provider.

Uses the CoinGecko API for cryptocurrency market data.
Supports price, market cap, OHLCV, trending, and global data.

CoinGecko API is free (10-50 req/min) with pro tiers available:
https://www.coingecko.com/en/api

Symbol convention: ``CG:<coin_id>`` (e.g., ``CG:bitcoin``, ``CG:ethereum``).
For price quotes use ``CG:<coin_id>/<vs_currency>`` (e.g., ``CG:bitcoin/usd``).

Rate limits: ~10-50 req/min (free), 500/min (analyst), 1000/min (pro).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from quant_nanggroe.data.providers.base import DataProvider
from quant_nanggroe.types.market import OHLCV, OrderBook, Ticker, TimeFrame

logger = logging.getLogger(__name__)

# Map internal TimeFrame to CoinGecko OHLC days parameter
_TIMEFRAME_DAYS_MAP: Dict[TimeFrame, int] = {
    TimeFrame.H1: 1,       # 1 day of hourly data
    TimeFrame.H4: 1,       # 1 day (CoinGecko returns 30-min candles for 1d)
    TimeFrame.D1: 30,      # 30 days of daily candles
    TimeFrame.W1: 90,      # 90 days (4-hour candles)
    TimeFrame.MO1: 365,    # 365 days (daily candles)
}

# CoinGecko OHLC candle timeframe based on days parameter
# days=1 -> 30min candles, days=7-30 -> 4h candles, days=90+ -> daily
_DAYS_TO_INTERVAL: Dict[int, str] = {
    1: "30min",
    7: "4h",
    14: "4h",
    30: "daily",
    90: "daily",
    180: "daily",
    365: "daily",
}


class CoinGeckoError(Exception):
    """CoinGecko API error."""


def _parse_symbol(symbol: str) -> tuple[str, str]:
    """Extract CoinGecko coin ID and vs_currency from symbol.

    Args:
        symbol: Symbol in CG:<coin_id>/<vs_currency> or CG:<coin_id> format,
                or raw coin_id.

    Returns:
        Tuple of (coin_id, vs_currency). vs_currency defaults to 'usd'.
    """
    if symbol.startswith("CG:"):
        symbol = symbol[3:]

    if "/" in symbol:
        coin_id, vs_currency = symbol.split("/", 1)
        return coin_id.lower(), vs_currency.lower()
    return symbol.lower(), "usd"


class CoinGeckoProvider(DataProvider):
    """CoinGecko data provider.

    Provides cryptocurrency market data via the CoinGecko API.
    Optionally uses QNAI_COINGECKO_API_KEY for pro API access.

    Features:
    - OHLCV candlestick data for 10,000+ cryptocurrencies
    - Real-time price, market cap, and volume data
    - Trending coins and global market data
    - Free tier: 10-50 requests/min; Pro: up to 1000/min

    Example:
        >>> provider = CoinGeckoProvider(api_key="your-key")
        >>> candles = await provider.get_ohlcv("CG:bitcoin/usd", TimeFrame.D1)
        >>> ticker = await provider.get_ticker("CG:ethereum")
    """

    BASE_URL_FREE = "https://api.coingecko.com/api/v3"
    BASE_URL_PRO = "https://pro-api.coingecko.com/api/v3"

    def __init__(
        self,
        api_key: Optional[str] = None,
        priority: int = 15,
        **kwargs,
    ):
        """Initialize CoinGecko provider.

        Args:
            api_key: CoinGecko API key (optional, enables pro API).
                     Falls back to QNAI_COINGECKO_API_KEY env var.
            priority: Failover priority (lower = higher priority). Default 15.
        """
        super().__init__(name="coingecko", priority=priority, **kwargs)
        self._api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def _base_url(self) -> str:
        """Get the appropriate base URL based on API key availability."""
        if self._api_key or os.environ.get("QNAI_COINGECKO_API_KEY"):
            return self.BASE_URL_PRO
        return self.BASE_URL_FREE

    def _get_client(self) -> httpx.AsyncClient:
        """Lazy-initialize the HTTP client."""
        if self._client is None or self._client.is_closed:
            headers: Dict[str, str] = {}
            key = self._api_key or os.environ.get("QNAI_COINGECKO_API_KEY", "")
            if key:
                headers["x-cg-pro-api-key"] = key
            self._client = httpx.AsyncClient(timeout=30.0, headers=headers)
        return self._client

    async def _request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Make a request to the CoinGecko API.

        Args:
            endpoint: API endpoint (e.g., 'ping', 'coins/bitcoin/ohlc').
            params: Query parameters.

        Returns:
            Parsed JSON response.

        Raises:
            CoinGeckoError: On API errors.
        """
        client = self._get_client()
        url = f"{self._base_url}/{endpoint}"

        try:
            response = await client.get(url, params=params or {})
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                self.mark_error("CoinGecko rate limit exceeded")
                raise CoinGeckoError("Rate limited") from e
            self.mark_error(f"CoinGecko HTTP error: {e.response.status_code}")
            raise CoinGeckoError(f"HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            self.mark_error(f"CoinGecko request error: {e}")
            raise CoinGeckoError(f"Request failed: {e}") from e

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.D1,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[OHLCV]:
        """Fetch OHLCV data from CoinGecko.

        Uses the CoinGecko /coins/{id}/ohlc endpoint for OHLC data
        and /coins/{id}/market_chart for volume data.

        Args:
            symbol: Symbol in CG:<coin_id>/<vs_currency> format.
            timeframe: Candle timeframe.
            start: Start datetime.
            end: End datetime.
            limit: Maximum number of candles.

        Returns:
            List of OHLCV candles sorted by timestamp ascending.
        """
        try:
            coin_id, vs_currency = _parse_symbol(symbol)
            days = _TIMEFRAME_DAYS_MAP.get(timeframe, 30)

            # Use market_chart/range if start/end provided, else use days
            if start and end:
                endpoint = f"coins/{coin_id}/market_chart/range"
                params = {
                    "vs_currency": vs_currency,
                    "from": int(start.timestamp()),
                    "to": int(end.timestamp()),
                }
                data = await self._request(endpoint, params)

                prices = data.get("prices", [])
                volumes = data.get("total_volumes", [])

                # Build volume lookup
                vol_map = {int(v[0] / 1000): v[1] for v in volumes}

                # Aggregate prices into daily OHLCV
                result = self._aggregate_prices_to_ohlcv(
                    prices, vol_map, symbol, timeframe, limit
                )
            else:
                # Use OHLC endpoint (returns [timestamp, open, high, low, close])
                endpoint = f"coins/{coin_id}/ohlc"
                params = {
                    "vs_currency": vs_currency,
                    "days": str(days),
                }
                data = await self._request(endpoint, params)

                result = []
                for candle in data:
                    ts = datetime.fromtimestamp(candle[0] / 1000, tz=timezone.utc).replace(
                        tzinfo=None
                    )
                    ohlcv = OHLCV(
                        symbol=symbol,
                        timestamp=ts,
                        open=float(candle[1]),
                        high=float(candle[2]),
                        low=float(candle[3]),
                        close=float(candle[4]),
                        volume=0.0,  # OHLC endpoint doesn't include volume
                    )
                    result.append(ohlcv)

            self.mark_success()
            return result[-limit:]

        except CoinGeckoError:
            return []
        except Exception as e:
            self.mark_error(str(e))
            logger.warning(f"CoinGecko OHLCV error for {symbol}: {e}")
            return []

    def _aggregate_prices_to_ohlcv(
        self,
        prices: List[List[float]],
        vol_map: Dict[int, float],
        symbol: str,
        timeframe: TimeFrame,
        limit: int,
    ) -> List[OHLCV]:
        """Aggregate raw price data into OHLCV candles.

        Args:
            prices: List of [timestamp_ms, price] pairs.
            vol_map: Mapping of timestamp_seconds -> volume.
            symbol: Symbol string.
            timeframe: Target timeframe.
            limit: Maximum number of candles.

        Returns:
            List of OHLCV candles.
        """
        if not prices:
            return []

        # Group by day
        from collections import defaultdict

        daily_groups: Dict[str, List[tuple[datetime, float]]] = defaultdict(list)

        for ts_ms, price in prices:
            ts = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).replace(tzinfo=None)
            day_key = ts.strftime("%Y-%m-%d")
            daily_groups[day_key].append((ts, price))

        result = []
        for day_key in sorted(daily_groups.keys()):
            day_prices = daily_groups[day_key]
            day_timestamps = [p[0] for p in day_prices]
            day_values = [p[1] for p in day_prices]

            # Find matching volume
            vol = 0.0
            if day_timestamps:
                ts_key = int(day_timestamps[-1].timestamp())
                vol = vol_map.get(ts_key, 0.0)

            candle = OHLCV(
                symbol=symbol,
                timestamp=day_timestamps[0],
                open=day_values[0],
                high=max(day_values),
                low=min(day_values),
                close=day_values[-1],
                volume=vol,
            )
            result.append(candle)

        return result[-limit:]

    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Fetch current ticker data from CoinGecko.

        Uses the /simple/price endpoint for real-time data.

        Args:
            symbol: Symbol in CG:<coin_id>/<vs_currency> format.

        Returns:
            Current ticker data.
        """
        try:
            coin_id, vs_currency = _parse_symbol(symbol)

            params = {
                "ids": coin_id,
                "vs_currencies": vs_currency,
                "include_market_cap": "true",
                "include_24hr_vol": "true",
                "include_24hr_change": "true",
                "include_last_updated_at": "true",
            }
            data = await self._request("simple/price", params)

            coin_data = data.get(coin_id)
            if not coin_data:
                self.mark_error(f"No price data for {symbol}")
                return None

            currency_data = coin_data.get(vs_currency, {})
            if not currency_data:
                # Try getting the first available currency
                if coin_data:
                    first_key = next(iter(coin_data))
                    currency_data = coin_data[first_key]

            last_price = currency_data if isinstance(currency_data, (int, float)) else 0.0
            market_cap = 0.0
            vol_24h = 0.0
            change_24h = 0.0

            if isinstance(coin_data, dict):
                last_price = coin_data.get(vs_currency, 0.0)
                market_cap = coin_data.get(f"{vs_currency}_market_cap", 0.0)
                vol_24h = coin_data.get(f"{vs_currency}_24h_vol", 0.0)
                change_24h = coin_data.get(f"{vs_currency}_24h_change", 0.0)

            ticker = Ticker(
                symbol=symbol,
                timestamp=datetime.now(),
                last_price=float(last_price),
                volume_24h=float(vol_24h),
                change_pct_24h=float(change_24h) if change_24h else None,
            )
            self.mark_success()
            return ticker

        except CoinGeckoError:
            return None
        except Exception as e:
            self.mark_error(str(e))
            logger.warning(f"CoinGecko ticker error for {symbol}: {e}")
            return None

    async def get_orderbook(self, symbol: str, limit: int = 20) -> Optional[OrderBook]:
        """CoinGecko does not support order book data.

        Returns:
            None — CoinGecko provides aggregated market data only.
        """
        logger.debug("CoinGecko does not support order book data")
        return None

    async def get_trending(self) -> List[Dict[str, Any]]:
        """Fetch trending coins from CoinGecko.

        Returns:
            List of trending coin data dicts.
        """
        try:
            data = await self._request("search/trending")
            self.mark_success()
            return data.get("coins", [])
        except Exception as e:
            self.mark_error(str(e))
            logger.warning(f"CoinGecko trending error: {e}")
            return []

    async def get_global_data(self) -> Dict[str, Any]:
        """Fetch global cryptocurrency market data.

        Returns:
            Dict with global market data (total market cap, volume, etc.).
        """
        try:
            data = await self._request("global")
            self.mark_success()
            return data.get("data", {})
        except Exception as e:
            self.mark_error(str(e))
            logger.warning(f"CoinGecko global data error: {e}")
            return {}

    async def get_coin_markets(
        self,
        vs_currency: str = "usd",
        category: Optional[str] = None,
        order: str = "market_cap_desc",
        per_page: int = 100,
        page: int = 1,
    ) -> List[Dict[str, Any]]:
        """Fetch coin market data with filtering.

        Args:
            vs_currency: Target currency (e.g., 'usd', 'eur').
            category: Filter by category (e.g., 'defi', 'nft').
            order: Sort order (e.g., 'market_cap_desc', 'volume_desc').
            per_page: Results per page (max 250).
            page: Page number.

        Returns:
            List of coin market data dicts.
        """
        try:
            params: Dict[str, Any] = {
                "vs_currency": vs_currency,
                "order": order,
                "per_page": str(min(per_page, 250)),
                "page": str(page),
                "sparkline": "false",
            }
            if category:
                params["category"] = category

            data = await self._request("coins/markets", params)
            self.mark_success()
            return data if isinstance(data, list) else []
        except Exception as e:
            self.mark_error(str(e))
            logger.warning(f"CoinGecko markets error: {e}")
            return []

    async def health_check(self) -> bool:
        """Check if the CoinGecko API is accessible.

        Returns:
            True if the API responds successfully.
        """
        try:
            data = await self._request("ping")
            self._is_available = data.get("gecko_says") == "(V3) To the Moon!"
            return self._is_available
        except Exception as e:
            self._is_available = False
            self._last_error = str(e)
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
