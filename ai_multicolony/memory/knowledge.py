"""KnowledgeBase – knowledge management with RAG-style retrieval,
fact confidence scores, temporal facts, fact supersession, and
category-based organization.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


# ── Models ───────────────────────────────────────────────────────

class Fact(BaseModel):
    """A single fact in the knowledge base with confidence and temporal validity."""
    model_config = ConfigDict(frozen=False)

    fact_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    content: str = ""
    category: str = "general"
    confidence: float = 1.0
    valid_from: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    valid_to: Optional[str] = None
    source: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    superseded_by: Optional[str] = None  # fact_id of newer fact
    supersedes: Optional[str] = None     # fact_id of older fact
    access_count: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Document(BaseModel):
    """An ingested document."""
    model_config = ConfigDict(frozen=False)

    doc_id: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    chunks: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Chunk(BaseModel):
    """A chunk of an ingested document."""
    model_config = ConfigDict(frozen=False)

    chunk_id: str
    doc_id: str
    content: str
    index: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ── Knowledge Base ───────────────────────────────────────────────

class KnowledgeBase:
    """Knowledge management with RAG-style retrieval.

    Features
    --------
    * Document ingestion with automatic chunking
    * Fact storage with confidence scores
    * Temporal facts (valid_from / valid_to)
    * Fact supersession (newer facts replace older ones)
    * Category-based organization
    * Search and query across documents and facts
    """

    def __init__(self, name: str = "default", chunk_size: int = 512, chunk_overlap: int = 64) -> None:
        self.name = name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Documents
        self._documents: Dict[str, Document] = {}
        self._chunks: Dict[str, Chunk] = {}

        # Facts
        self._facts: Dict[str, Fact] = {}
        self._facts_by_category: Dict[str, List[str]] = {}

    # ── Document ingestion ───────────────────────────────────────

    async def ingest(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[Dict] = None,
    ) -> str:
        """Ingest a document into the knowledge base.

        The document is automatically split into chunks for retrieval.
        """
        if doc_id in self._documents:
            # Re-ingest: remove old chunks
            old_doc = self._documents[doc_id]
            for chunk_id in old_doc.chunks:
                self._chunks.pop(chunk_id, None)

        chunk_ids = []
        start = 0
        index = 0

        while start < len(content):
            end = start + self.chunk_size
            chunk_content = content[start:end]
            chunk_id = f"{doc_id}-chunk-{index}"
            chunk = Chunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                content=chunk_content,
                index=index,
                metadata=metadata or {},
            )
            self._chunks[chunk_id] = chunk
            chunk_ids.append(chunk_id)
            index += 1
            start += self.chunk_size - self.chunk_overlap

        doc = Document(
            doc_id=doc_id,
            content=content,
            metadata=metadata or {},
            chunks=chunk_ids,
        )
        self._documents[doc_id] = doc

        logger.debug("Ingested document %s: %d chunks", doc_id, len(chunk_ids))
        return doc_id

    # ── Fact management ──────────────────────────────────────────

    async def add_fact(
        self,
        content: str,
        category: str = "general",
        confidence: float = 1.0,
        valid_from: Optional[str] = None,
        valid_to: Optional[str] = None,
        source: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
    ) -> Fact:
        """Add a fact to the knowledge base."""
        fact = Fact(
            content=content,
            category=category,
            confidence=confidence,
            valid_from=valid_from or datetime.now(timezone.utc).isoformat(),
            valid_to=valid_to,
            source=source or {},
            tags=tags or [],
        )

        self._facts[fact.fact_id] = fact
        if category not in self._facts_by_category:
            self._facts_by_category[category] = []
        self._facts_by_category[category].append(fact.fact_id)

        return fact

    async def supersede_fact(self, old_fact_id: str, new_content: str, confidence: float = 1.0) -> Optional[Fact]:
        """Create a new fact that supersedes an existing one.

        The old fact's ``superseded_by`` is set to the new fact's ID,
        and the new fact's ``supersedes`` points back.
        """
        old_fact = self._facts.get(old_fact_id)
        if not old_fact:
            return None

        new_fact = await self.add_fact(
            content=new_content,
            category=old_fact.category,
            confidence=confidence,
            source=old_fact.source,
            tags=old_fact.tags,
        )

        old_fact.superseded_by = new_fact.fact_id
        new_fact.supersedes = old_fact_id

        return new_fact

    async def get_fact(self, fact_id: str) -> Optional[Fact]:
        """Get a fact by ID."""
        fact = self._facts.get(fact_id)
        if fact:
            fact.access_count += 1
        return fact

    async def get_active_facts(self, category: Optional[str] = None) -> List[Fact]:
        """Get all non-superseded facts, optionally filtered by category."""
        facts = []
        if category:
            fact_ids = self._facts_by_category.get(category, [])
            for fid in fact_ids:
                fact = self._facts.get(fid)
                if fact and not fact.superseded_by:
                    facts.append(fact)
        else:
            for fact in self._facts.values():
                if not fact.superseded_by:
                    facts.append(fact)
        return facts

    async def get_facts_in_range(
        self,
        from_time: Optional[str] = None,
        to_time: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Fact]:
        """Get facts within a time range based on valid_from / valid_to."""
        results = []
        for fact in self._facts.values():
            if fact.superseded_by:
                continue
            if category and fact.category != category:
                continue
            if from_time and fact.valid_from < from_time:
                continue
            if to_time and fact.valid_to and fact.valid_to > to_time:
                continue
            if to_time and not fact.valid_to:
                # Still valid
                pass
            results.append(fact)
        return results

    # ── Query ────────────────────────────────────────────────────

    async def query(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Query the knowledge base for relevant chunks and facts."""
        q = query.lower()
        results: List[Dict[str, Any]] = []

        # Search chunks
        for chunk_id, chunk in self._chunks.items():
            if q in chunk.content.lower():
                results.append({
                    "type": "chunk",
                    "chunk_id": chunk_id,
                    "content": chunk.content[:300],
                    "doc_id": chunk.doc_id,
                    "relevance": 0.9,
                })

        # Search facts
        for fact in self._facts.values():
            if fact.superseded_by:
                continue
            if q in fact.content.lower():
                results.append({
                    "type": "fact",
                    "fact_id": fact.fact_id,
                    "content": fact.content,
                    "category": fact.category,
                    "confidence": fact.confidence,
                    "relevance": 0.85,
                })

        # Sort by relevance
        results.sort(key=lambda r: r.get("relevance", 0), reverse=True)
        return results[:limit]

    async def search_by_category(self, category: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search facts by category."""
        fact_ids = self._facts_by_category.get(category, [])
        results = []
        for fid in fact_ids:
            fact = self._facts.get(fid)
            if fact and not fact.superseded_by:
                results.append({
                    "fact_id": fact.fact_id,
                    "content": fact.content,
                    "confidence": fact.confidence,
                    "valid_from": fact.valid_from,
                    "tags": fact.tags,
                })
        return results[:limit]

    # ── Delete ───────────────────────────────────────────────────

    async def delete_document(self, doc_id: str) -> None:
        """Delete a document and its chunks."""
        doc = self._documents.pop(doc_id, None)
        if doc:
            for chunk_id in doc.chunks:
                self._chunks.pop(chunk_id, None)

    async def delete_fact(self, fact_id: str) -> bool:
        """Delete a fact."""
        fact = self._facts.pop(fact_id, None)
        if not fact:
            return False
        # Remove from category index
        cat_facts = self._facts_by_category.get(fact.category, [])
        self._facts_by_category[fact.category] = [f for f in cat_facts if f != fact_id]
        # Update supersession links
        if fact.supersedes:
            old = self._facts.get(fact.supersedes)
            if old:
                old.superseded_by = None
        return True

    # ── Counts ───────────────────────────────────────────────────

    def document_count(self) -> int:
        return len(self._documents)

    def chunk_count(self) -> int:
        return len(self._chunks)

    def fact_count(self, category: Optional[str] = None, active_only: bool = True) -> int:
        if category:
            fact_ids = self._facts_by_category.get(category, [])
            if active_only:
                return sum(1 for fid in fact_ids if not self._facts.get(fid, Fact()).superseded_by)
            return len(fact_ids)
        if active_only:
            return sum(1 for f in self._facts.values() if not f.superseded_by)
        return len(self._facts)

    def get_categories(self) -> List[str]:
        return list(self._facts_by_category.keys())

    def get_stats(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "documents": len(self._documents),
            "chunks": len(self._chunks),
            "facts": len(self._facts),
            "active_facts": sum(1 for f in self._facts.values() if not f.superseded_by),
            "categories": len(self._facts_by_category),
            "superseded_facts": sum(1 for f in self._facts.values() if f.superseded_by),
        }
