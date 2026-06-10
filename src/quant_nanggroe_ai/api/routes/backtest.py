"""
Backtest Routes — Submit, monitor, and retrieve backtest results
=================================================================
Integrates with BacktestEngine for real backtest execution,
with async job queue for long-running backtests.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException

from quant_nanggroe_ai.api.schemas import (
    BacktestRequest,
    BacktestResultResponse,
    BacktestSubmissionResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter()

# In-memory backtest job store (production would use database)
_backtest_jobs: dict[str, dict[str, Any]] = {}


async def _execute_backtest(job_id: str, config_dict: dict[str, Any]) -> None:
    """
    Execute a backtest in the background and update the job store.

    Args:
        job_id: Unique backtest job identifier.
        config_dict: BacktestConfig fields as a dict.
    """
    from quant_nanggroe_ai.backtest.engine import BacktestConfig, BacktestEngine

    _backtest_jobs[job_id]["status"] = "RUNNING"
    _backtest_jobs[job_id]["started_at"] = datetime.now().isoformat()

    try:
        config = BacktestConfig(
            symbol=config_dict["symbol"],
            strategy_name=config_dict["strategy"],
            start_date=datetime.fromisoformat(config_dict["start_date"]),
            end_date=datetime.fromisoformat(config_dict["end_date"]),
            initial_capital=config_dict.get("initial_capital", 10000.0),
            commission=config_dict.get("commission", 0.001),
            slippage=config_dict.get("slippage", 0.0005),
            position_sizing=config_dict.get("position_sizing", "fixed"),
        )

        engine = BacktestEngine()
        result = await engine.run(config)

        _backtest_jobs[job_id]["status"] = "COMPLETED"
        _backtest_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        _backtest_jobs[job_id]["result"] = {
            "total_return": result.total_return,
            "sharpe_ratio": result.sharpe_ratio,
            "max_drawdown": result.max_drawdown,
            "win_rate": result.win_rate,
            "total_trades": result.total_trades,
            "profit_factor": result.profit_factor,
            "avg_trade_pnl": result.avg_trade_pnl,
            "avg_win": result.avg_win,
            "avg_loss": result.avg_loss,
            "equity_curve": result.equity_curve,
        }

        logger.info(
            "backtest_completed",
            job_id=job_id,
            symbol=config.symbol,
            strategy=config.strategy_name,
            total_return=result.total_return,
        )

    except Exception as exc:
        _backtest_jobs[job_id]["status"] = "FAILED"
        _backtest_jobs[job_id]["error"] = str(exc)
        _backtest_jobs[job_id]["completed_at"] = datetime.now().isoformat()

        logger.error(
            "backtest_failed",
            job_id=job_id,
            symbol=config_dict.get("symbol", "unknown"),
            error=str(exc),
        )


# ══════════════════════════════════════════════════════════════════════
# Submit Backtest
# ══════════════════════════════════════════════════════════════════════

@router.post("/run", response_model=BacktestSubmissionResponse)
async def run_backtest(body: BacktestRequest) -> BacktestSubmissionResponse:
    """
    Submit a backtest job for execution.

    Creates a BacktestConfig and dispatches the BacktestEngine
    as a background task. Returns a job ID for status polling.
    """
    backtest_id = f"BT-{uuid.uuid4().hex[:8]}"

    _backtest_jobs[backtest_id] = {
        "id": backtest_id,
        "symbol": body.symbol,
        "strategy": body.strategy,
        "start_date": body.start_date,
        "end_date": body.end_date,
        "initial_capital": body.initial_capital,
        "status": "QUEUED",
        "submitted_at": datetime.now().isoformat(),
        "result": None,
        "error": None,
    }

    # Fire and forget — runs in background
    config_dict = {
        "symbol": body.symbol,
        "strategy": body.strategy,
        "start_date": body.start_date,
        "end_date": body.end_date,
        "initial_capital": body.initial_capital,
        "commission": body.commission,
        "slippage": body.slippage,
        "position_sizing": body.position_sizing,
    }
    asyncio.create_task(_execute_backtest(backtest_id, config_dict))

    logger.info(
        "backtest_submitted",
        backtest_id=backtest_id,
        symbol=body.symbol,
        strategy=body.strategy,
    )

    return BacktestSubmissionResponse(
        backtest_id=backtest_id,
        status="QUEUED",
        symbol=body.symbol,
        strategy=body.strategy,
        submitted_at=datetime.now(),
        message="Backtest queued for execution",
    )


# ══════════════════════════════════════════════════════════════════════
# Backtest Results
# ══════════════════════════════════════════════════════════════════════

@router.get("/results/{backtest_id}", response_model=BacktestResultResponse)
async def get_backtest_results(backtest_id: str) -> BacktestResultResponse:
    """
    Get backtest results by job ID.

    Returns the current status and results (if completed) for a
    previously submitted backtest job.
    """
    job = _backtest_jobs.get(backtest_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Backtest job '{backtest_id}' not found")

    result_data = job.get("result") or {}

    return BacktestResultResponse(
        backtest_id=job["id"],
        status=job["status"],
        symbol=job["symbol"],
        strategy=job["strategy"],
        total_return=result_data.get("total_return", 0.0),
        sharpe_ratio=result_data.get("sharpe_ratio", 0.0),
        max_drawdown=result_data.get("max_drawdown", 0.0),
        win_rate=result_data.get("win_rate", 0.0),
        total_trades=result_data.get("total_trades", 0),
        profit_factor=result_data.get("profit_factor", 0.0),
        avg_trade_pnl=result_data.get("avg_trade_pnl", 0.0),
        avg_win=result_data.get("avg_win", 0.0),
        avg_loss=result_data.get("avg_loss", 0.0),
        equity_curve=result_data.get("equity_curve", []),
        error=job.get("error"),
    )


# ══════════════════════════════════════════════════════════════════════
# List Backtests
# ══════════════════════════════════════════════════════════════════════

@router.get("/list")
async def list_backtests(limit: int = 20, status: str | None = None):
    """
    List recent backtest jobs.

    Args:
        limit: Maximum number of jobs to return (default 20).
        status: Optional filter by status (QUEUED, RUNNING, COMPLETED, FAILED).

    Returns:
        List of backtest job summaries.
    """
    jobs = list(_backtest_jobs.values())

    if status:
        jobs = [j for j in jobs if j["status"] == status]

    jobs = sorted(jobs, key=lambda j: j.get("submitted_at", ""), reverse=True)[:limit]

    return {
        "backtests": [
            {
                "id": j["id"],
                "symbol": j["symbol"],
                "strategy": j["strategy"],
                "status": j["status"],
                "submitted_at": j["submitted_at"],
            }
            for j in jobs
        ],
        "total_count": len(_backtest_jobs),
    }


# ══════════════════════════════════════════════════════════════════════
# Walk-Forward Analysis
# ══════════════════════════════════════════════════════════════════════

@router.post("/walk-forward")
async def run_walk_forward_analysis(
    symbol: str,
    strategy: str,
    start_date: str,
    end_date: str,
    train_window: int = 252,
    test_window: int = 63,
):
    """
    Submit a walk-forward analysis job.

    Splits the data into rolling train/test windows to measure
    out-of-sample performance degradation.
    """
    job_id = f"WF-{uuid.uuid4().hex[:8]}"

    _backtest_jobs[job_id] = {
        "id": job_id,
        "symbol": symbol,
        "strategy": strategy,
        "start_date": start_date,
        "end_date": end_date,
        "status": "QUEUED",
        "submitted_at": datetime.now().isoformat(),
        "result": None,
        "error": None,
        "type": "walk_forward",
    }

    async def _run_wf():
        from quant_nanggroe_ai.backtest.walk_forward import (
            WalkForwardConfig,
            run_walk_forward,
        )

        _backtest_jobs[job_id]["status"] = "RUNNING"
        try:
            config = WalkForwardConfig(
                train_window=train_window,
                test_window=test_window,
            )
            # Placeholder returns — actual data would be fetched from DB
            result = await run_walk_forward(returns=[], config=config)
            _backtest_jobs[job_id]["status"] = "COMPLETED"
            _backtest_jobs[job_id]["result"] = result.model_dump()
        except Exception as exc:
            _backtest_jobs[job_id]["status"] = "FAILED"
            _backtest_jobs[job_id]["error"] = str(exc)

    asyncio.create_task(_run_wf())

    return {
        "job_id": job_id,
        "status": "QUEUED",
        "message": "Walk-forward analysis queued for execution",
    }


# ══════════════════════════════════════════════════════════════════════
# Performance Metrics
# ══════════════════════════════════════════════════════════════════════

@router.post("/metrics")
async def calculate_metrics(returns: list[float], benchmark: list[float] | None = None):
    """
    Calculate performance metrics from a returns series.

    Computes Sharpe, Sortino, max drawdown, win rate, profit factor, etc.
    """
    from quant_nanggroe_ai.backtest.metrics import calculate_metrics

    return calculate_metrics(returns, benchmark)
