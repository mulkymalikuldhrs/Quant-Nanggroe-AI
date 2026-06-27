# engine.backtest.optimizers.risk_parity_optimizer

## Class: 

Risk parity: equalize risk contributions across assets.

Uses inverse-volatility seeding with Newton-style refinement
to ensure each asset contributes equally to portfolio risk.

Args:
    lookback: Lookback days for covariance estimation.
    **kwargs: Additional parameters (ignored).

**Methods:** _calc_weights

*Line: 19*

---

## Function: 

Module-level entry: risk-parity-adjusted positions.

Args:
    ret: Return matrix (dates x codes).
    pos: Raw signal positions.
    dates: Date index aligned with ``pos``.
    lookback: Lookback window for covariance.

Returns:
    Adjusted position matrix.

*Line: 66*

---

## Function: 

Equal risk contribution weights.

Args:
    ctx: Context dict with ``cov`` key.

Returns:
    Weight vector summing to 1.

*Line: 30*

---

