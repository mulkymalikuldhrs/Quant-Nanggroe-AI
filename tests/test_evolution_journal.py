"""Tests for EvolutionJournal — append-only SQLite journal."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from quant_nanggroe.engine.evolution.evolution_journal import EvolutionJournal

# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def journal() -> EvolutionJournal:
    """Return journal backed by a temp file. Cleans up on teardown."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    path = Path(tmp.name)
    tmp.close()
    j = EvolutionJournal(path)
    try:
        yield j
    finally:
        j.close()
        path.unlink(missing_ok=True)


# ── Journal creation / table init ─────────────────────────────────────────


class TestInit:
    def test_creates_db_file(self, journal: EvolutionJournal) -> None:
        """DB file exists after init."""
        assert journal._path.exists()

    def test_tables_exist(self, journal: EvolutionJournal) -> None:
        """All three tables created."""
        tables = journal._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        names = [r["name"] for r in tables]
        assert "closed_trades" in names
        assert "evolution_runs" in names
        assert "strategy_snapshots" in names

    def test_indexes_exist(self, journal: EvolutionJournal) -> None:
        """Expected indexes present."""
        idxs = journal._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        ).fetchall()
        idx_names = [r["name"] for r in idxs]
        assert "idx_closed_trades_strategy" in idx_names
        assert "idx_closed_trades_timestamp" in idx_names
        assert "idx_snapshots_run_id" in idx_names

    def test_close(self, journal: EvolutionJournal) -> None:
        """close() does not crash."""
        journal.close()  # first close
        journal.close()  # second close (idempotent)


# ── closed_trades ─────────────────────────────────────────────────────────


class TestRecordTrade:
    def test_record_and_retrieve(self, journal: EvolutionJournal) -> None:
        rid = journal.record_trade({
            "strategy": "test_macd",
            "symbol": "BTCUSD",
            "direction": "long",
            "pnl": 150.0,
            "pnl_pct": 2.5,
            "entry_price": 50000.0,
            "exit_price": 51250.0,
            "hold_hours": 4.5,
        })
        assert rid == 1
        trades = journal.get_recent_trades("test_macd", limit=10)
        assert len(trades) == 1
        assert trades[0]["symbol"] == "BTCUSD"
        assert trades[0]["pnl"] == 150.0

    def test_record_multiple_trades(self, journal: EvolutionJournal) -> None:
        for i in range(5):
            journal.record_trade({
                "strategy": "ema_cross",
                "symbol": "ETHUSD",
                "direction": "short",
                "pnl": 50.0 * i,
            })
        trades = journal.get_recent_trades("ema_cross")
        assert len(trades) == 5
        # newest first (DESC id)
        assert trades[0]["pnl"] == 200.0
        assert trades[-1]["pnl"] == 0.0

    def test_record_empty_trade(self, journal: EvolutionJournal) -> None:
        """Minimal trade with only required fields."""
        rid = journal.record_trade({
            "strategy": "minimal",
            "symbol": "XRPUSD",
            "direction": "long",
        })
        assert rid >= 1
        trades = journal.get_recent_trades("minimal")
        assert len(trades) == 1

    def test_all_trades(self, journal: EvolutionJournal) -> None:
        for name in ("strat_a", "strat_b", "strat_c"):
            journal.record_trade({
                "strategy": name,
                "symbol": "SOLUSD",
                "direction": "long",
                "pnl": 10.0,
            })
        all_t = journal.all_trades(limit=100)
        assert len(all_t) == 3


