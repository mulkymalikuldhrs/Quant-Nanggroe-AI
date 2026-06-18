"""Long-term memory with checkpointing for the AI-MultiColony harness.

Provides persistent memory storage with SQLite backend, automatic
checkpointing, and recall capabilities for agent execution state.

This complements the core memory module with harness-specific
features focused on execution context persistence.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


# ── Models ───────────────────────────────────────────────────────────────────


class MemoryEntry(BaseModel):
    """A single memory entry."""
    model_config = ConfigDict(frozen=False)

    entry_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])
    key: str = ""
    value: Any = None
    category: str = "general"
    tags: List[str] = Field(default_factory=list)
    importance: float = 0.5  # 0.0 to 1.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    accessed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = 0
    expires_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "key": self.key,
            "value": self.value,
            "category": self.category,
            "tags": self.tags,
            "importance": self.importance,
            "created_at": self.created_at.isoformat(),
            "accessed_at": self.accessed_at.isoformat(),
            "access_count": self.access_count,
        }


class CheckpointEntry(BaseModel):
    """A checkpoint of execution state."""
    model_config = ConfigDict(frozen=False)

    checkpoint_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    graph_id: str = ""
    label: str = ""
    state: Dict[str, Any] = Field(default_factory=dict)
    step_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RecallResult(BaseModel):
    """Result from a memory recall operation."""
    model_config = ConfigDict(frozen=False)

    entries: List[MemoryEntry] = Field(default_factory=list)
    total_count: int = 0
    query: str = ""
    elapsed_ms: float = 0.0


# ── SQLite Backend ───────────────────────────────────────────────────────────


class SQLiteMemoryStore:
    """SQLite-based persistent memory store.

    Stores memory entries and checkpoints in a local SQLite database,
    providing durability and query capabilities.

    Usage::

        store = SQLiteMemoryStore("/path/to/memory.db")
        store.initialize()
        store.store(entry)
        results = store.recall("search term")
    """

    def __init__(self, db_path: str = ""):
        if not db_path:
            db_path = os.path.join(
                os.environ.get("AI_MULTICOLONY_DATA_DIR", "/tmp"),
                "harness_memory.db",
            )
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def initialize(self) -> None:
        """Initialize the database schema."""
        self._conn = sqlite3.connect(self._db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_entries (
                entry_id TEXT PRIMARY KEY,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                tags TEXT DEFAULT '[]',
                importance REAL DEFAULT 0.5,
                created_at TEXT NOT NULL,
                accessed_at TEXT NOT NULL,
                access_count INTEGER DEFAULT 0,
                expires_at TEXT
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_key ON memory_entries(key)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_category ON memory_entries(category)
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                checkpoint_id TEXT PRIMARY KEY,
                graph_id TEXT NOT NULL,
                label TEXT DEFAULT '',
                state TEXT NOT NULL,
                step_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_checkpoints_graph ON checkpoints(graph_id)
        """)
        self._conn.commit()

    def store(self, entry: MemoryEntry) -> None:
        """Store a memory entry."""
        if self._conn is None:
            self.initialize()
        assert self._conn is not None

        self._conn.execute(
            """INSERT OR REPLACE INTO memory_entries
               (entry_id, key, value, category, tags, importance,
                created_at, accessed_at, access_count, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                entry.entry_id,
                entry.key,
                json.dumps(entry.value, default=str),
                entry.category,
                json.dumps(entry.tags),
                entry.importance,
                entry.created_at.isoformat(),
                entry.accessed_at.isoformat(),
                entry.access_count,
                entry.expires_at.isoformat() if entry.expires_at else None,
            ),
        )
        self._conn.commit()

    def recall(self, query: str, limit: int = 50, category: Optional[str] = None) -> List[MemoryEntry]:
        """Recall memory entries matching a query.

        Parameters
        ----------
        query:
            Search term (matched against key and value).
        limit:
            Maximum entries to return.
        category:
            Optional category filter.

        Returns
        -------
        list[MemoryEntry]
            Matching memory entries.
        """
        if self._conn is None:
            self.initialize()
        assert self._conn is not None

        sql = """
            SELECT entry_id, key, value, category, tags, importance,
                   created_at, accessed_at, access_count, expires_at
            FROM memory_entries
            WHERE (key LIKE ? OR value LIKE ?)
        """
        params: List[Any] = [f"%{query}%", f"%{query}%"]

        if category:
            sql += " AND category = ?"
            params.append(category)

        sql += " ORDER BY importance DESC, accessed_at DESC LIMIT ?"
        params.append(limit)

        rows = self._conn.execute(sql, params).fetchall()
        entries: List[MemoryEntry] = []
        for row in rows:
            try:
                entries.append(MemoryEntry(
                    entry_id=row[0],
                    key=row[1],
                    value=json.loads(row[2]),
                    category=row[3],
                    tags=json.loads(row[4]),
                    importance=row[5],
                    created_at=datetime.fromisoformat(row[6]),
                    accessed_at=datetime.fromisoformat(row[7]),
                    access_count=row[8],
                    expires_at=datetime.fromisoformat(row[9]) if row[9] else None,
                ))
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning("Failed to parse memory entry %s: %s", row[0], e)

        # Update access counts
        for entry in entries:
            self._update_access(entry.entry_id)

        return entries

    def get_by_key(self, key: str) -> Optional[MemoryEntry]:
        """Get a memory entry by exact key."""
        if self._conn is None:
            self.initialize()
        assert self._conn is not None

        row = self._conn.execute(
            "SELECT entry_id, key, value, category, tags, importance, "
            "created_at, accessed_at, access_count, expires_at "
            "FROM memory_entries WHERE key = ?",
            (key,),
        ).fetchone()

        if row is None:
            return None

        try:
            return MemoryEntry(
                entry_id=row[0],
                key=row[1],
                value=json.loads(row[2]),
                category=row[3],
                tags=json.loads(row[4]),
                importance=row[5],
                created_at=datetime.fromisoformat(row[6]),
                accessed_at=datetime.fromisoformat(row[7]),
                access_count=row[8],
                expires_at=datetime.fromisoformat(row[9]) if row[9] else None,
            )
        except (json.JSONDecodeError, ValueError):
            return None

    def delete(self, entry_id: str) -> bool:
        """Delete a memory entry by ID."""
        if self._conn is None:
            self.initialize()
        assert self._conn is not None

        cursor = self._conn.execute(
            "DELETE FROM memory_entries WHERE entry_id = ?", (entry_id,),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def store_checkpoint(self, checkpoint: CheckpointEntry) -> None:
        """Store a checkpoint."""
        if self._conn is None:
            self.initialize()
        assert self._conn is not None

        self._conn.execute(
            """INSERT OR REPLACE INTO checkpoints
               (checkpoint_id, graph_id, label, state, step_count, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                checkpoint.checkpoint_id,
                checkpoint.graph_id,
                checkpoint.label,
                json.dumps(checkpoint.state, default=str),
                checkpoint.step_count,
                checkpoint.created_at.isoformat(),
            ),
        )
        self._conn.commit()

    def load_checkpoint(self, checkpoint_id: str) -> Optional[CheckpointEntry]:
        """Load a checkpoint by ID."""
        if self._conn is None:
            self.initialize()
        assert self._conn is not None

        row = self._conn.execute(
            "SELECT checkpoint_id, graph_id, label, state, step_count, created_at "
            "FROM checkpoints WHERE checkpoint_id = ?",
            (checkpoint_id,),
        ).fetchone()

        if row is None:
            return None

        try:
            return CheckpointEntry(
                checkpoint_id=row[0],
                graph_id=row[1],
                label=row[2],
                state=json.loads(row[3]),
                step_count=row[4],
                created_at=datetime.fromisoformat(row[5]),
            )
        except (json.JSONDecodeError, ValueError):
            return None

    def list_checkpoints(self, graph_id: Optional[str] = None) -> List[CheckpointEntry]:
        """List stored checkpoints, optionally filtered by graph_id."""
        if self._conn is None:
            self.initialize()
        assert self._conn is not None

        if graph_id:
            rows = self._conn.execute(
                "SELECT checkpoint_id, graph_id, label, state, step_count, created_at "
                "FROM checkpoints WHERE graph_id = ? ORDER BY created_at DESC",
                (graph_id,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT checkpoint_id, graph_id, label, state, step_count, created_at "
                "FROM checkpoints ORDER BY created_at DESC",
            ).fetchall()

        entries: List[CheckpointEntry] = []
        for row in rows:
            try:
                entries.append(CheckpointEntry(
                    checkpoint_id=row[0],
                    graph_id=row[1],
                    label=row[2],
                    state=json.loads(row[3]),
                    step_count=row[4],
                    created_at=datetime.fromisoformat(row[5]),
                ))
            except (json.JSONDecodeError, ValueError):
                continue
        return entries

    def _update_access(self, entry_id: str) -> None:
        """Update access count and timestamp for an entry."""
        if self._conn is None:
            return
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "UPDATE memory_entries SET access_count = access_count + 1, accessed_at = ? "
            "WHERE entry_id = ?",
            (now, entry_id),
        )
        self._conn.commit()

    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        if self._conn is None:
            self.initialize()
        assert self._conn is not None

        mem_count = self._conn.execute("SELECT COUNT(*) FROM memory_entries").fetchone()[0]
        cp_count = self._conn.execute("SELECT COUNT(*) FROM checkpoints").fetchone()[0]
        categories = self._conn.execute(
            "SELECT category, COUNT(*) FROM memory_entries GROUP BY category"
        ).fetchall()

        return {
            "memory_entries": mem_count,
            "checkpoints": cp_count,
            "categories": {cat: count for cat, count in categories},
            "db_path": self._db_path,
        }

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __del__(self) -> None:
        self.close()


