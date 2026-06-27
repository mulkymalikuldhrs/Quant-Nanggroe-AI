# engine.execution.guards.whitelist

## Class: 

Symbol Whitelist Guard.

Only allows orders for symbols that are on the approved whitelist.
If no whitelist is set, all symbols are allowed.

Usage:
    guard = WhitelistGuard(allowed_symbols=["AAPL", "GOOGL", "MSFT"])
    result = guard.check(order)

**Methods:** __init__, check, add_symbol, remove_symbol, block_symbol, unblock_symbol, allowed_symbols, blocked_symbols

*Line: 15*

---

## Function: 

Initialize whitelist guard.

Args:
    allowed_symbols: If set, only these symbols can be traded.
    blocked_symbols: These symbols are always blocked, regardless of whitelist.

*Line: 26*

---

## Function: 

Check if order passes whitelist guard.

Args:
    order: Order to check.

Returns:
    Dict with 'allowed' (bool) and 'reason' (str).

*Line: 44*

---

## Function: 

Add a symbol to the whitelist.

Args:
    symbol: Symbol to add.

*Line: 71*

---

## Function: 

Remove a symbol from the whitelist.

Args:
    symbol: Symbol to remove.

*Line: 80*

---

## Function: 

Block a symbol.

Args:
    symbol: Symbol to block.

*Line: 89*

---

## Function: 

Unblock a symbol.

Args:
    symbol: Symbol to unblock.

*Line: 97*

---

## Function: 

Get the set of allowed symbols.

*Line: 106*

---

## Function: 

Get the set of blocked symbols.

*Line: 111*

---

