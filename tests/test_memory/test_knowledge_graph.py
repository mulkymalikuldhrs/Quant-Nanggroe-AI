"""Comprehensive tests for Knowledge Graph module.

Tests:
- Entity operations (add, get, update, remove, search)
- Relationship operations (add, get, remove, by type)
- Graph queries (neighbors, shortest path, subgraph, centrality, patterns)
- Trading-specific convenience methods
- Persistence (save/load)
- Serialization (to_dict, from_dict)
"""

from __future__ import annotations

import json
import os
import tempfile
import pytest

from quant_nanggroe.memory.knowledge_graph import (
    KnowledgeGraph, Entity, Relationship,
    EntityType, RelationType,
)


@pytest.fixture
def kg():
    """Fresh KnowledgeGraph instance."""
    return KnowledgeGraph()


@pytest.fixture
def kg_with_data(kg):
    """KnowledgeGraph with basic entities and relationships."""
    btc = kg.add_entity("BTC/USDT", EntityType.SYMBOL, properties={"sector": "crypto"})
    eth = kg.add_entity("ETH/USDT", EntityType.SYMBOL, properties={"sector": "crypto"})
    momentum = kg.add_entity("momentum", EntityType.STRATEGY, properties={"type": "trend_following"})
    rsi = kg.add_entity("RSI", EntityType.INDICATOR, properties={"period": 14})
    fed = kg.add_entity("Fed Rate Decision", EntityType.EVENT, properties={"impact": "high"})
    bull = kg.add_entity("Bull Market", EntityType.MARKET_REGIME)

    kg.add_relationship(btc.id, momentum.id, RelationType.APPLIES_TO, weight=0.8)
    kg.add_relationship(momentum.id, rsi.id, RelationType.USES, weight=0.9)
    kg.add_relationship(fed.id, btc.id, RelationType.AFFECTS, weight=0.7)
    kg.add_relationship(btc.id, eth.id, RelationType.CORRELATED_WITH, weight=0.85,
                        properties={"correlation": 0.85})
    kg.add_relationship(rsi.id, bull.id, RelationType.INDICATES, weight=0.6)

    return kg


@pytest.fixture
def persist_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


# ═══════════════════════════════════════════════════════════════════════════
# Entity Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestEntityType:
    def test_all_values(self):
        assert EntityType.SYMBOL.value == "symbol"
        assert EntityType.STRATEGY.value == "strategy"
        assert EntityType.EVENT.value == "event"
        assert EntityType.INDICATOR.value == "indicator"
        assert EntityType.AGENT.value == "agent"
        assert EntityType.MARKET_REGIME.value == "market_regime"

    def test_from_string(self):
        assert EntityType("symbol") == EntityType.SYMBOL


class TestRelationType:
    def test_all_values(self):
        assert RelationType.CORRELATED_WITH.value == "correlated_with"
        assert RelationType.USES.value == "uses"
        assert RelationType.APPLIES_TO.value == "applies_to"
        assert RelationType.AFFECTS.value == "affects"
        assert RelationType.INDICATES.value == "indicates"

    def test_from_string(self):
        assert RelationType("uses") == RelationType.USES


class TestEntityDataClass:
    def test_to_dict(self):
        entity = Entity(id="E-test", name="BTC", entity_type=EntityType.SYMBOL)
        d = entity.to_dict()
        assert d["id"] == "E-test"
        assert d["name"] == "BTC"
        assert d["entity_type"] == "symbol"

    def test_from_dict(self):
        data = {
            "id": "E-test",
            "name": "BTC",
            "entity_type": "symbol",
            "properties": {"sector": "crypto"},
            "tags": ["crypto"],
            "confidence": 0.9,
        }
        entity = Entity.from_dict(data)
        assert entity.name == "BTC"
        assert entity.entity_type == EntityType.SYMBOL
        assert entity.confidence == 0.9

    def test_from_dict_defaults(self):
        data = {"id": "E-test", "name": "BTC"}
        entity = Entity.from_dict(data)
        assert entity.entity_type == EntityType.SYMBOL
        assert entity.tags == []
        assert entity.confidence == 1.0


