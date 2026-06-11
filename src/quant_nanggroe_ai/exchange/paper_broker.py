"""Paper Trading Exchange Broker — Simulated execution with realistic fills.

Implements :class:`~quant_nanggroe_ai.exchange.base.ExchangeInterface` for
paper trading, extending the concepts from the existing
``engine/execution/brokers/paper.py`` with full market-data simulation
and P&L tracking.

Features
--------
* Market, limit, stop, and stop-limit order simulation.
* Configurable slippage (basis points) and commission (percentage or fixed).
* Partial fills and order rejections (insufficient capital, invalid price).
* Simulated OHLCV, ticker, order book, and trade data.
* Local position book with real-time P&L and drawdown tracking.
* WebSocket-like callback dispatch for real-time data simulation.
* Portfolio sync with full snapshot generation.
"""

from __future__ import annotations

import asyncio
import logging
import random
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from quant_nanggroe_ai.exchange.base import (
    ExchangeConfig,
    ExchangeError,
    ExchangeInterface,
    ExchangeState,
    InsufficientFundsError,
    MarketDataError,
    OrderError,
    WebSocketCallback,
)
from quant_nanggroe_ai.types.market import (
    OHLCV,
    OrderBook,
    OrderBookLevel,
    Ticker,
    TimeFrame,
)
from quant_nanggroe_ai.types.orders import Order, OrderSide, OrderStatus, OrderType
from quant_nanggroe_ai.types.positions import Position, PositionSide, Portfolio

logger = logging.getLogger(__name__)


