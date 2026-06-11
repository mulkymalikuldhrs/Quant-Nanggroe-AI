"""Memory system for AI-MultiColony.

Provides the unified memory gateway (MemoryManager), Letta-style paging
(LettaStylePaging), vector store (VectorStore), eight condenser types,
knowledge base (KnowledgeBase), temporal knowledge graph
(TemporalKnowledgeGraph), and session memory (SessionMemory).
"""

from .manager import MemoryManager, MemoryTier
from .paging import LettaStylePaging, PagingManager, MemoryPage, WorkingSetEntry
from .vector import VectorStore, VectorDocument, QueryResult, CollectionInfo
from .condensers import (
    BaseCondenser,
    SummaryCondenser,
    KeyFactCondenser,
    TemporalCondenser,
    RelevanceCondenser,
    RedundancyCondenser,
    ProceduralCondenser,
    RelationalCondenser,
    HybridCondenser,
    # Backward-compat aliases
    ExtractionCondenser,
    RollupCondenser,
    PriorityCondenser,
    DeduplicationCondenser,
    SlidingWindowCondenser,
    HierarchicalCondenser,
    CONDENSERS,
)
from .knowledge import KnowledgeBase, Fact, Document, Chunk
from .knowledge_graph import TemporalKnowledgeGraph, Triple, Entity, EvolutionEntry
from .session import SessionMemory, Session, Message, CompactionResult

__all__ = [
    # Manager
    "MemoryManager",
    "MemoryTier",
    # Paging
    "LettaStylePaging",
    "PagingManager",
    "MemoryPage",
    "WorkingSetEntry",
    # Vector
    "VectorStore",
    "VectorDocument",
    "QueryResult",
    "CollectionInfo",
    # Condensers
    "BaseCondenser",
    "SummaryCondenser",
    "KeyFactCondenser",
    "TemporalCondenser",
    "RelevanceCondenser",
    "RedundancyCondenser",
    "ProceduralCondenser",
    "RelationalCondenser",
    "HybridCondenser",
    "ExtractionCondenser",
    "RollupCondenser",
    "PriorityCondenser",
    "DeduplicationCondenser",
    "SlidingWindowCondenser",
    "HierarchicalCondenser",
    "CONDENSERS",
    # Knowledge
    "KnowledgeBase",
    "Fact",
    "Document",
    "Chunk",
    # Knowledge Graph
    "TemporalKnowledgeGraph",
    "Triple",
    "Entity",
    "EvolutionEntry",
    # Session
    "SessionMemory",
    "Session",
    "Message",
    "CompactionResult",
]
