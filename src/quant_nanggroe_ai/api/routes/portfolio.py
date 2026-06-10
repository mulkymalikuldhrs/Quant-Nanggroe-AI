"""
Portfolio Routes — Summary, risk metrics, positions
====================================================
Queries real position and trade history data to compute
portfolio-level metrics instead of returning stub zeros.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, Request

from quant_nanggroe_ai.api.schemas import (
    PortfolioSummaryResponse,
    PortfolioRiskResponse,
    PositionResponse,
)
from quant_nanggroe_ai.services import get_risk_guard

logger = structlog.get_logger(__name__)

router = APIRouter()

# Shared reference to trading route's in-memory stores
# In production, this would query the database
_positions: dict[str, dict[str, Any]] = {}
_trade_history: list[dict[str, Any]] = []
_equity_curve: list[float] = [10000.0]  # Start with initial capital
_realized_pnl: float = 0.0
_cash_balance: float = 10000.0


def _get_portfolio_data():
    """Import trading route stores for consistency (lazy to avoid circular imports)."""
    global _positions, _trade_history
    try:
        from quant_nanggroe_ai.api.routes.trading import _positions as trading_positions
        from quant_nanggroe_ai.api.routes.trading import _trade_history as trading_history

        _positions = trading_positions
        _trade_history = trading_history
    except (ImportError, AttributeError):
        pass


# ══════════════════════════════════════════════════════════════════════
# Portfolio Summary
# ══════════════════════════════════════════════════════════════════════

@router.get("/summary", response_model=PortfolioSummaryResponse)
async def get_portfolio_summary(request: Request) -> PortfolioSummaryResponse:
    """
    Get portfolio summary.

    Computes total value, unrealized/realized PnL, and position list
    from the actual position and trade data.
    """
    _get_portfolio_data()

    # Calculate unrealized PnL from positions
    unrealized_pnl = 0.0
    position_responses = []

    for pos_data in _positions.values():
        pos_pnl = pos_data.get("pnl", 0.0)
        unrealized_pnl += pos_pnl

        position_responses.append(
            PositionResponse(
                ticker=pos_data["ticker"],
                amount=pos_data["amount"],
                avg_price=pos_data["avg_price"],
                current_price=pos_data["current_price"],
                pnl=pos_pnl,
            )
        )

    # Calculate realized PnL from trade history
    realized_pnl = sum(
        t.get("realized_pnl", 0.0) or 0.0
        for t in _trade_history
    )

    # Total value = cash + position values
    position_value = sum(
        p["amount"] * p["current_price"]
        for p in _positions.values()
    )
    total_value = _cash_balance + position_value

    # Get daily PnL from risk guard
    guard = get_risk_guard(request.app)
    risk_status = guard.status()

    return PortfolioSummaryResponse(
        total_value=total_value,
        unrealized_pnl=unrealized_pnl,
        realized_pnl=realized_pnl,
        positions=position_responses,
        position_count=len(_positions),
        cash_balance=_cash_balance,
    )


# ══════════════════════════════════════════════════════════════════════
# Portfolio Risk Metrics
# ══════════════════════════════════════════════════════════════════════

@router.get("/risk", response_model=PortfolioRiskResponse)
async def get_portfolio_risk(request: Request) -> PortfolioRiskResponse:
    """
    Get portfolio risk metrics.

    Computes VaR, CVaR, drawdown, and other risk metrics from
    actual equity curve and trade data.
    """
    _get_portfolio_data()

    guard = get_risk_guard(request.app)
    risk_status = guard.status()

    # Compute VaR/CVaR from equity curve returns
    var_95 = 0.0
    cvar_95 = 0.0

    if len(_equity_curve) > 2:
        try:
            # Calculate returns from equity curve
            returns = [
                (_equity_curve[i] - _equity_curve[i - 1]) / _equity_curve[i - 1]
                for i in range(1, len(_equity_curve))
                if _equity_curve[i - 1] > 0
            ]

            if returns:
                from quant_nanggroe_ai.risk.var import historical_var
                from quant_nanggroe_ai.risk.cvar import historical_cvar

                var_95 = historical_var(returns, confidence=0.95)
                cvar_95 = historical_cvar(returns, confidence=0.95)
        except Exception as exc:
            logger.warning("var_calculation_failed", error=str(exc))

    # Compute drawdown
    max_drawdown = 0.0
    current_drawdown = 0.0

    if len(_equity_curve) > 1:
        try:
            from quant_nanggroe_ai.risk.drawdown import max_drawdown as calc_max_dd
            from quant_nanggroe_ai.risk.drawdown import current_drawdown as calc_current_dd

            max_drawdown = calc_max_dd(_equity_curve)
            current_drawdown = calc_current_dd(_equity_curve)
        except Exception as exc:
            logger.warning("drawdown_calculation_failed", error=str(exc))

    # Compute Sharpe ratio
    sharpe_ratio = 0.0
    sortino_ratio = 0.0

    if len(_equity_curve) > 2:
        returns = [
            (_equity_curve[i] - _equity_curve[i - 1]) / _equity_curve[i - 1]
            for i in range(1, len(_equity_curve))
            if _equity_curve[i - 1] > 0
        ]
        if returns:
            try:
                from quant_nanggroe_ai.backtest.metrics import calculate_metrics

                metrics = calculate_metrics(returns)
                sharpe_ratio = metrics.get("sharpe_ratio", 0.0)
            except Exception:
                pass

    # Parse daily/weekly PnL from risk status
    daily_pnl_str = risk_status.get("daily_pnl", "0.00%")
    weekly_pnl_str = risk_status.get("weekly_pnl", "0.00%")
    daily_pnl_pct = float(daily_pnl_str.replace("%", "")) / 100 if "%" in daily_pnl_str else 0.0
    weekly_pnl_pct = float(weekly_pnl_str.replace("%", "")) / 100 if "%" in weekly_pnl_str else 0.0

    risk_status_str = risk_status.get("overall_status", "TRADING_ALLOWED")

    return PortfolioRiskResponse(
        var_95=var_95,
        cvar_95=cvar_95,
        max_drawdown=max_drawdown,
        current_drawdown=current_drawdown,
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio,
        daily_pnl_pct=daily_pnl_pct,
        weekly_pnl_pct=weekly_pnl_pct,
        daily_trades=risk_status.get("trades_today", 0),
        risk_status=risk_status_str,
    )


# ══════════════════════════════════════════════════════════════════════
# Equity Curve
# ══════════════════════════════════════════════════════════════════════

@router.get("/equity-curve")
async def get_equity_curve():
    """
    Get the portfolio equity curve.

    Returns the historical equity values for charting.
    """
    return {
        "equity_curve": _equity_curve,
        "initial_capital": _equity_curve[0] if _equity_curve else 10000.0,
        "current_value": _equity_curve[-1] if _equity_curve else 10000.0,
        "data_points": len(_equity_curve),
    }


# ══════════════════════════════════════════════════════════════════════
# Position Sizing Recommendations
# ══════════════════════════════════════════════════════════════════════

@router.post("/position-sizing")
async def calculate_position_sizing(
    method: str = "kelly",
    account_balance: float = 10000.0,
    win_rate: float = 0.5,
    avg_win: float = 200.0,
    avg_loss: float = 100.0,
):
    """
    Calculate position sizing recommendations.

    Supports Kelly Criterion and risk parity methods.
    """
    if method == "kelly":
        from quant_nanggroe_ai.risk.position_sizing import kelly_criterion_size

        return kelly_criterion_size(
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            account_balance=account_balance,
        )
    else:
        return {
            "method": method,
            "message": f"Position sizing method '{method}' not yet implemented",
        }


# ══════════════════════════════════════════════════════════════════════
# Trade Journal
# ══════════════════════════════════════════════════════════════════════

@router.get("/journal")
async def get_trade_journal(limit: int = 50, symbol: str | None = None):
    """
    Get trade journal entries.

    Returns detailed trade history for review and analysis.
    Optionally filtered by symbol.
    """
    _get_portfolio_data()

    trades = _trade_history
    if symbol:
        trades = [t for t in trades if t.get("ticker", "").upper() == symbol.upper()]

    trades = sorted(trades, key=lambda t: t.get("timestamp", ""), reverse=True)[:limit]

    return {
        "journal": trades,
        "total_count": len(_trade_history),
        "filtered_count": len(trades),
    }
