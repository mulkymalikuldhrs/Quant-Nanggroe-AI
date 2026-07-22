"""Async adapter: MT5Broker (BrokerConnector, sync) -> engine.execution.base.Broker (async).

ponytail: two ABCs existed (engine base.Broker vs connectors broker_base.BrokerConnector);
MT5Broker implemented the wrong one, so it never reached ExecutionManager. This thin
adapter bridges them. No new broker logic — only sync->async + type mapping.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from quant_nanggroe.connectors.broker_base import Order as ConnOrder
from quant_nanggroe.engine.execution.base import (
    AccountInfo,
    Broker,
    Fill,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    PositionInfo,
)
from quant_nanggroe.connectors.mt5_broker import MT5Broker

logger = logging.getLogger(__name__)

_SIDE_MAP = {"BUY": "buy", "SELL": "sell"}
_REV_SIDE = {"buy": OrderSide.BUY, "sell": OrderSide.SELL}


class MT5ExecutionBroker(Broker):
    """Wraps a connected MT5Broker into the async execution-engine Broker ABC."""

    def __init__(self, mt5: MT5Broker) -> None:
        self._mt5 = mt5

    @property
    def name(self) -> str:
        return "mt5"

    @property
    def is_connected(self) -> bool:
        return self._mt5.connected

    async def connect(self) -> bool:
        # P0 fix: MT5Broker.connect() already called mt5.initialize() in the
        # builder's live-wiring loop. Calling it again here double-inits the
        # same MT5 terminal in one process -> IPC timeout. Skip if already up.
        if self._mt5.connected:
            return True
        return self._mt5.connect()

    async def disconnect(self) -> None:
        self._mt5.disconnect()

    async def get_account(self) -> AccountInfo:
        # P0 fix: read REAL equity/balance from MT5, not assume equity==balance.
        # Phantom equity fed the risk veto with wrong numbers.
        try:
            import MetaTrader5 as mt5
            acc = mt5.account_info()
            if acc:
                return AccountInfo(
                    balance=float(acc.balance),
                    equity=float(acc.equity),
                    margin_available=float(acc.margin_free),
                    buying_power=float(acc.margin_free),
                )
        except Exception as e:
            logger.warning("MT5 get_account failed: %s", e)
        bal = self._mt5.get_balance()
        return AccountInfo(balance=bal, equity=bal, margin_available=bal, buying_power=bal)

    async def submit_order(self, order: Order) -> Order:
        try:
            conn_order = ConnOrder(
                symbol=order.symbol,
                side=_SIDE_MAP.get(order.side.value, "buy"),
                quantity=order.quantity,
                order_type=order.order_type.value.lower(),
                price=order.price,
                # P0 fix: carry protective SL/TP into the connector order so the
                # broker receives sl/tp on open (previously dropped -> naked positions).
                stop_loss=order.stop_loss,
                take_profit=order.take_profit,
            )
            result = self._mt5.place_order(conn_order)
            if result:
                order.status = OrderStatus.FILLED
                price = await self.get_price(order.symbol)
                order.metadata["fill_price"] = price
                order.metadata["broker_order_id"] = result
            else:
                order.status = OrderStatus.REJECTED
                order.metadata["reason"] = "MT5 order rejected"
        except Exception as e:
            order.status = OrderStatus.REJECTED
            order.metadata["reason"] = str(e)
        return order

    async def cancel_order(self, order_id: str) -> bool:
        # ponytail: MT5Broker has no cancel API surface; market orders fill instantly.
        logger.warning("MT5 cancel not supported for order %s", order_id)
        return False

    async def get_order(self, order_id: str) -> Optional[Order]:
        try:
            import MetaTrader5 as mt5
            orders = mt5.orders_get(ticket=int(order_id))
            if orders:
                o = orders[0]
                return Order(
                    id=str(o.ticket),
                    symbol=o.symbol,
                    side=OrderSide.BUY if o.type == 0 else OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    quantity=o.volume_current,
                    price=o.price_open,
                    status=OrderStatus.FILLED,
                )
        except Exception:
            pass
        return None

    async def get_positions(self) -> List[PositionInfo]:
        out: List[PositionInfo] = []
        for p in self._mt5.get_positions():
            out.append(PositionInfo(
                symbol=p.symbol, quantity=p.quantity,
                avg_entry_price=p.entry_price, current_price=p.current_price,
                unrealized_pnl=p.pnl, market_value=p.quantity * p.current_price,
            ))
        return out

    async def get_price(self, symbol: str) -> float:
        # ponytail: reuse MT5Broker tick via place_order path is overkill; read directly.
        import MetaTrader5 as mt5  # already imported by MT5Broker.connect
        sym = symbol.replace("-", "").upper()
        tick = mt5.symbol_info_tick(sym)
        return float(tick.ask if tick else 0.0)
