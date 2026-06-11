"""VectorStore – ChromaDB-compatible vector store with collection
management, embedding storage/search, metadata filtering, batch
operations, and health check.

This is a fully self-contained in-memory implementation.  Swap in
a real ChromaDB / Qdrant / Pinecone backend by replacing the
internals while keeping the same interface.
"""

from __future__ import annotations

import hashlib
import logging
import math
import random
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


# ── Models ───────────────────────────────────────────────────────

class VectorDocument(BaseModel):
    """A document in the vector store."""
    model_config = ConfigDict(frozen=False)

    id: str
    document: str
    embedding: List[float] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class QueryResult(BaseModel):
    """Result from a vector query."""
    model_config = ConfigDict(frozen=False)

    ids: List[str] = Field(default_factory=list)
    documents: List[str] = Field(default_factory=list)
    distances: List[float] = Field(default_factory=list)
    metadatas: List[Dict[str, Any]] = Field(default_factory=list)
    embeddings: List[List[float]] = Field(default_factory=list)


class CollectionInfo(BaseModel):
    """Metadata about a collection."""
    model_config = ConfigDict(frozen=False)

    name: str
    count: int = 0
    embedding_dims: int = 1536
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ── Vector Store ─────────────────────────────────────────────────

class VectorStore:
    """In-memory vector store with ChromaDB-compatible interface.

    Features
    --------
    * Collection management (create, switch, list)
    * Embedding storage and similarity search (cosine distance)
    * Metadata filtering (exact match and range)
    * Batch add / delete / query
    * Health check
    """

    def __init__(
        self,
        collection_name: str = "default",
        embedding_dims: int = 1536,
    ) -> None:
        self.collection_name = collection_name
        self.embedding_dims = embedding_dims

        # Collections: name -> {documents, embeddings, metadata}
        self._collections: Dict[str, Dict[str, Any]] = {}
        self._active_collection: str = collection_name

        # Initialize default collection
        self._collections[collection_name] = {
            "documents": {},
            "embeddings": {},
            "metadata": {},
            "info": CollectionInfo(
                name=collection_name,
                embedding_dims=embedding_dims,
            ),
        }

    # ── Collection management ────────────────────────────────────

    def create_collection(self, name: str, embedding_dims: int = 1536) -> CollectionInfo:
        """Create a new collection."""
        if name in self._collections:
            raise ValueError(f"Collection already exists: {name}")

        info = CollectionInfo(name=name, embedding_dims=embedding_dims)
        self._collections[name] = {
            "documents": {},
            "embeddings": {},
            "metadata": {},
            "info": info,
        }
        logger.info("Created collection: %s", name)
        return info

    def switch_collection(self, name: str) -> None:
        """Switch the active collection."""
        if name not in self._collections:
            raise ValueError(f"Collection not found: {name}")
        self.collection_name = name
        self._active_collection = name

    def list_collections(self) -> List[CollectionInfo]:
        """List all collections."""
        return [col["info"] for col in self._collections.values()]

    def delete_collection(self, name: str) -> bool:
        """Delete a collection."""
        if name not in self._collections:
            return False
        del self._collections[name]
        if self._active_collection == name:
            self._active_collection = "default"
        return True

    def _get_collection(self, name: Optional[str] = None) -> Dict[str, Any]:
        col_name = name or self._active_collection
        if col_name not in self._collections:
            raise ValueError(f"Collection not found: {col_name}")
        return self._collections[col_name]

    # ── Add documents ────────────────────────────────────────────

    async def add(
        self,
        ids: List[str],
        documents: List[str],
        embeddings: Optional[List[List[float]]] = None,
        metadatas: Optional[List[Dict]] = None,
        collection: Optional[str] = None,
    ) -> List[str]:
        """Add documents to the store.

        If ``embeddings`` are not provided, deterministic fake embeddings
        are generated from the document text for compatibility.
        """
        col = self._get_collection(collection)

        for i, doc_id in enumerate(ids):
            doc = documents[i] if i < len(documents) else ""
            emb = embeddings[i] if embeddings and i < len(embeddings) else self._fake_embedding(doc)
            meta = metadatas[i] if metadatas and i < len(metadatas) else {}

            col["documents"][doc_id] = VectorDocument(
                id=doc_id,
                document=doc,
                embedding=emb,
                metadata=meta,
            )
            col["embeddings"][doc_id] = emb
            col["metadata"][doc_id] = meta

        # Update count
        col["info"].count = len(col["documents"])
        return ids

    async def add_single(
        self,
        document: str,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict] = None,
        doc_id: Optional[str] = None,
        collection: Optional[str] = None,
    ) -> str:
        """Add a single document."""
        doc_id = doc_id or uuid.uuid4().hex[:12]
        await self.add(
            ids=[doc_id],
            documents=[document],
            embeddings=[embedding] if embedding else None,
            metadatas=[metadata] if metadata else None,
            collection=collection,
        )
        return doc_id

    # ── Query ────────────────────────────────────────────────────

    async def query(
        self,
        query_embeddings: Optional[List[List[float]]] = None,
        query_texts: Optional[List[str]] = None,
        n_results: int = 10,
        where: Optional[Dict] = None,
        collection: Optional[str] = None,
    ) -> QueryResult:
        """Query for similar documents using cosine distance.

        Provide either ``query_embeddings`` or ``query_texts``.
        Metadata filtering with ``where`` supports exact match and
        ``$gte``, ``$lte``, ``$gt``, ``$lt`` operators.
        """
        col = self._get_collection(collection)

        if not col["documents"]:
            return QueryResult()

        # Get query embedding
        if query_embeddings:
            q_emb = query_embeddings[0]
        elif query_texts:
            q_emb = self._fake_embedding(query_texts[0])
        else:
            # Return all
            ids = list(col["documents"].keys())[:n_results]
            return QueryResult(
                ids=ids,
                documents=[col["documents"][iid].document for iid in ids],
                distances=[0.0] * len(ids),
                metadatas=[col["metadata"].get(iid, {}) for iid in ids],
            )

        # Compute cosine distances
        scored: List[Tuple[str, float]] = []
        for doc_id, emb in col["embeddings"].items():
            if not emb:
                continue
            dist = self._cosine_distance(q_emb, emb)
            scored.append((doc_id, dist))

        # Sort by distance (lower = more similar)
        scored.sort(key=lambda x: x[1])

        # Apply metadata filter
        if where:
            scored = [(did, dist) for did, dist in scored if self._matches_filter(col["metadata"].get(did, {}), where)]

        # Take top n
        top = scored[:n_results]

        return QueryResult(
            ids=[did for did, _ in top],
            documents=[col["documents"][did].document for did, _ in top],
            distances=[round(dist, 6) for _, dist in top],
            metadatas=[col["metadata"].get(did, {}) for did, _ in top],
        )

    # ── Get by ID ────────────────────────────────────────────────

    async def get(
        self,
        ids: Optional[List[str]] = None,
        where: Optional[Dict] = None,
        collection: Optional[str] = None,
    ) -> QueryResult:
        """Get documents by ID or metadata filter."""
        col = self._get_collection(collection)

        if ids:
            results = []
            for doc_id in ids:
                doc = col["documents"].get(doc_id)
                if doc:
                    if where and not self._matches_filter(doc.metadata, where):
                        continue
                    results.append(doc)
            return QueryResult(
                ids=[r.id for r in results],
                documents=[r.document for r in results],
                metadatas=[r.metadata for r in results],
            )

        # No IDs: return all (with optional filter)
        results = []
        for doc in col["documents"].values():
            if where and not self._matches_filter(doc.metadata, where):
                continue
            results.append(doc)

        return QueryResult(
            ids=[r.id for r in results],
            documents=[r.document for r in results],
            metadatas=[r.metadata for r in results],
        )

    # ── Delete ───────────────────────────────────────────────────

    async def delete(self, ids: List[str], collection: Optional[str] = None) -> None:
        """Delete documents by ID."""
        col = self._get_collection(collection)
        for doc_id in ids:
            col["documents"].pop(doc_id, None)
            col["embeddings"].pop(doc_id, None)
            col["metadata"].pop(doc_id, None)
        col["info"].count = len(col["documents"])

    # ── Count / Reset / Health ───────────────────────────────────

    def count(self, collection: Optional[str] = None) -> int:
        """Count documents in a collection."""
        col = self._get_collection(collection)
        return len(col["documents"])

    async def reset(self, collection: Optional[str] = None) -> None:
        """Reset (clear) a collection."""
        col = self._get_collection(collection)
        col["documents"].clear()
        col["embeddings"].clear()
        col["metadata"].clear()
        col["info"].count = 0

    async def health_check(self) -> bool:
        """Check if the store is operational."""
        try:
            # Verify all collections are consistent
            for name, col in self._collections.items():
                doc_count = len(col["documents"])
                if col["info"].count != doc_count:
                    col["info"].count = doc_count
            return True
        except Exception:
            return False

    # ── Distance functions ───────────────────────────────────────

    @staticmethod
    def _cosine_distance(a: List[float], b: List[float]) -> float:
        """Compute cosine distance between two vectors (1 - similarity)."""
        if not a or not b:
            return 1.0

        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))

        if norm_a == 0 or norm_b == 0:
            return 1.0

        similarity = dot / (norm_a * norm_b)
        return 1.0 - similarity

    def _fake_embedding(self, text: str) -> List[float]:
        """Generate a deterministic fake embedding from text.

        Used when real embeddings are not provided.  NOT suitable
        for real semantic search.
        """
        # Create a seed from text hash
        h = hashlib.sha256(text.encode()).digest()
        seed = int.from_bytes(h[:4], "little")
        rng = random.Random(seed)

        # Generate random vector and normalize
        vec = [rng.gauss(0, 1) for _ in range(self.embedding_dims)]
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    # ── Metadata filter ──────────────────────────────────────────

    @staticmethod
    def _matches_filter(metadata: Dict[str, Any], where: Dict[str, Any]) -> bool:
        """Check if metadata matches a filter condition.

        Supports:
          - Exact match: ``{"key": "value"}``
          - Range: ``{"key": {"$gte": 5, "$lte": 10}}``
        """
        for key, condition in where.items():
            value = metadata.get(key)
            if value is None:
                return False

            if isinstance(condition, dict):
                # Range operators
                if "$gte" in condition and value < condition["$gte"]:
                    return False
                if "$lte" in condition and value > condition["$lte"]:
                    return False
                if "$gt" in condition and value <= condition["$gt"]:
                    return False
                if "$lt" in condition and value >= condition["$lt"]:
                    return False
            else:
                # Exact match
                if value != condition:
                    return False

        return True
