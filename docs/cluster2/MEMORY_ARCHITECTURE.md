# AI-MultiColony-Ecosystem — Memory Architecture

> Cluster 2 Memory System Design Document
> Version: 0.1.0-draft | Status: Pre-Implementation | Classification: Internal

---

## 1. Overview

The memory architecture defines how agents store, retrieve, compress, and share
knowledge across the AI-MultiColony-Ecosystem. The system combines four memory
layers with distinct storage backends, compression strategies, and access patterns,
integrating Letta/MemGPT for conversation management, openhuman's Memory Tree
for hierarchical knowledge, Qdrant for vector search (from agentcloud), and
TokenJuice for token compression.

**Core principle**: Memory is the differentiator between a stateless chatbot and an
autonomous agent. Every agent must have access to layered memory that scales from
fast working context to persistent knowledge, with intelligent compression at every
layer boundary.

---

## 2. Memory Layers

### 2.1 Four-Layer Model

```
┌────────────────────────────────────────────────────────────────┐
│                      AGENT MEMORY STACK                        │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  L1: WORKING MEMORY                                      │  │
│  │  - What the agent is actively thinking about             │  │
│  │  - Token budget: 4K-32K per agent                       │  │
│  │  - Storage: In-process (Python dict)                     │  │
│  │  - Latency: <1ms                                        │  │
│  │  - Persistence: None (lost on agent restart)             │  │
│  │  - Source: LangGraph state, PydanticAI context           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          │ compression                         │
│                          ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  L2: EPISODIC MEMORY                                     │  │
│  │  - Recent experiences and task outcomes                  │  │
│  │  - Token budget: 50K-200K per colony                    │  │
│  │  - Storage: SQLite → PostgreSQL + Redis cache            │  │
│  │  - Latency: <10ms                                       │  │
│  │  - Persistence: Full (survives restart)                  │  │
│  │  - Source: Letta/MemGPT core memory                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          │ extraction                          │
│                          ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  L3: SEMANTIC MEMORY                                     │  │
│  │  - Facts, concepts, relationships                       │  │
│  │  - Token budget: Unbounded (vector DB)                  │  │
│  │  - Storage: Qdrant + openhuman Memory Tree              │  │
│  │  - Latency: <50ms                                       │  │
│  │  - Persistence: Full (durable storage)                   │  │
│  │  - Source: agentcloud Qdrant, openhuman tree             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          │ skill extraction                    │
│                          ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  L4: PROCEDURAL MEMORY                                   │  │
│  │  - Learned patterns, optimized workflows, skills         │  │
│  │  - Token budget: N/A (code, not tokens)                  │  │
│  │  - Storage: Skill Registry + Git repositories            │  │
│  │  - Latency: <100ms (skill load)                          │  │
│  │  - Persistence: Full (version controlled)                │  │
│  │  - Source: superpowers skills, DSPy optimization          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 2.2 Layer Interaction Flow

```
                  NEW INFORMATION
                       │
                       ▼
              ┌────────────────┐
              │ WORKING (L1)   │ ◄── Agent observes/acts
              │ Current context│
              └───────┬────────┘
                      │
           ┌──────────┼──────────┐
           │          │          │
           ▼          ▼          ▼
     ┌──────────┐ ┌────────┐ ┌──────────┐
     │Discard   │ │Archive │ │Compress  │
     │(irrelevant│ │(keep   │ │(summarize│
     │ detail)  │ │raw)    │ │ + embed) │
     └──────────┘ └───┬────┘ └────┬─────┘
                      │           │
                      ▼           ▼
              ┌────────────────┐
              │ EPISODIC (L2)  │ ◄── Letta/MemGPT manages
              │ Recent events  │
              └───────┬────────┘
                      │
           ┌──────────┼──────────┐
           │          │          │
           ▼          ▼          ▼
     ┌──────────┐ ┌────────┐ ┌──────────┐
     │Expire    │ │Extract │ │Generalize│
     │(TTL over)│ │facts   │ │patterns  │
     └──────────┘ └───┬────┘ └────┬─────┘
                      │           │
                      ▼           ▼
              ┌────────────────┐
              │ SEMANTIC (L3)  │ ◄── Qdrant + Memory Tree
              │ Knowledge      │
              └───────┬────────┘
                      │
           ┌──────────┼──────────┐
           │          │          │
           ▼          ▼          ▼
     ┌──────────┐ ┌────────┐ ┌──────────┐
     │Forget    │ │Distill │ │Extract   │
     │(low use) │ │relations│ │procedures│
     └──────────┘ └───┬────┘ └────┬─────┘
                      │           │
                      ▼           ▼
              ┌────────────────┐
              │ PROCEDURAL (L4)│ ◄── Skill Registry + DSPy
              │ Skills/code    │
              └────────────────┘
