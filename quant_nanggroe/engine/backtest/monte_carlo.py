"""Monte Carlo Simulation for Backtest Confidence Intervals.

Implements Monte Carlo simulation to estimate confidence intervals
for backtest results, addressing the randomness in trade sequencing
and providing robust performance estimates.

Methods:
- Trade shuffle: Randomly reorder trades to test sequence dependence
- Bootstrap resampling: Resample returns with replacement (non-parametric)
- Return resample: Bootstrap resample returns with replacement
- Parametric simulation: Generate paths from fitted distribution
- Price path: Generate random price paths from return distribution
- Regime-aware simulation: Account for market regime changes
- Confidence intervals for all metrics
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

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
    all_sim_values: Optional[np.ndarray] = None  # Raw simulation values


@dataclass
class MultiMetricMonteCarloResult:
    """Monte Carlo results across multiple metrics."""

    metrics: Dict[str, MonteCarloResult]
    num_simulations: int
    correlation_matrix: Optional[np.ndarray] = None  # Inter-metric correlations


@dataclass
class RegimeInfo:
    """Information about a market regime segment."""

    start_index: int
    end_index: int
    mean_return: float
    std_return: float
    label: str = ""


class MonteCarloSimulator:
    """Monte Carlo simulation for backtest confidence intervals.

    Provides robust estimates of strategy performance by resampling
    trade returns or equity curve returns thousands of times.

    Supports:
    - Trade shuffle simulation
    - Bootstrap resampling (non-parametric)
    - Parametric simulation (fitted distribution)
    - Regime-aware simulation
    - Multi-metric confidence intervals
    - Price path simulation

    Usage:
        simulator = MonteCarloSimulator(num_simulations=1000)
        result = simulator.simulate_trade_shuffle(trades, initial_capital)
        result = simulator.simulate_bootstrap(returns, initial_capital)
        result = simulator.simulate_parametric(returns, initial_capital)
    """

    def __init__(
        self,
        num_simulations: int = 1000,
        random_seed: Optional[int] = None,
        confidence_levels: Optional[List[float]] = None,
    ) -> None:
        """Initialize Monte Carlo simulator.

        Args:
            num_simulations: Number of Monte Carlo simulations to run.
            random_seed: Optional seed for reproducibility.
            confidence_levels: List of confidence levels for CIs (default: [0.90, 0.95, 0.99]).
        """
        self.num_simulations = num_simulations
        self.random_seed = random_seed
        self.confidence_levels = confidence_levels or [0.90, 0.95, 0.99]

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
            metric: Metric to compute ('total_return', 'max_drawdown', 'sharpe',
                   'sortino', 'calmar', 'win_rate').

        Returns:
            MonteCarloResult with confidence intervals.
        """
        if not trades_pnl:
            return self._empty_result(metric)

        rng = np.random.default_rng(self.random_seed)
        pnl_array = np.array(trades_pnl, dtype=float)

        # Calculate original metric
        original_value = self._calc_metric(pnl_array, initial_capital, metric)

        # Run simulations
        sim_results = np.empty(self.num_simulations)
        for i in range(self.num_simulations):
            shuffled = rng.permutation(pnl_array)
            sim_results[i] = self._calc_metric(shuffled, initial_capital, metric)

        return self._build_result(sim_results, metric, original_value)

    def simulate_bootstrap(
        self,
        returns: pd.Series,
        initial_capital: float = 1_000_000.0,
        metric: str = "total_return",
        block_size: Optional[int] = None,
    ) -> MonteCarloResult:
        """Simulate using bootstrap resampling (non-parametric).

        Resamples returns with replacement to create alternative
        equity paths. Supports block bootstrap for autocorrelated returns.

        Args:
            returns: Series of per-bar returns.
            initial_capital: Starting capital.
            metric: Metric to compute.
            block_size: Optional block size for block bootstrap.
                       If None, uses standard bootstrap (block_size=1).

        Returns:
            MonteCarloResult with confidence intervals.
        """
        if len(returns) < 2:
            return self._empty_result(metric)

        rng = np.random.default_rng(self.random_seed)
        ret_array = returns.values.astype(float)
        n = len(ret_array)

        # Calculate original metric
        original_equity = initial_capital * np.cumprod(1 + ret_array)
        original_value = self._calc_equity_metric(
            pd.Series(original_equity), initial_capital, metric
        )

        # Determine block size
        if block_size is None or block_size <= 1:
            # Standard bootstrap
            sim_results = np.empty(self.num_simulations)
            for i in range(self.num_simulations):
                indices = rng.integers(0, n, size=n)
                resampled = ret_array[indices]
                equity = initial_capital * np.cumprod(1 + resampled)
                sim_results[i] = self._calc_equity_metric(
                    pd.Series(equity), initial_capital, metric
                )
        else:
            # Block bootstrap
            sim_results = np.empty(self.num_simulations)
            for i in range(self.num_simulations):
                resampled = self._block_bootstrap(rng, ret_array, block_size, n)
                equity = initial_capital * np.cumprod(1 + resampled)
                sim_results[i] = self._calc_equity_metric(
                    pd.Series(equity), initial_capital, metric
                )

        return self._build_result(sim_results, metric, original_value)

    def simulate_return_resample(
        self,
        returns: pd.Series,
        initial_capital: float = 1_000_000.0,
        metric: str = "total_return",
    ) -> MonteCarloResult:
        """Simulate by bootstrap resampling returns.

        This is an alias for simulate_bootstrap with block_size=None.

        Args:
            returns: Series of per-bar returns.
            initial_capital: Starting capital.
            metric: Metric to compute.

        Returns:
            MonteCarloResult with confidence intervals.
        """
        return self.simulate_bootstrap(returns, initial_capital, metric, block_size=None)

    def simulate_parametric(
        self,
        returns: pd.Series,
        initial_capital: float = 1_000_000.0,
        metric: str = "total_return",
        distribution: str = "normal",
        n_bars: Optional[int] = None,
    ) -> MonteCarloResult:
        """Simulate using parametric distribution fitting.

        Fits a distribution to the returns and generates random paths
        from the fitted distribution. Supports normal, student-t, and
        skewed-normal distributions.

        Args:
            returns: Series of per-bar returns to fit.
            initial_capital: Starting capital.
            metric: Metric to compute.
            distribution: Distribution type ('normal', 'student_t', 'skew_normal').
            n_bars: Number of bars per simulation. Defaults to length of returns.

        Returns:
            MonteCarloResult with confidence intervals.
        """
        if len(returns) < 2:
            return self._empty_result(metric)

        rng = np.random.default_rng(self.random_seed)
        ret_array = returns.values.astype(float)
        n = n_bars or len(ret_array)

        # Fit distribution parameters
        mean_ret = float(np.mean(ret_array))
        std_ret = float(np.std(ret_array, ddof=1))

        # Calculate original metric
        original_equity = initial_capital * np.cumprod(1 + ret_array)
        original_value = self._calc_equity_metric(
            pd.Series(original_equity), initial_capital, metric
        )

        sim_results = np.empty(self.num_simulations)

        if distribution == "normal":
            for i in range(self.num_simulations):
                random_returns = rng.normal(mean_ret, std_ret, size=n)
                equity = initial_capital * np.cumprod(1 + random_returns)
                sim_results[i] = self._calc_equity_metric(
                    pd.Series(equity), initial_capital, metric
                )

        elif distribution == "student_t":
            # Fit student-t using method of moments
            from scipy import stats as sp_stats
            try:
                # Fit t-distribution
                t_df, t_loc, t_scale = sp_stats.t.fit(ret_array)
                for i in range(self.num_simulations):
                    random_returns = sp_stats.t.rvs(
                        df=t_df, loc=t_loc, scale=t_scale,
                        size=n, random_state=rng
                    )
                    equity = initial_capital * np.cumprod(1 + random_returns)
                    sim_results[i] = self._calc_equity_metric(
                        pd.Series(equity), initial_capital, metric
                    )
            except ImportError:
                logger.warning("scipy not available, falling back to normal distribution")
                for i in range(self.num_simulations):
                    random_returns = rng.normal(mean_ret, std_ret, size=n)
                    equity = initial_capital * np.cumprod(1 + random_returns)
                    sim_results[i] = self._calc_equity_metric(
                        pd.Series(equity), initial_capital, metric
                    )

        elif distribution == "skew_normal":
            # Approximate skewed normal using mix of normal and chi-squared
            try:
                from scipy import stats as sp_stats
                skewness = float(sp_stats.skew(ret_array))
                # Use skewed normal approximation
                for i in range(self.num_simulations):
                    # Generate via normal + skew adjustment
                    random_returns = rng.normal(mean_ret, std_ret, size=n)
                    if abs(skewness) > 0.1:
                        # Apply simple skew correction
                        skew_correction = skewness * std_ret * 0.1
                        random_returns += skew_correction * (random_returns - mean_ret) / (std_ret + 1e-10)
                    equity = initial_capital * np.cumprod(1 + random_returns)
                    sim_results[i] = self._calc_equity_metric(
                        pd.Series(equity), initial_capital, metric
                    )
            except ImportError:
                logger.warning("scipy not available, falling back to normal distribution")
                for i in range(self.num_simulations):
                    random_returns = rng.normal(mean_ret, std_ret, size=n)
                    equity = initial_capital * np.cumprod(1 + random_returns)
                    sim_results[i] = self._calc_equity_metric(
                        pd.Series(equity), initial_capital, metric
                    )
        else:
            raise ValueError(f"Unknown distribution: {distribution}")

        return self._build_result(sim_results, metric, original_value)

    def simulate_regime_aware(
        self,
        returns: pd.Series,
        initial_capital: float = 1_000_000.0,
        metric: str = "total_return",
        n_regimes: int = 2,
        n_bars: Optional[int] = None,
    ) -> MonteCarloResult:
        """Simulate with regime-awareness.

        Detects market regimes (e.g., bull/bear, high/low volatility)
        and generates returns that respect regime transitions.

        Args:
            returns: Series of per-bar returns.
            initial_capital: Starting capital.
            metric: Metric to compute.
            n_regimes: Number of regimes to detect.
            n_bars: Number of bars per simulation. Defaults to length of returns.

        Returns:
            MonteCarloResult with confidence intervals.
        """
        if len(returns) < 30:
            return self._empty_result(metric)

        rng = np.random.default_rng(self.random_seed)
        ret_array = returns.values.astype(float)
        n = n_bars or len(ret_array)

        # Detect regimes using simple volatility clustering
        regimes = self._detect_regimes(ret_array, n_regimes)

        # Calculate original metric
        original_equity = initial_capital * np.cumprod(1 + ret_array)
        original_value = self._calc_equity_metric(
            pd.Series(original_equity), initial_capital, metric
        )

        # Estimate transition matrix
        transition_matrix = self._estimate_transition_matrix(regimes, n_regimes)

        # Calculate per-regime statistics
        regime_stats = []
        for r in range(n_regimes):
            mask = regimes == r
            regime_returns = ret_array[mask]
            if len(regime_returns) > 1:
                regime_stats.append({
                    "mean": float(np.mean(regime_returns)),
                    "std": float(np.std(regime_returns, ddof=1)),
                    "prob": float(np.mean(mask)),
                })
            else:
                regime_stats.append({
                    "mean": float(np.mean(ret_array)),
                    "std": float(np.std(ret_array, ddof=1)),
                    "prob": 1.0 / n_regimes,
                })

        # Generate regime-aware simulations
        sim_results = np.empty(self.num_simulations)

        for i in range(self.num_simulations):
            sim_returns = np.empty(n)
            current_regime = rng.integers(0, n_regimes)

            for j in range(n):
                stats = regime_stats[current_regime]
                sim_returns[j] = rng.normal(stats["mean"], stats["std"])

                # Transition to next regime
                probs = transition_matrix[current_regime]
                current_regime = rng.choice(n_regimes, p=probs)

            equity = initial_capital * np.cumprod(1 + sim_returns)
            sim_results[i] = self._calc_equity_metric(
                pd.Series(equity), initial_capital, metric
            )

        return self._build_result(sim_results, metric, original_value)

    def simulate_price_path(
        self,
        mean_return: float,
        std_return: float,
        n_bars: int,
        initial_capital: float = 1_000_000.0,
        metric: str = "total_return",
    ) -> MonteCarloResult:
        """Simulate by generating random price paths from a normal distribution.

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

        return self._build_result(
            sim_results, metric, original_value=mean_return * n_bars
        )

    def simulate_multi_metric(
        self,
        returns: pd.Series,
        initial_capital: float = 1_000_000.0,
        metrics: Optional[List[str]] = None,
        method: str = "bootstrap",
    ) -> MultiMetricMonteCarloResult:
        """Run Monte Carlo simulation for multiple metrics simultaneously.

        Args:
            returns: Series of per-bar returns.
            initial_capital: Starting capital.
            metrics: List of metrics to compute. Defaults to all supported.
            method: Simulation method ('bootstrap', 'parametric', 'regime_aware').

        Returns:
            MultiMetricMonteCarloResult with results for each metric.
        """
        if metrics is None:
            metrics = ["total_return", "max_drawdown", "sharpe_ratio", "sortino_ratio"]

        results: Dict[str, MonteCarloResult] = {}

        for metric in metrics:
            if method == "bootstrap":
                results[metric] = self.simulate_bootstrap(
                    returns, initial_capital, metric
                )
            elif method == "parametric":
                results[metric] = self.simulate_parametric(
                    returns, initial_capital, metric
                )
            elif method == "regime_aware":
                results[metric] = self.simulate_regime_aware(
                    returns, initial_capital, metric
                )
            else:
                raise ValueError(f"Unknown simulation method: {method}")

        return MultiMetricMonteCarloResult(
            metrics=results,
            num_simulations=self.num_simulations,
        )

    # ── Metric computation ────────────────────────────────────────────

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
            dd = (equity - peak) / np.maximum(peak, 1e-10)
            return float(np.min(dd))
        elif metric in ("sharpe", "sharpe_ratio"):
            returns = np.diff(equity) / np.maximum(equity[:-1], 1e-10)
            if len(returns) < 2 or np.std(returns) < 1e-10:
                return 0.0
            return float(np.mean(returns) / np.std(returns) * np.sqrt(252))
        elif metric in ("sortino", "sortino_ratio"):
            returns = np.diff(equity) / np.maximum(equity[:-1], 1e-10)
            downside = returns[returns < 0]
            if len(downside) < 2 or np.std(downside) < 1e-10:
                return 0.0
            return float(np.mean(returns) / np.std(downside) * np.sqrt(252))
        elif metric in ("calmar", "calmar_ratio"):
            total_ret = float(equity[-1] / initial_capital - 1)
            peak = np.maximum.accumulate(equity)
            dd = (equity - peak) / np.maximum(peak, 1e-10)
            max_dd = abs(float(np.min(dd)))
            if max_dd < 1e-10:
                return 0.0
            return total_ret / max_dd
        elif metric == "win_rate":
            wins = np.sum(pnl_array > 0)
            return float(wins / len(pnl_array)) if len(pnl_array) > 0 else 0.0
        else:
            return float(equity[-1] / initial_capital - 1)

    @staticmethod
    def _calc_equity_metric(
        equity: pd.Series,
        initial_capital: float,
        metric: str,
    ) -> float:
        """Calculate a metric from an equity curve."""
        if len(equity) < 2:
            return 0.0

        if metric == "total_return":
            return float(equity.iloc[-1] / initial_capital - 1)
        elif metric == "max_drawdown":
            peak = equity.cummax()
            dd = (equity - peak) / np.maximum(peak, 1e-10)
            return float(dd.min())
        elif metric in ("sharpe", "sharpe_ratio"):
            returns = equity.pct_change().dropna()
            if len(returns) < 2 or returns.std() < 1e-10:
                return 0.0
            return float(returns.mean() / returns.std() * np.sqrt(252))
        elif metric in ("sortino", "sortino_ratio"):
            returns = equity.pct_change().dropna()
            downside = returns[returns < 0]
            if len(downside) < 2 or downside.std() < 1e-10:
                return 0.0
            return float(returns.mean() / downside.std() * np.sqrt(252))
        elif metric in ("calmar", "calmar_ratio"):
            total_ret = float(equity.iloc[-1] / initial_capital - 1)
            peak = equity.cummax()
            dd = (equity - peak) / np.maximum(peak, 1e-10)
            max_dd = abs(float(dd.min()))
            if max_dd < 1e-10:
                return 0.0
            return total_ret / max_dd
        elif metric == "win_rate":
            returns = equity.pct_change().dropna()
            if len(returns) == 0:
                return 0.0
            return float((returns > 0).mean())
        else:
            return float(equity.iloc[-1] / initial_capital - 1)

    # ── Confidence intervals ──────────────────────────────────────────

    def compute_confidence_intervals(
        self,
        values: np.ndarray,
    ) -> Dict[float, Tuple[float, float]]:
        """Compute confidence intervals at specified levels.

        Args:
            values: Array of simulated metric values.

        Returns:
            Dict mapping confidence level to (lower, upper) bounds.
        """
        result = {}
        for level in self.confidence_levels:
            alpha = (1 - level) / 2
            lower = float(np.percentile(values, alpha * 100))
            upper = float(np.percentile(values, (1 - alpha) * 100))
            result[level] = (lower, upper)
        return result

    # ── Regime detection ──────────────────────────────────────────────

    @staticmethod
    def _detect_regimes(
        returns: np.ndarray,
        n_regimes: int = 2,
        window: int = 21,
    ) -> np.ndarray:
        """Detect market regimes using rolling volatility clustering.

        Uses k-means-like clustering on rolling volatility to identify
        distinct market regimes.

        Args:
            returns: Array of per-bar returns.
            n_regimes: Number of regimes to detect.
            window: Rolling window for volatility calculation.

        Returns:
            Array of regime labels (0 to n_regimes-1) for each bar.
        """
        n = len(returns)
        if n < window * 2:
            # Not enough data for regime detection, return single regime
            return np.zeros(n, dtype=int)

        # Calculate rolling volatility
        rolling_vol = np.full(n, np.nan)
        for i in range(window - 1, n):
            rolling_vol[i] = np.std(returns[i - window + 1:i + 1], ddof=1)

        # Fill NaN with overall mean
        valid_vol = rolling_vol[~np.isnan(rolling_vol)]
        if len(valid_vol) == 0:
            return np.zeros(n, dtype=int)

        mean_vol = np.mean(valid_vol)
        rolling_vol = np.where(np.isnan(rolling_vol), mean_vol, rolling_vol)

        # Simple threshold-based clustering for 2 regimes
        if n_regimes == 2:
            median_vol = np.median(rolling_vol)
            regimes = (rolling_vol > median_vol).astype(int)
        else:
            # Quantile-based clustering for more regimes
            quantiles = np.linspace(0, 100, n_regimes + 1)
            thresholds = np.percentile(rolling_vol, quantiles[1:-1])
            regimes = np.digitize(rolling_vol, thresholds)

        return regimes

    @staticmethod
    def _estimate_transition_matrix(
        regimes: np.ndarray,
        n_regimes: int,
    ) -> np.ndarray:
        """Estimate Markov transition matrix from regime sequence.

        Args:
            regimes: Array of regime labels.
            n_regimes: Number of regimes.

        Returns:
            Transition probability matrix (n_regimes x n_regimes).
        """
        transition_counts = np.zeros((n_regimes, n_regimes))

        for i in range(len(regimes) - 1):
            from_regime = int(regimes[i])
            to_regime = int(regimes[i + 1])
            if 0 <= from_regime < n_regimes and 0 <= to_regime < n_regimes:
                transition_counts[from_regime, to_regime] += 1

        # Normalize rows
        row_sums = transition_counts.sum(axis=1, keepdims=True)
        row_sums = np.where(row_sums == 0, 1, row_sums)
        transition_matrix = transition_counts / row_sums

        # Ensure each row sums to 1
        for i in range(n_regimes):
            row_sum = transition_matrix[i].sum()
            if row_sum < 1e-10:
                transition_matrix[i] = np.ones(n_regimes) / n_regimes

        return transition_matrix

    @staticmethod
    def _block_bootstrap(
        rng: np.random.Generator,
        data: np.ndarray,
        block_size: int,
        total_length: int,
    ) -> np.ndarray:
        """Generate a block bootstrap resample.

        Args:
            rng: Random number generator.
            data: Original data array.
            block_size: Size of each block.
            total_length: Desired length of resample.

        Returns:
            Resampled array of specified length.
        """
        n = len(data)
        result = []
        while len(result) < total_length:
            start = rng.integers(0, n - block_size + 1)
            block = data[start:start + block_size]
            result.extend(block.tolist())

        return np.array(result[:total_length])

    # ── Result builders ───────────────────────────────────────────────

    def _build_result(
        self,
        sim_results: np.ndarray,
        metric: str,
        original_value: float,
    ) -> MonteCarloResult:
        """Build MonteCarloResult from simulation results."""
        # Compute confidence intervals at all specified levels
        ci = self.compute_confidence_intervals(sim_results)

        # Use 95% CI for the main result
        confidence_95 = ci.get(0.95, (
            float(np.percentile(sim_results, 2.5)),
            float(np.percentile(sim_results, 97.5)),
        ))

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
            confidence_95=confidence_95,
            probability_of_loss=float(np.mean(sim_results < 0)),
            all_sim_values=sim_results,
        )

    def _empty_result(self, metric: str) -> MonteCarloResult:
        """Return empty MonteCarloResult when no data is available."""
        return MonteCarloResult(
            num_simulations=0,
            metric_name=metric,
            original_value=0.0,
            mean_value=0.0,
            median_value=0.0,
            p5=0.0,
            p25=0.0,
            p75=0.0,
            p95=0.0,
            confidence_95=(0.0, 0.0),
            probability_of_loss=1.0,
        )
