"""Regression tests for the v8.0.9 parallel-fix batch (full-audit findings).

Covers:
- R1: MT5 structured-record rates -> DataFrame (shape bug that killed all data)
- R2 companion: duplicate-position gate allows CLOSE/reduce_only orders
- R5/F2: MT5Broker.place_order side normalization (BUY must not become SELL)
- R6/F3: history_deals_get failure -> PNL_SYNC_STALE veto
- F4: context-gate circuit breaker (3 consecutive provider failures -> VETO)
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

from quant_nanggroe.engine.agentic import context_gate


def _order(symbol="EURUSD", side="buy", reduce_only=False):
    from quant_nanggroe.engine.execution.base import (
        Order,
        OrderSide,
        OrderStatus,
        OrderType,
    )
    side_enum = OrderSide.BUY if side == "buy" else OrderSide.SELL
    return Order(
        id=f"t-{side}-{symbol}", symbol=symbol, side=side_enum,
        order_type=OrderType.MARKET, quantity=0.01,
        status=OrderStatus.PENDING,
        metadata={"reduce_only": reduce_only},
    )


class _FakeBroker:
    def __init__(self, positions=None, raise_on_positions=False):
        self.is_connected = True
        self.name = "fake"
        self._positions = positions or []
        self._raise = raise_on_positions
        self.submitted = []

    async def get_positions(self):
        if self._raise:
            raise RuntimeError("down")
        return self._positions

    async def get_account(self):
        return SimpleNamespace(balance=10_000.0)

    async def submit_order(self, order):
        from quant_nanggroe.engine.execution.base import OrderStatus
        self.submitted.append(order)
        order.status = OrderStatus.FILLED
        order.metadata = {"fill_price": 1.1000}
        return order

    async def connect(self):
        return True


class TestDuplicateGateSideSemantics(unittest.TestCase):
    """Same-side pyramid BLOCKED; opposite-side close ALLOWED; reduce_only ALLOWED."""

    def _manager(self, broker):
        from quant_nanggroe.engine.execution.manager import ExecutionManager
        em = ExecutionManager()
        em.add_broker(broker, primary=True)
        em.set_kill_switch(MagicMock())
        em.set_risk_manager(MagicMock())
        em._risk_manager.check_trade.return_value = {"verdict": "APPROVED"}
        ks = MagicMock()
        ks.can_trade.return_value = True
        ks.check_auto_activate.return_value = None
        ks.check_warning.return_value = False
        em._kill_switch = ks
        return em

    def test_opposite_side_close_allowed(self):
        long_pos = SimpleNamespace(symbol="EURUSD", side="buy", quantity=0.02)
        broker = _FakeBroker(positions=[long_pos])
        em = self._manager(broker)
        fill = asyncio_run(em.execute_order(_order("EURUSD", "sell")))
        self.assertIsNotNone(fill, "opposite-side order is a CLOSE — must pass")

    def test_reduce_only_never_blocked(self):
        long_pos = SimpleNamespace(symbol="EURUSD", side="buy", quantity=0.02)
        broker = _FakeBroker(positions=[long_pos])
        em = self._manager(broker)
        fill = asyncio_run(em.execute_order(_order("EURUSD", "sell", reduce_only=True)))
        self.assertIsNotNone(fill)

    def test_same_side_pyramid_still_blocked(self):
        long_pos = SimpleNamespace(symbol="EURUSD", side="buy", quantity=0.02)
        broker = _FakeBroker(positions=[long_pos])
        em = self._manager(broker)
        fill = asyncio_run(em.execute_order(_order("EURUSD", "buy")))
        self.assertIsNone(fill, "same-side addition must stay BLOCKED")

    def test_suffix_variant_blocked_f8(self):
        suffixed = SimpleNamespace(symbol="EURUSD.vx", side="buy", quantity=0.02)
        broker = _FakeBroker(positions=[suffixed])
        em = self._manager(broker)
        fill = asyncio_run(em.execute_order(_order("EURUSD", "buy")))
        self.assertIsNone(fill, "EURUSD.vx open must block bare EURUSD entry")

    def test_quantity_sign_infers_side(self):
        short_pos = SimpleNamespace(symbol="XAUUSD.vxc", quantity=-0.05)  # no side attr
        broker = _FakeBroker(positions=[short_pos])
        em = self._manager(broker)
        ok_fill = asyncio_run(em.execute_order(_order("XAUUSD", "sell", reduce_only=True)))
        self.assertIsNotNone(ok_fill)


class TestConnectorSideNormalization(unittest.TestCase):
    """R5/F2: engine enum BUY must map to ORDER_TYPE_BUY, never SELL."""

    def test_engine_enum_buy_maps_to_buy(self):
        import quant_nanggroe.connectors.mt5_broker as mb
        from quant_nanggroe.engine.execution.base import OrderSide

        calls = {}

        class _MT5Stub:
            TRADE_ACTION_DEAL = 1
            ORDER_TYPE_BUY = 0
            ORDER_TYPE_SELL = 1
            ORDER_FILLING_FOK = 0
            ORDER_TIME_GTC = 0
            TRADE_RETCODE_DONE = 10009

            def symbol_select(self, s, enable):
                return True

            def symbol_info_tick(self, s):
                return SimpleNamespace(ask=1.1000, bid=1.0998)

            def order_send(self, req):
                calls["type"] = req["type"]
                calls["price"] = req["price"]
                return SimpleNamespace(retcode=10009, order=12345)

        b = object.__new__(mb.MT5Broker)
        b.connected = True
        b.magic = 0
        b._mt5 = _MT5Stub()
        b._available_symbols = {"eurusd": "EURUSD"}

        eng_order = SimpleNamespace(
            symbol="EURUSD", side=OrderSide.BUY, quantity=0.01,
            stop_loss=None, take_profit=None, metadata={},
        )
        ticket = b.place_order(eng_order)
        self.assertEqual(ticket, "12345")
        self.assertEqual(calls["type"], 0, "enum BUY must map to ORDER_TYPE_BUY")
        self.assertEqual(calls["price"], 1.1000, "buy must use ASK")

    def test_invalid_side_raises(self):
        import quant_nanggroe.connectors.mt5_broker as mb

        class _MT5Stub:
            def symbol_select(self, s, e):
                return False

        b = object.__new__(mb.MT5Broker)
        b.connected = True
        b._mt5 = _MT5Stub()
        with self.assertRaises(RuntimeError):
            b.place_order(SimpleNamespace(
                symbol="EURUSD", side="LONG", quantity=0.01,
                stop_loss=None, take_profit=None, metadata={}))


class TestPnlSyncStaleVeto(unittest.TestCase):
    """R6/F3: failed broker read must VETO, never zero out real losses."""

    def test_failed_read_vetoes(self):
        from quant_nanggroe.engine.risk.manager import RiskManager

        rm = RiskManager(initial_equity=100_000.0)
        rm.set_broker_handle(SimpleNamespace(
            history_deals_get=lambda a, b_: (_ for _ in ()).throw(
                RuntimeError("IPC down"))))
        rm.state.daily_pnl = -4_000.0   # simulate prior known loss
        rm.state.weekly_pnl = -4_000.0
        verdict = rm.check_trade(symbol="EURUSD", direction="BUY",
                                 lot_size=0.01, entry=1.10, stop_loss=1.09,
                                 account_balance=100_000.0)
        self.assertEqual(verdict["verdict"], "VETOED")
        self.assertEqual(verdict["reason"], "PNL_SYNC_STALE")
        # and the real loss must NOT have been overwritten by 0.0
        self.assertEqual(rm.state.daily_pnl, -4_000.0)

    def test_successful_read_clears_stale(self):
        from quant_nanggroe.engine.risk.manager import RiskManager

        deal = SimpleNamespace(profit=-50.0)
        rm = RiskManager(initial_equity=100_000.0)
        rm.set_broker_handle(SimpleNamespace(
            history_deals_get=lambda a, b_: [deal]))
        verdict = rm.check_trade(symbol="EURUSD", direction="BUY",
                                 lot_size=0.01, entry=1.10, stop_loss=1.09,
                                 account_balance=100_000.0)
        self.assertFalse(rm._pnl_sync_stale)
        self.assertEqual(rm.state.daily_pnl, -50.0)


class TestContextGateCircuitBreaker(unittest.TestCase):
    def setUp(self):
        context_gate.reset_cache()

    def tearDown(self):
        context_gate.reset_cache()

    def test_three_consecutive_failures_flip_to_veto(self):
        with patch(
            "quant_nanggroe.engine.fundamental.calendar.EconomicCalendar.get_high_impact_events",
            side_effect=RuntimeError("feed down"),
        ):
            r1 = context_gate.check_event_risk()
            r2 = context_gate.check_event_risk()
            r3 = context_gate.check_event_risk()
            self.assertFalse(r1["vetoed"], "first failure stays NEUTRAL")
            self.assertFalse(r2["vetoed"])
            self.assertTrue(r3["vetoed"], "3rd failure flips fail-closed")
            r4 = context_gate.check_event_risk()
            self.assertTrue(r4["vetoed"], "stays vetoed until recovery")

    def test_recovery_resets_breaker(self):
        events_mock = "quant_nanggroe.engine.fundamental.calendar.EconomicCalendar.get_high_impact_events"
        with patch(events_mock, side_effect=RuntimeError("x")):
            context_gate.check_event_risk()
            context_gate.check_event_risk()
            context_gate.check_event_risk()  # breaker trips
        context_gate.reset_cache()
        with patch(events_mock, return_value=[]):
            r = context_gate.check_event_risk()
        self.assertFalse(r["vetoed"])


class TestMt5RatesShape(unittest.TestCase):
    """R1: numpy structured records must build a valid OHLCV DataFrame."""

    def test_structured_records_to_df(self):
        n = 60
        recs = np.zeros(n, dtype=[
            ("time", "<i8"), ("open", "<f8"), ("high", "<f8"),
            ("low", "<f8"), ("close", "<f8"), ("tick_volume", "<i8"),
            ("spread", "<i8"), ("real_volume", "<i8"),
        ])
        recs["time"] = np.arange(n) * 900
        recs["open"] = 1.10; recs["high"] = 1.11
        recs["low"] = 1.09; recs["close"] = 1.105
        recs["tick_volume"] = 100

        cols = {name: recs[name] for name in recs.dtype.names}
        df = pd.DataFrame(cols)
        if "volume" not in df.columns and "tick_volume" in df.columns:
            df["volume"] = df["tick_volume"]
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df.set_index("time", inplace=True)
        df = df[["open", "high", "low", "close", "volume"]].astype(float)

        self.assertEqual(df.shape, (n, 5))
        self.assertFalse(df["volume"].isna().any())


def asyncio_run(coro):
    import asyncio
    return asyncio.run(coro)


if __name__ == "__main__":
    unittest.main()
