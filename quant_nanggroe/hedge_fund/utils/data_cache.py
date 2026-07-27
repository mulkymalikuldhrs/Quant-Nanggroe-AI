"""Shared OHLCV data cache — single source of market data for all signal providers.

Prevents N redundant MT5/yfinance calls when 200+ providers all request the same
symbol. Cache is per-session (in-memory dict) with configurable TTL.

Usage:
    from quant_nanggroe.hedge_fund.utils.data_cache import DataCache
    cache = DataCache()
    df = cache.get("EURUSD", count=100, tf=15)
"""

import threading
import time
from typing import Optional

import pandas as pd

from quant_nanggroe.hedge_fund.utils.config import log
from quant_nanggroe.hedge_fund.utils.data import get_historical_mt5

# ── Cache Bucket ──────────────────────────────────────────────────────


class _Bucket:
    """Single cache entry with TTL."""

    __slots__ = ("df", "ts", "ttl")

    def __init__(self, df: pd.DataFrame, ttl: float = 30.0):
        self.df = df
        self.ts = time.time()
        self.ttl = ttl

    @property
    def expired(self) -> bool:
        return (time.time() - self.ts) > self.ttl


# ── Data Cache (thread-safe singleton) ────────────────────────────────


class DataCache:
    """Thread-safe shared OHLCV cache.

    Key format: ``{symbol}:{count}:{tf}``
    Default TTL: 30 seconds (configurable via ``default_ttl``).

    Thread-safe via ``threading.Lock``.
    """

    _instance: Optional["DataCache"] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._buckets: dict[str, _Bucket] = {}
                    cls._instance._default_ttl = 30.0
        return cls._instance

    # ── Public API ────────────────────────────────────────────────────

    def get(self, symbol: str = "EURUSD", count: int = 100, tf: int = 15,
            force_refresh: bool = False) -> Optional[pd.DataFrame]:
        """Get cached OHLCV data, fetching from MT5 if needed.

        Args:
            symbol: Trading symbol.
            count: Number of bars.
            tf: Timeframe in minutes (MT5 constant).
            force_refresh: Bypass cache and fetch fresh data.

        Returns:
            DataFrame with OHLCV data or None if unavailable.
        """
        key = f"{symbol}:{count}:{tf}"

        # Return cached if fresh
        if not force_refresh:
            with self._lock:
                bucket = self._buckets.get(key)
                if bucket is not None and not bucket.expired:
                    return bucket.df.copy()

        # Fetch fresh
        try:
            df = get_historical_mt5(symbol=symbol, count=count, tf=tf)
            if df is not None and len(df) > 10:
                with self._lock:
                    self._buckets[key] = _Bucket(df, ttl=self._default_ttl)
                return df.copy()
        except RuntimeError:
            pass  # MT5 unavailable — caller handles None
        except Exception as e:
            log.debug("DataCache fetch error for %s: %s", symbol, e)

        return None

    def get_multi(self, symbols: list[str], count: int = 100, tf: int = 15
                  ) -> dict[str, Optional[pd.DataFrame]]:
        """Get cached data for multiple symbols.

        Returns dict mapping symbol -> DataFrame or None.
        """
        return {s: self.get(s, count=count, tf=tf) for s in symbols}

    def invalidate(self, symbol: Optional[str] = None, tf: Optional[int] = None):
        """Invalidate cache entries.

        Args:
            symbol: If given, only invalidate entries for this symbol.
            tf: If given, only invalidate entries for this timeframe.
        """
        with self._lock:
            if symbol is None and tf is None:
                self._buckets.clear()
                return
            keys = list(self._buckets.keys())
            for key in keys:
                parts = key.split(":")
                if symbol is not None and parts[0] != symbol:
                    continue
                if tf is not None and len(parts) > 2 and parts[2] != str(tf):
                    continue
                self._buckets.pop(key, None)

    def set_ttl(self, ttl: float):
        """Set default TTL for future cache entries."""
        self._default_ttl = max(5.0, min(300.0, ttl))

    def clear(self):
        """Clear entire cache."""
        with self._lock:
            self._buckets.clear()

    @property
    def size(self) -> int:
        """Number of cached entries."""
        with self._lock:
            return len(self._buckets)


# ── Module-level convenience ──────────────────────────────────────────

_cache = DataCache()

get_cached_data = _cache.get
invalidate_cache = _cache.invalidate
clear_cache = _cache.clear
