# Coverage target: portfolio.py, metrics.py, monte_carlo.py

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import pandas as pd

from quant_nanggroe.engine.backtest.metrics import PerformanceMetrics
from quant_nanggroe.engine.backtest.monte_carlo import (
    MonteCarloResult,
    MonteCarloSimulator,
    MultiMetricMonteCarloResult,
)
from quant_nanggroe.engine.backtest.portfolio import Portfolio, TradeRecord


class TestPortfolioInit(unittest.TestCase):
    """Portfolio construction and basic properties."""

    def test_default_initialization(self):
        p = Portfolio()
        self.assertEqual(p.initial_capital, 1_000_000.0)
        self.assertEqual(p.cash, 1_000_000.0)
        self.assertEqual(p.max_positions, 10)
        self.assertEqual(p.position_count, 0)

    def test_custom_initialization(self):
        p = Portfolio(initial_capital=500_000.0, max_positions=5)
        self.assertEqual(p.initial_capital, 500_000.0)
        self.assertEqual(p.max_positions, 5)

    def test_equity_equals_cash_when_no_positions(self):
        p = Portfolio()
        self.assertEqual(p.equity, p.cash)

    def test_unrealized_pnl_zero_when_no_positions(self):
        p = Portfolio()
        self.assertEqual(p.unrealized_pnl, 0.0)