class TestGetStrategyStats:
    def test_empty_strategy_returns_zeros(self, journal: EvolutionJournal) -> None:
        stats = journal.get_strategy_stats("nonexistent")
        assert stats["trade_count"] == 0
        assert stats["win_rate"] == 0.0

    def test_stats_with_data(self, journal: EvolutionJournal) -> None:
        # 3 wins, 2 losses
        journal.record_trade({
            "strategy": "bb_rsi", "symbol": "BTC", "direction": "long", "pnl": 100.0
        })
        journal.record_trade({
            "strategy": "bb_rsi", "symbol": "BTC", "direction": "long", "pnl": 50.0
        })
        journal.record_trade({
            "strategy": "bb_rsi", "symbol": "BTC", "direction": "short", "pnl": 25.0
        })
        journal.record_trade({
            "strategy": "bb_rsi", "symbol": "BTC", "direction": "short", "pnl": -30.0
        })
        journal.record_trade({
            "strategy": "bb_rsi", "symbol": "BTC", "direction": "long", "pnl": -10.0
        })
        stats = journal.get_strategy_stats("bb_rsi")
        assert stats["trade_count"] == 5
        assert stats["wins"] == 3
        assert stats["losses"] == 2
        assert stats["win_rate"] == 0.6
        assert stats["avg_pnl"] == pytest.approx(27.0)

    def test_stats_zero_pnl_is_loss(self, journal: EvolutionJournal) -> None:
        journal.record_trade({
            "strategy": "edge", "symbol": "BTC", "direction": "long", "pnl": 0.0
        })
        stats = journal.get_strategy_stats("edge")
        assert stats["losses"] == 1
        assert stats["wins"] == 0

    def test_strategy_isolation(self, journal: EvolutionJournal) -> None:
        journal.record_trade({
            "strategy": "strat_a", "symbol": "A", "direction": "long", "pnl": 100.0
        })
        journal.record_trade({
            "strategy": "strat_b", "symbol": "B", "direction": "short", "pnl": 200.0
        })
        a = journal.get_strategy_stats("strat_a")
        b = journal.get_strategy_stats("strat_b")
        assert a["trade_count"] == 1
        assert b["trade_count"] == 1
        assert a["avg_pnl"] == 100.0
        assert b["avg_pnl"] == 200.0


# ── evolution_runs ────────────────────────────────────────────────────────


class TestEvolutionRuns:
    def test_record_run(self, journal: EvolutionJournal) -> None:
        rid = journal.record_run({
            "trigger": "test",
            "total_strategies": 10,
            "active_after": 8,
            "disabled_count": 1,
            "evolved_count": 2,
            "promoted_count": 0,
            "status": "completed",
        })
        assert rid == 1

    def test_get_last_run(self, journal: EvolutionJournal) -> None:
        assert journal.get_last_run() is None
        journal.record_run({"trigger": "first", "total_strategies": 5})
        journal.record_run({"trigger": "second", "total_strategies": 10})
        last = journal.get_last_run()
        assert last is not None
        assert last["trigger"] == "second"
        assert last["total_strategies"] == 10

    def test_get_recent_runs(self, journal: EvolutionJournal) -> None:
        for i in range(5):
            journal.record_run({"trigger": f"run_{i}"})
        runs = journal.get_recent_runs(limit=3)
        assert len(runs) == 3
        assert runs[0]["trigger"] == "run_4"

    def test_recording_run_with_timestamp_override(self, journal: EvolutionJournal) -> None:
        """record_run() uses timestamp from dict if provided."""
        rid = journal.record_run({
            "trigger": "manual",
            "timestamp": "2020-01-01T00:00:00.000",
        })
        assert rid == 1
        last = journal.get_last_run()
        assert last["timestamp"] == "2020-01-01T00:00:00.000"


# ── strategy_snapshots ────────────────────────────────────────────────────


class TestStrategySnapshots:
    def test_record_snapshot(self, journal: EvolutionJournal) -> None:
        run_id = journal.record_run({"trigger": "snapshot_test"})
        sid = journal.record_snapshot({
            "run_id": run_id,
            "strategy_name": "macd",
            "sharpe": 1.5,
            "win_rate": 0.6,
            "trade_count": 20,
            "action": "keep",
        })
        assert sid >= 1

    def test_get_snapshots(self, journal: EvolutionJournal) -> None:
        run_id = journal.record_run({"trigger": "multi_snapshot"})
        for name in ("strat_a", "strat_b"):
            journal.record_snapshot({
                "run_id": run_id,
                "strategy_name": name,
                "sharpe": 1.0,
                "trade_count": 10,
                "action": "keep",
            })
        snaps = journal.get_snapshots(run_id)
        assert len(snaps) == 2
        assert snaps[0]["strategy_name"] == "strat_a"
        assert snaps[1]["strategy_name"] == "strat_b"

    def test_snapshot_foreign_key(self, journal: EvolutionJournal) -> None:
        """Snapshot without valid run_id does not crash (no FK enforced by default)."""
        sid = journal.record_snapshot({
            "run_id": 999,
            "strategy_name": "orphan",
            "sharpe": 0.5,
        })
        assert sid >= 1
        snaps = journal.get_snapshots(999)
        assert len(snaps) == 1