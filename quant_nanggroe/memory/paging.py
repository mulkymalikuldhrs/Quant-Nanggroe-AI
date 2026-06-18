"""Letta-style Memory Paging System for Quant Nanggroe AI.

Implements a three-tier memory architecture inspired by the Letta framework:

1. Core Memory (Working Memory): Fast, limited-size memory for what the agent
   is currently thinking about. Analogous to CPU registers / L1 cache.
   - Maximum capacity with LRU eviction
   - Direct read/write access for agents
   - Auto-compaction when approaching limits

2. Archival Memory: Large persistent storage for historical data, trade records,
   and long-term knowledge. Analogous to disk storage.
   - Unlimited capacity (backed by disk)
   - Write-once with versioning
   - Supports bulk import/export

3. Recall Memory: Search/retrieval interface across archival memory.
   Analogous to an index/search engine.
   - Semantic search using embeddings (with TF-IDF fallback)
   - Keyword and metadata filtering
   - Relevance scoring and ranking

Page-in/Page-out Semantics:
- Page-in: Load relevant context from archival to core memory
- Page-out: Evict least-recently-used items from core to archival
- Automatic eviction when core memory exceeds capacity
- Manual page-in for agent-driven context loading

Memory Blocks:
Each memory item is stored as a MemoryBlock with metadata:
- timestamp: When the block was created
- importance: Priority score (0.0-1.0) for eviction decisions
- source_agent: Which agent created this block
- tags: Categorization labels
- block_type: Type classification (thought, trade, analysis, etc.)
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Data Classes
# =============================================================================


class MemoryTier(str, Enum):
    """Memory tier classification."""
    CORE = "core"           # Working memory (fast, limited)
    ARCHIVAL = "archival"   # Long-term storage (large, persistent)
    RECALL = "recall"       # Search/retrieval index


class BlockType(str, Enum):
    """Type classification for memory blocks."""
    THOUGHT = "thought"             # Agent's current thinking
    ANALYSIS = "analysis"           # Market or trade analysis
    TRADE_RECORD = "trade_record"   # Historical trade data
    SIGNAL = "signal"               # Trading signal
    RISK_ASSESSMENT = "risk_assessment"  # Risk check result
    MARKET_DATA = "market_data"     # Market data snapshot
    KNOWLEDGE = "knowledge"         # Learned knowledge
    CONTEXT = "context"             # Contextual information
    DECISION = "decision"           # Trading decision
    REFLECTION = "reflection"       # Post-trade reflection


class EvictionPolicy(str, Enum):
    """Policy for evicting blocks from core memory."""
    LRU = "lru"                   # Least Recently Used
    IMPORTANCE = "importance"     # Lowest importance first
    LRU_IMPORTANCE = "lru_importance"  # Combined LRU + importance score


@dataclass
class MemoryBlock:
    """
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
    """
    id: str
    content: str
    tier: MemoryTier = MemoryTier.CORE
    block_type: BlockType = BlockType.THOUGHT
    importance: float = 0.5
    source_agent: str = ""
    tags: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def touch(self) -> None:
        """Update access time and count (for LRU tracking)."""
        self.last_accessed = time.time()
        self.access_count += 1

    def to_dict(self) -> Dict[str, Any]:
        """Serialize block to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "tier": self.tier.value,
            "block_type": self.block_type.value,
            "importance": self.importance,
            "source_agent": self.source_agent,
            "tags": self.tags,
            "timestamp": self.timestamp,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MemoryBlock:
        """Deserialize block from dictionary."""
        return cls(
            id=data["id"],
            content=data["content"],
            tier=MemoryTier(data.get("tier", "core")),
            block_type=BlockType(data.get("block_type", "thought")),
            importance=data.get("importance", 0.5),
            source_agent=data.get("source_agent", ""),
            tags=data.get("tags", []),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            last_accessed=data.get("last_accessed", time.time()),
            access_count=data.get("access_count", 0),
            metadata=data.get("metadata", {}),
        )


