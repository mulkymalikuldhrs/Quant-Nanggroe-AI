# memory.vector

## Class: 

Pre-configured vector store collections.

*Line: 48*

---

## Class: 

Embedding provider for vector generation.

*Line: 57*

---

## Class: 

A document stored in the vector store.

*Line: 68*

---

## Class: 

A search result from the vector store.

*Line: 79*

---

## Class: 

Vector store statistics.

*Line: 89*

---

## Class: 

ChromaDB-backed vector store for trading knowledge.

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

**Methods:** __init__, _fallback_search

*Line: 101*

---

## Function: 

Get or create the default VectorStore instance.

*Line: 520*

---

## Function: 

*Line: 119*

---

## Function: 

Simple keyword-based fallback search.

*Line: 477*

---

