"""Order Management — tracking, lifecycle, and state persistence.

Provides order tracking, state management, query capabilities,
and crash-safe persistence for all orders flowing through the
execution engine.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import asdict
from typing import Dict, List, Optional

from quant_nanggroe.engine.execution.base import Order, OrderSide, OrderStatus, OrderType

logger = logging.getLogger(__name__)

_STATE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "paper_state",
)


class OrderManager:
    """Order lifecycle manager.

    Tracks all orders, manages state transitions, and provides
    query capabilities for order analysis and reconciliation.
    """

    def __init__(self) -> None:
        self._orders: Dict[str, Order] = {}
        self._state_path: Optional[str] = None
        self._setup_persistence()
        self._load()

    def _setup_persistence(self) -> None:
        """Initialize persistence path."""
        try:
            os.makedirs(_STATE_DIR, exist_ok=True)
            self._state_path = os.path.join(_STATE_DIR, "orders.json")
        except Exception:
            self._state_path = None

    def _persist(self) -> None:
        """Save all orders to disk (atomic write)."""
        if not self._state_path:
            return
        try:
            data = []
            for o in self._orders.values():
                d = asdict(o)
                data.append(d)
            tmp = self._state_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, default=str, indent=2)
            os.replace(tmp, self._state_path)
        except Exception as exc:
            logger.warning("Failed to persist orders: %s", exc)

    def _load(self) -> None:
        """Load orders from disk on startup."""
        if not self._state_path or not os.path.exists(self._state_path):
            return
        try:
            with open(self._state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for d in data:
                order = Order(
                    id=d["id"],
                    symbol=d["symbol"],
                    side=OrderSide(d["side"]),
                    order_type=OrderType(d["order_type"]),
                    quantity=d["quantity"],
                    price=d.get("price"),
                    stop_price=d.get("stop_price"),
                    time_in_force=d.get("time_in_force", "GTC"),
                    status=OrderStatus(d["status"]),
                    created_at=d.get("created_at", ""),
                    updated_at=d.get("updated_at", ""),
                    metadata=d.get("metadata", {}),
                )
                self._orders[order.id] = order
            logger.info("Loaded %d orders from disk", len(self._orders))
        except Exception as exc:
            logger.warning("Failed to load orders from disk: %s", exc)

    def create_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "GTC",
    ) -> Order:
        """Create a new order.

        Args:
            symbol: Trading symbol.
            side: BUY or SELL.
            quantity: Number of units.
            order_type: Market, limit, stop, etc.
            price: Limit price.
            stop_price: Stop trigger price.
            time_in_force: GTC, DAY, IOC, FOK.

        Returns:
            New Order instance with assigned ID.
        """
        order = Order(
            id=str(uuid.uuid4()),
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            time_in_force=time_in_force,
            status=OrderStatus.PENDING,
        )
        self._orders[order.id] = order
        return order

    def track(self, order: Order) -> None:
        """Track an existing order.

        Args:
            order: Order to track.
        """
        self._orders[order.id] = order
        self._persist()

    def get(self, order_id: str) -> Optional[Order]:
        """Get an order by ID.

        Args:
            order_id: Order ID.

        Returns:
            Order if found, None otherwise.
        """
        return self._orders.get(order_id)

    def update_status(self, order_id: str, status: OrderStatus) -> Optional[Order]:
        """Update order status.

        Args:
            order_id: Order ID.
            status: New status.

        Returns:
            Updated Order if found, None otherwise.
        """
        order = self._orders.get(order_id)
        if order is None:
            return None

        updated = Order(
            id=order.id,
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            quantity=order.quantity,
            price=order.price,
            stop_price=order.stop_price,
            time_in_force=order.time_in_force,
            status=status,
            created_at=order.created_at,
            metadata=order.metadata,
        )
        self._orders[order_id] = updated
        self._persist()
        return updated

    def get_by_symbol(self, symbol: str) -> List[Order]:
        """Get all orders for a symbol.

        Args:
            symbol: Trading symbol.

        Returns:
            List of Orders for the symbol.
        """
        return [o for o in self._orders.values() if o.symbol == symbol]

    def get_by_status(self, status: OrderStatus) -> List[Order]:
        """Get all orders with a given status.

        Args:
            status: Order status to filter by.

        Returns:
            List of Orders with the given status.
        """
        return [o for o in self._orders.values() if o.status == status]

    def get_open_orders(self) -> List[Order]:
        """Get all open (pending/submitted) orders.

        Returns:
            List of open Orders.
        """
        return [
            o for o in self._orders.values()
            if o.status in (OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED)
        ]

    @property
    def total_orders(self) -> int:
        """Total number of tracked orders."""
        return len(self._orders)
