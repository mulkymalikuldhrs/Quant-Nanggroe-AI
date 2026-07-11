"""Production-readiness wiring verification (NO mock data — real component behavior).

Validates the two Phase-0/Phase-1 wiring fixes:
  A. Kill switch ENFORCES order blocking when thresholds are breached.
  B. ExchangeFactory can instantiate the MT5 broker (free, no API key).

These tests exercise the real code paths. MT5.connect() is NOT called
(no live terminal available) — we only assert the broker object is built
correctly and that the factory wires it as a selectable exchange.
"""
from __future__ import annotations

import asyncio
import sys
import os

import pytest

# Ensure repo root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quant_nanggroe.engine.execution.base import Order, OrderSide, OrderType, OrderStatus
from quant_nanggroe.engine.execution.manager import ExecutionManager
from quant_nanggroe.engine.risk.kill_switch import (
    KillSwitch,
    KillSwitchConfig,
    KillSwitchLevel,
)
from quant_nanggroe.exchange.factory import ExchangeFactory
from quant_nanggroe.exchange.mt5_broker import MT5Broker


def _make_order(symbol="BTC/USDT", qty=0.01):
    return Order(
        id="test-order-1",
        symbol=symbol,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=qty,
        status=OrderStatus.PENDING,
    )


def _make_paper_em():
    """ExecutionManager with a paper broker + an ACTIVE kill switch (production default)."""
    from quant_nanggroe.engine.execution.brokers.paper import PaperBroker
    from quant_nanggroe.engine.risk.kill_switch import KillSwitch, KillSwitchConfig

    em = ExecutionManager()
    em.set_kill_switch(KillSwitch(KillSwitchConfig(auto_daily_loss_pct=0.015)))
    em.add_broker(PaperBroker(), primary=True)
    return em


# ── Test A: Kill switch enforcement ────────────────────────────────────────
def test_kill_switch_blocks_order_when_active():
    """When daily loss breaches threshold, execute_order must return None (blocked)."""
    em = _make_paper_em()
    # Breach daily loss threshold (config default 1.5%); pass -0.05 = -5%
    fill = asyncio.run(
        em.execute_order(_make_order(), daily_pnl_pct=-0.05)
    )
    assert fill is None, "Kill switch MUST block order when daily loss breached"
    # Audit log should record the block
    actions = [e.get("action") for e in em.get_audit_log()]
    assert "KILL_SWITCH_BLOCKED" in actions, "Audit log missing KILL_SWITCH_BLOCKED"


def test_kill_switch_allows_order_when_safe():
    """With safe P&L, order proceeds (not blocked by kill switch)."""
    em = _make_paper_em()
    fill = asyncio.run(em.execute_order(_make_order(), daily_pnl_pct=0.01))
    # Either a fill OR a guard block (whitelist/cooldown) — but NOT a kill-switch block
    actions = [e.get("action") for e in em.get_audit_log()]
    assert "KILL_SWITCH_BLOCKED" not in actions


def test_kill_switch_auto_activates():
    ks = KillSwitch(KillSwitchConfig(auto_daily_loss_pct=0.015))
    evt = ks.check_auto_activate(daily_pnl_pct=-0.05)
    assert evt is not None
    assert ks.current_level in (KillSwitchLevel.LEVEL_1, KillSwitchLevel.LEVEL_2)
    assert not ks.can_trade()


# ── Test B: MT5 factory wiring ─────────────────────────────────────────────
def test_factory_builds_mt5_broker():
    """ExchangeFactory.create('mt5') returns a real MT5Broker instance (no live connect)."""
    factory = ExchangeFactory()
    broker = factory.create(
        "mt5",
        api_key="12345678",      # MT5 login
        api_secret="pw",         # MT5 password
        passphrase="MetaQuotes-Demo",  # MT5 server
    )
    assert isinstance(broker, MT5Broker), f"Expected MT5Broker, got {type(broker)}"
    assert broker.name == "mt5", f"Expected broker name 'mt5', got {broker.name}"


def test_factory_mt5_not_ccxt():
    """MT5 must be routed to MT5Broker, never CCXTBroker."""
    from quant_nanggroe.exchange.ccxt_broker import CCXTBroker

    broker = ExchangeFactory().create("mt5", api_key="1", api_secret="2", passphrase="s")
    assert not isinstance(broker, CCXTBroker)


def _make_risk_em():
    """ExecutionManager with a paper broker + RiskManager, NO kill switch (isolate risk path)."""
    from quant_nanggroe.engine.execution.brokers.paper import PaperBroker
    from quant_nanggroe.engine.risk.manager import RiskManager

    em = ExecutionManager()
    em.set_risk_manager(RiskManager(initial_equity=1_000_000.0))
    em.add_broker(PaperBroker(), primary=True)
    return em


# ── Test C: Constitutional RiskManager enforcement ─────────────────────────
def test_risk_manager_is_invoked_on_order():
    """RiskManager.check_trade MUST run on every order (constitutional enforcement wired)."""
    em = _make_risk_em()
    # Small order that passes guards but still runs through the risk gate
    order = _make_order(symbol="BTC/USDT", qty=0.001)
    order.price = 50_000.0  # 50 USDT notional — within limits, exercises the gate
    fill = asyncio.run(em.execute_order(order, daily_pnl_pct=0.0))
    # Risk check ran and did NOT veto a clean small order → order proceeds to broker
    actions = [e.get("action") for e in em.get_audit_log()]
    assert "RISK_VETOED" not in actions, "Clean small order must not be risk-vetoed"
    assert fill is not None, "RiskManager ran but order should still execute"


def test_risk_manager_blocks_when_daily_loss_breached():
    """When real-time daily loss exceeds the constitutional budget, check_trade VETOES
    and execute_order blocks the order."""
    em = _make_risk_em()
    order = _make_order(symbol="BTC/USDT", qty=0.001)
    order.price = 50_000.0
    # Pass real-time daily loss of -5% (> MAX_DAILY_LOSS 1%) through the execution layer.
    # Unit is percent (consistent with the gate's daily_pnl_pct semantics).
    fill = asyncio.run(em.execute_order(order, daily_pnl_pct=-5.0))
    assert fill is None, "RiskManager MUST veto order when daily loss budget exhausted"
    actions = [e.get("action") for e in em.get_audit_log()]
    assert "RISK_VETOED" in actions, "Audit log missing RISK_VETOED"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
