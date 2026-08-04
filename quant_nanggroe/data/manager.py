"""Data Provider Manager with automatic failover, caching, and rate limit handling.

Manages multiple data providers and routes requests to the best
available provider based on priority and health.

Features:
- Automatic failover between providers by priority
- TTL-based in-memory caching
- Rate limit graceful handling with backoff
- Provider health monitoring
- No mock data — all data comes from real APIs
- Market-type based provider selection
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from quant_nanggroe.data.providers.base import DataProvider
from quant_nanggroe.types.market import OHLCV, MarketData, OrderBook, Ticker, TimeFrame

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cached data entry with TTL."""
    data: Any
    created_at: float = field(default_factory=time.monotonic)
    ttl: float = 300.0  # 5 minutes default

    @property
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return (time.monotonic() - self.created_at) > self.ttl


class DataProviderManager:
    """Manages multiple data providers with automatic failover and caching.

    Inspired by HermesQuantOS AutoSwitch engine. Routes requests
    to the highest-priority healthy provider, falling back to
    alternatives on failure.

    Features:
    - Priority-based automatic failover
    - TTL-based in-memory caching
    - Rate limit handling with exponential backoff
    - Provider health monitoring and scoring
    - Market-type aware provider selection
    - Async-safe operations

    Usage:
        manager = DataProviderManager()
        manager.register(BinanceProvider(), markets=["crypto"])
        manager.register(YahooFinanceProvider(), markets=["stocks", "forex", "crypto"])

        data = await manager.get_ohlcv("BTC/USDT", TimeFrame.D1)
    """

    def __init__(self, default_cache_ttl: float = 300.0):
        """Initialize the DataProviderManager.

        Args:
            default_cache_ttl: Default cache TTL in seconds (default 5 minutes).
        """
        self._providers: Dict[str, DataProvider] = {}
        self._market_map: Dict[str, List[str]] = {}  # market -> provider names
        self._cache: Dict[str, CacheEntry] = {}
        self._default_cache_ttl = default_cache_ttl
        self._cache_lock = asyncio.Lock()

    def register(
        self,
        provider: DataProvider,
        markets: Optional[List[str]] = None,
    ) -> None:
        """Register a data provider.

        Args:
            provider: DataProvider instance to register
            markets: List of market types this provider supports
                     (e.g., ['crypto', 'stocks', 'forex', 'macro'])
        """
        self._providers[provider.name] = provider
        if markets:
            for market in markets:
                if market not in self._market_map:
                    self._market_map[market] = []
                if provider.name not in self._market_map[market]:
                    self._market_map[market].append(provider.name)
        logger.info(
            f"Registered data provider: {provider.name} "
            f"(priority={provider.priority}, markets={markets or 'all'})"
        )

    def _get_providers_for_symbol(self, symbol: str) -> List[DataProvider]:
        """Get available providers for a symbol, sorted by priority.

        Args:
            symbol: Trading pair symbol

        Returns:
            List of providers sorted by priority (lowest first)
        """
        market = self._infer_market(symbol)
        provider_names = self._market_map.get(market, list(self._providers.keys()))

        providers = [
            self._providers[name]
            for name in provider_names
            if name in self._providers and self._providers[name].is_available
        ]
        return sorted(providers, key=lambda p: p.priority)

    @staticmethod
    def _infer_market(symbol: str) -> str:
        """Infer market type from symbol format."""
        if symbol.startswith("FRED:"):
            return "macro"
        if symbol.startswith("ECB:"):
            return "forex"
        if symbol.startswith("WB:"):
            return "macro"
        # Crypto pairs: BTC/USDT, ETH/USDT, etc. (crypto base + stablecoin quote)
        if "/" in symbol:
            base, _, quote = symbol.partition("/")
            # Stablecoins and crypto-only quotes → crypto market
            crypto_quotes = {"USDT", "BUSD", "BTC", "ETH", "BNB", "USDC", "DAI"}
            if quote in crypto_quotes:
                return "crypto"
            # Major fiat pairs → forex (EUR/USD, GBP/JPY, etc.)
            fiat_currencies = {
                "USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD",
                "SEK", "NOK", "DKK", "SGD", "HKD", "MXN", "ZAR", "TRY",
                "INR", "CNY", "KRW", "BRL", "THB", "PLN", "CZK", "HUF",
                "RUB", "ILS", "PHP", "MYR", "IDR", "TWD", "SAR", "AED",
            }
            if quote in fiat_currencies and base in fiat_currencies:
                return "forex"
            # Mixed: could be crypto with fiat quote (BTC/USD, ETH/USD)
            crypto_bases = {
                "BTC", "ETH", "XRP", "LTC", "BCH", "ADA", "DOT", "LINK",
                "SOL", "MATIC", "AVAX", "DOGE", "SHIB", "UNI", "AAVE",
                "ATOM", "ALGO", "NEAR", "FTM", "XTZ", "FIL", "VET",
                "SAND", "MANA", "AXS", "CRV", "MKR", "COMP", "SNX",
            }
            if base in crypto_bases:
                return "crypto"
        if "=" in symbol or symbol.endswith("X"):
            return "forex"
        # CoinGecko-style lowercase IDs (e.g., 'bitcoin', 'ethereum')
        if symbol.islower() and not symbol.startswith("fred:") and not symbol.startswith("wb:"):
            return "crypto"
        return "stocks"

    def _cache_key(
        self,
        method: str,
        symbol: str,
        timeframe: Optional[TimeFrame] = None,
        **kwargs,
    ) -> str:
        """Generate a cache key for a request.

        Args:
            method: API method name (e.g., 'ohlcv', 'ticker', 'orderbook')
            symbol: Trading pair symbol
            timeframe: Optional timeframe
            **kwargs: Additional key components

        Returns:
            Cache key string
        """
        parts = [method, symbol]
        if timeframe:
            parts.append(timeframe.value)
        for k, v in sorted(kwargs.items()):
            if v is not None:
                parts.append(f"{k}={v}")
        return "|".join(parts)

    async def _get_cached(self, key: str) -> Optional[Any]:
        """Get data from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Cached data or None if not found or expired
        """
        async with self._cache_lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if entry.is_expired:
                del self._cache[key]
                return None
            return entry.data

    async def _set_cached(
        self,
        key: str,
        data: Any,
        ttl: Optional[float] = None,
    ) -> None:
        """Store data in cache with TTL.

        Args:
            key: Cache key
            data: Data to cache
            ttl: Cache TTL in seconds (uses default if None)
        """
        async with self._cache_lock:
            self._cache[key] = CacheEntry(
                data=data,
                ttl=ttl or self._default_cache_ttl,
            )

    async def _try_providers(
        self,
        method_name: str,
        symbol: str,
        *args,
        cache_ttl: Optional[float] = None,
        skip_cache: bool = False,
        **kwargs,
    ) -> Any:
        """Try a method on providers in priority order with caching and failover.

        Args:
            method_name: Provider method name (e.g., 'get_ohlcv')
            symbol: Trading pair symbol
            *args: Additional positional args for the provider method
            cache_ttl: Override cache TTL for this request
            skip_cache: If True, bypass cache and fetch fresh data
            **kwargs: Additional keyword args for the provider method

        Returns:
            Result from the first successful provider, or cached data
        """
        # Generate cache key
        timeframe = kwargs.get("timeframe", args[0] if args else None)
        cache_key = self._cache_key(
            method_name,
            symbol,
            timeframe=timeframe,
            **{k: v for k, v in kwargs.items() if k != "timeframe"},
        )

        # Check cache first
        if not skip_cache:
            cached = await self._get_cached(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached

        # Try providers in priority order
        providers = self._get_providers_for_symbol(symbol)

        if not providers:
            logger.warning(f"No available providers for {symbol}")
            # Try all providers regardless of market type
            providers = sorted(
                [p for p in self._providers.values() if p.is_available],
                key=lambda p: p.priority,
            )

        last_error: Optional[str] = None

        for provider in providers:
            method = getattr(provider, method_name, None)
            if method is None:
                continue

            try:
                result = await method(symbol, *args, **kwargs)

                # Check if result is valid
                if result is not None and result != [] and result != {}:
                    # Cache the successful result
                    await self._set_cached(cache_key, result, ttl=cache_ttl)
                    return result

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Provider {provider.name} failed for {symbol} "
                    f"{method_name}: {e}"
                )
                provider.mark_error(str(e))

                # If provider health is low, mark unavailable temporarily
                if provider.health_score < 0.3:
                    logger.warning(
                        f"Provider {provider.name} health score too low "
                        f"({provider.health_score:.2f}), marking unavailable"
                    )
                    # Schedule recovery after 60 seconds
                    asyncio.create_task(self._schedule_recovery(provider.name, 60))

        # All providers failed — check if we have stale cache
        stale_entry = self._cache.get(cache_key)
        if stale_entry is not None:
            logger.warning(
                f"All providers failed for {symbol} {method_name}, "
                f"returning stale cache (age: {time.monotonic() - stale_entry.created_at:.0f}s)"
            )
            return stale_entry.data

        logger.error(
            f"All providers failed for {symbol} {method_name}"
            f"{f': {last_error}' if last_error else ''}"
        )
        return None

    async def _schedule_recovery(self, provider_name: str, delay: float) -> None:
        """Schedule a provider recovery check after a delay.

        Args:
            provider_name: Name of the provider to recover
            delay: Delay in seconds before checking
        """
        await asyncio.sleep(delay)
        provider = self._providers.get(provider_name)
        if provider and not provider.is_available:
            try:
                is_healthy = await provider.health_check()
                if is_healthy:
                    provider.reset()
                    logger.info(f"Provider {provider_name} recovered and is available again")
                else:
                    # Schedule another check
                    asyncio.create_task(self._schedule_recovery(provider_name, delay * 2))
            except Exception:
                asyncio.create_task(self._schedule_recovery(provider_name, delay * 2))

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.D1,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
        cache_ttl: Optional[float] = None,
        skip_cache: bool = False,
    ) -> List[OHLCV]:
        """Fetch OHLCV data with automatic failover and caching.

        Tries each provider in priority order until one succeeds.

        Args:
            symbol: Trading pair symbol
            timeframe: Candle timeframe
            start: Start datetime
            end: End datetime
            limit: Maximum number of candles
            cache_ttl: Override cache TTL for this request
            skip_cache: If True, bypass cache and fetch fresh data

        Returns:
            List of OHLCV candles, or empty list if all providers fail
        """
        result = await self._try_providers(
            "get_ohlcv",
            symbol,
            timeframe,
            start=start,
            end=end,
            limit=limit,
            cache_ttl=cache_ttl,
            skip_cache=skip_cache,
        )
        return result or []

    async def get_ticker(
        self,
        symbol: str,
        cache_ttl: Optional[float] = None,
        skip_cache: bool = False,
    ) -> Optional[Ticker]:
        """Fetch ticker with automatic failover and caching."""
        return await self._try_providers(
            "get_ticker",
            symbol,
            cache_ttl=cache_ttl or 60.0,  # Shorter TTL for ticker data
            skip_cache=skip_cache,
        )

    async def get_orderbook(
        self,
        symbol: str,
        limit: int = 20,
        skip_cache: bool = True,  # Order book data should be fresh
    ) -> Optional[OrderBook]:
        """Fetch order book with automatic failover.

        Note: Order book data is not cached by default since it changes rapidly.
        """
        return await self._try_providers(
            "get_orderbook",
            symbol,
            limit,
            cache_ttl=5.0,  # Very short TTL for order books
            skip_cache=skip_cache,
        )

    async def get_market_data(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.D1,
        include_ohlcv: bool = True,
        include_ticker: bool = True,
        include_orderbook: bool = False,
    ) -> MarketData:
        """Fetch aggregated market data for a symbol.

        Uses failover for each component independently.

        Args:
            symbol: Trading pair symbol
            timeframe: Candle timeframe
            include_ohlcv: Whether to include OHLCV data
            include_ticker: Whether to include ticker data
            include_orderbook: Whether to include order book data

        Returns:
            Aggregated MarketData object
        """
        ohlcv = await self.get_ohlcv(symbol, timeframe) if include_ohlcv else []
        ticker = await self.get_ticker(symbol) if include_ticker else None
        orderbook = await self.get_orderbook(symbol) if include_orderbook else None

        # Determine which provider actually provided data
        provider_name = "unknown"
        if ticker:
            provider_name = "multiple"
        elif ohlcv:
            provider_name = "multiple"

        return MarketData(
            symbol=symbol,
            timeframe=timeframe,
            ohlcv=ohlcv,
            ticker=ticker,
            orderbook=orderbook,
            provider=provider_name,
        )

    async def health_check_all(self) -> Dict[str, bool]:
        """Check health of all registered providers."""
        results = {}
        tasks = []
        for name, provider in self._providers.items():
            tasks.append(self._check_provider_health(name, provider))

        health_results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, (name, _) in enumerate(self._providers.items()):
            result = health_results[i]
            if isinstance(result, Exception):
                results[name] = False
            else:
                results[name] = result

        return results

    async def _check_provider_health(
        self, name: str, provider: DataProvider
    ) -> bool:
        """Check health of a single provider."""
        try:
            return await provider.health_check()
        except Exception:
            return False

    def get_status(self) -> Dict[str, Dict]:
        """Get status information for all providers."""
        return {
            name: {
                "available": p.is_available,
                "priority": p.priority,
                "health_score": p.health_score,
                "last_error": p.last_error,
                "request_count": p._request_count,
                "error_count": p._error_count,
            }
            for name, p in self._providers.items()
        }

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_entries = len(self._cache)
        expired_entries = sum(
            1 for entry in self._cache.values() if entry.is_expired
        )
        return {
            "total_entries": total_entries,
            "expired_entries": expired_entries,
            "active_entries": total_entries - expired_entries,
            "default_ttl": self._default_cache_ttl,
        }

    async def clear_cache(self) -> None:
        """Clear all cached data."""
        async with self._cache_lock:
            self._cache.clear()
        logger.info("Data cache cleared")

    async def close_all(self) -> None:
        """Close all providers and release resources."""
        for name, provider in self._providers.items():
            try:
                if hasattr(provider, "close"):
                    await provider.close()
                logger.info(f"Closed provider: {name}")
            except Exception as e:
                logger.warning(f"Error closing provider {name}: {e}")
        await self.clear_cache()


