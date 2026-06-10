"""
Backtest Tool — Strategy Backtesting for Agents
=================================================
Provides a high-level interface for running backtests and retrieving
results. Wraps the BacktestEngine from quant_nanggroe_ai.backtest
with agent-friendly async methods, result caching, and validation.

Features:
  - Multiple strategy support (SMA crossover, RSI mean-revert, custom)
  - Configurable commission, slippage, and position sizing
  - Comprehensive performance metrics via BacktestMetrics
  - Result storage and retrieval by backtest_id
  - Data fetching integration via MarketDataTool
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from quant_nanggroe_ai.backtest.engine import BacktestEngine, BacktestResult
from quant_nanggroe_ai.backtest.metrics import BacktestMetrics
from quant_nanggroe_ai.config import get_settings
from quant_nanggroe_ai.exceptions import DataError, EngineError, InsufficientDataError

logger = logging.getLogger(__name__)

# ── Built-in strategy generators ──────────────────────────────────────

def _sma_crossover_signals(
    closes: list[float],
    fast_period: int = 20,
    slow_period: int = 50,
) -> list[dict[str, Any]]:
    """
    Generate SMA crossover trade signals.

    Returns a list of signal dicts with 'bar_index', 'direction', 'price'.
    """
    from quant_nanggroe_ai.engine.math_lib import MathEngine

    if len(closes) < slow_period + 1:
        return []

    fast_sma = MathEngine.sma(closes, fast_period)
    slow_sma = MathEngine.sma(closes, slow_period)

    signals: list[dict[str, Any]] = []
    for i in range(slow_period, len(closes)):
        if fast_sma[i] is None or slow_sma[i] is None:
            continue
        if fast_sma[i - 1] is None or slow_sma[i - 1] is None:
            continue

        # Crossover: fast crosses above slow → BUY
        if fast_sma[i] > slow_sma[i] and fast_sma[i - 1] <= slow_sma[i - 1]:
            signals.append({
                "bar_index": i,
                "direction": "BUY",
                "price": closes[i],
            })
        # Crossunder: fast crosses below slow → SELL
        elif fast_sma[i] < slow_sma[i] and fast_sma[i - 1] >= slow_sma[i - 1]:
            signals.append({
                "bar_index": i,
                "direction": "SELL",
                "price": closes[i],
            })

    return signals


def _rsi_mean_revert_signals(
    closes: list[float],
    rsi_period: int = 14,
    oversold: float = 30.0,
    overbought: float = 70.0,
) -> list[dict[str, Any]]:
    """
    Generate RSI mean-reversion trade signals.

    Buy when RSI crosses above oversold, sell when RSI crosses below overbought.
    """
    from quant_nanggroe_ai.engine.math_lib import MathEngine

    rsi_vals = MathEngine.rsi(closes, rsi_period)

    signals: list[dict[str, Any]] = []
    for i in range(rsi_period + 1, len(closes)):
        if rsi_vals[i] is None or rsi_vals[i - 1] is None:
            continue

        # RSI crosses above oversold → BUY
        if rsi_vals[i] > oversold and rsi_vals[i - 1] <= oversold:
            signals.append({
                "bar_index": i,
                "direction": "BUY",
                "price": closes[i],
            })
        # RSI crosses below overbought → SELL
        elif rsi_vals[i] < overbought and rsi_vals[i - 1] >= overbought:
            signals.append({
                "bar_index": i,
                "direction": "SELL",
                "price": closes[i],
            })

    return signals


# Strategy registry
_BUILTIN_STRATEGIES: dict[str, Callable[..., list[dict[str, Any]]]] = {
    "sma_crossover": _sma_crossover_signals,
    "rsi_mean_revert": _rsi_mean_revert_signals,
}


class _BacktestResultStore:
    """In-memory store for backtest results, keyed by backtest_id."""

    def __init__(self, max_results: int = 100) -> None:
        self._results: dict[str, dict[str, Any]] = {}
        self._max = max_results

    def store(self, backtest_id: str, result: dict[str, Any]) -> None:
        """Store a backtest result."""
        # Evict oldest if at capacity
        if len(self._results) >= self._max:
            oldest_key = next(iter(self._results))
            del self._results[oldest_key]
        self._results[backtest_id] = result

    def get(self, backtest_id: str) -> dict[str, Any] | None:
        """Retrieve a backtest result by ID."""
        return self._results.get(backtest_id)

    def list_ids(self) -> list[str]:
        """List all stored backtest IDs."""
        return list(self._results.keys())


class BacktestTool:
    """
    Backtesting tool for agent consumption.

    Provides a high-level interface to run strategy backtests, store
    results, and retrieve them by ID. Uses BacktestEngine for simulation
    and BacktestMetrics for performance reporting.

    Supports both built-in strategies (SMA crossover, RSI mean-revert)
    and custom strategy functions.

    Usage::

        tool = BacktestTool(market_data_tool=mdt)
        result = await tool.run_backtest(
            strategy="sma_crossover",
            symbol="AAPL",
            timeframe="1d",
            start_date="2023-01-01",
            end_date="2024-01-01",
        )
        print(result["metrics"]["sharpe_ratio"])
    """

    def __init__(
        self,
        market_data_tool: Any | None = None,
        max_stored_results: int = 100,
    ) -> None:
        """
        Initialize the BacktestTool.

        Args:
            market_data_tool: Optional MarketDataTool for auto-fetching data.
            max_stored_results: Maximum number of results to keep in memory.
        """
        self._settings = get_settings()
        self._market_data = market_data_tool
        self._store = _BacktestResultStore(max_results=max_stored_results)
        self._metrics_calc = BacktestMetrics()

    async def run_backtest(
        self,
        strategy: str,
        symbol: str,
        timeframe: str = "1d",
        start_date: str = "2023-01-01",
        end_date: str = "2024-01-01",
        initial_capital: float = 10000.0,
        commission: float = 0.001,
        slippage_bps: float = 5.0,
        strategy_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Run a backtest for a strategy on a symbol.

        Args:
            strategy: Strategy name ('sma_crossover', 'rsi_mean_revert',
                or a custom strategy key registered via register_strategy).
            symbol: Ticker symbol to backtest.
            timeframe: Candle interval.
            start_date: Backtest start date (YYYY-MM-DD).
            end_date: Backtest end date (YYYY-MM-DD).
            initial_capital: Starting capital (default $10,000).
            commission: Commission rate per trade (default 0.1%).
            slippage_bps: Slippage in basis points (default 5 bps).
            strategy_params: Additional parameters for the strategy function.

        Returns:
            Dict with:
              - 'backtest_id': Unique ID for the backtest run
              - 'strategy': Strategy name
              - 'symbol': Symbol tested
              - 'timeframe': Timeframe used
              - 'period': Start/end dates
              - 'config': BacktestConfig parameters
              - 'signals': Generated trade signals
              - 'trades': Executed trades
              - 'equity_curve': Portfolio equity over time
              - 'metrics': Performance metrics (Sharpe, drawdown, etc.)
              - 'status': "COMPLETED" or "FAILED"
              - 'timestamp': When the backtest was run

        Raises:
            DataError: If data cannot be fetched.
            EngineError: If the backtest fails.
        """
        # Generate backtest ID
        backtest_id = f"BT-{uuid.uuid4().hex[:8]}"

        logger.info(
            "Starting backtest %s: strategy=%s symbol=%s period=%s→%s",
            backtest_id, strategy, symbol, start_date, end_date,
        )

        try:
            # ── Fetch data ────────────────────────────────────────────
            if self._market_data is None:
                raise DataError(
                    "No MarketDataTool configured — provide one at init"
                )

            ohlcv = await self._market_data.get_ohlcv(symbol, timeframe, limit=1000)
            candles = ohlcv_result.get("candles", []) if False else ohlcv.get("candles", [])

            if len(candles) < 50:
                raise InsufficientDataError(50, len(candles), "backtest")

            # Filter candles by date range
            candles = self._filter_candles_by_date(candles, start_date, end_date)
            if len(candles) < 30:
                raise InsufficientDataError(30, len(candles), "backtest (after date filter)")

            closes = [c["close"] for c in candles]
            highs = [c["high"] for c in candles]
            lows = [c["low"] for c in candles]
            volumes = [c["volume"] for c in candles]

            # ── Generate signals ──────────────────────────────────────
            signal_func = _BUILTIN_STRATEGIES.get(strategy)
            if signal_func is None:
                raise EngineError(
                    f"Unknown strategy: '{strategy}'. "
                    f"Available: {list(_BUILTIN_STRATEGIES.keys())}"
                )

            params = strategy_params or {}
            signals = signal_func(closes, **params)

            # ── Run backtest engine ───────────────────────────────────
            engine = BacktestEngine(
                initial_capital=initial_capital,
                commission=commission,
                slippage_bps=slippage_bps,
            )

            # Build a DataFrame from candles for the engine
            import pandas as pd
            df = pd.DataFrame(candles)
            if "timestamp" in df.columns:
                df = df.rename(columns={"timestamp": "timestamp"})

            # Create a strategy function from our signals
            signal_indices = {s["bar_index"]: s for s in signals}
            position_open = False

            def signal_strategy(bar: dict[str, Any], positions: dict, equity: float) -> dict[str, Any] | None:
                nonlocal position_open
                bar_idx = bar.get("bar_idx", 0)
                sig = signal_indices.get(bar_idx)
                if sig is None:
                    return None
                if sig["direction"] == "BUY" and not positions:
                    return {"action": "BUY", "symbol": symbol, "quantity": None}
                elif sig["direction"] == "SELL" and positions:
                    return {"action": "SELL", "symbol": symbol}
                return None

            # Add bar_idx to each bar for signal matching
            indexed_candles = []
            for idx, c in enumerate(candles):
                indexed_candles.append({**c, "bar_idx": idx})

            engine_result = engine.run(signal_strategy, indexed_candles)

            # ── Simulate trades from signals (simple) ─────────────────
            trades, equity_curve = self._simulate_trades(
                signals, closes, initial_capital, commission, slippage_bps / 10_000,
            )

            # ── Calculate metrics ─────────────────────────────────────
            returns = self._compute_returns(equity_curve)
            metrics = self._metrics_calc.calculate_all(
                returns=returns,
                equity_curve=equity_curve,
                trades=trades,
            ) if returns else {}

            # ── Build result ──────────────────────────────────────────
            result = {
                "backtest_id": backtest_id,
                "strategy": strategy,
                "symbol": symbol,
                "timeframe": timeframe,
                "period": {"start": start_date, "end": end_date},
                "config": {
                    "initial_capital": initial_capital,
                    "commission": commission,
                    "slippage_bps": slippage_bps,
                    "strategy_params": params,
                },
                "signals_count": len(signals),
                "signals": signals[-20:],  # Last 20 signals for brevity
                "trades": trades,
                "trades_count": len(trades),
                "equity_curve": equity_curve,
                "metrics": metrics,
                "engine_result": engine_result.model_dump() if hasattr(engine_result, 'model_dump') else {},
                "status": "COMPLETED",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Store result
            self._store.store(backtest_id, result)

            logger.info(
                "Backtest %s completed: %d signals, %d trades, "
                "sharpe=%.2f, max_dd=%.2f%%",
                backtest_id, len(signals), len(trades),
                metrics.get("sharpe_ratio", 0.0),
                metrics.get("max_drawdown_pct", 0.0),
            )
            return result

        except (DataError, InsufficientDataError, EngineError):
            raise
        except Exception as exc:
            logger.error("Backtest %s failed: %s", backtest_id, exc)
            failed_result = {
                "backtest_id": backtest_id,
                "strategy": strategy,
                "symbol": symbol,
                "status": "FAILED",
                "error": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self._store.store(backtest_id, failed_result)
            raise EngineError(f"Backtest {backtest_id} failed: {exc}") from exc

    async def get_backtest_results(self, backtest_id: str) -> dict[str, Any]:
        """
        Retrieve stored backtest results by ID.

        Args:
            backtest_id: The backtest run ID.

        Returns:
            Full backtest result dict.

        Raises:
            EngineError: If the backtest ID is not found.
        """
        result = self._store.get(backtest_id)
        if result is None:
            raise EngineError(f"Backtest not found: {backtest_id}")
        return result

    async def list_backtests(self) -> list[dict[str, Any]]:
        """
        List all stored backtest summaries.

        Returns:
            List of dicts with 'backtest_id', 'strategy', 'symbol', 'status', 'timestamp'.
        """
        summaries: list[dict[str, Any]] = []
        for bt_id in self._store.list_ids():
            result = self._store.get(bt_id)
            if result:
                summaries.append({
                    "backtest_id": bt_id,
                    "strategy": result.get("strategy", ""),
                    "symbol": result.get("symbol", ""),
                    "status": result.get("status", "UNKNOWN"),
                    "timestamp": result.get("timestamp", ""),
                })
        return summaries

    def register_strategy(
        self, name: str, func: Callable[..., list[dict[str, Any]]]
    ) -> None:
        """
        Register a custom strategy function.

        The function must accept `closes: list[float]` as the first
        argument and return a list of signal dicts with keys
        'bar_index', 'direction', 'price'.

        Args:
            name: Strategy name for lookup.
            func: Strategy signal generation function.
        """
        _BUILTIN_STRATEGIES[name] = func
        logger.info("Registered custom strategy: %s", name)

    # ── Private helpers ───────────────────────────────────────────────

    @staticmethod
    def _filter_candles_by_date(
        candles: list[dict[str, Any]],
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        """Filter candles to the requested date range."""
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)

        filtered: list[dict[str, Any]] = []
        for c in candles:
            ts = c.get("timestamp", "")
            try:
                # Handle ISO format with or without timezone
                ts_clean = ts.replace("Z", "+00:00")
                candle_dt = datetime.fromisoformat(ts_clean)
                # Strip timezone for comparison
                candle_dt = candle_dt.replace(tzinfo=None)
            except (ValueError, AttributeError):
                continue
            if start <= candle_dt <= end:
                filtered.append(c)

        return filtered

    @staticmethod
    def _simulate_trades(
        signals: list[dict[str, Any]],
        closes: list[float],
        initial_capital: float,
        commission: float,
        slippage: float,
    ) -> tuple[list[dict[str, Any]], list[float]]:
        """
        Simulate trades from signals and build equity curve.

        Simple simulation: alternate BUY/SELL signals, track P&L.

        Returns:
            Tuple of (trades_list, equity_curve_list).
        """
        capital = initial_capital
        position_size: float = 0.0
        entry_price: float = 0.0
        trades: list[dict[str, Any]] = []
        equity_curve: list[float] = [initial_capital]

        for signal in signals:
            bar_idx = signal["bar_index"]
            direction = signal["direction"]
            price = signal["price"]

            if direction == "BUY" and position_size == 0.0:
                # Enter long
                slip = price * slippage
                fill_price = price + slip
                position_size = capital / fill_price if fill_price > 0 else 0.0
                commission_cost = fill_price * position_size * commission
                entry_price = fill_price
                capital -= commission_cost
                trades.append({
                    "bar_index": bar_idx,
                    "direction": "BUY",
                    "entry_price": round(fill_price, 6),
                    "quantity": round(position_size, 6),
                    "commission": round(commission_cost, 6),
                })

            elif direction == "SELL" and position_size > 0.0:
                # Exit long
                slip = price * slippage
                fill_price = price - slip
                gross_value = fill_price * position_size
                commission_cost = gross_value * commission
                pnl = (fill_price - entry_price) * position_size - commission_cost
                capital += gross_value - commission_cost
                trades.append({
                    "bar_index": bar_idx,
                    "direction": "SELL",
                    "exit_price": round(fill_price, 6),
                    "quantity": round(position_size, 6),
                    "pnl": round(pnl, 6),
                    "commission": round(commission_cost, 6),
                })
                position_size = 0.0
                entry_price = 0.0

            # Update equity curve
            idx = min(bar_idx, len(closes) - 1)
            current_equity = capital + (position_size * closes[idx] if position_size > 0 else 0)
            equity_curve.append(current_equity)

        return trades, equity_curve

    @staticmethod
    def _compute_returns(equity_curve: list[float]) -> list[float]:
        """Compute period returns from an equity curve."""
        if len(equity_curve) < 2:
            return []

        returns: list[float] = []
        for i in range(1, len(equity_curve)):
            if equity_curve[i - 1] > 0:
                returns.append(
                    (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
                )
            else:
                returns.append(0.0)
        return returns
