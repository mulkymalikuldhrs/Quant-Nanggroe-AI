"""Compliance & Audit Trail — Institutional-grade trade journal.

Records every order, fill, rejection, risk check, and kill-switch event
to an append-only SQLite journal. Designed for regulatory audit readiness.

Usage::
    from quant_nanggroe.engine.compliance import ComplianceJournal

    journal = ComplianceJournal()
    journal.record_order("BTC/USDT", "buy", 0.1, 67000, "limit", "pending")
    journal.record_fill("BTC/USDT", 0.1, 67050)
    journal.record_risk_event("kill_switch_activated", {"reason": "daily_loss_limit"})
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_APPEND_ONLY_ERROR = "ComplianceJournal is append-only; deletion not permitted"


@dataclass
class ComplianceRecord:
    id: int = 0
    event_type: str = ""
    symbol: str = ""
    details: str = ""
    severity: str = "info"
    timestamp: float = 0.0
    user_id: str = ""
    tags: List[str] = field(default_factory=list)


class ComplianceJournal:
    """Append-only SQLite compliance journal.

    Thread-safe via RLock. The journal cannot be deleted or modified
    after insertion — only queried and exported.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._lock = threading.RLock()
        if db_path is None:
            db_path = os.environ.get(
                "QNAI_COMPLIANCE_DB",
                os.path.join(os.path.expanduser("~"), ".qn_compliance.db"),
            )
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self._lock:
            conn = self._get_conn()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS compliance_journal (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type  TEXT NOT NULL,
                    symbol      TEXT DEFAULT '',
                    details     TEXT DEFAULT '',
                    severity    TEXT DEFAULT 'info',
                    timestamp   REAL NOT NULL,
                    user_id     TEXT DEFAULT '',
                    tags        TEXT DEFAULT '[]'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS paper_trading_state (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
        return self._conn

    def _insert(
        self,
        event_type: str,
        symbol: str = "",
        details: Optional[Dict[str, Any]] = None,
        severity: str = "info",
        user_id: str = "",
        tags: Optional[List[str]] = None,
    ) -> int:
        with self._lock:
            conn = self._get_conn()
            now = time.time()
            cursor = conn.execute(
                """
                INSERT INTO compliance_journal
                    (event_type, symbol, details, severity, timestamp, user_id, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_type,
                    symbol,
                    json.dumps(details or {}),
                    severity,
                    now,
                    user_id,
                    json.dumps(tags or []),
                ),
            )
            conn.commit()
            return cursor.lastrowid or 0

    def record_order(
        self, symbol: str, side: str, quantity: float, price: float,
        order_type: str, status: str, user_id: str = "",
    ) -> int:
        return self._insert(
            "order",
            symbol,
            {"side": side, "quantity": quantity, "price": price, "order_type": order_type, "status": status},
            severity="info", user_id=user_id,
            tags=["order", status],
        )

    def record_fill(self, symbol: str, quantity: float, price: float, user_id: str = "") -> int:
        return self._insert(
            "fill", symbol, {"quantity": quantity, "price": price},
            severity="info", user_id=user_id, tags=["fill"],
        )

    def record_rejection(self, symbol: str, reason: str, details: Optional[Dict[str, Any]] = None, user_id: str = "") -> int:
        return self._insert(
            "rejection", symbol, {"reason": reason, **(details or {})},
            severity="warning", user_id=user_id, tags=["rejection"],
        )

    def record_risk_event(self, event_type: str, details: Optional[Dict[str, Any]] = None, user_id: str = "") -> int:
        return self._insert(
            f"risk_{event_type}", "", details or {},
            severity="critical", user_id=user_id, tags=["risk", event_type],
        )

    def record_auth_event(self, event_type: str, user_id: str = "", details: Optional[Dict[str, Any]] = None) -> int:
        return self._insert(
            f"auth_{event_type}", "", details or {},
            severity="info", user_id=user_id, tags=["auth", event_type],
        )

    def record_system_event(self, event_type: str, details: Optional[Dict[str, Any]] = None) -> int:
        return self._insert(
            f"system_{event_type}", "", details or {},
            severity="info", tags=["system", event_type],
        )

    def query(
        self,
        limit: int = 100,
        offset: int = 0,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        since: Optional[float] = None,
    ) -> List[ComplianceRecord]:
        with self._lock:
            conn = self._get_conn()
            parts = ["SELECT * FROM compliance_journal WHERE 1=1"]
            params: List[Any] = []
            if event_type:
                parts.append("AND event_type LIKE ?")
                params.append(f"{event_type}%")
            if severity:
                parts.append("AND severity = ?")
                params.append(severity)
            if since:
                parts.append("AND timestamp >= ?")
                params.append(since)
            parts.append("ORDER BY id DESC LIMIT ? OFFSET ?")
            params.extend([limit, offset])
            rows = conn.execute(" ".join(parts), params).fetchall()
            return [self._row_to_record(r) for r in rows]

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> ComplianceRecord:
        return ComplianceRecord(
            id=row["id"],
            event_type=row["event_type"],
            symbol=row["symbol"],
            details=row["details"],
            severity=row["severity"],
            timestamp=row["timestamp"],
            user_id=row["user_id"],
            tags=json.loads(row["tags"]),
        )

    def count(self, since: Optional[float] = None) -> int:
        with self._lock:
            conn = self._get_conn()
            if since:
                return conn.execute("SELECT COUNT(*) FROM compliance_journal WHERE timestamp >= ?", (since,)).fetchone()[0]
            return conn.execute("SELECT COUNT(*) FROM compliance_journal").fetchone()[0]

    def export_json(self, path: str, limit: int = 10000) -> None:
        records = self.query(limit=limit)
        with open(path, "w") as f:
            json.dump([asdict(r) for r in records], f, indent=2, default=str)
        logger.info("Exported %d compliance records to %s", len(records), path)

    def get_paper_state(self, key: str, default: str = "") -> str:
        with self._lock:
            row = self._get_conn().execute("SELECT value FROM paper_trading_state WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else default

    def set_paper_state(self, key: str, value: str) -> None:
        with self._lock:
            self._get_conn().execute(
                "INSERT OR REPLACE INTO paper_trading_state (key, value) VALUES (?, ?)", (key, value),
            )
            self._get_conn().commit()

    def close(self) -> None:
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None
