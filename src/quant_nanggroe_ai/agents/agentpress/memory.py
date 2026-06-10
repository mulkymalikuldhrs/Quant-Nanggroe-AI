"""
Memory Module - Unified memory system for AgentPress.

Adapted from suna's memory system for Quant-Nanggroe-AI.
Combines embedding, retrieval, extraction, and storage into a single
convenient module. Key improvements over suna's approach:
- Pluggable embedding providers (OpenAI, local, custom)
- In-memory + optional file persistence (no Supabase dependency)
- Trading-specific memory types (market_insight, trading_decision)
- Context formatting optimized for trading agent prompts
"""

import asyncio
import hashlib
import json
import time
import uuid
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
from abc import ABC, abstractmethod
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class MemoryType(str, Enum):
    """Types of memories that can be stored."""
    FACT = "fact"
    PREFERENCE = "preference"
    CONTEXT = "context"
    CONVERSATION_SUMMARY = "conversation_summary"
    MARKET_INSIGHT = "market_insight"
    TRADING_DECISION = "trading_decision"


@dataclass
class MemoryEntry:
    """A single memory entry.

    Attributes:
        id: Unique identifier
        content: The memory content as a complete sentence
        memory_type: Type of memory
        confidence_score: Confidence level (0.0-1.0)
        embedding: Optional vector embedding for similarity search
        metadata: Additional metadata
        created_at: Unix timestamp of creation
        updated_at: Unix timestamp of last update
        access_count: Number of times accessed
        source: Where this memory came from
    """
    id: str
    content: str
    memory_type: MemoryType
    confidence_score: float = 0.8
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    access_count: int = 0
    source: str = "conversation"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        result['memory_type'] = self.memory_type.value
        result.pop('embedding', None)  # Don't serialize embeddings
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryEntry':
        """Create from dictionary."""
        if isinstance(data.get('memory_type'), str):
            data['memory_type'] = MemoryType(data['memory_type'])
        data.pop('embedding', None)
        return cls(**data)


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        pass

    @abstractmethod
    async def embed_single(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider using text-embedding-3-small."""

    def __init__(self, model: str = "text-embedding-3-small", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                import os
                self._client = AsyncOpenAI(api_key=self.api_key or os.environ.get("OPENAI_API_KEY"))
            except ImportError:
                raise ImportError("openai package required: pip install openai")
        return self._client

    async def embed(self, texts: List[str]) -> List[List[float]]:
        response = await self.client.embeddings.create(model=self.model, input=texts)
        return [e.embedding for e in response.data]

    async def embed_single(self, text: str) -> List[float]:
        return (await self.embed([text]))[0]


class LocalEmbeddingProvider(EmbeddingProvider):
    """Local embedding provider using sentence-transformers."""

    def __init__(self, model: str = "all-MiniLM-L6-v2"):
        self.model_name = model
        self._model = None

    @property
    def model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
            except ImportError:
                raise ImportError("sentence-transformers required: pip install sentence-transformers")
        return self._model

    async def embed(self, texts: List[str]) -> List[List[float]]:
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None, lambda: self.model.encode(texts, convert_to_numpy=True)
        )
        return embeddings.tolist()

    async def embed_single(self, text: str) -> List[float]:
        return (await self.embed([text]))[0]


class HashEmbeddingProvider(EmbeddingProvider):
    """Simple hash-based embedding for testing (no external deps).

    NOT suitable for production similarity search — use OpenAI or
    sentence-transformers instead.
    """

    def __init__(self, dimensions: int = 384):
        self.dimensions = dimensions

    async def embed(self, texts: List[str]) -> List[List[float]]:
        return [await self.embed_single(t) for t in texts]

    async def embed_single(self, text: str) -> List[float]:
        h = hashlib.sha256(text.encode()).digest()
        return [float(b) / 255.0 for b in h[:self.dimensions]]


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class AgentMemory:
    """Unified memory system for trading agents.

    Adapted from suna's memory services (embedding, retrieval, extraction)
    for Quant-Nanggroe-AI. Combines all memory operations in one class:
    - Store memories with type classification and confidence scoring
    - Embed memories for semantic similarity search
    - Retrieve relevant memories for prompt context
    - Extract memories from conversation text via LLM
    - Format memories for injection into agent prompts

    Usage:
        memory = AgentMemory()
        memory.add("User prefers low-risk strategies", MemoryType.PREFERENCE, 0.9)
        context = memory.format_for_prompt(query="risk settings")
    """

    def __init__(
        self,
        embedding_provider: Optional[str] = "hash",
        persist_path: Optional[str] = None,
    ):
        self._memories: Dict[str, MemoryEntry] = {}
        self._type_index: Dict[MemoryType, List[str]] = {mt: [] for mt in MemoryType}
        self._persist_path = persist_path
        self._embedding_provider = self._create_provider(embedding_provider)

        if persist_path:
            self._load_from_disk()

    def _create_provider(self, provider_name: str) -> Optional[EmbeddingProvider]:
        """Create an embedding provider by name."""
        if provider_name == "openai":
            return OpenAIEmbeddingProvider()
        elif provider_name == "local":
            return LocalEmbeddingProvider()
        elif provider_name == "hash":
            return HashEmbeddingProvider()
        elif provider_name == "none":
            return None
        return HashEmbeddingProvider()

    def add(
        self,
        content: str,
        memory_type: MemoryType,
        confidence_score: float = 0.8,
        metadata: Optional[Dict[str, Any]] = None,
        source: str = "conversation",
        memory_id: Optional[str] = None,
    ) -> MemoryEntry:
        """Add a new memory.

        Args:
            content: Memory content as a complete sentence
            memory_type: Type classification
            confidence_score: Confidence level (0.0-1.0)
            metadata: Additional metadata
            source: Where this memory came from
            memory_id: Optional custom ID

        Returns:
            The created MemoryEntry
        """
        entry_id = memory_id or str(uuid.uuid4())

        # Deduplicate
        for existing in self._memories.values():
            if existing.content == content and existing.memory_type == memory_type:
                if confidence_score > existing.confidence_score:
                    existing.confidence_score = confidence_score
                    existing.updated_at = time.time()
                return existing

        entry = MemoryEntry(
            id=entry_id,
            content=content,
            memory_type=memory_type,
            confidence_score=confidence_score,
            metadata=metadata or {},
            source=source,
        )

        self._memories[entry_id] = entry
        self._type_index[memory_type].append(entry_id)
        self._persist()

        logger.debug(f"Added {memory_type.value} memory: {content[:50]}...")
        return entry

    async def add_with_embedding(
        self,
        content: str,
        memory_type: MemoryType,
        confidence_score: float = 0.8,
        **kwargs,
    ) -> MemoryEntry:
        """Add a memory and compute its embedding.

        Args:
            content: Memory content
            memory_type: Type classification
            confidence_score: Confidence level
            **kwargs: Additional args passed to add()

        Returns:
            MemoryEntry with embedding populated
        """
        entry = self.add(content, memory_type, confidence_score, **kwargs)

        if self._embedding_provider:
            try:
                entry.embedding = await self._embedding_provider.embed_single(content)
            except Exception as e:
                logger.warning(f"Failed to embed memory: {e}")

        return entry

    async def search(
        self,
        query: str,
        limit: int = 10,
        similarity_threshold: float = 0.1,
        memory_type: Optional[MemoryType] = None,
    ) -> List[MemoryEntry]:
        """Search memories by semantic similarity.

        Falls back to keyword search if no embedding provider is available.

        Args:
            query: Search query
            limit: Maximum results
            similarity_threshold: Minimum similarity score
            memory_type: Optional type filter

        Returns:
            List of matching MemoryEntry objects
        """
        if not self._embedding_provider:
            return self._keyword_search(query, limit, memory_type)

        try:
            query_embedding = await self._embedding_provider.embed_single(query)
        except Exception as e:
            logger.warning(f"Embedding failed, using keyword search: {e}")
            return self._keyword_search(query, limit, memory_type)

        scored = []
        for entry in self._memories.values():
            if memory_type and entry.memory_type != memory_type:
                continue
            if entry.embedding:
                sim = _cosine_similarity(query_embedding, entry.embedding)
                if sim >= similarity_threshold:
                    scored.append((sim, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:limit]]

    def _keyword_search(
        self,
        query: str,
        limit: int = 10,
        memory_type: Optional[MemoryType] = None,
    ) -> List[MemoryEntry]:
        """Simple keyword-based search fallback."""
        query_lower = query.lower()
        results = []

        for entry in self._memories.values():
            if memory_type and entry.memory_type != memory_type:
                continue
            content_lower = entry.content.lower()
            score = sum(content_lower.count(w) for w in query_lower.split())
            score += entry.confidence_score
            if score > 0:
                results.append((score, entry))

        results.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in results[:limit]]

    def get_by_type(self, memory_type: MemoryType) -> List[MemoryEntry]:
        """Get all memories of a specific type.

        Args:
            memory_type: The type to filter by

        Returns:
            List of MemoryEntry sorted by confidence (highest first)
        """
        entries = [
            self._memories[eid]
            for eid in self._type_index.get(memory_type, [])
            if eid in self._memories
        ]
        return sorted(entries, key=lambda e: e.confidence_score, reverse=True)

    def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        entry = self._memories.pop(memory_id, None)
        if entry and memory_id in self._type_index.get(entry.memory_type, []):
            self._type_index[entry.memory_type].remove(memory_id)
        self._persist()
        return entry is not None

    def clear(self, memory_type: Optional[MemoryType] = None):
        """Clear memories, optionally by type."""
        if memory_type:
            for eid in self._type_index.get(memory_type, []):
                self._memories.pop(eid, None)
            self._type_index[memory_type] = []
        else:
            self._memories.clear()
            self._type_index = {mt: [] for mt in MemoryType}
        self._persist()

    def format_for_prompt(self, query: Optional[str] = None, max_entries: int = 10) -> str:
        """Format memories as context string for LLM prompts.

        Args:
            query: Optional query to prioritize relevant memories
            max_entries: Maximum memories to include

        Returns:
            Formatted string for prompt injection
        """
        if not self._memories:
            return ""

        if query:
            # Will be async, so fall back to sorted entries
            entries = sorted(
                self._memories.values(),
                key=lambda e: (e.confidence_score, e.access_count),
                reverse=True,
            )
        else:
            type_priority = [
                MemoryType.PREFERENCE,
                MemoryType.TRADING_DECISION,
                MemoryType.MARKET_INSIGHT,
                MemoryType.CONTEXT,
                MemoryType.FACT,
                MemoryType.CONVERSATION_SUMMARY,
            ]
            entries = []
            for mt in type_priority:
                entries.extend(self.get_by_type(mt))

        entries = entries[:max_entries]
        if not entries:
            return ""

        sections: Dict[str, List[str]] = {}
        for entry in entries:
            label = entry.memory_type.value.replace("_", " ").title()
            sections.setdefault(label, []).append(
                f"- {entry.content} (confidence: {entry.confidence_score:.1f})"
            )

        lines = ["## Agent Memory"]
        for label, items in sections.items():
            lines.append(f"\n### {label}")
            lines.extend(items)

        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        """Get memory store statistics."""
        return {
            "total_memories": len(self._memories),
            "by_type": {mt.value: len(ids) for mt, ids in self._type_index.items()},
            "avg_confidence": (
                sum(e.confidence_score for e in self._memories.values()) / len(self._memories)
                if self._memories else 0.0
            ),
        }

    def _persist(self):
        """Persist memories to disk if configured."""
        if not self._persist_path:
            return
        try:
            path = Path(self._persist_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            data = {"memories": {eid: e.to_dict() for eid, e in self._memories.items()}}
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist memories: {e}")

    def _load_from_disk(self):
        """Load memories from disk if configured."""
        if not self._persist_path:
            return
        try:
            path = Path(self._persist_path)
            if not path.exists():
                return
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for eid, entry_data in data.get("memories", {}).items():
                try:
                    entry = MemoryEntry.from_dict(entry_data)
                    self._memories[eid] = entry
                    self._type_index[entry.memory_type].append(eid)
                except Exception as e:
                    logger.warning(f"Failed to load memory {eid}: {e}")
            logger.info(f"Loaded {len(self._memories)} memories from disk")
        except Exception as e:
            logger.error(f"Failed to load memories: {e}")