```

---

## 3. L1: Working Memory

### 3.1 Design

Working memory is the agent's active context window. It contains the current
conversation, task state, and any information the agent is actively reasoning about.

```python
class WorkingMemory(BaseModel):
    """
    L1: In-process working memory.
    Lives in the agent's Python process, backed by LangGraph state.
    """
    # Conversation history (for LLM context)
    messages: list[dict] = Field(default_factory=list)

    # Current task
    current_task: Optional[dict] = None
    task_step: int = 0

    # Active tool results (recent)
    tool_results: dict[str, Any] = Field(default_factory=dict)

    # Scratch pad for intermediate reasoning
    scratch_pad: str = ""

    # Token accounting
    tokens_used: int = 0
    token_budget: int = 8000

    # Access statistics
    read_count: int = 0
    write_count: int = 0
    last_access: datetime = Field(default_factory=datetime.utcnow)

    def remaining_budget(self) -> int:
        return self.token_budget - self.tokens_used

    def can_fit(self, token_count: int) -> bool:
        return self.tokens_used + token_count <= self.token_budget

    def add_message(self, role: str, content: str, tokens: int) -> bool:
        if not self.can_fit(tokens):
            return False  # Need to compress or flush
        self.messages.append({"role": role, "content": content})
        self.tokens_used += tokens
        self.write_count += 1
        return True

    def compress(self) -> str:
        """
        Trigger compression when approaching token budget.
        Summarizes older messages to free space.
        Returns compression summary.
        """
        ...
```

### 3.2 Working Memory Budget Allocation

| Agent Type | Default Budget | Max Budget | Notes |
|---|---|---|---|
| Framework | 4K | 8K | Low context needs |
| Coding | 16K | 32K | Code context is large |
| Research | 8K | 16K | Moderate context |
| Trading | 8K | 16K | Market data context |
| Ops | 8K | 16K | System state context |
| Creative | 8K | 16K | Content generation |
| Specialist | 4K | 8K | Focused tasks |

### 3.3 Compression Triggers

```python
WORKING_MEMORY_TRIGGERS = {
    "soft_limit": 0.75,    # Start compression at 75% budget
    "hard_limit": 0.90,    # Force compression at 90% budget
    "critical_limit": 0.98, # Emergency compression at 98%
}

COMPRESSION_STRATEGIES = {
    "soft_limit": {
        "method": "summarize_oldest",
        "keep_recent_n": 4,    # Keep last 4 messages verbatim
        "summarize_to": 0.3,   # Compress to 30% of original
    },
    "hard_limit": {
        "method": "aggressive_summarize",
        "keep_recent_n": 2,
        "summarize_to": 0.2,
        "flush_tool_results": True,
    },
    "critical_limit": {
        "method": "emergency_compress",
        "keep_recent_n": 1,
        "summarize_to": 0.1,
        "flush_tool_results": True,
        "flush_scratch_pad": True,
    },
}
```

---

## 4. L2: Episodic Memory

### 4.1 Design

Episodic memory stores recent experiences — task outcomes, conversation summaries,
and intermediate results. It is managed by Letta/MemGPT for conversation-level
memory and backed by SQLite/PostgreSQL for persistence.

```python
class EpisodicMemory(BaseModel):
    """
    L2: Episodic memory for recent experiences.
    Managed by Letta/MemGPT, stored in SQLite/PostgreSQL.
    """
    memory_id: str = Field(default_factory=lambda: uuid4().hex)
    agent_id: str
    colony_id: str

    # Content
    episode_type: Literal[
        "task_start", "task_step", "task_complete", "task_failed",
        "conversation_summary", "tool_result", "reflection", "handoff"
    ]
    content: str                     # The actual memory content
    summary: Optional[str] = None   # Compressed version

    # Metadata
    importance: float = 0.5         # 0.0-1.0 importance score
    access_count: int = 0           # How often recalled
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None  # TTL-based expiration

    # Relationships
    task_id: Optional[str] = None
    parent_episode_id: Optional[str] = None
    tags: list[str] = Field(default_factory=list)

    # Embedding (for semantic search within episodic memory)
    embedding: Optional[list[float]] = None
