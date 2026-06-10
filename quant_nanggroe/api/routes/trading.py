"""Trading API routes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request

from quant_nanggroe.api.schemas import (
    OrderRequest,
    OrderResponse,
    PositionsResponse,
    TradeHistoryResponse,
    RiskCheckRequest,
    RiskCheckResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/order", response_model=OrderResponse)
async def place_order(request: OrderRequest, http_request: Request) -> OrderResponse:
    """Place a trade order.

    Submits an order through the risk management system for validation
    before execution.

    Args:
        request: OrderRequest with order details.
        http_request: HTTP request for accessing app state.

    Returns:
        OrderResponse with order status.
    """
    # Placeholder — would integrate with execution engine
    return OrderResponse(
        order_id="pending",
        status="PENDING",
        symbol=request.symbol,
        direction=request.direction,
        quantity=request.quantity,
    )


@router.get("/positions", response_model=PositionsResponse)
async def get_positions() -> PositionsResponse:
    """Get all open positions.

    Returns:
        PositionsResponse with current portfolio positions.
    """
    return PositionsResponse(positions=[], total_count=0)


@router.get("/trades", response_model=TradeHistoryResponse)
async def get_trade_history(limit: int = 50) -> TradeHistoryResponse:
    """Get trade history.

    Args:
        limit: Maximum number of trades to return.

    Returns:
        TradeHistoryResponse with recent trade records.
    """
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
