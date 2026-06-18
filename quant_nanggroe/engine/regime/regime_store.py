import json
import sqlite3
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional
from quant_nanggroe.engine.regime.hmm_detector import RegimeState

logger = logging.getLogger(__name__)


class RegimeStore:
    def __init__(self, db_path: str = "/tmp/quant_nanggroe_regime.db"):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS regime_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                regime TEXT NOT NULL,
                confidence REAL NOT NULL,
                method TEXT NOT NULL,
                features TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_regime_timestamp
            ON regime_history(timestamp)
        """)
        conn.commit()

    def store(self, state: RegimeState) -> int:
        conn = self._get_conn()
        cursor = conn.execute(
            "INSERT INTO regime_history (regime, confidence, method, features, timestamp) VALUES (?, ?, ?, ?, ?)",
            (state.regime.value, state.confidence, state.method,
             json.dumps(state.features), state.timestamp.isoformat()),
        )
        conn.commit()
        return cursor.lastrowid

    def get_latest(self) -> Optional[RegimeState]:
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT regime, confidence, method, features, timestamp FROM regime_history ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if row is None:
            return None
        from quant_nanggroe.engine.regime.hmm_detector import Regime
        return RegimeState(
            regime=Regime(row["regime"]), confidence=row["confidence"],
            method=row["method"], features=json.loads(row["features"] or "{}"),
            timestamp=datetime.fromisoformat(row["timestamp"]),
        )

    def query(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT regime, confidence, method, features, timestamp FROM regime_history ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_regime_distribution(self, since: Optional[str] = None) -> Dict[str, int]:
        conn = self._get_conn()
        if since:
            cursor = conn.execute(
                "SELECT regime, COUNT(*) as cnt FROM regime_history WHERE timestamp >= ? GROUP BY regime",
                (since,),
            )
        else:
            cursor = conn.execute("SELECT regime, COUNT(*) as cnt FROM regime_history GROUP BY regime")
        return {row["regime"]: row["cnt"] for row in cursor.fetchall()}

    def prune(self, keep_last: int = 10000) -> int:
        conn = self._get_conn()
        cursor = conn.execute(
            "DELETE FROM regime_history WHERE id NOT IN (SELECT id FROM regime_history ORDER BY id DESC LIMIT ?)",
            (keep_last,),
        )
        conn.commit()
        return cursor.rowcount

    def close(self) -> None:
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
