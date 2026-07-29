"""Unified risk guard — merges ConstitutionalRiskGuard + risk_guard_approve().

Imports limits from engine/risk/constants.py (SSOT — single source of truth).
Calls ConstitutionalRiskGuard.check_trade() first (hard constitutional limits).
Then runs risk scoring from tools/risk_guard.approve().
Output: VETOED if EITHER gate rejects (stricter of both wins).
Default: VETOED (fail-closed).
"""

from quant_nanggroe.engine.risk.checks import (
    ConstitutionalRiskGuard,
    PortfolioSnapshot,
    TradeAction,
    TradeRequest,
)
from quant_nanggroe.engine.risk.constants import MAX_WEEKLY_LOSS as _MAX_WEEKLY_LOSS
from quant_nanggroe.hedge_fund.utils.config import log

_CONSTITUTIONAL_GUARD = ConstitutionalRiskGuard()


def risk_guard_approve(proposal: dict) -> dict:
    """Unified risk guard approval: constitutional checks + risk scoring.

    Parameters
    ----------
    proposal : dict
        Trade proposal with keys: symbol, action, volume, price, sl,
        account_balance, daily_pnl, weekly_pnl, open_positions, market_volatility.

    Returns
    -------
    dict with keys: status, risk_score, reasons, warnings, constitutional, timestamp
    """
    merged_reasons: list[str] = []
    merged_warnings: list[str] = []

    # ── Phase 1: ConstitutionalRiskGuard (hard limits, fail-closed) ──────────
    symbol = proposal.get("symbol", "")
    action_raw = proposal.get("action", "buy")
    if action_raw.lower() in ("buy", "long"):
        action = TradeAction.BUY
    elif action_raw.lower() in ("sell", "short"):
        action = TradeAction.SELL
    else:
        action = TradeAction.HOLD

    volume = proposal.get("volume", 0.0)
    price = proposal.get("price", 0.0)
    sl = proposal.get("sl", 0.0)
    balance = proposal.get("account_balance", 0.0)
    daily_pnl = proposal.get("daily_pnl", 0.0)
    weekly_pnl = proposal.get("weekly_pnl", 0.0)

    # Heuristic from ConstitutionalRiskGuard.evaluate(): values < 30 are % already
    sl_pct = sl if sl < 30 else (abs(sl - price) / price * 100 if price > 0 else sl)

    req = TradeRequest(
        symbol=symbol,
        action=action,
        quantity=volume,
        price=price,
        stop_loss_pct=sl_pct,
    )
    pf = PortfolioSnapshot(
        total_equity=balance if balance > 0 else 100_000.0,
        daily_pnl=daily_pnl,
        weekly_pnl=weekly_pnl,
    )

    constitutional_result = _CONSTITUTIONAL_GUARD.check_trade(req, pf)
    merged_reasons.extend(constitutional_result.reasons)
    merged_warnings.extend(constitutional_result.warnings)

    if not constitutional_result.approved:
        return {
            "status": "VETOED",
            "risk_score": 1.0,
            "reasons": merged_reasons or ["constitutional_veto"],
            "warnings": merged_warnings,
            "constitutional": False,
            "threshold": 0.0,
            "timestamp": constitutional_result.timestamp.isoformat(),
        }

    # ── Phase 2: Risk scoring from tools/risk_guard.py ───────────────────────
    try:
        from quant_nanggroe.hedge_fund.tools.risk_guard import approve as rg_approve

        rg_result = rg_approve(proposal)
        risk_score = rg_result.get("risk_score", 0.0)
        rg_reasons: list[str] = rg_result.get("reasons", [])
        rg_status: str = rg_result.get("status", "VETOED")
        threshold: float = rg_result.get("threshold", 0.8)

        merged_reasons.extend(rg_reasons)

        # ── Weekly loss hard veto (canonical gate, independent of risk threshold) ──
        # Follows Path-A pattern (checks.py Check 4): hard veto, not soft risk-score bump.
        if weekly_pnl < 0 and balance > 0:
            weekly_loss_frac = abs(weekly_pnl) / balance
            if weekly_loss_frac >= _MAX_WEEKLY_LOSS:
                merged_reasons.append(
                    f"weekly_loss_veto: {weekly_loss_frac:.2%} >= {_MAX_WEEKLY_LOSS:.2%}"
                )
                return {
                    "status": "VETOED",
                    "risk_score": 1.0,
                    "reasons": merged_reasons,
                    "warnings": merged_warnings,
                    "constitutional": True,
                    "threshold": threshold,
                    "timestamp": str(rg_result.get("timestamp", "")),
                }

        if rg_status == "VETOED":
            return {
                "status": "VETOED",
                "risk_score": risk_score,
                "reasons": merged_reasons or ["risk_scoring_veto"],
                "warnings": merged_warnings,
                "constitutional": True,
                "threshold": threshold,
                "timestamp": str(rg_result.get("timestamp", "")),
            }
    except Exception as e:
        log.error("Risk scoring failed (fail-closed veto): %s", e)
        return {
            "status": "VETOED",
            "risk_score": 1.0,
            "reasons": merged_reasons + [f"risk_scoring_failed: {e}"],
            "warnings": merged_warnings,
            "constitutional": True,
            "threshold": 0.0,
            "timestamp": "",
        }

    # ── Both gates passed ────────────────────────────────────────────────────
    return {
        "status": "APPROVED",
        "risk_score": risk_score,
        "reasons": merged_reasons,
        "warnings": merged_warnings,
        "constitutional": True,
        "threshold": threshold,
        "timestamp": str(rg_result.get("timestamp", "")),
    }
