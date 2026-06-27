# memory.paging

## Class: 

Memory tier classification.

*Line: 61*

---

## Class: 

Type classification for memory blocks.

*Line: 68*

---

## Class: 

Policy for evicting blocks from core memory.

*Line: 82*

---

## Class: 

A single unit of memory with metadata.

Memory blocks are the fundamental unit of storage in the paging system.
Each block carries content plus metadata used for retrieval, eviction,
and relevance scoring.

Attributes:
    id: Unique block identifier
    content: The actual memory content (text or structured data)
    tier: Which memory tier this block resides in
    block_type: Type classification
    importance: Priority score (0.0-1.0) for eviction decisions
    source_agent: Agent that created this block
    tags: Categorization labels for search
    timestamp: When the block was created
    last_accessed: When the block was last accessed (for LRU)
    access_count: Number of times accessed
    embedding: Optional vector embedding for semantic search
    metadata: Additional metadata

**Methods:** touch, to_dict, from_dict

*Line: 90*

---

## Class: 

Simple TF-IDF vectorizer for semantic search when embedding models
are not available.

Implements term frequency-inverse document frequency for text similarity.

**Methods:** __init__, _tokenize, fit, transform, vocabulary_size

*Line: 169*

---

## Function: 

Compute cosine similarity between two vectors.

*Line: 253*

---

## Class: 

Fast, limited-size working memory for agent context.

Analogous to CPU registers / L1 cache. Holds the most relevant
information the agent needs for current decision-making.

Features:
- Fixed capacity with LRU eviction
- Direct read/write access
- Auto-compaction when approaching limits
- Block-level granularity for page-in/page-out

**Methods:** __init__, size, total_content_chars, utilization, insert, get, remove, search, get_all_blocks, clear, _evict, stats

*Line: 270*

---

## Class: 

Large persistent storage for historical data and trade records.

Analogous to disk storage. Provides unlimited capacity (backed by disk)
with write-once semantics and versioning support.

Features:
- Unlimited capacity with disk backing
- Persistent across sessions
- Bulk import/export
- Version tracking

**Methods:** __init__, size, insert, get, remove, search, bulk_insert, get_blocks_by_type, get_blocks_by_agent, _idf_score, save, load, stats

*Line: 509*

---

## Class: 

Search/retrieval interface across archival memory.

Analogous to an index/search engine. Provides semantic search
using embeddings (with TF-IDF fallback when embeddings are unavailable),
keyword filtering, and relevance scoring.

Features:
- Semantic search using vector similarity
- TF-IDF fallback when embeddings are not available
- Hybrid search (semantic + keyword)
- Metadata and tag filtering
- Relevance scoring and ranking

**Methods:** __init__, _ensure_tfidf_fitted, _get_embedding, search, recall_by_time, recall_by_agent, stats

*Line: 788*

---

## Class: 

Controller that manages the three-tier memory system with page-in/page-out.

Coordinates the flow of memory blocks between tiers:
- Page-in: Load relevant blocks from archival to core memory
- Page-out: Evict blocks from core to archival memory
- Automatic eviction when core memory is full
- Manual page operations for agent-driven context management

Usage:
    controller = MemoryPagingController()
    block = controller.core_insert(
        content="BTC showing bullish divergence",
        block_type=BlockType.ANALYSIS,
        source_agent="researcher",
    )
    # ... later, when core memory fills up, blocks are automatically paged out

    # Manually page in relevant context
    results = controller.page_in(
        query="BTC analysis",
        tags=["crypto"],
        limit=5,
    )

**Methods:** __init__, core, archival, recall, _generate_block_id, core_insert, core_get, page_in, page_out, archive_block, search, save, load, stats, clear_all

*Line: 991*

---

## Function: 

Update access time and count (for LRU tracking).

*Line: 125*

---

## Function: 

Serialize block to dictionary.

*Line: 130*

---

## Function: 

Deserialize block from dictionary.

*Line: 147*

---

## Function: 

*Line: 177*

---

## Function: 

Simple tokenization: lowercase, split on non-alphanumeric.

*Line: 184*

---

## Function: 

Build vocabulary and compute IDF from documents.

*Line: 188*

---

## Function: 

Transform text to TF-IDF vector.

*Line: 215*

---

## Function: 

Get vocabulary size.

*Line: 243*

---

## Function: 

Initialize core memory.

Args:
    max_blocks: Maximum number of memory blocks
    max_content_chars: Maximum total content characters
    eviction_policy: Policy for evicting blocks when full

*Line: 284*

---

## Function: 

Number of blocks in core memory.

*Line: 304*

---

## Function: 

Total content characters in core memory.

*Line: 309*

---

## Function: 

Memory utilization as a fraction (0.0-1.0).

*Line: 314*

---

## Function: 

Insert a block into core memory.

If memory is full, evicts blocks according to the eviction policy
to make room.

Args:
    block: Memory block to insert

Returns:
    Evicted block if one was removed, None otherwise

*Line: 318*

---

## Function: 

Get a block by ID and update access time.

Args:
    block_id: Block identifier

Returns:
    Memory block if found, None otherwise

*Line: 359*

---

## Function: 

Remove a block from core memory.

Args:
    block_id: Block identifier

Returns:
    Removed block if found, None otherwise

*Line: 375*

---

## Function: 

Search core memory blocks.

Args:
    query: Text query (matched against content)
    tags: Filter by tags (any match)
    block_type: Filter by block type
    source_agent: Filter by source agent
    limit: Maximum results

Returns:
    List of matching blocks

*Line: 387*

---

## Function: 

Get all blocks in core memory.

*Line: 435*

---

## Function: 

Clear all blocks from core memory.

*Line: 439*

---

## Function: 

Evict a block according to the eviction policy.

