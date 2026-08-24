"""Trade History — SQLite-backed unlimited trade/signal history.

Replaces the 500-event JSON buffer with persistent SQLite storage.
Every candle close event, signal, and trade is logged with full metadata.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = Path("data/trade_history.db")


@dataclass
class TradeEvent:
    """A single trade/signal event."""
    id: Optional[int] = None
    symbol: str = ""
    timeframe: str = ""
    signal: str = "hold"
    confidence: float = 0.0
    traded: bool = False
    notified: bool = False
    regime: str = "unknown"
    strategy: str = "ensemble"
    entry_price: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
    pnl: float = 0.0
    duration_ms: float = 0.0
    error: str = ""
    metadata: str = "{}"
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class TradeHistory:
    """SQLite-backed trade history with unlimited storage."""

    def __init__(self, db_path: str | Path | None = None):
        self._db_path = Path(db_path) if db_path else DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trade_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    signal TEXT NOT NULL DEFAULT 'hold',
                    confidence REAL NOT NULL DEFAULT 0.0,
                    traded INTEGER NOT NULL DEFAULT 0,
                    notified INTEGER NOT NULL DEFAULT 0,
                    regime TEXT DEFAULT 'unknown',
                    strategy TEXT DEFAULT 'ensemble',
                    entry_price REAL DEFAULT 0.0,
                    sl REAL DEFAULT 0.0,
                    tp REAL DEFAULT 0.0,
                    pnl REAL DEFAULT 0.0,
                    duration_ms REAL DEFAULT 0.0,
                    error TEXT DEFAULT '',
                    metadata TEXT DEFAULT '{}',
                    timestamp TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trade_events_symbol
                ON trade_events(symbol)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trade_events_timeframe
                ON trade_events(timeframe)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trade_events_timestamp
                ON trade_events(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trade_events_traded
                ON trade_events(traded)
            """)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def add_event(self, event: TradeEvent) -> int:
        """Add a trade event to history. Returns the event ID."""
        with self._conn() as conn:
            cursor = conn.execute("""
                INSERT INTO trade_events
                (symbol, timeframe, signal, confidence, traded, notified,
                 regime, strategy, entry_price, sl, tp, pnl,
                 duration_ms, error, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.symbol, event.timeframe, event.signal, event.confidence,
                1 if event.traded else 0, 1 if event.notified else 0,
                event.regime, event.strategy, event.entry_price,
                event.sl, event.tp, event.pnl,
                event.duration_ms, event.error, event.metadata, event.timestamp,
            ))
            return cursor.lastrowid or 0

    def query(
        self,
        symbol: str | None = None,
        timeframe: str | None = None,
        traded_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """Query trade events with filters."""
        conditions = []
        params = []

        if symbol:
            conditions.append("symbol = ?")
            params.append(symbol)
        if timeframe:
            conditions.append("timeframe = ?")
            params.append(timeframe)
        if traded_only:
            conditions.append("traded = 1")

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM trade_events {where} ORDER BY id DESC LIMIT ? OFFSET ?",
                params + [limit, offset],
            ).fetchall()
            return [dict(r) for r in rows]

    def count(
        self,
        symbol: str | None = None,
        timeframe: str | None = None,
        traded_only: bool = False,
    ) -> int:
        """Count events matching filters."""
        conditions = []
        params = []

        if symbol:
            conditions.append("symbol = ?")
            params.append(symbol)
        if timeframe:
            conditions.append("timeframe = ?")
            params.append(timeframe)
        if traded_only:
            conditions.append("traded = 1")

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        with self._conn() as conn:
            row = conn.execute(
                f"SELECT COUNT(*) as cnt FROM trade_events {where}", params
            ).fetchone()
            return row["cnt"] if row else 0

    def stats(self) -> dict:
        """Get aggregate statistics."""
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) as cnt FROM trade_events").fetchone()["cnt"]
            trades = conn.execute("SELECT COUNT(*) as cnt FROM trade_events WHERE traded = 1").fetchone()["cnt"]
            signals = conn.execute("SELECT COUNT(*) as cnt FROM trade_events WHERE signal != 'hold' AND traded = 0").fetchone()["cnt"]
            errors = conn.execute("SELECT COUNT(*) as cnt FROM trade_events WHERE error != ''").fetchone()["cnt"]

            # Per-symbol stats
            syms = conn.execute("""
                SELECT symbol, COUNT(*) as total,
                       SUM(CASE WHEN traded = 1 THEN 1 ELSE 0 END) as trades,
                       AVG(confidence) as avg_confidence
                FROM trade_events GROUP BY symbol ORDER BY total DESC
            """).fetchall()

            # Per-TF stats
            tfs = conn.execute("""
                SELECT timeframe, COUNT(*) as total,
                       SUM(CASE WHEN traded = 1 THEN 1 ELSE 0 END) as trades,
                       AVG(confidence) as avg_confidence
                FROM trade_events GROUP BY timeframe ORDER BY total DESC
            """).fetchall()

            # Last 24h
            last_24h = conn.execute("""
                SELECT COUNT(*) as cnt FROM trade_events
                WHERE timestamp > datetime('now', '-1 day')
            """).fetchone()["cnt"]

            return {
                "total": total,
                "trades": trades,
                "signals": signals,
                "errors": errors,
                "last_24h": last_24h,
                "by_symbol": [dict(r) for r in syms],
                "by_timeframe": [dict(r) for r in tfs],
            }

    def prune(self, max_age_days: int = 90) -> int:
        """Remove events older than max_age_days. Returns count removed."""
        with self._conn() as conn:
            cursor = conn.execute(
                "DELETE FROM trade_events WHERE timestamp < datetime('now', ?)",
                (f"-{max_age_days} days",),
            )
            return cursor.rowcount


# Module-level singleton
_history: TradeHistory | None = None


def get_trade_history() -> TradeHistory:
    global _history
    if _history is None:
        _history = TradeHistory()
    return _history