```

### 4.2 Letta/MemGPT Integration

Letta (formerly MemGPT) provides the conversation management layer for episodic
memory. It handles:

- **Core memory**: Key-value pairs that the agent can read/write (identity, preferences)
- **Archival memory**: Long-term storage for conversation summaries
- **Recall memory**: Searchable history of past interactions

```python
class LettaMemoryBridge:
    """
    Bridge between our memory system and Letta/MemGPT.
    Letta manages conversation-level memory; we manage the broader ecosystem.
    """

    def __init__(self, letta_client: LettaClient, pg_pool: AsyncConnectionPool):
        self.letta = letta_client
        self.pg = pg_pool

    async def create_agent_memory(self, agent_id: str, colony_id: str) -> str:
        """
        Create a Letta agent for memory management.
        Returns: Letta agent ID
        """
        letta_agent = await self.letta.agent.create(
            name=f"memory_{agent_id}",
            description=f"Memory manager for agent {agent_id} in colony {colony_id}",
            memory_blocks=[
                {"label": "identity", "value": f"Agent {agent_id}, Colony {colony_id}"},
                {"label": "preferences", "value": ""},
                {"label": "context", "value": ""},
            ],
            llm="gpt-4o",
            embedding="text-embedding-3-small",
        )
        return letta_agent.id

    async def store_episode(self, episode: EpisodicMemory) -> None:
        """Store an episode in both Letta and PostgreSQL"""
        # 1. Store in PostgreSQL (durable)
        await self.pg.execute(
            """INSERT INTO episodic_memory
               (memory_id, agent_id, colony_id, episode_type, content,
                summary, importance, task_id, tags, created_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)""",
            episode.memory_id, episode.agent_id, episode.colony_id,
            episode.episode_type, episode.content, episode.summary,
            episode.importance, episode.task_id, episode.tags, episode.created_at
        )

        # 2. Send to Letta for conversation management
        if episode.episode_type in ("conversation_summary", "reflection"):
            await self.letta.agent.message(
                agent_id=episode.agent_id,
                message=f"Remember: {episode.content}",
                role="system"
            )

        # 3. Generate and store embedding
        embedding = await self.embed(episode.content)
        await self.pg.execute(
            "UPDATE episodic_memory SET embedding = $1 WHERE memory_id = $2",
            embedding, episode.memory_id
        )

    async def recall(self, agent_id: str, query: str, top_k: int = 5) -> list[EpisodicMemory]:
        """Recall relevant episodes using semantic search"""
        query_embedding = await self.embed(query)

        results = await self.pg.fetch(
            """SELECT *, embedding <=> $1 as distance
               FROM episodic_memory
               WHERE agent_id = $2 OR colony_id = $3
               ORDER BY distance ASC
               LIMIT $4""",
            query_embedding, agent_id, self._get_colony_id(agent_id), top_k
        )

        return [EpisodicMemory(**r) for r in results]
```

### 4.3 Episodic Memory Schema (PostgreSQL)

```sql
CREATE TABLE episodic_memory (
    memory_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id        VARCHAR(64) NOT NULL,
    colony_id       VARCHAR(64) NOT NULL,
    episode_type    VARCHAR(32) NOT NULL,
    content         TEXT NOT NULL,
    summary         TEXT,
    importance      FLOAT DEFAULT 0.5 CHECK (importance BETWEEN 0.0 AND 1.0),
    access_count    INTEGER DEFAULT 0,
    task_id         VARCHAR(64),
    parent_episode_id UUID REFERENCES episodic_memory(memory_id),
    tags            TEXT[] DEFAULT '{}',
    embedding       vector(1536),  -- pgvector extension
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    last_accessed   TIMESTAMPTZ DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,

    -- Indexes
    CONSTRAINT valid_episode_type CHECK (episode_type IN (
        'task_start', 'task_step', 'task_complete', 'task_failed',
        'conversation_summary', 'tool_result', 'reflection', 'handoff'
    ))
);

CREATE INDEX idx_episodic_agent ON episodic_memory(agent_id);
CREATE INDEX idx_episodic_colony ON episodic_memory(colony_id);
CREATE INDEX idx_episodic_task ON episodic_memory(task_id);
CREATE INDEX idx_episodic_type ON episodic_memory(episode_type);
CREATE INDEX idx_episodic_importance ON episodic_memory(importance DESC);
CREATE INDEX idx_episodic_created ON episodic_memory(created_at DESC);

-- Vector similarity search index
CREATE INDEX idx_episodic_embedding ON episodic_memory
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

---

## 5. L3: Semantic Memory

### 5.1 Design

Semantic memory stores facts, concepts, and relationships as a knowledge graph
with vector search capabilities. It combines Qdrant (from agentcloud) for vector
search with openhuman's Memory Tree for hierarchical knowledge organization.

```python
class SemanticMemoryEntry(BaseModel):
    """
    L3: Semantic memory entry.
    Stored in Qdrant (vectors) + PostgreSQL (metadata) + Memory Tree (hierarchy).
    """
    entry_id: str = Field(default_factory=lambda: uuid4().hex)
    colony_id: str

    # Content
    content: str                    # The fact or concept
    content_type: Literal["fact", "concept", "procedure", "relationship", "entity"]

    # Hierarchical position (Memory Tree)
    parent_id: Optional[str] = None
    children_ids: list[str] = Field(default_factory=list)
    depth: int = 0                  # Tree depth
    path: str = ""                  # e.g., "/trading/crypto/bitcoin/halving"

    # Vector embedding
    embedding: Optional[list[float]] = None
    embedding_model: str = "text-embedding-3-small"

    # Relationships
    relations: list[MemoryRelation] = Field(default_factory=list)

    # Metadata
    source: str                     # Where this fact came from
    confidence: float = 1.0         # 0.0-1.0 confidence score
    access_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

class MemoryRelation(BaseModel):
    """A relationship between two semantic memory entries"""
    relation_type: str  # "is_a", "part_of", "related_to", "causes", "depends_on"
    target_id: str
    properties: dict = Field(default_factory=dict)
```

### 5.2 openhuman Memory Tree Integration

