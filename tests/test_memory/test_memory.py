"""Tests for memory system."""
import pytest
import asyncio
from ai_multicolony.memory.manager import MemoryManager
from ai_multicolony.memory.paging import LettaStylePaging
from ai_multicolony.memory.vector import VectorStore
from ai_multicolony.memory.condensers import SummaryCondenser, KeyFactCondenser, HybridCondenser
from ai_multicolony.memory.knowledge import KnowledgeBase
from ai_multicolony.memory.knowledge_graph import TemporalKnowledgeGraph
from ai_multicolony.memory.session import SessionMemory

class TestMemoryManager:
    def test_create(self): assert MemoryManager() is not None

class TestPaging:
    def test_create(self):
        p = LettaStylePaging()
        assert p is not None

class TestVectorStore:
    def test_create(self): assert VectorStore() is not None
    def test_collections(self):
        v = VectorStore()
        collections = v.list_collections()
        assert isinstance(collections, (list, set))

class TestCondensers:
    def test_summary(self):
        c = SummaryCondenser()
        result = c.condense([{"content": "Hello world"}, {"content": "Test content"}])
        assert isinstance(result, dict)
    def test_key_fact(self):
        c = KeyFactCondenser()
        result = c.condense([{"content": "Price is $100"}, {"content": "Date is 2025-01-01"}])
        assert isinstance(result, dict)
    def test_hybrid(self):
        c = HybridCondenser(condensers=[SummaryCondenser()])
        result = c.condense([{"content": "Test content"}])
        assert isinstance(result, dict)

class TestKnowledgeBase:
    def test_create(self): assert KnowledgeBase() is not None
    @pytest.mark.asyncio
    async def test_add_fact(self):
        k = KnowledgeBase()
        fact = await k.add_fact(content="Python is a programming language", category="tech", confidence=0.99)
        assert fact is not None
    @pytest.mark.asyncio
    async def test_fact_count(self):
        k = KnowledgeBase()
        await k.add_fact(content="Test fact", category="general")
        count = k.fact_count()
        assert count >= 1

class TestTemporalKnowledgeGraph:
    def test_create(self): assert TemporalKnowledgeGraph() is not None
    @pytest.mark.asyncio
    async def test_add_triple(self):
        t = TemporalKnowledgeGraph()
        triple = await t.add_triple(subject="PR42", predicate="has_status", object="open", valid_from="2025-01-01")
        assert triple is not None
    @pytest.mark.asyncio
    async def test_triple_count(self):
        t = TemporalKnowledgeGraph()
        await t.add_triple(subject="X", predicate="status", object="open", valid_from="2025-01-01")
        count = t.triple_count()
        assert count >= 1

class TestSessionMemory:
    def test_create(self):
        s = SessionMemory(context_window_tokens=4096, compaction_threshold=0.8)
        assert s is not None
