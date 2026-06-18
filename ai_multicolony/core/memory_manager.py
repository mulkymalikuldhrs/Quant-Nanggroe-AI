"""Memory manager with Letta-style paging and OpenHands condensers.

Implements 8 condenser types from OpenHands and Letta-style memory paging
for efficient context window management. Also provides optional vector
search integration via Qdrant or ChromaDB.
"""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Optional

from ai_multicolony.config.logging_config import get_logger
from ai_multicolony.exceptions import MemoryError
from ai_multicolony.types.events import Event, Observation, ObservationType
from ai_multicolony.types.memory import (
    CondenserType,
    MemoryCondenserType,
    MemoryEntry,
    MemoryPage,
    MemoryQuery,
    MemoryQueryResult,
    MemorySession,
    MemoryType,
    SessionState,
)

logger = get_logger(__name__)


# === Condensers (from OpenHands) ===

class BaseCondenser(ABC):
    """Abstract base class for memory condensers.

    Condensers reduce memory content to fit within context windows.
    Ported from OpenHands condenser implementations.
    """

    @abstractmethod
    def condense(self, events: list[Event], max_tokens: int = 4000) -> list[Event]:
        """Condense a list of events to fit within token limits.

        Args:
            events: The events to condense.
            max_tokens: Maximum token budget.

        Returns:
            Condensed list of events.
        """
        ...

    @property
    @abstractmethod
    def condenser_type(self) -> CondenserType:
        """Get the condenser type."""
        ...


class NoOpCondenser(BaseCondenser):
    """No-op condenser that passes events through unchanged."""

    def condense(self, events: list[Event], max_tokens: int = 4000) -> list[Event]:
        return list(events)

    @property
    def condenser_type(self) -> CondenserType:
        return CondenserType.NOOP


class RecentCondenser(BaseCondenser):
    """Keep only the most recent N events."""

    def __init__(self, max_events: int = 20) -> None:
        self.max_events = max_events

    def condense(self, events: list[Event], max_tokens: int = 4000) -> list[Event]:
        return events[-self.max_events:]

    @property
    def condenser_type(self) -> CondenserType:
        return CondenserType.RECENT


class ObservationCondenser(BaseCondenser):
    """Keep only observations, discard intermediate actions."""

    def __init__(self, keep_recent_actions: int = 2) -> None:
        self.keep_recent_actions = keep_recent_actions

    def condense(self, events: list[Event], max_tokens: int = 4000) -> list[Event]:
        observations = [e for e in events if e.observation is not None]
        recent_actions = [
            e for e in events if e.action is not None
        ][-self.keep_recent_actions:]
        combined = sorted(observations + recent_actions, key=lambda e: e.timestamp)
        return combined

    @property
    def condenser_type(self) -> CondenserType:
        return CondenserType.OBSERVATION


class LLMCondenser(BaseCondenser):
    """LLM-based summarization condenser."""

    def __init__(self, llm_provider: Optional[Any] = None) -> None:
        self._llm_provider = llm_provider

    async def condense_async(self, events: list[Event], max_tokens: int = 4000) -> list[Event]:
        """Async version of condense that uses LLM for summarization."""
        if not self._llm_provider or not events:
            return events

        event_texts = []
        for event in events:
            if event.observation:
                event_texts.append(f"[OBS] {event.observation.content[:200]}")
            elif event.action:
                thought = event.action.thought or ""
                event_texts.append(f"[ACT] {event.action.action_type.value}: {thought[:200]}")

        summary_text = "\n".join(event_texts)
        if len(summary_text) <= max_tokens * 4:
            return events

        try:
            response = await self._llm_provider.chat(
                messages=[
                    {"role": "system", "content": "Summarize the following agent events concisely, preserving key information."},
                    {"role": "user", "content": summary_text},
                ],
                max_tokens=max_tokens,
            )
            summary_event = Event(
                source="condenser",
                observation=Observation(
                    observation_type=ObservationType.MEMORY_CONDENSED,
                    agent_id="condenser",
                    action_id="condensed",
                    content=f"[Condensed Summary]\n{response.content}",
                ),
                data={"condensed": True, "original_count": len(events)},
            )
            return [summary_event]
        except Exception as e:
            logger.error("llm_condenser_error", error=str(e))
            return events[-10:]

    def condense(self, events: list[Event], max_tokens: int = 4000) -> list[Event]:
        """Synchronous fallback - just use recent events."""
        return events[-10:]

    @property
    def condenser_type(self) -> CondenserType:
        return CondenserType.LLM


