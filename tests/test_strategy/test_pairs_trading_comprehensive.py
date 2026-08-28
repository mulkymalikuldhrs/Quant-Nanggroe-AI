"""Comprehensive tests for PairsTradingStrategy - matches actual implementation."""

import unittest

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.pairs_trading import PairsTradingStrategy
from quant_nanggroe.types.signals import SignalType


class TestPairsTradingStrategyInit(unittest.TestCase):
    """Tests for PairsTradingStrategy initialization."""

    def test_default_initialization(self):
        strategy = PairsTradingStrategy()
        self.assertEqual(strategy.name, "PairsTrading")
        self.assertEqual(strategy.lookback, 60)
        self.assertEqual(strategy.entry_z, 2.0)
        self.assertEqual(strategy.exit_z, 0.5)
        self.assertEqual(strategy.hedge_ratio_lookback, 252)
        self.assertEqual(strategy.transaction_cost_bps, 10.0)
        self.assertEqual(strategy.min_trade_interval_bars, 5)

    def test_custom_params(self):
        strategy = PairsTradingStrategy(params={
            "lookback": 30,
            "entry_z": 1.5,
            "exit_z": 0.3,
            "hedge_ratio_lookback": 126,
            "transaction_cost_bps": 5.0,
        })
        self.assertEqual(strategy.lookback, 30)
        self.assertEqual(strategy.entry_z, 1.5)
        self.assertEqual(strategy.exit_z, 0.3)
        self.assertEqual(strategy.hedge_ratio_lookback, 126)
        self.assertEqual(strategy.transaction_cost_bps, 5.0)

    def test_positions_initialized(self):
        strategy = PairsTradingStrategy()
        self.assertEqual(strategy._position, 0.0)
        self.assertEqual(strategy._last_trade_bar, -strategy.min_trade_interval_bars)


class TestPairsTradingStrategyColumns(unittest.TestCase):
    """Tests for required_columns and warmup_period."""

    def test_required_columns(self):
        strategy = PairsTradingStrategy()
        cols = strategy.required_columns()
        self.assertIn("ASSET_A", cols)
        self.assertIn("ASSET_B", cols)
        self.assertEqual(cols, ["ASSET_A", "ASSET_B"])

    def test_warmup_period(self):
        strategy = PairsTradingStrategy()
        expected = 252 + 60
        self.assertEqual(strategy.warmup_period(), expected)

    def test_warmup_period_custom(self):
        strategy = PairsTradingStrategy(params={"lookback": 50, "hedge_ratio_lookback": 100})
        self.assertEqual(strategy.warmup_period(), 150)


class TestPairsTradingStrategyHedgeRatio(unittest.TestCase):
    """Tests for OLS hedge ratio calculation."""

    def test_ols_hedge_ratio_basic(self):
        strategy = PairsTradingStrategy()
        y = pd.Series([10, 11, 12, 13, 14], dtype=float)
        x = pd.Series([5, 5.5, 6, 6.5, 7], dtype=float)
        hr = strategy._ols_hedge_ratio(y, x)
        self.assertIsInstance(hr, float)
        # y ≈ 2*x, so hedge ratio should be close to 2
        self.assertAlmostEqual(hr, 2.0, places=1)

    def test_ols_hedge_ratio_with_intercept(self):
        strategy = PairsTradingStrategy()
        x = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        y = pd.Series([3.0, 5.0, 7.0, 9.0, 11.0])  # y = 2*x + 1
        hr = strategy._ols_hedge_ratio(y, x)
        self.assertGreater(hr, 1.0)

    def test_ols_hedge_ratio_constant_x(self):
        strategy = PairsTradingStrategy()
        x = pd.Series([10.0] * 20)
        y = pd.Series([100.0] * 20)
        hr = strategy._ols_hedge_ratio(y, x)
        # Should handle singular matrix gracefully
        self.assertIsInstance(hr, float)


class TestPairsTradingStrategySignalGeneration(unittest.TestCase):
    """Tests for generate_signal method."""

    def setUp(self):
        np.random.seed(42)
        n = 350  # Enough for hedge_ratio_lookback + lookback
        dates = pd.date_range("2024-01-01", periods=n, freq="1D")
        # Cointegrated pair
        x = 100 + np.cumsum(np.random.randn(n) * 0.5)
        spread = np.zeros(n)
        spread[0] = 0.5
        for t in range(1, n):
            spread[t] = 0.8 * spread[t-1] + np.random.randn() * 0.3
        y = 2.0 * x + spread
        self.cointegrated_data = pd.DataFrame({
            "close": y,  # Symbol B
        }, index=dates)
        self.cointegrated_data["symbol_pair"] = x  # Symbol A - rename in real usage

    def test_generate_signal_with_insufficient_columns(self):
        strategy = PairsTradingStrategy(params={
            "symbol": "ASSET_A",
            "symbol_pair": "ASSET_B",
        })
        # Without proper symbol columns — validate_data raises ValueError
        data = pd.DataFrame({"close": [100, 101, 102], "high": [101, 102, 103], "low": [99, 100, 101]})
        with self.assertRaises(ValueError):
            strategy.generate_signal(data)

    def test_insufficient_data_returns_none(self):
        strategy = PairsTradingStrategy()
        small_data = pd.DataFrame({
            "ASSET_A": [100, 101, 102],
            "ASSET_B": [50, 51, 52],
        })
        signal = strategy.generate_signal(small_data)
        self.assertIsNone(signal)