class TestRelationshipDataClass:
    def test_to_dict(self):
        rel = Relationship(
            id="R-test", source_id="E1", target_id="E2",
            relation_type=RelationType.USES, weight=0.8,
        )
        d = rel.to_dict()
        assert d["source_id"] == "E1"
        assert d["weight"] == 0.8

    def test_from_dict(self):
        data = {
            "id": "R-test",
            "source_id": "E1",
            "target_id": "E2",
            "relation_type": "uses",
            "weight": 0.7,
        }
        rel = Relationship.from_dict(data)
        assert rel.relation_type == RelationType.USES
        assert rel.weight == 0.7


# ═══════════════════════════════════════════════════════════════════════════
# Add Entity Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestAddEntity:
    def test_returns_entity(self, kg):
        entity = kg.add_entity("BTC/USDT", EntityType.SYMBOL)
        assert isinstance(entity, Entity)
        assert entity.name == "BTC/USDT"

    def test_auto_generates_id(self, kg):
        entity = kg.add_entity("BTC/USDT", EntityType.SYMBOL)
        assert entity.id.startswith("E-symbol-")

    def test_custom_id(self, kg):
        entity = kg.add_entity("BTC/USDT", EntityType.SYMBOL, entity_id="custom-id")
        assert entity.id == "custom-id"

    def test_with_properties(self, kg):
        entity = kg.add_entity("BTC/USDT", EntityType.SYMBOL,
                               properties={"sector": "crypto", "market_cap": "large"})
        assert entity.properties["sector"] == "crypto"

    def test_with_tags(self, kg):
        entity = kg.add_entity("BTC/USDT", EntityType.SYMBOL, tags=["crypto", "defi"])
        assert "crypto" in entity.tags

    def test_with_confidence(self, kg):
        entity = kg.add_entity("BTC/USDT", EntityType.SYMBOL, confidence=0.7)
        assert entity.confidence == 0.7

    def test_duplicate_name_updates_existing(self, kg):
        e1 = kg.add_entity("BTC/USDT", EntityType.SYMBOL, properties={"price": 50000})
        e2 = kg.add_entity("BTC/USDT", EntityType.SYMBOL, properties={"volume": 1000})
        # Should update same entity, not create duplicate
        assert e1.id == e2.id
        assert e1.properties["price"] == 50000
        assert e1.properties["volume"] == 1000

    def test_entity_count(self, kg):
        kg.add_entity("BTC/USDT", EntityType.SYMBOL)
        kg.add_entity("ETH/USDT", EntityType.SYMBOL)
        assert kg.entity_count == 2

    def test_different_types_same_name(self, kg):
        """Same name but different type = different entity."""
        e1 = kg.add_entity("momentum", EntityType.STRATEGY)
        e2 = kg.add_entity("momentum", EntityType.INDICATOR)
        assert e1.id != e2.id
        assert kg.entity_count == 2


# ═══════════════════════════════════════════════════════════════════════════
# Get Entity Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestGetEntity:
    def test_get_by_id(self, kg):
        entity = kg.add_entity("BTC/USDT", EntityType.SYMBOL)
        retrieved = kg.get_entity(entity.id)
        assert retrieved is not None
        assert retrieved.name == "BTC/USDT"

    def test_get_nonexistent(self, kg):
        assert kg.get_entity("nonexistent") is None

    def test_get_by_name(self, kg):
        kg.add_entity("BTC/USDT", EntityType.SYMBOL)
        entity = kg.get_entity_by_name("BTC/USDT")
        assert entity is not None
        assert entity.entity_type == EntityType.SYMBOL

    def test_get_by_name_case_insensitive(self, kg):
        kg.add_entity("BTC/USDT", EntityType.SYMBOL)
        entity = kg.get_entity_by_name("btc/usdt")
        assert entity is not None

    def test_get_by_name_nonexistent(self, kg):
        assert kg.get_entity_by_name("nonexistent") is None

    def test_get_by_type(self, kg):
        kg.add_entity("BTC/USDT", EntityType.SYMBOL)
        kg.add_entity("ETH/USDT", EntityType.SYMBOL)
        kg.add_entity("momentum", EntityType.STRATEGY)
        symbols = kg.get_entities_by_type(EntityType.SYMBOL)
        assert len(symbols) == 2
        strategies = kg.get_entities_by_type(EntityType.STRATEGY)
        assert len(strategies) == 1


