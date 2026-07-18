#!/usr/bin/env python3
"""Tests: KillSwitch — levels, activation, deactivation, reset,
check_auto_trigger, check_warning, callbacks, AutoDisableManager integration.

Run: python3 -m unittest tests/test_kill_switch.py -v
"""

from __future__ import annotations

import sys
import unittest
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from quant_nanggroe.engine.risk.kill_switch import (
    KillSwitch,
    KillSwitchLevel,
    KillSwitchTrigger,
    KillSwitchStatus,
    KillSwitchConfig,
    KillSwitchEvent,
    RESET_CONFIRMATION,
    EARLY_WARNING_THRESHOLD,
)


class TestKillSwitchInit(unittest.TestCase):
    """Tests for KillSwitch construction."""

    def test_default_config(self):
        ks = KillSwitch()
        self.assertEqual(ks._current_level, KillSwitchLevel.NONE)
        self.assertEqual(ks._status, KillSwitchStatus.INACTIVE)
        self.assertFalse(ks.is_active)
        self.assertEqual(len(ks._events), 0)

    def test_custom_config(self):
        cfg = KillSwitchConfig(auto_daily_loss_pct=0.02, cooldown_minutes=60)
        ks = KillSwitch(config=cfg)
        self.assertEqual(ks._config.auto_daily_loss_pct, 0.02)
        self.assertEqual(ks._config.cooldown_minutes, 60)

    def test_default_threshold_constants(self):
        self.assertEqual(EARLY_WARNING_THRESHOLD, 0.8)
        self.assertEqual(RESET_CONFIRMATION, "CONFIRM_RESET_AFTER_REVIEW")


class TestKillSwitchActivate(unittest.TestCase):
    """Tests for KillSwitch.activate()."""

    def setUp(self):
        self.ks = KillSwitch()

    def test_activate_level_1(self):
        event = self.ks.activate(KillSwitchLevel.LEVEL_1, reason="Test")
        self.assertEqual(event.level, KillSwitchLevel.LEVEL_1)
        self.assertTrue(self.ks.is_active)
        self.assertEqual(self.ks._current_level, KillSwitchLevel.LEVEL_1)
        self.assertEqual(self.ks._status, KillSwitchStatus.ACTIVE)

    def test_activate_level_2(self):
        event = self.ks.activate(KillSwitchLevel.LEVEL_2, reason="Drawdown")
        self.assertEqual(event.level, KillSwitchLevel.LEVEL_2)
        self.assertEqual(self.ks._current_level, KillSwitchLevel.LEVEL_2)

    def test_activate_level_3(self):
        event = self.ks.activate(KillSwitchLevel.LEVEL_3, reason="Crash")
        self.assertEqual(event.level, KillSwitchLevel.LEVEL_3)
        self.assertTrue(self.ks.is_active)

    def test_activate_none_level_warns(self):
        event = self.ks.activate(KillSwitchLevel.NONE)
        self.assertIsInstance(event, KillSwitchEvent)
        self.assertFalse(self.ks.is_active)

    def test_activate_with_string_as_reason(self):
        event = self.ks.activate("Manual override")
        self.assertEqual(event.level, KillSwitchLevel.LEVEL_1)
        self.assertEqual(event.reason, "Manual override")
        self.assertEqual(event.trigger, KillSwitchTrigger.MANUAL)

    def test_activate_with_auto_activated_flag(self):
        event = self.ks.activate(
            KillSwitchLevel.LEVEL_1, reason="Auto", trigger=KillSwitchTrigger.DAILY_LOSS_EXCEEDED, auto_activated=True,
        )
        self.assertTrue(event.auto_activated)
        self.assertEqual(event.trigger, KillSwitchTrigger.DAILY_LOSS_EXCEEDED)

    def test_activate_creates_event_in_list(self):
        self.ks.activate(KillSwitchLevel.LEVEL_2, reason="Test")
        self.assertEqual(len(self.ks._events), 1)
        event = self.ks._events[0]
        self.assertEqual(event.level, KillSwitchLevel.LEVEL_2)

    def test_activate_appends_multiple_events(self):
        self.ks.activate(KillSwitchLevel.LEVEL_1, reason="First")
        self.ks.deactivate()
        self.ks.activate(KillSwitchLevel.LEVEL_1, reason="Second")
        self.assertEqual(len(self.ks._events), 2)

    def test_activate_sets_previous_level(self):
        self.ks.activate(KillSwitchLevel.LEVEL_1, reason="First")
        event = self.ks.activate(KillSwitchLevel.LEVEL_2, reason="Second")
        self.assertEqual(event.previous_level, KillSwitchLevel.LEVEL_1)

    def test_activate_trigger_types(self):
        for trigger in KillSwitchTrigger:
            self.ks = KillSwitch()
            event = self.ks.activate(KillSwitchLevel.LEVEL_1, trigger=trigger)
            self.assertEqual(event.trigger, trigger)


