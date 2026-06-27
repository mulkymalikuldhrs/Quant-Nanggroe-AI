# memory.knowledge

## Class: 

Persistent knowledge base for trading insights and market knowledge.

Stores categorized knowledge entries with timestamps and metadata,
enabling agents to build and retrieve institutional memory over time.

Usage:
    kb = KnowledgeBase()
    kb.add(
        category="market_regime",
        title="BTC 2024 Halving Cycle",
        content="Post-halving supply shock typically takes 6-12 months...",
        tags=["btc", "halving", "cycle"],
    )
    results = kb.search("halving cycle", category="market_regime")

**Methods:** __init__, add, search, get, get_by_category, update, delete, get_categories, get_stats, save, load

*Line: 18*

---

## Function: 

*Line: 36*

---

## Function: 

Add a knowledge entry.

Args:
    category: Knowledge category
    title: Entry title
    content: Entry content
    tags: Optional tags for search
    source: Source of the knowledge
    confidence: Confidence level (0.0-1.0)
    metadata: Additional metadata

Returns:
    Entry ID

*Line: 41*

---

## Function: 

Search knowledge base entries.

Args:
    query: Search query (matched against title and content)
    category: Filter by category
    tags: Filter by tags (any match)
    limit: Maximum results to return

Returns:
    List of matching entries sorted by relevance

*Line: 83*

---

## Function: 

Get a specific knowledge entry by ID.

*Line: 130*

---

## Function: 

Get all entries in a category.

*Line: 137*

---

## Function: 

Update an existing knowledge entry.

*Line: 141*

---

## Function: 

Delete a knowledge entry.

*Line: 153*

---

## Function: 

Get all unique categories.

*Line: 158*

---

## Function: 

Get knowledge base statistics.

*Line: 162*

---

## Function: 

Persist knowledge base to disk.

*Line: 172*

---

## Function: 

Load knowledge base from disk.

*Line: 185*

---

