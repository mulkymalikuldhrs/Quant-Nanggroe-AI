"""MemoryManager – unified memory gateway for the AI-MultiColony ecosystem.

Routes operations to the appropriate memory tier, manages context window
(T0) lifecycle, orchestrates compaction, and provides cross-store
synchronization and statistics.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


# ── Memory tiers ─────────────────────────────────────────────────

class MemoryTier:
    """Memory tier constants."""
    T0_CONTEXT = "t0_context"        # Active context window (hot)
    T1_LETTA = "t1_letta"           # Letta-style paged memory
    T2_VECTOR = "t2_vector"         # Vector / embedding store
    T3_TEMPORAL = "t3_temporal"     # Temporal knowledge graph
    T4_TREE = "t4_tree"             # Hierarchical tree store


# ── Pydantic models ──────────────────────────────────────────────

class MemoryPageModel(BaseModel):
    """A memory page (T1 Letta tier)."""
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


class TemporalFactModel(BaseModel):
    """A temporal fact (T3 tier)."""
    model_config = ConfigDict(frozen=False)

    fact_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    subject: str = ""
    predicate: str = ""
    obj: str = ""
    valid_from: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    valid_to: Optional[str] = None
    confidence: float = 1.0
    source: Dict[str, Any] = Field(default_factory=dict)


class TreeNodeModel(BaseModel):
    """A tree node (T4 tier)."""
    model_config = ConfigDict(frozen=False)

    node_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    parent_id: Optional[str] = None
    path: str = "/"
    node_type: str = "generic"
    content: Dict[str, Any] = Field(default_factory=dict)
    children: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    access_count: int = 0


# ── Memory Manager ───────────────────────────────────────────────

class MemoryManager:
    """Unified memory gateway managing all memory tiers.

    Tiers
    -----
    T0 – Context window: active conversation / working context.
          Auto-compacts when usage exceeds ``compaction_threshold``.
    T1 – Letta-style paged memory: conversation pages with summaries.
    T2 – Vector store: embedding-based semantic search.
    T3 – Temporal knowledge graph: time-bound facts and relations.
    T4 – Tree store: hierarchical data (file trees, org charts, etc.).

    The manager acts as a router: ``store`` and ``retrieve`` automatically
    select the correct tier based on the ``tier`` parameter.
    """

    def __init__(
        self,
        compaction_threshold: float = 0.8,
        page_size: int = 4096,
        context_capacity: int = 8192,
    ) -> None:
        self.compaction_threshold = compaction_threshold
        self.page_size = page_size
        self.context_capacity = context_capacity

        # T0 – context window
        self._context_window: List[Dict[str, Any]] = []
        self._context_usage: int = 0

        # T1 – paged memory
        self._pages: Dict[str, MemoryPageModel] = {}
        self._page_counter: int = 0

        # T2 – vector store (delegated to VectorStore)
        self._vectors: Dict[str, Dict[str, Any]] = {}

        # T3 – temporal facts
        self._temporal_facts: List[TemporalFactModel] = []

        # T4 – tree nodes
        self._tree_nodes: Dict[str, TreeNodeModel] = {}

        # Sessions
        self._sessions: Dict[str, Dict[str, Any]] = {}

        # Compaction stats
        self._compaction_count: int = 0

    # ── Properties ───────────────────────────────────────────────

    @property
    def context_usage_ratio(self) -> float:
        """Current T0 context usage as a fraction of capacity."""
        return self._context_usage / max(1, self.context_capacity)

    # ── Store ────────────────────────────────────────────────────

    async def store(
        self,
        key: str,
        value: Any,
        tier: str = MemoryTier.T1_LETTA,
        metadata: Optional[Dict] = None,
    ) -> str:
        """Store data in the specified memory tier.

        Returns the ID of the created record.
        """
        store_id = uuid.uuid4().hex[:12]

        if tier == MemoryTier.T0_CONTEXT:
            self._context_window.append({
                "id": store_id,
                "key": key,
                "value": value,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {},
            })
            self._context_usage += len(str(value))
            # Auto-compact if threshold exceeded
            if self.context_usage_ratio >= self.compaction_threshold:
                await self.compact()

        elif tier == MemoryTier.T1_LETTA:
            self._page_counter += 1
            page = MemoryPageModel(
                page_id=store_id,
                summary=str(value),
                key_facts=[key],
                page_number=self._page_counter,
                token_count=len(str(value)),
                metadata=metadata or {},
            )
            self._pages[page.page_id] = page

        elif tier == MemoryTier.T2_VECTOR:
            self._vectors[store_id] = {
                "id": store_id,
                "key": key,
                "value": value,
                "metadata": metadata or {},
            }

        elif tier == MemoryTier.T3_TEMPORAL:
            fact = TemporalFactModel(
                fact_id=store_id,
                subject=key,
                obj=str(value),
                source=metadata or {},
            )
            self._temporal_facts.append(fact)

        elif tier == MemoryTier.T4_TREE:
            node = TreeNodeModel(
                node_id=store_id,
                path=f"/{key}",
                content={"value": value},
                tags=metadata.get("tags", []) if metadata else [],
            )
            self._tree_nodes[node.node_id] = node

        return store_id

    # ── Retrieve ─────────────────────────────────────────────────

    async def retrieve(self, key: str, tier: Optional[str] = None) -> Optional[Any]:
        """Retrieve data from memory by key.

        If ``tier`` is None, searches all tiers in order: T0 → T1 → T2 → T3 → T4.
        """
        # T0
        if tier in (None, MemoryTier.T0_CONTEXT):
            for entry in reversed(self._context_window):
                if entry["key"] == key:
                    return entry["value"]

        # T1
        if tier in (None, MemoryTier.T1_LETTA):
            for page in self._pages.values():
                if key in page.key_facts:
                    return page.summary
                if key == page.page_id:
                    return page

        # T2
        if tier in (None, MemoryTier.T2_VECTOR):
            for vec in self._vectors.values():
                if vec["key"] == key:
                    return vec["value"]

        # T3
        if tier in (None, MemoryTier.T3_TEMPORAL):
            for fact in self._temporal_facts:
                if fact.subject == key or fact.fact_id == key:
                    return fact.obj

        # T4
        if tier in (None, MemoryTier.T4_TREE):
            for node in self._tree_nodes.values():
                if node.path.strip("/") == key or node.node_id == key:
                    return node.content

        return None

    # ── Search ───────────────────────────────────────────────────

    async def search(
        self,
        query: str,
        limit: int = 10,
        tier: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search across memory tiers by query string."""
        results: List[Dict[str, Any]] = []
        q = query.lower()

        # T1 – pages
        if tier in (None, MemoryTier.T1_LETTA):
            for page in self._pages.values():
                if q in page.summary.lower() or any(q in f.lower() for f in page.key_facts):
                    results.append({
                        "tier": "letta",
                        "page_id": page.page_id,
                        "summary": page.summary,
                        "relevance": 0.9 if q in page.summary.lower() else 0.7,
                    })

        # T2 – vectors
        if tier in (None, MemoryTier.T2_VECTOR):
            for vid, vec in self._vectors.items():
                if q in vec["key"].lower() or q in str(vec["value"]).lower():
                    results.append({
                        "tier": "vector",
                        "id": vid,
                        "key": vec["key"],
                        "relevance": 0.8,
                    })

        # T3 – temporal
        if tier in (None, MemoryTier.T3_TEMPORAL):
            for fact in self._temporal_facts:
                if q in fact.subject.lower() or q in fact.obj.lower() or q in fact.predicate.lower():
                    results.append({
                        "tier": "temporal",
                        "fact_id": fact.fact_id,
                        "subject": fact.subject,
                        "relevance": 0.85,
                    })

        # T4 – tree
        if tier in (None, MemoryTier.T4_TREE):
            for node in self._tree_nodes.values():
                if q in node.path.lower() or q in str(node.content).lower():
                    results.append({
                        "tier": "tree",
                        "node_id": node.node_id,
                        "path": node.path,
                        "relevance": 0.75,
                    })

        # Sort by relevance
        results.sort(key=lambda r: r.get("relevance", 0), reverse=True)
        return results[:limit]

    # ── Compaction ───────────────────────────────────────────────

    async def compact(self) -> Dict[str, Any]:
        """Compact the T0 context window into a T1 page.

        Triggered automatically when context usage exceeds the threshold.
        """
        if not self._context_window:
            return {"pages_compacted": 0, "message": "Nothing to compact"}

        old_count = len(self._context_window)
        old_usage = self._context_usage

        # Build summary and key facts
        summary_parts = [str(e.get("value", ""))[:200] for e in self._context_window]
        summary = " ".join(summary_parts)[:2048]
        key_facts = list({e["key"] for e in self._context_window if e.get("key")})

        # Create page
        self._page_counter += 1
        page = MemoryPageModel(
            agent_id="system",
            summary=f"Compacted context: {summary[:500]}",
            messages=list(self._context_window),
            key_facts=key_facts,
            page_number=self._page_counter,
            token_count=old_usage,
            metadata={
                "compaction_reason": "threshold_exceeded",
                "compaction_ratio": round(self.context_usage_ratio, 3),
                "entries_compacted": old_count,
            },
        )
        self._pages[page.page_id] = page

        # Clear T0
        self._context_window = []
        self._context_usage = 0
        self._compaction_count += 1

        logger.info(
            "Memory compacted: %d entries -> page %s (%d tokens freed)",
            old_count, page.page_id, old_usage,
        )

        return {
            "page_id": page.page_id,
            "entries_compacted": old_count,
            "tokens_freed": old_usage,
            "compaction_count": self._compaction_count,
        }

    # ── Page management ──────────────────────────────────────────

    async def load_page(self, page_id: str) -> Optional[MemoryPageModel]:
        """Load a memory page by ID."""
        return self._pages.get(page_id)

    async def delete_page(self, page_id: str) -> bool:
        """Delete a memory page."""
        if page_id in self._pages:
            del self._pages[page_id]
            return True
        return False

    # ── Delete ───────────────────────────────────────────────────

    async def delete(self, key: str, tier: Optional[str] = None) -> bool:
        """Delete data from memory by key."""
        deleted = False

        # T0
        if tier in (None, MemoryTier.T0_CONTEXT):
            before = len(self._context_window)
            self._context_window = [e for e in self._context_window if e["key"] != key]
            if len(self._context_window) < before:
                deleted = True
                self._context_usage = sum(len(str(e["value"])) for e in self._context_window)

        # T1
        if tier in (None, MemoryTier.T1_LETTA) and not deleted:
            for pid, page in list(self._pages.items()):
                if key in page.key_facts:
                    del self._pages[pid]
                    deleted = True
                    break

        # T2
        if tier in (None, MemoryTier.T2_VECTOR) and not deleted:
            for vid, vec in list(self._vectors.items()):
                if vec["key"] == key:
                    del self._vectors[vid]
                    deleted = True
                    break

        # T3
        if tier in (None, MemoryTier.T3_TEMPORAL) and not deleted:
            before = len(self._temporal_facts)
            self._temporal_facts = [f for f in self._temporal_facts if f.subject != key]
            if len(self._temporal_facts) < before:
                deleted = True

        return deleted

    # ── Session management ───────────────────────────────────────

    def create_session(self, agent_id: str, metadata: Optional[Dict] = None) -> str:
        """Create a new memory session."""
        session_id = uuid.uuid4().hex[:12]
        self._sessions[session_id] = {
            "agent_id": agent_id,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._sessions.get(session_id)

    # ── Cross-store sync ─────────────────────────────────────────

    async def sync_to_vector(self) -> int:
        """Sync T1 pages to T2 vector store for semantic search.

        Returns the number of pages synced.
        """
        synced = 0
        for page in self._pages.values():
            vid = f"vec-{page.page_id}"
            if vid not in self._vectors:
                self._vectors[vid] = {
                    "id": vid,
                    "key": page.page_id,
                    "value": page.summary,
                    "metadata": {"source": "letta_page", "key_facts": page.key_facts},
                }
                synced += 1
        return synced

    async def sync_to_temporal(self) -> int:
        """Sync T1 key facts to T3 temporal store.

        Returns the number of facts synced.
        """
        synced = 0
        for page in self._pages.values():
            for fact_text in page.key_facts:
                exists = any(f.subject == fact_text for f in self._temporal_facts)
                if not exists:
                    fact = TemporalFactModel(
                        subject=fact_text,
                        obj=page.summary[:200],
                        source={"page_id": page.page_id},
                    )
                    self._temporal_facts.append(fact)
                    synced += 1
        return synced

    # ── Statistics ───────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Return comprehensive memory statistics."""
        return {
            "context_usage": round(self.context_usage_ratio, 3),
            "context_capacity": self.context_capacity,
            "context_entries": len(self._context_window),
            "pages": len(self._pages),
            "vectors": len(self._vectors),
            "temporal_facts": len(self._temporal_facts),
            "tree_nodes": len(self._tree_nodes),
            "sessions": len(self._sessions),
            "compaction_count": self._compaction_count,
            "compaction_threshold": self.compaction_threshold,
        }
