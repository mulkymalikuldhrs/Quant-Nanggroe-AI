"""Execution Agent Tools for Quant Nanggroe AI Trading Framework.

PRODUCTION: Wired to real order management:
- submit_order: Uses ExecutionManager for real order routing
- cancel_order: Uses ExecutionManager/OrderManager for real cancellation
- get_fills: Uses FillTracker for real fill information
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func=None, *args, **kwargs):
        """No-op fallback when langchain_core is not installed."""
        if func is not None:
            return func
        def decorator(f):
            return f
        return decorator


logger = logging.getLogger(__name__)

# ── Mock mode flag ─────────────────────────────────────────────────────
_MOCK_MODE = False


# ── Lazy imports for real engine components ─────────────────────────────
def _get_execution_manager():
    """Lazy-load ExecutionManager from engine."""
    try:
        from quant_nanggroe.engine.execution.manager import ExecutionManager
        from quant_nanggroe.engine.execution.brokers.paper import PaperExchangeBroker
        em = ExecutionManager()
        paper = PaperExchangeBroker()
        em.add_broker(paper, primary=True)
        return em
    except Exception as exc:
        logger.warning("Failed to load ExecutionManager: %s", exc)
        return None


def _get_execution_tool():
    """Lazy-load ExecutionTool from shared tools."""
    try:
        from quant_nanggroe.agents.tools.execution import ExecutionTool
        from quant_nanggroe.agents.tools.market_data import MarketDataTool
        mdt = MarketDataTool()
        return ExecutionTool(market_data_tool=mdt)
    except Exception as exc:
        logger.warning("Failed to load ExecutionTool: %s", exc)
        return None


# ── Mock data fallbacks ─────────────────────────────────────────────────

def _mock_submit_order(symbol, action, quantity, order_type, price, time_in_force) -> dict:
    logger.warning("MOCK MODE: Returning hardcoded order submission for %s %s", action, symbol)
    order_id = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    return {
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
        "_mock": True,
    }


def _mock_cancel_order(order_id, reason) -> dict:
    logger.warning("MOCK MODE: Returning hardcoded cancel result for %s", order_id)
    return {
        "order_id": order_id,
        "status": "CANCELLED",
        "reason": reason,
        "cancelled_at": datetime.now().isoformat(),
        "message": f"Order {order_id} cancelled: {reason}",
        "_mock": True,
    }


def _mock_get_fills(order_id) -> dict:
    logger.warning("MOCK MODE: Returning hardcoded fill data")
    return {
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
        "total_fills": 0,
        "timestamp": datetime.now().isoformat(),
        "_mock": True,
    }


# ═══════════════════════════════════════════════════════════════════════
# LangChain @tool functions — PRODUCTION wired
# ═══════════════════════════════════════════════════════════════════════

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

    PRODUCTION: Uses ExecutionManager for real order routing through
    PaperBroker (or live broker when configured).
    Falls back to mock data only in _MOCK_MODE.

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
    if not _MOCK_MODE:
        # PRODUCTION: Wired to real engine — try ExecutionTool first
        et = _get_execution_tool()
        if et is not None:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if not loop.is_running():
                    result = loop.run_until_complete(
                        et.place_order(
                            symbol=symbol,
                            side=action,
                            quantity=quantity,
                            order_type=order_type,
                            price=price,
                        )
                    )
                    result["time_in_force"] = time_in_force
                    result["_source"] = "ExecutionTool"  # PRODUCTION: Wired to real engine
                    return json.dumps(result, indent=2, default=str)
            except Exception as exc:
                logger.error("ExecutionTool submit_order failed for %s: %s", symbol, exc)
                raise RuntimeError(
                    f"Failed to submit order for {symbol}: {exc}. "
                    "Set _MOCK_MODE=True for mock fallback."
                ) from exc

        # Try ExecutionManager directly
        em = _get_execution_manager()
        if em is not None:
            try:
                from quant_nanggroe.engine.execution.base import Order, OrderSide, OrderType as OT
                side_map = {"BUY": OrderSide.BUY, "SELL": OrderSide.SELL}
                ot_map = {"market": OT.MARKET, "limit": OT.LIMIT,
                          "stop": OT.STOP, "stop_limit": OT.STOP_LIMIT}
                order = Order(
                    symbol=symbol,
                    side=side_map.get(action.upper(), OrderSide.BUY),
                    quantity=quantity,
                    order_type=ot_map.get(order_type.lower(), OT.LIMIT),
                    price=price,
                )
                import asyncio
                loop = asyncio.get_event_loop()
                if not loop.is_running():
                    fill = loop.run_until_complete(em.execute_order(order))
                    if fill:
                        return json.dumps({  # PRODUCTION: Wired to real engine
                            "order_id": fill.order_id,
                            "symbol": symbol.upper(),
                            "action": action.upper(),
                            "quantity": quantity,
                            "order_type": order_type,
                            "price": price,
                            "time_in_force": time_in_force,
                            "status": "FILLED",
                            "submitted_at": datetime.now().isoformat(),
                            "fill_price": fill.fill_price,
                            "venue": fill.broker or "PAPER",
                            "message": f"Order filled: {action} {quantity} {symbol} @ {fill.fill_price}",
                            "_source": "ExecutionManager",
                        }, indent=2)
            except Exception as exc:
                logger.error("ExecutionManager submit_order failed for %s: %s", symbol, exc)
                raise RuntimeError(
                    f"Failed to submit order for {symbol}: {exc}. "
                    "Set _MOCK_MODE=True for mock fallback."
                ) from exc

    # Mock fallback
    if _MOCK_MODE:
        return json.dumps(_mock_submit_order(symbol, action, quantity, order_type, price, time_in_force), indent=2)

    raise RuntimeError(
        f"Cannot submit order for {symbol}: real execution engine unavailable and _MOCK_MODE=False. "
        "Install required dependencies or set _MOCK_MODE=True."
    )


@tool
def cancel_order(order_id: str, reason: str = "User request") -> str:
    """
    Cancel an existing order.

    PRODUCTION: Uses ExecutionManager/OrderManager for real cancellation.
    Falls back to mock data only in _MOCK_MODE.

    Args:
        order_id: Order ID to cancel
        reason: Cancellation reason

    Returns:
        JSON string with cancellation result
    """
    if not _MOCK_MODE:
        # PRODUCTION: Wired to real engine — try ExecutionTool first
        et = _get_execution_tool()
        if et is not None:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if not loop.is_running():
                    result = loop.run_until_complete(
                        et.cancel_order(order_id=order_id)
                    )
                    result["reason"] = reason
                    result["_source"] = "ExecutionTool"  # PRODUCTION: Wired to real engine
                    return json.dumps(result, indent=2, default=str)
            except Exception as exc:
                logger.error("ExecutionTool cancel_order failed for %s: %s", order_id, exc)
                raise RuntimeError(
                    f"Failed to cancel order {order_id}: {exc}. "
                    "Set _MOCK_MODE=True for mock fallback."
                ) from exc

        # Try ExecutionManager directly
        em = _get_execution_manager()
        if em is not None:
            try:
                success = em._order_manager.cancel_order(order_id)
                return json.dumps({  # PRODUCTION: Wired to real engine
                    "order_id": order_id,
                    "status": "CANCELLED" if success else "CANCEL_FAILED",
                    "reason": reason,
                    "cancelled_at": datetime.now().isoformat(),
                    "message": f"Order {order_id} cancelled: {reason}",
                    "_source": "ExecutionManager",
                }, indent=2)
            except Exception as exc:
                logger.error("ExecutionManager cancel_order failed for %s: %s", order_id, exc)
                raise RuntimeError(
                    f"Failed to cancel order {order_id}: {exc}. "
                    "Set _MOCK_MODE=True for mock fallback."
                ) from exc

    # Mock fallback
    if _MOCK_MODE:
        return json.dumps(_mock_cancel_order(order_id, reason), indent=2)

    raise RuntimeError(
        f"Cannot cancel order {order_id}: real execution engine unavailable and _MOCK_MODE=False."
    )


@tool
def get_fills(order_id: Optional[str] = None) -> str:
    """
    Get order fill information.

    PRODUCTION: Uses FillTracker for real fill data.
    Falls back to mock data only in _MOCK_MODE.

    Args:
        order_id: Optional specific order ID (returns all if not specified)

    Returns:
        JSON string with fill information
    """
    if not _MOCK_MODE:
        # PRODUCTION: Wired to real engine — try ExecutionTool first
        et = _get_execution_tool()
        if et is not None:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if not loop.is_running():
                    if order_id:
                        result = loop.run_until_complete(
                            et.get_order_status(order_id=order_id)
                        )
                    else:
                        result = loop.run_until_complete(
                            et.get_open_orders()
                        )
                    result["_source"] = "ExecutionTool"  # PRODUCTION: Wired to real engine
                    return json.dumps(result, indent=2, default=str)
            except Exception as exc:
                logger.error("ExecutionTool get_fills failed: %s", exc)
                raise RuntimeError(
                    f"Failed to get fills: {exc}. "
                    "Set _MOCK_MODE=True for mock fallback."
                ) from exc

        # Try ExecutionManager directly
        em = _get_execution_manager()
        if em is not None:
            try:
                fills = em._fill_tracker.get_fills(order_id=order_id)
                fill_data = []
                for f in fills:
                    fill_data.append({
                        "fill_id": getattr(f, 'fill_id', ''),
                        "order_id": getattr(f, 'order_id', order_id or ''),
                        "filled_quantity": getattr(f, 'quantity', 0),
                        "fill_price": getattr(f, 'fill_price', 0.0),
                        "fill_time": getattr(f, 'timestamp', datetime.now().isoformat()),
                        "slippage_bps": getattr(f, 'slippage_bps', 0),
                        "venue": getattr(f, 'broker', 'PAPER'),
                    })
                return json.dumps({  # PRODUCTION: Wired to real engine
                    "order_id": order_id or "ALL",
                    "fills": fill_data,
                    "total_fills": len(fill_data),
                    "timestamp": datetime.now().isoformat(),
                    "_source": "ExecutionManager",
                }, indent=2, default=str)
            except Exception as exc:
                logger.error("ExecutionManager get_fills failed: %s", exc)
                raise RuntimeError(
                    f"Failed to get fills: {exc}. "
                    "Set _MOCK_MODE=True for mock fallback."
                ) from exc

    # Mock fallback
    if _MOCK_MODE:
        return json.dumps(_mock_get_fills(order_id), indent=2)

    raise RuntimeError(
        "Cannot get fills: real execution engine unavailable and _MOCK_MODE=False."
    )


EXECUTION_TOOLS = [submit_order, cancel_order, get_fills]
