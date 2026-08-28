#!/usr/bin/env python3
"""Tests: BaseEngine — abstract base for multi-market engines.

Uses a concrete subclass to test BaseEngine's shared run() loop,
position management, rebalance, close, force-close, and stats.

Run: python3 -m unittest tests/test_base_engine.py -v
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import pandas as pd

from quant_nanggroe.engine.backtest.engines.base_engine import (
    BaseEngine,
    EngineConfig,
    EquitySnapshot,
    Position,
)


class SimpleTestEngine(BaseEngine):
    """Concrete test subclass that uses minimal market rules."""

    def can_execute(self, symbol, direction, bar):
        return True

    def round_size(self, raw_size, price):
        return round(raw_size, 4)

    def calc_commission(self, size, price, direction, is_open):
        return max(size * price * 0.001, 1.0)

    def apply_slippage(self, price, direction):
        slippage = price * 0.0005
        return price + slippage if direction > 0 else price - slippage


class AnotherTestEngine(BaseEngine):
    """Engine that blocks shorts."""

    def can_execute(self, symbol, direction, bar):
        if direction == -1:
            return False
        return True

    def round_size(self, raw_size, price):
        return round(raw_size, 0)

    def calc_commission(self, size, price, direction, is_open):
        return 0.0

    def apply_slippage(self, price, direction):
        return price


class TestBaseEngineInit(unittest.TestCase):
    """Tests for BaseEngine construction."""

    def test_init_with_config(self):
        engine = SimpleTestEngine({"initial_cash": 500_000.0, "leverage": 2.0})
        self.assertEqual(engine.initial_capital, 500_000.0)
        self.assertEqual(engine.default_leverage, 2.0)
        self.assertEqual(engine.capital, 500_000.0)
        self.assertEqual(engine.positions, {})
        self.assertEqual(engine.trades, [])

    def test_default_config(self):
        engine = SimpleTestEngine({})
        self.assertEqual(engine.initial_capital, 1_000_000.0)
        self.assertEqual(engine.default_leverage, 1.0)

    def test_reset_state(self):
        engine = SimpleTestEngine({"initial_cash": 100_000.0})
        engine.positions = {"FAKE": Position("FAKE", 1, 100, pd.Timestamp("2024-01-01"), 10)}
        engine.trades = ["dummy"]
        engine._reset_state()
        self.assertEqual(engine.positions, {})
        self.assertEqual(engine.trades, [])
        self.assertEqual(engine.capital, 100_000.0)
        self.assertEqual(len(engine.equity_snapshots), 0)
        self.assertEqual(engine._bar_idx, 0)

    def test_engine_config_defaults(self):
        cfg = EngineConfig()
        self.assertEqual(cfg.initial_cash, 1_000_000.0)
        self.assertEqual(cfg.leverage, 1.0)
        self.assertEqual(cfg.bars_per_year, 252)
        self.assertIsNone(cfg.benchmark)
        self.assertEqual(cfg.max_positions, 20)

    def test_abstract_methods_prevent_instantiation(self):
        with self.assertRaises(TypeError):
            BaseEngine({})


class TestBaseEngineRun(unittest.TestCase):
    """Tests for BaseEngine.run()."""

    def setUp(self):
        self.engine = SimpleTestEngine({"initial_cash": 100_000.0})
        n = 50
        dates = pd.date_range("2024-01-01", periods=n, freq="D")
        rng = np.random.default_rng(42)
        self.prices = pd.DataFrame(
            {"AAPL": 100.0 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))},
            index=dates,
        )
        self.signals = pd.DataFrame(
            {"AAPL": [0.5 if i % 2 == 0 else 0.0 for i in range(n)]},
            index=dates,
        )

    def test_run_returns_dict_with_expected_keys(self):
        result = self.engine.run(self.prices, self.signals)
        expected_keys = {"metrics", "equity_curve", "trades", "final_equity", "total_trades"}
        self.assertTrue(expected_keys.issubset(result.keys()))

    def test_run_equity_curve_is_series(self):
        result = self.engine.run(self.prices, self.signals)
        self.assertIsInstance(result["equity_curve"], pd.Series)

    def test_run_final_equity_close_to_initial_for_flat_signals(self):
        flat = pd.DataFrame({"AAPL": [0.0] * len(self.prices)}, index=self.prices.index)
        result = self.engine.run(self.prices, flat)
        self.assertAlmostEqual(result["final_equity"], 100_000.0, delta=100)

    def test_run_with_prices_only_index_diff(self):
        prices = self.prices.copy()
        signals = pd.DataFrame(
            {"AAPL": [1.0] * len(self.prices)},
            index=self.prices.index,
        )
        result = self.engine.run(prices, signals)
        self.assertGreaterEqual(result["total_trades"], 0)

    def test_run_resets_state_between_runs(self):
        r1 = self.engine.run(self.prices, self.signals)
        r2 = self.engine.run(self.prices, self.signals)
        self.assertEqual(r1["total_trades"], r2["total_trades"])

    def test_run_different_bars_per_year(self):
        result = self.engine.run(self.prices, self.signals, bars_per_year=365)
        self.assertIn("sharpe_ratio", result["metrics"])

    def test_run_empty_prices(self):
        empty = pd.DataFrame({"AAPL": []}, index=pd.DatetimeIndex([]))
        empty_sig = pd.DataFrame({"AAPL": []}, index=pd.DatetimeIndex([]))
        result = self.engine.run(empty, empty_sig)
        self.assertEqual(result["final_equity"], 100_000.0)

    def test_run_single_bar(self):
        dates = pd.DatetimeIndex(["2024-01-01"])
        prices = pd.DataFrame({"AAPL": [100.0]}, index=dates)
        signals = pd.DataFrame({"AAPL": [1.0]}, index=dates)
        result = self.engine.run(prices, signals)
        self.assertEqual(result["total_trades"], 0)
        self.assertEqual(result["final_equity"], 100_000.0)

    def test_run_with_rebalance_on_every_bar(self):
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        prices = pd.DataFrame({"AAPL": 100.0 + np.arange(10, dtype=float)}, index=dates)
        signals = pd.DataFrame({"AAPL": [1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0]}, index=dates)
        result = self.engine.run(prices, signals)
        self.assertGreater(result["total_trades"], 0)
        self.assertIsInstance(result["final_equity"], float)

    def test_run_custom_position_sizer(self):
        def sizer(signal, capital, price):
            return 5.0
        result = self.engine.run(self.prices, self.signals, position_sizer=sizer)
        self.assertGreaterEqual(result["total_trades"], 0)

    def test_run_with_benchmark_returns_present(self):
        bench = pd.Series(
            np.random.default_rng(42).normal(0.001, 0.01, len(self.prices)),
            index=self.prices.index,
        )
        result = self.engine.run(self.prices, self.signals, benchmark_returns=bench)
        self.assertIn("alpha", result["metrics"])

    def test_run_with_no_trades_metrics(self):
        flat = pd.DataFrame({"AAPL": [0.0] * len(self.prices)}, index=self.prices.index)
        result = self.engine.run(self.prices, flat)
        self.assertEqual(result["total_trades"], 0)
        self.assertAlmostEqual(result["final_equity"], 100_000.0, delta=100)


class TestBaseEnginePositionManagement(unittest.TestCase):
    """Tests for _rebalance, _close_position, _force_close_all."""

    def setUp(self):
        self.engine = SimpleTestEngine({"initial_cash": 100_000.0})
        dates = pd.date_range("2024-01-01", periods=5, freq="D")
        self.prices = pd.DataFrame({"AAPL": [100.0, 101.0, 102.0, 101.5, 103.0]}, index=dates)

    def test_rebalance_opens_position(self):
        self.engine._rebalance("AAPL", 0.5, 100.0, pd.Timestamp("2024-01-01"), 100_000.0)
        self.assertIn("AAPL", self.engine.positions)
        pos = self.engine.positions["AAPL"]
        self.assertEqual(pos.direction, 1)
        self.assertGreater(pos.size, 0)

    def test_rebalance_closes_when_target_zero(self):
        self.engine._rebalance("AAPL", 0.5, 100.0, pd.Timestamp("2024-01-01"), 100_000.0)
        self.engine._rebalance("AAPL", 0.0, 101.0, pd.Timestamp("2024-01-02"), 101_000.0)
        self.assertNotIn("AAPL", self.engine.positions)
        self.assertEqual(len(self.engine.trades), 1)

    def test_rebalance_does_nothing_when_no_position_and_zero_target(self):
        self.engine._rebalance("AAPL", 0.0, 100.0, pd.Timestamp("2024-01-01"), 100_000.0)
        self.assertNotIn("AAPL", self.engine.positions)

    def test_close_position_records_trade(self):
        self.engine._rebalance("AAPL", 0.5, 100.0, pd.Timestamp("2024-01-01"), 100_000.0)
        self.engine._close_position("AAPL", 105.0, pd.Timestamp("2024-01-02"), "test_close")
        self.assertNotIn("AAPL", self.engine.positions)
        self.assertEqual(len(self.engine.trades), 1)
        trade = self.engine.trades[0]
        self.assertEqual(trade.exit_reason, "test_close")
        self.assertGreater(trade.exit_price, trade.entry_price)

    def test_close_position_nonexistent(self):
        self.engine._close_position("NONEXISTENT", 100.0, pd.Timestamp("2024-01-01"), "test")
        self.assertEqual(len(self.engine.trades), 0)

    def test_force_close_all_closes_remaining(self):
        self.engine._rebalance("AAPL", 0.3, 100.0, pd.Timestamp("2024-01-01"), 100_000.0)
        self.engine._force_close_all(self.prices)
        self.assertEqual(len(self.engine.positions), 0)
        self.assertEqual(len(self.engine.trades), 1)
        self.assertEqual(self.engine.trades[0].exit_reason, "end_of_backtest")

    def test_force_close_all_empty_prices(self):
        self.engine._force_close_all(pd.DataFrame())
        self.assertEqual(len(self.engine.trades), 0)

    def test_short_engine_blocked_by_can_execute(self):
        eng = AnotherTestEngine({"initial_cash": 100_000.0})
        eng._rebalance("AAPL", -0.5, 100.0, pd.Timestamp("2024-01-01"), 100_000.0)
        self.assertNotIn("AAPL", eng.positions)


class TestBaseEnginePnlAndMargin(unittest.TestCase):
    """Tests for _calc_pnl, _calc_margin, _calc_raw_size."""

    def setUp(self):
        self.engine = SimpleTestEngine({"initial_cash": 100_000.0})

    def test_calc_pnl_long_profit(self):
        pnl = self.engine._calc_pnl("AAPL", 1, 10, 100.0, 110.0)
        self.assertEqual(pnl, 100.0)

    def test_calc_pnl_long_loss(self):
        pnl = self.engine._calc_pnl("AAPL", 1, 10, 100.0, 90.0)
        self.assertEqual(pnl, -100.0)

    def test_calc_pnl_short_profit(self):
        pnl = self.engine._calc_pnl("AAPL", -1, 10, 100.0, 90.0)
        self.assertEqual(pnl, 100.0)

    def test_calc_pnl_short_loss(self):
        pnl = self.engine._calc_pnl("AAPL", -1, 10, 100.0, 110.0)
        self.assertEqual(pnl, -100.0)

    def test_calc_margin(self):
        margin = self.engine._calc_margin("AAPL", 10, 100.0, 2.0)
        self.assertEqual(margin, 500.0)

    def test_calc_margin_no_leverage(self):
        margin = self.engine._calc_margin("AAPL", 10, 100.0, 1.0)
        self.assertEqual(margin, 1000.0)

    def test_calc_raw_size(self):
        size = self.engine._calc_raw_size("AAPL", 50_000.0, 100.0)
        self.assertEqual(size, 500.0)

    def test_calc_raw_size_zero_price(self):
        size = self.engine._calc_raw_size("AAPL", 50_000.0, 0.0)
        self.assertEqual(size, float("inf"))


class TestBaseEngineStats(unittest.TestCase):
    """Tests for _by_symbol_stats and _by_exit_reason_stats."""

    def setUp(self):
        self.engine = SimpleTestEngine({"initial_cash": 100_000.0})
        dates = pd.date_range("2024-01-01", periods=5, freq="D")
        self.prices = pd.DataFrame({"AAPL": [100.0, 101.0, 102.0, 103.0, 104.0]}, index=dates)
        self.signals = pd.DataFrame({"AAPL": [1.0, 0.5, 0.0, 0.5, 0.0]}, index=dates)

    def test_by_symbol_stats_after_backtest(self):
        result = self.engine.run(self.prices, self.signals)
        by_symbol = result["metrics"].get("by_symbol", {})
        if by_symbol:
            for sym, stats in by_symbol.items():
                self.assertIn("count", stats)
                self.assertIn("win_rate", stats)
                self.assertIn("total_pnl", stats)

    def test_by_symbol_stats_empty(self):
        stats = self.engine._by_symbol_stats()
        self.assertEqual(stats, {})

    def test_by_exit_reason_stats_after_backtest(self):
        result = self.engine.run(self.prices, self.signals)
        by_reason = result["metrics"].get("by_exit_reason", {})
        self.assertIsInstance(by_reason, dict)

    def test_by_exit_reason_stats_empty(self):
        stats = self.engine._by_exit_reason_stats()
        self.assertEqual(stats, {})


class TestBaseEngineEquitySnapshot(unittest.TestCase):
    """Tests for EquitySnapshot and equity tracking."""

    def test_snapshot_fields(self):
        snap = EquitySnapshot(
            timestamp=pd.Timestamp("2024-01-01"),
            capital=100_000.0,
            unrealized=500.0,
            equity=100_500.0,
            positions=1,
        )
        self.assertEqual(snap.capital, 100_000.0)
        self.assertEqual(snap.unrealized, 500.0)
        self.assertEqual(snap.equity, 100_500.0)
        self.assertEqual(snap.positions, 1)

    def test_equity_series_from_run(self):
        engine = SimpleTestEngine({"initial_cash": 100_000.0})
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        prices = pd.DataFrame({"AAPL": 100.0 + np.arange(10, dtype=float)}, index=dates)
        signals = pd.DataFrame({"AAPL": [1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0]}, index=dates)
        result = engine.run(prices, signals)
        eq = result["equity_curve"]
        self.assertEqual(len(eq), 10)
        self.assertGreater(len(eq), 0)

    def test_calc_equity_from_prices_no_positions(self):
        engine = SimpleTestEngine({"initial_cash": 200_000.0})
        price_row = pd.Series({"AAPL": 100.0})
        eq = engine._calc_equity_from_prices(price_row)
        self.assertEqual(eq, 200_000.0)

    def test_calc_equity_from_prices_with_position(self):
        engine = SimpleTestEngine({"initial_cash": 200_000.0})
        engine.positions["AAPL"] = Position("AAPL", 1, 100.0, pd.Timestamp("2024-01-01"), 10, 1.0, 0, 0)
        engine.capital = 199_000.0  # used 1000 margin
        price_row = pd.Series({"AAPL": 110.0})
        eq = engine._calc_equity_from_prices(price_row)
        self.assertGreater(eq, 200_000.0)


class TestBaseEngineOnBar(unittest.TestCase):
    """Tests for on_bar hook."""

    def test_on_bar_default_noop(self):
        engine = SimpleTestEngine({"initial_cash": 100_000.0})
        bar = pd.Series({"close": 100.0, "open": 99.0, "high": 101.0, "low": 98.0, "volume": 1000})
        engine.on_bar("AAPL", bar, pd.Timestamp("2024-01-01"))
        self.assertEqual(len(engine.trades), 0)

    def test_on_bar_calls_subclass(self):
        class EngineWithHook(SimpleTestEngine):
            def __init__(self, cfg):
                super().__init__(cfg)
                self.hook_called = False

            def on_bar(self, symbol, bar, timestamp):
                self.hook_called = True

        engine = EngineWithHook({"initial_cash": 100_000.0})
        dates = pd.date_range("2024-01-01", periods=3, freq="D")
        prices = pd.DataFrame({"AAPL": [100.0, 101.0, 102.0]}, index=dates)
        signals = pd.DataFrame({"AAPL": [1.0, 1.0, 1.0]}, index=dates)
        engine.run(prices, signals)
        self.assertTrue(engine.hook_called)


class TestPositionDataclass(unittest.TestCase):
    """Tests for Position frozen dataclass."""

    def test_position_fields(self):
        pos = Position("AAPL", 1, 100.0, pd.Timestamp("2024-01-01"), 10, 1.0, 0, 5.0)
        self.assertEqual(pos.symbol, "AAPL")
        self.assertEqual(pos.direction, 1)
        self.assertEqual(pos.entry_price, 100.0)
        self.assertEqual(pos.size, 10)
        self.assertEqual(pos.leverage, 1.0)
        self.assertEqual(pos.entry_bar_idx, 0)
        self.assertEqual(pos.entry_commission, 5.0)

    def test_position_is_frozen(self):
        pos = Position("AAPL", 1, 100.0, pd.Timestamp("2024-01-01"), 10)
        with self.assertRaises(AttributeError):
            pos.size = 20

    def test_position_defaults(self):
        pos = Position("AAPL", 1, 100.0, pd.Timestamp("2024-01-01"), 10)
        self.assertEqual(pos.leverage, 1.0)
        self.assertEqual(pos.entry_bar_idx, 0)
        self.assertEqual(pos.entry_commission, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
