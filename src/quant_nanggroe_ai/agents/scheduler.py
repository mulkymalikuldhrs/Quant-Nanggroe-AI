"""
scheduler.py — Trading Task Scheduler
Adapted from ghoststudio-ai scheduler.py for trading operations.

SQLite-backed persistent job queue with priority ordering,
retry with exponential backoff, and cron-ready scheduling.
"""

import sqlite3
import json
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class TradingScheduler:
    """
    Persistent job queue for scheduled trading operations.
    Thread-safe, SQLite-backed, supports recurring schedules.

    Supports:
    - Scheduled order placement
    - Recurring strategy execution (cron-like)
    - Priority-based job ordering
    - Automatic retry with exponential backoff
    - Job status tracking and audit log
    """

    STATUS_PENDING = "pending"
    STATUS_QUEUED = "queued"
    STATUS_PROCESSING = "processing"
    STATUS_DONE = "done"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"
    STATUS_REVIEW = "review"

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = "~/.quant_nanggroe_ai/scheduler.db"
        self.db_path = str(Path(db_path).expanduser())
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                job_type TEXT NOT NULL DEFAULT 'trade',
                symbol TEXT,
                side TEXT,
                quantity REAL,
                price REAL,
                strategy TEXT,
                schedule_at INTEGER,
                cron_expr TEXT,
                status TEXT DEFAULT 'pending',
                priority INTEGER DEFAULT 5,
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,
                result TEXT,
                error_msg TEXT,
                metadata TEXT DEFAULT '{}',
                created_at INTEGER DEFAULT (strftime('%s','now')),
                updated_at INTEGER DEFAULT (strftime('%s','now'))
            );

            CREATE TABLE IF NOT EXISTS queue_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                schedule_id INTEGER,
                action TEXT,
                status TEXT,
                message TEXT,
                created_at INTEGER DEFAULT (strftime('%s','now'))
            );

            CREATE INDEX IF NOT EXISTS idx_schedule_status ON schedule(status);
            CREATE INDEX IF NOT EXISTS idx_schedule_time ON schedule(schedule_at);
            CREATE INDEX IF NOT EXISTS idx_schedule_symbol ON schedule(symbol);
        """)
        conn.commit()

    # ── Job Management ──────────────────────────────────────────

    def add_job(
        self,
        job_type: str = "trade",
        title: Optional[str] = None,
        symbol: Optional[str] = None,
        side: Optional[str] = None,
        quantity: Optional[float] = None,
        price: Optional[float] = None,
        strategy: Optional[str] = None,
        schedule_at: Optional[int] = None,
        cron_expr: Optional[str] = None,
        priority: int = 5,
        max_retries: int = 3,
        metadata: Optional[dict] = None,
    ) -> int:
        """Add a scheduled trading job."""
        conn = self._get_conn()
        now = int(time.time())
        sched_time = schedule_at if schedule_at else now
        status = self.STATUS_PENDING if (schedule_at and schedule_at > now) else self.STATUS_QUEUED

        conn.execute("""
            INSERT INTO schedule
                (title, job_type, symbol, side, quantity, price, strategy,
                 schedule_at, cron_expr, status, priority, max_retries,
                 metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            title or f"{job_type} {symbol or 'N/A'}",
            job_type,
            symbol,
            side,
            quantity,
            price,
            strategy,
            sched_time,
            cron_expr,
            status,
            priority,
            max_retries,
            json.dumps(metadata or {}),
            now,
            now,
        ))
        conn.commit()
        job_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        self._log(job_id, "created", status, "Job added to queue")
        return job_id

    def get_next_job(self, job_type: Optional[str] = None) -> Optional[dict[str, Any]]:
        """Get the next job to process (FIFO with priority ordering)."""
        conn = self._get_conn()
        now = int(time.time())
        if job_type:
            row = conn.execute("""
                SELECT * FROM schedule
                WHERE status=? AND schedule_at<=? AND job_type=?
                ORDER BY priority DESC, schedule_at ASC, id ASC
                LIMIT 1
            """, (self.STATUS_QUEUED, now, job_type)).fetchone()
        else:
            row = conn.execute("""
                SELECT * FROM schedule
                WHERE status=? AND schedule_at<=?
                ORDER BY priority DESC, schedule_at ASC, id ASC
                LIMIT 1
            """, (self.STATUS_QUEUED, now)).fetchone()
        if row:
            self._set_status(row["id"], self.STATUS_PROCESSING)
            return dict(row)
        return None

    def get_pending_jobs(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get all queued jobs ready for processing."""
        conn = self._get_conn()
        now = int(time.time())
        rows = conn.execute("""
            SELECT * FROM schedule
            WHERE status=? AND schedule_at<=?
            ORDER BY priority DESC, schedule_at ASC, id ASC
            LIMIT ?
        """, (self.STATUS_QUEUED, now, limit)).fetchall()
        return [dict(r) for r in rows]

    def mark_done(self, job_id: int, result: Optional[dict] = None) -> None:
        """Mark a job as successfully completed."""
        conn = self._get_conn()
        self._set_status(job_id, self.STATUS_DONE)
        if result:
            conn.execute(
                "UPDATE schedule SET result=? WHERE id=?",
                (json.dumps(result), job_id),
            )
            conn.commit()
        self._log(job_id, "completed", self.STATUS_DONE, "Job completed successfully")

    def mark_failed(self, job_id: int, error_msg: str, retry: bool = True) -> None:
        """Mark a job as failed, optionally re-queuing with exponential backoff."""
        conn = self._get_conn()
        job = conn.execute("SELECT * FROM schedule WHERE id=?", (job_id,)).fetchone()
        if not job:
            return
        retry_count = job["retry_count"] + 1
        max_retries = job["max_retries"]

        if retry and retry_count < max_retries:
            backoff = min(300, 30 * (2 ** retry_count))
            new_time = int(time.time()) + backoff
            conn.execute("""
                UPDATE schedule SET status=?, retry_count=?, error_msg=?,
                    schedule_at=?, updated_at=?
                WHERE id=?
            """, (
                self.STATUS_QUEUED,
                retry_count,
                error_msg[:500],
                new_time,
                int(time.time()),
                job_id,
            ))
            conn.commit()
            self._log(
                job_id, "retry", self.STATUS_QUEUED,
                f"Retry {retry_count}/{max_retries} in {backoff}s: {error_msg[:100]}",
            )
        else:
            self._set_status(job_id, self.STATUS_FAILED, error_msg=error_msg)
            self._log(job_id, "failed", self.STATUS_FAILED, error_msg[:300])

    def mark_review(self, job_id: int, reason: Optional[str] = None) -> None:
        """Mark a job as needing review."""
        self._set_status(job_id, self.STATUS_REVIEW, error_msg=reason)
        self._log(
            job_id, "review", self.STATUS_REVIEW,
            f"Needs review: {reason[:100] if reason else 'quality check'}"[:300],
        )

    def cancel_job(self, job_id: int) -> None:
        """Cancel a scheduled job."""
        self._set_status(job_id, self.STATUS_CANCELLED)
        self._log(job_id, "cancelled", self.STATUS_CANCELLED, "Job cancelled")

    def _set_status(
        self, job_id: int, status: str, error_msg: Optional[str] = None
    ) -> None:
        conn = self._get_conn()
        now = int(time.time())
        if error_msg is not None:
            conn.execute(
                "UPDATE schedule SET status=?, error_msg=?, updated_at=? WHERE id=?",
                (status, error_msg[:500], now, job_id),
            )
        else:
            conn.execute(
                "UPDATE schedule SET status=?, updated_at=? WHERE id=?",
                (status, now, job_id),
            )
        conn.commit()

    def _log(
        self, schedule_id: int, action: str, status: str, message: str = ""
    ) -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO queue_log (schedule_id, action, status, message) VALUES (?, ?, ?, ?)",
            (schedule_id, action, status, message[:500]),
        )
        conn.commit()

    # ── Stats & Query ──────────────────────────────────────────

    def get_stats(self) -> dict[str, int]:
        """Get job counts by status."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT status, COUNT(*) as count FROM schedule GROUP BY status"
        ).fetchall()
        stats = {r["status"]: r["count"] for r in rows}
        stats["total"] = sum(stats.values())
        return stats

    def get_jobs_by_symbol(
        self, symbol: str, status: Optional[str] = None, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Get jobs for a specific symbol."""
        conn = self._get_conn()
        if status:
            rows = conn.execute(
                "SELECT * FROM schedule WHERE symbol=? AND status=? ORDER BY created_at DESC LIMIT ?",
                (symbol, status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM schedule WHERE symbol=? ORDER BY created_at DESC LIMIT ?",
                (symbol, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_job(self, job_id: int) -> Optional[dict[str, Any]]:
        """Get a specific job by ID."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM schedule WHERE id=?", (job_id,)).fetchone()
        return dict(row) if row else None

    def cleanup_old_jobs(self, days: int = 30) -> int:
        """Remove completed/failed jobs older than N days."""
        cutoff = int(time.time()) - (days * 86400)
        conn = self._get_conn()
        conn.execute(
            "DELETE FROM schedule WHERE status IN (?,?) AND updated_at < ?",
            (self.STATUS_DONE, self.STATUS_FAILED, cutoff),
        )
        conn.execute("DELETE FROM queue_log WHERE created_at < ?", (cutoff,))
        conn.commit()
        return conn.total_changes

    def close(self) -> None:
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# Singleton
_scheduler_instance: Optional[TradingScheduler] = None


def get_scheduler(db_path: Optional[str] = None) -> TradingScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = TradingScheduler(db_path)
    return _scheduler_instance
