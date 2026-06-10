"""Walk-Forward Analysis — Mandatory Validation.

Implements walk-forward analysis for robust strategy validation.
This is MANDATORY for all strategies before live deployment.

Walk-forward analysis addresses overfitting by:
1. Training on a rolling window of data
2. Testing on the subsequent out-of-sample window
3. Rolling forward and repeating
4. Aggregating out-of-sample results

Reference: Robert Pardo, "The Evaluation and Optimization of Trading Strategies"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

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


class WalkForwardAnalyzer:
    """Walk-Forward Analysis for strategy validation.

    Implements anchored and rolling walk-forward analysis with
    configurable train/test windows. This is MANDATORY for
    validating that a strategy is not overfit.

    Usage:
        analyzer = WalkForwardAnalyzer(engine, train_window=252, test_window=63)
        results = analyzer.analyze(prices, signals)
    """

    def __init__(
        self,
        engine: Any,  # BacktestEngine
        train_window: int = 252,
        test_window: int = 63,
        anchored: bool = False,
        min_observations: int = 60,
    ) -> None:
        """Initialize walk-forward analyzer.

        Args:
            engine: BacktestEngine instance.
            train_window: Training window in bars.
            test_window: Test window in bars.
            anchored: If True, use anchored walk-forward (expanding window).
            min_observations: Minimum observations required for a valid window.
        """
        self.engine = engine
        self.train_window = train_window
        self.test_window = test_window
        self.anchored = anchored
        self.min_observations = min_observations

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
        """
        n_bars = len(prices)
        total_window = self.train_window + self.test_window

        if n_bars < total_window:
            logger.warning(
                "Insufficient data for walk-forward: %d bars < %d required",
                n_bars, total_window,
            )
            return {"windows": [], "aggregate": {}, "degradation_stats": {}}

        windows: List[WalkForwardResult] = []
        oos_returns: List[float] = []
        oos_sharpes: List[float] = []

        start = 0
        while start + total_window <= n_bars:
            # Define windows
            if self.anchored:
                train_end = start + self.train_window
                train_start = 0
            else:
                train_start = start
                train_end = start + self.train_window

            test_start = train_end
            test_end = test_start + self.test_window

            if test_end > n_bars:
                break

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

            # Roll forward
            start += self.test_window

        # Calculate aggregate statistics
        aggregate = self._calculate_aggregate(windows, oos_returns, oos_sharpes)
        degradation_stats = self._calculate_degradation_stats(windows)

        return {
            "windows": windows,
            "aggregate": aggregate,
            "degradation_stats": degradation_stats,
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
            "avg_oos_sharpe": float(np.mean(oos_sharpes)) if oos_sharpes else 0.0,
            "oos_sharpe_std": float(np.std(oos_sharpes)) if len(oos_sharpes) > 1 else 0.0,
            "win_rate": sum(1 for r in oos_returns if r > 0) / len(oos_returns) if oos_returns else 0.0,
            "worst_oos_return": min(oos_returns) if oos_returns else 0.0,
            "best_oos_return": max(oos_returns) if oos_returns else 0.0,
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
            "healthy_windows": sum(1 for d in degradation_ratios if d > 0.5),
            "total_windows": len(windows),
            "pass_rate": sum(1 for d in degradation_ratios if d > 0.5) / len(windows),
        }
