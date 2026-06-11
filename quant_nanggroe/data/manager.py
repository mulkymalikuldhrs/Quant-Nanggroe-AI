"""Data Provider Manager with automatic failover.

Manages multiple data providers and routes requests to the best
available provider based on priority and health.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional

from quant_nanggroe.data.providers.base import DataProvider
from quant_nanggroe.types.market import OHLCV, MarketData, OrderBook, Ticker, TimeFrame

logger = logging.getLogger(__name__)


class DataProviderManager:
    """
    Manages multiple data providers with automatic failover.

    Inspired by HermesQuantOS AutoSwitch engine. Routes requests
    to the highest-priority healthy provider, falling back to
    alternatives on failure.

    Usage:
        manager = DataProviderManager()
        manager.register(BinanceProvider(api_key="..."), markets=["crypto"])
        manager.register(YahooFinanceProvider(), markets=["stocks", "forex"])

        data = await manager.get_ohlcv("BTC/USDT", TimeFrame.D1)
    """

    def __init__(self):
        self._providers: Dict[str, DataProvider] = {}
        self._market_map: Dict[str, List[str]] = {}  # market → provider names

    def register(
        self,
        provider: DataProvider,
        markets: Optional[List[str]] = None,
    ) -> None:
        """
        Register a data provider.

        Args:
            provider: DataProvider instance to register
            markets: List of market types this provider supports
                     (e.g., ['crypto', 'stocks', 'forex'])
        """
        self._providers[provider.name] = provider
        if markets:
            for market in markets:
                if market not in self._market_map:
                    self._market_map[market] = []
                self._market_map[market].append(provider.name)
        logger.info(f"Registered data provider: {provider.name} (priority={provider.priority})")

    def _get_providers_for_symbol(self, symbol: str) -> List[DataProvider]:
        """
        Get available providers for a symbol, sorted by priority.

        Args:
            symbol: Trading pair symbol

        Returns:
            List of providers sorted by priority (lowest first)
        """
        # Determine market type from symbol
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
        if "/" in symbol and any(
            symbol.endswith(f"/{fiat}") for fiat in ["USDT", "BUSD", "USD", "BTC", "ETH"]
        ):
            return "crypto"
        elif "=" in symbol or symbol.endswith("X"):
            return "forex"
        else:
            return "stocks"

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.D1,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[OHLCV]:
        """
        Fetch OHLCV data with automatic failover.

        Tries each provider in priority order until one succeeds.

        Args:
            symbol: Trading pair symbol
            timeframe: Candle timeframe
            start: Start datetime
            end: End datetime
            limit: Maximum number of candles

        Returns:
            List of OHLCV candles, or empty list if all providers fail
        """
        providers = self._get_providers_for_symbol(symbol)
        for provider in providers:
            try:
                result = await provider.get_ohlcv(symbol, timeframe, start, end, limit)
                if result:
                    return result
            except Exception as e:
                logger.warning(
                    f"Provider {provider.name} failed for {symbol} OHLCV: {e}"
                )
                provider.mark_error(str(e))

        logger.error(f"All providers failed for {symbol} OHLCV")
        return []

    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Fetch ticker with automatic failover."""
        providers = self._get_providers_for_symbol(symbol)
        for provider in providers:
            try:
                result = await provider.get_ticker(symbol)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"Provider {provider.name} failed for {symbol} ticker: {e}")
                provider.mark_error(str(e))
        return None

    async def get_orderbook(self, symbol: str, limit: int = 20) -> Optional[OrderBook]:
        """Fetch order book with automatic failover."""
        providers = self._get_providers_for_symbol(symbol)
        for provider in providers:
            try:
                result = await provider.get_orderbook(symbol, limit)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"Provider {provider.name} failed for {symbol} orderbook: {e}")
                provider.mark_error(str(e))
        return None

    async def health_check_all(self) -> Dict[str, bool]:
        """Check health of all registered providers."""
        results = {}
        for name, provider in self._providers.items():
            try:
                results[name] = await provider.health_check()
            except Exception:
                results[name] = False
        return results

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
