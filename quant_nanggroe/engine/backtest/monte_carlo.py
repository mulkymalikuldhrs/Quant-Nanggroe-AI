"""Monte Carlo Simulation for Backtest Confidence Intervals.

Implements Monte Carlo simulation to estimate confidence intervals
for backtest results, addressing the randomness in trade sequencing
and providing robust performance estimates.

Methods:
- Trade shuffle: Randomly reorder trades to test sequence dependence
- Return resample: Bootstrap resample returns
- Price path: Generate random price paths from return distribution
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class MonteCarloResult:
    """Result from Monte Carlo simulation."""

    num_simulations: int
    metric_name: str
    original_value: float
    mean_value: float
    median_value: float
    p5: float  # 5th percentile
    p25: float  # 25th percentile
    p75: float  # 75th percentile
    p95: float  # 95th percentile
    confidence_95: tuple  # (lower, upper) 95% CI
    probability_of_loss: float  # P(result < 0)


class MonteCarloSimulator:
    """Monte Carlo simulation for backtest confidence intervals.

    Provides robust estimates of strategy performance by resampling
    trade returns or equity curve returns thousands of times.

    Usage:
        simulator = MonteCarloSimulator(num_simulations=1000)
        result = simulator.simulate_trade_shuffle(trades, initial_capital)
    """

    def __init__(self, num_simulations: int = 1000, random_seed: Optional[int] = None) -> None:
        """Initialize Monte Carlo simulator.

        Args:
            num_simulations: Number of Monte Carlo simulations to run.
            random_seed: Optional seed for reproducibility.
        """
        self.num_simulations = num_simulations
        self.random_seed = random_seed

    def simulate_trade_shuffle(
        self,
        trades_pnl: List[float],
        initial_capital: float = 1_000_000.0,
        metric: str = "total_return",
    ) -> MonteCarloResult:
        """Simulate by shuffling trade P&L sequence.

        Tests whether the strategy's performance depends on the
        specific sequence of trades (it shouldn't for a robust strategy).

        Args:
            trades_pnl: List of trade P&L values.
            initial_capital: Starting capital.
            metric: Metric to compute ('total_return', 'max_drawdown', 'sharpe').

        Returns:
            MonteCarloResult with confidence intervals.
        """
        if not trades_pnl:
            return MonteCarloResult(
                num_simulations=0, metric_name=metric,
                original_value=0.0, mean_value=0.0, median_value=0.0,
                p5=0.0, p25=0.0, p75=0.0, p95=0.0,
                confidence_95=(0.0, 0.0), probability_of_loss=1.0,
            )

        rng = np.random.default_rng(self.random_seed)
        pnl_array = np.array(trades_pnl)

        # Calculate original metric
        original_value = self._calc_metric(pnl_array, initial_capital, metric)

        # Run simulations
        sim_results = np.empty(self.num_simulations)

        for i in range(self.num_simulations):
            shuffled = rng.permutation(pnl_array)
            sim_results[i] = self._calc_metric(shuffled, initial_capital, metric)

        return self._build_result(sim_results, metric, original_value)

    def simulate_return_resample(
        self,
        returns: pd.Series,
        initial_capital: float = 1_000_000.0,
        metric: str = "total_return",
    ) -> MonteCarloResult:
        """Simulate by bootstrap resampling returns.

        Resamples returns with replacement to create alternative
        equity paths.

        Args:
            returns: Series of per-bar returns.
            initial_capital: Starting capital.
            metric: Metric to compute.

        Returns:
            MonteCarloResult with confidence intervals.
        """
        if len(returns) == 0:
            return MonteCarloResult(
                num_simulations=0, metric_name=metric,
                original_value=0.0, mean_value=0.0, median_value=0.0,
                p5=0.0, p25=0.0, p75=0.0, p95=0.0,
                confidence_95=(0.0, 0.0), probability_of_loss=1.0,
            )

        rng = np.random.default_rng(self.random_seed)
        ret_array = returns.values

        # Calculate original metric
        original_equity = initial_capital * (1 + pd.Series(ret_array)).cumprod()
        original_value = self._calc_equity_metric(original_equity, initial_capital, metric)

        # Run simulations
        sim_results = np.empty(self.num_simulations)

        for i in range(self.num_simulations):
            # Resample with replacement
            indices = rng.integers(0, len(ret_array), size=len(ret_array))
            resampled = ret_array[indices]
            equity = initial_capital * (1 + pd.Series(resampled)).cumprod()
            sim_results[i] = self._calc_equity_metric(equity, initial_capital, metric)

        return self._build_result(sim_results, metric, original_value)

    def simulate_price_path(
        self,
        mean_return: float,
        std_return: float,
        n_bars: int,
        initial_capital: float = 1_000_000.0,
        metric: str = "total_return",
    ) -> MonteCarloResult:
        """Simulate by generating random price paths.

        Generates price paths from a normal distribution with
        given mean and std of returns.

        Args:
            mean_return: Mean per-bar return.
            std_return: Std of per-bar returns.
            n_bars: Number of bars per simulation.
            initial_capital: Starting capital.
            metric: Metric to compute.

        Returns:
            MonteCarloResult with confidence intervals.
        """
        rng = np.random.default_rng(self.random_seed)

        sim_results = np.empty(self.num_simulations)

        for i in range(self.num_simulations):
            random_returns = rng.normal(mean_return, std_return, size=n_bars)
            equity = initial_capital * np.cumprod(1 + random_returns)
            sim_results[i] = self._calc_equity_metric(
                pd.Series(equity), initial_capital, metric
            )

        return self._build_result(sim_results, metric, original_value=mean_return * n_bars)

    @staticmethod
    def _calc_metric(
        pnl_array: np.ndarray,
        initial_capital: float,
        metric: str,
    ) -> float:
        """Calculate a metric from a P&L array."""
        cumulative_pnl = np.cumsum(pnl_array)
        equity = initial_capital + cumulative_pnl

        if metric == "total_return":
            return float(equity[-1] / initial_capital - 1)
        elif metric == "max_drawdown":
            peak = np.maximum.accumulate(equity)
            dd = (equity - peak) / peak
            return float(np.min(dd))
        elif metric == "sharpe":
            returns = np.diff(equity) / equity[:-1]
            return float(np.mean(returns) / (np.std(returns) + 1e-10) * np.sqrt(252))
        else:
            return float(equity[-1] / initial_capital - 1)

    @staticmethod
    def _calc_equity_metric(
        equity: pd.Series,
        initial_capital: float,
        metric: str,
    ) -> float:
        """Calculate a metric from an equity curve."""
        if metric == "total_return":
            return float(equity.iloc[-1] / initial_capital - 1)
        elif metric == "max_drawdown":
            peak = equity.cummax()
            dd = (equity - peak) / peak
            return float(dd.min())
        elif metric == "sharpe":
            returns = equity.pct_change().dropna()
            return float(returns.mean() / (returns.std() + 1e-10) * np.sqrt(252))
        else:
            return float(equity.iloc[-1] / initial_capital - 1)

    def _build_result(
        self,
        sim_results: np.ndarray,
        metric: str,
        original_value: float,
    ) -> MonteCarloResult:
        """Build MonteCarloResult from simulation results."""
        return MonteCarloResult(
            num_simulations=self.num_simulations,
            metric_name=metric,
            original_value=original_value,
            mean_value=float(np.mean(sim_results)),
            median_value=float(np.median(sim_results)),
            p5=float(np.percentile(sim_results, 5)),
            p25=float(np.percentile(sim_results, 25)),
            p75=float(np.percentile(sim_results, 75)),
            p95=float(np.percentile(sim_results, 95)),
            confidence_95=(
                float(np.percentile(sim_results, 2.5)),
                float(np.percentile(sim_results, 97.5)),
            ),
            probability_of_loss=float(np.mean(sim_results < 0)),
        )
