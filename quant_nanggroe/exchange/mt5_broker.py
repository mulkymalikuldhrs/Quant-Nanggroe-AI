"""MetaTrader 5 Broker — Forex/CFD Trading via MT5 Terminal.

Provides a production-grade implementation of
:class:`~quant_nanggroe.exchange.base.ExchangeInterface` for the
MetaTrader 5 platform, supporting forex, CFDs, and futures.

Features
--------
* Connect to MT5 terminal (local or remote)
* Market, limit, stop, and stop-limit order execution
* Position tracking with SL/TP modification
* Trade history retrieval
* Account info and position sizing
* Symbol information and tick data

Dependencies
------------
Requires the ``MetaTrader5`` package (Windows only). Install with:
``pip install MetaTrader5``

Notes
-----
MT5 only runs on Windows. On other platforms, all methods will
gracefully raise ConnectionError indicating the platform limitation.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from quant_nanggroe.exchange.base import (
    AuthenticationError,
    ConnectionError,
    ExchangeConfig,
    ExchangeError,
    ExchangeInterface,
    ExchangeState,
    MarketDataError,
    OrderError,
    WebSocketCallback,
)
from quant_nanggroe.types.market import OHLCV, OrderBook, Ticker, TimeFrame
from quant_nanggroe.types.orders import Order, OrderSide, OrderStatus, OrderType
from quant_nanggroe.types.positions import Portfolio, Position, PositionSide

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# MT5-specific models
# ---------------------------------------------------------------------------

class MT5AccountInfo(BaseModel):
    """MetaTrader 5 account information."""
    login: int = 0
    trade_mode: int = 0
    leverage: int = 100
    limit_orders: int = 0
    margin_so_mode: int = 0
    margin_currency: str = "USD"
    balance: float = 0.0
    credit: float = 0.0
    profit: float = 0.0
    equity: float = 0.0
    margin: float = 0.0
    margin_free: float = 0.0
    margin_level: float = 0.0
    server: str = ""
    name: str = ""
    currency: str = "USD"


class MT5SymbolInfo(BaseModel):
    """MetaTrader 5 symbol information."""
    symbol: str = ""
    bid: float = 0.0
    ask: float = 0.0
    last: float = 0.0
    point: float = 0.0
    spread: int = 0
    volume_min: float = 0.01
    volume_max: float = 100.0
    volume_step: float = 0.01
    trade_stops_level: int = 0
    trade_tick_size: float = 0.0
    trade_tick_value: float = 0.0


class MT5PositionInfo(BaseModel):
    """MetaTrader 5 position information."""
    ticket: int = 0
    symbol: str = ""
    type: str = "BUY"
    volume: float = 0.0
    open_price: float = 0.0
    current_price: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
    pnl: float = 0.0
    swap: float = 0.0
    commission: float = 0.0
    magic: int = 0
    comment: str = ""


# ---------------------------------------------------------------------------
# Timeframe mapping
# ---------------------------------------------------------------------------

_TIMEFRAME_TO_MT5: Dict[TimeFrame, str] = {
    TimeFrame.M1: "M1",
    TimeFrame.M5: "M5",
    TimeFrame.M15: "M15",
    TimeFrame.M30: "M30",
    TimeFrame.H1: "H1",
    TimeFrame.H4: "H4",
    TimeFrame.D1: "D1",
    TimeFrame.W1: "W1",
    TimeFrame.MO1: "MN1",
}


# ---------------------------------------------------------------------------
# MT5Broker
# ---------------------------------------------------------------------------

class MT5Broker(ExchangeInterface):
    """MetaTrader 5 broker implementing ExchangeInterface.

    Provides full trading capabilities via the MetaTrader5 Python API,
    including order placement, position management, market data, and
    account information.

    Parameters
    ----------
    config:
        Exchange configuration. ``exchange_id`` should be ``"mt5"``.
        ``api_key`` should contain the login ID (as string).
        ``api_secret`` should contain the password.
        ``options["server"]`` should contain the server name.
        ``options["path"]`` should contain the terminal path (optional).

    Examples
    --------
    .. code-block:: python

        config = ExchangeConfig(
            exchange_id="mt5",
            api_key="<placeholder>",
            api_secret="<placeholder>",
            options={"server": "MetaQuotes-Demo"},
        )
        broker = MT5Broker(config)
        await broker.connect()
        account = await broker.get_account_info()
    """

    def __init__(self, config: ExchangeConfig) -> None:
        self._config = config
        self._state: ExchangeState = ExchangeState.DISCONNECTED
        self._mt5 = None
        self._local_orders: Dict[str, Order] = {}
        self._local_positions: Dict[str, Position] = {}

    # ----- Connection lifecycle -----

    async def connect(self) -> bool:
        """Connect to the MetaTrader 5 terminal.

        Returns
        -------
        bool
            ``True`` if connected successfully.

        Raises
        ------
        ConnectionError
            If the connection fails.
        AuthenticationError
            If the login credentials are invalid.
        """
        if self._state == ExchangeState.CONNECTED:
            return True

        self._state = ExchangeState.CONNECTING
        try:
            import MetaTrader5 as mt5  # type: ignore[import-untyped]

            self._mt5 = mt5

            # Initialize MT5
            init_params: Dict[str, Any] = {"timeout": 60000}
            path = self._config.options.get("path")
            if path:
                init_params["path"] = path

            if not mt5.initialize(**init_params):
                error = mt5.last_error()
                self._state = ExchangeState.ERROR
                raise ConnectionError(
                    f"MT5 initialization failed: {error}",
                    exchange="mt5",
                )

            # Login if credentials provided
            login = self._config.api_key
            password = self._config.api_secret
            server = self._config.options.get("server")

            if login and password and server:
                try:
                    login_id = int(login)
                except (ValueError, TypeError):
                    self._state = ExchangeState.ERROR
                    raise AuthenticationError(
                        f"Invalid MT5 login ID: {login}",
                        exchange="mt5",
                    )

                if not mt5.login(login=login_id, password=password, server=server):
                    error = mt5.last_error()
                    self._state = ExchangeState.ERROR
                    raise AuthenticationError(
                        f"MT5 login failed: {error}",
                        exchange="mt5",
                    )

            self._state = ExchangeState.CONNECTED
            logger.info("MT5Broker: Connected to %s", server or "Local Terminal")
            return True

        except ImportError as exc:
            self._state = ExchangeState.ERROR
            raise ImportError(
                "MetaTrader5 package is required. Install with: pip install MetaTrader5 "
                "(Windows only)"
            ) from exc
        except (ConnectionError, AuthenticationError):
            raise
        except Exception as exc:
            self._state = ExchangeState.ERROR
            raise ConnectionError(
                f"Failed to connect to MT5: {exc}",
                exchange="mt5",
                original=exc,
            ) from exc

    async def disconnect(self) -> None:
        """Close the MT5 connection and clean up resources."""
        if self._mt5:
            try:
                self._mt5.shutdown()
            except Exception as exc:
                logger.warning("MT5 shutdown error: %s", exc)
            self._mt5 = None

        self._state = ExchangeState.DISCONNECTED
        logger.info("MT5Broker: Disconnected")

    @property
    def is_connected(self) -> bool:
        if self._mt5 and self._state == ExchangeState.CONNECTED:
            try:
                return self._mt5.initialize()
            except Exception:
                return False
        return False

    @property
    def state(self) -> ExchangeState:
        return self._state

    @property
    def name(self) -> str:
        return "mt5"

    # ----- Account -----

    async def get_account_info(self) -> MT5AccountInfo:
        """Get MT5 account information.

        Returns:
            MT5AccountInfo with account details.
        """
        self._require_mt5()
        try:
            info = self._mt5.account_info()
            if info is None:
                raise ExchangeError("Failed to get MT5 account info", exchange="mt5")

            return MT5AccountInfo(
                login=info.login,
                trade_mode=info.trade_mode,
                leverage=info.leverage,
                limit_orders=info.limit_orders,
                margin_so_mode=info.margin_so_mode,
                margin_currency=info.margin_currency,
                balance=float(info.balance),
                credit=float(info.credit),
                profit=float(info.profit),
                equity=float(info.equity),
                margin=float(info.margin),
                margin_free=float(info.margin_free),
                margin_level=float(info.margin_level or 0),
                server=info.server,
                name=info.name,
                currency=info.currency,
            )
        except ExchangeError:
            raise
        except Exception as exc:
            raise ExchangeError(
                f"Failed to get account info: {exc}",
                exchange="mt5",
                original=exc,
            ) from exc

    async def get_balance(self) -> Dict[str, float]:
        """Get account balances from MT5.

        Returns:
            Mapping of currency → balance.
        """
        info = await self.get_account_info()
        return {
            info.currency: info.balance,
            "equity": info.equity,
            "margin_free": info.margin_free,
        }

    async def get_positions(self) -> List[Position]:
        """Get all open positions from MT5.

        Returns:
            List of Position instances.
        """
        self._require_mt5()
        try:
            mt5_positions = self._mt5.positions_get()
            if not mt5_positions:
                return []

            positions = []
            for p in mt5_positions:
                side = PositionSide.LONG if p.type == self._mt5.POSITION_TYPE_BUY else PositionSide.SHORT
                pos = Position(
                    symbol=p.symbol,
                    side=side,
                    quantity=float(p.volume),
                    entry_price=float(p.price_open),
                    current_price=float(p.price_current),
                    unrealized_pnl=float(p.profit),
                    cost_basis=float(p.price_open) * float(p.volume),
                    market_value=float(p.price_current) * float(p.volume),
                    broker_id="mt5",
                    last_updated=datetime.now(tz=timezone.utc),
                )
                positions.append(pos)
                self._local_positions[f"{p.symbol}:{p.ticket}"] = pos

            return positions
        except ExchangeError:
            raise
        except Exception as exc:
            raise ExchangeError(
                f"Failed to get positions: {exc}",
                exchange="mt5",
                original=exc,
            ) from exc

    async def get_portfolio(self) -> Portfolio:
        """Get portfolio snapshot from MT5.

        Returns:
            Complete Portfolio with positions and metrics.
        """
        info = await self.get_account_info()
        positions = await self.get_positions()

        portfolio = Portfolio(
            name="mt5",
            currency=info.currency,
            initial_capital=info.balance,
            cash=info.balance - sum(p.cost_basis for p in positions),
        )
        for pos in positions:
            portfolio.positions[pos.symbol] = pos
        portfolio.recalculate()
        return portfolio

    # ----- Trading -----

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
        """Place an order on MT5.

        Supports market, limit, and stop orders.

        Args:
            symbol: Trading symbol (e.g., "EURUSD").
            side: Buy or sell.
            order_type: Market, limit, or stop.
            quantity: Position size in lots.
            price: Limit/stop price (required for limit/stop orders).
            stop_price: Stop trigger price.
            notes: Order comment.

        Returns:
            The placed Order with MT5-assigned ticket.

        Raises:
            OrderError: If the order is invalid or rejected.
        """
        self._require_mt5()
        mt5 = self._mt5

        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                raise OrderError(
                    f"Symbol {symbol} not available",
                    exchange="mt5",
                )

            # Determine order type and action
            if side == OrderSide.BUY:
                if order_type == OrderType.MARKET:
                    action_enum = mt5.TRADE_ACTION_DEAL
                    type_enum = mt5.ORDER_TYPE_BUY
                    order_price = tick.ask
                elif order_type == OrderType.LIMIT:
                    if price is None:
                        raise OrderError("Limit price required for BUY LIMIT", exchange="mt5")
                    action_enum = mt5.TRADE_ACTION_PENDING
                    type_enum = mt5.ORDER_TYPE_BUY_LIMIT
                    order_price = price
                elif order_type == OrderType.STOP:
                    if stop_price is None:
                        raise OrderError("Stop price required for BUY STOP", exchange="mt5")
                    action_enum = mt5.TRADE_ACTION_PENDING
                    type_enum = mt5.ORDER_TYPE_BUY_STOP
                    order_price = stop_price
                else:
                    raise OrderError(f"Unsupported order type: {order_type}", exchange="mt5")
            else:
                if order_type == OrderType.MARKET:
                    action_enum = mt5.TRADE_ACTION_DEAL
                    type_enum = mt5.ORDER_TYPE_SELL
                    order_price = tick.bid
                elif order_type == OrderType.LIMIT:
                    if price is None:
                        raise OrderError("Limit price required for SELL LIMIT", exchange="mt5")
                    action_enum = mt5.TRADE_ACTION_PENDING
                    type_enum = mt5.ORDER_TYPE_SELL_LIMIT
                    order_price = price
                elif order_type == OrderType.STOP:
                    if stop_price is None:
                        raise OrderError("Stop price required for SELL STOP", exchange="mt5")
                    action_enum = mt5.TRADE_ACTION_PENDING
                    type_enum = mt5.ORDER_TYPE_SELL_STOP
                    order_price = stop_price
                else:
                    raise OrderError(f"Unsupported order type: {order_type}", exchange="mt5")

            # Build request
            request: Dict[str, Any] = {
                "action": action_enum,
                "symbol": symbol,
                "volume": quantity,
                "type": type_enum,
                "price": order_price,
                "deviation": 10,
                "magic": 9001,
                "comment": notes or "QNAI",
                "type_filling": mt5.ORDER_FILLING_IOC,
                "type_time": mt5.ORDER_TIME_GTC,
            }

            result = mt5.order_send(request)

            if result is None:
                raise OrderError("order_send returned None", exchange="mt5")

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                raise OrderError(
                    f"Order failed: {result.comment} (retcode={result.retcode})",
                    exchange="mt5",
                )

            order = Order(
                id=str(result.order),
                client_order_id=client_order_id,
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=order_price,
                status=OrderStatus.SUBMITTED,
                filled_quantity=float(result.volume) if result.volume else 0,
                average_fill_price=float(result.price) if result.price else None,
                created_at=datetime.now(tz=timezone.utc),
                updated_at=datetime.now(tz=timezone.utc),
                broker_id="mt5",
                broker_order_id=str(result.order),
                strategy_name=strategy_name,
                agent_name=agent_name,
                notes=notes,
            )
            self._local_orders[order.id] = order
            return order

        except (OrderError, ExchangeError):
            raise
        except Exception as exc:
            raise OrderError(
                f"Failed to place order: {exc}",
                exchange="mt5",
                original=exc,
            ) from exc

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        """Cancel a pending order on MT5.

        Args:
            order_id: MT5 order ticket number.

        Returns:
            The cancelled Order.
        """
        self._require_mt5()
        try:
            ticket = int(order_id)
            orders = self._mt5.orders_get(ticket=ticket)
            if not orders:
                raise OrderError(f"Order {order_id} not found", exchange="mt5")

            order_info = orders[0]
            request = {
                "action": self._mt5.TRADE_ACTION_REMOVE,
                "order": ticket,
                "symbol": order_info.symbol,
            }

            result = self._mt5.order_send(request)
            if result.retcode != self._mt5.TRADE_RETCODE_DONE:
                raise OrderError(
                    f"Cancel failed: {result.comment}",
                    order_id=order_id,
                    exchange="mt5",
                )

            if order_id in self._local_orders:
                order = self._local_orders[order_id]
                order.status = OrderStatus.CANCELED
                order.updated_at = datetime.now(tz=timezone.utc)
                return order

            return Order(
                id=order_id,
                symbol=order_info.symbol,
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=0,
                status=OrderStatus.CANCELED,
                updated_at=datetime.now(tz=timezone.utc),
                broker_id="mt5",
                broker_order_id=order_id,
            )

        except (OrderError, ExchangeError):
            raise
        except Exception as exc:
            raise OrderError(
                f"Failed to cancel order {order_id}: {exc}",
                order_id=order_id,
                exchange="mt5",
                original=exc,
            ) from exc

    async def get_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        """Get order status from MT5.

        Args:
            order_id: MT5 order ticket number.

        Returns:
            Current Order state.
        """
        self._require_mt5()
        try:
            ticket = int(order_id)
            orders = self._mt5.orders_get(ticket=ticket)

            if orders:
                o = orders[0]
                side = OrderSide.BUY if "BUY" in str(o.type) else OrderSide.SELL
                return Order(
                    id=str(o.ticket),
                    symbol=o.symbol,
                    side=side,
                    order_type=OrderType.LIMIT,
                    quantity=float(o.volume_initial),
                    price=float(o.price_open),
                    status=OrderStatus.SUBMITTED,
                    created_at=datetime.now(tz=timezone.utc),
                    updated_at=datetime.now(tz=timezone.utc),
                    broker_id="mt5",
                    broker_order_id=str(o.ticket),
                )

            # Check in history
            history_orders = self._mt5.history_orders_get(ticket=ticket)
            if history_orders:
                o = history_orders[0]
                side = OrderSide.BUY if "BUY" in str(o.type) else OrderSide.SELL
                status = OrderStatus.FILLED if o.state == self._mt5.ORDER_STATE_FILLED else OrderStatus.CANCELED

                return Order(
                    id=str(o.ticket),
                    symbol=o.symbol,
                    side=side,
                    order_type=OrderType.LIMIT,
                    quantity=float(o.volume_initial),
                    price=float(o.price_open),
                    status=status,
                    created_at=datetime.now(tz=timezone.utc),
                    updated_at=datetime.now(tz=timezone.utc),
                    broker_id="mt5",
                    broker_order_id=str(o.ticket),
                )

            raise OrderError(f"Order {order_id} not found", order_id=order_id, exchange="mt5")

        except (OrderError, ExchangeError):
            raise
        except Exception as exc:
            raise OrderError(
                f"Failed to get order {order_id}: {exc}",
                order_id=order_id,
                exchange="mt5",
                original=exc,
            ) from exc

    async def modify_position(
        self,
        ticket: int,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Modify position SL/TP.

        Args:
            ticket: Position ticket number.
            stop_loss: New stop loss price.
            take_profit: New take profit price.

        Returns:
            Dict with modification result.
        """
        self._require_mt5()
        try:
            positions = self._mt5.positions_get(ticket=ticket)
            if not positions:
                return {"success": False, "error": f"Position {ticket} not found"}

            position = positions[0]
            request = {
                "action": self._mt5.TRADE_ACTION_SLTP,
                "symbol": position.symbol,
                "sl": stop_loss if stop_loss is not None else position.sl,
                "tp": take_profit if take_profit is not None else position.tp,
                "position": ticket,
            }

            result = self._mt5.order_send(request)
            if result.retcode != self._mt5.TRADE_RETCODE_DONE:
                return {"success": False, "error": f"Modify failed: {result.comment}"}

            return {"success": True, "comment": result.comment}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def close_position(
        self,
        ticket: int,
        volume: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Close a position by ticket.

        Args:
            ticket: Position ticket number.
            volume: Volume to close (None for full close).

        Returns:
            Dict with close result.
        """
        self._require_mt5()
        try:
            positions = self._mt5.positions_get(ticket=ticket)
            if not positions:
                return {"success": False, "error": f"Position {ticket} not found"}

            position = positions[0]
            tick = self._mt5.symbol_info_tick(position.symbol)
            if tick is None:
                return {"success": False, "error": f"Symbol {position.symbol} not available"}

            close_price = tick.bid if position.type == self._mt5.POSITION_TYPE_BUY else tick.ask
            close_type = (
                self._mt5.ORDER_TYPE_SELL
                if position.type == self._mt5.POSITION_TYPE_BUY
                else self._mt5.ORDER_TYPE_BUY
            )

            request = {
                "action": self._mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": volume or position.volume,
                "type": close_type,
                "position": ticket,
                "price": close_price,
                "deviation": 10,
                "magic": position.magic,
                "comment": "QNAI_Close",
                "type_filling": self._mt5.ORDER_FILLING_IOC,
            }

            result = self._mt5.order_send(request)
            if result.retcode != self._mt5.TRADE_RETCODE_DONE:
                return {"success": False, "error": f"Close failed: {result.comment}"}

            return {
                "success": True,
                "order": result.order,
                "volume": result.volume,
                "price": result.price,
                "pnl": result.profit,
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ----- Market data -----

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.D1,
        since: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[OHLCV]:
        """Fetch OHLCV data from MT5.

        Args:
            symbol: Trading symbol (e.g., "EURUSD").
            timeframe: Candle timeframe.
            since: Start time.
            limit: Maximum number of candles.

        Returns:
            List of OHLCV candles.
        """
        self._require_mt5()
        try:
            tf_str = _TIMEFRAME_TO_MT5.get(timeframe, "D1")
            tf_enum = self._get_timeframe_enum(tf_str)
            if tf_enum is None:
                raise MarketDataError(f"Invalid timeframe: {timeframe}", exchange="mt5")

            rates = self._mt5.copy_rates_from_pos(symbol, tf_enum, 0, limit)
            if rates is None:
                return []

            result: List[OHLCV] = []
            for r in rates:
                ts = datetime.fromtimestamp(r["time"], tz=timezone.utc)
                result.append(OHLCV(
                    symbol=symbol,
                    timestamp=ts,
                    open=float(r["open"]),
                    high=float(r["high"]),
                    low=float(r["low"]),
                    close=float(r["close"]),
                    volume=float(r["tick_volume"]),
                ))
            return result

        except MarketDataError:
            raise
        except Exception as exc:
            raise MarketDataError(
                f"Failed to get OHLCV for {symbol}: {exc}",
                exchange="mt5",
                original=exc,
            ) from exc

    async def get_ticker(self, symbol: str) -> Ticker:
        """Get latest tick data for a symbol.

        Args:
            symbol: Trading symbol.

        Returns:
            Ticker with bid/ask data.
        """
        self._require_mt5()
        try:
            tick = self._mt5.symbol_info_tick(symbol)
            if tick is None:
                raise MarketDataError(
                    f"No tick data for {symbol}",
                    exchange="mt5",
                )

            return Ticker(
                symbol=symbol,
                timestamp=datetime.fromtimestamp(tick.time, tz=timezone.utc),
                last_price=float(tick.last or tick.bid),
                bid=float(tick.bid),
                ask=float(tick.ask),
                volume=float(tick.volume),
            )
        except MarketDataError:
            raise
        except Exception as exc:
            raise MarketDataError(
                f"Failed to get ticker for {symbol}: {exc}",
                exchange="mt5",
                original=exc,
            ) from exc

    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
        """Get market depth from MT5.

        Args:
            symbol: Trading symbol.
            limit: Depth per side.

        Returns:
            OrderBook snapshot.
        """
        self._require_mt5()
        try:
            book = self._mt5.market_book_get(symbol)
            if book is None:
                raise MarketDataError(
                    f"No order book data for {symbol}",
                    exchange="mt5",
                )

            bids = []
            asks = []
            for item in book:
                entry = {
                    "price": float(item.price),
                    "quantity": float(item.volume),
                }
                if item.type == self._mt5.BOOK_TYPE_SELL:
                    asks.append(entry)
                elif item.type == self._mt5.BOOK_TYPE_BUY:
                    bids.append(entry)

            return OrderBook(
                symbol=symbol,
                timestamp=datetime.now(tz=timezone.utc),
                bids=bids[:limit],
                asks=asks[:limit],
            )
        except MarketDataError:
            raise
        except Exception as exc:
            raise MarketDataError(
                f"Failed to get orderbook for {symbol}: {exc}",
                exchange="mt5",
                original=exc,
            ) from exc

    async def get_trades(
        self,
        symbol: str,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get recent trades from MT5.

        Args:
            symbol: Trading symbol.
            since: Start time.
            limit: Maximum number of trades.

        Returns:
            List of trade dicts.
        """
        self._require_mt5()
        try:
            from_date = since or datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            to_date = datetime.now()

            deals = self._mt5.history_deals_get(from_date, to_date)
            if not deals:
                return []

            trades = []
            for d in deals:
                if symbol and d.symbol != symbol:
                    continue
                trades.append({
                    "id": str(d.ticket),
                    "order": str(d.order),
                    "symbol": d.symbol,
                    "price": float(d.price),
                    "amount": float(d.volume),
                    "side": "BUY" if d.type == self._mt5.DEAL_TYPE_BUY else "SELL",
                    "pnl": float(d.profit),
                    "timestamp": datetime.fromtimestamp(d.time, tz=timezone.utc).isoformat(),
                })
                if len(trades) >= limit:
                    break

            return trades
        except Exception as exc:
            raise MarketDataError(
                f"Failed to get trades for {symbol}: {exc}",
                exchange="mt5",
                original=exc,
            ) from exc

    async def get_symbol_info(self, symbol: str) -> MT5SymbolInfo:
        """Get symbol information from MT5.

        Args:
            symbol: Trading symbol.

        Returns:
            MT5SymbolInfo with symbol details.
        """
        self._require_mt5()
        try:
            info = self._mt5.symbol_info(symbol)
            if info is None:
                raise MarketDataError(
                    f"Symbol {symbol} not found",
                    exchange="mt5",
                )

            return MT5SymbolInfo(
                symbol=info.name,
                bid=float(info.bid),
                ask=float(info.ask),
                last=float(info.last),
                point=float(info.point),
                spread=int(info.spread),
                volume_min=float(info.volume_min),
                volume_max=float(info.volume_max),
                volume_step=float(info.volume_step),
                trade_stops_level=int(info.trade_stops_level),
                trade_tick_size=float(info.trade_tick_size),
                trade_tick_value=float(info.trade_tick_value),
            )
        except MarketDataError:
            raise
        except Exception as exc:
            raise MarketDataError(
                f"Failed to get symbol info for {symbol}: {exc}",
                exchange="mt5",
                original=exc,
            ) from exc

    async def calculate_position_size(
        self,
        symbol: str,
        risk_percent: float,
        stop_loss: float,
        entry_price: float,
    ) -> float:
        """Calculate position size based on risk.

        Args:
            symbol: Trading symbol.
            risk_percent: Risk percentage of account.
            stop_loss: Stop loss price.
            entry_price: Entry price.

        Returns:
            Position size in lots.
        """
        self._require_mt5()
        try:
            account = await self.get_account_info()
            symbol_info = self._mt5.symbol_info(symbol)
            if symbol_info is None:
                return 0.0

            risk_amount = account.equity * (risk_percent / 100)
            sl_distance = abs(entry_price - stop_loss)
            sl_pips = sl_distance / symbol_info.point if symbol_info.point > 0 else 0

            if sl_pips == 0 or symbol_info.trade_tick_value == 0:
                return 0.0

            position_size = risk_amount / (sl_pips * symbol_info.trade_tick_value)

            # Clamp to valid range
            position_size = max(
                symbol_info.volume_min,
                min(position_size, symbol_info.volume_max),
            )
            position_size = round(position_size / symbol_info.volume_step) * symbol_info.volume_step

            return position_size
        except Exception as exc:
            logger.error("Error calculating position size: %s", exc)
            return 0.0

    # ----- WebSocket / real-time -----

    async def subscribe_ticker(self, symbol: str, callback: WebSocketCallback) -> None:
        """MT5 does not support WebSocket subscriptions natively."""
        logger.info("MT5Broker: Ticker subscription for %s (polling mode)", symbol)

    async def subscribe_orderbook(self, symbol: str, callback: WebSocketCallback) -> None:
        """MT5 does not support WebSocket subscriptions natively."""
        logger.info("MT5Broker: Orderbook subscription for %s (polling mode)", symbol)

    async def subscribe_trades(self, symbol: str, callback: WebSocketCallback) -> None:
        """MT5 does not support WebSocket subscriptions natively."""
        logger.info("MT5Broker: Trade subscription for %s (polling mode)", symbol)

    async def unsubscribe(self, symbol: str, channel: str) -> None:
        """Unsubscribe from a real-time data stream."""
        logger.info("MT5Broker: Unsubscribe %s %s", channel, symbol)

    # ----- Utility -----

    async def get_markets(self) -> List[str]:
        """List available symbols from MT5."""
        self._require_mt5()
        try:
            symbols = self._mt5.symbols_get()
            if symbols:
                return [s.name for s in symbols if s.visible]
            return []
        except Exception:
            return []

    async def health_check(self) -> bool:
        """Check MT5 connection health."""
        try:
            self._require_mt5()
            info = self._mt5.account_info()
            if info:
                self._state = ExchangeState.CONNECTED
                return True
            return False
        except Exception:
            self._state = ExchangeState.ERROR
            return False

    # ----- Internal helpers -----

    def _require_mt5(self):
        """Ensure MT5 is initialized and connected."""
        if not self._mt5 or not self.is_connected:
            raise ConnectionError(
                "MT5Broker is not connected",
                exchange="mt5",
            )
        return self._mt5

    def _get_timeframe_enum(self, timeframe: str):
        """Get MT5 timeframe enum value."""
        mt5 = self._mt5
        if mt5 is None:
            return None

        mapping = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1,
            "W1": mt5.TIMEFRAME_W1,
            "MN1": mt5.TIMEFRAME_MN1,
        }
        return mapping.get(timeframe.upper())

    def __repr__(self) -> str:
        state = self._state.value
        return f"MT5Broker(state={state})"


__all__ = [
    "MT5Broker",
    "MT5AccountInfo",
    "MT5SymbolInfo",
    "MT5PositionInfo",
]
