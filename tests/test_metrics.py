#!/usr/bin/env python3
"""Tests: PerformanceMetrics — Sharpe, Sortino, Calmar, max drawdown, CAGR,
trade statistics, VaR/CVaR, Ulcer Index, benchmark comparison.

Run: python3 -m unittest tests/test_metrics.py -v
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import pandas as pd

from quant_nanggroe.engine.backtest import PerformanceMetrics, TradeRecord


class TestPerformanceMetricsInit(unittest.TestCase):
    """Tests for PerformanceMetrics construction."""

    def test_default_bars_per_year(self):
        pm = PerformanceMetrics()
        self.assertEqual(pm.bars_per_year, 252)

    def test_custom_bars_per_year(self):
        pm = PerformanceMetrics(bars_per_year=365)
        self.assertEqual(pm.bars_per_year, 365)


class TestPerformanceMetricsCalculate(unittest.TestCase):
    """Tests for PerformanceMetrics.calculate()."""

    def setUp(self):
        self.pm = PerformanceMetrics(bars_per_year=252)
        n = 252
        dates = pd.date_range("2024-01-01", periods=n, freq="D")
        rng = np.random.default_rng(42)
        equity = 1_000_000.0 * np.exp(np.cumsum(rng.normal(0.001, 0.01, n)))
        self.equity_curve = pd.Series(equity, index=dates)
        self.initial_capital = 1_000_000.0
        self.trades = [
            TradeRecord(
                symbol="AAPL", direction=1,
                entry_price=100.0, exit_price=105.0,
                entry_time=dates[0], exit_time=dates[10],
                size=100, pnl=500.0, pnl_pct=0.05,
                exit_reason="signal", commission=10.0, holding_bars=10,
            ),
            TradeRecord(
                symbol="AAPL", direction=-1,
                entry_price=105.0, exit_price=100.0,
                entry_time=dates[11], exit_time=dates[20],
                size=100, pnl=-500.0, pnl_pct=-0.0476,
                exit_reason="signal", commission=10.0, holding_bars=9,
            ),
        ]

    def test_calculate_returns_dict_with_all_fields(self):
        metrics = self.pm.calculate(self.equity_curve, self.trades, self.initial_capital)
        expected_fields = [
            "total_return", "cagr", "max_drawdown", "sharpe_ratio",
            "sortino_ratio", "calmar_ratio", "win_rate", "profit_factor",
            "total_trades", "final_equity", "var_95", "cvar_95",
            "recovery_factor", "tail_ratio", "ulcer_index",
            "volatility", "downside_deviation",
            "avg_trade_pnl", "avg_win", "avg_loss",
            "max_consecutive_losses", "avg_holding_bars",
        ]
        for field in expected_fields:
            self.assertIn(field, metrics, f"Missing field: {field}")

    def test_total_return_correct(self):
        metrics = self.pm.calculate(self.equity_curve, self.trades, self.initial_capital)
        expected_return = self.equity_curve.iloc[-1] / self.initial_capital - 1
        self.assertAlmostEqual(metrics["total_return"], expected_return, places=6)

    def test_sharpe_ratio_positive_for_good_returns(self):
        metrics = self.pm.calculate(self.equity_curve, self.trades, self.initial_capital)
        self.assertGreater(metrics["sharpe_ratio"], 0)

    def test_total_trades_correct(self):
        metrics = self.pm.calculate(self.equity_curve, self.trades, self.initial_capital)
        self.assertEqual(metrics["total_trades"], 2)

    def test_win_rate(self):
        metrics = self.pm.calculate(self.equity_curve, self.trades, self.initial_capital)
        self.assertEqual(metrics["win_rate"], 0.5)

    def test_max_drawdown_non_positive(self):
        metrics = self.pm.calculate(self.equity_curve, self.trades, self.initial_capital)
        self.assertLessEqual(metrics["max_drawdown"], 0)

    def test_final_equity_matches(self):
        metrics = self.pm.calculate(self.equity_curve, self.trades, self.initial_capital)
        self.assertAlmostEqual(metrics["final_equity"], self.equity_curve.iloc[-1], places=4)

    def test_cagr_reasonable(self):
        metrics = self.pm.calculate(self.equity_curve, self.trades, self.initial_capital)
        self.assertIsInstance(metrics["cagr"], float)

    def test_var_95_negative(self):
        metrics = self.pm.calculate(self.equity_curve, self.trades, self.initial_capital)
        self.assertLessEqual(metrics["var_95"], 0)

    def test_cvar_95_less_than_or_equal_var(self):
        metrics = self.pm.calculate(self.equity_curve, self.trades, self.initial_capital)
        self.assertLessEqual(metrics["cvar_95"], metrics["var_95"])

    def test_profit_factor(self):
        metrics = self.pm.calculate(self.equity_curve, self.trades, self.initial_capital)
        self.assertGreaterEqual(metrics["profit_factor"], 0)


class TestPerformanceMetricsEmptyEdgeCases(unittest.TestCase):
    """Tests for PerformanceMetrics with empty/edge data."""

    def setUp(self):
        self.pm = PerformanceMetrics()

    def test_empty_equity_curve(self):
        metrics = self.pm.calculate(pd.Series([], dtype=float), [], 1_000_000.0)
        self.assertEqual(metrics["final_equity"], 1_000_000.0)
        self.assertEqual(metrics["total_return"], 0)
        self.assertEqual(metrics["total_trades"], 0)

    def test_single_bar_equity_curve(self):
        equity = pd.Series([1_000_000.0], index=pd.DatetimeIndex(["2024-01-01"]))
        metrics = self.pm.calculate(equity, [], 1_000_000.0)
        self.assertEqual(metrics["total_return"], 0)
        self.assertEqual(metrics["total_trades"], 0)

    def test_constant_equity_no_return(self):
        equity = pd.Series(np.ones(50) * 1_000_000.0, index=pd.date_range("2024-01-01", periods=50, freq="D"))
        metrics = self.pm.calculate(equity, [], 1_000_000.0)
        self.assertAlmostEqual(metrics["total_return"], 0.0, places=6)
        self.assertEqual(metrics["sharpe_ratio"], 0.0)

    def test_negative_total_return_cagr_handling(self):
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        equity = pd.Series([1_000_000.0 * 0.9] * 10, index=dates)
        equity.iloc[-1] = 500_000.0  # 50% loss
        metrics = self.pm.calculate(equity, [], 1_000_000.0)
        self.assertLess(metrics["total_return"], -0.4)
        self.assertIsInstance(metrics["cagr"], float)

    def test_no_trades(self):
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        equity = 1_000_000.0 * np.exp(np.cumsum(np.zeros(10)))
        metrics = self.pm.calculate(pd.Series(equity, index=dates), [], 1_000_000.0)
        self.assertEqual(metrics["total_trades"], 0)
        self.assertEqual(metrics["win_rate"], 0.0)
        self.assertEqual(metrics["max_consecutive_losses"], 0)

    def test_all_losses(self):
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        trades = [
            TradeRecord("X", 1, 100, 90, dates[0], dates[1], 10, -100, -0.1, "signal", 5, 1),
            TradeRecord("X", 1, 90, 80, dates[2], dates[3], 10, -100, -0.1, "signal", 5, 1),
        ]
        equity = pd.Series(
            1_000_000.0 * np.exp(np.cumsum(np.random.default_rng(42).normal(-0.001, 0.01, 10))),
            index=dates,
        )
        metrics = self.pm.calculate(equity, trades, 1_000_000.0)
        self.assertEqual(metrics["win_rate"], 0.0)
        self.assertGreaterEqual(metrics["profit_factor"], 0)

    def test_all_wins(self):
        dates = pd.date_range("2024-01-01", periods=5, freq="D")
        trades = [
            TradeRecord("X", 1, 100, 110, dates[0], dates[1], 10, 100, 0.1, "signal", 5, 1),
        ]
        equity = pd.Series(
            1_000_000.0 * np.exp(np.cumsum(np.random.default_rng(42).normal(0.001, 0.01, 5))),
            index=dates,
        )
        metrics = self.pm.calculate(equity, trades, 1_000_000.0)
        self.assertEqual(metrics["win_rate"], 1.0)


class TestPerformanceMetricsWithBenchmark(unittest.TestCase):
    """Tests for calculate() with benchmark_returns."""

    def setUp(self):
        self.pm = PerformanceMetrics(bars_per_year=252)
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        rng = np.random.default_rng(42)
        self.equity = pd.Series(
            1_000_000.0 * np.exp(np.cumsum(rng.normal(0.001, 0.01, 100))),
            index=dates,
        )
        self.benchmark = pd.Series(
            rng.normal(0.0005, 0.01, 100), index=dates,
        )

    def test_benchmark_metrics_present(self):
        metrics = self.pm.calculate(self.equity, [], 1_000_000.0, self.benchmark)
        self.assertIn("alpha", metrics)
        self.assertIn("beta", metrics)
        self.assertIn("excess_return", metrics)
        self.assertIn("information_ratio", metrics)
        self.assertIn("tracking_error", metrics)
        self.assertIn("benchmark_return", metrics)

    def test_beta_reasonable(self):
        metrics = self.pm.calculate(self.equity, [], 1_000_000.0, self.benchmark)
        self.assertIsInstance(metrics["beta"], float)

    def test_no_benchmark_no_benchmark_fields(self):
        metrics = self.pm.calculate(self.equity, [], 1_000_000.0)
        self.assertNotIn("alpha", metrics)
        self.assertNotIn("beta", metrics)


class TestPerformanceMetricsCalcBarsPerYear(unittest.TestCase):
    """Tests for calc_bars_per_year static method."""

    def test_daily_equity(self):
        bpy = PerformanceMetrics.calc_bars_per_year("1D", "equity")
        self.assertEqual(bpy, 252)

    def test_daily_crypto(self):
        bpy = PerformanceMetrics.calc_bars_per_year("1D", "crypto")
        self.assertEqual(bpy, 365)

    def test_minute_equity(self):
        bpy = PerformanceMetrics.calc_bars_per_year("1m", "equity")
        self.assertEqual(bpy, 252 * 390)

    def test_unknown_interval(self):
        bpy = PerformanceMetrics.calc_bars_per_year("unknown", "equity")
        self.assertEqual(bpy, 252)

    def test_unknown_market(self):
        bpy = PerformanceMetrics.calc_bars_per_year("1D", "unknown")
        self.assertEqual(bpy, 365)


class TestPerformanceMetricsDrawdownDuration(unittest.TestCase):
    """Tests for _calc_max_drawdown_duration."""

    def test_rising_equity(self):
        equity = pd.Series([100, 101, 102, 103, 104])
        duration = PerformanceMetrics._calc_max_drawdown_duration(equity)
        self.assertGreaterEqual(duration, 0)

    def test_never_recovers(self):
        equity = pd.Series([100, 90, 80, 85, 82])
        duration = PerformanceMetrics._calc_max_drawdown_duration(equity)
        self.assertGreater(duration, 0)

    def test_short_equity(self):
        duration = PerformanceMetrics._calc_max_drawdown_duration(pd.Series([100]))
        self.assertEqual(duration, 0)

    def test_empty_equity(self):
        duration = PerformanceMetrics._calc_max_drawdown_duration(pd.Series([], dtype=float))
        self.assertEqual(duration, 0)


class TestPerformanceMetricsUlcerIndex(unittest.TestCase):
    """Tests for _calc_ulcer_index."""

    def test_no_drawdown(self):
        dd = pd.Series([0.0, 0.0, 0.0])
        ui = PerformanceMetrics._calc_ulcer_index(dd)
        self.assertEqual(ui, 0.0)

    def test_with_drawdown(self):
        dd = pd.Series([0.0, -0.1, -0.2, -0.1, 0.0])
        ui = PerformanceMetrics._calc_ulcer_index(dd)
        self.assertGreater(ui, 0)

    def test_empty_series(self):
        ui = PerformanceMetrics._calc_ulcer_index(pd.Series([], dtype=float))
        self.assertEqual(ui, 0.0)


class TestTradeStatistics(unittest.TestCase):
    """Tests for _trade_statistics."""

    def setUp(self):
        self.pm = PerformanceMetrics()
        dates = pd.date_range("2024-01-01", periods=10, freq="D")

        self.trades = [
            TradeRecord("A", 1, 100, 110, dates[0], dates[1], 10, 100, 0.1, "signal", 5, 1),
            TradeRecord("A", 1, 110, 105, dates[2], dates[3], 10, -50, -0.05, "signal", 5, 1),
            TradeRecord("A", 1, 105, 115, dates[4], dates[5], 10, 100, 0.095, "signal", 5, 1),
        ]

    def test_win_rate(self):
        stats = self.pm._trade_statistics(self.trades)
        self.assertAlmostEqual(stats["win_rate"], 2 / 3, places=4)

    def test_profit_factor(self):
        stats = self.pm._trade_statistics(self.trades)
        self.assertGreater(stats["profit_factor"], 0)

    def test_max_consecutive_losses(self):
        stats = self.pm._trade_statistics(self.trades)
        self.assertGreaterEqual(stats["max_consecutive_losses"], 0)

    def test_avg_holding_bars(self):
        stats = self.pm._trade_statistics(self.trades)
        self.assertGreater(stats["avg_holding_bars"], 0)

    def test_empty_trades_defaults(self):
        stats = self.pm._trade_statistics([])
        self.assertEqual(stats["win_rate"], 0.0)
        self.assertEqual(stats["profit_factor"], 0.0)
        self.assertEqual(stats["max_consecutive_losses"], 0)
        self.assertEqual(stats["avg_holding_bars"], 0.0)
        self.assertEqual(stats["avg_trade_pnl"], 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
