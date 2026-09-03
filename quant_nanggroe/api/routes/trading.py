"""Trading API routes."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

from quant_nanggroe.api.schemas import (
    OrderRequest,
    OrderResponse,
    PositionResponse,
    PositionsResponse,
    RiskCheckRequest,
    RiskCheckResponse,
    TradeHistoryItem,
    TradeHistoryResponse,
)
from quant_nanggroe.engine.execution.base import (
    AccountInfo,
    Broker,
)
from quant_nanggroe.engine.execution.base import (
    Order as ExecOrder,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class ExchangeBrokerAdapter(Broker):
    """Bridge the live ExchangeManager (paper/MT5/crypto) into ExecutionManager.

    ExecutionManager expects an ``execution.base.Broker``; the live brokers in
    ExchangeManager implement a different ``exchange.base.ExchangeInterface``. This
    adapter delegates every execution call to the ExchangeManager's failover path,
    so a POST /api/trading/order actually reaches a real broker after passing the
    kill-switch + constitutional risk-manager guards.
    """

    def __init__(self, exchange_manager) -> None:
        self._em = exchange_manager

    @property
    def name(self) -> str:
        return "exchange_manager"

    @property
    def is_connected(self) -> bool:
        return True  # ExchangeManager handles per-broker health internally

    async def connect(self) -> bool:
        return True

    async def disconnect(self) -> None:
        return None

    async def get_account(self) -> AccountInfo:
        try:
            portfolio = await self._em.get_aggregated_portfolio()
            return AccountInfo(
                balance=portfolio.cash,
                equity=portfolio.cash + portfolio.total_market_value,
                buying_power=portfolio.cash,
            )
        except Exception:
            return AccountInfo(balance=0.0, equity=0.0, buying_power=0.0)

    async def get_positions(self):
        portfolio = await self._em.get_aggregated_portfolio()
        return [
            type("_P", (), {"symbol": s, "quantity": p.quantity})()
            for s, p in portfolio.positions.items()
        ]

    async def get_price(self, symbol: str) -> float:
        return await self._em.get_price(symbol)

    async def get_order(self, order_id: str):
        return None

    async def submit_order(self, order: ExecOrder):
        from quant_nanggroe.types.orders import OrderSide as EmSide
        from quant_nanggroe.types.orders import OrderType as EmType
        # execution.base uses UPPERCASE enum values ("BUY"); exchange.types uses
        # lowercase ("buy"). Normalize to the exchange convention.
        side = EmSide(order.side.value.lower())
        otype = EmType(order.order_type.value.lower())
        placed = await self._em.place_order(
            symbol=order.symbol,
            side=side,
            order_type=otype,
            quantity=order.quantity,
            price=order.price,
            stop_price=order.stop_price,
        )
        status_val = placed.status.value if hasattr(placed.status, "value") else str(placed.status)
        order.status = type(order.status)(status_val.upper())
        order.metadata = getattr(placed, "metadata", {}) or {}
        return order

    async def cancel_order(self, order_id: str) -> bool:
        return False


def _get_execution_manager(http_request: Request):
    """Retrieve the singleton ExecutionManager from services, with ExchangeManager bridge.

    The ExecutionManager is ALWAYS wired with the constitutional RiskManager and
    KillSwitch so every order is enforced (no override path). A trade that breaches
    the daily/weekly loss budget or a halt is vetoed before it reaches the broker.

    The ExecutionManager is also bridged to the live ExchangeManager (paper / MT5 /
    crypto), so executes_order actually reaches a real broker instead of a phantom
    "paper" default. Without this bridge, execute_order routes to a broker that was
    never registered and silently returns None (no fill, no error).
    """
    from quant_nanggroe.services import get_execution_manager

    em = get_execution_manager(http_request.app)

    # Bridge: ensure the live ExchangeManager is registered as a broker.
    # The adapter is idempotent — adding it twice is a no-op if already present.
    if not hasattr(em, "_exchange_bridge_added"):
        em.add_broker(ExchangeBrokerAdapter(_get_exchange_manager(http_request)))
        em._exchange_bridge_added = True

    return em


def _get_exchange_manager(http_request: Request):
    """Retrieve the singleton ExchangeManager from services."""
    from quant_nanggroe.services import get_exchange_manager
    return get_exchange_manager(http_request.app)


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
    from quant_nanggroe.security.auth import UserRole
    if hasattr(http_request.state, 'user_role') and http_request.state.user_role not in (UserRole.ADMIN, UserRole.TRADER):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=403,
            content={"error": "Trader+ role required to place orders", "status": "forbidden"},
        )

    from quant_nanggroe.engine.execution.base import Order, OrderSide, OrderStatus, OrderType

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
            strategy=request.strategy,
            regime=request.regime,
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


@router.get("/orders", response_model=TradeHistoryResponse)
async def get_orders(limit: int = 50, http_request: Request = None) -> TradeHistoryResponse:
    """Get all orders (alias for /trades for frontend compat)."""
    return await get_trade_history(limit=limit, http_request=http_request)


@router.delete("/order/{order_id}")
async def cancel_order(order_id: str, http_request: Request) -> dict:
    """Cancel an open order by ID."""
    try:
        em = _get_execution_manager(http_request)
        success = await em.cancel_order(order_id.replace("order-", ""))
        return {"success": success, "order_id": order_id}
    except Exception as exc:
        logger.warning("cancel_order_failed id=%s error=%s", order_id, exc)
        return {"success": False, "order_id": order_id, "error": str(exc)}


@router.get("/exchanges")
async def get_exchanges(http_request: Request) -> dict:
    """Get connected exchanges and their status."""
    try:
        em = _get_exchange_manager(http_request)
        registrations = em._registrations if hasattr(em, "_registrations") else {}
        exchanges = [
            {"id": name, "name": name, "type": "Equity", "status": "connected" if reg.connected else "disconnected"}
            for name, reg in registrations.items()
        ]
        return {"exchanges": exchanges, "count": len(exchanges)}
    except Exception as exc:
        logger.warning("get_exchanges_failed error=%s", exc)
        return {"exchanges": [], "count": 0}


@router.post("/slice-order")
async def slice_order(request: dict, http_request: Request) -> dict:
    """Slice a large order into smaller chunks for TWAP/VWAP execution."""
    try:
        symbol = request.get("symbol", "")
        side = request.get("side", "buy")
        quantity = request.get("quantity", 0.0)
        num_slices = request.get("num_slices", 5)
        duration_minutes = request.get("duration_minutes", 60)

        if not symbol or quantity <= 0:
            return {"success": False, "error": "Invalid order parameters", "slices": []}

        slice_qty = quantity / num_slices
        interval_seconds = (duration_minutes * 60) / num_slices

        slices = []
        for i in range(num_slices):
            slices.append({
                "slice": i + 1,
                "quantity": round(slice_qty, 6),
                "delay_seconds": int(interval_seconds * i),
                "status": "pending",
            })

        return {"success": True, "slices": slices, "num_slices": num_slices, "symbol": symbol, "side": side}
    except Exception as exc:
        logger.warning("slice_order_failed error=%s", exc)
        return {"success": False, "error": str(exc), "slices": []}


# ── Hedge-fund cycle (wires strategy -> risk -> execution -> portfolio) ──
from typing import Any, Dict, Optional

from pydantic import BaseModel

from quant_nanggroe.engine.trading_loop import run_cycle as _run_cycle


class CycleRequest(BaseModel):
    symbol: str = "AAPL"
    strategy: str = "trend_follow"
    quantity: float = 10.0


class CycleResponse(BaseModel):
    symbol: str
    signal: str
    confidence: float
    order: Optional[Dict[str, Any]] = None
    portfolio: Dict[str, Any] = {}
    error: Optional[str] = None


@router.post("/cycle", response_model=CycleResponse)
async def trading_cycle(request: CycleRequest, http_request: Request) -> CycleResponse:
    """Run one full hedge-fund cycle: data -> strategy -> execute -> portfolio.

    Uses the live ExchangeManager (MT5 if configured, else paper broker) so the
    same endpoint drives real or simulated trading.
    """
    # FIX S5: Require TRADER+ role for cycle execution
    from quant_nanggroe.security.auth import UserRole
    if hasattr(http_request.state, "user_role") and http_request.state.user_role not in (UserRole.ADMIN, UserRole.TRADER):
        raise HTTPException(status_code=403, detail="Trader+ role required to run trading cycle")
    em = http_request.app.state.exchange_manager
    if em is None:
        return CycleResponse(
            symbol=request.symbol, signal="hold", confidence=0.0,
            error="exchange_manager not available",
        )
    # ponytail: backbone is registered at boot but NOT connected (MT5 needs a
    # live terminal; connecting in-thread corrupts the proactor loop). Without
    # this lazy connect, /cycle is a permanent no-op returning "No healthy
    # exchanges". Connect on first cycle so the pipeline actually executes.
    if not any(reg.connected for reg in em._registrations.values()):
        try:
            await em.connect_all()
        except Exception as exc:
            logger.warning("cycle_lazy_connect_failed: %s", exc)
    res = await _run_cycle(
        em, symbol=request.symbol, strategy_name=request.strategy,
        quantity=request.quantity,
    )
    return CycleResponse(
        symbol=res.symbol, signal=res.signal, confidence=res.confidence,
        order=res.order, portfolio=res.portfolio, error=res.error,
    )


# ── Purified Engine Routes (fail-closed, MT5-guarded) ──────────────
_purified_engine = None


def _get_purified():
    global _purified_engine
    if _purified_engine is None:
        from quant_nanggroe.engine_production_bridge_purified import PurifiedEngine
        _purified_engine = PurifiedEngine()
    return _purified_engine


@router.post("/purified/start")
async def purified_start() -> dict:
    eng = _get_purified()
    try:
        eng.start()
        return {"status": "started", "balance": eng.risk.balance}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/purified/status")
async def purified_status() -> dict:
    eng = _get_purified()
    return eng.status()


@router.post("/purified/cycle")
async def purified_cycle(request: dict) -> dict:
    from quant_nanggroe.engine_production_bridge_purified import Signal
    eng = _get_purified()
    signals = []
    for s in request.get("signals", []):
        signals.append(Signal(
            symbol=s.get("symbol", "EURUSD"),
            side=s.get("side", "buy"),
            confidence=s.get("confidence", 0.5),
            strategy=s.get("strategy", "manual"),
            price=s.get("price", 0.0),
            stop_loss=s.get("sl", 0.0),
            take_profit=s.get("tp", 0.0),
        ))
    results = eng.cycle(signals)
    return {"status": "ok", "executed": len(results), "results": results}


@router.post("/purified/trade")
async def purified_trade(request: dict) -> dict:
    from quant_nanggroe.engine_production_bridge_purified import Signal
    eng = _get_purified()
    sig = Signal(
        symbol=request.get("symbol", "EURUSD"),
        side=request.get("side", "buy"),
        confidence=1.0,
        strategy=request.get("strategy", "manual"),
        price=request.get("price", 0.0),
        stop_loss=request.get("sl", 0.0),
        take_profit=request.get("tp", 0.0),
    )
    try:
        results = eng.cycle([sig])
        return {"status": "ok", "results": results}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/purified/positions")
async def purified_positions() -> dict:
    try:
        import MetaTrader5 as mt5
        positions = mt5.positions_get() or []
        return {"positions": [{"symbol": p.symbol, "type": "BUY" if p.type == 0 else "SELL", "volume": p.volume, "price": p.price_open, "pnl": p.profit, "ticket": p.ticket} for p in positions]}
    except Exception as e:
        return {"positions": [], "error": str(e)}


@router.post("/purified/close/{ticket}")
async def purified_close(ticket: int) -> dict:
    eng = _get_purified()
    try:
        result = eng.close_position(ticket)
        return {"status": "closed", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/purified/trades")
async def purified_trades() -> dict:
    try:
        from datetime import datetime, timedelta

        import MetaTrader5 as mt5
        deals = mt5.history_deals_get(datetime.now() - timedelta(days=30), datetime.now()) or []
        return {"trades": [{"ticket": d.ticket, "symbol": d.symbol, "type": "BUY" if d.type == 0 else "SELL", "volume": d.volume, "price": d.price, "pnl": d.profit, "time": str(d.time)} for d in deals[-50:]]}
    except Exception as e:
        return {"trades": [], "error": str(e)}


@router.get("/accounts")
async def list_accounts() -> dict:
    """Return every MT5 account QNA can see (auto-detected terminals + config).

    GATE-6: dashboard monitors ALL accounts, not just the traded one.
    Fail-closed: empty list if MT5 is unavailable — never a fabricated account.
    """
    from quant_nanggroe.engine.execution.account_discovery import discover_accounts
    try:
        accounts = discover_accounts()
    except Exception as e:
        raise HTTPException(500, f"account discovery failed: {e}")
    return {"accounts": [a.to_dict() for a in accounts], "count": len(accounts)}


@router.get("/accounts/ledger")
async def get_account_ledger():
    """All MT5 accounts that have EVER connected (persistent ledger)."""
    from quant_nanggroe.engine.execution.account_ledger import get_all_accounts
    accounts = get_all_accounts()
    return {"accounts": accounts, "count": len(accounts)}
