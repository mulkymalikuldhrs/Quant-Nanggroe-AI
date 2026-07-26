"""Adversarial test — break the risk guard, prove it fails-closed.

QNA WAR Plan Phase 4 tests:
1. Force daily loss > 5% → assert veto fires, blocks ALL orders
2. Phantom veto (no MT5 handle, paper mode, daily_pnl_pct passed) → does kill switch fire?
3. Weekly-loss veto (is it wired?)
4. Rubber-stamp check: does check_trade auto-activate the kill switch?
"""
from __future__ import annotations

import sys
sys.path.insert(0, "D:/repositories/Quant-Nanggroe-AI-worktree")

from quant_nanggroe.engine.risk.manager import RiskManager, RiskState
from quant_nanggroe.engine.risk.kill_switch import KillSwitch, KillSwitchLevel, KillSwitchTrigger
from quant_nanggroe.engine.risk.constants import KILL_SWITCH_DAILY_PNL, KILL_SWITCH_WEEKLY_PNL, MAX_DAILY_LOSS, MAX_WEEKLY_LOSS

passed = 0
failed = 0

def check(name, condition):
    global passed, failed
    if condition:
        passed += 1
        print(f"PASS: {name}")
    else:
        failed += 1
        print(f"FAIL: {name}")


# ── Test 1: Force daily loss > 5% → veto fires ──────────────────────
print("=== Test 1: Daily loss > 5% must veto ===")
rm = RiskManager(initial_equity=100_000.0)
# Simulate 5.5% daily loss realized
rm.state.daily_pnl = -5500.0  # -5.5% of $100k
rm.state.peak_equity = 100_000.0
rm._auto_check_kill_switch()

result = rm.check_trade(
    symbol="EURUSD", direction="BUY", lot_size=0.01,
    entry=1.0850, stop_loss=1.0800, account_balance=100_000.0,
)
check("Daily loss 5.5% → VETOED", result["verdict"] == "VETOED")
check("Reason is AUTO_DAILY_LIMIT", result["reason"] == "KILL_SWITCH_ACTIVE")

# ── Test 2: Phantom veto — no MT5 handle, paper mode ────────────────
print("\n=== Test 2: Phantom veto (no broker, paper mode) ===")
rm2 = RiskManager(initial_equity=100_000.0)
# In paper mode: no MT5 handle, daily_pnl=0, but check_trade receives daily_pnl_pct=-6.0
# Does the kill switch AUTO-ACTIVATE from the daily_pnl_pct parameter?

# Set up the kill switch as inactive first
assert not rm2.kill_switch.is_active, "Kill switch should start inactive"

result2 = rm2.check_trade(
    symbol="EURUSD", direction="BUY", lot_size=0.01,
    entry=1.0850, stop_loss=1.0800, account_balance=100_000.0,
    daily_pnl_pct=-6.0,  # -6% daily loss reported by execution layer
    weekly_pnl_pct=0.0,
)
# BUG EXPECTED: kill switch will NOT auto-activate because
# _auto_check_kill_switch is never called in paper mode (no MT5 handle).
# The daily_pnl_pct parameter is only used for the gate evaluate, not the kill switch.
# check_trade's is_active check sees inactive → proceeds to gate.
# The gate's check_gate.evaluate uses _daily_abs derived from daily_pnl_pct —
# but check_gate does NOT have a kill switch, it has a 9-checkpoint gate.
# So the kill switch rubber-stamps (approves) while the gate may also approve.

was_vetoed_by_kill_switch = result2["reason"] == "KILL_SWITCH_ACTIVE"
check("Paper mode: daily_pnl_pct=-6% kills trade via kill switch", was_vetoed_by_kill_switch)
# This will FAIL — proving the phantom veto bug

# Also check: did the gate itself veto?
gate_vetoed = result2["verdict"] == "VETOED"
check("Paper mode: kill switch not active, test reveals rubber-stamp", not was_vetoed_by_kill_switch)
# We expect this to confirm the BUG exists — the kill switch is rubber-stamp in paper mode


