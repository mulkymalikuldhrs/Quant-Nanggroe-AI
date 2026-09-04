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


def _stub_em_delayed(ticket):
    """Broker whose positions appear only on the 2nd poll (MT5 latency)."""
    from quant_nanggroe.engine.execution.base import Fill, OrderSide, PositionInfo
    fill = Fill(id="f1", order_id="o1", symbol="EURUSD",
                side=OrderSide.BUY, quantity=0.01, price=1.0850)
    positions = [PositionInfo(symbol="EURUSD.vxc", quantity=0.01,
                              avg_entry_price=1.0850, current_price=1.0850,
                              unrealized_pnl=0.0, market_value=1085.0,
                              ticket=ticket)]
    broker = SimpleNamespace(get_positions=AsyncMock(side_effect=[[], positions]))
    em = SimpleNamespace(
        _brokers={"mt5": broker},
        execute_order=AsyncMock(return_value=fill),
        get_audit_log=lambda: [],
    )
    return em


@pytest.mark.asyncio
async def test_make_decision_ticket_retry_second_poll():
    """v8.1.4: position visible only on 2nd poll must still resolve (no 0-ticket)."""
    pipe = _make_pipeline(_stub_em_delayed(ticket=20188224177))
    out = await pipe._make_decision("EURUSD", "buy", 0.5, current_price=1.0850,
                                    risk_lot_size=0.01)
    assert out["execution"] == "filled"
    assert out["ticket"] == 20188224177


def test_signal_context_rowid_linkage_contract():
    """v8.1.4 BREAK-B pin: the fixed SELECT must expose rowid so the UPDATE links.
    Replicates the exact query shape from journal_sync (rowid first column)."""
    import sqlite3
    con = sqlite3.connect(":memory:")
    con.execute("""CREATE TABLE signal_context (
        symbol TEXT, entry_price REAL, ticket INTEGER,
        sl REAL, tp REAL, confidence REAL, atr REAL, lot_size REAL,
        timestamp TEXT, filled INTEGER DEFAULT 0, pnl REAL DEFAULT 0.0,
        outcome TEXT DEFAULT '', hit_type TEXT DEFAULT '')""")
    con.execute("""INSERT INTO signal_context
        (symbol, entry_price, ticket, sl, tp, confidence, atr, lot_size, timestamp)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        ("EURUSD", 1.0850, None, 1.0800, 1.0900, 0.5, 0.001, 0.01, "2026-09-04T00:00:00"))
    sig_row = con.execute(
        """SELECT rowid, sl, tp, confidence, atr, lot_size FROM signal_context
           WHERE symbol=? AND ticket IS NULL
             AND ABS(entry_price - ?) < 0.002
           ORDER BY timestamp DESC LIMIT 1""",
        ("EURUSD", 1.0850)).fetchone()
    assert sig_row is not None
    con.execute(
        "UPDATE signal_context SET ticket=?, filled=1, pnl=?, outcome=?, hit_type=? WHERE rowid=?",
        (20188224176, 3.67, "win", "", sig_row[0]))
    linked = con.execute("SELECT ticket, filled FROM signal_context").fetchone()
    assert linked[0] == 20188224176
    assert linked[1] == 1
