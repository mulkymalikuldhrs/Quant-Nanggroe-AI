"""Audit Trail — Append-only audit logging with SQLite storage.

Provides an immutable, append-only audit log for all trading decisions,
risk verdicts, and order events. Records cannot be updated or deleted.

Features
--------
* Append-only audit log stored in SQLite
* Log all trading decisions, risk verdicts, order events
* Immutable records (no UPDATE/DELETE operations)
* Query by date range, symbol, agent, verdict
* Daily audit report generation
* Configurable retention policy

Security
--------
The audit log is designed for compliance and forensics. Records are
insert-only — no modification or deletion is possible through the API.
The SQLite database file should be backed up regularly.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class AuditRecord(BaseModel):
    """A single audit trail record.

    Attributes
    ----------
    id:
        Unique record ID (auto-incremented).
    timestamp:
        When the event occurred.
    agent:
        Agent or component that generated the event.
    event_type:
        Type of event (e.g. ``"order_placed"``, ``"risk_check"``).
    symbol:
        Trading symbol involved (optional).
    action:
        Action taken (e.g. ``"buy"``, ``"sell"``, ``"approved"``).
    verdict:
        Outcome or decision (e.g. ``"approved"``, ``"rejected"``).
    details:
        Additional JSON-serializable details.
    metadata:
        Extra metadata (e.g. order IDs, amounts).
    """

    id: Optional[int] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    agent: str = ""
    event_type: str = ""
    symbol: Optional[str] = None
    action: str = ""
    verdict: str = ""
    details: str = "{}"
    metadata: str = "{}"

    model_config = {"from_attributes": True}


class DailyAuditReport(BaseModel):
    """Summary report for a single day's audit trail.

    Attributes
    ----------
    date:
        Report date.
    total_events:
        Total number of events.
    events_by_type:
        Breakdown by event type.
    events_by_agent:
        Breakdown by agent.
    events_by_verdict:
        Breakdown by verdict.
    symbols_traded:
        List of symbols involved in trading events.
    risk_rejections:
        Number of risk rejections.
    orders_placed:
        Number of orders placed.
    orders_filled:
        Number of orders filled.
    """

    date: str
    total_events: int = 0
    events_by_type: Dict[str, int] = Field(default_factory=dict)
    events_by_agent: Dict[str, int] = Field(default_factory=dict)
    events_by_verdict: Dict[str, int] = Field(default_factory=dict)
    symbols_traded: List[str] = Field(default_factory=list)
    risk_rejections: int = 0
    orders_placed: int = 0
    orders_filled: int = 0

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# AuditLogger
# ---------------------------------------------------------------------------

class AuditLogger:
    """Append-only audit logger backed by SQLite.

    All records are insert-only. No UPDATE or DELETE operations are
    provided, ensuring immutability for compliance.

    Parameters
    ----------
    db_path:
        Path to the SQLite database file. If ``None``, uses an
        in-memory database (useful for testing).
    auto_create:
        Whether to auto-create the database schema on init.

    Examples
    --------
    .. code-block:: python

        audit = AuditLogger(db_path="audit.db")
        await audit.log_event(
            agent="risk_agent",
            event_type="risk_check",
            symbol="BTC/USDT",
            verdict="approved",
        )
        records = await audit.query(symbol="BTC/USDT")
    """

    def __init__(
        self,
        db_path: Optional[str] = "audit.db",
        auto_create: bool = True,
    ) -> None:
        self._db_path = db_path or ":memory:"
        self._conn: Optional[sqlite3.Connection] = None

        if auto_create:
            self._ensure_schema()

    # ----- Schema -----

    def _ensure_schema(self) -> None:
        """Create the audit table if it doesn't exist."""
        conn = self._get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                agent TEXT NOT NULL DEFAULT '',
                event_type TEXT NOT NULL DEFAULT '',
                symbol TEXT,
                action TEXT NOT NULL DEFAULT '',
                verdict TEXT NOT NULL DEFAULT '',
                details TEXT NOT NULL DEFAULT '{}',
                metadata TEXT NOT NULL DEFAULT '{}'
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp
            ON audit_log(timestamp)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_agent
            ON audit_log(agent)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_symbol
            ON audit_log(symbol)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_event_type
            ON audit_log(event_type)
        """)
        conn.commit()

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create the database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    # ----- Logging -----

    async def log_event(
        self,
        agent: str,
        event_type: str,
        symbol: Optional[str] = None,
        action: str = "",
        verdict: str = "",
        details: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditRecord:
        """Log an audit event.

        This is an append-only operation — records cannot be modified
        or deleted after insertion.

        Parameters
        ----------
        agent:
            Agent or component name.
        event_type:
            Event type (e.g. ``"order_placed"``, ``"risk_check"``).
        symbol:
            Trading symbol (optional).
        action:
            Action taken.
        verdict:
            Outcome or decision.
        details:
            Additional details (will be JSON-serialized).
        metadata:
            Extra metadata (will be JSON-serialized).

        Returns
        -------
        AuditRecord
            The created audit record.
        """
        conn = self._get_connection()
        now = datetime.now(tz=timezone.utc).isoformat()

        details_json = json.dumps(details or {})
        metadata_json = json.dumps(metadata or {})

        cursor = conn.execute(
            """
            INSERT INTO audit_log (timestamp, agent, event_type, symbol, action, verdict, details, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (now, agent, event_type, symbol, action, verdict, details_json, metadata_json),
        )
        conn.commit()

        record = AuditRecord(
            id=cursor.lastrowid,
            timestamp=datetime.fromisoformat(now),
            agent=agent,
            event_type=event_type,
            symbol=symbol,
            action=action,
            verdict=verdict,
            details=details_json,
            metadata=metadata_json,
        )
        logger.debug("Audit event logged: %s/%s", agent, event_type)
        return record

    # ----- Queries -----

    async def query(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        symbol: Optional[str] = None,
        agent: Optional[str] = None,
        event_type: Optional[str] = None,
        verdict: Optional[str] = None,
        limit: int = 1000,
    ) -> List[AuditRecord]:
        """Query audit records with optional filters.

        Parameters
        ----------
        start_date:
            Filter by start date (inclusive).
        end_date:
            Filter by end date (inclusive).
        symbol:
            Filter by trading symbol.
        agent:
            Filter by agent name.
        event_type:
            Filter by event type.
        verdict:
            Filter by verdict.
        limit:
            Maximum number of records to return.

        Returns
        -------
        list of AuditRecord
        """
        conn = self._get_connection()

        conditions: List[str] = []
        params: List[Any] = []

        if start_date:
            conditions.append("timestamp >= ?")
            params.append(start_date.isoformat())
        if end_date:
            conditions.append("timestamp <= ?")
            params.append(end_date.isoformat())
        if symbol:
            conditions.append("symbol = ?")
            params.append(symbol)
        if agent:
            conditions.append("agent = ?")
            params.append(agent)
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        if verdict:
            conditions.append("verdict = ?")
            params.append(verdict)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query_sql = f"""
            SELECT * FROM audit_log
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ?
        """
        params.append(limit)

        rows = conn.execute(query_sql, params).fetchall()
        return [self._row_to_record(row) for row in rows]

    async def get_record(self, record_id: int) -> Optional[AuditRecord]:
        """Get a specific audit record by ID.

        Parameters
        ----------
        record_id:
            The record ID.

        Returns
        -------
        AuditRecord or None
        """
        conn = self._get_connection()
        row = conn.execute(
            "SELECT * FROM audit_log WHERE id = ?", (record_id,)
        ).fetchone()
        if row:
            return self._row_to_record(row)
        return None

    async def count(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        agent: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> int:
        """Count audit records matching filters.

        Returns
        -------
        int
            Number of matching records.
        """
        conn = self._get_connection()

        conditions: List[str] = []
        params: List[Any] = []

        if start_date:
            conditions.append("timestamp >= ?")
            params.append(start_date.isoformat())
        if end_date:
            conditions.append("timestamp <= ?")
            params.append(end_date.isoformat())
        if agent:
            conditions.append("agent = ?")
            params.append(agent)
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        result = conn.execute(
            "SELECT COUNT(*) FROM audit_log WHERE " + where_clause, params
        ).fetchone()

        return result[0] if result else 0

    # ----- Daily Report -----

    async def generate_daily_report(
        self,
        date: Optional[str] = None,
    ) -> DailyAuditReport:
        """Generate a summary report for a specific date.

        Parameters
        ----------
        date:
            Date string in ``YYYY-MM-DD`` format. Defaults to today (UTC).

        Returns
        -------
        DailyAuditReport
        """
        if date is None:
            date = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

        start = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end = start + timedelta(days=1)

        records = await self.query(start_date=start, end_date=end, limit=10000)

        events_by_type: Dict[str, int] = {}
        events_by_agent: Dict[str, int] = {}
        events_by_verdict: Dict[str, int] = {}
        symbols: set[str] = set()
        risk_rejections = 0
        orders_placed = 0
        orders_filled = 0

        for record in records:
            # By type
            events_by_type[record.event_type] = events_by_type.get(record.event_type, 0) + 1
            # By agent
            events_by_agent[record.agent] = events_by_agent.get(record.agent, 0) + 1
            # By verdict
            if record.verdict:
                events_by_verdict[record.verdict] = events_by_verdict.get(record.verdict, 0) + 1
            # Symbols
            if record.symbol:
                symbols.add(record.symbol)
            # Counts
            if record.event_type == "risk_check" and record.verdict == "rejected":
                risk_rejections += 1
            if record.event_type == "order_placed":
                orders_placed += 1
            if record.event_type == "order_filled":
                orders_filled += 1

        return DailyAuditReport(
            date=date,
            total_events=len(records),
            events_by_type=events_by_type,
            events_by_agent=events_by_agent,
            events_by_verdict=events_by_verdict,
            symbols_traded=sorted(symbols),
            risk_rejections=risk_rejections,
            orders_placed=orders_placed,
            orders_filled=orders_filled,
        )

    # ----- Cleanup -----

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    # ----- Internal -----

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> AuditRecord:
        """Convert a database row to an AuditRecord."""
        return AuditRecord(
            id=row["id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            agent=row["agent"],
            event_type=row["event_type"],
            symbol=row["symbol"],
            action=row["action"],
            verdict=row["verdict"],
            details=row["details"],
            metadata=row["metadata"],
        )

    def __repr__(self) -> str:
        return f"AuditLogger(db_path={self._db_path})"