class TestPortfolioOpenClose(unittest.TestCase):
    """Position opening, closing, and lifecycle."""

    def setUp(self):
        self.p = Portfolio(initial_capital=100_000.0)
        self.ts = pd.Timestamp("2024-01-01")

    def test_open_position_deducts_cash(self):
        self.p.open_position("AAPL", 1, 100, 150.0, self.ts, commission=10.0)
        self.assertAlmostEqual(self.p.cash, 100_000.0 - (100 * 150.0 + 10.0))
        self.assertEqual(self.p.position_count, 1)

    def test_open_position_returns_none(self):
        result = self.p.open_position("AAPL", 1, 100, 150.0, self.ts)
        self.assertIsNone(result)

    def test_get_position_returns_position(self):
        self.p.open_position("AAPL", 1, 100, 150.0, self.ts)
        pos = self.p.get_position("AAPL")
        self.assertIsNotNone(pos)
        self.assertEqual(pos.symbol, "AAPL")
        self.assertEqual(pos.direction, 1)
        self.assertEqual(pos.size, 100)

    def test_get_position_returns_none_for_missing(self):
        self.assertIsNone(self.p.get_position("MISSING"))

    def test_close_position_returns_trade_record(self):
        self.p.open_position("AAPL", 1, 100, 150.0, self.ts)
        record = self.p.close_position("AAPL", 155.0, pd.Timestamp("2024-01-10"), "signal")
        self.assertIsNotNone(record)
        self.assertIsInstance(record, TradeRecord)
        self.assertEqual(record.symbol, "AAPL")
        self.assertEqual(record.exit_reason, "signal")
        self.assertGreater(record.pnl, 0)

    def test_close_position_adds_cash(self):
        self.p.open_position("AAPL", 1, 100, 150.0, self.ts)
        cash_before = self.p.cash
        entry_value = 100 * 150.0
        self.p.close_position("AAPL", 155.0, pd.Timestamp("2024-01-10"), "signal")
        self.assertEqual(self.p.position_count, 0)
        self.assertGreater(self.p.cash, cash_before)
        self.assertAlmostEqual(self.p.cash, cash_before + entry_value + (155.0 - 150.0) * 100)

    def test_close_nonexistent_returns_none(self):
        result = self.p.close_position("NONE", 100.0, self.ts, "signal")
        self.assertIsNone(result)

    def test_can_open_position_true(self):
        self.assertTrue(self.p.can_open_position(150.0, 100, 10.0))

    def test_can_open_position_false_insufficient_cash(self):
        self.assertFalse(self.p.can_open_position(1e9, 1, 0))

    def test_can_open_position_false_max_positions(self):
        for i in range(10):
            self.p.open_position(f"SYM{i}", 1, 1, 100.0, self.ts)
        self.assertFalse(self.p.can_open_position(100.0, 1, 0))

    def test_open_position_reduces_size_for_limited_cash(self):
        self.p.cash = 500.0
        result = self.p.open_position("AAPL", 1, 10000, 100.0, self.ts, commission=0)
        self.assertIsNone(result)
        pos = self.p.get_position("AAPL")
        self.assertIsNotNone(pos)
        self.assertAlmostEqual(pos.size, 5.0)  # 500 / 100

    def test_open_position_returns_none_when_cash_insufficient(self):
        self.p.cash = 10.0
        result = self.p.open_position("AAPL", 1, 100, 150.0, self.ts, commission=20.0)
        self.assertIsNone(result)

    def test_open_position_replaces_existing(self):
        self.p.open_position("AAPL", 1, 100, 150.0, self.ts)
        self.p._current_prices["AAPL"] = 150.0
        self.p.open_position("AAPL", 1, 50, 160.0, self.ts)
        self.assertEqual(self.p.position_count, 1)
        pos = self.p.get_position("AAPL")
        self.assertEqual(pos.size, 50)
        self.assertEqual(pos.entry_price, 160.0)

    def test_equity_includes_unrealized_pnl(self):
        self.p.open_position("AAPL", 1, 100, 150.0, self.ts)
        self.p._current_prices["AAPL"] = 160.0
        expected_equity = self.p.cash + (100 * 150.0) + (160.0 - 150.0) * 100
        self.assertAlmostEqual(self.p.equity, expected_equity)

    def test_unrealized_pnl_positive(self):
        self.p.open_position("AAPL", 1, 100, 150.0, self.ts)
        self.p._current_prices["AAPL"] = 160.0
        self.assertAlmostEqual(self.p.unrealized_pnl, 1000.0)

    def test_unrealized_pnl_negative(self):
        self.p.open_position("AAPL", 1, 100, 150.0, self.ts)
        self.p._current_prices["AAPL"] = 140.0
        self.assertAlmostEqual(self.p.unrealized_pnl, -1000.0)

    def test_mark_to_market_updates_prices(self):
        self.p.open_position("AAPL", 1, 100, 150.0, self.ts)
        self.p.open_position("MSFT", -1, 50, 300.0, self.ts)
        price_series = pd.Series({"AAPL": 160.0, "MSFT": 290.0})
        self.p.mark_to_market(price_series)
        self.assertEqual(self.p._current_prices["AAPL"], 160.0)
        self.assertEqual(self.p._current_prices["MSFT"], 290.0)
        self.assertEqual(self.p._bar_count, 1)

    def test_apply_commission(self):
        cash_before = self.p.cash
        self.p._apply_commission("AAPL", 15.0)
        self.assertAlmostEqual(self.p.cash, cash_before - 15.0)

    def test_position_direction_short(self):
        self.p.open_position("AAPL", -1, 100, 150.0, self.ts)
        pos = self.p.get_position("AAPL")
        self.assertEqual(pos.direction, -1)
        self.p.close_position("AAPL", 140.0, pd.Timestamp("2024-01-10"), "signal")
        self.assertAlmostEqual(self.p.cash, 100_000.0 + (-1) * 100 * (140.0 - 150.0), places=4)

    def test_holding_bars_in_trade_record(self):
        self.p.open_position("AAPL", 1, 100, 150.0, self.ts)
        self.p._bar_count = 10
        record = self.p.close_position("AAPL", 155.0, pd.Timestamp("2024-01-10"), "signal")
        self.assertEqual(record.holding_bars, 10)