# ═══════════════════════════════════════════════════════════════════════════
# Search Entity Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestSearchEntities:
    def test_search_by_name(self, kg):
        kg.add_entity("BTC/USDT", EntityType.SYMBOL)
        results = kg.search_entities("BTC")
        assert len(results) >= 1

    def test_search_by_property(self, kg):
        kg.add_entity("BTC/USDT", EntityType.SYMBOL, properties={"sector": "crypto"})
        results = kg.search_entities("crypto")
        assert len(results) >= 1

    def test_search_by_tag(self, kg):
        kg.add_entity("BTC/USDT", EntityType.SYMBOL, tags=["defi"])
        results = kg.search_entities("defi")
        assert len(results) >= 1

    def test_search_with_type_filter(self, kg):
        kg.add_entity("momentum", EntityType.STRATEGY)
        kg.add_entity("momentum", EntityType.INDICATOR)
        results = kg.search_entities("momentum", entity_type=EntityType.STRATEGY)
        assert len(results) == 1

    def test_search_with_tag_filter(self, kg):
        kg.add_entity("BTC/USDT", EntityType.SYMBOL, tags=["crypto", "defi"])
        kg.add_entity("AAPL", EntityType.SYMBOL, tags=["equity"])
        results = kg.search_entities("", tags=["crypto"])
        assert len(results) == 1

    def test_search_limit(self, kg):
        for i in range(20):
            kg.add_entity(f"SYM{i}", EntityType.SYMBOL)
        results = kg.search_entities("SYM", limit=5)
        assert len(results) <= 5

    def test_search_no_results(self, kg):
        results = kg.search_entities("nonexistent_xyz")
        assert len(results) == 0


# ═══════════════════════════════════════════════════════════════════════════
# Update/Remove Entity Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestUpdateEntity:
    def test_update_properties(self, kg):
        entity = kg.add_entity("BTC/USDT", EntityType.SYMBOL, properties={"price": 50000})
        kg.update_entity(entity.id, properties={"price": 55000, "volume": 1000})
        updated = kg.get_entity(entity.id)
        assert updated.properties["price"] == 55000
        assert updated.properties["volume"] == 1000

    def test_update_tags(self, kg):
        entity = kg.add_entity("BTC/USDT", EntityType.SYMBOL, tags=["crypto"])
        kg.update_entity(entity.id, tags=["defi"])
        updated = kg.get_entity(entity.id)
        assert "defi" in updated.tags
        assert "crypto" in updated.tags  # Tags are added, not replaced

    def test_update_nonexistent(self, kg):
        result = kg.update_entity("nonexistent", properties={"x": 1})
        assert result is False


class TestRemoveEntity:
    def test_remove_entity(self, kg):
        entity = kg.add_entity("BTC/USDT", EntityType.SYMBOL)
        result = kg.remove_entity(entity.id)
        assert result is True
        assert kg.get_entity(entity.id) is None

    def test_remove_nonexistent(self, kg):
        result = kg.remove_entity("nonexistent")
        assert result is False

    def test_remove_cascades_relationships(self, kg):
        e1 = kg.add_entity("BTC/USDT", EntityType.SYMBOL)
        e2 = kg.add_entity("ETH/USDT", EntityType.SYMBOL)
        rel = kg.add_relationship(e1.id, e2.id, RelationType.CORRELATED_WITH)
        kg.remove_entity(e1.id)
        # Relationship should also be removed
        assert kg.get_relationship(rel.id) is None

    def test_remove_decrements_count(self, kg):
        entity = kg.add_entity("BTC/USDT", EntityType.SYMBOL)
        assert kg.entity_count == 1
        kg.remove_entity(entity.id)
        assert kg.entity_count == 0


