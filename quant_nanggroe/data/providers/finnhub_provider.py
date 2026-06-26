"""Finnhub Provider — Stock & market data via Finnhub API.

Provides OHLCV candles, news, economic calendar, and basic financials
with rate limiting (60 calls/min for free tier), in-memory caching with
TTL, and exponential backoff retry logic.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx
import pandas as pd

logger = logging.getLogger(__name__)


class TokenBucket:
    """Token bucket rate limiter (class-level, shared across instances)."""

    def __init__(self, rate: float, capacity: int) -> None:
        self._rate = rate
        self._capacity = capacity
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            self._refill()
            if self._tokens < 1:
                sleep_time = (1 - self._tokens) / self._rate
                await asyncio.sleep(sleep_time)
                self._refill()
            self._tokens -= 1

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
        self._last_refill = now


@dataclass
class _CacheEntry:
    value: Any
    expires_at: float


class FinnhubProvider:
    """Stock & market data provider using the Finnhub REST API.

    Rate-limited to 60 calls/minute (free tier). Responses are cached
    in-memory with configurable TTL (default 300 s). Failed requests
    are retried up to 3 times with exponential backoff.
    """

    BASE_URL = "https://finnhub.io/api/v1"
    RATE_PER_SECOND = 60.0 / 60.0
    BURST_CAPACITY = 5
    MAX_RETRIES = 3

    _bucket: TokenBucket | None = None

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._api_key = api_key or os.getenv("QNAI_FINNHUB_API_KEY", "")
        self._client: httpx.AsyncClient | None = None
        self._cache: Dict[str, _CacheEntry] = {}

        if FinnhubProvider._bucket is None:
            FinnhubProvider._bucket = TokenBucket(self.RATE_PER_SECOND, self.BURST_CAPACITY)

    @property
    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.BASE_URL, timeout=15.0)
        return self._client

    # ------------------------------------------------------------------
    # Cache
    # ------------------------------------------------------------------

    def _get_cache(self, key: str) -> Any:
        entry = self._cache.get(key)
        if entry is None:
            return None
        if time.monotonic() > entry.expires_at:
            del self._cache[key]
            return None
        return entry.value

    def _set_cache(self, key: str, value: Any, ttl: float = 300.0) -> None:
        self._cache[key] = _CacheEntry(value=value, expires_at=time.monotonic() + ttl)

    # ------------------------------------------------------------------
    # Request
    # ------------------------------------------------------------------

    async def _request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        retries: int = MAX_RETRIES,
    ) -> Any:
        params = dict(params or {})
        params.setdefault("token", self._api_key)

        last_exc: Exception | None = None
        for attempt in range(retries):
            await self._bucket.acquire()
            try:
                response = await self._http.get(endpoint, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    wait = 2 ** attempt * 5
                    logger.warning("Finnhub rate limited, retrying in %ds", wait)
                    await asyncio.sleep(wait)
                    last_exc = exc
                elif exc.response.status_code >= 500 and attempt < retries - 1:
                    wait = 2 ** attempt * 2
                    logger.warning(
                        "Finnhub %d, retry %d in %ds",
                        exc.response.status_code,
                        attempt + 1,
                        wait,
                    )
                    await asyncio.sleep(wait)
                    last_exc = exc
                else:
                    raise
            except httpx.RequestError as exc:
                wait = 2 ** attempt * 2
                logger.warning(
                    "Finnhub request failed (attempt %d), retry in %ds: %s",
                    attempt + 1,
                    wait,
                    exc,
                )
                await asyncio.sleep(wait)
                last_exc = exc

        raise last_exc  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def get_stock_candle(
        self,
        symbol: str,
        resolution: str = "D",
        count: int = 100,
    ) -> pd.DataFrame:
        """Fetch OHLCV candle data for a symbol.

        Parameters
        ----------
        symbol:
            Stock symbol, e.g. ``"AAPL"``.
        resolution:
            Candle resolution. Supported: ``1``, ``5``, ``15``, ``30``,
            ``60``, ``D``, ``W``, ``M``.
        count:
            Number of candles to fetch (max 5000).

        Returns
        -------
        pd.DataFrame
            Columns: ``timestamp``, ``open``, ``high``, ``low``, ``close``, ``volume``.
            Empty DataFrame if no data returned.
        """
        cache_key = f"candle:{symbol}:{resolution}:{count}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        data = await self._request("/stock/candle", params={
            "symbol": symbol,
            "resolution": resolution,
            "count": str(count),
        })

        if data.get("s") != "ok":
            logger.warning("Finnhub returned no data for %s (resolution=%s)", symbol, resolution)
            return pd.DataFrame()

        df = pd.DataFrame({
            "timestamp": pd.to_datetime(data["t"], unit="s"),
            "open": data["o"],
            "high": data["h"],
            "low": data["l"],
            "close": data["c"],
            "volume": data["v"],
        })
        df = df.dropna().sort_values("timestamp").reset_index(drop=True)
        self._set_cache(cache_key, df)
        return df

    async def get_news(self, symbol: str, from_date: str, to_date: str) -> List[Dict[str, Any]]:
        """Fetch company news for a symbol within a date range.

        Parameters
        ----------
        symbol:
            Stock symbol, e.g. ``"AAPL"``.
        from_date:
            Start date in ``YYYY-MM-DD`` format.
        to_date:
            End date in ``YYYY-MM-DD`` format.

        Returns
        -------
        List[Dict]
            List of news article dicts as returned by the Finnhub API.
        """
        cache_key = f"news:{symbol}:{from_date}:{to_date}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        data = await self._request("/company-news", params={
            "symbol": symbol,
            "from": from_date,
            "to": to_date,
        })
        self._set_cache(cache_key, data, ttl=120.0)
        return data

    async def get_market_news(self, category: str = "general") -> List[Dict[str, Any]]:
        """Fetch market news by category.

        Parameters
        ----------
        category:
            One of ``general``, ``forex``, ``crypto``, ``merger``.

        Returns
        -------
        List[Dict]
            List of news article dicts as returned by the Finnhub API.
        """
        cache_key = f"market_news:{category}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        data = await self._request("/news", params={"category": category})
        self._set_cache(cache_key, data, ttl=120.0)
        return data

    async def get_economic_calendar(self) -> List[Dict[str, Any]]:
        """Fetch upcoming economic events (may require paid plan).

        Returns
        -------
        List[Dict]
            List of economic event dicts. Empty list if not available
            on the current API plan.
        """
        data = await self._request("/calendar/economic")
        return data.get("economicCalendar", [])

    async def get_financials(
        self,
        symbol: str,
        metric_type: str = "all",
    ) -> Dict[str, Any]:
        """Fetch basic financial metrics for a symbol.

        Parameters
        ----------
        symbol:
            Stock symbol, e.g. ``"AAPL"``.
        metric_type:
            Metric type. ``"all"`` returns both price and basic financial
            metrics. Other options: ``"price"``, ``"valuation"``.

        Returns
        -------
        Dict
            Dict with ``"metric"`` key containing the metric values.
        """
        cache_key = f"financials:{symbol}:{metric_type}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        data = await self._request("/stock/metric", params={
            "symbol": symbol,
            "metric": metric_type,
        })
        self._set_cache(cache_key, data, ttl=600.0)
        return data

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> FinnhubProvider:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()


__all__ = ["FinnhubProvider"]
