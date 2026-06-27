# engine.strategies.smc_strategy

## Class: 

Smart Money Concepts Strategy.

Detects institutional trading patterns:
- Order Blocks (OB): Last bearish candle before bullish move (bullish OB)
  or last bullish candle before bearish move (bearish OB)
- Fair Value Gaps (FVG): 3-candle gap indicating imbalance
- Break of Structure (BOS): Trend continuation
- Change of Character (CHOCH): Trend reversal
- Liquidity Sweeps: Price taking out stops before reversing

**Methods:** __init__, generate_signal, _detect_fvg, _detect_order_block, _detect_structure, _detect_liquidity_sweep, _hold

*Line: 21*

---

## Function: 

*Line: 37*

---

## Function: 

Generate SMC-based trading signal.

*Line: 47*

---

## Function: 

Detect Fair Value Gap (3-candle imbalance).

*Line: 140*

---

## Function: 

Detect Order Block.

*Line: 161*

---

## Function: 

Detect BOS or CHOCH.

*Line: 176*

---

## Function: 

Detect liquidity sweep.

*Line: 198*

---

## Function: 

*Line: 217*

---

