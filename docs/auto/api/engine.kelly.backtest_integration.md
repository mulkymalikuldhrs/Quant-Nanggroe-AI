# engine.kelly.backtest_integration

## Class: 

Output from Kelly calculator for a single period.

*Line: 24*

---

## Class: 

Bridge that injects Kelly position sizing into a backtest strategy.

Wraps any base strategy and:
1. Computes optimal Kelly fraction at each step
2. Adjusts position sizes accordingly
3. Tracks Kelly-derived risk metrics

**Methods:** __init__, compute_signals, _compute_single_signal, _fallback_signal, _infer_regime, _estimate_drawdown, _conviction_score, signal_history, reset_history

*Line: 35*

---

## Class: 

Mixin to add Kelly position sizing to any backtest strategy.

**Methods:** __init__, adjust_position_size

*Line: 243*

---

## Function: 

*Line: 45*

---

## Function: 

Compute Kelly-based position sizing signals.

Args:
    prices: Price DataFrame with DatetimeIndex and symbol columns.
    returns: Return Series for the primary asset.
    equity: Current portfolio equity.
    regime: Optional market regime label.

Returns:
    List of KellySignal objects, one per symbol in prices.

*Line: 65*

---

## Function: 

Compute a single KellySignal for one symbol.

*Line: 104*

---

## Function: 

Return a safe fallback signal when data is insufficient.

*Line: 179*

---

## Function: 

Infer market regime from recent returns.

*Line: 193*

---

## Function: 

Estimate current drawdown from peak.

*Line: 211*

---

## Function: 

Compute a 0.0-1.0 conviction score.

Factors: sample size, regime clarity, win rate stability.

*Line: 219*

---

## Function: 

Return all computed signals.

*Line: 234*

---

## Function: 

Clear signal history.

*Line: 238*

---

## Function: 

*Line: 248*

---

## Function: 

Adjust a base position size using the Kelly bridge.

Args:
    base_size: Original position size (notional or shares).
    prices: Price DataFrame for Kelly signal computation.
    returns: Return Series for Kelly signal computation.
    equity: Current portfolio equity.

Returns:
    Adjusted position size scaled by the Kelly capped fraction.

*Line: 252*

---

