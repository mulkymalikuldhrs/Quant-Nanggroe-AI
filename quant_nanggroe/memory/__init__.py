"""Memory and knowledge persistence for Quant Nanggroe AI.

Provides session memory, trade journal, knowledge base,
Letta-style memory paging, knowledge graph for agents,
and vector storage for semantic search across trading history.
"""

from quant_nanggroe.memory.session import SessionMemory
from quant_nanggroe.memory.journal import TradeJournal
from quant_nanggroe.memory.knowledge import KnowledgeBase
from quant_nanggroe.memory.paging import (
    MemoryPagingController,
    CoreMemory,
    ArchivalMemory,
    RecallMemory,
    MemoryBlock,
    MemoryTier,
    BlockType,
    EvictionPolicy,
)
from quant_nanggroe.memory.knowledge_graph import (
    KnowledgeGraph,
    Entity,
    Relationship,
    EntityType,
    RelationType,
)
from quant_nanggroe.memory.vector import (
    VectorStore,
    CollectionName,
    EmbeddingProvider,
    VectorDocument,
    SearchResult,
    VectorStoreStats,
    get_vector_store,
)

# Seulanga RAG bridge — standalone degradable
try:
    from quant_nanggroe.memory.seulanga_bridge import seulanga_learn, seulanga_search
    HAS_SEULANGA = True
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("Seulanga RAG bridge unavailable (missing httpx)")
    HAS_SEULANGA = False

    async def seulanga_learn(content: str, source: str = "qna", tags: list = None) -> dict:
        return {"error": "Seulanga bridge unavailable"}

    async def seulanga_search(query: str, limit: int = 5) -> dict:
        return {"error": "Seulanga bridge unavailable"}

__all__ = [
    # Legacy memory
    "SessionMemory",
    "TradeJournal",
    "KnowledgeBase",
    # Letta-style memory paging
    "MemoryPagingController",
    "CoreMemory",
    "ArchivalMemory",
    "RecallMemory",
    "MemoryBlock",
    "MemoryTier",
    "BlockType",
    "EvictionPolicy",
    # Knowledge graph
    "KnowledgeGraph",
    "Entity",
    "Relationship",
    "EntityType",
    "RelationType",
    # Vector store (ChromaDB)
    "VectorStore",
    "CollectionName",
    "EmbeddingProvider",
    "VectorDocument",
    "SearchResult",
    "VectorStoreStats",
    "get_vector_store",
    # Seulanga RAG bridge
    "seulanga_learn",
    "seulanga_search",
    "HAS_SEULANGA",
]
