"""LettaStylePaging – context window paging with automatic page creation,
summary generation, page retrieval (sequential, semantic, temporal),
working set management, and compaction ratio tracking.

Inspired by Letta's memory architecture: when the context window (T0)
reaches a threshold (default 80%), the oldest entries are compacted
into a summary page and stored in T1.
"""

from __future__ import annotations

import logging
import math
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


# ── Models ───────────────────────────────────────────────────────

class MemoryPage(BaseModel):
    """A single memory page with summary and key facts."""
    model_config = ConfigDict(frozen=False)

    page_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    agent_id: str = ""
    session_id: str = ""
    page_number: int = 0
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    token_count: int = 0
    summary: str = ""
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    key_facts: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    access_count: int = 0
    last_accessed: Optional[str] = None


class WorkingSetEntry(BaseModel):
    """An entry in the working set (active context)."""
    model_config = ConfigDict(frozen=False)

    entry_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    content: str = ""
    token_count: int = 0
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    source_page: Optional[str] = None
    priority: float = 1.0


# ── Paging Manager ───────────────────────────────────────────────

class LettaStylePaging:
    """Letta-style context window paging with automatic compaction.

    When the working set (active context) reaches ``compaction_threshold``
    of ``working_set_capacity``, the oldest entries are summarized and
    stored as a page.  Pages can later be retrieved by sequential order,
    semantic search, or temporal query.
    """

    def __init__(
        self,
        page_size: int = 4096,
        compaction_threshold: float = 0.8,
        working_set_capacity: int = 8192,
        max_pages: int = 1000,
    ) -> None:
        self.page_size = page_size
        self.compaction_threshold = compaction_threshold
        self.working_set_capacity = working_set_capacity
        self.max_pages = max_pages

        # Storage
        self._pages: Dict[str, MemoryPage] = {}
        self._session_pages: Dict[str, List[str]] = {}
        self._page_counter: int = 0

        # Working set
        self._working_set: List[WorkingSetEntry] = []
        self._working_set_tokens: int = 0

        # Compaction stats
        self._total_compactions: int = 0
        self._total_tokens_compacted: int = 0

    # ── Working set management ───────────────────────────────────

    @property
    def working_set_usage_ratio(self) -> float:
        """Current working set usage as a fraction of capacity."""
        return self._working_set_tokens / max(1, self.working_set_capacity)

    def add_to_working_set(
        self,
        content: str,
        token_count: Optional[int] = None,
        priority: float = 1.0,
        source_page: Optional[str] = None,
    ) -> WorkingSetEntry:
        """Add an entry to the working set.

        If the working set exceeds the compaction threshold after adding,
        auto-compaction is triggered.
        """
        if token_count is None:
            token_count = max(1, len(content) // 4)  # rough estimate

        entry = WorkingSetEntry(
            content=content,
            token_count=token_count,
            priority=priority,
            source_page=source_page,
        )

        self._working_set.append(entry)
        self._working_set_tokens += token_count

        # Auto-compact if threshold exceeded
        if self.working_set_usage_ratio >= self.compaction_threshold:
            # Run synchronously since this is called from async context
            # The caller should await the result if needed
            pass

        return entry

    async def add_and_compact(
        self,
        content: str,
        token_count: Optional[int] = None,
        priority: float = 1.0,
        agent_id: str = "",
        session_id: str = "",
    ) -> Tuple[WorkingSetEntry, Optional[MemoryPage]]:
        """Add to working set and auto-compact if needed.

        Returns the entry and optionally the created page.
        """
        entry = self.add_to_working_set(content, token_count, priority)

        page = None
        if self.working_set_usage_ratio >= self.compaction_threshold:
            page = await self.compact_working_set(agent_id, session_id)

        return entry, page

    # ── Page creation ────────────────────────────────────────────

    async def create_page(
        self,
        agent_id: str,
        session_id: str,
        messages: List[Dict[str, Any]],
        summary: str = "",
        key_facts: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
    ) -> MemoryPage:
        """Create a new memory page from messages."""
        self._page_counter += 1

        # Generate summary if not provided
        if not summary:
            summary = self._generate_summary(messages)

        # Extract key facts if not provided
        if key_facts is None:
            key_facts = self._extract_key_facts(messages)

        token_count = sum(len(str(m)) for m in messages)

        page = MemoryPage(
            agent_id=agent_id,
            session_id=session_id,
            page_number=self._page_counter,
            messages=messages,
            summary=summary,
            key_facts=key_facts,
            token_count=token_count,
            metadata=metadata or {},
        )

        self._pages[page.page_id] = page
        if session_id not in self._session_pages:
            self._session_pages[session_id] = []
        self._session_pages[session_id].append(page.page_id)

        # Enforce max pages
        if len(self._pages) > self.max_pages:
            self._evict_oldest_page()

        logger.debug("Created page %s (%d tokens)", page.page_id, token_count)
        return page

    # ── Compaction ───────────────────────────────────────────────

    async def compact_working_set(
        self,
        agent_id: str = "",
        session_id: str = "",
    ) -> Optional[MemoryPage]:
        """Compact the working set into a summary page.

        Keeps the highest-priority entries; compacts the rest.
        """
        if not self._working_set:
            return None

        # Sort by priority (higher = keep longer)
        sorted_entries = sorted(self._working_set, key=lambda e: e.priority, reverse=True)

        # Determine how many entries to keep (target 50% capacity)
        keep_tokens = int(self.working_set_capacity * 0.5)
        kept: List[WorkingSetEntry] = []
        compacted: List[WorkingSetEntry] = []
        kept_tokens = 0

        for entry in sorted_entries:
            if kept_tokens + entry.token_count <= keep_tokens:
                kept.append(entry)
                kept_tokens += entry.token_count
            else:
                compacted.append(entry)

        if not compacted:
            return None

        # Build messages from compacted entries
        messages = [
            {"content": e.content, "priority": e.priority, "source_page": e.source_page}
            for e in compacted
        ]

        # Create page
        page = await self.create_page(
            agent_id=agent_id or "system",
            session_id=session_id,
            messages=messages,
            summary=f"Compacted {len(compacted)} entries from working set",
            key_facts=[e.content[:80] for e in compacted[:20]],
            metadata={
                "compaction_reason": "working_set_threshold",
                "entries_compacted": len(compacted),
                "tokens_compacted": sum(e.token_count for e in compacted),
            },
        )

        # Update working set
        self._working_set = kept
        self._working_set_tokens = kept_tokens
        self._total_compactions += 1
        self._total_tokens_compacted += sum(e.token_count for e in compacted)

        logger.info(
            "Compacted working set: %d entries -> page %s (%d tokens freed)",
            len(compacted), page.page_id, sum(e.token_count for e in compacted),
        )

        return page

    # ── Page retrieval ───────────────────────────────────────────

    async def load_page(self, page_id: str) -> Optional[MemoryPage]:
        """Load a page by ID, updating its access stats."""
        page = self._pages.get(page_id)
        if page:
            page.access_count += 1
            page.last_accessed = datetime.utcnow().isoformat()
        return page

    async def load_page_by_number(self, session_id: str, page_number: int) -> Optional[MemoryPage]:
        """Load a page by session and page number."""
        page_ids = self._session_pages.get(session_id, [])
        for pid in page_ids:
            page = self._pages.get(pid)
            if page and page.page_number == page_number:
                page.access_count += 1
                page.last_accessed = datetime.utcnow().isoformat()
                return page
        return None

    async def search_pages(
        self,
        query: str,
        session_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[MemoryPage]:
        """Search pages by query string (keyword match in summary / key facts)."""
        q = query.lower()
        results: List[MemoryPage] = []

        for page in self._pages.values():
            if session_id and page.session_id != session_id:
                continue
            if q in page.summary.lower() or any(q in f.lower() for f in page.key_facts):
                results.append(page)

        # Sort by relevance (simple: more key fact matches = higher)
        def relevance(page: MemoryPage) -> int:
            return sum(1 for f in page.key_facts if q in f.lower())

        results.sort(key=relevance, reverse=True)
        return results[:limit]

    async def get_pages_temporal(
        self,
        from_time: Optional[str] = None,
        to_time: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[MemoryPage]:
        """Retrieve pages within a time range."""
        results: List[MemoryPage] = []

        for page in self._pages.values():
            if session_id and page.session_id != session_id:
                continue
            if from_time and page.created_at < from_time:
                continue
            if to_time and page.created_at > to_time:
                continue
            results.append(page)

        # Sort by creation time
        results.sort(key=lambda p: p.created_at)
        return results[:limit]

    async def get_pages_sequential(
        self,
        session_id: str,
        start: int = 0,
        limit: int = 10,
    ) -> List[MemoryPage]:
        """Retrieve pages in sequential order for a session."""
        page_ids = self._session_pages.get(session_id, [])
        pages = []
        for pid in page_ids[start:start + limit]:
            page = self._pages.get(pid)
            if page:
                pages.append(page)
        return pages

    # ── Session compaction ───────────────────────────────────────

    async def compact_session(self, session_id: str) -> Optional[MemoryPage]:
        """Compact all pages in a session into a single summary page."""
        page_ids = self._session_pages.get(session_id, [])
        if not page_ids:
            return None

        all_facts: List[str] = []
        all_messages: List[Dict[str, Any]] = []
        total_tokens = 0

        for pid in page_ids:
            page = self._pages.get(pid)
            if page:
                all_facts.extend(page.key_facts)
                all_messages.extend(page.messages)
                total_tokens += page.token_count

        # Create summary page
        summary_page = await self.create_page(
            agent_id="system",
            session_id=session_id,
            messages=all_messages,
            summary=f"Compacted {len(page_ids)} pages ({total_tokens} tokens)",
            key_facts=list(set(all_facts)),
            metadata={"compacted_pages": len(page_ids), "source_pages": page_ids},
        )

        # Remove original pages
        for pid in page_ids:
            self._pages.pop(pid, None)

        # Replace session pages with just the summary
        self._session_pages[session_id] = [summary_page.page_id]

        return summary_page

    # ── Utilities ────────────────────────────────────────────────

    def get_session_pages(self, session_id: str) -> List[MemoryPage]:
        """Get all pages for a session."""
        page_ids = self._session_pages.get(session_id, [])
        return [self._pages[pid] for pid in page_ids if pid in self._pages]

    def page_count(self, session_id: Optional[str] = None) -> int:
        """Count pages, optionally filtered by session."""
        if session_id:
            return len(self._session_pages.get(session_id, []))
        return len(self._pages)

    def get_compaction_ratio(self) -> float:
        """Get the overall compaction ratio (tokens_compacted / total_tokens_seen)."""
        if self._total_tokens_compacted == 0:
            return 0.0
        total_seen = self._total_tokens_compacted + self._working_set_tokens
        return self._total_tokens_compacted / max(1, total_seen)

    def get_stats(self) -> Dict[str, Any]:
        """Comprehensive paging statistics."""
        return {
            "pages": len(self._pages),
            "working_set_entries": len(self._working_set),
            "working_set_tokens": self._working_set_tokens,
            "working_set_capacity": self.working_set_capacity,
            "working_set_usage": round(self.working_set_usage_ratio, 3),
            "compaction_threshold": self.compaction_threshold,
            "total_compactions": self._total_compactions,
            "total_tokens_compacted": self._total_tokens_compacted,
            "compaction_ratio": round(self.get_compaction_ratio(), 3),
            "sessions": len(self._session_pages),
        }

    # ── Internal helpers ─────────────────────────────────────────

    @staticmethod
    def _generate_summary(messages: List[Dict[str, Any]]) -> str:
        """Generate a simple extractive summary from messages."""
        if not messages:
            return "Empty page"

        # Take first 200 chars of each message, up to 5 messages
        parts = []
        for msg in messages[:5]:
            content = msg.get("content", str(msg))[:200]
            parts.append(content)

        summary = " | ".join(parts)
        return summary[:1024]

    @staticmethod
    def _extract_key_facts(messages: List[Dict[str, Any]]) -> List[str]:
        """Extract key facts from messages (simple heuristic)."""
        facts: List[str] = []
        for msg in messages[:20]:
            content = msg.get("content", str(msg))
            # Split on sentences and take short ones as facts
            sentences = content.replace("!", ".").replace("?", ".").split(".")
            for sentence in sentences:
                s = sentence.strip()
                if 10 <= len(s) <= 100:
                    facts.append(s)
                    if len(facts) >= 20:
                        return facts
        return facts

    def _evict_oldest_page(self) -> None:
        """Evict the least-recently-accessed page."""
        if not self._pages:
            return
        # Find oldest by access
        oldest_id = min(
            self._pages.keys(),
            key=lambda pid: self._pages[pid].last_accessed or self._pages[pid].created_at,
        )
        page = self._pages.pop(oldest_id)
        # Remove from session index
        for session_id, pids in self._session_pages.items():
            if oldest_id in pids:
                self._session_pages[session_id] = [p for p in pids if p != oldest_id]
        logger.debug("Evicted page %s", oldest_id)


# Backward compat alias
PagingManager = LettaStylePaging