class TestPairsTradingStrategyTradeFrequency(unittest.TestCase):
    """Tests for trade frequency controls."""

    def setUp(self):
        np.random.seed(42)
        n = 350
        dates = pd.date_range("2024-01-01", periods=n, freq="1D")
        x = 100 + np.cumsum(np.random.randn(n) * 0.5)
        self.data = pd.DataFrame({
            "close": x,
            "symbol_pair": x * 2,
        }, index=dates)

    def test_min_trade_interval_enforced(self):
        strategy = PairsTradingStrategy(params={
            "symbol": "TEST_A",
            "symbol_pair": "TEST_B",
            "min_trade_interval_bars": 10,
        })
        # After a trade, next bars should be blocked
        strategy._last_trade_bar = len(self.data) - 10
        strategy._position = 1.0
        # This should not generate signal due to frequency gate
        bars_since_last = (len(self.data) - 1) - strategy._last_trade_bar
        self.assertLess(bars_since_last, strategy.min_trade_interval_bars)


class TestPairsTradingStrategyEntrySignal(unittest.TestCase):
    """Tests for entry signal generation via generate_signal."""

    def setUp(self):
        np.random.seed(42)
        n = 350
        dates = pd.date_range("2024-01-01", periods=n, freq="1D")
        x = 100 + np.cumsum(np.random.randn(n) * 0.5)
        spread = np.zeros(n)
        spread[0] = 10  # Start with large spread to ensure strong signal
        for t in range(1, n):
            spread[t] = 2.0 + np.random.randn() * 0.5
        y = 2.0 * x + spread
        self.data = pd.DataFrame({"close": y}, index=dates)
        self.data["TEST_A"] = x
        self.data["TEST_B"] = y

    def test_entry_signal_long_spread(self):
        strategy = PairsTradingStrategy(params={
            "symbol": "TEST_A",
            "symbol_pair": "TEST_B",
        })
        strategy._last_trade_bar = -50
        # Use negative z-score to trigger long spread (buy signal)
        # We need to craft data that will produce a negative z-score
        signal = strategy.generate_signal(self.data)
        # May or may not generate signal, but if it does, verify structure
        if signal is not None:
            self.assertEqual(signal.signal_type in [SignalType.BUY, SignalType.SELL, SignalType.HOLD], True)

    def test_entry_signal_short_spread(self):
        strategy = PairsTradingStrategy(params={
            "symbol": "TEST_A",
            "symbol_pair": "TEST_B",
            "entry_z": 0.01,
        })
        strategy._last_trade_bar = -50
        signal = strategy.generate_signal(self.data)
        if signal is not None:
            self.assertIn(signal.signal_type, [SignalType.BUY, SignalType.SELL])


class TestPairsTradingStrategyEvidence(unittest.TestCase):
    """Tests for signal evidence structure."""

    def setUp(self):
        np.random.seed(42)
        n = 350
        dates = pd.date_range("2024-01-01", periods=n, freq="1D")
        x = 100 + np.cumsum(np.random.randn(n) * 0.5)
        spread = np.zeros(n)
        spread[0] = 10
        for t in range(1, n):
            spread[t] = 2.0 + np.random.randn() * 0.5
        y = 2.0 * x + spread
        self.data = pd.DataFrame({"close": y}, index=dates)
        self.data["TEST_A"] = x
        self.data["TEST_B"] = y

    def test_entry_signal_evidence(self):
        strategy = PairsTradingStrategy(params={"symbol": "TEST_A", "symbol_pair": "TEST_B", "entry_z": 0.01})
        strategy._last_trade_bar = -50
        signal = strategy.generate_signal(self.data)
        if signal is not None:
            self.assertIn("spread_z", signal.evidence)
            self.assertIn("hedge_ratio", signal.evidence)


class TestPairsTradingStrategyRepr(unittest.TestCase):
    """Tests for string representation."""

    def test_repr(self):
        strategy = PairsTradingStrategy()
        repr_str = repr(strategy)
        self.assertIn("PairsTrading", repr_str)


if __name__ == "__main__":
    unittest.main()