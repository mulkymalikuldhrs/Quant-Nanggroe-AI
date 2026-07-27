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
- CPCV (RECOMMENDED): Combinatorial Purged Cross-Validation with
  purging and embargo from de Prado (AFML Ch.12).  Evaluates across
  ALL combinations of train/test splits, not a single path.

Reference: Robert Pardo, "The Evaluation and Optimization of Trading Strategies"
Reference: Marcos López de Prado, "Advances in Financial Machine Learning" (for CPCV)

**IMPORTANT — Per-Fold Re-Fitting:**
``analyze()`` now raises ``DeprecationWarning`` when called with pre-computed
signals (no ``strategy_class``).  This is because pre-computed signals contain
lookahead bias when the strategy involves any fitted model (cointegration,
GARCH, HMM, ML, etc.).  Use ``analyze_strategy()`` instead, which re-instantiates
and re-fits the strategy on **every training fold**, eliminating lookahead bias.
CPCV mode also supports per-fold re-fitting when ``strategy_class`` is provided.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.backtest.cpcv import CombinatorialPurgedCV
from quant_nanggroe.types.signals import SignalType

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
    is_trades: int = 0  # trades fired in-sample fold (significance context)
    oos_trades: int = 0  # trades fired out-of-sample fold (significance context)


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
        mode: str = "cpcv",
        anchored: bool = False,
        min_observations: int = 60,
        purge_gap: int = 5,
        # CPCV parameters
        n_groups: int = 6,
        n_test_groups: int = 2,
        embargo: int = 3,
        force_precomputed: bool = False,
    ) -> None:
        """Initialize walk-forward analyzer.

        Args:
            engine: BacktestEngine instance.
            train_window: Training window in bars.
            test_window: Test window in bars.
            mode: Walk-forward mode ('cpcv' (default), 'rolling', 'anchored').
                  CPCV is the RECOMMENDED default — see class docstring.
            anchored: If True, use anchored walk-forward (expanding window).
                     Equivalent to mode='anchored'.
            min_observations: Minimum observations required for a valid window.
            purge_gap: Number of bars between train and test to prevent leakage.
                       Default 5 for CPCV (was 0 in v1 — edge case risk).
            n_groups: Number of groups for CPCV mode.
            n_test_groups: Number of test groups for CPCV mode.
            embargo: Number of bars to embargo after test period (CPCV).
            force_precomputed: If True, suppress the DeprecationWarning in
                               :meth:`analyze` when called without
                               ``strategy_class`` (legacy callers only).
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
        self.force_precomputed = force_precomputed

    def analyze(
        self,
        prices: pd.DataFrame,
        signals: pd.DataFrame,
        strategy_class: Optional[type] = None,
        strategy_params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Run walk-forward analysis.

        **When ``strategy_class`` is provided** delegates to
        :meth:`analyze_strategy` with per-fold re-fitting (recommended).

        **When ``strategy_class`` is None** falls back to pre-computed signals
        and emits a ``DeprecationWarning`` — the caller MUST set
        ``force_precomputed=True`` on the constructor to suppress the warning
        for legacy strategies that genuinely cannot be re-fitted per fold
        (e.g., simple technical indicators with no trainable parameters).

        Args:
            prices: Price data with DatetimeIndex.
            signals: Signal data with same index.
            strategy_class: **Required** for new code.  Strategy class for
                per-fold re-fitting.  When provided, signals are regenerated
                per fold using the strategy's ``generate_signal`` method,
                eliminating lookahead bias.
            strategy_params: Parameters passed to the strategy constructor.
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
        if strategy_class is not None:
            return self.analyze_strategy(
                prices=prices,
                strategy_class=strategy_class,
                strategy_params=strategy_params or {},
                purge_gap=self.purge_gap,
                embargo=self.embargo,
                **kwargs,
            )

        # Pre-computed-signals path — deprecated unless explicitly opted in
        if not self.force_precomputed:
            import warnings
            warnings.warn(
                "WalkForwardAnalyzer.analyze() called with pre-computed signals "
                "(no strategy_class).  This does NOT re-fit the strategy per fold "
                "and produces lookahead-biased results for any strategy with "
                "trainable parameters.  Pass strategy_class + strategy_params for "
                "per-fold re-fitting, or set force_precomputed=True on the "
                "constructor to suppress this warning for legacy strategies.",
                DeprecationWarning,
                stacklevel=2,
            )

        if self.mode == "cpcv":
            return self._analyze_cpcv(prices, signals, strategy_class=strategy_class, strategy_params=strategy_params or {}, **kwargs)

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
        oos_trade_counts: List[int] = []  # ponytail: per-fold trade count for return-per-trade
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

            # Apply purge gap: remove bars from end of training data
            # adjacent to the test fold (prevents information leakage)
            effective_train_end = train_end - self.purge_gap if self.purge_gap > 0 else train_end

            # Validate minimum observations
            if (effective_train_end - train_start) < self.min_observations:
                start += self.test_window + self.embargo
                continue

            # Extract data slices (purged training data)
            train_prices = prices.iloc[train_start:effective_train_end]
            train_signals = signals.iloc[train_start:effective_train_end]
            test_prices = prices.iloc[test_start:test_end]
            test_signals = signals.iloc[test_start:test_end]

            # Run in-sample backtest
            is_result = self.engine.run(train_prices, train_signals, **kwargs)
            is_metrics = is_result.get("metrics", {})
            is_trades = is_metrics.get("total_trades", 0)

            # Run out-of-sample backtest
            oos_result = self.engine.run(test_prices, test_signals, **kwargs)
            oos_metrics = oos_result.get("metrics", {})
            oos_trades = oos_metrics.get("total_trades", 0)

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
                is_trades=is_trades,
                oos_trades=oos_trades,
            )

            windows.append(wf_result)
            oos_returns.append(oos_metrics.get("total_return", 0.0))
            oos_sharpes.append(oos_sharpe)
            oos_trade_counts.append(max(oos_trades, 1))

            # Collect OOS equity curve parts
            oos_eq = oos_result.get("equity_curve", pd.Series(dtype=float))
            if len(oos_eq) > 0:
                oos_equity_parts.append(oos_eq)

            # Roll forward (skip embargo bars to prevent leakage)
            start += self.test_window + self.embargo

        # Calculate aggregate statistics
        aggregate = self._calculate_aggregate(windows, oos_returns, oos_sharpes, oos_trade_counts)
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

    def analyze_strategy(
        self,
        prices: pd.DataFrame,
        strategy_class: type,
        strategy_params: Optional[Dict[str, Any]] = None,
        purge_gap: int = 10,
        embargo: int = 5,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Run walk-forward with per-fold strategy re-fitting.

        Unlike :meth:`analyze`, this method re-instantiates and re-fits the
        strategy on each training fold, eliminating lookahead bias from
        pre-computed signals.

        Args:
            prices: Price data with DatetimeIndex.
            strategy_class: Strategy class (subclass of BaseStrategy).
            strategy_params: Parameters to pass to strategy constructor.
            purge_gap: Bars to purge between train/test boundaries.
            embargo: Bars to embargo after test period.
            **kwargs: Additional arguments passed to engine.run().

        Returns:
            Same structure as :meth:`analyze`.
        """
        params = strategy_params or {}
        n_bars = len(prices)
        total_window = self.train_window + self.test_window + purge_gap

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
        oos_trade_counts: List[int] = []  # ponytail: per-fold trade count for return-per-trade
        oos_equity_parts: List[pd.Series] = []

        start = 0
        fold = 0
        while start + total_window <= n_bars:
            fold += 1
            if self.mode == "anchored":
                train_end = start + self.train_window
                train_start = 0
            else:
                train_start = start
                train_end = start + self.train_window

            test_start = train_end + purge_gap
            test_end = test_start + self.test_window

            if test_end > n_bars:
                break

            effective_train_end = train_end - purge_gap if purge_gap > 0 else train_end
            if (effective_train_end - train_start) < self.min_observations:
                start += self.test_window + embargo
                continue

            train_prices = prices.iloc[train_start:effective_train_end]
            test_prices = prices.iloc[test_start:test_end]

            logger.info(
                "Fold %d: train [%d:%d] test [%d:%d]",
                fold, train_start, effective_train_end, test_start, test_end,
            )

            try:
                strategy = strategy_class(**params)
                train_signals = self._generate_strategy_signals(strategy, train_prices)
                test_signals = self._generate_strategy_signals(strategy, test_prices)
            except Exception as e:
                logger.warning("Fold %d strategy execution failed: %s", fold, e)
                start += self.test_window + embargo
                continue

            if train_signals is None or train_signals.empty:
                logger.warning("Fold %d: no training signals generated", fold)
                start += self.test_window + embargo
                continue

            is_result = self.engine.run(train_prices, train_signals, **kwargs)
            is_metrics = is_result.get("metrics", {})
            is_trades = is_metrics.get("total_trades", 0)

            if test_signals is not None and not test_signals.empty:
                oos_result = self.engine.run(test_prices, test_signals, **kwargs)
                oos_metrics = oos_result.get("metrics", {})
                oos_eq = oos_result.get("equity_curve", pd.Series(dtype=float))
                oos_trades = oos_metrics.get("total_trades", 0)
                if len(oos_eq) > 0:
                    oos_equity_parts.append(oos_eq)
            else:
                oos_metrics = {"sharpe_ratio": 0.0, "total_return": 0.0, "max_drawdown": 0.0}
                oos_trades = 0

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
                is_trades=is_trades,
                oos_trades=oos_trades,
            )

            windows.append(wf_result)
            oos_returns.append(oos_metrics.get("total_return", 0.0))
            oos_sharpes.append(oos_sharpe)
            oos_trade_counts.append(max(oos_trades, 1))
            start += self.test_window + embargo

        aggregate = self._calculate_aggregate(windows, oos_returns, oos_sharpes, oos_trade_counts)
        degradation_stats = self._calculate_degradation_stats(windows)
        stability = self._calculate_stability(windows, oos_sharpes, oos_returns)
        oos_equity_curve = self._combine_oos_equity(oos_equity_parts)

        return {
            "windows": windows,
            "aggregate": aggregate,
            "degradation_stats": degradation_stats,
            "stability": stability,
            "mode": self.mode,
            "oos_equity_curve": oos_equity_curve,
            "n_folds": fold,
        }

    @staticmethod
    def _generate_strategy_signals(
        strategy: Any,
        prices: pd.DataFrame,
    ) -> pd.DataFrame:
        """Generate signals from a strategy instance for a price slice.

        Calls ``generate_signal`` bar-by-bar to avoid lookahead bias,
        then assembles the results into a single-column signal DataFrame.

        Args:
            strategy: BaseStrategy instance.
            prices: Price DataFrame for the fold.

        Returns:
            Signal DataFrame with same index as prices, or None on failure.
        """
        signals = []
        required_cols = strategy.required_columns()
        warmup = strategy.warmup_period()
        # ponytail: strategies expect lowercase OHLCV (validate_data raises on Capitalized).
        # Normalize once here — single shared point, not 75 strategy files.
        prices = prices.rename(columns={c: c.lower() for c in prices.columns})

        for i in range(len(prices)):
            data_slice = prices.iloc[max(0, i - warmup):i + 1]
            if len(data_slice) < warmup:
                signals.append(0.0)
                continue
            try:
                signal = strategy.generate_signal(data_slice)
                # ponytail: Signal has no `.signal`; use strength, fall back to ±1 by type
                if signal is None:
                    signals.append(0.0)
                else:
                    weight = signal.strength if signal.strength not in (None, 0.0) else (
                        1.0 if signal.signal_type == SignalType.BUY else -1.0
                    )
                    signals.append(weight)
            except Exception:
                signals.append(0.0)

        return pd.DataFrame({prices.columns[0]: signals}, index=prices.index)

    def _analyze_cpcv(
        self,
        prices: pd.DataFrame,
        signals: pd.DataFrame,
        strategy_class: Optional[type] = None,
        strategy_params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Run Combinatorial Purged Cross-Validation (CPCV).

        Uses :class:`~quant_nanggroe.engine.backtest.cpcv.CombinatorialPurgedCV`
        for proper purging and embargo (de Prado, AFML Ch.12), then runs a
        backtest on every train/test split.

        When ``strategy_class`` is provided, signals are regenerated
        per fold using the strategy's ``generate_signal`` method,
        eliminating lookahead bias from pre-computed signals.

        Args:
            prices: Price data.
            signals: Signal data (used as fallback when strategy_class is None).
            strategy_class: Optional strategy class for per-fold re-fitting.
            strategy_params: Parameters passed to the strategy constructor.
            **kwargs: Additional arguments.

        Returns:
            CPCV results dict.
        """
        n_bars = len(prices)
        timestamps = list(range(n_bars))

        # Dynamically adjust n_groups so each group is large enough
        n_groups = self.n_groups
        group_size = n_bars // n_groups
        if group_size < self.min_observations:
            logger.warning(
                "CPCV: Group size %d < min_observations %d. Reducing n_groups.",
                group_size, self.min_observations,
            )
            n_groups = max(2, n_bars // self.min_observations)

        # Build the CombinatorialPurgedCV splitter
        cpcv_splitter = CombinatorialPurgedCV(
            n_groups=n_groups,
            n_test_groups=self.n_test_groups,
            purge_gap=self.purge_gap,
            embargo=self.embargo,
            min_train_fraction=self.min_observations / max(n_bars, 1),
        )

        # Use split_detailed for metadata-rich splits
        detailed_splits = cpcv_splitter.split_detailed(timestamps)

        windows: List[WalkForwardResult] = []
        oos_returns: List[float] = []
        oos_sharpes: List[float] = []
        oos_trade_counts: List[int] = []
        oos_equity_parts: List[pd.Series] = []

        for split_info in detailed_splits:
            train_indices = split_info.train_indices
            test_indices = split_info.test_indices

            if len(train_indices) < self.min_observations or len(test_indices) < 10:
                continue

            train_prices = prices.iloc[train_indices]
            test_prices = prices.iloc[test_indices]

            # Generate signals per fold if strategy_class is provided
            if strategy_class is not None:
                try:
                    strategy = strategy_class(**(strategy_params or {}))
                    train_signals = self._generate_strategy_signals(strategy, train_prices)
                    test_signals = self._generate_strategy_signals(strategy, test_prices)
                except Exception as e:
                    logger.warning("CPCV fold strategy generation failed: %s", e)
                    continue
            else:
                train_signals = signals.iloc[train_indices]
                test_signals = signals.iloc[test_indices]

            try:
                is_result = self.engine.run(train_prices, train_signals, **kwargs)
                is_metrics = is_result.get("metrics", {})
                is_trades = is_metrics.get("total_trades", 0)

                oos_result = self.engine.run(test_prices, test_signals, **kwargs)
                oos_metrics = oos_result.get("metrics", {})
                oos_trades = oos_metrics.get("total_trades", 0)
            except Exception as e:
                logger.warning("CPCV window failed: %s", e)
                continue

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
                is_trades=is_trades,
                oos_trades=oos_trades,
            )

            windows.append(wf_result)
            oos_returns.append(oos_metrics.get("total_return", 0.0))
            oos_sharpes.append(oos_sharpe)
            oos_trade_counts.append(max(oos_trades, 1))

            oos_eq = oos_result.get("equity_curve", pd.Series(dtype=float))
            if len(oos_eq) > 0:
                oos_equity_parts.append(oos_eq)

        aggregate = self._calculate_aggregate(windows, oos_returns, oos_sharpes, oos_trade_counts)
        degradation_stats = self._calculate_degradation_stats(windows)
        stability = self._calculate_stability(windows, oos_sharpes, oos_returns)
        oos_equity_curve = self._combine_oos_equity(oos_equity_parts)

        return {
            "windows": windows,
            "aggregate": aggregate,
            "degradation_stats": degradation_stats,
            "stability": stability,
            "mode": "cpcv",
            "n_groups": n_groups,
            "n_test_groups": self.n_test_groups,
            "n_combinations": len(detailed_splits),
            "oos_equity_curve": oos_equity_curve,
        }

    def _calculate_aggregate(
        self,
        windows: List[WalkForwardResult],
        oos_returns: List[float],
        oos_sharpes: List[float],
        oos_trade_counts: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """Calculate aggregate walk-forward statistics."""
        if oos_trade_counts is None:
            oos_trade_counts = [1] * len(windows)
        if not windows:
            return {}

        median_fold_trades = float(np.median([w.oos_trades for w in windows]))
        per_trade = [r / tc for r, tc in zip(oos_returns, oos_trade_counts)] if oos_returns else []
        return {
            "num_windows": len(windows),
            "avg_oos_return": float(np.mean(oos_returns)) if oos_returns else 0.0,  # per-fold mean (readable, vol-inflated)
            "median_oos_return": float(np.median(oos_returns)) if oos_returns else 0.0,
            "avg_oos_return_per_trade": float(np.mean(per_trade)) if per_trade else 0.0,  # ponytail: expectancy proxy
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
            # Significance context: Sharpe on too few trades is noise, not edge.
            # Aggregate OOS trade count + a hard under-sample flag so a "+X% / Sharpe+Y"
            # headline cannot be read as "repeatable edge" without enough observed trades.
            "total_oos_trades": int(sum(w.oos_trades for w in windows)),
            "median_fold_oos_trades": int(median_fold_trades),
            "under_sampled": bool(
                median_fold_trades < 30 or len(windows) < 3
            ),
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