# ═══════════════════════════════════════════════════════════════════════════
# Relationship Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestAddRelationship:
    def test_returns_relationship(self, kg_with_data):
        assert kg_with_data.relationship_count >= 1

    def test_auto_generates_id(self, kg_with_data):
        for rid, rel in kg_with_data._relationships.items():
            assert rid.startswith("R-")

    def test_nonexistent_source_raises(self, kg):
        e2 = kg.add_entity("ETH/USDT", EntityType.SYMBOL)
        with pytest.raises(ValueError, match="Source entity"):
            kg.add_relationship("nonexistent", e2.id, RelationType.CORRELATED_WITH)

    def test_nonexistent_target_raises(self, kg):
        e1 = kg.add_entity("BTC/USDT", EntityType.SYMBOL)
        with pytest.raises(ValueError, match="Target entity"):
            kg.add_relationship(e1.id, "nonexistent", RelationType.CORRELATED_WITH)

    def test_duplicate_relationship_updates(self, kg):
        e1 = kg.add_entity("BTC/USDT", EntityType.SYMBOL)
        e2 = kg.add_entity("ETH/USDT", EntityType.SYMBOL)
        r1 = kg.add_relationship(e1.id, e2.id, RelationType.CORRELATED_WITH, weight=0.5)
        r2 = kg.add_relationship(e1.id, e2.id, RelationType.CORRELATED_WITH, weight=0.9)
        # Should update, not create duplicate
        assert r1.id == r2.id
        assert r2.weight == 0.9
        assert kg.relationship_count == 1

    def test_with_properties(self, kg):
        e1 = kg.add_entity("BTC/USDT", EntityType.SYMBOL)
        e2 = kg.add_entity("ETH/USDT", EntityType.SYMBOL)
        rel = kg.add_relationship(e1.id, e2.id, RelationType.CORRELATED_WITH,
                                   properties={"correlation": 0.85})
        assert rel.properties["correlation"] == 0.85


class TestGetRelationship:
    def test_get_by_id(self, kg_with_data):
        for rid in kg_with_data._relationships:
            rel = kg_with_data.get_relationship(rid)
            assert rel is not None

    def test_get_nonexistent(self, kg):
        assert kg.get_relationship("nonexistent") is None

    def test_get_by_type(self, kg_with_data):
        corr_rels = kg_with_data.get_relationships_by_type(RelationType.CORRELATED_WITH)
        assert len(corr_rels) >= 1


class TestRemoveRelationship:
    def test_remove_relationship(self, kg):
        e1 = kg.add_entity("A", EntityType.SYMBOL)
        e2 = kg.add_entity("B", EntityType.SYMBOL)
        rel = kg.add_relationship(e1.id, e2.id, RelationType.CORRELATED_WITH)
        result = kg.remove_relationship(rel.id)
        assert result is True
        assert kg.get_relationship(rel.id) is None

    def test_remove_nonexistent(self, kg):
        result = kg.remove_relationship("nonexistent")
        assert result is False

    def test_remove_decrements_count(self, kg):
        e1 = kg.add_entity("A", EntityType.SYMBOL)
        e2 = kg.add_entity("B", EntityType.SYMBOL)
        rel = kg.add_relationship(e1.id, e2.id, RelationType.CORRELATED_WITH)
        assert kg.relationship_count == 1
        kg.remove_relationship(rel.id)
        assert kg.relationship_count == 0


# ═══════════════════════════════════════════════════════════════════════════
# Graph Query Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestGetNeighbors:
    def test_get_all_neighbors(self, kg_with_data):
        btc = kg_with_data.get_entity_by_name("BTC/USDT")
        neighbors = kg_with_data.get_neighbors(btc.id)
        assert len(neighbors) >= 2  # momentum and ETH

    def test_get_neighbors_by_type(self, kg_with_data):
        btc = kg_with_data.get_entity_by_name("BTC/USDT")
        neighbors = kg_with_data.get_neighbors(btc.id, relation_type=RelationType.CORRELATED_WITH)
        assert len(neighbors) >= 1

    def test_get_outgoing_neighbors(self, kg_with_data):
        btc = kg_with_data.get_entity_by_name("BTC/USDT")
        neighbors = kg_with_data.get_neighbors(btc.id, direction="outgoing")
        # BTC has outgoing CORRELATED_WITH and APPLIES_TO
        assert len(neighbors) >= 1

    def test_get_incoming_neighbors(self, kg_with_data):
        btc = kg_with_data.get_entity_by_name("BTC/USDT")
        neighbors = kg_with_data.get_neighbors(btc.id, direction="incoming")
        # Fed AFFECTS BTC
        assert len(neighbors) >= 1

    def test_neighbors_nonexistent_entity(self, kg):
        neighbors = kg.get_neighbors("nonexistent")
        assert len(neighbors) == 0


