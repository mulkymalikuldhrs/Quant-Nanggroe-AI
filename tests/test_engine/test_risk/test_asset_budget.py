"""Tests: Per-asset risk budgets (P1-26) + Concentration limits & cost-aware budget (P1-32).

Run: python3 -m unittest tests/test_risk/test_asset_budget.py -v
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from quant_nanggroe.engine.risk.constants import (
    HARD_STOP_ATR_MULTIPLIER,
    MAX_ASSET_DAILY_LOSS_PCT,
    MAX_POSITION_SIZE_PCT,
    MAX_TOTAL_CONCENTRATION,
    TRADING_BUDGET_PCT,
)
from quant_nanggroe.engine.risk.manager import RiskManager


class TestAssetBudgetSetAndCheck(unittest.TestCase):
    def setUp(self):
        self.rm = RiskManager(initial_equity=1_000_000.0)

    def test_set_asset_budget_defaults(self):
        self.rm.set_asset_budget("AAPL")
        budget = self.rm.asset_budgets["AAPL"]
        self.assertEqual(budget["max_position_pct"], MAX_POSITION_SIZE_PCT)
        self.assertEqual(budget["max_daily_loss_pct"], MAX_ASSET_DAILY_LOSS_PCT)

    def test_set_asset_budget_custom(self):
        self.rm.set_asset_budget("AAPL", max_position_pct=0.05, max_daily_loss_pct=0.02)
        budget = self.rm.asset_budgets["AAPL"]
        self.assertEqual(budget["max_position_pct"], 0.05)
        self.assertEqual(budget["max_daily_loss_pct"], 0.02)

    def test_check_asset_risk_approved(self):
        result = self.rm.check_asset_risk(
            symbol="AAPL",
            pnl_change=100.0,
            current_price=150.0,
            entry_price=148.0,
            atr=2.0,
        )
        self.assertEqual(result["verdict"], "APPROVED")
        self.assertEqual(result["asset_daily_pnl"], 100.0)

    def test_check_asset_risk_daily_loss_exceeded(self):
        big_loss = -1_000_000.0 * MAX_ASSET_DAILY_LOSS_PCT - 1
        result = self.rm.check_asset_risk(
            symbol="AAPL",
            pnl_change=big_loss,
            current_price=150.0,
            entry_price=148.0,
            atr=2.0,
        )
        self.assertEqual(result["verdict"], "REJECTED")
        self.assertIn("ASSET_DAILY_LOSS", result["reason"])

    def test_asset_daily_pnl_reset_on_new_day(self):
        self.rm.asset_daily_pnl["AAPL"] = -5000.0
        self.rm.state.last_reset_date = None
        self.rm.check_asset_risk(
            symbol="AAPL",
            pnl_change=100.0,
            current_price=150.0,
            entry_price=148.0,
            atr=2.0,
        )
        self.assertEqual(self.rm.asset_daily_pnl["AAPL"], 100.0)


class TestHardStopAtEntry(unittest.TestCase):
    def setUp(self):
        self.rm = RiskManager(initial_equity=1_000_000.0)

    def test_hard_stop_initialized_on_first_call(self):
        symbol = "AAPL"
        self.rm.check_asset_risk(
            symbol=symbol,
            pnl_change=0,
            current_price=150.0,
            entry_price=150.0,
            atr=2.0,
        )
        self.assertIn(symbol, self.rm._hard_stops)
        self.assertEqual(self.rm._hard_stops[symbol]["entry_price"], 150.0)
        expected_stop = 150.0 - HARD_STOP_ATR_MULTIPLIER * 2.0
        self.assertAlmostEqual(self.rm._hard_stops[symbol]["stop_price"], expected_stop)

    def test_hard_stop_triggers_long(self):
        symbol = "TSLA"
        entry = 200.0
        atr = 5.0
        stop_distance = HARD_STOP_ATR_MULTIPLIER * atr

        result = self.rm.check_asset_risk(
            symbol=symbol,
            pnl_change=0,
            current_price=entry - stop_distance - 0.01,
            entry_price=entry,
            atr=atr,
        )
        self.assertEqual(result["verdict"], "REJECTED")
        self.assertIn("HARD_STOP", result["reason"])

    def test_hard_stop_not_triggered_within_limit(self):
        symbol = "TSLA"
        entry = 200.0
        atr = 5.0
        within_distance = (HARD_STOP_ATR_MULTIPLIER * atr) - 1.0

        result = self.rm.check_asset_risk(
            symbol=symbol,
            pnl_change=0,
            current_price=entry - within_distance,
            entry_price=entry,
            atr=atr,
        )
        self.assertEqual(result["verdict"], "APPROVED")

    def test_hard_stop_tightens_only(self):
        symbol = "NVDA"
        entry = 100.0
        long_direction_price = 110.0  # price moving up, tighten stop

        self.rm.check_asset_risk(
            symbol=symbol,
            pnl_change=0,
            current_price=long_direction_price,
            entry_price=entry,
            atr=3.0,
        )
        first_stop = self.rm._hard_stops[symbol]["stop_price"]

        # Price moves further up — stop should tighten (move up)
        self.rm.check_asset_risk(
            symbol=symbol,
            pnl_change=0,
            current_price=120.0,
            entry_price=entry,
            atr=3.0,
        )
        second_stop = self.rm._hard_stops[symbol]["stop_price"]

        self.assertGreater(second_stop, first_stop,
                           "Hard stop should tighten (move up) as price rises")


class TestConcentrationLimits(unittest.TestCase):
    def setUp(self):
        self.rm = RiskManager(initial_equity=1_000_000.0)

    def test_check_concentration_approved(self):
        result = self.rm.check_concentration("AAPL", 50_000.0, 1_000_000.0)
        self.assertEqual(result["verdict"], "APPROVED")
        self.assertEqual(result["current_pct"], 0.05)

    def test_check_concentration_rejected(self):
        result = self.rm.check_concentration("AAPL", 200_000.0, 1_000_000.0)
        self.assertEqual(result["verdict"], "REJECTED")
        self.assertIn("CONCENTRATION_LIMIT", result["reason"])

    def test_check_concentration_custom_limit(self):
        self.rm.concentration_limits["AAPL"] = 0.03
        result = self.rm.check_concentration("AAPL", 40_000.0, 1_000_000.0)
        self.assertEqual(result["verdict"], "REJECTED")

    def test_check_total_concentration_approved(self):
        positions = [
            {"market_value": 200_000.0},
            {"market_value": 300_000.0},
        ]
        result = self.rm.check_total_concentration(positions, 1_000_000.0)
        self.assertEqual(result["verdict"], "APPROVED")
        self.assertEqual(result["total_pct"], 0.50)

    def test_check_total_concentration_rejected(self):
        positions = [
            {"market_value": 500_000.0},
            {"market_value": 400_000.0},
        ]
        result = self.rm.check_total_concentration(positions, 1_000_000.0)
        self.assertEqual(result["verdict"], "REJECTED")
        self.assertIn("TOTAL_CONCENTRATION", result["reason"])
        self.assertEqual(result["total_pct"], 0.90)

    def test_check_total_concentration_empty_portfolio(self):
        result = self.rm.check_total_concentration([], 0)
        self.assertEqual(result["total_pct"], 0.0)

    def test_max_total_concentration_constant(self):
        self.assertEqual(MAX_TOTAL_CONCENTRATION, 0.80)


class TestCostBudget(unittest.TestCase):
    def setUp(self):
        self.rm = RiskManager(initial_equity=1_000_000.0)

    def test_initial_cost_budget(self):
        expected = 1_000_000.0 * TRADING_BUDGET_PCT
        self.assertAlmostEqual(self.rm.cost_budget_remaining, expected)

    def test_track_cost_deducts(self):
        self.rm.track_cost(100.0)
        expected = (1_000_000.0 * TRADING_BUDGET_PCT) - 100.0
        self.assertAlmostEqual(self.rm.cost_budget_remaining, expected)

    def test_track_cost_returns_info(self):
        result = self.rm.track_cost(50.0)
        self.assertEqual(result["cost"], 50.0)
        self.assertFalse(result["budget_exhausted"])

    def test_track_cost_budget_exhausted(self):
        total_budget = 1_000_000.0 * TRADING_BUDGET_PCT
        self.rm.track_cost(total_budget)
        self.assertAlmostEqual(self.rm.cost_budget_remaining, 0.0)

    def test_check_cost_affordable_true(self):
        self.assertTrue(self.rm.check_cost_affordable(100.0))

    def test_check_cost_affordable_false(self):
        total_budget = 1_000_000.0 * TRADING_BUDGET_PCT
        self.assertFalse(self.rm.check_cost_affordable(total_budget + 1.0))


if __name__ == "__main__":
    unittest.main()