The openhuman Memory Tree provides a hierarchical structure for organizing
knowledge. Each node in the tree can have children, metadata, and relationships.

```python
class MemoryTreeIntegration:
    """
    Integration with openhuman's Memory Tree.
    The tree provides hierarchical organization; Qdrant provides fast search.
    """

    def __init__(self, qdrant: QdrantClient, tree_store: TreeStore):
        self.qdrant = qdrant
        self.tree = tree_store

    async def insert(self, entry: SemanticMemoryEntry) -> str:
        """
        Insert a semantic memory entry into both the tree and Qdrant.

        1. Find the appropriate parent node in the tree
        2. Insert as a child node
        3. Generate embedding
        4. Insert into Qdrant
        """
        # 1. Find parent using tree traversal
        if entry.parent_id:
            parent = await self.tree.get_node(entry.parent_id)
        else:
            # Auto-find parent based on content and path
            parent = await self.tree.find_best_parent(
                content=entry.content,
                suggested_path=entry.path
            )

        # 2. Insert into tree
        node = await self.tree.insert(
            parent_id=parent.id if parent else None,
            content=entry.content,
            metadata={
                "content_type": entry.content_type,
                "source": entry.source,
                "confidence": entry.confidence,
            }
        )
        entry.entry_id = node.id

        # 3. Generate embedding
        embedding = await self.embed(entry.content)
        entry.embedding = embedding

        # 4. Insert into Qdrant
        await self.qdrant.upsert(
            collection_name=f"colony_{entry.colony_id}_semantic",
            points=[{
                "id": entry.entry_id,
                "vector": embedding,
                "payload": {
                    "content": entry.content,
                    "content_type": entry.content_type,
                    "path": entry.path,
                    "parent_id": entry.parent_id,
                    "source": entry.source,
                    "confidence": entry.confidence,
                }
            }]
        )

        return entry.entry_id

    async def search(self, colony_id: str, query: str, top_k: int = 10,
                     path_prefix: str = None) -> list[SemanticMemoryEntry]:
        """
        Hybrid search: vector similarity + tree path filtering

        1. Generate query embedding
        2. Search Qdrant with optional path filter
        3. Enrich results with tree context (parent/children)
        """
        query_embedding = await self.embed(query)

        # Qdrant search with filter
        filter_conditions = []
        if path_prefix:
            filter_conditions.append({
                "key": "path",
                "match": {"text": path_prefix, "method": "prefix"}
            })

        results = await self.qdrant.search(
            collection_name=f"colony_{colony_id}_semantic",
            query_vector=query_embedding,
            query_filter={"must": filter_conditions} if filter_conditions else None,
            limit=top_k,
        )

        # Enrich with tree context
        entries = []
        for result in results:
            node = await self.tree.get_node(result.id)
            parent = await self.tree.get_node(node.parent_id) if node.parent_id else None
            children = await self.tree.get_children(node.id)

            entries.append(SemanticMemoryEntry(
                entry_id=node.id,
                colony_id=colony_id,
                content=result.payload["content"],
                content_type=result.payload["content_type"],
                parent_id=node.parent_id,
                children_ids=[c.id for c in children],
                depth=node.depth,
                path=node.path,
                confidence=result.payload.get("confidence", 1.0),
                source=result.payload.get("source", "unknown"),
            ))

        return entries

    async def get_subtree(self, node_id: str, max_depth: int = 3) -> dict:
        """Get a subtree from the memory tree (for context loading)"""
        return await self.tree.get_subtree(node_id, max_depth)
```

### 5.3 Qdrant Configuration (from agentcloud)

```python
QDRANT_CONFIG = {
    "collections": {
        # Per-colony semantic memory
        "colony_{colony_id}_semantic": {
            "vectors": {
                "size": 1536,          # text-embedding-3-small
                "distance": "Cosine",
            },
            "hnsw_config": {
                "m": 16,               # Connections per node
                "ef_construct": 100,   # Build-time search width
                "full_scan_threshold": 10000,
            },
            "optimizers_config": {
                "indexing_threshold": 20000,
                "flush_interval_sec": 5,
            },
        },
        # Cross-colony shared knowledge
        "ecosystem_shared": {
            "vectors": {
                "size": 1536,
                "distance": "Cosine",
            },
            "hnsw_config": {
                "m": 32,               # Higher connectivity for shared
                "ef_construct": 200,
            },
        },
        # public-apis catalog index
        "public_apis": {
            "vectors": {
                "size": 1536,
                "distance": "Cosine",
            },
        },
    },
    "performance": {
        "max_search_timeout_ms": 1000,
        "max_upsert_batch_size": 100,
        "wal_size_mb": 64,
    },
}
```

---

## 6. Token Compression (openhuman TokenJuice)

### 6.1 TokenJuice Integration

TokenJuice from openhuman provides intelligent token compression. It reduces
memory content to essential information while preserving semantic meaning.

