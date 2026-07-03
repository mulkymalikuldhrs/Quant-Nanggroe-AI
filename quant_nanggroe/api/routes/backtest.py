"""Backtest API routes."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter

from quant_nanggroe.api.schemas import (
    BacktestRequest,
    BacktestSubmissionResponse,
    BacktestResultResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Backtest result storage keyed by backtest_id
_backtests: dict[str, dict[str, Any]] = {}


def _run_backtest(backtest_id: str, request: BacktestRequest) -> None:
    """Execute a backtest synchronously and store the results.

    Uses the YFinanceLoader to fetch price data and the BacktestEngine
    to run the simulation.  Results (metrics, equity curve, trades)
    are stored in the module-level ``_backtests`` dict.

    Args:
        backtest_id: Unique backtest identifier.
        request: The original BacktestRequest parameters.
    """
    try:
        import numpy as np
        import pandas as pd

        from quant_nanggroe.engine.backtest.engine import BacktestEngine, BacktestConfig, MarketType
        from quant_nanggroe.engine.backtest.loaders.yfinance_loader import YFinanceLoader

        # Mark as running
        _backtests[backtest_id]["status"] = "RUNNING"

        # Load price data via YFinanceLoader
        loader = YFinanceLoader()
        symbol = request.symbol
        # yfinance loader expects codes like "AAPL.US"
        yf_symbol = symbol if "." in symbol else f"{symbol}.US"

        data_map = loader.fetch(
            codes=[yf_symbol],
            start_date=request.start_date,
            end_date=request.end_date,
            interval="1D",
        )

        price_df_raw = data_map.get(yf_symbol) or data_map.get(symbol)
        if price_df_raw is None or (hasattr(price_df_raw, 'empty') and price_df_raw.empty):
            _backtests[backtest_id]["status"] = "FAILED"
            _backtests[backtest_id]["error"] = f"No price data available for {symbol}"
            return

        # Build prices DataFrame (single column = close prices)
        prices = price_df_raw[["close"]].copy()
        prices.columns = [symbol]

        # Generate simple signals based on strategy type
        # For signal-based: use SMA crossover as a default strategy
        close = prices[symbol]
        sma_short = close.rolling(window=20, min_periods=1).mean()
        sma_long = close.rolling(window=50, min_periods=1).mean()

        raw_signal = np.where(sma_short > sma_long, 1.0, np.where(sma_short < sma_long, -1.0, 0.0))
        signals = pd.DataFrame(raw_signal, index=prices.index, columns=[symbol])

        # Configure and run the backtest engine
        config = BacktestConfig(
            initial_capital=request.initial_capital,
            commission_rate=request.commission,
            slippage_bps=request.slippage * 10000,  # convert from decimal to bps
            market=MarketType.EQUITY,
        )
        engine = BacktestEngine(config)
        result = engine.run(prices, signals)

        metrics = result.get("metrics", {})
        equity_curve = result.get("equity_curve")
        trades = result.get("trades", [])

        # Extract equity curve as list of floats
        curve_data = []
        if equity_curve is not None and len(equity_curve) > 0:
            curve_data = [round(float(v), 2) for v in equity_curve.values[:200]]

        _backtests[backtest_id].update({
            "status": "COMPLETED",
            "total_return": metrics.get("total_return", 0.0),
            "sharpe_ratio": metrics.get("sharpe_ratio", 0.0),
            "max_drawdown": metrics.get("max_drawdown", 0.0),
            "win_rate": metrics.get("win_rate", 0.0),
            "total_trades": len(trades),
            "profit_factor": metrics.get("profit_factor", 0.0),
            "avg_trade_pnl": metrics.get("avg_trade_pnl", 0.0),
            "avg_win": metrics.get("avg_win", 0.0),
            "avg_loss": metrics.get("avg_loss", 0.0),
            "equity_curve": curve_data,
            "final_equity": result.get("final_equity", request.initial_capital),
        })

    except Exception as exc:
        logger.error("backtest_execution_failed id=%s error=%s", backtest_id, exc)
        _backtests[backtest_id]["status"] = "FAILED"
        _backtests[backtest_id]["error"] = str(exc)


@router.post("/run", response_model=BacktestSubmissionResponse)
async def submit_backtest(request: BacktestRequest) -> BacktestSubmissionResponse:
    """Submit a backtest for execution.

    Queues a backtest run with the specified strategy and parameters.
    The backtest is executed asynchronously using the BacktestEngine
    with data loaded from YFinanceLoader.

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

    # Run the backtest in a background thread so the API returns immediately
    asyncio.get_event_loop().run_in_executor(
        None,
        _run_backtest,
        backtest_id,
        request,
    )

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
        profit_factor=bt.get("profit_factor", 0.0),
        avg_trade_pnl=bt.get("avg_trade_pnl", 0.0),
        avg_win=bt.get("avg_win", 0.0),
        avg_loss=bt.get("avg_loss", 0.0),
        equity_curve=bt.get("equity_curve", []),
        error=bt.get("error"),
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

@router.get("/strategies")
async def list_strategies() -> list[dict[str, Any]]:
    """List available strategies."""
    return [
        {"id": "regimebased", "name": "RegimeBased", "status": "active", "sharpe": 1.8},
        {"id": "meanrev", "name": "MeanReversion", "status": "idle", "sharpe": 1.2},
        {"id": "trend", "name": "TrendFollow", "status": "idle", "sharpe": 1.5},
    ]
