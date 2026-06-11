"""
Knowledge & Memory Package — Persistent Storage & Retrieval
============================================================
Vector store, conversation tracking, research memory, paging system,
knowledge graph, trade journal, and session memory modules.

Exports:
    VectorMemory         — In-memory vector store with TF-IDF embeddings
    ConversationMemory   — Multi-turn conversation tracking per session
    ResearchMemory       — Research result caching with TTL
    CompressibleMemory   — Token-aware message compression
    MemoryPagingController — Letta-style three-tier memory (core/archival/recall)
    KnowledgeGraph       — Domain-specific trading knowledge graph
    KnowledgeBase        — Persistent knowledge storage with search
    TradeJournal         — Trade decision recording and analysis
    SessionMemory        — Agent session context preservation
"""

from quant_nanggroe_ai.memory.vector import VectorMemory, VectorDocument
from quant_nanggroe_ai.memory.conversation import (
    ConversationMemory,
    ConversationMessage,
)
from quant_nanggroe_ai.memory.research import ResearchMemory, ResearchEntry

# CompressibleMemory — adapted from agenticSeek (C2-SUPPORT, Task 9)
from quant_nanggroe_ai.memory.compression import (
    CompressibleMemory,
    MessageRole as CompressionMessageRole,
    CompressionStrategy,
    ConversationMessage as CompressionConversationMessage,
)

# New modules from quant_nanggroe package
from quant_nanggroe_ai.memory.paging import (
    MemoryPagingController,
    CoreMemory,
    ArchivalMemory,
    RecallMemory,
    MemoryBlock,
    MemoryTier,
    BlockType,
    EvictionPolicy,
)
from quant_nanggroe_ai.memory.knowledge_graph import KnowledgeGraph, Entity, Relationship, EntityType, RelationType
from quant_nanggroe_ai.memory.knowledge import KnowledgeBase
from quant_nanggroe_ai.memory.journal import TradeJournal
from quant_nanggroe_ai.memory.session import SessionMemory

__all__ = [
    "VectorMemory",
    "VectorDocument",
    "ConversationMemory",
    "ConversationMessage",
    "ResearchMemory",
    "ResearchEntry",
    "CompressibleMemory",
    "CompressionMessageRole",
    "CompressionStrategy",
    "CompressionConversationMessage",
    # Paging system
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
    # Knowledge base
    "KnowledgeBase",
    # Journal
    "TradeJournal",
    # Session
    "SessionMemory",
]
