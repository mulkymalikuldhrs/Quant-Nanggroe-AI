# engine.strategy.strategies.volatility_arbitrage

## Class: 

Vol arbitrage via vol-ratio z-score.  Shorts vol when z > entry,
longs vol when z < -entry.

Parameters
----------
vol_lookback : int  (20)
    Short-term vol estimation window.
vol_long_lookback : int  (60)
    Long-term vol rolling window.
entry_threshold : float  (2.0)
    Z-score entry threshold.
exit_threshold : float  (0.5)
    Z-score exit threshold.
vol_estimation : str  ("ewma")
    ``"historical"``, ``"ewma"``, or ``"garch"``.
transaction_cost_bps : float  (10.0)
    One-way cost in basis points.
min_trade_interval_bars : int  (5)
    Minimum bars between consecutive trades.

**Methods:** __init__, required_columns, warmup_period, _compute_vol_series, _garch_vol, _compute_target, generate_signal, _build_entry, _build_exit

*Line: 33*

---

## Function: 

*Line: 55*

---

## Function: 

*Line: 67*

---

## Function: 

*Line: 70*

---

## Function: 

*Line: 75*

---

## Function: 

GARCH(1,1) conditional vol via MLE + forward pass.
Falls back to EWMA when scipy unavailable or optimisation fails.

*Line: 86*

---

## Function: 

*Line: 126*

---

## Function: 

*Line: 150*

---

## Function: 

*Line: 168*

---

## Function: 

*Line: 192*

---

## Function: 

*Line: 97*

---