class TestKillSwitchDeactivate(unittest.TestCase):
    """Tests for KillSwitch.deactivate()."""

    def setUp(self):
        self.ks = KillSwitch()

    def test_deactivate_not_active(self):
        result = self.ks.deactivate("test")
        self.assertIsNone(result)

    def test_deactivate_after_activation(self):
        self.ks.activate(KillSwitchLevel.LEVEL_1, reason="Test")
        self.ks._activated_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        result = self.ks.deactivate("Done")
        self.assertIsNotNone(result)
        self.assertEqual(result.level, KillSwitchLevel.NONE)
        self.assertEqual(result.reason, "Done")
        self.assertFalse(self.ks.is_active)

    def test_deactivate_marks_event_resolved(self):
        self.ks.activate(KillSwitchLevel.LEVEL_1, reason="Test")
        self.ks._activated_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        self.ks.deactivate("Done")
        self.assertTrue(self.ks._events[0].resolved)
        self.assertIsNotNone(self.ks._events[0].resolved_at)

    @patch("quant_nanggroe.engine.risk.kill_switch.datetime")
    def test_deactivate_cooldown_check(self, mock_dt):
        mock_dt.now.return_value = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        self.ks.activate(KillSwitchLevel.LEVEL_1, reason="Test")
        # Time hasn't advanced — cooldown not elapsed
        result = self.ks.deactivate("Too soon")
        self.assertIsNone(result)

    def test_deactivate_cooldown_elapsed(self):
        self.ks.activate(KillSwitchLevel.LEVEL_1, reason="Test")
        # Simulate time passing by setting _activated_at far back
        self.ks._activated_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        result = self.ks.deactivate("Finally")
        self.assertIsNotNone(result)
        self.assertFalse(self.ks.is_active)

    def test_deactivate_resets_to_none(self):
        self.ks.activate(KillSwitchLevel.LEVEL_2, reason="Test")
        self.ks._activated_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        self.ks.deactivate("Done")
        self.assertEqual(self.ks._current_level, KillSwitchLevel.NONE)

    def test_deactivate_level_3_cooldown_longer(self):
        cfg = KillSwitchConfig(level_2_cooldown_minutes=60, cooldown_minutes=30)
        self.ks = KillSwitch(config=cfg)
        self.ks.activate(KillSwitchLevel.LEVEL_3, reason="Crash")
        self.ks._activated_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        self.ks.approve_level3_deactivation()
        result = self.ks.deactivate("Approved")
        self.assertIsNotNone(result)


class TestKillSwitchReset(unittest.TestCase):
    """Tests for KillSwitch.reset()."""

    def setUp(self):
        self.ks = KillSwitch()

    def test_reset_not_active(self):
        result = self.ks.reset()
        self.assertEqual(result["status"], "NOT_ACTIVE")

    def test_reset_with_wrong_confirmation(self):
        self.ks.activate(KillSwitchLevel.LEVEL_2, reason="Test")
        result = self.ks.reset("wrong")
        self.assertEqual(result["status"], "STILL_ACTIVE")
        self.assertTrue(self.ks.is_active)

    def test_reset_with_correct_confirmation(self):
        self.ks.activate(KillSwitchLevel.LEVEL_2, reason="Emergency")
        result = self.ks.reset(RESET_CONFIRMATION)
        self.assertEqual(result["status"], "RESET")
        self.assertFalse(self.ks.is_active)
        self.assertEqual(self.ks._current_level, KillSwitchLevel.NONE)

    def test_reset_marks_event_resolved(self):
        self.ks.activate(KillSwitchLevel.LEVEL_2, reason="Test")
        self.ks.reset(RESET_CONFIRMATION)
        self.assertTrue(self.ks._events[0].resolved)
        self.assertIsNotNone(self.ks._events[0].resolved_at)

    def test_reset_clears_activated_at(self):
        self.ks.activate(KillSwitchLevel.LEVEL_1, reason="Test")
        self.ks.reset(RESET_CONFIRMATION)
        self.assertIsNone(self.ks._activated_at)


