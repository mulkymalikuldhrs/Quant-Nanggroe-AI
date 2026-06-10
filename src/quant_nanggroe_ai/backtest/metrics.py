"""
Backtest Metrics — Comprehensive Performance Analysis
=====================================================
Production-quality implementations of all standard quantitative
performance metrics with proper annualization and edge-case handling.

Metrics:
    - Sharpe Ratio (annualized)
    - Sortino Ratio
    - Calmar Ratio
    - Maximum Drawdown
    - Win Rate
    - Profit Factor
    - Average Win/Loss
    - Value at Risk (Historical)
    - Conditional VaR (CVaR / Expected Shortfall)

All ratio calculations use proper annualization factors and
handle edge cases (zero division, empty inputs, etc.).
"""

from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class BacktestMetrics:
    """
    Comprehensive backtest performance metrics calculator.

    All methods are stateless and can be called independently.
    Handles edge cases gracefully with proper fallback values.

    Example:
        metrics = BacktestMetrics()
        sharpe = metrics.sharpe_ratio(returns, risk_free_rate=0.02)
        sortino = metrics.sortino_ratio(returns)
        max_dd = metrics.max_drawdown(equity_curve)
    """

    # ==================================================================
    # SHARPE RATIO
    # ==================================================================

    def sharpe_ratio(
        self,
        returns: list[float] | np.ndarray,
        risk_free_rate: float = 0.02,
        periods_per_year: int = 252,
    ) -> float:
        """
        Calculate annualized Sharpe ratio.

        Sharpe = (E[R] - Rf) / sigma(R) * sqrt(periods_per_year)

        Where:
        - E[R] = mean return
        - Rf = risk-free rate (annualized, e.g. 0.02 for 2%)
        - sigma(R) = standard deviation of returns

        Args:
            returns: Period returns (daily, hourly, etc.)
            risk_free_rate: Annualized risk-free rate (default 2%)
            periods_per_year: Number of periods per year
                (252 for daily, 52 for weekly, 12 for monthly)

        Returns:
            Annualized Sharpe ratio. Returns 0.0 on edge cases.
        """
        if not returns or len(returns) < 2:
            logger.debug("sharpe_ratio: insufficient data (%d points)", len(returns) if returns else 0)
            return 0.0

        arr = np.array(returns, dtype=np.float64)
        mean_return = np.mean(arr)
        std_return = np.std(arr, ddof=1)

        if std_return == 0 or not np.isfinite(std_return):
            return 0.0

        # Convert annual risk-free rate to per-period
        rf_per_period = (1 + risk_free_rate) ** (1 / periods_per_year) - 1

        # Excess return per period, annualized
        excess_return = mean_return - rf_per_period
        sharpe = excess_return / std_return * math.sqrt(periods_per_year)

        if not np.isfinite(sharpe):
            return 0.0

        return float(sharpe)

    # ==================================================================
    # SORTINO RATIO
    # ==================================================================

    def sortino_ratio(
        self,
        returns: list[float] | np.ndarray,
        risk_free_rate: float = 0.02,
        periods_per_year: int = 252,
        target_return: float | None = None,
    ) -> float:
        """
        Calculate annualized Sortino ratio.

        Sortino = (E[R] - Rf) / sigma_downside(R) * sqrt(periods_per_year)

        Unlike Sharpe, Sortino only penalizes downside volatility,
        making it more appropriate for asymmetric return distributions.

        Args:
            returns: Period returns
            risk_free_rate: Annualized risk-free rate
            periods_per_year: Periods per year for annualization
            target_return: Minimum acceptable return (defaults to risk-free rate per period)

        Returns:
            Annualized Sortino ratio. Returns 0.0 on edge cases.
        """
        if not returns or len(returns) < 2:
            return 0.0

        arr = np.array(returns, dtype=np.float64)
        rf_per_period = (1 + risk_free_rate) ** (1 / periods_per_year) - 1
        mar = target_return if target_return is not None else rf_per_period

        mean_return = np.mean(arr)

        # Downside deviation: only returns below MAR
        downside = arr[arr < mar] - mar
        if len(downside) == 0:
            # No downside returns - perfect performance
            return float("inf") if mean_return > mar else 0.0

        downside_std = np.sqrt(np.mean(downside ** 2))
        if downside_std == 0 or not np.isfinite(downside_std):
            return 0.0

        excess_return = mean_return - mar
        sortino = excess_return / downside_std * math.sqrt(periods_per_year)

        if not np.isfinite(sortino):
            return 0.0

        return float(sortino)

    # ==================================================================
    # MAX DRAWDOWN
    # ==================================================================

    def max_drawdown(
        self,
        equity_curve: list[float] | list[dict[str, Any]] | np.ndarray,
    ) -> dict[str, Any]:
        """
        Calculate maximum drawdown from an equity curve.

        Drawdown = (Peak - Trough) / Peak

        Args:
            equity_curve: List of equity values, or list of EquityPoint dicts

        Returns:
            Dict with:
                - max_drawdown: Maximum drawdown in currency units
                - max_drawdown_pct: Maximum drawdown as percentage
                - peak_idx: Index of peak before max drawdown
                - trough_idx: Index of trough of max drawdown
                - recovery_idx: Index of recovery (or None if not recovered)
        """
        if not equity_curve:
            return {
                "max_drawdown": 0.0,
                "max_drawdown_pct": 0.0,
                "peak_idx": 0,
                "trough_idx": 0,
                "recovery_idx": None,
            }

        # Extract equity values
        if isinstance(equity_curve, (list, np.ndarray)) and len(equity_curve) > 0:
            first = equity_curve[0]
            if isinstance(first, dict):
                values = [float(e.get("equity", e.get("value", 0))) for e in equity_curve]
            elif isinstance(first, (int, float, np.floating, np.integer)):
                values = [float(v) for v in equity_curve]
            else:
                values = [float(getattr(e, "equity", 0)) for e in equity_curve]
        else:
            return {
                "max_drawdown": 0.0, "max_drawdown_pct": 0.0,
                "peak_idx": 0, "trough_idx": 0, "recovery_idx": None,
            }

        if len(values) < 2:
            return {
                "max_drawdown": 0.0, "max_drawdown_pct": 0.0,
                "peak_idx": 0, "trough_idx": 0, "recovery_idx": None,
            }

        peak = values[0]
        peak_idx = 0
        max_dd = 0.0
        max_dd_pct = 0.0
        max_peak_idx = 0
        max_trough_idx = 0

        for i, val in enumerate(values):
            if val > peak:
                peak = val
                peak_idx = i

            dd = peak - val
            dd_pct = dd / peak if peak > 0 else 0.0

            if dd > max_dd:
                max_dd = dd
                max_dd_pct = dd_pct
                max_peak_idx = peak_idx
                max_trough_idx = i

        # Find recovery point
        recovery_idx = None
        if max_trough_idx < len(values) - 1:
            for i in range(max_trough_idx + 1, len(values)):
                if values[i] >= values[max_peak_idx]:
                    recovery_idx = i
                    break

        return {
            "max_drawdown": round(max_dd, 4),
            "max_drawdown_pct": round(max_dd_pct * 100, 4),
            "peak_idx": max_peak_idx,
            "trough_idx": max_trough_idx,
            "recovery_idx": recovery_idx,
        }

    # ==================================================================
    # WIN RATE
    # ==================================================================

    def win_rate(self, trades: list[dict[str, Any]]) -> float:
        """
        Calculate win rate from a list of trades.

        Args:
            trades: List of trade dicts with 'pnl' key, or list of numeric PnLs

        Returns:
            Win rate as a decimal (0.0 - 1.0)
        """
        if not trades:
            return 0.0

        pnls = self._extract_pnls(trades)
        if not pnls:
            return 0.0

        wins = sum(1 for p in pnls if p > 0)
        return round(wins / len(pnls), 4)

    # ==================================================================
    # PROFIT FACTOR
    # ==================================================================

    def profit_factor(self, trades: list[dict[str, Any]]) -> float:
        """
        Calculate profit factor.

        Profit Factor = Gross Profit / Gross Loss

        Values > 1.0 indicate profitability.

        Args:
            trades: List of trade dicts with 'pnl' key, or list of numeric PnLs

        Returns:
            Profit factor. Returns float('inf') if no losses.
        """
        pnls = self._extract_pnls(trades)
        if not pnls:
            return 0.0

        gross_profit = sum(p for p in pnls if p > 0)
        gross_loss = abs(sum(p for p in pnls if p < 0))

        if gross_loss == 0:
            return float("inf") if gross_profit > 0 else 0.0

        return round(gross_profit / gross_loss, 4)

    # ==================================================================
    # CALMAR RATIO
    # ==================================================================

    def calmar_ratio(
        self,
        returns: list[float] | np.ndarray,
        max_drawdown: float | dict[str, Any],
        periods_per_year: int = 252,
    ) -> float:
        """
        Calculate Calmar ratio.

        Calmar = Annualized Return / Max Drawdown

        Args:
            returns: Period returns
            max_drawdown: Maximum drawdown value (float or dict from max_drawdown())
            periods_per_year: Periods per year

        Returns:
            Calmar ratio. Returns 0.0 if max drawdown is 0.
        """
        if not returns or len(returns) < 2:
            return 0.0

        arr = np.array(returns, dtype=np.float64)

        # Annualized return
        cumulative = float(np.prod(1 + arr))
        n_years = len(arr) / periods_per_year
        if n_years <= 0:
            return 0.0
        annualized_return = (cumulative ** (1 / n_years) - 1)

        # Extract max drawdown
        if isinstance(max_drawdown, dict):
            mdd = abs(max_drawdown.get("max_drawdown_pct", 0)) / 100
        else:
            mdd = abs(float(max_drawdown))

        if mdd == 0:
            return 0.0 if annualized_return <= 0 else float("inf")

        calmar = annualized_return / mdd

        if not np.isfinite(calmar):
            return 0.0

        return float(calmar)

    # ==================================================================
    # VALUE AT RISK (Historical)
    # ==================================================================

    def value_at_risk(
        self,
        returns: list[float] | np.ndarray,
        confidence: float = 0.95,
    ) -> float:
        """
        Calculate Historical Value at Risk (VaR).

        VaR at 95% confidence = 5th percentile of returns.

        Args:
            returns: Period returns
            confidence: Confidence level (0.95 = 95%)

        Returns:
            VaR as a positive number (loss amount)
        """
        if not returns or len(returns) < 10:
            return 0.0

        arr = np.array(returns, dtype=np.float64)
        var = float(np.percentile(arr, (1 - confidence) * 100))
        return abs(var)

    # ==================================================================
    # CONDITIONAL VaR (CVaR / Expected Shortfall)
    # ==================================================================

    def conditional_var(
        self,
        returns: list[float] | np.ndarray,
        confidence: float = 0.95,
    ) -> float:
        """
        Calculate Conditional Value at Risk (CVaR / Expected Shortfall).

        CVaR = E[R | R <= VaR]

        The average loss when losses exceed VaR.

        Args:
            returns: Period returns
            confidence: Confidence level

        Returns:
            CVaR as a positive number
        """
        if not returns or len(returns) < 10:
            return 0.0

        arr = np.array(returns, dtype=np.float64)
        var = np.percentile(arr, (1 - confidence) * 100)
        tail = arr[arr <= var]

        if len(tail) == 0:
            return abs(float(var))

        return abs(float(np.mean(tail)))

    # ==================================================================
    # COMPREHENSIVE METRICS
    # ==================================================================

    def calculate_all(
        self,
        returns: list[float] | np.ndarray,
        equity_curve: list[float] | list[dict[str, Any]] | np.ndarray | None = None,
        trades: list[dict[str, Any]] | None = None,
        risk_free_rate: float = 0.02,
        periods_per_year: int = 252,
    ) -> dict[str, Any]:
        """
        Calculate all available metrics at once.

        Args:
            returns: Period returns
            equity_curve: Optional equity curve for drawdown calculations
            trades: Optional trade list for trade-based metrics
            risk_free_rate: Annualized risk-free rate
            periods_per_year: Periods per year

        Returns:
            Dict with all calculated metrics
        """
        result: dict[str, Any] = {}

        result["sharpe_ratio"] = self.sharpe_ratio(returns, risk_free_rate, periods_per_year)
        result["sortino_ratio"] = self.sortino_ratio(returns, risk_free_rate, periods_per_year)
        result["var_95"] = self.value_at_risk(returns, 0.95)
        result["cvar_95"] = self.conditional_var(returns, 0.95)

        if equity_curve:
            dd = self.max_drawdown(equity_curve)
            result["max_drawdown"] = dd["max_drawdown"]
            result["max_drawdown_pct"] = dd["max_drawdown_pct"]
            result["calmar_ratio"] = self.calmar_ratio(returns, dd, periods_per_year)
        else:
            result["max_drawdown"] = 0.0
            result["max_drawdown_pct"] = 0.0
            result["calmar_ratio"] = 0.0

        if trades:
            result["win_rate"] = self.win_rate(trades)
            result["profit_factor"] = self.profit_factor(trades)
            pnls = self._extract_pnls(trades)
            if pnls:
                result["avg_win"] = float(np.mean([p for p in pnls if p > 0])) if any(p > 0 for p in pnls) else 0.0
                result["avg_loss"] = float(np.mean([p for p in pnls if p < 0])) if any(p < 0 for p in pnls) else 0.0
                result["total_trades"] = len(pnls)
        else:
            result["win_rate"] = 0.0
            result["profit_factor"] = 0.0

        # Basic return statistics
        if returns:
            arr = np.array(returns, dtype=np.float64)
            result["total_return"] = float(np.sum(arr))
            result["avg_return"] = float(np.mean(arr))
            result["std_return"] = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
            result["skewness"] = float(self._skewness(arr))
            result["kurtosis"] = float(self._kurtosis(arr))

        return result

    # ==================================================================
    # INTERNAL HELPERS
    # ==================================================================

    @staticmethod
    def _extract_pnls(trades: list[Any]) -> list[float]:
        """Extract PnL values from trades (flexible input format)."""
        pnls = []
        for t in trades:
            if isinstance(t, dict):
                pnls.append(float(t.get("pnl", 0)))
            elif isinstance(t, (int, float, np.floating, np.integer)):
                pnls.append(float(t))
            elif hasattr(t, "pnl"):
                pnls.append(float(t.pnl))
        return pnls

    @staticmethod
    def _skewness(data: np.ndarray) -> float:
        """Calculate skewness of returns."""
        if len(data) < 3:
            return 0.0
        n = len(data)
        mean = np.mean(data)
        std = np.std(data, ddof=1)
        if std == 0:
            return 0.0
        skew = (n / ((n - 1) * (n - 2))) * np.sum(((data - mean) / std) ** 3)
        return float(skew) if np.isfinite(skew) else 0.0

    @staticmethod
    def _kurtosis(data: np.ndarray) -> float:
        """Calculate excess kurtosis of returns."""
        if len(data) < 4:
            return 0.0
        n = len(data)
        mean = np.mean(data)
        std = np.std(data, ddof=1)
        if std == 0:
            return 0.0
        m4 = np.sum(((data - mean) / std) ** 4)
        kurt = ((n * (n + 1)) / ((n - 1) * (n - 2) * (n - 3))) * m4 - \
               (3 * (n - 1) ** 2) / ((n - 2) * (n - 3))
        return float(kurt) if np.isfinite(kurt) else 0.0


