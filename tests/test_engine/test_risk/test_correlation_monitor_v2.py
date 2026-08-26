"""Tests: CorrelationMonitor — additional edge cases, paper mode, persistence, stress.

Run: python3 -m unittest tests/test_risk/test_correlation_monitor_v2.py -v
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import numpy as np
import pandas as pd

from quant_nanggroe.engine.risk.correlation import (
    CorrelationMonitor,
    StrategyCorrelationMonitor,
    CorrelationAlert,
)
from quant_nanggroe.engine.risk.kill_switch import KillSwitch


class TestCorrelationAlert(unittest.TestCase):
    def test_default_construction(self):
        alert = CorrelationAlert(
            pair="A-B",
            current_correlation=0.9,
            historical_avg=0.5,
            z_score=3.0,
            alert_type="high_correlation",
        )
        self.assertEqual(alert.pair, "A-B")
        self.assertEqual(alert.current_correlation, 0.9)
        self.assertEqual(alert.alert_type, "high_correlation")

    def test_stress_alert_type(self):
        alert = CorrelationAlert(
            pair="C-D",
            current_correlation=0.95,
            historical_avg=0.6,
            z_score=4.0,
            alert_type="stress",
        )
        self.assertEqual(alert.alert_type, "stress")


class TestCorrelationMonitorEdgeCases(unittest.TestCase):
    def test_empty_dataframe_rolling_corr(self):
        mon = CorrelationMonitor(lookback=30)
        df = pd.DataFrame()
        corr = mon.compute_rolling_correlation(df)
        self.assertTrue(corr.empty)

    def test_single_column_rolling_corr(self):
        mon = CorrelationMonitor(lookback=30)
        df = pd.DataFrame({"A": np.random.randn(50)})
        corr = mon.compute_rolling_correlation(df)
        self.assertEqual(corr.shape, (1, 1))

    def test_custom_window_smaller_than_data(self):
        mon = CorrelationMonitor(lookback=30)
        df = pd.DataFrame({"A": np.random.randn(10), "B": np.random.randn(10)})
        corr = mon.compute_rolling_correlation(df, window=5)
        self.assertIsInstance(corr, pd.DataFrame)

    def test_diversification_score_two_assets(self):
        mon = CorrelationMonitor()
        df = pd.DataFrame({
            "A": np.random.randn(100),
            "B": np.random.randn(100),
        })
        score = mon.compute_diversification_score(df)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_diversification_score_custom_weights(self):
        mon = CorrelationMonitor()
        df = pd.DataFrame({
            "A": np.random.randn(100),
            "B": np.random.randn(100),
            "C": np.random.randn(100),
        })
        weights = np.array([0.5, 0.3, 0.2])
        score = mon.compute_diversification_score(df, weights=weights)
        self.assertGreaterEqual(score, 0.0)

    def test_diversification_score_zero_vol(self):
        mon = CorrelationMonitor()
        df = pd.DataFrame({
            "A": [1.0] * 50,
            "B": [2.0] * 50,
        })
        score = mon.compute_diversification_score(df)
        self.assertEqual(score, 0.0)

    def test_detect_stress_single_asset(self):
        mon = CorrelationMonitor()
        df = pd.DataFrame({"A": np.random.randn(50)})
        result = mon.detect_stress(df)
        self.assertFalse(result["stress_detected"])
        self.assertEqual(result["avg_correlation"], 0.0)
        self.assertEqual(result["stress_level"], "NORMAL")

    def test_detect_stress_two_identical_series(self):
        mon = CorrelationMonitor(stress_threshold=0.5, high_correlation_threshold=0.3)
        base = np.random.randn(100)
        df = pd.DataFrame({"A": base, "B": base.copy()})
        result = mon.detect_stress(df)
        self.assertTrue(result["stress_detected"])
        self.assertEqual(result["stress_level"], "STRESS")

    def test_detect_stress_two_assets_uncorrelated(self):
        mon = CorrelationMonitor(stress_threshold=0.9)
        rng = np.random.default_rng(42)
        df = pd.DataFrame({
            "A": rng.normal(0, 1, 200),
            "B": rng.normal(0, 1, 200),
        })
        result = mon.detect_stress(df)
        self.assertFalse(result["stress_detected"])

    def test_is_correlated_case_insensitive(self):
        mon = CorrelationMonitor()
        self.assertTrue(mon.is_correlated("eurusd", "gbpusd"))
        self.assertTrue(mon.is_correlated("EURUSD", "GBPUSD"))
        self.assertTrue(mon.is_correlated("xauusd", "xagusd"))

    def test_is_correlated_unmatched_groups(self):
        mon = CorrelationMonitor()
        self.assertFalse(mon.is_correlated("SPY", "BTCUSDT"))

    def test_count_correlated_no_matches(self):
        mon = CorrelationMonitor()
        count = mon.count_correlated_positions("BTCUSDT", ["SPY", "QQQ"])
        self.assertEqual(count, 0)

    def test_count_correlated_all_matches(self):
        mon = CorrelationMonitor()
        count = mon.count_correlated_positions("ETHUSDT", ["BTCUSDT"])
        self.assertEqual(count, 1)


class TestCorrelationMonitorHistory(unittest.TestCase):
    def test_history_starts_empty(self):
        mon = CorrelationMonitor()
        self.assertEqual(len(mon._history), 0)


class TestStrategyCorrelationMonitorPaperMode(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_paper_mode_suppresses_kill_switch(self):
        ks = KillSwitch()
        mon = StrategyCorrelationMonitor(
            kill_switch=ks,
            window=10,
            threshold=0.5,
            state_dir=self.tmpdir,
            paper_mode=True,
        )
        returns = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        mon.update("strat_a", returns)
        mon.update("strat_b", returns)
        mon.check_and_act()
        self.assertFalse(ks.is_active)

    def test_paper_mode_still_checks_correlation(self):
        mon = StrategyCorrelationMonitor(
            kill_switch=None,
            window=10,
            threshold=0.5,
            state_dir=self.tmpdir,
            paper_mode=True,
        )
        returns = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        mon.update("strat_a", returns)
        mon.update("strat_b", returns)
        status = mon.check_and_act()
        self.assertGreater(status["avg_correlation"], 0.5)


class TestStrategyCorrelationMonitorPersistence(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_state_creates_file(self):
        state_path = Path(self.tmpdir) / "correlation_state.json"
        mon = StrategyCorrelationMonitor(
            kill_switch=KillSwitch(),
            window=10,
            threshold=0.5,
            state_dir=self.tmpdir,
        )
        returns = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        mon.update("a", returns)
        mon.update("b", returns)
        mon.check_and_act()
        self.assertTrue(state_path.exists())

    def test_save_state_valid_json(self):
        state_path = Path(self.tmpdir) / "correlation_state.json"
        mon = StrategyCorrelationMonitor(
            kill_switch=KillSwitch(),
            window=10,
            threshold=0.5,
            state_dir=self.tmpdir,
        )
        returns = np.array([1.0, 2.0, 3.0])
        mon.update("a", returns)
        mon.update("b", returns)
        mon.check_and_act()
        with open(state_path) as f:
            data = json.load(f)
        self.assertIn("trailing_returns", data)
        self.assertIn("kill_switch_fired", data)
        self.assertIn("a", data["trailing_returns"])

    def test_load_state_corrupt_json(self):
        state_path = Path(self.tmpdir) / "correlation_state.json"
        with open(state_path, "w") as f:
            f.write("corrupt json")
        mon = StrategyCorrelationMonitor(
            kill_switch=KillSwitch(),
            window=10,
            threshold=0.5,
            state_dir=self.tmpdir,
        )
        self.assertEqual(len(mon._trailing_returns), 0)
        self.assertFalse(mon._fired)

    def test_load_state_empty_json(self):
        state_path = Path(self.tmpdir) / "correlation_state.json"
        with open(state_path, "w") as f:
            f.write("{}")
        mon = StrategyCorrelationMonitor(
            kill_switch=KillSwitch(),
            window=10,
            threshold=0.5,
            state_dir=self.tmpdir,
        )
        self.assertEqual(len(mon._trailing_returns), 0)

    def test_load_state_populates_returns(self):
        initial = StrategyCorrelationMonitor(
            kill_switch=KillSwitch(),
            window=20,
            threshold=0.5,
            state_dir=self.tmpdir,
        )
        rng = np.random.default_rng(42)
        initial.update("a", rng.normal(0.001, 0.01, 10))
        initial.update("b", rng.normal(0.002, 0.01, 10))
        initial.check_and_act()

        loaded = StrategyCorrelationMonitor(
            kill_switch=KillSwitch(),
            window=20,
            threshold=0.5,
            state_dir=self.tmpdir,
        )
        self.assertIn("a", loaded._trailing_returns)
        self.assertIn("b", loaded._trailing_returns)
        self.assertEqual(len(loaded._trailing_returns["a"]), 10)


class TestStrategyCorrelationMonitorEdgeCases(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_single_strategy_get_status(self):
        mon = StrategyCorrelationMonitor(
            kill_switch=None,
            window=10,
            threshold=0.85,
            state_dir=self.tmpdir,
        )
        mon.update("only_one", np.array([1.0, 2.0, 3.0]))
        status = mon.get_status()
        self.assertEqual(status["num_strategies"], 1)
        self.assertIsNone(status["avg_correlation"])

    def test_update_overwrites_fifo(self):
        mon = StrategyCorrelationMonitor(
            kill_switch=None,
            window=3,
            threshold=0.85,
            state_dir=self.tmpdir,
        )
        mon.update("a", np.array([1.0, 2.0, 3.0, 4.0, 5.0]))
        self.assertEqual(len(mon._trailing_returns["a"]), 3)

    def test_fired_flag_persisted_across_instances(self):
        mon1 = StrategyCorrelationMonitor(
            kill_switch=KillSwitch(),
            window=10,
            threshold=0.5,
            state_dir=self.tmpdir,
        )
        returns = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        mon1.update("a", returns)
        mon1.update("b", returns)
        mon1.check_and_act()
        self.assertTrue(mon1._fired)

        mon2 = StrategyCorrelationMonitor(
            kill_switch=KillSwitch(),
            window=10,
            threshold=0.5,
            state_dir=self.tmpdir,
        )
        self.assertEqual(mon2._fired, mon1._fired)

    def test_update_with_scalar(self):
        mon = StrategyCorrelationMonitor(
            kill_switch=None,
            window=10,
            threshold=0.85,
            state_dir=self.tmpdir,
        )
        mon.update("a", np.array(1.0))
        self.assertEqual(len(mon._trailing_returns["a"]), 1)

    def test_no_kill_switch_herding_logs_warning(self):
        mon = StrategyCorrelationMonitor(
            kill_switch=None,
            window=10,
            threshold=0.0,
            state_dir=self.tmpdir,
        )
        returns = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        mon.update("a", returns)
        mon.update("b", returns)
        status = mon.check_and_act()
        self.assertIsNotNone(status["avg_correlation"])

    def test_three_strategies_pairwise_corr(self):
        mon = StrategyCorrelationMonitor(
            kill_switch=None,
            window=10,
            threshold=0.85,
            state_dir=self.tmpdir,
        )
        rng = np.random.default_rng(42)
        mon.update("a", rng.normal(0, 1, 10))
        mon.update("b", rng.normal(0, 1, 10))
        mon.update("c", rng.normal(0, 1, 10))
        corr = mon.compute_correlations()
        self.assertIn("a", corr)
        self.assertIn("b", corr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
