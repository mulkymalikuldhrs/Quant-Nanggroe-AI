# engine.risk.correlation

## Class: 

Alert for correlation anomaly.

*Line: 34*

---

## Class: 

Asset Correlation Monitor.

Tracks rolling correlations between assets and alerts when:
- Pairwise correlation exceeds threshold
- Correlation regime changes (e.g., decorrelation → high correlation)
- Market stress is detected (everything becomes correlated)

**Methods:** __init__, is_correlated, count_correlated_positions, compute_rolling_correlation, compute_diversification_score, detect_stress

*Line: 44*

---

## Class: 

Monitors pairwise strategy return correlations to detect rank collapse (herding).

Tracks trailing returns for all registered strategies, computes pairwise
Spearman rank correlations, and auto-activates the kill switch when the
mean correlation exceeds the herding threshold.

Parameters
----------
kill_switch : KillSwitch, optional
    Kill switch instance to trigger on herding. If None, only logs warnings.
window : int
    Trailing window size for return history (default 30).
threshold : float
    Mean Spearman correlation threshold for herding detection (default 0.85).
state_dir : str
    Directory for persisting correlation state as JSON (default "paper_state").

**Methods:** __init__, update, compute_correlations, check_and_act, get_status, load_state, save_state

*Line: 210*

---

## Function: 

*Line: 62*

---

## Function: 

Check if two symbols are in the same correlated group.

Args:
    symbol_a: First symbol.
    symbol_b: Second symbol.

Returns:
    True if symbols are known to be correlated.

*Line: 73*

---

## Function: 

Count how many active positions are correlated with the given symbol.

Args:
    symbol: Symbol to check.
    active_positions: List of currently held symbols.

Returns:
    Number of correlated positions.

*Line: 88*

---

## Function: 

Compute rolling correlation matrix.

Args:
    returns: DataFrame of asset returns (columns = assets).
    window: Rolling window size (default: self.lookback).

Returns:
    Rolling correlation matrix for the last window.

*Line: 104*

---

## Function: 

Compute portfolio diversification score.

Score is based on the ratio of weighted average volatility
to portfolio volatility. Higher = more diversified.

Args:
    returns: DataFrame of asset returns.
    weights: Portfolio weights (default: equal weight).

Returns:
    Diversification score (0-1, higher is more diversified).

*Line: 126*

---

## Function: 

Detect market stress via correlation analysis.

During stress, correlations tend to increase (everything falls together).
This is measured as the average pairwise correlation.

Args:
    returns: DataFrame of asset returns.
    window: Rolling window size.

Returns:
    Dict with stress detection results.

*Line: 169*

---

## Function: 

*Line: 229*

---

## Function: 

Feed latest returns for a strategy. Stores trailing window.

*Line: 252*

---

## Function: 

Pairwise Spearman rank correlations between all tracked strategies.

Returns
-------
Dict[str, Dict[str, float]]
    Nested dict: {strategy_a: {strategy_b: correlation}}.
    Empty dict when fewer than 2 strategies are tracked.

*Line: 260*

---

## Function: 

Check for herding and activate kill switch if threshold breached.

Returns
-------
Dict
    Current status dictionary from ``get_status()``.

*Line: 296*

---

## Function: 

Current correlation matrix summary, avg, max, disabled strategies.

Returns
-------
Dict
    Keys: num_strategies, avg_correlation, max_correlation, matrix,
    threshold, kill_switch_fired, window.

*Line: 338*

---

## Function: 

Load persisted trailing returns from JSON file.

*Line: 371*

---

## Function: 

Persist trailing returns to JSON file.

*Line: 389*

---

