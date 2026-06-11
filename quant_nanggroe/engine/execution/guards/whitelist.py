"""Symbol Whitelist Guard — Only trade approved symbols.

Enforces a whitelist of approved trading symbols to prevent
trading on unapproved or dangerous instruments.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Set

from quant_nanggroe.engine.execution.base import Order


class WhitelistGuard:
    """Symbol Whitelist Guard.

    Only allows orders for symbols that are on the approved whitelist.
    If no whitelist is set, all symbols are allowed.

    Usage:
        guard = WhitelistGuard(allowed_symbols=["AAPL", "GOOGL", "MSFT"])
        result = guard.check(order)
    """

    def __init__(
        self,
        allowed_symbols: Optional[List[str]] = None,
        blocked_symbols: Optional[List[str]] = None,
    ) -> None:
        """Initialize whitelist guard.

        Args:
            allowed_symbols: If set, only these symbols can be traded.
            blocked_symbols: These symbols are always blocked, regardless of whitelist.
        """
        self._allowed: Optional[Set[str]] = (
            set(s.upper() for s in allowed_symbols) if allowed_symbols else None
        )
        self._blocked: Set[str] = (
            set(s.upper() for s in blocked_symbols) if blocked_symbols else set()
        )

    def check(self, order: Order) -> dict:
        """Check if order passes whitelist guard.

        Args:
            order: Order to check.

        Returns:
            Dict with 'allowed' (bool) and 'reason' (str).
        """
        symbol_upper = order.symbol.upper()

        # Check blocked list first
        if symbol_upper in self._blocked:
            return {
                "allowed": False,
                "reason": f"Symbol {order.symbol} is on the blocked list",
            }

        # Check whitelist
        if self._allowed is not None and symbol_upper not in self._allowed:
            return {
                "allowed": False,
                "reason": f"Symbol {order.symbol} is not on the approved whitelist",
            }

        return {"allowed": True, "reason": ""}

    def add_symbol(self, symbol: str) -> None:
        """Add a symbol to the whitelist.

        Args:
            symbol: Symbol to add.
        """
        if self._allowed is not None:
            self._allowed.add(symbol.upper())

    def remove_symbol(self, symbol: str) -> None:
        """Remove a symbol from the whitelist.

        Args:
            symbol: Symbol to remove.
        """
        if self._allowed is not None:
            self._allowed.discard(symbol.upper())

    def block_symbol(self, symbol: str) -> None:
        """Block a symbol.

        Args:
            symbol: Symbol to block.
        """
        self._blocked.add(symbol.upper())

    def unblock_symbol(self, symbol: str) -> None:
        """Unblock a symbol.

        Args:
            symbol: Symbol to unblock.
        """
        self._blocked.discard(symbol.upper())

    @property
    def allowed_symbols(self) -> Optional[Set[str]]:
        """Get the set of allowed symbols."""
        return self._allowed

    @property
    def blocked_symbols(self) -> Set[str]:
        """Get the set of blocked symbols."""
        return self._blocked
