"""
Knowledge & Memory Package — Persistent Storage & Retrieval
============================================================
Vector store, conversation tracking, and research memory modules.

Exports:
    VectorMemory         — In-memory vector store with TF-IDF embeddings
    ConversationMemory   — Multi-turn conversation tracking per session
    ResearchMemory       — Research result caching with TTL

Usage:
    from quant_nanggroe_ai.memory import VectorMemory, ConversationMemory, ResearchMemory

    vec = VectorMemory()
    vec.add_documents([{"text": "AAPL earnings beat", "metadata": {"symbol": "AAPL"}}])
    results = vec.similarity_search("earnings report", k=5)
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
]
