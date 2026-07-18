"""Fill Tracking, Reconciliation, and Crash-Safe Persistence.

Tracks all fills (executions), provides reconciliation between
orders and fills, computes execution quality metrics, and persists
state to disk for crash recovery.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

from quant_nanggroe.engine.execution.base import Fill, OrderSide

logger = logging.getLogger(__name__)

_STATE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "paper_state",
)


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
        self._state_path: Optional[str] = None
        self._setup_persistence()
        self._load()

    def _setup_persistence(self) -> None:
        """Initialize persistence path."""
        try:
            os.makedirs(_STATE_DIR, exist_ok=True)
            self._state_path = os.path.join(_STATE_DIR, "fills.json")
        except Exception:
            self._state_path = None

    def _persist(self) -> None:
        """Save all fills to disk (atomic write)."""
        if not self._state_path:
            return
        try:
            data = [asdict(f) for f in self._fills.values()]
            tmp = self._state_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, default=str, indent=2)
            os.replace(tmp, self._state_path)
        except Exception as exc:
            logger.warning("Failed to persist fills: %s", exc)

    def _load(self) -> None:
        """Load fills from disk on startup."""
        if not self._state_path or not os.path.exists(self._state_path):
            return
        try:
            with open(self._state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for d in data:
                fill = Fill(
                    id=d["id"],
                    order_id=d["order_id"],
                    symbol=d["symbol"],
                    side=OrderSide(d["side"]),
                    quantity=d["quantity"],
                    price=d["price"],
                    commission=d.get("commission", 0.0),
                    slippage=d.get("slippage", 0.0),
                    timestamp=d.get("timestamp", ""),
                )
                self._fills[fill.id] = fill
                if fill.order_id not in self._fills_by_order:
                    self._fills_by_order[fill.order_id] = []
                self._fills_by_order[fill.order_id].append(fill)
            logger.info("Loaded %d fills from disk", len(self._fills))
        except Exception as exc:
            logger.warning("Failed to load fills from disk: %s", exc)

    def record(self, fill: Fill) -> None:
        """Record a fill.

        Args:
            fill: Fill to record.
        """
        self._fills[fill.id] = fill
        if fill.order_id not in self._fills_by_order:
            self._fills_by_order[fill.order_id] = []
        self._fills_by_order[fill.order_id].append(fill)
        self._persist()

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
