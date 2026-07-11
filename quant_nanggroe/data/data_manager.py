"""Data Manager — Unified data interface for Quant Nanggroe AI.

Provides multi-provider data access with automatic failover,
in-memory caching with TTL, and real-time data subscription
callbacks. All candles are returned as standardized DataFrames.

Usage:
    manager = DataManager()
    manager.register("binance", binance_provider, ProviderType.CRYPTO, priority=0)
    manager.register("ccxt", ccxt_provider, ProviderType.CRYPTO, priority=1)

    df = manager.get_ohlcv("BTC/USDT", TimeFrame.H1)
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import pandas as pd
from pydantic import BaseModel, Field

from quant_nanggroe.types.market import TimeFrame

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CACHE_TTL = 60  # seconds
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0  # exponential backoff multiplier

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ProviderType(str, Enum):
    """Market data provider categories."""
    CRYPTO = "crypto"
    EQUITY = "equity"
    FOREX = "forex"
    MACRO = "macro"
    NEWS = "news"

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class DataProvider(BaseModel):
    """A registered data provider with failover priority.

    Lower ``priority`` values are tried first during failover.
    """
    name: str
    instance: Any = Field(..., description="Provider instance with fetch_ohlcv method")
    provider_type: ProviderType
    priority: int = 0

    model_config = {"from_attributes": True, "arbitrary_types_allowed": True}


class CacheEntry(BaseModel):
    """Cached DataFrame with expiration timestamp."""
    data: pd.DataFrame
    expires_at: float

    model_config = {"from_attributes": True, "arbitrary_types_allowed": True}


# ---------------------------------------------------------------------------
# Data Manager (singleton)
# ---------------------------------------------------------------------------

class DataManager:
    """Unified data interface — singleton.

    Providers register themselves with a type and priority.
    ``get_ohlcv`` automatically tries providers in priority order,
    falling back on failure. Results are cached with configurable TTL.
    """

    _instance: Optional[DataManager] = None

    def __new__(cls) -> DataManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._providers: Dict[str, List[DataProvider]] = {}
        self._cache: Dict[str, CacheEntry] = {}
        self._callbacks: Dict[str, List[Callable[[pd.DataFrame], None]]] = {}
        self._initialized = True
        logger.info("DataManager initialized")

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        name: str,
        instance: Any,
        provider_type: ProviderType,
        priority: int = 0,
    ) -> None:
        """Register a data provider.

        Args:
            name: Human-readable provider identifier.
            instance: Provider object that implements ``fetch_ohlcv``.
            provider_type: Category of market data.
            priority: Lower values are preferred during failover.
        """
        provider = DataProvider(
            name=name,
            instance=instance,
            provider_type=provider_type,
            priority=priority,
        )
        key = provider_type.value
        self._providers.setdefault(key, []).append(provider)
        self._providers[key].sort(key=lambda p: p.priority)
        logger.info("Registered provider '%s' for %s (priority=%d)", name, key, priority)

    def registered(self, provider_type: Optional[ProviderType] = None) -> List[DataProvider]:
        """List registered providers, optionally filtered by type."""
        if provider_type is not None:
            return list(self._providers.get(provider_type.value, []))
        return [p for providers in self._providers.values() for p in providers]

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _cache_key(
        self,
        symbol: str,
        timeframe: str,
        start: Optional[str],
        end: Optional[str],
        provider_type: ProviderType,
    ) -> str:
        return f"{provider_type.value}:{symbol}:{timeframe}:{start or ''}:{end or ''}"

    def _cache_get(self, key: str) -> Optional[pd.DataFrame]:
        entry = self._cache.get(key)
        if entry is None:
            return None
        if time.time() > entry.expires_at:
            del self._cache[key]
            return None
        return entry.data.copy()

    def _cache_set(self, key: str, data: pd.DataFrame, ttl: int = CACHE_TTL) -> None:
        self._cache[key] = CacheEntry(data=data.copy(), expires_at=time.time() + ttl)

    def _cache_invalidate(self, symbol: Optional[str] = None) -> None:
        if symbol is None:
            self._cache.clear()
            return
        self._cache = {k: v for k, v in self._cache.items() if not k.startswith(symbol)}

    # ------------------------------------------------------------------
    # Core data fetch
    # ------------------------------------------------------------------

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.D1,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        provider_type: ProviderType = ProviderType.CRYPTO,
    ) -> pd.DataFrame:
        """Fetch OHLCV candles with automatic failover and caching.

        Tries registered providers in priority order. If the primary
        provider fails, falls back to the next. Raises after all
        providers fail.

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume.
            Timestamps are timezone-naive UTC.
        """
        start_str = start.isoformat() if start else None
        end_str = end.isoformat() if end else None
        cache_key = self._cache_key(symbol, timeframe.value, start_str, end_str, provider_type)

        cached = self._cache_get(cache_key)
        if cached is not None:
            logger.debug("Cache hit for %s", cache_key)
            return cached

        providers = self._providers.get(provider_type.value, [])
        if not providers:
            raise ValueError(f"No providers registered for {provider_type.value}")

        last_error: Optional[Exception] = None
        for attempt in range(MAX_RETRIES):
            for idx, provider in enumerate(providers):
                try:
                    logger.debug(
                        "Fetching %s %s from %s (attempt %d)",
                        symbol, timeframe.value, provider.name, attempt + 1,
                    )
                    df = provider.instance.fetch_ohlcv(
                        symbol=symbol,
                        timeframe=timeframe.value,
                        start=start,
                        end=end,
                    )
                except Exception as exc:
                    logger.warning(
                        "Provider '%s' failed for %s: %s",
                        provider.name, symbol, exc,
                    )
                    last_error = exc
                    continue

                if not isinstance(df, pd.DataFrame) or df.empty:
                    logger.warning("Provider '%s' returned empty data for %s", provider.name, symbol)
                    continue

                df = self._normalize(df, symbol)
                self._cache_set(cache_key, df)
                logger.info(
                    "Fetched %d candles for %s from %s",
                    len(df), symbol, provider.name,
                )
                return df

            if attempt < MAX_RETRIES - 1:
                backoff = RETRY_BACKOFF ** attempt
                logger.debug("Retrying in %.1fs (attempt %d/%d)", backoff, attempt + 1, MAX_RETRIES)
                time.sleep(backoff)

        raise RuntimeError(
            f"All providers failed for {provider_type.value}:{symbol} "
            f"after {MAX_RETRIES} attempt(s)"
        ) from last_error

    # ------------------------------------------------------------------
    # Real-time subscriptions
    # ------------------------------------------------------------------

    def subscribe(self, symbol: str, callback: Callable[[pd.DataFrame], None]) -> None:
        """Register a callback for real-time candle updates.

        The callback receives a single-row DataFrame with the standard
        candle columns whenever the provider pushes an update.
        """
        self._callbacks.setdefault(symbol, []).append(callback)
        logger.debug("Subscribed callback for %s (total %d)", symbol, len(self._callbacks[symbol]))

    def unsubscribe(self, symbol: str, callback: Callable[[pd.DataFrame], None]) -> None:
        """Remove a previously registered callback."""
        callbacks = self._callbacks.get(symbol, [])
        if callback in callbacks:
            callbacks.remove(callback)
            logger.debug("Unsubscribed callback for %s", symbol)

    def _notify(self, symbol: str, candle: pd.DataFrame) -> None:
        """Push a candle update to all subscribers for the symbol."""
        for cb in self._callbacks.get(symbol, []):
            try:
                cb(candle)
            except Exception as exc:
                logger.error("Callback error for %s: %s", symbol, exc)

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------

    _CANDLE_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]

    @classmethod
    def _normalize(cls, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Standardize a raw provider DataFrame into the canonical format.

        Expected output columns: timestamp, open, high, low, close, volume.
        Timestamps are converted to UTC datetime with no timezone info.
        """
        if df.empty:
            return pd.DataFrame(columns=cls._CANDLE_COLUMNS)

        result = df.copy()

        for col in cls._CANDLE_COLUMNS:
            if col not in result.columns:
                result[col] = None

        result = result[cls._CANDLE_COLUMNS]

        if result["timestamp"].dtype.kind in ("i", "f"):
            result["timestamp"] = pd.to_datetime(result["timestamp"], unit="s", utc=True)
        elif result["timestamp"].dtype.kind == "O":
            result["timestamp"] = pd.to_datetime(result["timestamp"], utc=True)

        result["timestamp"] = result["timestamp"].dt.tz_localize(None)

        for col in ["open", "high", "low", "close"]:
            if col in result.columns:
                result[col] = pd.to_numeric(result[col], errors="coerce").astype("float64")

        if "volume" in result.columns:
            result["volume"] = pd.to_numeric(result["volume"], errors="coerce").astype("float64")

        result = result.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

        return result
