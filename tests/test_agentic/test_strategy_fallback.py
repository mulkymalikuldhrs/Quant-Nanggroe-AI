"""tests/test_agentic/test_strategy_fallback.py — unknown-attribution pin.

record_signal / record_signal_context must never persist an empty/None
strategy string: fallback is "ensemble" (existing autonomous.py
trigger_strategy convention). Synthetic temp DBs only — never the live journal.
"""
from __future__ import annotations

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
    d = Path(tempfile.mkdtemp(prefix="qna_fallback_"))
    yield d
    shutil.rmtree(str(d), ignore_errors=True)


@pytest.mark.parametrize("bad", ["", "   ", None])
def test_record_signal_falls_back_to_ensemble(workdir, bad):
    from quant_nanggroe.engine.agentic.strategy_evaluator import StrategyEvaluator

    ev = StrategyEvaluator(
        journal_db=workdir / "j.db",
        eval_db=workdir / "e.db",
    )
    ev.record_signal(bad, "EURUSD", 777001, 1.0850)
    con = sqlite3.connect(str(workdir / "e.db"))
    try:
        row = con.execute(
            "SELECT strategy FROM signal_outcomes WHERE ticket=777001").fetchone()
    finally:
        con.close()
    assert row is not None
    assert row[0] == "ensemble"


@pytest.mark.parametrize("bad", ["", "   ", None])
def test_record_signal_context_falls_back_to_ensemble(workdir, monkeypatch, bad):
    import quant_nanggroe.engine.journal_sync as js

    db = workdir / "ctx.db"
    js._ensure_schema(db)
    monkeypatch.setattr(js, "_get_db", lambda: db)
    js.record_signal_context(
        symbol="EURUSD", strategy=bad, entry_price=1.0850,
        sl=1.0800, tp=1.0950, confidence=0.6)
    con = sqlite3.connect(str(db))
    try:
        row = con.execute(
            "SELECT strategy FROM signal_context ORDER BY id DESC LIMIT 1").fetchone()
    finally:
        con.close()
    assert row is not None
    assert row[0] == "ensemble"


def test_record_signal_keeps_valid_strategy(workdir):
    from quant_nanggroe.engine.agentic.strategy_evaluator import StrategyEvaluator

    ev = StrategyEvaluator(
        journal_db=workdir / "j.db",
        eval_db=workdir / "e.db",
    )
    ev.record_signal("smc", "XAUUSD", 777002, 2650.0)
    con = sqlite3.connect(str(workdir / "e.db"))
    try:
        row = con.execute(
            "SELECT strategy FROM signal_outcomes WHERE ticket=777002").fetchone()
    finally:
        con.close()
    assert row[0] == "smc"
