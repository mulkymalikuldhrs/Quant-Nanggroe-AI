"""
Trader Agent Tools for Quant Nanggroe AI Trading Framework.

PRODUCTION: Wired to real execution components:
- place_order: Uses ExecutionTool/ExecutionManager for real order routing
- get_position: Uses PaperBroker for real position data
- get_portfolio: Uses PaperBroker for real portfolio overview
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
    """Lazy-load PaperExchangeBroker for position/portfolio queries."""
    try:
        from quant_nanggroe.exchange.paper_broker import PaperExchangeBroker
        return PaperExchangeBroker()
    except Exception as exc:
        logger.warning("Failed to load PaperExchangeBroker: %s", exc)
        return None


# ── Mock data fallbacks ─────────────────────────────────────────────────

def _mock_place_order(symbol, action, quantity, order_type, price, stop_loss, take_profit) -> dict:
    logger.warning("MOCK MODE: Returning hardcoded order confirmation for %s %s", action, symbol)
    return {
        "order_id": f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "symbol": symbol.upper(),
        "action": action.upper(),
        "quantity": quantity,
        "order_type": order_type,
        "price": price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "status": "SUBMITTED",
        "timestamp": datetime.now().isoformat(),
        "message": f"Order submitted: {action.upper()} {quantity} {symbol.upper()}",
        "_mock": True,
    }


def _mock_get_position(symbol) -> dict:
    logger.warning("MOCK MODE: Returning hardcoded position data for %s", symbol)
    return {
        "symbol": symbol.upper(),
        "quantity": 0,
        "entry_price": 0.0,
        "current_price": 0.0,
        "unrealized_pnl": 0.0,
        "direction": "FLAT",
        "stop_loss": None,
        "take_profit": None,
        "_mock": True,
    }


def _mock_get_portfolio() -> dict:
    logger.warning("MOCK MODE: Returning hardcoded portfolio data")
    return {
        "total_value": 100000.0,
        "cash": 100000.0,
        "positions": {},
        "unrealized_pnl": 0.0,
        "realized_pnl": 0.0,
        "daily_pnl": 0.0,
        "number_of_positions": 0,
        "risk_budget_used": 0.0,
        "timestamp": datetime.now().isoformat(),
        "_mock": True,
    }


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
    PaperBroker (or live broker when configured).
    Falls back to mock data only in _MOCK_MODE.

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
    if not _MOCK_MODE:
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
                    result["_source"] = "ExecutionTool"  # PRODUCTION: Wired to real engine
                    return json.dumps(result, indent=2, default=str)
            except Exception as exc:
                logger.error("ExecutionTool place_order failed for %s: %s", symbol, exc)
                raise RuntimeError(
                    f"Failed to place order for {symbol}: {exc}. "
                    "Set _MOCK_MODE=True for mock fallback."
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
                        return json.dumps({  # PRODUCTION: Wired to real engine
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
                    f"Failed to place order for {symbol}: {exc}. "
                    "Set _MOCK_MODE=True for mock fallback."
                ) from exc

    # Mock fallback
    if _MOCK_MODE:
        return json.dumps(_mock_place_order(symbol, action, quantity, order_type, price, stop_loss, take_profit), indent=2)

    raise RuntimeError(
        f"Cannot place order for {symbol}: real execution engine unavailable and _MOCK_MODE=False. "
        "Install required dependencies or set _MOCK_MODE=True."
    )


@tool
def get_position(symbol: str) -> str:
    """
    Get current position information for a symbol.

    PRODUCTION: Uses PaperBroker for real position data.
    Falls back to mock data only in _MOCK_MODE.

    Args:
        symbol: Trading symbol

    Returns:
        JSON string with position details
    """
    if not _MOCK_MODE:
        # PRODUCTION: Wired to real engine — try PaperBroker
        broker = _get_paper_broker()
        if broker is not None:
            try:
                positions = broker.get_positions()
                pos = positions.get(symbol.upper(), positions.get(symbol, None))
                if pos is not None:
                    return json.dumps({  # PRODUCTION: Wired to real engine
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
                    f"Failed to get position for {symbol}: {exc}. "
                    "Set _MOCK_MODE=True for mock fallback."
                ) from exc

    # Mock fallback
    if _MOCK_MODE:
        return json.dumps(_mock_get_position(symbol), indent=2)

    raise RuntimeError(
        f"Cannot get position for {symbol}: real broker unavailable and _MOCK_MODE=False."
    )


@tool
def get_portfolio() -> str:
    """
    Get current portfolio overview.

    PRODUCTION: Uses PaperBroker for real portfolio data.
    Falls back to mock data only in _MOCK_MODE.

    Returns:
        JSON string with portfolio summary
    """
    if not _MOCK_MODE:
        # PRODUCTION: Wired to real engine — try PaperBroker
        broker = _get_paper_broker()
        if broker is not None:
            try:
                summary = broker.get_account_summary()
                if summary:
                    summary["_source"] = "PaperBroker"  # PRODUCTION: Wired to real engine
                    return json.dumps(summary, indent=2, default=str)
            except Exception as exc:
                logger.error("PaperBroker get_portfolio failed: %s", exc)
                raise RuntimeError(
                    f"Failed to get portfolio: {exc}. "
                    "Set _MOCK_MODE=True for mock fallback."
                ) from exc

    # Mock fallback
    if _MOCK_MODE:
        return json.dumps(_mock_get_portfolio(), indent=2)

    raise RuntimeError(
        "Cannot get portfolio: real broker unavailable and _MOCK_MODE=False."
    )


TRADER_TOOLS = [place_order, get_position, get_portfolio]
