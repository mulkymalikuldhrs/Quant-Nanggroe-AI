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
                "volume": (
                    price_df_raw["volume"] if "volume" in price_df_raw.columns
                    else pd.Series(1e6, index=close.index)
                ),
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
    """List available strategies from the live registry.

    Includes walk-forward validation status when WalkForwardRegistry
    has results for a strategy.
    """
    from quant_nanggroe.api.routes.strategies import get_strategy_metadata
    from quant_nanggroe.engine.strategies import create_strategy
    from quant_nanggroe.engine.strategies import list_strategies as _list

    # Lazy-load WalkForwardRegistry for validation status
    wf_registry = None
    try:
        from quant_nanggroe.engine.strategy.registry import WalkForwardRegistry
        wf_registry = WalkForwardRegistry()
    except Exception:
        pass

    result = []
    for name in _list():
        meta = get_strategy_metadata(name)
        try:
            s = create_strategy(name)
            required = s.required_columns() if hasattr(s, "required_columns") else []
        except Exception:
            required = []

        # Walk-forward validation status
        wf_status: dict[str, Any] = {"validated": False, "oos_sharpe": None, "decayed": False}
        if wf_registry is not None:
            wf_meta = wf_registry.get(name)
            if wf_meta is not None and wf_meta.oos_sharpes:
                avg_oos = sum(wf_meta.oos_sharpes) / len(wf_meta.oos_sharpes)
                wf_status = {
                    "validated": True,
                    "oos_sharpe": round(avg_oos, 4),
                    "n_windows": len(wf_meta.oos_sharpes),
                    "decayed": wf_registry.decayed(name),
                }

        result.append({
            "id": name.replace("_", ""),
            "name": name.replace("_", " ").title(),
            "status": "idle",
            "sharpe": 0.0,
            "category": meta.get("category", ""),
            "asset_classes": meta.get("asset_classes", []),
            "required_columns": required,
            "walk_forward": wf_status,
        })
    return result


# ── Walk-Forward Analysis Endpoint ────────────────────────────────────────