class TestKillSwitchCheckAutoTrigger(unittest.TestCase):
    """Tests for check_auto_trigger() and check_auto_activate()."""

    def setUp(self):
        self.ks = KillSwitch()

    def test_check_auto_trigger_daily_loss(self):
        result = self.ks.check_auto_trigger(daily_loss_pct=0.02)
        self.assertIsNotNone(result)
        self.assertTrue(result["is_active"])

    def test_check_auto_trigger_daily_loss_below(self):
        result = self.ks.check_auto_trigger(daily_loss_pct=0.001)
        self.assertIsNone(result)

    def test_check_auto_trigger_weekly_loss(self):
        result = self.ks.check_auto_trigger(weekly_loss_pct=0.05)
        self.assertIsNotNone(result)
        self.assertTrue(result["is_active"])

    def test_check_auto_trigger_drawdown(self):
        result = self.ks.check_auto_trigger(drawdown_pct=0.06)
        self.assertIsNotNone(result)

    def test_check_auto_trigger_volatility(self):
        result = self.ks.check_auto_trigger(volatility_pct=0.12)
        self.assertIsNotNone(result)

    def test_check_auto_trigger_none_when_inactive(self):
        result = self.ks.check_auto_trigger(daily_loss_pct=0.001, weekly_loss_pct=0.001, drawdown_pct=0.001, volatility_pct=0.001)
        self.assertIsNone(result)

    def test_check_auto_trigger_does_not_fire_if_already_active(self):
        self.ks.activate(KillSwitchLevel.LEVEL_1, reason="Manual")
        result = self.ks.check_auto_trigger(daily_loss_pct=0.1)
        self.assertIsNone(result)

    def test_auto_activate_returns_event(self):
        event = self.ks.check_auto_activate(daily_pnl_pct=-0.02)
        self.assertIsNotNone(event)
        self.assertTrue(event.auto_activated)
        self.assertEqual(event.trigger, KillSwitchTrigger.DAILY_LOSS_EXCEEDED)

    def test_check_auto_activate_no_trigger(self):
        event = self.ks.check_auto_activate(daily_pnl_pct=-0.001)
        self.assertIsNone(event)

    def test_auto_activate_priority_order(self):
        # Weekly loss should trigger level_2 before daily loss
        event = self.ks.check_auto_activate(
            daily_pnl_pct=-0.02, weekly_pnl_pct=-0.05,
        )
        self.assertEqual(event.level, KillSwitchLevel.LEVEL_1)  # Daily checked first

    def test_auto_activate_volatility(self):
        event = self.ks.check_auto_activate(volatility_pct=0.11)
        self.assertEqual(event.level, KillSwitchLevel.LEVEL_1)
        self.assertEqual(event.trigger, KillSwitchTrigger.VOLATILITY_SPIKE)

    def test_auto_activate_drawdown_exceeded(self):
        event = self.ks.check_auto_activate(max_drawdown_pct=0.06)
        self.assertEqual(event.level, KillSwitchLevel.LEVEL_2)
        self.assertEqual(event.trigger, KillSwitchTrigger.DRAWDOWN_EXCEEDED)


