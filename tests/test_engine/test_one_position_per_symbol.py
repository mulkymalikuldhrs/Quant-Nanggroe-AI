"""Tests: ONE position per symbol — broker-truth enforcement in execute_order.

Non-negotiable rule #5. Fail-closed: a failed position query must BLOCK.
"""
from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from quant_nanggroe.engine.execution.base import (
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
)


def _order(symbol="EURUSD", side=OrderSide.BUY) -> Order:
    return Order(
        id="test-order-1", symbol=symbol, side=side,
        order_type=OrderType.MARKET, quantity=0.01,
        status=OrderStatus.PENDING,
    )


class _FakeBroker:
    def __init__(self, positions=None, raise_on_positions=False, reject_submit=False):
        self.is_connected = True
        self.name = "fake"
        self._positions = positions or []
        self._raise = raise_on_positions
        self._reject_submit = reject_submit
        self.submitted = []

    async def get_positions(self):
        if self._raise:
            raise RuntimeError("position query down")
        return self._positions

    async def get_account(self):
        return SimpleNamespace(balance=10_000.0)

    async def submit_order(self, order):
        self.submitted.append(order)
        if self._reject_submit:
            order.status = OrderStatus.REJECTED
            order.metadata = {"reason": "MT5 order rejected", "error_code": "REJECTED"}
        else:
            order.status = OrderStatus.FILLED
            order.metadata = {"fill_price": 1.1000}
        return order

    async def connect(self):
        return True


class TestOnePositionPerSymbol(unittest.TestCase):
    def _build_manager(self, broker):
        from quant_nanggroe.engine.execution.manager import ExecutionManager
        em = ExecutionManager()
        em.add_broker(broker, primary=True)
        em.set_kill_switch(MagicMock())
        em.set_risk_manager(MagicMock())
        # neutralize risk verdict to APPROVED so we isolate the duplicate check
        em._risk_manager.check_trade.return_value = {"verdict": "APPROVED"}
        ks = MagicMock()
        ks.can_trade.return_value = True
        ks.check_auto_activate.return_value = None
        ks.check_warning.return_value = False
        em._kill_switch = ks
        return em

    def test_duplicate_symbol_blocked(self):
        open_pos = [SimpleNamespace(symbol="EURUSD", side="buy")]
        broker = _FakeBroker(positions=open_pos)
        em = self._build_manager(broker)
        fill = asyncio.run(em.execute_order(_order("EURUSD")))
        self.assertIsNone(fill, "second EURUSD position must be BLOCKED")
        self.assertEqual(broker.submitted, [], "no order may reach the broker")

    def test_different_symbol_allowed(self):
        open_pos = [SimpleNamespace(symbol="GBPUSD", side="buy")]
        broker = _FakeBroker(positions=open_pos)
        em = self._build_manager(broker)
        fill = asyncio.run(em.execute_order(_order("EURUSD")))
        self.assertIsNotNone(fill)
        self.assertEqual(len(broker.submitted), 1)

    def test_no_open_positions_allowed(self):
        broker = _FakeBroker(positions=[])
        em = self._build_manager(broker)
        fill = asyncio.run(em.execute_order(_order("XAUUSD.vxc")))
        self.assertIsNotNone(fill)

    def test_position_query_failure_blocks_fail_closed(self):
        broker = _FakeBroker(raise_on_positions=True)
        em = self._build_manager(broker)
        fill = asyncio.run(em.execute_order(_order("EURUSD")))
        self.assertIsNone(fill, "failed position query must FAIL CLOSED")
        self.assertEqual(broker.submitted, [])

    def test_rejected_submit_produces_no_phantom_fill(self):
        """A REJECTED order must return None — never a phantom Fill (price 0)."""
        broker = _FakeBroker(reject_submit=True)
        em = self._build_manager(broker)
        fill = asyncio.run(em.execute_order(_order("XAUUSD.vxc")))
        self.assertIsNone(fill, "REJECTED order must not produce a Fill")
        # guards must NOT record the phantom trade
        audit_actions = [a.get("action") for a in em.get_audit_log()]
        self.assertIn("ORDER_NOT_FILLED", audit_actions)
        self.assertNotIn("ORDER_SUBMITTED", audit_actions)


if __name__ == "__main__":
    unittest.main()
