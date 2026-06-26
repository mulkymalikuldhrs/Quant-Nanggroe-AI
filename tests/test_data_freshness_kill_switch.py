#!/usr/bin/env python3
"""Tests: data freshness monitor → kill switch bridge.

Run: python3 tests/test_data_freshness_kill_switch.py [--verbose]
"""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone, timedelta

# ── Mock pandas before any quant_nanggroe import ──────────────────────
# data_manager.py eagerly imports pandas; we bypass it by direct import.
import unittest.mock as mock
sys.modules["pandas"] = mock.MagicMock()
sys.modules["pandas"].DataFrame = mock.MagicMock
sys.modules["pandas"].Series = mock.MagicMock

from quant_nanggroe.data.monitor import (
    DataFreshnessMonitor,
    STALE_LEVEL_1_MINUTES,
    STALE_LEVEL_2_MINUTES,
    STALE_LEVEL_3_MINUTES,
)
from quant_nanggroe.engine.risk.kill_switch import (
    KillSwitch,
    KillSwitchLevel,
    KillSwitchTrigger,
)
from quant_nanggroe.types.market import TimeFrame


def _seed_old_data(monitor: DataFreshnessMonitor, age_minutes: float) -> None:
    old = datetime.now(timezone.utc) - timedelta(minutes=age_minutes)
    monitor._last_fetch["BTC/USDT"]["1h"] = old


class TestDataFreshnessKillSwitch(unittest.TestCase):
    """Verify the monitor → kill-switch chain at each level."""

    def test_fresh_data_no_trigger(self):
        ks = KillSwitch()
        mon = DataFreshnessMonitor(kill_switch=ks)
        mon.record_fetch("BTC/USDT", TimeFrame.H1)
        result = mon.check_and_trigger_kill_switch()
        self.assertIsNone(result)
        self.assertEqual(ks.current_level, KillSwitchLevel.NONE)

    def test_level_1_triggered(self):
        ks = KillSwitch()
        mon = DataFreshnessMonitor(kill_switch=ks)
        _seed_old_data(mon, STALE_LEVEL_1_MINUTES + 1)
        result = mon.check_and_trigger_kill_switch()
        self.assertEqual(result, KillSwitchLevel.LEVEL_1.value)
        self.assertEqual(ks.current_level, KillSwitchLevel.LEVEL_1)

    def test_level_2_triggered(self):
        ks = KillSwitch()
        mon = DataFreshnessMonitor(kill_switch=ks)
        _seed_old_data(mon, STALE_LEVEL_2_MINUTES + 1)
        result = mon.check_and_trigger_kill_switch()
        self.assertEqual(result, KillSwitchLevel.LEVEL_2.value)
        self.assertEqual(ks.current_level, KillSwitchLevel.LEVEL_2)

    def test_level_3_triggered(self):
        ks = KillSwitch()
        mon = DataFreshnessMonitor(kill_switch=ks)
        _seed_old_data(mon, STALE_LEVEL_3_MINUTES + 1)
        result = mon.check_and_trigger_kill_switch()
        self.assertEqual(result, KillSwitchLevel.LEVEL_3.value)
        self.assertEqual(ks.current_level, KillSwitchLevel.LEVEL_3)

    def test_no_kill_switch_bound(self):
        mon = DataFreshnessMonitor()
        _seed_old_data(mon, 61)
        result = mon.check_and_trigger_kill_switch()
        self.assertIsNone(result)

    def test_trigger_reason_contains_age(self):
        ks = KillSwitch()
        mon = DataFreshnessMonitor(kill_switch=ks)
        _seed_old_data(mon, 10)
        mon.check_and_trigger_kill_switch()
        self.assertEqual(len(ks.events), 1)
        self.assertIn("stale", ks.events[0].reason.lower())

    def test_trigger_is_auto_activated(self):
        ks = KillSwitch()
        mon = DataFreshnessMonitor(kill_switch=ks)
        _seed_old_data(mon, 10)
        mon.check_and_trigger_kill_switch()
        self.assertTrue(ks.events[0].auto_activated)
        self.assertEqual(ks.events[0].trigger, KillSwitchTrigger.DATA_STALE)

    def test_set_kill_switch_late_binding(self):
        ks = KillSwitch()
        mon = DataFreshnessMonitor()
        mon.set_kill_switch(ks)
        _seed_old_data(mon, 10)
        result = mon.check_and_trigger_kill_switch()
        self.assertEqual(result, KillSwitchLevel.LEVEL_1.value)
        self.assertEqual(ks.current_level, KillSwitchLevel.LEVEL_1)

    def test_escalation_highest_level_wins(self):
        ks = KillSwitch()
        mon = DataFreshnessMonitor(kill_switch=ks)
        mon.record_fetch("ETH/USDT", TimeFrame.H1)
        _seed_old_data(mon, 61)
        result = mon.check_and_trigger_kill_switch()
        self.assertEqual(result, KillSwitchLevel.LEVEL_3.value)

    def test_logger_warning_on_trigger(self):
        import logging
        ks = KillSwitch()
        mon = DataFreshnessMonitor(kill_switch=ks)
        _seed_old_data(mon, 10)
        with self.assertLogs(level="WARNING") as ctx:
            mon.check_and_trigger_kill_switch()
        self.assertTrue(any("level_1" in msg for msg in ctx.output))


if __name__ == "__main__":
    unittest.main(verbosity=2 if "--verbose" in sys.argv else 1)
