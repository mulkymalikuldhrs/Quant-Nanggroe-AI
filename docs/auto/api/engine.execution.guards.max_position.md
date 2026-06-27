# engine.execution.guards.max_position

## Class: 

Max Position Guard.

Prevents position concentration by enforcing maximum position
size limits. Can be configured per-symbol or as a global limit.

Usage:
    guard = MaxPositionGuard(max_pct=0.10)
    result = guard.check(order)

**Methods:** __init__, check, update_position, update_portfolio_value, remove_position

*Line: 15*

---

## Function: 

Initialize max position guard.

Args:
    max_pct: Maximum position size as fraction of portfolio (0.10 = 10%).
    max_notional: Maximum notional value for any single position.

*Line: 26*

---

## Function: 

Check if order passes max position guard.

Args:
    order: Order to check.

Returns:
    Dict with 'allowed' (bool) and 'reason' (str).

*Line: 42*

---

## Function: 

Update the tracked position notional value.

Args:
    symbol: Trading symbol.
    notional: New position notional value.

*Line: 78*

---

## Function: 

Update the total portfolio value.

Args:
    value: New portfolio value.

*Line: 87*

---

## Function: 

Remove a position from tracking.

Args:
    symbol: Trading symbol.

*Line: 95*

---

