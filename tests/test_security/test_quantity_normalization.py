"""F011: server must normalize client quantity to LOT before broker submit."""
from __future__ import annotations

import asyncio
from typing import Optional

import pytest

from quant_nanggroe.engine.execution.base import Order, OrderSide, OrderStatus, OrderType
from quant_nanggroe.engine.execution.brokers.mt5_adapter import MT5ExecutionBroker


class DummyMT5Broker:
    def __init__(self):
        self.connected = True
        self.last_order = None

    def connect(self):
        return True

    def disconnect(self):
        pass

    def get_account(self):
        return type("A", (), {"balance": 1000.0, "equity": 1000.0, "margin_free": 1000.0})

    def get_balance(self):
        return 1000.0

    def place_order(self, conn_order):
        self.last_order = conn_order
        return "DUMMY_TICKET"

    def get_positions(self):
        return []

    def get_orders(self):
        return []

    def cancel_order(self, order_id):
        return False

    def get_history(self, *a, **kw):
        return []


@pytest.mark.asyncio
async def test_client_quantity_is_normalized_to_lots():
    broker = DummyMT5Broker()
    adapter = MT5ExecutionBroker(broker)
    order = Order(
        id="test-f011",
        symbol="EURUSD",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=100000.0,
        price=1.0856,
        stop_price=None,
        status=OrderStatus.PENDING,
    )
    await adapter.submit_order(order)
    assert broker.last_order is not None
    qty = broker.last_order.quantity
    assert qty <= 10.0, f"quantity must be normalized to lots, got {qty}"
    assert qty >= 0.01, f"quantity must be >= min lot, got {qty}"

