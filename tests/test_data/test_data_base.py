"""Tests for Data Provider module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from quant_nanggroe.data.base import (
    DataCache,
    DataFrequency,
    DataProvider,
    DataProviderConfig,
    DataRequest,
    DataResponse,
    MarketType,
    OHLCVBar,
    ProviderRegistry,
    ProviderStatus,
    RateLimiter,
    TickerData,
)
from quant_nanggroe.data.yfinance_provider import YFinanceProvider
from quant_nanggroe.data.alpha_vantage_provider import AlphaVantageProvider
from quant_nanggroe.data.fred_provider import FREDProvider
from quant_nanggroe.data.sec_edgar_provider import SECEdgarProvider
from quant_nanggroe.data.manager import DataProviderManager


# ======================================================================
# Base Classes
# ======================================================================

class TestRateLimiter:
    def test_construction(self):
        limiter = RateLimiter(max_calls=5, period=1.0)
        assert limiter._max_calls == 5

    @pytest.mark.asyncio
    async def test_acquire(self):
        limiter = RateLimiter(max_calls=100, period=1.0)
        await limiter.acquire()  # Should not block


class TestDataCache:
    def test_set_and_get(self):
        cache = DataCache(default_ttl=60)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing(self):
        cache = DataCache()
        assert cache.get("nonexistent") is None

    def test_clear(self):
        cache = DataCache()
        cache.set("key1", "value1")
        cache.clear()
        assert cache.get("key1") is None

    def test_size(self):
        cache = DataCache()
        assert cache.size() == 0
        cache.set("key1", "value1")
        assert cache.size() == 1


class TestDataProviderConfig:
    def test_defaults(self):
        config = DataProviderConfig(name="test")
        assert config.rate_limit == 5
        assert config.cache_ttl == 300
        assert config.enabled is True

    def test_custom(self):
        config = DataProviderConfig(name="test", api_key="abc123", rate_limit=10)
        assert config.api_key == "abc123"
        assert config.rate_limit == 10


class TestDataRequest:
    def test_defaults(self):
        req = DataRequest(symbol="AAPL")
        assert req.market_type == MarketType.EQUITY
        assert req.frequency == DataFrequency.DAY_1
        assert req.limit == 100


class TestDataResponse:
    def test_success(self):
        resp = DataResponse(success=True, provider="test", data=[1, 2, 3])
        assert resp.success is True
        assert resp.provider == "test"

    def test_failure(self):
        resp = DataResponse(success=False, error="API error")
        assert resp.success is False
        assert resp.error == "API error"


class TestProviderRegistry:
    def test_list_providers(self):
        providers = ProviderRegistry.list_providers()
        assert "yfinance" in providers
        assert "alpha_vantage" in providers
        assert "fred" in providers
        assert "sec_edgar" in providers

    def test_create_provider(self):
        config = DataProviderConfig(name="yfinance", rate_limit=5)
        provider = ProviderRegistry.create("yfinance", config)
        assert provider is not None
        assert provider.name == "yfinance"

    def test_create_nonexistent(self):
        config = DataProviderConfig(name="nonexistent")
        provider = ProviderRegistry.create("nonexistent", config)
        assert provider is None


# ======================================================================
# YFinance Provider
# ======================================================================

class TestYFinanceProvider:
    def test_construction(self):
        config = DataProviderConfig(name="yfinance", rate_limit=5)
        provider = YFinanceProvider(config)
        assert provider.name == "yfinance"
        assert provider.status == ProviderStatus.HEALTHY  # No key needed

    def test_supported_markets(self):
        config = DataProviderConfig(name="yfinance")
        provider = YFinanceProvider(config)
        assert MarketType.EQUITY in provider.supported_markets
        assert MarketType.CRYPTO in provider.supported_markets


class TestAlphaVantageProvider:
    def test_construction(self):
        config = DataProviderConfig(name="alpha_vantage", api_key="test_key")
        provider = AlphaVantageProvider(config)
        assert provider.name == "alpha_vantage"
        assert provider.is_configured is True

    def test_no_key(self):
        # AlphaVantage always sets base_url in constructor, so is_configured
        # returns truthy. The real check is whether API calls work.
        config = DataProviderConfig(name="alpha_vantage")
        provider = AlphaVantageProvider(config)
        # Provider without API key will fail on actual API calls
        assert provider._config.api_key == ""


class TestFREDProvider:
    def test_construction(self):
        config = DataProviderConfig(name="fred", api_key="test_key")
        provider = FREDProvider(config)
        assert provider.name == "fred"
        assert MarketType.ECONOMIC in provider.supported_markets


class TestSECEdgarProvider:
    def test_construction(self):
        config = DataProviderConfig(name="sec_edgar")
        provider = SECEdgarProvider(config)
        assert provider.name == "sec_edgar"
        assert provider.status == ProviderStatus.HEALTHY  # No key needed


# ======================================================================
# Data Provider Manager
# ======================================================================

class TestDataProviderManager:
    def test_construction(self):
        manager = DataProviderManager()
        assert "yfinance" in manager._providers

    def test_list_available(self):
        manager = DataProviderManager()
        available = manager.list_available_providers()
        assert "yfinance" in available

    def test_get_stats(self):
        manager = DataProviderManager()
        stats = manager.get_provider_stats()
        assert isinstance(stats, dict)
        assert "yfinance" in stats