# ── High-level Memory Interface ──────────────────────────────────────────────


class HarnessMemory:
    """High-level memory interface for the harness.

    Combines short-term (in-memory) and long-term (SQLite) storage
    with automatic checkpointing and recall.

    Usage::

        memory = HarnessMemory()
        memory.store("result_1", {"answer": 42}, category="results")
        results = memory.recall("result")
    """

    def __init__(self, db_path: str = ""):
        self._short_term: Dict[str, MemoryEntry] = {}
        self._long_term = SQLiteMemoryStore(db_path)
        self._initialized = False

    def _ensure_init(self) -> None:
        """Ensure the long-term store is initialized."""
        if not self._initialized:
            self._long_term.initialize()
            self._initialized = True

    def store(
        self,
        key: str,
        value: Any,
        category: str = "general",
        tags: Optional[List[str]] = None,
        importance: float = 0.5,
    ) -> MemoryEntry:
        """Store a value in memory.

        Parameters
        ----------
        key:
            Unique key for the entry.
        value:
            Value to store (must be JSON-serializable).
        category:
            Category for organization.
        tags:
            Tags for search.
        importance:
            Importance score (0.0-1.0).

        Returns
        -------
        MemoryEntry
            The created entry.
        """
        entry = MemoryEntry(
            key=key,
            value=value,
            category=category,
            tags=tags or [],
            importance=importance,
        )

        # Store in short-term
        self._short_term[key] = entry

        # Store in long-term
        try:
            self._ensure_init()
            self._long_term.store(entry)
        except Exception as e:
            logger.warning("Failed to store in long-term memory: %s", e)

        return entry

    def recall(self, query: str, limit: int = 50) -> RecallResult:
        """Recall memory entries matching a query.

        Searches both short-term and long-term stores.
        """
        import time
        start = time.monotonic()
        results: List[MemoryEntry] = []
        seen_ids: set = set()

        # Search short-term first
        query_lower = query.lower()
        for entry in self._short_term.values():
            if (query_lower in entry.key.lower() or
                query_lower in json.dumps(entry.value, default=str).lower()):
                if entry.entry_id not in seen_ids:
                    results.append(entry)
                    seen_ids.add(entry.entry_id)

        # Search long-term
        try:
            self._ensure_init()
            lt_results = self._long_term.recall(query, limit=limit - len(results))
            for entry in lt_results:
                if entry.entry_id not in seen_ids:
                    results.append(entry)
                    seen_ids.add(entry.entry_id)
        except Exception as e:
            logger.warning("Long-term recall failed: %s", e)

        elapsed = (time.monotonic() - start) * 1000
        return RecallResult(
            entries=results[:limit],
            total_count=len(results),
            query=query,
            elapsed_ms=elapsed,
        )

    def get(self, key: str) -> Optional[MemoryEntry]:
        """Get a memory entry by exact key."""
        # Check short-term first
        if key in self._short_term:
            return self._short_term[key]

        # Check long-term
        try:
            self._ensure_init()
            return self._long_term.get_by_key(key)
        except Exception:
            return None

    def delete(self, key: str) -> bool:
        """Delete a memory entry by key."""
        entry = self._short_term.pop(key, None)
        if entry:
            try:
                self._ensure_init()
                self._long_term.delete(entry.entry_id)
            except Exception:
                pass
            return True

        # Try long-term
        try:
            self._ensure_init()
            lt_entry = self._long_term.get_by_key(key)
            if lt_entry:
                return self._long_term.delete(lt_entry.entry_id)
        except Exception:
            pass
        return False

    def save_checkpoint(
        self,
        graph_id: str,
        state: Dict[str, Any],
        label: str = "",
        step_count: int = 0,
    ) -> CheckpointEntry:
        """Save a checkpoint."""
        checkpoint = CheckpointEntry(
            graph_id=graph_id,
            label=label,
            state=state,
            step_count=step_count,
        )
        try:
            self._ensure_init()
            self._long_term.store_checkpoint(checkpoint)
        except Exception as e:
            logger.warning("Failed to save checkpoint: %s", e)
        return checkpoint

    def load_checkpoint(self, checkpoint_id: str) -> Optional[CheckpointEntry]:
        """Load a checkpoint by ID."""
        try:
            self._ensure_init()
            return self._long_term.load_checkpoint(checkpoint_id)
        except Exception:
            return None

    def list_checkpoints(self, graph_id: Optional[str] = None) -> List[CheckpointEntry]:
        """List stored checkpoints."""
        try:
            self._ensure_init()
            return self._long_term.list_checkpoints(graph_id)
        except Exception:
            return []

    @property
    def stats(self) -> Dict[str, Any]:
        """Memory statistics."""
        stats = {"short_term_entries": len(self._short_term)}
        try:
            self._ensure_init()
            stats.update(self._long_term.get_stats())
        except Exception:
            pass
        return stats