@router.post("/walk-forward")
async def run_walk_forward(body: dict[str, Any]) -> dict[str, Any]:
    """Run walk-forward analysis on a strategy with real data.

    Body params:
        strategy: Strategy name (required)
        symbol: Symbol to test on (default: BTC-USD)
        period: Data period (default: 6mo)
        train_window: Training window in bars (default: 120)
        test_window: Test window in bars (default: 60)
        mode: Walk-forward mode: rolling|anchored|cpcv (default: cpcv)
    """
    try:
        import pandas as pd
        import yfinance as yf

        from quant_nanggroe.engine.backtest.engine import BacktestConfig, BacktestEngine
        from quant_nanggroe.engine.backtest.walk_forward import WalkForwardAnalyzer
        from quant_nanggroe.engine.strategies import create_strategy

        strategy_name = body.get("strategy")
        if not strategy_name:
            return {"error": "strategy parameter required"}

        symbol = body.get("symbol", "BTC-USD")
        period = body.get("period", "6mo")
        train_window = int(body.get("train_window", 120))
        test_window = int(body.get("test_window", 60))
        mode = body.get("mode", "cpcv")

        # Fetch data
        ticker_map = {
            "BTC-USD": "BTC-USD", "ETH-USD": "ETH-USD",
            "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X",
        }
        yf_sym = ticker_map.get(symbol, symbol)
        df = yf.Ticker(yf_sym).history(period=period)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]

        if len(df) < train_window + test_window + 20:
            return {
                "error": f"Insufficient data: {len(df)} bars < {train_window + test_window + 20} required",
                "symbol": symbol,
                "strategy": strategy_name,
            }

        # Create strategy instance
        strategy = create_strategy(strategy_name)
        if strategy is None:
            return {"error": f"Strategy '{strategy_name}' not found"}

        # Infer bars_per_year from data spacing
        med_delta = df.index.to_series().diff().median()
        if med_delta is not None and med_delta.total_seconds() > 0:
            bars_per_year = int(pd.Timedelta(days=365) / med_delta)
        else:
            bars_per_year = 252

        # Configure engine
        engine = BacktestEngine(BacktestConfig(
            initial_capital=10000.0,
            commission_rate=0.001,
            slippage_bps=5.0,
            bars_per_year=bars_per_year,
        ))

        # Run walk-forward with per-fold strategy re-fitting
        analyzer = WalkForwardAnalyzer(
            engine=engine,
            train_window=train_window,
            test_window=test_window,
            mode=mode,
            purge_gap=5,
            embargo=3,
        )

        wf_result = analyzer.analyze_strategy(
            prices=df,
            strategy_class=type(strategy),
            strategy_params={},
        )

        # Format results
        windows = wf_result.get("windows", [])
        aggregate = wf_result.get("aggregate", {})
        stability = wf_result.get("stability")

        return {
            "strategy": strategy_name,
            "symbol": symbol,
            "mode": mode,
            "n_folds": len(windows),
            "aggregate": aggregate,
            "stability": {
                "sharpe_stability": stability.sharpe_stability if stability else 0.0,
                "return_stability": stability.return_stability if stability else 0.0,
                "sharpe_positive_rate": stability.sharpe_positive_rate if stability else 0.0,
                "effective_tests": stability.effective_tests if stability else 0,
            } if stability else {},
            "windows": [
                {
                    "fold": i + 1,
                    "train_period": f"{w.train_start.date()} → {w.train_end.date()}",
                    "test_period": f"{w.test_start.date()} → {w.test_end.date()}",
                    "is_sharpe": round(w.in_sample_sharpe, 4),
                    "oos_sharpe": round(w.out_of_sample_sharpe, 4),
                    "is_return": round(w.in_sample_return, 4),
                    "oos_return": round(w.out_of_sample_return, 4),
                    "degradation": round(w.degradation_ratio, 4),
                    "oos_trades": w.oos_trades,
                }
                for i, w in enumerate(windows)
            ],
            "status": "completed",
        }
    except Exception as exc:
        logger.error("walk_forward_failed: %s", exc)
        return {"error": str(exc), "status": "failed"}


# ── Parameter Tuning Endpoint ─────────────────────────────────────────────


@router.post("/tune")
async def tune_strategy(body: dict[str, Any]) -> dict[str, Any]:
    """Auto-tune strategy parameters using grid search + walk-forward validation.

    Body params:
        strategy: Strategy name (required)
        symbol: Symbol to test on (default: BTC-USD)
        period: Data period (default: 1y)
        param_grid: Dict of param_name -> [values] to search
        top_n: Return top N results (default: 5)
        n_windows: Walk-forward windows (default: 4)
    """
    try:
        import pandas as pd
        import yfinance as yf

        from quant_nanggroe.engine.backtest.auto_tune import AutoTuner, ParameterGrid

        strategy_name = body.get("strategy")
        if not strategy_name:
            return {"error": "strategy parameter required"}

        param_grid = body.get("param_grid")
        if not param_grid:
            return {"error": "param_grid parameter required (e.g. {'fast_period': [10, 20, 30]})"}

        symbol = body.get("symbol", "BTC-USD")
        period = body.get("period", "1y")
        top_n = int(body.get("top_n", 5))
        n_windows = int(body.get("n_windows", 4))

        # Fetch data
        ticker_map = {
            "BTC-USD": "BTC-USD", "ETH-USD": "ETH-USD",
            "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X",
        }
        yf_sym = ticker_map.get(symbol, symbol)
        df = yf.Ticker(yf_sym).history(period=period)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]

        if len(df) < 100:
            return {"error": f"Insufficient data: {len(df)} bars < 100 required"}

        # Run auto-tuning
        tuner = AutoTuner(
            strategy_name=strategy_name,
            param_grid=ParameterGrid(param_grid),
            data=df,
            n_windows=n_windows,
        )
        results = tuner.tune(top_n=top_n, verbose=False)

        return {
            "strategy": strategy_name,
            "symbol": symbol,
            "n_combinations_tested": len(results),
            "top_results": [
                {
                    "rank": i + 1,
                    "params": r.params,
                    "sharpe": round(r.sharpe, 4),
                    "total_return": round(r.total_return, 4),
                    "num_trades": r.num_trades,
                }
                for i, r in enumerate(results)
            ],
            "status": "completed",
        }
    except Exception as exc:
        import traceback as _tb
        logger.error("tune_failed: %s\n%s", exc, _tb.format_exc())
        return {"error": str(exc), "status": "failed", "traceback": _tb.format_exc()[-1500:]}


