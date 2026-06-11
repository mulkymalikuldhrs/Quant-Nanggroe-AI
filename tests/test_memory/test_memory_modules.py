"""Tests for Memory module — paging, knowledge graph, journal, session."""

import pytest


class TestMemoryPagingController:
    """Tests for Memory Paging system."""

    def test_import(self):
        from quant_nanggroe_ai.memory.paging import MemoryPagingController
        assert MemoryPagingController is not None

    def test_creation(self):
        from quant_nanggroe_ai.memory.paging import MemoryPagingController
        paging = MemoryPagingController()
        assert paging is not None


class TestMemoryBlock:
    """Tests for MemoryBlock."""

    def test_import(self):
        from quant_nanggroe_ai.memory.paging import MemoryBlock
        assert MemoryBlock is not None


class TestMemoryTier:
    """Tests for MemoryTier enum."""

    def test_import(self):
        from quant_nanggroe_ai.memory.paging import MemoryTier
        assert MemoryTier is not None

    def test_tiers(self):
        from quant_nanggroe_ai.memory.paging import MemoryTier
        for tier in MemoryTier:
            assert tier is not None


class TestKnowledgeGraph:
    """Tests for Knowledge Graph memory."""

    def test_import(self):
        from quant_nanggroe_ai.memory.knowledge_graph import KnowledgeGraph
        assert KnowledgeGraph is not None

    def test_creation(self):
        from quant_nanggroe_ai.memory.knowledge_graph import KnowledgeGraph
        kg = KnowledgeGraph()
        assert kg is not None


class TestTradeJournal:
    """Tests for Trade Journal."""

    def test_import(self):
        from quant_nanggroe_ai.memory.journal import TradeJournal
        assert TradeJournal is not None

    def test_creation(self):
        from quant_nanggroe_ai.memory.journal import TradeJournal
        journal = TradeJournal()
        assert journal is not None


class TestSessionMemory:
    """Tests for Session Memory."""

    def test_import(self):
        from quant_nanggroe_ai.memory.session import SessionMemory
        assert SessionMemory is not None

    def test_creation(self):
        from quant_nanggroe_ai.memory.session import SessionMemory
        session = SessionMemory()
        assert session is not None


class TestMemoryInit:
    """Tests for memory package __init__."""

    def test_package_import(self):
        import quant_nanggroe_ai.memory
        assert quant_nanggroe_ai.memory is not None