class AmortizedCondenser(BaseCondenser):
    """Amortized forgetting - gradually reduce older event importance."""

    def __init__(self, decay_factor: float = 0.9, min_importance: float = 0.1) -> None:
        self.decay_factor = decay_factor
        self.min_importance = min_importance
        self._importance: dict[str, float] = {}

    def condense(self, events: list[Event], max_tokens: int = 4000) -> list[Event]:
        for event_id in list(self._importance.keys()):
            self._importance[event_id] *= self.decay_factor

        for event in events:
            if event.id not in self._importance:
                self._importance[event.id] = 1.0

        important_events = [
            e for e in events
            if self._importance.get(e.id, 0) >= self.min_importance
        ]

        self._importance = {
            k: v for k, v in self._importance.items()
            if v >= self.min_importance * 0.1
        }

        return important_events

    @property
    def condenser_type(self) -> CondenserType:
        return CondenserType.AMORTIZED


class BrowserOutputCondenser(BaseCondenser):
    """Specialized condenser for browser output - truncates long HTML."""

    def __init__(self, max_browser_output: int = 2000) -> None:
        self.max_browser_output = max_browser_output

    def condense(self, events: list[Event], max_tokens: int = 4000) -> list[Event]:
        condensed = []
        for event in events:
            if event.observation and "browser" in event.data.get("observation_type", "").lower():
                content = event.observation.content
                if len(content) > self.max_browser_output:
                    new_obs = event.observation.model_copy(update={
                        "content": content[:self.max_browser_output] + "\n[...truncated...]",
                    })
                    new_event = event.model_copy(update={"observation": new_obs})
                    condensed.append(new_event)
                else:
                    condensed.append(event)
            else:
                condensed.append(event)
        return condensed

    @property
    def condenser_type(self) -> CondenserType:
        return CondenserType.BROWSER_OUTPUT


class LLMLinguaCondenser(BaseCondenser):
    """LLMLingua-style token compression (simplified implementation)."""

    def __init__(self, compression_rate: float = 0.5) -> None:
        self.compression_rate = compression_rate

    def condense(self, events: list[Event], max_tokens: int = 4000) -> list[Event]:
        target_count = int(len(events) * self.compression_rate)
        if len(events) <= target_count:
            return events
        keep_start = target_count // 2
        keep_end = target_count - keep_start
        return events[:keep_start] + events[-keep_end:]

    @property
    def condenser_type(self) -> CondenserType:
        return CondenserType.LLMLINGUA


class EventMaskCondenser(BaseCondenser):
    """Mask irrelevant events based on type filtering."""

    def __init__(self, mask_types: Optional[list[str]] = None) -> None:
        self.mask_types = mask_types or ["agent_state_changed"]

    def condense(self, events: list[Event], max_tokens: int = 4000) -> list[Event]:
        return [
            e for e in events
            if e.event_type not in self.mask_types
            and e.data.get("observation_type", "") not in self.mask_types
        ]

    @property
    def condenser_type(self) -> CondenserType:
        return CondenserType.EVENT_MASK


# === Vector Store Integration (optional) ===

class VectorStoreBackend(ABC):
    """Abstract interface for vector store backends."""

    @abstractmethod
    async def upsert(self, id: str, embedding: list[float], metadata: dict[str, Any]) -> None:
        ...

    @abstractmethod
    async def search(self, embedding: list[float], limit: int = 10) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    async def delete(self, id: str) -> None:
        ...