# ---------------------------------------------------------------------------
# Factory: build a manager with all key-gated optional providers registered.
# Fail-closed: a provider whose API key is absent is simply skipped (logged),
# never crashes import or startup. No silent mock data.
# ---------------------------------------------------------------------------

def build_provider_manager(default_cache_ttl: float = 300.0) -> "DataProviderManager":
    """Construct a DataProviderManager and register every available provider.

    Each optional provider is key-gated on its environment variable:
      - Alpha Vantage  -> QNAI_ALPHA_VANTAGE_API_KEY
      - Polygon        -> QNAI_POLYGON_API_KEY
      - Twelve Data    -> QNAI_TWELVEDATA_API_KEY
      - FRED           -> FRED_API_KEY
      - OpenBB         -> OPENBB_TOKEN (requires `openbb` SDK; skipped if absent)
      - LSE            -> LSE_API_KEY (not a DataProvider subclass; skipped in manager)

    Returns a manager with only the providers that could be constructed.
    """
    import os
    import logging as _log
    _l = _log.getLogger(__name__)

    manager = DataProviderManager(default_cache_ttl=default_cache_ttl)

    # Direct key-gated providers (subclass DataProvider, take api_key=)
    _direct = [
        ("alpha_vantage", "AlphaVantageProvider", "QNAI_ALPHA_VANTAGE_API_KEY", ["stocks", "forex", "crypto", "macro"]),
        ("polygon", "PolygonProvider", "QNAI_POLYGON_API_KEY", ["stocks", "forex", "crypto"]),
        ("twelvedata", "TwelveDataProvider", "QNAI_TWELVEDATA_API_KEY", ["stocks", "forex", "crypto"]),
    ]
    for mod, cls, env_key, markets in _direct:
        key = os.environ.get(env_key)
        if not key:
            _l.info("Provider %s skipped (no %s)", mod, env_key)
            continue
        try:
            import importlib
            m = importlib.import_module(f"quant_nanggroe.data.providers.{mod}")
            provider = getattr(m, cls)(api_key=key)
            manager.register(provider, markets=markets)
            _l.info("Provider %s registered (key present)", mod)
        except Exception as e:  # noqa: BLE001 - fail-closed
            _l.warning("Provider %s failed to construct: %s", mod, e)

    # Adapter providers (inner provider wrapped by a DataProvider adapter)
    # FRED: FREDProvider(api_key) -> FREDProviderAdapter
    fred_key = os.environ.get("FRED_API_KEY")
    if fred_key:
        try:
            import importlib
            m = importlib.import_module("quant_nanggroe.data.providers.fred")
            inner = m.FREDProvider(api_key=fred_key)
            adapter = m.FREDProviderAdapter(inner)
            manager.register(adapter, markets=["macro"])
            _l.info("Provider fred registered")
        except Exception as e:  # noqa: BLE001
            _l.warning("Provider fred failed: %s", e)
    else:
        _l.info("Provider fred skipped (no FRED_API_KEY)")

    # Twelve Data adapter: TwelveDataProvider(api_key) -> TwelveDataProviderAdapter
    td_key = os.environ.get("QNAI_TWELVEDATA_API_KEY")
    if td_key:
        try:
            import importlib
            m = importlib.import_module("quant_nanggroe.data.providers.twelvedata")
            inner = m.TwelveDataProvider(api_key=td_key)
            adapter = m.TwelveDataProviderAdapter(inner)
            manager.register(adapter, markets=["stocks", "forex", "crypto"])
            _l.info("Provider twelvedata adapter registered")
        except Exception as e:  # noqa: BLE001
            _l.warning("Provider twelvedata adapter failed: %s", e)
    else:
        _l.info("Provider twelvedata skipped (no QNAI_TWELVEDATA_API_KEY)")

    # OpenBB: requires `openbb` SDK; skipped silently if not installed
    openbb_token = os.environ.get("OPENBB_TOKEN")
    if openbb_token:
        try:
            import importlib
            m = importlib.import_module("quant_nanggroe.data.providers.openbb_mcp")
            inner = m.OpenBBMCPProvider(api_key=openbb_token)
            adapter = m.OpenBBMCPProviderAdapter(inner)
            manager.register(adapter, markets=["stocks", "forex", "crypto", "macro"])
            _l.info("Provider openbb registered")
        except Exception as e:  # noqa: BLE001
            _l.warning("Provider openbb failed (SDK missing?): %s", e)
    else:
        _l.info("Provider openbb skipped (no OPENBB_TOKEN or SDK absent)")

    return manager
