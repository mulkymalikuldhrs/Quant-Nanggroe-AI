# engine.backtest.optimizers.mean_variance_optimizer

## Class: 

Maximize Sharpe ratio subject to long-only simplex.

Uses SLSQP optimisation via scipy. Falls back to equal weight
if optimisation fails or scipy is unavailable.

Args:
    lookback: Lookback days for covariance estimation.
    risk_free: Risk-free rate for Sharpe calculation.
    **kwargs: Additional parameters.

**Methods:** __init__, _build_context, _calc_weights

*Line: 22*

---

## Function: 

Module-level entry: max-Sharpe-adjusted positions.

Args:
    ret: Return matrix (dates x codes).
    pos: Raw signal positions.
    dates: Date index aligned with ``pos``.
    lookback: Lookback window for covariance.
    risk_free: Risk-free rate.

Returns:
    Adjusted position matrix.

*Line: 107*

---

## Function: 

*Line: 34*

---

## Function: 

Build context with mean vector and covariance.

Args:
    window: Return window.
    active: Active codes.

Returns:
    Context with ``cov`` and ``mu``, or None if NaN detected.

*Line: 40*

---

## Function: 

SLSQP max-Sharpe weights.

Falls back to equal weight if:
  - scipy is not installed
  - optimisation fails
  - any weight is negative after normalisation

Args:
    ctx: Context dict with ``cov`` and ``mu``.

Returns:
    Weight vector summing to 1.

*Line: 58*

---

## Function: 

*Line: 82*

---