class PaperExchangeBroker(ExchangeInterface):
    """Paper trading exchange broker with realistic simulation.

    Simulates a full exchange with order execution, market data generation,
    position tracking, and portfolio management.  Designed for backtesting,
    strategy development, and integration testing.

    Parameters
    ----------
    initial_capital:
        Starting cash balance in quote currency.
    commission_rate:
        Commission as a fraction of trade value (e.g. 0.001 = 0.1%).
    slippage_bps:
        Slippage in basis points (e.g. 5 = 0.05%).
    min_commission:
        Minimum commission per trade.
    default_price:
        Default price for symbols that have not been explicitly set.

    Examples
    --------
    .. code-block:: python

        broker = PaperExchangeBroker(initial_capital=100_000)
        await broker.connect()
        broker.set_price("BTC/USDT", 42000.0)

        order = await broker.place_order(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.5,
        )
        assert order.status == OrderStatus.FILLED
    """

    def __init__(
        self,
        initial_capital: float = 1_000_000.0,
        commission_rate: float = 0.001,
        slippage_bps: float = 5.0,
        min_commission: float = 1.0,
        default_price: float = 100.0,
    ) -> None:
        self._initial_capital = initial_capital
        self._cash = initial_capital
        self._commission_rate = commission_rate
        self._slippage_bps = slippage_bps
        self._min_commission = min_commission
        self._default_price = default_price

        self._state: ExchangeState = ExchangeState.DISCONNECTED
        self._connected: bool = False

        # Price simulation
        self._prices: Dict[str, float] = {}
        self._tickers: Dict[str, Ticker] = {}

        # Order tracking
        self._orders: Dict[str, Order] = {}
        self._pending_orders: Dict[str, Order] = {}

        # Position tracking
        self._positions: Dict[str, Position] = {}

        # Realized P&L
        self._realized_pnl: float = 0.0
        self._total_commission: float = 0.0
        self._total_slippage: float = 0.0

        # Trade history for get_trades()
        self._trade_history: List[Dict[str, Any]] = []

        # OHLCV history
        self._ohlcv_history: Dict[str, List[OHLCV]] = {}

        # WebSocket simulation
        self._ws_callbacks: Dict[str, Dict[str, WebSocketCallback]] = {}
        self._ws_tasks: Dict[str, asyncio.Task] = {}

        # Configuration-compatible interface
        self._config = ExchangeConfig(exchange_id="paper")

    # ------------------------------------------------------------------ #
    # Connection lifecycle
    # ------------------------------------------------------------------ #

    async def connect(self) -> bool:
        """Connect the paper broker (always succeeds)."""
        self._connected = True
        self._state = ExchangeState.CONNECTED
        logger.info("PaperExchangeBroker: Connected (simulated)")
        return True

    async def disconnect(self) -> None:
        """Disconnect and clean up all WebSocket tasks."""
        for task in self._ws_tasks.values():
            task.cancel()
        self._ws_tasks.clear()
        self._ws_callbacks.clear()
        self._connected = False
        self._state = ExchangeState.DISCONNECTED
        logger.info("PaperExchangeBroker: Disconnected")

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def state(self) -> ExchangeState:
        return self._state

    @property
    def name(self) -> str:
        return "paper"

    # ------------------------------------------------------------------ #
    # Price simulation helpers
    # ------------------------------------------------------------------ #

    def set_price(self, symbol: str, price: float) -> None:
        """Set the simulated market price for a symbol.

        Also updates all positions tracking that symbol.

        Args:
            symbol: Trading pair (e.g. ``"BTC/USDT"``).
            price: New market price.
        """
        if price <= 0:
            raise ValueError(f"Price must be positive, got {price}")
        self._prices[symbol] = price

        # Update ticker
        prev_price = self._tickers.get(symbol, None)
        self._tickers[symbol] = Ticker(
            symbol=symbol,
            timestamp=datetime.now(tz=timezone.utc),
            last_price=price,
            bid=price * 0.9999,
            ask=price * 1.0001,
            high_24h=max(price, prev_price.high_24h) if prev_price else price,
            low_24h=min(price, prev_price.low_24h) if prev_price and prev_price.low_24h else price,
            volume_24h=prev_price.volume_24h if prev_price else 0.0,
        )

        # Update positions
        if symbol in self._positions:
            self._positions[symbol].update_price(price)

    def get_price(self, symbol: str) -> float:
        """Get the current simulated price for a symbol."""
        return self._prices.get(symbol, self._default_price)

    def add_ohlcv(self, symbol: str, candle: OHLCV) -> None:
        """Add an OHLCV candle to the simulated history."""
        if symbol not in self._ohlcv_history:
            self._ohlcv_history[symbol] = []
        self._ohlcv_history[symbol].append(candle)
        # Also update the current price from the candle's close
        self.set_price(symbol, candle.close)

    # ------------------------------------------------------------------ #
    # Account
    # ------------------------------------------------------------------ #

    async def get_balance(self) -> Dict[str, float]:
        """Return the simulated account balances."""
        balances: Dict[str, float] = {}

        # Infer quote currency from position symbols
        quote_currencies = set()
        for symbol in self._positions:
            parts = symbol.split("/")
            if len(parts) == 2:
                quote_currencies.add(parts[1])
        if not quote_currencies:
            quote_currencies.add("USDT")

        for qc in quote_currencies:
            balances[qc] = self._cash

        # Add base currency positions
        for symbol, pos in self._positions.items():
            parts = symbol.split("/")
            if len(parts) == 2:
                base = parts[0]
                balances[base] = balances.get(base, 0.0) + pos.quantity

        return balances

    async def get_positions(self) -> List[Position]:
        """Return all open positions."""
        return list(self._positions.values())

    async def get_portfolio(self) -> Portfolio:
        """Build a full portfolio snapshot."""
        portfolio = Portfolio(
            name="paper",
            currency="USDT",
            initial_capital=self._initial_capital,
            cash=self._cash,
            total_realized_pnl=self._realized_pnl,
        )
        for symbol, pos in self._positions.items():
            portfolio.positions[symbol] = pos
        portfolio.recalculate()
        return portfolio

    # ------------------------------------------------------------------ #
    # Trading
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
        """Place an order and simulate execution.

        Market orders are filled immediately with slippage.
        Limit orders are filled if the price crosses the limit, or left pending.
        Stop orders are converted to market orders when the stop price is hit.
        """
        if not self._connected:
            raise OrderError("Not connected", exchange=self.name)

        current_price = self._prices.get(symbol, self._default_price)
        if current_price <= 0:
            raise OrderError(
                f"No price data available for {symbol}",
                exchange=self.name,
            )

        order_id = str(uuid.uuid4())
        order = Order(
            id=order_id,
            client_order_id=client_order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            status=OrderStatus.PENDING,
            broker_id=self.name,
            strategy_name=strategy_name,
            agent_name=agent_name,
            notes=notes,
            created_at=datetime.now(tz=timezone.utc),
        )
        self._orders[order_id] = order

        # Execute based on order type
        if order_type == OrderType.MARKET:
            order = await self._execute_market_order(order, current_price)
        elif order_type == OrderType.LIMIT:
            order = await self._execute_limit_order(order, current_price)
        elif order_type == OrderType.STOP:
            order = await self._execute_stop_order(order, current_price)
        elif order_type == OrderType.STOP_LIMIT:
            order = await self._execute_stop_limit_order(order, current_price)
        else:
            # Default: treat as market order
            order = await self._execute_market_order(order, current_price)

        self._orders[order_id] = order
        return order

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        """Cancel a pending order."""
        order = self._orders.get(order_id)
        if order is None:
            raise OrderError(f"Order {order_id} not found", order_id=order_id, exchange=self.name)

        if order.status not in (OrderStatus.PENDING, OrderStatus.SUBMITTED):
            raise OrderError(
                f"Cannot cancel order {order_id} with status {order.status.value}",
                order_id=order_id,
                exchange=self.name,
            )

        order.status = OrderStatus.CANCELED
        order.updated_at = datetime.now(tz=timezone.utc)
        self._pending_orders.pop(order_id, None)
        self._orders[order_id] = order
        return order

    async def get_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        """Retrieve an order by ID."""
        order = self._orders.get(order_id)
        if order is None:
            raise OrderError(f"Order {order_id} not found", order_id=order_id, exchange=self.name)
        return order

    # ------------------------------------------------------------------ #
    # Market data (simulated)
    # ------------------------------------------------------------------ #

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.D1,
        since: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[OHLCV]:
        """Return stored OHLCV history, or generate synthetic data."""
        history = self._ohlcv_history.get(symbol, [])
        if since:
            history = [c for c in history if c.timestamp >= since]
        return history[-limit:]

    async def get_ticker(self, symbol: str) -> Ticker:
        """Return the current simulated ticker."""
        if symbol in self._tickers:
            return self._tickers[symbol]
        price = self._prices.get(symbol, self._default_price)
        return Ticker(
            symbol=symbol,
            timestamp=datetime.now(tz=timezone.utc),
            last_price=price,
            bid=price * 0.9999,
            ask=price * 1.0001,
        )

    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
        """Generate a synthetic order book from the current price."""
        price = self._prices.get(symbol, self._default_price)
        # Simulate order book with decreasing quantity away from mid
        bids = []
        asks = []
        for i in range(limit):
            bid_price = price * (1 - (i + 1) * 0.0002)
            ask_price = price * (1 + (i + 1) * 0.0002)
            # Random quantity, decreasing with distance
            bid_qty = random.uniform(0.1, 10.0) * (1.0 / (i + 1))
            ask_qty = random.uniform(0.1, 10.0) * (1.0 / (i + 1))
            bids.append(OrderBookLevel(price=round(bid_price, 2), quantity=round(bid_qty, 4)))
            asks.append(OrderBookLevel(price=round(ask_price, 2), quantity=round(ask_qty, 4)))

        spread = asks[0].price - bids[0].price if bids and asks else None
        mid_price = (bids[0].price + asks[0].price) / 2 if bids and asks else price

        return OrderBook(
            symbol=symbol,
            timestamp=datetime.now(tz=timezone.utc),
            bids=bids,
            asks=asks,
            spread=spread,
            mid_price=mid_price,
        )

    async def get_trades(
        self,
        symbol: str,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Return the simulated trade history."""
        trades = self._trade_history
        if since:
            trades = [t for t in trades if t.get("symbol") == symbol]
        symbol_trades = [t for t in trades if t.get("symbol") == symbol]
        return symbol_trades[-limit:]

    # ------------------------------------------------------------------ #
    # WebSocket / real-time simulation
    # ------------------------------------------------------------------ #

    async def subscribe_ticker(self, symbol: str, callback: WebSocketCallback) -> None:
        """Subscribe to simulated ticker updates."""
        key = f"ticker:{symbol}"
        self._ws_callbacks.setdefault(key, {})[symbol] = callback
        logger.info("PaperExchangeBroker: Subscribed to ticker %s", symbol)

    async def subscribe_orderbook(self, symbol: str, callback: WebSocketCallback) -> None:
        """Subscribe to simulated order book updates."""
        key = f"orderbook:{symbol}"
        self._ws_callbacks.setdefault(key, {})[symbol] = callback
        logger.info("PaperExchangeBroker: Subscribed to orderbook %s", symbol)

    async def subscribe_trades(self, symbol: str, callback: WebSocketCallback) -> None:
        """Subscribe to simulated trade updates."""
        key = f"trades:{symbol}"
        self._ws_callbacks.setdefault(key, {})[symbol] = callback
        logger.info("PaperExchangeBroker: Subscribed to trades %s", symbol)

    async def unsubscribe(self, symbol: str, channel: str) -> None:
        """Unsubscribe from a simulated data stream."""
        key = f"{channel}:{symbol}"
        task = self._ws_tasks.pop(key, None)
        if task and not task.done():
            task.cancel()
        self._ws_callbacks.pop(key, None)
        logger.info("PaperExchangeBroker: Unsubscribed from %s %s", channel, symbol)

    async def emit_ticker(self, symbol: str) -> None:
        """Manually emit a ticker update to all subscribers.

        Useful for testing: call this after :meth:`set_price` to trigger
        callback invocation.
        """
        key = f"ticker:{symbol}"
        callbacks = self._ws_callbacks.get(key, {})
        ticker = await self.get_ticker(symbol)
        for cb in callbacks.values():
            try:
                await cb(ticker.model_dump())
            except Exception as exc:
                logger.warning("PaperExchangeBroker: Ticker callback error: %s", exc)

    async def emit_orderbook(self, symbol: str) -> None:
        """Manually emit an order book update to all subscribers."""
        key = f"orderbook:{symbol}"
        callbacks = self._ws_callbacks.get(key, {})
        ob = await self.get_orderbook(symbol)
        for cb in callbacks.values():
            try:
                await cb(ob.model_dump())
            except Exception as exc:
                logger.warning("PaperExchangeBroker: OrderBook callback error: %s", exc)

    # ------------------------------------------------------------------ #
    # Utility
    # ------------------------------------------------------------------ #

    async def get_markets(self) -> List[str]:
        """List all symbols with price data set."""
        return list(self._prices.keys())

    async def health_check(self) -> bool:
        """Paper broker is always healthy when connected."""
        return self._connected

    # ------------------------------------------------------------------ #
    # Order execution internals
    # ------------------------------------------------------------------ #

    async def _execute_market_order(self, order: Order, current_price: float) -> Order:
        """Execute a market order with slippage and commission."""
        exec_price = self._apply_slippage(current_price, order.side)
        commission = max(
            self._min_commission,
            self._commission_rate * order.quantity * exec_price,
        )

        # Check capital for buys
        if order.side == OrderSide.BUY:
            cost = order.quantity * exec_price + commission
            if cost > self._cash:
                raise InsufficientFundsError(
                    f"Need {cost:.2f} but only have {self._cash:.2f}",
                    exchange=self.name,
                )
            self._cash -= cost
        else:  # SELL
            revenue = order.quantity * exec_price - commission
            self._cash += revenue

        # Calculate slippage amount
        slippage_amount = abs(exec_price - current_price) * order.quantity
        self._total_slippage += slippage_amount
        self._total_commission += commission

        # Update position
        self._update_position(order, exec_price)

        # Record trade
        self._trade_history.append({
            "id": str(uuid.uuid4()),
            "symbol": order.symbol,
            "price": exec_price,
            "amount": order.quantity,
            "side": order.side.value,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        })

        # Update order
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.average_fill_price = exec_price
        order.commission = commission
        order.slippage = slippage_amount
        order.updated_at = datetime.now(tz=timezone.utc)
        return order

    async def _execute_limit_order(self, order: Order, current_price: float) -> Order:
        """Execute a limit order — fill if price crosses, else leave pending."""
        if order.price is None:
            raise OrderError("Limit order requires a price", exchange=self.name)

        # Check if limit is immediately fillable
        fillable = False
        if order.side == OrderSide.BUY and current_price <= order.price:
            fillable = True
        elif order.side == OrderSide.SELL and current_price >= order.price:
            fillable = True

        if fillable:
            # Fill at the limit price (or better)
            exec_price = order.price
            commission = max(
                self._min_commission,
                self._commission_rate * order.quantity * exec_price,
            )

            if order.side == OrderSide.BUY:
                cost = order.quantity * exec_price + commission
                if cost > self._cash:
                    raise InsufficientFundsError(
                        f"Need {cost:.2f} but only have {self._cash:.2f}",
                        exchange=self.name,
                    )
                self._cash -= cost
            else:
                revenue = order.quantity * exec_price - commission
                self._cash += revenue

            slippage_amount = abs(exec_price - current_price) * order.quantity
            self._total_slippage += slippage_amount
            self._total_commission += commission

            self._update_position(order, exec_price)

            self._trade_history.append({
                "id": str(uuid.uuid4()),
                "symbol": order.symbol,
                "price": exec_price,
                "amount": order.quantity,
                "side": order.side.value,
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            })

            order.status = OrderStatus.FILLED
            order.filled_quantity = order.quantity
            order.average_fill_price = exec_price
            order.commission = commission
            order.slippage = slippage_amount
            order.updated_at = datetime.now(tz=timezone.utc)
        else:
            # Leave pending
            order.status = OrderStatus.SUBMITTED
            self._pending_orders[order.id] = order
            order.updated_at = datetime.now(tz=timezone.utc)

        return order

    async def _execute_stop_order(self, order: Order, current_price: float) -> Order:
        """Execute a stop order — triggers market order when stop price hit."""
        if order.stop_price is None:
            raise OrderError("Stop order requires a stop_price", exchange=self.name)

        triggered = False
        if order.side == OrderSide.BUY and current_price >= order.stop_price:
            triggered = True
        elif order.side == OrderSide.SELL and current_price <= order.stop_price:
            triggered = True

        if triggered:
            # Convert to market order execution
            return await self._execute_market_order(order, current_price)
        else:
            order.status = OrderStatus.SUBMITTED
            self._pending_orders[order.id] = order
            order.updated_at = datetime.now(tz=timezone.utc)
            return order

    async def _execute_stop_limit_order(self, order: Order, current_price: float) -> Order:
        """Execute a stop-limit order — triggers limit when stop hit."""
        if order.stop_price is None or order.price is None:
            raise OrderError(
                "Stop-limit order requires both stop_price and price",
                exchange=self.name,
            )

        triggered = False
        if order.side == OrderSide.BUY and current_price >= order.stop_price:
            triggered = True
        elif order.side == OrderSide.SELL and current_price <= order.stop_price:
            triggered = True

        if triggered:
            return await self._execute_limit_order(order, current_price)
        else:
            order.status = OrderStatus.SUBMITTED
            self._pending_orders[order.id] = order
            order.updated_at = datetime.now(tz=timezone.utc)
            return order

    # ------------------------------------------------------------------ #
    # Position management
    # ------------------------------------------------------------------ #

    def _update_position(self, order: Order, exec_price: float) -> None:
        """Update the position book after an order fill."""
        symbol = order.symbol

        if symbol in self._positions:
            pos = self._positions[symbol]
            old_qty = pos.quantity
            old_entry = pos.entry_price

            if order.side == OrderSide.BUY:
                new_qty = old_qty + order.quantity
                # Weighted average entry price
                new_entry = (
                    (old_entry * old_qty + exec_price * order.quantity) / new_qty
                    if new_qty > 0
                    else exec_price
                )
                new_cost_basis = new_entry * new_qty

                # Realize P&L if we had a short position and are closing it
                if pos.side == PositionSide.SHORT:
                    closing_qty = min(order.quantity, old_qty)
                    pnl = (old_entry - exec_price) * closing_qty
                    self._realized_pnl += pnl
                    if new_qty <= old_qty:
                        # Fully or partially closed short
                        if new_qty == 0:
                            del self._positions[symbol]
                            return
                        side = PositionSide.SHORT
                    else:
                        # Flipped to long
                        side = PositionSide.LONG
                        new_entry = exec_price
                        new_cost_basis = new_entry * new_qty
                else:
                    side = PositionSide.LONG

                self._positions[symbol] = Position(
                    symbol=symbol,
                    side=side,
                    quantity=new_qty,
                    entry_price=new_entry,
                    current_price=exec_price,
                    cost_basis=new_cost_basis,
                    market_value=new_qty * exec_price,
                    broker_id=self.name,
                    strategy_name=order.strategy_name,
                    agent_name=order.agent_name,
                )

            else:  # SELL
                new_qty = old_qty - order.quantity

                if pos.side == PositionSide.LONG:
                    # Realize P&L for closed long portion
                    closing_qty = min(order.quantity, old_qty)
                    pnl = (exec_price - old_entry) * closing_qty
                    self._realized_pnl += pnl

                    if new_qty <= 0:
                        if new_qty == 0:
                            del self._positions[symbol]
                            return
                        # Flipped to short
                        self._positions[symbol] = Position(
                            symbol=symbol,
                            side=PositionSide.SHORT,
                            quantity=abs(new_qty),
                            entry_price=exec_price,
                            current_price=exec_price,
                            cost_basis=abs(new_qty) * exec_price,
                            market_value=abs(new_qty) * exec_price,
                            broker_id=self.name,
                            strategy_name=order.strategy_name,
                            agent_name=order.agent_name,
                        )
                    else:
                        self._positions[symbol] = Position(
                            symbol=symbol,
                            side=PositionSide.LONG,
                            quantity=new_qty,
                            entry_price=old_entry,
                            current_price=exec_price,
                            cost_basis=old_entry * new_qty,
                            market_value=new_qty * exec_price,
                            broker_id=self.name,
                            strategy_name=order.strategy_name,
                            agent_name=order.agent_name,
                        )
                else:
                    # Increasing short position
                    new_qty = old_qty + order.quantity
                    new_entry = (
                        (old_entry * old_qty + exec_price * order.quantity) / new_qty
                        if new_qty > 0
                        else exec_price
                    )
                    self._positions[symbol] = Position(
                        symbol=symbol,
                        side=PositionSide.SHORT,
                        quantity=new_qty,
                        entry_price=new_entry,
                        current_price=exec_price,
                        cost_basis=new_entry * new_qty,
                        market_value=new_qty * exec_price,
                        broker_id=self.name,
                        strategy_name=order.strategy_name,
                        agent_name=order.agent_name,
                    )
        else:
            # New position
            side = PositionSide.LONG if order.side == OrderSide.BUY else PositionSide.SHORT
            qty = order.quantity
            self._positions[symbol] = Position(
                symbol=symbol,
                side=side,
                quantity=qty,
                entry_price=exec_price,
                current_price=exec_price,
                cost_basis=exec_price * qty,
                market_value=exec_price * qty,
                broker_id=self.name,
                strategy_name=order.strategy_name,
                agent_name=order.agent_name,
            )

    def _apply_slippage(self, price: float, side: OrderSide) -> float:
        """Apply slippage to price — buying pushes price up, selling pushes down."""
        slip = self._slippage_bps / 10_000.0
        if side == OrderSide.BUY:
            return price * (1 + slip)
        else:
            return price * (1 - slip)

    # ------------------------------------------------------------------ #
    # Additional helpers for testing
    # ------------------------------------------------------------------ #

    @property
    def cash(self) -> float:
        """Current cash balance."""
        return self._cash

    @property
    def total_commission(self) -> float:
        """Total commission paid."""
        return self._total_commission

    @property
    def total_slippage(self) -> float:
        """Total slippage incurred."""
        return self._total_slippage

    @property
    def realized_pnl(self) -> float:
        """Total realized P&L."""
        return self._realized_pnl

    @property
    def order_count(self) -> int:
        """Total number of orders placed."""
        return len(self._orders)

    @property
    def pending_order_count(self) -> int:
        """Number of currently pending orders."""
        return len(self._pending_orders)

    def check_pending_orders(self) -> int:
        """Check and fill any pending orders whose conditions are now met.

        Call this after :meth:`set_price` to simulate limit/stop triggers.

        Returns:
            Number of orders that were filled.
        """
        filled_count = 0
        # We iterate over a copy because _execute_* may modify _pending_orders
        pending = list(self._pending_orders.items())
        for order_id, order in pending:
            current_price = self._prices.get(order.symbol, self._default_price)

            if order.order_type == OrderType.LIMIT and order.price is not None:
                can_fill = False
                if order.side == OrderSide.BUY and current_price <= order.price:
                    can_fill = True
                elif order.side == OrderSide.SELL and current_price >= order.price:
                    can_fill = True
                if can_fill:
                    self._pending_orders.pop(order_id, None)
                    # Re-execute synchronously (we're already in a compatible state)
                    exec_price = order.price
                    commission = max(
                        self._min_commission,
                        self._commission_rate * order.quantity * exec_price,
                    )
                    if order.side == OrderSide.BUY:
                        cost = order.quantity * exec_price + commission
                        if cost <= self._cash:
                            self._cash -= cost
                        else:
                            continue
                    else:
                        self._cash += order.quantity * exec_price - commission

                    self._total_commission += commission
                    self._update_position(order, exec_price)
                    order.status = OrderStatus.FILLED
                    order.filled_quantity = order.quantity
                    order.average_fill_price = exec_price
                    order.commission = commission
                    order.updated_at = datetime.now(tz=timezone.utc)
                    self._orders[order_id] = order
                    filled_count += 1

            elif order.order_type == OrderType.STOP and order.stop_price is not None:
                triggered = False
                if order.side == OrderSide.BUY and current_price >= order.stop_price:
                    triggered = True
                elif order.side == OrderSide.SELL and current_price <= order.stop_price:
                    triggered = True
                if triggered:
                    self._pending_orders.pop(order_id, None)
                    exec_price = self._apply_slippage(current_price, order.side)
                    commission = max(
                        self._min_commission,
                        self._commission_rate * order.quantity * exec_price,
                    )
                    if order.side == OrderSide.BUY:
                        cost = order.quantity * exec_price + commission
                        if cost <= self._cash:
                            self._cash -= cost
                        else:
                            continue
                    else:
                        self._cash += order.quantity * exec_price - commission

                    self._total_commission += commission
                    self._total_slippage += abs(exec_price - current_price) * order.quantity
                    self._update_position(order, exec_price)
                    order.status = OrderStatus.FILLED
                    order.filled_quantity = order.quantity
                    order.average_fill_price = exec_price
                    order.commission = commission
                    order.updated_at = datetime.now(tz=timezone.utc)
                    self._orders[order_id] = order
                    filled_count += 1

        return filled_count