class TestKillSwitchCheckWarning(unittest.TestCase):
    """Tests for check_warning()."""

    def setUp(self):
        self.ks = KillSwitch()

    def test_warning_daily_loss_approaching(self):
        threshold = KillSwitchConfig().auto_daily_loss_pct * EARLY_WARNING_THRESHOLD
        self.assertTrue(self.ks.check_warning(daily_pnl_pct=-threshold - 0.001))

    def test_warning_daily_loss_not_approaching(self):
        self.assertFalse(self.ks.check_warning(daily_pnl_pct=-0.001))

    def test_warning_weekly_loss_approaching(self):
        threshold = KillSwitchConfig().auto_weekly_loss_pct * EARLY_WARNING_THRESHOLD
        self.assertTrue(self.ks.check_warning(weekly_pnl_pct=-threshold - 0.001))

    def test_warning_drawdown_approaching(self):
        threshold = KillSwitchConfig().auto_max_drawdown_pct * EARLY_WARNING_THRESHOLD
        self.assertTrue(self.ks.check_warning(max_drawdown_pct=threshold + 0.001))

    def test_warning_volatility_approaching(self):
        threshold = KillSwitchConfig().auto_volatility_spike_pct * EARLY_WARNING_THRESHOLD
        self.assertTrue(self.ks.check_warning(volatility_pct=threshold + 0.001))

    def test_warning_false_when_all_below(self):
        self.assertFalse(self.ks.check_warning(daily_pnl_pct=-0.001))

    def test_warning_does_not_activate(self):
        self.ks.check_warning(daily_pnl_pct=-0.1)
        self.assertFalse(self.ks.is_active)


class TestKillSwitchQueryMethods(unittest.TestCase):
    """Tests for can_trade, can_hold_positions, status()."""

    def setUp(self):
        self.ks = KillSwitch()

    def test_can_trade_when_inactive(self):
        self.assertTrue(self.ks.can_trade())

    def test_can_trade_when_active(self):
        self.ks.activate(KillSwitchLevel.LEVEL_1, reason="Test")
        self.assertFalse(self.ks.can_trade())

    def test_can_hold_positions_level_1(self):
        self.ks.activate(KillSwitchLevel.LEVEL_1, reason="Test")
        self.assertTrue(self.ks.can_hold_positions())

    def test_can_hold_positions_level_2(self):
        self.ks.activate(KillSwitchLevel.LEVEL_2, reason="Test")
        self.assertTrue(self.ks.can_hold_positions())

    def test_can_hold_positions_level_3(self):
        self.ks.activate(KillSwitchLevel.LEVEL_3, reason="Crash")
        self.assertFalse(self.ks.can_hold_positions())

    def test_status_returns_dict(self):
        self.ks.activate(KillSwitchLevel.LEVEL_2, reason="Drawdown", trigger=KillSwitchTrigger.DRAWDOWN_EXCEEDED)
        st = self.ks.status()
        self.assertTrue(st["is_active"])
        self.assertEqual(st["current_level"], "level_2")
        self.assertEqual(st["status"], "active")
        self.assertIn("activation_reason", st)
        self.assertIn("total_activations", st)
        self.assertIn("auto_triggers", st)
        self.assertIn("manual_triggers", st)

    def test_status_empty_before_activation(self):
        st = self.ks.status()
        self.assertFalse(st["is_active"])
        self.assertEqual(st["current_level"], "none")
        self.assertEqual(st["total_activations"], 0)
        self.assertIsNone(st["activated_at"])

    def test_current_level_property(self):
        self.ks.activate(KillSwitchLevel.LEVEL_2, reason="Test")
        self.assertEqual(self.ks.current_level, KillSwitchLevel.LEVEL_2)

    def test_events_property(self):
        self.ks.activate(KillSwitchLevel.LEVEL_1, reason="Test")
        self.assertEqual(len(self.ks.events), 1)

    def test_config_property(self):
        cfg = self.ks.config
        self.assertIsInstance(cfg, KillSwitchConfig)


