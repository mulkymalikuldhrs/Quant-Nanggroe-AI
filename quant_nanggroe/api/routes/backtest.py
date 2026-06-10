"""Backtest API routes."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter

from quant_nanggroe.api.schemas import (
    BacktestRequest,
    BacktestSubmissionResponse,
    BacktestResultResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory backtest storage (placeholder for database)
_backtests: dict[str, dict[str, Any]] = {}


@router.post("/run", response_model=BacktestSubmissionResponse)
async def submit_backtest(request: BacktestRequest) -> BacktestSubmissionResponse:
    """Submit a backtest for execution.

    Queues a backtest run with the specified strategy and parameters.

    Args:
        request: BacktestRequest with strategy configuration.

    Returns:
        BacktestSubmissionResponse with backtest ID and status.
    """
    backtest_id = str(uuid.uuid4())
    _backtests[backtest_id] = {
        "id": backtest_id,
        "status": "QUEUED",
        "symbol": request.symbol,
        "strategy": request.strategy,
        "request": request,
    }

    return BacktestSubmissionResponse(
        backtest_id=backtest_id,
        symbol=request.symbol,
        strategy=request.strategy,
    )


@router.get("/result/{backtest_id}", response_model=BacktestResultResponse)
async def get_backtest_result(backtest_id: str) -> BacktestResultResponse:
    """Get backtest results by ID.

    Args:
        backtest_id: Backtest identifier returned from submission.

    Returns:
        BacktestResultResponse with results or current status.
    """
    bt = _backtests.get(backtest_id)
    if not bt:
        return BacktestResultResponse(
            backtest_id=backtest_id,
            status="NOT_FOUND",
            symbol="",
            strategy="",
            error="Backtest not found",
        )

    return BacktestResultResponse(
        backtest_id=backtest_id,
        status=bt.get("status", "UNKNOWN"),
        symbol=bt["symbol"],
        strategy=bt["strategy"],
        total_return=bt.get("total_return", 0.0),
        sharpe_ratio=bt.get("sharpe_ratio", 0.0),
        max_drawdown=bt.get("max_drawdown", 0.0),
        win_rate=bt.get("win_rate", 0.0),
        total_trades=bt.get("total_trades", 0),
    )


@router.get("/list")
async def list_backtests() -> dict[str, Any]:
    """List all backtests.

    Returns:
        Dict with list of backtest summaries.
    """
    return {
        "backtests": [
            {
                "id": bt["id"],
                "status": bt.get("status", "UNKNOWN"),
                "symbol": bt["symbol"],
                "strategy": bt["strategy"],
            }
            for bt in _backtests.values()
        ],
        "total": len(_backtests),
    }
