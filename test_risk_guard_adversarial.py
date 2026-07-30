#!/usr/bin/env python
"""
Adversarial test for QNA Risk Guard — Phase 4.
Break the risk guard. Prove it fails-closed.

Tests:
1. Force daily loss > 5% → assert veto fires, blocks ALL orders
2. Floating equity fallback (phantom veto) → report if guard halts on 0 real fills
3. Weekly-loss veto (currently missing?) → report gap
4. Kill-switch auto-activate on thresholds
"""

import sys
sys.path.insert(0, "D:/repositories/Quant-Nanggroe-AI-worktree")

from quant_nanggroe.engine.risk.manager import RiskManager
from quant_nanggroe.engine.risk.kill_switch import KillSwitch, KillSwitchLevel, KillSwitchTrigger
from quant_nanggroe.engine.risk.checks import ConstitutionalRiskGuard, TradeRequest, PortfolioSnapshot, TradeAction
from quant_nanggroe.engine.risk.constants import (
    MAX_DAILY_LOSS, MAX_WEEKLY_LOSS, MAX_RISK_PER_TRADE,
    KILL_SWITCH_DAILY_PNL, KILL_SWITCH_WEEKLY_PNL
)

print("=" * 60)
print("QNA RISK GUARD — ADVERSARIAL TEST (Phase 4)")
print("=" * 60)

# ============================================================
# TEST 1: Daily loss > 5% → veto fires, blocks ALL orders
# ============================================================
print("\n[TEST 1] Daily loss > 5% → veto should fire")
print(f"  Constitutional MAX_DAILY_LOSS = {MAX_DAILY_LOSS:.2%}")
print(f"  Kill switch threshold = {abs(KILL_SWITCH_DAILY_PNL):.2%}")

rm = RiskManager(initial_equity=1_000_000.0)
# Force daily P&L to -55,000 (-5.5%)
rm.state.daily_pnl = -55_000.0
rm.state.peak_equity = 1_000_000.0

result = rm.check_trade(
    symbol="BTCUSDT",
    direction="BUY",
    lot_size=0.1,
    entry=50000.0,
    stop_loss=49000.0,
    account_balance=1_000_000.0,
)

print(f"  Result verdict: {result['verdict']}")
print(f"  Failed checkpoints: {result.get('failed_checkpoints', [])}")
print(f"  Reason: {result.get('reason', 'N/A')}")

# Check kill switch activated
ks_status = rm.kill_switch.status()
print(f"  Kill switch active: {ks_status['is_active']}")
print(f"  Kill switch level: {ks_status['current_level']}")

if result['verdict'] == 'VETOED' and 'daily' in str(result.get('failed_checkpoints', '')).lower():
    print("  ✅ PASS: Daily loss veto fired")
else:
    print("  ❌ FAIL: Daily loss veto DID NOT fire")

# ============================================================
# TEST 2: Weekly loss > 3% → veto should fire (Level 2)
# ============================================================
print("\n[TEST 2] Weekly loss > 3% → veto should fire (Level 2)")
print(f"  Constitutional MAX_WEEKLY_LOSS = {MAX_WEEKLY_LOSS:.2%}")
print(f"  Kill switch threshold = {abs(KILL_SWITCH_WEEKLY_PNL):.2%}")

rm2 = RiskManager(initial_equity=1_000_000.0)
rm2.state.weekly_pnl = -35_000.0  # -3.5%
rm2.state.peak_equity = 1_000_000.0

result2 = rm2.check_trade(
    symbol="ETHUSDT",
    direction="BUY",
    lot_size=0.1,
    entry=3000.0,
    stop_loss=2900.0,
    account_balance=1_000_000.0,
)

print(f"  Result verdict: {result2['verdict']}")
print(f"  Failed checkpoints: {result2.get('failed_checkpoints', [])}")
print(f"  Reason: {result2.get('reason', 'N/A')}")

ks_status2 = rm2.kill_switch.status()
print(f"  Kill switch active: {ks_status2['is_active']}")
print(f"  Kill switch level: {ks_status2['current_level']}")

if result2['verdict'] == 'VETOED' and 'weekly' in str(result2.get('failed_checkpoints', '')).lower():
    print("  ✅ PASS: Weekly loss veto fired")
