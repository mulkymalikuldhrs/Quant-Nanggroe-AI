"""
Performance Metrics — ffn-style analytics
==========================================
Sharpe, Sortino, Calmar, drawdown, rolling metrics, benchmarking.

Terinspirasi dari ffn (pmorissette/ffn), QuantPy (jsmidt/QuantPy),
Finance-Python (alpha-miner/Finance-Python).

Ponytail: numpy-native, minimal deps.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Aggregated performance metrics for a strategy or portfolio.

    Semua metrik distandarisasi dari return series.
    """
    total_return: float = 0.0
    annualized_return: float = 0.0
    annualized_vol: float = 0.0
    sharpe: float = 0.0
    sortino: float = 0.0
    calmar: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    count_trades: int = 0
    skew: float = 0.0
    kurtosis: float = 0.0
    var_95: float = 0.0
    cvar_95: float = 0.0
    rolling_sharpe_6m: Optional[float] = None
    rolling_sharpe_12m: Optional[float] = None
    benchmark_return: Optional[float] = None
    alpha: Optional[float] = None
    beta: Optional[float] = None
    information_ratio: Optional[float] = None
    trades: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {k: float(v) if isinstance(v, (np.floating,)) else v for k, v in self.__dict__.items() if k != "trades"}

    def summary(self) -> str:
        """One-line performance summary."""
        return (
            f"Sharpe {self.sharpe:.2f} | Sortino {self.sortino:.2f} | "
            f"Calmar {self.calmar:.2f} | Return {self.total_return:.1%} | "
            f"DD {self.max_drawdown:.1%} | Vol {self.annualized_vol:.1%}"
        )


def compute_metrics(
    returns: np.ndarray | pd.Series,
    risk_free_rate: float = 0.05,
    periods_per_year: int = 252,
    trades: Optional[list[dict]] = None,
    benchmark_returns: Optional[np.ndarray] = None,
) -> PerformanceMetrics:
    """Compute comprehensive performance metrics from a return series.

    Args:
        returns: Array of periodic returns (decimal, not %)
        risk_free_rate: Annual risk-free rate
        periods_per_year: Trading periods per year (252 daily, 52 weekly, 12 monthly)
        trades: Optional list of trade dicts with 'pnl' key
        benchmark_returns: Optional benchmark return series for alpha/beta

    Returns:
        PerformanceMetrics dataclass
    """
    r = np.asarray(returns, dtype=np.float64)
    n = len(r)
    if n < 2:
        return PerformanceMetrics(count_trades=len(trades or []))

    # Annualized metrics
    total_ret = float(np.prod(1 + r) - 1)
    ann_factor = periods_per_year
    ann_ret = float((1 + total_ret) ** (ann_factor / n) - 1) if n > 0 else 0.0
    ann_vol = float(np.std(r, ddof=1) * np.sqrt(ann_factor))

    # Risk-adjusted
    excess = r - risk_free_rate / ann_factor
    sharpe = float(np.mean(excess) / (np.std(r, ddof=1) + 1e-8) * np.sqrt(ann_factor))

    # Sortino (downside deviation only)
    downside = r[r < 0]
    dd = float(np.std(downside, ddof=1) * np.sqrt(ann_factor)) if len(downside) > 1 else 0.001
    sortino = float(np.mean(excess) / (dd + 1e-8) * np.sqrt(ann_factor))

    # Drawdown
    cum = np.cumprod(1 + r)
    peak = np.maximum.accumulate(cum)
    dd_raw = (cum - peak) / peak
    max_dd = float(np.min(dd_raw))
    calmar = float(ann_ret / (-max_dd + 1e-8))

    # Drawdown duration
    is_dd = dd_raw < 0
    durations = _drawdown_durations(is_dd)
    max_dd_dur = max(durations) if durations else 0

    # Trade stats
    if trades:
        pnls = np.array([t.get("pnl", 0) for t in trades])
        wins = pnls[pnls > 0]
        losses = pnls[pnls < 0]
        win_rate = float(len(wins) / len(pnls)) if len(pnls) > 0 else 0.0
        profit_factor = float(abs(np.sum(wins) / np.sum(losses))) if np.sum(losses) != 0 else float("inf")
        avg_win = float(np.mean(wins)) if len(wins) > 0 else 0.0
        avg_loss = float(np.mean(losses)) if len(losses) > 0 else 0.0
    else:
        win_rate = profit_factor = avg_win = avg_loss = 0.0

    # Distribution
    skew = float(pd.Series(r).skew())
    kurt = float(pd.Series(r).kurtosis())

    # VaR / CVaR
    sorted_r = np.sort(r)
    var95 = float(sorted_r[int(0.05 * n)])
    cvar95 = float(np.mean(sorted_r[:int(0.05 * n)])) if int(0.05 * n) > 0 else var95

    # Benchmark-relative (alpha, beta, IR)
    alpha = beta = ir = None
    if benchmark_returns is not None and len(benchmark_returns) == n:
        b = np.asarray(benchmark_returns, dtype=np.float64)
        cov = np.cov(r, b)[0, 1]
        var_b = np.var(b, ddof=1)
        beta = float(cov / var_b) if var_b > 0 else 0.0
        alpha = float(ann_ret - risk_free_rate - beta * (float(np.prod(1 + b) ** (ann_factor / n) - 1) - risk_free_rate))  # noqa: E501
        residual = r - beta * b
        te = float(np.std(residual, ddof=1) * np.sqrt(ann_factor))
        ir = float((alpha + 1e-8) / (te + 1e-8))  # information ratio ≈ alpha / tracking error

    return PerformanceMetrics(
        total_return=total_ret,
        annualized_return=ann_ret,
        annualized_vol=ann_vol,
        sharpe=sharpe,
        sortino=sortino,
        calmar=calmar,
        max_drawdown=max_dd,
        max_drawdown_duration=max_dd_dur,
        win_rate=win_rate,
        profit_factor=profit_factor,
        avg_win=avg_win,
        avg_loss=avg_loss,
        count_trades=len(trades or []),
        skew=skew,
        kurtosis=kurt,
        var_95=var95,
        cvar_95=cvar95,
        benchmark_return=float(np.prod(1 + benchmark_returns) - 1) if benchmark_returns is not None else None,
        alpha=alpha,
        beta=beta,
        information_ratio=ir,
        trades=trades or [],
    )


