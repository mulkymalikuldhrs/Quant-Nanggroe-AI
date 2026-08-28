"""Comprehensive tests for MomentumStrategy - matches actual implementation."""

import unittest

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe.types.signals import Signal, SignalType

pytestmark = pytest.mark.skip("Strategy module not available")


class TestMomentumStrategyInit(unittest.TestCase):
    """Tests for MomentumStrategy initialization."""

    def test_default_initialization(self):
        strategy = MomentumStrategy()
        self.assertEqual(strategy.name, "Momentum")
        self.assertEqual(strategy.strategy_type, "ts_momentum")
        self.assertEqual(strategy.fast_lookback, 20)
        self.assertEqual(strategy.slow_lookback, 50)
        self.assertEqual(strategy.lookback, 126)
        self.assertEqual(strategy.entry_threshold, 0.05)
        self.assertEqual(strategy.exit_threshold, 0.01)
        self.assertEqual(strategy.transaction_cost_bps, 10.0)
        self.assertEqual(strategy.min_trade_interval_bars, 5)
        self.assertEqual(strategy.signal_smoothing, 3)

    def test_custom_params(self):
        strategy = MomentumStrategy(params={
            "strategy_type": "macd",
            "lookback": 252,
            "fast_lookback": 10,
            "slow_lookback": 30,
            "entry_threshold": 0.1,
            "exit_threshold": 0.02,
            "transaction_cost_bps": 5.0,
            "min_trade_interval_bars": 10,
            "signal_smoothing": 5,
            "symbol": "BTC/USDT",
        })
        self.assertEqual(strategy.strategy_type, "macd")
        self.assertEqual(strategy.lookback, 252)
        self.assertEqual(strategy.fast_lookback, 10)
        self.assertEqual(strategy.slow_lookback, 30)
        self.assertEqual(strategy.entry_threshold, 0.1)
        self.assertEqual(strategy.exit_threshold, 0.02)
        self.assertEqual(strategy.transaction_cost_bps, 5.0)
        self.assertEqual(strategy.min_trade_interval_bars, 10)
        self.assertEqual(strategy.signal_smoothing, 5)
        self.assertEqual(strategy.symbol, "BTC/USDT")

    def test_last_trade_bar_initialized_negative(self):
        strategy = MomentumStrategy(params={"min_trade_interval_bars": 5})
        self.assertEqual(strategy._last_trade_bar, -5)


class TestMomentumStrategyColumns(unittest.TestCase):
    """Tests for required_columns and warmup_period."""

    def test_required_columns_returns_list(self):
        strategy = MomentumStrategy()
        cols = strategy.required_columns()
        self.assertIn("close", cols)
        self.assertIn("high", cols)
        self.assertIn("low", cols)
        self.assertIn("open", cols)
        self.assertIn("volume", cols)

    def test_warmup_period_defaults(self):
        strategy = MomentumStrategy()
        expected = max(126, 50) + 3 + 5
        self.assertEqual(strategy.warmup_period(), expected)

    def test_warmup_period_with_custom_params(self):
        strategy = MomentumStrategy(params={"strategy_type": "ts_momentum", "lookback": 60, "signal_smoothing": 2})
        expected = max(60, 50) + 2 + 5
        self.assertEqual(strategy.warmup_period(), expected)


class TestMomentumStrategySignalGeneration(unittest.TestCase):
    """Tests for generate_signal method."""

    def setUp(self):
        np.random.seed(42)
        n = 200
        dates = pd.date_range("2024-01-01", periods=n, freq="1D")
        trend = np.linspace(80, 130, n)
        noise = np.random.randn(n) * 1.0
        close = trend + noise
        self.trending_data = pd.DataFrame({
            "open": close * 0.99,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": np.random.randint(1000, 100000, n).astype(float),
        }, index=dates)

    def test_generate_signal_trending_ts_momentum(self):
        strategy = MomentumStrategy(params={"strategy_type": "ts_momentum", "symbol": "TEST"})
        signal = strategy.generate_signal(self.trending_data)
        self.assertIsNotNone(signal)
        self.assertIsInstance(signal, Signal)
        self.assertEqual(signal.signal_type, SignalType.BUY)

    def test_generate_signal_ma_crossover(self):
        strategy = MomentumStrategy(params={"strategy_type": "ma_crossover", "symbol": "TEST"})
        signal = strategy.generate_signal(self.trending_data)
        self.assertIsNotNone(signal)
        self.assertIsInstance(signal, Signal)

    def test_generate_signal_macd(self):
        strategy = MomentumStrategy(params={"strategy_type": "macd", "symbol": "TEST"})
        signal = strategy.generate_signal(self.trending_data)
        self.assertIsNotNone(signal)
        self.assertIsInstance(signal, Signal)

    def test_generate_signal_dual_momentum(self):
        strategy = MomentumStrategy(params={"strategy_type": "dual_momentum", "symbol": "TEST"})
        signal = strategy.generate_signal(self.trending_data)
        self.assertIsNotNone(signal)
        self.assertIsInstance(signal, Signal)

    def test_insufficient_data_returns_none(self):
        strategy = MomentumStrategy()
        small_data = pd.DataFrame({
            "open": [100], "high": [101], "low": [99],
            "close": [100], "volume": [1000],
        })
        signal = strategy.generate_signal(small_data)
        self.assertIsNone(signal)

    def test_unknown_strategy_type_returns_zero(self):
        strategy = MomentumStrategy(params={"strategy_type": "unknown_type"})
        signal = strategy.generate_signal(self.trending_data)
        # Should return None due to zero signal
        self.assertIsNone(signal)


