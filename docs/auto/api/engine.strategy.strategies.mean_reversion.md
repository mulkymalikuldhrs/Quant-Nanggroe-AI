# engine.strategy.strategies.mean_reversion

## Class: 

Mean reversion with configurable variant and trade frequency controls.

Parameters
----------
strategy_type : str
    ``"zscore"``, ``"bollinger"``, or ``"ou"`` (default ``"zscore"``).
lookback : int
    Rolling window for mean / std calculation (default 20).
entry_threshold : float
    Z-score or band threshold for entry (default 2.0).
exit_threshold : float
    Z-score or band threshold for exit (default 0.5).
bollinger_std : float
    Standard deviations for Bollinger Bands (default 2.0).
min_signal_strength : float
    Minimum absolute signal value to generate a trade (default 0.1).
transaction_cost_bps : float
    One-way transaction cost in basis points (default 10.0 = 0.1%).
min_trade_interval_bars : int
    Minimum bars between consecutive trades (default 5).

**Methods:** __init__, required_columns, warmup_period, estimate_half_life, generate_signal, _compute_target, _zscore_target, _bollinger_target, _ou_target, _entry_signal, _exit_signal

*Line: 33*

---

## Function: 

*Line: 56*

---

## Function: 

*Line: 71*

---

## Function: 

*Line: 74*

---

## Function: 

OU half-life via OLS: X_{t+1} - X_t = alpha + beta * X_t + eps.

Returns bars-to-half-mean-reversion or ``inf`` if not mean-reverting.

.. math:: \text{half-life} = -\ln(2) / \beta,\quad \beta < 0

*Line: 82*

---

## Function: 

*Line: 110*

---

## Function: 

Dispatch to variant. Returns target position in [-1, 1].

*Line: 139*

---

## Function: 

*Line: 154*

---

## Function: 

*Line: 165*

---

## Function: 

*Line: 180*

---

## Function: 

*Line: 199*

---

## Function: 

*Line: 223*

---