def rolling_sharpe(
    returns: np.ndarray,
    window: int = 252,
    risk_free_rate: float = 0.05,
    periods_per_year: int = 252,
) -> np.ndarray:
    """Compute rolling Sharpe ratio over a window.

    Args:
        returns: Return series
        window: Rolling window in periods
        risk_free_rate: Annual risk-free rate
        periods_per_year: Trading periods per year

    Returns:
        Array of rolling Sharpe ratios (length len(returns) - window + 1)
    """
    r = np.asarray(returns, dtype=np.float64)
    n = len(r)
    if n < window + 1:
        return np.array([])

    rf_period = risk_free_rate / periods_per_year
    result = np.zeros(n - window + 1)
    for i in range(len(result)):
        window_ret = r[i:i + window]
        excess = window_ret - rf_period
        std = np.std(window_ret, ddof=1)
        result[i] = np.mean(excess) / (std + 1e-8) * np.sqrt(periods_per_year)
    return result


def benchmark_returns(ticker: str, start: str, end: str) -> Optional[pd.Series]:
    """Fetch benchmark return series (delegates to yfinance or data provider).

    Args:
        ticker: Benchmark symbol (SPY, BTC-USD, ^GSPC...)
        start: Start date YYYY-MM-DD
        end: End date YYYY-MM-DD

    Returns:
        Daily return series or None if unavailable
    """
    try:
        import yfinance as yf
        data = yf.download(ticker, start=start, end=end, progress=False)
        if data.empty:
            return None
        prices = data["Close"]
        return prices.pct_change().dropna()
    except Exception as e:
        logger.warning("Failed to fetch benchmark %s: %s", ticker, e)
        return None


def strategy_comparison(
    strategies: dict[str, np.ndarray],
    risk_free_rate: float = 0.05,
    periods_per_year: int = 252,
    benchmark: Optional[np.ndarray] = None,
) -> pd.DataFrame:
    """Compare multiple strategies side-by-side.

    Args:
        strategies: {name: return_series}
        risk_free_rate: Annual risk-free rate
        periods_per_year: Periods per year
        benchmark: Optional benchmark return series

    Returns:
        DataFrame with one row per metric, one column per strategy
    """
    results = {}
    for name, rets in strategies.items():
        bm = benchmark if benchmark is not None else None
        if bm is not None and len(bm) != len(rets):
            bm = None
        results[name] = compute_metrics(rets, risk_free_rate, periods_per_year, benchmark_returns=bm).to_dict()

    df = pd.DataFrame(results)
    df.index.name = "metric"
    return df


def _drawdown_durations(is_dd: np.ndarray) -> list[int]:
    """Compute lengths of consecutive drawdown periods."""
    durations = []
    current = 0
    for val in is_dd:
        if val:
            current += 1
        else:
            if current > 0:
                durations.append(current)
                current = 0
    if current > 0:
        durations.append(current)
    return durations
