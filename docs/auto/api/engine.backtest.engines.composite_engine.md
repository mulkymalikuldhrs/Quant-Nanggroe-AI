# engine.backtest.engines.composite_engine

## Function: 

Instantiate one sub-engine per market type detected in codes.

Sub-engines are stateless rule providers — they don't hold their own
capital, positions, or trades. All state lives in CompositeEngine.

Args:
    config: Backtest configuration dict.
    codes: List of instrument codes.

Returns:
    Mapping of market type -> engine instance.

*Line: 39*

---

## Class: 

Cross-market engine with shared capital pool.

Sub-engines are stateless rule providers. All positions, capital,
and trades live here (inherited from BaseEngine).

Args:
    config: Backtest configuration dict.
    codes: List of instrument codes spanning multiple markets.

**Methods:** __init__, _reset_state, _rule_for, can_execute, round_size, calc_commission, apply_slippage, _calc_pnl, _calc_margin, _calc_raw_size, on_bar

*Line: 74*

---

## Function: 

*Line: 85*

---

## Function: 

Reset engine state including cross-market tracking.

*Line: 107*

---

## Function: 

Get the sub-engine that provides rules for this symbol.

Args:
    symbol: Instrument identifier.

Returns:
    Sub-engine instance.

Raises:
    ValueError: If no rule engine is available for the symbol's market.

*Line: 114*

---

## Function: 

Market-rule check with T+1 interceptor for A-shares.

*Line: 144*

---

## Function: 

Delegate to active symbol's sub-engine.

*Line: 166*

---

## Function: 

Delegate to active symbol's sub-engine.

*Line: 170*

---

## Function: 

Delegate to active symbol's sub-engine.

*Line: 178*

---

## Function: 

Delegate P&L calculation to the symbol's rule engine.

*Line: 187*

---

## Function: 

Delegate margin calculation to the symbol's rule engine.

*Line: 200*

---

## Function: 

Delegate size calculation to the symbol's rule engine.

*Line: 210*

---

## Function: 

Per-bar hooks dispatched by market type.

Crypto: funding fee + liquidation check.
Forex: swap/rollover.

*Line: 221*

---