class TestPerformanceMetricsCalculate(unittest.TestCase):
    """PerformanceMetrics.calculate for all key metrics."""

    def setUp(self):
        self.metrics = PerformanceMetrics(bars_per_year=252)

    def _make_equity(self, values):
        return pd.Series(values, index=pd.date_range("2024-01-01", periods=len(values), freq="D"))

    def test_empty_equity_returns_defaults(self):
        eq = pd.Series(dtype=float)
        result = self.metrics.calculate(eq, [], 1_000_000.0)
        self.assertEqual(result["final_equity"], 1_000_000.0)
        self.assertEqual(result["total_return"], 0)

    def test_total_return_positive(self):
        eq = self._make_equity([1_000_000, 1_050_000, 1_100_000])
        result = self.metrics.calculate(eq, [], 1_000_000.0)
        self.assertAlmostEqual(result["total_return"], 0.1)

    def test_total_return_negative(self):
        eq = self._make_equity([1_000_000, 900_000, 800_000])
        result = self.metrics.calculate(eq, [], 1_000_000.0)
        self.assertAlmostEqual(result["total_return"], -0.2)

    def test_cagr(self):
        # 252 days of 0.1% daily return => CAGR ~ (1.001)^252 - 1
        daily = 1_000_000 * (1.001 ** np.arange(253))
        eq = self._make_equity(daily)
        result = self.metrics.calculate(eq, [], 1_000_000.0)
        self.assertAlmostEqual(result["cagr"], 0.001 * 252, places=1)

    def test_sharpe_ratio(self):
        np.random.seed(42)
        daily_rets = np.random.normal(0.001, 0.02, 252)
        equity = 1_000_000 * np.cumprod(1 + daily_rets)
        eq = self._make_equity(equity)
        result = self.metrics.calculate(eq, [], 1_000_000.0)
        self.assertGreater(result["sharpe_ratio"], -10)
        self.assertLess(result["sharpe_ratio"], 10)

    def test_sharpe_ratio_constant_returns(self):
        eq = self._make_equity([1_000_000] * 10)
        result = self.metrics.calculate(eq, [], 1_000_000.0)
        self.assertAlmostEqual(result["sharpe_ratio"], 0.0, places=4)

    def test_sortino_ratio(self):
        returns = np.array([0.001, -0.005, 0.002, -0.003, 0.004, -0.001, 0.003, -0.002])
        equity = 1_000_000 * np.cumprod(1 + returns)
        eq = self._make_equity(equity)
        result = self.metrics.calculate(eq, [], 1_000_000.0)
        self.assertIsInstance(result["sortino_ratio"], float)

    def test_calmar_ratio_with_drawdown(self):
        equity = self._make_equity([1_000_000, 1_200_000, 900_000, 1_100_000])
        result = self.metrics.calculate(equity, [], 1_000_000.0)
        self.assertGreater(result["calmar_ratio"], 0)

    def test_max_drawdown(self):
        equity = self._make_equity([1_000_000, 1_100_000, 800_000, 950_000])
        result = self.metrics.calculate(equity, [], 1_000_000.0)
        self.assertAlmostEqual(result["max_drawdown"], -0.272727, places=4)

    def test_max_drawdown_duration(self):
        equity = self._make_equity([1_000_000, 1_100_000, 900_000, 950_000, 980_000, 1_100_000])
        result = self.metrics.calculate(equity, [], 1_000_000.0)
        self.assertGreaterEqual(result["max_drawdown_duration"], 0)

    def test_volatility(self):
        equity = self._make_equity([1_000_000, 1_010_000, 990_000, 1_020_000, 980_000])
        result = self.metrics.calculate(equity, [], 1_000_000.0)
        self.assertGreater(result["volatility"], 0)

    def test_var_95(self):
        np.random.seed(99)
        daily_rets = np.random.normal(0.0, 0.02, 500)
        equity = 1_000_000 * np.cumprod(1 + daily_rets)
        eq = self._make_equity(equity)
        result = self.metrics.calculate(eq, [], 1_000_000.0)
        self.assertLess(result["var_95"], 0)

    def test_cvar_95(self):
        np.random.seed(99)
        daily_rets = np.random.normal(0.0, 0.02, 500)
        equity = 1_000_000 * np.cumprod(1 + daily_rets)
        eq = self._make_equity(equity)
        result = self.metrics.calculate(eq, [], 1_000_000.0)
        self.assertLess(result["cvar_95"], 0)
        self.assertLessEqual(result["cvar_95"], result["var_95"])

    def test_win_rate_from_trades(self):
        ts = pd.Timestamp("2024-01-01")
        trades = [
            TradeRecord("A", 1, 100, 110, ts, ts, 10, 100, 10.0, "signal", 0, 5),
            TradeRecord("A", -1, 100, 90, ts, ts, 10, -100, -10.0, "signal", 0, 3),
            TradeRecord("A", 1, 100, 105, ts, ts, 10, 50, 5.0, "signal", 0, 2),
        ]
        equity = self._make_equity([1_000_000, 1_000_050])
        result = self.metrics.calculate(equity, trades, 1_000_000.0)
        self.assertAlmostEqual(result["win_rate"], 2 / 3, places=4)

    def test_profit_factor(self):
        ts = pd.Timestamp("2024-01-01")
        trades = [
            TradeRecord("A", 1, 100, 110, ts, ts, 10, 200, 10.0, "signal", 0, 5),
            TradeRecord("A", 1, 100, 90, ts, ts, 10, -50, -10.0, "signal", 0, 3),
            TradeRecord("A", 1, 100, 102, ts, ts, 10, 20, 2.0, "signal", 0, 2),
        ]
        equity = self._make_equity([1_000_000, 1_000_170])
        result = self.metrics.calculate(equity, trades, 1_000_000.0)
        self.assertAlmostEqual(result["profit_factor"], 220.0 / 50.0, places=4)

    def test_avg_trade_pnl(self):
        ts = pd.Timestamp("2024-01-01")
        trades = [
            TradeRecord("A", 1, 100, 110, ts, ts, 10, 100, 10.0, "signal", 0, 5),
            TradeRecord("A", 1, 100, 90, ts, ts, 10, -50, -5.0, "signal", 0, 3),
        ]
        equity = self._make_equity([1_000_000, 1_000_050])
        result = self.metrics.calculate(equity, trades, 1_000_000.0)
        self.assertAlmostEqual(result["avg_trade_pnl"], 25.0, places=4)

    def test_empty_metrics_with_trades(self):
        ts = pd.Timestamp("2024-01-01")
        trades = [
            TradeRecord("A", 1, 100, 110, ts, ts, 10, 100, 10.0, "signal", 0, 5),
        ]
        equity = self._make_equity([1_000_000])
        result = self.metrics.calculate(equity, trades, 1_000_000.0)
        self.assertEqual(result["total_trades"], 1)

    def test_recovery_factor(self):
        equity = self._make_equity([1_000_000, 900_000, 1_100_000])
        result = self.metrics.calculate(equity, [], 1_000_000.0)
        self.assertGreater(result["recovery_factor"], 0)

    def test_tail_ratio(self):
        np.random.seed(42)
        daily_rets = np.random.normal(0.001, 0.02, 500)
        equity = 1_000_000 * np.cumprod(1 + daily_rets)
        eq = self._make_equity(equity)
        result = self.metrics.calculate(eq, [], 1_000_000.0)
        self.assertGreaterEqual(result["tail_ratio"], 0)

    def test_ulcer_index(self):
        equity = self._make_equity([1_000_000, 950_000, 920_000, 980_000, 1_100_000])
        result = self.metrics.calculate(equity, [], 1_000_000.0)
        self.assertGreater(result["ulcer_index"], 0)

    def test_benchmark_metrics(self):
        np.random.seed(123)
        daily_rets = np.random.normal(0.001, 0.02, 100)
        equity = 1_000_000 * np.cumprod(1 + daily_rets)
        eq = self._make_equity(equity)
        bench = pd.Series(
            np.random.normal(0.0005, 0.015, 100),
            index=eq.index,
        )
        result = self.metrics.calculate(eq, [], 1_000_000.0, benchmark_returns=bench)
        self.assertIn("benchmark_return", result)
        self.assertIn("alpha", result)
        self.assertIn("beta", result)
        self.assertIn("information_ratio", result)
        self.assertIn("tracking_error", result)

    def test_calc_bars_per_year_default(self):
        bpy = PerformanceMetrics.calc_bars_per_year()
        self.assertEqual(bpy, 252)

    def test_calc_bars_per_year_crypto(self):
        bpy = PerformanceMetrics.calc_bars_per_year("1H", "crypto")
        self.assertEqual(bpy, 365 * 24)

    def test_consecutive_losses(self):
        ts = pd.Timestamp("2024-01-01")
        trades = [
            TradeRecord("A", 1, 100, 110, ts, ts, 10, 100, 10.0, "signal", 0, 1),
            TradeRecord("A", 1, 100, 90, ts, ts, 10, -50, -5.0, "signal", 0, 1),
            TradeRecord("A", 1, 100, 90, ts, ts, 10, -30, -3.0, "signal", 0, 1),
            TradeRecord("A", 1, 100, 105, ts, ts, 10, 50, 5.0, "signal", 0, 1),
            TradeRecord("A", 1, 100, 90, ts, ts, 10, -20, -2.0, "signal", 0, 1),
        ]
        equity = self._make_equity([1_000_000, 1_000_050])
        result = self.metrics.calculate(equity, trades, 1_000_000.0)
        self.assertEqual(result["max_consecutive_losses"], 2)


