"""Append-only SQLite journal for evolution loop.

Tracks closed trades, evolution runs, and strategy snapshots.
All tables use INTEGER PRIMARY KEY for auto-increment.
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


_JDBC_DATETIME = "YYYY-MM-DDTHH:MM:SS.sss"  # ISO-8601 format


_DDL = """
CREATE TABLE IF NOT EXISTS closed_trades (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT    NOT NULL,
    symbol          TEXT    NOT NULL,
    strategy        TEXT    NOT NULL,
    timeframe       TEXT,
    direction       TEXT    NOT NULL,
    entry_price     REAL,
    exit_price      REAL,
    pnl             REAL,
    pnl_pct         REAL,
    hold_hours      REAL,
    spread          REAL,
    entry_reason    TEXT,
    sl_type         TEXT,
    tags            TEXT
);

CREATE TABLE IF NOT EXISTS evolution_runs (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp         TEXT    NOT NULL,
    trigger           TEXT,
    account           TEXT,
    total_strategies  INTEGER DEFAULT 0,
    active_after      INTEGER DEFAULT 0,
    disabled_count    INTEGER DEFAULT 0,
    evolved_count     INTEGER DEFAULT 0,
    promoted_count    INTEGER DEFAULT 0,
    status            TEXT    DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS strategy_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          INTEGER NOT NULL,
    strategy_name   TEXT    NOT NULL,
    timeframe       TEXT,
    sharpe          REAL,
    sortino         REAL,
    win_rate        REAL,
    profit_factor   REAL,
    max_drawdown    REAL,
    avg_return      REAL,
    trade_count     INTEGER DEFAULT 0,
    action          TEXT,
    action_reason   TEXT,
    FOREIGN KEY (run_id) REFERENCES evolution_runs(id)
);

