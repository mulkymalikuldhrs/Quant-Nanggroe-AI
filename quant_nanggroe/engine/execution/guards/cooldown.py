"""Cooldown Guard — Prevent rapid-fire trades.

Enforces a minimum time interval between trades for the same symbol
to prevent overtrading and reduce market impact.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from quant_nanggroe.engine.execution.base import Order, OrderSide


@dataclass
class GuardCheckResult:
    """Result from a guard check."""

    allowed: bool
    reason: str = ""


class CooldownGuard:
    """Cooldown Guard.

    Prevents placing trades for the same symbol too quickly.
    Configurable cooldown period per symbol or globally.

    Usage:
        guard = CooldownGuard(seconds=60)
        result = guard.check(order)
        if not result.allowed:
            # Order blocked by cooldown
    """

    def __init__(self, seconds: float = 60.0) -> None:
        """Initialize cooldown guard.

        Args:
            seconds: Minimum seconds between trades for same symbol.
        """
        self._cooldown_seconds = seconds
        self._last_trade_time: Dict[str, float] = {}

    def check(self, order: Order) -> GuardCheckResult:
        """Check if order passes cooldown guard.

        Args:
            order: Order to check.

        Returns:
            GuardCheckResult with allow/deny decision.
        """
        now = time.time()
        last_time = self._last_trade_time.get(order.symbol, 0.0)
        elapsed = now - last_time

        if elapsed < self._cooldown_seconds:
            remaining = self._cooldown_seconds - elapsed
            return GuardCheckResult(
                allowed=False,
                reason=f"Cooldown active for {order.symbol}: {remaining:.1f}s remaining",
            )

        return GuardCheckResult(allowed=True)

    def record_trade(self, symbol: str) -> None:
        """Record that a trade was executed for a symbol.

        Args:
            symbol: Trading symbol.
        """
        self._last_trade_time[symbol] = time.time()

    def get_cooldown_remaining(self, symbol: str) -> float:
        """Get remaining cooldown time for a symbol.

        Args:
            symbol: Trading symbol.

        Returns:
            Remaining seconds (0 if no cooldown active).
        """
        last_time = self._last_trade_time.get(symbol, 0.0)
        elapsed = time.time() - last_time
        return max(0.0, self._cooldown_seconds - elapsed)

    def reset(self, symbol: Optional[str] = None) -> None:
        """Reset cooldown for a symbol or all symbols.

        Args:
            symbol: Symbol to reset, or None for all.
        """
        if symbol:
            self._last_trade_time.pop(symbol, None)
        else:
            self._last_trade_time.clear()
