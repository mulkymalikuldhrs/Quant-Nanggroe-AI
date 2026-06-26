"""Simulated broker for testing multi-broker abstraction."""
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from quant_nanggroe.connectors.broker_base import BrokerConnector, Order, Position


class SimulatedBroker(BrokerConnector):
    def __init__(self, initial_balance: float = 100_000.0):
        self.balance = initial_balance
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.connected = False
        self.prices: Dict[str, float] = {}

    def connect(self) -> bool:
        self.connected = True
        return True

    def disconnect(self):
        self.connected = False
        self.positions.clear()
        self.orders.clear()

    def update_price(self, symbol: str, price: float):
        self.prices[symbol] = price
        if symbol in self.positions:
            pos = self.positions[symbol]
            pos.current_price = price
            pos.pnl = (price - pos.entry_price) * pos.quantity

    def place_order(self, order: Order) -> str:
        order_id = str(uuid.uuid4())
        self.orders.append(order)

        if order.side == "buy":
            cost = order.price or self.prices.get(order.symbol, 100.0)
            if cost * order.quantity > self.balance:
                raise ValueError("Insufficient funds")
            self.balance -= cost * order.quantity

            if order.symbol in self.positions:
                pos = self.positions[order.symbol]
                total_qty = pos.quantity + order.quantity
                total_cost = (pos.quantity * pos.entry_price) + (order.quantity * cost)
                self.positions[order.symbol] = Position(
                    symbol=order.symbol,
                    quantity=total_qty,
                    entry_price=total_cost / total_qty,
                    current_price=cost,
                    broker="simulated",
                )
            else:
                self.positions[order.symbol] = Position(
                    symbol=order.symbol,
                    quantity=order.quantity,
                    entry_price=cost,
                    current_price=cost,
                    broker="simulated",
                )
        elif order.side == "sell":
            if order.symbol not in self.positions:
                raise ValueError("No position to sell")
            pos = self.positions[order.symbol]
            price = order.price or self.prices.get(order.symbol, 100.0)
            if order.quantity > pos.quantity:
                raise ValueError("Insufficient position quantity")

            self.balance += price * order.quantity
            remaining = pos.quantity - order.quantity
            if remaining <= 0:
                del self.positions[order.symbol]
            else:
                self.positions[order.symbol] = Position(
                    symbol=order.symbol,
                    quantity=remaining,
                    entry_price=pos.entry_price,
                    current_price=price,
                    broker="simulated",
                )

        return order_id

    def get_positions(self) -> List[Position]:
        return list(self.positions.values())

    def get_balance(self) -> float:
        return self.balance