Returns:
    Evicted block, or None if no blocks to evict

*Line: 443*

---

## Function: 

Get core memory statistics.

*Line: 483*

---

## Function: 

Initialize archival memory.

Args:
    persist_path: Directory path for persistence

*Line: 523*

---

## Function: 

Number of blocks in archival memory.

*Line: 536*

---

## Function: 

Insert a block into archival memory.

Args:
    block: Memory block to archive

Returns:
    Block ID

*Line: 540*

---

## Function: 

Get a block by ID.

Args:
    block_id: Block identifier

Returns:
    Memory block if found, None otherwise

*Line: 569*

---

## Function: 

Remove a block from archival memory.

Args:
    block_id: Block identifier

Returns:
    True if removed, False if not found

*Line: 584*

---

## Function: 

Search archival memory by keywords and filters.

Uses inverted index for fast keyword search.

Args:
    query: Text query
    tags: Filter by tags
    block_type: Filter by block type
    source_agent: Filter by source agent
    limit: Maximum results

Returns:
    List of matching blocks

*Line: 615*

---

## Function: 

Insert multiple blocks at once.

Args:
    blocks: List of memory blocks

Returns:
    List of inserted block IDs

*Line: 698*

---

## Function: 

Get all blocks of a specific type.

*Line: 713*

---

## Function: 

Get all blocks from a specific agent.

*Line: 717*

---

## Function: 

Compute simple IDF score for a word.

*Line: 721*

---

## Function: 

Persist archival memory to disk.

*Line: 729*

---

## Function: 

Load archival memory from disk.

*Line: 742*

---

## Function: 

Get archival memory statistics.

*Line: 768*

---

## Function: 

Initialize recall memory.

Args:
    archival: Reference to the archival memory to search
    embedding_fn: Optional function to compute text embeddings

*Line: 804*

---

## Function: 

Fit TF-IDF vectorizer on archival content if not already done.

*Line: 822*

---

## Function: 

Get embedding for text, using embedding function or TF-IDF fallback.

*Line: 831*

---

## Function: 

Search archival memory with semantic and keyword matching.

Args:
    query: Search query text
    tags: Filter by tags
    block_type: Filter by block type
    source_agent: Filter by source agent
    min_relevance: Minimum relevance score threshold
    limit: Maximum results
    use_semantic: Whether to use semantic search

Returns:
    List of (block, relevance_score) tuples sorted by relevance

*Line: 842*

---

## Function: 

Recall memory blocks by time range.

Args:
    start_time: Start time ISO string (inclusive)
    end_time: End time ISO string (inclusive)
    block_type: Filter by block type
    limit: Maximum results

Returns:
    List of memory blocks within the time range

*Line: 922*

---

## Function: 

Recall all memory blocks from a specific agent.

Args:
    source_agent: Source agent name
    limit: Maximum results

Returns:
    List of memory blocks from the agent

*Line: 955*

---

## Function: 

Get recall memory statistics.

*Line: 974*

---

## Function: 

Initialize the memory paging controller.

Args:
    core_max_blocks: Maximum blocks in core memory
    core_max_content_chars: Maximum total content chars in core
    eviction_policy: Eviction policy for core memory
    archival_persist_path: Path for archival persistence
    embedding_fn: Optional embedding function for semantic search

*Line: 1018*

---

## Function: 

Access core memory directly.

*Line: 1051*

---

## Function: 

Access archival memory directly.

*Line: 1056*

---

## Function: 

Access recall memory directly.

*Line: 1061*

---

## Function: 

Generate a unique block ID.

*Line: 1065*

---

## Function: 

Insert a new block into core memory.

If core memory is full, the least-priority block is automatically
paged out to archival memory.

Args:
    content: Block content text
    block_type: Type classification
    importance: Importance score (0.0-1.0)
    source_agent: Agent creating this block
    tags: Categorization tags
    metadata: Additional metadata

Returns:
    The created memory block

*Line: 1071*

---

## Function: 

Get a block from core memory by ID.

*Line: 1120*

---

## Function: 

Page in relevant blocks from archival to core memory.

Searches archival memory for blocks matching the query and
loads them into core memory. If core memory is full, existing
blocks are paged out to make room.

Args:
    query: Search query for finding relevant blocks
    tags: Filter by tags
    block_type: Filter by block type
    source_agent: Filter by source agent
    limit: Maximum blocks to page in

Returns:
    List of blocks that were paged in

*Line: 1124*

---

## Function: 

Page out blocks from core to archival memory.

Can either page out specific blocks by ID, or page out
a number of least-priority blocks.

Args:
    block_ids: Specific block IDs to page out (takes priority)
    count: Number of least-priority blocks to page out

Returns:
    List of blocks that were paged out

*Line: 1180*

---

## Function: 

Directly insert a block into archival memory (bypasses core).

Useful for storing historical data that doesn't need immediate access.

Args:
    content: Block content text
    block_type: Type classification
    importance: Importance score
    source_agent: Agent creating this block
    tags: Categorization tags
    metadata: Additional metadata

Returns:
    The created memory block

*Line: 1221*

---

## Function: 

Search across all memory tiers.

First searches core memory, then archival memory via recall.
Returns combined results sorted by relevance.

Args:
    query: Search query
    tags: Filter by tags
    block_type: Filter by block type
    source_agent: Filter by source agent
    limit: Maximum results

Returns:
    List of (block, relevance_score) tuples

*Line: 1259*

---

## Function: 

Save all persistent memory tiers to disk.

*Line: 1320*

---

## Function: 

Load persistent memory tiers from disk.

*Line: 1324*

---

## Function: 

Get comprehensive memory system statistics.

*Line: 1328*

---

## Function: 

Clear all memory tiers.

*Line: 1341*

---