class QdrantBackend(VectorStoreBackend):
    """Qdrant vector store backend."""

    def __init__(self, url: str = "http://localhost:6333", collection: str = "ai_multicolony",
                 api_key: Optional[str] = None, embedding_dimension: int = 1536) -> None:
        self._url = url
        self._collection = collection
        self._api_key = api_key
        self._embedding_dimension = embedding_dimension
        self._client: Optional[Any] = None

    def _get_client(self) -> Any:
        """Lazy-initialize the Qdrant client."""
        if self._client is None:
            try:
                from qdrant_client import QdrantClient
                kwargs: dict[str, Any] = {"url": self._url}
                if self._api_key:
                    kwargs["api_key"] = self._api_key
                self._client = QdrantClient(**kwargs)
            except ImportError:
                raise MemoryError("qdrant-client not installed. Install with: pip install qdrant-client")
        return self._client

    async def upsert(self, id: str, embedding: list[float], metadata: dict[str, Any]) -> None:
        try:
            client = self._get_client()
            from qdrant_client.models import PointStruct
            client.upsert(
                collection_name=self._collection,
                points=[PointStruct(id=id, vector=embedding, payload=metadata)],
            )
        except Exception as e:
            logger.warning("qdrant_upsert_error", error=str(e))

    async def search(self, embedding: list[float], limit: int = 10) -> list[dict[str, Any]]:
        try:
            client = self._get_client()
            results = client.search(
                collection_name=self._collection,
                query_vector=embedding,
                limit=limit,
            )
            return [{"id": str(r.id), "score": r.score, "payload": r.payload} for r in results]
        except Exception as e:
            logger.warning("qdrant_search_error", error=str(e))
            return []

    async def delete(self, id: str) -> None:
        try:
            client = self._get_client()
            client.delete(collection_name=self._collection, points_selector=[id])
        except Exception as e:
            logger.warning("qdrant_delete_error", error=str(e))


class ChromaBackend(VectorStoreBackend):
    """ChromaDB vector store backend."""

    def __init__(self, persist_directory: str = "./data/chroma", collection: str = "ai_multicolony") -> None:
        self._persist_directory = persist_directory
        self._collection_name = collection
        self._client: Optional[Any] = None
        self._collection: Optional[Any] = None

    def _get_collection(self) -> Any:
        """Lazy-initialize the ChromaDB client and collection."""
        if self._collection is None:
            try:
                import chromadb
                self._client = chromadb.PersistentClient(path=self._persist_directory)
                self._collection = self._client.get_or_create_collection(self._collection_name)
            except ImportError:
                raise MemoryError("chromadb not installed. Install with: pip install chromadb")
        return self._collection

    async def upsert(self, id: str, embedding: list[float], metadata: dict[str, Any]) -> None:
        try:
            collection = self._get_collection()
            collection.upsert(
                ids=[id],
                embeddings=[embedding],
                metadatas=[metadata],
            )
        except Exception as e:
            logger.warning("chroma_upsert_error", error=str(e))

    async def search(self, embedding: list[float], limit: int = 10) -> list[dict[str, Any]]:
        try:
            collection = self._get_collection()
            results = collection.query(query_embeddings=[embedding], n_results=limit)
            items = []
            for i in range(len(results["ids"][0])):
                items.append({
                    "id": results["ids"][0][i],
                    "score": results["distances"][0][i] if "distances" in results else 0,
                    "payload": results["metadatas"][0][i] if "metadatas" in results else {},
                })
            return items
        except Exception as e:
            logger.warning("chroma_search_error", error=str(e))
            return []

    async def delete(self, id: str) -> None:
        try:
            collection = self._get_collection()
            collection.delete(ids=[id])
        except Exception as e:
            logger.warning("chroma_delete_error", error=str(e))


# === Memory Manager ===