class TestKillSwitchCallbacks(unittest.TestCase):
    """Tests for on_activate callback registration and execution."""

    def setUp(self):
        self.ks = KillSwitch()

    def test_callback_invoked_on_activation(self):
        cb = MagicMock()
        self.ks.on_activate(KillSwitchLevel.LEVEL_1, cb)
        self.ks.activate(KillSwitchLevel.LEVEL_1, reason="Test")
        cb.assert_called_once()

    def test_callback_not_invoked_for_different_level(self):
        cb = MagicMock()
        self.ks.on_activate(KillSwitchLevel.LEVEL_2, cb)
        self.ks.activate(KillSwitchLevel.LEVEL_1, reason="Test")
        cb.assert_not_called()

    def test_callback_receives_event(self):
        cb = MagicMock()
        self.ks.on_activate(KillSwitchLevel.LEVEL_1, cb)
        self.ks.activate(KillSwitchLevel.LEVEL_1, reason="Test")
        event_arg = cb.call_args[0][0]
        self.assertIsInstance(event_arg, KillSwitchEvent)
        self.assertEqual(event_arg.reason, "Test")

    def test_multiple_callbacks(self):
        cb1 = MagicMock()
        cb2 = MagicMock()
        self.ks.on_activate(KillSwitchLevel.LEVEL_1, cb1)
        self.ks.on_activate(KillSwitchLevel.LEVEL_1, cb2)
        self.ks.activate(KillSwitchLevel.LEVEL_1, reason="Test")
        cb1.assert_called_once()
        cb2.assert_called_once()

    def test_callback_error_does_not_raise(self):
        def failing_cb(event):
            raise ValueError("fail")
        self.ks.on_activate(KillSwitchLevel.LEVEL_1, failing_cb)
        self.ks.activate(KillSwitchLevel.LEVEL_1, reason="Test")

    def test_stats_property(self):
        self.ks.activate(KillSwitchLevel.LEVEL_1, reason="Test")
        stats = self.ks.stats
        self.assertIn("current_level", stats)
        self.assertIn("is_active", stats)
        self.assertIn("can_trade", stats)
        self.assertIn("total_events", stats)
        self.assertIn("auto_activations", stats)
        self.assertIn("manual_activations", stats)

    def test_stats_can_trade_false_when_active(self):
        self.ks.activate(KillSwitchLevel.LEVEL_1, reason="Test")
        self.assertFalse(self.ks.stats["can_trade"])


class TestKillSwitchConfig(unittest.TestCase):
    """Tests for KillSwitchConfig dataclass."""

    def test_default_values(self):
        cfg = KillSwitchConfig()
        self.assertEqual(cfg.auto_daily_loss_pct, 0.015)
        self.assertEqual(cfg.auto_weekly_loss_pct, 0.04)
        self.assertEqual(cfg.auto_max_drawdown_pct, 0.05)
        self.assertEqual(cfg.auto_volatility_spike_pct, 0.10)
        self.assertEqual(cfg.cooldown_minutes, 30)
        self.assertEqual(cfg.level_2_cooldown_minutes, 60)
        self.assertTrue(cfg.level_3_requires_approval)
        self.assertTrue(cfg.notify_on_activation)
        self.assertEqual(cfg.notification_channels, ["log", "api"])

    def test_custom_values(self):
        cfg = KillSwitchConfig(
            auto_daily_loss_pct=0.03,
            auto_weekly_loss_pct=0.06,
            cooldown_minutes=15,
        )
        self.assertEqual(cfg.auto_daily_loss_pct, 0.03)
        self.assertEqual(cfg.auto_weekly_loss_pct, 0.06)
        self.assertEqual(cfg.cooldown_minutes, 15)


class TestKillSwitchEvent(unittest.TestCase):
    """Tests for KillSwitchEvent dataclass."""

    def test_default_values(self):
        event = KillSwitchEvent()
        self.assertEqual(event.level, KillSwitchLevel.NONE)
        self.assertEqual(event.trigger, KillSwitchTrigger.MANUAL)
        self.assertFalse(event.auto_activated)
        self.assertFalse(event.resolved)
        self.assertIsNone(event.resolved_at)
        self.assertIsNotNone(event.event_id)

    def test_custom_event(self):
        event = KillSwitchEvent(
            level=KillSwitchLevel.LEVEL_2,
            trigger=KillSwitchTrigger.DRAWDOWN_EXCEEDED,
            reason="DD breach",
            auto_activated=True,
        )
        self.assertEqual(event.level, KillSwitchLevel.LEVEL_2)
        self.assertEqual(event.trigger, KillSwitchTrigger.DRAWDOWN_EXCEEDED)
        self.assertEqual(event.reason, "DD breach")
        self.assertTrue(event.auto_activated)

    def test_resolve(self):
        event = KillSwitchEvent()
        event.resolved = True
        event.resolved_at = datetime.now(timezone.utc)
        self.assertTrue(event.resolved)
        self.assertIsNotNone(event.resolved_at)


if __name__ == "__main__":
    unittest.main(verbosity=2)
