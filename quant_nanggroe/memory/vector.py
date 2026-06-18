"""Vector Memory — ChromaDB Integration for Semantic Search.

Provides ChromaDB-based vector storage for trading decisions,
strategies, research notes, market regime observations, and risk
events. Enables semantic search across trading history and
knowledge persistence across sessions.

Features
--------
* ChromaDB integration for vector storage
* Embedding generation for trading decisions, strategies, research
* Semantic search across trading history
* Pre-configured collections: strategies, research, decisions,
  market_regimes, risk_events
* Graceful fallback when ChromaDB is not installed

Dependencies
------------
Requires the ``chromadb`` package (optional). Install with:
``pip install chromadb``

Notes
-----
When ChromaDB is not installed, all operations return empty results
or no-op responses. This ensures the system works without the
optional dependency.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CollectionName(str, Enum):
    """Pre-configured vector store collections."""
    STRATEGIES = "strategies"
    RESEARCH = "research"
    DECISIONS = "decisions"
    MARKET_REGIMES = "market_regimes"
    RISK_EVENTS = "risk_events"


class EmbeddingProvider(str, Enum):
    """Embedding provider for vector generation."""
    DEFAULT = "default"  # ChromaDB default (all-MiniLM-L6-v2)
    OPENAI = "openai"
    LOCAL = "local"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class VectorDocument(BaseModel):
    """A document stored in the vector store."""
    doc_id: str = Field(..., description="Unique document ID")
    collection: str = Field(..., description="Collection name")
    content: str = Field(..., description="Document text content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")
    created_at: str = Field("")
    updated_at: str = Field("")


class SearchResult(BaseModel):
    """A search result from the vector store."""
    doc_id: str = Field(..., description="Document ID")
    collection: str = Field("", description="Collection name")
    content: str = Field("", description="Document content")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    distance: float = Field(0.0, description="Distance score (lower = more similar)")
    relevance_score: float = Field(0.0, description="Relevance score (0-1)")


class VectorStoreStats(BaseModel):
    """Vector store statistics."""
    total_documents: int = 0
    collections: Dict[str, int] = Field(default_factory=dict)
    embedding_provider: str = "default"
    last_updated: str = ""


# ---------------------------------------------------------------------------
# Vector Store (ChromaDB)
# ---------------------------------------------------------------------------

class VectorStore:
    """ChromaDB-backed vector store for trading knowledge.

    Provides semantic search across trading decisions, strategies,
    research notes, market regime observations, and risk events.

    When ChromaDB is not installed, all operations return empty
    results with appropriate warnings.

    Usage::

        store = VectorStore()
        await store.initialize()
        await store.add("strategies", "Moving average crossover with 50/200 EMA",
                        metadata={"type": "trend_following"})
        results = await store.search("strategies", "trend following strategy")
    """

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        embedding_provider: EmbeddingProvider = EmbeddingProvider.DEFAULT,
    ) -> None:
        self._persist_directory = persist_directory
        self._embedding_provider = embedding_provider
        self._client = None
        self._collections: Dict[str, Any] = {}
        self._initialized = False
        self._chromadb_available = False
        self._fallback_store: Dict[str, List[VectorDocument]] = {
            c.value: [] for c in CollectionName
        }

    async def initialize(self) -> bool:
        """Initialize the ChromaDB client and collections.

        Returns:
            True if initialization succeeded, False if using fallback.
        """
        if self._initialized:
            return True

        try:
            import chromadb  # type: ignore[import-untyped]

            # Create client
            if self._persist_directory:
                self._client = chromadb.PersistentClient(path=self._persist_directory)
            else:
                self._client = chromadb.Client()

            # Create collections
            for collection_name in CollectionName:
                try:
                    self._collections[collection_name.value] = self._client.get_or_create_collection(
                        name=collection_name.value,
                        metadata={"hnsw:space": "cosine"},
                    )
                except Exception as exc:
                    logger.warning("Failed to create collection %s: %s", collection_name.value, exc)

            self._chromadb_available = True
            self._initialized = True
            logger.info("VectorStore: ChromaDB initialized successfully")
            return True

        except ImportError:
            logger.warning(
                "chromadb not installed. Vector store will use in-memory fallback. "
                "Install with: pip install chromadb"
            )
            self._chromadb_available = False
            self._initialized = True
            return False
        except Exception as exc:
            logger.warning("ChromaDB initialization failed: %s. Using fallback.", exc)
            self._chromadb_available = False
            self._initialized = True
            return False

    async def add(
        self,
        collection: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None,
    ) -> VectorDocument:
        """Add a document to the vector store.

        Args:
            collection: Collection name (e.g., "strategies").
            content: Document text content.
            metadata: Optional metadata dict.
            doc_id: Optional document ID (auto-generated if None).

        Returns:
            VectorDocument with the stored document.
        """
        if not self._initialized:
            await self.initialize()

        doc_id = doc_id or str(uuid.uuid4())
        metadata = metadata or {}
        now = datetime.now(tz=timezone.utc).isoformat()

        document = VectorDocument(
            doc_id=doc_id,
            collection=collection,
            content=content,
            metadata=metadata,
            created_at=now,
            updated_at=now,
        )

        if self._chromadb_available and collection in self._collections:
            try:
                col = self._collections[collection]
                col.add(
                    ids=[doc_id],
                    documents=[content],
                    metadatas=[{**metadata, "created_at": now}],
                )
                return document
            except Exception as exc:
                logger.warning("ChromaDB add failed, using fallback: %s", exc)

        # Fallback: store in memory
        if collection not in self._fallback_store:
            self._fallback_store[collection] = []
        self._fallback_store[collection].append(document)
        return document

    async def search(
        self,
        collection: str,
        query: str,
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Search for similar documents in the vector store.

        Args:
            collection: Collection to search.
            query: Search query text.
            n_results: Maximum number of results.
            where: Optional metadata filter.

        Returns:
            List of SearchResult sorted by relevance.
        """
        if not self._initialized:
            await self.initialize()

        if self._chromadb_available and collection in self._collections:
            try:
                col = self._collections[collection]
                query_params: Dict[str, Any] = {
                    "query_texts": [query],
                    "n_results": min(n_results, col.count()) if col.count() > 0 else 0,
                }
                if where:
                    query_params["where"] = where

                if col.count() == 0:
                    return []

                results = col.query(**query_params)

                search_results = []
                ids = results.get("ids", [[]])[0]
                documents = results.get("documents", [[]])[0]
                distances = results.get("distances", [[]])[0]
                metadatas = results.get("metadatas", [[]])[0]

                for i, doc_id in enumerate(ids):
                    distance = distances[i] if i < len(distances) else 0.0
                    relevance = max(0.0, 1.0 - distance)
                    search_results.append(SearchResult(
                        doc_id=doc_id,
                        collection=collection,
                        content=documents[i] if i < len(documents) else "",
                        metadata=metadatas[i] if i < len(metadatas) else {},
                        distance=round(distance, 4),
                        relevance_score=round(relevance, 4),
                    ))

                return search_results

            except Exception as exc:
                logger.warning("ChromaDB search failed, using fallback: %s", exc)

        # Fallback: simple keyword search
        return self._fallback_search(collection, query, n_results)

    async def delete(
        self,
        collection: str,
        doc_id: str,
    ) -> bool:
        """Delete a document from the vector store.

        Args:
            collection: Collection name.
            doc_id: Document ID to delete.

        Returns:
            True if deleted successfully.
        """
        if not self._initialized:
            await self.initialize()

        if self._chromadb_available and collection in self._collections:
            try:
                self._collections[collection].delete(ids=[doc_id])
                return True
            except Exception as exc:
                logger.warning("ChromaDB delete failed: %s", exc)

        # Fallback
        if collection in self._fallback_store:
            self._fallback_store[collection] = [
                d for d in self._fallback_store[collection] if d.doc_id != doc_id
            ]
            return True

        return False

    async def get_stats(self) -> VectorStoreStats:
        """Get vector store statistics.

        Returns:
            VectorStoreStats with collection counts.
        """
        if not self._initialized:
            await self.initialize()

        collections = {}
        total = 0

        if self._chromadb_available:
            for name, col in self._collections.items():
                try:
                    count = col.count()
                    collections[name] = count
                    total += count
                except Exception:
                    collections[name] = 0
        else:
            for name, docs in self._fallback_store.items():
                count = len(docs)
                collections[name] = count
                total += count

        return VectorStoreStats(
            total_documents=total,
            collections=collections,
            embedding_provider=self._embedding_provider.value,
            last_updated=datetime.now(tz=timezone.utc).isoformat(),
        )

    # ----- Convenience methods -----

    async def add_strategy(
        self,
        content: str,
        strategy_type: str = "",
        symbols: Optional[List[str]] = None,
    ) -> VectorDocument:
        """Add a strategy document.

        Args:
            content: Strategy description.
            strategy_type: Type of strategy.
            symbols: Associated symbols.

        Returns:
            VectorDocument for the stored strategy.
        """
        return await self.add(
            CollectionName.STRATEGIES,
            content,
            metadata={"strategy_type": strategy_type, "symbols": json.dumps(symbols or [])},
        )

    async def add_research(
        self,
        content: str,
        topic: str = "",
        source: str = "",
    ) -> VectorDocument:
        """Add a research note.

        Args:
            content: Research content.
            topic: Research topic.
            source: Data source.

        Returns:
            VectorDocument for the stored research.
        """
        return await self.add(
            CollectionName.RESEARCH,
            content,
            metadata={"topic": topic, "source": source},
        )

    async def add_decision(
        self,
        content: str,
        symbol: str = "",
        direction: str = "",
        outcome: str = "",
    ) -> VectorDocument:
        """Add a trading decision record.

        Args:
            content: Decision description.
            symbol: Trading symbol.
            direction: BUY or SELL.
            outcome: Decision outcome.

        Returns:
            VectorDocument for the stored decision.
        """
        return await self.add(
            CollectionName.DECISIONS,
            content,
            metadata={"symbol": symbol, "direction": direction, "outcome": outcome},
        )

    async def add_market_regime(
        self,
        content: str,
        regime: str = "",
        symbol: str = "",
    ) -> VectorDocument:
        """Add a market regime observation.

        Args:
            content: Regime description.
            regime: Regime type.
            symbol: Associated symbol.

        Returns:
            VectorDocument for the stored regime.
        """
        return await self.add(
            CollectionName.MARKET_REGIMES,
            content,
            metadata={"regime": regime, "symbol": symbol},
        )

    async def add_risk_event(
        self,
        content: str,
        event_type: str = "",
        severity: str = "",
    ) -> VectorDocument:
        """Add a risk event record.

        Args:
            content: Event description.
            event_type: Risk event type.
            severity: Event severity.

        Returns:
            VectorDocument for the stored risk event.
        """
        return await self.add(
            CollectionName.RISK_EVENTS,
            content,
            metadata={"event_type": event_type, "severity": severity},
        )

    # ----- Fallback search -----

    def _fallback_search(
        self,
        collection: str,
        query: str,
        n_results: int,
    ) -> List[SearchResult]:
        """Simple keyword-based fallback search."""
        docs = self._fallback_store.get(collection, [])
        query_lower = query.lower()
        query_words = set(query_lower.split())

        scored = []
        for doc in docs:
            content_lower = doc.content.lower()
            content_words = set(content_lower.split())

            # Simple word overlap scoring
            overlap = len(query_words & content_words)
            total = len(query_words)
            score = overlap / total if total > 0 else 0.0

            if score > 0 or not query_words:
                scored.append(SearchResult(
                    doc_id=doc.doc_id,
                    collection=collection,
                    content=doc.content,
                    metadata=doc.metadata,
                    distance=round(1.0 - score, 4),
                    relevance_score=round(score, 4),
                ))

        # Sort by relevance
        scored.sort(key=lambda r: r.relevance_score, reverse=True)
        return scored[:n_results]


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

_default_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    """Get or create the default VectorStore instance."""
    global _default_store
    if _default_store is None:
        _default_store = VectorStore()
    return _default_store


__all__ = [
    "VectorStore",
    "CollectionName",
    "EmbeddingProvider",
    "VectorDocument",
    "SearchResult",
    "VectorStoreStats",
    "get_vector_store",
]
