"""Tests: qna-toggle.py — strategy on/off toggle CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "scripts")

_spec = importlib.util.spec_from_file_location("qna_toggle", os.path.join(SCRIPTS_DIR, "qna-toggle.py"))
qna_toggle = importlib.util.module_from_spec(_spec)
sys.modules["qna_toggle"] = qna_toggle
_spec.loader.exec_module(qna_toggle)


class TestToggleCore(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.state_dir = self.tmpdir

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _config_path(self):
        return os.path.join(self.state_dir, "strategy_config.json")

    def test_list_enabled(self):
        statuses = qna_toggle.get_strategy_statuses(self.state_dir)
        names = [s["name"] for s in statuses]
        self.assertIn("regime_based", names)
        self.assertIn("mean_reversion", names)
        self.assertIn("trend_follow", names)
        for s in statuses:
            self.assertEqual(s["status"], "enabled")

    def test_enable_disable_round_trip(self):
        qna_toggle.disable_strategy(self.state_dir, "mean_reversion")
        config = qna_toggle.read_config(self.state_dir)
        self.assertIn("mean_reversion", config["disabled"])
        statuses = qna_toggle.get_strategy_statuses(self.state_dir)
        status_map = {s["name"]: s["status"] for s in statuses}
        self.assertEqual(status_map["mean_reversion"], "disabled")
        qna_toggle.enable_strategy(self.state_dir, "mean_reversion")
        config = qna_toggle.read_config(self.state_dir)
        self.assertNotIn("mean_reversion", config["disabled"])
        self.assertIn("mean_reversion", config["enabled"])
        statuses = qna_toggle.get_strategy_statuses(self.state_dir)
        status_map = {s["name"]: s["status"] for s in statuses}
        self.assertEqual(status_map["mean_reversion"], "enabled")

    def test_unknown_strategy_rejected(self):
        with self.assertRaises(ValueError):
            qna_toggle.enable_strategy(self.state_dir, "NonExistentStrategy")
        with self.assertRaises(ValueError):
            qna_toggle.disable_strategy(self.state_dir, "NonExistentStrategy")

    def test_cannot_disable_all_strategies(self):
        all_strats = qna_toggle.list_strategies()
        for s in all_strats[:-1]:
            qna_toggle.disable_strategy(self.state_dir, s)
        with self.assertRaises(ValueError):
            qna_toggle.disable_strategy(self.state_dir, all_strats[-1])

    def test_disable_already_disabled_is_noop(self):
        qna_toggle.disable_strategy(self.state_dir, "trend_follow")
        config_before = qna_toggle.read_config(self.state_dir)
        qna_toggle.disable_strategy(self.state_dir, "trend_follow")
        config_after = qna_toggle.read_config(self.state_dir)
        self.assertEqual(config_before["disabled"], config_after["disabled"])

    def test_enable_already_enabled_is_noop(self):
        qna_toggle.disable_strategy(self.state_dir, "trend_follow")
        qna_toggle.enable_strategy(self.state_dir, "trend_follow")
        config_before = qna_toggle.read_config(self.state_dir)
        qna_toggle.enable_strategy(self.state_dir, "trend_follow")
        config_after = qna_toggle.read_config(self.state_dir)
        self.assertEqual(config_before["disabled"], config_after["disabled"])

    def test_config_persists_to_disk(self):
        qna_toggle.disable_strategy(self.state_dir, "pairs_trading")
        self.assertTrue(os.path.exists(self._config_path()))
        with open(self._config_path()) as f:
            data = json.load(f)
        self.assertIn("pairs_trading", data["disabled"])
        self.assertIsNotNone(data.get("last_modified"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
