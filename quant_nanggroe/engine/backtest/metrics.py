"""Performance Metrics — Comprehensive Backtest Evaluation.

Implements comprehensive performance metrics for backtest evaluation
with proper annualization for different markets.

Metrics include:
- Total return, CAGR (Compound Annual Growth Rate)
- Sharpe, Sortino, Calmar ratios
- Max drawdown, max drawdown duration
- Win rate, profit factor
- Average trade, average win, average loss
- Recovery factor
- Tail ratio
- Ulcer index
- VaR, CVaR
- Benchmark comparison metrics
- All with proper annualization
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.backtest.portfolio import TradeRecord

logger = logging.getLogger(__name__)


@dataclass
class MetricsResult:
    """Container for all performance metrics."""

    total_return: float = 0.0
    annual_return: float = 0.0  # CAGR
    cagr: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0  # in bars
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    profit_loss_ratio: float = 0.0
    avg_trade: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    total_trades: int = 0
    max_consecutive_losses: int = 0
    avg_holding_bars: float = 0.0
    final_equity: float = 0.0
    volatility: float = 0.0
    downside_deviation: float = 0.0
    var_95: float = 0.0
    cvar_95: float = 0.0
    recovery_factor: float = 0.0
    tail_ratio: float = 0.0
    ulcer_index: float = 0.0


class PerformanceMetrics:
    """Comprehensive performance metrics calculator.

    Supports annualisation for different markets (252 for equities, 365 for crypto),
    benchmark comparison, and risk-adjusted return metrics.

    All ratios are properly annualized:
    - Sharpe: (mean_return / std) * sqrt(bars_per_year)
    - Sortino: (mean_return / downside_std) * sqrt(bars_per_year)
    - Calmar: CAGR / abs(max_drawdown)
    - Volatility: std * sqrt(bars_per_year)
    """

    def __init__(self, bars_per_year: int = 252) -> None:
        self.bars_per_year = bars_per_year

    def calculate(
        self,
        equity_series: pd.Series,
        trades: List[TradeRecord],
        initial_capital: float,
        benchmark_returns: Optional[pd.Series] = None,
    ) -> Dict[str, Any]:
        """Calculate full set of performance metrics.

        Args:
            equity_series: Equity curve (index=timestamp, values=equity).
            trades: List of completed trade records.
            initial_capital: Starting capital.
            benchmark_returns: Optional benchmark return series.

        Returns:
            Dict of metric name -> value.
        """
        if len(equity_series) == 0:
            return self._empty_metrics(initial_capital)

        returns = equity_series.pct_change().fillna(0.0)
        n = len(equity_series)

        # ── Basic returns ─────────────────────────────────────────────
        total_return = float(equity_series.iloc[-1] / initial_capital - 1)
        # CAGR: (1 + total_return) ^ (bars_per_year / n_bars) - 1
        cagr = float((1 + total_return) ** (self.bars_per_year / max(n, 1)) - 1) if total_return > -1 else -1.0

        # ── Volatility ────────────────────────────────────────────────
        vol = float(returns.std() * np.sqrt(self.bars_per_year))

        # ── Drawdown ──────────────────────────────────────────────────
        peak = equity_series.cummax()
        drawdown = (equity_series - peak) / peak.replace(0, 1)
        max_dd = float(drawdown.min())

        # Max drawdown duration (in bars)
        max_dd_duration = self._calc_max_drawdown_duration(equity_series)

        # ── Sharpe Ratio ──────────────────────────────────────────────
        sharpe = float(returns.mean() / (returns.std() + 1e-10) * np.sqrt(self.bars_per_year))

        # ── Sortino Ratio ─────────────────────────────────────────────
        downside = returns[returns < 0]
        downside_std_val = float(downside.std()) if len(downside) > 1 else 0.0
        downside_std = float(downside_std_val * np.sqrt(self.bars_per_year)) if downside_std_val > 1e-10 else 1e-10
        sortino = float(returns.mean() * self.bars_per_year / downside_std)

        # ── Calmar Ratio ──────────────────────────────────────────────
        calmar = cagr / abs(max_dd) if abs(max_dd) > 1e-10 else 0.0

        # ── VaR and CVaR (95%) ────────────────────────────────────────
        var_95 = float(returns.quantile(0.05)) if len(returns) > 0 else 0.0
        cvar_95 = float(returns[returns <= var_95].mean()) if len(returns[returns <= var_95]) > 0 else var_95

        # ── Recovery Factor ───────────────────────────────────────────
        # Total profit / abs(max drawdown)
        total_profit = equity_series.iloc[-1] - initial_capital
        recovery_factor = float(total_profit / abs(max_dd * initial_capital)) if abs(max_dd) > 1e-10 else 0.0

        # ── Tail Ratio ────────────────────────────────────────────────
        # Ratio of the 95th percentile to the 5th percentile of returns
        p95_ret = float(returns.quantile(0.95)) if len(returns) > 0 else 0.0
        p5_ret = float(returns.quantile(0.05)) if len(returns) > 0 else 1e-10
        tail_ratio = abs(p95_ret / p5_ret) if abs(p5_ret) > 1e-10 else 0.0

        # ── Ulcer Index ───────────────────────────────────────────────
        ulcer_index = self._calc_ulcer_index(drawdown)

        # ── Trade statistics ──────────────────────────────────────────
        trade_stats = self._trade_statistics(trades)

        # ── Downside deviation (annualized) ───────────────────────────
        downside_dev = downside_std

        # ── Benchmark comparison ──────────────────────────────────────
        bench_metrics = {}
        if benchmark_returns is not None and len(benchmark_returns) > 0:
            bench_total = float((1 + benchmark_returns).prod() - 1)
            excess_return = total_return - bench_total
            active_ret = returns - benchmark_returns.reindex(returns.index).fillna(0.0)
            tracking_error = float(active_ret.std() * np.sqrt(self.bars_per_year))
            info_ratio = float(active_ret.mean() / (active_ret.std() + 1e-10) * np.sqrt(self.bars_per_year))

            # Alpha and Beta
            cov_matrix = np.cov(
                returns.values,
                benchmark_returns.reindex(returns.index).fillna(0.0).values,
            )
            beta = cov_matrix[0, 1] / (cov_matrix[1, 1] + 1e-10) if cov_matrix[1, 1] > 1e-10 else 1.0
            risk_free_per_bar = 0.02 / self.bars_per_year
            alpha = float(
                (returns.mean() - risk_free_per_bar) -
                beta * (benchmark_returns.reindex(returns.index).fillna(0.0).mean() - risk_free_per_bar)
            ) * self.bars_per_year

            bench_metrics = {
                "benchmark_return": round(bench_total, 6),
                "excess_return": round(excess_return, 6),
                "alpha": round(alpha, 6),
                "beta": round(beta, 4),
                "information_ratio": round(info_ratio, 4),
                "tracking_error": round(tracking_error, 4),
            }

        return {
            "final_equity": float(equity_series.iloc[-1]),
            "total_return": round(total_return, 6),
            "annual_return": round(cagr, 6),
            "cagr": round(cagr, 6),
            "max_drawdown": round(max_dd, 6),
            "max_drawdown_duration": max_dd_duration,
            "sharpe_ratio": round(sharpe, 4),
            "sortino_ratio": round(sortino, 4),
            "calmar_ratio": round(calmar, 4),
            "volatility": round(vol, 6),
            "downside_deviation": round(downside_dev, 6),
            "var_95": round(var_95, 6),
            "cvar_95": round(cvar_95, 6),
            "recovery_factor": round(recovery_factor, 4),
            "tail_ratio": round(tail_ratio, 4),
            "ulcer_index": round(ulcer_index, 6),
            "total_trades": len(trades),
            **trade_stats,
            **bench_metrics,
        }

    def _trade_statistics(self, trades: List[TradeRecord]) -> Dict[str, Any]:
        """Calculate trade-level statistics.

        Args:
            trades: List of completed trade records.

        Returns:
            Dict of trade statistics.
        """
        if not trades:
            return {
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "profit_loss_ratio": 0.0,
                "max_consecutive_losses": 0,
                "avg_holding_bars": 0.0,
                "avg_trade_pnl": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "max_win": 0.0,
                "max_loss": 0.0,
            }

        wins = [t.pnl for t in trades if t.pnl > 0]
        losses = [t.pnl for t in trades if t.pnl < 0]

        win_rate = len(wins) / len(trades) if trades else 0.0
        avg_win = float(np.mean(wins)) if wins else 0.0
        avg_loss = abs(float(np.mean(losses))) if losses else 1e-10
        profit_loss_ratio = avg_win / avg_loss if avg_loss > 1e-10 else 0.0

        gross_profit = sum(wins) if wins else 0.0
        gross_loss = abs(sum(losses)) if losses else 1e-10
        profit_factor = gross_profit / gross_loss if gross_loss > 1e-10 else 0.0

        # Max consecutive losses
        max_consec = 0
        cur_consec = 0
        for t in trades:
            if t.pnl < 0:
                cur_consec += 1
                max_consec = max(max_consec, cur_consec)
            else:
                cur_consec = 0

        hold_bars = [t.holding_bars for t in trades if t.holding_bars > 0]
        avg_holding = float(np.mean(hold_bars)) if hold_bars else 0.0

        # Average trade P&L
        all_pnls = [t.pnl for t in trades]
        avg_trade_pnl = float(np.mean(all_pnls)) if all_pnls else 0.0

        return {
            "win_rate": round(win_rate, 4),
            "profit_factor": round(profit_factor, 4),
            "profit_loss_ratio": round(profit_loss_ratio, 4),
            "max_consecutive_losses": max_consec,
            "avg_holding_bars": round(avg_holding, 1),
            "avg_trade_pnl": round(avg_trade_pnl, 4),
            "avg_win": round(avg_win, 4),
            "avg_loss": round(float(np.mean([t.pnl for t in trades if t.pnl < 0])) if losses else 0.0, 4),
            "max_win": round(max(all_pnls), 4) if all_pnls else 0.0,
            "max_loss": round(min(all_pnls), 4) if all_pnls else 0.0,
        }

    @staticmethod
    def _calc_max_drawdown_duration(equity_series: pd.Series) -> int:
        """Calculate maximum drawdown duration in bars.

        The drawdown duration is the number of bars from a peak
        until the equity recovers to or exceeds that peak.

        Args:
            equity_series: Equity curve.

        Returns:
            Maximum drawdown duration in bars.
        """
        if len(equity_series) < 2:
            return 0

        peak = equity_series.iloc[0]
        peak_idx = 0
        max_duration = 0

        for i in range(1, len(equity_series)):
            if equity_series.iloc[i] >= peak:
                # New peak or recovery
                duration = i - peak_idx
                max_duration = max(max_duration, duration)
                peak = equity_series.iloc[i]
                peak_idx = i

        # Handle case where we never recovered
        if peak_idx < len(equity_series) - 1:
            duration = len(equity_series) - 1 - peak_idx
            max_duration = max(max_duration, duration)

        return max_duration

    @staticmethod
    def _calc_ulcer_index(drawdown: pd.Series) -> float:
        """Calculate the Ulcer Index.

        The Ulcer Index measures the depth and duration of drawdowns:
        UI = sqrt(mean(drawdown^2))

        Args:
            drawdown: Drawdown series (negative values).

        Returns:
            Ulcer Index value.
        """
        if len(drawdown) == 0:
            return 0.0

        squared_dd = drawdown ** 2
        return float(np.sqrt(squared_dd.mean()))

    def _empty_metrics(self, initial_capital: float) -> Dict[str, Any]:
        """Return zero-valued metrics when no data is available."""
        return {
            "final_equity": initial_capital,
            "total_return": 0, "annual_return": 0, "cagr": 0,
            "max_drawdown": 0, "max_drawdown_duration": 0,
            "sharpe_ratio": 0, "sortino_ratio": 0, "calmar_ratio": 0,
            "volatility": 0, "downside_deviation": 0,
            "var_95": 0, "cvar_95": 0,
            "recovery_factor": 0, "tail_ratio": 0, "ulcer_index": 0,
            "total_trades": 0, "win_rate": 0, "profit_factor": 0,
            "profit_loss_ratio": 0, "max_consecutive_losses": 0,
            "avg_holding_bars": 0, "avg_trade_pnl": 0,
            "avg_win": 0, "avg_loss": 0,
            "max_win": 0, "max_loss": 0,
        }

    @staticmethod
    def calc_bars_per_year(interval: str = "1D", market: str = "equity") -> int:
        """Calculate bars per year for annualisation.

        Args:
            interval: Bar size (1m, 5m, 15m, 30m, 1H, 4H, 1D).
            market: Market type (equity, crypto, forex, futures).

        Returns:
            Number of bars per year.
        """
        trading_days = 252 if market in ("equity", "forex", "futures") else 365
        bars_per_day = {
            "1m": {"equity": 390, "crypto": 1440, "forex": 1440, "futures": 390},
            "5m": {"equity": 78, "crypto": 288, "forex": 288, "futures": 78},
            "15m": {"equity": 26, "crypto": 96, "forex": 96, "futures": 26},
            "30m": {"equity": 13, "crypto": 48, "forex": 48, "futures": 13},
            "1H": {"equity": 7, "crypto": 24, "forex": 24, "futures": 7},
            "4H": {"equity": 2, "crypto": 6, "forex": 6, "futures": 2},
            "1D": {"equity": 1, "crypto": 1, "forex": 1, "futures": 1},
        }
        bpd = bars_per_day.get(interval, {}).get(market, 1)
        return trading_days * bpd