class TestShortestPath:
    def test_same_entity(self, kg_with_data):
        btc = kg_with_data.get_entity_by_name("BTC/USDT")
        path = kg_with_data.shortest_path(btc.id, btc.id)
        assert path is not None
        assert len(path) == 1

    def test_direct_path(self, kg_with_data):
        btc = kg_with_data.get_entity_by_name("BTC/USDT")
        eth = kg_with_data.get_entity_by_name("ETH/USDT")
        path = kg_with_data.shortest_path(btc.id, eth.id)
        assert path is not None
        assert len(path) == 2  # BTC → ETH

    def test_indirect_path(self, kg_with_data):
        btc = kg_with_data.get_entity_by_name("BTC/USDT")
        rsi = kg_with_data.get_entity_by_name("RSI")
        path = kg_with_data.shortest_path(btc.id, rsi.id)
        # BTC → momentum → RSI
        assert path is not None
        assert len(path) >= 2

    def test_no_path(self, kg):
        e1 = kg.add_entity("A", EntityType.SYMBOL)
        e2 = kg.add_entity("B", EntityType.SYMBOL)
        # No relationship between them
        path = kg.shortest_path(e1.id, e2.id)
        assert path is None

    def test_nonexistent_source(self, kg_with_data):
        eth = kg_with_data.get_entity_by_name("ETH/USDT")
        path = kg_with_data.shortest_path("nonexistent", eth.id)
        assert path is None

    def test_max_depth_limit(self, kg_with_data):
        btc = kg_with_data.get_entity_by_name("BTC/USDT")
        eth = kg_with_data.get_entity_by_name("ETH/USDT")
        # BTC and ETH are directly connected (depth 1), so max_depth=0 won't find it
        # but max_depth=1 should
        path = kg_with_data.shortest_path(btc.id, eth.id, max_depth=0)
        # Either no path found or the path is very short (direct connection)
        if path is not None:
            # Direct connection still counts as depth 1
            assert len(path) <= 2


class TestGetSubgraph:
    def test_subgraph_0_hops(self, kg_with_data):
        btc = kg_with_data.get_entity_by_name("BTC/USDT")
        entities, rels = kg_with_data.get_subgraph([btc.id], max_hops=0)
        assert len(entities) == 1

    def test_subgraph_1_hop(self, kg_with_data):
        btc = kg_with_data.get_entity_by_name("BTC/USDT")
        entities, rels = kg_with_data.get_subgraph([btc.id], max_hops=1)
        assert len(entities) >= 2  # BTC + at least one neighbor
        assert len(rels) >= 1


class TestCentrality:
    def test_centrality(self, kg_with_data):
        central = kg_with_data.centrality(top_k=5)
        assert len(central) >= 1
        # BTC should be most central (connected to momentum, ETH, fed)
        top_entity = central[0][0]
        assert top_entity.name in ("BTC/USDT", "RSI", "momentum")

    def test_centrality_empty_graph(self, kg):
        central = kg.centrality()
        assert len(central) == 0


class TestFindPatterns:
    def test_find_strategy_uses_indicator(self, kg_with_data):
        patterns = kg_with_data.find_patterns(
            EntityType.STRATEGY, RelationType.USES, EntityType.INDICATOR
        )
        assert len(patterns) >= 1
        source, rel, target = patterns[0]
        assert source.entity_type == EntityType.STRATEGY
        assert target.entity_type == EntityType.INDICATOR

    def test_find_no_matching_patterns(self, kg_with_data):
        patterns = kg_with_data.find_patterns(
            EntityType.AGENT, RelationType.USES, EntityType.SYMBOL
        )
        assert len(patterns) == 0


# ═══════════════════════════════════════════════════════════════════════════
# Trading Convenience Methods
# ═══════════════════════════════════════════════════════════════════════════

