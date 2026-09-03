"""Kelly/sizing parity tests — CONSOLIDATION PREP (workstream F2, observation only).

Compares the four fixed-size entry points on IDENTICAL inputs
(price/SL/balance → size), plus the Kelly delegation path:

  A. ConstitutionalRiskGuard.calculate_position_size
     quant_nanggroe/engine/risk/checks.py:401
     (equity, entry_price, stop_loss_price, risk_pct) — risk_pct is PERCENT
     (0.5 = 0.5%), returns units float, capped at 10% position value.
  B. sizing.calculate_position_size ... quant_nanggroe/engine/risk/sizing.py:7
     (entry_price, stop_loss, account_balance, risk_per_trade, pip_value,
     instrument_type) — risk_per_trade is a DECIMAL fraction (0.02 = 2%),
     returns dict, NO position cap.
  C. PositionSizer.fixed_fractional ... quant_nanggroe/engine/risk/position_sizing.py:43
     (equity, risk_pct, entry_price, stop_price) — risk_pct is a DECIMAL
     fraction (0.01), hard-capped at MAX_RISK_PER_TRADE, returns dataclass.
  D. RiskManager.calculate_position_size
     quant_nanggroe/engine/risk/manager.py:670
     (account_balance, risk_pct, stop_loss_pips, pip_value) — risk_pct is a
     DECIMAL fraction, capped at MAX_RISK_PER_TRADE, returns dict with a
     0.01 minimum lot floor.
  E. Kelly path: sizing.calculate_kelly_size (sizing.py:55) delegates to
     risk/kelly.py KellyCriterion (legacy shim over engine/kelly/).

Shared baseline: ENTRY=100.0, SL=90.0 (distance 10.0), BALANCE=100_000,
RISK=0.5% (0.5 for A; 0.005 for B/C/D — same economics, see *1).

AGREEMENT TABLE (observed 2026-09-03, must match test outcomes):

| # | scenario                 | A      | B (fx,pv=1) | C      | D (pv=1) | agree? |
|---|--------------------------|--------|-------------|--------|----------|--------|
| T1| 0.5% risk, dist 10       | 50.0   | 50.0        | 50.0   | 50.0     | YES    |
| T2| zero SL distance         | 0.0    | 0.0 (+err)  | 0.0    | 0.01 *2  | NO     |
| T3| same literal 0.5 passed  | 50.0   | 5000.0 *1   | —      | —        | NO     |
| T4| tight SL (dist 1), 0.5%  | 100.0 *3| 500.0      | —      | —        | NO     |
| T5| Kelly delegation (E)     | —      | == direct KellyCriterion *4 | — | —   | YES    |

*1 UNIT CONVENTION TRAP: B takes a decimal fraction (sizing.py:11
    `risk_per_trade: 0.02 = 2%`) while A takes percent (checks.py:406
    `risk_pct` with `/100`). Passing the same literal 0.5 means 50% to B
    but 0.5% to A — a 100x divergence at the call-site, not in the math.
*2 D floors the lot at 0.01 (manager.py:696
    `max(0.01, ...)`): a zero-risk/zero-distance trade still reports a
    0.01 minimum lot while A/B/C report 0.0. Fail-open floor — F5 must decide.
*3 A caps notional at 10% of equity (checks.py:438-441:
    max_position_value/price = 100 units here); B has no cap (sizing.py
    returns raw risk_amount/ticks_risk). Same formula, different guardrails.
*4 E delegates exactly (sizing.py:79-88 constructs KellyCriterion +
    KellyParameters and scales by kelly_fraction); the dict values equal the
    direct legacy-shim result term-for-term.

DO NOT unify conventions here — parity first, merge in F5.
"""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("PERSISTENCE_BACKEND", "memory")

from quant_nanggroe.engine.risk.checks import ConstitutionalRiskGuard
from quant_nanggroe.engine.risk.manager import RiskManager
from quant_nanggroe.engine.risk.position_sizing import PositionSizer
from quant_nanggroe.engine.risk.sizing import (
    calculate_kelly_size,
    calculate_position_size,
)

ENTRY = 100.0
SL_WIDE = 90.0
SL_TIGHT = 99.0
BALANCE = 100_000.0

_GUARD = ConstitutionalRiskGuard()
_RM = RiskManager(initial_equity=BALANCE)