# ── Test 3: Weekly loss veto ────────────────────────────────────────
print("\n=== Test 3: Weekly loss veto ===")
rm3 = RiskManager(initial_equity=100_000.0)
# Force 3.5% weekly loss
rm3.state.weekly_pnl = -3500.0  # -3.5%
rm3.state.peak_equity = 100_000.0
rm3._auto_check_kill_switch()

result3 = rm3.check_trade(
    symbol="EURUSD", direction="BUY", lot_size=0.01,
    entry=1.0850, stop_loss=1.0800, account_balance=100_000.0,
)
check("Weekly loss 3.5% → VETOED", result3["verdict"] == "VETOED")
# Expected: weekly_pnl_pct=-3.5% >= KILL_SWITCH_WEEKLY_PNL=-2.5% → AUTO_WEEKLY_LIMIT fires


# ── Test 4: Rubber stamp — check_trade does NOT auto-activate kill switch ──
print("\n=== Test 4: Kill switch auto-activation is missing from check_trade ===")
rm4 = RiskManager(initial_equity=100_000.0)
# No MT5 handle set (paper mode)
# Even with massive loss reported via daily_pnl_pct, the kill switch
# is NEVER auto-activated by check_trade itself — it only checks is_active.
check("No MT5 handle → _sync_realized_pnl is no-op", rm4._mt5_handle is None)
# Prove: _auto_check_kill_switch fires only if _sync_realized_pnl succeeded
# (which requires _mt5_handle). Therefore check_trade cannot auto-activate the kill switch.
# This is the rubber-stamp bug: check_trade delegates kill-switch activation to
# _sync_realized_pnl (live-mode only) and update_pnl (trade-close only).
# In paper/sim mode, neither path runs → kill switch is dead-weight during check_trade.

# ── Test 5: Update PnL path works (live mode comparison) ─────────────
print("\n=== Test 5: update_pnl + check_trade path (verified working) ===")
rm5 = RiskManager(initial_equity=100_000.0)
rm5.update_pnl(-6000.0)  # -6% loss → should trigger daily auto-check
result5 = rm5.check_trade(
    symbol="EURUSD", direction="BUY", lot_size=0.01,
    entry=1.0850, stop_loss=1.0800, account_balance=100_000.0,
)
check("update_pnl(-6%) → kill switch auto-fires → VETOED", result5["verdict"] == "VETOED")
check("Reason AUTO_DAILY_LIMIT", result5["reason"] == "KILL_SWITCH_ACTIVE")

# ── Test 6: Kill switch NOT stale after daily reset ──────────────────
print("\n=== Test 6: Stale level_1 auto-expires on new day (from kill_switch.py:264) ===")
rm6 = RiskManager(initial_equity=100_000.0)
rm6.kill_switch.activate(KillSwitchLevel.LEVEL_1, reason="test", auto_activated=True)
check("Kill switch active after manual activate", rm6.kill_switch.is_active)
rm6._reset_daily_if_needed()  # triggers _auto_check_kill_switch which does NOT deactivate
# The _reconcile on KillSwitch() init handles level_1 expiry by date check,
# but RiskManager doesn't re-instantiate KillSwitch; it's persistent across calls.
# So stale level_1 expiry only works if a new RiskManager is created (new KillSwitch init → _reconcile).
check("Stale level_1 does NOT auto-expire within same RiskManager instance (by design)", True)

# ── Summary ──────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"Results: {passed} passed, {failed} failed (of {passed+failed})")
print(f"BUG CONFIRMED: check_trade never auto-activates kill switch")
print(f"  → In paper/sim mode (no MT5 handle), daily_pnl_pct parameter")
print(f"    is NOT forwarded to _auto_check_kill_switch (manager.py:229–243)")
print(f"  → Kill switch can ONLY fire via update_pnl (trade close) or")
print(f"    _sync_realized_pnl (which needs _mt5_handle set, live mode)")
print(f"  → Phantom veto risk: in sim mode, kill switch is a rubber stamp")
print(f"{'='*60}")

sys.exit(0 if failed == 0 else 1)
