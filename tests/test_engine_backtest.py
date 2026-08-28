#!/usr/bin/env python3
"""Tests: BacktestEngine — core backtest loop, P&L, signal processing.

Run: python3 -m unittest tests/test_engine_backtest.py -v
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import pandas as pd

from quant_nanggroe.engine.backtest import (
    BacktestConfig,
    BacktestEngine,
    MarketType,
    StrategyType,
)


class TestBacktestConfig(unittest.TestCase):
    """Tests for BacktestConfig dataclass."""

    def test_default_values(self):
        cfg = BacktestConfig()
        self.assertEqual(cfg.initial_capital, 1_000_000.0)
        self.assertEqual(cfg.market, MarketType.EQUITY)
        self.assertEqual(cfg.strategy_type, StrategyType.SIGNAL_BASED)
        self.assertEqual(cfg.commission_rate, 0.001)
        self.assertEqual(cfg.slippage_bps, 5.0)
        self.assertEqual(cfg.leverage, 1.0)
        self.assertEqual(cfg.risk_per_trade, 0.005)
        self.assertEqual(cfg.max_positions, 10)
        self.assertEqual(cfg.bars_per_year, 252)
        self.assertIsNone(cfg.benchmark)
        self.assertFalse(cfg.short_enabled)

    def test_custom_values(self):
        cfg = BacktestConfig(
            initial_capital=500_000.0,
            market=MarketType.CRYPTO,
            strategy_type=StrategyType.ML_BASED,
            short_enabled=True,
            leverage=2.0,
        )
        self.assertEqual(cfg.initial_capital, 500_000.0)
        self.assertEqual(cfg.market, MarketType.CRYPTO)
        self.assertEqual(cfg.strategy_type, StrategyType.ML_BASED)
        self.assertTrue(cfg.short_enabled)
        self.assertEqual(cfg.leverage, 2.0)

    def test_market_type_values(self):
        self.assertEqual(MarketType.EQUITY.value, "equity")
        self.assertEqual(MarketType.CRYPTO.value, "crypto")
        self.assertEqual(MarketType.FOREX.value, "forex")
        self.assertEqual(MarketType.FUTURES.value, "futures")

    def test_strategy_type_values(self):
        self.assertEqual(StrategyType.SIGNAL_BASED.value, "signal_based")
        self.assertEqual(StrategyType.FACTOR_BASED.value, "factor_based")
        self.assertEqual(StrategyType.ML_BASED.value, "ml_based")


class TestBacktestEngineInit(unittest.TestCase):
    """Tests for BacktestEngine construction."""

    def test_default_config(self):
        engine = BacktestEngine()
        self.assertIsNotNone(engine.config)
        self.assertIsNotNone(engine.execution)
        self.assertIsNotNone(engine.metrics_calculator)

    def test_custom_config(self):
        cfg = BacktestConfig(initial_capital=250_000.0, bars_per_year=365)
        engine = BacktestEngine(cfg)
        self.assertEqual(engine.config.initial_capital, 250_000.0)
        self.assertEqual(engine.config.bars_per_year, 365)

    def test_market_type_propagates_to_execution(self):
        cfg = BacktestConfig(market=MarketType.FOREX)
        engine = BacktestEngine(cfg)
        self.assertEqual(engine.execution.config.market, "forex")


class TestBacktestEngineRun(unittest.TestCase):
    """Tests for BacktestEngine.run()."""

    def setUp(self):
        self.engine = BacktestEngine(BacktestConfig(initial_capital=100_000.0))
        n = 100
        dates = pd.date_range("2024-01-01", periods=n, freq="D")
        rng = np.random.default_rng(42)
        self.prices = pd.DataFrame(
            {"AAPL": 100.0 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))},
            index=dates,
        )
        # Simple long signal: buy on odd days
        self.signals = pd.DataFrame(
            {"AAPL": [1.0 if i % 2 == 0 else 0.0 for i in range(n)]},
            index=dates,
        )

    def test_run_returns_dict_with_expected_keys(self):
        result = self.engine.run(self.prices, self.signals)
        expected_keys = {"metrics", "equity_curve", "trades", "final_equity", "total_trades", "trade_analytics"}
        self.assertTrue(expected_keys.issubset(result.keys()))

    def test_run_returns_metrics(self):
        result = self.engine.run(self.prices, self.signals)
        metrics = result["metrics"]
        self.assertIn("total_return", metrics)
        self.assertIn("sharpe_ratio", metrics)
        self.assertIsInstance(metrics["total_return"], float)

    def test_run_final_equity_is_positive(self):
        result = self.engine.run(self.prices, self.signals)
        self.assertGreater(result["final_equity"], 0)

    def test_run_with_flat_signals(self):
        flat_signals = pd.DataFrame({"AAPL": [0.0] * len(self.prices)}, index=self.prices.index)
        result = self.engine.run(self.prices, flat_signals)
        self.assertEqual(result["total_trades"], 0)
        self.assertAlmostEqual(result["final_equity"], 100_000.0, delta=1)

    def test_run_with_empty_price_data(self):
        empty_prices = pd.DataFrame({"AAPL": []}, index=pd.DatetimeIndex([]))
        empty_signals = pd.DataFrame({"AAPL": []}, index=pd.DatetimeIndex([]))
        result = self.engine.run(empty_prices, empty_signals)
        self.assertEqual(result["total_trades"], 0)
        self.assertEqual(result["final_equity"], 100_000.0)

    def test_run_with_single_bar(self):
        dates = pd.DatetimeIndex(["2024-01-01"])
        prices = pd.DataFrame({"AAPL": [100.0]}, index=dates)
        signals = pd.DataFrame({"AAPL": [1.0]}, index=dates)
        result = self.engine.run(prices, signals)
        self.assertEqual(result["total_trades"], 0)  # signal shifted, no bar to trade
        self.assertEqual(result["final_equity"], 100_000.0)

    def test_run_custom_position_sizer(self):
        def sizer(signal, capital, price):
            return 10.0
        result = self.engine.run(self.prices, self.signals, position_sizer=sizer)
        self.assertGreater(result["total_trades"], 0)

    def test_run_custom_execution_model(self):
        def exec_model(price, direction, size, ts):
            return price * 1.001 if direction > 0 else price * 0.999
        result = self.engine.run(self.prices, self.signals, execution_model=exec_model)
        self.assertIn("trades", result)


class TestBacktestEngineMultiStrategy(unittest.TestCase):
    """Tests for BacktestEngine.run_multi_strategy()."""

    def setUp(self):
        self.engine = BacktestEngine(BacktestConfig(initial_capital=100_000.0))
        n = 50
        dates = pd.date_range("2024-01-01", periods=n, freq="D")
        rng = np.random.default_rng(42)
        self.prices = pd.DataFrame(
            {"AAPL": 100.0 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))},
            index=dates,
        )
        self.signal_a = pd.DataFrame({"AAPL": [1.0] * n}, index=dates)
        self.signal_b = pd.DataFrame({"AAPL": [0.5] * n}, index=dates)

    def test_multi_strategy_returns_combined_and_per_strategy(self):
        strategies = {"strat_a": self.signal_a, "strat_b": self.signal_b}
        result = self.engine.run_multi_strategy(self.prices, strategies)
        self.assertIn("combined", result)
        self.assertIn("per_strategy", result)
        self.assertIn("strat_a", result["per_strategy"])
        self.assertIn("strat_b", result["per_strategy"])

    def test_multi_strategy_empty_raises(self):
        with self.assertRaises(ValueError):
            self.engine.run_multi_strategy(self.prices, {})

    def test_multi_strategy_with_weights(self):
        strategies = {"strat_a": self.signal_a, "strat_b": self.signal_b}
        weights = {"strat_a": 0.8, "strat_b": 0.2}
        result = self.engine.run_multi_strategy(self.prices, strategies, weights)
        self.assertIn("strategy_weights", result)
        self.assertAlmostEqual(result["strategy_weights"]["strat_a"], 0.8)
        self.assertAlmostEqual(result["strategy_weights"]["strat_b"], 0.2)

    def test_multi_strategy_strategy_correlation(self):
        strategies = {"a": self.signal_a, "b": self.signal_b}
        result = self.engine.run_multi_strategy(self.prices, strategies)
        self.assertIn("strategy_correlation", result)

    def test_multi_strategy_single_strategy(self):
        strategies = {"only_one": self.signal_a}
        result = self.engine.run_multi_strategy(self.prices, strategies)
        self.assertIn("combined", result)


class TestBacktestEngineSensitivity(unittest.TestCase):
    """Tests for run_sensitivity_analysis()."""

    def setUp(self):
        self.engine = BacktestEngine(BacktestConfig(initial_capital=100_000.0))
        n = 50
        dates = pd.date_range("2024-01-01", periods=n, freq="D")
        rng = np.random.default_rng(42)
        self.prices = pd.DataFrame(
            {"AAPL": 100.0 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))},
            index=dates,
        )
        self.signals = pd.DataFrame({"AAPL": [1.0] * n}, index=dates)

    def test_sensitivity_returns_results_by_param(self):
        result = self.engine.run_sensitivity_analysis(
            self.prices, self.signals, "leverage", [1.0, 2.0],
        )
        self.assertIn("results", result)
        self.assertIn("1.0", result["results"])
        self.assertIn("2.0", result["results"])

    def test_sensitivity_returns_metrics_summary(self):
        result = self.engine.run_sensitivity_analysis(
            self.prices, self.signals, "leverage", [1.0],
        )
        self.assertIn("metrics_summary", result)

    def test_sensitivity_optimal_found(self):
        result = self.engine.run_sensitivity_analysis(
            self.prices, self.signals, "commission_rate", [0.0, 0.01],
        )
        self.assertIn("optimal", result)
        self.assertIn("optimal_value", result["optimal"])

    def test_sensitivity_with_custom_applier(self):
        def applier(cfg, name, value):
            import copy
            c = copy.deepcopy(cfg)
            setattr(c, name, value)
            return c
        result = self.engine.run_sensitivity_analysis(
            self.prices, self.signals, "initial_capital", [50_000.0],
            param_applier=applier,
        )
        self.assertIn("results", result)


class TestBacktestEngineBenchmark(unittest.TestCase):
    """Tests for run_with_benchmark()."""

    def setUp(self):
        self.engine = BacktestEngine(BacktestConfig(initial_capital=100_000.0))
        n = 50
        dates = pd.date_range("2024-01-01", periods=n, freq="D")
        rng = np.random.default_rng(42)
        self.prices = pd.DataFrame(
            {"AAPL": 100.0 * np.exp(np.cumsum(rng.normal(0.001, 0.01, n)))},
            index=dates,
        )
        self.signals = pd.DataFrame({"AAPL": [1.0] * n}, index=dates)
        self.benchmark = pd.Series(
            100.0 * np.exp(np.cumsum(rng.normal(0.0005, 0.01, n))),
            index=dates,
        )

    def test_run_with_benchmark_includes_benchmark_comparison(self):
        result = self.engine.run_with_benchmark(self.prices, self.signals, self.benchmark)
        self.assertIn("benchmark_comparison", result)

    def test_run_with_benchmark_returns_metrics(self):
        result = self.engine.run_with_benchmark(self.prices, self.signals, self.benchmark)
        self.assertIn("metrics", result)
        self.assertIn("total_return", result["metrics"])

    def test_run_with_benchmark_no_benchmark_provided(self):
        result = self.engine.run_with_benchmark(self.prices, self.signals)
        self.assertIn("equity_curve", result)


class TestBacktestEngineTradeAnalytics(unittest.TestCase):
    """Tests for _compute_trade_analytics."""

    def test_empty_trades_returns_defaults(self):
        result = BacktestEngine._compute_trade_analytics([])
        self.assertIn("by_symbol", result)
        self.assertIn("by_direction", result)
        self.assertIn("by_exit_reason", result)
        self.assertIn("time_analysis", result)

    def test_empty_trades_returns_zero_counts(self):
        result = BacktestEngine._compute_trade_analytics([])
        self.assertEqual(result["by_symbol"], {})
        self.assertEqual(result["by_direction"]["long"], {})
        self.assertEqual(result["by_direction"]["short"], {})

    def test_strategy_correlation_less_than_two(self):
        eq_curves = {"a": pd.Series([100, 101, 102])}
        corr = BacktestEngine._compute_strategy_correlation(eq_curves)
        self.assertTrue(corr.empty)

    def test_strategy_correlation_two_curves(self):
        dates = pd.date_range("2024-01-01", periods=3, freq="D")
        eq_curves = {
            "a": pd.Series([100, 101, 102], index=dates),
            "b": pd.Series([100, 99, 101], index=dates),
        }
        corr = BacktestEngine._compute_strategy_correlation(eq_curves)
        self.assertIsInstance(corr, pd.DataFrame)


if __name__ == "__main__":
    unittest.main(verbosity=2)