def _a(equity: float, entry: float, sl: float, risk_pct: float) -> float:
    return _GUARD.calculate_position_size(equity, entry, sl, risk_pct)


def _b(entry: float, sl: float, balance: float, risk_frac: float) -> dict:
    return calculate_position_size(
        entry, sl, balance, risk_per_trade=risk_frac, pip_value=1.0,
        instrument_type="forex",
    )


def _c(equity: float, risk_frac: float, entry: float, sl: float) -> float:
    return PositionSizer.fixed_fractional(equity, risk_frac, entry, sl).size


def _d(balance: float, risk_frac: float, sl_pips: float) -> dict:
    return _RM.calculate_position_size(balance, risk_frac, sl_pips, pip_value=1.0)


# ── T1: identical economics agree ────────────────────────────────────────
def test_kelly_parity_t1_same_economics_agree() -> None:
    assert _a(BALANCE, ENTRY, SL_WIDE, 0.5) == pytest.approx(50.0)
    assert _b(ENTRY, SL_WIDE, BALANCE, 0.005)["lot_size"] == pytest.approx(50.0)
    assert _c(BALANCE, 0.005, ENTRY, SL_WIDE) == pytest.approx(50.0)
    assert _d(BALANCE, 0.005, 10.0)["lot_size"] == pytest.approx(50.0)


# ── T2: zero SL distance — D floors at 0.01 ──────────────────────────────
@pytest.mark.xfail(
    strict=False,
    reason="D floors at 0.01 lots (manager.py:696) while A/B/C report 0.0. "
    "Documented *2.",
)
def test_kelly_parity_t2_zero_distance_unanimous_zero() -> None:
    assert _a(BALANCE, ENTRY, ENTRY, 0.5) == 0.0
    assert _b(ENTRY, ENTRY, BALANCE, 0.005)["lot_size"] == 0.0
    assert _c(BALANCE, 0.005, ENTRY, ENTRY) == 0.0
    assert _d(BALANCE, 0.005, 0.0)["lot_size"] == 0.0


# ── T3: same literal 0.5 — percent vs decimal trap ───────────────────────
@pytest.mark.xfail(
    strict=False,
    reason="B reads 0.5 as 50% (decimal, sizing.py:11), A reads 0.5 as 0.5% "
    "(percent, checks.py:406) — 100x call-site divergence. Documented *1.",
)
def test_kelly_parity_t3_same_literal_agrees() -> None:
    assert _a(BALANCE, ENTRY, SL_WIDE, 0.5) == pytest.approx(
        _b(ENTRY, SL_WIDE, BALANCE, 0.5)["lot_size"]
    )


# ── T4: tight SL — A caps at 10% notional, B uncapped ────────────────────
@pytest.mark.xfail(
    strict=False,
    reason="A caps at 10% position value (checks.py:438-441 -> 100.0 units); "
    "B returns raw 500.0 (no cap). Documented *3.",
)
def test_kelly_parity_t4_tight_sl_agrees() -> None:
    assert _a(BALANCE, ENTRY, SL_TIGHT, 0.5) == pytest.approx(
        _b(ENTRY, SL_TIGHT, BALANCE, 0.005)["lot_size"]
    )


# ── T5: Kelly delegation equals direct shim ──────────────────────────────
def test_kelly_parity_t5_kelly_delegation_matches_direct() -> None:
    from quant_nanggroe.engine.risk.kelly import (
        KellyCriterion,
        KellyMethod,
        KellyParameters,
    )

    via_sizing = calculate_kelly_size(
        win_rate=0.6, avg_win=100.0, avg_loss=50.0,
        account_balance=10_000.0, kelly_fraction=0.25,
    )
    direct = KellyCriterion().calculate_kelly(
        KellyParameters(win_rate=0.6, avg_win=100.0, avg_loss=50.0),
        KellyMethod.FRACTIONAL_KELLY,
    )
    assert via_sizing["kelly_pct"] == pytest.approx(
        direct.optimal_fraction * 100, rel=1e-6
    )
    assert via_sizing["fractional_kelly"] == pytest.approx(
        direct.adjusted_fraction * 0.25 * 100, rel=1e-6
    )
    assert via_sizing["suggested_position"] == pytest.approx(
        10_000.0 * direct.adjusted_fraction * 0.25, rel=1e-6
    )