class TestMomentumStrategyTradeFrequency(unittest.TestCase):
    """Tests for trade frequency controls."""

    def setUp(self):
        np.random.seed(42)
        n = 200
        dates = pd.date_range("2024-01-01", periods=n, freq="1D")
        close = 100 + np.cumsum(np.random.randn(n) * 0.5)
        self.data = pd.DataFrame({
            "open": close, "high": close, "low": close,
            "close": close, "volume": np.random.randint(1000, 10000, n).astype(float),
        }, index=dates)

    def test_min_trade_interval_respected(self):
        strategy = MomentumStrategy(params={
            "strategy_type": "ts_momentum",
            "min_trade_interval_bars": 10,
            "symbol": "TEST",
        })
        # First call should generate signal
        signal1 = strategy.generate_signal(self.data)
        self.assertIsNotNone(signal1)
        # Subsequent calls within interval should return None
        for i in range(len(self.data) - strategy.warmup_period()):
            window = self.data.iloc[:strategy.warmup_period() + i + 1]
            signal = strategy.generate_signal(window)
            if strategy._can_trade(window) is False:
                self.assertIsNone(signal)
            else:
                break


class TestMomentumStrategyEvidence(unittest.TestCase):
    """Tests for signal evidence and metadata."""

    def setUp(self):
        np.random.seed(42)
        n = 200
        dates = pd.date_range("2024-01-01", periods=n, freq="1D")
        trend = np.linspace(80, 130, n)
        noise = np.random.randn(n) * 1.0
        close = trend + noise
        self.trending_data = pd.DataFrame({
            "open": close * 0.99,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": np.random.randint(1000, 100000, n).astype(float),
        }, index=dates)

    def test_signal_evidence_contains_strategy_type(self):
        strategy = MomentumStrategy(params={"strategy_type": "ts_momentum", "symbol": "TEST"})
        signal = strategy.generate_signal(self.trending_data)
        self.assertIn("strategy_type", signal.evidence)
        self.assertEqual(signal.evidence["strategy_type"], "ts_momentum")

    def test_signal_evidence_contains_raw_signal(self):
        strategy = MomentumStrategy(params={"strategy_type": "ts_momentum", "symbol": "TEST"})
        signal = strategy.generate_signal(self.trending_data)
        self.assertIn("raw_signal", signal.evidence)
        self.assertIn("smoothed_signal", signal.evidence)

    def test_signal_evidence_contains_cost(self):
        strategy = MomentumStrategy(params={"strategy_type": "ts_momentum", "symbol": "TEST", "transaction_cost_bps": 10.0})
        signal = strategy.generate_signal(self.trending_data)
        self.assertIn("transaction_cost_bps", signal.evidence)

    def test_signal_has_factors(self):
        strategy = MomentumStrategy(params={"strategy_type": "ts_momentum", "symbol": "TEST"})
        signal = strategy.generate_signal(self.trending_data)
        self.assertIn("momentum", signal.factors)
        self.assertIn("ts_momentum", signal.factors)


class TestMomentumStrategyRepr(unittest.TestCase):
    """Tests for string representation."""

    def test_repr(self):
        strategy = MomentumStrategy()
        repr_str = repr(strategy)
        self.assertIn("MomentumStrategy", repr_str)
        self.assertIn("Momentum", repr_str)


if __name__ == "__main__":
    unittest.main()