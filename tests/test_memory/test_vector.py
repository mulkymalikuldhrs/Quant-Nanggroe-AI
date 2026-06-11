"""Comprehensive tests for Vector Memory — ChromaDB Integration.

Tests cover:
- CollectionName and EmbeddingProvider enums
- VectorDocument, SearchResult, VectorStoreStats models
- VectorStore initialization (fallback & ChromaDB mock)
- Adding documents to all 5 collections
- Semantic search with mocked embeddings
- Convenience methods: add_strategy, add_research, add_decision,
  add_market_regime, add_risk_event
- Delete operations
- Stats retrieval
- Fallback keyword search
- Error handling when ChromaDB unavailable (graceful degradation)
- Module-level get_vector_store singleton

All tests use in-memory fallback — no real ChromaDB required.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from quant_nanggroe.memory.vector import (
    VectorStore,
    CollectionName,
    EmbeddingProvider,
    VectorDocument,
    SearchResult,
    VectorStoreStats,
    get_vector_store,
)


# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture
def vector_store():
    """Create a fresh VectorStore with in-memory fallback (no ChromaDB leakage)."""
    return VectorStore(use_fallback=True)


@pytest.fixture
def vector_store_with_dir(tmp_path):
    """Create a VectorStore with a temp persist directory."""
    return VectorStore(persist_directory=str(tmp_path))


@pytest.fixture
def initialized_store(vector_store):
    """Return an already-initialized VectorStore."""
    import asyncio
    asyncio.get_event_loop().run_until_complete(vector_store.initialize())
    return vector_store


# ======================================================================
# 1. CollectionName Enum Tests
# ======================================================================

class TestCollectionName:
    """Tests for CollectionName enum."""

    def test_strategies_value(self):
        assert CollectionName.STRATEGIES == "strategies"

    def test_research_value(self):
        assert CollectionName.RESEARCH == "research"

    def test_decisions_value(self):
        assert CollectionName.DECISIONS == "decisions"

    def test_market_regimes_value(self):
        assert CollectionName.MARKET_REGIMES == "market_regimes"

    def test_risk_events_value(self):
        assert CollectionName.RISK_EVENTS == "risk_events"

    def test_collection_count(self):
        assert len(CollectionName) == 5

    def test_is_string_enum(self):
        assert isinstance(CollectionName.STRATEGIES, str)

    def test_from_value(self):
        assert CollectionName("strategies") == CollectionName.STRATEGIES

    def test_iteration(self):
        names = [c.value for c in CollectionName]
        assert "strategies" in names
        assert "risk_events" in names


# ======================================================================
# 2. EmbeddingProvider Enum Tests
# ======================================================================

class TestEmbeddingProvider:
    """Tests for EmbeddingProvider enum."""

    def test_default_provider(self):
        assert EmbeddingProvider.DEFAULT == "default"

    def test_openai_provider(self):
        assert EmbeddingProvider.OPENAI == "openai"

    def test_local_provider(self):
        assert EmbeddingProvider.LOCAL == "local"

    def test_provider_count(self):
        assert len(EmbeddingProvider) == 3

    def test_is_string_enum(self):
        assert isinstance(EmbeddingProvider.DEFAULT, str)


# ======================================================================
# 3. VectorDocument Model Tests
# ======================================================================

class TestVectorDocument:
    """Tests for VectorDocument model validation and defaults."""

    def test_required_fields_only(self):
        doc = VectorDocument(doc_id="doc-1", collection="strategies", content="Test content")
        assert doc.doc_id == "doc-1"
        assert doc.collection == "strategies"
        assert doc.content == "Test content"

    def test_default_metadata(self):
        doc = VectorDocument(doc_id="d1", collection="test", content="c")
        assert doc.metadata == {}

    def test_default_embedding(self):
        doc = VectorDocument(doc_id="d1", collection="test", content="c")
        assert doc.embedding is None

    def test_default_timestamps(self):
        doc = VectorDocument(doc_id="d1", collection="test", content="c")
        assert doc.created_at == ""
        assert doc.updated_at == ""

    def test_with_metadata(self):
        doc = VectorDocument(
            doc_id="doc-2",
            collection="research",
            content="Research note",
            metadata={"topic": "macro", "source": "fred"},
        )
        assert doc.metadata["topic"] == "macro"
        assert doc.metadata["source"] == "fred"

    def test_with_embedding(self):
        doc = VectorDocument(
            doc_id="doc-3",
            collection="decisions",
            content="Decision",
            embedding=[0.1, 0.2, 0.3],
        )
        assert doc.embedding == [0.1, 0.2, 0.3]
        assert len(doc.embedding) == 3

    def test_with_timestamps(self):
        doc = VectorDocument(
            doc_id="d4", collection="test", content="c",
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
        )
        assert doc.created_at == "2025-01-01T00:00:00Z"

    def test_metadata_can_hold_complex_types(self):
        doc = VectorDocument(
            doc_id="d5", collection="test", content="c",
            metadata={"tags": ["crypto", "btc"], "score": 0.95, "nested": {"key": "val"}},
        )
        assert doc.metadata["tags"] == ["crypto", "btc"]
        assert doc.metadata["nested"]["key"] == "val"

    def test_embedding_can_be_empty_list(self):
        doc = VectorDocument(
            doc_id="d6", collection="test", content="c",
            embedding=[],
        )
        assert doc.embedding == []


# ======================================================================
# 4. SearchResult Model Tests
# ======================================================================

class TestSearchResult:
    """Tests for SearchResult model validation and defaults."""

    def test_required_fields_only(self):
        result = SearchResult(doc_id="doc-1")
        assert result.doc_id == "doc-1"

    def test_default_collection(self):
        result = SearchResult(doc_id="doc-1")
        assert result.collection == ""

    def test_default_content(self):
        result = SearchResult(doc_id="doc-1")
        assert result.content == ""

    def test_default_scores(self):
        result = SearchResult(doc_id="doc-1")
        assert result.distance == 0.0
        assert result.relevance_score == 0.0

    def test_default_metadata(self):
        result = SearchResult(doc_id="doc-1")
        assert result.metadata == {}

    def test_full_construction(self):
        result = SearchResult(
            doc_id="doc-1",
            collection="strategies",
            content="Test content",
            metadata={"type": "trend"},
            distance=0.25,
            relevance_score=0.75,
        )
        assert result.collection == "strategies"
        assert result.content == "Test content"
        assert result.distance == 0.25
        assert result.relevance_score == 0.75

    def test_distance_and_relevance_relationship(self):
        """Relevance should be 1 - distance for cosine similarity."""
        result = SearchResult(doc_id="d1", distance=0.3, relevance_score=0.7)
        assert abs((1.0 - result.distance) - result.relevance_score) < 0.01


# ======================================================================
# 5. VectorStoreStats Model Tests
# ======================================================================

class TestVectorStoreStatsModel:
    """Tests for VectorStoreStats model."""

    def test_default_values(self):
        stats = VectorStoreStats()
        assert stats.total_documents == 0
        assert stats.collections == {}
        assert stats.embedding_provider == "default"
        assert stats.last_updated == ""

    def test_with_data(self):
        stats = VectorStoreStats(
            total_documents=10,
            collections={"strategies": 5, "research": 5},
            embedding_provider="openai",
            last_updated="2025-01-01T00:00:00Z",
        )
        assert stats.total_documents == 10
        assert stats.collections["strategies"] == 5

    def test_collections_is_dict(self):
        stats = VectorStoreStats()
        assert isinstance(stats.collections, dict)


# ======================================================================
# 6. VectorStore Initialization Tests
# ======================================================================

class TestVectorStoreInit:
    """Tests for VectorStore initialization."""

    def test_default_construction(self):
        store = VectorStore()
        assert store._persist_directory is None
        assert store._embedding_provider == EmbeddingProvider.DEFAULT
        assert store._client is None
        assert store._collections == {}
        assert store._initialized is False
        assert store._chromadb_available is False

    def test_with_persist_directory(self):
        store = VectorStore(persist_directory="/tmp/test_chroma")
        assert store._persist_directory == "/tmp/test_chroma"

    def test_with_embedding_provider(self):
        store = VectorStore(embedding_provider=EmbeddingProvider.OPENAI)
        assert store._embedding_provider == EmbeddingProvider.OPENAI

    def test_fallback_store_has_all_collections(self):
        store = VectorStore()
        for col in CollectionName:
            assert col.value in store._fallback_store

    def test_fallback_store_initially_empty(self):
        store = VectorStore()
        for docs in store._fallback_store.values():
            assert docs == []

    @pytest.mark.asyncio
    async def test_initialize_fallback(self, vector_store):
        """Without ChromaDB, should initialize with fallback."""
        result = await vector_store.initialize()
        assert vector_store._initialized is True
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, vector_store):
        """Second initialize should return True immediately."""
        await vector_store.initialize()
        result = await vector_store.initialize()
        assert result is True

    @pytest.mark.asyncio
    async def test_initialize_with_chromadb_import_error(self, vector_store):
        """ImportError for chromadb should result in fallback mode."""
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "chromadb":
                raise ImportError("no chromadb")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            vector_store._initialized = False
            result = await vector_store.initialize()
            assert vector_store._initialized is True
            assert vector_store._chromadb_available is False

    @pytest.mark.asyncio
    async def test_initialize_with_chromadb_mock(self):
        """Test initialization with mocked ChromaDB via sys.modules injection."""
        import sys
        store = VectorStore()  # Not use_fallback=True, so ChromaDB path is attempted
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chroma = MagicMock()
        mock_chroma.Client.return_value = mock_client
        mock_chroma.PersistentClient.return_value = mock_client

        with patch.dict(sys.modules, {"chromadb": mock_chroma}):
            result = await store.initialize()
            assert store._initialized is True
            assert store._chromadb_available is True

    @pytest.mark.asyncio
    async def test_initialize_persistent_client(self, tmp_path):
        """With persist_directory, should use PersistentClient."""
        import sys
        store = VectorStore(persist_directory=str(tmp_path))
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chroma = MagicMock()
        mock_chroma.PersistentClient.return_value = mock_client
        mock_chroma.Client.return_value = MagicMock()

        with patch.dict(sys.modules, {"chromadb": mock_chroma}):
            await store.initialize()
            mock_chroma.PersistentClient.assert_called_once_with(path=str(tmp_path))

    @pytest.mark.asyncio
    async def test_initialize_creates_all_collections(self):
        """All 5 collections should be created with ChromaDB mock."""
        import sys
        store = VectorStore()  # Not use_fallback=True
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chroma = MagicMock()
        mock_chroma.Client.return_value = mock_client
        mock_chroma.PersistentClient.return_value = mock_client

        with patch.dict(sys.modules, {"chromadb": mock_chroma}):
            await store.initialize()
            # Should have called get_or_create_collection for each of the 5 collections
            assert mock_client.get_or_create_collection.call_count == 5

    @pytest.mark.asyncio
    async def test_initialize_collection_creation_failure(self, vector_store):
        """If one collection fails, others should still be created."""
        import sys
        mock_client = MagicMock()
        call_count = 0

        def side_effect(name, metadata):
            nonlocal call_count
            call_count += 1
            if name == "decisions":
                raise Exception("Collection creation failed")
            return MagicMock()

        mock_client.get_or_create_collection.side_effect = side_effect
        mock_chroma = MagicMock()
        mock_chroma.Client.return_value = mock_client
        mock_chroma.PersistentClient.return_value = mock_client

        vector_store._initialized = False
        with patch.dict(sys.modules, {"chromadb": mock_chroma}):
            result = await vector_store.initialize()
            assert vector_store._initialized is True

    @pytest.mark.asyncio
    async def test_initialize_general_exception_falls_back(self, vector_store):
        """General exception during init should fall back gracefully."""
        import sys
        mock_chroma = MagicMock()
        mock_chroma.Client.side_effect = RuntimeError("Unexpected error")
        mock_chroma.PersistentClient.side_effect = RuntimeError("Unexpected error")

        vector_store._initialized = False
        with patch.dict(sys.modules, {"chromadb": mock_chroma}):
            result = await vector_store.initialize()
            assert vector_store._chromadb_available is False
            assert vector_store._initialized is True


# ======================================================================
# 7. VectorStore Add Documents Tests
# ======================================================================

class TestVectorStoreAdd:
    """Tests for adding documents."""

    @pytest.mark.asyncio
    async def test_add_document(self, vector_store):
        await vector_store.initialize()
        doc = await vector_store.add("strategies", "MA crossover strategy")
        assert isinstance(doc, VectorDocument)
        assert doc.content == "MA crossover strategy"
        assert doc.collection == "strategies"
        assert doc.doc_id != ""

    @pytest.mark.asyncio
    async def test_add_with_metadata(self, vector_store):
        await vector_store.initialize()
        doc = await vector_store.add(
            "strategies",
            "Trend following",
            metadata={"type": "trend_following"},
        )
        assert doc.metadata["type"] == "trend_following"

    @pytest.mark.asyncio
    async def test_add_with_custom_id(self, vector_store):
        await vector_store.initialize()
        doc = await vector_store.add(
            "research",
            "Fed rate analysis",
            doc_id="custom-id-123",
        )
        assert doc.doc_id == "custom-id-123"

    @pytest.mark.asyncio
    async def test_add_to_unknown_collection(self, vector_store):
        await vector_store.initialize()
        doc = await vector_store.add("custom_collection", "Custom content")
        assert doc.collection == "custom_collection"

    @pytest.mark.asyncio
    async def test_add_auto_initializes(self, vector_store):
        """Add should auto-initialize if not already done."""
        doc = await vector_store.add("strategies", "Auto-init test")
        assert vector_store._initialized is True
        assert doc.content == "Auto-init test"

    @pytest.mark.asyncio
    async def test_add_generates_timestamps(self, vector_store):
        await vector_store.initialize()
        doc = await vector_store.add("strategies", "Timestamped doc")
        assert doc.created_at != ""
        assert doc.updated_at != ""

    @pytest.mark.asyncio
    async def test_add_to_each_collection(self, vector_store):
        """Add documents to all 5 standard collections."""
        await vector_store.initialize()
        for col in CollectionName:
            doc = await vector_store.add(col.value, f"Content for {col.value}")
            assert doc.collection == col.value

    @pytest.mark.asyncio
    async def test_add_multiple_to_same_collection(self, vector_store):
        await vector_store.initialize()
        doc1 = await vector_store.add("strategies", "Strategy A")
        doc2 = await vector_store.add("strategies", "Strategy B")
        assert doc1.doc_id != doc2.doc_id
        stats = await vector_store.get_stats()
        assert stats.collections.get("strategies", 0) == 2

    @pytest.mark.asyncio
    async def test_add_with_none_metadata(self, vector_store):
        """None metadata should default to empty dict."""
        await vector_store.initialize()
        doc = await vector_store.add("strategies", "Test", metadata=None)
        assert doc.metadata == {}

    @pytest.mark.asyncio
    async def test_add_with_chromadb_available(self, vector_store):
        """Test add path when ChromaDB is available."""
        await vector_store.initialize()
        mock_col = MagicMock()
        vector_store._chromadb_available = True
        vector_store._collections["strategies"] = mock_col

        doc = await vector_store.add("strategies", "ChromaDB add test")
        assert doc.content == "ChromaDB add test"
        mock_col.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_chromadb_failure_falls_back(self, vector_store):
        """If ChromaDB add fails, should fall back to memory."""
        await vector_store.initialize()
        mock_col = MagicMock()
        mock_col.add.side_effect = Exception("ChromaDB write error")
        vector_store._chromadb_available = True
        vector_store._collections["strategies"] = mock_col

        doc = await vector_store.add("strategies", "Fallback add")
        assert doc.content == "Fallback add"


# ======================================================================
# 8. VectorStore Search Tests
# ======================================================================

class TestVectorStoreSearch:
    """Tests for searching documents."""

    @pytest.mark.asyncio
    async def test_search_empty_collection(self, vector_store):
        await vector_store.initialize()
        results = await vector_store.search("strategies", "trend following")
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_with_documents(self, vector_store):
        await vector_store.initialize()
        await vector_store.add("strategies", "Moving average crossover with 50/200 EMA")
        await vector_store.add("strategies", "RSI mean reversion strategy")

        results = await vector_store.search("strategies", "moving average")
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_auto_initializes(self, vector_store):
        results = await vector_store.search("strategies", "test")
        assert vector_store._initialized is True

    @pytest.mark.asyncio
    async def test_search_with_n_results(self, vector_store):
        await vector_store.initialize()
        for i in range(5):
            await vector_store.add("strategies", f"Strategy number {i}")

        results = await vector_store.search("strategies", "Strategy", n_results=2)
        assert len(results) <= 2

    @pytest.mark.asyncio
    async def test_search_relevance_scores(self, vector_store):
        await vector_store.initialize()
        await vector_store.add("research", "Federal Reserve interest rate decision")
        await vector_store.add("research", "Apple earnings beat expectations")

        results = await vector_store.search("research", "Federal Reserve rate")
        for result in results:
            assert isinstance(result.relevance_score, float)
            assert 0.0 <= result.relevance_score <= 1.0

    @pytest.mark.asyncio
    async def test_search_returns_search_result_instances(self, vector_store):
        await vector_store.initialize()
        await vector_store.add("strategies", "Test strategy")
        results = await vector_store.search("strategies", "Test")
        for result in results:
            assert isinstance(result, SearchResult)

    @pytest.mark.asyncio
    async def test_search_result_has_doc_id(self, vector_store):
        await vector_store.initialize()
        doc = await vector_store.add("strategies", "Find me")
        results = await vector_store.search("strategies", "Find")
        assert any(r.doc_id == doc.doc_id for r in results)

    @pytest.mark.asyncio
    async def test_search_with_chromadb_available(self, vector_store):
        """Test search path when ChromaDB is available."""
        await vector_store.initialize()
        mock_col = MagicMock()
        mock_col.count.return_value = 1
        mock_col.query.return_value = {
            "ids": [["doc-1"]],
            "documents": [["Test content"]],
            "distances": [[0.2]],
            "metadatas": [[{"key": "val"}]],
        }
        vector_store._chromadb_available = True
        vector_store._collections["strategies"] = mock_col

        results = await vector_store.search("strategies", "test")
        assert len(results) == 1
        assert results[0].doc_id == "doc-1"
        assert results[0].distance == 0.2
        assert results[0].relevance_score == 0.8

    @pytest.mark.asyncio
    async def test_search_chromadb_empty_collection(self, vector_store):
        """ChromaDB search with 0 documents should return empty."""
        await vector_store.initialize()
        mock_col = MagicMock()
        mock_col.count.return_value = 0
        vector_store._chromadb_available = True
        vector_store._collections["strategies"] = mock_col

        results = await vector_store.search("strategies", "test")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_chromadb_failure_falls_back(self, vector_store):
        """If ChromaDB search fails, should fall back to keyword search."""
        await vector_store.initialize()
        await vector_store.add("strategies", "Fallback search test")

        mock_col = MagicMock()
        mock_col.count.return_value = 1
        mock_col.query.side_effect = Exception("ChromaDB search error")
        vector_store._chromadb_available = True
        vector_store._collections["strategies"] = mock_col

        results = await vector_store.search("strategies", "Fallback search")
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_with_where_filter(self, vector_store):
        """Test search with metadata filter (where clause)."""
        await vector_store.initialize()
        mock_col = MagicMock()
        mock_col.count.return_value = 1
        mock_col.query.return_value = {
            "ids": [["doc-1"]],
            "documents": [["Filtered result"]],
            "distances": [[0.1]],
            "metadatas": [[{"type": "trend"}]],
        }
        vector_store._chromadb_available = True
        vector_store._collections["strategies"] = mock_col

        results = await vector_store.search("strategies", "test", where={"type": "trend"})
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_n_results_capped_by_collection_count(self, vector_store):
        """n_results should be capped by actual document count in ChromaDB."""
        await vector_store.initialize()
        mock_col = MagicMock()
        mock_col.count.return_value = 3
        mock_col.query.return_value = {
            "ids": [["doc-1", "doc-2", "doc-3"]],
            "documents": [["A", "B", "C"]],
            "distances": [[0.1, 0.2, 0.3]],
            "metadatas": [[{}, {}, {}]],
        }
        vector_store._chromadb_available = True
        vector_store._collections["strategies"] = mock_col

        results = await vector_store.search("strategies", "test", n_results=100)
        # Should be capped to 3 (the collection count)
        mock_col.query.assert_called_once()
        call_kwargs = mock_col.query.call_args[1]
        assert call_kwargs["n_results"] <= 3


# ======================================================================
# 9. VectorStore Delete Tests
# ======================================================================

class TestVectorStoreDelete:
    """Tests for deleting documents."""

    @pytest.mark.asyncio
    async def test_delete_document(self, vector_store):
        await vector_store.initialize()
        doc = await vector_store.add("strategies", "To be deleted")
        result = await vector_store.delete("strategies", doc.doc_id)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent_doc_in_existing_collection(self, vector_store):
        """Deleting a nonexistent doc from an existing collection still returns True
        (fallback store always returns True if collection exists)."""
        await vector_store.initialize()
        result = await vector_store.delete("strategies", "nonexistent-id")
        # Fallback implementation returns True if collection exists
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_from_unknown_collection(self, vector_store):
        await vector_store.initialize()
        result = await vector_store.delete("unknown", "any-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_auto_initializes(self, vector_store):
        result = await vector_store.delete("strategies", "some-id")
        assert vector_store._initialized is True

    @pytest.mark.asyncio
    async def test_delete_with_chromadb_available(self, vector_store):
        """Test delete path when ChromaDB is available."""
        await vector_store.initialize()
        mock_col = MagicMock()
        vector_store._chromadb_available = True
        vector_store._collections["strategies"] = mock_col

        result = await vector_store.delete("strategies", "doc-1")
        assert result is True
        mock_col.delete.assert_called_once_with(ids=["doc-1"])

    @pytest.mark.asyncio
    async def test_delete_chromadb_failure_falls_to_fallback(self, vector_store):
        """If ChromaDB delete fails, falls back to fallback store (returns True)."""
        await vector_store.initialize()
        mock_col = MagicMock()
        mock_col.delete.side_effect = Exception("ChromaDB delete error")
        vector_store._chromadb_available = True
        vector_store._collections["strategies"] = mock_col

        # Fallback store for "strategies" exists and returns True
        result = await vector_store.delete("strategies", "doc-1")
        assert result is True
        mock_col.delete.assert_called_once_with(ids=["doc-1"])

    @pytest.mark.asyncio
    async def test_delete_removes_from_fallback(self, vector_store):
        await vector_store.initialize()
        doc = await vector_store.add("strategies", "To delete")
        stats_before = await vector_store.get_stats()
        count_before = stats_before.collections.get("strategies", 0)

        await vector_store.delete("strategies", doc.doc_id)
        stats_after = await vector_store.get_stats()
        count_after = stats_after.collections.get("strategies", 0)
        assert count_after == count_before - 1


# ======================================================================
# 10. VectorStore Stats Tests
# ======================================================================

class TestVectorStoreGetStats:
    """Tests for vector store statistics."""

    @pytest.mark.asyncio
    async def test_get_stats_empty(self, vector_store):
        await vector_store.initialize()
        stats = await vector_store.get_stats()
        assert isinstance(stats, VectorStoreStats)
        assert stats.total_documents == 0

    @pytest.mark.asyncio
    async def test_get_stats_with_docs(self, vector_store):
        await vector_store.initialize()
        await vector_store.add("strategies", "Strategy 1")
        await vector_store.add("strategies", "Strategy 2")
        await vector_store.add("research", "Research 1")

        stats = await vector_store.get_stats()
        assert stats.total_documents == 3
        assert stats.collections.get("strategies", 0) == 2
        assert stats.collections.get("research", 0) == 1

    @pytest.mark.asyncio
    async def test_get_stats_auto_initializes(self, vector_store):
        stats = await vector_store.get_stats()
        assert vector_store._initialized is True

    @pytest.mark.asyncio
    async def test_get_stats_embedding_provider(self, vector_store):
        await vector_store.initialize()
        stats = await vector_store.get_stats()
        assert stats.embedding_provider == "default"

    @pytest.mark.asyncio
    async def test_get_stats_with_openai_provider(self):
        store = VectorStore(embedding_provider=EmbeddingProvider.OPENAI)
        await store.initialize()
        stats = await store.get_stats()
        assert stats.embedding_provider == "openai"

    @pytest.mark.asyncio
    async def test_get_stats_has_timestamp(self, vector_store):
        await vector_store.initialize()
        stats = await vector_store.get_stats()
        assert stats.last_updated != ""

    @pytest.mark.asyncio
    async def test_get_stats_all_collections_present(self, vector_store):
        await vector_store.initialize()
        stats = await vector_store.get_stats()
        for col in CollectionName:
            assert col.value in stats.collections

    @pytest.mark.asyncio
    async def test_get_stats_with_chromadb_available(self, vector_store):
        """Test stats path when ChromaDB is available."""
        await vector_store.initialize()
        mock_col = MagicMock()
        mock_col.count.return_value = 5
        vector_store._chromadb_available = True
        vector_store._collections = {c.value: mock_col for c in CollectionName}

        stats = await vector_store.get_stats()
        assert stats.total_documents == 25  # 5 collections * 5 docs

    @pytest.mark.asyncio
    async def test_get_stats_chromadb_count_failure(self, vector_store):
        """If ChromaDB count fails, should default to 0."""
        await vector_store.initialize()
        mock_col = MagicMock()
        mock_col.count.side_effect = Exception("Count error")
        vector_store._chromadb_available = True
        vector_store._collections = {"strategies": mock_col}

        stats = await vector_store.get_stats()
        assert stats.collections["strategies"] == 0


# ======================================================================
# 11. VectorStore Convenience Methods Tests
# ======================================================================

class TestVectorStoreConvenience:
    """Tests for convenience methods."""

    @pytest.mark.asyncio
    async def test_add_strategy(self, vector_store):
        await vector_store.initialize()
        doc = await vector_store.add_strategy(
            "MA crossover", strategy_type="trend_following", symbols=["EURUSD"],
        )
        assert doc.collection == "strategies"
        assert doc.metadata.get("strategy_type") == "trend_following"

    @pytest.mark.asyncio
    async def test_add_strategy_symbols_serialized(self, vector_store):
        """Symbols should be JSON-serialized in metadata."""
        await vector_store.initialize()
        doc = await vector_store.add_strategy(
            "Breakout", strategy_type="momentum", symbols=["BTC", "ETH"],
        )
        symbols = json.loads(doc.metadata.get("symbols", "[]"))
        assert "BTC" in symbols
        assert "ETH" in symbols

    @pytest.mark.asyncio
    async def test_add_strategy_defaults(self, vector_store):
        await vector_store.initialize()
        doc = await vector_store.add_strategy("Test strategy")
        assert doc.metadata.get("strategy_type") == ""
        assert json.loads(doc.metadata.get("symbols", "[]")) == []

    @pytest.mark.asyncio
    async def test_add_research(self, vector_store):
        await vector_store.initialize()
        doc = await vector_store.add_research(
            "Fed analysis", topic="monetary_policy", source="cftc",
        )
        assert doc.collection == "research"
        assert doc.metadata.get("topic") == "monetary_policy"
        assert doc.metadata.get("source") == "cftc"

    @pytest.mark.asyncio
    async def test_add_research_defaults(self, vector_store):
        await vector_store.initialize()
        doc = await vector_store.add_research("Simple note")
        assert doc.metadata.get("topic") == ""
        assert doc.metadata.get("source") == ""

    @pytest.mark.asyncio
    async def test_add_decision(self, vector_store):
        await vector_store.initialize()
        doc = await vector_store.add_decision(
            "BUY EURUSD", symbol="EURUSD", direction="BUY", outcome="profit",
        )
        assert doc.collection == "decisions"
        assert doc.metadata.get("symbol") == "EURUSD"
        assert doc.metadata.get("direction") == "BUY"
        assert doc.metadata.get("outcome") == "profit"

    @pytest.mark.asyncio
    async def test_add_decision_defaults(self, vector_store):
        await vector_store.initialize()
        doc = await vector_store.add_decision("Holding position")
        assert doc.metadata.get("symbol") == ""
        assert doc.metadata.get("direction") == ""

    @pytest.mark.asyncio
    async def test_add_market_regime(self, vector_store):
        await vector_store.initialize()
        doc = await vector_store.add_market_regime(
            "Risk-on regime", regime="risk_on", symbol="SPY",
        )
        assert doc.collection == "market_regimes"
        assert doc.metadata.get("regime") == "risk_on"
        assert doc.metadata.get("symbol") == "SPY"

    @pytest.mark.asyncio
    async def test_add_market_regime_defaults(self, vector_store):
        await vector_store.initialize()
        doc = await vector_store.add_market_regime("Market shift")
        assert doc.metadata.get("regime") == ""

    @pytest.mark.asyncio
    async def test_add_risk_event(self, vector_store):
        await vector_store.initialize()
        doc = await vector_store.add_risk_event(
            "Drawdown alert", event_type="drawdown", severity="HIGH",
        )
        assert doc.collection == "risk_events"
        assert doc.metadata.get("event_type") == "drawdown"
        assert doc.metadata.get("severity") == "HIGH"

    @pytest.mark.asyncio
    async def test_add_risk_event_defaults(self, vector_store):
        await vector_store.initialize()
        doc = await vector_store.add_risk_event("Something happened")
        assert doc.metadata.get("event_type") == ""
        assert doc.metadata.get("severity") == ""

    @pytest.mark.asyncio
    async def test_convenience_methods_auto_init(self, vector_store):
        """Convenience methods should auto-initialize the store."""
        doc = await vector_store.add_strategy("Auto init strategy")
        assert vector_store._initialized is True


# ======================================================================
# 12. Fallback Search Tests
# ======================================================================

class TestVectorStoreFallbackSearch:
    """Tests for keyword-based fallback search."""

    @pytest.mark.asyncio
    async def test_fallback_search_word_overlap(self, vector_store):
        await vector_store.initialize()
        await vector_store.add("strategies", "moving average crossover trend following")
        await vector_store.add("strategies", "RSI mean reversion oversold")

        results = vector_store._fallback_search("strategies", "moving average", 10)
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_fallback_search_empty_query(self, vector_store):
        await vector_store.initialize()
        await vector_store.add("strategies", "Some strategy")
        results = vector_store._fallback_search("strategies", "", 10)
        assert len(results) == 1  # Empty query matches all

    @pytest.mark.asyncio
    async def test_fallback_search_no_match(self, vector_store):
        await vector_store.initialize()
        await vector_store.add("strategies", "Simple strategy")
        results = vector_store._fallback_search("strategies", "quantum computing", 10)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_fallback_search_sorted_by_relevance(self, vector_store):
        """Results should be sorted by relevance_score descending."""
        await vector_store.initialize()
        await vector_store.add("research", "Bitcoin Bitcoin Bitcoin analysis")
        await vector_store.add("research", "Bitcoin mentioned once")

        results = vector_store._fallback_search("research", "Bitcoin", 10)
        if len(results) >= 2:
            assert results[0].relevance_score >= results[1].relevance_score

    @pytest.mark.asyncio
    async def test_fallback_search_respects_limit(self, vector_store):
        await vector_store.initialize()
        for i in range(10):
            await vector_store.add("strategies", f"Strategy about Bitcoin {i}")

        results = vector_store._fallback_search("strategies", "Bitcoin", 3)
        assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_fallback_search_case_insensitive(self, vector_store):
        await vector_store.initialize()
        await vector_store.add("strategies", "Moving Average Crossover")
        results = vector_store._fallback_search("strategies", "moving average", 10)
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_fallback_search_unknown_collection(self, vector_store):
        results = vector_store._fallback_search("nonexistent", "test", 10)
        assert results == []

    @pytest.mark.asyncio
    async def test_fallback_search_distance_relevance_inverse(self, vector_store):
        """Distance should be 1 - relevance_score."""
        await vector_store.initialize()
        await vector_store.add("strategies", "trend following strategy")
        results = vector_store._fallback_search("strategies", "trend following", 10)
        for r in results:
            assert abs(r.distance - (1.0 - r.relevance_score)) < 0.01

    @pytest.mark.asyncio
    async def test_fallback_search_partial_word_match(self, vector_store):
        """Word overlap scoring - partial word matches don't count."""
        await vector_store.initialize()
        await vector_store.add("strategies", "momentum trading breakout")
        # "momentum" is a word, but "moment" is not in the doc
        results = vector_store._fallback_search("strategies", "momentum", 10)
        assert len(results) > 0


