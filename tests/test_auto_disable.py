#!/usr/bin/env python3
"""Tests: AutoDisableManager — trailing Sharpe based auto-disable.

Run: python3 -m unittest tests/test_auto_disable.py -v
"""

from __future__ import annotations

import sys
import unittest
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import shutil
import tempfile

import numpy as np
import pandas as pd

from quant_nanggroe.engine.risk.strategy_auto_disable import (
    AutoDisableManager,
    StrategyPerformance,
)
from quant_nanggroe.engine.risk.kill_switch import KillSwitch


class TestAutoDisableManager(unittest.TestCase):
    """Tests for AutoDisableManager."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.state_path = os.path.join(self.tmpdir, "auto_disable_state.json")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_mgr(self, **kwargs):
        params = dict(
            sharpe_window=30,
            threshold=0.3,
            confirm_window=30,
            state_path=self.state_path,
            kill_switch=KillSwitch(),
        )
        params.update(kwargs)
        return AutoDisableManager(**params)

    # ── 1. High trailing Sharpe → stays active ───────────────────────────

    def test_high_sharpe_stays_active(self):
        mgr = self._make_mgr()
        rng = np.random.default_rng(42)
        returns = pd.Series(rng.normal(0.002, 0.01, 30))
        active = mgr.update("strat_a", returns)
        self.assertTrue(active)
        self.assertFalse(mgr.is_disabled("strat_a"))

    # ── 2. Low trailing Sharpe → disabled ────────────────────────────────

    def test_low_sharpe_disables(self):
        mgr = self._make_mgr()
        rng = np.random.default_rng(42)
        returns = pd.Series(rng.normal(-0.002, 0.01, 30))
        active = mgr.update("strat_a", returns)
        self.assertFalse(active)
        self.assertTrue(mgr.is_disabled("strat_a"))

    # ── 3. Auto re-enable after confirm_window healthy updates ───────────

    def test_auto_re_enable_after_healthy_period(self):
        mgr = self._make_mgr(confirm_window=3, threshold=0.3)
        rng = pd.Series(np.random.default_rng(42).normal(-0.002, 0.01, 30))
        mgr.update("strat_a", rng)
        self.assertTrue(mgr.is_disabled("strat_a"))

        for _ in range(3):
            good = pd.Series(np.random.default_rng(99).normal(0.002, 0.01, 30))
            mgr.update("strat_a", good)

        self.assertFalse(mgr.is_disabled("strat_a"))
        self.assertIn("strat_a", mgr.get_active_strategies())

    # ── 4. Threshold boundary — just above stays active ──────────────────

    def test_boundary_just_above_threshold(self):
        mgr = self._make_mgr(threshold=0.0, sharpe_window=30)
        rng = np.random.default_rng(42)
        returns = pd.Series(rng.normal(0.0, 0.01, 30))
        active = mgr.update("strat_a", returns)
        self.assertTrue(active)

    # ── 5. State persistence round-trip ──────────────────────────────────

    def test_state_persistence_round_trip(self):
        mgr1 = self._make_mgr()
        rng = np.random.default_rng(42)
        bad = pd.Series(rng.normal(-0.002, 0.01, 30))
        mgr1.update("strat_a", bad)
        self.assertTrue(mgr1.is_disabled("strat_a"))

        mgr2 = self._make_mgr()
        self.assertTrue(mgr2.is_disabled("strat_a"))
        self.assertEqual(mgr2.get_config(), mgr1.get_config())

    # ── 6. Short series (< sharpe_window) not disabled ───────────────────

    def test_short_series_does_not_disable(self):
        mgr = self._make_mgr(sharpe_window=30)
        short = pd.Series(np.random.default_rng(42).normal(-0.002, 0.01, 10))
        active = mgr.update("strat_a", short)
        self.assertTrue(active)
        self.assertFalse(mgr.is_disabled("strat_a"))

    # ── 7. Manual disable / enable ───────────────────────────────────────

    def test_manual_disable_then_enable(self):
        mgr = self._make_mgr()
        self.assertTrue(mgr.disable("strat_a", "Testing"))
        self.assertTrue(mgr.is_disabled("strat_a"))
        self.assertIn("strat_a", mgr.get_disabled_strategies())

        self.assertTrue(mgr.enable("strat_a", "Done testing"))
        self.assertFalse(mgr.is_disabled("strat_a"))
        self.assertNotIn("strat_a", mgr.get_disabled_strategies())

    def test_double_disable_returns_false(self):
        mgr = self._make_mgr()
        self.assertTrue(mgr.disable("strat_a"))
        self.assertFalse(mgr.disable("strat_a"))

    def test_enable_nonexistent_returns_false(self):
        mgr = self._make_mgr()
        self.assertFalse(mgr.enable("nonexistent"))

    # ── 8. Kill switch activation on disable ─────────────────────────────

    def test_kill_switch_not_activated_on_per_strategy_disable(self):
        ks = KillSwitch()
        mgr = self._make_mgr(kill_switch=ks)
        rng = np.random.default_rng(42)
        bad = pd.Series(rng.normal(-0.002, 0.01, 30))
        mgr.update("strat_a", bad)
        self.assertTrue(mgr.is_disabled("strat_a"))
        self.assertFalse(ks.is_active)

    # ── 9. get_state and to_dict serialization ───────────────────────────

    def test_get_state_serializable(self):
        mgr = self._make_mgr()
        rng = np.random.default_rng(42)
        mgr.update("strat_a", pd.Series(rng.normal(-0.002, 0.01, 30)))
        state = mgr.get_state()
        dumped = json.dumps(state)
        loaded = json.loads(dumped)
        self.assertIn("strat_a", loaded)
        self.assertTrue(loaded["strat_a"]["disabled"])

    # ── 10. None series does not disable ─────────────────────────────────

    def test_none_series_no_disable(self):
        mgr = self._make_mgr()
        active = mgr.update("strat_a", None)
        self.assertTrue(active)

    # ── 11. Multiple strategies tracked independently ────────────────────

    def test_multiple_strategies_independent(self):
        mgr = self._make_mgr()
        rng = np.random.default_rng(42)
        mgr.update("good", pd.Series(rng.normal(0.002, 0.01, 30)))
        mgr.update("bad", pd.Series(rng.normal(-0.002, 0.01, 30)))
        self.assertFalse(mgr.is_disabled("good"))
        self.assertTrue(mgr.is_disabled("bad"))


class TestStrategyPerformance(unittest.TestCase):
    """Tests for StrategyPerformance helper."""

    def test_to_dict_round_trip(self):
        perf = StrategyPerformance("test_strat")
        perf.disabled = True
        perf.disabled_at = "2024-01-01T00:00:00"
        perf.disabled_reason = "test"
        perf.consecutive_above_threshold = 5
        perf.total_updates = 10

        d = perf.to_dict()
        restored = StrategyPerformance.from_dict(d)
        self.assertEqual(restored.name, "test_strat")
        self.assertTrue(restored.disabled)
        self.assertEqual(restored.disabled_at, "2024-01-01T00:00:00")
        self.assertEqual(restored.disabled_reason, "test")
        self.assertEqual(restored.consecutive_above_threshold, 5)
        self.assertEqual(restored.total_updates, 10)

    def test_default_initialization(self):
        perf = StrategyPerformance("new_strat")
        self.assertEqual(perf.name, "new_strat")
        self.assertFalse(perf.disabled)
        self.assertIsNone(perf.disabled_at)
        self.assertEqual(perf.disabled_reason, "")
        self.assertEqual(perf.consecutive_above_threshold, 0)
        self.assertEqual(perf.total_updates, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