else:
    print("  ❌ FAIL: Weekly loss veto DID NOT fire")

# ============================================================
# TEST 3: Floating equity fallback (phantom veto)
# Guard should NOT halt on floating MT5 equity when 0 real fills
# ============================================================
print("\n[TEST 3] Phantom veto — floating equity with 0 real fills")
print("  Simulating: demo account with open losing position, 0 closed trades")

rm3 = RiskManager(initial_equity=10_000.0)
# 0 trades this week, but floating PnL = -1000 (-10%)
# Without live MT5 handle, _sync_realized_pnl does nothing
# check_trade should use state.daily_pnl (0.0) not floating equity
# If it uses floating → phantom VETOED

rm3.state.trade_count_week = 0
rm3.state.trade_count_today = 0
rm3.state.daily_pnl = 0.0  # REALIZED = 0
rm3.state.weekly_pnl = 0.0  # REALIZED = 0

# Simulate a caller passing floating daily_pnl_pct (pitfall #58)
# The guard should IGNORE caller overrides when MT5 handle is None?
# Actually: the code at line 387-390 uses overrides ONLY when _mt5_handle is None
# But lines 407-412 DO use overrides for the check_gate when _mt5_handle is None
# This is the PHANTOM VETO bug!

result3 = rm3.check_trade(
    symbol="EURUSD",
    direction="BUY",
    lot_size=0.1,
    entry=1.0800,
    stop_loss=1.0750,
    account_balance=10_000.0,
    daily_pnl_pct=-0.10,  # Floating -10% (NOT realized)
    weekly_pnl_pct=-0.10,
)

print(f"  Result verdict: {result3['verdict']}")
print(f"  Failed checkpoints: {result3.get('failed_checkpoints', [])}")
print(f"  Realized daily_pnl in state: {rm3.state.daily_pnl}")
print(f"  Realized weekly_pnl in state: {rm3.state.weekly_pnl}")
print(f"  Caller passed daily_pnl_pct=-0.10 (floating)")

# Check if phantom veto happened
if result3['verdict'] == 'VETOED' and 'daily' in str(result3.get('failed_checkpoints', '')).lower():
    print("  ❌ FAIL: Phantom veto triggered on floating equity (0 real fills)")
    print("      This is pitfall #58 — floating equity fallback vetoes incorrectly")
else:
    print("  ✅ PASS: No phantom veto (correctly ignored floating equity)")

# ============================================================
# TEST 4: Kill switch auto-activate at KILL_SWITCH_DAILY_PNL (-0.8%)
# ============================================================
print("\n[TEST 4] Kill switch auto-activate at -0.8% daily loss (early warning)")

rm4 = RiskManager(initial_equity=1_000_000.0)
rm4.state.daily_pnl = -9_000.0  # -0.9% (> -0.8% threshold)
rm4.state.peak_equity = 1_000_000.0

# Trigger auto check
rm4._auto_check_kill_switch()

ks_status4 = rm4.kill_switch.status()
print(f"  Kill switch active: {ks_status4['is_active']}")
print(f"  Kill switch level: {ks_status4['current_level']}")
print(f"  Activation reason: {ks_status4['activation_reason']}")

if ks_status4['is_active'] and ks_status4['current_level'] == 'level_1':
    print("  ✅ PASS: Kill switch auto-activated at -0.8% (LEVEL_1)")
else:
    print("  ❌ FAIL: Kill switch did NOT auto-activate at early warning threshold")

# ============================================================
# TEST 5: Kill switch auto-activate at KILL_SWITCH_WEEKLY_PNL (-2.5%)
# ============================================================
print("\n[TEST 5] Kill switch auto-activate at -2.5% weekly loss (early warning)")

rm5 = RiskManager(initial_equity=1_000_000.0)
rm5.state.weekly_pnl = -30_000.0  # -3.0% (> -2.5% threshold)
rm5.state.peak_equity = 1_000_000.0

rm5._auto_check_kill_switch()

ks_status5 = rm5.kill_switch.status()
print(f"  Kill switch active: {ks_status5['is_active']}")
print(f"  Kill switch level: {ks_status5['current_level']}")
print(f"  Activation reason: {ks_status5['activation_reason']}")