```python
class TokenJuiceCompressor:
    """
    Token compression using openhuman TokenJuice techniques.
    Applies at each memory layer boundary.
    """

    COMPRESSION_RATIOS = {
        "working_to_episodic": 0.3,    # Keep 30% of working memory
        "episodic_to_semantic": 0.15,  # Keep 15% of episode detail
        "semantic_to_procedural": 0.05, # Extract only the procedure
    }

    async def compress(self, content: str, target_ratio: float,
                       preserve_entities: bool = True) -> CompressedResult:
        """
        Compress content to approximately target_ratio of original length.

        Strategy:
        1. Extract key entities and relationships
        2. Generate a summary that preserves entities
        3. Verify semantic similarity above threshold
        4. Return compressed content with metadata
        """
        # 1. Extract entities
        entities = await self.extract_entities(content) if preserve_entities else []

        # 2. Generate compressed summary
        target_tokens = int(self.count_tokens(content) * target_ratio)
        compressed = await self.llm.reason(
            system_prompt=COMPRESSION_PROMPT,
            context=f"Compress to ~{target_tokens} tokens. Preserve entities: {entities}",
            content=content,
            max_tokens=target_tokens + 200,  # Small buffer
        )

        # 3. Verify semantic similarity
        original_embedding = await self.embed(content)
        compressed_embedding = await self.embed(compressed)
        similarity = cosine_similarity(original_embedding, compressed_embedding)

        if similarity < 0.85:
            # Compression lost too much meaning, try again with higher ratio
            return await self.compress(content, target_ratio * 1.2, preserve_entities)

        return CompressedResult(
            original_tokens=self.count_tokens(content),
            compressed_tokens=self.count_tokens(compressed),
            compression_ratio=self.count_tokens(compressed) / self.count_tokens(content),
            semantic_similarity=similarity,
            content=compressed,
            extracted_entities=entities,
        )
```

### 6.2 Compression Pipeline

```
Agent generates output (e.g., 4000 tokens)
        │
        ▼
┌────────────────────┐
│ L1 → L2 Compress  │  Target: 30% (1200 tokens)
│ - Keep key facts   │  Method: Summarize + extract entities
│ - Preserve numbers │  Verify: Semantic similarity > 0.85
│ - Keep decisions   │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ L2 → L3 Compress  │  Target: 15% (600 tokens)
│ - Extract facts    │  Method: Fact extraction + relationship mapping
│ - Build relations  │  Verify: All entities preserved
│ - Assign to tree   │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ L3 → L4 Extract   │  Target: 5% (200 tokens → code)
│ - Extract patterns │  Method: Pattern recognition → skill template
│ - Generalize       │  Verify: Skill tests pass
│ - Create skill     │
└────────────────────┘
```

---

## 7. Memory Persistence

### 7.1 Storage Stack

```
┌──────────────────────────────────────────────────────────────┐
│                     STORAGE BACKENDS                          │
│                                                              │
│  ┌───────────┐  ┌───────────┐  ┌──────────┐  ┌───────────┐ │
│  │  SQLite   │  │ PostgreSQL│  │  Qdrant  │  │    S3     │ │
│  │  (local)  │  │  (shared) │  │ (vectors)│  │ (archive) │ │
│  │           │  │           │  │          │  │           │ │
│  │ Dev: L2   │  │ All: L2   │  │ All: L3  │  │ All: L2   │ │
│  │ Dev: L3   │  │ All: L3   │  │          │  │ All: L3   │ │
│  │ metadata  │  │ metadata  │  │          │  │ snapshots │ │
│  └───────────┘  └───────────┘  └──────────┘  └───────────┘ │
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │  Redis (cache layer)                                     ││
│  │  - Hot episodic memory (recently accessed)               ││
│  │  - Working memory snapshots                              ││
│  │  - Session state                                         ││
│  │  TTL: 1 hour (episodic), 5 min (working snapshots)       ││
│  └──────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

### 7.2 Migration Path: SQLite → PostgreSQL

```python
class MemoryMigrator:
    """
    Handles migration from SQLite (dev) to PostgreSQL (production).
    Zero-downtime migration strategy.
    """

    async def migrate_l2(self, sqlite_path: str, pg_dsn: str) -> MigrationResult:
        """
        Migrate episodic memory from SQLite to PostgreSQL.

        Steps:
        1. Create PostgreSQL schema (if not exists)
        2. Copy data in batches of 1000
        3. Verify row counts match
        4. Switch read/write to PostgreSQL
        5. Keep SQLite as read-only backup for 7 days
        6. Remove SQLite after verification period
        """
        ...

    async def migrate_l3(self, sqlite_path: str, qdrant_url: str) -> MigrationResult:
        """
        Migrate semantic memory from SQLite metadata + local vectors to Qdrant.

        Steps:
        1. Create Qdrant collection (if not exists)
        2. Read entries from SQLite
        3. Re-embed with current model (handles model upgrades)
        4. Upsert to Qdrant in batches of 100
        5. Migrate tree structure to PostgreSQL
        6. Verify search quality (compare old vs new results)
        7. Switch to Qdrant + PostgreSQL
        """
        ...