# ======================================================================
# Module-level convenience function
# ======================================================================


def by_symbol_stats(trades: list[Any]) -> dict[str, dict[str, Any]]:
    """Compute per-symbol performance summary from a list of TradeRecord objects.

    Args:
        trades: List of TradeRecord (or dict-like) objects.

    Returns:
        Dict mapping symbol -> {count, win_rate, total_pnl, avg_pnl}.
    """
    from collections import defaultdict

    buckets: dict[str, list[float]] = defaultdict(list)
    for t in trades:
        symbol = getattr(t, "symbol", t.get("symbol", "UNKNOWN") if isinstance(t, dict) else "UNKNOWN")
        pnl = getattr(t, "pnl", t.get("pnl", 0.0) if isinstance(t, dict) else 0.0)
        buckets[symbol].append(float(pnl))

    result: dict[str, dict[str, Any]] = {}
    for sym, pnls in sorted(buckets.items()):
        wins = sum(1 for p in pnls if p > 0)
        result[sym] = {
            "count": len(pnls),
            "win_rate": round(wins / len(pnls), 4) if pnls else 0.0,
            "total_pnl": round(sum(pnls), 4),
            "avg_pnl": round(float(np.mean(pnls)), 4) if pnls else 0.0,
        }
    return result


def by_exit_reason_stats(trades: list[Any]) -> dict[str, dict[str, Any]]:
    """Compute performance summary grouped by exit reason.

    Args:
        trades: List of TradeRecord (or dict-like) objects.

    Returns:
        Dict mapping exit_reason -> {count, win_rate, total_pnl, avg_pnl}.
    """
    from collections import defaultdict

    buckets: dict[str, list[float]] = defaultdict(list)
    for t in trades:
        reason = getattr(t, "exit_reason", t.get("exit_reason", "unknown") if isinstance(t, dict) else "unknown")
        pnl = getattr(t, "pnl", t.get("pnl", 0.0) if isinstance(t, dict) else 0.0)
        buckets[reason].append(float(pnl))

    result: dict[str, dict[str, Any]] = {}
    for reason, pnls in sorted(buckets.items()):
        wins = sum(1 for p in pnls if p > 0)
        result[reason] = {
            "count": len(pnls),
            "win_rate": round(wins / len(pnls), 4) if pnls else 0.0,
            "total_pnl": round(sum(pnls), 4),
            "avg_pnl": round(float(np.mean(pnls)), 4) if pnls else 0.0,
        }
    return result


