"""Max Position Guard — Limit position concentration.

Prevents over-concentration in a single symbol by enforcing
maximum position size limits as a percentage of portfolio.
"""

from __future__ import annotations

from typing import Dict, Optional

from quant_nanggroe.engine.execution.base import Order, OrderSide


class MaxPositionGuard:
    """Max Position Guard.

    Prevents position concentration by enforcing maximum position
    size limits. Can be configured per-symbol or as a global limit.

    Usage:
        guard = MaxPositionGuard(max_pct=0.10)
        result = guard.check(order)
    """

    def __init__(
        self,
        max_pct: float = 0.10,
        max_notional: Optional[float] = None,
    ) -> None:
        """Initialize max position guard.

        Args:
            max_pct: Maximum position size as fraction of portfolio (0.10 = 10%).
            max_notional: Maximum notional value for any single position.
        """
        self._max_pct = max_pct
        self._max_notional = max_notional
        self._current_positions: Dict[str, float] = {}  # symbol -> notional value
        self._portfolio_value: float = 0.0  # FAIL-CLOSED: must be set via update_portfolio_value()

    def check(self, order: Order) -> dict:
        """Check if order passes max position guard.

        Args:
            order: Order to check.

        Returns:
            Dict with 'allowed' (bool) and 'reason' (str).
        """
        order_notional = order.quantity * (order.price or 0.0)
        current_notional = self._current_positions.get(order.symbol, 0.0)

        if order.side == OrderSide.BUY:
            new_notional = current_notional + order_notional
        else:
            new_notional = max(0.0, current_notional - order_notional)

        # FAIL-CLOSED: portfolio value must be set before trading
        if self._portfolio_value <= 0:
            return {
                "allowed": False,
                "reason": "Portfolio value not initialized — cannot validate position size",
            }

        # Check percentage limit
        max_allowed = self._portfolio_value * self._max_pct
        if new_notional > max_allowed:
            return {
                "allowed": False,
                "reason": f"Position would exceed {self._max_pct:.0%} of portfolio "
                          f"({new_notional:.0f} > {max_allowed:.0f})",
            }

        # Check notional limit
        if self._max_notional and new_notional > self._max_notional:
            return {
                "allowed": False,
                "reason": f"Position would exceed max notional "
                          f"({new_notional:.0f} > {self._max_notional:.0f})",
            }

        return {"allowed": True, "reason": ""}

    def update_position(self, symbol: str, notional: float) -> None:
        """Update the tracked position notional value.

        Args:
            symbol: Trading symbol.
            notional: New position notional value.
        """
        self._current_positions[symbol] = notional

    def update_portfolio_value(self, value: float) -> None:
        """Update the total portfolio value.

        Args:
            value: New portfolio value.
        """
        self._portfolio_value = value

    def remove_position(self, symbol: str) -> None:
        """Remove a position from tracking.

        Args:
            symbol: Trading symbol.
        """
        self._current_positions.pop(symbol, None)