# ── Batch Walk-Forward for All Strategies ─────────────────────────────────


@router.post("/walk-forward/batch")
async def batch_walk_forward(body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run walk-forward validation on all registered strategies.

    Body params (optional):
        symbol: Symbol to test on (default: BTC-USD)
        period: Data period (default: 6mo)
        max_strategies: Limit number of strategies (default: 50)
    """
    try:
        import pandas as pd
        import yfinance as yf

        from quant_nanggroe.engine.backtest.engine import BacktestConfig, BacktestEngine
        from quant_nanggroe.engine.backtest.walk_forward import WalkForwardAnalyzer
        from quant_nanggroe.engine.strategies import create_strategy, list_strategies
        from quant_nanggroe.engine.strategy.registry import WalkForwardRegistry

        body = body or {}
        symbol = body.get("symbol", "BTC-USD")
        period = body.get("period", "6mo")
        max_strategies = int(body.get("max_strategies", 50))

        # Fetch data once
        ticker_map = {
            "BTC-USD": "BTC-USD", "ETH-USD": "ETH-USD",
            "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X",
        }
        yf_sym = ticker_map.get(symbol, symbol)
        df = yf.Ticker(yf_sym).history(period=period)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]

        if len(df) < 200:
            return {"error": f"Insufficient data: {len(df)} bars < 200 required"}

        # Infer bars_per_year
        med_delta = df.index.to_series().diff().median()
        if med_delta is not None and med_delta.total_seconds() > 0:
            bars_per_year = int(pd.Timedelta(days=365) / med_delta)
        else:
            bars_per_year = 252

        engine = BacktestEngine(BacktestConfig(
            initial_capital=10000.0,
            commission_rate=0.001,
            slippage_bps=5.0,
            bars_per_year=bars_per_year,
        ))

        wf_registry = WalkForwardRegistry()
        all_names = list_strategies()[:max_strategies]

        results = []
        for name in all_names:
            try:
                strategy = create_strategy(name)
                if strategy is None:
                    continue

                analyzer = WalkForwardAnalyzer(
                    engine=engine,
                    train_window=max(120, int(len(df) * 0.6)),
                    test_window=max(60, int(len(df) * 0.2)),
                    mode="rolling",
                    purge_gap=5,
                    embargo=3,
                )

                wf_result = analyzer.analyze_strategy(
                    prices=df,
                    strategy_class=type(strategy),
                    strategy_params={},
                )

                aggregate = wf_result.get("aggregate", {})
                oos_sharpe = aggregate.get("avg_oos_sharpe", 0.0)
                oos_return = aggregate.get("avg_oos_return", 0.0)
                n_folds = len(wf_result.get("windows", []))

                # Record in WalkForwardRegistry
                try:
                    from quant_nanggroe.engine.strategy.registry import WalkForwardResult as WFResult
                    wf_registry.register(name)
                    wf_reg_result = WFResult(
                        window_index=0,
                        train_sharpe=aggregate.get("avg_is_sharpe", 0.0),
                        test_sharpe=oos_sharpe,
                        train_return=aggregate.get("avg_is_return", 0.0),
                        test_return=oos_return,
                        train_max_dd=aggregate.get("avg_is_max_dd", 0.0),
                        test_max_dd=aggregate.get("avg_oos_max_dd", 0.0),
                    )
                    wf_registry.record_walk_forward(name, wf_reg_result)
                except Exception:
                    pass

                results.append({
                    "strategy": name,
                    "n_folds": n_folds,
                    "oos_sharpe": round(oos_sharpe, 4),
                    "oos_return": round(oos_return, 4),
                    "status": "validated" if n_folds > 0 else "no_folds",
                })
            except Exception as exc:
                results.append({
                    "strategy": name,
                    "status": "error",
                    "error": str(exc),
                })

        # Sort by OOS Sharpe descending
        results.sort(key=lambda x: x.get("oos_sharpe", 0.0), reverse=True)

        return {
            "symbol": symbol,
            "n_strategies_tested": len(results),
            "results": results,
            "status": "completed",
        }
    except Exception as exc:
        logger.error("batch_walk_forward_failed: %s", exc)
        return {"error": str(exc), "status": "failed"}


# ── Walk-Forward Status Endpoint ──────────────────────────────────────────


@router.get("/walk-forward/status")
async def walk_forward_status() -> dict[str, Any]:
    """Get walk-forward validation status for all strategies.

    Returns summary from WalkForwardRegistry including OOS Sharpe,
    decay status, and stability metrics.
    """
    try:
        from quant_nanggroe.engine.strategy.registry import WalkForwardRegistry

        wf_registry = WalkForwardRegistry()
        all_strategies = wf_registry.list()

        results = []
        for meta in all_strategies:
            summary = wf_registry.summary(meta.name)
            results.append({
                "strategy": meta.name,
                "status": meta.status,
                "n_windows": summary.get("n_windows", 0),
                "avg_train_sharpe": summary.get("avg_train_sharpe", 0.0),
                "avg_test_sharpe": summary.get("avg_test_sharpe", 0.0),
                "decay": summary.get("decay", 0.0),
                "stability": summary.get("stability", 0.0),
                "decayed": wf_registry.decayed(meta.name),
            })

        # Sort by avg_test_sharpe descending
        results.sort(key=lambda x: x.get("avg_test_sharpe", 0.0), reverse=True)

        # Best OOS performers
        best_oos = wf_registry.best_oos(n=5)

        return {
            "total_strategies": len(results),
            "validated": sum(1 for r in results if r["n_windows"] > 0),
            "decayed": sum(1 for r in results if r["decayed"]),
            "results": results,
            "best_oos": best_oos,
            "status": "ok",
        }
    except Exception as exc:
        logger.error("walk_forward_status_failed: %s", exc)
        return {"error": str(exc), "status": "failed"}


# ── Evolution Status Endpoint ─────────────────────────────────────────────


@router.get("/evolution/status")
async def evolution_status() -> dict[str, Any]:
    """Get strategy evolution status from StrategyEvolver.

    Returns evolution statistics and recent attempts.
    """
    try:
        from quant_nanggroe.engine.strategies.strategy_evolver import StrategyEvolver

        evolver = StrategyEvolver()
        stats = evolver.get_stats()
        history = evolver.get_history()[-10:]  # Last 10 attempts

        return {
            "stats": stats,
            "recent_attempts": [
                {
                    "strategy": a.strategy_name,
                    "metric": a.metric,
                    "baseline": round(a.baseline_value, 4),
                    "mutated": round(a.mutated_value, 4),
                    "accepted": a.accepted,
                    "reason": a.reason,
                    "timestamp": a.timestamp,
                }
                for a in history
            ],
            "status": "ok",
        }
    except Exception as exc:
        logger.error("evolution_status_failed: %s", exc)
        return {"error": str(exc), "status": "failed"}
