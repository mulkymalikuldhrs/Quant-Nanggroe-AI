"""Tests for data layer components."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from quant_nanggroe.data.providers.base import DataProvider
from quant_nanggroe.data.manager import DataProviderManager
from quant_nanggroe.types.market import OHLCV, TimeFrame


class MockProvider(DataProvider):
    """Mock data provider for testing."""

    def __init__(self, name: str = "mock", priority: int = 0):
        super().__init__(name=name, priority=priority)
        self._ohlcv_data = [
            OHLCV(
                symbol="BTC/USDT",
                timestamp=datetime(2024, 1, i+1),
                open=42000.0 + i * 100,
                high=42500.0 + i * 100,
                low=41800.0 + i * 100,
                close=42300.0 + i * 100,
                volume=1000.0,
            )
            for i in range(10)
        ]

    async def get_ohlcv(self, symbol, timeframe=TimeFrame.D1, start=None, end=None, limit=500):
        self.mark_success()
        return self._ohlcv_data[:limit]

    async def get_ticker(self, symbol):
        from quant_nanggroe.types.market import Ticker
        self.mark_success()
        return Ticker(
            symbol=symbol,
            timestamp=datetime.now(),
            last_price=42300.0,
        )

    async def get_orderbook(self, symbol, limit=20):
        return None

    async def health_check(self):
        return True


class TestDataProviderBase:
    def test_provider_creation(self):
        provider = MockProvider(name="test", priority=5)
        assert provider.name == "test"
        assert provider.priority == 5
        assert provider.is_available is True

    def test_health_score(self):
        provider = MockProvider()
        assert provider.health_score == 1.0
        provider.mark_error("test error")
        assert provider.health_score < 1.0

    def test_mark_error_tracks_errors(self):
        provider = MockProvider()
        provider.mark_error("error 1")
        assert provider.last_error == "error 1"
        assert provider._error_count == 1


class TestDataProviderManager:
    def test_register_provider(self):
        manager = DataProviderManager()
        provider = MockProvider(name="test_provider", priority=1)
        manager.register(provider, markets=["crypto"])
        status = manager.get_status()
        assert "test_provider" in status

    def test_infer_market_crypto(self):
        assert DataProviderManager._infer_market("BTC/USDT") == "crypto"

    def test_infer_market_stocks(self):
        assert DataProviderManager._infer_market("AAPL") == "stocks"

    def test_infer_market_forex(self):
        assert DataProviderManager._infer_market("EURUSD=X") == "forex"

    @pytest.mark.asyncio
    async def test_get_ohlcv_with_failover(self):
        manager = DataProviderManager()
        provider = MockProvider(name="primary", priority=1)
        manager.register(provider, markets=["crypto"])

        result = await manager.get_ohlcv("BTC/USDT", TimeFrame.D1, limit=5)
        assert len(result) == 5
        assert result[0].symbol == "BTC/USDT"

    @pytest.mark.asyncio
    async def test_get_ticker(self):
        manager = DataProviderManager()
        provider = MockProvider(name="test", priority=1)
        manager.register(provider, markets=["crypto"])

        ticker = await manager.get_ticker("BTC/USDT")
        assert ticker is not None
        assert ticker.last_price == 42300.0
