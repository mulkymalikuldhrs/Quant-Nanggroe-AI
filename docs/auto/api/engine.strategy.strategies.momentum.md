# engine.strategy.strategies.momentum

## Class: 

Multi-variant momentum strategy with cost and frequency controls.

Signal format: float in [-1, 1] embedded via SignalType + confidence.
   > 0 → BUY,  < 0 → SELL,  0 → no position.

Parameters:
    strategy_type: "ts_momentum", "dual_momentum", "ma_crossover", "macd"
    lookback: TS momentum lookback (default 126, ~6 months daily)
    fast_lookback: Fast MA period for dual/ma_crossover/macd (default 20)
    slow_lookback: Slow MA period for dual/ma_crossover/macd (default 50)
    entry_threshold: Minimum |signal| to open a position (default 0.05)
    exit_threshold: |signal| below this forces flat (default 0.01)
    transaction_cost_bps: One-way cost in basis points (default 10.0)
    min_trade_interval_bars: Minimum bars between trades (default 5)
    signal_smoothing: SMA window on raw signal to reduce whipsaws (default 3)
    symbol: Trading symbol for Signal generation (default "ASSET")

**Methods:** __init__, required_columns, warmup_period, generate_signal, _compute_raw_signal, _ts_momentum, _dual_momentum, _ma_crossover, _macd, _smooth, _can_trade, _classify

*Line: 28*

---

## Function: 

*Line: 47*

---

## Function: 

*Line: 63*

---

## Function: 

*Line: 66*

---

## Function: 

Generate momentum signal.

Steps:
  1. Compute raw signal from the active variant ([-1, 1]).
  2. Smooth via SMA of last N values.
  3. Reject if minimum trade interval not met.
  4. Map smoothed signal to SignalType + confidence.
  5. Deduct transaction cost from confidence.

*Line: 69*

---

## Function: 

Return raw momentum signal in [-1, 1]; 0 = no conviction.

*Line: 124*

---

## Function: 

Buy when return > entry_threshold, sell when < -entry_threshold.

*Line: 141*

---

## Function: 

Require both absolute (price vs slow MA) and relative (fast vs slow MA) aligment.

*Line: 159*

---

## Function: 

+1 when fast MA crosses above slow MA, -1 when crosses below.

*Line: 183*

---

## Function: 

Signal direction from MACD histogram sign and crossover.

*Line: 209*

---

## Function: 

Simple FIFO SMA to reduce whipsaw signals.

*Line: 237*

---

## Function: 

Enforce minimum gap between consecutive trades.

*Line: 244*

---

## Function: 

Map smoothed signal to (SignalType, confidence) or None if flat.

*Line: 249*

---

