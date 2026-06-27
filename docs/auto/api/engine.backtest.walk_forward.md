# engine.backtest.walk_forward

## Class: 

Result from a single walk-forward window.

*Line: 34*

---

## Class: 

Stability metrics for walk-forward analysis.

Measures how consistent strategy performance is across
different time windows.

*Line: 51*

---

## Class: 

Walk-Forward Analysis for strategy validation.

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

**Methods:** __init__, analyze, analyze_strategy, _generate_strategy_signals, _analyze_cpcv, _calculate_aggregate, _calculate_degradation_stats, _calculate_stability, _combine_oos_equity

*Line: 67*

---

## Function: 

Initialize walk-forward analyzer.

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

*Line: 92*

---

## Function: 

Run walk-forward analysis on pre-computed signals.

.. warning::

    This method accepts pre-computed signals — it does **not** re-fit
    the strategy on each fold. Use only for strategies that require
    no model fitting (e.g., simple technical indicators).
    For strategies with fitted models (cointegration, GARCH, HMM, ML),
    use :meth:`analyze_strategy` instead, which re-fits per fold and
    eliminates lookahead bias.

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

*Line: 135*

---

## Function: 

Run walk-forward with per-fold strategy re-fitting.

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

*Line: 276*

---

## Function: 

Generate signals from a strategy instance for a price slice.

Calls ``generate_signal`` bar-by-bar to avoid lookahead bias,
then assembles the results into a single-column signal DataFrame.

Args:
    strategy: BaseStrategy instance.
    prices: Price DataFrame for the fold.

Returns:
    Signal DataFrame with same index as prices, or None on failure.

*Line: 417*

---

## Function: 

Run Combinatorial Purged Cross-Validation (CPCV).

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

*Line: 450*

---

## Function: 

Calculate aggregate walk-forward statistics.

*Line: 602*

---

## Function: 

Calculate degradation statistics (IS vs OOS).

*Line: 629*

---

## Function: 

Calculate walk-forward stability metrics.

Args:
    windows: List of walk-forward results.
    oos_sharpes: List of OOS Sharpe ratios.
    oos_returns: List of OOS returns.

Returns:
    WalkForwardStability with stability metrics.

*Line: 649*

---

## Function: 

Combine OOS equity curve parts into a single series.

Uses the last known equity value of each window as the base
for the next window's returns.

Args:
    equity_parts: List of OOS equity curve Series.

Returns:
    Combined equity curve Series.

*Line: 716*

---

