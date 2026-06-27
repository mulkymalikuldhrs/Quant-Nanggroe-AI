# memory.knowledge_graph

## Class: 

Types of entities in the trading knowledge graph.

*Line: 56*

---

## Class: 

Types of relationships between entities.

*Line: 70*

---

## Class: 

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

**Methods:** to_dict, from_dict

*Line: 97*

---

## Class: 

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

**Methods:** to_dict, from_dict

*Line: 153*

---

## Class: 

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

**Methods:** __init__, entity_count, relationship_count, add_entity, get_entity, get_entity_by_name, get_entities_by_type, search_entities, remove_entity, update_entity, add_relationship, get_relationship, get_relationships_by_type, remove_relationship, get_neighbors, shortest_path, get_subgraph, get_entities_by_relation, centrality, find_patterns, add_symbol, add_strategy, add_event, link_strategy_to_symbol, link_symbols_correlation, get_strategies_for_symbol, get_correlated_symbols, save, load, stats, clear, to_dict, from_dict

*Line: 213*

---

## Function: 

Serialize entity to dictionary.

*Line: 122*

---

## Function: 

Deserialize entity from dictionary.

*Line: 137*

---

## Function: 

Serialize relationship to dictionary.

*Line: 178*

---

## Function: 

Deserialize relationship from dictionary.

*Line: 193*

---

## Function: 

Initialize the knowledge graph.

Args:
    persist_path: Path for graph persistence

*Line: 237*

---

## Function: 

Number of entities in the graph.

*Line: 253*

---

## Function: 

Number of relationships in the graph.

*Line: 258*

---

## Function: 

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

*Line: 266*

---

## Function: 

Get an entity by ID.

Args:
    entity_id: Entity identifier

Returns:
    Entity if found, None otherwise

*Line: 329*

---

## Function: 

Get an entity by name.

Args:
    name: Entity name (case-insensitive)

Returns:
    Entity if found, None otherwise

*Line: 341*

---

## Function: 

Get all entities of a specific type.

Args:
    entity_type: Entity type to filter by

Returns:
    List of matching entities

*Line: 356*

---

## Function: 

Search entities by name, properties, or tags.

Args:
    query: Search query (matched against name and properties)
    entity_type: Filter by entity type
    tags: Filter by tags (any match)
    limit: Maximum results

Returns:
    List of matching entities

*Line: 369*

---

## Function: 

Remove an entity and all its relationships.

Args:
    entity_id: Entity identifier

Returns:
    True if removed, False if not found

*Line: 418*

---

## Function: 

Update an existing entity's properties and tags.

Args:
    entity_id: Entity identifier
    properties: Properties to merge
    tags: Tags to add

Returns:
    True if updated, False if entity not found

*Line: 446*

---

## Function: 

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

*Line: 478*

---

## Function: 

Get a relationship by ID.

*Line: 554*

---

## Function: 

Get all relationships of a specific type.

*Line: 558*

---

## Function: 

Remove a relationship.

Args:
    relationship_id: Relationship identifier

Returns:
    True if removed, False if not found

*Line: 563*

---

## Function: 

Get neighboring entities and their relationships.

Args:
    entity_id: Entity to find neighbors for
    relation_type: Filter by relationship type
    direction: "outgoing", "incoming", or "both"

Returns:
    List of (neighbor_entity, relationship) tuples

*Line: 598*

---

## Function: 

Find the shortest path between two entities using BFS.

Args:
    source_id: Source entity ID
    target_id: Target entity ID
    max_depth: Maximum search depth

Returns:
    List of (entity, relationship) tuples representing the path,
    or None if no path exists

*Line: 652*

---

## Function: 

Extract a subgraph around specified entities.

Args:
    entity_ids: Seed entity IDs
    max_hops: Maximum hops from seed entities

Returns:
    Tuple of (entities, relationships) in the subgraph

*Line: 717*

---

## Function: 

Get entities connected by a specific relationship type.

Args:
    entity_id: Source entity
    relation_type: Relationship type to filter by
    direction: "outgoing" or "incoming"

Returns:
    List of connected entities

*Line: 768*

---

## Function: 

Compute degree centrality for all entities.

Entities with more connections are more central.

Args:
    top_k: Number of top entities to return

Returns:
    List of (entity, degree) tuples sorted by degree descending

*Line: 790*

---

## Function: 

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

*Line: 825*

---

## Function: 

Add a trading symbol entity.

*Line: 871*

---

## Function: 

Add a trading strategy entity.

*Line: 891*

---

## Function: 

Add a market event entity.

*Line: 911*

---

## Function: 

Link a strategy to a symbol it applies to.

*Line: 934*

---

## Function: 

Link two symbols by their correlation.

*Line: 954*

---

## Function: 

Get all strategies applicable to a symbol.

*Line: 973*

---

## Function: 

Get all symbols correlated with a given symbol.

*Line: 982*

---

## Function: 

Persist the knowledge graph to disk.

*Line: 999*

---

## Function: 

Load the knowledge graph from disk.

*Line: 1017*

---

## Function: 

Get knowledge graph statistics.

*Line: 1050*

---

## Function: 

Clear the entire knowledge graph.

*Line: 1069*

---

## Function: 

Export the entire graph as a dictionary.

*Line: 1078*

---

## Function: 

Create a knowledge graph from a dictionary.

*Line: 1086*

---

