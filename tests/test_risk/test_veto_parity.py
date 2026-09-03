"""Veto parity tests — CONSOLIDATION PREP (workstream F1, observation only).

Compares the four veto-family entry points on the SAME 6 scenarios:

  A. RiskManager.check_trade .......... quant_nanggroe/engine/risk/manager.py:389
  B. ConstitutionalRiskGuard.check_trade quant_nanggroe/engine/risk/checks.py:191
  C. GovernanceVetoGuard.check ........ quant_nanggroe/engine/risk/veto_guard.py:81
  D. QuickVetoBridge.evaluate ......... quant_nanggroe/engine/risk/quick_veto.py:165

Shared fixture baseline (all guards see the same economics):
  equity/balance = 100_000, entry = 100.0, qty = 10 unless stated.

AGREEMENT TABLE (observed 2026-09-03 under pytest, must match test outcomes):

| # | scenario            | A RiskManager | B ConstGuard | C GovVeto | D QuickVeto | unanimous? |
|---|---------------------|---------------|--------------|-----------|-------------|------------|
| S1| clean trade         | CRASH *0      | APPROVED     | VETOED *1 | APPROVED    | NO         |
| S2| oversized (50% eq)  | CRASH *0      | APPROVED+adj | VETOED    | VETOED      | NO         |
| S3| no stop-loss        | CRASH *0      | VETOED       | VETOED *2 | APPROVED *3 | NO         |
| S4| daily-loss breach   | CRASH *0      | VETOED       | VETOED    | VETOED      | YES (B/C/D)|
| S5| weekly-loss breach  | CRASH *0      | VETOED       | VETOED    | APPROVED *4 | NO         |
| S6| kill-switch active  | VETOED        | APPROVED *5  | VETOED    | KILL_SWITCH | NO (A/C/D block, B does not) |

*0 A CRASHES with UnboundLocalError (manager.py:492 MAX_DAILY_TRADES) whenever
    the kill switch is inactive: get_effective_config() raises under the pytest
    env (DB-backed UI config), the try/except at manager.py:439-453 swallows it
    AFTER the shadow assignments made the names function-locals, leaving them
    unbound. Kill-active (S6/S7) returns early at manager.py:478 before the
    crash line, so A vetoes correctly there. Live-path bug — recorded for F5.
*1 C vetoes the clean trade: veto_guard.py:106-111 compares notional dollars
    (qty*price = 1000) against the FRACTIONAL limit 0.005, so any real-size
    order trips it (unit mismatch). B/D approve the same trade.
*2 C vetoes no-SL for the *1 reason (it never inspects stop-loss at all).
*3 D has no missing-SL check (quick_veto.py:253-260 only flags a WIDE stop);
    a proposal without 'sl' scores 0.35 and is APPROVED.
*4 D's proposal schema has no weekly_pnl key (quick_veto.py:165-189); a
    weekly-only breach is invisible to it -> APPROVED.
*5 B has no kill-switch concept (checks.py:191-350 inspects only the
    request+portfolio); with clean books it APPROVES while the switch is live.

DO NOT "fix" any guard to make this table green — parity first, merge in F5.
"""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("PERSISTENCE_BACKEND", "memory")

from quant_nanggroe.engine.execution.base import Order, OrderSide, OrderType
from quant_nanggroe.engine.risk.checks import (
    ConstitutionalRiskGuard,
    PortfolioSnapshot,
    TradeAction,
    TradeRequest,
)
from quant_nanggroe.engine.risk.manager import RiskManager
from quant_nanggroe.engine.risk.quick_veto import QuickVetoBridge, QuickVerdict
from quant_nanggroe.engine.risk.veto_guard import GovernanceVetoGuard

EQUITY = 100_000.0
ENTRY = 100.0
QTY = 10.0


class _EmptyBroker:
    """Fake live-broker handle: no deals -> realised PnL 0, sync healthy."""

    def history_deals_get(self, _from, _to):
        return []


def _risk_manager() -> RiskManager:
    rm = RiskManager(initial_equity=EQUITY)
    rm.set_broker_handle(_EmptyBroker())
    return rm


def _const_guard_approved(
    qty: float = QTY,
    stop_loss_pct: float = 1.0,
    daily_pnl: float = 0.0,
    weekly_pnl: float = 0.0,
) -> bool:
    guard = ConstitutionalRiskGuard()
    req = TradeRequest(
        symbol="EURUSD",
        action=TradeAction.BUY,
        quantity=qty,
        price=ENTRY,
        stop_loss_pct=stop_loss_pct,
    )
    pf = PortfolioSnapshot(
        total_equity=EQUITY, daily_pnl=daily_pnl, weekly_pnl=weekly_pnl
    )
    return guard.check_trade(req, pf).approved


def _gov_allowed(
    qty: float = QTY,
    daily_pct: float = 0.0,
    weekly_pct: float = 0.0,
    kill: bool = False,
) -> bool:
    guard = GovernanceVetoGuard()
    guard.update_pnl(daily_pct, weekly_pct)
    guard.set_kill_switch_active(kill)
    order = Order(
        id="parity-1",
        symbol="EURUSD",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=qty,
        price=ENTRY,
    )
    return guard.check(order).allowed


def _quick_verdict(
    volume: float = QTY,
    sl: float | None = 99.0,
    daily_pnl: float = 0.0,
    risk_manager=None,
) -> QuickVerdict:
    bridge = QuickVetoBridge(risk_manager=risk_manager, log_veto=False)
    proposal = {
        "symbol": "EURUSD",
        "action": "buy",
        "volume": volume,
        "price": ENTRY,
        "account_balance": EQUITY,
        "daily_pnl": daily_pnl,
        "open_positions": 1,
        "market_volatility": 0.001,
    }
    if sl is not None:
        proposal["sl"] = sl
    return bridge.evaluate(proposal).verdict


