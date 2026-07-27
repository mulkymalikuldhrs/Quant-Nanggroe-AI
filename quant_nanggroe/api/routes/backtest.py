"""Backtest API routes."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from typing import Any

from fastapi import APIRouter

from quant_nanggroe.api.schemas import (
    BacktestRequest,
    BacktestResultResponse,
    BacktestSubmissionResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Backtest result storage keyed by backtest_id
_backtests: dict[str, dict[str, Any]] = {}

# Persistent backtest state file
_BACKTEST_STATE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "paper_state", "backtests.jsonl",
)


def _load_backtests() -> None:
    """Restore in-memory backtest state from the JSONL file on module load."""
    if not os.path.exists(_BACKTEST_STATE):
        return
    try:
        with open(_BACKTEST_STATE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                bt_id = record.get("id")
                if bt_id:
                    _backtests[bt_id] = record
    except Exception as exc:
        logger.warning("Failed to load backtest state: %s", exc)


def _persist_backtest(backtest_id: str) -> None:
    """Append a backtest record to the JSONL file."""
    record = _backtests.get(backtest_id)
    if record is None:
        return
    try:
        os.makedirs(os.path.dirname(_BACKTEST_STATE), exist_ok=True)
        # Remove non-serializable request object before persisting
        clean = {k: v for k, v in record.items() if k != "request"}
        with open(_BACKTEST_STATE, "a", encoding="utf-8") as f:
            f.write(json.dumps(clean, default=str) + "\n")
    except Exception as exc:
        logger.warning("Failed to persist backtest %s: %s", backtest_id, exc)


# Load existing state on import
_load_backtests()


def _run_backtest(backtest_id: str, request: BacktestRequest) -> None:
    """Execute a backtest synchronously and store the results.

    Uses the YFinanceLoader to fetch price data and the BacktestEngine
    to run the simulation.  Results (metrics, equity curve, trades)
    are stored in the module-level ``_backtests`` dict and persisted
    to a JSONL file.

    Args:
        backtest_id: Unique backtest identifier.
        request: The original BacktestRequest parameters.
    """
    try:
        import numpy as np
        import pandas as pd

        from quant_nanggroe.engine.backtest.engine import BacktestConfig, BacktestEngine, MarketType
        from quant_nanggroe.engine.backtest.loaders.yfinance_loader import YFinanceLoader
        from quant_nanggroe.engine.strategies import create_strategy

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
            _persist_backtest(backtest_id)
            return

        # Build prices DataFrame (single column = close prices)
        prices = price_df_raw[["close"]].copy()
        prices.columns = [symbol]

        # Generate signals using the selected strategy from the registry
        close = prices[symbol]
        strategy_name = request.strategy

        try:
            strategy = create_strategy(strategy_name)
            warmup = strategy.warmup_period() if hasattr(strategy, "warmup_period") else 0

            # Build OHLCV DataFrame for the strategy
            ohlcv = pd.DataFrame({
                "open": price_df_raw["open"] if "open" in price_df_raw.columns else close,
                "high": price_df_raw["high"] if "high" in price_df_raw.columns else close,
                "low": price_df_raw["low"] if "low" in price_df_raw.columns else close,
                "close": close,
                "volume": price_df_raw["volume"] if "volume" in price_df_raw.columns else pd.Series(1e6, index=close.index),
            })

            raw_signal = np.zeros(len(close))
            from quant_nanggroe.types.signals import Signal, SignalType

            for i in range(warmup, len(ohlcv)):
                window = ohlcv.iloc[: i + 1]
                sig = strategy.generate_signal(window)
                if sig is not None and isinstance(sig, Signal):
                    if sig.signal_type == SignalType.BUY:
                        raw_signal[i] = 1.0
                    elif sig.signal_type == SignalType.SELL:
                        raw_signal[i] = -1.0
                    else:
                        raw_signal[i] = 0.0
                else:
                    raw_signal[i] = 0.0

            signals = pd.DataFrame(raw_signal, index=prices.index, columns=[symbol])
        except Exception as strat_exc:
            logger.warning("Strategy '%s' failed (%s), falling back to SMA crossover", strategy_name, strat_exc)
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
        _persist_backtest(backtest_id)

    except Exception as exc:
        logger.error("backtest_execution_failed id=%s error=%s", backtest_id, exc)
        _backtests[backtest_id]["status"] = "FAILED"
        _backtests[backtest_id]["error"] = str(exc)
        _persist_backtest(backtest_id)


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
    _persist_backtest(backtest_id)

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
    """List available strategies from the live registry."""
    from quant_nanggroe.api.routes.strategies import get_strategy_metadata
    from quant_nanggroe.engine.strategies import create_strategy
    from quant_nanggroe.engine.strategies import list_strategies as _list

    result = []
    for name in _list():
        meta = get_strategy_metadata(name)
        # Try to get default sharpe from strategy's backtest results if available
        try:
            s = create_strategy(name)
            required = s.required_columns() if hasattr(s, "required_columns") else []
        except Exception:
            required = []
        result.append({
            "id": name.replace("_", ""),
            "name": name.replace("_", " ").title(),
            "status": "idle",
            "sharpe": 0.0,
            "category": meta.get("category", ""),
            "asset_classes": meta.get("asset_classes", []),
            "required_columns": required,
        })
    return result
