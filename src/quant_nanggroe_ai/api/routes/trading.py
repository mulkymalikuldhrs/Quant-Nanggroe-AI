"""
Trading Routes — Order placement, positions, risk checks
=========================================================
Uses shared ConstitutionalRiskGuard singleton from app.state
so that daily/weekly PnL limits persist correctly across requests.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request

from quant_nanggroe_ai.api.schemas import (
    OrderRequest,
    OrderResponse,
    PositionsResponse,
    PositionResponse,
    TradeHistoryResponse,
    TradeHistoryItem,
    RiskCheckRequest,
    RiskCheckResponse,
    RiskCheckpointResult as RiskCheckpointSchema,
)
from quant_nanggroe_ai.services import get_kill_switch, get_risk_guard

logger = structlog.get_logger(__name__)

router = APIRouter()

# In-memory stores (production would use database)
_positions: dict[str, dict[str, Any]] = {}
_trade_history: list[dict[str, Any]] = []
_order_counter: int = 0


# ══════════════════════════════════════════════════════════════════════
# Order Placement
# ══════════════════════════════════════════════════════════════════════

@router.post("/order", response_model=OrderResponse)
async def place_order(request: Request, body: OrderRequest) -> OrderResponse:
    """
    Place a trade order.

    Validates the order through the constitutional risk guard before
    submission. If the kill switch is active, the order is rejected.
    """
    global _order_counter

    ks = get_kill_switch(request.app)

    # Check kill switch
    if ks.is_active:
        logger.warning("order_rejected", reason="kill_switch_active", symbol=body.symbol)
        raise HTTPException(status_code=403, detail="Kill switch active — trading halted")

    # Run risk check through shared guard
    guard = get_risk_guard(request.app)

    # Get current account balance from positions
    account_balance = 10000.0  # Default; production would query from DB

    risk_result = guard.check_trade(
        symbol=body.symbol,
        direction=body.direction,
        lot_size=body.quantity,
        entry=body.price or 0.0,
        stop_loss=body.stop_loss,
        account_balance=account_balance,
        take_profit=body.take_profit,
    )

    if risk_result.verdict == "VETOED":
        failed_checks = [
            name for name, cp in risk_result.checkpoints.items() if not cp.passed
        ]
        logger.warning(
            "order_vetoed",
            symbol=body.symbol,
            direction=body.direction,
            failed_checks=failed_checks,
        )
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Order vetoed by risk guard",
                "failed_checks": failed_checks,
                "risk_pct": risk_result.risk_pct,
                "verdict": risk_result.verdict,
            },
        )

    # Execute order (paper trading in dev mode)
    _order_counter += 1
    order_id = f"ORD-{_order_counter:06d}"

    # Determine fill price (paper: use requested price or zero)
    filled_price = body.price

    # Update position tracking
    symbol = body.symbol.upper()
    if symbol not in _positions:
        _positions[symbol] = {
            "ticker": symbol,
            "amount": 0.0,
            "avg_price": 0.0,
            "current_price": filled_price or 0.0,
            "pnl": 0.0,
        }

    pos = _positions[symbol]
    if body.direction.upper() in ("BUY", "LONG"):
        total_cost = pos["avg_price"] * pos["amount"] + (filled_price or 0.0) * body.quantity
        pos["amount"] += body.quantity
        pos["avg_price"] = total_cost / pos["amount"] if pos["amount"] > 0 else 0.0
    elif body.direction.upper() in ("SELL", "SHORT"):
        pos["amount"] -= body.quantity
        if pos["amount"] <= 0:
            del _positions[symbol]

    # Record in trade history
    trade_record = {
        "id": order_id,
        "timestamp": datetime.now().isoformat(),
        "ticker": body.symbol,
        "action": body.direction.upper(),
        "amount": body.quantity,
        "price": filled_price or 0.0,
        "total_value": (filled_price or 0.0) * body.quantity,
        "fees": 0.0,
        "realized_pnl": None,
        "triggered_by_signals": ["api_order"],
    }
    _trade_history.append(trade_record)

    # Update risk guard PnL tracking
    guard.update_pnl(trade_pnl=0.0)  # No immediate PnL on entry

    logger.info(
        "order_placed",
        order_id=order_id,
        symbol=body.symbol,
        direction=body.direction,
        quantity=body.quantity,
        risk_verdict=risk_result.verdict,
    )

    return OrderResponse(
        order_id=order_id,
        status="FILLED",
        symbol=body.symbol,
        direction=body.direction,
        quantity=body.quantity,
        filled_price=filled_price,
    )


# ══════════════════════════════════════════════════════════════════════
# Positions
# ══════════════════════════════════════════════════════════════════════

@router.get("/positions", response_model=PositionsResponse)
async def get_positions() -> PositionsResponse:
    """
    Get all open positions.

    Returns current position details including unrealized PnL.
    """
    positions = [
        PositionResponse(
            ticker=p["ticker"],
            amount=p["amount"],
            avg_price=p["avg_price"],
            current_price=p["current_price"],
            pnl=p["pnl"],
            last_updated=datetime.now(),
        )
        for p in _positions.values()
    ]

    return PositionsResponse(
        positions=positions,
        total_count=len(positions),
    )


# ══════════════════════════════════════════════════════════════════════
# Trade History
# ══════════════════════════════════════════════════════════════════════

@router.get("/history", response_model=TradeHistoryResponse)
async def get_trade_history(limit: int = 50) -> TradeHistoryResponse:
    """
    Get trade history.

    Args:
        limit: Maximum number of trades to return (default 50).

    Returns:
        Recent trade history with total count.
    """
    trades = sorted(_trade_history, key=lambda t: t["timestamp"], reverse=True)[:limit]

    trade_items = [
        TradeHistoryItem(
            id=t["id"],
            timestamp=datetime.fromisoformat(t["timestamp"]),
            ticker=t["ticker"],
            action=t["action"],
            amount=t["amount"],
            price=t["price"],
            total_value=t["total_value"],
            fees=t["fees"],
            realized_pnl=t.get("realized_pnl"),
        )
        for t in trades
    ]

    return TradeHistoryResponse(
        trades=trade_items,
        total_count=len(_trade_history),
        limit=limit,
    )


# ══════════════════════════════════════════════════════════════════════
# Risk Check
# ══════════════════════════════════════════════════════════════════════

@router.post("/risk-check", response_model=RiskCheckResponse)
async def risk_check(request: Request, body: RiskCheckRequest) -> RiskCheckResponse:
    """
    Run a 9-checkpoint constitutional risk check for a proposed trade.

    Uses the shared ConstitutionalRiskGuard instance so that daily/weekly
    PnL limits and trade counts are correctly tracked across requests.
    """
    guard = get_risk_guard(request.app)

    result = guard.check_trade(
        symbol=body.symbol,
        direction=body.direction,
        lot_size=body.lot_size,
        entry=body.entry,
        stop_loss=body.stop_loss,
        account_balance=body.account_balance,
        take_profit=body.take_profit,
    )

    logger.info(
        "risk_check",
        symbol=body.symbol,
        direction=body.direction,
        verdict=result.verdict,
        risk_pct=result.risk_pct,
    )

    checkpoints = {
        name: RiskCheckpointSchema(
            name=cp.name,
            value=cp.value,
            limit=cp.limit,
            passed=cp.passed,
        )
        for name, cp in result.checkpoints.items()
    }

    return RiskCheckResponse(
        symbol=result.symbol,
        direction=result.direction,
        lot_size=result.lot_size,
        entry=result.entry,
        stop_loss=result.stop_loss,
        take_profit=result.take_profit,
        risk_pct=result.risk_pct,
        rr_ratio=result.rr_ratio,
        verdict=result.verdict,
        checkpoints=checkpoints,
        veto_count_total=result.veto_count_total,
        approval_count_total=result.approval_count_total,
    )


# ══════════════════════════════════════════════════════════════════════
# Risk Status
# ══════════════════════════════════════════════════════════════════════

@router.get("/risk/status")
async def get_risk_status(request: Request):
    """
    Get current risk guard status.

    Returns daily/weekly PnL, trade counts, and limit status from
    the shared ConstitutionalRiskGuard instance.
    """
    guard = get_risk_guard(request.app)
    return guard.status()


# ══════════════════════════════════════════════════════════════════════
# Position Sizing
# ══════════════════════════════════════════════════════════════════════

@router.post("/position-size")
async def calculate_position_size(
    account_balance: float = 10000.0,
    risk_pct: float = 0.005,
    stop_loss_pips: float = 50.0,
    pip_value: float = 10.0,
    request: Request = None,
):
    """
    Calculate proper position size based on risk parameters.

    Uses the ConstitutionalRiskGuard's lot size calculator, which
    caps risk at the hardcoded maximum regardless of input.
    """
    guard = get_risk_guard(request.app)
    return guard.calculate_lot_size(
        account_balance=account_balance,
        risk_pct=risk_pct,
        stop_loss_pips=stop_loss_pips,
        pip_value=pip_value,
    )
