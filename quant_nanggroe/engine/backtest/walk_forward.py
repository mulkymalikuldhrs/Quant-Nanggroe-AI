"""Walk-Forward Analysis — Mandatory Validation.

Implements walk-forward analysis for robust strategy validation.
This is MANDATORY for all strategies before live deployment.

Walk-forward analysis addresses overfitting by:
1. Training on a rolling window of data
2. Testing on the subsequent out-of-sample window
3. Rolling forward and repeating
4. Aggregating out-of-sample results

Supported modes:
- Rolling: Fixed-size training window that slides forward
- Anchored: Expanding training window (anchored to start of data)
- Combinatorial Purged Cross-Validation (CPCV): Multiple overlapping train/test splits

Reference: Robert Pardo, "The Evaluation and Optimization of Trading Strategies"
Reference: Marcos López de Prado, "Advances in Financial Machine Learning" (for CPCV)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class WalkForwardResult:
    """Result from a single walk-forward window."""

    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    in_sample_return: float
    out_of_sample_return: float
    in_sample_sharpe: float
    out_of_sample_sharpe: float
    in_sample_max_dd: float
    out_of_sample_max_dd: float
    degradation_ratio: float  # OOS/IS performance ratio


@dataclass
class WalkForwardStability:
    """Stability metrics for walk-forward analysis.

    Measures how consistent strategy performance is across
    different time windows.
    """

    sharpe_stability: float = 0.0  # Std of OOS Sharpe ratios
    return_stability: float = 0.0  # Std of OOS returns
    sharpe_positive_rate: float = 0.0  # % of windows with positive OOS Sharpe
    return_positive_rate: float = 0.0  # % of windows with positive OOS return
    degradation_consistency: float = 0.0  # % of windows with degradation > 0.5
    sharpe_rank_correlation: float = 0.0  # IS vs OOS Sharpe rank correlation
    effective_tests: int = 0  # Number of effective independent tests


class WalkForwardAnalyzer:
    """Walk-Forward Analysis for strategy validation.

    Implements anchored, rolling, and combinatorial purged cross-validation
    walk-forward analysis with configurable train/test windows.
    This is MANDATORY for validating that a strategy is not overfit.

    Supported modes:
    - Rolling: Fixed-size training window slides forward
    - Anchored: Training window expands from the start
    - CPCV: Combinatorial purged cross-validation (de Prado)

    Usage:
        analyzer = WalkForwardAnalyzer(engine, train_window=252, test_window=63)
        results = analyzer.analyze(prices, signals)

        # Anchored walk-forward
        analyzer = WalkForwardAnalyzer(engine, mode="anchored", train_window=252, test_window=63)
        results = analyzer.analyze(prices, signals)

        # CPCV
        analyzer = WalkForwardAnalyzer(engine, mode="cpcv", n_groups=6, n_test_groups=2)
        results = analyzer.analyze(prices, signals)
    """

    def __init__(
        self,
        engine: Any,  # BacktestEngine
        train_window: int = 252,
        test_window: int = 63,
        mode: str = "rolling",
        anchored: bool = False,
        min_observations: int = 60,
        purge_gap: int = 0,
        # CPCV parameters
        n_groups: int = 6,
        n_test_groups: int = 2,
        embargo: int = 0,
    ) -> None:
        """Initialize walk-forward analyzer.

        Args:
            engine: BacktestEngine instance.
            train_window: Training window in bars.
            test_window: Test window in bars.
            mode: Walk-forward mode ('rolling', 'anchored', 'cpcv').
            anchored: If True, use anchored walk-forward (expanding window).
                     Equivalent to mode='anchored'.
            min_observations: Minimum observations required for a valid window.
            purge_gap: Number of bars between train and test to prevent leakage.
            n_groups: Number of groups for CPCV mode.
            n_test_groups: Number of test groups for CPCV mode.
            embargo: Number of bars to embargo after test period (CPCV).
        """
        self.engine = engine
        self.train_window = train_window
        self.test_window = test_window
        # Support backward compatibility: anchored=True implies mode='anchored'
        if anchored:
            self.mode = "anchored"
        else:
            self.mode = mode
        self.min_observations = min_observations
        self.purge_gap = purge_gap
        self.n_groups = n_groups
        self.n_test_groups = n_test_groups
        self.embargo = embargo

    def analyze(
        self,
        prices: pd.DataFrame,
        signals: pd.DataFrame,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Run walk-forward analysis.

        Args:
            prices: Price data with DatetimeIndex.
            signals: Signal data with same index.
            **kwargs: Additional arguments passed to engine.run().

        Returns:
            Dict with:
                - windows: List of WalkForwardResult for each window
                - aggregate: Aggregated performance metrics
                - degradation_stats: Statistics on IS vs OOS degradation
                - stability: WalkForwardStability metrics
                - mode: Walk-forward mode used
                - oos_equity_curve: Combined OOS equity curve
        """
        if self.mode == "cpcv":
            return self._analyze_cpcv(prices, signals, **kwargs)

        n_bars = len(prices)
        total_window = self.train_window + self.test_window + self.purge_gap

        if n_bars < total_window:
            logger.warning(
                "Insufficient data for walk-forward: %d bars < %d required",
                n_bars, total_window,
            )
            return {
                "windows": [], "aggregate": {}, "degradation_stats": {},
                "stability": WalkForwardStability(), "mode": self.mode,
                "oos_equity_curve": pd.Series(dtype=float),
            }

        windows: List[WalkForwardResult] = []
        oos_returns: List[float] = []
        oos_sharpes: List[float] = []
        oos_equity_parts: List[pd.Series] = []

        start = 0
        while start + total_window <= n_bars:
            # Define windows
            if self.mode == "anchored":
                train_end = start + self.train_window
                train_start = 0
            else:  # rolling
                train_start = start
                train_end = start + self.train_window

            # Apply purge gap
            test_start = train_end + self.purge_gap
            test_end = test_start + self.test_window

            if test_end > n_bars:
                break

            # Validate minimum observations
            if (train_end - train_start) < self.min_observations:
                start += self.test_window
                continue

            # Extract data slices
            train_prices = prices.iloc[train_start:train_end]
            train_signals = signals.iloc[train_start:train_end]
            test_prices = prices.iloc[test_start:test_end]
            test_signals = signals.iloc[test_start:test_end]

            # Run in-sample backtest
            is_result = self.engine.run(train_prices, train_signals, **kwargs)
            is_metrics = is_result.get("metrics", {})

            # Run out-of-sample backtest
            oos_result = self.engine.run(test_prices, test_signals, **kwargs)
            oos_metrics = oos_result.get("metrics", {})

            # Calculate degradation ratio
            is_sharpe = is_metrics.get("sharpe_ratio", 0.0)
            oos_sharpe = oos_metrics.get("sharpe_ratio", 0.0)
            degradation = oos_sharpe / is_sharpe if abs(is_sharpe) > 1e-10 else 0.0

            wf_result = WalkForwardResult(
                train_start=train_prices.index[0],
                train_end=train_prices.index[-1],
                test_start=test_prices.index[0],
                test_end=test_prices.index[-1],
                in_sample_return=is_metrics.get("total_return", 0.0),
                out_of_sample_return=oos_metrics.get("total_return", 0.0),
                in_sample_sharpe=is_sharpe,
                out_of_sample_sharpe=oos_sharpe,
                in_sample_max_dd=is_metrics.get("max_drawdown", 0.0),
                out_of_sample_max_dd=oos_metrics.get("max_drawdown", 0.0),
                degradation_ratio=degradation,
            )

            windows.append(wf_result)
            oos_returns.append(oos_metrics.get("total_return", 0.0))
            oos_sharpes.append(oos_sharpe)

            # Collect OOS equity curve parts
            oos_eq = oos_result.get("equity_curve", pd.Series(dtype=float))
            if len(oos_eq) > 0:
                oos_equity_parts.append(oos_eq)

            # Roll forward
            start += self.test_window

        # Calculate aggregate statistics
        aggregate = self._calculate_aggregate(windows, oos_returns, oos_sharpes)
        degradation_stats = self._calculate_degradation_stats(windows)
        stability = self._calculate_stability(windows, oos_sharpes, oos_returns)

        # Combine OOS equity curves
        oos_equity_curve = self._combine_oos_equity(oos_equity_parts)

        return {
            "windows": windows,
            "aggregate": aggregate,
            "degradation_stats": degradation_stats,
            "stability": stability,
            "mode": self.mode,
            "oos_equity_curve": oos_equity_curve,
        }

    def _analyze_cpcv(
        self,
        prices: pd.DataFrame,
        signals: pd.DataFrame,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Run Combinatorial Purged Cross-Validation (CPCV).

        Based on de Prado's CPCV method:
        1. Divide data into n_groups
        2. Form all combinations of n_test_groups for testing
        3. Train on remaining groups (with purge/embargo)
        4. Collect all OOS results

        Args:
            prices: Price data.
            signals: Signal data.
            **kwargs: Additional arguments.

        Returns:
            CPCV results dict.
        """
        n_bars = len(prices)
        group_size = n_bars // self.n_groups

        if group_size < self.min_observations:
            logger.warning(
                "CPCV: Group size %d < min_observations %d. Reducing n_groups.",
                group_size, self.min_observations,
            )
            self.n_groups = max(2, n_bars // self.min_observations)
            group_size = n_bars // self.n_groups

        # Generate all combinations of test groups
        from itertools import combinations
        test_combos = list(combinations(range(self.n_groups), self.n_test_groups))

        windows: List[WalkForwardResult] = []
        oos_returns: List[float] = []
        oos_sharpes: List[float] = []
        oos_equity_parts: List[pd.Series] = []

        for test_group_indices in test_combos:
            test_groups = set(test_group_indices)
            train_groups = set(range(self.n_groups)) - test_groups

            # Build train/test index masks
            train_indices = []
            test_indices = []

            for g in train_groups:
                start = g * group_size
                end = start + group_size if g < self.n_groups - 1 else n_bars
                train_indices.extend(range(start, min(end, n_bars)))

            for g in test_groups:
                start = g * group_size
                end = start + group_size if g < self.n_groups - 1 else n_bars
                # Apply embargo
                emb_start = start + self.embargo
                test_indices.extend(range(emb_start, min(end, n_bars)))

            if not train_indices or not test_indices:
                continue

            # Apply purge: remove indices from train that are within purge_gap of test
            if self.purge_gap > 0:
                test_set = set(test_indices)
                purged_train = []
                for idx in train_indices:
                    is_purged = any(
                        abs(idx - t) <= self.purge_gap
                        for t in test_set
                    )
                    if not is_purged:
                        purged_train.append(idx)
                train_indices = purged_train

            if len(train_indices) < self.min_observations:
                continue

            # Sort indices
            train_indices = sorted(train_indices)
            test_indices = sorted(test_indices)

            # Extract data slices
            train_prices = prices.iloc[train_indices]
            train_signals = signals.iloc[train_indices]
            test_prices = prices.iloc[test_indices]
            test_signals = signals.iloc[test_indices]

            if len(train_prices) < self.min_observations or len(test_prices) < 10:
                continue

            try:
                # Run in-sample backtest
                is_result = self.engine.run(train_prices, train_signals, **kwargs)
                is_metrics = is_result.get("metrics", {})

                # Run out-of-sample backtest
                oos_result = self.engine.run(test_prices, test_signals, **kwargs)
                oos_metrics = oos_result.get("metrics", {})
            except Exception as e:
                logger.warning(f"CPCV window failed: {e}")
                continue

            # Calculate degradation
            is_sharpe = is_metrics.get("sharpe_ratio", 0.0)
            oos_sharpe = oos_metrics.get("sharpe_ratio", 0.0)
            degradation = oos_sharpe / is_sharpe if abs(is_sharpe) > 1e-10 else 0.0

            wf_result = WalkForwardResult(
                train_start=train_prices.index[0],
                train_end=train_prices.index[-1],
                test_start=test_prices.index[0],
                test_end=test_prices.index[-1],
                in_sample_return=is_metrics.get("total_return", 0.0),
                out_of_sample_return=oos_metrics.get("total_return", 0.0),
                in_sample_sharpe=is_sharpe,
                out_of_sample_sharpe=oos_sharpe,
                in_sample_max_dd=is_metrics.get("max_drawdown", 0.0),
                out_of_sample_max_dd=oos_metrics.get("max_drawdown", 0.0),
                degradation_ratio=degradation,
            )

            windows.append(wf_result)
            oos_returns.append(oos_metrics.get("total_return", 0.0))
            oos_sharpes.append(oos_sharpe)

            # Collect OOS equity curve parts
            oos_eq = oos_result.get("equity_curve", pd.Series(dtype=float))
            if len(oos_eq) > 0:
                oos_equity_parts.append(oos_eq)

        # Calculate statistics
        aggregate = self._calculate_aggregate(windows, oos_returns, oos_sharpes)
        degradation_stats = self._calculate_degradation_stats(windows)
        stability = self._calculate_stability(windows, oos_sharpes, oos_returns)
        oos_equity_curve = self._combine_oos_equity(oos_equity_parts)

        return {
            "windows": windows,
            "aggregate": aggregate,
            "degradation_stats": degradation_stats,
            "stability": stability,
            "mode": "cpcv",
            "n_groups": self.n_groups,
            "n_test_groups": self.n_test_groups,
            "n_combinations": len(test_combos),
            "oos_equity_curve": oos_equity_curve,
        }

    def _calculate_aggregate(
        self,
        windows: List[WalkForwardResult],
        oos_returns: List[float],
        oos_sharpes: List[float],
    ) -> Dict[str, Any]:
        """Calculate aggregate walk-forward statistics."""
        if not windows:
            return {}

        return {
            "num_windows": len(windows),
            "avg_oos_return": float(np.mean(oos_returns)) if oos_returns else 0.0,
            "median_oos_return": float(np.median(oos_returns)) if oos_returns else 0.0,
            "std_oos_return": float(np.std(oos_returns)) if len(oos_returns) > 1 else 0.0,
            "avg_oos_sharpe": float(np.mean(oos_sharpes)) if oos_sharpes else 0.0,
            "median_oos_sharpe": float(np.median(oos_sharpes)) if oos_sharpes else 0.0,
            "oos_sharpe_std": float(np.std(oos_sharpes)) if len(oos_sharpes) > 1 else 0.0,
            "win_rate": sum(1 for r in oos_returns if r > 0) / len(oos_returns) if oos_returns else 0.0,
            "worst_oos_return": min(oos_returns) if oos_returns else 0.0,
            "best_oos_return": max(oos_returns) if oos_returns else 0.0,
            "avg_is_return": float(np.mean([w.in_sample_return for w in windows])),
            "avg_is_sharpe": float(np.mean([w.in_sample_sharpe for w in windows])),
            "avg_is_max_dd": float(np.mean([w.in_sample_max_dd for w in windows])),
            "avg_oos_max_dd": float(np.mean([w.out_of_sample_max_dd for w in windows])),
        }

    def _calculate_degradation_stats(
        self, windows: List[WalkForwardResult]
    ) -> Dict[str, Any]:
        """Calculate degradation statistics (IS vs OOS)."""
        if not windows:
            return {}

        degradation_ratios = [w.degradation_ratio for w in windows]

        return {
            "avg_degradation": float(np.mean(degradation_ratios)),
            "median_degradation": float(np.median(degradation_ratios)),
            "min_degradation": float(np.min(degradation_ratios)),
            "max_degradation": float(np.max(degradation_ratios)),
            "std_degradation": float(np.std(degradation_ratios)) if len(degradation_ratios) > 1 else 0.0,
            "healthy_windows": sum(1 for d in degradation_ratios if d > 0.5),
            "total_windows": len(windows),
            "pass_rate": sum(1 for d in degradation_ratios if d > 0.5) / len(windows),
        }

    def _calculate_stability(
        self,
        windows: List[WalkForwardResult],
        oos_sharpes: List[float],
        oos_returns: List[float],
    ) -> WalkForwardStability:
        """Calculate walk-forward stability metrics.

        Args:
            windows: List of walk-forward results.
            oos_sharpes: List of OOS Sharpe ratios.
            oos_returns: List of OOS returns.

        Returns:
            WalkForwardStability with stability metrics.
        """
        if not windows or len(oos_sharpes) < 2:
            return WalkForwardStability()

        # Sharpe stability (lower std = more stable)
        sharpe_stability = float(np.std(oos_sharpes))

        # Return stability
        return_stability = float(np.std(oos_returns))

        # Positive rate metrics
        sharpe_positive_rate = sum(1 for s in oos_sharpes if s > 0) / len(oos_sharpes)
        return_positive_rate = sum(1 for r in oos_returns if r > 0) / len(oos_returns)

        # Degradation consistency
        degradation_ratios = [w.degradation_ratio for w in windows]
        degradation_consistency = sum(1 for d in degradation_ratios if d > 0.5) / len(windows)

        # IS vs OOS Sharpe rank correlation (Spearman)
        is_sharpes = [w.in_sample_sharpe for w in windows]
        sharpe_rank_correlation = 0.0
        try:
            if len(is_sharpes) > 2:
                from scipy import stats as sp_stats
                corr, _ = sp_stats.spearmanr(is_sharpes, oos_sharpes)
                sharpe_rank_correlation = float(corr) if not np.isnan(corr) else 0.0
        except ImportError:
            # Manual rank correlation
            if len(is_sharpes) > 2:
                is_ranks = np.argsort(np.argsort(is_sharpes))
                oos_ranks = np.argsort(np.argsort(oos_sharpes))
                n = len(is_ranks)
                d_squared = np.sum((is_ranks - oos_ranks) ** 2)
                sharpe_rank_correlation = float(1 - 6 * d_squared / (n * (n ** 2 - 1)))

        # Effective number of tests (approximate)
        # For overlapping windows, the effective number is less than total windows
        n_windows = len(windows)
        overlap_ratio = max(0, 1 - self.test_window / self.train_window) if self.train_window > 0 else 0
        effective_tests = max(1, int(n_windows * (1 - overlap_ratio)))

        return WalkForwardStability(
            sharpe_stability=sharpe_stability,
            return_stability=return_stability,
            sharpe_positive_rate=sharpe_positive_rate,
            return_positive_rate=return_positive_rate,
            degradation_consistency=degradation_consistency,
            sharpe_rank_correlation=sharpe_rank_correlation,
            effective_tests=effective_tests,
        )

    @staticmethod
    def _combine_oos_equity(
        equity_parts: List[pd.Series],
    ) -> pd.Series:
        """Combine OOS equity curve parts into a single series.

        Uses the last known equity value of each window as the base
        for the next window's returns.

        Args:
            equity_parts: List of OOS equity curve Series.

        Returns:
            Combined equity curve Series.
        """
        if not equity_parts:
            return pd.Series(dtype=float)

        if len(equity_parts) == 1:
            return equity_parts[0]

        # Normalize each part to returns and chain them
        combined_values = []
        base_equity = 1.0

        for eq in equity_parts:
            if len(eq) < 2:
                continue
            returns = eq.pct_change().fillna(0.0)
            for ret in returns:
                base_equity *= (1 + ret)
                combined_values.append(base_equity)

        if not combined_values:
            return pd.Series(dtype=float)

        # Create a combined index
        all_indices = []
        for eq in equity_parts:
            all_indices.extend(eq.index.tolist())

        # Use sequential index if timestamps don't align well
        combined_index = all_indices[:len(combined_values)]

        return pd.Series(combined_values, index=combined_index[:len(combined_values)])