```

---

## 8. Memory Retrieval Strategies

### 8.1 Retrieval Methods

| Method | Layer | Use Case | Latency | Accuracy |
|---|---|---|---|---|
| **Direct access** | L1 | Current task context | <1ms | Exact |
| **Keyword search** | L2 | Find specific episodes | <10ms | High |
| **Semantic search** | L2, L3 | Find related knowledge | <50ms | High |
| **Tree traversal** | L3 | Navigate knowledge hierarchy | <20ms | High |
| **Graph query** | L3 | Follow relationships | <100ms | High |
| **Skill lookup** | L4 | Find relevant procedure | <100ms | Exact |
| **Hybrid search** | L2+L3 | Best overall recall | <100ms | Highest |

### 8.2 Retrieval Engine

```python
class MemoryRetrievalEngine:
    """
    Unified retrieval across all memory layers.
    Implements hybrid search combining vector similarity, keyword matching,
    and tree-based retrieval.
    """

    async def retrieve(self, query: MemoryQuery) -> list[MemoryResult]:
        """
        Retrieve relevant memories across all layers.

        Strategy depends on query type:
        - Factual query → L3 semantic search + tree traversal
        - Recent event → L2 keyword + semantic search
        - How-to query → L4 skill lookup + L3 procedure search
        - Context query → L1 direct access + L2 recent episodes
        """
        results = []

        # 1. Determine which layers to search
        layers = self._determine_layers(query)

        # 2. Search each layer in parallel
        tasks = []
        if MemoryLayer.WORKING in layers:
            tasks.append(self._search_working(query))
        if MemoryLayer.EPISODIC in layers:
            tasks.append(self._search_episodic(query))
        if MemoryLayer.SEMANTIC in layers:
            tasks.append(self._search_semantic(query))
        if MemoryLayer.PROCEDURAL in layers:
            tasks.append(self._search_procedural(query))

        layer_results = await asyncio.gather(*tasks)

        # 3. Merge and re-rank results
        for layer_result in layer_results:
            results.extend(layer_result)

        # 4. Re-rank using cross-encoder or learned ranker
        ranked = await self._rerank(query, results)

        # 5. Update access statistics
        for result in ranked:
            await self._update_access_stats(result.entry_id)

        return ranked

    def _determine_layers(self, query: MemoryQuery) -> set[MemoryLayer]:
        """Determine which memory layers are relevant for this query"""
        layers = set()

        if query.max_latency_ms and query.max_latency_ms < 10:
            layers.add(MemoryLayer.WORKING)
        elif query.max_latency_ms and query.max_latency_ms < 100:
            layers.update([MemoryLayer.WORKING, MemoryLayer.EPISODIC])
        else:
            layers.update([MemoryLayer.WORKING, MemoryLayer.EPISODIC, MemoryLayer.SEMANTIC])

        if query.query_type == "how_to":
            layers.add(MemoryLayer.PROCEDURAL)

        if query.require_facts:
            layers.add(MemoryLayer.SEMANTIC)

        return layers


class MemoryQuery(BaseModel):
    """A structured memory retrieval request"""
    query: str
    agent_id: str
    colony_id: str

    # Query parameters
    query_type: Literal["factual", "recent", "how_to", "context", "general"] = "general"
    top_k: int = 10
    max_latency_ms: Optional[int] = None
    require_facts: bool = False
    min_confidence: float = 0.5

    # Filters
    time_range: Optional[tuple[datetime, datetime]] = None
    path_prefix: Optional[str] = None
    content_type: Optional[str] = None
    tags: Optional[list[str]] = None
```

### 8.3 Context Window Assembly

```python
class ContextWindowAssembler:
    """
    Assembles the context window for an agent by selecting
    the most relevant memories from each layer.

    The context window has a fixed token budget. This component
    decides what to include to maximize utility.
    """

    async def assemble(self, agent: BaseAgent, task: Task) -> list[dict]:
        """
        Assemble context window for an agent given a task.

        Budget allocation:
        - System prompt: 10% (fixed)
        - Task description: 5% (fixed)
        - Working memory: 20% (current conversation)
        - Episodic memory: 25% (relevant past experiences)
        - Semantic memory: 25% (relevant knowledge)
        - Procedural memory: 15% (relevant skills)
        """
        budget = agent.config.memory_budget
        context = []

        # System prompt (10%)
        context.append({
            "role": "system",
            "content": agent.system_prompt,
            "tokens": int(budget * 0.10),
        })

        # Task description (5%)
        context.append({
            "role": "user",
            "content": f"Task: {task.description}",
            "tokens": int(budget * 0.05),
        })

        # Working memory (20%) - most recent conversation
        working_memories = agent.working_memory.messages[-4:]
        context.extend([{
            "role": m["role"],
            "content": m["content"],
        } for m in working_memories])

        # Episodic memory (25%) - relevant past experiences
        episodes = await self.retrieval.retrieve(MemoryQuery(
            query=task.description,
            agent_id=agent.config.agent_id,
            colony_id=agent.config.colony_id,
            query_type="recent",
            top_k=5,
        ))
        episode_text = self.format_episodes(episodes)
        context.append({
            "role": "system",
            "content": f"Relevant past experiences:\n{episode_text}",
        })

        # Semantic memory (25%) - relevant knowledge
        knowledge = await self.retrieval.retrieve(MemoryQuery(
            query=task.description,
            agent_id=agent.config.agent_id,
            colony_id=agent.config.colony_id,
            query_type="factual",
            top_k=10,
        ))
        knowledge_text = self.format_knowledge(knowledge)
        context.append({
            "role": "system",
            "content": f"Relevant knowledge:\n{knowledge_text}",
        })

        # Procedural memory (15%) - relevant skills
        skills = await self.skill_trigger.match(task, agent)
        if skills:
            skill_text = self.format_skills(skills[:3])
            context.append({
                "role": "system",
                "content": f"Available skills:\n{skill_text}",
            })

        return context
