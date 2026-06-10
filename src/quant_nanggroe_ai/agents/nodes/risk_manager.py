"""
Risk Manager Agent — 9-checkpoint Constitutional VETO system.
==============================================================
FULL VETO authority.  Cannot be overridden by any other agent.
Integrates with ConstitutionalRiskGuard for the 9-checkpoint validation
and KillSwitch for emergency halts.

Responsibilities:
  - Run all 9 risk checkpoints via ConstitutionalRiskGuard
  - Return proper RiskClearance enum (not string)
  - Track daily/weekly PnL and update kill switch
  - Return risk_verdict, risk_checkpoints, risk_clearance
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from quant_nanggroe_ai.agents.state import AgentState
from quant_nanggroe_ai.engine.kill_switch import KillSwitch
from quant_nanggroe_ai.engine.risk_guard import ConstitutionalRiskGuard
from quant_nanggroe_ai.types import DecisionAction, MarketRegime, RiskClearance

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# Shared singleton instances (preserves state across graph invocations)
# ══════════════════════════════════════════════════════════════════════

_risk_guard: ConstitutionalRiskGuard | None = None
_kill_switch: KillSwitch | None = None


def _get_risk_guard() -> ConstitutionalRiskGuard:
    """Return a shared ConstitutionalRiskGuard instance."""
    global _risk_guard
    if _risk_guard is None:
        _risk_guard = ConstitutionalRiskGuard()
    return _risk_guard


def _get_kill_switch() -> KillSwitch:
    """Return a shared KillSwitch instance."""
    global _kill_switch
    if _kill_switch is None:
        _kill_switch = KillSwitch()
    return _kill_switch


def _map_signal_to_direction(signal: str) -> str:
    """Map strategy signal to valid trade direction for risk guard."""
    mapping = {
        "BUY": "BUY",
        "SELL": "SELL",
        "LONG": "LONG",
        "SHORT": "SHORT",
    }
    return mapping.get(signal.upper(), "BUY")


def _compute_daily_pnl_pct(guard: ConstitutionalRiskGuard, account_balance: float) -> float:
    """Compute daily PnL as a percentage of account balance."""
    if account_balance <= 0:
        return 0.0
    return guard.daily_pnl / account_balance


def _compute_weekly_pnl_pct(guard: ConstitutionalRiskGuard, account_balance: float) -> float:
    """Compute weekly PnL as a percentage of account balance."""
    if account_balance <= 0:
        return 0.0
    return guard.weekly_pnl / account_balance


def _check_regime_risk(regime: MarketRegime) -> dict[str, Any]:
    """
    Additional regime-based risk check beyond the 9 checkpoints.

    Certain regimes warrant extra caution even if all 9 checkpoints pass.
    """
    if regime in (MarketRegime.PANIC, MarketRegime.RISK_OFF, MarketRegime.NO_TRADE):
        return {
            "name": "regime_safety",
            "passed": False,
            "reason": f"Regime {regime.value} — trading prohibited by constitutional rule",
        }
    if regime == MarketRegime.VOLATILE:
        return {
            "name": "regime_safety",
            "passed": True,
            "reason": "VOLATILE regime — increased caution, reduced position size recommended",
        }
    return {
        "name": "regime_safety",
        "passed": True,
        "reason": f"Regime {regime.value} — trading permitted",
    }


def _check_decision_risk(action: DecisionAction) -> dict[str, Any]:
    """
    Check if the decision action from the strategist is tradeable.

    WATCH actions should not proceed to execution.
    """
    if action == DecisionAction.NO_TRADE:
        return {
            "name": "decision_action_check",
            "passed": False,
            "reason": "Decision action is NO_TRADE",
        }
    if "WATCH" in action.value:
        return {
            "name": "decision_action_check",
            "passed": False,
            "reason": f"Decision action {action.value} is a WATCH — no execution allowed",
        }
    return {
        "name": "decision_action_check",
        "passed": True,
        "reason": f"Decision action {action.value} allows execution",
    }


async def risk_manager_node(state: AgentState) -> dict[str, Any]:
    """
    Risk Engine Agent node — Full VETO authority.

    Runs the 9-checkpoint ConstitutionalRiskGuard validation,
    checks kill switch status, validates regime safety, and
    returns a RiskClearance enum.
    """
    symbol = state.symbol or "SPY"
    errors: list[str] = []
    now = datetime.now().isoformat()

    # ── 1. Get shared engine instances ─────────────────────────────────
    risk_guard = _get_risk_guard()
    kill_switch = _get_kill_switch()

    # ── 2. Early exit: check kill switch ───────────────────────────────
    if kill_switch.is_active:
        logger.critical("Kill switch is ACTIVE — all trading blocked")
        return {
            "risk_verdict": "VETOED",
            "risk_clearance": RiskClearance.BLOCKED,
            "risk_checkpoints": {
                "kill_switch": {
                    "name": "kill_switch",
                    "value": "ACTIVE",
                    "limit": "INACTIVE",
                    "passed": False,
                }
            },
            "daily_pnl_pct": state.daily_pnl_pct,
            "weekly_pnl_pct": state.weekly_pnl_pct,
            "errors": state.errors + ["Kill switch is active — trading halted"],
            "agent_trace": state.agent_trace + [
                {
                    "agent": "risk_manager",
                    "status": "completed",
                    "verdict": "VETOED",
                    "clearance": RiskClearance.BLOCKED.value,
                    "reason": "kill_switch_active",
                    "timestamp": now,
                }
            ],
        }

    # ── 3. Early exit: check decision action ───────────────────────────
    decision_check = _check_decision_risk(state.decision_action)
    if not decision_check["passed"]:
        return {
            "risk_verdict": "VETOED",
            "risk_clearance": RiskClearance.BLOCKED,
            "risk_checkpoints": {
                "decision_action": {
                    "name": "decision_action_check",
                    "value": state.decision_action.value,
                    "limit": "ALLOW_*",
                    "passed": False,
                }
            },
            "daily_pnl_pct": state.daily_pnl_pct,
            "weekly_pnl_pct": state.weekly_pnl_pct,
            "errors": state.errors + [decision_check["reason"]],
            "agent_trace": state.agent_trace + [
                {
                    "agent": "risk_manager",
                    "status": "completed",
                    "verdict": "VETOED",
                    "clearance": RiskClearance.BLOCKED.value,
                    "reason": decision_check["reason"],
                    "timestamp": now,
                }
            ],
        }

    # ── 4. Early exit: check regime safety ─────────────────────────────
    regime_check = _check_regime_risk(state.regime)
    if not regime_check["passed"]:
        return {
            "risk_verdict": "VETOED",
            "risk_clearance": RiskClearance.BLOCKED,
            "risk_checkpoints": {
                "regime_safety": {
                    "name": "regime_safety",
                    "value": state.regime.value,
                    "limit": "TRADEABLE_REGIME",
                    "passed": False,
                }
            },
            "daily_pnl_pct": state.daily_pnl_pct,
            "weekly_pnl_pct": state.weekly_pnl_pct,
            "errors": state.errors + [regime_check["reason"]],
            "agent_trace": state.agent_trace + [
                {
                    "agent": "risk_manager",
                    "status": "completed",
                    "verdict": "VETOED",
                    "clearance": RiskClearance.BLOCKED.value,
                    "reason": regime_check["reason"],
                    "timestamp": now,
                }
            ],
        }

    # ── 5. Run 9-checkpoint ConstitutionalRiskGuard ────────────────────
    direction = _map_signal_to_direction(state.strategy_signal)
    lot_size = state.position_size if state.position_size > 0 else 0.01
    stop_loss = state.stop_loss if state.stop_loss > 0 else None
    take_profit = state.take_profit[0] if state.take_profit else None

    try:
        result = risk_guard.check_trade(
            symbol=symbol,
            direction=direction,
            lot_size=lot_size,
            entry=state.entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
    except Exception as exc:
        logger.error("Risk guard check_trade failed: %s", exc)
        errors.append(f"Risk guard: {exc}")
        result = None

    # ── 6. Determine risk clearance ────────────────────────────────────
    if result is None:
        risk_verdict = "VETOED"
        risk_clearance = RiskClearance.BLOCKED
        checkpoints_dict: dict[str, Any] = {
            "error": {
                "name": "risk_guard_error",
                "value": "exception",
                "limit": "normal",
                "passed": False,
            }
        }
    else:
        risk_verdict = result.verdict  # "APPROVED" or "VETOED"
        risk_clearance = RiskClearance.CLEAR if result.verdict == "APPROVED" else RiskClearance.BLOCKED
        checkpoints_dict = {k: v.model_dump() for k, v in result.checkpoints.items()}

    # ── 7. Update kill switch auto-trigger check ───────────────────────
    account_balance = 10000.0  # Default; should come from portfolio
    daily_pnl_pct = _compute_daily_pnl_pct(risk_guard, account_balance)
    weekly_pnl_pct = _compute_weekly_pnl_pct(risk_guard, account_balance)

    try:
        kill_status = kill_switch.check_auto_trigger(daily_pnl_pct, weekly_pnl_pct)
        if kill_status.get("status") == "ACTIVATED":
            logger.critical("Kill switch auto-activated: %s", kill_status)
            risk_verdict = "VETOED"
            risk_clearance = RiskClearance.BLOCKED
            checkpoints_dict["kill_switch_auto"] = {
                "name": "kill_switch_auto",
                "value": "AUTO_ACTIVATED",
                "limit": "INACTIVE",
                "passed": False,
            }
    except Exception as exc:
        logger.error("Kill switch check failed: %s", exc)
        errors.append(f"Kill switch: {exc}")

    # ── 8. Log risk status summary ─────────────────────────────────────
    if risk_clearance == RiskClearance.CLEAR:
        logger.info(
            "Risk CLEARED for %s %s | verdict=%s | checkpoints=%d passed",
            symbol, direction, risk_verdict,
            sum(1 for v in checkpoints_dict.values() if v.get("passed", False)),
        )
    else:
        failed_checks = [k for k, v in checkpoints_dict.items() if not v.get("passed", False)]
        logger.warning(
            "Risk BLOCKED for %s %s | failed_checkpoints=%s",
            symbol, direction, failed_checks,
        )

    # ── Return state updates ────────────────────────────────────────────
    return {
        "risk_verdict": risk_verdict,
        "risk_clearance": risk_clearance,
        "risk_checkpoints": checkpoints_dict,
        "daily_pnl_pct": daily_pnl_pct,
        "weekly_pnl_pct": weekly_pnl_pct,
        "errors": state.errors + errors,
        "agent_trace": state.agent_trace + [
            {
                "agent": "risk_manager",
                "status": "completed",
                "verdict": risk_verdict,
                "clearance": risk_clearance.value,
                "direction": direction,
                "lot_size": lot_size,
                "timestamp": now,
            }
        ],
    }