def calc_metrics(
    equity_series: Any,
    trades: list[Any],
    initial_capital: float = 1_000_000,
    bars_per_year: int = 252,
    bench_ret: Any = None,
) -> dict[str, Any]:
    """Calculate comprehensive backtest metrics from equity curve and trades.

    This is the primary metrics function used by the advanced engine framework
    (backtest.engines.base.BaseEngine). It accepts a pandas Series equity curve
    and a list of TradeRecord objects.

    Args:
        equity_series: pd.Series of equity values indexed by timestamp.
        trades: List of TradeRecord objects.
        initial_capital: Starting capital.
        bars_per_year: Bars per year for annualization (252 for daily).
        bench_ret: Optional pd.Series of benchmark returns.

    Returns:
        Dict with all standard backtest metrics.
    """
    import pandas as pd

    calc = BacktestMetrics()

    if equity_series is None or len(equity_series) < 2:
        return {"total_return": 0.0, "sharpe_ratio": 0.0, "max_drawdown_pct": 0.0}

    # Compute returns from equity series
    returns = equity_series.pct_change().dropna().values.tolist()

    # Core metrics
    result = calc.calculate_all(
        returns=returns,
        equity_curve=equity_series.tolist(),
        trades=None,  # We'll add trade metrics separately
        periods_per_year=bars_per_year,
    )

    # Total return from equity curve
    total_return = (float(equity_series.iloc[-1]) / initial_capital - 1.0) if initial_capital > 0 else 0.0
    result["total_return"] = round(total_return, 6)
    result["initial_capital"] = initial_capital
    result["final_equity"] = round(float(equity_series.iloc[-1]), 4)

    # Trade-based metrics
    if trades:
        pnls = []
        for t in trades:
            pnl = getattr(t, "pnl", t.get("pnl", 0.0) if isinstance(t, dict) else 0.0)
            pnls.append(float(pnl))
        result["total_trades"] = len(pnls)
        result["win_rate"] = calc.win_rate(trades)
        result["profit_factor"] = calc.profit_factor(trades)
        if pnls:
            result["avg_trade_pnl"] = round(float(np.mean(pnls)), 4)
            result["total_pnl"] = round(sum(pnls), 4)
    else:
        result["total_trades"] = 0

    # Benchmark comparison
    if bench_ret is not None and len(bench_ret) > 1:
        bench_returns = bench_ret.pct_change().dropna().values.tolist() if hasattr(bench_ret, "pct_change") else list(bench_ret)
        bench_metrics = calc.calculate_all(returns=bench_returns, periods_per_year=bars_per_year)
        result["benchmark_sharpe"] = bench_metrics.get("sharpe_ratio", 0.0)
        result["benchmark_total_return"] = bench_metrics.get("total_return", 0.0)

    return result


