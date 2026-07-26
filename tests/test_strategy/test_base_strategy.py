"""Tests for BaseStrategy."""

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe.engine.strategies.base import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType


class ConcreteStrategy(BaseStrategy):
    """Concrete implementation for testing."""

    def generate_signal(self, data: pd.DataFrame):
        return Signal(
            symbol="TEST",
            signal_type=SignalType.BUY,
            confidence=0.8,
            source_agent="test",
        )

    def required_columns(self):
        return ["close"]

    def warmup_period(self):
        return 20


class TestBaseStrategy:
    """Test BaseStrategy interface and utility methods."""

    def test_init_defaults(self):
        strategy = ConcreteStrategy(name="TestStrategy")
        assert strategy.name == "TestStrategy"
        assert strategy.params == {}
        assert strategy.is_warmed_up is False

    def test_init_with_params(self):
        strategy = ConcreteStrategy(name="TestStrategy", params={"period": 14})
        assert strategy.params["period"] == 14

    def test_validate_data_success(self):
        strategy = ConcreteStrategy(name="TestStrategy")
        data = pd.DataFrame({"close": np.random.randn(50)})
        assert strategy.validate_data(data) is True

    def test_validate_data_missing_columns(self):
        strategy = ConcreteStrategy(name="TestStrategy")
        data = pd.DataFrame({"open": np.random.randn(50)})
        with pytest.raises(ValueError, match="missing required columns"):
            strategy.validate_data(data)

    def test_validate_data_insufficient_length(self):
        strategy = ConcreteStrategy(name="TestStrategy")
        data = pd.DataFrame({"close": np.random.randn(10)})
        result = strategy.validate_data(data)
        assert result is False  # Not enough data for warmup

    def test_validate_data_none(self):
        strategy = ConcreteStrategy(name="TestStrategy")
        assert strategy.validate_data(None) is False

    def test_validate_data_empty(self):
        strategy = ConcreteStrategy(name="TestStrategy")
        assert strategy.validate_data(pd.DataFrame()) is False

    def test_compute_sma(self):
        series = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=float)
        sma = BaseStrategy.compute_sma(series, 3)
        assert not np.isnan(sma.iloc[-1])
        assert abs(sma.iloc[-1] - 9.0) < 1e-10

    def test_compute_ema(self):
        series = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=float)
        ema = BaseStrategy.compute_ema(series, 3)
        assert not np.isnan(ema.iloc[-1])
        assert ema.iloc[-1] > 5  # Should be above simple average due to recency

    def test_compute_rsi(self):
        prices = pd.Series([100 + i * 0.5 for i in range(50)], dtype=float)
        rsi = BaseStrategy.compute_rsi(prices, 14)
        # Uptrend should have RSI > 50
        assert rsi.iloc[-1] > 50

    def test_compute_atr(self):
        high = pd.Series([105, 106, 107, 108, 109] * 10, dtype=float)
        low = pd.Series([95, 96, 97, 98, 99] * 10, dtype=float)
        close = pd.Series([100, 101, 102, 103, 104] * 10, dtype=float)
        atr = BaseStrategy.compute_atr(high, low, close, 14)
        assert not np.isnan(atr.iloc[-1])
        assert atr.iloc[-1] > 0

    def test_compute_bollinger_bands(self):
        series = pd.Series(np.random.randn(100) + 50, dtype=float)
        upper, middle, lower = BaseStrategy.compute_bollinger_bands(series, 20, 2.0)
        assert not np.isnan(upper.iloc[-1])
        assert upper.iloc[-1] > middle.iloc[-1]
        assert lower.iloc[-1] < middle.iloc[-1]

    def test_compute_macd(self):
        series = pd.Series(np.cumsum(np.random.randn(100)), dtype=float)
        macd_line, signal_line, histogram = BaseStrategy.compute_macd(series, 12, 26, 9)
        assert len(macd_line) == len(series)
        assert len(signal_line) == len(series)

    def test_compute_zscore(self):
        series = pd.Series(np.random.randn(100), dtype=float)
        zscore = BaseStrategy.compute_zscore(series, 20)
        assert not np.isnan(zscore.iloc[-1])

    def test_repr(self):
        strategy = ConcreteStrategy(name="TestStrategy", params={"period": 14})
        repr_str = repr(strategy)
        assert "TestStrategy" in repr_str
        assert "period" in repr_str

    def test_generate_signal(self):
        strategy = ConcreteStrategy(name="TestStrategy")
        data = pd.DataFrame({"close": np.random.randn(50)})
        signal = strategy.generate_signal(data)
        assert isinstance(signal, Signal)
        assert signal.signal_type == SignalType.BUY
        assert signal.confidence == 0.8
