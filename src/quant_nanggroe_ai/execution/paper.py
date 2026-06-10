"""
Paper Trading Broker — Full Simulated Execution
================================================
In-memory order book and position tracking with realistic
slippage, commission, and trade event emission.

Features:
    - Market and limit order support
    - Configurable slippage model (basis points or fixed)
    - Position tracking with average cost basis
    - Trade event callbacks for real-time monitoring
    - Full order lifecycle: PENDING → FILLED / CANCELLED / REJECTED
    - Cash balance and equity computation
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# ORDER & POSITION MODELS
# ══════════════════════════════════════════════════════════════════════


class OrderStatus(str, Enum):
    """Order lifecycle states."""

    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class OrderSide(str, Enum):
    """Order side."""

    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Order type."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class TradeEvent(BaseModel):
    """Event emitted when a trade is executed."""

    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    filled_price: float
    commission: float
    slippage: float
    timestamp: datetime = Field(default_factory=datetime.now)


class PaperOrder(BaseModel):
    """Paper trading order with full lifecycle tracking."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    symbol: str
    side: OrderSide
    quantity: float
    order_type: OrderType = OrderType.MARKET
    limit_price: float | None = None
    stop_price: float | None = None
    status: OrderStatus = OrderStatus.PENDING
    filled_price: float | None = None
    filled_quantity: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    filled_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Position(BaseModel):
    """Tracked position for a symbol."""

    symbol: str
    quantity: float = 0.0
    avg_entry_price: float = 0.0
    current_price: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    last_updated: datetime = Field(default_factory=datetime.now)

    @property
    def market_value(self) -> float:
        """Current market value of the position."""
        return self.quantity * self.current_price

    @property
    def cost_basis(self) -> float:
        """Total cost basis of the position."""
        return self.quantity * self.avg_entry_price


# ══════════════════════════════════════════════════════════════════════
# SLIPPAGE MODELS
# ══════════════════════════════════════════════════════════════════════


class SlippageModel:
    """
    Configurable slippage simulation.

    Supports:
    - Fixed basis-point slippage
    - Volume-proportional slippage
    - Random slippage within a range
    """

    def __init__(
        self,
        base_bps: float = 5.0,
        volume_factor: float = 0.0,
        random_range_bps: float = 0.0,
    ) -> None:
        self.base_bps = base_bps
        self.volume_factor = volume_factor
        self.random_range_bps = random_range_bps

    def calculate(
        self,
        price: float,
        side: OrderSide,
        quantity: float = 0.0,
        avg_volume: float = 1.0,
    ) -> float:
        """
        Calculate slippage for a given order.

        Args:
            price: Current market price
            side: BUY or SELL
            quantity: Order quantity
            avg_volume: Average daily volume for volume-proportional model

        Returns:
            Slippage amount in price units (always positive)
        """
        import random

        base_slip = price * (self.base_bps / 10_000)

        # Volume-proportional: larger orders relative to avg volume get more slippage
        if self.volume_factor > 0 and avg_volume > 0:
            participation_rate = quantity / avg_volume if avg_volume else 0
            volume_slip = price * participation_rate * self.volume_factor
            base_slip += volume_slip

        # Random component
        if self.random_range_bps > 0:
            random_component = random.uniform(
                -self.random_range_bps, self.random_range_bps
            ) / 10_000 * price
            base_slip += abs(random_component)

        return abs(base_slip)


# ══════════════════════════════════════════════════════════════════════
# PAPER TRADING BROKER
# ══════════════════════════════════════════════════════════════════════


