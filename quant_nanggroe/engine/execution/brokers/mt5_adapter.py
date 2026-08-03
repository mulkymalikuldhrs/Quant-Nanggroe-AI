"""Async adapter: MT5Broker (BrokerConnector, sync) -> engine.execution.base.Broker (async).

ponytail: two ABCs existed (engine base.Broker vs connectors broker_base.BrokerConnector);
MT5Broker implemented the wrong one, so it never reached ExecutionManager. This thin
adapter bridges them. No new broker logic — only sync->async + type mapping.
"""
from __future__ import annotations

import logging
import time
from typing import List, Optional

from quant_nanggroe.connectors.broker_base import Order as ConnOrder
from quant_nanggroe.connectors.mt5_broker import MT5Broker
from quant_nanggroe.engine.execution.base import (
    AccountInfo,
    Broker,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    PositionInfo,
)
from quant_nanggroe.engine.risk.constants import MT5_SYMBOL_MAP

logger = logging.getLogger(__name__)

# MT5 TRADE_RETCODE values that warrant a single retry (stale price / slow server)
_MT5_REQUOTE = 10004
_MT5_TIMEOUT = 10013

_SIDE_MAP = {"BUY": "buy", "SELL": "sell"}
_REV_SIDE = {"buy": OrderSide.BUY, "sell": OrderSide.SELL}


class CircuitBreaker:
    """Simple circuit breaker for broker adapter.

    Trips after `threshold` consecutive failures within `window_seconds`.
    Once tripped, all operations are blocked for `recovery_seconds`.
    """

    def __init__(self, threshold: int = 5, window_seconds: float = 60.0, recovery_seconds: float = 300.0) -> None:
        self._threshold = threshold
        self._window_seconds = window_seconds
        self._recovery_seconds = recovery_seconds
        self._failures: list[float] = []
        self._tripped_at: Optional[float] = None

    @property
    def is_tripped(self) -> bool:
        if self._tripped_at is None:
            return False
        if time.monotonic() - self._tripped_at > self._recovery_seconds:
            self._tripped_at = None
            self._failures.clear()
            logger.info("Circuit breaker reset after recovery window")
            return False
        return True

    def record_success(self) -> None:
        self._failures.clear()

    def record_failure(self) -> None:
        now = time.monotonic()
        # Prune failures outside the window
        self._failures = [t for t in self._failures if now - t <= self._window_seconds]
        self._failures.append(now)
        if len(self._failures) >= self._threshold:
            self._tripped_at = now
            logger.critical(
                "Circuit breaker TRIPPED: %d failures in %.0fs — blocking orders for %.0fs",
                self._threshold, self._window_seconds, self._recovery_seconds,
            )


