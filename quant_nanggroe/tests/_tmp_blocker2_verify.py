"""Temporary verification for Blocker 2 SL/TP fix in ExecutionManager.execute_order."""
from __future__ import annotations
import asyncio
from typing import Optional
from quant_nanggroe.engine.execution.manager import ExecutionManager, _price_precision
from quant_nanggroe.engine.execution.base import Broker
from quant_nanggroe.types.orders import Order, OrderSide, OrderType, OrderStatus


class FakeAccount:
    balance = 10000.0


class FakeBroker(Broker):
    def __init__(self, price: float):
        self._price = price

    async def connect(self): return True
    async def disconnect(self): return None
    async def get_account(self): return FakeAccount()
    async def get_price(self, symbol): return self._price
    async def submit_order(self, order):
        order.status = OrderStatus.FILLED
        order.broker_order_id = "BRK1"
        return order
    async def cancel_order(self, order_id): return False
    async def get_order(self, order_id): return None
    async def get_positions(self): return []
    def name(self): return "fake"
    def is_connected(self): return True


def make_order(side, price, qty):
    o = Order(
        id="ORD1", symbol="EURUSD", side=side,
        order_type=OrderType.MARKET, quantity=qty,
        price=price, stop_loss=None, take_profit=None,
    )
    return o


async def run():
    mgr = ExecutionManager()
    mgr.add_broker(FakeBroker(price=1.0500))
    # BUY: SL below entry, TP above
    o = make_order(OrderSide.BUY, 1.0500, 0.1)
    await mgr.execute_order(o)
    assert o.stop_loss is not None, "SL must be set"
    assert o.take_profit is not None, "TP must be set"
    assert o.stop_loss < o.price, f"BUY SL {o.stop_loss} should be < {o.price}"
    assert o.take_profit > o.price, f"BUY TP {o.take_profit} should be > {o.price}"
    rr = (o.take_profit - o.price) / (o.price - o.stop_loss)
    assert abs(rr - 2.0) < 0.01, f"R:R {rr} should be ~2.0"
    print(f"BUY  SL={o.stop_loss} TP={o.take_profit} R:R={rr:.3f}")

    # SELL: SL above entry, TP below
    o2 = make_order(OrderSide.SELL, 1.0500, 0.1)
    await mgr.execute_order(o2)
    assert o2.stop_loss > o2.price, "SELL SL should be > price"
    assert o2.take_profit < o2.price, "SELL TP should be < price"
    print(f"SELL SL={o2.stop_loss} TP={o2.take_profit}")

    # Caller-supplied SL preserved
    o3 = make_order(OrderSide.BUY, 1.0500, 0.1)
    o3.stop_loss = 1.0000
    o3.take_profit = 1.1000
    await mgr.execute_order(o3)
    assert o3.stop_loss == 1.0000 and o3.take_profit == 1.1000, "explicit SL/TP must be preserved"
    print(f"PRESERVED SL={o3.stop_loss} TP={o3.take_profit}")

    # precision helper
    assert _price_precision(0.5) == 5
    assert _price_precision(50.0) == 4
    assert _price_precision(5000.0) == 2
    print("precision OK")

    # submit_order received populated order
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    asyncio.run(run())
