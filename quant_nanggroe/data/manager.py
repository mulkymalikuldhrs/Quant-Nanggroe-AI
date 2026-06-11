"""Data Provider Manager — Unified routing across all data providers.

Routes data requests to the appropriate provider based on
market type, symbol, and provider availability.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from quant_nanggroe.data.base import (
    DataFrequency,
    DataProvider,
    DataProviderConfig,
    DataRequest,
    DataResponse,
    MarketType,
    ProviderRegistry,
    ProviderStatus,
)
from quant_nanggroe.config.settings import get_settings

logger = logging.getLogger(__name__)


class DataProviderManager:
    """Unified data provider manager.

    Manages multiple data providers, routes requests based on
    market type and provider availability, and provides fallback
    when primary providers fail.

    Usage::

        manager = DataProviderManager()
        await manager.initialize()

        # Auto-routes to appropriate provider
        response = await manager.get_ohlcv(DataRequest(symbol="AAPL"))
        response = await manager.get_ohlcv(DataRequest(symbol="BTC/USDT", market_type=MarketType.CRYPTO))
    """

    # Default provider mapping by market type
    DEFAULT_PROVIDERS = {
        MarketType.EQUITY: ["yfinance", "polygon", "fmp", "alpha_vantage", "twelvedata"],
        MarketType.CRYPTO: ["coingecko", "ccxt_data", "yfinance"],
        MarketType.FOREX: ["yfinance", "alpha_vantage", "twelvedata"],
        MarketType.FUTURES: ["yfinance", "polygon"],
        MarketType.ECONOMIC: ["fred"],
        MarketType.ALTERNATIVE: ["sec_edgar"],
    }

    def __init__(self, configs: Optional[Dict[str, DataProviderConfig]] = None) -> None:
        self._providers: Dict[str, DataProvider] = {}
        self._initialized = False

        # Auto-discover and create providers
        if configs:
            for name, config in configs.items():
                provider = ProviderRegistry.create(name, config)
                if provider is not None:
                    self._providers[name] = provider
        else:
            self._auto_configure()

    def _auto_configure(self) -> None:
        """Auto-configure providers from environment variables."""
        try:
            settings = get_settings()
        except Exception:
            settings = None

        # YFinance - no API key needed
        self._providers["yfinance"] = ProviderRegistry.create(
            "yfinance", DataProviderConfig(name="yfinance", rate_limit=5, cache_ttl=300)
        ) or self._create_fallback("yfinance")

        # Providers that need API keys
        provider_configs = {
            "alpha_vantage": ("alpha_vantage", getattr(settings, "alpha_vantage_api_key", "") or ""),
            "polygon": ("polygon", getattr(settings, "polygon_api_key", "") or ""),
            "fmp": ("fmp", getattr(settings, "fmp_api_key", "") or ""),
            "fred": ("fred", getattr(settings, "fred_api_key", "") or ""),
            "twelvedata": ("twelvedata", getattr(settings, "twelvedata_api_key", "") or ""),
            "sec_edgar": ("sec_edgar", ""),
            "coingecko": ("coingecko", getattr(settings, "coingecko_api_key", "") or ""),
            "ccxt_data": ("ccxt_data", getattr(settings, "binance_api_key", "") or ""),
        }

        for key, (provider_name, api_key) in provider_configs.items():
            config = DataProviderConfig(
                name=provider_name,
                api_key=api_key,
                rate_limit=2,
                cache_ttl=300,
            )
            provider = ProviderRegistry.create(provider_name, config)
            if provider is not None:
                self._providers[key] = provider

    def _create_fallback(self, name: str) -> DataProvider:
        """Create a minimal fallback provider entry."""
        # This shouldn't happen if registration works
        raise ValueError(f"Provider {name} not registered")

    async def initialize(self) -> bool:
        """Initialize all providers and check health."""
        for name, provider in self._providers.items():
            try:
                await provider.initialize()
                status = await provider.health_check()
                logger.info("Provider %s: %s", name, status.value)
            except Exception as exc:
                logger.warning("Provider %s init failed: %s", name, exc)

        self._initialized = True
        return True

    def _get_providers_for_market(self, market_type: MarketType) -> List[DataProvider]:
        """Get providers ordered by preference for a market type."""
        preferred = self.DEFAULT_PROVIDERS.get(market_type, [])
        providers = []

        for name in preferred:
            if name in self._providers:
                provider = self._providers[name]
                if provider.status in (ProviderStatus.HEALTHY, ProviderStatus.DEGRADED):
                    providers.append(provider)

        return providers

    async def _route_request(
        self,
        market_type: MarketType,
        method_name: str,
        *args,
        provider_hint: Optional[str] = None,
        **kwargs,
    ) -> DataResponse:
        """Route a request to the best available provider.

        Tries providers in order of preference. Falls back to next
        provider if current one fails.
        """
        # Try specific provider if hinted
        if provider_hint and provider_hint in self._providers:
            provider = self._providers[provider_hint]
            if provider.status in (ProviderStatus.HEALTHY, ProviderStatus.DEGRADED):
                method = getattr(provider, method_name)
                response = await method(*args, **kwargs)
                if response.success:
                    return response

        # Try providers in order
        providers = self._get_providers_for_market(market_type)

        for provider in providers:
            try:
                method = getattr(provider, method_name)
                response = await method(*args, **kwargs)
                if response.success:
                    return response
            except Exception as exc:
                logger.debug(
                    "Provider %s failed for %s: %s",
                    provider.name, method_name, exc,
                )
                continue

        return DataResponse(
            success=False,
            error=f"No available provider for {market_type.value}",
        )

    async def get_ohlcv(self, request: DataRequest) -> DataResponse:
        """Get OHLCV data, routed to appropriate provider."""
        return await self._route_request(
            request.market_type,
            "get_ohlcv",
            request,
            provider_hint=request.provider_hint,
        )

    async def get_ticker(self, symbol: str, market_type: MarketType = MarketType.EQUITY) -> DataResponse:
        """Get ticker data, routed to appropriate provider."""
        return await self._route_request(market_type, "get_ticker", symbol)

    async def get_fundamentals(self, symbol: str, market_type: MarketType = MarketType.EQUITY) -> DataResponse:
        """Get fundamentals, routed to appropriate provider."""
        return await self._route_request(market_type, "get_fundamentals", symbol)

    async def get_news(self, symbol: str, market_type: MarketType = MarketType.EQUITY, limit: int = 10) -> DataResponse:
        """Get news, routed to appropriate provider."""
        return await self._route_request(market_type, "get_news", symbol, limit)

    def get_provider_stats(self) -> Dict[str, Any]:
        """Get statistics for all providers."""
        return {
            name: provider.get_stats()
            for name, provider in self._providers.items()
        }

    def list_available_providers(self) -> List[str]:
        """List names of available providers."""
        return [
            name for name, provider in self._providers.items()
            if provider.status in (ProviderStatus.HEALTHY, ProviderStatus.DEGRADED)
        ]


__all__ = ["DataProviderManager"]
