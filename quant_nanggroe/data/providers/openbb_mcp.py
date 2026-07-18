"""OpenBB MCP data provider for Quant Nanggroe AI.

Provides market data via the OpenBB Hub REST API with optional
OpenBB Python SDK acceleration. Per-request SDK→REST fallback.
Designed for integration with DataManager's ``fetch_ohlcv`` interface.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

from quant_nanggroe.data.providers.base import DataProvider
from quant_nanggroe.types.market import OHLCV, OrderBook, Ticker, TimeFrame

logger = logging.getLogger(__name__)


@dataclass
class _CacheEntry:
    value: pd.DataFrame
    expires_at: float


class OpenBBMCPProvider:
    """OpenBB MCP-based market data provider.

    Fetches OHLCV data via the OpenBB platform. Tries the OpenBB
    Python SDK first; falls back to the OpenBB Hub REST API.

    Parameters
    ----------
    api_key:
        OpenBB personal access token. Falls back to
        ``OPENBB_API_KEY`` or ``QNAI_OPENBB_API_KEY`` env vars.
    base_url:
        OpenBB Hub API base URL.
    """

    REST_TIMEOUT = 30
    CACHE_TTL = 60

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.openbb.co",
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._sdk = None
        self._cache: Dict[str, _CacheEntry] = {}
        self._init_sdk()

    # ------------------------------------------------------------------
    # Cache
    # ------------------------------------------------------------------

    def _get_cache(self, key: str) -> Optional[pd.DataFrame]:
        entry = self._cache.get(key)
        if entry is None:
            return None
        if time.monotonic() > entry.expires_at:
            del self._cache[key]
            return None
        return entry.value.copy()

    def _set_cache(self, key: str, df: pd.DataFrame) -> None:
        self._cache[key] = _CacheEntry(
            value=df.copy(),
            expires_at=time.monotonic() + self.CACHE_TTL,
        )

    # ------------------------------------------------------------------
    # SDK init
    # ------------------------------------------------------------------

    def _init_sdk(self) -> None:
        """Try to initialise the OpenBB Python SDK."""
        import os

        key = self.api_key or os.getenv("OPENBB_API_KEY") or os.getenv("QNAI_OPENBB_API_KEY")
        if key:
            self.api_key = key

        try:
            from openbb import obb  # type: ignore[import-untyped]

            if self.api_key:
                obb.account.login(pat=self.api_key)
            self._sdk = obb
            logger.info("OpenBB SDK initialised")
        except ImportError:
            logger.info("OpenBB SDK not available, using REST API fallback")
        except Exception as exc:
            logger.warning("OpenBB SDK init failed: %s", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "D1",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """Fetch OHLCV market data.

        Parameters
        ----------
        symbol:
            Ticker symbol, *e.g.* ``"AAPL"``.
        timeframe:
            Candle resolution string (*e.g.* ``"D1"``, ``"H1"``, ``"M1"``).
        start:
            Start datetime (inclusive).
        end:
            End datetime (inclusive).

        Returns
        -------
        pd.DataFrame
            Columns: ``timestamp``, ``open``, ``high``, ``low``,
            ``close``, ``volume``.  Empty DataFrame on error or no data.
        """
        cache_key = f"{symbol}:{timeframe}:{start.isoformat() if start else ''}:{end.isoformat() if end else ''}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        if self._sdk is not None:
            try:
                df = self._fetch_via_sdk(symbol, timeframe, start, end)
                if df is not None and not df.empty:
                    self._set_cache(cache_key, df)
                    return df
            except Exception as exc:
                logger.warning("SDK fetch failed, falling back to REST: %s", exc)
        df = self._fetch_via_rest(symbol, timeframe, start, end)
        if not df.empty:
            self._set_cache(cache_key, df)
        return df

    # ------------------------------------------------------------------
    # SDK path
    # ------------------------------------------------------------------

    @staticmethod
    def _timeframe_to_interval(timeframe: str) -> Optional[str]:
        mapping = {
            "D1": None,
            "H1": "1h",
            "H4": "4h",
            "W1": "1wk",
            "M1": "1mo",
        }
        return mapping.get(timeframe.upper())

    def _fetch_via_sdk(
        self,
        symbol: str,
        timeframe: str,
        start: Optional[datetime],
        end: Optional[datetime],
    ) -> pd.DataFrame:
        """Fetch data via the OpenBB Python SDK."""
        try:
            params: dict = {"symbol": symbol, "provider": "yfinance"}
            if start:
                params["start_date"] = start.isoformat()
            if end:
                params["end_date"] = end.isoformat()
            interval = self._timeframe_to_interval(timeframe)
            if interval:
                params["interval"] = interval
            data = self._sdk.equity.price.historical(  # type: ignore[union-attr]
                **params,
            )
            if data is not None and not data.empty:
                df = data.to_dataframe()
                return df.reset_index()
        except (AttributeError, TypeError, ValueError, KeyError, RuntimeError) as exc:
            logger.exception("OpenBB SDK fetch failed: %s", exc)
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    # ------------------------------------------------------------------
    # REST fallback
    # ------------------------------------------------------------------

    def _fetch_via_rest(
        self,
        symbol: str,
        timeframe: str,
        start: Optional[datetime],
        end: Optional[datetime],
    ) -> pd.DataFrame:
        """Fetch data via the OpenBB Hub REST API."""
        import requests

        try:
            params: dict = {"symbol": symbol, "provider": "yfinance"}
            if start:
                params["start_date"] = start.isoformat()
            if end:
                params["end_date"] = end.isoformat()
            interval = self._timeframe_to_interval(timeframe)
            if interval:
                params["interval"] = interval
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            resp = requests.get(
                f"{self.base_url}/api/v1/equity/price/historical",
                params=params,
                headers=headers,
                timeout=self.REST_TIMEOUT,
            )
            resp.raise_for_status()
            payload = resp.json()
            results = payload.get("results") if isinstance(payload, dict) else payload
            if results:
                df = pd.DataFrame(results)
                if "date" in df.columns and "timestamp" not in df.columns:
                    df = df.rename(columns={"date": "timestamp"})
                return df
        except Exception as exc:
            logger.warning("OpenBB REST fetch failed: %s", exc)
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])


__all__ = ["OpenBBMCPProvider"]


class OpenBBMCPProviderAdapter(DataProvider):
    """Async adapter wrapping sync OpenBBMCPProvider to conform to the DataProvider ABC."""

    def __init__(self, wrapped: OpenBBMCPProvider) -> None:
        super().__init__(name="openbb", priority=28)
        self._wrapped = wrapped

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.D1,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[OHLCV]:
        import asyncio

        tf_map = {
            TimeFrame.M1: "M1", TimeFrame.M5: "M5", TimeFrame.M15: "M15",
            TimeFrame.M30: "M30", TimeFrame.H1: "H1", TimeFrame.H4: "H4",
            TimeFrame.D1: "D1", TimeFrame.W1: "W1", TimeFrame.MO1: "M1",
        }
        tf_str = tf_map.get(timeframe, "D1")
        df = await asyncio.to_thread(
            self._wrapped.fetch_ohlcv, symbol, tf_str, start, end
        )
        if df.empty:
            return []
        results: List[OHLCV] = []
        for _, row in df.tail(limit).iterrows():
            try:
                results.append(OHLCV(
                    symbol=symbol,
                    timestamp=pd.Timestamp(row.get("timestamp", row.name)).to_pydatetime(),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row.get("volume", 0)),
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
        import asyncio

        try:
            df = await asyncio.to_thread(
                self._wrapped.fetch_ohlcv, "AAPL", "D1"
            )
            return not df.empty
        except Exception:
            return False