CREATE INDEX IF NOT EXISTS idx_closed_trades_strategy ON closed_trades(strategy);
CREATE INDEX IF NOT EXISTS idx_closed_trades_timestamp ON closed_trades(timestamp);
CREATE INDEX IF NOT EXISTS idx_snapshots_run_id ON strategy_snapshots(run_id);
"""


class EvolutionJournal:
    """Append-only SQLite journal for evolution loop data."""

    def __init__(self, path: str | Path = "data/evolution_journal.db") -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()

    # ── Connection management ────────────────────────────────────────

    @property
    def _conn(self) -> sqlite3.Connection:
        """Thread-local connection."""
        conn: sqlite3.Connection | None = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(str(self._path))
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn = conn
        return conn

    def _init_db(self) -> None:
        self._conn.executescript(_DDL)
        self._conn.commit()

    def close(self) -> None:
        conn: sqlite3.Connection | None = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None

    # ── closed_trades ─────────────────────────────────────────────────

    def record_trade(self, trade: dict[str, Any]) -> int:
        """Insert a closed trade. Returns row id."""
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        stmt = """INSERT INTO closed_trades
            (timestamp, symbol, strategy, timeframe, direction,
             entry_price, exit_price, pnl, pnl_pct, hold_hours,
             spread, entry_reason, sl_type, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        cur = self._conn.execute(stmt, (
            trade.get("timestamp", now),
            trade.get("symbol", ""),
            trade.get("strategy", ""),
            trade.get("timeframe"),
            trade.get("direction", ""),
            trade.get("entry_price"),
            trade.get("exit_price"),
            trade.get("pnl"),
            trade.get("pnl_pct"),
            trade.get("hold_hours"),
            trade.get("spread"),
            trade.get("entry_reason"),
            trade.get("sl_type"),
            trade.get("tags"),
        ))
        self._conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def get_recent_trades(
        self, strategy_name: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Return most recent closed trades for a strategy."""
        cur = self._conn.execute(
            "SELECT * FROM closed_trades WHERE strategy=? ORDER BY id DESC LIMIT ?",
            (strategy_name, limit),
        )
        return [dict(r) for r in cur.fetchall()]

    def get_strategy_stats(self, strategy_name: str) -> dict[str, Any]:
        """Return aggregate stats for a strategy from all closed trades."""
        cur = self._conn.execute(
            """SELECT
                COUNT(*)                                         AS trade_count,
                COALESCE(AVG(pnl), 0.0)                         AS avg_pnl,
                COALESCE(AVG(pnl_pct), 0.0)                     AS avg_pnl_pct,
                COALESCE(SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END), 0) AS wins,
                COALESCE(SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END), 0) AS losses
               FROM closed_trades
               WHERE strategy=?""",
            (strategy_name,),
        )
        row = cur.fetchone()
        if row is None or row["trade_count"] == 0:
            return {"trade_count": 0, "win_rate": 0.0, "avg_pnl": 0.0}

        win_rate = row["wins"] / row["trade_count"] if row["trade_count"] else 0.0
        return {
            "trade_count": row["trade_count"],
            "wins": row["wins"],
            "losses": row["losses"],
            "win_rate": round(win_rate, 4),
            "avg_pnl": round(row["avg_pnl"], 4),
            "avg_pnl_pct": round(row["avg_pnl_pct"], 4),
        }

    def all_trades(self, limit: int = 1000) -> list[dict[str, Any]]:
        """Return recent trades across all strategies."""
        cur = self._conn.execute(
            "SELECT * FROM closed_trades ORDER BY id DESC LIMIT ?", (limit,)
        )
        return [dict(r) for r in cur.fetchall()]

    # ── evolution_runs ────────────────────────────────────────────────

    def record_run(self, run: dict[str, Any]) -> int:
        """Insert an evolution run. Returns row id."""
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        stmt = """INSERT INTO evolution_runs
            (timestamp, trigger, account, total_strategies,
             active_after, disabled_count, evolved_count, promoted_count, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        cur = self._conn.execute(stmt, (
            run.get("timestamp", now),
            run.get("trigger", ""),
            run.get("account", ""),
            run.get("total_strategies", 0),
            run.get("active_after", 0),
            run.get("disabled_count", 0),
            run.get("evolved_count", 0),
            run.get("promoted_count", 0),
            run.get("status", "pending"),
        ))
        self._conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def get_last_run(self) -> dict[str, Any] | None:
        """Return most recent evolution run."""
        cur = self._conn.execute(
            "SELECT * FROM evolution_runs ORDER BY id DESC LIMIT 1"
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def get_recent_runs(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return recent evolution runs."""
        cur = self._conn.execute(
            "SELECT * FROM evolution_runs ORDER BY id DESC LIMIT ?", (limit,)
        )
        return [dict(r) for r in cur.fetchall()]

    # ── strategy_snapshots ────────────────────────────────────────────

    def record_snapshot(self, snapshot: dict[str, Any]) -> int:
        """Insert a strategy snapshot linked to a run. Returns row id."""
        stmt = """INSERT INTO strategy_snapshots
            (run_id, strategy_name, timeframe, sharpe, sortino,
             win_rate, profit_factor, max_drawdown, avg_return,
             trade_count, action, action_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        cur = self._conn.execute(stmt, (
            snapshot.get("run_id", 0),
            snapshot.get("strategy_name", ""),
            snapshot.get("timeframe"),
            snapshot.get("sharpe"),
            snapshot.get("sortino"),
            snapshot.get("win_rate"),
            snapshot.get("profit_factor"),
            snapshot.get("max_drawdown"),
            snapshot.get("avg_return"),
            snapshot.get("trade_count", 0),
            snapshot.get("action"),
            snapshot.get("action_reason"),
        ))
        self._conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def get_snapshots(self, run_id: int) -> list[dict[str, Any]]:
        """Return all snapshots for an evolution run."""
        cur = self._conn.execute(
            "SELECT * FROM strategy_snapshots WHERE run_id=? ORDER BY id",
            (run_id,),
        )
        return [dict(r) for r in cur.fetchall()]