# =============================================================================
# TF-IDF Vectorizer (Fallback for embedding-based search)
# =============================================================================


class TfidfVectorizer:
    """
    Simple TF-IDF vectorizer for semantic search when embedding models
    are not available.

    Implements term frequency-inverse document frequency for text similarity.
    """

    def __init__(self, max_features: int = 5000) -> None:
        self._max_features = max_features
        self._vocabulary: Dict[str, int] = {}
        self._idf: Dict[str, float] = {}
        self._doc_count: int = 0

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Simple tokenization: lowercase, split on non-alphanumeric."""
        return re.findall(r"[a-z0-9]+", text.lower())

    def fit(self, documents: List[str]) -> TfidfVectorizer:
        """Build vocabulary and compute IDF from documents."""
        self._doc_count = len(documents)
        doc_freq: Dict[str, int] = {}

        for doc in documents:
            tokens = set(self._tokenize(doc))
            for token in tokens:
                doc_freq[token] = doc_freq.get(token, 0) + 1

        # Sort by frequency and take top features
        sorted_terms = sorted(
            doc_freq.items(), key=lambda x: x[1], reverse=True
        )[: self._max_features]

        self._vocabulary = {
            term: idx for idx, (term, _) in enumerate(sorted_terms)
        }

        # Compute IDF
        for term, freq in sorted_terms:
            self._idf[term] = math.log(
                (self._doc_count + 1) / (freq + 1)
            ) + 1  # Smooth IDF

        return self

    def transform(self, text: str) -> List[float]:
        """Transform text to TF-IDF vector."""
        tokens = self._tokenize(text)
        if not tokens or not self._vocabulary:
            return [0.0] * max(len(self._vocabulary), 1)

        # Term frequency
        tf: Dict[str, int] = {}
        for token in tokens:
            tf[token] = tf.get(token, 0) + 1

        # TF-IDF vector
        vector = [0.0] * len(self._vocabulary)
        for term, count in tf.items():
            if term in self._vocabulary:
                idx = self._vocabulary[term]
                tf_val = count / len(tokens)
                idf_val = self._idf.get(term, 1.0)
                vector[idx] = tf_val * idf_val

        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]

        return vector

    @property
    def vocabulary_size(self) -> int:
        """Get vocabulary size."""
        return len(self._vocabulary)


# =============================================================================
# Similarity Utilities
# =============================================================================


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# =============================================================================
# Core Memory (L1 Cache - Working Memory)
# =============================================================================


class CoreMemory:
    """
    Fast, limited-size working memory for agent context.

    Analogous to CPU registers / L1 cache. Holds the most relevant
    information the agent needs for current decision-making.

    Features:
    - Fixed capacity with LRU eviction
    - Direct read/write access
    - Auto-compaction when approaching limits
    - Block-level granularity for page-in/page-out
    """

    def __init__(
        self,
        max_blocks: int = 50,
        max_content_chars: int = 50000,
        eviction_policy: EvictionPolicy = EvictionPolicy.LRU_IMPORTANCE,
    ) -> None:
        """
        Initialize core memory.

        Args:
            max_blocks: Maximum number of memory blocks
            max_content_chars: Maximum total content characters
            eviction_policy: Policy for evicting blocks when full
        """
        self._max_blocks = max_blocks
        self._max_content_chars = max_content_chars
        self._eviction_policy = eviction_policy
        self._blocks: OrderedDict[str, MemoryBlock] = OrderedDict()

    @property
    def size(self) -> int:
        """Number of blocks in core memory."""
        return len(self._blocks)

    @property
    def total_content_chars(self) -> int:
        """Total content characters in core memory."""
        return sum(len(b.content) for b in self._blocks.values())

    @property
    def utilization(self) -> float:
        """Memory utilization as a fraction (0.0-1.0)."""
        return len(self._blocks) / self._max_blocks if self._max_blocks > 0 else 0.0

    def insert(self, block: MemoryBlock) -> Optional[MemoryBlock]:
        """
        Insert a block into core memory.

        If memory is full, evicts blocks according to the eviction policy
        to make room.

        Args:
            block: Memory block to insert

        Returns:
            Evicted block if one was removed, None otherwise
        """
        evicted = None

        # Check if block already exists - update it
        if block.id in self._blocks:
            self._blocks.move_to_end(block.id)
            self._blocks[block.id] = block
            return None

        # Evict if at capacity
        while (
            len(self._blocks) >= self._max_blocks
            or self.total_content_chars + len(block.content) > self._max_content_chars
        ):
            evicted_block = self._evict()
            if evicted_block is None:
                break  # Cannot evict anything
            if evicted is None:
                evicted = evicted_block

        block.tier = MemoryTier.CORE
        self._blocks[block.id] = block
        self._blocks.move_to_end(block.id)  # Mark as most recently used
        logger.debug(
            f"Core memory: inserted block {block.id} "
            f"(size={len(self._blocks)}/{self._max_blocks})"
        )
        return evicted

    def get(self, block_id: str) -> Optional[MemoryBlock]:
        """
        Get a block by ID and update access time.

        Args:
            block_id: Block identifier

        Returns:
            Memory block if found, None otherwise
        """
        block = self._blocks.get(block_id)
        if block:
            block.touch()
            self._blocks.move_to_end(block_id)
        return block

    def remove(self, block_id: str) -> Optional[MemoryBlock]:
        """
        Remove a block from core memory.

        Args:
            block_id: Block identifier

        Returns:
            Removed block if found, None otherwise
        """
        return self._blocks.pop(block_id, None)

    def search(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        block_type: Optional[BlockType] = None,
        source_agent: Optional[str] = None,
        limit: int = 10,
    ) -> List[MemoryBlock]:
        """
        Search core memory blocks.

        Args:
            query: Text query (matched against content)
            tags: Filter by tags (any match)
            block_type: Filter by block type
            source_agent: Filter by source agent
            limit: Maximum results

        Returns:
            List of matching blocks
        """
        query_lower = query.lower()
        results = []

        for block in self._blocks.values():
            # Filter by tags
            if tags and not any(t in block.tags for t in tags):
                continue

            # Filter by block type
            if block_type and block.block_type != block_type:
                continue

            # Filter by source agent
            if source_agent and block.source_agent != source_agent:
                continue

            # Text matching
            if query_lower and query_lower in block.content.lower():
                block.touch()
                results.append(block)
            elif not query_lower:
                results.append(block)

        # Sort by last accessed (most recent first)
        results.sort(key=lambda b: b.last_accessed, reverse=True)
        return results[:limit]

    def get_all_blocks(self) -> List[MemoryBlock]:
        """Get all blocks in core memory."""
        return list(self._blocks.values())

    def clear(self) -> None:
        """Clear all blocks from core memory."""
        self._blocks.clear()

    def _evict(self) -> Optional[MemoryBlock]:
        """
        Evict a block according to the eviction policy.

        Returns:
            Evicted block, or None if no blocks to evict
        """
        if not self._blocks:
            return None

        if self._eviction_policy == EvictionPolicy.LRU:
            # Evict the least recently used (first in OrderedDict)
            block_id, block = self._blocks.popitem(last=False)
            logger.debug(f"Core memory: LRU evicted block {block_id}")
            return block

        elif self._eviction_policy == EvictionPolicy.IMPORTANCE:
            # Evict the lowest importance block
            min_block_id = min(
                self._blocks.keys(),
                key=lambda k: self._blocks[k].importance,
            )
            return self._blocks.pop(min_block_id)

        elif self._eviction_policy == EvictionPolicy.LRU_IMPORTANCE:
            # Combined score: lower importance + older access = higher eviction priority
            current_time = time.time()
            min_block_id = min(
                self._blocks.keys(),
                key=lambda k: (
                    self._blocks[k].importance * 0.5
                    + (1.0 - min((current_time - self._blocks[k].last_accessed) / 3600, 1.0)) * 0.5
                ),
            )
            block = self._blocks.pop(min_block_id)
            logger.debug(f"Core memory: LRU+importance evicted block {min_block_id}")
            return block

        return None

    def stats(self) -> Dict[str, Any]:
        """Get core memory statistics."""
        type_counts: Dict[str, int] = {}
        agent_counts: Dict[str, int] = {}
        for block in self._blocks.values():
            type_counts[block.block_type.value] = type_counts.get(block.block_type.value, 0) + 1
            agent_counts[block.source_agent] = agent_counts.get(block.source_agent, 0) + 1

        return {
            "tier": "core",
            "block_count": len(self._blocks),
            "max_blocks": self._max_blocks,
            "utilization": self.utilization,
            "total_content_chars": self.total_content_chars,
            "max_content_chars": self._max_content_chars,
            "block_types": type_counts,
            "source_agents": agent_counts,
            "eviction_policy": self._eviction_policy.value,
        }


# =============================================================================
# Archival Memory (Disk Storage)
# =============================================================================


class ArchivalMemory:
    """
    Large persistent storage for historical data and trade records.

    Analogous to disk storage. Provides unlimited capacity (backed by disk)
    with write-once semantics and versioning support.

    Features:
    - Unlimited capacity with disk backing
    - Persistent across sessions
    - Bulk import/export
    - Version tracking
    """

    def __init__(self, persist_path: Optional[str] = None) -> None:
        """
        Initialize archival memory.

        Args:
            persist_path: Directory path for persistence
        """
        self._persist_path = Path(persist_path) if persist_path else None
        self._blocks: Dict[str, MemoryBlock] = {}
        self._content_index: Dict[str, Set[str]] = {}  # word -> set of block IDs
        self._tag_index: Dict[str, Set[str]] = {}      # tag -> set of block IDs

    @property
    def size(self) -> int:
        """Number of blocks in archival memory."""
        return len(self._blocks)

    def insert(self, block: MemoryBlock) -> str:
        """
        Insert a block into archival memory.

        Args:
            block: Memory block to archive

        Returns:
            Block ID
        """
        block.tier = MemoryTier.ARCHIVAL
        self._blocks[block.id] = block

        # Update content index
        words = re.findall(r"[a-z0-9]+", block.content.lower())
        for word in set(words):
            if word not in self._content_index:
                self._content_index[word] = set()
            self._content_index[word].add(block.id)

        # Update tag index
        for tag in block.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(block.id)

        logger.debug(f"Archival memory: inserted block {block.id} (total={len(self._blocks)})")
        return block.id

    def get(self, block_id: str) -> Optional[MemoryBlock]:
        """
        Get a block by ID.

        Args:
            block_id: Block identifier

        Returns:
            Memory block if found, None otherwise
        """
        block = self._blocks.get(block_id)
        if block:
            block.touch()
        return block

    def remove(self, block_id: str) -> bool:
        """
        Remove a block from archival memory.

        Args:
            block_id: Block identifier

        Returns:
            True if removed, False if not found
        """
        block = self._blocks.pop(block_id, None)
        if block is None:
            return False

        # Clean up content index
        words = re.findall(r"[a-z0-9]+", block.content.lower())
        for word in set(words):
            if word in self._content_index:
                self._content_index[word].discard(block_id)
                if not self._content_index[word]:
                    del self._content_index[word]

        # Clean up tag index
        for tag in block.tags:
            if tag in self._tag_index:
                self._tag_index[tag].discard(block_id)
                if not self._tag_index[tag]:
                    del self._tag_index[tag]

        return True

    def search(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        block_type: Optional[BlockType] = None,
        source_agent: Optional[str] = None,
        limit: int = 20,
    ) -> List[MemoryBlock]:
        """
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
        """
        # Find candidate blocks using content index
        query_words = re.findall(r"[a-z0-9]+", query.lower())
        candidate_ids: Optional[Set[str]] = None

        for word in query_words:
            word_ids = self._content_index.get(word, set())
            if candidate_ids is None:
                candidate_ids = set(word_ids)
            else:
                candidate_ids = candidate_ids.union(word_ids)  # Union for broader recall

        if candidate_ids is None:
            # No query words found in index, try all blocks
            candidate_ids = set(self._blocks.keys())

        # Apply tag filter
        if tags:
            tag_ids: Set[str] = set()
            for tag in tags:
                tag_ids = tag_ids.union(self._tag_index.get(tag, set()))
            if tag_ids:
                candidate_ids = candidate_ids.intersection(tag_ids)

        # Score and rank candidates
        results: List[Tuple[float, MemoryBlock]] = []
        query_lower = query.lower()

        for block_id in candidate_ids:
            block = self._blocks.get(block_id)
            if block is None:
                continue

            # Filter by block type
            if block_type and block.block_type != block_type:
                continue

            # Filter by source agent
            if source_agent and block.source_agent != source_agent:
                continue

            # Score relevance
            score = 0.0
            content_lower = block.content.lower()
            for word in query_words:
                count = content_lower.count(word)
                score += count * self._idf_score(word)
            if query_lower in content_lower:
                score += 5.0  # Boost for exact phrase match

            # Boost by importance
            score *= (1.0 + block.importance)

            if score > 0:
                block.touch()
                results.append((score, block))

        # Sort by score descending
        results.sort(key=lambda x: x[0], reverse=True)
        return [block for _, block in results[:limit]]

    def bulk_insert(self, blocks: List[MemoryBlock]) -> List[str]:
        """
        Insert multiple blocks at once.

        Args:
            blocks: List of memory blocks

        Returns:
            List of inserted block IDs
        """
        ids = []
        for block in blocks:
            ids.append(self.insert(block))
        return ids

    def get_blocks_by_type(self, block_type: BlockType) -> List[MemoryBlock]:
        """Get all blocks of a specific type."""
        return [b for b in self._blocks.values() if b.block_type == block_type]

    def get_blocks_by_agent(self, source_agent: str) -> List[MemoryBlock]:
        """Get all blocks from a specific agent."""
        return [b for b in self._blocks.values() if b.source_agent == source_agent]

    def _idf_score(self, word: str) -> float:
        """Compute simple IDF score for a word."""
        doc_count = len(self._blocks)
        word_doc_count = len(self._content_index.get(word, set()))
        if doc_count == 0 or word_doc_count == 0:
            return 1.0
        return math.log((doc_count + 1) / (word_doc_count + 1)) + 1

    def save(self) -> None:
        """Persist archival memory to disk."""
        if not self._persist_path:
            return
        self._persist_path.mkdir(parents=True, exist_ok=True)
        data = {
            "blocks": {bid: block.to_dict() for bid, block in self._blocks.items()},
        }
        filepath = self._persist_path / "archival_memory.json"
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"Archival memory saved to {filepath} ({len(self._blocks)} blocks)")

    def load(self) -> bool:
        """Load archival memory from disk."""
        if not self._persist_path:
            return False
        filepath = self._persist_path / "archival_memory.json"
        if not filepath.exists():
            return False
        with open(filepath) as f:
            data = json.load(f)
        blocks_data = data.get("blocks", {})
        for bid, bdata in blocks_data.items():
            block = MemoryBlock.from_dict(bdata)
            self._blocks[bid] = block
            # Rebuild indices
            words = re.findall(r"[a-z0-9]+", block.content.lower())
            for word in set(words):
                if word not in self._content_index:
                    self._content_index[word] = set()
                self._content_index[word].add(bid)
            for tag in block.tags:
                if tag not in self._tag_index:
                    self._tag_index[tag] = set()
                self._tag_index[tag].add(bid)
        logger.info(f"Archival memory loaded: {len(self._blocks)} blocks")
        return True

    def stats(self) -> Dict[str, Any]:
        """Get archival memory statistics."""
        type_counts: Dict[str, int] = {}
        for block in self._blocks.values():
            type_counts[block.block_type.value] = type_counts.get(block.block_type.value, 0) + 1
        return {
            "tier": "archival",
            "block_count": len(self._blocks),
            "content_index_size": len(self._content_index),
            "tag_index_size": len(self._tag_index),
            "unique_tags": list(self._tag_index.keys()),
            "block_types": type_counts,
        }


# =============================================================================
# Recall Memory (Search Engine)
# =============================================================================


class RecallMemory:
    """
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
    """

    def __init__(
        self,
        archival: ArchivalMemory,
        embedding_fn: Optional[Callable[[str], List[float]]] = None,
    ) -> None:
        """
        Initialize recall memory.

        Args:
            archival: Reference to the archival memory to search
            embedding_fn: Optional function to compute text embeddings
        """
        self._archival = archival
        self._embedding_fn = embedding_fn
        self._tfidf = TfidfVectorizer()
        self._embedding_cache: Dict[str, List[float]] = {}
        self._tfidf_fitted = False

    def _ensure_tfidf_fitted(self) -> None:
        """Fit TF-IDF vectorizer on archival content if not already done."""
        if self._tfidf_fitted:
            return
        documents = [block.content for block in self._archival._blocks.values()]
        if documents:
            self._tfidf.fit(documents)
        self._tfidf_fitted = True

    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text, using embedding function or TF-IDF fallback."""
        if self._embedding_fn:
            if text not in self._embedding_cache:
                self._embedding_cache[text] = self._embedding_fn(text)
            return self._embedding_cache[text]

        # TF-IDF fallback
        self._ensure_tfidf_fitted()
        return self._tfidf.transform(text)

    def search(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        block_type: Optional[BlockType] = None,
        source_agent: Optional[str] = None,
        min_relevance: float = 0.1,
        limit: int = 10,
        use_semantic: bool = True,
    ) -> List[Tuple[MemoryBlock, float]]:
        """
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
        """
        if not self._archival._blocks:
            return []

        # Get query embedding
        query_embedding = self._get_embedding(query) if use_semantic else None

        # Score each block
        results: List[Tuple[MemoryBlock, float]] = []
        query_words = set(re.findall(r"[a-z0-9]+", query.lower()))

        for block in self._archival._blocks.values():
            # Apply filters
            if tags and not any(t in block.tags for t in tags):
                continue
            if block_type and block.block_type != block_type:
                continue
            if source_agent and block.source_agent != source_agent:
                continue

            score = 0.0

            # Semantic similarity
            if use_semantic and query_embedding:
                if block.embedding:
                    block_embedding = block.embedding
                else:
                    # Compute on-the-fly (and cache in block)
                    block_embedding = self._get_embedding(block.content)
                    block.embedding = block_embedding

                semantic_score = cosine_similarity(query_embedding, block_embedding)
                score += semantic_score * 0.6  # 60% weight for semantic

            # Keyword matching
            content_words = set(re.findall(r"[a-z0-9]+", block.content.lower()))
            if query_words:
                overlap = query_words.intersection(content_words)
                keyword_score = len(overlap) / max(len(query_words), 1)
                score += keyword_score * 0.3  # 30% weight for keyword

                # Exact phrase match boost
                if query.lower() in block.content.lower():
                    score += 0.15

            # Importance boost
            score += block.importance * 0.1  # 10% weight for importance

            if score >= min_relevance:
                block.touch()
                results.append((block, score))

        # Sort by relevance
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def recall_by_time(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        block_type: Optional[BlockType] = None,
        limit: int = 50,
    ) -> List[MemoryBlock]:
        """
        Recall memory blocks by time range.

        Args:
            start_time: Start time ISO string (inclusive)
            end_time: End time ISO string (inclusive)
            block_type: Filter by block type
            limit: Maximum results

        Returns:
            List of memory blocks within the time range
        """
        results = []
        for block in self._archival._blocks.values():
            if block_type and block.block_type != block_type:
                continue
            if start_time and block.timestamp < start_time:
                continue
            if end_time and block.timestamp > end_time:
                continue
            results.append(block)

        # Sort by timestamp descending (most recent first)
        results.sort(key=lambda b: b.timestamp, reverse=True)
        return results[:limit]

    def recall_by_agent(
        self,
        source_agent: str,
        limit: int = 50,
    ) -> List[MemoryBlock]:
        """
        Recall all memory blocks from a specific agent.

        Args:
            source_agent: Source agent name
            limit: Maximum results

        Returns:
            List of memory blocks from the agent
        """
        blocks = self._archival.get_blocks_by_agent(source_agent)
        blocks.sort(key=lambda b: b.timestamp, reverse=True)
        return blocks[:limit]

    def stats(self) -> Dict[str, Any]:
        """Get recall memory statistics."""
        return {
            "tier": "recall",
            "archival_size": self._archival.size,
            "embedding_fn_available": self._embedding_fn is not None,
            "tfidf_fitted": self._tfidf_fitted,
            "embedding_cache_size": len(self._embedding_cache),
            "tfidf_vocabulary_size": self._tfidf.vocabulary_size,
        }