class MT5ExecutionBroker(Broker):
    """Wraps a connected MT5Broker into the async execution-engine Broker ABC."""

    def __init__(self, mt5: MT5Broker) -> None:
        self._mt5 = mt5
        self._circuit_breaker = CircuitBreaker()

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
        # Circuit breaker gate — fail-fast if tripped
        if self._circuit_breaker.is_tripped:
            order.status = OrderStatus.REJECTED
            order.metadata["reason"] = "Circuit breaker tripped — MT5 unavailable"
            order.metadata["error_code"] = "CIRCUIT_BREAKER"
            logger.critical("Order %s rejected: circuit breaker tripped", order.id)
            return order

        max_attempts = 3
        last_err = None
        for attempt in range(max_attempts):
            try:
                # Normalize client quantity to MT5 lot units.
                # Client code previously sent raw units/contract counts; this
                # adapter now closes that gap by converting to lots using a
                # standard contract size unless the value is already within
                # normal lot range.
                quantity = float(order.quantity)
                contract_size = 100000.0
                if quantity > 100.0:
                    quantity = max(0.01, round(quantity / contract_size, 2))
                quantity = max(0.01, min(quantity, 100.0))
                conn_order = ConnOrder(
                    symbol=order.symbol,
                    side=_SIDE_MAP.get(order.side.value, "buy"),
                    quantity=quantity,
                    order_type=order.order_type.value.lower(),
                    price=order.price,
                    stop_loss=order.stop_loss,
                    take_profit=order.take_profit,
                )
                result = self._mt5.place_order(conn_order)
                if not result:
                    self._circuit_breaker.record_failure()
                    order.status = OrderStatus.REJECTED
                    order.metadata["reason"] = "MT5 order rejected"
                    order.metadata["error_code"] = "REJECTED"
                    return order

                price = await self.get_price(order.symbol)
                if price <= 0:
                    if attempt < max_attempts - 1:
                        logger.warning(
                            "MT5 fill price=0 on attempt %d for %s, retrying",
                            attempt + 1, order.symbol,
                        )
                        self._circuit_breaker.record_failure()
                        time.sleep(0.5 * (2 ** attempt))  # exponential backoff
                        continue
                    self._circuit_breaker.record_failure()
                    order.status = OrderStatus.REJECTED
                    order.metadata["reason"] = f"MT5 returned zero fill price after {max_attempts} attempts"
                    order.metadata["error_code"] = "ZERO_PRICE"
                    logger.error(
                        "Order %s rejected: fill price=0 after %d attempts for %s",
                        order.id, max_attempts, order.symbol,
                    )
                    return order

                # Success — reset circuit breaker
                self._circuit_breaker.record_success()
                order.status = OrderStatus.FILLED
                order.metadata["fill_price"] = price
                order.metadata["broker_order_id"] = result
                order.metadata["error_code"] = "OK"
                return order

            except RuntimeError as exc:
                last_err = exc
                err_str = str(exc)
                is_transient = any(code in err_str for code in ("10004", "10013", "REQUOTE", "TIMEOUT"))
                if is_transient and attempt < max_attempts - 1:
                    logger.warning(
                        "MT5 transient error on attempt %d for %s: %s",
                        attempt + 1, order.symbol, err_str,
                    )
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                self._circuit_breaker.record_failure()
                order.status = OrderStatus.REJECTED
                order.metadata["reason"] = err_str
                order.metadata["error_code"] = "MT5_ERROR"
                logger.error("MT5 submit_order failed: %s", err_str)
                return order

            except Exception as e:
                self._circuit_breaker.record_failure()
                order.status = OrderStatus.REJECTED
                order.metadata["reason"] = str(e)
                order.metadata["error_code"] = "EXCEPTION"
                logger.error("MT5 submit_order exception: %s", e, exc_info=True)
                return order

        self._circuit_breaker.record_failure()
        order.status = OrderStatus.REJECTED
        order.metadata["reason"] = f"MT5 order failed after {max_attempts} attempts: {last_err}"
        order.metadata["error_code"] = "MAX_RETRIES"
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
        """Fetch the current ask price for a symbol via MT5.

        Uses MT5_SYMBOL_MAP for correct symbol translation
        (e.g. BTCUSDT → BTCUSD). Falls back to the raw symbol
        if no mapping exists, then uppercased and stripped of hyphens.
        """
        import MetaTrader5 as mt5
        mt5_sym = MT5_SYMBOL_MAP.get(symbol)
        if not mt5_sym:
            mt5_sym = symbol.replace("-", "").upper()
        tick = mt5.symbol_info_tick(mt5_sym)
        return float(tick.ask if tick else 0.0)

    def get_rates(self, symbol: str, timeframe=None, count: int = 200):
        """Fetch OHLCV via the wrapped MT5Broker (owns the live MT5 session).

        Routes through MT5Broker.get_rates() to avoid the MetaTrader5
        'copy_rates_from_pos returned exception set' C-API corruption that
        occurs when a second bare `mt5` module handle is used after the
        broker already initialized the terminal in this process.
        """
        import MetaTrader5 as _mt5mod
        tf = timeframe if timeframe is not None else _mt5mod.TIMEFRAME_M15
        return self._mt5.get_rates(symbol, tf, count)
