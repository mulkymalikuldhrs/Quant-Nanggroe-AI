"""Benchmark Comparison Module.

Provides benchmark return series for comparing strategy performance
against market indices and other reference points.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd


@dataclass
class BenchmarkResult:
    """Result from benchmark comparison."""

    ticker: str
    total_ret: float
    ret_series: pd.Series


# Default benchmark mapping by market
BENCHMARK_MAP = {
    "equity_us": "SPY",
    "equity_cn": "000300.SS",
    "crypto": "BTC-USD",
    "forex": "DXY",
    "futures": "ES=F",
}


class BenchmarkManager:
    """Manages benchmark data for backtest comparison.

    Provides methods for:
    - Resolving benchmark tickers from strategy symbols
    - Computing benchmark return series
    - Comparing strategy vs benchmark performance
    """

    @staticmethod
    def resolve_benchmark(
        strategy_codes: list,
        market: str = "equity_us",
        explicit: Optional[str] = None,
    ) -> str:
        """Resolve benchmark ticker.

        Args:
            strategy_codes: List of strategy instrument codes.
            market: Market type.
            explicit: Explicit benchmark ticker override.

        Returns:
            Benchmark ticker string.
        """
        if explicit:
            return explicit
        return BENCHMARK_MAP.get(market, "SPY")

    @staticmethod
    def compute_benchmark_returns(
        prices: pd.Series,
    ) -> BenchmarkResult:
        """Compute benchmark return series from price data.

        Args:
            prices: Benchmark price series.

        Returns:
            BenchmarkResult with returns and total return.
        """
        returns = prices.pct_change().fillna(0.0)
        total_ret = float((1 + returns).prod() - 1)
        return BenchmarkResult(
            ticker=str(prices.name) if prices.name else "BENCHMARK",
            total_ret=total_ret,
            ret_series=returns,
        )

    @staticmethod
    def compare(
        strategy_returns: pd.Series,
        benchmark_returns: pd.Series,
        risk_free_rate: float = 0.02,
        bars_per_year: int = 252,
    ) -> dict:
        """Compare strategy vs benchmark performance.

        Args:
            strategy_returns: Strategy per-bar returns.
            benchmark_returns: Benchmark per-bar returns.
            risk_free_rate: Annual risk-free rate.
            bars_per_year: Bars per year for annualisation.

        Returns:
            Dict of comparison metrics.
        """
        # Align indices
        common_idx = strategy_returns.index.intersection(benchmark_returns.index)
        sr = strategy_returns.reindex(common_idx).fillna(0.0)
        br = benchmark_returns.reindex(common_idx).fillna(0.0)

        # Active returns
        active_ret = sr - br
        tracking_error = float(active_ret.std() * np.sqrt(bars_per_year))
        info_ratio = float(active_ret.mean() / (active_ret.std() + 1e-10) * np.sqrt(bars_per_year))

        # Beta
        cov_matrix = np.cov(sr.values, br.values)
        beta = cov_matrix[0, 1] / (cov_matrix[1, 1] + 1e-10) if cov_matrix[1, 1] > 0 else 1.0

        # Alpha (annualized)
        alpha = float((sr.mean() - br.mean()) * bars_per_year)

        # Strategy total return
        strat_total = float((1 + sr).prod() - 1)
        bench_total = float((1 + br).prod() - 1)

        return {
            "strategy_return": round(strat_total, 6),
            "benchmark_return": round(bench_total, 6),
            "excess_return": round(strat_total - bench_total, 6),
            "alpha": round(alpha, 6),
            "beta": round(beta, 4),
            "information_ratio": round(info_ratio, 4),
            "tracking_error": round(tracking_error, 4),
        }
