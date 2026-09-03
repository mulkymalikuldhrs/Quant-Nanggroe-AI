"""tests/test_agentic/test_fill_ticket.py — v8.1.0 (B1 fix pin).

_make_decision must return exec_decision["ticket"] resolved from broker
truth (PositionInfo.ticket) so StrategyEvaluator.record_signal() fires.
Fail-soft: ticket 0 when unresolvable — live trading unaffected.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _make_pipeline(em):
    from quant_nanggroe.engine.agentic.autonomous import AutonomousPipeline
    pipe = AutonomousPipeline.__new__(AutonomousPipeline)
    pipe._em = em
    pipe._trailing_stop = None
    pipe._position_tracker = {}
    return pipe


def _stub_em(ticket=None):
    from quant_nanggroe.engine.execution.base import Fill, OrderSide, PositionInfo
    fill = Fill(id="f1", order_id="o1", symbol="EURUSD",
                side=OrderSide.BUY, quantity=0.01, price=1.0850)
    positions = []
    if ticket is not None:
        positions = [PositionInfo(symbol="EURUSD.vxc", quantity=0.01,
                                  avg_entry_price=1.0850, current_price=1.0850,
                                  unrealized_pnl=0.0, market_value=1085.0,
                                  ticket=ticket)]
    broker = SimpleNamespace(get_positions=AsyncMock(return_value=positions))
    em = SimpleNamespace(
        _brokers={"mt5": broker},
        execute_order=AsyncMock(return_value=fill),
        get_audit_log=lambda: [],
    )
    return em


@pytest.mark.asyncio
async def test_make_decision_returns_mt5_ticket():
    pipe = _make_pipeline(_stub_em(ticket=20188224176))
    out = await pipe._make_decision("EURUSD", "buy", 0.5, current_price=1.0850,
                                    risk_lot_size=0.01)
    assert out["execution"] == "filled"
    assert out["ticket"] == 20188224176


@pytest.mark.asyncio
async def test_make_decision_ticket_zero_fail_soft():
    pipe = _make_pipeline(_stub_em(ticket=None))
    out = await pipe._make_decision("EURUSD", "buy", 0.5, current_price=1.0850,
                                    risk_lot_size=0.01)
    assert out["execution"] == "filled"
    assert out["ticket"] == 0