class PaperTradingBroker:
    """
    In-memory paper trading broker with full order and position management.

    Simulates realistic execution with configurable slippage, commission,
    and emits trade events for downstream processing.

    Args:
        initial_capital: Starting cash balance
        commission_rate: Commission as fraction of trade value (e.g. 0.001 = 0.1%)
        slippage_model: SlippageModel instance for price simulation
        min_commission: Minimum commission per trade
        enable_short_selling: Whether to allow negative positions

    Example:
        broker = PaperTradingBroker(initial_capital=100_000, commission_rate=0.001)
        order = await broker.buy("AAPL", 100, 150.0)
        print(broker.get_balance())
        print(broker.get_positions())
    """

    def __init__(
        self,
        initial_capital: float = 100_000.0,
        commission_rate: float = 0.001,
        slippage_model: SlippageModel | None = None,
        min_commission: float = 1.0,
        enable_short_selling: bool = False,
    ) -> None:
        self._initial_capital = initial_capital
        self._cash = initial_capital
        self._commission_rate = commission_rate
        self._min_commission = min_commission
        self._enable_short_selling = enable_short_selling

        self._slippage_model = slippage_model or SlippageModel(base_bps=5.0)

        # Internal state
        self._orders: dict[str, PaperOrder] = {}
        self._positions: dict[str, Position] = {}
        self._trade_history: list[TradeEvent] = []
        self._event_callbacks: list[Callable[[TradeEvent], None]] = []
        self._order_counter = 0

        # Market prices cache (updated via set_market_price)
        self._market_prices: dict[str, float] = {}

        logger.info(
            "PaperTradingBroker initialized: capital=%.2f, commission=%.4f",
            initial_capital,
            commission_rate,
        )

    # ══════════════════════════════════════════════════════════════════
    # ORDER SUBMISSION
    # ══════════════════════════════════════════════════════════════════

    async def buy(
        self,
        symbol: str,
        quantity: float,
        price: float | None = None,
        order_type: OrderType = OrderType.MARKET,
    ) -> PaperOrder:
        """
        Submit a buy order.

        Args:
            symbol: Trading symbol
            quantity: Number of shares/units
            price: Limit price (required for LIMIT orders)
            order_type: MARKET or LIMIT

        Returns:
            PaperOrder with execution details
        """
        return await self._submit_order(
            symbol=symbol,
            side=OrderSide.BUY,
            quantity=quantity,
            price=price,
            order_type=order_type,
        )

    async def sell(
        self,
        symbol: str,
        quantity: float,
        price: float | None = None,
        order_type: OrderType = OrderType.MARKET,
    ) -> PaperOrder:
        """
        Submit a sell order.

        Args:
            symbol: Trading symbol
            quantity: Number of shares/units
            price: Limit price (required for LIMIT orders)
            order_type: MARKET or LIMIT

        Returns:
            PaperOrder with execution details
        """
        return await self._submit_order(
            symbol=symbol,
            side=OrderSide.SELL,
            quantity=quantity,
            price=price,
            order_type=order_type,
        )

    async def _submit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        price: float | None = None,
        order_type: OrderType = OrderType.MARKET,
    ) -> PaperOrder:
        """
        Internal order submission with validation and execution simulation.
        """
        self._order_counter += 1
        order_id = f"PAPER-{self._order_counter:06d}"

        # Validate
        if quantity <= 0:
            order = PaperOrder(
                id=order_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=order_type,
                status=OrderStatus.REJECTED,
                metadata={"reject_reason": "Quantity must be positive"},
            )
            self._orders[order_id] = order
            logger.warning("Order rejected: invalid quantity %s", quantity)
            return order

        # Check if selling more than held (unless short selling enabled)
        if side == OrderSide.SELL and not self._enable_short_selling:
            position = self._positions.get(symbol)
            held = position.quantity if position else 0.0
            if quantity > held:
                order = PaperOrder(
                    id=order_id,
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    order_type=order_type,
                    status=OrderStatus.REJECTED,
                    metadata={"reject_reason": f"Insufficient shares: held={held}, requested={quantity}"},
                )
                self._orders[order_id] = order
                logger.warning(
                    "Order rejected: insufficient shares for %s (held=%.2f, requested=%.2f)",
                    symbol, held, quantity,
                )
                return order

        # Create order
        order = PaperOrder(
            id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            limit_price=price if order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT) else None,
            status=OrderStatus.PENDING,
        )
        self._orders[order_id] = order

        # Execute market orders immediately
        if order_type == OrderType.MARKET:
            market_price = price or self._market_prices.get(symbol, 0.0)
            if market_price <= 0:
                order.status = OrderStatus.REJECTED
                order.metadata["reject_reason"] = "No market price available"
                logger.warning("Order rejected: no market price for %s", symbol)
                return order

            await self._fill_order(order, market_price)

        elif order_type == OrderType.LIMIT:
            # Store for later evaluation
            logger.info(
                "Limit order queued: %s %s %d @ %.2f",
                side.value, symbol, quantity, price,
            )

        return order

    async def _fill_order(self, order: PaperOrder, market_price: float) -> None:
        """
        Fill an order at the given market price with slippage and commission.
        """
        # Calculate slippage
        slippage = self._slippage_model.calculate(
            price=market_price,
            side=order.side,
            quantity=order.quantity,
        )

        # Apply slippage directionally
        if order.side == OrderSide.BUY:
            fill_price = market_price + slippage
        else:
            fill_price = market_price - slippage

        fill_price = round(fill_price, 6)

        # Calculate commission
        trade_value = fill_price * order.quantity
        commission = max(trade_value * self._commission_rate, self._min_commission)

        # Check cash for buys
        if order.side == OrderSide.BUY:
            total_cost = trade_value + commission
            if total_cost > self._cash:
                order.status = OrderStatus.REJECTED
                order.metadata["reject_reason"] = (
                    f"Insufficient cash: balance={self._cash:.2f}, cost={total_cost:.2f}"
                )
                logger.warning(
                    "Order rejected: insufficient cash (%.2f < %.2f)",
                    self._cash, total_cost,
                )
                return

            # Deduct cash
            self._cash -= total_cost

            # Update position
            self._update_position_buy(order.symbol, order.quantity, fill_price)

        else:  # SELL
            # Add cash
            self._cash += trade_value - commission

            # Update position
            self._update_position_sell(order.symbol, order.quantity, fill_price)

        # Update order
        order.status = OrderStatus.FILLED
        order.filled_price = fill_price
        order.filled_quantity = order.quantity
        order.commission = commission
        order.slippage = slippage
        order.filled_at = datetime.now()
        order.updated_at = datetime.now()

        # Emit trade event
        event = TradeEvent(
            order_id=order.id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            filled_price=fill_price,
            commission=commission,
            slippage=slippage,
        )
        self._trade_history.append(event)
        self._emit_event(event)

        logger.info(
            "Order filled: %s %s %.2f @ %.2f (slip=%.4f, comm=%.2f)",
            order.side.value, order.symbol, order.quantity,
            fill_price, slippage, commission,
        )

    def _update_position_buy(self, symbol: str, quantity: float, price: float) -> None:
        """Update position after a buy fill."""
        if symbol not in self._positions:
            self._positions[symbol] = Position(
                symbol=symbol, quantity=quantity, avg_entry_price=price, current_price=price
            )
        else:
            pos = self._positions[symbol]
            total_cost = pos.avg_entry_price * pos.quantity + price * quantity
            pos.quantity += quantity
            pos.avg_entry_price = total_cost / pos.quantity if pos.quantity > 0 else 0.0
            pos.current_price = price
            pos.last_updated = datetime.now()

    def _update_position_sell(self, symbol: str, quantity: float, price: float) -> None:
        """Update position after a sell fill, tracking realized PnL."""
        if symbol not in self._positions:
            if self._enable_short_selling:
                self._positions[symbol] = Position(
                    symbol=symbol, quantity=-quantity, avg_entry_price=price, current_price=price
                )
            return

        pos = self._positions[symbol]
        realized = (price - pos.avg_entry_price) * quantity
        pos.realized_pnl += realized
        pos.quantity -= quantity
        pos.current_price = price
        pos.last_updated = datetime.now()

        # Remove closed positions
        if abs(pos.quantity) < 1e-9:
            del self._positions[symbol]

    # ══════════════════════════════════════════════════════════════════
    # MARKET PRICE UPDATES & LIMIT ORDER EVALUATION
    # ══════════════════════════════════════════════════════════════════

    def set_market_price(self, symbol: str, price: float) -> None:
        """
        Update the current market price for a symbol.

        Also evaluates pending limit orders that may now be fillable.

        Args:
            symbol: Trading symbol
            price: Current market price
        """
        self._market_prices[symbol] = price

        # Update position current prices
        if symbol in self._positions:
            pos = self._positions[symbol]
            pos.current_price = price
            pos.unrealized_pnl = (price - pos.avg_entry_price) * pos.quantity

        # Evaluate pending limit orders
        self._evaluate_limit_orders(symbol, price)

    def _evaluate_limit_orders(self, symbol: str, current_price: float) -> None:
        """Check if any pending limit orders for this symbol can be filled."""
        for order in self._orders.values():
            if (
                order.symbol != symbol
                or order.status != OrderStatus.PENDING
                or order.order_type != OrderType.LIMIT
                or order.limit_price is None
            ):
                continue

            fillable = False
            if (order.side == OrderSide.BUY and current_price <= order.limit_price) or (order.side == OrderSide.SELL and current_price >= order.limit_price):
                fillable = True

            if fillable:
                import asyncio
                asyncio.create_task(self._fill_order(order, current_price))

    # ══════════════════════════════════════════════════════════════════
    # QUERY METHODS
    # ══════════════════════════════════════════════════════════════════

    def get_positions(self) -> dict[str, Position]:
        """
        Get all current positions.

        Returns:
            Dict mapping symbol to Position
        """
        return dict(self._positions)

    def get_position(self, symbol: str) -> Position | None:
        """Get position for a specific symbol."""
        return self._positions.get(symbol)

    def get_balance(self) -> dict[str, float]:
        """
        Get account balance details.

        Returns:
            Dict with cash, equity, positions_value, unrealized_pnl, realized_pnl
        """
        positions_value = sum(p.market_value for p in self._positions.values())
        unrealized_pnl = sum(p.unrealized_pnl for p in self._positions.values())
        realized_pnl = sum(p.realized_pnl for p in self._positions.values())
        equity = self._cash + positions_value

        return {
            "cash": round(self._cash, 2),
            "equity": round(equity, 2),
            "initial_capital": self._initial_capital,
            "positions_value": round(positions_value, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "realized_pnl": round(realized_pnl, 2),
            "total_pnl": round(equity - self._initial_capital, 2),
            "return_pct": round((equity / self._initial_capital - 1) * 100, 4),
        }

    def get_open_orders(self, symbol: str | None = None) -> list[PaperOrder]:
        """
        Get all open (pending) orders.

        Args:
            symbol: Optional filter by symbol

        Returns:
            List of pending orders
        """
        orders = [
            o for o in self._orders.values() if o.status == OrderStatus.PENDING
        ]
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        return orders

    def get_order_history(self, symbol: str | None = None) -> list[PaperOrder]:
        """Get all orders, optionally filtered by symbol."""
        orders = list(self._orders.values())
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        return orders

    def get_trade_history(self) -> list[TradeEvent]:
        """Get all trade events."""
        return list(self._trade_history)

    # ══════════════════════════════════════════════════════════════════
    # ORDER CANCELLATION
    # ══════════════════════════════════════════════════════════════════

    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel a pending order.

        Args:
            order_id: ID of the order to cancel

        Returns:
            True if cancellation succeeded, False otherwise
        """
        order = self._orders.get(order_id)
        if order is None:
            logger.warning("Cancel failed: order %s not found", order_id)
            return False

        if order.status != OrderStatus.PENDING:
            logger.warning(
                "Cancel failed: order %s is %s (not PENDING)", order_id, order.status.value
            )
            return False

        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.now()
        logger.info("Order cancelled: %s", order_id)
        return True

    # ══════════════════════════════════════════════════════════════════
    # EVENT SYSTEM
    # ══════════════════════════════════════════════════════════════════

    def on_trade(self, callback: Callable[[TradeEvent], None]) -> None:
        """
        Register a callback for trade events.

        Args:
            callback: Function called with TradeEvent on each fill
        """
        self._event_callbacks.append(callback)
        logger.debug("Trade event callback registered: %s", callback.__name__)

    def _emit_event(self, event: TradeEvent) -> None:
        """Emit a trade event to all registered callbacks."""
        for callback in self._event_callbacks:
            try:
                callback(event)
            except Exception as exc:
                logger.error(
                    "Trade event callback error (%s): %s", callback.__name__, exc
                )

    # ══════════════════════════════════════════════════════════════════
    # RESET
    # ══════════════════════════════════════════════════════════════════

    def reset(self, initial_capital: float | None = None) -> None:
        """
        Reset the broker to initial state.

        Args:
            initial_capital: New initial capital (defaults to original)
        """
        self._initial_capital = initial_capital or self._initial_capital
        self._cash = self._initial_capital
        self._orders.clear()
        self._positions.clear()
        self._trade_history.clear()
        self._market_prices.clear()
        self._order_counter = 0
        logger.info("PaperTradingBroker reset: capital=%.2f", self._initial_capital)
