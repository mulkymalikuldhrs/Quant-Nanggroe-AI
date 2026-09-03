"""Performance Analytics — API routes (ffn-style)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


class MetricsRequest(BaseModel):
    returns: list[float]
    risk_free_rate: float = 0.05
    benchmark_returns: list[float] | None = None


class ComparisonRequest(BaseModel):
    returns_a: list[float]
    returns_b: list[float]
    name_a: str = "Strategy A"
    name_b: str = "Strategy B"


# DEPRECATED (v8.1.0 triage): no dashboard callers — see docs/DEAD_API.md
@router.post("/metrics")
async def compute_metrics(req: MetricsRequest) -> dict[str, Any]:
    """Compute performance metrics from return series."""
    try:
        from quant_nanggroe.engine.analytics import PerformanceMetrics

        pm = PerformanceMetrics(returns=req.returns, rfr=req.risk_free_rate)
        result = pm.all_metrics()
        if req.benchmark_returns:
            from quant_nanggroe.engine.analytics import performance_attribution

            result["attribution"] = performance_attribution(
                req.returns, req.benchmark_returns, req.risk_free_rate
            )
        return {
            "status": "success",
            "metrics": result,
            "n_observations": len(req.returns),
            "module": "analytics",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# DEPRECATED (v8.1.0 triage): no dashboard callers — see docs/DEAD_API.md
@router.post("/compare")
async def compare_strategies(req: ComparisonRequest) -> dict[str, Any]:
    """Compare two strategy return series."""
    try:
        from quant_nanggroe.engine.analytics import PerformanceMetrics

        pm_a = PerformanceMetrics(returns=req.returns_a)
        pm_b = PerformanceMetrics(returns=req.returns_b)
        metrics_a = pm_a.all_metrics()
        metrics_b = pm_b.all_metrics()

        return {
            "status": "success",
            "comparison": {
                req.name_a: metrics_a,
                req.name_b: metrics_b,
                "winner": req.name_a
                if metrics_a.get("sharpe_ratio", 0) > metrics_b.get("sharpe_ratio", 0)
                else req.name_b,
            },
            "module": "analytics",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# DEPRECATED (v8.1.0 triage): no dashboard callers — see docs/DEAD_API.md
@router.get("/metrics-list")
async def list_available_metrics() -> dict[str, Any]:
    """List all available metrics calculators."""
    return {
        "metrics": [
            {"name": "sharpe_ratio", "description": "Risk-adjusted return (annualized)"},
            {"name": "sortino_ratio", "description": "Downside risk-adjusted return"},
            {"name": "calmar_ratio", "description": "Return over max drawdown"},
            {"name": "max_drawdown", "description": "Maximum peak-to-trough decline"},
            {"name": "annualized_return", "description": "Geometric annualized return"},
            {"name": "annualized_volatility", "description": "Annualized standard deviation"},
            {"name": "win_rate", "description": "Fraction of positive periods"},
            {"name": "profit_factor", "description": "Gross profit / gross loss"},
            {"name": "kelly_criterion", "description": "Optimal bet size"},
            {"name": "var_history", "description": "Historical Value at Risk"},
            {"name": "cvar", "description": "Conditional VaR (expected shortfall)"},
            {"name": "rolling_sharpe", "description": "Rolling 12m Sharpe ratio"},
            {"name": "rolling_volatility", "description": "Rolling 12m volatility"},
            {"name": "drawdown_analysis", "description": "Drawdown duration & severity"},
            {"name": "skewness", "description": "Return distribution skew"},
            {"name": "kurtosis", "description": "Return distribution kurtosis"},
            {"name": "tail_ratio", "description": "95th/5th percentile ratio"},
        ],
        "module": "analytics",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
