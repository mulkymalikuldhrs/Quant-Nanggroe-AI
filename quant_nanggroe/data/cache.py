"""Persistent SQLite-backed cache for data providers.

Provides a thread-safe, TTL-aware cache that all data providers can use
instead of each maintaining their own in-memory cache. Entries are
JSON-serialized and namespaced by key prefix for scoped operations.

Usage::

    from quant_nanggroe.data.cache import DataCache

    cache = DataCache()
    cache.set("coingecko:price:BTC", {"usd": 42000}, ttl=300)
    value = cache.get("coingecko:price:BTC")
    cache.clear_namespace("coingecko")
    cache.close()
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class DataCache:
    """Thread-safe SQLite-backed persistent cache with TTL and namespace support.

    Lazily opens the database connection on first use. Each entry has a
    configurable TTL (time-to-live). Old entries are automatically purged
    on write when the total count exceeds *max_entries*.

    Parameters
    ----------
    db_path:
        Path to the SQLite database file. If ``None``, resolves to
        ``<project_root>/cache/data_cache.sqlite``, or the path
        specified by the ``QNAI_CACHE_DIR`` environment variable.
    max_entries:
        Maximum entries before auto-vacuum removes expired + oldest.
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        max_entries: int = 10_000,
    ) -> None:
        self._db_path = db_path or _default_db_path()
        self._max_entries = max_entries
        self._lock = threading.Lock()
        self._conn: Optional[sqlite3.Connection] = None

    # ------------------------------------------------------------------
    # Lazy init
    # ------------------------------------------------------------------

    def _ensure_connection(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn

        with self._lock:
            if self._conn is not None:
                return self._conn

            db_dir = os.path.dirname(self._db_path)
            os.makedirs(db_dir, exist_ok=True)

            conn = sqlite3.connect(self._db_path, check_same_thread=False, timeout=5.0)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute(
                """CREATE TABLE IF NOT EXISTS cache (
                    key        TEXT PRIMARY KEY,
                    value      TEXT    NOT NULL,
                    expires_at REAL    NOT NULL,
                    created_at REAL    NOT NULL
                )"""
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache(expires_at)")
            conn.commit()
            self._conn = conn
            logger.info(
                "DataCache opened: %s (max_entries=%d)",
                self._db_path,
                self._max_entries,
            )
            return conn

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Store *value* (must be JSON-serializable) with *ttl* in seconds."""
        conn = self._ensure_connection()
        now = time.time()
        expires_at = now + ttl
        # ponytail: json.dumps with default=str so dates/sets don't blow up
        payload = json.dumps(value, default=str)

        with self._lock:
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO cache (key, value, expires_at, created_at) "
                    "VALUES (?, ?, ?, ?)",
                    (key, payload, expires_at, now),
                )
                conn.commit()
            except sqlite3.Error:
                logger.exception("Cache set failed: key=%s", key)
                return

            self._maybe_vacuum(conn)

    def get(self, key: str) -> Any:
        """Retrieve value for *key*, or ``None`` if missing or expired."""
        conn = self._ensure_connection()
        with self._lock:
            try:
                row = conn.execute(
                    "SELECT value, expires_at FROM cache WHERE key = ?", (key,)
                ).fetchone()
            except sqlite3.Error:
                logger.exception("Cache get failed: key=%s", key)
                return None

        if row is None:
            return None

        value_json, expires_at = row
        if time.time() > expires_at:
            self.delete(key)
            return None

        try:
            return json.loads(value_json)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Corrupt JSON for key=%s, deleting", key)
            self.delete(key)
            return None

    def delete(self, key: str) -> None:
        """Remove a single entry."""
        conn = self._ensure_connection()
        with self._lock:
            try:
                conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                conn.commit()
            except sqlite3.Error:
                logger.exception("Cache delete failed: key=%s", key)

    def clear_namespace(self, namespace: str) -> None:
        """Remove all entries whose key starts with *namespace*."""
        conn = self._ensure_connection()
        pattern = f"{namespace}%"
        with self._lock:
            try:
                deleted = conn.execute(
                    "DELETE FROM cache WHERE key LIKE ?", (pattern,)
                ).rowcount
                conn.commit()
                if deleted:
                    logger.info("Cleared %d entries in namespace '%s'", deleted, namespace)
            except sqlite3.Error:
                logger.exception("Cache clear_namespace failed: namespace=%s", namespace)

    def stats(self) -> Dict[str, Any]:
        """Return cache statistics.

        Returns
        -------
        dict
            Keys: ``total_entries``, ``active_entries`` (not expired),
            ``db_size_mb``.
        """
        conn = self._ensure_connection()
        with self._lock:
            try:
                total = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
                active = conn.execute(
                    "SELECT COUNT(*) FROM cache WHERE expires_at > ?",
                    (time.time(),),
                ).fetchone()[0]
            except sqlite3.Error:
                logger.exception("Cache stats failed")
                total = active = 0

        try:
            size = os.path.getsize(self._db_path) / (1024.0 * 1024.0)
        except OSError:
            size = 0.0

        return {
            "total_entries": int(total),
            "active_entries": int(active),
            "db_size_mb": round(size, 3),
        }

    def clear(self) -> None:
        """Remove ALL entries (use with care)."""
        conn = self._ensure_connection()
        with self._lock:
            try:
                conn.execute("DELETE FROM cache")
                conn.commit()
            except sqlite3.Error:
                logger.exception("Cache clear failed")

    def close(self) -> None:
        """Close the database connection."""
        with self._lock:
            if self._conn is not None:
                try:
                    self._conn.close()
                except sqlite3.Error:
                    logger.exception("Error closing DataCache")
                self._conn = None
                logger.info("DataCache closed")

    def __enter__(self) -> DataCache:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Auto-vacuum
    # ------------------------------------------------------------------

    def _maybe_vacuum(self, conn: sqlite3.Connection) -> None:
        """Remove expired + oldest entries when over *max_entries*."""
        try:
            count = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
            if count <= self._max_entries:
                return

            # ponytail: delete expired first (free), then oldest by created_at
            conn.execute("DELETE FROM cache WHERE expires_at <= ?", (time.time(),))

            count = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
            if count > self._max_entries:
                excess = count - self._max_entries
                # ponytail: SQLite rowid works even with TEXT PK; ordering by
                # created_at evicts the oldest entries first
                conn.execute(
                    "DELETE FROM cache WHERE rowid IN ("
                    "  SELECT rowid FROM cache ORDER BY created_at ASC LIMIT ?"
                    ")",
                    (excess,),
                )

            conn.commit()
            remaining = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
            logger.debug("Auto-vacuum: trimmed cache to %d entries", remaining)
        except sqlite3.Error:
            logger.exception("Auto-vacuum failed")


# ------------------------------------------------------------------
# Default path resolution
# ------------------------------------------------------------------


def _default_db_path() -> str:
    """Resolve the cache database path.

    Priority:
    1. ``QNAI_CACHE_DIR`` env var → ``<dir>/data_cache.sqlite``
    2. Project root (walk up from ``cache.py`` looking for ``pyproject.toml``)
       → ``<project_root>/cache/data_cache.sqlite``
    """
    env_dir = os.environ.get("QNAI_CACHE_DIR")
    if env_dir:
        return os.path.join(env_dir, "data_cache.sqlite")

    current = os.path.dirname(os.path.abspath(__file__))
    for _ in range(20):
        marker = os.path.join(current, "pyproject.toml")
        if os.path.isfile(marker):
            return os.path.join(current, "cache", "data_cache.sqlite")
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    # ponytail: fallback to next to this file if pyproject.toml not found
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "cache", "data_cache.sqlite"
    )
