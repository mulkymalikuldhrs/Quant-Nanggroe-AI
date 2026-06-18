"""Order Management — tracking, lifecycle, and state transitions.

Provides order tracking, state management, and query capabilities
for all orders flowing through the execution engine.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from quant_nanggroe.engine.execution.base import Order, OrderStatus, OrderSide, OrderType


class OrderManager:
    """Order lifecycle manager.

    Tracks all orders, manages state transitions, and provides
    query capabilities for order analysis and reconciliation.
    """

    def __init__(self) -> None:
        self._orders: Dict[str, Order] = {}

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
