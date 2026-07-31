"""Integration test: kill-switch PnL auto-activation via ExecutionManager.execute_order.

BLOCKER 1h coverage:
  1) A simulated loss that exceeds the daily kill-switch limit, fed through
     execute_order(), MUST auto-trip the kill switch (can_trade() == False) and
     the order MUST be blocked (execute_order returns None).
  2) A PnL of exactly 0 MUST NOT trip the kill switch (can_trade() == True) and
     the order MUST fill.

The kill-switch daily threshold is KILL_SWITCH_DAILY_PNL (a fraction, e.g.
-0.008 == -0.8%). execute_order() takes PnL as PERCENT and divides by 100 at the
boundary, so a percent loss > 0.8% (e.g. -2.0%) breaches the daily limit.

Run:
    PYTHONPATH= .venv/Scripts/python.exe -m pytest tests/test_killswitch_pnl_integration.py -v
"""

from __future__ import annotations

import asyncio
import os
import sys
import unittest
import uuid
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

from quant_nanggroe.engine.execution.base import Order, OrderSide, OrderType
from quant_nanggroe.engine.execution.brokers.paper import PaperBroker
from quant_nanggroe.engine.execution.manager import ExecutionManager
from quant_nanggroe.engine.risk.constants import KILL_SWITCH_DAILY_PNL
from quant_nanggroe.engine.risk.kill_switch import KillSwitch, KillSwitchStatus


def _fresh_manager() -> ExecutionManager:
    """Build an ExecutionManager wired to a connected paper broker with a
    fresh, in-memory (non-shared) kill switch so tests never cross-contaminate."""
    manager = ExecutionManager()
    broker = PaperBroker(initial_capital=1_000_000.0)
    asyncio.get_event_loop()  # ensure loop exists for sync callers
    manager.add_broker(broker, primary=True)
    # Replace with a guaranteed-fresh in-memory kill switch (no shared state file).
    manager.set_kill_switch(KillSwitch())
    return manager, broker


def _make_order(symbol: str = "BTC-USD") -> Order:
    return Order(
        id=uuid.uuid4().hex[:12],
        symbol=symbol,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=0.001,
        price=50_000.0,
    )


class TestKillSwitchPnLIntegration(unittest.TestCase):
    def setUp(self) -> None:
        # Guarantee in-memory (isolated) kill-switch state — no shared file.
        self._saved_env = os.environ.pop("QNA_KILL_SWITCH_STATE_FILE", None)

    def tearDown(self) -> None:
        if self._saved_env is not None:
            os.environ["QNA_KILL_SWITCH_STATE_FILE"] = self._saved_env

    def test_loss_exceeding_daily_limit_trips_kill_switch(self) -> None:
        """execute_order with simulated loss > daily limit → kill switch trips."""

        async def _run() -> None:
            manager, broker = _fresh_manager()
            await broker.connect()
            broker.set_price("BTC-USD", 50_000.0)
            order = _make_order()

            ks = manager._kill_switch
            # Sanity: fresh switch allows trading before any loss.
            self.assertTrue(ks.can_trade(), "fresh kill switch should allow trading")

            # Daily limit is a fraction (e.g. -0.008). Feed a PERCENT loss well
            # beyond it: 2.0% >> 0.8% threshold. execute_order divides by 100.
            breach_pct = abs(KILL_SWITCH_DAILY_PNL) * 100.0 * 3.0  # e.g. 2.4%
            fill = await manager.execute_order(
                order,
                daily_pnl_pct=-breach_pct,
                weekly_pnl_pct=0.0,
                max_drawdown_pct=0.0,
                volatility_pct=0.0,
            )

            # Kill switch MUST have auto-tripped.
            self.assertFalse(
                ks.can_trade(),
                "kill switch MUST trip (can_trade=False) after loss exceeding daily limit",
            )
            self.assertEqual(ks._status, KillSwitchStatus.ACTIVE)
            # And the order MUST be blocked.
            self.assertIsNone(fill, "order must be blocked when kill switch is active")

        asyncio.run(_run())

    def test_zero_pnl_does_not_trip_kill_switch(self) -> None:
        """execute_order with PnL == 0 → kill switch stays inactive, order fills."""

        async def _run() -> None:
            manager, broker = _fresh_manager()
            await broker.connect()
            broker.set_price("BTC-USD", 50_000.0)
            order = _make_order()

            ks = manager._kill_switch
            fill = await manager.execute_order(
                order,
                daily_pnl_pct=0.0,
                weekly_pnl_pct=0.0,
                max_drawdown_pct=0.0,
                volatility_pct=0.0,
            )

            self.assertTrue(
                ks.can_trade(),
                "kill switch MUST NOT trip (can_trade=True) when PnL is 0",
            )
            self.assertEqual(ks._status, KillSwitchStatus.INACTIVE)
            self.assertIsNotNone(fill, "order must fill when PnL is 0 and no guard blocks")

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main(verbosity=2)