```

---

## 9. Memory Privacy and Access Control

### 9.1 Access Control Model

```python
class MemoryAccessControl:
    """
    Controls which agents can access which memories.
    Three scopes: agent-private, colony-shared, ecosystem-public.
    """

    ACCESS_LEVELS = {
        "private":    "Only the creating agent can access",
        "colony":     "All agents in the same colony can access",
        "ecosystem":  "All agents in the ecosystem can access",
    }

    async def check_access(self, agent_id: str, memory_id: str) -> bool:
        """Check if an agent can access a specific memory"""
        memory = await self.store.get(memory_id)
        agent = await self.agent_registry.get(agent_id)

        if memory.access_level == "ecosystem":
            return True
        elif memory.access_level == "colony":
            return memory.colony_id == agent.colony_id
        elif memory.access_level == "private":
            return memory.agent_id == agent_id
        return False

    async def filter_results(self, agent_id: str, results: list) -> list:
        """Filter memory search results based on access control"""
        filtered = []
        for result in results:
            if await self.check_access(agent_id, result.entry_id):
                filtered.append(result)
            else:
                # Replace with access-denied placeholder
                filtered.append(MemoryResult(
                    entry_id=result.entry_id,
                    content="[Access denied]",
                    access_level=result.access_level,
                ))
        return filtered
```

### 9.2 Privacy Controls

```python
PRIVACY_CONFIG = {
    # PII detection and redaction
    "pii_detection": {
        "enabled": True,
        "scan_on_store": True,          # Scan when storing
        "scan_on_retrieve": True,       # Scan when retrieving
        "redaction_method": "replace",  # replace, mask, or delete
        "redaction_placeholder": "[REDACTED]",
        "patterns": {
            "ssn": True,
            "email": True,
            "phone": True,
            "credit_card": True,
            "api_key": True,
            "ip_address": False,        # IP addresses are useful for context
        },
    },

    # Data retention
    "retention": {
        "working_memory": "session",        # Cleared on session end
        "episodic_private": "30_days",      # Private episodes expire after 30d
        "episodic_colony": "90_days",       # Colony episodes expire after 90d
        "episodic_ecosystem": "365_days",   # Ecosystem episodes expire after 1y
        "semantic": "infinite",             # Semantic memory is permanent
        "procedural": "infinite",           # Skills are permanent
    },

    # Encryption
    "encryption": {
        "at_rest": "AES-256-GCM",
        "in_transit": "TLS 1.3",
        "key_management": "environment_variable",  # Or "hashicorp_vault"
        "per_colony_keys": True,            # Each colony has its own encryption key
    },

    # Cross-colony sharing
    "sharing": {
        "default_access": "private",        # New memories are private by default
        "colony_auto_share": False,         # Don't auto-share with colony
        "ecosystem_auto_share": False,      # Never auto-share with ecosystem
        "share_requires_approval": True,    # Human approval for sharing
    },
}
```

### 9.3 Memory Isolation Between Colonies

```
┌─────────────────────────────────────────────────────┐
│ Colony A Memory                                      │
│ ┌─────────┐ ┌─────────┐ ┌───────────────────────┐ │
│ │Private  │ │Colony   │ │Ecosystem (read-only)  │ │
│ │(agent-  │ │Shared   │ │Public knowledge base   │ │
│ │specific)│ │         │ │                       │ │
│ └─────────┘ └─────────┘ └───────────────────────┘ │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Colony B Memory                                      │
│ ┌─────────┐ ┌─────────┐ ┌───────────────────────┐ │
│ │Private  │ │Colony   │ │Ecosystem (read-only)  │ │
│ │(agent-  │ │Shared   │ │Public knowledge base   │ │
│ │specific)│ │         │ │                       │ │
│ └─────────┘ └─────────┘ └───────────────────────┘ │
└─────────────────────────────────────────────────────┘

