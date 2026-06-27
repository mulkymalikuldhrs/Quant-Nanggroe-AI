# engine.backtest.optimizers.equal_volatility_optimizer

## Class: 

Inverse-volatility weights without a full covariance model.

Each asset receives weight proportional to the inverse of its
rolling volatility, so lower-volatility assets get higher weights
and each asset contributes similar volatility to the portfolio.

Args:
    lookback: Lookback days for volatility estimation.
    **kwargs: Additional parameters (ignored).

**Methods:** _build_context, _calc_weights

*Line: 20*

---

## Function: 

Module-level entry: inverse-volatility-adjusted positions.

Args:
    ret: Return matrix (dates x codes).
    pos: Raw signal positions.
    dates: Date index aligned with ``pos``.
    lookback: Lookback window for volatility.

Returns:
    Adjusted position matrix.

*Line: 62*

---

## Function: 

Build context with rolling per-asset volatilities.

Args:
    window: Return window.
    active: Active codes.

Returns:
    Context with ``vols`` or None if any vol is NaN or near-zero.

*Line: 32*

---

## Function: 

Inverse-volatility weights.

Args:
    ctx: Context dict with ``vols`` key.

Returns:
    Weight vector summing to 1.

*Line: 49*

---

