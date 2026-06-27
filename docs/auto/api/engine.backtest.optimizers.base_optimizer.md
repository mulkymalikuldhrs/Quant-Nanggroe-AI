# engine.backtest.optimizers.base_optimizer

## Class: 

Abstract portfolio optimizer.

Subclasses implement ``_calc_weights``; the base handles:
  - active asset selection
  - rolling window slicing and sanity checks
  - covariance matrix + NaN checks
  - applying weights while preserving signal sign

Attributes:
    lookback: Lookback days for covariance / mean.
    params: Extra keyword args for subclasses.

**Methods:** __init__, optimize, _build_context, _calc_weights, _normalize, _equal_weight

*Line: 18*

---

## Function: 

*Line: 32*

---

## Function: 

Apply optimizer to position weights.

For each date with active positions, computes optimal weights
using a rolling window of returns, while preserving the sign
of the original signal.

Args:
    ret: Return matrix (dates x codes).
    pos: Raw signal positions (dates x codes).
    dates: Date index aligned with ``pos``.

Returns:
    Adjusted position matrix (not dollar-normalized).

*Line: 38*

---

## Function: 

Build context dict for ``_calc_weights``.

Default: covariance only. Override to add means, vols, etc.
Return None to skip the date.

Args:
    window: Return window for active assets.
    active: Active asset codes.

Returns:
    Context dict with at least ``cov``, or None.

*Line: 88*

---

## Function: 

Compute target weights from context.

Args:
    ctx: Dict from ``_build_context``.

Returns:
    Weight vector (n,) summing to 1.

*Line: 111*

---

## Function: 

Normalize nonnegative weights to sum 1.

Args:
    w: Raw weight vector.

Returns:
    Normalized weight vector.

*Line: 124*

---

## Function: 

Equal weights for n assets.

Args:
    n: Number of assets.

Returns:
    Equal weight vector.

*Line: 140*

---

