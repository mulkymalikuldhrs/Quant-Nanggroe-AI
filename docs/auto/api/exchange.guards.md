# exchange.guards

## Class: 

Result verdict from a guard check.

*Line: 51*

---

## Class: 

Result from a single guard check.

Attributes:
    verdict: Whether the order passed or failed.
    guard_name: Name of the guard that produced this result.
    reason: Human-readable reason (empty on pass).
    details: Additional details about the decision.

**Methods:** passed

*Line: 58*

---

## Class: 

Aggregated result from running all guards in a pipeline.

Attributes:
    passed: Whether all guards passed.
    results: Individual guard results in execution order.
    failed_guards: Names of guards that failed.
    reasons: Concatenated failure reasons.

*Line: 81*

---

## Class: 

Abstract base class for trading guards.

All guards must implement the :meth:`check` method, which takes an
order and returns a :class:`GuardResult`. Guards should also
implement :meth:`name` to identify themselves in logs and results.

**Methods:** name, check

*Line: 103*

---

## Class: 

Only allow trades for whitelisted symbols.

If no whitelist is set, all symbols are allowed (unless blocked).
The blocked list takes precedence over the whitelist.

Args:
    allowed_symbols: If set, only these symbols can be traded.
    blocked_symbols: These symbols are always blocked.

**Methods:** __init__, name, check, add_symbol, remove_symbol, block_symbol, unblock_symbol, allowed_symbols, blocked_symbols

*Line: 134*

---

## Class: 

Enforce minimum time between trades on the same symbol.

Args:
    seconds: Minimum cooldown period in seconds.
    per_symbol: If True, cooldown is per-symbol. If False, global cooldown.

**Methods:** __init__, name, check, record_trade, get_cooldown_remaining, reset

*Line: 227*

---

## Class: 

Enforce maximum position size limits.

Prevents position concentration by checking the notional value of
the resulting position against a percentage of portfolio or an
absolute notional limit.

Args:
    max_pct: Maximum position as fraction of portfolio (0.10 = 10%).
    max_notional: Maximum absolute notional value for any single position.
    portfolio_value: Current portfolio value for percentage calculations.

**Methods:** __init__, name, check, update_position, update_portfolio_value, remove_position

*Line: 333*

---

## Class: 

Composable pipeline that runs all guards in sequence.

Guards are executed in the order they are added. If any guard fails,
the pipeline stops and returns a failure result. All guard decisions
are logged.

Usage
-----
.. code-block:: python

    pipeline = GuardPipeline()
    pipeline.add_guard(WhitelistGuard(allowed_symbols=["BTC/USDT"]))
    pipeline.add_guard(CooldownGuard(seconds=60))
    pipeline.add_guard(MaxPositionGuard(max_pct=0.10))

    result = pipeline.check(order)
    if not result.passed:
        print("Order rejected:", result.reasons)

**Methods:** __init__, name, guards, add_guard, remove_guard, check, check_single, get_guard, clear

*Line: 454*

---

## Function: 

Whether the order passed this guard.

*Line: 74*

---

## Function: 

Human-readable name of this guard.

*Line: 113*

---

## Function: 

Check whether an order passes this guard.

Args:
    order: The order to validate.
    context: Optional context dict with additional info
        (e.g., current positions, portfolio value).

Returns:
    :class:`GuardResult` with pass/fail verdict and reason.

*Line: 117*

---

## Function: 

*Line: 145*

---

## Function: 

*Line: 158*

---

## Function: 

Check if the order's symbol is allowed.

*Line: 161*

---

## Function: 

Add a symbol to the whitelist.

*Line: 194*

---

## Function: 

Remove a symbol from the whitelist.

*Line: 199*

---

## Function: 

Block a symbol.

*Line: 204*

---

## Function: 

Unblock a symbol.

*Line: 208*

---

## Function: 

Get the set of allowed symbols.

*Line: 213*

---

## Function: 

Get the set of blocked symbols.

*Line: 218*

---

## Function: 

*Line: 235*

---

## Function: 

*Line: 246*

---

## Function: 

Check if the cooldown period has elapsed.

*Line: 249*

---

## Function: 

Record that a trade was executed for a symbol.

Call this after a trade is successfully placed.

Args:
    symbol: Trading symbol.

*Line: 287*

---

## Function: 

Get remaining cooldown time for a symbol.

Args:
    symbol: Trading symbol.

Returns:
    Remaining seconds (0 if no cooldown active).

*Line: 299*

---

## Function: 

Reset cooldown for a symbol or all symbols.

Args:
    symbol: Symbol to reset, or None for all.

*Line: 316*

---

## Function: 

*Line: 346*

---

## Function: 

*Line: 358*

---

## Function: 

Check if the order would exceed position limits.

*Line: 361*

---

## Function: 

Update the tracked position notional value.

Args:
    symbol: Trading symbol.
    notional: New position notional value.

*Line: 424*

---

## Function: 

Update the total portfolio value.

Args:
    value: New portfolio value.

*Line: 433*

---

## Function: 

Remove a position from tracking.

Args:
    symbol: Trading symbol.

*Line: 441*

---

## Function: 

Initialize the pipeline.

Args:
    name: Human-readable name for this pipeline.

*Line: 475*

---

## Function: 

Pipeline name.

*Line: 485*

---

## Function: 

List of guards in this pipeline.

*Line: 490*

---

## Function: 

Add a guard to the pipeline.

Args:
    guard: A :class:`BaseGuard` implementation.

Raises:
    TypeError: If the guard is not a BaseGuard instance.

*Line: 494*

---

## Function: 

Remove a guard by name.

Args:
    guard_name: Name of the guard to remove.

Returns:
    True if a guard was removed, False otherwise.

*Line: 508*

---

## Function: 

Run all guards against an order.

Args:
    order: The order to validate.
    context: Optional context dict with additional info.
    fail_fast: If True, stop on first failure. If False, run all guards.

Returns:
    :class:`PipelineResult` with aggregated results.

*Line: 524*

---

## Function: 

Run a single guard by name.

Args:
    guard_name: Name of the guard to run.
    order: The order to validate.
    context: Optional context dict.

Returns:
    :class:`GuardResult` or None if the guard is not found.

*Line: 578*

---

## Function: 

Get a guard by name.

Args:
    guard_name: Name of the guard.

Returns:
    The guard instance, or None if not found.

*Line: 599*

---

## Function: 

Remove all guards from the pipeline.

*Line: 613*

---

