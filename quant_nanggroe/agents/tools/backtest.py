"""
Backtest Tool — Strategy Backtesting for Agents
=================================================
Provides a high-level interface for running backtests and retrieving
results. Wraps the BacktestEngine from quant_nanggroe.engine.backtest
with agent-friendly async methods, result caching, and validation.

Features:
  - Multiple strategy support (SMA crossover, RSI mean-revert, custom)
  - Configurable commission, slippage, and position sizing
  - Comprehensive performance metrics via PerformanceMetrics
  - Result storage and retrieval by backtest_id
  - Data fetching integration via MarketDataTool

LangChain @tool functions are also exposed for direct agent consumption.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd
from langchain_core.tools import tool

from quant_nanggroe.config.settings import get_settings
from quant_nanggroe.exceptions import DataError, EngineError, InsufficientDataError

logger = logging.getLogger(__name__)

# ── Built-in strategy generators ──────────────────────────────────────


def _sma_crossover_signals(
    closes: List[float],
    fast_period: int = 20,
    slow_period: int = 50,
) -> List[Dict[str, Any]]:
    """
    Generate SMA crossover trade signals.

    Returns a list of signal dicts with 'bar_index', 'direction', 'price'.
    """
    if len(closes) < slow_period + 1:
        return []

    arr = np.array(closes, dtype=float)

    # Calculate SMAs
    fast_sma = np.full(len(arr), np.nan)
    slow_sma = np.full(len(arr), np.nan)

    for i in range(fast_period - 1, len(arr)):
        fast_sma[i] = np.mean(arr[i - fast_period + 1:i + 1])
    for i in range(slow_period - 1, len(arr)):
        slow_sma[i] = np.mean(arr[i - slow_period + 1:i + 1])

    signals: List[Dict[str, Any]] = []
    for i in range(slow_period, len(arr)):
        if np.isnan(fast_sma[i]) or np.isnan(slow_sma[i]):
            continue
        if np.isnan(fast_sma[i - 1]) or np.isnan(slow_sma[i - 1]):
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
    closes: List[float],
    rsi_period: int = 14,
    oversold: float = 30.0,
    overbought: float = 70.0,
) -> List[Dict[str, Any]]:
    """
    Generate RSI mean-reversion trade signals.

    Buy when RSI crosses above oversold, sell when RSI crosses below overbought.
    """
    if len(closes) < rsi_period + 1:
        return []

    arr = np.array(closes, dtype=float)
    deltas = np.diff(arr)

    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = np.mean(gains[:rsi_period])
    avg_loss = np.mean(losses[:rsi_period])

    rsi_vals: List[Optional[float]] = [None] * rsi_period

    if avg_loss == 0:
        rsi_vals.append(100.0)
    else:
        rs = avg_gain / avg_loss
        rsi_vals.append(100.0 - (100.0 / (1.0 + rs)))

    for i in range(rsi_period, len(deltas)):
        avg_gain = (avg_gain * (rsi_period - 1) + gains[i]) / rsi_period
        avg_loss = (avg_loss * (rsi_period - 1) + losses[i]) / rsi_period
        if avg_loss == 0:
            rsi_vals.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_vals.append(100.0 - (100.0 / (1.0 + rs)))

    signals: List[Dict[str, Any]] = []
    for i in range(rsi_period + 1, len(rsi_vals)):
        if rsi_vals[i] is None or rsi_vals[i - 1] is None:
            continue

        # RSI crosses above oversold → BUY
        if rsi_vals[i] > oversold and rsi_vals[i - 1] <= oversold:
            signals.append({
                "bar_index": i,
                "direction": "BUY",
                "price": closes[min(i, len(closes) - 1)],
            })
        # RSI crosses below overbought → SELL
        elif rsi_vals[i] < overbought and rsi_vals[i - 1] >= overbought:
            signals.append({
                "bar_index": i,
                "direction": "SELL",
                "price": closes[min(i, len(closes) - 1)],
            })

    return signals


def _macd_signals(
    closes: List[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> List[Dict[str, Any]]:
    """
    Generate MACD crossover signals.

    Buy when MACD line crosses above signal line.
    Sell when MACD line crosses below signal line.
    """
    if len(closes) < slow + signal:
        return []

    arr = np.array(closes, dtype=float)

    # EMAs
    def ema(data: np.ndarray, period: int) -> np.ndarray:
        result = np.full_like(data, np.nan, dtype=float)
        result[period - 1] = np.mean(data[:period])
        multiplier = 2.0 / (period + 1)
        for i in range(period, len(data)):
            result[i] = (data[i] - result[i - 1]) * multiplier + result[i - 1]
        return result

    ema_fast = ema(arr, fast)
    ema_slow = ema(arr, slow)

    macd_line = np.where(
        np.isnan(ema_fast) | np.isnan(ema_slow),
        np.nan,
        ema_fast - ema_slow,
    )

    # Signal line from valid MACD values
    valid_macd = macd_line[~np.isnan(macd_line)]
    if len(valid_macd) < signal:
        return []

    signal_line = np.full_like(valid_macd, np.nan, dtype=float)
    signal_line[signal - 1] = np.mean(valid_macd[:signal])
    multiplier = 2.0 / (signal + 1)
    for i in range(signal, len(valid_macd)):
        signal_line[i] = (valid_macd[i] - signal_line[i - 1]) * multiplier + signal_line[i - 1]

    # Align signal_line with macd_line indices
    offset = len(macd_line) - len(valid_macd)

    signals: List[Dict[str, Any]] = []
    for i in range(signal, len(valid_macd)):
        macd_idx = offset + i
        if np.isnan(signal_line[i]) or np.isnan(signal_line[i - 1]):
            continue
        if np.isnan(valid_macd[i]) or np.isnan(valid_macd[i - 1]):
            continue

        # MACD crosses above signal → BUY
        if valid_macd[i] > signal_line[i] and valid_macd[i - 1] <= signal_line[i - 1]:
            signals.append({
                "bar_index": macd_idx,
                "direction": "BUY",
                "price": closes[min(macd_idx, len(closes) - 1)],
            })
        # MACD crosses below signal → SELL
        elif valid_macd[i] < signal_line[i] and valid_macd[i - 1] >= signal_line[i - 1]:
            signals.append({
                "bar_index": macd_idx,
                "direction": "SELL",
                "price": closes[min(macd_idx, len(closes) - 1)],
            })

    return signals


# Strategy registry
_BUILTIN_STRATEGIES: Dict[str, Callable[..., List[Dict[str, Any]]]] = {
    "sma_crossover": _sma_crossover_signals,
    "rsi_mean_revert": _rsi_mean_revert_signals,
    "macd_crossover": _macd_signals,
}


class _BacktestResultStore:
    """In-memory store for backtest results, keyed by backtest_id."""

    def __init__(self, max_results: int = 100) -> None:
        self._results: Dict[str, Dict[str, Any]] = {}
        self._max = max_results

    def store(self, backtest_id: str, result: Dict[str, Any]) -> None:
        """Store a backtest result."""
        # Evict oldest if at capacity
        if len(self._results) >= self._max:
            oldest_key = next(iter(self._results))
            del self._results[oldest_key]
        self._results[backtest_id] = result

    def get(self, backtest_id: str) -> Dict[str, Any] | None:
        """Retrieve a backtest result by ID."""
        return self._results.get(backtest_id)

    def list_ids(self) -> List[str]:
        """List all stored backtest IDs."""
        return list(self._results.keys())


class BacktestTool:
    """
    Backtesting tool for agent consumption.

    Provides a high-level interface to run strategy backtests, store
    results, and retrieve them by ID. Supports both built-in strategies
    and custom strategy functions.

    Built-in strategies:
      - sma_crossover: SMA fast/slow crossover
      - rsi_mean_revert: RSI oversold/overbought mean-reversion
      - macd_crossover: MACD line/signal crossover

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
        strategy_params: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        Run a backtest for a strategy on a symbol.

        Args:
            strategy: Strategy name ('sma_crossover', 'rsi_mean_revert',
                'macd_crossover', or a custom registered strategy).
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
            candles = ohlcv.get("candles", [])

            if len(candles) < 50:
                raise InsufficientDataError(50, len(candles), "backtest")

            # Filter candles by date range
            candles = self._filter_candles_by_date(candles, start_date, end_date)
            if len(candles) < 30:
                raise InsufficientDataError(30, len(candles), "backtest (after date filter)")

            closes = [c["close"] for c in candles]

            # ── Generate signals ──────────────────────────────────────
            signal_func = _BUILTIN_STRATEGIES.get(strategy)
            if signal_func is None:
                raise EngineError(
                    f"Unknown strategy: '{strategy}'. "
                    f"Available: {list(_BUILTIN_STRATEGIES.keys())}"
                )

            params = strategy_params or {}
            signals = signal_func(closes, **params)

            # ── Simulate trades from signals ──────────────────────────
            trades, equity_curve = self._simulate_trades(
                signals, closes, initial_capital, commission, slippage_bps / 10_000,
            )

            # ── Calculate metrics ─────────────────────────────────────
            metrics = self._calculate_metrics(
                equity_curve, trades, initial_capital
            )

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

    async def get_backtest_results(self, backtest_id: str) -> Dict[str, Any]:
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

    async def list_backtests(self) -> List[Dict[str, Any]]:
        """
        List all stored backtest summaries.

        Returns:
            List of dicts with 'backtest_id', 'strategy', 'symbol', 'status', 'timestamp'.
        """
        summaries: List[Dict[str, Any]] = []
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
        self, name: str, func: Callable[..., List[Dict[str, Any]]]
    ) -> None:
        """
        Register a custom strategy function.

        The function must accept `closes: List[float]` as the first
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
        candles: List[Dict[str, Any]],
        start_date: str,
        end_date: str,
    ) -> List[Dict[str, Any]]:
        """Filter candles to the requested date range."""
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)

        filtered: List[Dict[str, Any]] = []
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
        signals: List[Dict[str, Any]],
        closes: List[float],
        initial_capital: float,
        commission: float,
        slippage: float,
    ) -> tuple[List[Dict[str, Any]], List[float]]:
        """
        Simulate trades from signals and build equity curve.

        Simple simulation: alternate BUY/SELL signals, track P&L.

        Returns:
            Tuple of (trades_list, equity_curve_list).
        """
        capital = initial_capital
        position_size: float = 0.0
        entry_price: float = 0.0
        trades: List[Dict[str, Any]] = []
        equity_curve: List[float] = [initial_capital]

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
    def _calculate_metrics(
        equity_curve: List[float],
        trades: List[Dict[str, Any]],
        initial_capital: float,
    ) -> Dict[str, Any]:
        """
        Calculate backtest performance metrics.

        Computes Sharpe ratio, max drawdown, win rate, and other metrics
        from the equity curve and trade list.
        """
        if len(equity_curve) < 2:
            return {}

        eq = np.array(equity_curve, dtype=float)

        # Returns
        returns = np.diff(eq) / eq[:-1]
        returns = np.where(np.isfinite(returns), returns, 0.0)

        # Total return
        total_return = (eq[-1] / initial_capital) - 1.0

        # Annual return (assume 252 trading days)
        n_days = len(eq) - 1
        if n_days > 0 and total_return > -1.0:
            annual_return = (1 + total_return) ** (252 / max(n_days, 1)) - 1
        else:
            annual_return = 0.0

        # Max drawdown
        peak = np.maximum.accumulate(eq)
        drawdown = (eq - peak) / np.where(peak > 0, peak, 1.0)
        max_drawdown = float(np.min(drawdown))
        max_drawdown_pct = abs(max_drawdown) * 100

        # Sharpe ratio
        if len(returns) > 1 and np.std(returns) > 0:
            sharpe_ratio = float(np.mean(returns) / np.std(returns) * np.sqrt(252))
        else:
            sharpe_ratio = 0.0

        # Sortino ratio
        downside = returns[returns < 0]
        if len(downside) > 1 and np.std(downside) > 0:
            sortino_ratio = float(np.mean(returns) / np.std(downside) * np.sqrt(252))
        else:
            sortino_ratio = 0.0

        # Win rate
        winning_trades = [t for t in trades if t.get("pnl", 0) > 0]
        losing_trades = [t for t in trades if t.get("pnl", 0) < 0]
        total_closed = len(winning_trades) + len(losing_trades)
        win_rate = len(winning_trades) / total_closed if total_closed > 0 else 0.0

        # Profit factor
        gross_profit = sum(t.get("pnl", 0) for t in winning_trades)
        gross_loss = abs(sum(t.get("pnl", 0) for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

        # Calmar ratio
        calmar_ratio = annual_return / max_drawdown_pct if max_drawdown_pct > 0 else 0.0

        return {
            "initial_capital": initial_capital,
            "final_equity": round(float(eq[-1]), 2),
            "total_return": round(total_return, 6),
            "total_return_pct": round(total_return * 100, 2),
            "annual_return": round(annual_return, 6),
            "annual_return_pct": round(annual_return * 100, 2),
            "max_drawdown": round(max_drawdown, 6),
            "max_drawdown_pct": round(max_drawdown_pct, 2),
            "sharpe_ratio": round(sharpe_ratio, 4),
            "sortino_ratio": round(sortino_ratio, 4),
            "calmar_ratio": round(calmar_ratio, 4),
            "win_rate": round(win_rate, 4),
            "win_rate_pct": round(win_rate * 100, 2),
            "profit_factor": round(profit_factor, 4),
            "total_trades": len(trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
        }


# ══════════════════════════════════════════════════════════════════════
# Singleton instance for @tool functions
# ══════════════════════════════════════════════════════════════════════

_default_bt: BacktestTool | None = None


def _get_default_bt() -> BacktestTool:
    """Get or create the default BacktestTool instance."""
    global _default_bt
    if _default_bt is None:
        from quant_nanggroe.agents.tools.market_data import _get_default_mdt
        _default_bt = BacktestTool(market_data_tool=_get_default_mdt())
    return _default_bt


# ══════════════════════════════════════════════════════════════════════
# LangChain @tool functions for agent consumption
# ══════════════════════════════════════════════════════════════════════


@tool
async def run_backtest(
    strategy: str,
    symbol: str,
    timeframe: str = "1d",
    start_date: str = "2023-01-01",
    end_date: str = "2024-01-01",
    initial_capital: float = 10000.0,
    commission: float = 0.001,
    slippage_bps: float = 5.0,
) -> str:
    """
    Run a strategy backtest on a trading symbol.

    Supports built-in strategies: sma_crossover, rsi_mean_revert,
    macd_crossover. Fetches historical data, generates signals,
    simulates trades, and calculates performance metrics.

    Args:
        strategy: Strategy name ('sma_crossover', 'rsi_mean_revert', 'macd_crossover')
        symbol: Ticker symbol (e.g., 'AAPL', 'BTC/USDT')
        timeframe: Candle interval ('1d', '1h', '4h')
        start_date: Backtest start date (YYYY-MM-DD)
        end_date: Backtest end date (YYYY-MM-DD)
        initial_capital: Starting capital in USD (default 10000)
        commission: Commission rate per trade (default 0.001 = 0.1%)
        slippage_bps: Slippage in basis points (default 5)

    Returns:
        JSON string with backtest results including performance metrics
        (Sharpe ratio, max drawdown, win rate, etc.), trade list,
        equity curve, and signal details.
    """
    try:
        bt = _get_default_bt()
        result = await bt.run_backtest(
            strategy=strategy,
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            commission=commission,
            slippage_bps=slippage_bps,
        )
        return json.dumps(result, indent=2, default=str)
    except (DataError, InsufficientDataError, EngineError) as exc:
        return json.dumps({"error": str(exc), "symbol": symbol, "strategy": strategy})
    except Exception as exc:
        logger.error("run_backtest tool error: %s", exc)
        return json.dumps({"error": f"Backtest failed: {exc}", "symbol": symbol, "strategy": strategy})


@tool
async def get_backtest_results(backtest_id: str) -> str:
    """
    Retrieve stored backtest results by ID.

    Args:
        backtest_id: The backtest run ID (e.g., 'BT-a1b2c3d4')

    Returns:
        JSON string with full backtest results including metrics,
        trades, equity curve, and signals.
    """
    try:
        bt = _get_default_bt()
        result = await bt.get_backtest_results(backtest_id)
        return json.dumps(result, indent=2, default=str)
    except EngineError as exc:
        return json.dumps({"error": str(exc), "backtest_id": backtest_id})
    except Exception as exc:
        logger.error("get_backtest_results tool error: %s", exc)
        return json.dumps({"error": f"Failed to retrieve results: {exc}", "backtest_id": backtest_id})


@tool
async def list_backtests() -> str:
    """
    List all stored backtest summaries.

    Returns:
        JSON string with list of backtest summaries including
        ID, strategy, symbol, status, and timestamp.
    """
    try:
        bt = _get_default_bt()
        result = await bt.list_backtests()
        return json.dumps(result, indent=2, default=str)
    except Exception as exc:
        logger.error("list_backtests tool error: %s", exc)
        return json.dumps({"error": f"Failed to list backtests: {exc}"})