# =============================================================================
# Memory Paging Controller
# =============================================================================


class MemoryPagingController:
    """
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
    """

    def __init__(
        self,
        core_max_blocks: int = 50,
        core_max_content_chars: int = 50000,
        eviction_policy: EvictionPolicy = EvictionPolicy.LRU_IMPORTANCE,
        archival_persist_path: Optional[str] = None,
        embedding_fn: Optional[Callable[[str], List[float]]] = None,
    ) -> None:
        """
        Initialize the memory paging controller.

        Args:
            core_max_blocks: Maximum blocks in core memory
            core_max_content_chars: Maximum total content chars in core
            eviction_policy: Eviction policy for core memory
            archival_persist_path: Path for archival persistence
            embedding_fn: Optional embedding function for semantic search
        """
        self._core = CoreMemory(
            max_blocks=core_max_blocks,
            max_content_chars=core_max_content_chars,
            eviction_policy=eviction_policy,
        )
        self._archival = ArchivalMemory(persist_path=archival_persist_path)
        self._recall = RecallMemory(
            archival=self._archival,
            embedding_fn=embedding_fn,
        )
        self._block_counter: int = 0
        self._page_in_count: int = 0
        self._page_out_count: int = 0

    @property
    def core(self) -> CoreMemory:
        """Access core memory directly."""
        return self._core

    @property
    def archival(self) -> ArchivalMemory:
        """Access archival memory directly."""
        return self._archival

    @property
    def recall(self) -> RecallMemory:
        """Access recall memory directly."""
        return self._recall

    def _generate_block_id(self) -> str:
        """Generate a unique block ID."""
        self._block_counter += 1
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"MB-{ts}-{self._block_counter:06d}"

    def core_insert(
        self,
        content: str,
        block_type: BlockType = BlockType.THOUGHT,
        importance: float = 0.5,
        source_agent: str = "",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryBlock:
        """
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
        """
        block = MemoryBlock(
            id=self._generate_block_id(),
            content=content,
            tier=MemoryTier.CORE,
            block_type=block_type,
            importance=importance,
            source_agent=source_agent,
            tags=tags or [],
            metadata=metadata or {},
        )

        # Insert into core; auto-page-out evicted blocks
        evicted = self._core.insert(block)
        if evicted is not None:
            self._archival.insert(evicted)
            self._page_out_count += 1
            logger.info(
                f"Auto page-out: {evicted.id} -> archival "
                f"(type={evicted.block_type.value}, agent={evicted.source_agent})"
            )

        return block

    def core_get(self, block_id: str) -> Optional[MemoryBlock]:
        """Get a block from core memory by ID."""
        return self._core.get(block_id)

    def page_in(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        block_type: Optional[BlockType] = None,
        source_agent: Optional[str] = None,
        limit: int = 5,
    ) -> List[MemoryBlock]:
        """
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
        """
        results = self._recall.search(
            query=query,
            tags=tags,
            block_type=block_type,
            source_agent=source_agent,
            limit=limit,
        )

        paged_in = []
        for block, score in results:
            # Skip if already in core memory
            if self._core.get(block.id) is not None:
                continue

            # Remove from archival and insert into core
            self._archival.remove(block.id)
            evicted = self._core.insert(block)
            if evicted is not None:
                self._archival.insert(evicted)
                self._page_out_count += 1
                logger.info(f"Page-out during page-in: {evicted.id} -> archival")

            self._page_in_count += 1
            paged_in.append(block)
            logger.info(
                f"Page-in: {block.id} -> core "
                f"(score={score:.3f}, type={block.block_type.value})"
            )

        return paged_in

    def page_out(
        self,
        block_ids: Optional[List[str]] = None,
        count: Optional[int] = None,
    ) -> List[MemoryBlock]:
        """
        Page out blocks from core to archival memory.

        Can either page out specific blocks by ID, or page out
        a number of least-priority blocks.

        Args:
            block_ids: Specific block IDs to page out (takes priority)
            count: Number of least-priority blocks to page out

        Returns:
            List of blocks that were paged out
        """
        paged_out = []

        if block_ids:
            for block_id in block_ids:
                block = self._core.remove(block_id)
                if block:
                    self._archival.insert(block)
                    self._page_out_count += 1
                    paged_out.append(block)
                    logger.info(f"Page-out: {block_id} -> archival")

        elif count:
            for _ in range(min(count, self._core.size)):
                # Evict the least priority block
                block = self._core._evict()
                if block:
                    self._archival.insert(block)
                    self._page_out_count += 1
                    paged_out.append(block)
                    logger.info(f"Page-out: {block.id} -> archival")

        return paged_out

    def archive_block(
        self,
        content: str,
        block_type: BlockType = BlockType.KNOWLEDGE,
        importance: float = 0.3,
        source_agent: str = "",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryBlock:
        """
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
        """
        block = MemoryBlock(
            id=self._generate_block_id(),
            content=content,
            tier=MemoryTier.ARCHIVAL,
            block_type=block_type,
            importance=importance,
            source_agent=source_agent,
            tags=tags or [],
            metadata=metadata or {},
        )
        self._archival.insert(block)
        return block

    def search(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        block_type: Optional[BlockType] = None,
        source_agent: Optional[str] = None,
        limit: int = 10,
    ) -> List[Tuple[MemoryBlock, float]]:
        """
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
        """
        results: List[Tuple[MemoryBlock, float]] = []

        # Search core memory
        core_results = self._core.search(
            query=query,
            tags=tags,
            block_type=block_type,
            source_agent=source_agent,
            limit=limit,
        )
        query_lower = query.lower()
        for block in core_results:
            # Simple relevance scoring for core results
            score = 1.0  # Core results start with high base score
            if query_lower in block.content.lower():
                score += 0.5
            score *= (1.0 + block.importance * 0.5)
            results.append((block, score))

        # Search archival memory via recall
        archival_results = self._recall.search(
            query=query,
            tags=tags,
            block_type=block_type,
            source_agent=source_agent,
            limit=limit * 2,  # Fetch more for dedup
        )
        for block, score in archival_results:
            # Dedup against core results
            if any(r[0].id == block.id for r in results):
                continue
            results.append((block, score))

        # Sort by relevance and return
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def save(self) -> None:
        """Save all persistent memory tiers to disk."""
        self._archival.save()

    def load(self) -> bool:
        """Load persistent memory tiers from disk."""
        return self._archival.load()

    def stats(self) -> Dict[str, Any]:
        """Get comprehensive memory system statistics."""
        return {
            "core": self._core.stats(),
            "archival": self._archival.stats(),
            "recall": self._recall.stats(),
            "page_operations": {
                "page_in_count": self._page_in_count,
                "page_out_count": self._page_out_count,
                "total_blocks_created": self._block_counter,
            },
        }

    def clear_all(self) -> None:
        """Clear all memory tiers."""
        self._core.clear()
        self._archival._blocks.clear()
        self._archival._content_index.clear()
        self._archival._tag_index.clear()
        self._block_counter = 0
        self._page_in_count = 0
        self._page_out_count = 0
