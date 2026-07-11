"""Exchange Manager — Multi-exchange orchestration, failover, and portfolio sync.

Manages multiple :class:`~quant_nanggroe.exchange.base.ExchangeInterface`
connections, providing:

* **Registration** — add/remove exchanges with roles (primary, failover, data-only).
* **Failover** — automatic switch to backup exchanges on primary failure.
* **Unified API** — delegate calls to the best available exchange.
* **Portfolio sync** — aggregate positions across all connected exchanges.
* **Health monitoring** — periodic health checks with reconnection logic.

Usage
-----
.. code-block:: python

    manager = ExchangeManager()
    manager.register("binance", binance_broker, role="primary")
    manager.register("bybit", bybit_broker, role="failover")
    manager.register("paper", paper_broker, role="failover")

    await manager.connect_all()

    # Routed to primary (binance) or failover
    ticker = await manager.get_ticker("BTC/USDT")
    order = await manager.place_order("BTC/USDT", OrderSide.BUY, OrderType.MARKET, 0.1)

    # Cross-exchange portfolio
    portfolio = await manager.get_aggregated_portfolio()
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel

from quant_nanggroe.exchange.base import (
    ExchangeError,
    ExchangeInterface,
    MarketDataError,
    OrderError,
    WebSocketCallback,
)
from quant_nanggroe.types.market import OHLCV, OrderBook, Ticker, TimeFrame
from quant_nanggroe.types.orders import Order, OrderSide, OrderType
from quant_nanggroe.types.positions import Portfolio, Position

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exchange role
# ---------------------------------------------------------------------------

class ExchangeRole(str, Enum):
    """Role assigned to a registered exchange."""

    PRIMARY = "primary"
    FAILOVER = "failover"
    DATA_ONLY = "data_only"  # market data only — no trading


# ---------------------------------------------------------------------------
# Registration record
# ---------------------------------------------------------------------------

class ExchangeRegistration(BaseModel):
    """Internal record for a registered exchange."""

    name: str
    exchange: Any  # ExchangeInterface (not typed to avoid Pydantic schema issues)
    role: ExchangeRole
    priority: int = 0  # Lower = higher priority for failover ordering
    connected: bool = False
    healthy: bool = False
    last_health_check: Optional[datetime] = None
    error_count: int = 0

    model_config = {"arbitrary_types_allowed": True}


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class ExchangeManager:
    """Multi-exchange manager with failover and portfolio aggregation.

    Parameters
    ----------
    health_check_interval:
        Seconds between automatic health checks (0 = disabled).
    max_errors:
        Mark an exchange unhealthy after this many consecutive errors.
    """

    def __init__(
        self,
        health_check_interval: float = 60.0,
        max_errors: int = 5,
    ) -> None:
        self._registrations: Dict[str, ExchangeRegistration] = {}
        self._primary_name: Optional[str] = None
        self._health_check_interval = health_check_interval
        self._max_errors = max_errors
        self._health_task: Optional[asyncio.Task] = None
        self._running = False

        # Cache
        self._cached_markets: Dict[str, Set[str]] = {}

    # ------------------------------------------------------------------ #
    # Registration
    # ------------------------------------------------------------------ #

    def register(
        self,
        name: str,
        exchange: ExchangeInterface,
        role: str = "failover",
        priority: int = 0,
    ) -> None:
        """Register an exchange connection.

        Args:
            name: Unique name for this exchange (e.g. ``"binance"``).
            exchange: An :class:`ExchangeInterface` implementation.
            role: One of ``"primary"``, ``"failover"``, ``"data_only"``.
            priority: Lower = higher priority in failover chain.

        Raises:
            ValueError: If an exchange with the same name is already registered.
        """
        if name in self._registrations:
            raise ValueError(f"Exchange '{name}' is already registered")

        exchange_role = ExchangeRole(role)

        reg = ExchangeRegistration(
            name=name,
            exchange=exchange,
            role=exchange_role,
            priority=priority,
        )
        self._registrations[name] = reg

        # Track primary
        if exchange_role == ExchangeRole.PRIMARY:
            if self._primary_name is not None and self._primary_name != name:
                # Downgrade existing primary to failover
                old = self._registrations.get(self._primary_name)
                if old:
                    old.role = ExchangeRole.FAILOVER
                    logger.warning(
                        "ExchangeManager: Downgrading %s from PRIMARY to FAILOVER",
                        self._primary_name,
                    )
            self._primary_name = name

        logger.info(
            "ExchangeManager: Registered %s as %s (priority=%d)",
            name, role, priority,
        )

    def unregister(self, name: str) -> None:
        """Remove a registered exchange.

        Args:
            name: Exchange name to remove.
        """
        reg = self._registrations.pop(name, None)
        if reg is None:
            return

        if self._primary_name == name:
            # Promote next best failover
            failovers = [
                r for r in self._registrations.values()
                if r.role in (ExchangeRole.FAILOVER,)
            ]
            if failovers:
                failovers.sort(key=lambda r: r.priority)
                best = failovers[0]
                best.role = ExchangeRole.PRIMARY
                self._primary_name = best.name
                logger.info(
                    "ExchangeManager: Promoted %s to PRIMARY after %s removal",
                    best.name, name,
                )
            else:
                self._primary_name = None
                logger.warning("ExchangeManager: No exchanges left after %s removal", name)

        logger.info("ExchangeManager: Unregistered %s", name)

    @property
    def registered_exchanges(self) -> List[str]:
        """Names of all registered exchanges."""
        return list(self._registrations.keys())

    @property
    def primary_name(self) -> Optional[str]:
        """Name of the current primary exchange."""
        return self._primary_name

    # ------------------------------------------------------------------ #
    # Connection lifecycle
    # ------------------------------------------------------------------ #

    async def connect_all(self) -> Dict[str, bool]:
        """Connect all registered exchanges.

        Returns:
            Mapping of exchange name → connection success.
        """
        results: Dict[str, bool] = {}
        for name, reg in self._registrations.items():
            try:
                success = await reg.exchange.connect()
                reg.connected = success
                reg.healthy = success
                reg.error_count = 0
                results[name] = success
                logger.info("ExchangeManager: %s connected successfully", name)
            except Exception as exc:
                reg.connected = False
                reg.healthy = False
                results[name] = False
                logger.error("ExchangeManager: %s connection failed: %s", name, exc)

        # Start health check loop
        if self._health_check_interval > 0 and not self._running:
            self._running = True
            self._health_task = asyncio.create_task(self._health_check_loop())

        return results

    async def disconnect_all(self) -> None:
        """Disconnect all registered exchanges."""
        self._running = False
        if self._health_task and not self._health_task.done():
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
            self._health_task = None

        for name, reg in self._registrations.items():
            try:
                await reg.exchange.disconnect()
                reg.connected = False
                reg.healthy = False
                logger.info("ExchangeManager: %s disconnected", name)
            except Exception as exc:
                logger.error("ExchangeManager: %s disconnect error: %s", name, exc)

    # ------------------------------------------------------------------ #
    # Failover routing
    # ------------------------------------------------------------------ #

    def _get_trading_exchange(self) -> Optional[ExchangeRegistration]:
        """Get the best available trading exchange (primary or failover).

        Returns:
            The highest-priority healthy exchange, or ``None``.
        """
        candidates = [
            r for r in self._registrations.values()
            if r.role in (ExchangeRole.PRIMARY, ExchangeRole.FAILOVER)
            and r.healthy
            and r.connected
        ]
        if not candidates:
            # Fallback: try unhealthy primary
            primary = self._registrations.get(self._primary_name or "")
            if primary and primary.connected:
                return primary
            return None

        # Sort: PRIMARY first, then by priority
        candidates.sort(
            key=lambda r: (0 if r.role == ExchangeRole.PRIMARY else 1, r.priority),
        )
        return candidates[0]

    def _get_data_exchange(self, preferred: Optional[str] = None) -> Optional[ExchangeRegistration]:
        """Get the best available data exchange.

        Args:
            preferred: Preferred exchange name (tries this first).

        Returns:
            The preferred or best available healthy exchange.
        """
        if preferred:
            reg = self._registrations.get(preferred)
            if reg and reg.healthy and reg.connected:
                return reg

        # Any healthy connected exchange
        candidates = [
            r for r in self._registrations.values()
            if r.healthy and r.connected
        ]
        if not candidates:
            return None
        candidates.sort(
            key=lambda r: (0 if r.role == ExchangeRole.PRIMARY else 1, r.priority),
        )
        return candidates[0]

    def _record_error(self, name: str, exc: Exception) -> None:
        """Record an error and potentially mark the exchange unhealthy."""
        reg = self._registrations.get(name)
        if reg is None:
            return
        reg.error_count += 1
        if reg.error_count >= self._max_errors:
            reg.healthy = False
            logger.warning(
                "ExchangeManager: %s marked UNHEALTHY after %d errors",
                name, reg.error_count,
            )
            # Trigger failover if this was primary
            if name == self._primary_name:
                self._promote_failover()

    def _record_success(self, name: str) -> None:
        """Reset error count on a successful operation."""
        reg = self._registrations.get(name)
        if reg:
            reg.error_count = 0
            reg.healthy = True

    def _promote_failover(self) -> None:
        """Promote the best failover exchange to primary."""
        failovers = [
            r for r in self._registrations.values()
            if r.role == ExchangeRole.FAILOVER and r.healthy and r.connected
        ]
        if failovers:
            failovers.sort(key=lambda r: r.priority)
            best = failovers[0]
            best.role = ExchangeRole.PRIMARY
            self._primary_name = best.name
            logger.info(
                "ExchangeManager: FAILOVER — promoted %s to PRIMARY",
                best.name,
            )
        else:
            logger.error("ExchangeManager: FAILOVER — no healthy exchanges available")

    # ------------------------------------------------------------------ #
    # Unified trading API
    # ------------------------------------------------------------------ #

    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        client_order_id: Optional[str] = None,
        strategy_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Order:
        """Place an order on the best available trading exchange.

        Automatically fails over to the next exchange on error.

        Raises:
            ExchangeError: If all trading exchanges fail.
        """
        reg = self._get_trading_exchange()
        if reg is None:
            raise ExchangeError("No healthy trading exchanges available")

        try:
            order = await reg.exchange.place_order(
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                stop_price=stop_price,
                client_order_id=client_order_id,
                strategy_name=strategy_name,
                agent_name=agent_name,
                notes=notes,
            )
            self._record_success(reg.name)
            return order
        except Exception as exc:
            self._record_error(reg.name, exc)
            logger.warning(
                "ExchangeManager: %s place_order failed, trying failover: %s",
                reg.name, exc,
            )
            # Try failover
            failover_reg = self._get_trading_exchange()
            if failover_reg and failover_reg.name != reg.name:
                try:
                    order = await failover_reg.exchange.place_order(
                        symbol=symbol,
                        side=side,
                        order_type=order_type,
                        quantity=quantity,
                        price=price,
                        stop_price=stop_price,
                        client_order_id=client_order_id,
                        strategy_name=strategy_name,
                        agent_name=agent_name,
                        notes=notes,
                    )
                    self._record_success(failover_reg.name)
                    return order
                except Exception as fo_exc:
                    self._record_error(failover_reg.name, fo_exc)
                    raise ExchangeError(
                        f"All trading exchanges failed: {exc}; {fo_exc}",
                    ) from fo_exc
            raise ExchangeError(f"Order failed on {reg.name}: {exc}") from exc

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        """Cancel an order, searching across all trading exchanges."""
        last_exc: Optional[Exception] = None
        for reg in self._registrations.values():
            if reg.role == ExchangeRole.DATA_ONLY or not reg.connected:
                continue
            try:
                order = await reg.exchange.cancel_order(order_id, symbol)
                self._record_success(reg.name)
                return order
            except (OrderError, Exception) as exc:
                last_exc = exc
                continue

        raise OrderError(
            f"Order {order_id} not found on any exchange: {last_exc}",
            order_id=order_id,
        )

    async def get_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        """Query an order across all trading exchanges."""
        last_exc: Optional[Exception] = None
        for reg in self._registrations.values():
            if reg.role == ExchangeRole.DATA_ONLY or not reg.connected:
                continue
            try:
                order = await reg.exchange.get_order(order_id, symbol)
                self._record_success(reg.name)
                return order
            except (OrderError, Exception) as exc:
                last_exc = exc
                continue

        raise OrderError(
            f"Order {order_id} not found on any exchange: {last_exc}",
            order_id=order_id,
        )

    # ------------------------------------------------------------------ #
    # Unified market data API
    # ------------------------------------------------------------------ #

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.D1,
        since: Optional[datetime] = None,
        limit: int = 500,
        preferred: Optional[str] = None,
    ) -> List[OHLCV]:
        """Fetch OHLCV from the best available data exchange."""
        reg = self._get_data_exchange(preferred)
        if reg is None:
            raise MarketDataError("No healthy exchanges available for market data")

        try:
            result = await reg.exchange.get_ohlcv(symbol, timeframe, since, limit)
            self._record_success(reg.name)
            return result
        except Exception as exc:
            self._record_error(reg.name, exc)
            # Try another exchange
            alt = self._get_data_exchange()
            if alt and alt.name != reg.name:
                try:
                    result = await alt.exchange.get_ohlcv(symbol, timeframe, since, limit)
                    self._record_success(alt.name)
                    return result
                except Exception as alt_exc:
                    raise MarketDataError(
                        f"All exchanges failed for OHLCV {symbol}: {exc}; {alt_exc}",
                    ) from alt_exc
            raise MarketDataError(f"OHLCV fetch failed: {exc}") from exc

    async def get_ticker(
        self,
        symbol: str,
        preferred: Optional[str] = None,
    ) -> Ticker:
        """Fetch ticker from the best available data exchange."""
        reg = self._get_data_exchange(preferred)
        if reg is None:
            raise MarketDataError("No healthy exchanges available for market data")

        try:
            result = await reg.exchange.get_ticker(symbol)
            self._record_success(reg.name)
            return result
        except Exception as exc:
            self._record_error(reg.name, exc)
            alt = self._get_data_exchange()
            if alt and alt.name != reg.name:
                try:
                    result = await alt.exchange.get_ticker(symbol)
                    self._record_success(alt.name)
                    return result
                except Exception as alt_exc:
                    raise MarketDataError(
                        f"All exchanges failed for ticker {symbol}: {exc}; {alt_exc}",
                    ) from alt_exc
            raise MarketDataError(f"Ticker fetch failed: {exc}") from exc

    async def get_orderbook(
        self,
        symbol: str,
        limit: int = 20,
        preferred: Optional[str] = None,
    ) -> OrderBook:
        """Fetch order book from the best available data exchange."""
        reg = self._get_data_exchange(preferred)
        if reg is None:
            raise MarketDataError("No healthy exchanges available for market data")

        try:
            result = await reg.exchange.get_orderbook(symbol, limit)
            self._record_success(reg.name)
            return result
        except Exception as exc:
            self._record_error(reg.name, exc)
            alt = self._get_data_exchange()
            if alt and alt.name != reg.name:
                try:
                    result = await alt.exchange.get_orderbook(symbol, limit)
                    self._record_success(alt.name)
                    return result
                except Exception as alt_exc:
                    raise MarketDataError(
                        f"All exchanges failed for orderbook {symbol}: {exc}; {alt_exc}",
                    ) from alt_exc
            raise MarketDataError(f"Orderbook fetch failed: {exc}") from exc

    async def get_trades(
        self,
        symbol: str,
        since: Optional[datetime] = None,
        limit: int = 100,
        preferred: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch recent trades from the best available data exchange."""
        reg = self._get_data_exchange(preferred)
        if reg is None:
            raise MarketDataError("No healthy exchanges available for market data")

        try:
            result = await reg.exchange.get_trades(symbol, since, limit)
            self._record_success(reg.name)
            return result
        except Exception as exc:
            self._record_error(reg.name, exc)
            alt = self._get_data_exchange()
            if alt and alt.name != reg.name:
                try:
                    result = await alt.exchange.get_trades(symbol, since, limit)
                    self._record_success(alt.name)
                    return result
                except Exception as alt_exc:
                    raise MarketDataError(
                        f"All exchanges failed for trades {symbol}: {exc}; {alt_exc}",
                    ) from alt_exc
            raise MarketDataError(f"Trades fetch failed: {exc}") from exc

    # ------------------------------------------------------------------ #
    # Account & Portfolio
    # ------------------------------------------------------------------ #

    async def get_balance(self, exchange_name: Optional[str] = None) -> Dict[str, float]:
        """Fetch balance from a specific or best exchange."""
        reg = self._get_data_exchange(exchange_name)
        if reg is None:
            raise ExchangeError("No healthy exchange available")

        try:
            result = await reg.exchange.get_balance()
            self._record_success(reg.name)
            return result
        except Exception as exc:
            self._record_error(reg.name, exc)
            raise ExchangeError(f"Balance fetch failed: {exc}") from exc

    async def get_positions(self, exchange_name: Optional[str] = None) -> List[Position]:
        """Fetch positions from a specific or best exchange."""
        reg = self._get_data_exchange(exchange_name)
        if reg is None:
            raise ExchangeError("No healthy exchange available")

        try:
            result = await reg.exchange.get_positions()
            self._record_success(reg.name)
            return result
        except Exception as exc:
            self._record_error(reg.name, exc)
            raise ExchangeError(f"Positions fetch failed: {exc}") from exc

    async def get_portfolio(self, exchange_name: Optional[str] = None) -> Portfolio:
        """Fetch portfolio from a specific or best exchange."""
        reg = self._get_data_exchange(exchange_name)
        if reg is None:
            raise ExchangeError("No healthy exchange available")

        try:
            result = await reg.exchange.get_portfolio()
            self._record_success(reg.name)
            return result
        except Exception as exc:
            self._record_error(reg.name, exc)
            raise ExchangeError(f"Portfolio fetch failed: {exc}") from exc

    async def get_aggregated_portfolio(self) -> Portfolio:
        """Aggregate positions across all connected exchanges.

        Returns:
            A single :class:`~quant_nanggroe.types.positions.Portfolio` with
            combined cash, positions, and P&L from all exchanges.

        Note:
            Positions on the same symbol across exchanges are merged
            using weighted average entry price.
        """
        total_cash = 0.0
        total_initial = 0.0
        total_realized_pnl = 0.0
        merged_positions: Dict[str, Position] = {}

        for reg in self._registrations.values():
            if not reg.connected:
                continue
            try:
                portfolio = await reg.exchange.get_portfolio()
                total_cash += portfolio.cash
                total_initial += portfolio.initial_capital
                total_realized_pnl += portfolio.total_realized_pnl

                for symbol, pos in portfolio.positions.items():
                    if symbol in merged_positions:
                        existing = merged_positions[symbol]
                        # Weighted average
                        total_qty = existing.quantity + pos.quantity
                        if total_qty > 0:
                            avg_entry = (
                                existing.entry_price * existing.quantity
                                + pos.entry_price * pos.quantity
                            ) / total_qty
                            merged_positions[symbol] = Position(
                                symbol=symbol,
                                side=existing.side,
                                quantity=total_qty,
                                entry_price=avg_entry,
                                current_price=pos.current_price,
                                cost_basis=avg_entry * total_qty,
                                market_value=total_qty * pos.current_price,
                            )
                    else:
                        merged_positions[symbol] = pos

                self._record_success(reg.name)
            except Exception as exc:
                self._record_error(reg.name, exc)
                logger.warning(
                    "ExchangeManager: Failed to fetch portfolio from %s: %s",
                    reg.name, exc,
                )

        agg = Portfolio(
            name="aggregated",
            currency="USDT",
            # ponytail: gt=0 constraint — fall back to 1.0 when no capital booked yet
            initial_capital=max(total_initial or total_cash, 1.0),
            cash=total_cash,
            total_realized_pnl=total_realized_pnl,
        )
        for symbol, pos in merged_positions.items():
            agg.positions[symbol] = pos
        agg.recalculate()
        return agg

    # ------------------------------------------------------------------ #
    # Markets
    # ------------------------------------------------------------------ #

    async def get_markets(self, exchange_name: Optional[str] = None) -> List[str]:
        """List markets from a specific or best exchange."""
        reg = self._get_data_exchange(exchange_name)
        if reg is None:
            raise MarketDataError("No healthy exchange available")

        try:
            result = await reg.exchange.get_markets()
            self._cached_markets[reg.name] = set(result)
            self._record_success(reg.name)
            return result
        except Exception as exc:
            self._record_error(reg.name, exc)
            raise MarketDataError(f"Markets fetch failed: {exc}") from exc

    async def get_all_markets(self) -> Dict[str, List[str]]:
        """Fetch markets from all connected exchanges.

        Returns:
            Mapping of exchange name → list of symbols.
        """
        result: Dict[str, List[str]] = {}
        for name, reg in self._registrations.items():
            if not reg.connected:
                continue
            try:
                markets = await reg.exchange.get_markets()
                result[name] = markets
                self._cached_markets[name] = set(markets)
                self._record_success(name)
            except Exception as exc:
                self._record_error(name, exc)
                logger.warning("ExchangeManager: Failed to get markets from %s: %s", name, exc)
        return result

    # ------------------------------------------------------------------ #
    # Health monitoring
    # ------------------------------------------------------------------ #

    async def health_check_all(self) -> Dict[str, bool]:
        """Run health checks on all registered exchanges.

        Returns:
            Mapping of exchange name → health status.
        """
        results: Dict[str, bool] = {}
        for name, reg in self._registrations.items():
            if not reg.connected:
                results[name] = False
                continue
            try:
                healthy = await reg.exchange.health_check()
                reg.healthy = healthy
                reg.last_health_check = datetime.now(tz=timezone.utc)
                if healthy:
                    reg.error_count = 0
                results[name] = healthy
            except Exception as exc:
                reg.healthy = False
                results[name] = False
                logger.warning("ExchangeManager: %s health check failed: %s", name, exc)

        return results

    async def _health_check_loop(self) -> None:
        """Periodic health check coroutine."""
        try:
            while self._running:
                await asyncio.sleep(self._health_check_interval)
                results = await self.health_check_all()
                unhealthy = [n for n, h in results.items() if not h]
                if unhealthy:
                    logger.warning(
                        "ExchangeManager: Unhealthy exchanges: %s", unhealthy,
                    )
                    # Attempt reconnection for unhealthy exchanges
                    for name in unhealthy:
                        reg = self._registrations.get(name)
                        if reg and not reg.healthy:
                            try:
                                await reg.exchange.disconnect()
                                success = await reg.exchange.connect()
                                reg.connected = success
                                reg.healthy = success
                                reg.error_count = 0
                                if success:
                                    logger.info(
                                        "ExchangeManager: %s reconnected successfully", name,
                                    )
                            except Exception as exc:
                                logger.error(
                                    "ExchangeManager: %s reconnection failed: %s", name, exc,
                                )

                    # Check if primary needs failover
                    if self._primary_name and not results.get(self._primary_name, False):
                        self._promote_failover()

        except asyncio.CancelledError:
            pass

    # ------------------------------------------------------------------ #
    # WebSocket delegation
    # ------------------------------------------------------------------ #

    async def subscribe_ticker(
        self,
        symbol: str,
        callback: WebSocketCallback,
        exchange_name: Optional[str] = None,
    ) -> None:
        """Subscribe to ticker updates from a specific or best exchange."""
        reg = self._get_data_exchange(exchange_name)
        if reg is None:
            raise MarketDataError("No healthy exchange for WebSocket subscription")
        await reg.exchange.subscribe_ticker(symbol, callback)

    async def subscribe_orderbook(
        self,
        symbol: str,
        callback: WebSocketCallback,
        exchange_name: Optional[str] = None,
    ) -> None:
        """Subscribe to order book updates from a specific or best exchange."""
        reg = self._get_data_exchange(exchange_name)
        if reg is None:
            raise MarketDataError("No healthy exchange for WebSocket subscription")
        await reg.exchange.subscribe_orderbook(symbol, callback)

    async def subscribe_trades(
        self,
        symbol: str,
        callback: WebSocketCallback,
        exchange_name: Optional[str] = None,
    ) -> None:
        """Subscribe to trade updates from a specific or best exchange."""
        reg = self._get_data_exchange(exchange_name)
        if reg is None:
            raise MarketDataError("No healthy exchange for WebSocket subscription")
        await reg.exchange.subscribe_trades(symbol, callback)

    async def unsubscribe(
        self,
        symbol: str,
        channel: str,
        exchange_name: Optional[str] = None,
    ) -> None:
        """Unsubscribe from a data stream on a specific or best exchange."""
        reg = self._get_data_exchange(exchange_name)
        if reg is None:
            return
        await reg.exchange.unsubscribe(symbol, channel)

    # ------------------------------------------------------------------ #
    # Diagnostics
    # ------------------------------------------------------------------ #

    def get_status(self) -> Dict[str, Dict[str, Any]]:
        """Get the status of all registered exchanges.

        Returns:
            Mapping of exchange name → status dict with keys:
            ``role``, ``connected``, ``healthy``, ``error_count``,
            ``last_health_check``.
        """
        return {
            name: {
                "role": reg.role.value,
                "connected": reg.connected,
                "healthy": reg.healthy,
                "error_count": reg.error_count,
                "last_health_check": (
                    reg.last_health_check.isoformat() if reg.last_health_check else None
                ),
            }
            for name, reg in self._registrations.items()
        }
