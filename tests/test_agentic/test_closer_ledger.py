"""tests/test_agentic/test_closer_ledger.py — PROMPT 6 (closer-ledger) pin.

record_outcome must close the loop on temp DBs only (never the live journal):
matched closes update by ticket; unmatched closes warn with ticket id, no crash.
"""
from __future__ import annotations

import logging
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def workdir():
    d = Path(tempfile.mkdtemp(prefix="qna_closer_"))
    yield d
    shutil.rmtree(str(d), ignore_errors=True)


def _ev(workdir):
    from quant_nanggroe.engine.agentic.strategy_evaluator import StrategyEvaluator

    return StrategyEvaluator(
        journal_db=workdir / "j.db",
        eval_db=workdir / "e.db",
    )


def _row(workdir, ticket):
    con = sqlite3.connect(str(workdir / "e.db"))
    try:
        return con.execute(
            "SELECT strategy, symbol, ticket, exit_price, pnl, outcome, closed_at"
            " FROM signal_outcomes WHERE ticket=?", (ticket,)).fetchone()
    finally:
        con.close()


def test_outcome_matched_win_closes_by_ticket(workdir):
    ev = _ev(workdir)
    ev.record_signal("smc", "EURUSD", 900001, 1.0850)
    ev.record_outcome(900001, 1.0950, 12.5)
    row = _row(workdir, 900001)
    assert row is not None
    assert row[3] == pytest.approx(1.0950)
    assert row[4] == pytest.approx(12.5)
    assert row[5] == "win"
    assert row[6]  # closed_at stamped


def test_outcome_unmatched_warns_with_ticket_no_crash(workdir, caplog):
    ev = _ev(workdir)
    with caplog.at_level(logging.WARNING, logger="QNA.StrategyEvaluator"):
        ev.record_outcome(999888777, 1.0800, -3.0)  # no crash
    assert any(
        "record_outcome unmatched" in r.message and "999888777" in r.message
        for r in caplog.records
    )
    assert _row(workdir, 999888777) is None


def test_outcome_loss_and_breakeven_classification(workdir):
    ev = _ev(workdir)
    ev.record_signal("smc", "XAUUSD", 900002, 2650.0)
    ev.record_signal("smc", "XAUUSD", 900003, 2651.0)
    ev.record_outcome(900002, 2640.0, -8.25)
    ev.record_outcome(900003, 2651.0, 0.0)
    assert _row(workdir, 900002)[5] == "loss"
    assert _row(workdir, 900003)[5] == "breakeven"


def test_signal_outcome_roundtrip_join_key_ticket(workdir):
    ev = _ev(workdir)
    ev.record_signal("ensemble", "EURUSD", 900004, 1.0900)
    ev.record_outcome(900004, 1.0920, 4.0)
    row = _row(workdir, 900004)
    assert row is not None
    assert (row[0], row[1], row[2]) == ("ensemble", "EURUSD", 900004)
    assert row[5] == "win"
