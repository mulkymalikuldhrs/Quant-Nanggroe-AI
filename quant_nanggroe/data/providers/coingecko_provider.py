"""CoinGecko Provider — Cryptocurrency market data via CoinGecko public API.

Provides price, historical data, top coins, and coin list queries
with rate limiting, in-memory caching, and retry logic.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx
import pandas as pd

logger = logging.getLogger(__name__)


class TokenBucket:
    """Simple token bucket rate limiter (class-level, shared)."""

    def __init__(self, rate: float, capacity: int) -> None:
        self._rate = rate
        self._capacity = capacity
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a token is available."""
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


class CoinGeckoProvider:
    """Cryptocurrency market data provider using CoinGecko public API.

    Rate-limited to 20 calls/minute with a token bucket.
    Caches price data for 300s and coin list for 3600s.
    Retries failed requests up to 3 times with exponential backoff.
    """

    BASE_URL = "https://api.coingecko.com/api/v3"
    RATE_PER_SECOND = 20.0 / 60.0
    BURST_CAPACITY = 5

    _bucket: TokenBucket | None = None

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._cache: Dict[str, _CacheEntry] = {}

        if CoinGeckoProvider._bucket is None:
            CoinGeckoProvider._bucket = TokenBucket(self.RATE_PER_SECOND, self.BURST_CAPACITY)

    @property
    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.BASE_URL, timeout=15.0)
        return self._client

    # ----- Cache -----

    def _get_cache(self, key: str) -> Any:
        entry = self._cache.get(key)
        if entry is None:
            return None
        if time.monotonic() > entry.expires_at:
            del self._cache[key]
            return None
        return entry.value

    def _set_cache(self, key: str, value: Any, ttl: float) -> None:
        self._cache[key] = _CacheEntry(value=value, expires_at=time.monotonic() + ttl)

    # ----- Request -----

    async def _request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        retries: int = 3,
    ) -> Any:
        last_exc: Exception | None = None
        for attempt in range(retries):
            await self._bucket.acquire()  # type: ignore[union-attr]
            try:
                response = await self._http.get(endpoint, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    wait = 2 ** attempt * 5
                    logger.warning("CoinGecko rate limited, retrying in %ds", wait)
                    await asyncio.sleep(wait)
                    last_exc = exc
                elif exc.response.status_code >= 500 and attempt < retries - 1:
                    wait = 2 ** attempt * 2
                    logger.warning(
                        "CoinGecko %d, retry %d in %ds",
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
                    "CoinGecko request failed (attempt %d), retry in %ds: %s",
                    attempt + 1,
                    wait,
                    exc,
                )
                await asyncio.sleep(wait)
                last_exc = exc
        raise last_exc  # type: ignore[misc]

    # ----- Public Methods -----

    async def get_price(self, coin_id: str, vs_currency: str = "usd") -> Optional[float]:
        """Get current price for a coin (cached for 300s)."""
        cache_key = f"price:{coin_id}:{vs_currency}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        data = await self._request("/simple/price", params={
            "ids": coin_id,
            "vs_currencies": vs_currency,
        })
        price = data.get(coin_id, {}).get(vs_currency)
        if price is not None:
            self._set_cache(cache_key, price, ttl=300)
        return price

    async def get_historical_data(
        self,
        coin_id: str,
        days: int = 30,
        vs_currency: str = "usd",
    ) -> pd.DataFrame:
        """Get historical price data as daily OHLCV DataFrame.

        Columns: open, high, low, close, volume
        """
        # ponytail: /coins/{id}/ohlc is lighter but limited to 10k candles;
        # /coins/{id}/market_chart gives price+volume which we reshape to OHLCV.
        data = await self._request(f"/coins/{coin_id}/market_chart", params={
            "vs_currency": vs_currency,
            "days": str(days),
        })

        prices = data.get("prices", [])
        volumes = data.get("total_volumes", [])

        if not prices:
            return pd.DataFrame()

        df = pd.DataFrame(prices, columns=["timestamp", "price"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)

        ohlc = df["price"].resample("D").ohlc()

        vol_df = pd.DataFrame(volumes, columns=["timestamp", "volume"])
        vol_df["timestamp"] = pd.to_datetime(vol_df["timestamp"], unit="ms")
        vol_df.set_index("timestamp", inplace=True)
        vol_df = vol_df["volume"].resample("D").sum().to_frame()

        result = ohlc.join(vol_df, how="left")
        result.columns = ["open", "high", "low", "close", "volume"]
        return result.dropna()

    async def get_top_coins(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get top coins by market cap."""
        # ponytail: CoinGecko returns 250 max per page; implement pagination if needed
        data = await self._request("/coins/markets", params={
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": str(min(limit, 250)),
            "page": "1",
        })
        return data[:limit]

    async def get_coin_list(self) -> List[Dict[str, Any]]:
        """Get all supported coins (cached for 3600s)."""
        cached = self._get_cache("coin_list")
        if cached is not None:
            return cached

        data = await self._request("/coins/list")
        self._set_cache("coin_list", data, ttl=3600)
        return data

    async def close(self) -> None:
        """Cleanup HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


__all__ = ["CoinGeckoProvider"]
