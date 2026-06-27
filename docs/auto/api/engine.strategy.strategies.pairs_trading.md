# engine.strategy.strategies.pairs_trading

## Class: 

Pairs trading strategy using OLS hedge ratio and spread z-score.

Spread = price_B - hedge_ratio * price_A.
Entry when |z-score| > entry_z, exit when |z-score| < exit_z.

Parameters:
    symbol: Primary symbol (asset A).
    symbol_pair: Second symbol (asset B).
    lookback: Rolling window for spread z-score (default 60).
    entry_z: Z-score threshold to open a position (default 2.0).
    exit_z: Z-score threshold to close a position (default 0.5).
    hedge_ratio_lookback: Bars used for OLS estimation (default 252).
    transaction_cost_bps: Round-turn transaction cost in bps (default 10.0).
    min_trade_interval_bars: Minimum bars between successive trades
        (default 5).

**Methods:** __init__, required_columns, warmup_period, _ols_hedge_ratio, generate_signal

*Line: 28*

---

## Function: 

*Line: 46*

---

## Function: 

*Line: 60*

---

## Function: 

*Line: 63*

---

## Function: 

Regress y (B) on x (A) with intercept, return slope.

Returns 1.0 on failure.

*Line: 67*

---

## Function: 

*Line: 80*

---

