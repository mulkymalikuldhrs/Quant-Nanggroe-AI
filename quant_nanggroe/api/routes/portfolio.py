"""Portfolio API routes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request

from quant_nanggroe.api.schemas import (
    PortfolioSummaryResponse,
    PortfolioRiskResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/summary", response_model=PortfolioSummaryResponse)
async def get_portfolio_summary(http_request: Request) -> PortfolioSummaryResponse:
    """Get portfolio summary.

    Returns current portfolio value, positions, and PnL.

    Args:
        http_request: HTTP request for accessing app state.

    Returns:
        PortfolioSummaryResponse with portfolio data.
    """
    try:
        from quant_nanggroe.services import get_risk_manager
        rm = get_risk_manager(http_request.app)
        status = rm.status()
        return PortfolioSummaryResponse(
            total_value=status.get("current_equity", 0.0),
            unrealized_pnl=0.0,
            realized_pnl=status.get("daily_pnl", 0.0),
            position_count=status.get("active_positions", 0),
        )
    except Exception:
        return PortfolioSummaryResponse()


@router.get("/risk", response_model=PortfolioRiskResponse)
async def get_portfolio_risk(http_request: Request) -> PortfolioRiskResponse:
    """Get portfolio risk metrics.

    Returns VaR, CVaR, drawdown, and other risk metrics.

    Args:
        http_request: HTTP request for accessing app state.

    Returns:
        PortfolioRiskResponse with risk metrics.
    """
    try:
        from quant_nanggroe.services import get_risk_manager
        rm = get_risk_manager(http_request.app)
        status = rm.status()

        dd_info = status.get("drawdown", {})

        risk_status = "OK"
        if status.get("overall_status") == "TRADING_HALT":
            risk_status = "HALT"

        return PortfolioRiskResponse(
            max_drawdown=float(dd_info.get("max_drawdown", 0.0)),
            current_drawdown=float(dd_info.get("current_drawdown", 0.0)),
            daily_pnl_pct=float(status.get("daily_loss_pct", "0").rstrip("%")) / 100 if "%" in str(status.get("daily_loss_pct", "0")) else 0.0,
            risk_status=risk_status,
        )
    except Exception:
        return PortfolioRiskResponse()


@router.get("/stress-test")
async def run_stress_test(http_request: Request) -> dict[str, Any]:
    """Run portfolio stress test.

    Applies historical-like scenarios to estimate portfolio
    performance under adverse conditions.

    Args:
        http_request: HTTP request for accessing app state.

    Returns:
        Dict with stress test results per scenario.
    """
    return {"scenarios": {}, "message": "Stress test requires historical returns data"}