Rules:
- Colony A private → Colony A agent only
- Colony A shared → Colony A agents only
- Colony B private → Colony B agent only
- Colony B shared → Colony B agents only
- Ecosystem → All agents (read-only unless explicitly granted write)
- Cross-colony sharing requires explicit A2A handoff with context
```

---

## 10. Memory Operations Reference

### 10.1 Write Operations

| Operation | Layer | Access Level | Async | Audit |
|---|---|---|---|---|
| `memory.working.write` | L1 | Private | No | No |
| `memory.episodic.store` | L2 | Private/Colony | Yes | Yes |
| `memory.semantic.insert` | L3 | Colony/Ecosystem | Yes | Yes |
| `memory.procedural.register` | L4 | Ecosystem | Yes | Yes |
| `memory.working.compress` | L1→L2 | Private | Yes | Yes |

### 10.2 Read Operations

| Operation | Layer | Access Level | Caching | Latency Target |
|---|---|---|---|---|
| `memory.working.read` | L1 | Private | No | <1ms |
| `memory.episodic.recall` | L2 | Private/Colony | Redis | <10ms |
| `memory.semantic.search` | L3 | Colony/Ecosystem | Redis | <50ms |
| `memory.semantic.tree_get` | L3 | Colony/Ecosystem | Redis | <20ms |
| `memory.procedural.lookup` | L4 | Ecosystem | File | <100ms |

### 10.3 Management Operations

| Operation | Description | Access Level |
|---|---|---|
| `memory.episodic.expire` | Remove expired episodes | Colony |
| `memory.semantic.consolidate` | Merge similar entries | Colony |
| `memory.semantic.forget` | Remove low-confidence entries | Colony |
| `memory.procedural.optimize` | DSPy optimization of skill | Ecosystem |
| `memory.backup.create` | Create backup snapshot | Ecosystem |
| `memory.backup.restore` | Restore from snapshot | Ecosystem |
| `memory.stats` | Get memory usage statistics | Colony |

---

## 11. Memory Performance Targets

| Metric | Target | Measurement |
|---|---|---|
| Working memory read latency | <1ms | p99 |
| Episodic store latency | <50ms | p99 |
| Episodic recall latency | <10ms | p99 |
| Semantic search latency | <50ms | p99 |
| Tree traversal latency | <20ms | p99 |
| Compression ratio (L1→L2) | 0.25-0.35 | Ratio of compressed/original |
| Compression semantic similarity | >0.85 | Cosine similarity |
| Memory usage per colony | <500MB | Resident memory |
| Qdrant collection size limit | 10M vectors | Per collection |
| Backup creation time | <5min | Full colony backup |
| Restore time | <10min | Full colony restore |

---

## Appendix A: Embedding Model Configuration

```python
EMBEDDING_CONFIG = {
    "primary": {
        "model": "text-embedding-3-small",
        "provider": "openai",
        "dimensions": 1536,
        "cost_per_1k_tokens": 0.00002,
        "max_input_tokens": 8191,
    },
    "large": {
        "model": "text-embedding-3-large",
        "provider": "openai",
        "dimensions": 3072,
        "cost_per_1k_tokens": 0.00013,
        "max_input_tokens": 8191,
    },
    "local": {
        "model": "all-MiniLM-L6-v2",
        "provider": "sentence-transformers",
        "dimensions": 384,
        "cost_per_1k_tokens": 0,
        "max_input_tokens": 256,
    },
}

# Default: primary for production, local for development
# Dimensions must be consistent within a Qdrant collection
# Migration needed if switching embedding models
```

## Appendix B: Memory Garbage Collection

```python
class MemoryGarbageCollector:
    """
    Periodic cleanup of expired, low-value, and duplicate memories.
    Runs as a background task per colony.
    """

    SCHEDULE = {
        "episodic_expire": "every_1_hour",     # Remove expired episodes
        "episodic_dedup": "every_6_hours",     # Merge duplicate episodes
        "semantic_consolidate": "every_24_hours", # Merge similar facts
        "semantic_forget": "every_7_days",      # Remove low-confidence, unused facts
        "working_cleanup": "every_5_minutes",   # Clear stale working memory
        "cache_warm": "every_1_hour",           # Pre-warm Redis cache
    }

    async def episodic_expire(self, colony_id: str) -> int:
        """Remove expired episodic memories. Returns count removed."""
        result = await self.pg.execute(
            """DELETE FROM episodic_memory
               WHERE colony_id = $1
               AND expires_at IS NOT NULL
               AND expires_at < NOW()""",
            colony_id
        )
        return result.rowcount

    async def episodic_dedup(self, colony_id: str) -> int:
        """Merge semantically similar episodes. Returns count merged."""
        # Find pairs with >0.95 cosine similarity
        # Merge into single entry with combined metadata
        # Remove duplicates
        ...

    async def semantic_forget(self, colony_id: str) -> int:
        """
        Remove low-value semantic memories.
        Criteria: confidence < 0.3 AND access_count < 2 AND age > 30 days
        """
        result = await self.pg.execute(
            """DELETE FROM semantic_memory
               WHERE colony_id = $1
               AND confidence < 0.3
               AND access_count < 2
               AND created_at < NOW() - INTERVAL '30 days'""",
            colony_id
        )
        return result.rowcount
```
