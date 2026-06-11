"""MemoryTool – memory operations for the agent context.

Autonomy levels:
  - L0: search, load_page
  - L1: store
  - L2: compact, delete
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import MCPTool

logger = logging.getLogger(__name__)


class MemoryEntry:
    """A single entry in the in-memory store."""

    __slots__ = ("key", "value", "metadata", "created_at", "updated_at", "access_count")

    def __init__(self, key: str, value: Any, metadata: Optional[Dict] = None) -> None:
        self.key = key
        self.value = value
        self.metadata = metadata or {}
        self.created_at: str = datetime.now(timezone.utc).isoformat()
        self.updated_at: str = self.created_at
        self.access_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "access_count": self.access_count,
        }


class MemoryPage:
    """A compacted page of memory entries."""

    def __init__(
        self,
        page_id: str,
        summary: str,
        key_facts: List[str],
        entry_count: int,
        metadata: Optional[Dict] = None,
    ) -> None:
        self.page_id = page_id
        self.summary = summary
        self.key_facts = key_facts
        self.entry_count = entry_count
        self.metadata = metadata or {}
        self.created_at: str = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_id": self.page_id,
            "summary": self.summary,
            "key_facts": self.key_facts,
            "entry_count": self.entry_count,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


class MemoryTool(MCPTool):
    """Memory operations: store, search, load, compact, delete.

    This tool provides a lightweight in-memory store that integrates
    with the broader :mod:`memory` subsystem.  For persistent /
    vector-backed storage, use the :class:`MemoryManager` directly.
    """

    # ── MCPTool interface ────────────────────────────────────────

    def name(self) -> str:
        return "memory.manage"

    def category(self) -> str:
        return "memory"

    def autonomy_level(self) -> int:
        return 0  # minimum; varies per action

    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["action"],
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["store", "retrieve", "search", "compact", "delete", "load_page", "stats"],
                    "description": "Memory action",
                },
                "key": {"type": "string", "description": "Memory key"},
                "value": {"type": "object", "description": "Value to store"},
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "default": 10, "description": "Max results"},
                "page_id": {"type": "string", "description": "Memory page ID to load"},
                "metadata": {"type": "object", "description": "Optional metadata for stored value"},
            },
        }

    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "data": {"type": "object"},
                "results": {"type": "array"},
            },
        }

    def error_codes(self) -> List[Dict[str, Any]]:
        return [
            {"code": 8001, "message": "Key not found"},
            {"code": 8002, "message": "Memory page not found"},
            {"code": 8003, "message": "Compaction failed"},
        ]

    # ── Constructor ──────────────────────────────────────────────

    def __init__(self) -> None:
        super().__init__()
        self._store: Dict[str, MemoryEntry] = {}
        self._pages: Dict[str, MemoryPage] = {}

    # ── Autonomy mapping ─────────────────────────────────────────

    @staticmethod
    def action_autonomy(action: str) -> int:
        mapping = {
            "search": 0, "retrieve": 0, "load_page": 0, "stats": 0,
            "store": 1,
            "compact": 2, "delete": 2,
        }
        return mapping.get(action, 1)

    # ── Execute ──────────────────────────────────────────────────

    async def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        action: str = params["action"]
        autonomy = context.get("autonomy_level", 0)
        required = self.action_autonomy(action)

        if autonomy < required:
            self.record_call(False)
            return {
                "success": False,
                "data": {"error": f"Action '{action}' requires L{required}, current L{autonomy}"},
                "results": [],
            }

        dispatch = {
            "store": self._store_op,
            "retrieve": self._retrieve,
            "search": self._search,
            "compact": self._compact,
            "delete": self._delete,
            "load_page": self._load_page,
            "stats": self._stats,
        }

        handler = dispatch.get(action)
        if handler is None:
            self.record_call(False)
            return {"success": False, "data": {"error": f"Unknown action: {action}"}, "results": []}

        start = time.monotonic()
        try:
            result = await handler(params)
            duration = (time.monotonic() - start) * 1000
            self.record_call(result.get("success", True), duration)
            return result
        except Exception as exc:
            duration = (time.monotonic() - start) * 1000
            self.record_call(False, duration)
            return {"success": False, "data": {"error": str(exc)}, "results": []}

    # ── Action implementations ───────────────────────────────────

    async def _store_op(self, params: Dict[str, Any]) -> Dict[str, Any]:
        key = params.get("key", "")
        value = params.get("value", {})
        metadata = params.get("metadata")

        if not key:
            return {"success": False, "data": {"error": "Key is required"}, "results": []}

        if key in self._store:
            # Update existing entry
            entry = self._store[key]
            entry.value = value
            entry.updated_at = datetime.now(timezone.utc).isoformat()
            if metadata:
                entry.metadata.update(metadata)
            return {
                "success": True,
                "data": {"key": key, "action": "updated"},
                "results": [],
            }

        entry = MemoryEntry(key=key, value=value, metadata=metadata)
        self._store[key] = entry
        return {
            "success": True,
            "data": {"key": key, "action": "created", "created_at": entry.created_at},
            "results": [],
        }

    async def _retrieve(self, params: Dict[str, Any]) -> Dict[str, Any]:
        key = params.get("key", "")

        if key not in self._store:
            return {"success": False, "data": {"error": f"Key not found: {key}"}, "results": []}

        entry = self._store[key]
        entry.access_count += 1
        entry.updated_at = datetime.now(timezone.utc).isoformat()
        return {
            "success": True,
            "data": entry.to_dict(),
            "results": [],
        }

    async def _search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = params.get("query", "")
        limit = params.get("limit", 10)

        if not query:
            # Return all keys
            results = [{"key": k, "relevance": 1.0} for k in self._store.keys()]
            return {"success": True, "data": {}, "results": results[:limit]}

        q_lower = query.lower()
        results = []
        for key, entry in self._store.items():
            # Match on key
            if q_lower in key.lower():
                results.append({"key": key, "relevance": 1.0, "match": "key"})
                continue
            # Match on value (stringified)
            val_str = str(entry.value).lower()
            if q_lower in val_str:
                results.append({"key": key, "relevance": 0.8, "match": "value"})
                continue
            # Match on metadata
            for mk, mv in entry.metadata.items():
                if q_lower in str(mk).lower() or q_lower in str(mv).lower():
                    results.append({"key": key, "relevance": 0.6, "match": "metadata"})
                    break

        # Sort by relevance
        results.sort(key=lambda r: r["relevance"], reverse=True)
        return {"success": True, "data": {}, "results": results[:limit]}

    async def _compact(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Compact all memory entries into a summary page."""
        if not self._store:
            return {"success": True, "data": {"pages_compacted": 0, "message": "Nothing to compact"}, "results": []}

        # Build summary and key facts from entries
        keys = list(self._store.keys())
        summary = f"Compacted {len(keys)} memory entries: " + ", ".join(keys[:20])
        key_facts = [f"{k}: {str(self._store[k].value)[:50]}" for k in keys[:30]]

        page = MemoryPage(
            page_id=uuid.uuid4().hex[:12],
            summary=summary,
            key_facts=key_facts,
            entry_count=len(keys),
            metadata={"compaction_time": datetime.now(timezone.utc).isoformat()},
        )
        self._pages[page.page_id] = page

        # Clear the store
        self._store.clear()

        return {
            "success": True,
            "data": {
                "page_id": page.page_id,
                "pages_compacted": 1,
                "entries_compacted": page.entry_count,
                "key_facts_count": len(key_facts),
            },
            "results": [],
        }

    async def _delete(self, params: Dict[str, Any]) -> Dict[str, Any]:
        key = params.get("key", "")
        if key in self._store:
            del self._store[key]
            return {"success": True, "data": {"key": key, "deleted": True}, "results": []}
        return {"success": False, "data": {"error": f"Key not found: {key}"}, "results": []}

    async def _load_page(self, params: Dict[str, Any]) -> Dict[str, Any]:
        page_id = params.get("page_id", "")
        if page_id not in self._pages:
            return {"success": False, "data": {"error": f"Page not found: {page_id}"}, "results": []}
        page = self._pages[page_id]
        return {"success": True, "data": page.to_dict(), "results": []}

    async def _stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "success": True,
            "data": {
                "entries": len(self._store),
                "pages": len(self._pages),
                "keys": list(self._store.keys()),
            },
            "results": [],
        }