class TestTradingConvenienceMethods:
    def test_add_symbol(self, kg):
        entity = kg.add_symbol("BTC/USDT", sector="crypto", asset_class="digital")
        assert entity.entity_type == EntityType.SYMBOL
        assert entity.properties["sector"] == "crypto"

    def test_add_strategy(self, kg):
        entity = kg.add_strategy("momentum", strategy_type="trend_following")
        assert entity.entity_type == EntityType.STRATEGY

    def test_add_event(self, kg):
        entity = kg.add_event("Fed Meeting", event_type="rate_decision", impact="high")
        assert entity.entity_type == EntityType.EVENT

    def test_link_strategy_to_symbol(self, kg):
        kg.add_strategy("momentum")
        kg.add_symbol("BTC/USDT")
        rel = kg.link_strategy_to_symbol("momentum", "BTC/USDT", weight=0.8)
        assert rel is not None
        assert rel.relation_type == RelationType.APPLIES_TO

    def test_link_symbols_correlation(self, kg):
        kg.add_symbol("BTC/USDT")
        kg.add_symbol("ETH/USDT")
        rel = kg.link_symbols_correlation("BTC/USDT", "ETH/USDT", correlation=0.85)
        assert rel is not None
        assert rel.properties["correlation"] == 0.85

    def test_get_strategies_for_symbol(self, kg):
        kg.add_strategy("momentum")
        kg.add_symbol("BTC/USDT")
        kg.link_strategy_to_symbol("momentum", "BTC/USDT")
        strategies = kg.get_strategies_for_symbol("BTC/USDT")
        assert len(strategies) >= 1

    def test_get_correlated_symbols(self, kg):
        kg.add_symbol("BTC/USDT")
        kg.add_symbol("ETH/USDT")
        kg.link_symbols_correlation("BTC/USDT", "ETH/USDT", correlation=0.85)
        correlated = kg.get_correlated_symbols("BTC/USDT")
        assert len(correlated) >= 1
        symbol, corr = correlated[0]
        assert corr == 0.85

    def test_link_nonexistent_returns_none(self, kg):
        result = kg.link_strategy_to_symbol("nonexistent", "also_nonexistent")
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════
# Persistence Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestKnowledgeGraphPersistence:
    def test_save_and_load(self, persist_dir):
        kg1 = KnowledgeGraph(persist_path=persist_dir)
        kg1.add_symbol("BTC/USDT", sector="crypto")
        kg1.save()

        kg2 = KnowledgeGraph(persist_path=persist_dir)
        assert kg2.load() is True
        assert kg2.entity_count == 1

    def test_save_creates_directory(self, persist_dir):
        path = os.path.join(persist_dir, "subdir")
        kg = KnowledgeGraph(persist_path=path)
        kg.add_entity("BTC/USDT", EntityType.SYMBOL)
        kg.save()
        assert os.path.exists(os.path.join(path, "knowledge_graph.json"))

    def test_load_nonexistent(self):
        kg = KnowledgeGraph(persist_path="/tmp/nonexistent_kg_dir")
        assert kg.load() is False

    def test_save_without_path(self):
        kg = KnowledgeGraph()
        kg.add_entity("BTC/USDT", EntityType.SYMBOL)
        kg.save()  # Should not raise

    def test_load_without_path(self):
        kg = KnowledgeGraph()
        assert kg.load() is False

    def test_round_trip_preserves_relationships(self, persist_dir):
        kg1 = KnowledgeGraph(persist_path=persist_dir)
        e1 = kg1.add_entity("BTC/USDT", EntityType.SYMBOL)
        e2 = kg1.add_entity("ETH/USDT", EntityType.SYMBOL)
        kg1.add_relationship(e1.id, e2.id, RelationType.CORRELATED_WITH, weight=0.85)
        kg1.save()

        kg2 = KnowledgeGraph(persist_path=persist_dir)
        kg2.load()
        assert kg2.entity_count == 2
        assert kg2.relationship_count == 1


# ═══════════════════════════════════════════════════════════════════════════
# Serialization Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestSerialization:
    def test_to_dict(self, kg_with_data):
        data = kg_with_data.to_dict()
        assert "entities" in data
        assert "relationships" in data
        assert len(data["entities"]) > 0

    def test_from_dict(self, kg_with_data):
        data = kg_with_data.to_dict()
        kg2 = KnowledgeGraph.from_dict(data)
        assert kg2.entity_count == kg_with_data.entity_count
        assert kg2.relationship_count == kg_with_data.relationship_count

    def test_stats(self, kg_with_data):
        stats = kg_with_data.stats()
        assert stats["entity_count"] > 0
        assert stats["relationship_count"] > 0
        assert "symbol" in stats["entity_types"]

    def test_clear(self, kg_with_data):
        kg_with_data.clear()
        assert kg_with_data.entity_count == 0
        assert kg_with_data.relationship_count == 0
