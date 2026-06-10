"""
Walk-Forward Analysis — Robust Out-of-Sample Strategy Validation
================================================================
Implements walk-forward optimization to measure strategy robustness
and detect overfitting. Splits data into rolling train/test windows,
optimizes on in-sample data, and evaluates on out-of-sample data.

Features:
    - Rolling and anchored walk-forward windows
    - In-sample and out-of-sample performance tracking
    - Degradation analysis (OOS vs IS performance drop)
    - Parameter optimization across windows
    - Statistical significance testing

Walk-forward is the gold standard for strategy validation:
    1. Optimize parameters on training window
    2. Apply optimized parameters to test window
    3. Roll forward and repeat
    4. Aggregate out-of-sample results

Usage:
    analyzer = WalkForwardAnalyzer(train_pct=0.7, test_pct=0.3, n_splits=5)
    result = analyzer.run(data, strategy_func, param_grid)
    print(f"OOS Sharpe: {result.out_of_sample_sharpe:.2f}")
    print(f"Degradation: {result.degradation_pct:.1f}%")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

import numpy as np
import pandas as pd

from quant_nanggroe_ai.backtest.engine import BacktestEngine, BacktestResult, StrategyFunc
from quant_nanggroe_ai.backtest.metrics import BacktestMetrics

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# DATA MODELS
# ══════════════════════════════════════════════════════════════════════


@dataclass
class WindowResult:
    """Result from a single walk-forward window."""

    window_idx: int
    train_start: int
    train_end: int
    test_start: int
    test_end: int
    train_result: BacktestResult | None = None
    test_result: BacktestResult | None = None
    best_params: dict[str, Any] = field(default_factory=dict)
    train_sharpe: float = 0.0
    test_sharpe: float = 0.0
    train_return_pct: float = 0.0
    test_return_pct: float = 0.0
    train_max_dd_pct: float = 0.0
    test_max_dd_pct: float = 0.0


class WalkForwardResult:
    """
    Aggregated result from walk-forward analysis.

    Provides comprehensive statistics across all windows
    and comparison of in-sample vs out-of-sample performance.
    """

    def __init__(self) -> None:
        self.windows: list[WindowResult] = []
        self.in_sample_sharpes: list[float] = []
        self.out_of_sample_sharpes: list[float] = []
        self.in_sample_returns: list[float] = []
        self.out_of_sample_returns: list[float] = []
        self.in_sample_max_dds: list[float] = []
        self.out_of_sample_max_dds: list[float] = []
        self.all_test_returns: list[float] = []
        self.all_test_trades: list[Any] = []

    @property
    def avg_in_sample_sharpe(self) -> float:
        """Average in-sample Sharpe ratio across windows."""
        return float(np.mean(self.in_sample_sharpes)) if self.in_sample_sharpes else 0.0

    @property
    def avg_out_of_sample_sharpe(self) -> float:
        """Average out-of-sample Sharpe ratio across windows."""
        return float(np.mean(self.out_of_sample_sharpes)) if self.out_of_sample_sharpes else 0.0

    @property
    def avg_in_sample_return(self) -> float:
        """Average in-sample return % across windows."""
        return float(np.mean(self.in_sample_returns)) if self.in_sample_returns else 0.0

    @property
    def avg_out_of_sample_return(self) -> float:
        """Average out-of-sample return % across windows."""
        return float(np.mean(self.out_of_sample_returns)) if self.out_of_sample_returns else 0.0

    @property
    def degradation(self) -> float:
        """
        Performance degradation from IS to OOS.

        degradation = 1 - (OOS_Sharpe / IS_Sharpe)

        Values:
        - < 0.3: Low degradation (strategy is robust)
        - 0.3 - 0.6: Moderate degradation (some overfitting)
        - > 0.6: High degradation (likely overfit)
        - > 1.0: Strategy loses money OOS (severe overfitting)
        """
        if not self.in_sample_sharpes or self.avg_in_sample_sharpe == 0:
            return 0.0
        return 1 - (self.avg_out_of_sample_sharpe / self.avg_in_sample_sharpe)

    @property
    def degradation_pct(self) -> float:
        """Degradation as a percentage."""
        return self.degradation * 100

    @property
    def is_robust(self) -> bool:
        """
        Whether the strategy passes robustness checks.

        A strategy is considered robust if:
        - OOS Sharpe > 0
        - Degradation < 0.5 (less than 50% drop)
        - OOS return is positive
        """
        return (
            self.avg_out_of_sample_sharpe > 0
            and self.degradation < 0.5
            and self.avg_out_of_sample_return > 0
        )

    @property
    def overall_oos_sharpe(self) -> float:
        """Sharpe ratio calculated from all concatenated OOS returns."""
        if not self.all_test_returns:
            return 0.0
        metrics = BacktestMetrics()
        return metrics.sharpe_ratio(self.all_test_returns)

    def summary(self) -> dict[str, Any]:
        """Generate a summary dict of the walk-forward analysis."""
        return {
            "n_windows": len(self.windows),
            "avg_is_sharpe": round(self.avg_in_sample_sharpe, 4),
            "avg_oos_sharpe": round(self.avg_out_of_sample_sharpe, 4),
            "overall_oos_sharpe": round(self.overall_oos_sharpe, 4),
            "avg_is_return_pct": round(self.avg_in_sample_return, 2),
            "avg_oos_return_pct": round(self.avg_out_of_sample_return, 2),
            "degradation_pct": round(self.degradation_pct, 2),
            "is_robust": self.is_robust,
            "total_oos_trades": len(self.all_test_trades),
            "windows": [
                {
                    "idx": w.window_idx,
                    "train": f"{w.train_start}:{w.train_end}",
                    "test": f"{w.test_start}:{w.test_end}",
                    "is_sharpe": round(w.train_sharpe, 4),
                    "oos_sharpe": round(w.test_sharpe, 4),
                    "is_return": round(w.train_return_pct, 2),
                    "oos_return": round(w.test_return_pct, 2),
                    "best_params": w.best_params,
                }
                for w in self.windows
            ],
        }


# ══════════════════════════════════════════════════════════════════════
# WALK-FORWARD ANALYZER
# ══════════════════════════════════════════════════════════════════════


class WalkForwardAnalyzer:
    """
    Walk-forward analysis engine for strategy validation.

    Splits data into rolling or anchored train/test windows,
    optimizes strategy parameters on training data, and evaluates
    on out-of-sample test data.

    Args:
        train_pct: Fraction of each window for training (0.0 - 1.0)
        test_pct: Fraction of each window for testing (0.0 - 1.0)
        n_splits: Number of walk-forward splits
        anchored: If True, training window expands; if False, it rolls
        purge_gap: Number of bars between train and test to prevent leakage
        initial_capital: Starting capital for each backtest
        commission: Commission rate for backtests
        optimize_func: Optional function to optimize strategy parameters

    Example:
        analyzer = WalkForwardAnalyzer(
            train_pct=0.7, test_pct=0.3, n_splits=5
        )
        result = analyzer.run(data, my_strategy, param_grid={"period": [10, 20, 30]})
        if result.is_robust:
            print("Strategy is robust!")
    """

    def __init__(
        self,
        train_pct: float = 0.7,
        test_pct: float = 0.3,
        n_splits: int = 5,
        anchored: bool = False,
        purge_gap: int = 0,
        initial_capital: float = 100_000.0,
        commission: float = 0.001,
        optimize_func: Callable[..., dict[str, Any]] | None = None,
    ) -> None:
        if train_pct + test_pct > 1.0:
            raise ValueError("train_pct + test_pct cannot exceed 1.0")
        if n_splits < 1:
            raise ValueError("n_splits must be at least 1")

        self._train_pct = train_pct
        self._test_pct = test_pct
        self._n_splits = n_splits
        self._anchored = anchored
        self._purge_gap = purge_gap
        self._initial_capital = initial_capital
        self._commission = commission
        self._optimize_func = optimize_func

    def run(
        self,
        data: pd.DataFrame | list[dict[str, Any]],
        strategy_func: StrategyFunc,
        param_grid: dict[str, list[Any]] | None = None,
    ) -> WalkForwardResult:
        """
        Run walk-forward analysis.

        For each split:
        1. Extract training and test windows
        2. Optimize parameters on training data (if param_grid provided)
        3. Run backtest with best parameters on test data
        4. Record in-sample and out-of-sample results

        Args:
            data: OHLCV data as DataFrame or list of dicts
            strategy_func: Strategy function to evaluate
            param_grid: Optional parameter grid for optimization

        Returns:
            WalkForwardResult with comprehensive analysis
        """
        # Normalize data
        if isinstance(data, pd.DataFrame):
            total_bars = len(data)
        else:
            total_bars = len(data)

        if total_bars < 50:
            logger.error("Insufficient data for walk-forward analysis (%d bars)", total_bars)
            return WalkForwardResult()

        # Calculate window boundaries
        windows = self._generate_windows(total_bars)
        if not windows:
            logger.error("Could not generate any walk-forward windows")
            return WalkForwardResult()

        logger.info(
            "Walk-forward analysis: %d splits, %d total bars, anchored=%s",
            len(windows), total_bars, self._anchored,
        )

        result = WalkForwardResult()

        for window in windows:
            window_result = self._run_window(
                data, strategy_func, window, param_grid
            )
            result.windows.append(window_result)

            # Aggregate statistics
            result.in_sample_sharpes.append(window_result.train_sharpe)
            result.out_of_sample_sharpes.append(window_result.test_sharpe)
            result.in_sample_returns.append(window_result.train_return_pct)
            result.out_of_sample_returns.append(window_result.test_return_pct)
            result.in_sample_max_dds.append(window_result.train_max_dd_pct)
            result.out_of_sample_max_dds.append(window_result.test_max_dd_pct)

            if window_result.test_result and window_result.test_result.returns:
                result.all_test_returns.extend(window_result.test_result.returns)
            if window_result.test_result and window_result.test_result.trades:
                result.all_test_trades.extend(window_result.test_result.trades)

            logger.info(
                "Window %d: IS Sharpe=%.2f, OOS Sharpe=%.2f, IS Return=%.1f%%, OOS Return=%.1f%%",
                window_result.window_idx,
                window_result.train_sharpe,
                window_result.test_sharpe,
                window_result.train_return_pct,
                window_result.test_return_pct,
            )

        logger.info(
            "Walk-forward complete: avg OOS Sharpe=%.2f, degradation=%.1f%%, robust=%s",
            result.avg_out_of_sample_sharpe,
            result.degradation_pct,
            result.is_robust,
        )

        return result

    def _generate_windows(self, total_bars: int) -> list[tuple[int, int, int, int]]:
        """
        Generate (train_start, train_end, test_start, test_end) tuples.

        For rolling windows, each window advances by the test window size.
        For anchored windows, the training start stays at 0.
        """
        windows = []

        # Calculate minimum window sizes
        window_size = total_bars // (self._n_splits + 1)
        if window_size < 20:
            logger.warning("Window size too small (%d bars), reducing n_splits", window_size)
            window_size = 30
            self._n_splits = max(1, total_bars // window_size - 1)

        train_size = int(window_size * self._train_pct)
        test_size = int(window_size * self._test_pct)

        if train_size < 20 or test_size < 10:
            logger.error("Train (%d) or test (%d) window too small", train_size, test_size)
            return []

        if self._anchored:
            # Anchored: training always starts from beginning
            for i in range(self._n_splits):
                train_end = train_size + i * test_size
                test_start = train_end + self._purge_gap
                test_end = test_start + test_size

                if test_end > total_bars:
                    test_end = total_bars
                if test_start >= total_bars:
                    break

                windows.append((0, train_end, test_start, test_end))
        else:
            # Rolling: both windows advance
            step = test_size
            for i in range(self._n_splits):
                train_start = i * step
                train_end = train_start + train_size
                test_start = train_end + self._purge_gap
                test_end = test_start + test_size

                if test_end > total_bars:
                    test_end = total_bars
                if test_start >= total_bars:
                    break
                if train_end > total_bars:
                    break

                windows.append((train_start, train_end, test_start, test_end))

        return windows

    def _run_window(
        self,
        data: pd.DataFrame | list[dict[str, Any]],
        strategy_func: StrategyFunc,
        window: tuple[int, int, int, int],
        param_grid: dict[str, list[Any]] | None,
    ) -> WindowResult:
        """Run analysis for a single walk-forward window."""
        train_start, train_end, test_start, test_end = window
        window_idx = len(window)  # Will be set by caller via list index

        engine = BacktestEngine(
            initial_capital=self._initial_capital,
            commission=self._commission,
        )

        # Split data
        if isinstance(data, pd.DataFrame):
            train_data = data.iloc[train_start:train_end].reset_index(drop=True)
            test_data = data.iloc[test_start:test_end].reset_index(drop=True)
        else:
            train_data = data[train_start:train_end]
            test_data = data[test_start:test_end]

        # Optimize parameters on training data
        best_params: dict[str, Any] = {}
        if param_grid and self._optimize_func:
            best_params = self._optimize_func(
                strategy_func, train_data, param_grid
            )
        elif param_grid:
            best_params = self._grid_search(strategy_func, train_data, param_grid, engine)

        # Run in-sample backtest
        train_result = engine.run(strategy_func, train_data)

        # Create optimized strategy if parameters found
        if best_params:
            optimized_func = self._create_param_strategy(strategy_func, best_params)
            train_result = engine.run(optimized_func, train_data)
            test_result = engine.run(optimized_func, test_data)
        else:
            test_result = engine.run(strategy_func, test_data)

        return WindowResult(
            window_idx=0,  # Will be overwritten
            train_start=train_start,
            train_end=train_end,
            test_start=test_start,
            test_end=test_end,
            train_result=train_result,
            test_result=test_result,
            best_params=best_params,
            train_sharpe=train_result.sharpe_ratio,
            test_sharpe=test_result.sharpe_ratio,
            train_return_pct=train_result.total_return_pct,
            test_return_pct=test_result.total_return_pct,
            train_max_dd_pct=train_result.max_drawdown_pct,
            test_max_dd_pct=test_result.max_drawdown_pct,
        )

    def _grid_search(
        self,
        strategy_func: StrategyFunc,
        train_data: pd.DataFrame | list[dict[str, Any]],
        param_grid: dict[str, list[Any]],
        engine: BacktestEngine,
    ) -> dict[str, Any]:
        """
        Simple grid search over parameter combinations.

        Evaluates each parameter combination on training data
        and returns the one with the highest Sharpe ratio.
        """
        import itertools

        # Generate all parameter combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combinations = list(itertools.product(*param_values))

        best_sharpe = float("-inf")
        best_params: dict[str, Any] = {}

        for combo in combinations:
            params = dict(zip(param_names, combo))
            try:
                param_strategy = self._create_param_strategy(strategy_func, params)
                result = engine.run(param_strategy, train_data)

                if result.sharpe_ratio > best_sharpe:
                    best_sharpe = result.sharpe_ratio
                    best_params = params
            except Exception as exc:
                logger.debug("Grid search params %s failed: %s", params, exc)
                continue

        return best_params

    @staticmethod
    def _create_param_strategy(
        base_strategy: StrategyFunc,
        params: dict[str, Any],
    ) -> StrategyFunc:
        """
        Create a strategy function that injects parameters.

        The base strategy function receives an additional 'params' key
        in the bar data for parameter access.
        """
        def param_strategy(
            bar: dict[str, Any],
            positions: dict[str, Any],
            equity: float,
        ) -> dict[str, Any] | None:
            # Inject params into bar data
            enriched_bar = {**bar, "strategy_params": params}
            return base_strategy(enriched_bar, positions, equity)

        return param_strategy