def calculate_metrics(
    returns: list[float] | np.ndarray,
    benchmark: list[float] | np.ndarray | None = None,
    equity_curve: list[float] | list[dict[str, Any]] | np.ndarray | None = None,
    trades: list[dict[str, Any]] | None = None,
    risk_free_rate: float = 0.02,
    periods_per_year: int = 252,
) -> dict[str, Any]:
    """
    Convenience function to calculate all backtest metrics at once.

    This is a module-level wrapper around BacktestMetrics.calculate_all()
    for easy import and use in API routes and other modules.

    Args:
        returns: Period returns (daily, hourly, etc.)
        benchmark: Optional benchmark returns for comparison.
        equity_curve: Optional equity curve for drawdown calculations.
        trades: Optional trade list for trade-based metrics.
        risk_free_rate: Annualized risk-free rate (default 2%).
        periods_per_year: Number of periods per year (252 for daily).

    Returns:
        Dict with all calculated metrics including optional benchmark comparison.

    Example::

        from quant_nanggroe_ai.backtest.metrics import calculate_metrics
        result = calculate_metrics(daily_returns)
    """
    calculator = BacktestMetrics()
    result = calculator.calculate_all(
        returns=returns,
        equity_curve=equity_curve,
        trades=trades,
        risk_free_rate=risk_free_rate,
        periods_per_year=periods_per_year,
    )

    # Add benchmark comparison if provided
    if benchmark is not None and len(benchmark) > 1:
        bench_metrics = calculator.calculate_all(
            returns=benchmark,
            risk_free_rate=risk_free_rate,
            periods_per_year=periods_per_year,
        )
        result["benchmark_sharpe"] = bench_metrics.get("sharpe_ratio", 0.0)
        result["benchmark_total_return"] = bench_metrics.get("total_return", 0.0)

    return result