class TestMonteCarloSingleMetric(unittest.TestCase):
    """MonteCarloSimulator basic simulation and results."""

    def setUp(self):
        self.sim = MonteCarloSimulator(num_simulations=100, random_seed=42)

    def test_simulate_trade_shuffle_returns_result(self):
        pnls = [100, -50, 200, -30, 150, -10, 80]
        result = self.sim.simulate_trade_shuffle(pnls, 1_000_000.0)
        self.assertIsInstance(result, MonteCarloResult)
        self.assertEqual(result.num_simulations, 100)
        self.assertEqual(result.metric_name, "total_return")
        self.assertGreater(result.original_value, 0)

    def test_simulate_trade_shuffle_empty_returns_empty(self):
        result = self.sim.simulate_trade_shuffle([], 1_000_000.0)
        self.assertEqual(result.num_simulations, 0)
        self.assertEqual(result.original_value, 0.0)

    def test_simulate_trade_shuffle_max_drawdown(self):
        pnls = [100, -200, 300, -150, 50]
        result = self.sim.simulate_trade_shuffle(pnls, 1_000_000.0, metric="max_drawdown")
        self.assertEqual(result.metric_name, "max_drawdown")
        self.assertLessEqual(result.original_value, 0)

    def test_simulate_trade_shuffle_sharpe(self):
        pnls = [100, -50, 200, -30, 150]
        result = self.sim.simulate_trade_shuffle(pnls, 1_000_000.0, metric="sharpe")
        self.assertEqual(result.metric_name, "sharpe")

    def test_simulate_trade_shuffle_sortino(self):
        pnls = [100, -50, 200, -30, 150]
        result = self.sim.simulate_trade_shuffle(pnls, 1_000_000.0, metric="sortino")
        self.assertEqual(result.metric_name, "sortino")

    def test_simulate_trade_shuffle_calmar(self):
        pnls = [100, -50, 200, -30, 150]
        result = self.sim.simulate_trade_shuffle(pnls, 1_000_000.0, metric="calmar")
        self.assertEqual(result.metric_name, "calmar")

    def test_simulate_trade_shuffle_win_rate(self):
        pnls = [100, -50, 200, -30, 150]
        result = self.sim.simulate_trade_shuffle(pnls, 1_000_000.0, metric="win_rate")
        self.assertEqual(result.metric_name, "win_rate")
        self.assertAlmostEqual(result.original_value, 0.6)

    def test_simulate_bootstrap_returns_result(self):
        returns = pd.Series(np.random.normal(0.001, 0.02, 100))
        result = self.sim.simulate_bootstrap(returns, 1_000_000.0)
        self.assertIsInstance(result, MonteCarloResult)
        self.assertEqual(result.num_simulations, 100)

    def test_simulate_bootstrap_short_returns_empty(self):
        returns = pd.Series([0.01])
        result = self.sim.simulate_bootstrap(returns, 1_000_000.0)
        self.assertEqual(result.num_simulations, 0)

    def test_simulate_bootstrap_block(self):
        returns = pd.Series(np.random.normal(0.001, 0.02, 50))
        result = self.sim.simulate_bootstrap(returns, 1_000_000.0, block_size=5)
        self.assertEqual(result.num_simulations, 100)

    def test_simulate_return_resample(self):
        returns = pd.Series(np.random.normal(0.001, 0.02, 50))
        result = self.sim.simulate_return_resample(returns, 1_000_000.0)
        self.assertIsInstance(result, MonteCarloResult)

    def test_simulate_parametric_normal(self):
        returns = pd.Series(np.random.normal(0.001, 0.02, 100))
        result = self.sim.simulate_parametric(returns, 1_000_000.0, distribution="normal")
        self.assertEqual(result.num_simulations, 100)

    def test_simulate_parametric_short_fails(self):
        returns = pd.Series([0.01])
        result = self.sim.simulate_parametric(returns, 1_000_000.0)
        self.assertEqual(result.num_simulations, 0)

    def test_simulate_price_path(self):
        result = self.sim.simulate_price_path(0.001, 0.02, 100, 1_000_000.0)
        self.assertEqual(result.num_simulations, 100)
        self.assertEqual(result.metric_name, "total_return")

    def test_confidence_intervals(self):
        values = np.random.normal(0.05, 0.1, 1000)
        ci = self.sim.compute_confidence_intervals(values)
        self.assertIn(0.95, ci)
        self.assertIn(0.90, ci)
        self.assertIn(0.99, ci)
        lower, upper = ci[0.95]
        self.assertLess(lower, upper)

    def test_result_has_percentiles(self):
        pnls = [100, -50, 200, -30, 150]
        result = self.sim.simulate_trade_shuffle(pnls, 1_000_000.0, metric="max_drawdown")
        self.assertLessEqual(result.p5, result.p95)
        self.assertLessEqual(result.p25, result.p75)
        self.assertIsNotNone(result.all_sim_values)

    def test_probability_of_loss(self):
        pnls = [100, -50, 200, -30, 150]
        result = self.sim.simulate_trade_shuffle(pnls, 1_000_000.0)
        self.assertGreaterEqual(result.probability_of_loss, 0)
        self.assertLessEqual(result.probability_of_loss, 1)


