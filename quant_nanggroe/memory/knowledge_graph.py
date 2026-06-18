"""Knowledge Graph for Quant Nanggroe AI Trading Framework.

Implements a domain-specific knowledge graph for trading knowledge,
representing entities (symbols, strategies, events, indicators),
relationships between them, and supporting complex graph queries.

Entity Types:
- Symbol: Trading instruments (BTC/USDT, AAPL, EUR/USD)
- Strategy: Trading strategies (momentum, mean_reversion, breakout)
- Event: Market events (earnings, halving, fed_rate_decision)
- Indicator: Technical/fundamental indicators (RSI, MACD, PE_ratio)
- Agent: Trading agents (researcher, strategist, risk)
- MarketRegime: Market states (bull, bear, ranging, volatile)

Relationship Types:
- CORRELATED_WITH: Symbol-to-Symbol correlation
- USES: Strategy-to-Indicator dependency
- APPLIES_TO: Strategy-to-Symbol applicability
- TRIGGERED_BY: Event-to-Strategy trigger
- AFFECTS: Event-to-Symbol impact
- RECOMMENDED_BY: Symbol-to-Agent attribution
- PRECEDED_BY: Event-to-Event temporal ordering
- INDICATES: Indicator-to-MarketRegime signal
- PERFORMS_WELL_IN: Strategy-to-MarketRegime suitability
- RIVAL_OF: Symbol-to-Symbol competition
- HEDGE_FOR: Symbol-to-Symbol hedging relationship

Graph Queries:
- Shortest path between entities
- Neighbors by relationship type
- Subgraph extraction
- Pattern matching
- Centrality analysis
"""

from __future__ import annotations

import json
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================


class EntityType(str, Enum):
    """Types of entities in the trading knowledge graph."""
    SYMBOL = "symbol"
    STRATEGY = "strategy"
    EVENT = "event"
    INDICATOR = "indicator"
    AGENT = "agent"
    MARKET_REGIME = "market_regime"
    FACTOR = "factor"
    PORTFOLIO = "portfolio"
    RISK_METRIC = "risk_metric"
    DATASOURCE = "datasource"


class RelationType(str, Enum):
    """Types of relationships between entities."""
    CORRELATED_WITH = "correlated_with"
    USES = "uses"
    APPLIES_TO = "applies_to"
    TRIGGERED_BY = "triggered_by"
    AFFECTS = "affects"
    RECOMMENDED_BY = "recommended_by"
    PRECEDED_BY = "preceded_by"
    INDICATES = "indicates"
    PERFORMS_WELL_IN = "performs_well_in"
    RIVAL_OF = "rival_of"
    HEDGE_FOR = "hedge_for"
    DEPENDS_ON = "depends_on"
    COMPONENT_OF = "component_of"
    BACKTESTED_WITH = "backtested_with"
    GENERATED_BY = "generated_by"
    REGULATED_BY = "regulated_by"
    FEEDS_INTO = "feeds_into"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class Entity:
    """
    A node in the knowledge graph representing a trading concept.

    Attributes:
        id: Unique entity identifier
        name: Human-readable name
        entity_type: Type classification
        properties: Additional properties/metadata
        tags: Categorization tags
        confidence: Confidence in this entity's validity (0.0-1.0)
        source: Where this entity came from
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    id: str
    name: str
    entity_type: EntityType
    properties: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    confidence: float = 1.0
    source: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize entity to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type.value,
            "properties": self.properties,
            "tags": self.tags,
            "confidence": self.confidence,
            "source": self.source,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Entity:
        """Deserialize entity from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            entity_type=EntityType(data.get("entity_type", "symbol")),
            properties=data.get("properties", {}),
            tags=data.get("tags", []),
            confidence=data.get("confidence", 1.0),
            source=data.get("source", ""),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
        )