def _is_veto_family(verdict: str | QuickVerdict | bool) -> bool:
    if isinstance(verdict, bool):
        return not verdict
    if isinstance(verdict, QuickVerdict):
        return verdict in (QuickVerdict.VETOED, QuickVerdict.KILL_SWITCH)
    return verdict == "VETOED"


# ── S1: clean trade (B/D approve, C vetoes — *1) ─────────────────────────
@pytest.mark.xfail(
    strict=False,
    reason="C vetoes clean trade (unit mismatch veto_guard.py:106-111); "
    "B/D approve. Documented *1.",
)
def test_parity_s1_clean_trade_unanimous_approve() -> None:
    assert _const_guard_approved() is True
    assert _gov_allowed() is True
    assert _quick_verdict() == QuickVerdict.APPROVED


# ── S2: oversized (B adjusts+approves, C/D veto) ─────────────────────────
@pytest.mark.xfail(
    strict=False,
    reason="B auto-adjusts oversized to 10% and APPROVES (checks.py:239-252); "
    "C/D VETO. Documented S2 split.",
)
def test_parity_s2_oversized_unanimous_veto() -> None:
    assert _is_veto_family(_const_guard_approved(qty=500.0, stop_loss_pct=2.0))
    assert _is_veto_family(_gov_allowed(qty=500.0))
    assert _is_veto_family(_quick_verdict(volume=500.0))


# ── S3: no stop-loss (B/C veto, D approves — *3) ─────────────────────────
@pytest.mark.xfail(
    strict=False,
    reason="D has no missing-SL check and APPROVES (quick_veto.py:253-260); "
    "B/C veto. Documented *3.",
)
def test_parity_s3_no_sl_unanimous_veto() -> None:
    assert _is_veto_family(_const_guard_approved(stop_loss_pct=0.0))
    assert _is_veto_family(_gov_allowed())
    assert _is_veto_family(_quick_verdict(sl=None))


# ── S4: daily-loss breach (-2% vs 1% limit) — unanimous veto ─────────────
def test_parity_s4_daily_loss_unanimous_veto() -> None:
    assert _is_veto_family(_const_guard_approved(daily_pnl=-2000.0))
    assert _is_veto_family(_gov_allowed(daily_pct=-0.02))
    assert _is_veto_family(_quick_verdict(daily_pnl=-2000.0))


# ── S5: weekly-loss breach (B/C veto, D approves — *4) ───────────────────
@pytest.mark.xfail(
    strict=False,
    reason="D schema has no weekly_pnl key (quick_veto.py:165-189) and "
    "APPROVES a weekly-only breach; B/C veto. Documented *4.",
)
def test_parity_s5_weekly_loss_unanimous_veto() -> None:
    assert _is_veto_family(_const_guard_approved(weekly_pnl=-4000.0))
    assert _is_veto_family(_gov_allowed(weekly_pct=-0.04))
    assert _is_veto_family(_quick_verdict())


# ── S6: kill-switch active (A/C/D block, B approves — *5) ────────────────
@pytest.mark.xfail(
    strict=False,
    reason="B has no kill-switch concept and APPROVES (checks.py:191-350); "
    "A/C/D block. Documented *5.",
)
def test_parity_s6_kill_active_unanimous_veto() -> None:
    rm = _risk_manager()
    rm.kill_switch.activate("parity probe s6")
    assert (
        rm.check_trade(
            symbol="EURUSD",
            direction="BUY",
            lot_size=QTY,
            entry=ENTRY,
            stop_loss=99.0,
            account_balance=EQUITY,
        )["verdict"]
        == "VETOED"
    )
    assert _is_veto_family(_const_guard_approved())
    assert _is_veto_family(_gov_allowed(kill=True))
    rm2 = _risk_manager()
    rm2.kill_switch.activate("parity probe s6")
    assert _is_veto_family(_quick_verdict(risk_manager=rm2))


# ── S7: kill-aware trio agrees (B excluded — no kill concept) ────────────
def test_parity_s7_kill_aware_trio_agrees() -> None:
    rm = _risk_manager()
    rm.kill_switch.activate("parity probe s7")
    assert (
        rm.check_trade(
            symbol="EURUSD",
            direction="BUY",
            lot_size=QTY,
            entry=ENTRY,
            stop_loss=99.0,
            account_balance=EQUITY,
        )["verdict"]
        == "VETOED"
    )
    assert _gov_allowed(kill=True) is False
    rm3 = _risk_manager()
    rm3.kill_switch.activate("parity probe s7")
    assert _quick_verdict(risk_manager=rm3) == QuickVerdict.KILL_SWITCH


# ── S8: A no longer crashes when kill inactive (FIXED v8.1.0 WS-A) ─────
# The old override-shadowing block assigned to bare constant names, making them
# function-locals; the RHS read raised UnboundLocalError (swallowed by
# `except: pass`, so overrides silently never applied). WS-A replaced it with
# underscore-prefixed locals + live-constant defaults. This test pins the fix:
# check_trade must return a verdict dict, never raise, with kill inactive.
def test_parity_s8_risk_manager_no_crash_when_kill_inactive() -> None:
    rm = _risk_manager()
    assert not rm.kill_switch.is_active
    out = rm.check_trade(
        symbol="EURUSD",
        direction="BUY",
        lot_size=QTY,
        entry=ENTRY,
        stop_loss=99.0,
        account_balance=EQUITY,
    )
    assert out["verdict"] in ("APPROVED", "VETOED")
