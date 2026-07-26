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

from quant_nanggroe.engine.kelly import FractionalKelly, KellyParameters, KellyMethod


logger = logging.getLogger(__name__)

# ── Single source of truth for wired ExecutionManager ──────────────────
def _get_execution_manager():
    """Lazy-load a fully-wired ExecutionManager (paper + live MT5 if enabled)."""
    try:
        from quant_nanggroe.engine.execution.builder import build_execution_manager
        return build_execution_manager()
    except Exception as exc:
        logger.warning("Failed to build ExecutionManager: %s", exc)
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
    PaperBroker (or live broker when configured). Fails closed if unavailable.

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
                result["_source"] = "ExecutionTool"
                return json.dumps(result, indent=2, default=str)
        except Exception as exc:
            logger.error("ExecutionTool submit_order failed for %s: %s", symbol, exc)
            raise RuntimeError(
                f"Failed to submit order for {symbol}: {exc}."
            ) from exc

    # Try ExecutionManager directly
    em = _get_execution_manager()
    if em is not None:
        try:
            from quant_nanggroe.engine.execution.base import Order, OrderSide
            from quant_nanggroe.engine.execution.base import OrderType as OT
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
                    return json.dumps({
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
                f"Failed to submit order for {symbol}: {exc}."
            ) from exc

    raise RuntimeError(
        f"Cannot submit order for {symbol}: real execution engine unavailable."
    )


@tool
def cancel_order(order_id: str, reason: str = "User request") -> str:
    """
    Cancel an existing order.

    PRODUCTION: Uses ExecutionManager/OrderManager for real cancellation.

    Args:
        order_id: Order ID to cancel
        reason: Cancellation reason

    Returns:
        JSON string with cancellation result
    """
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
                result["_source"] = "ExecutionTool"
                return json.dumps(result, indent=2, default=str)
        except Exception as exc:
            logger.error("ExecutionTool cancel_order failed for %s: %s", order_id, exc)
            raise RuntimeError(
                f"Failed to cancel order {order_id}: {exc}."
            ) from exc

    # Try ExecutionManager directly
    em = _get_execution_manager()
    if em is not None:
        try:
            success = em._order_manager.cancel_order(order_id)
            return json.dumps({
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
                f"Failed to cancel order {order_id}: {exc}."
            ) from exc

    raise RuntimeError(
        f"Cannot cancel order {order_id}: real execution engine unavailable."
    )


@tool
def get_fills(order_id: Optional[str] = None) -> str:
    """
    Get order fill information.

    PRODUCTION: Uses FillTracker for real fill data.

    Args:
        order_id: Optional specific order ID (returns all if not specified)

    Returns:
        JSON string with fill information
    """
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
                result["_source"] = "ExecutionTool"
                return json.dumps(result, indent=2, default=str)
        except Exception as exc:
            logger.error("ExecutionTool get_fills failed: %s", exc)
            raise RuntimeError(
                f"Failed to get fills: {exc}."
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
            return json.dumps({
                "order_id": order_id or "ALL",
                "fills": fill_data,
                "total_fills": len(fill_data),
                "timestamp": datetime.now().isoformat(),
                "_source": "ExecutionManager",
            }, indent=2, default=str)
        except Exception as exc:
            logger.error("ExecutionManager get_fills failed: %s", exc)
            raise RuntimeError(
                f"Failed to get fills: {exc}."
            ) from exc

    raise RuntimeError(
        "Cannot get fills: real execution engine unavailable."
    )


@tool
def kelly_lot_size(
    symbol: str,
    balance: float,
    confidence: float = 0.5,
    win_rate: Optional[float] = None,
    avg_win: Optional[float] = None,
    avg_loss: Optional[float] = None,
) -> str:
    """Compute optimal position size using FractionalKelly.

    Uses conservative quarter-Kelly defaults when trade-history
    parameters are not provided. The returned lot/quantity respects
    the FractionalKelly f_star capped at 2% of balance.

    Args:
        symbol: Trading symbol (e.g. EURUSD, BTCUSD)
        balance: Current account balance in USD
        confidence: Signal confidence 0-1 (default 0.5)
        win_rate: Optional win rate from trade history
        avg_win: Optional average win amount as fraction of balance
        avg_loss: Optional average loss amount as fraction of balance

    Returns:
        JSON string with lot_size and kelly_fraction
    """
    try:
        kelly = FractionalKelly(fraction=0.25)
        params = KellyParameters(
            win_rate=win_rate or 0.55,
            avg_win=avg_win or 0.012,
            avg_loss=avg_loss or 0.008,
            fraction=0.25,
            leverage_max=0.02,
        )
        result = kelly.compute(params)
        kelly_fraction = max(0.01, min(result.f_star, params.leverage_max))
    except Exception as exc:
        logger.warning("FractionalKelly computation failed: %s", exc)
        kelly_fraction = 0.01

    # Convert to lot size using standard FX conventions
    contract_size = 100000.0
    pip_size = 0.0001
    atr_val = 0.0010  # default ATR
    try:
        from quant_nanggroe.hedge_fund.hedge_fund import calc_atr
        raw_atr = calc_atr(symbol)
        if raw_atr:
            atr_val = raw_atr
    except Exception:
        pass
    sl_dist = max(atr_val * 2, 0.0010)
    sl_pips = sl_dist / pip_size if pip_size > 0 else sl_dist / 0.0001
    dollar_per_pip_per_lot = contract_size * pip_size

    risk_amount = balance * kelly_fraction
    raw_lot = (risk_amount / (sl_pips * dollar_per_pip_per_lot)) if (sl_pips * dollar_per_pip_per_lot) > 0 else 0.01
    conf = max(0.1, min(1.0, confidence))
    lot = round(raw_lot * conf, 2)
    lot = max(0.01, lot)
    notional_cap_lot = max(0.01, round((balance * kelly_fraction * 2) / (1.0 / contract_size) if contract_size > 0 else 0.02, 2))
    lot = min(lot, notional_cap_lot)
    lot = max(0.01, lot)

    return json.dumps({
        "symbol": symbol.upper(),
        "lot_size": lot,
        "kelly_fraction": round(kelly_fraction, 4),
        "f_star": round(kelly_fraction, 4),
        "risk_amount": round(risk_amount, 2),
        "_source": "FractionalKelly",
    }, indent=2, default=str)


EXECUTION_TOOLS = [submit_order, cancel_order, get_fills, kelly_lot_size]
