"""RAG retrieval for the Multi-Colony Ecosystem.

This module provides Retrieval-Augmented Generation (RAG) capabilities
using Qdrant vector database and embedding models for semantic search
and hybrid retrieval.

RAG Pipeline:
    1. Query embedding: Convert query to vector representation.
    2. Vector search: Find similar documents in Qdrant.
    3. Optional keyword search: BM25-style text matching.
    4. Hybrid fusion: Combine vector and keyword results.
    5. Context assembly: Build context window from top results.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class SearchMode(str, Enum):
    """Search modes for RAG retrieval."""

    VECTOR = "vector"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


class RetrievalResult(BaseModel):
    """A single retrieval result.

    Attributes:
        chunk_id: ID of the retrieved chunk.
        document_id: ID of the source document.
        content: The chunk content.
        score: Relevance score (0.0-1.0).
        search_mode: Which search mode produced this result.
        metadata: Chunk metadata.
    """

    chunk_id: str = ""
    document_id: str = ""
    content: str
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    search_mode: SearchMode = SearchMode.VECTOR
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalResponse(BaseModel):
    """Response from a RAG retrieval operation.

    Attributes:
        query: The original query.
        results: Ordered list of retrieval results.
        mode: Search mode used.
        total_found: Total number of results found.
        context_text: Assembled context from top results.
        context_tokens: Estimated token count of context.
        elapsed_ms: Retrieval time in milliseconds.
    """

    query: str
    results: list[RetrievalResult] = Field(default_factory=list)
    mode: SearchMode = SearchMode.VECTOR
    total_found: int = 0
    context_text: str = ""
    context_tokens: int = 0
    elapsed_ms: float = 0.0


class RAGConfig(BaseModel):
    """Configuration for RAG retrieval.

    Attributes:
        collection_name: Qdrant collection name.
        embedding_dim: Dimension of embedding vectors.
        default_mode: Default search mode.
        top_k: Default number of results to return.
        min_score: Minimum relevance score threshold.
        context_max_tokens: Maximum tokens for assembled context.
        hybrid_alpha: Weight for vector results in hybrid mode (0.0-1.0).
        reranking_enabled: Whether to apply reranking.
        qdrant_url: URL of the Qdrant server.
    """

    collection_name: str = "knowledge_base"
    embedding_dim: int = 1536
    default_mode: SearchMode = SearchMode.HYBRID
    top_k: int = 5
    min_score: float = 0.3
    context_max_tokens: int = 4000
    hybrid_alpha: float = 0.7
    reranking_enabled: bool = False
    qdrant_url: str | None = None


class RAGRetriever:
    """RAG retrieval with Qdrant vector database and hybrid search.

    This class provides retrieval capabilities for the RAG pipeline,
    supporting vector search, keyword search, and hybrid fusion.

    Note:
        Qdrant integration is stubbed. In production, this would use
        the qdrant-client library for vector storage and retrieval.

    Example::

        retriever = RAGRetriever(config=RAGConfig())
        response = await retriever.retrieve("What is quantum computing?")
        response = await retriever.hybrid_search("Python async patterns", top_k=10)
    """

    def __init__(self, config: RAGConfig | None = None) -> None:
        """Initialize the RAG retriever.

        Args:
            config: RAG configuration. Uses defaults if not provided.
        """
        self._config = config or RAGConfig()
        self._chunks: dict[str, dict[str, Any]] = {}  # chunk_id -> chunk data
        self._qdrant_client: Any = None  # Stub for qdrant_client
        self._log = logger.bind(component="rag_retriever")

    @property
    def chunk_count(self) -> int:
        """Number of indexed chunks."""
        return len(self._chunks)

    async def index_chunks(
        self,
        chunks: list[dict[str, Any]],
    ) -> int:
        """Index document chunks for retrieval.

        Args:
            chunks: List of chunk dictionaries with 'chunk_id', 'content',
                'document_id', and optional 'metadata' and 'embedding'.

        Returns:
            Number of chunks indexed.
        """
        indexed = 0
        for chunk in chunks:
            chunk_id = chunk.get("chunk_id", str(uuid.uuid4()))
            content = chunk.get("content", "")
            embedding = chunk.get("embedding", [])

            # Generate embedding if not provided
            if not embedding:
                embedding = await self._generate_embedding(content)

            self._chunks[chunk_id] = {
                "chunk_id": chunk_id,
                "document_id": chunk.get("document_id", ""),
                "content": content,
                "embedding": embedding,
                "metadata": chunk.get("metadata", {}),
            }
            indexed += 1

        self._log.info(
            "chunks_indexed",
            count=indexed,
            total=len(self._chunks),
        )

        return indexed

    async def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        min_score: float | None = None,
        mode: SearchMode | None = None,
    ) -> RetrievalResponse:
        """Retrieve relevant chunks for a query.

        Args:
            query: The search query.
            top_k: Number of results to return.
            min_score: Minimum relevance score.
            mode: Search mode.

        Returns:
            A retrieval response with results and assembled context.
        """
        import time

        start_time = time.monotonic()

        effective_top_k = top_k or self._config.top_k
        effective_min_score = min_score or self._config.min_score
        effective_mode = mode or self._config.default_mode

        results: list[RetrievalResult] = []

        if effective_mode == SearchMode.VECTOR:
            results = await self._vector_search(query, effective_top_k, effective_min_score)
        elif effective_mode == SearchMode.KEYWORD:
            results = await self._keyword_search(query, effective_top_k, effective_min_score)
        elif effective_mode == SearchMode.HYBRID:
            results = await self._hybrid_search(query, effective_top_k, effective_min_score)

        # Assemble context
        context_text = self._assemble_context(results)

        elapsed_ms = (time.monotonic() - start_time) * 1000

        response = RetrievalResponse(
            query=query,
            results=results,
            mode=effective_mode,
            total_found=len(results),
            context_text=context_text,
            context_tokens=len(context_text) // 4,
            elapsed_ms=elapsed_ms,
        )

        self._log.info(
            "rag_retrieval",
            query=query[:50],
            mode=effective_mode.value,
            results=len(results),
            elapsed_ms=round(elapsed_ms, 2),
        )

        return response

    async def hybrid_search(
        self,
        query: str,
        top_k: int | None = None,
        min_score: float | None = None,
    ) -> RetrievalResponse:
        """Perform a hybrid search combining vector and keyword results.

        Args:
            query: The search query.
            top_k: Number of results to return.
            min_score: Minimum relevance score.

        Returns:
            A retrieval response.
        """
        return await self.retrieve(
            query=query,
            top_k=top_k,
            min_score=min_score,
            mode=SearchMode.HYBRID,
        )

    async def _vector_search(
        self,
        query: str,
        top_k: int,
        min_score: float,
    ) -> list[RetrievalResult]:
        """Perform vector similarity search.

        Args:
            query: Search query.
            top_k: Number of results.
            min_score: Minimum score.

        Returns:
            A list of retrieval results.
        """
        query_embedding = await self._generate_embedding(query)

        results: list[RetrievalResult] = []
        for chunk_data in self._chunks.values():
            chunk_embedding = chunk_data.get("embedding", [])
            if chunk_embedding:
                score = self._cosine_similarity(query_embedding, chunk_embedding)
            else:
                score = self._text_similarity(query, chunk_data.get("content", ""))

            if score >= min_score:
                results.append(RetrievalResult(
                    chunk_id=chunk_data["chunk_id"],
                    document_id=chunk_data.get("document_id", ""),
                    content=chunk_data.get("content", ""),
                    score=score,
                    search_mode=SearchMode.VECTOR,
                    metadata=chunk_data.get("metadata", {}),
                ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    async def _keyword_search(
        self,
        query: str,
        top_k: int,
        min_score: float,
    ) -> list[RetrievalResult]:
        """Perform keyword-based search (BM25-style).

        Args:
            query: Search query.
            top_k: Number of results.
            min_score: Minimum score.

        Returns:
            A list of retrieval results.
        """
        query_terms = set(query.lower().split())

        results: list[RetrievalResult] = []
        for chunk_data in self._chunks.values():
            content = chunk_data.get("content", "")
            content_terms = set(content.lower().split())

            # Simple term overlap score
            if not query_terms:
                score = 0.0
            else:
                overlap = query_terms & content_terms
                score = len(overlap) / len(query_terms)

            if score >= min_score:
                results.append(RetrievalResult(
                    chunk_id=chunk_data["chunk_id"],
                    document_id=chunk_data.get("document_id", ""),
                    content=content,
                    score=score,
                    search_mode=SearchMode.KEYWORD,
                    metadata=chunk_data.get("metadata", {}),
                ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    async def _hybrid_search(
        self,
        query: str,
        top_k: int,
        min_score: float,
    ) -> list[RetrievalResult]:
        """Perform hybrid search combining vector and keyword results.

        Uses Reciprocal Rank Fusion (RRF) to combine results from
        both search modes.

        Args:
            query: Search query.
            top_k: Number of results.
            min_score: Minimum score.

        Returns:
            A list of retrieval results.
        """
        alpha = self._config.hybrid_alpha

        # Get results from both modes
        vector_results = await self._vector_search(query, top_k * 2, 0.0)
        keyword_results = await self._keyword_search(query, top_k * 2, 0.0)

        # Build score maps
        vector_scores: dict[str, float] = {
            r.chunk_id: r.score for r in vector_results
        }
        keyword_scores: dict[str, float] = {
            r.chunk_id: r.score for r in keyword_results
        }

        # Combine using weighted fusion
        all_chunk_ids = set(vector_scores.keys()) | set(keyword_scores.keys())
        fused_results: list[RetrievalResult] = []

        for chunk_id in all_chunk_ids:
            v_score = vector_scores.get(chunk_id, 0.0)
            k_score = keyword_scores.get(chunk_id, 0.0)

            # Weighted combination
            fused_score = alpha * v_score + (1 - alpha) * k_score

            if fused_score >= min_score:
                # Get content from whichever result has it
                content = ""
                metadata: dict[str, Any] = {}
                document_id = ""

                for r in vector_results:
                    if r.chunk_id == chunk_id:
                        content = r.content
                        metadata = r.metadata
                        document_id = r.document_id
                        break
                if not content:
                    for r in keyword_results:
                        if r.chunk_id == chunk_id:
                            content = r.content
                            metadata = r.metadata
                            document_id = r.document_id
                            break

                fused_results.append(RetrievalResult(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    content=content,
                    score=fused_score,
                    search_mode=SearchMode.HYBRID,
                    metadata=metadata,
                ))

        fused_results.sort(key=lambda r: r.score, reverse=True)
        return fused_results[:top_k]

    def _assemble_context(
        self,
        results: list[RetrievalResult],
    ) -> str:
        """Assemble context text from retrieval results.

        Args:
            results: Retrieval results to assemble.

        Returns:
            Assembled context string within token budget.
        """
        max_chars = self._config.context_max_tokens * 4  # Rough char estimate
        parts: list[str] = []
        current_length = 0

        for result in results:
            entry = f"[Source: {result.document_id}]\n{result.content}\n"
            if current_length + len(entry) > max_chars:
                break
            parts.append(entry)
            current_length += len(entry)

        return "\n---\n".join(parts)

    async def _generate_embedding(self, text: str) -> list[float]:
        """Generate an embedding vector for text.

        Stub: In production, would use an embedding model.

        Args:
            text: Text to embed.

        Returns:
            A placeholder embedding vector.
        """
        return [0.0] * self._config.embedding_dim

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors.

        Args:
            a: First vector.
            b: Second vector.

        Returns:
            Cosine similarity score.
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
            content: Content to compare.

        Returns:
            Similarity score (0.0-1.0).
        """
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())

        if not query_words:
            return 0.0

        overlap = query_words & content_words
        return len(overlap) / len(query_words)

    def get_stats(self) -> dict[str, Any]:
        """Get retriever statistics.

        Returns:
            A dictionary of retriever statistics.
        """
        return {
            "chunk_count": self.chunk_count,
            "collection_name": self._config.collection_name,
            "embedding_dim": self._config.embedding_dim,
            "default_mode": self._config.default_mode.value,
            "qdrant_connected": self._qdrant_client is not None,
        }
