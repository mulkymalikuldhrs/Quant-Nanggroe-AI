# engine.execution.guards.cooldown

## Class: 

Result from a guard check.

*Line: 17*

---

## Class: 

Cooldown Guard.

Prevents placing trades for the same symbol too quickly.
Configurable cooldown period per symbol or globally.

Usage:
    guard = CooldownGuard(seconds=60)
    result = guard.check(order)
    if not result.allowed:
        # Order blocked by cooldown

**Methods:** __init__, check, record_trade, get_cooldown_remaining, reset

*Line: 24*

---

## Function: 

Initialize cooldown guard.

Args:
    seconds: Minimum seconds between trades for same symbol.

*Line: 37*

---

## Function: 

Check if order passes cooldown guard.

Args:
    order: Order to check.

Returns:
    GuardCheckResult with allow/deny decision.

*Line: 46*

---

## Function: 

Record that a trade was executed for a symbol.

Args:
    symbol: Trading symbol.

*Line: 68*

---

## Function: 

Get remaining cooldown time for a symbol.

Args:
    symbol: Trading symbol.

Returns:
    Remaining seconds (0 if no cooldown active).

*Line: 76*

---

## Function: 

Reset cooldown for a symbol or all symbols.

Args:
    symbol: Symbol to reset, or None for all.

*Line: 89*

---

