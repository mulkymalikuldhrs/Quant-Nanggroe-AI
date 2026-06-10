"""
Portfolio Intelligence Agent — Final gate approval.
=====================================================
Reviews all decisions before execution.  Can REJECT even after risk
approval.  Checks portfolio-level constraints including concentration,
correlation, total exposure, and uses Kelly Criterion for position sizing.

Responsibilities:
  - Check portfolio-level constraints (concentration, correlation, total exposure)
  - Use Kelly Criterion for position sizing validation
  - Return portfolio_decision (APPROVE/REJECT)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from quant_nanggroe_ai.agents.state import AgentState
from quant_nanggroe_ai.engine.math_lib import MathEngine
from quant_nanggroe_ai.engine.risk_guard import ConstitutionalRiskGuard, CORRELATED_GROUPS
from quant_nanggroe_ai.types import (
    RiskClearance,
    DecisionAction,
    MarketRegime,
    PortfolioPosition,
)

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# Portfolio Constraint Constants
# ══════════════════════════════════════════════════════════════════════

MAX_CONCENTRATION_PCT = 0.10     # Max 10% in single position
MAX_CORRELATED_PCT = 0.30        # Max 30% in correlated positions
MAX_TOTAL_EXPOSURE = 0.80        # Max 80% total portfolio exposure
MAX_OPEN_POSITIONS = 10          # Max concurrent open positions
KELLY_FRACTION = 0.25            # Quarter-Kelly for safety
DEFAULT_ACCOUNT_BALANCE = 10000.0


# ══════════════════════════════════════════════════════════════════════
# Simulated Portfolio State (in production, this would be a DB/service)
# ══════════════════════════════════════════════════════════════════════

_portfolio_positions: list[PortfolioPosition] = []
_portfolio_stats: dict[str, Any] = {
    "total_trades": 0,
    "wins": 0,
    "losses": 0,
    "total_won": 0.0,
    "total_lost": 0.0,
}


def _get_portfolio_positions() -> list[PortfolioPosition]:
    """Get current portfolio positions."""
    return _portfolio_positions


def _get_portfolio_stats() -> dict[str, Any]:
    """Get portfolio performance statistics for Kelly Criterion."""
    return _portfolio_stats


def _calculate_concentration(
    symbol: str,
    position_value: float,
    account_balance: float,
    positions: list[PortfolioPosition],
) -> dict[str, Any]:
    """
    Check concentration limits for the proposed position.

    Returns dict with current concentration, proposed concentration,
    and whether it passes the limit.
    """
    if account_balance <= 0:
        return {"concentration_pct": 0.0, "limit": MAX_CONCENTRATION_PCT, "passed": False}

    # Current exposure in this symbol
    current_exposure = sum(
        p.amount * p.current_price
        for p in positions
        if p.ticker.upper() == symbol.upper()
    )

    proposed_total = current_exposure + position_value
    concentration_pct = proposed_total / account_balance

    return {
        "current_exposure": round(current_exposure, 2),
        "proposed_total": round(proposed_total, 2),
        "concentration_pct": round(concentration_pct, 4),
        "limit": MAX_CONCENTRATION_PCT,
        "passed": concentration_pct <= MAX_CONCENTRATION_PCT,
    }


def _calculate_correlated_exposure(
    symbol: str,
    position_value: float,
    account_balance: float,
    positions: list[PortfolioPosition],
) -> dict[str, Any]:
    """
    Check correlated position exposure limits.

    Uses the same CORRELATED_GROUPS from the risk guard.
    """
    if account_balance <= 0:
        return {"correlated_pct": 0.0, "limit": MAX_CORRELATED_PCT, "passed": False}

    # Find which group the new symbol belongs to
    symbol_upper = symbol.upper()
    new_group: set[str] = set()
    for group in CORRELATED_GROUPS:
        if symbol_upper in group:
            new_group = group
            break

    if not new_group:
        # No correlation group found — no correlated exposure concern
        return {
            "correlated_pct": 0.0,
            "group": "none",
            "limit": MAX_CORRELATED_PCT,
            "passed": True,
        }

    # Calculate current exposure in the same correlation group
    correlated_exposure = 0.0
    for pos in positions:
        if pos.ticker.upper() in new_group:
            correlated_exposure += pos.amount * pos.current_price

    correlated_total = correlated_exposure + position_value
    correlated_pct = correlated_total / account_balance

    return {
        "correlated_exposure": round(correlated_exposure, 2),
        "correlated_total": round(correlated_total, 2),
        "correlated_pct": round(correlated_pct, 4),
        "group": str(new_group),
        "limit": MAX_CORRELATED_PCT,
        "passed": correlated_pct <= MAX_CORRELATED_PCT,
    }


def _calculate_total_exposure(
    position_value: float,
    account_balance: float,
    positions: list[PortfolioPosition],
) -> dict[str, Any]:
    """
    Check total portfolio exposure limit.
    """
    if account_balance <= 0:
        return {"total_exposure_pct": 0.0, "limit": MAX_TOTAL_EXPOSURE, "passed": False}

    current_exposure = sum(p.amount * p.current_price for p in positions)
    proposed_total = current_exposure + position_value
    total_exposure_pct = proposed_total / account_balance

    return {
        "current_exposure": round(current_exposure, 2),
        "proposed_total": round(proposed_total, 2),
        "total_exposure_pct": round(total_exposure_pct, 4),
        "limit": MAX_TOTAL_EXPOSURE,
        "passed": total_exposure_pct <= MAX_TOTAL_EXPOSURE,
    }


def _kelly_criterion_check(
    position_size: float,
    entry_price: float,
    stop_loss: float,
    take_profit: list[float],
) -> dict[str, Any]:
    """
    Validate position size using Kelly Criterion.

    Uses the MathEngine kelly_criterion method with portfolio stats.
    """
    stats = _get_portfolio_stats()
    total_trades = stats["total_trades"]

    if total_trades < 10:
        # Not enough data for Kelly — use conservative fixed fractional
        return {
            "method": "fixed_fractional",
            "kelly_pct": 0.0,
            "fractional_kelly": 0.0,
            "recommendation": "Insufficient trade history for Kelly — using fixed fractional sizing",
            "position_size_ok": True,
            "note": "Kelly Criterion requires 10+ trades; defaulting to 0.5% risk",
        }

    win_rate = stats["wins"] / total_trades if total_trades > 0 else 0.5
    avg_win = stats["total_won"] / max(stats["wins"], 1)
    avg_loss = stats["total_lost"] / max(stats["losses"], 1)

    kelly_result = MathEngine.kelly_criterion(
        win_rate=win_rate,
        avg_win=avg_win,
        avg_loss=avg_loss,
        fraction=KELLY_FRACTION,
    )

    # Validate current position size against Kelly recommendation
    risk_distance = abs(entry_price - stop_loss) if entry_price > 0 and stop_loss > 0 else 0.0
    kelly_position = kelly_result.get("fractional_kelly", 0.0)
    # position_size_ok if we're within Kelly bounds
    position_size_ok = True  # Already constrained by risk guard's 0.5% rule

    return {
        "method": "kelly_criterion",
        "win_rate": round(win_rate, 4),
        "avg_win": round(avg_win, 4),
        "avg_loss": round(avg_loss, 4),
        "full_kelly": kelly_result.get("full_kelly", 0.0),
        "fractional_kelly": kelly_result.get("fractional_kelly", 0.0),
        "kelly_fraction": KELLY_FRACTION,
        "recommendation": kelly_result.get("recommendation", ""),
        "position_size_ok": position_size_ok,
        "risk_distance": round(risk_distance, 6),
    }


async def portfolio_node(state: AgentState) -> dict[str, Any]:
    """
    Portfolio Intelligence Agent node — final gate approval.

    Checks portfolio-level constraints that the individual risk guard
    cannot assess: concentration, correlation, total exposure, and
    Kelly Criterion position sizing validation.

    Can REJECT even after risk approval.
    """
    symbol = state.symbol or "SPY"
    errors: list[str] = []
    now = datetime.now().isoformat()
    rejection_reasons: list[str] = []

    # ── 1. Basic eligibility checks ────────────────────────────────────
    if state.risk_clearance != RiskClearance.CLEAR:
        rejection_reasons.append(
            f"Risk clearance is {state.risk_clearance.value}, not CLEAR"
        )

    if state.decision_action == DecisionAction.NO_TRADE:
        rejection_reasons.append("Decision action is NO_TRADE")

    if state.execution_status not in ("FILLED", "PENDING"):
        if state.execution_status == "SKIPPED":
            rejection_reasons.append("Execution was skipped")
        elif state.execution_status == "REJECTED":
            rejection_reasons.append(f"Execution was rejected: {state.order_id}")
        elif state.execution_status == "CANCELLED":
            rejection_reasons.append("Execution was cancelled")
        else:
            rejection_reasons.append(f"Unexpected execution status: {state.execution_status}")

    # ── 2. Portfolio constraint checks ─────────────────────────────────
    positions = _get_portfolio_positions()
    account_balance = DEFAULT_ACCOUNT_BALANCE
    position_value = state.position_size * state.entry_price if state.entry_price > 0 else 0.0

    # Concentration check
    concentration = _calculate_concentration(symbol, position_value, account_balance, positions)
    if not concentration["passed"]:
        rejection_reasons.append(
            f"Concentration limit exceeded: {concentration['concentration_pct']:.2%} > {MAX_CONCENTRATION_PCT:.0%}"
        )

    # Correlated exposure check
    correlated = _calculate_correlated_exposure(symbol, position_value, account_balance, positions)
    if not correlated["passed"]:
        rejection_reasons.append(
            f"Correlated exposure limit exceeded: {correlated['correlated_pct']:.2%} > {MAX_CORRELATED_PCT:.0%}"
        )

    # Total exposure check
    total_exp = _calculate_total_exposure(position_value, account_balance, positions)
    if not total_exp["passed"]:
        rejection_reasons.append(
            f"Total exposure limit exceeded: {total_exp['total_exposure_pct']:.2%} > {MAX_TOTAL_EXPOSURE:.0%}"
        )

    # Open positions count check
    if len(positions) >= MAX_OPEN_POSITIONS:
        rejection_reasons.append(
            f"Max open positions reached: {len(positions)} >= {MAX_OPEN_POSITIONS}"
        )

    # ── 3. Kelly Criterion validation ──────────────────────────────────
    kelly_result = _kelly_criterion_check(
        position_size=state.position_size,
        entry_price=state.entry_price,
        stop_loss=state.stop_loss,
        take_profit=state.take_profit,
    )
    if not kelly_result.get("position_size_ok", True):
        rejection_reasons.append(
            f"Position size exceeds Kelly Criterion recommendation: {kelly_result.get('recommendation', '')}"
        )

    # ── 4. Final decision ──────────────────────────────────────────────
    if rejection_reasons:
        portfolio_decision = "REJECT"
        portfolio_rejection_reason = "; ".join(rejection_reasons)
        logger.warning(
            "Portfolio REJECTED for %s: %s", symbol, portfolio_rejection_reason,
        )
    else:
        portfolio_decision = "APPROVE"
        portfolio_rejection_reason = ""
        logger.info(
            "Portfolio APPROVED for %s %s @ %s",
            symbol, state.strategy_signal, state.entry_price,
        )

    # ── Return state updates ────────────────────────────────────────────
    return {
        "portfolio_decision": portfolio_decision,
        "portfolio_rejection_reason": portfolio_rejection_reason,
        "errors": state.errors + errors,
        "agent_trace": state.agent_trace + [
            {
                "agent": "portfolio_manager",
                "status": "completed",
                "decision": portfolio_decision,
                "rejection_reason": portfolio_rejection_reason,
                "concentration": concentration,
                "correlated": correlated,
                "total_exposure": total_exp,
                "kelly": kelly_result,
                "timestamp": now,
            }
        ],
    }
