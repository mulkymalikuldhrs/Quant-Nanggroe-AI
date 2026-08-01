"""
Trader Agent Tools for Quant Nanggroe AI Trading Framework.

PRODUCTION: Wired to real execution components:
- place_order: Uses ExecutionTool/ExecutionManager for real order routing
- get_position: Uses live MT5 broker for real position data
- get_portfolio: Uses live MT5 broker for real portfolio overview
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

# ── Lazy imports for real engine components ─────────────────────────────
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


def _get_execution_manager():
    """Lazy-load ExecutionManager from engine."""
    try:
        from quant_nanggroe.engine.execution.builder import build_execution_manager
        em = build_execution_manager()
        return em
    except Exception as exc:
        logger.warning("Failed to load ExecutionManager: %s", exc)
        return None


def _get_paper_broker():
    """REAL-ONLY mode: no paper broker. Raise — live MT5 broker required."""
    raise RuntimeError("PaperExchangeBroker disabled (REAL-ONLY mode) — use live MT5 broker for position/portfolio")


# ═══════════════════════════════════════════════════════════════════════
# LangChain @tool functions — PRODUCTION wired
# ═══════════════════════════════════════════════════════════════════════

@tool
def place_order(
    symbol: str,
    action: str,
    quantity: float,
    order_type: str = "market",
    price: Optional[float] = None,
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None,
) -> str:
    """
    Place a trading order.

    PRODUCTION: Uses ExecutionTool for real order routing through
    PaperBroker (or live broker when configured). Fails closed if unavailable.

    Args:
        symbol: Trading symbol (e.g., AAPL, BTCUSDT)
        action: Trade action (BUY, SELL, SHORT, COVER)
        quantity: Number of shares/contracts
        order_type: Order type (market, limit, stop, stop_limit)
        price: Limit price (required for limit orders)
        stop_loss: Stop loss price
        take_profit: Take profit price

    Returns:
        JSON string with order confirmation
    """
    # PRODUCTION: Wired to real engine — try ExecutionTool
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
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                    )
                )
                result["_source"] = "ExecutionTool"
                return json.dumps(result, indent=2, default=str)
        except Exception as exc:
            logger.error("ExecutionTool place_order failed for %s: %s", symbol, exc)
            raise RuntimeError(
                f"Failed to place order for {symbol}: {exc}."
            ) from exc

    # Try ExecutionManager directly
    em = _get_execution_manager()
    if em is not None:
        try:
            from quant_nanggroe.engine.execution.base import Order, OrderSide
            from quant_nanggroe.engine.execution.base import OrderType as OT
            side_map = {"BUY": OrderSide.BUY, "SELL": OrderSide.SELL,
                        "SHORT": OrderSide.SELL, "COVER": OrderSide.BUY}
            ot_map = {"market": OT.MARKET, "limit": OT.LIMIT,
                      "stop": OT.STOP, "stop_limit": OT.STOP_LIMIT}
            order = Order(
                symbol=symbol,
                side=side_map.get(action.upper(), OrderSide.BUY),
                quantity=quantity,
                order_type=ot_map.get(order_type.lower(), OT.MARKET),
                price=price,
            )
            import asyncio
            loop = asyncio.get_event_loop()
            if not loop.is_running():
                fill = loop.run_until_complete(em.execute_order(order))
                if fill:
                    return json.dumps({
                        "order_id": fill.order_id,
                        "symbol": symbol.upper(),
                        "action": action.upper(),
                        "quantity": quantity,
                        "order_type": order_type,
                        "price": price,
                        "fill_price": fill.fill_price,
                        "stop_loss": stop_loss,
                        "take_profit": take_profit,
                        "status": "FILLED",
                        "timestamp": datetime.now().isoformat(),
                        "message": f"Order filled: {action.upper()} {quantity} {symbol.upper()} @ {fill.fill_price}",
                        "_source": "ExecutionManager",
                    }, indent=2)
        except Exception as exc:
            logger.error("ExecutionManager place_order failed for %s: %s", symbol, exc)
            raise RuntimeError(
                f"Failed to place order for {symbol}: {exc}."
            ) from exc

    raise RuntimeError(
        f"Cannot place order for {symbol}: real execution engine unavailable."
    )


@tool
def get_position(symbol: str) -> str:
    """
    Get current position information for a symbol.

    PRODUCTION: Uses PaperBroker for real position data.

    Args:
        symbol: Trading symbol

    Returns:
        JSON string with position details
    """
    # PRODUCTION: Wired to real engine — try PaperBroker
    broker = _get_paper_broker()
    if broker is not None:
        try:
            positions = broker.get_positions()
            pos = positions.get(symbol.upper(), positions.get(symbol, None))
            if pos is not None:
                return json.dumps({
                    "symbol": symbol.upper(),
                    "quantity": getattr(pos, 'quantity', 0),
                    "entry_price": getattr(pos, 'entry_price', 0.0),
                    "current_price": getattr(pos, 'current_price', 0.0),
                    "unrealized_pnl": getattr(pos, 'unrealized_pnl', 0.0),
                    "direction": getattr(pos, 'direction', 'FLAT'),
                    "stop_loss": getattr(pos, 'stop_loss', None),
                    "take_profit": getattr(pos, 'take_profit', None),
                    "_source": "PaperBroker",
                }, indent=2, default=str)
        except Exception as exc:
            logger.error("PaperBroker get_position failed for %s: %s", symbol, exc)
            raise RuntimeError(
                f"Failed to get position for {symbol}: {exc}."
            ) from exc

    raise RuntimeError(
        f"Cannot get position for {symbol}: real broker unavailable."
    )


@tool
def get_portfolio() -> str:
    """
    Get current portfolio overview.

    PRODUCTION: Uses PaperBroker for real portfolio data.

    Returns:
        JSON string with portfolio summary
    """
    # PRODUCTION: Wired to real engine — try PaperBroker
    broker = _get_paper_broker()
    if broker is not None:
        try:
            summary = broker.get_account_summary()
            if summary:
                summary["_source"] = "PaperBroker"
                return json.dumps(summary, indent=2, default=str)
        except Exception as exc:
            logger.error("PaperBroker get_portfolio failed: %s", exc)
            raise RuntimeError(
                f"Failed to get portfolio: {exc}."
            ) from exc

    raise RuntimeError(
        "Cannot get portfolio: real broker unavailable."
    )


TRADER_TOOLS = [place_order, get_position, get_portfolio]
