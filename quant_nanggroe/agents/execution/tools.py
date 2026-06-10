"""Execution Agent Tools for Quant Nanggroe AI Trading Framework."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

from langchain_core.tools import tool


logger = logging.getLogger(__name__)


@tool
def submit_order(
    symbol: str,
    action: str,
    quantity: float,
    order_type: str = "limit",
    price: Optional[float] = None,
    time_in_force: str = "GTC",
) -> str:
    """
    Submit an order to the broker.

    Args:
        symbol: Trading symbol
        action: BUY or SELL
        quantity: Number of shares/contracts
        order_type: Order type (market, limit, stop, stop_limit)
        price: Limit price (required for limit orders)
        time_in_force: Time in force (GTC, DAY, IOC, FOK)

    Returns:
        JSON string with order submission result
    """
    order_id = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    result = {
        "order_id": order_id,
        "symbol": symbol.upper(),
        "action": action.upper(),
        "quantity": quantity,
        "order_type": order_type,
        "price": price,
        "time_in_force": time_in_force,
        "status": "SUBMITTED",
        "submitted_at": datetime.now().isoformat(),
        "venue": "SMART_ROUTING",
        "message": f"Order {order_id} submitted: {action} {quantity} {symbol}",
    }
    return json.dumps(result, indent=2)


@tool
def cancel_order(order_id: str, reason: str = "User request") -> str:
    """
    Cancel an existing order.

    Args:
        order_id: Order ID to cancel
        reason: Cancellation reason

    Returns:
        JSON string with cancellation result
    """
    result = {
        "order_id": order_id,
        "status": "CANCELLED",
        "reason": reason,
        "cancelled_at": datetime.now().isoformat(),
        "message": f"Order {order_id} cancelled: {reason}",
    }
    return json.dumps(result, indent=2)


@tool
def get_fills(order_id: Optional[str] = None) -> str:
    """
    Get order fill information.

    Args:
        order_id: Optional specific order ID (returns all if not specified)

    Returns:
        JSON string with fill information
    """
    result = {
        "order_id": order_id or "ALL",
        "fills": [
            {
                "fill_id": f"FILL-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "order_id": order_id or "ORD-SAMPLE",
                "filled_quantity": 0,
                "fill_price": 0.0,
                "fill_time": datetime.now().isoformat(),
                "slippage_bps": 0,
                "venue": "PRIMARY",
            }
        ],
        "total_fills": 0 if order_id else 0,
        "timestamp": datetime.now().isoformat(),
    }
    return json.dumps(result, indent=2)


EXECUTION_TOOLS = [submit_order, cancel_order, get_fills]
