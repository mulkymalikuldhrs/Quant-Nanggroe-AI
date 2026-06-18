"""Trading API routes."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request

from quant_nanggroe.api.schemas import (
    OrderRequest,
    OrderResponse,
    PositionsResponse,
    PositionResponse,
    TradeHistoryItem,
    TradeHistoryResponse,
    RiskCheckRequest,
    RiskCheckResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_execution_manager(http_request: Request):
    """Retrieve or lazily create the ExecutionManager from app state."""
    from quant_nanggroe.engine.execution.manager import ExecutionManager

    if not hasattr(http_request.app.state, "_services"):
        http_request.app.state._services = {}

    if "execution_manager" not in http_request.app.state._services:
        http_request.app.state._services["execution_manager"] = ExecutionManager()
    return http_request.app.state._services["execution_manager"]


def _get_exchange_manager(http_request: Request):
    """Retrieve or lazily create the ExchangeManager from app state."""
    from quant_nanggroe.exchange.manager import ExchangeManager

    if not hasattr(http_request.app.state, "_services"):
        http_request.app.state._services = {}

    if "exchange_manager" not in http_request.app.state._services:
        http_request.app.state._services["exchange_manager"] = ExchangeManager()
    return http_request.app.state._services["exchange_manager"]


@router.post("/order", response_model=OrderResponse)
async def place_order(request: OrderRequest, http_request: Request) -> OrderResponse:
    """Place a trade order.

    Submits an order through the ExecutionManager guard pipeline for
    validation and execution. The guard pipeline enforces cooldown,
    max-position, and whitelist checks before routing to a broker.

    Args:
        request: OrderRequest with order details.
        http_request: HTTP request for accessing app state.

    Returns:
        OrderResponse with order status.
    """
    from quant_nanggroe.engine.execution.base import Order, OrderSide, OrderType, OrderStatus

    # Map direction string to OrderSide enum
    try:
        side = OrderSide(request.direction.upper())
    except ValueError:
        return OrderResponse(
            order_id="",
            status="REJECTED",
            symbol=request.symbol,
            direction=request.direction,
            quantity=request.quantity,
        )

    # Map order type string
    try:
        order_type = OrderType(request.order_type.upper())
    except ValueError:
        order_type = OrderType.MARKET

    # Build the Order object for the execution manager
    order = Order(
        id=str(uuid.uuid4()),
        symbol=request.symbol,
        side=side,
        order_type=order_type,
        quantity=request.quantity,
        price=request.price,
        stop_price=request.stop_loss,
        status=OrderStatus.PENDING,
    )

    em = _get_execution_manager(http_request)

    try:
        fill = await em.execute_order(order)

        if fill is not None:
            return OrderResponse(
                order_id=order.id,
                status="FILLED",
                symbol=request.symbol,
                direction=request.direction,
                quantity=request.quantity,
                filled_price=fill.price,
                timestamp=datetime.now(),
            )
        else:
            # Order was blocked by a guard
            return OrderResponse(
                order_id=order.id,
                status="REJECTED",
                symbol=request.symbol,
                direction=request.direction,
                quantity=request.quantity,
            )
    except Exception as exc:
        logger.error("place_order_failed symbol=%s error=%s", request.symbol, exc)
        return OrderResponse(
            order_id=order.id,
            status="ERROR",
            symbol=request.symbol,
            direction=request.direction,
            quantity=request.quantity,
        )


@router.get("/positions", response_model=PositionsResponse)
async def get_positions(http_request: Request) -> PositionsResponse:
    """Get all open positions.

    Queries real positions from the broker through the ExchangeManager's
    aggregated portfolio endpoint.

    Args:
        http_request: HTTP request for accessing app state.

    Returns:
        PositionsResponse with current portfolio positions.
    """
    try:
        em = _get_exchange_manager(http_request)
        portfolio = await em.get_aggregated_portfolio()

        positions = []
        for symbol, pos in portfolio.positions.items():
            positions.append(
                PositionResponse(
                    ticker=symbol,
                    amount=pos.quantity,
                    avg_price=pos.entry_price,
                    current_price=pos.current_price,
                    pnl=pos.market_value - pos.cost_basis if pos.cost_basis > 0 else 0.0,
                )
            )

        return PositionsResponse(
            positions=positions,
            total_count=len(positions),
        )
    except Exception as exc:
        logger.warning("get_positions_failed error=%s", exc)
        return PositionsResponse(positions=[], total_count=0)


@router.get("/trades", response_model=TradeHistoryResponse)
async def get_trade_history(limit: int = 50, http_request: Request = None) -> TradeHistoryResponse:
    """Get trade history.

    Retrieves the execution audit log from the ExecutionManager, which
    records every order submission, guard block, and execution failure.

    Args:
        limit: Maximum number of trades to return.
        http_request: HTTP request for accessing app state.

    Returns:
        TradeHistoryResponse with recent trade records.
    """
    try:
        em = _get_execution_manager(http_request)
        audit_log = em.get_audit_log()

        # Convert audit log entries to TradeHistoryItem objects
        trades = []
        for entry in audit_log[-limit:]:
            action = entry.get("action", "UNKNOWN")
            trades.append(
                TradeHistoryItem(
                    id=entry.get("order_id", str(uuid.uuid4())[:8]),
                    timestamp=datetime.now(),
                    ticker=entry.get("symbol", ""),
                    action=action,
                    amount=entry.get("quantity", 0.0),
                    price=0.0,
                    total_value=0.0,
                    fees=0.0,
                )
            )

        # Also include filled trades from the fill tracker
        fill_tracker = em.fill_tracker
        for fill_id, fill in list(fill_tracker._fills.items())[-limit:]:
            trades.append(
                TradeHistoryItem(
                    id=fill.id,
                    timestamp=datetime.fromisoformat(fill.timestamp) if isinstance(fill.timestamp, str) else fill.timestamp,
                    ticker=fill.symbol,
                    action=fill.side.value,
                    amount=fill.quantity,
                    price=fill.price,
                    total_value=fill.quantity * fill.price,
                    fees=fill.commission,
                )
            )

        # Sort by most recent and apply limit
        trades = sorted(trades, key=lambda t: t.timestamp, reverse=True)[:limit]

        return TradeHistoryResponse(
            trades=trades,
            total_count=len(trades),
            limit=limit,
        )
    except Exception as exc:
        logger.warning("get_trade_history_failed error=%s", exc)
        return TradeHistoryResponse(trades=[], total_count=0, limit=limit)


@router.post("/risk-check", response_model=RiskCheckResponse)
async def risk_check(request: RiskCheckRequest, http_request: Request) -> RiskCheckResponse:
    """Run 9-checkpoint risk validation on a proposed trade.

    Evaluates the trade through the constitutional risk management system.

    Args:
        request: RiskCheckRequest with trade details.
        http_request: HTTP request for accessing app state.

    Returns:
        RiskCheckResponse with verdict and checkpoint details.
    """
    from quant_nanggroe.services import get_risk_manager

    try:
        rm = get_risk_manager(http_request.app)
        stop_loss = request.stop_loss or (request.entry * 0.99)
        result = rm.check_trade(
            symbol=request.symbol,
            direction=request.direction,
            lot_size=request.lot_size,
            entry=request.entry,
            stop_loss=stop_loss,
            account_balance=request.account_balance,
            take_profit=request.take_profit,
        )
        return RiskCheckResponse(
            symbol=result.get("symbol", request.symbol),
            direction=result.get("direction", request.direction),
            lot_size=request.lot_size,
            entry=request.entry,
            stop_loss=request.stop_loss,
            take_profit=request.take_profit,
            risk_pct=result.get("risk_pct", 0.0),
            rr_ratio=result.get("rr_ratio", 0.0),
            verdict=result.get("verdict", "UNKNOWN"),
            checkpoints=result.get("checkpoints", {}),
            veto_count_total=result.get("veto_count_total", 0),
            approval_count_total=result.get("approval_count_total", 0),
        )
    except Exception as exc:
        logger.error("risk_check_failed", extra={"error": str(exc)})
        return RiskCheckResponse(
            symbol=request.symbol,
            direction=request.direction,
            lot_size=request.lot_size,
            entry=request.entry,
            stop_loss=request.stop_loss,
            take_profit=request.take_profit,
            risk_pct=0.0,
            verdict="ERROR",
            checkpoints={},
        )
