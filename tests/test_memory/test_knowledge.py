"""Comprehensive tests for Knowledge Base module.

Tests:
- Adding entries with all fields
- Search with query, category, and tags
- Getting entries by ID and category
- Updating entries
- Deleting entries
- Statistics
- Persistence (save/load)
"""

from __future__ import annotations

import os
import tempfile
import pytest

from quant_nanggroe.memory.knowledge import KnowledgeBase


@pytest.fixture
def kb():
    """Fresh KnowledgeBase instance."""
    return KnowledgeBase()


@pytest.fixture
def kb_with_entries(kb):
    """KnowledgeBase with pre-populated entries."""
    kb.add(
        category="market_regime",
        title="BTC Halving Cycle",
        content="Post-halving supply shock typically takes 6-12 months to materialize",
        tags=["btc", "halving", "cycle"],
        source="historical_analysis",
        confidence=0.8,
    )
    kb.add(
        category="strategy",
        title="Momentum Strategy",
        content="Trend following works best in trending markets with low volatility",
        tags=["momentum", "trend", "strategy"],
        source="backtesting",
        confidence=0.7,
    )
    kb.add(
        category="market_regime",
        title="Fed Rate Impact",
        content="Rate hikes typically suppress risk assets for 3-6 months",
        tags=["fed", "rates", "macro"],
        source="research",
        confidence=0.6,
    )
    return kb


@pytest.fixture
def persist_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestAddEntry:
    def test_returns_entry_id(self, kb):
        entry_id = kb.add(category="test", title="Test", content="Content")
        assert isinstance(entry_id, int)
        assert entry_id == 1

    def test_sequential_ids(self, kb):
        id1 = kb.add(category="test", title="T1", content="C1")
        id2 = kb.add(category="test", title="T2", content="C2")
        assert id2 == id1 + 1

    def test_entry_stored_correctly(self, kb):
        kb.add(
            category="market_regime",
            title="BTC Halving",
            content="Supply shock impact",
            tags=["btc", "halving"],
            source="research",
            confidence=0.9,
        )
        entry = kb.get(1)
        assert entry is not None
        assert entry["category"] == "market_regime"
        assert entry["title"] == "BTC Halving"
        assert entry["content"] == "Supply shock impact"
        assert entry["tags"] == ["btc", "halving"]
        assert entry["source"] == "research"
        assert entry["confidence"] == 0.9

    def test_default_values(self, kb):
        kb.add(category="test", title="Test", content="Content")
        entry = kb.get(1)
        assert entry["tags"] == []
        assert entry["source"] is None
        assert entry["confidence"] == 1.0
        assert entry["metadata"] == {}

    def test_with_metadata(self, kb):
        kb.add(
            category="test", title="Test", content="Content",
            metadata={"author": "AI", "version": 1},
        )
        entry = kb.get(1)
        assert entry["metadata"]["author"] == "AI"

    def test_timestamps_set(self, kb):
        kb.add(category="test", title="Test", content="Content")
        entry = kb.get(1)
        assert entry["created_at"] is not None
        assert entry["updated_at"] is not None


