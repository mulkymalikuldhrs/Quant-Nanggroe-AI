"""G1 + G3 hardening tests — devbot 2026-08-03.

These tests verify the fail-closed behavior that was MISSING from the live path:
1. G1: TradeJournal._init_db + db_healthy — schema must init or report dead
2. G3: MT5Adapter.account_balance returns -1.0 on failure (not fallback seed)
   RiskGuard.PurifiedEngine.start/cycle abort on MT5 down

No broker required — tests use temp dirs + monkey-patching.
"""
from __future__ import annotations
import os, sys, sqlite3, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "quant_nanggroe"))

# ──────────────────────────────────────────────
# G1: TradeJournal fail-closed init + db_healthy
# ──────────────────────────────────────────────
import importlib
trade_journal = importlib.import_module("trade_journal")
TradeJournal = trade_journal.TradeJournal


def test_journal_creates_schema_on_init(tmp_path):
    """G1: _init_db must create 'trades' table. db_healthy() returns True."""
    db = tmp_path / "test_journal.db"
    j = TradeJournal(str(db))
    assert j._init_ok is True
    assert j.db_healthy() is True


def test_journal_db_healthy_returns_false_on_corruption(tmp_path):
    """G1: a pre-existing corrupt/zero-byte DB must be detected as unhealthy."""
    db = tmp_path / "corrupt.db"
    db.write_bytes(b"not a database")  # garbage header
    j = TradeJournal(str(db))
    # _init_ok is True (we tried), but db_healthy() must catch corruption
    assert j.db_healthy() is False


def test_journal_record_open_then_close(tmp_path):
    """G1+G3: full round-trip — record_open, then record_close via _on_closed path."""
    db = tmp_path / "roundtrip.db"
    j = TradeJournal(str(db))
    j.record_open(ticket=12345, strategy="SMC", symbol="EURUSD.vx",
                  side="buy", entry=1.1000, sl=1.0950, tp=1.1050,
                  confidence=0.75, comment="SMC:EURUSD.vx")
    rec = j.get_open_trade(12345)
    assert rec is not None
    assert rec["ticket"] == 12345
    assert rec["strategy"] == "SMC"
    assert rec["outcome"] == "open"
    # Close it
    j.record_close(12345, exit_price=1.1040, pnl=40.0)
    closed = j.get_closed_trades()
    assert len(closed) == 1
    assert closed[0]["outcome"] == "win"
    assert abs(closed[0]["pnl"] - 40.0) < 0.01


def test_journal_record_close_without_open_is_noop(tmp_path):
    """G1-hardening: closing a non-existent ticket must not crash."""
    db = tmp_path / "noop.db"
    j = TradeJournal(str(db))
    # Should not raise even though ticket 99999 has no open record
    j.record_close(99999, exit_price=1.1, pnl=0.0)


# ──────────────────────────────────────────────
# G3: MT5Adapter fail-closed account_balance
# ──────────────────────────────────────────────
engine_bridge = importlib.import_module("engine_production_bridge_purified")
MT5Adapter = engine_bridge.MT5Adapter
RiskGuard = engine_bridge.RiskGuard
PurifiedEngine = engine_bridge.PurifiedEngine
Signal = engine_bridge.Signal


def test_account_balance_returns_negative_when_uninit():
    """G3-core: account_balance must return -1.0 (MT5_DOWN signal) when
    MT5 is not initialized, NOT a seed/fallback balance."""
    adapter = MT5Adapter()
    bal = adapter.account_balance()
    assert bal == -1.0  # MT5_DOWN sentinel, not 0.0 or 10000.0


def test_account_balance_returns_negative_on_exception(monkeypatch):
    """G3-core: if mt5.account_info() raises, return -1.0 (NOT swallow)."""
    adapter = MT5Adapter()
    adapter._initialized = True
    adapter._mt5_loaded = True
    # Fake mt5 module that raises on account_info
    class FakeMT5:
        def account_info(self):
            raise ConnectionError("network down")
    adapter._mt5_mod = FakeMT5()
    bal = adapter.account_balance()
    assert bal == -1.0


def test_purified_engine_start_aborts_on_mt5_down(monkeypatch):
    """G3-hardening: if MT5 is down, engine must NOT activate — no phantom trades."""
    eng = PurifiedEngine(initial_balance=10000.0)
    # Simulate MT5 connect failure — account_balance returns -1.0
    monkeypatch.setattr(eng.mt5, "connect", lambda: (_ for _ in ()).throw(
        RuntimeError("MT5 not available")))
    # start() will call connect() which raises
    import pytest
    with pytest.raises(RuntimeError):
        eng.start()
    assert eng.active is False


def test_purified_engine_cycle_aborts_on_stale_balance(monkeypatch):
    """G3-cycle: if account_balance returns -1.0 (MT5 down mid-cycle),
    cycle() must return [] (fail-closed), not trade on phantom balance."""
    eng = PurifiedEngine(initial_balance=5000.0)
    eng.active = True
    eng.risk.balance = 5000.0
    # Force account_balance to return -1.0 (MT5 dropped mid-run)
    monkeypatch.setattr(eng.mt5, "account_balance", lambda: -1.0)
    result = eng.cycle([])
    assert result == []
    # Balance must NOT have changed (no phantom update)
    assert eng.risk.balance == 5000.0


# ──────────────────────────────────────────────
# G1-deep: initialize() fail-closed on dead journal
# ──────────────────────────────────────────────
def test_autonomous_cycle_init_aborts_on_dead_journal(tmp_path, monkeypatch):
    """G1-deep: if TradeJournal.db_healthy() is False, initialize() must
    raise RuntimeError (fail-closed), not proceed with journal=None.
    """
    from autonomous_cycle import AutonomousCycle
    # Patch TradeJournal to simulate lock-contended 0-byte DB
    class DeadJournal:
        _init_ok = False
        def db_healthy(self): return False
    import autonomous_cycle as ac_mod
    monkeypatch.setattr(ac_mod, "TradeJournal", lambda: DeadJournal())
    cyc = AutonomousCycle()
    import pytest
    with pytest.raises(RuntimeError, match="journal"):
        cyc.initialize()
    # Fail-closed proof: dead journal detected, error explicitly raised
    assert cyc.journal is not None
    assert cyc.journal._init_ok is False
