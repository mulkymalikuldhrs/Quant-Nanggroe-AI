"""Memory API — real vector storage, knowledge base, and graph operations.

Replaces the stub with full memory subsystem integration:

- /memory/search    → VectorStore.search() + KnowledgeBase.search()
- /memory/store     → VectorStore.add() / KnowledgeBase.add()
- /memory/list      → list entries with stats
- /memory/{id}      → get specific entry
- /memory/delete/{id} → delete entry
- /memory/graph     → KnowledgeGraph stats + entities/relationships
- /memory/graph/entity      → add entity to knowledge graph
- /memory/graph/relationship → add relationship to knowledge graph
- /memory/vector/{collection}/search → direct vector search
- /memory/knowledge/categories → list knowledge categories

Uses real VectorStore, KnowledgeBase, KnowledgeGraph from quant_nanggroe.memory
when available, with in-memory fallback.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory", tags=["memory"])

# ---------------------------------------------------------------------------
# Real memory modules — graceful fallback
# ---------------------------------------------------------------------------

_HAS_VECTOR_STORE = False
_HAS_KNOWLEDGE_BASE = False
_HAS_KNOWLEDGE_GRAPH = False

try:
    from quant_nanggroe.memory.vector import (
        VectorStore,
        CollectionName,
        VectorDocument,
        SearchResult,
        get_vector_store,
    )

    _vector_store: VectorStore = get_vector_store()
    _HAS_VECTOR_STORE = True
except ImportError:
    _vector_store = None  # type: ignore
    logger.info("VectorStore not available — using in-memory fallback")

try:
    from quant_nanggroe.memory.knowledge import KnowledgeBase

    _knowledge_base = KnowledgeBase()
    _HAS_KNOWLEDGE_BASE = True
except ImportError:
    _knowledge_base = None  # type: ignore

try:
    from quant_nanggroe.memory.knowledge_graph import (
        KnowledgeGraph,
        EntityType,
        RelationType,
        Entity,
        Relationship,
    )

    _knowledge_graph = KnowledgeGraph()
    _HAS_KNOWLEDGE_GRAPH = True
except ImportError:
    _knowledge_graph = None  # type: ignore
    EntityType = None  # type: ignore
    RelationType = None  # type: ignore

# ---------------------------------------------------------------------------
# In-memory fallback stores
# ---------------------------------------------------------------------------

_fallback_store: Dict[str, Any] = {}
_fallback_id_counter: int = 0

# Pre-populate fallback knowledge graph
_fallback_graph_entities: Dict[str, Dict[str, Any]] = {}
_fallback_graph_relationships: List[Dict[str, Any]] = []


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _make_id() -> str:
    return uuid.uuid4().hex[:12]


async def _ensure_vector_initialized() -> bool:
    """Initialize vector store if needed. Returns True if ready."""
    global _HAS_VECTOR_STORE
    if _HAS_VECTOR_STORE and _vector_store:
        try:
            return await _vector_store.initialize()
        except Exception:
            pass
    return False


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/search")
async def memory_search(
    q: str = Query("", description="Search query"),
    limit: int = Query(10, ge=1, le=100),
    collection: Optional[str] = Query(None, description="Collection filter"),
) -> Dict[str, Any]:
    """Search across all memory stores (vector + knowledge)."""
    results = []

    # Search vector store
    if _HAS_VECTOR_STORE and _vector_store:
        await _ensure_vector_initialized()
        collections_to_search = (
            [collection]
            if collection
            else [c.value for c in CollectionName]
        )
        for col in collections_to_search:
            try:
                hits = await _vector_store.search(col, q, n_results=limit // len(collections_to_search))
                for hit in hits:
                    results.append({
                        "id": hit.doc_id,
                        "type": "vector",
                        "collection": col,
                        "content": hit.content,
                        "metadata": hit.metadata,
                        "relevance": hit.relevance_score,
                        "source": "vector_store",
                    })
            except Exception:
                pass

    # Fallback vector search (keyword)
    else:
        q_lower = q.lower()
        for key, entry in _fallback_store.items():
            content = str(entry.get("content", entry.get("data", "")))
            if q_lower in content.lower() or q_lower in key.lower():
                results.append({
                    "id": entry.get("id", key),
                    "type": "fallback",
                    "collection": entry.get("collection", "general"),
                    "content": content[:300],
                    "metadata": entry,
                    "relevance": 0.5,
                    "source": "fallback",
                })

    # Search knowledge base
    if _HAS_KNOWLEDGE_BASE and _knowledge_base and q:
        try:
            kb_results = _knowledge_base.search(q, limit=limit)
            for entry in kb_results:
                results.append({
                    "id": str(entry.get("id", "")),
                    "type": "knowledge",
                    "collection": entry.get("category", "general"),
                    "content": entry.get("content", "")[:300],
                    "title": entry.get("title", ""),
                    "tags": entry.get("tags", []),
                    "confidence": entry.get("confidence", 0),
                    "relevance": entry.get("relevance_score", 0.5),
                    "source": "knowledge_base",
                })
        except Exception:
            pass

    # Sort by relevance
    results.sort(key=lambda r: r.get("relevance", 0), reverse=True)

    return {
        "results": results[:limit],
        "total": min(len(results), limit),
        "query": q,
    }


@router.post("/store")
async def memory_store(
    data: Dict[str, Any],
    collection: str = "general",
) -> Dict[str, Any]:
    """Store data in memory (vector + knowledge base)."""
    content = data.get("content", data.get("data", json.dumps(data)))
    entry_id = data.get("id", f"mem-{_make_id()}")
    metadata = {k: v for k, v in data.items() if k not in ("content", "data", "id")}

    stored_count = 0

    # Store in VectorStore
    if _HAS_VECTOR_STORE and _vector_store:
        await _ensure_vector_initialized()
        try:
            doc = await _vector_store.add(
                collection=collection,
                content=content,
                metadata=metadata,
                doc_id=entry_id,
            )
            stored_count += 1
        except Exception:
            pass

    # Store in KnowledgeBase
    if _HAS_KNOWLEDGE_BASE and _knowledge_base:
        try:
            kb_id = _knowledge_base.add(
                category=collection,
                title=data.get("title", content[:50]),
                content=content,
                tags=metadata.get("tags", []),
                source=metadata.get("source", "api"),
                confidence=metadata.get("confidence", 1.0),
            )
            stored_count += 1
        except Exception:
            pass

    # Fallback
    if stored_count == 0:
        global _fallback_id_counter
        _fallback_id_counter += 1
        entry = {
            "id": entry_id,
            "collection": collection,
            "content": content,
            "metadata": metadata,
            "created_at": _now(),
        }
        _fallback_store[entry_id] = entry
        stored_count = 1

    return {
        "status": "stored",
        "id": entry_id,
        "stores_updated": stored_count,
        "collection": collection,
    }


@router.get("/entry/{entry_id:path}")
async def memory_get_entry(entry_id: str) -> Dict[str, Any]:
    """Get a specific memory entry by ID."""
    # Check VectorStore fallback
    for col_name in _fallback_store:
        entry = _fallback_store.get(entry_id)
        if entry:
            return {"id": entry_id, "content": entry, "source": "fallback"}

    # Check KnowledgeBase
    if _HAS_KNOWLEDGE_BASE and _knowledge_base:
        try:
            kb_entry = _knowledge_base.get(int(entry_id))
            if kb_entry:
                return {
                    "id": entry_id,
                    "type": "knowledge",
                    "title": kb_entry.get("title", ""),
                    "content": kb_entry.get("content", ""),
                    "category": kb_entry.get("category", ""),
                    "tags": kb_entry.get("tags", []),
                    "confidence": kb_entry.get("confidence", 0),
                    "created_at": kb_entry.get("created_at", ""),
                    "updated_at": kb_entry.get("updated_at", ""),
                    "source": "knowledge_base",
                }
        except (ValueError, TypeError):
            pass

    raise HTTPException(status_code=404, detail=f"Entry {entry_id} not found")


@router.get("/list")
async def memory_list(
    collection: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """List memory entries with statistics."""
    entries = []

    # KnowledgeBase entries
    if _HAS_KNOWLEDGE_BASE and _knowledge_base:
        try:
            if collection:
                kb_entries = _knowledge_base.get_by_category(collection)
            else:
                kb_entries = []
                for cat in _knowledge_base.get_categories():
                    kb_entries.extend(_knowledge_base.get_by_category(cat))

            for entry in kb_entries[:limit]:
                entries.append({
                    "id": str(entry.get("id", "")),
                    "type": "knowledge",
                    "category": entry.get("category", ""),
                    "title": entry.get("title", "")[:100],
                    "tags": entry.get("tags", []),
                    "created_at": entry.get("created_at", ""),
                    "confidence": entry.get("confidence", 0),
                })
        except Exception:
            pass

    # Fallback entries
    for key, entry in _fallback_store.items():
        col = entry.get("collection", "general")
        if collection and col != collection:
            continue
        entries.append({
            "id": key,
            "type": "fallback",
            "category": col,
            "content": str(entry.get("content", ""))[:100],
            "created_at": entry.get("created_at", ""),
        })

    # Stats
    total = len(entries)
    if _HAS_KNOWLEDGE_BASE and _knowledge_base:
        try:
            stats = _knowledge_base.get_stats()
        except Exception:
            stats = {"total_entries": total, "categories": {}}
    else:
        stats = {"total_entries": total, "categories": {}}

    # VectorStore stats
    if _HAS_VECTOR_STORE and _vector_store:
        await _ensure_vector_initialized()
        try:
            vs_stats = await _vector_store.get_stats()
            stats["vector_store"] = {
                "total_documents": vs_stats.total_documents,
                "collections": vs_stats.collections,
            }
        except Exception:
            pass

    return {
        "entries": entries[:limit],
        "total": min(len(entries), limit),
        "stats": stats,
    }


@router.delete("/entry/{entry_id:path}")
async def memory_delete(entry_id: str) -> Dict[str, Any]:
    """Delete a memory entry."""
    deleted = False

    # VectorStore
    if _HAS_VECTOR_STORE and _vector_store:
        await _ensure_vector_initialized()
        for col in (c.value for c in CollectionName):
            try:
                if await _vector_store.delete(col, entry_id):
                    deleted = True
                    break
            except Exception:
                pass

    # KnowledgeBase
    if _HAS_KNOWLEDGE_BASE and _knowledge_base:
        try:
            _knowledge_base.delete(int(entry_id))
            deleted = True
        except (ValueError, TypeError):
            pass

    # Fallback
    if entry_id in _fallback_store:
        del _fallback_store[entry_id]
        deleted = True

    return {
        "status": "deleted" if deleted else "not_found",
        "id": entry_id,
        "deleted": deleted,
    }


# ---------------------------------------------------------------------------
# Knowledge Graph endpoints
# ---------------------------------------------------------------------------


@router.get("/graph")
async def memory_graph_stats() -> Dict[str, Any]:
    """Get knowledge graph statistics and summary."""
    entities = []
    relationships = []

    if _HAS_KNOWLEDGE_GRAPH and _knowledge_graph:
        try:
            stats = _knowledge_graph.stats()
            # Top entities by centrality
            top = _knowledge_graph.centrality(top_k=10)
            entities = [
                {"id": e.id, "name": e.name, "type": e.entity_type.value, "degree": d}
                for e, d in top
            ]
            # Recent relationships
            rels = []
            for rt_name in stats.get("relationship_types", {}):
                rt = getattr(RelationType, rt_name.upper(), None) if RelationType else None
                if rt:
                    rels.extend(_knowledge_graph.get_relationships_by_type(rt))
            rels = rels[:20]
            relationships = [
                {
                    "id": r.id,
                    "source": _knowledge_graph.get_entity(r.source_id).name if _knowledge_graph.get_entity(r.source_id) else r.source_id,
                    "target": _knowledge_graph.get_entity(r.target_id).name if _knowledge_graph.get_entity(r.target_id) else r.target_id,
                    "type": r.relation_type.value,
                    "weight": r.weight,
                }
                for r in rels
            ]
        except Exception as e:
            logger.debug("Graph query failed: %s", e)
            stats = {"entity_count": 0, "relationship_count": 0}

    elif _fallback_graph_entities:
        stats = {
            "entity_count": len(_fallback_graph_entities),
            "relationship_count": len(_fallback_graph_relationships),
        }
    else:
        stats = {"entity_count": 0, "relationship_count": 0}

    return {
        "stats": stats,
        "top_entities": entities[:20],
        "recent_relationships": relationships[:20],
    }


@router.post("/graph/entity")
async def memory_graph_add_entity(
    name: str,
    entity_type: str = "symbol",
    properties: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Add an entity to the knowledge graph."""
    if _HAS_KNOWLEDGE_GRAPH and _knowledge_graph:
        try:
            et = EntityType(entity_type)
            entity = _knowledge_graph.add_entity(
                name=name,
                entity_type=et,
                properties=properties or {},
                tags=tags or [],
                source="memory_api",
            )
            return {
                "status": "created",
                "id": entity.id,
                "name": entity.name,
                "type": entity.entity_type.value,
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Fallback
    eid = f"E-{entity_type}-{_make_id()}"
    _fallback_graph_entities[eid] = {
        "id": eid,
        "name": name,
        "entity_type": entity_type,
        "properties": properties or {},
        "tags": tags or [],
    }
    return {
        "status": "created",
        "id": eid,
        "name": name,
        "type": entity_type,
        "source": "fallback",
    }


@router.post("/graph/relationship")
async def memory_graph_add_relationship(
    source_id: str,
    target_id: str,
    relation_type: str = "correlated_with",
    weight: float = 1.0,
) -> Dict[str, Any]:
    """Add a relationship between two entities in the knowledge graph."""
    if _HAS_KNOWLEDGE_GRAPH and _knowledge_graph:
        try:
            rt = RelationType(relation_type)
            rel = _knowledge_graph.add_relationship(
                source_id=source_id,
                target_id=target_id,
                relation_type=rt,
                weight=weight,
                source="memory_api",
            )
            return {
                "status": "created",
                "id": rel.id,
                "source_id": source_id,
                "target_id": target_id,
                "type": relation_type,
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Fallback
    rid = f"R-{relation_type}-{_make_id()}"
    _fallback_graph_relationships.append({
        "id": rid,
        "source_id": source_id,
        "target_id": target_id,
        "relation_type": relation_type,
        "weight": weight,
    })
    return {
        "status": "created",
        "id": rid,
        "source_id": source_id,
        "target_id": target_id,
        "type": relation_type,
        "source": "fallback",
    }


@router.get("/vector/{collection}/search")
async def memory_vector_search(
    collection: str,
    q: str = Query("", description="Search query"),
    limit: int = Query(10, ge=1, le=100),
) -> Dict[str, Any]:
    """Directly search a specific vector collection."""
    if _HAS_VECTOR_STORE and _vector_store:
        await _ensure_vector_initialized()
        try:
            results = await _vector_store.search(collection, q, n_results=limit)
            return {
                "results": [
                    {
                        "id": r.doc_id,
                        "content": r.content[:300],
                        "metadata": r.metadata,
                        "distance": r.distance,
                        "relevance": r.relevance_score,
                    }
                    for r in results
                ],
                "total": len(results),
                "collection": collection,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Vector search failed: {e}")

    raise HTTPException(status_code=501, detail="Vector store not available")


@router.get("/knowledge/categories")
async def memory_knowledge_categories() -> Dict[str, Any]:
    """List all knowledge base categories."""
    categories = []

    if _HAS_KNOWLEDGE_BASE and _knowledge_base:
        try:
            for cat in _knowledge_base.get_categories():
                entries = _knowledge_base.get_by_category(cat)
                categories.append({
                    "name": cat,
                    "count": len(entries),
                })
        except Exception:
            pass

    if not categories:
        # Derive from fallback
        from collections import Counter
        cat_counts = Counter(e.get("collection", "general") for e in _fallback_store.values())
        for name, count in cat_counts.items():
            categories.append({"name": name, "count": count})

    return {
        "categories": categories,
        "total": len(categories),
    }
