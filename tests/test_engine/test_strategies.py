"""Tests for Strategy Library."""

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe.engine.strategies.base import (
    SignalDirection,
    SignalStrength,
    StrategyParameters,
    StrategySignal,
)
from quant_nanggroe.engine.strategies.fibonacci import FibonacciStrategy
from quant_nanggroe.engine.strategies.ict import ICTStrategy
from quant_nanggroe.engine.strategies.registry import StrategyRegistry
from quant_nanggroe.engine.strategies.smc_strategy import SMCStrategy
from quant_nanggroe.engine.strategies.unified_retail import UnifiedRetailStrategy
from quant_nanggroe.engine.strategies.wyckoff import WyckoffStrategy

# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture
def sample_ohlcv():
    """Generate sample OHLCV DataFrame."""
    np.random.seed(42)
    n = 50
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    close = 100 + np.cumsum(np.random.randn(n) * 2)
    high = close + np.abs(np.random.randn(n))
    low = close - np.abs(np.random.randn(n))
    open_prices = close + np.random.randn(n) * 0.5
    volume = np.random.randint(1000000, 10000000, n)

    return pd.DataFrame({
        "open": open_prices,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }, index=dates)


@pytest.fixture
def bullish_data():
    """Generate bullish trending data."""
    n = 30
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    close = np.linspace(100, 130, n) + np.random.randn(n) * 0.5
    high = close + np.abs(np.random.randn(n))
    low = close - np.abs(np.random.randn(n))
    open_prices = close - np.random.randn(n) * 0.3
    volume = np.random.randint(2000000, 8000000, n)

    return pd.DataFrame({
        "open": open_prices,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }, index=dates)


# ======================================================================
# Base Strategy
# ======================================================================

class TestStrategySignal:
    def test_defaults(self):
        signal = StrategySignal()
        assert signal.direction == SignalDirection.HOLD
        assert signal.confidence == 0.0

    def test_with_data(self):
        signal = StrategySignal(
            strategy_name="wyckoff",
            direction=SignalDirection.BUY,
            strength=SignalStrength.STRONG,
            confidence=0.8,
            entry_price=150.0,
            stop_loss=145.0,
            take_profit=160.0,
        )
        assert signal.direction == SignalDirection.BUY
        assert signal.confidence == 0.8


class TestStrategyParameters:
    def test_get_set(self):
        params = StrategyParameters()
        params.set("lookback", 20)
        assert params.get("lookback") == 20
        assert params.get("missing", 10) == 10


# ======================================================================
# Strategy Registry
# ======================================================================

class TestStrategyRegistry:
    def test_list_strategies(self):
        strategies = StrategyRegistry.list_strategies()
        assert "wyckoff" in strategies
        assert "smc" in strategies
        assert "ict" in strategies
        assert "fibonacci" in strategies
        assert "unified_retail" in strategies

    def test_create_strategy(self):
        strategy = StrategyRegistry.create("wyckoff")
        assert strategy is not None
        assert strategy.name == "wyckoff"

    def test_create_nonexistent(self):
        strategy = StrategyRegistry.create("nonexistent_strategy")
        assert strategy is None

    def test_count(self):
        assert StrategyRegistry.count() >= 5


# ======================================================================
# Wyckoff Strategy
# ======================================================================

class TestWyckoffStrategy:
    def test_construction(self):
        strategy = WyckoffStrategy()
        assert strategy.name == "wyckoff"

    def test_hold_on_insufficient_data(self):
        strategy = WyckoffStrategy()
        data = pd.DataFrame({"close": [100, 101], "high": [101, 102], "low": [99, 100], "volume": [1000, 1000]})
        signal = strategy.generate_signal(data)
        assert signal.direction == SignalDirection.HOLD

    def test_generate_signal(self, sample_ohlcv):
        strategy = WyckoffStrategy()
        signal = strategy.generate_signal(sample_ohlcv, symbol="AAPL")
        assert isinstance(signal, StrategySignal)
        assert signal.strategy_name == "wyckoff"
        assert signal.direction in (SignalDirection.BUY, SignalDirection.SELL, SignalDirection.HOLD)


# ======================================================================
# SMC Strategy
# ======================================================================

class TestSMCStrategy:
    def test_construction(self):
        strategy = SMCStrategy()
        assert strategy.name == "smc"

    def test_generate_signal(self, sample_ohlcv):
        strategy = SMCStrategy()
        signal = strategy.generate_signal(sample_ohlcv, symbol="AAPL")
        assert isinstance(signal, StrategySignal)
        assert signal.strategy_name == "smc"

    def test_fvg_detection(self):
        """Test FVG detection with gap data."""
        strategy = SMCStrategy()
        # Create data with a bullish FVG
        data = pd.DataFrame({
            "open": [100, 102, 105, 103, 104],
            "high": [101, 103, 108, 106, 106],
            "low": [99, 101, 104, 102, 103],
            "close": [100, 102, 107, 104, 105],
            "volume": [1000, 1000, 2000, 1500, 1200],
        })
        signal = strategy.generate_signal(data)
        assert isinstance(signal, StrategySignal)


# ======================================================================
# ICT Strategy
# ======================================================================

class TestICTStrategy:
    def test_construction(self):
        strategy = ICTStrategy()
        assert strategy.name == "ict"

    def test_generate_signal(self, sample_ohlcv):
        strategy = ICTStrategy()
        signal = strategy.generate_signal(sample_ohlcv, symbol="AAPL")
        assert isinstance(signal, StrategySignal)
        assert signal.strategy_name == "ict"

    def test_ote_zone(self):
        """Test OTE zone detection."""
        strategy = ICTStrategy()
        # Create data where price is in OTE zone
        n = 30
        close = np.linspace(100, 120, n)
        # Retrace to 70% level
        close[-3:] = [112, 110, 109]  # In OTE zone
        data = pd.DataFrame({
            "open": close,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": np.random.randint(1000000, 5000000, n),
        })
        signal = strategy.generate_signal(data, symbol="AAPL")
        assert isinstance(signal, StrategySignal)


# ======================================================================
# Fibonacci Strategy
# ======================================================================

class TestFibonacciStrategy:
    def test_construction(self):
        strategy = FibonacciStrategy()
        assert strategy.name == "fibonacci"

    def test_generate_signal(self, sample_ohlcv):
        strategy = FibonacciStrategy()
        signal = strategy.generate_signal(sample_ohlcv, symbol="AAPL")
        assert isinstance(signal, StrategySignal)
        assert signal.strategy_name == "fibonacci"
        # Should have fib levels in indicators
        if signal.indicators:
            assert "fib_retracement" in signal.indicators


# ======================================================================
# Unified Retail Strategy
# ======================================================================

class TestUnifiedRetailStrategy:
    def test_construction(self):
        strategy = UnifiedRetailStrategy()
        assert strategy.name == "unified_retail"

    def test_generate_signal(self, sample_ohlcv):
        strategy = UnifiedRetailStrategy()
        signal = strategy.generate_signal(sample_ohlcv, symbol="AAPL")
        assert isinstance(signal, StrategySignal)
        assert signal.strategy_name == "unified_retail"
        # Should have sub-strategy indicators
        if signal.indicators:
            assert "ict" in signal.indicators or "smc" in signal.indicators
