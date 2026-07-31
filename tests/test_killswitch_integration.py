#!/usr/bin/env python3
"""Integration tests: kill-switch wiring between RiskLimits and KillSwitch.

BLOCKER 3e — verifies the two safety gates that must stop trading when
loss limits are breached:

1. ``RiskLimits.can_trade()`` blocks once the weekly loss exceeds the
   configured limit (the RiskLimits weekly-loss gate).
2. ``KillSwitch.check_auto_activate()`` trips automatically when a risk
   metric breaches its threshold (the emergency kill switch gate).

These are "integration" tests in the sense that they exercise the real
public API of both classes (including persistence + cross-process file
reconcile paths) rather than mocking the internals.

Run:
    PYTHONPATH= pytest tests/test_killswitch_integration.py -v
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture
def isolated_kill_switch_file(tmp_path, monkeypatch):
    """Point every KillSwitch() in this test at a fresh, isolated state file.

    Prevents cross-test state leakage through the shared cross-process file
    (the QNA_KILL_SWITCH_STATE_FILE env var that conftest.py seeds at import).
    """
    ks_file = tmp_path / "kill_switch_state.json"
    monkeypatch.setenv("QNA_KILL_SWITCH_STATE_FILE", str(ks_file))
    return ks_file


def test_risklimits_blocks_trading_when_weekly_loss_exceeds_limit(tmp_path):
    """RiskLimits.can_trade() must return False once weekly loss > limit."""
    from quant_nanggroe.engine.risk.limits import RiskLimits

    # Tight 2% weekly loss limit, isolated JSON state in tmp_path.
    limits = RiskLimits(max_weekly_loss_pct=0.02, state_dir=tmp_path)
    assert limits.can_trade() is True  # no loss yet -> allowed

    # Record a 5% weekly loss -> exceeds the 2% limit.
    limits.record_trade(pnl=-0.05)
    assert limits.current_weekly_loss_pct() == pytest.approx(0.05)
    # The gate must now block all new trades.
    assert limits.can_trade() is False

    # A winning trade that still leaves us net-down past the limit keeps blocking.
    limits.record_trade(pnl=0.01)  # net -0.04
    assert limits.can_trade() is False

    # Fully recovering above the limit re-opens trading.
    limits.record_trade(pnl=0.10)  # net +0.06
    assert limits.can_trade() is True


def test_killswitch_check_auto_activate_trips_on_weekly_loss(isolated_kill_switch_file):
    """KillSwitch.check_auto_activate() must trip when weekly loss > threshold."""
    from quant_nanggroe.engine.risk.kill_switch import (
        KillSwitch,
        KillSwitchLevel,
        KillSwitchTrigger,
    )

    ks = KillSwitch()
    assert ks.is_active is False
    assert ks.can_trade() is True

    # Weekly loss of -3% breaches the default -2.5% weekly kill-switch limit.
    event = ks.check_auto_activate(
        daily_pnl_pct=-0.001,
        weekly_pnl_pct=-0.03,
        max_drawdown_pct=0.01,
        volatility_pct=0.02,
    )

    # An activation event must be returned and flagged as auto-triggered.
    assert event is not None
    assert event.auto_activated is True
    assert event.trigger == KillSwitchTrigger.WEEKLY_LOSS_EXCEEDED
    assert event.level == KillSwitchLevel.LEVEL_2

    # The switch is now active and trading is blocked.
    assert ks.is_active is True
    assert ks.can_trade() is False


def test_killswitch_check_auto_activate_does_not_trip_within_limits(isolated_kill_switch_file):
    """Sanity check: no breach -> no trip (gate is not fail-open)."""
    from quant_nanggroe.engine.risk.kill_switch import KillSwitch

    ks = KillSwitch()
    event = ks.check_auto_activate(
        daily_pnl_pct=-0.001,
        weekly_pnl_pct=-0.01,   # within the -2.5% weekly limit
        max_drawdown_pct=0.01,   # within the 5% drawdown limit
        volatility_pct=0.02,     # within the 10% volatility limit
    )
    assert event is None
    assert ks.is_active is False
    assert ks.can_trade() is True


def test_killswitch_check_auto_activate_fail_closed_on_missing_metric(isolated_kill_switch_file):
    """Fail-closed: omitting a required metric must raise, never silently pass."""
    from quant_nanggroe.engine.risk.kill_switch import KillSwitch

    ks = KillSwitch()
    with pytest.raises(ValueError):
        # Omit weekly_pnl_pct (None) -> must refuse, not assume "no loss".
        ks.check_auto_activate(
            daily_pnl_pct=-0.001,
            weekly_pnl_pct=None,
            max_drawdown_pct=0.01,
            volatility_pct=0.02,
        )
    # Switch must remain inactive (did not fail open / trip on missing data).
    assert ks.is_active is False
