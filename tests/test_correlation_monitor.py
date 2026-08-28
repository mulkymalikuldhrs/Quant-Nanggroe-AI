#!/usr/bin/env python3
"""Tests: StrategyCorrelationMonitor — herding detection & kill switch.

Run: python3 -m unittest tests/test_correlation_monitor.py -v
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import shutil
import tempfile
from pathlib import Path

import numpy as np

from quant_nanggroe.engine.risk.correlation import StrategyCorrelationMonitor
from quant_nanggroe.engine.risk.kill_switch import KillSwitch


class TestStrategyCorrelationMonitor(unittest.TestCase):
    """Tests for StrategyCorrelationMonitor."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_monitor(self, threshold=0.85, window=30):
        return StrategyCorrelationMonitor(
            kill_switch=KillSwitch(),
            window=window,
            threshold=threshold,
            state_dir=self.tmpdir,
        )

    # ── 1. Identical returns → ρ ≈ 1.0 → triggers kill switch ────────────

    def test_identical_returns_trigger_herding(self):
        mon = self._make_monitor(threshold=0.5)
        returns = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        mon.update("strat_a", returns)
        mon.update("strat_b", returns)
        status = mon.check_and_act()
        self.assertIsNotNone(status["avg_correlation"])
        self.assertGreater(status["avg_correlation"], 0.5)
        self.assertTrue(mon._fired)
        self.assertTrue(mon.kill_switch.is_active)

    # ── 2. Independent returns → ρ ≈ 0 → no trigger ──────────────────────

    def test_independent_returns_no_trigger(self):
        mon = self._make_monitor(threshold=0.85)
        rng_a = np.random.default_rng(42)
        rng_b = np.random.default_rng(99)
        returns_a = rng_a.normal(0, 1, 30)
        returns_b = rng_b.normal(0, 1, 30)
        mon.update("strat_a", returns_a)
        mon.update("strat_b", returns_b)
        status = mon.check_and_act()
        self.assertIsNotNone(status["avg_correlation"])
        self.assertLess(abs(status["avg_correlation"]), 0.5)
        self.assertFalse(mon._fired)

    # ── 3. Empty state (no strategies registered) ──────────────────────────

    def test_empty_state(self):
        mon = self._make_monitor()
        corr = mon.compute_correlations()
        self.assertEqual(corr, {})
        status = mon.get_status()
        self.assertEqual(status["num_strategies"], 0)
        self.assertIsNone(status["avg_correlation"])

    # ── 4. Insufficient data (< 3 points) → no correlations ──────────────

    def test_insufficient_data(self):
        mon = self._make_monitor()
        mon.update("strat_a", np.array([1.0]))
        mon.update("strat_b", np.array([2.0]))
        corr = mon.compute_correlations()
        self.assertTrue(all(len(pairs) == 0 for pairs in corr.values()))

    def test_insufficient_data_one_side(self):
        mon = self._make_monitor()
        mon.update("strat_a", np.array([1.0, 2.0, 3.0, 4.0, 5.0]))
        mon.update("strat_b", np.array([1.0, 2.0]))
        corr = mon.compute_correlations()
        self.assertTrue(all(len(pairs) == 0 for pairs in corr.values()))

    # ── 5. State persistence round-trip ───────────────────────────────────

    def test_state_persistence_round_trip(self):
        mon1 = self._make_monitor()
        rng = np.random.default_rng(42)
        mon1.update("strat_a", rng.normal(0.001, 0.01, 10))
        mon1.update("strat_b", rng.normal(0.002, 0.01, 10))
        mon1.save_state(Path(self.tmpdir) / "correlation_state.json")
        status1 = mon1.get_status()

        mon2 = StrategyCorrelationMonitor(
            kill_switch=KillSwitch(),
            window=30,
            threshold=0.85,
            state_dir=self.tmpdir,
        )
        status2 = mon2.get_status()
        self.assertEqual(status1["num_strategies"], status2["num_strategies"])
        self.assertEqual(set(status1["matrix"].keys()), set(status2["matrix"].keys()))
        self.assertEqual(mon1._fired, mon2._fired)

    # ── 6. check_and_act with no kill switch (edge) ───────────────────────

    def test_no_kill_switch_still_logs(self):
        mon = StrategyCorrelationMonitor(
            kill_switch=None, window=30, threshold=0.5, state_dir=self.tmpdir,
        )
        returns = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        mon.update("strat_a", returns)
        mon.update("strat_b", returns)
        status = mon.check_and_act()
        self.assertGreater(status["avg_correlation"], 0.5)
        self.assertIsNone(mon.kill_switch)

    # ── 7. Single strategy → no correlations possible ────────────────────

    def test_single_strategy_no_correlation(self):
        mon = self._make_monitor()
        mon.update("strat_a", np.array([1.0, 2.0, 3.0, 4.0, 5.0]))
        status = mon.get_status()
        self.assertEqual(status["num_strategies"], 1)
        self.assertIsNone(status["avg_correlation"])
        self.assertEqual(status["matrix"], {})

    # ── 8. check_and_act returns status dict ─────────────────────────────

    def test_check_and_act_returns_status(self):
        mon = self._make_monitor()
        result = mon.check_and_act()
        self.assertIn("num_strategies", result)
        self.assertIn("avg_correlation", result)
        self.assertIn("threshold", result)
        self.assertIn("kill_switch_fired", result)

    # ── 9. Re-firing prevention (one-shot flag) ──────────────────────────

    def test_only_fires_once(self):
        mon = self._make_monitor(threshold=0.5)
        returns = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        mon.update("strat_a", returns)
        mon.update("strat_b", returns)

        status1 = mon.check_and_act()
        self.assertTrue(mon._fired)

        event_count = len(mon.kill_switch._events)

        status2 = mon.check_and_act()
        self.assertEqual(len(mon.kill_switch._events), event_count)

    # ── 10. Custom threshold ─────────────────────────────────────────────

    def test_custom_threshold_not_breached(self):
        mon = self._make_monitor(threshold=0.99)
        rng = np.random.default_rng(42)
        returns_a = rng.normal(0, 1, 30)
        returns_b = rng.normal(0, 1, 30)
        mon.update("strat_a", returns_a)
        mon.update("strat_b", returns_b)
        status = mon.check_and_act()
        self.assertFalse(mon._fired)


if __name__ == "__main__":
    unittest.main(verbosity=2)