class MemoryManager:
    """Memory manager with Letta-style paging and OpenHands condensers.

    Features:
    - 8 condenser implementations for context management
    - Letta-style memory paging (load/unload pages)
    - Session-based memory isolation
    - Vector search integration (optional, Qdrant or ChromaDB)
    """

    def __init__(
        self,
        default_condenser: CondenserType = CondenserType.RECENT,
        max_pages: int = 100,
        page_size: int = 4000,
        llm_provider: Optional[Any] = None,
        vector_backend: Optional[VectorStoreBackend] = None,
    ) -> None:
        self._pages: dict[str, MemoryPage] = {}
        self._entries: dict[str, list[MemoryEntry]] = {}
        self._sessions: dict[str, MemorySession] = {}
        self._condensers: dict[CondenserType, BaseCondenser] = {
            CondenserType.NOOP: NoOpCondenser(),
            CondenserType.RECENT: RecentCondenser(),
            CondenserType.OBSERVATION: ObservationCondenser(),
            CondenserType.LLM: LLMCondenser(llm_provider),
            CondenserType.AMORTIZED: AmortizedCondenser(),
            CondenserType.BROWSER_OUTPUT: BrowserOutputCondenser(),
            CondenserType.LLMLINGUA: LLMLinguaCondenser(),
            CondenserType.EVENT_MASK: EventMaskCondenser(),
        }
        self._default_condenser = default_condenser
        self._max_pages = max_pages
        self._page_size = page_size
        self._llm_provider = llm_provider
        self._vector_backend = vector_backend

    def get_condenser(self, condenser_type: Optional[CondenserType] = None) -> BaseCondenser:
        """Get a condenser by type.

        Args:
            condenser_type: The condenser type to get. Defaults to the default.

        Returns:
            The condenser instance.
        """
        ct = condenser_type or self._default_condenser
        return self._condensers.get(ct, self._condensers[CondenserType.NOOP])

    # === Session Operations ===

    def create_session(self, agent_id: str, metadata: Optional[dict[str, Any]] = None) -> MemorySession:
        """Create a new memory session for an agent.

        Args:
            agent_id: The agent ID.
            metadata: Optional session metadata.

        Returns:
            The created session.
        """
        session = MemorySession(
            agent_id=agent_id,
            metadata=metadata or {},
        )
        self._sessions[session.id] = session
        return session

    def get_session(self, session_id: str) -> Optional[MemorySession]:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def get_active_sessions(self, agent_id: Optional[str] = None) -> list[MemorySession]:
        """Get all active sessions, optionally filtered by agent.

        Args:
            agent_id: Optional agent ID filter.

        Returns:
            List of active sessions.
        """
        sessions = [s for s in self._sessions.values() if s.state == SessionState.ACTIVE]
        if agent_id:
            sessions = [s for s in sessions if s.agent_id == agent_id]
        return sessions

    def close_session(self, session_id: str) -> None:
        """Close a session.

        Args:
            session_id: The session ID.
        """
        session = self._sessions.get(session_id)
        if session:
            session.close()

    # === Paging Operations (Letta-style) ===

    def create_page(
        self,
        agent_id: str,
        memory_type: MemoryType = MemoryType.WORKING,
        title: str = "",
        content: str = "",
        tags: Optional[list[str]] = None,
        session_id: Optional[str] = None,
    ) -> MemoryPage:
        """Create a new memory page.

        Args:
            agent_id: The agent this page belongs to.
            memory_type: Type of memory.
            title: Page title.
            content: Page content.
            tags: Optional tags.
            session_id: Optional session to associate with.

        Returns:
            The created page.
        """
        if len(self._pages) >= self._max_pages:
            self._evict_page()

        page_number = len([p for p in self._pages.values() if p.memory_type == memory_type])
        page = MemoryPage(
            page_number=page_number,
            memory_type=memory_type,
            title=title,
            content=content,
            token_count=len(content) // 4,
            tags=tags or [],
        )
        self._pages[page.id] = page

        if agent_id not in self._entries:
            self._entries[agent_id] = []
        self._entries[agent_id].append(MemoryEntry(
            memory_type=memory_type,
            agent_id=agent_id,
            content=content,
            page_id=page.id,
            tags=tags or [],
        ))

        # Associate with session if provided
        if session_id and session_id in self._sessions:
            self._sessions[session_id].add_page(page.id, page.token_count)

        return page

    def load_page(self, page_id: str) -> MemoryPage:
        """Load a memory page into active context.

        Args:
            page_id: The page ID to load.

        Returns:
            The loaded page.

        Raises:
            MemoryError: If the page is not found.
        """
        if page_id not in self._pages:
            raise MemoryError(f"Page not found: {page_id}")

        page = self._pages[page_id]
        page.is_active = True
        page.accessed_at = time.time()
        page.access_count += 1
        return page

    def unload_page(self, page_id: str) -> None:
        """Unload a memory page from active context.

        Args:
            page_id: The page ID to unload.
        """
        if page_id in self._pages:
            self._pages[page_id].is_active = False

    def get_active_pages(self, agent_id: Optional[str] = None) -> list[MemoryPage]:
        """Get all currently active (loaded) pages.

        Args:
            agent_id: Optional filter by agent.

        Returns:
            List of active pages.
        """
        pages = [p for p in self._pages.values() if p.is_active]
        if agent_id:
            entry_page_ids = {e.page_id for e in self._entries.get(agent_id, [])}
            pages = [p for p in pages if p.id in entry_page_ids]
        return pages

    def get_page(self, page_id: str) -> Optional[MemoryPage]:
        """Get a page by ID."""
        return self._pages.get(page_id)

    def update_page(self, page_id: str, content: Optional[str] = None, title: Optional[str] = None) -> MemoryPage:
        """Update a page's content.

        Args:
            page_id: The page ID.
            content: New content (if provided).
            title: New title (if provided).

        Returns:
            The updated page.
        """
        if page_id not in self._pages:
            raise MemoryError(f"Page not found: {page_id}")

        page = self._pages[page_id]
        if content is not None:
            page.content = content
            page.token_count = len(content) // 4
        if title is not None:
            page.title = title
        page.updated_at = time.time()
        return page

    def delete_page(self, page_id: str) -> None:
        """Delete a memory page.

        Args:
            page_id: The page ID to delete.
        """
        self._pages.pop(page_id, None)

    def _evict_page(self) -> None:
        """Evict the least recently used inactive page."""
        inactive_pages = [p for p in self._pages.values() if not p.is_active]
        if inactive_pages:
            lru_page = min(inactive_pages, key=lambda p: p.accessed_at)
            self.delete_page(lru_page.id)

    # === Entry Operations ===

    def add_entry(
        self,
        agent_id: str,
        content: str,
        memory_type: MemoryType = MemoryType.EPISODIC,
        importance: float = 0.5,
        tags: Optional[list[str]] = None,
        source: Optional[str] = None,
        embedding: Optional[list[float]] = None,
    ) -> MemoryEntry:
        """Add a memory entry.

        Args:
            agent_id: The agent ID.
            content: Memory content.
            memory_type: Type of memory.
            importance: Importance score (0-1).
            tags: Optional tags.
            source: Source of the memory.
            embedding: Optional embedding vector for search.

        Returns:
            The created entry.
        """
        entry = MemoryEntry(
            memory_type=memory_type,
            agent_id=agent_id,
            content=content,
            importance=importance,
            tags=tags or [],
            source=source,
            embedding=embedding,
        )
        if agent_id not in self._entries:
            self._entries[agent_id] = []
        self._entries[agent_id].append(entry)

        # Store in vector backend if available and embedding provided
        if self._vector_backend and embedding:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(
                        self._vector_backend.upsert(
                            id=entry.id,
                            embedding=embedding,
                            metadata={"agent_id": agent_id, "content": content[:500], "tags": tags or []},
                        )
                    )
                else:
                    loop.run_until_complete(
                        self._vector_backend.upsert(
                            id=entry.id,
                            embedding=embedding,
                            metadata={"agent_id": agent_id, "content": content[:500], "tags": tags or []},
                        )
                    )
            except Exception as e:
                logger.warning("vector_store_upsert_error", error=str(e))

        return entry

    def query(self, query: MemoryQuery) -> MemoryQueryResult:
        """Query memory entries.

        Args:
            query: The memory query.

        Returns:
            Query results.
        """
        start_time = time.time()
        entries = []

        for agent_id, agent_entries in self._entries.items():
            if query.agent_id and agent_id != query.agent_id:
                continue

            for entry in agent_entries:
                if query.memory_types and entry.memory_type not in query.memory_types:
                    continue
                if entry.importance < query.min_importance:
                    continue
                if query.tags and not any(t in entry.tags for t in query.tags):
                    continue
                if query.query.lower() in entry.content.lower():
                    entries.append(entry)

        entries.sort(key=lambda e: (e.importance, e.created_at), reverse=True)
        entries = entries[:query.limit]

        return MemoryQueryResult(
            entries=entries,
            total_count=len(entries),
            query=query,
            execution_time=time.time() - start_time,
        )

    async def vector_search(self, embedding: list[float], limit: int = 10, agent_id: Optional[str] = None) -> list[MemoryEntry]:
        """Search memory entries using vector similarity.

        Args:
            embedding: The query embedding vector.
            limit: Maximum results to return.
            agent_id: Optional agent filter.

        Returns:
            List of matching memory entries.
        """
        if not self._vector_backend:
            logger.warning("vector_search_no_backend")
            return []

        try:
            results = await self._vector_backend.search(embedding=embedding, limit=limit)
            entries = []
            for result in results:
                payload = result.get("payload", {})
                if agent_id and payload.get("agent_id") != agent_id:
                    continue
                entry = MemoryEntry(
                    agent_id=payload.get("agent_id", ""),
                    content=payload.get("content", ""),
                    tags=payload.get("tags", []),
                    relevance_score=result.get("score"),
                )
                entries.append(entry)
            return entries
        except Exception as e:
            logger.warning("vector_search_error", error=str(e))
            return []

    def get_entries(self, agent_id: str, memory_type: Optional[MemoryType] = None, limit: int = 50) -> list[MemoryEntry]:
        """Get entries for an agent.

        Args:
            agent_id: The agent ID.
            memory_type: Optional filter by type.
            limit: Maximum entries to return.

        Returns:
            List of memory entries.
        """
        entries = self._entries.get(agent_id, [])
        if memory_type:
            entries = [e for e in entries if e.memory_type == memory_type]
        return entries[-limit:]

    def clear_entries(self, agent_id: Optional[str] = None) -> int:
        """Clear memory entries.

        Args:
            agent_id: Optional agent ID. If None, clears all.

        Returns:
            Number of entries cleared.
        """
        if agent_id:
            count = len(self._entries.get(agent_id, []))
            self._entries.pop(agent_id, None)
            return count
        else:
            count = sum(len(v) for v in self._entries.values())
            self._entries.clear()
            return count

    # === Condensation ===

    def condense_events(
        self,
        events: list[Event],
        condenser_type: Optional[CondenserType] = None,
        max_tokens: int = 4000,
    ) -> list[Event]:
        """Condense a list of events using the specified condenser.

        Args:
            events: The events to condense.
            condenser_type: The condenser type to use.
            max_tokens: Maximum token budget.

        Returns:
            Condensed events.
        """
        condenser = self.get_condenser(condenser_type)
        return condenser.condense(events, max_tokens)

    def get_stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        total_entries = sum(len(v) for v in self._entries.values())
        active_pages = sum(1 for p in self._pages.values() if p.is_active)
        active_sessions = sum(1 for s in self._sessions.values() if s.state == SessionState.ACTIVE)
        return {
            "total_pages": len(self._pages),
            "active_pages": active_pages,
            "total_entries": total_entries,
            "total_sessions": len(self._sessions),
            "active_sessions": active_sessions,
            "agents_with_memory": len(self._entries),
            "max_pages": self._max_pages,
            "vector_backend": type(self._vector_backend).__name__ if self._vector_backend else None,
        }