class TestMonteCarloMultiMetric(unittest.TestCase):
    """MonteCarloSimulator multi-metric and regime-aware."""

    def setUp(self):
        self.sim = MonteCarloSimulator(num_simulations=50, random_seed=42)

    def test_simulate_multi_metric_bootstrap(self):
        returns = pd.Series(np.random.normal(0.001, 0.02, 100))
        result = self.sim.simulate_multi_metric(returns, 1_000_000.0, method="bootstrap")
        self.assertIsInstance(result, MultiMetricMonteCarloResult)
        self.assertIn("total_return", result.metrics)
        self.assertIn("max_drawdown", result.metrics)

    def test_simulate_multi_metric_parametric(self):
        returns = pd.Series(np.random.normal(0.001, 0.02, 100))
        result = self.sim.simulate_multi_metric(returns, 1_000_000.0, method="parametric")
        self.assertIn("total_return", result.metrics)

    def test_simulate_multi_metric_custom_metrics(self):
        returns = pd.Series(np.random.normal(0.001, 0.02, 100))
        result = self.sim.simulate_multi_metric(
            returns, 1_000_000.0, metrics=["sharpe_ratio", "sortino_ratio"], method="bootstrap"
        )
        self.assertIn("sharpe_ratio", result.metrics)
        self.assertIn("sortino_ratio", result.metrics)

    def test_simulate_regime_aware(self):
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.001, 0.02, 100))
        result = self.sim.simulate_regime_aware(returns, 1_000_000.0)
        self.assertEqual(result.num_simulations, 50)

    def test_simulate_regime_aware_short_fails(self):
        returns = pd.Series([0.01] * 10)
        result = self.sim.simulate_regime_aware(returns, 1_000_000.0)
        self.assertEqual(result.num_simulations, 0)

    def test_detect_regimes_returns_array(self):
        returns = np.random.normal(0.001, 0.02, 100)
        regimes = self.sim._detect_regimes(returns, n_regimes=2)
        self.assertEqual(len(regimes), 100)
        self.assertIn(0, regimes)
        self.assertIn(1, regimes)

    def test_detect_regimes_too_short(self):
        returns = np.random.normal(0.001, 0.02, 10)
        regimes = self.sim._detect_regimes(returns, n_regimes=2)
        self.assertTrue(np.all(regimes == 0))

    def test_estimate_transition_matrix(self):
        regimes = np.array([0, 0, 1, 1, 0, 1, 0, 0, 1, 1])
        mat = self.sim._estimate_transition_matrix(regimes, 2)
        self.assertEqual(mat.shape, (2, 2))
        for i in range(2):
            self.assertAlmostEqual(mat[i].sum(), 1.0)

    def test_unknown_distribution_raises(self):
        returns = pd.Series(np.random.normal(0.001, 0.02, 50))
        with self.assertRaises(ValueError):
            self.sim.simulate_parametric(returns, 1_000_000.0, distribution="unknown")

    def test_unknown_method_raises(self):
        returns = pd.Series(np.random.normal(0.001, 0.02, 50))
        with self.assertRaises(ValueError):
            self.sim.simulate_multi_metric(returns, 1_000_000.0, method="unknown")


