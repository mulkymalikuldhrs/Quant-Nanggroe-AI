"""Tests: AutoDisableManager — additional edge cases, paper mode, persistence, config.

Run: python3 -m unittest tests/test_risk/test_strategy_auto_disable_v2.py -v
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import numpy as np
import pandas as pd

from quant_nanggroe.engine.risk.strategy_auto_disable import (
    AutoDisableManager,
    StrategyPerformance,
)
from quant_nanggroe.engine.risk.kill_switch import KillSwitch


class TestAutoDisableManagerPaperMode(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.state_path = os.path.join(self.tmpdir, "auto_disable_state.json")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_paper_mode_never_disables(self):
        mgr = AutoDisableManager(
            sharpe_window=5,
            threshold=999.0,  # impossible to exceed
            confirm_window=3,
            state_path=self.state_path,
            kill_switch=KillSwitch(),
            paper_mode=True,
        )
        rng = np.random.default_rng(42)
        bad = pd.Series(rng.normal(-0.01, 0.01, 10))
        active = mgr.update("strat_a", bad)
        self.assertTrue(active)

    def test_paper_mode_skips_disable_check(self):
        mgr = AutoDisableManager(
            sharpe_window=5,
            threshold=999.0,
            confirm_window=3,
            state_path=self.state_path,
            kill_switch=KillSwitch(),
            paper_mode=True,
        )
        bad = pd.Series(np.random.default_rng(42).normal(-0.01, 0.01, 10))
        mgr.update("strat_a", bad)
        self.assertFalse(mgr.is_disabled("strat_a"))


class TestAutoDisableManagerConfig(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.state_path = os.path.join(self.tmpdir, "auto_disable_state.json")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_get_config_returns_dict(self):
        mgr = AutoDisableManager(
            sharpe_window=20,
            threshold=0.5,
            confirm_window=10,
            state_path=self.state_path,
            kill_switch=KillSwitch(),
            paper_mode=True,
        )
        cfg = mgr.get_config()
        self.assertEqual(cfg["sharpe_window"], 20)
        self.assertEqual(cfg["threshold"], 0.5)
        self.assertEqual(cfg["confirm_window"], 10)
        self.assertEqual(cfg["state_path"], self.state_path)
        self.assertTrue(cfg["paper_mode"])

    def test_get_active_strategies_initial(self):
        mgr = AutoDisableManager(
            state_path=self.state_path,
            kill_switch=KillSwitch(),
        )
        self.assertEqual(mgr.get_active_strategies(), [])

    def test_get_active_strategies(self):
        mgr = AutoDisableManager(
            sharpe_window=5, threshold=0.0,
            confirm_window=3, state_path=self.state_path,
            kill_switch=KillSwitch(),
        )
        good = pd.Series(np.random.default_rng(42).normal(0.01, 0.01, 10))
        mgr.update("good", good)
        self.assertIn("good", mgr.get_active_strategies())

    def test_get_disabled_strategies_empty(self):
        mgr = AutoDisableManager(
            state_path=self.state_path,
            kill_switch=KillSwitch(),
        )
        self.assertEqual(mgr.get_disabled_strategies(), [])


class TestAutoDisableManagerSharpeEdgeCases(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.state_path = os.path.join(self.tmpdir, "auto_disable_state.json")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_constant_returns_zero_sharpe_disables(self):
        mgr = AutoDisableManager(
            sharpe_window=5,
            threshold=0.001,
            confirm_window=3,
            state_path=self.state_path,
            kill_switch=KillSwitch(),
        )
        constant = pd.Series([1.0] * 10)
        active = mgr.update("strat_a", constant)
        self.assertFalse(active)

    def test_single_value_series(self):
        mgr = AutoDisableManager(
            sharpe_window=5,
            threshold=0.1,
            confirm_window=3,
            state_path=self.state_path,
        )
        single = pd.Series([1.0])
        active = mgr.update("strat_a", single)
        self.assertTrue(active)

    def test_all_nan_series_disables(self):
        mgr = AutoDisableManager(
            sharpe_window=5,
            threshold=0.001,
            confirm_window=3,
            state_path=self.state_path,
        )
        nan_series = pd.Series([np.nan] * 10)
        active = mgr.update("strat_a", nan_series)
        self.assertFalse(active)

    def test_exactly_window_length_series(self):
        mgr = AutoDisableManager(
            sharpe_window=5,
            threshold=0.0,
            confirm_window=3,
            state_path=self.state_path,
        )
        exact = pd.Series(np.random.default_rng(42).normal(-0.01, 0.01, 5))
        active = mgr.update("strat_a", exact)
        self.assertFalse(active)

    def test_sharpe_with_negative_mean_and_high_std(self):
        mgr = AutoDisableManager(
            sharpe_window=10,
            threshold=-1.0,
            confirm_window=3,
            state_path=self.state_path,
        )
        bad = pd.Series(np.random.default_rng(42).normal(-0.005, 0.02, 20))
        active = mgr.update("strat_a", bad)
        self.assertTrue(active)


class TestAutoDisableManagerSaveState(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.state_path = os.path.join(self.tmpdir, "auto_disable_state.json")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_state_creates_file(self):
        mgr = AutoDisableManager(
            sharpe_window=5,
            threshold=0.0,
            confirm_window=3,
            state_path=self.state_path,
            kill_switch=KillSwitch(),
        )
        bad = pd.Series(np.random.default_rng(42).normal(-0.01, 0.01, 10))
        mgr.update("strat_a", bad)
        self.assertTrue(os.path.exists(self.state_path))

    def test_save_state_valid_json(self):
        mgr = AutoDisableManager(
            sharpe_window=5,
            threshold=0.0,
            confirm_window=3,
            state_path=self.state_path,
            kill_switch=KillSwitch(),
        )
        bad = pd.Series(np.random.default_rng(42).normal(-0.01, 0.01, 10))
        mgr.update("strat_a", bad)
        with open(self.state_path) as f:
            data = json.load(f)
        self.assertIn("version", data)
        self.assertIn("config", data)
        self.assertIn("strategies", data)
        self.assertIn("strat_a", data["strategies"])
        self.assertTrue(data["strategies"]["strat_a"]["disabled"])

    def test_save_state_after_enable(self):
        mgr = AutoDisableManager(
            sharpe_window=5,
            threshold=0.0,
            confirm_window=1,
            state_path=self.state_path,
            kill_switch=KillSwitch(),
        )
        bad = pd.Series(np.random.default_rng(42).normal(-0.01, 0.01, 10))
        mgr.update("strat_a", bad)
        good = pd.Series(np.random.default_rng(99).normal(0.01, 0.01, 5))
        mgr.update("strat_a", good)
        with open(self.state_path) as f:
            data = json.load(f)
        self.assertFalse(data["strategies"]["strat_a"]["disabled"])


class TestAutoDisableManagerLoadState(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.state_path = os.path.join(self.tmpdir, "auto_disable_state.json")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_load_state_missing_file(self):
        mgr = AutoDisableManager(
            state_path=self.state_path,
            kill_switch=KillSwitch(),
        )
        self.assertEqual(len(mgr._strategies), 0)

    def test_load_state_corrupt_json(self):
        with open(self.state_path, "w") as f:
            f.write("not valid json")
        mgr = AutoDisableManager(
            state_path=self.state_path,
            kill_switch=KillSwitch(),
        )
        self.assertEqual(len(mgr._strategies), 0)

    def test_load_state_empty_json(self):
        with open(self.state_path, "w") as f:
            f.write("{}")
        mgr = AutoDisableManager(
            state_path=self.state_path,
            kill_switch=KillSwitch(),
        )
        self.assertEqual(len(mgr._strategies), 0)

    def test_load_state_populates_strategies(self):
        initial = AutoDisableManager(
            sharpe_window=5,
            threshold=0.0,
            confirm_window=3,
            state_path=self.state_path,
            kill_switch=KillSwitch(),
        )
        bad = pd.Series(np.random.default_rng(42).normal(-0.01, 0.01, 10))
        initial.update("strat_a", bad)

        loaded = AutoDisableManager(
            sharpe_window=5,
            threshold=0.0,
            confirm_window=3,
            state_path=self.state_path,
            kill_switch=KillSwitch(),
        )
        self.assertTrue(loaded.is_disabled("strat_a"))


class TestAutoDisableManagerReEnableFlow(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.state_path = os.path.join(self.tmpdir, "auto_disable_state.json")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_re_enable_after_confirm_window(self):
        mgr = AutoDisableManager(
            sharpe_window=5,
            threshold=-5.0,  # Always above threshold
            confirm_window=3,
            state_path=self.state_path,
            kill_switch=KillSwitch(),
        )
        mgr.disable("strat_a", "initial")
        for _ in range(5):
            good = pd.Series(np.random.default_rng(42).normal(0.01, 0.01, 10))
            mgr.update("strat_a", good)
        self.assertFalse(mgr.is_disabled("strat_a"))
        self.assertIn("strat_a", mgr.get_active_strategies())

    def test_disable_enable_then_disable_cycle(self):
        mgr = AutoDisableManager(
            sharpe_window=5,
            threshold=0.0,
            confirm_window=3,
            state_path=self.state_path,
            kill_switch=KillSwitch(),
        )
        self.assertTrue(mgr.disable("strat_a", "First disable"))
        self.assertTrue(mgr.is_disabled("strat_a"))

        self.assertTrue(mgr.enable("strat_a", "Re-enable"))
        self.assertFalse(mgr.is_disabled("strat_a"))

        self.assertTrue(mgr.disable("strat_a", "Second disable"))
        self.assertTrue(mgr.is_disabled("strat_a"))

    def test_disable_reason_tracked(self):
        mgr = AutoDisableManager(
            state_path=self.state_path,
            kill_switch=KillSwitch(),
        )
        mgr.disable("strat_a", "My custom reason")
        perf = mgr._strategies["strat_a"]
        self.assertEqual(perf.disabled_reason, "My custom reason")


class TestStrategyPerformanceEdgeCases(unittest.TestCase):
    def test_to_dict_disabled_state(self):
        perf = StrategyPerformance("test")
        perf.disabled = True
        perf.disabled_at = "2024-06-01T00:00:00"
        perf.disabled_reason = "low sharpe"
        perf.total_updates = 5
        d = perf.to_dict()
        self.assertTrue(d["disabled"])
        self.assertEqual(d["total_updates"], 5)

    def test_from_dict_with_missing_fields(self):
        d = {
            "name": "partial",
            "disabled": True,
        }
        perf = StrategyPerformance.from_dict(d)
        self.assertTrue(perf.disabled)
        self.assertEqual(perf.consecutive_above_threshold, 0)
        self.assertEqual(perf.total_updates, 0)
        self.assertEqual(perf.disabled_reason, "")

    def test_from_dict_full(self):
        d = {
            "name": "full",
            "disabled": True,
            "disabled_at": "2024-06-01T00:00:00",
            "disabled_reason": "reason",
            "consecutive_above_threshold": 5,
            "total_updates": 10,
        }
        perf = StrategyPerformance.from_dict(d)
        self.assertEqual(perf.consecutive_above_threshold, 5)
        self.assertEqual(perf.total_updates, 10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
