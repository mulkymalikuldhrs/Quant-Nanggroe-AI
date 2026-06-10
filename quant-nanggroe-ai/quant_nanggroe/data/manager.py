"""DataProviderManager with failover support.

Manages multiple data providers with automatic failover, health tracking,
and provider selection — inspired by Quant-Nanggroe-AI's AutoSwitch system
(HermesQuantOS AutoSwitch).

The manager tries providers in priority order, falling back to the next
provider on failure. Health status is tracked to proactively avoid
failing providers.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from quant_nanggroe.data.cache import DataCache
from quant_nanggroe.data.providers.base import DataProvider
from quant_nanggroe.types.market import OHLCV, Interval, OrderBook, Ticker
from quant_nanggroe.config.settings import get_settings

logger = logging.getLogger("quant_nanggroe.data.manager")


@dataclass
class ProviderHealth:
    """Health tracking for a single data provider."""

    last_success: float = 0.0
    last_failure: float = 0.0
    failure_count: int = 0
    success_count: int = 0
    cooldown_until: float = 0.0

    @property
    def is_healthy(self) -> bool:
        """Check if the provider is not in cooldown."""
        if self.cooldown_until > 0 and time.time() < self.cooldown_until:
            return False
        # Proactive: if many recent failures, cool down
        if self.failure_count > 5 and time.time() - self.last_success > 60:
            return False
        return True

    def record_success(self) -> None:
        self.last_success = time.time()
        self.success_count += 1
        self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self, cooldown_seconds: float = 30.0) -> None:
        self.last_failure = time.time()
        self.failure_count += 1
        # Set cooldown for repeated failures (3+), or on explicit long cooldown
        if self.failure_count >= 3 or cooldown_seconds >= 60:
            self.cooldown_until = time.time() + cooldown_seconds


class DataProviderManager:
    """Manager for multiple data providers with automatic failover.

    Features:
    - Priority-ordered provider selection
    - Health tracking per provider
    - Automatic failover on errors
    - Caching layer with TTL
    - Rate-limit-aware retry with exponential backoff

    Usage::

        manager = DataProviderManager([yahoo, binance, alpaca])
        candles = await manager.get_ohlcv("BTC/USDT")
    """

    def __init__(
        self,
        providers: Optional[list[DataProvider]] = None,
    ) -> None:
        self._providers: dict[str, DataProvider] = {}
        self._priority: list[str] = []
        self._health: dict[str, ProviderHealth] = {}
        self._cache = DataCache()

        settings = get_settings()
        self._max_retries = settings.autoswitch_max_retries
        self._retry_delay = settings.autoswitch_retry_delay_ms / 1000.0
        self._cooldown_seconds = settings.autoswitch_cooldown_ms / 1000.0

        if providers:
            for p in providers:
                self.register(p)

    def register(self, provider: DataProvider, priority: Optional[int] = None) -> None:
        """Register a data provider.

        Args:
            provider: DataProvider instance to register.
            priority: Priority index (lower = tried first). If None, appended last.
        """
        name = provider.name
        self._providers[name] = provider
        self._health[name] = ProviderHealth()

        if priority is not None:
            self._priority.insert(priority, name)
        else:
            self._priority.append(name)

        logger.info(f"Registered data provider: {name}")

    def unregister(self, name: str) -> None:
        """Remove a provider by name."""
        self._providers.pop(name, None)
        self._health.pop(name, None)
        if name in self._priority:
            self._priority.remove(name)

    def _get_healthy_providers(self) -> list[DataProvider]:
        """Return providers sorted by health (fewest failures first)."""
        healthy = []
        for name in self._priority:
            health = self._health.get(name)
            provider = self._providers.get(name)
            if provider and health and health.is_healthy and provider.is_available:
                healthy.append(provider)

        # Sort by health: fewest failures, then most successes
        healthy.sort(
            key=lambda p: (
                self._health[p.name].failure_count,
                -self._health[p.name].success_count,
            )
        )

        return healthy

    async def get_ohlcv(
        self,
        symbol: str,
        interval: Interval = Interval.DAY_1,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> list[OHLCV]:
        """Fetch OHLCV data with automatic failover.

        Tries providers in health-priority order, falling back on failure.
        Results are cached for the configured TTL.
        """
        # Check cache first
        cache_key = DataCache.make_key(
            "ohlcv", symbol=symbol, interval=interval.value, limit=limit
        )
        cached = self._cache.get_json(cache_key)
        if cached:
            return [OHLCV(**c) for c in cached]

        providers = self._get_healthy_providers()
        last_error: Optional[Exception] = None

        for provider in providers:
            for attempt in range(self._max_retries):
                try:
                    result = await provider.get_ohlcv(symbol, interval, start, end, limit)
                    if result:
                        self._health[provider.name].record_success()
                        # Cache the result
                        self._cache.set_json(
                            cache_key, [c.model_dump(mode="json") for c in result]
                        )
                        return result
                except Exception as e:
                    self._health[provider.name].record_failure(self._cooldown_seconds)
                    last_error = e
                    logger.warning(
                        f"Provider {provider.name} failed (attempt {attempt + 1}): {e}"
                    )
                    if attempt < self._max_retries - 1:
                        await asyncio.sleep(self._retry_delay * (2**attempt))

        logger.error(f"All providers failed for OHLCV {symbol}: {last_error}")
        return []

    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Fetch ticker data with automatic failover."""
        cache_key = DataCache.make_key("ticker", symbol=symbol)
        cached = self._cache.get_json(cache_key)
        if cached:
            return Ticker(**cached)

        providers = self._get_healthy_providers()
        for provider in providers:
            try:
                result = await provider.get_ticker(symbol)
                if result:
                    self._health[provider.name].record_success()
                    self._cache.set_json(cache_key, result.model_dump(mode="json"), ttl=30)
                    return result
            except Exception as e:
                self._health[provider.name].record_failure(self._cooldown_seconds)
                logger.warning(f"Provider {provider.name} failed for ticker {symbol}: {e}")

        return None

    async def get_orderbook(self, symbol: str, depth: int = 20) -> Optional[OrderBook]:
        """Fetch order book with automatic failover."""
        providers = self._get_healthy_providers()
        for provider in providers:
            try:
                result = await provider.get_orderbook(symbol, depth)
                if result and (result.bids or result.asks):
                    self._health[provider.name].record_success()
                    return result
            except Exception as e:
                self._health[provider.name].record_failure(self._cooldown_seconds)
                logger.warning(f"Provider {provider.name} failed for orderbook {symbol}: {e}")

        return None

    async def get_fundamentals(self, symbol: str) -> dict:
        """Fetch fundamental data with automatic failover."""
        providers = self._get_healthy_providers()
        for provider in providers:
            try:
                result = await provider.get_fundamentals(symbol)
                if result:
                    self._health[provider.name].record_success()
                    return result
            except Exception as e:
                self._health[provider.name].record_failure(self._cooldown_seconds)
                logger.warning(f"Provider {provider.name} failed for fundamentals {symbol}: {e}")

        return {}

    def get_health_report(self) -> dict[str, dict[str, Any]]:
        """Return health status for all registered providers."""
        report: dict[str, dict[str, Any]] = {}
        for name, health in self._health.items():
            report[name] = {
                "is_healthy": health.is_healthy,
                "failure_count": health.failure_count,
                "success_count": health.success_count,
                "last_success": health.last_success,
                "last_failure": health.last_failure,
                "cooldown_until": health.cooldown_until,
            }
        return report
