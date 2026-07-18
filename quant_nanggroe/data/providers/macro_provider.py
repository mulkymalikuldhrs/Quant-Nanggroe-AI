"""Macro-Economic Data Provider — FRED API integration.

Provides US macroeconomic data via the Federal Reserve Economic Data (FRED) API.
Supports GDP, inflation (CPI), unemployment, interest rates, and treasury yields
with rate limiting, caching, and exponential-backoff retry.

FRED API docs: https://fred.stlouisfed.org/docs/api/fred/
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
import pandas as pd

from quant_nanggroe.data.providers.base import DataProvider
from quant_nanggroe.types.market import OHLCV, OrderBook, Ticker, TimeFrame

logger = logging.getLogger(__name__)


@dataclass
class _CacheEntry:
    value: Any
    expires_at: float


class TokenBucket:
    """Simple token bucket rate limiter (class-level, shared across instances)."""

    def __init__(self, rate: float, capacity: int) -> None:
        self._rate = rate
        self._capacity = capacity
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a token is available before proceeding."""
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


class MacroProvider:
    """Macro-economic data provider via the FRED API.

    Fetches US economic indicators (GDP, CPI, unemployment, federal funds rate,
    treasury yields) from the Federal Reserve Economic Data API.

    The API key is read from the ``QNAI_FRED_API_KEY`` environment variable.

    Rate-limited to 120 calls/minute (FRED free tier limit) using a shared
    token bucket. Responses are cached in-memory with a default TTL of 3600s.

    Usage::

        provider = MacroProvider()
        gdp = await provider.get_gdp()
        cpi = await provider.get_inflation()
        unemp = await provider.get_unemployment()
        await provider.close()
    """

    BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
    RATE_PER_SECOND = 120.0 / 60.0
    BURST_CAPACITY = 10
    DEFAULT_CACHE_TTL = 3600

    _bucket: TokenBucket | None = None

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._api_key = api_key or os.environ.get("QNAI_FRED_API_KEY", "")
        if not self._api_key:
            logger.warning("QNAI_FRED_API_KEY not set; FRED API calls will fail")

        self._client: httpx.AsyncClient | None = None
        self._cache: Dict[str, _CacheEntry] = {}

        if MacroProvider._bucket is None:
            MacroProvider._bucket = TokenBucket(self.RATE_PER_SECOND, self.BURST_CAPACITY)

    @property
    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
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

    def _set_cache(self, key: str, value: Any, ttl: float = DEFAULT_CACHE_TTL) -> None:
        self._cache[key] = _CacheEntry(value=value, expires_at=time.monotonic() + ttl)

    # ------------------------------------------------------------------
    # HTTP request with retry
    # ------------------------------------------------------------------

    async def _request(
        self,
        series_id: str,
        observation_start: Optional[str] = None,
        observation_end: Optional[str] = None,
        retries: int = 3,
    ) -> Dict[str, Any]:
        """Fetch FRED series observations with exponential-backoff retry.

        Args:
            series_id: FRED series identifier.
            observation_start: Start date as ``YYYY-MM-DD``.
            observation_end: End date as ``YYYY-MM-DD``.
            retries: Maximum number of retry attempts (default 3).

        Returns:
            Parsed JSON response dict.

        Raises:
            RuntimeError: After exhausting all retries.
            httpx.HTTPStatusError: On 4xx errors other than 429.
        """
        params: Dict[str, str] = {
            "series_id": series_id,
            "api_key": self._api_key,
            "file_type": "json",
        }
        if observation_start:
            params["observation_start"] = observation_start
        if observation_end:
            params["observation_end"] = observation_end

        last_exc: Exception | None = None
        for attempt in range(retries):
            await MacroProvider._bucket.acquire()  # type: ignore[union-attr]
            try:
                response = await self._http.get(self.BASE_URL, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    wait = 2**attempt * 5
                    logger.warning("FRED rate limited, retrying in %ds", wait)
                    await asyncio.sleep(wait)
                    last_exc = exc
                elif exc.response.status_code >= 500 and attempt < retries - 1:
                    wait = 2**attempt * 2
                    logger.warning(
                        "FRED %d, retry %d in %ds",
                        exc.response.status_code,
                        attempt + 1,
                        wait,
                    )
                    await asyncio.sleep(wait)
                    last_exc = exc
                else:
                    raise
            except httpx.RequestError as exc:
                wait = 2**attempt * 2
                logger.warning(
                    "FRED request failed (attempt %d), retry in %ds: %s",
                    attempt + 1,
                    wait,
                    exc,
                )
                await asyncio.sleep(wait)
                last_exc = exc

        raise RuntimeError(
            f"FRED series '{series_id}' failed after {retries} retries"
        ) from last_exc

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def get_series(
        self,
        series_id: str,
        observation_start: Optional[str] = None,
        observation_end: Optional[str] = None,
    ) -> pd.DataFrame:
        """Fetch a generic FRED series and return as a DataFrame.

        Args:
            series_id: FRED series identifier (e.g. ``"GDP"``, ``"CPIAUCSL"``).
            observation_start: Inclusive start date in ``YYYY-MM-DD`` format.
            observation_end: Inclusive end date in ``YYYY-MM-DD`` format.

        Returns:
            DataFrame with columns ``date`` (datetime) and ``value`` (float).
        """
        cache_key = f"series:{series_id}:{observation_start or ''}:{observation_end or ''}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        data = await self._request(series_id, observation_start, observation_end)
        df = self._parse_observations(data)
        self._set_cache(cache_key, df)
        return df

    async def get_gdp(self, series_id: str = "GDP") -> pd.DataFrame:
        """Fetch US Gross Domestic Product (GDP).

        Args:
            series_id: FRED series ID (default: ``GDP`` — nominal GDP).

        Returns:
            DataFrame with columns ``date`` and ``value``.
        """
        return await self.get_series(series_id)

    async def get_inflation(self, series_id: str = "CPIAUCSL") -> pd.DataFrame:
        """Fetch Consumer Price Index (CPI) / inflation data.

        Args:
            series_id: FRED series ID (default: ``CPIAUCSL`` — CPI All Urban).

        Returns:
            DataFrame with columns ``date`` and ``value``.
        """
        return await self.get_series(series_id)

    async def get_unemployment(self) -> pd.DataFrame:
        """Fetch unemployment rate (FRED series: UNRATE).

        Returns:
            DataFrame with columns ``date`` and ``value``.
        """
        return await self.get_series("UNRATE")

    async def get_interest_rate(self) -> pd.DataFrame:
        """Fetch effective federal funds rate (FRED series: FEDFUNDS).

        Returns:
            DataFrame with columns ``date`` and ``value``.
        """
        return await self.get_series("FEDFUNDS")

    async def get_treasury_yield(self, maturity: str = "10-year") -> pd.DataFrame:
        """Fetch constant-maturity Treasury yield.

        Args:
            maturity: Maturity term. Maps to FRED series IDs:
                ``1-month``, ``3-month``, ``6-month``, ``1-year``, ``2-year``,
                ``3-year``, ``5-year``, ``7-year``, ``10-year``, ``20-year``,
                ``30-year``.

        Returns:
            DataFrame with columns ``date`` and ``value``.

        Raises:
            ValueError: If *maturity* is not recognised.
        """
        series_map = {
            "1-month": "DGS1MO",
            "3-month": "DGS3MO",
            "6-month": "DGS6MO",
            "1-year": "DGS1",
            "2-year": "DGS2",
            "3-year": "DGS3",
            "5-year": "DGS5",
            "7-year": "DGS7",
            "10-year": "DGS10",
            "20-year": "DGS20",
            "30-year": "DGS30",
        }
        series_id = series_map.get(maturity)
        if series_id is None:
            raise ValueError(
                f"Unsupported maturity '{maturity}'. "
                f"Supported: {', '.join(sorted(series_map.keys()))}"
            )
        return await self.get_series(series_id)

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_observations(data: Dict[str, Any]) -> pd.DataFrame:
        """Parse FRED API JSON response into a (date, value) DataFrame.

        Filters out observations where the value is ``"."``  (FRED's
        sentinel for missing data).
        """
        observations = data.get("observations", [])
        if not observations:
            return pd.DataFrame(columns=["date", "value"])

        rows = []
        for obs in observations:
            val = obs.get("value", "")
            if val and val != ".":
                rows.append({"date": obs.get("date"), "value": float(val)})

        df = pd.DataFrame(rows, columns=["date", "value"])
        df["date"] = pd.to_datetime(df["date"])
        df = df.dropna(subset=["date", "value"]).sort_values("date").reset_index(drop=True)
        return df

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying HTTP client session."""
        if self._client:
            await self._client.aclose()
            self._client = None


__all__ = ["MacroProvider"]


class MacroProviderAdapter(DataProvider):
    """Adapter wrapping MacroProvider to conform to the DataProvider ABC."""

    def __init__(self, wrapped: MacroProvider) -> None:
        super().__init__(name="macro", priority=25)
        self._wrapped = wrapped

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.D1,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[OHLCV]:
        series_id = symbol.upper().replace("FRED:", "")
        start_str = start.strftime("%Y-%m-%d") if start else None
        end_str = end.strftime("%Y-%m-%d") if end else None
        df = await self._wrapped.get_series(series_id, start_str, end_str)
        if df.empty:
            return []
        results: List[OHLCV] = []
        for _, row in df.tail(limit).iterrows():
            try:
                results.append(OHLCV(
                    symbol=symbol,
                    timestamp=pd.Timestamp(row["date"]).to_pydatetime(),
                    open=float(row["value"]),
                    high=float(row["value"]),
                    low=float(row["value"]),
                    close=float(row["value"]),
                    volume=0.0,
                ))
            except Exception:
                continue
        return results

    async def get_ticker(self, symbol: str) -> Ticker:
        return Ticker(
            symbol=symbol,
            timestamp=datetime.utcnow(),
            last_price=0.0,
        )

    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
        return OrderBook(
            symbol=symbol,
            timestamp=datetime.utcnow(),
        )

    async def health_check(self) -> bool:
        try:
            await self._wrapped.get_series("GDP")
            return True
        except Exception:
            return False
