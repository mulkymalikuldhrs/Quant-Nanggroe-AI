# engine.decision

## Class: 

A single decision table rule.

*Line: 28*

---

## Class: 

Result of decision synthesis.

*Line: 47*

---

## Class: 

Deterministic decision table that synthesizes pressure + regime → trade decision.

The decision is made by evaluating the decision table rules in order.
The first matching rule determines the action.

Risk clearance is then applied on top:
- CLEAR: ALLOW_* actions pass risk check
- PAUSE: WATCH_* actions need monitoring
- BLOCKED: NO_TRADE or risk limits exceeded

**Methods:** __init__, evaluate, status

*Line: 137*

---

## Function: 

*Line: 150*

---

## Function: 

Evaluate market state against decision table.

Args:
    regime: Market regime classification
    buy_pressure: Normalized buy pressure (0-1)
    sell_pressure: Normalized sell pressure (0-1)
    confidence: Signal confidence (0-1)
    volatility: Market volatility level
    daily_pnl_pct: Current daily PnL percentage

Returns:
    DecisionResult with action, risk_clearance, and details

*Line: 153*

---

## Function: 

Get current decision engine status.

*Line: 244*

---