@dataclass
class Relationship:
    """
    An edge in the knowledge graph connecting two entities.

    Attributes:
        id: Unique relationship identifier
        source_id: Source entity ID
        target_id: Target entity ID
        relation_type: Type of relationship
        weight: Relationship strength (0.0-1.0)
        properties: Additional properties/metadata
        confidence: Confidence in this relationship (0.0-1.0)
        source: Where this relationship came from
        created_at: Creation timestamp
    """
    id: str
    source_id: str
    target_id: str
    relation_type: RelationType
    weight: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    source: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize relationship to dictionary."""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "weight": self.weight,
            "properties": self.properties,
            "confidence": self.confidence,
            "source": self.source,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Relationship:
        """Deserialize relationship from dictionary."""
        return cls(
            id=data["id"],
            source_id=data["source_id"],
            target_id=data["target_id"],
            relation_type=RelationType(data.get("relation_type", "correlated_with")),
            weight=data.get("weight", 1.0),
            properties=data.get("properties", {}),
            confidence=data.get("confidence", 1.0),
            source=data.get("source", ""),
            created_at=data.get("created_at", datetime.now().isoformat()),
        )


# =============================================================================
# Knowledge Graph
# =============================================================================


class KnowledgeGraph:
    """
    Domain-specific knowledge graph for trading knowledge.

    Provides entity and relationship management with graph query
    capabilities including shortest path, neighbor discovery,
    subgraph extraction, and centrality analysis.

    Usage:
        kg = KnowledgeGraph()

        # Add entities
        btc = kg.add_entity("BTC/USDT", EntityType.SYMBOL, properties={"sector": "crypto"})
        momentum = kg.add_entity("momentum", EntityType.STRATEGY, properties={"type": "trend_following"})

        # Add relationship
        kg.add_relationship(btc.id, momentum.id, RelationType.APPLIES_TO, weight=0.8)

        # Query
        neighbors = kg.get_neighbors(btc.id)
        path = kg.shortest_path(btc.id, momentum.id)
        strategies = kg.get_entities_by_type(EntityType.STRATEGY)
    """

    def __init__(self, persist_path: Optional[str] = None) -> None:
        """
        Initialize the knowledge graph.

        Args:
            persist_path: Path for graph persistence
        """
        self._persist_path = Path(persist_path) if persist_path else None
        self._entities: Dict[str, Entity] = {}
        self._relationships: Dict[str, Relationship] = {}
        self._adjacency: Dict[str, List[str]] = defaultdict(list)  # entity_id -> [rel_ids]
        self._entity_type_index: Dict[EntityType, Set[str]] = defaultdict(set)
        self._relation_type_index: Dict[RelationType, Set[str]] = defaultdict(set)
        self._entity_name_index: Dict[str, str] = {}  # name -> entity_id

    @property
    def entity_count(self) -> int:
        """Number of entities in the graph."""
        return len(self._entities)

    @property
    def relationship_count(self) -> int:
        """Number of relationships in the graph."""
        return len(self._relationships)

    # -------------------------------------------------------------------------
    # Entity Operations
    # -------------------------------------------------------------------------

    def add_entity(
        self,
        name: str,
        entity_type: EntityType,
        properties: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        confidence: float = 1.0,
        source: str = "",
        entity_id: Optional[str] = None,
    ) -> Entity:
        """
        Add an entity to the knowledge graph.

        If an entity with the same name and type already exists,
        updates its properties instead of creating a duplicate.

        Args:
            name: Human-readable entity name
            entity_type: Type classification
            properties: Additional properties
            tags: Categorization tags
            confidence: Confidence score (0.0-1.0)
            source: Source of the entity
            entity_id: Optional specific ID (auto-generated if None)

        Returns:
            The created or updated entity
        """
        # Check for existing entity by name and type
        for eid, entity in self._entities.items():
            if entity.name == name and entity.entity_type == entity_type:
                # Update existing
                if properties:
                    entity.properties.update(properties)
                if tags:
                    entity.tags = list(set(entity.tags + tags))
                entity.confidence = max(entity.confidence, confidence)
                entity.updated_at = datetime.now().isoformat()
                logger.debug(f"Updated existing entity: {name} ({entity_type.value})")
                return entity

        # Create new entity
        if entity_id is None:
            entity_id = f"E-{entity_type.value}-{uuid.uuid4().hex[:8]}"

        entity = Entity(
            id=entity_id,
            name=name,
            entity_type=entity_type,
            properties=properties or {},
            tags=tags or [],
            confidence=confidence,
            source=source,
        )

        self._entities[entity_id] = entity
        self._entity_type_index[entity_type].add(entity_id)
        self._entity_name_index[name.lower()] = entity_id
        self._adjacency[entity_id] = []

        logger.debug(f"Added entity: {name} ({entity_type.value}) -> {entity_id}")
        return entity

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """
        Get an entity by ID.

        Args:
            entity_id: Entity identifier

        Returns:
            Entity if found, None otherwise
        """
        return self._entities.get(entity_id)

    def get_entity_by_name(self, name: str) -> Optional[Entity]:
        """
        Get an entity by name.

        Args:
            name: Entity name (case-insensitive)

        Returns:
            Entity if found, None otherwise
        """
        entity_id = self._entity_name_index.get(name.lower())
        if entity_id:
            return self._entities.get(entity_id)
        return None

    def get_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        """
        Get all entities of a specific type.

        Args:
            entity_type: Entity type to filter by

        Returns:
            List of matching entities
        """
        entity_ids = self._entity_type_index.get(entity_type, set())
        return [self._entities[eid] for eid in entity_ids if eid in self._entities]

    def search_entities(
        self,
        query: str,
        entity_type: Optional[EntityType] = None,
        tags: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[Entity]:
        """
        Search entities by name, properties, or tags.

        Args:
            query: Search query (matched against name and properties)
            entity_type: Filter by entity type
            tags: Filter by tags (any match)
            limit: Maximum results

        Returns:
            List of matching entities
        """
        query_lower = query.lower()
        results = []

        for entity in self._entities.values():
            # Type filter
            if entity_type and entity.entity_type != entity_type:
                continue

            # Tag filter
            if tags and not any(t in entity.tags for t in tags):
                continue

            # Name/property matching
            score = 0.0
            if query_lower in entity.name.lower():
                score += 2.0
            for prop_key, prop_val in entity.properties.items():
                if query_lower in str(prop_val).lower():
                    score += 1.0
                if query_lower in str(prop_key).lower():
                    score += 0.5
            if any(query_lower in tag.lower() for tag in entity.tags):
                score += 1.5

            if score > 0:
                results.append((entity, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return [entity for entity, _ in results[:limit]]

    def remove_entity(self, entity_id: str) -> bool:
        """
        Remove an entity and all its relationships.

        Args:
            entity_id: Entity identifier

        Returns:
            True if removed, False if not found
        """
        entity = self._entities.pop(entity_id, None)
        if entity is None:
            return False

        # Remove from indices
        self._entity_type_index[entity.entity_type].discard(entity_id)
        self._entity_name_index.pop(entity.name.lower(), None)

        # Remove all relationships involving this entity
        rels_to_remove = list(self._adjacency.get(entity_id, []))
        for rel_id in rels_to_remove:
            self.remove_relationship(rel_id)

        # Remove adjacency entry
        self._adjacency.pop(entity_id, None)

        return True

    def update_entity(
        self,
        entity_id: str,
        properties: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """
        Update an existing entity's properties and tags.

        Args:
            entity_id: Entity identifier
            properties: Properties to merge
            tags: Tags to add

        Returns:
            True if updated, False if entity not found
        """
        entity = self._entities.get(entity_id)
        if entity is None:
            return False

        if properties:
            entity.properties.update(properties)
        if tags:
            entity.tags = list(set(entity.tags + tags))
        entity.updated_at = datetime.now().isoformat()
        return True

    # -------------------------------------------------------------------------
    # Relationship Operations
    # -------------------------------------------------------------------------

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
        weight: float = 1.0,
        properties: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0,
        source: str = "",
        relationship_id: Optional[str] = None,
    ) -> Optional[Relationship]:
        """
        Add a relationship between two entities.

        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            relation_type: Type of relationship
            weight: Relationship strength (0.0-1.0)
            properties: Additional properties
            confidence: Confidence score
            source: Source of this relationship
            relationship_id: Optional specific ID

        Returns:
            Created relationship, or None if entities don't exist

        Raises:
            ValueError: If source or target entity doesn't exist
        """
        if source_id not in self._entities:
            raise ValueError(f"Source entity {source_id} not found")
        if target_id not in self._entities:
            raise ValueError(f"Target entity {target_id} not found")

        # Check for duplicate relationship
        for rel_id in self._adjacency.get(source_id, []):
            rel = self._relationships.get(rel_id)
            if (
                rel
                and rel.source_id == source_id
                and rel.target_id == target_id
                and rel.relation_type == relation_type
            ):
                # Update existing
                rel.weight = max(rel.weight, weight)
                if properties:
                    rel.properties.update(properties)
                rel.confidence = max(rel.confidence, confidence)
                return rel

        # Create new relationship
        if relationship_id is None:
            relationship_id = f"R-{relation_type.value}-{uuid.uuid4().hex[:8]}"

        relationship = Relationship(
            id=relationship_id,
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            weight=weight,
            properties=properties or {},
            confidence=confidence,
            source=source,
        )

        self._relationships[relationship_id] = relationship
        self._adjacency[source_id].append(relationship_id)
        self._adjacency[target_id].append(relationship_id)
        self._relation_type_index[relation_type].add(relationship_id)

        logger.debug(
            f"Added relationship: {source_id} --{relation_type.value}--> {target_id}"
        )
        return relationship

    def get_relationship(self, relationship_id: str) -> Optional[Relationship]:
        """Get a relationship by ID."""
        return self._relationships.get(relationship_id)

    def get_relationships_by_type(self, relation_type: RelationType) -> List[Relationship]:
        """Get all relationships of a specific type."""
        rel_ids = self._relation_type_index.get(relation_type, set())
        return [self._relationships[rid] for rid in rel_ids if rid in self._relationships]

    def remove_relationship(self, relationship_id: str) -> bool:
        """
        Remove a relationship.

        Args:
            relationship_id: Relationship identifier

        Returns:
            True if removed, False if not found
        """
        rel = self._relationships.pop(relationship_id, None)
        if rel is None:
            return False

        # Remove from adjacency lists
        if rel.source_id in self._adjacency:
            try:
                self._adjacency[rel.source_id].remove(relationship_id)
            except ValueError:
                pass
        if rel.target_id in self._adjacency:
            try:
                self._adjacency[rel.target_id].remove(relationship_id)
            except ValueError:
                pass

        # Remove from type index
        self._relation_type_index[rel.relation_type].discard(relationship_id)

        return True

    # -------------------------------------------------------------------------
    # Graph Queries
    # -------------------------------------------------------------------------

    def get_neighbors(
        self,
        entity_id: str,
        relation_type: Optional[RelationType] = None,
        direction: str = "both",
    ) -> List[Tuple[Entity, Relationship]]:
        """
        Get neighboring entities and their relationships.

        Args:
            entity_id: Entity to find neighbors for
            relation_type: Filter by relationship type
            direction: "outgoing", "incoming", or "both"

        Returns:
            List of (neighbor_entity, relationship) tuples
        """
        if entity_id not in self._entities:
            return []

        neighbors = []
        seen_rel_ids = set()

        for rel_id in self._adjacency.get(entity_id, []):
            if rel_id in seen_rel_ids:
                continue
            seen_rel_ids.add(rel_id)

            rel = self._relationships.get(rel_id)
            if rel is None:
                continue

            # Filter by relationship type
            if relation_type and rel.relation_type != relation_type:
                continue

            # Determine direction and neighbor
            if rel.source_id == entity_id:
                if direction == "incoming":
                    continue
                neighbor_id = rel.target_id
            elif rel.target_id == entity_id:
                if direction == "outgoing":
                    continue
                neighbor_id = rel.source_id
            else:
                continue

            neighbor = self._entities.get(neighbor_id)
            if neighbor:
                neighbors.append((neighbor, rel))

        return neighbors

    def shortest_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 6,
    ) -> Optional[List[Tuple[Entity, Optional[Relationship]]]]:
        """
        Find the shortest path between two entities using BFS.

        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            max_depth: Maximum search depth

        Returns:
            List of (entity, relationship) tuples representing the path,
            or None if no path exists
        """
        if source_id not in self._entities or target_id not in self._entities:
            return None

        if source_id == target_id:
            return [(self._entities[source_id], None)]

        # BFS
        from collections import deque

        visited: Set[str] = {source_id}
        queue: deque[Tuple[str, List[Tuple[str, Optional[str]]]]] = deque()
        queue.append((source_id, [(source_id, None)]))

        while queue:
            current_id, path = queue.popleft()

            if len(path) > max_depth + 1:
                continue

            for rel_id in self._adjacency.get(current_id, []):
                rel = self._relationships.get(rel_id)
                if rel is None:
                    continue

                # Get neighbor
                neighbor_id = rel.target_id if rel.source_id == current_id else rel.source_id

                if neighbor_id in visited:
                    continue

                visited.add(neighbor_id)
                new_path = path + [(neighbor_id, rel_id)]

                if neighbor_id == target_id:
                    # Build result
                    result = []
                    for eid, rid in new_path:
                        entity = self._entities.get(eid)
                        relationship = self._relationships.get(rid) if rid else None
                        if entity:
                            result.append((entity, relationship))
                    return result

                queue.append((neighbor_id, new_path))

        return None  # No path found

    def get_subgraph(
        self,
        entity_ids: List[str],
        max_hops: int = 1,
    ) -> Tuple[List[Entity], List[Relationship]]:
        """
        Extract a subgraph around specified entities.

        Args:
            entity_ids: Seed entity IDs
            max_hops: Maximum hops from seed entities

        Returns:
            Tuple of (entities, relationships) in the subgraph
        """
        visited_entities: Set[str] = set(entity_ids)
        visited_rels: Set[str] = set()

        current_frontier = set(entity_ids)

        for _ in range(max_hops):
            next_frontier: Set[str] = set()
            for entity_id in current_frontier:
                for rel_id in self._adjacency.get(entity_id, []):
                    if rel_id in visited_rels:
                        continue
                    visited_rels.add(rel_id)

                    rel = self._relationships.get(rel_id)
                    if rel is None:
                        continue

                    # Add connected entity
                    neighbor_id = (
                        rel.target_id if rel.source_id == entity_id else rel.source_id
                    )
                    if neighbor_id not in visited_entities:
                        visited_entities.add(neighbor_id)
                        next_frontier.add(neighbor_id)

            current_frontier = next_frontier

        entities = [
            self._entities[eid] for eid in visited_entities if eid in self._entities
        ]
        relationships = [
            self._relationships[rid] for rid in visited_rels if rid in self._relationships
        ]

        return entities, relationships

    def get_entities_by_relation(
        self,
        entity_id: str,
        relation_type: RelationType,
        direction: str = "outgoing",
    ) -> List[Entity]:
        """
        Get entities connected by a specific relationship type.

        Args:
            entity_id: Source entity
            relation_type: Relationship type to filter by
            direction: "outgoing" or "incoming"

        Returns:
            List of connected entities
        """
        neighbors = self.get_neighbors(
            entity_id, relation_type=relation_type, direction=direction
        )
        return [entity for entity, _ in neighbors]

    def centrality(self, top_k: int = 10) -> List[Tuple[Entity, int]]:
        """
        Compute degree centrality for all entities.

        Entities with more connections are more central.

        Args:
            top_k: Number of top entities to return

        Returns:
            List of (entity, degree) tuples sorted by degree descending
        """
        degree_counts: Dict[str, int] = {}
        for entity_id, rel_ids in self._adjacency.items():
            # Count unique neighbor entities (not relationships)
            neighbor_ids: Set[str] = set()
            for rel_id in rel_ids:
                rel = self._relationships.get(rel_id)
                if rel:
                    if rel.source_id == entity_id:
                        neighbor_ids.add(rel.target_id)
                    else:
                        neighbor_ids.add(rel.source_id)
            degree_counts[entity_id] = len(neighbor_ids)

        sorted_entities = sorted(
            degree_counts.items(), key=lambda x: x[1], reverse=True
        )[:top_k]

        return [
            (self._entities[eid], degree)
            for eid, degree in sorted_entities
            if eid in self._entities
        ]

    def find_patterns(
        self,
        source_type: EntityType,
        relation_type: RelationType,
        target_type: EntityType,
    ) -> List[Tuple[Entity, Relationship, Entity]]:
        """
        Find all patterns of entity_type -> relation -> entity_type.

        Useful for discovering trading knowledge patterns like:
        "Which strategies use RSI indicator?"
        "Which events affect crypto symbols?"

        Args:
            source_type: Source entity type
            relation_type: Relationship type
            target_type: Target entity type

        Returns:
            List of (source_entity, relationship, target_entity) tuples
        """
        results = []
        rel_ids = self._relation_type_index.get(relation_type, set())

        for rel_id in rel_ids:
            rel = self._relationships.get(rel_id)
            if rel is None:
                continue

            source = self._entities.get(rel.source_id)
            target = self._entities.get(rel.target_id)

            if (
                source
                and target
                and source.entity_type == source_type
                and target.entity_type == target_type
            ):
                results.append((source, rel, target))

        return results

    # -------------------------------------------------------------------------
    # Trading-Specific Convenience Methods
    # -------------------------------------------------------------------------

    def add_symbol(
        self,
        symbol: str,
        sector: Optional[str] = None,
        asset_class: Optional[str] = None,
        **properties: Any,
    ) -> Entity:
        """Add a trading symbol entity."""
        props = {k: v for k, v in properties.items() if v is not None}
        if sector:
            props["sector"] = sector
        if asset_class:
            props["asset_class"] = asset_class
        return self.add_entity(
            name=symbol,
            entity_type=EntityType.SYMBOL,
            properties=props,
            tags=[sector, asset_class] if sector or asset_class else [],
        )

    def add_strategy(
        self,
        name: str,
        strategy_type: Optional[str] = None,
        indicators: Optional[List[str]] = None,
        **properties: Any,
    ) -> Entity:
        """Add a trading strategy entity."""
        props = {k: v for k, v in properties.items() if v is not None}
        if strategy_type:
            props["type"] = strategy_type
        if indicators:
            props["indicators"] = indicators
        return self.add_entity(
            name=name,
            entity_type=EntityType.STRATEGY,
            properties=props,
            tags=[strategy_type] if strategy_type else [],
        )

    def add_event(
        self,
        name: str,
        event_type: Optional[str] = None,
        date: Optional[str] = None,
        impact: Optional[str] = None,
        **properties: Any,
    ) -> Entity:
        """Add a market event entity."""
        props = {k: v for k, v in properties.items() if v is not None}
        if event_type:
            props["event_type"] = event_type
        if date:
            props["date"] = date
        if impact:
            props["impact"] = impact
        return self.add_entity(
            name=name,
            entity_type=EntityType.EVENT,
            properties=props,
            tags=[event_type, impact] if event_type or impact else [],
        )

    def link_strategy_to_symbol(
        self,
        strategy_name: str,
        symbol_name: str,
        weight: float = 1.0,
        confidence: float = 1.0,
    ) -> Optional[Relationship]:
        """Link a strategy to a symbol it applies to."""
        strategy = self.get_entity_by_name(strategy_name)
        symbol = self.get_entity_by_name(symbol_name)
        if strategy and symbol:
            return self.add_relationship(
                source_id=strategy.id,
                target_id=symbol.id,
                relation_type=RelationType.APPLIES_TO,
                weight=weight,
                confidence=confidence,
            )
        return None

    def link_symbols_correlation(
        self,
        symbol_a: str,
        symbol_b: str,
        correlation: float = 0.0,
    ) -> Optional[Relationship]:
        """Link two symbols by their correlation."""
        entity_a = self.get_entity_by_name(symbol_a)
        entity_b = self.get_entity_by_name(symbol_b)
        if entity_a and entity_b:
            return self.add_relationship(
                source_id=entity_a.id,
                target_id=entity_b.id,
                relation_type=RelationType.CORRELATED_WITH,
                weight=abs(correlation),
                properties={"correlation": correlation},
            )
        return None

    def get_strategies_for_symbol(self, symbol_name: str) -> List[Entity]:
        """Get all strategies applicable to a symbol."""
        symbol = self.get_entity_by_name(symbol_name)
        if symbol is None:
            return []
        return self.get_entities_by_relation(
            symbol.id, RelationType.APPLIES_TO, direction="incoming"
        )

    def get_correlated_symbols(self, symbol_name: str) -> List[Tuple[Entity, float]]:
        """Get all symbols correlated with a given symbol."""
        symbol = self.get_entity_by_name(symbol_name)
        if symbol is None:
            return []

        neighbors = self.get_neighbors(symbol.id, RelationType.CORRELATED_WITH)
        results = []
        for neighbor, rel in neighbors:
            corr = rel.properties.get("correlation", rel.weight)
            results.append((neighbor, corr))
        return results

    # -------------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------------

    def save(self) -> None:
        """Persist the knowledge graph to disk."""
        if not self._persist_path:
            return
        self._persist_path.mkdir(parents=True, exist_ok=True)

        data = {
            "entities": {eid: e.to_dict() for eid, e in self._entities.items()},
            "relationships": {rid: r.to_dict() for rid, r in self._relationships.items()},
        }
        filepath = self._persist_path / "knowledge_graph.json"
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(
            f"Knowledge graph saved: {len(self._entities)} entities, "
            f"{len(self._relationships)} relationships"
        )

    def load(self) -> bool:
        """Load the knowledge graph from disk."""
        if not self._persist_path:
            return False
        filepath = self._persist_path / "knowledge_graph.json"
        if not filepath.exists():
            return False

        with open(filepath) as f:
            data = json.load(f)

        # Load entities
        for eid, edata in data.get("entities", {}).items():
            entity = Entity.from_dict(edata)
            self._entities[eid] = entity
            self._entity_type_index[entity.entity_type].add(eid)
            self._entity_name_index[entity.name.lower()] = eid
            self._adjacency[eid] = []

        # Load relationships
        for rid, rdata in data.get("relationships", {}).items():
            rel = Relationship.from_dict(rdata)
            self._relationships[rid] = rel
            self._adjacency[rel.source_id].append(rid)
            self._adjacency[rel.target_id].append(rid)
            self._relation_type_index[rel.relation_type].add(rid)

        logger.info(
            f"Knowledge graph loaded: {len(self._entities)} entities, "
            f"{len(self._relationships)} relationships"
        )
        return True

    def stats(self) -> Dict[str, Any]:
        """Get knowledge graph statistics."""
        type_counts = {
            etype.value: len(eids)
            for etype, eids in self._entity_type_index.items()
            if eids
        }
        rel_counts = {
            rtype.value: len(rids)
            for rtype, rids in self._relation_type_index.items()
            if rids
        }
        return {
            "entity_count": len(self._entities),
            "relationship_count": len(self._relationships),
            "entity_types": type_counts,
            "relationship_types": rel_counts,
        }

    def clear(self) -> None:
        """Clear the entire knowledge graph."""
        self._entities.clear()
        self._relationships.clear()
        self._adjacency.clear()
        self._entity_type_index.clear()
        self._relation_type_index.clear()
        self._entity_name_index.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Export the entire graph as a dictionary."""
        return {
            "entities": {eid: e.to_dict() for eid, e in self._entities.items()},
            "relationships": {rid: r.to_dict() for rid, r in self._relationships.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> KnowledgeGraph:
        """Create a knowledge graph from a dictionary."""
        kg = cls()
        for eid, edata in data.get("entities", {}).items():
            entity = Entity.from_dict(edata)
            kg._entities[eid] = entity
            kg._entity_type_index[entity.entity_type].add(eid)
            kg._entity_name_index[entity.name.lower()] = eid
            kg._adjacency[eid] = []
        for rid, rdata in data.get("relationships", {}).items():
            rel = Relationship.from_dict(rdata)
            kg._relationships[rid] = rel
            kg._adjacency[rel.source_id].append(rid)
            kg._adjacency[rel.target_id].append(rid)
            kg._relation_type_index[rel.relation_type].add(rid)
        return kg
