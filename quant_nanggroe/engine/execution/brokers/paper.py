"""Paper Trading Broker with Realistic Simulation.

Implements a paper trading broker that simulates realistic execution
with configurable slippage, commission, and market impact.

This is the primary broker for backtesting and development.
Extracted from Misi-Screener's PaperTradingBroker with enhancements.
"""

from __future__ import annotations

import uuid
import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.execution.base import (
    Broker,
    Order,
    OrderSide,
    OrderType,
    OrderStatus,
    Fill,
    PositionInfo,
    AccountInfo,
)

logger = logging.getLogger(__name__)


class PaperBroker(Broker):
    """Paper trading broker with realistic simulation.

    Simulates:
    - Market/Limit/Stop order execution
    - Configurable slippage (basis points)
    - Commission (percentage or fixed)
    - Partial fills
    - Order rejections (insufficient funds, etc.)
    """

    def __init__(
        self,
        initial_capital: float = 1_000_000.0,
        commission_rate: float = 0.001,
        slippage_bps: float = 5.0,
        min_commission: float = 1.0,
    ) -> None:
        self._capital = initial_capital
        self._initial_capital = initial_capital
        self._commission_rate = commission_rate
        self._slippage_bps = slippage_bps
        self._min_commission = min_commission
        self._positions: Dict[str, PositionInfo] = {}
        self._prices: Dict[str, float] = {}
        self._connected = False
        self._order_history: List[Order] = []
        self._fill_history: List[Fill] = []

    @property
    def name(self) -> str:
        return "paper"

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        self._connected = True
        logger.info("PaperBroker: Connected (simulated)")
        return True

    async def disconnect(self) -> None:
        self._connected = False
        logger.info("PaperBroker: Disconnected")

    async def get_account(self) -> AccountInfo:
        total_position_value = sum(
            p.market_value for p in self._positions.values()
        )
        equity = self._capital + total_position_value

        return AccountInfo(
            balance=self._capital,
            equity=equity,
            margin_used=0.0,
            margin_available=equity,
            buying_power=equity,
        )

    async def submit_order(self, order: Order) -> Order:
        """Submit an order for paper execution.

        Simulates realistic execution with slippage and commission.
        """
        if not self._connected:
            order.status = OrderStatus.REJECTED
            return order

        # Get current price
        current_price = self._prices.get(order.symbol)
        if current_price is None or current_price <= 0:
            order.status = OrderStatus.REJECTED
            order.metadata["rejection_reason"] = "No price data available"
            return order

        # Determine execution price
        if order.order_type == OrderType.MARKET:
            exec_price = self._apply_slippage(current_price, order.side)
        elif order.order_type == OrderType.LIMIT:
            if order.price is None:
                order.status = OrderStatus.REJECTED
                return order
            # Check if limit price is reachable
            if order.side == OrderSide.BUY and current_price > order.price:
                order.status = OrderStatus.PENDING
                return order
            elif order.side == OrderSide.SELL and current_price < order.price:
                order.status = OrderStatus.PENDING
                return order
            exec_price = order.price
        else:
            exec_price = self._apply_slippage(current_price, order.side)

        # Calculate commission
        commission = max(self._min_commission, self._commission_rate * order.quantity * exec_price)

        # Check if we have enough capital for buys
        if order.side == OrderSide.BUY:
            cost = order.quantity * exec_price + commission
            if cost > self._capital:
                order.status = OrderStatus.REJECTED
                order.metadata["rejection_reason"] = "Insufficient capital"
                return order
            self._capital -= cost
        else:  # SELL
            self._capital += order.quantity * exec_price - commission

        # Update position
        self._update_position(order, exec_price)

        # Create fill
        fill = Fill(
            id=str(uuid.uuid4()),
            order_id=order.id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=exec_price,
            commission=commission,
            slippage=abs(exec_price - current_price),
        )
        self._fill_history.append(fill)

        # Update order
        order.status = OrderStatus.FILLED
        order.metadata["fill_price"] = exec_price
        order.metadata["commission"] = commission
        self._order_history.append(order)

        return order

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        for order in self._order_history:
            if order.id == order_id and order.status == OrderStatus.PENDING:
                order.status = OrderStatus.CANCELLED
                return True
        return False

    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        for order in self._order_history:
            if order.id == order_id:
                return order
        return None

    async def get_positions(self) -> List[PositionInfo]:
        """Get all open positions."""
        return list(self._positions.values())

    async def get_price(self, symbol: str) -> float:
        """Get current price for a symbol."""
        return self._prices.get(symbol, 0.0)

    def set_price(self, symbol: str, price: float) -> None:
        """Set the current price for a symbol (for simulation).

        Args:
            symbol: Trading symbol.
            price: Current market price.
        """
        self._prices[symbol] = price
        # Update position values
        if symbol in self._positions:
            pos = self._positions[symbol]
            new_pnl = pos.quantity * (price - pos.avg_entry_price)
            self._positions[symbol] = PositionInfo(
                symbol=symbol,
                quantity=pos.quantity,
                avg_entry_price=pos.avg_entry_price,
                current_price=price,
                unrealized_pnl=new_pnl,
                market_value=pos.quantity * price,
            )

    def _apply_slippage(self, price: float, side: OrderSide) -> float:
        """Apply slippage to price.

        Buying: price increases (adverse)
        Selling: price decreases (adverse)
        """
        slip = self._slippage_bps / 10000.0
        if side == OrderSide.BUY:
            return price * (1 + slip)
        else:
            return price * (1 - slip)

    def _update_position(self, order: Order, exec_price: float) -> None:
        """Update position after order fill."""
        symbol = order.symbol
        qty = order.quantity if order.side == OrderSide.BUY else -order.quantity

        if symbol in self._positions:
            pos = self._positions[symbol]
            new_qty = pos.quantity + qty
            if new_qty == 0:
                del self._positions[symbol]
            else:
                # Weighted average entry price
                total_cost = pos.avg_entry_price * pos.quantity + exec_price * qty
                new_avg = total_cost / new_qty if new_qty != 0 else 0
                self._positions[symbol] = PositionInfo(
                    symbol=symbol,
                    quantity=new_qty,
                    avg_entry_price=new_avg,
                    current_price=exec_price,
                    unrealized_pnl=new_qty * (exec_price - new_avg),
                    market_value=new_qty * exec_price,
                )
        else:
            self._positions[symbol] = PositionInfo(
                symbol=symbol,
                quantity=qty,
                avg_entry_price=exec_price,
                current_price=exec_price,
                unrealized_pnl=0.0,
                market_value=qty * exec_price,
            )
