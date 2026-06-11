"""Performance Metrics — Sharpe, Sortino, Max DD, Calmar, etc.

Implements comprehensive performance metrics for backtest evaluation.
Extracted from Vibe-Trading's metrics and ai-hedge-fund's backtest metrics.
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
    annual_return: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    profit_loss_ratio: float = 0.0
    total_trades: int = 0
    max_consecutive_losses: int = 0
    avg_holding_bars: float = 0.0
    final_equity: float = 0.0
    volatility: float = 0.0
    downside_deviation: float = 0.0
    var_95: float = 0.0
    cvar_95: float = 0.0


class PerformanceMetrics:
    """Comprehensive performance metrics calculator.

    Supports annualisation for different markets (252 for equities, 365 for crypto),
    benchmark comparison, and risk-adjusted return metrics.
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

        # Basic returns
        total_return = float(equity_series.iloc[-1] / initial_capital - 1)
        n = len(equity_series)
        ann_return = float((1 + total_return) ** (self.bars_per_year / max(n, 1)) - 1)

        # Volatility
        vol = float(returns.std() * np.sqrt(self.bars_per_year))

        # Drawdown
        peak = equity_series.cummax()
        drawdown = (equity_series - peak) / peak.replace(0, 1)
        max_dd = float(drawdown.min())

        # Sharpe Ratio
        sharpe = float(returns.mean() / (returns.std() + 1e-10) * np.sqrt(self.bars_per_year))

        # Sortino Ratio
        downside = returns[returns < 0]
        downside_std = float(downside.std() * np.sqrt(self.bars_per_year)) if len(downside) > 1 else 1e-10
        sortino = float(returns.mean() * self.bars_per_year / downside_std)

        # Calmar Ratio
        calmar = ann_return / abs(max_dd) if abs(max_dd) > 1e-10 else 0.0

        # VaR and CVaR (95%)
        var_95 = float(returns.quantile(0.05)) if len(returns) > 0 else 0.0
        cvar_95 = float(returns[returns <= var_95].mean()) if len(returns[returns <= var_95]) > 0 else var_95

        # Trade statistics
        trade_stats = self._trade_statistics(trades)

        # Benchmark comparison
        bench_metrics = {}
        if benchmark_returns is not None and len(benchmark_returns) > 0:
            bench_total = float((1 + benchmark_returns).prod() - 1)
            excess_return = total_return - bench_total
            active_ret = returns - benchmark_returns.reindex(returns.index).fillna(0.0)
            tracking_error = float(active_ret.std() * np.sqrt(self.bars_per_year))
            info_ratio = float(active_ret.mean() / (active_ret.std() + 1e-10) * np.sqrt(self.bars_per_year))
            bench_metrics = {
                "benchmark_return": round(bench_total, 6),
                "excess_return": round(excess_return, 6),
                "information_ratio": round(info_ratio, 4),
                "tracking_error": round(tracking_error, 4),
            }

        return {
            "final_equity": float(equity_series.iloc[-1]),
            "total_return": round(total_return, 6),
            "annual_return": round(ann_return, 6),
            "max_drawdown": round(max_dd, 6),
            "sharpe_ratio": round(sharpe, 4),
            "sortino_ratio": round(sortino, 4),
            "calmar_ratio": round(calmar, 4),
            "volatility": round(vol, 6),
            "downside_deviation": round(downside_std, 6),
            "var_95": round(var_95, 6),
            "cvar_95": round(cvar_95, 6),
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

        return {
            "win_rate": round(win_rate, 4),
            "profit_factor": round(profit_factor, 4),
            "profit_loss_ratio": round(profit_loss_ratio, 4),
            "max_consecutive_losses": max_consec,
            "avg_holding_bars": round(avg_holding, 1),
            "avg_trade_pnl": round(float(np.mean([t.pnl for t in trades])), 4),
            "max_win": round(max([t.pnl for t in trades]), 4) if trades else 0.0,
            "max_loss": round(min([t.pnl for t in trades]), 4) if trades else 0.0,
        }

    def _empty_metrics(self, initial_capital: float) -> Dict[str, Any]:
        """Return zero-valued metrics when no data is available."""
        return {
            "final_equity": initial_capital,
            "total_return": 0, "annual_return": 0, "max_drawdown": 0,
            "sharpe_ratio": 0, "sortino_ratio": 0, "calmar_ratio": 0,
            "volatility": 0, "downside_deviation": 0,
            "var_95": 0, "cvar_95": 0,
            "total_trades": 0, "win_rate": 0, "profit_factor": 0,
            "profit_loss_ratio": 0, "max_consecutive_losses": 0,
            "avg_holding_bars": 0, "avg_trade_pnl": 0,
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
