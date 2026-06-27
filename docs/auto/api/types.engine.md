# types.engine

## Class: 

Market regime classification.

Deterministic classification based on ADX, RSI, price change, volume, and ATR.
If regime is NO_TRADE → the entire system must stop.

*Line: 21*

---

## Class: 

Market volatility classification.

*Line: 40*

---

## Class: 

Market liquidity classification.

*Line: 48*

---

## Class: 

Current market state summary.

Combines regime, volatility, and liquidity into a single model
for use by the decision pipeline.

*Line: 55*

---

## Class: 

Normalized pressure state from sensor fusion.

All values are normalized to 0.0-1.0 for deterministic decision synthesis.

*Line: 73*

---

## Class: 

Risk clearance level for trade decisions.

CLEAR: Trade allowed, all risk checks passed.
PAUSE: Monitor closely, risk conditions elevated.
BLOCKED: Trade blocked, risk limits exceeded.

*Line: 85*

---

## Class: 

Action produced by the decision synthesis engine.

ALLOW_*: Trade approved at the decision layer.
WATCH_*: Monitoring — do not enter yet.
NO_TRADE: No action — conditions not met.

*Line: 97*

---

## Class: 

Darwinian strategy lifecycle states.

ACTIVE: Strategy is live and generating trades.
HIBERNATING: Strategy paused due to excessive drawdown.
KILLED: Strategy permanently disabled due to negative expectancy.

*Line: 117*

---