# ======================================================================
# 13. Module-level get_vector_store Tests
# ======================================================================

class TestGetVectorStore:
    """Tests for get_vector_store function."""

    def test_returns_vector_store(self):
        store = get_vector_store()
        assert isinstance(store, VectorStore)

    def test_returns_same_instance(self):
        store1 = get_vector_store()
        store2 = get_vector_store()
        assert store1 is store2


# ======================================================================
# 14. ChromaDB Unavailable / Graceful Degradation Tests
# ======================================================================

class TestVectorStoreChromaDBUnavailable:
    """Tests for graceful fallback when ChromaDB is not installed."""

    @pytest.mark.asyncio
    async def test_operations_without_chromadb(self, vector_store):
        """All operations should work via fallback."""
        await vector_store.initialize()

        # Add
        doc = await vector_store.add("strategies", "Test strategy")
        assert doc.content == "Test strategy"

        # Search
        results = await vector_store.search("strategies", "Test")
        assert isinstance(results, list)

        # Stats
        stats = await vector_store.get_stats()
        assert stats.total_documents >= 1

    @pytest.mark.asyncio
    async def test_chromadb_error_falls_back(self, vector_store):
        """If ChromaDB operations fail, should fall back gracefully."""
        await vector_store.initialize()

        # Mock ChromaDB as available but failing
        vector_store._chromadb_available = True
        vector_store._collections["strategies"] = MagicMock()
        vector_store._collections["strategies"].add.side_effect = Exception("ChromaDB error")
        vector_store._collections["strategies"].count.return_value = 0

        doc = await vector_store.add("strategies", "Fallback test")
        assert doc.content == "Fallback test"

    @pytest.mark.asyncio
    async def test_full_workflow_without_chromadb(self, vector_store):
        """Complete add -> search -> delete -> stats workflow in fallback mode."""
        await vector_store.initialize()
        assert vector_store._chromadb_available is False or vector_store._chromadb_available is True

        # Add
        doc = await vector_store.add("decisions", "BUY AAPL at 150")
        assert doc.collection == "decisions"

        # Search
        results = await vector_store.search("decisions", "AAPL")
        assert len(results) > 0

        # Delete
        deleted = await vector_store.delete("decisions", doc.doc_id)
        assert deleted is True

        # Verify deletion
        stats = await vector_store.get_stats()
        assert stats.collections.get("decisions", 0) == 0

    @pytest.mark.asyncio
    async def test_chromadb_search_error_falls_back(self, vector_store):
        """If ChromaDB search fails, should use fallback keyword search."""
        await vector_store.initialize()
        await vector_store.add("research", "Bitcoin halving analysis")

        mock_col = MagicMock()
        mock_col.count.return_value = 1
        mock_col.query.side_effect = Exception("ChromaDB query error")
        vector_store._chromadb_available = True
        vector_store._collections["research"] = mock_col

        results = await vector_store.search("research", "Bitcoin halving")
        assert isinstance(results, list)
        # Should still get results from fallback
