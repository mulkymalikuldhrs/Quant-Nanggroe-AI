"""
Market Data Tool — OHLCV & Price Fetching for Agents
=====================================================
Provides unified market data access across stocks (yfinance),
crypto (ccxt), and forex data sources with caching and normalization.

All methods are async and return normalized dictionaries consistent
with the CandleData / DataMetadata types from quant_nanggroe_ai.types.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from quant_nanggroe_ai.config import get_settings
from quant_nanggroe_ai.exceptions import DataError, DataSourceUnavailableError, DataValidationError

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════
# Symbol classification helpers
# ══════════════════════════════════════════════════════════════════════

CRYPTO_PREFIXES = ("BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "DOT", "AVAX", "MATIC")
FOREX_SUFFIX = ("=X", "=F")
CRYPTO_SUFFIX = ("-USD", "/USD", "USDT", "BUSD")

# Timeframe mapping: internal → yfinance interval string
_YF_INTERVAL_MAP: dict[str, str] = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "4h": "1h",  # yfinance max is 1h for intraday
    "1d": "1d",
    "1w": "1wk",
    "1M": "1mo",
}

# Timeframe mapping: internal → ccxt timeframe string
_CCXT_TIMEFRAME_MAP: dict[str, str] = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
    "1w": "1w",
    "1M": "1M",
}


class _InMemoryCache:
    """Simple TTL-based in-memory cache for market data."""

    def __init__(self, default_ttl: int = 60) -> None:
        self._store: dict[str, tuple[Any, float]] = {}
        self._default_ttl = default_ttl

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        ttl = ttl if ttl is not None else self._default_ttl
        self._store[key] = (value, time.monotonic() + ttl)

    def clear(self) -> None:
        self._store.clear()


def _is_crypto_symbol(symbol: str) -> bool:
    """Determine if a symbol refers to a crypto asset."""
    upper = symbol.upper()
    if upper.endswith(CRYPTO_SUFFIX):
        return True
    if "/" in symbol and upper.split("/")[-1] in ("USD", "USDT", "BUSD"):
        return True
    for prefix in CRYPTO_PREFIXES:
        if upper.startswith(prefix):
            return True
    return False


def _is_forex_symbol(symbol: str) -> bool:
    """Determine if a symbol refers to a forex pair."""
    return symbol.upper().endswith(FOREX_SUFFIX) or "=" in symbol


def _normalize_ohlcv_dataframe(df: pd.DataFrame, symbol: str, timeframe: str) -> dict[str, Any]:
    """Normalize a yfinance/ccxt DataFrame into our standard OHLCV dict."""
    if df.empty:
        return {"symbol": symbol, "timeframe": timeframe, "candles": [], "count": 0}

    # Handle MultiIndex columns from yfinance
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    candles: list[dict[str, Any]] = []
    for idx, row in df.iterrows():
        close_val = row.get("Close", row.get("close", 0.0))
        if close_val is None or (isinstance(close_val, float) and close_val != close_val):
            continue  # skip NaN rows
        candle = {
            "timestamp": idx.isoformat() if isinstance(idx, pd.Timestamp) else str(idx),
            "open": float(row.get("Open", row.get("open", 0.0)) or 0.0),
            "high": float(row.get("High", row.get("high", 0.0)) or 0.0),
            "low": float(row.get("Low", row.get("low", 0.0)) or 0.0),
            "close": float(close_val),
            "volume": float(row.get("Volume", row.get("volume", 0.0)) or 0.0),
        }
        candles.append(candle)

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "candles": candles,
        "count": len(candles),
        "metadata": {
            "source": "market_data_tool",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        },
    }


class MarketDataTool:
    """
    Unified market data tool for agent consumption.

    Routes data requests to the appropriate backend:
      - Crypto symbols → ccxt (Binance by default)
      - Stock symbols  → yfinance
      - Forex symbols  → yfinance

    Features:
      - In-memory TTL cache to reduce API calls
      - Data normalization across all sources
      - Graceful fallback when a data source is unavailable
      - Trust-score metadata per data source
    """

    def __init__(self, cache_ttl: int = 60) -> None:
        """
        Initialize the MarketDataTool.

        Args:
            cache_ttl: Cache time-to-live in seconds (default 60).
        """
        self._settings = get_settings()
        self._cache = _InMemoryCache(default_ttl=cache_ttl)
        self._ccxt_exchange: Any = None

    # ── Public API ────────────────────────────────────────────────────

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1d",
        limit: int = 200,
    ) -> dict[str, Any]:
        """
        Fetch OHLCV candle data for a symbol.

        Args:
            symbol: Ticker symbol (e.g. 'AAPL', 'BTC/USDT', 'EURUSD=X')
            timeframe: Candle interval ('1m', '5m', '15m', '1h', '4h', '1d', '1w')
            limit: Number of candles to return (max 1000)

        Returns:
            Normalized dict with 'symbol', 'timeframe', 'candles', 'count', 'metadata'.

        Raises:
            DataError: If the data cannot be fetched from any source.
        """
        limit = min(max(limit, 1), 1000)
        cache_key = f"ohlcv:{symbol}:{timeframe}:{limit}"

        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.debug("Cache hit for %s", cache_key)
            return cached

        try:
            if _is_crypto_symbol(symbol):
                result = await self._fetch_crypto_ohlcv(symbol, timeframe, limit)
            else:
                result = await self._fetch_yfinance_ohlcv(symbol, timeframe, limit)
        except Exception as exc:
            logger.error("Failed to fetch OHLCV for %s: %s", symbol, exc)
            raise DataError(f"Cannot fetch OHLCV for {symbol}: {exc}") from exc

        # Attach trust score
        result["metadata"] = {
            **result.get("metadata", {}),
            "trust_score": 0.9 if not _is_crypto_symbol(symbol) else 0.85,
        }

        # Cache with shorter TTL for intraday data
        ttl = 30 if timeframe in ("1m", "5m", "15m") else 60
        self._cache.set(cache_key, result, ttl=ttl)
        return result

    async def get_current_price(self, symbol: str) -> dict[str, Any]:
        """
        Get the latest price for a single symbol.

        Args:
            symbol: Ticker symbol.

        Returns:
            Dict with 'symbol', 'price', 'timestamp', 'source'.

        Raises:
            DataError: If price cannot be retrieved.
        """
        cache_key = f"price:{symbol}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            if _is_crypto_symbol(symbol):
                result = await self._fetch_crypto_price(symbol)
            else:
                result = await self._fetch_yfinance_price(symbol)
        except Exception as exc:
            logger.error("Failed to fetch price for %s: %s", symbol, exc)
            raise DataError(f"Cannot fetch price for {symbol}: {exc}") from exc

        self._cache.set(cache_key, result, ttl=15)
        return result

    async def get_multiple_prices(self, symbols: list[str]) -> dict[str, Any]:
        """
        Fetch current prices for multiple symbols in batch.

        Args:
            symbols: List of ticker symbols.

        Returns:
            Dict with 'prices' (mapping symbol→price dict), 'errors', 'fetched_at'.
        """
        prices: dict[str, Any] = {}
        errors: dict[str, str] = {}

        for symbol in symbols:
            try:
                prices[symbol] = await self.get_current_price(symbol)
            except DataError as exc:
                errors[symbol] = str(exc)
            except Exception as exc:
                errors[symbol] = f"Unexpected error: {exc}"

        return {
            "prices": prices,
            "errors": errors,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "total_requested": len(symbols),
            "total_fetched": len(prices),
        }

    # ── yfinance backend ──────────────────────────────────────────────

    async def _fetch_yfinance_ohlcv(
        self, symbol: str, timeframe: str, limit: int
    ) -> dict[str, Any]:
        """Fetch OHLCV data from yfinance (stocks & forex)."""
        try:
            import yfinance as yf
        except ImportError:
            raise DataSourceUnavailableError(
                "yfinance", "Package not installed. Run: pip install yfinance"
            )

        interval = _YF_INTERVAL_MAP.get(timeframe, "1d")
        ticker = yf.Ticker(symbol)

        # yfinance period selection: for intraday, max 60 days; for daily, 2y
        if timeframe in ("1m", "5m", "15m", "30m", "1h"):
            period = "60d"
        elif timeframe in ("4h",):
            period = "60d"
        else:
            period = "2y"

        df = ticker.history(period=period, interval=interval)
        df = df.tail(limit)

        result = _normalize_ohlcv_dataframe(df, symbol, timeframe)
        result["metadata"] = {
            "source": "yfinance",
            "interval": interval,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        }
        return result

    async def _fetch_yfinance_price(self, symbol: str) -> dict[str, Any]:
        """Fetch current price from yfinance."""
        try:
            import yfinance as yf
        except ImportError:
            raise DataSourceUnavailableError("yfinance", "Package not installed")

        ticker = yf.Ticker(symbol)
        fast_info = ticker.fast_info
        price = getattr(fast_info, "last_price", None)
        if price is None:
            # Fallback: last close from history
            hist = ticker.history(period="5d", interval="1d")
            if hist.empty:
                raise DataError(f"No price data available for {symbol}")
            price = float(hist["Close"].iloc[-1])

        return {
            "symbol": symbol,
            "price": float(price),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "yfinance",
        }

    # ── ccxt crypto backend ───────────────────────────────────────────

    async def _get_ccxt_exchange(self) -> Any:
        """Lazily initialize the ccxt exchange instance."""
        if self._ccxt_exchange is not None:
            return self._ccxt_exchange

        try:
            import ccxt
        except ImportError:
            raise DataSourceUnavailableError(
                "ccxt", "Package not installed. Run: pip install ccxt"
            )

        api_key = self._settings.data_sources.binance_api_key
        secret = self._settings.data_sources.binance_secret_key

        self._ccxt_exchange = ccxt.binance(
            {
                "apiKey": api_key or None,
                "secret": secret or None,
                "enableRateLimit": True,
                "options": {"defaultType": "spot"},
            }
        )
        return self._ccxt_exchange

    async def _fetch_crypto_ohlcv(
        self, symbol: str, timeframe: str, limit: int
    ) -> dict[str, Any]:
        """Fetch OHLCV data from ccxt exchange (Binance)."""
        exchange = await self._get_ccxt_exchange()
        ccxt_tf = _CCXT_TIMEFRAME_MAP.get(timeframe, "1d")

        # Normalize symbol format for ccxt (e.g., BTC-USD → BTC/USDT)
        ccxt_symbol = self._normalize_crypto_symbol(symbol)

        ohlcv = exchange.fetch_ohlcv(ccxt_symbol, ccxt_tf, limit=limit)

        candles: list[dict[str, Any]] = []
        for entry in ohlcv:
            ts_ms, o, h, l, c, v = entry
            candles.append(
                {
                    "timestamp": datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat(),
                    "open": float(o),
                    "high": float(h),
                    "low": float(l),
                    "close": float(c),
                    "volume": float(v),
                }
            )

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "candles": candles,
            "count": len(candles),
            "metadata": {
                "source": "ccxt_binance",
                "ccxt_symbol": ccxt_symbol,
                "interval": ccxt_tf,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    async def _fetch_crypto_price(self, symbol: str) -> dict[str, Any]:
        """Fetch current crypto price from ccxt exchange."""
        exchange = await self._get_ccxt_exchange()
        ccxt_symbol = self._normalize_crypto_symbol(symbol)

        ticker = exchange.fetch_ticker(ccxt_symbol)
        price = ticker.get("last") or ticker.get("close", 0.0)

        return {
            "symbol": symbol,
            "price": float(price),
            "bid": float(ticker.get("bid", 0.0)),
            "ask": float(ticker.get("ask", 0.0)),
            "volume_24h": float(ticker.get("quoteVolume", 0.0)),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "ccxt_binance",
        }

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _normalize_crypto_symbol(symbol: str) -> str:
        """
        Normalize a crypto symbol to ccxt format.

        Examples:
            'BTC-USD'  → 'BTC/USDT'
            'BTC/USD'  → 'BTC/USDT'
            'BTCUSDT'  → 'BTC/USDT'
            'BTC/USDT' → 'BTC/USDT'
        """
        upper = symbol.upper()
        if "/" in upper:
            base, quote = upper.split("/", 1)
            if quote == "USD":
                quote = "USDT"
            return f"{base}/{quote}"
        if upper.endswith("-USD"):
            return f"{upper[:-4]}/USDT"
        if upper.endswith("USDT"):
            return f"{upper[:-4]}/USDT"
        if upper.endswith("BUSD"):
            return f"{upper[:-4]}/BUSD"
        # Fallback: assume USDT pair
        return f"{upper}/USDT"