class TestMonteCarloEdgeCases(unittest.TestCase):
    """Edge cases for Monte Carlo simulation."""

    def test_empty_trades_pnl(self):
        sim = MonteCarloSimulator(num_simulations=10)
        result = sim.simulate_trade_shuffle([], 1_000_000.0)
        self.assertEqual(result.original_value, 0.0)

    def test_single_trade(self):
        sim = MonteCarloSimulator(num_simulations=10)
        result = sim.simulate_trade_shuffle([100.0], 1_000_000.0)
        self.assertEqual(result.num_simulations, 10)
        self.assertAlmostEqual(result.original_value, 0.0001)

    def test_empty_result_has_zero_fields(self):
        sim = MonteCarloSimulator()
        result = sim._empty_result("total_return")
        self.assertEqual(result.original_value, 0.0)
        self.assertEqual(result.num_simulations, 0)
        self.assertEqual(result.probability_of_loss, 1.0)

    def test_block_bootstrap_varied_size(self):
        sim = MonteCarloSimulator(random_seed=42)
        rng = np.random.default_rng(42)
        data = np.array([0.01, -0.02, 0.03, -0.01, 0.02])
        resample = sim._block_bootstrap(rng, data, 2, 10)
        self.assertEqual(len(resample), 10)

    def test_default_confidence_levels(self):
        sim = MonteCarloSimulator()
        self.assertEqual(sim.confidence_levels, [0.90, 0.95, 0.99])

    def test_custom_confidence_levels(self):
        sim = MonteCarloSimulator(confidence_levels=[0.50, 0.80])
        values = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        ci = sim.compute_confidence_intervals(values)
        self.assertIn(0.50, ci)
        self.assertIn(0.80, ci)


if __name__ == "__main__":
    unittest.main()