if ks_status5['is_active'] and ks_status5['current_level'] == 'level_2':
    print("  ✅ PASS: Kill switch auto-activated at -2.5% (LEVEL_2)")
else:
    print("  ❌ FAIL: Kill switch did NOT auto-activate at weekly early warning")

# ============================================================
# TEST 6: Constitutional Risk Guard (checks.py) — rubber stamp test
# ============================================================
print("\n[TEST 6] ConstitutionalRiskGuard — rubber stamp detection")
print("  Checking if guard approves everything at fixed score (pitfall #57)")

guard = ConstitutionalRiskGuard()

# Create a portfolio with 0 loss, high equity
portfolio = PortfolioSnapshot(
    total_equity=100_000.0,
    daily_pnl=0.0,
    weekly_pnl=0.0,
)

# Send 10 different trade requests — all should be evaluated on merit
approvals = 0
for i in range(10):
    req = TradeRequest(
        symbol="BTCUSDT" if i % 2 == 0 else "ETHUSDT",
        action=TradeAction.BUY,
        quantity=0.5,
        price=50000.0 if i % 2 == 0 else 3000.0,
        stop_loss_pct=2.0,
    )
    result = guard.check_trade(req, portfolio)
    if result.approved:
        approvals += 1

print(f"  Approvals: {approvals}/10")
if approvals == 10:
    print("  ⚠️  WARNING: 100% approval rate — may be rubber stamp (pitfall #57)")
    print("      Check if strategy signal/confidence is wired into the guard")
else:
    print("  ✅ PASS: Not all trades approved — guard is selective")

# ============================================================
# TEST 7: Verify kill-switch config uses KILL_SWITCH_* constants
# (not MAX_DAILY_LOSS/MAX_WEEKLY_LOSS directly — pitfall #41)
# ============================================================
print("\n[TEST 7] KillSwitchConfig thresholds = KILL_SWITCH_* constants")

ks = KillSwitch()
config = ks.config
print(f"  config.auto_daily_loss_pct = {config.auto_daily_loss_pct:.4f} (expected {abs(KILL_SWITCH_DAILY_PNL):.4f})")
print(f"  config.auto_weekly_loss_pct = {config.auto_weekly_loss_pct:.4f} (expected {abs(KILL_SWITCH_WEEKLY_PNL):.4f})")

if abs(config.auto_daily_loss_pct - abs(KILL_SWITCH_DAILY_PNL)) < 0.0001:
    print("  ✅ PASS: Daily threshold uses KILL_SWITCH_DAILY_PNL (-0.8%)")
else:
    print("  ❌ FAIL: Daily threshold does NOT match KILL_SWITCH_DAILY_PNL")

if abs(config.auto_weekly_loss_pct - abs(KILL_SWITCH_WEEKLY_PNL)) < 0.0001:
    print("  ✅ PASS: Weekly threshold uses KILL_SWITCH_WEEKLY_PNL (-2.5%)")
else:
    print("  ❌ FAIL: Weekly threshold does NOT match KILL_SWITCH_WEEKLY_PNL")

# ============================================================
# TEST 8: RiskManager._auto_check_kill_switch uses KILL_SWITCH_* constants
# ============================================================
print("\n[TEST 8] RiskManager._auto_check_kill_switch uses KILL_SWITCH_* constants")
# Read the source to verify lines 984-990 use KILL_SWITCH_DAILY_PNL/WEEKLY_PNL
import inspect
src = inspect.getsource(RiskManager._auto_check_kill_switch)
if "KILL_SWITCH_DAILY_PNL" in src and "KILL_SWITCH_WEEKLY_PNL" in src:
    print("  ✅ PASS: _auto_check_kill_switch references KILL_SWITCH_* constants")
else:
    print("  ❌ FAIL: _auto_check_kill_switch does NOT use KILL_SWITCH_* constants")
    print("      This is pitfall #41 — using MAX_DAILY_LOSS/MAX_WEEKLY_LOSS directly")

print("\n" + "=" * 60)
print("ADVERSARIAL TEST COMPLETE")
print("=" * 60)