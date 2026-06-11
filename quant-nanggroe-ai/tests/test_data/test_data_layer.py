"""Tests for quant_nanggroe.data — data providers, cache, normalizer, manager."""

import os
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("CACHE_BACKEND", "memory")

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from quant_nanggroe.data.cache import DataCache, MemoryCache, FileCache
from quant_nanggroe.data.normalizer import normalize_ohlcv, normalize_ticker, normalize_orderbook
from quant_nanggroe.data.manager import DataProviderManager, ProviderHealth
from quant_nanggroe.data.providers.base import DataProvider
from quant_nanggroe.types.market import OHLCV, Interval, Ticker


# ── Cache Tests ──


class TestMemoryCache:
    def test_set_and_get(self):
        cache = MemoryCache()
        cache.set("test_key", "test_value", ttl=60)
        assert cache.get("test_key") == "test_value"

    def test_expired_entry(self):
        cache = MemoryCache()
        cache.set("test_key", "test_value", ttl=0)  # Immediately expired
        assert cache.get("test_key") is None

    def test_delete(self):
        cache = MemoryCache()
        cache.set("test_key", "test_value", ttl=60)
        cache.delete("test_key")
        assert cache.get("test_key") is None

    def test_exists(self):
        cache = MemoryCache()
        cache.set("test_key", "test_value", ttl=60)
        assert cache.exists("test_key") is True
        assert cache.exists("nonexistent") is False


class TestFileCache:
    def test_set_and_get(self, tmp_path):
        cache = FileCache(cache_dir=str(tmp_path / "cache"))
        cache.set("test_key", "test_value", ttl=60)
        assert cache.get("test_key") == "test_value"

    def test_expired_entry(self, tmp_path):
        cache = FileCache(cache_dir=str(tmp_path / "cache"))
        cache.set("test_key", "test_value", ttl=0)
        assert cache.get("test_key") is None


class TestDataCache:
    def test_make_key(self):
        key = DataCache.make_key("ohlcv", symbol="BTC", interval="1d")
        assert "ohlcv" in key
        assert "BTC" in key

    def test_set_and_get_json(self):
        cache = DataCache()
        cache.set_json("test", {"key": "value"}, ttl=60)
        result = cache.get_json("test")
        assert result == {"key": "value"}

    def test_cache_disabled(self):
        os.environ["CACHE_ENABLED"] = "false"
        try:
            # Reset settings singleton to pick up env change
            import quant_nanggroe.config.settings as _settings
            _settings._settings = None
            cache = DataCache()
            cache.set_json("test", {"key": "value"})
            assert cache.get_json("test") is None
        finally:
            os.environ["CACHE_ENABLED"] = "true"
            import quant_nanggroe.config.settings as _settings
            _settings._settings = None

    def test_invalidate(self):
        cache = DataCache()
        cache.set_json("test", {"key": "value"}, ttl=60)
        cache.invalidate("test")
        assert cache.get_json("test") is None


# ── Normalizer Tests ──


class TestNormalizeOHLCV:
    def test_standard_keys(self):
        raw = [
            {
                "timestamp": "2024-01-15T00:00:00Z",
                "open": 42500.0,
                "high": 43100.0,
                "low": 42200.0,
                "close": 42800.0,
                "volume": 12345.0,
            }
        ]
        result = normalize_ohlcv(raw, "BTC/USDT", "test")
        assert len(result) == 1
        assert result[0].symbol == "BTC/USDT"
        assert result[0].open == 42500.0

    def test_yfinance_keys(self):
        raw = [
            {
                "Date": "2024-01-15",
                "Open": 42500.0,
                "High": 43100.0,
                "Low": 42200.0,
                "Close": 42800.0,
                "Volume": 12345.0,
            }
        ]
        result = normalize_ohlcv(raw, "BTC/USDT", "test")
        assert len(result) == 1
        assert result[0].close == 42800.0

    def test_ccxt_keys(self):
        raw = [
            {
                "t": 1705276800000,
                "o": 42500.0,
                "h": 43100.0,
                "l": 42200.0,
                "c": 42800.0,
                "v": 12345.0,
            }
        ]
        result = normalize_ohlcv(raw, "BTC/USDT", "test")
        assert len(result) == 1

    def test_empty_data(self):
        result = normalize_ohlcv([], "BTC/USDT", "test")
        assert len(result) == 0


