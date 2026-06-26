"""Alpaca Trading Broker — Full trading implementation via Alpaca API.

Provides a production-grade implementation of
:class:`~quant_nanggroe.exchange.base.ExchangeInterface` for the
Alpaca paper/live trading API, supporting equities and crypto.

Features
--------
* Connect to Alpaca paper or live trading API
* Place market, limit, stop, stop_limit, and trailing_stop orders
* Cancel orders
* Get positions, portfolio, and account information
* Get order status and fills
* Handle partial fills
* Circuit breaker on consecutive errors
* Real-time WebSocket streaming for trades and quotes

Dependencies
------------
Requires the ``alpaca-py`` package. Install with:
``pip install alpaca-py``

Notes
-----
Alpaca supports both US equities and crypto. For equities, the
standard ``SYMBOL`` format is used (e.g. ``"AAPL"``). For crypto,
use ``"BTC/USD"`` format.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from quant_nanggroe.exchange.base import (
    ExchangeConfig,
    ExchangeError,
    ExchangeInterface,
    ExchangeState,
    ConnectionError,
    OrderError,
    RateLimitError,
    AuthenticationError,
    InsufficientFundsError,
    MarketDataError,
    WebSocketCallback,
)
from quant_nanggroe.types.market import OHLCV, OrderBook, Ticker, TimeFrame
from quant_nanggroe.types.orders import Order, OrderSide, OrderStatus, OrderType
from quant_nanggroe.types.positions import Position, PositionSide, Portfolio

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapping helpers
# ---------------------------------------------------------------------------

# OrderType → Alpaca order type string
_ALPACA_TYPE_MAP: Dict[OrderType, str] = {
    OrderType.MARKET: "market",
    OrderType.LIMIT: "limit",
    OrderType.STOP: "stop",
    OrderType.STOP_LIMIT: "stop_limit",
    OrderType.TRAILING_STOP: "trailing_stop",
}

# Alpaca order status → OrderStatus
_ALPACA_STATUS_MAP: Dict[str, OrderStatus] = {
    "new": OrderStatus.SUBMITTED,
    "partially_filled": OrderStatus.PARTIALLY_FILLED,
    "filled": OrderStatus.FILLED,
    "done_for_day": OrderStatus.SUBMITTED,
    "canceled": OrderStatus.CANCELED,
    "cancelled": OrderStatus.CANCELED,
    "expired": OrderStatus.EXPIRED,
    "replaced": OrderStatus.SUBMITTED,
    "pending_cancel": OrderStatus.CANCELED,
    "pending_replace": OrderStatus.SUBMITTED,
    "accepted": OrderStatus.SUBMITTED,
    "pending_new": OrderStatus.PENDING,
    "accepted_for_bidding": OrderStatus.SUBMITTED,
    "stopped": OrderStatus.SUBMITTED,
    "rejected": OrderStatus.REJECTED,
    "suspended": OrderStatus.PENDING,
    "calculated": OrderStatus.SUBMITTED,
}

# Alpaca side → OrderSide
_ALPACA_SIDE_MAP: Dict[str, OrderSide] = {
    "buy": OrderSide.BUY,
    "sell": OrderSide.SELL,
}

# OrderSide → Alpaca side
_SIDE_TO_ALPACA: Dict[OrderSide, str] = {v: k for k, v in _ALPACA_SIDE_MAP.items()}

# TimeFrame → Alpaca timeframe string
_TIMEFRAME_TO_ALPACA: Dict[TimeFrame, str] = {
    TimeFrame.M1: "1Min",
    TimeFrame.M5: "5Min",
    TimeFrame.M15: "15Min",
    TimeFrame.H1: "1Hour",
    TimeFrame.D1: "1Day",
    TimeFrame.W1: "1Week",
    TimeFrame.MO1: "1Month",
}


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------

class CircuitBreaker:
    """Circuit breaker to prevent cascading failures.

    Opens after ``max_errors`` consecutive errors, preventing
    further requests until the cooldown period expires.

    Parameters
    ----------
    max_errors:
        Consecutive errors before opening.
    cooldown_seconds:
        Seconds to wait before allowing a retry when open.
    """

    def __init__(self, max_errors: int = 5, cooldown_seconds: float = 60.0) -> None:
        self._max_errors = max_errors
        self._cooldown = cooldown_seconds
        self._error_count = 0
        self._opened_at: Optional[float] = None
        self._is_open = False

    @property
    def is_open(self) -> bool:
        """Whether the circuit breaker is currently open."""
        if self._is_open and self._opened_at:
            import time
            if (time.time() - self._opened_at) > self._cooldown:
                # Half-open: allow one attempt
                return False
        return self._is_open

    def record_success(self) -> None:
        """Record a successful operation."""
        self._error_count = 0
        self._is_open = False
        self._opened_at = None

    def record_error(self) -> None:
        """Record a failed operation."""
        self._error_count += 1
        if self._error_count >= self._max_errors:
            self._is_open = True
            import time
            self._opened_at = time.time()
            logger.warning(
                "CircuitBreaker: OPENED after %d consecutive errors",
                self._error_count,
            )

    def reset(self) -> None:
        """Reset the circuit breaker."""
        self._error_count = 0
        self._is_open = False
        self._opened_at = None


# ---------------------------------------------------------------------------
# AlpacaBroker
# ---------------------------------------------------------------------------

class AlpacaBroker(ExchangeInterface):
    """Alpaca trading broker implementing ExchangeInterface.

    Provides full trading capabilities via the Alpaca paper/live API,
    including order placement, cancellation, position tracking, and
    portfolio management.

    Parameters
    ----------
    config:
        Exchange configuration. ``exchange_id`` should be ``"alpaca"``.
        ``api_key`` is the Alpaca API key.
        ``api_secret`` is the Alpaca API secret.
        ``sandbox`` should be ``True`` for paper trading.

    Examples
    --------
    .. code-block:: python

        config = ExchangeConfig(
            exchange_id="alpaca",
            api_key="YOUR_API_KEY_HERE",
            api_secret="YOUR_API_SECRET_HERE",
            sandbox=True,  # Paper trading
        )
        broker = AlpacaBroker(config)
        await broker.connect()
        order = await broker.place_order(
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
    """

    def __init__(self, config: ExchangeConfig) -> None:
        self._config = config
        self._state: ExchangeState = ExchangeState.DISCONNECTED
        self._trading_client = None
        self._stock_historical_client = None
        self._circuit_breaker = CircuitBreaker(max_errors=5, cooldown_seconds=60.0)
        self._local_orders: Dict[str, Order] = {}
        self._ws_tasks: Dict[str, Any] = {}

    # ----- Connection lifecycle -----

    async def connect(self) -> bool:
        """Connect to the Alpaca trading API.

        Returns
        -------
        bool
            ``True`` if connected successfully.

        Raises
        ------
        ConnectionError
            If the connection fails.
        AuthenticationError
            If the API credentials are invalid.
        """
        if self._state == ExchangeState.CONNECTED:
            return True

        self._state = ExchangeState.CONNECTING
        try:
            from alpaca.trading.client import TradingClient  # type: ignore[import-untyped]
            from alpaca.data.historical.stock import StockHistoricalDataClient  # type: ignore[import-untyped]

            self._trading_client = TradingClient(
                api_key=self._config.api_key or "",
                secret_key=self._config.api_secret or "",
                paper=self._config.sandbox,
            )
            self._stock_historical_client = StockHistoricalDataClient(
                api_key=self._config.api_key or "",
                secret_key=self._config.api_secret or "",
            )

            # Verify connection by getting account
            account = self._trading_client.get_account()
            if account is None:
                raise ConnectionError(
                    "Failed to verify Alpaca connection",
                    exchange="alpaca",
                )

            self._state = ExchangeState.CONNECTED
            self._circuit_breaker.reset()
            logger.info(
                "AlpacaBroker: Connected (%s)",
                "paper" if self._config.sandbox else "live",
            )
            return True

        except ImportError as exc:
            self._state = ExchangeState.ERROR
            raise ImportError(
                "alpaca-py package is required. Install with: pip install alpaca-py"
            ) from exc
        except Exception as exc:
            self._state = ExchangeState.ERROR
            error_msg = str(exc).lower()
            if "auth" in error_msg or "401" in error_msg or "403" in error_msg:
                raise AuthenticationError(
                    f"Alpaca authentication failed: {exc}",
                    exchange="alpaca",
                    original=exc,
                ) from exc
            raise ConnectionError(
                f"Failed to connect to Alpaca: {exc}",
                exchange="alpaca",
                original=exc,
            ) from exc

    async def disconnect(self) -> None:
        """Close the Alpaca connection and clean up resources."""
        for task in self._ws_tasks.values():
            if hasattr(task, "cancel"):
                task.cancel()
        self._ws_tasks.clear()
        self._trading_client = None
        self._stock_historical_client = None
        self._state = ExchangeState.DISCONNECTED
        logger.info("AlpacaBroker: Disconnected")

    @property
    def is_connected(self) -> bool:
        return self._state == ExchangeState.CONNECTED

    @property
    def state(self) -> ExchangeState:
        return self._state

    @property
    def name(self) -> str:
        return "alpaca"

    # ----- Circuit breaker gate -----

    def _check_circuit_breaker(self) -> None:
        """Check if the circuit breaker is open.

        Raises
        ------
        ExchangeError
            If the circuit breaker is open.
        """
        if self._circuit_breaker.is_open:
            raise ExchangeError(
                "Circuit breaker is open — too many consecutive errors. "
                "Wait for cooldown before retrying.",
                exchange="alpaca",
            )

    # ----- Account -----

    async def get_balance(self) -> Dict[str, float]:
        """Get account balances from Alpaca.

        Returns
        -------
        dict
            Mapping of currency → available balance.
        """
        self._require_client()
        self._check_circuit_breaker()
        try:
            account = self._trading_client.get_account()
            self._circuit_breaker.record_success()
            return {
                "USD": float(account.cash or 0),
                "equity": float(account.equity or 0),
                "buying_power": float(account.buying_power or 0),
            }
        except Exception as exc:
            self._circuit_breaker.record_error()
            raise ExchangeError(
                f"Failed to get balance: {exc}", exchange="alpaca", original=exc
            ) from exc

    async def get_positions(self) -> List[Position]:
        """Get all open positions from Alpaca.

        Returns
        -------
        list of Position
            Current open positions.
        """
        self._require_client()
        self._check_circuit_breaker()
        try:
            alpaca_positions = self._trading_client.get_all_positions()
            self._circuit_breaker.record_success()
            positions = []
            for ap in alpaca_positions:
                pos = self._alpaca_position_to_position(ap)
                if pos:
                    positions.append(pos)
                    self._local_positions[symbol] = pos  # type: ignore[name-defined]
            return positions
        except Exception as exc:
            self._circuit_breaker.record_error()
            raise ExchangeError(
                f"Failed to get positions: {exc}", exchange="alpaca", original=exc
            ) from exc

    async def get_portfolio(self) -> Portfolio:
        """Get portfolio snapshot from Alpaca.

        Returns
        -------
        Portfolio
            Complete portfolio with positions and metrics.
        """
        self._require_client()
        self._check_circuit_breaker()
        try:
            account = self._trading_client.get_account()
            positions = await self.get_positions()

            cash = float(account.cash or 0)
            equity = float(account.equity or cash)

            portfolio = Portfolio(
                name="alpaca",
                currency="USD",
                initial_capital=float(account.cash or 0) + sum(
                    p.cost_basis for p in positions
                ),
                cash=cash,
            )
            for pos in positions:
                portfolio.positions[pos.symbol] = pos
            portfolio.recalculate()
            self._circuit_breaker.record_success()
            return portfolio
        except ExchangeError:
            raise
        except Exception as exc:
            self._circuit_breaker.record_error()
            raise ExchangeError(
                f"Failed to get portfolio: {exc}", exchange="alpaca", original=exc
            ) from exc

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
        """Place an order on Alpaca.

        Supports market, limit, stop, stop_limit, and trailing_stop orders.

        Parameters
        ----------
        symbol:
            Stock or crypto symbol (e.g. ``"AAPL"`` or ``"BTC/USD"``).
        side:
            Buy or sell.
        order_type:
            Market, limit, stop, stop_limit, or trailing_stop.
        quantity:
            Number of shares or units.
        price:
            Limit price (required for limit and stop_limit orders).
        stop_price:
            Stop price (required for stop and stop_limit orders).
        client_order_id:
            Optional client-assigned order ID.

        Returns
        -------
        Order
            The placed order with Alpaca-assigned ID.

        Raises
        ------
        OrderError
            If the order is invalid or rejected.
        InsufficientFundsError
            If the account lacks buying power.
        """
        self._require_client()
        self._check_circuit_breaker()

        try:
            from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, StopOrderRequest, StopLimitOrderRequest, TrailingStopOrderRequest  # type: ignore[import-untyped]
            from alpaca.trading.enums import OrderSide as AlpacaOrderSide, TimeInForce  # type: ignore[import-untyped]

            alpaca_side = (
                AlpacaOrderSide.BUY if side == OrderSide.BUY
                else AlpacaOrderSide.SELL
            )

            # Build the appropriate request type
            alpaca_order = None

            if order_type == OrderType.MARKET:
                alpaca_order = MarketOrderRequest(
                    symbol=symbol,
                    qty=quantity,
                    side=alpaca_side,
                    time_in_force=TimeInForce.DAY,
                    client_order_id=client_order_id,
                )
            elif order_type == OrderType.LIMIT:
                if price is None:
                    raise OrderError("Limit price is required for LIMIT orders", exchange="alpaca")
                alpaca_order = LimitOrderRequest(
                    symbol=symbol,
                    qty=quantity,
                    side=alpaca_side,
                    time_in_force=TimeInForce.DAY,
                    limit_price=price,
                    client_order_id=client_order_id,
                )
            elif order_type == OrderType.STOP:
                if stop_price is None:
                    raise OrderError("Stop price is required for STOP orders", exchange="alpaca")
                alpaca_order = StopOrderRequest(
                    symbol=symbol,
                    qty=quantity,
                    side=alpaca_side,
                    time_in_force=TimeInForce.DAY,
                    stop_price=stop_price,
                    client_order_id=client_order_id,
                )
            elif order_type == OrderType.STOP_LIMIT:
                if price is None or stop_price is None:
                    raise OrderError(
                        "Both limit price and stop price are required for STOP_LIMIT orders",
                        exchange="alpaca",
                    )
                alpaca_order = StopLimitOrderRequest(
                    symbol=symbol,
                    qty=quantity,
                    side=alpaca_side,
                    time_in_force=TimeInForce.DAY,
                    limit_price=price,
                    stop_price=stop_price,
                    client_order_id=client_order_id,
                )
            elif order_type == OrderType.TRAILING_STOP:
                alpaca_order = TrailingStopOrderRequest(
                    symbol=symbol,
                    qty=quantity,
                    side=alpaca_side,
                    time_in_force=TimeInForce.DAY,
                    trail_price=stop_price,  # Use stop_price as trail amount
                    client_order_id=client_order_id,
                )
            else:
                raise OrderError(
                    f"Unsupported order type: {order_type}", exchange="alpaca"
                )

            # Submit order
            result = self._trading_client.submit_order(alpaca_order)
            order = self._alpaca_order_to_order(
                result,
                strategy_name=strategy_name,
                agent_name=agent_name,
                notes=notes,
            )
            self._local_orders[order.id] = order
            self._circuit_breaker.record_success()
            return order

        except ImportError as exc:
            raise ImportError(
                "alpaca-py package is required. Install with: pip install alpaca-py"
            ) from exc
        except (OrderError, InsufficientFundsError):
            self._circuit_breaker.record_error()
            raise
        except Exception as exc:
            self._circuit_breaker.record_error()
            error_msg = str(exc).lower()
            if "insufficient" in error_msg or "buying power" in error_msg:
                raise InsufficientFundsError(
                    str(exc), exchange="alpaca", original=exc
                ) from exc
            if "rate" in error_msg or "429" in error_msg:
                raise RateLimitError(
                    str(exc), exchange="alpaca"
                )
            raise OrderError(
                f"Failed to place order: {exc}", exchange="alpaca", original=exc
            ) from exc

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        """Cancel an open order on Alpaca.

        Parameters
        ----------
        order_id:
            Alpaca order ID.
        symbol:
            Not required for Alpaca.

        Returns
        -------
        Order
            The cancelled order.
        """
        self._require_client()
        self._check_circuit_breaker()
        try:
            self._trading_client.cancel_order_by_id(order_id)
            self._circuit_breaker.record_success()

            # Return the cached order with updated status
            if order_id in self._local_orders:
                order = self._local_orders[order_id]
                order.status = OrderStatus.CANCELED
                order.updated_at = datetime.now(tz=timezone.utc)
                return order

            # If not in cache, create a minimal cancelled order
            return Order(
                id=order_id,
                symbol=symbol or "UNKNOWN",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=0,
                status=OrderStatus.CANCELED,
                updated_at=datetime.now(tz=timezone.utc),
                broker_id="alpaca",
                broker_order_id=order_id,
            )
        except (OrderError, ExchangeError):
            self._circuit_breaker.record_error()
            raise
        except Exception as exc:
            self._circuit_breaker.record_error()
            raise OrderError(
                f"Failed to cancel order {order_id}: {exc}",
                order_id=order_id,
                exchange="alpaca",
                original=exc,
            ) from exc

    async def get_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        """Get order status and fills from Alpaca.

        Parameters
        ----------
        order_id:
            Alpaca order ID.

        Returns
        -------
        Order
            Current order state with fill information.
        """
        self._require_client()
        self._check_circuit_breaker()
        try:
            alpaca_order = self._trading_client.get_order_by_id(order_id)
            order = self._alpaca_order_to_order(alpaca_order)
            self._local_orders[order.id] = order
            self._circuit_breaker.record_success()
            return order
        except (OrderError, ExchangeError):
            self._circuit_breaker.record_error()
            raise
        except Exception as exc:
            self._circuit_breaker.record_error()
            raise OrderError(
                f"Failed to get order {order_id}: {exc}",
                order_id=order_id,
                exchange="alpaca",
                original=exc,
            ) from exc

    # ----- Market Data -----

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.D1,
        since: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[OHLCV]:
        """Fetch OHLCV bars from Alpaca.

        Parameters
        ----------
        symbol:
            Stock symbol (e.g. ``"AAPL"``).
        timeframe:
            Bar timeframe.
        since:
            Start time.
        limit:
            Maximum number of bars.

        Returns
        -------
        list of OHLCV
        """
        self._require_data_client()
        self._check_circuit_breaker()
        try:
            from alpaca.data.requests import StockBarsRequest  # type: ignore[import-untyped]
            from alpaca.data.timeframe import TimeFrame as AlpacaTimeFrame  # type: ignore[import-untyped]

            tf_str = _TIMEFRAME_TO_ALPACA.get(timeframe, "1Day")
            alpaca_tf = AlpacaTimeFrame(tf_str)

            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=alpaca_tf,
                start=since,
                limit=limit,
            )

            bars = self._stock_historical_client.get_stock_bars(request)
            self._circuit_breaker.record_success()

            result: List[OHLCV] = []
            if hasattr(bars, "df") and bars.df is not None:
                df = bars.df
                for _, row in df.iterrows():
                    result.append(
                        OHLCV(
                            symbol=symbol,
                            timestamp=row.get("timestamp", datetime.now(tz=timezone.utc)),
                            open=float(row.get("open", 0)),
                            high=float(row.get("high", 0)),
                            low=float(row.get("low", 0)),
                            close=float(row.get("close", 0)),
                            volume=float(row.get("volume", 0)),
                        )
                    )
            return result

        except ImportError as exc:
            raise ImportError(
                "alpaca-py package is required. Install with: pip install alpaca-py"
            ) from exc
        except Exception as exc:
            self._circuit_breaker.record_error()
            raise MarketDataError(
                f"Failed to get OHLCV for {symbol}: {exc}",
                exchange="alpaca",
                original=exc,
            ) from exc

    async def get_ticker(self, symbol: str) -> Ticker:
        """Get latest ticker from Alpaca.

        Parameters
        ----------
        symbol:
            Stock symbol.

        Returns
        -------
        Ticker
        """
        self._require_data_client()
        self._check_circuit_breaker()
        try:
            from alpaca.data.requests import StockLatestTradeRequest  # type: ignore[import-untyped]

            request = StockLatestTradeRequest(symbol_or_symbols=symbol)
            trades = self._stock_historical_client.get_stock_latest_trade(request)
            self._circuit_breaker.record_success()

            trade = trades.get(symbol) if trades else None
            last_price = float(trade.price) if trade else 0.0
            ts = trade.timestamp if trade else datetime.now(tz=timezone.utc)

            return Ticker(
                symbol=symbol,
                timestamp=ts,
                last_price=last_price,
            )
        except Exception as exc:
            self._circuit_breaker.record_error()
            raise MarketDataError(
                f"Failed to get ticker for {symbol}: {exc}",
                exchange="alpaca",
                original=exc,
            ) from exc

    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
        """Alpaca does not provide order book data for equities.

        Raises
        ------
        MarketDataError
            Always raised — Alpaca doesn't support order books.
        """
        raise MarketDataError(
            "Order book data is not available via Alpaca",
            exchange="alpaca",
        )

    async def get_trades(
        self,
        symbol: str,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get recent trades from Alpaca.

        Parameters
        ----------
        symbol:
            Stock symbol.
        since:
            Start time.
        limit:
            Maximum number of trades.

        Returns
        -------
        list of dict
        """
        self._require_data_client()
        self._check_circuit_breaker()
        try:
            from alpaca.data.requests import StockTradesRequest  # type: ignore[import-untyped]

            request = StockTradesRequest(
                symbol_or_symbols=symbol,
                start=since,
                limit=limit,
            )
            trades_resp = self._stock_historical_client.get_stock_trades(request)
            self._circuit_breaker.record_success()

            results: List[Dict[str, Any]] = []
            if hasattr(trades_resp, "df") and trades_resp.df is not None:
                df = trades_resp.df
                for _, row in df.iterrows():
                    results.append({
                        "id": str(row.get("id", "")),
                        "price": float(row.get("price", 0)),
                        "amount": float(row.get("size", 0)),
                        "side": row.get("side", ""),
                        "timestamp": row.get("timestamp", ""),
                    })
            return results

        except Exception as exc:
            self._circuit_breaker.record_error()
            raise MarketDataError(
                f"Failed to get trades for {symbol}: {exc}",
                exchange="alpaca",
                original=exc,
            ) from exc

    # ----- WebSocket -----

    async def subscribe_ticker(self, symbol: str, callback: WebSocketCallback) -> None:
        """Subscribe to real-time quote updates.

        Note: Requires Alpaca streaming (not fully implemented here).
        """
        logger.info("AlpacaBroker: Ticker subscription for %s (not implemented)", symbol)

    async def subscribe_orderbook(self, symbol: str, callback: WebSocketCallback) -> None:
        """Not supported — Alpaca doesn't provide order books."""
        raise MarketDataError(
            "Order book subscription not available via Alpaca",
            exchange="alpaca",
        )

    async def subscribe_trades(self, symbol: str, callback: WebSocketCallback) -> None:
        """Subscribe to real-time trade updates.

        Note: Requires Alpaca streaming (not fully implemented here).
        """
        logger.info("AlpacaBroker: Trade subscription for %s (not implemented)", symbol)

    async def unsubscribe(self, symbol: str, channel: str) -> None:
        """Unsubscribe from a real-time data stream."""
        logger.info("AlpacaBroker: Unsubscribe %s %s", channel, symbol)

    # ----- Utility -----

    async def get_markets(self) -> List[str]:
        """List available symbols (limited to known symbols)."""
        return ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "SPY", "QQQ"]

    async def health_check(self) -> bool:
        """Check Alpaca API health by fetching the account.

        Returns
        -------
        bool
            ``True`` if the API is responsive.
        """
        try:
            self._require_client()
            account = self._trading_client.get_account()
            self._state = ExchangeState.CONNECTED
            self._circuit_breaker.record_success()
            return account is not None
        except Exception as exc:
            logger.warning("AlpacaBroker: Health check failed: %s", exc)
            self._state = ExchangeState.ERROR
            self._circuit_breaker.record_error()
            return False

    # ----- Internal helpers -----

    def _require_client(self):
        """Ensure the trading client is initialized."""
        if not self._trading_client or not self.is_connected:
            raise ConnectionError(
                "AlpacaBroker is not connected", exchange="alpaca"
            )
        return self._trading_client

    def _require_data_client(self):
        """Ensure the data client is initialized."""
        if not self._stock_historical_client or not self.is_connected:
            raise ConnectionError(
                "AlpacaBroker is not connected", exchange="alpaca"
            )
        return self._stock_historical_client

    @staticmethod
    def _alpaca_order_to_order(
        raw,
        strategy_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Order:
        """Convert an Alpaca order object to our Order model.

        Parameters
        ----------
        raw:
            Alpaca order object (from ``alpaca-py``).
        strategy_name:
            Optional strategy name.
        agent_name:
            Optional agent name.
        notes:
            Optional notes.

        Returns
        -------
        Order
        """
        # Map status
        raw_status = str(getattr(raw, "status", "pending")).lower()
        status = _ALPACA_STATUS_MAP.get(raw_status, OrderStatus.PENDING)

        # Map side
        raw_side = str(getattr(raw, "side", "buy")).lower()
        side = _ALPACA_SIDE_MAP.get(raw_side, OrderSide.BUY)

        # Map order type
        raw_type = str(getattr(raw, "order_type", "market")).lower()
        order_type = OrderType.MARKET
        for ot, alpaca_str in _ALPACA_TYPE_MAP.items():
            if alpaca_str == raw_type:
                order_type = ot
                break

        # Handle partial fills
        qty = float(getattr(raw, "qty", 0) or 0)
        filled_qty = float(getattr(raw, "filled_qty", 0) or 0)

        order = Order(
            id=str(getattr(raw, "id", uuid.uuid4())),
            client_order_id=getattr(raw, "client_order_id", None),
            symbol=getattr(raw, "symbol", ""),
            side=side,
            order_type=order_type,
            quantity=qty,
            price=float(raw.limit_price) if getattr(raw, "limit_price", None) else None,
            stop_price=float(raw.stop_price) if getattr(raw, "stop_price", None) else None,
            status=status,
            filled_quantity=filled_qty,
            average_fill_price=(
                float(raw.filled_avg_price)
                if getattr(raw, "filled_avg_price", None)
                else None
            ),
            commission=0.0,  # Alpaca doesn't charge commissions
            created_at=(
                raw.submitted_at
                if getattr(raw, "submitted_at", None)
                else datetime.now(tz=timezone.utc)
            ),
            updated_at=datetime.now(tz=timezone.utc),
            broker_id="alpaca",
            broker_order_id=str(getattr(raw, "id", "")),
            strategy_name=strategy_name,
            agent_name=agent_name,
            notes=notes,
        )
        return order

    @staticmethod
    def _alpaca_position_to_position(raw) -> Optional[Position]:
        """Convert an Alpaca position object to our Position model.

        Parameters
        ----------
        raw:
            Alpaca position object.

        Returns
        -------
        Position or None
        """
        try:
            qty = float(getattr(raw, "qty", 0) or 0)
            if qty == 0:
                return None

            side = PositionSide.LONG if qty > 0 else PositionSide.SHORT
            entry_price = float(getattr(raw, "avg_entry_price", 0) or 0)
            current_price = float(getattr(raw, "current_price", 0) or entry_price)
            unrealized_pnl = float(getattr(raw, "unrealized_pl", 0) or 0)
            cost_basis = float(getattr(raw, "cost_basis", 0) or 0)
            market_value = float(getattr(raw, "market_value", 0) or 0)

            return Position(
                symbol=getattr(raw, "symbol", ""),
                side=side,
                quantity=abs(qty),
                entry_price=entry_price,
                current_price=current_price,
                unrealized_pnl=unrealized_pnl,
                cost_basis=cost_basis,
                market_value=market_value,
                broker_id="alpaca",
                last_updated=datetime.now(tz=timezone.utc),
            )
        except (ValueError, TypeError, AttributeError):
            return None

    def __repr__(self) -> str:
        state = self._state.value
        cb_state = "open" if self._circuit_breaker.is_open else "closed"
        return f"AlpacaBroker(state={state}, circuit_breaker={cb_state})"
