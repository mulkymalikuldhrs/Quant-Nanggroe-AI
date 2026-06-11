"""L3: Semantic memory for the Multi-Colony Ecosystem.

This module implements semantic memory (Layer 3) using Qdrant vector
database and RAG (Retrieval-Augmented Generation) patterns.

Semantic memory stores facts, concepts, and knowledge as structured
entries with vector embeddings for similarity search.

Memory Hierarchy:
    L1: Working memory (immediate context)
    L2: Episodic memory (event sequences)
    L3: Semantic memory (this module - facts and knowledge)
    L4: Procedural memory (skills and procedures)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class FactType(str, Enum):
    """Types of facts stored in semantic memory."""

    ENTITY = "entity"
    RELATION = "relation"
    CONCEPT = "concept"
    RULE = "rule"
    PROCEDURE = "procedure"
    PREFERENCE = "preference"
    CONTEXT = "context"


class Fact(BaseModel):
    """A fact stored in semantic memory.

    Attributes:
        fact_id: Unique identifier for the fact.
        content: The factual content/statement.
        fact_type: Type of fact.
        source: Where the fact originated (episode_id, url, etc.).
        confidence: Confidence score (0.0-1.0).
        embedding: Vector embedding for similarity search.
        tags: Tags for categorization.
        metadata: Additional metadata.
        created_at: When the fact was created.
        updated_at: When the fact was last updated.
        access_count: Number of times the fact has been accessed.
    """

    fact_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    fact_type: FactType = FactType.CONCEPT
    source: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    embedding: list[float] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = 0


class SearchResult(BaseModel):
    """Result of a semantic search operation.

    Attributes:
        fact: The matching fact.
        score: Similarity score (0.0-1.0).
        query: The original search query.
    """

    fact: Fact
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    query: str = ""


class SemanticMemory:
    """L3 Semantic memory with Qdrant vector database integration.

    This class manages semantic memory for agents, providing methods
    to store facts, search by similarity, and integrate with Qdrant
    for persistent vector storage.

    Note:
        Qdrant integration is stubbed. In production, this would use
        the qdrant-client library for vector storage and retrieval.

    Example::

        memory = SemanticMemory(agent_id="agent-1")
        fact_id = await memory.store_facts(
            content="Python uses indentation for code blocks",
            fact_type=FactType.CONCEPT,
        )
        results = await memory.search_facts("Python code blocks", limit=5)
    """

    def __init__(
        self,
        agent_id: str = "",
        colony_id: str = "",
        collection_name: str = "semantic_memory",
        embedding_dim: int = 1536,
        qdrant_url: str | None = None,
    ) -> None:
        """Initialize semantic memory.

        Args:
            agent_id: ID of the agent this memory belongs to.
            colony_id: ID of the colony.
            collection_name: Qdrant collection name.
            embedding_dim: Dimension of embedding vectors.
            qdrant_url: URL of the Qdrant server.
        """
        self._agent_id = agent_id
        self._colony_id = colony_id
        self._collection_name = collection_name
        self._embedding_dim = embedding_dim
        self._qdrant_url = qdrant_url
        self._facts: dict[str, Fact] = {}
        self._qdrant_client: Any = None  # Stub for qdrant_client
        self._log = logger.bind(
            agent_id=agent_id,
            component="semantic_memory",
        )

    @property
    def fact_count(self) -> int:
        """Number of facts stored in memory."""
        return len(self._facts)

    async def store_facts(
        self,
        content: str,
        fact_type: FactType = FactType.CONCEPT,
        source: str = "",
        confidence: float = 1.0,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store a fact in semantic memory.

        Args:
            content: The factual content.
            fact_type: Type of fact.
            source: Source of the fact.
            confidence: Confidence score (0.0-1.0).
            tags: Tags for categorization.
            metadata: Additional metadata.

        Returns:
            The fact_id of the stored fact.
        """
        # Generate embedding (stub: in production, use embedding model)
        embedding = await self._generate_embedding(content)

        fact = Fact(
            content=content,
            fact_type=fact_type,
            source=source,
            confidence=confidence,
            embedding=embedding,
            tags=tags or [],
            metadata=metadata or {},
        )

        self._facts[fact.fact_id] = fact

        # Upsert to Qdrant (stub)
        await self._upsert_to_qdrant(fact)

        self._log.info(
            "fact_stored",
            fact_id=fact.fact_id,
            fact_type=fact_type.value,
            confidence=confidence,
        )

        return fact.fact_id

    async def store_facts_batch(
        self,
        facts: list[dict[str, Any]],
    ) -> list[str]:
        """Store multiple facts in batch.

        Args:
            facts: List of fact dictionaries with keys matching store_facts args.

        Returns:
            List of stored fact IDs.
        """
        fact_ids = []
        for fact_data in facts:
            fact_id = await self.store_facts(**fact_data)
            fact_ids.append(fact_id)
        return fact_ids

    async def search_facts(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 0.5,
        fact_type: FactType | None = None,
        tags: list[str] | None = None,
    ) -> list[SearchResult]:
        """Search facts by semantic similarity.

        Args:
            query: Search query text.
            limit: Maximum number of results.
            min_score: Minimum similarity score threshold.
            fact_type: Filter by fact type.
            tags: Filter by tags.

        Returns:
            A list of search results sorted by relevance.
        """
        # Generate query embedding
        query_embedding = await self._generate_embedding(query)

        # Search in local facts (stub: in production, use Qdrant search)
        results: list[SearchResult] = []
        for fact in self._facts.values():
            # Filter by type
            if fact_type is not None and fact.fact_type != fact_type:
                continue
            # Filter by tags
            if tags is not None and not all(t in fact.tags for t in tags):
                continue

            # Compute similarity (cosine similarity)
            if fact.embedding and query_embedding:
                score = self._cosine_similarity(query_embedding, fact.embedding)
            else:
                # Fallback to text matching
                score = self._text_similarity(query, fact.content)

            if score >= min_score:
                results.append(SearchResult(
                    fact=fact,
                    score=score,
                    query=query,
                ))
                fact.access_count += 1

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)

        self._log.info(
            "facts_searched",
            query=query,
            result_count=len(results[:limit]),
        )

        return results[:limit]

    async def get_fact(self, fact_id: str) -> Fact:
        """Get a specific fact by ID.

        Args:
            fact_id: ID of the fact.

        Returns:
            The fact.

        Raises:
            FactNotFoundError: If the fact is not found.
        """
        if fact_id not in self._facts:
            raise FactNotFoundError(f"Fact {fact_id} not found.")

        fact = self._facts[fact_id]
        fact.access_count += 1
        return fact

    async def update_fact(
        self,
        fact_id: str,
        content: str | None = None,
        confidence: float | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Fact:
        """Update an existing fact.

        Args:
            fact_id: ID of the fact to update.
            content: Updated content.
            confidence: Updated confidence score.
            tags: Updated tags.
            metadata: Updated metadata.

        Returns:
            The updated fact.

        Raises:
            FactNotFoundError: If the fact is not found.
        """
        if fact_id not in self._facts:
            raise FactNotFoundError(f"Fact {fact_id} not found.")

        fact = self._facts[fact_id]

        if content is not None:
            fact.content = content
            fact.embedding = await self._generate_embedding(content)
        if confidence is not None:
            fact.confidence = confidence
        if tags is not None:
            fact.tags = tags
        if metadata is not None:
            fact.metadata = metadata

        fact.updated_at = datetime.now(timezone.utc)
        await self._upsert_to_qdrant(fact)

        return fact

    async def delete_fact(self, fact_id: str) -> None:
        """Delete a fact from memory.

        Args:
            fact_id: ID of the fact to delete.

        Raises:
            FactNotFoundError: If the fact is not found.
        """
        if fact_id not in self._facts:
            raise FactNotFoundError(f"Fact {fact_id} not found.")

        del self._facts[fact_id]
        self._log.info("fact_deleted", fact_id=fact_id)

    def clear(self) -> None:
        """Clear all facts from memory."""
        self._facts.clear()
        self._log.info("semantic_memory_cleared")

    def get_stats(self) -> dict[str, Any]:
        """Get memory statistics.

        Returns:
            A dictionary of memory statistics.
        """
        type_counts: dict[str, int] = {}
        for fact in self._facts.values():
            type_counts[fact.fact_type.value] = type_counts.get(fact.fact_type.value, 0) + 1

        return {
            "agent_id": self._agent_id,
            "fact_count": self.fact_count,
            "type_counts": type_counts,
            "collection_name": self._collection_name,
            "embedding_dim": self._embedding_dim,
            "qdrant_connected": self._qdrant_client is not None,
        }

    async def _generate_embedding(self, text: str) -> list[float]:
        """Generate an embedding vector for text.

        Stub: In production, this would call an embedding model
        (e.g., OpenAI text-embedding-3-small, sentence-transformers).

        Args:
            text: Text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """
        # Placeholder: return a zero vector of the expected dimension
        return [0.0] * self._embedding_dim

    async def _upsert_to_qdrant(self, fact: Fact) -> None:
        """Upsert a fact to Qdrant vector database.

        Stub: In production, this would use qdrant_client to upsert
        the fact with its embedding vector.

        Args:
            fact: The fact to upsert.
        """
        if self._qdrant_client is None:
            return
        # Stub: would call self._qdrant_client.upsert(...)
        pass

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors.

        Args:
            a: First vector.
            b: Second vector.

        Returns:
            Cosine similarity score (-1.0 to 1.0).
        """
        if len(a) != len(b) or len(a) == 0:
            return 0.0

        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (norm_a * norm_b)

    @staticmethod
    def _text_similarity(query: str, content: str) -> float:
        """Simple text similarity based on word overlap.

        Args:
            query: Query text.
            content: Content to compare against.

        Returns:
            Similarity score (0.0-1.0).
        """
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())

        if not query_words:
            return 0.0

        overlap = query_words & content_words
        return len(overlap) / len(query_words)


class FactNotFoundError(Exception):
    """Raised when a fact is not found in semantic memory."""