class TestSearch:
    def test_search_by_query_in_title(self, kb_with_entries):
        results = kb_with_entries.search("Halving")
        assert len(results) >= 1
        assert any(r["title"] == "BTC Halving Cycle" for r in results)

    def test_search_by_query_in_content(self, kb_with_entries):
        results = kb_with_entries.search("supply shock")
        assert len(results) >= 1

    def test_search_by_category(self, kb_with_entries):
        results = kb_with_entries.search("", category="market_regime")
        assert len(results) == 2

    def test_search_by_tags(self, kb_with_entries):
        results = kb_with_entries.search("", tags=["btc"])
        assert len(results) >= 1

    def test_search_relevance_scoring(self, kb_with_entries):
        results = kb_with_entries.search("halving")
        # Title match should score higher than content-only match
        assert results[0]["relevance_score"] >= 2.0  # Title match = 2.0

    def test_search_sorted_by_relevance(self, kb_with_entries):
        kb_with_entries.add(
            category="test",
            title="Halving Direct",
            content="This is about halving halving halving",
            tags=["halving"],
        )
        results = kb_with_entries.search("halving")
        scores = [r["relevance_score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_search_no_results(self, kb_with_entries):
        results = kb_with_entries.search("nonexistent_topic_xyz")
        assert len(results) == 0

    def test_search_limit(self, kb_with_entries):
        # Add many entries
        for i in range(20):
            kb_with_entries.add(category="test", title=f"Test {i}", content="Content")
        results = kb_with_entries.search("Test", limit=5)
        assert len(results) <= 5

    def test_search_case_insensitive(self, kb_with_entries):
        results = kb_with_entries.search("halving")
        assert len(results) >= 1

    def test_tag_match_scores(self, kb_with_entries):
        results = kb_with_entries.search("", tags=["btc"])
        assert len(results) >= 1

    def test_combined_category_and_tags(self, kb_with_entries):
        results = kb_with_entries.search("", category="market_regime", tags=["btc"])
        assert len(results) >= 1


class TestGetEntry:
    def test_get_existing_entry(self, kb_with_entries):
        entry = kb_with_entries.get(1)
        assert entry is not None

    def test_get_nonexistent_entry(self, kb):
        entry = kb.get(999)
        assert entry is None

    def test_get_by_category(self, kb_with_entries):
        entries = kb_with_entries.get_by_category("market_regime")
        assert len(entries) == 2
        assert all(e["category"] == "market_regime" for e in entries)


class TestUpdateEntry:
    def test_update_content(self, kb_with_entries):
        kb_with_entries.update(1, content="Updated content")
        entry = kb_with_entries.get(1)
        assert entry["content"] == "Updated content"

    def test_update_tags(self, kb_with_entries):
        kb_with_entries.update(1, tags=["new_tag", "another_tag"])
        entry = kb_with_entries.get(1)
        assert entry["tags"] == ["new_tag", "another_tag"]

    def test_update_nonexistent(self, kb):
        result = kb.update(999, content="Test")
        assert result is False

    def test_updated_at_changes(self, kb_with_entries):
        import time
        entry_before = kb_with_entries.get(1)
        time.sleep(0.01)
        kb_with_entries.update(1, content="New content")
        entry_after = kb_with_entries.get(1)
        assert entry_after["updated_at"] >= entry_before["updated_at"]


class TestDeleteEntry:
    def test_delete_existing(self, kb_with_entries):
        result = kb_with_entries.delete(1)
        assert result is True
        assert kb_with_entries.get(1) is None

    def test_delete_nonexistent(self, kb):
        result = kb.delete(999)
        assert result is True  # Delete always returns True in this impl


class TestGetCategories:
    def test_get_categories(self, kb_with_entries):
        categories = kb_with_entries.get_categories()
        assert "market_regime" in categories
        assert "strategy" in categories

    def test_get_categories_empty(self, kb):
        categories = kb.get_categories()
        assert len(categories) == 0


class TestGetStats:
    def test_stats_with_entries(self, kb_with_entries):
        stats = kb_with_entries.get_stats()
        assert stats["total_entries"] == 3
        assert "market_regime" in stats["categories"]
        assert stats["categories"]["market_regime"] == 2

    def test_stats_empty(self, kb):
        stats = kb.get_stats()
        assert stats["total_entries"] == 0
        assert stats["categories"] == {}


class TestKnowledgeBasePersistence:
    def test_save_and_load(self, persist_dir):
        path = os.path.join(persist_dir, "kb.json")
        kb1 = KnowledgeBase(persist_path=path)
        kb1.add(category="test", title="Test", content="Content")
        kb1.save()

        kb2 = KnowledgeBase(persist_path=path)
        assert kb2.load() is True
        assert kb2.get_stats()["total_entries"] == 1

    def test_load_preserves_id_counter(self, persist_dir):
        path = os.path.join(persist_dir, "kb.json")
        kb1 = KnowledgeBase(persist_path=path)
        kb1.add(category="test", title="T1", content="C1")
        kb1.add(category="test", title="T2", content="C2")
        kb1.save()

        kb2 = KnowledgeBase(persist_path=path)
        kb2.load()
        new_id = kb2.add(category="test", title="T3", content="C3")
        assert new_id == 3

    def test_save_creates_directory(self, persist_dir):
        path = os.path.join(persist_dir, "subdir", "kb.json")
        kb = KnowledgeBase(persist_path=path)
        kb.add(category="test", title="Test", content="Content")
        kb.save()
        assert os.path.exists(path)

    def test_load_nonexistent(self):
        kb = KnowledgeBase(persist_path="/tmp/nonexistent_kb.json")
        assert kb.load() is False

    def test_save_without_path(self):
        kb = KnowledgeBase()
        kb.add(category="test", title="Test", content="Content")
        kb.save()  # Should not raise

    def test_load_without_path(self):
        kb = KnowledgeBase()
        assert kb.load() is False
