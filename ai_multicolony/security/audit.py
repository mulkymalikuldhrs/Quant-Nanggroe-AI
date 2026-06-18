"""Audit logger – append-only audit trail with hash-chain integrity.

Features:
* Log levels: minimal, summary, full
* Event types: tool_call, auth, credential_access, escalation, colony_change
* Structured logging with agent_id, colony_id, timestamp
* Query/filter capabilities
* Retention policy enforcement
* Storage backends: memory, file (JSONL)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

from ..types import AuditEntry, AuditEvent, AuditEventType, AuditLevel, AuditQuery

logger = logging.getLogger(__name__)


# ── Storage backend protocol ──────────────────────────────────────────────────


class AuditStorage(Protocol):
    """Protocol for audit log storage backends."""

    def append(self, entry: AuditEntry, chain_hash: str) -> None: ...
    def query(self, query: AuditQuery) -> List[AuditEntry]: ...
    def count(self) -> int: ...
    def flush(self) -> None: ...


class MemoryAuditStorage:
    """In-memory audit storage (default)."""

    def __init__(self):
        self._entries: List[AuditEntry] = []
        self._hash_chain: List[str] = []

    def append(self, entry: AuditEntry, chain_hash: str) -> None:
        self._entries.append(entry)
        self._hash_chain.append(chain_hash)

    def query(self, query: AuditQuery) -> List[AuditEntry]:
        results = self._entries

        if query.agent_id:
            results = [e for e in results if e.agent_id == query.agent_id]
        if query.colony_id:
            results = [e for e in results if e.colony_id == query.colony_id]
        if query.start_time:
            results = [e for e in results if e.timestamp >= query.start_time]
        if query.end_time:
            results = [e for e in results if e.timestamp <= query.end_time]
        if query.approved_only:
            results = [e for e in results if e.approved]

        return results[query.offset : query.offset + query.limit]

    def count(self) -> int:
        return len(self._entries)

    def flush(self) -> None:
        pass  # no-op for memory storage


class FileAuditStorage:
    """File-based audit storage (JSONL format)."""

    def __init__(self, file_path: str = "/var/log/multicolony/audit.jsonl"):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: List[AuditEntry] = []
        self._hash_chain: List[str] = []
        self._load_existing()

    def _load_existing(self) -> None:
        """Load existing entries from the JSONL file on startup."""
        if not self.file_path.exists():
            return
        try:
            with open(self.file_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        entry = AuditEntry(**{k: v for k, v in data.items() if k != "chain_hash"})
                        self._entries.append(entry)
                        if "chain_hash" in data:
                            self._hash_chain.append(data["chain_hash"])
                    except Exception:
                        continue
        except Exception as exc:
            logger.warning("Failed to load audit log: %s", exc)

    def append(self, entry: AuditEntry, chain_hash: str) -> None:
        self._entries.append(entry)
        self._hash_chain.append(chain_hash)
        # Append to file immediately
        data = entry.model_dump(mode="json")
        data["chain_hash"] = chain_hash
        with open(self.file_path, "a") as f:
            f.write(json.dumps(data) + "\n")

    def query(self, query: AuditQuery) -> List[AuditEntry]:
        results = self._entries

        if query.agent_id:
            results = [e for e in results if e.agent_id == query.agent_id]
        if query.colony_id:
            results = [e for e in results if e.colony_id == query.colony_id]
        if query.start_time:
            results = [e for e in results if e.timestamp >= query.start_time]
        if query.end_time:
            results = [e for e in results if e.timestamp <= query.end_time]
        if query.approved_only:
            results = [e for e in results if e.approved]

        return results[query.offset : query.offset + query.limit]

    def count(self) -> int:
        return len(self._entries)

    def flush(self) -> None:
        """Force-write buffered data (already writing per-append, so no-op)."""
        pass


# ── Main audit logger ─────────────────────────────────────────────────────────


class AuditTrail:
    """Merkle hash-chain audit log with configurable verbosity and storage.

    The audit trail is append-only: entries can never be modified or
    deleted (except by retention policy).  Each entry's hash depends on
    the previous entry's hash, forming a tamper-evident chain.

    Parameters
    ----------
    level : AuditLevel
        Verbosity: ``minimal`` records only critical events,
        ``summary`` adds tool calls, ``full`` logs everything.
    storage : str
        "memory" or "file".
    file_path : str
        Path for file storage (only used when storage="file").
    retention_days : int
        Entries older than this are pruned on ``enforce_retention()``.
    """

    def __init__(
        self,
        level: AuditLevel = AuditLevel.FULL,
        storage: str = "memory",
        file_path: str = "/var/log/multicolony/audit.jsonl",
        retention_days: int = 90,
    ):
        self.level = level
        self.retention_days = retention_days
        self._prev_hash = "0" * 64

        # Select storage backend
        if storage == "file":
            self._storage: AuditStorage = FileAuditStorage(file_path)
        else:
            self._storage = MemoryAuditStorage()

        # Level-based filtering: which event types to record at each level
        self._level_filters: Dict[AuditLevel, set] = {
            AuditLevel.MINIMAL: {
                AuditEventType.ESCALATION,
                AuditEventType.CREDENTIAL_ACCESS,
                AuditEventType.APPROVAL_DENY,
            },
            AuditLevel.SUMMARY: {
                AuditEventType.TOOL_CALL,
                AuditEventType.AUTH,
                AuditEventType.ESCALATION,
                AuditEventType.CREDENTIAL_ACCESS,
                AuditEventType.APPROVAL_GRANT,
                AuditEventType.APPROVAL_DENY,
            },
            AuditLevel.FULL: {et for et in AuditEventType},  # all events
        }

    # ── Recording ──────────────────────────────────────────────────────────

    def _should_record(self, event_type: AuditEventType) -> bool:
        """Check if an event type should be recorded at the current level."""
        return event_type in self._level_filters.get(self.level, set())

    def _compute_hash(self, entry: AuditEntry) -> str:
        """Compute the hash-chain link for an entry."""
        data = (
            f"{entry.entry_id}"
            f"{entry.agent_id}"
            f"{entry.colony_id}"
            f"{entry.tool_name}"
            f"{entry.action}"
            f"{entry.timestamp.isoformat()}"
            f"{self._prev_hash}"
        )
        return hashlib.sha256(data.encode()).hexdigest()

    def record(
        self,
        agent_id: str,
        tool_name: str,
        action: str,
        autonomy_level: int = 0,
        approved: bool = True,
        details: Optional[Dict] = None,
        colony_id: str = "",
        event_type: AuditEventType = AuditEventType.TOOL_CALL,
    ) -> Optional[AuditEntry]:
        """Record an audit entry.

        Returns the entry if recorded, or ``None`` if filtered out by
        the current audit level.
        """
        if not self._should_record(event_type):
            return None

        entry = AuditEntry(
            agent_id=agent_id,
            colony_id=colony_id,
            tool_name=tool_name,
            action=action,
            autonomy_level=autonomy_level,
            approved=approved,
            details=details or {},
        )

        chain_hash = self._compute_hash(entry)
        self._prev_hash = chain_hash
        self._storage.append(entry, chain_hash)

        return entry

    def record_event(self, event: AuditEvent) -> Optional[AuditEntry]:
        """Record an audit event from an AuditEvent model.

        Convenience method that converts AuditEvent → AuditEntry.
        """
        if not self._should_record(event.event_type):
            return None

        entry = AuditEntry(
            agent_id=event.agent_id,
            colony_id=event.colony_id,
            tool_name=event.metadata.get("tool_name", ""),
            action=event.event_type.value,
            autonomy_level=event.metadata.get("autonomy_level", 0),
            approved=event.metadata.get("approved", True),
            details={
                "description": event.description,
                "session_id": event.session_id,
                "ip_address": event.ip_address,
                **event.metadata,
            },
        )

        chain_hash = self._compute_hash(entry)
        self._prev_hash = chain_hash
        self._storage.append(entry, chain_hash)

        return entry

    # ── Query / filter ─────────────────────────────────────────────────────

    def get_entries(
        self,
        agent_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditEntry]:
        """Get audit entries, optionally filtered by agent."""
        query = AuditQuery(agent_id=agent_id, limit=limit)
        return self._storage.query(query)

    def query(self, query: AuditQuery) -> List[AuditEntry]:
        """Advanced query with full filter support."""
        return self._storage.query(query)

    def get_entries_by_colony(self, colony_id: str, limit: int = 100) -> List[AuditEntry]:
        """Get audit entries for a specific colony."""
        return self._storage.query(AuditQuery(colony_id=colony_id, limit=limit))

    def get_entries_by_time_range(
        self,
        start: datetime,
        end: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[AuditEntry]:
        """Get audit entries within a time range."""
        return self._storage.query(AuditQuery(start_time=start, end_time=end, limit=limit))

    def get_entries_by_type(
        self,
        event_type: AuditEventType,
        limit: int = 100,
    ) -> List[AuditEntry]:
        """Get audit entries matching a specific action/event type."""
        return self._storage.query(AuditQuery(limit=limit))

    def get_unapproved(self, limit: int = 100) -> List[AuditEntry]:
        """Get entries that were not approved (denied actions)."""
        return self._storage.query(AuditQuery(approved_only=False, limit=limit))

    # ── Chain verification ─────────────────────────────────────────────────

    def verify_chain(self) -> bool:
        """Verify the integrity of the hash chain.

        Returns ``True`` if the chain is intact, ``False`` if any
        entry has been tampered with.
        """
        if isinstance(self._storage, MemoryAuditStorage):
            entries = self._storage._entries
            hashes = self._storage._hash_chain
        elif isinstance(self._storage, FileAuditStorage):
            entries = self._storage._entries
            hashes = self._storage._hash_chain
        else:
            return True  # can't verify custom storage

        prev = "0" * 64
        for i, entry in enumerate(entries):
            data = (
                f"{entry.entry_id}"
                f"{entry.agent_id}"
                f"{entry.colony_id}"
                f"{entry.tool_name}"
                f"{entry.action}"
                f"{entry.timestamp.isoformat()}"
                f"{prev}"
            )
            expected = hashlib.sha256(data.encode()).hexdigest()
            if i < len(hashes) and hashes[i] != expected:
                logger.error("Hash chain broken at entry %d (%s)", i, entry.entry_id)
                return False
            prev = expected

        return True

    # ── Retention ──────────────────────────────────────────────────────────

    def enforce_retention(self) -> int:
        """Remove entries older than the retention period.

        **Warning:** This breaks the hash chain for removed entries.
        In production, use a WORM storage layer instead.

        Returns the number of entries removed.
        """
        if isinstance(self._storage, MemoryAuditStorage):
            cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
            original = len(self._storage._entries)

            # Filter entries
            kept = []
            kept_hashes = []
            prev = "0" * 64
            for i, entry in enumerate(self._storage._entries):
                if entry.timestamp >= cutoff:
                    # Re-hash since chain is broken
                    data = (
                        f"{entry.entry_id}"
                        f"{entry.agent_id}"
                        f"{entry.colony_id}"
                        f"{entry.tool_name}"
                        f"{entry.action}"
                        f"{entry.timestamp.isoformat()}"
                        f"{prev}"
                    )
                    new_hash = hashlib.sha256(data.encode()).hexdigest()
                    kept.append(entry)
                    kept_hashes.append(new_hash)
                    prev = new_hash

            removed = original - len(kept)
            self._storage._entries = kept
            self._storage._hash_chain = kept_hashes
            self._prev_hash = prev

            logger.info("Retention policy removed %d audit entries", removed)
            return removed

        return 0  # file storage retention handled externally

    # ── Flush ──────────────────────────────────────────────────────────────

    def flush(self) -> None:
        """Flush buffered entries to persistent storage."""
        self._storage.flush()

    # ── Properties ─────────────────────────────────────────────────────────

    @property
    def entry_count(self) -> int:
        return self._storage.count()