class TestNormalizeTicker:
    def test_standard_keys(self):
        raw = {
            "current_price": 42800.0,
            "price_change_24h": 800.0,
            "price_change_pct_24h": 1.9,
        }
        result = normalize_ticker(raw, "BTC/USDT", "test")
        assert result.symbol == "BTC/USDT"
        assert result.current_price == 42800.0

    def test_ccxt_keys(self):
        raw = {
            "last": 42800.0,
            "change": 800.0,
            "percentage": 1.9,
        }
        result = normalize_ticker(raw, "BTC/USDT", "test")
        assert result.current_price == 42800.0


class TestNormalizeOrderBook:
    def test_array_format(self):
        raw = {
            "bids": [[42790.0, 1.5], [42780.0, 2.0]],
            "asks": [[42810.0, 1.2], [42820.0, 0.8]],
        }
        result = normalize_orderbook(raw, "BTC/USDT", "test")
        assert len(result.bids) == 2
        assert len(result.asks) == 2
        assert result.best_bid == 42790.0


# ── Manager Tests ──


class MockProvider(DataProvider):
    """Mock data provider for testing."""

    def __init__(self, name: str = "mock", should_fail: bool = False):
        self._name = name
        self._should_fail = should_fail

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_available(self) -> bool:
        return not self._should_fail

    async def get_ohlcv(self, symbol, interval=Interval.DAY_1, start=None, end=None, limit=500):
        if self._should_fail:
            raise ConnectionError(f"Provider {self._name} is down")
        return [
            OHLCV(
                symbol=symbol,
                timestamp=datetime.now(tz=timezone.utc),
                open=100.0,
                high=105.0,
                low=95.0,
                close=102.0,
                volume=1000.0,
                interval=interval,
            )
        ]

    async def get_ticker(self, symbol):
        if self._should_fail:
            raise ConnectionError(f"Provider {self._name} is down")
        return Ticker(symbol=symbol, current_price=102.0)

    async def get_orderbook(self, symbol, depth=20):
        if self._should_fail:
            raise ConnectionError(f"Provider {self._name} is down")
        from quant_nanggroe.types.market import OrderBook
        return OrderBook(
            symbol=symbol,
            timestamp=datetime.now(tz=timezone.utc),
        )


class TestDataProviderManager:
    @pytest.mark.asyncio
    async def test_single_provider(self):
        provider = MockProvider("mock1")
        manager = DataProviderManager([provider])
        result = await manager.get_ohlcv("BTC/USDT")
        assert len(result) == 1
        assert result[0].close == 102.0

    @pytest.mark.asyncio
    async def test_failover(self):
        failing = MockProvider("failing", should_fail=True)
        working = MockProvider("working")
        manager = DataProviderManager([failing, working])
        result = await manager.get_ohlcv("BTC/USDT")
        assert len(result) == 1
        assert result[0].close == 102.0

    @pytest.mark.asyncio
    async def test_ticker_failover(self):
        failing = MockProvider("failing", should_fail=True)
        working = MockProvider("working")
        manager = DataProviderManager([failing, working])
        result = await manager.get_ticker("BTC/USDT")
        assert result is not None
        assert result.current_price == 102.0

    def test_health_report(self):
        provider = MockProvider("mock1")
        manager = DataProviderManager([provider])
        report = manager.get_health_report()
        assert "mock1" in report


class TestProviderHealth:
    def test_initial_healthy(self):
        health = ProviderHealth()
        assert health.is_healthy is True

    def test_cooldown(self):
        health = ProviderHealth()
        health.record_failure(cooldown_seconds=3600)
        assert health.is_healthy is False

    def test_success_reduces_failures(self):
        health = ProviderHealth()
        health.failure_count = 3
        health.record_success()
        assert health.failure_count == 2
