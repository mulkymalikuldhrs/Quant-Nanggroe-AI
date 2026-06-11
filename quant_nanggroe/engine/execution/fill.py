"""Fill Tracking and Reconciliation.

Tracks all fills (executions), provides reconciliation between
orders and fills, and computes execution quality metrics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from quant_nanggroe.engine.execution.base import Fill, OrderSide


@dataclass
class ExecutionQuality:
    """Execution quality metrics for a fill."""

    fill_id: str
    symbol: str
    side: OrderSide
    expected_price: float
    actual_price: float
    slippage_bps: float
    commission: float
    total_cost: float


class FillTracker:
    """Fill tracking and reconciliation.

    Tracks all fills, computes execution quality metrics,
    and provides query capabilities for fill analysis.
    """

    def __init__(self) -> None:
        self._fills: Dict[str, Fill] = {}
        self._fills_by_order: Dict[str, List[Fill]] = {}

    def record(self, fill: Fill) -> None:
        """Record a fill.

        Args:
            fill: Fill to record.
        """
        self._fills[fill.id] = fill
        if fill.order_id not in self._fills_by_order:
            self._fills_by_order[fill.order_id] = []
        self._fills_by_order[fill.order_id].append(fill)

    def get(self, fill_id: str) -> Optional[Fill]:
        """Get a fill by ID."""
        return self._fills.get(fill_id)

    def get_by_order(self, order_id: str) -> List[Fill]:
        """Get all fills for an order."""
        return self._fills_by_order.get(order_id, [])

    def get_by_symbol(self, symbol: str) -> List[Fill]:
        """Get all fills for a symbol."""
        return [f for f in self._fills.values() if f.symbol == symbol]

    def compute_execution_quality(
        self,
        fill: Fill,
        expected_price: float,
    ) -> ExecutionQuality:
        """Compute execution quality metrics for a fill.

        Args:
            fill: Fill to analyze.
            expected_price: Expected execution price.

        Returns:
            ExecutionQuality with slippage and cost metrics.
        """
        if expected_price > 0:
            slippage_bps = abs(fill.price - expected_price) / expected_price * 10000
        else:
            slippage_bps = 0.0

        total_cost = fill.commission + abs(fill.price - expected_price) * fill.quantity

        return ExecutionQuality(
            fill_id=fill.id,
            symbol=fill.symbol,
            side=fill.side,
            expected_price=expected_price,
            actual_price=fill.price,
            slippage_bps=slippage_bps,
            commission=fill.commission,
            total_cost=total_cost,
        )

    def get_total_commission(self) -> float:
        """Get total commission paid across all fills."""
        return sum(f.commission for f in self._fills.values())

    def get_total_slippage(self) -> float:
        """Get total slippage across all fills."""
        return sum(f.slippage for f in self._fills.values())

    def get_fill_count(self) -> int:
        """Get total number of fills."""
        return len(self._fills)

    def get_buys_sells(self, symbol: Optional[str] = None) -> Dict[str, int]:
        """Get count of buys and sells, optionally filtered by symbol.

        Args:
            symbol: Optional symbol filter.

        Returns:
            Dict with 'buys' and 'sells' counts.
        """
        fills = [f for f in self._fills.values() if symbol is None or f.symbol == symbol]
        return {
            "buys": sum(1 for f in fills if f.side == OrderSide.BUY),
            "sells": sum(1 for f in fills if f.side == OrderSide.SELL),
        }
