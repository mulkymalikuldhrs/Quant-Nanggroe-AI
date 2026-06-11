# AI-MultiColony-Ecosystem — System Architecture

> Cluster 2 Technical Architecture Document
> Version: 0.1.0-draft | Status: Pre-Implementation | Classification: Internal

---

## 1. Overview

The AI-MultiColony-Ecosystem is a multi-agent operating system where autonomous agent
colonies collaborate to solve complex tasks. The architecture merges 19+ audited
repositories into a unified system built on LangGraph orchestration, MCP tool
integration, and PydanticAI validation.

**Core principle**: Every component is independently deployable, replaceable, and
testable. The colony model provides fault isolation while the orchestrator provides
coordination.

---

## 2. High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR LAYER                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  LangGraph    │  │  A2A Protocol │  │  oh-my-claudecode        │  │
│  │  Orchestrator │  │  Inter-Colony│  │  Agent Router            │  │
│  │  (sim viz)    │  │  Comm        │  │  (28 agents, 30 skills)  │  │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬──────────────┘  │
│         │                 │                       │                  │
│  ┌──────┴─────────────────┴───────────────────────┴──────────────┐  │
│  │                    Internal Message Bus                       │  │
│  │              (Redis Streams + Protocol Buffers)               │  │
│  └──────────┬──────────┬──────────┬──────────┬──────────────────┘  │
└─────────────┼──────────┼──────────┼──────────┼──────────────────────┘
              │          │          │          │
   ┌──────────▼──┐ ┌─────▼────┐ ┌──▼────────┐ ┌▼──────────────┐
   │  COLONY A   │ │ COLONY B │ │ COLONY C  │ │ COLONY D      │
   │  (Coding)   │ │(Research)│ │ (Trading)  │ │ (Operations)  │
   │             │ │          │ │            │ │               │
   │ ┌─────────┐ │ │┌───────┐│ │┌─────────┐ │ │┌───────────┐  │
   │ │Agent 1  │ │ ││Agent 1││ ││Agent 1  │ │ ││Agent 1    │  │
   │ │Agent 2  │ │ ││Agent 2││ ││Agent 2  │ │ ││Agent 2    │  │
   │ │Agent N  │ │ ││Agent N││ ││Agent N  │ │ ││Agent N    │  │
   │ └─────────┘ │ │└───────┘│ │└─────────┘ │ │└───────────┘  │
   │             │ │          │ │            │ │               │
   │ ┌─────────┐ │ │┌───────┐│ │┌─────────┐ │ │┌───────────┐  │
   │ │ Memory  │ │ ││Memory ││ ││ Memory  │ │ ││ Memory    │  │
   │ │ (local) │ │ ││(local)││ ││ (local) │ │ ││ (local)   │  │
   │ └─────────┘ │ │└───────┘│ │└─────────┘ │ │└───────────┘  │
   └──────┬──────┘ └────┬─────┘ └─────┬──────┘ └──────┬────────┘
          │             │             │               │
   ┌──────▼─────────────▼─────────────▼───────────────▼────────────┐
   │                      SHARED SERVICES                          │
   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
   │  │  Memory   │  │  Tool    │  │  Skill   │  │  Knowledge   │ │
   │  │  Store    │  │  Registry│  │  Registry│  │  Base        │ │
   │  │(Letta+   │  │  (MCP)   │  │(super-   │  │(Qdrant +     │ │
   │  │ MemTree)  │  │          │  │ powers)  │  │ SQLite)      │ │
   │  └──────────┘  └──────────┘  └──────────┘  └──────────────┘ │
   └──────────────────────────┬────────────────────────────────────┘
                              │
   ┌──────────────────────────▼────────────────────────────────────┐
   │                      INFRASTRUCTURE                           │
   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
   │  │ Docker   │  │ K8s      │  │ Sandbox  │  │ Credential   │ │
   │  │ Runtime  │  │ Orchest. │  │(E2B/     │  │ Vault        │ │
   │  │          │  │          │  │ Daytona) │  │ (AES-256)    │ │
   │  └──────────┘  └──────────┘  └──────────┘  └──────────────┘ │
   └───────────────────────────────────────────────────────────────┘
```

---

## 3. Colony Model

### 3.1 Definition

A **colony** is a LangGraph subgraph that encapsulates a group of agents with shared
context, memory, and purpose. Each colony operates as an independent unit that can:

- Spawn, configure, and terminate agents
- Maintain colony-level memory and state
- Communicate with other colonies via A2A protocol
- Request tools from the shared tool registry
- Be deployed, scaled, and versioned independently

### 3.2 Colony Anatomy

```
Colony (LangGraph Subgraph)
├── ColonyConfig
│   ├── colony_id: UUID
│   ├── colony_type: ColonyType  # CODING, RESEARCH, TRADING, OPS, CUSTOM
│   ├── max_agents: int          # Default: 10
│   ├── memory_budget: int       # Token budget per colony
│   ├── tool_access: List[str]   # Tool permission whitelist
│   └── security_level: SecurityLevel  # SANDBOXED, ELEVATED, PRIVILEGED
├── AgentPool
│   ├── agents: Dict[str, Agent]  # Active agents by ID
│   ├── agent_templates: Dict[str, AgentTemplate]
│   └── spawn_queue: PriorityQueue[AgentSpawnRequest]
├── ColonyMemory
│   ├── working_memory: Dict[str, Any]     # Current task context
│   ├── shared_context: ContextWindow      # Shared across agents
│   └── colony_knowledge: KnowledgeGraph   # Persistent colony knowledge
├── CommunicationBus
│   ├── internal: InternalBus              # Agent-to-agent within colony
│   ├── external: A2AClient                # Colony-to-colony
│   └── tool_channel: MCPClient            # Tool requests
└── LifecycleManager
    ├── health_monitor: HealthCheck
    ├── resource_monitor: ResourceTracker
    └── recovery_handler: RecoveryStrategy
```

### 3.3 Colony Types (Initial)

| Colony Type | Purpose | Source Repos | Max Agents |
|---|---|---|---|
| `CODING` | Software development, debugging, refactoring | OpenHands, OpenManus, ai-manus, nanocode | 8 |
| `RESEARCH` | Information gathering, analysis, synthesis | agenticSeek, public-apis, CloakBrowser | 6 |
| `TRADING` | Financial analysis, strategy execution | AI-MultiColony-Ecosystem (agents 1-36) | 10 |
| `OPS` | Infrastructure, deployment, monitoring | openfang, project-nomad-offline | 6 |
| `CREATIVE` | Content generation, design, multimedia | open-lovable, suna | 4 |

### 3.4 Colony Lifecycle

```
  INITIALIZING ──► RUNNING ──► SCALING ──► RUNNING
       │              │                        │
       │              ├──► IDLE ──► RUNNING    │
       │              │              (new task) │
       ▼              ▼                        ▼
    FAILED       HIBERNATING              TERMINATING
   (retry?)     (low resource)             (cleanup)
```

---

## 4. Agent Hierarchy

### 4.1 Four-Level Hierarchy

```
Level 4: ECOSYSTEM
  │  Global orchestrator, cross-colony coordination
  │  Source: LangGraph top-level graph, sim visual builder
  │
  ├── Level 3: COLONY
  │    │  Colony-level coordination, task decomposition
  │    │  Source: LangGraph subgraph, oh-my-claudecode router
  │    │
  │    ├── Level 2: SPECIALIZED
  │    │    │  Domain-specific agents (coder, researcher, browser)
  │    │    │  Source: OpenHands (5 types), OpenManus (ReAct/Browser/SWE)
  │    │    │
  │    └── Level 1: BASE
  │         │  Foundation agent with core capabilities
  │         │  Source: nanobot (~4K LOC), nanocode (~250 LOC)
  │         └── Tool Access → MCP Protocol
  │         └── Memory Access → Letta/MemGPT
  │         └── Skill Access → Skill Registry
```

### 4.2 Agent Base Class

```python
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, Any
from datetime import datetime

class AgentState(str, Enum):
    SPAWNING = "spawning"
    CONFIGURING = "configuring"
    READY = "ready"
    EXECUTING = "executing"
    WAITING = "waiting"
    LEARNING = "learning"
    HIBERNATING = "hibernating"
    TERMINATING = "terminating"
    FAILED = "failed"

class AgentConfig(BaseModel):
    agent_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    agent_type: str
    colony_id: str
    llm_provider: str = "openai"  # With failover chain
    llm_model: str = "gpt-4o"
    max_tokens: int = 4096
    temperature: float = 0.1
    tools: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    memory_budget: int = 8000
    sandbox_enabled: bool = True
    security_level: str = "sandboxed"
    timeout_seconds: int = 300
    retry_config: dict = Field(default_factory=lambda: {
        "max_retries": 3,
        "backoff_base": 2.0,
        "max_backoff": 60.0
    })

class BaseAgent(BaseModel):
    config: AgentConfig
    state: AgentState = AgentState.SPAWNING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    execution_count: int = 0
    error_count: int = 0
    parent_agent_id: Optional[str] = None
    child_agent_ids: list[str] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True
```

### 4.3 LLM Provider Failover Chain

Inherited from AI-MultiColony-Ecosystem's 7-provider failover system:

```python
LLM_FAILOVER_CHAINS = {
    "default": ["openai", "anthropic", "google", "deepseek", "groq", "ollama", "local"],
    "coding": ["anthropic", "openai", "deepseek", "google"],
    "research": ["google", "openai", "anthropic", "perplexity"],
    "fast": ["groq", "deepseek", "ollama", "openai"],
    "local_only": ["ollama", "local"],
}

# Per-provider configuration
LLM_PROVIDERS = {
    "openai": {"models": ["gpt-4o", "gpt-4o-mini", "o1", "o3-mini"]},
    "anthropic": {"models": ["claude-sonnet-4-20250514", "claude-3.5-haiku"]},
    "google": {"models": ["gemini-2.0-flash", "gemini-1.5-pro"]},
    "deepseek": {"models": ["deepseek-chat", "deepseek-reasoner"]},
    "groq": {"models": ["llama-3.3-70b", "mixtral-8x7b"]},
    "ollama": {"models": ["llama3.1", "codellama", "mistral"]},
    "local": {"models": ["custom-finetuned"]},
}
```

---

## 5. Tool/MCP Integration Architecture

### 5.1 MCP as the Universal Tool Interface

All tools are exposed via the Model Context Protocol (MCP). This provides:

- **Standardized interface**: Every tool implements `list_tools()` and `call_tool()`
- **Transport agnostic**: stdio, SSE, HTTP
- **Schema validation**: JSON Schema for all inputs/outputs
- **Capability negotiation**: Client and server exchange capabilities on connect

### 5.2 Tool Integration Stack

```
┌─────────────────────────────────────────┐
│          Agent Tool Request             │
│  (via LangGraph tool node)              │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│          MCP Client Layer               │
│  (connection pooling, routing)          │
├─────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌──────────┐  │
│  │Browser  │ │Computer │ │ API      │  │
│  │MCP Srv  │ │Use MCP  │ │ MCP Srv  │  │
│  │(Cloak)  │ │(o-c-u)  │ │(Composio)│  │
│  └─────────┘ └─────────┘ └──────────┘  │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐  │
│  │File     │ │Database │ │Messaging │  │
│  │MCP Srv  │ │ MCP Srv │ │ MCP Srv  │  │
│  └─────────┘ └─────────┘ └──────────┘  │
└─────────────────────────────────────────┘
```

### 5.3 MCP Server Configuration

```python
MCP_SERVERS = {
    "browser": {
        "command": "python",
        "args": ["-m", "mcp_browser_server"],
        "transport": "stdio",
        "env": {"BROWSER_ENGINE": "cloak", "HEADLESS": "true"},
        "capabilities": ["navigate", "click", "type", "screenshot", "extract"],
        "source_repo": "CloakBrowser",
    },
    "computer-use": {
        "command": "swift",
        "args": ["run", "MCPComputerUse"],
        "transport": "stdio",
        "env": {"SCREENSHOT_FORMAT": "png"},
        "capabilities": ["screen_capture", "mouse_click", "keyboard_type", "window_manage"],
        "source_repo": "open-computer-use",
    },
    "composio": {
        "command": "npx",
        "args": ["@composio/mcp-server"],
        "transport": "sse",
        "url": "http://localhost:3001/mcp",
        "capabilities": ["250+ integrations"],
        "source_repo": "Composio (external)",
    },
    "filesystem": {
        "command": "npx",
        "args": ["@modelcontextprotocol/server-filesystem", "/workspace"],
        "transport": "stdio",
        "capabilities": ["read_file", "write_file", "list_directory", "search"],
        "source_repo": "MCP Reference (external)",
    },
    "code-execution": {
        "command": "python",
        "args": ["-m", "mcp_code_server"],
        "transport": "stdio",
        "env": {"SANDBOX": "e2b", "TIMEOUT": "60"},
        "capabilities": ["execute_python", "execute_javascript", "install_packages"],
        "source_repo": "ai-manus + OpenHands",
    },
}
```

---

## 6. Memory Architecture

### 6.1 Layered Memory Model

```
┌────────────────────────────────────────────────────────┐
│                  AGENT MEMORY                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  L1: Working Memory (in-context)                │  │
│  │  - Current conversation, active task context     │  │
│  │  - Token budget: 4K-32K per agent               │  │
│  │  - Storage: Agent process memory                 │  │
│  │  - Source: LangGraph state, PydanticAI context   │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  L2: Episodic Memory (recent experiences)       │  │
│  │  - Task outcomes, conversation summaries         │  │
│  │  - Token budget: 50K-200K per colony            │  │
│  │  - Storage: SQLite + Redis cache                 │  │
│  │  - Source: Letta/MemGPT core memory              │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  L3: Semantic Memory (knowledge)                │  │
│  │  - Facts, concepts, relationships               │  │
│  │  - Token budget: Unbounded (vector DB)          │  │
│  │  - Storage: Qdrant + Memory Tree (openhuman)    │  │
│  │  - Source: agentcloud Qdrant, openhuman tree     │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  L4: Procedural Memory (skills & procedures)    │  │
│  │  - Learned patterns, optimized workflows         │  │
│  │  - Token budget: N/A (code, not tokens)          │  │
│  │  - Storage: Skill Registry + Code modules        │  │
│  │  - Source: superpowers skills, DSPy optimization  │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

### 6.2 Memory Flow

```
Agent observes ──► Working Memory (L1)
       │                │
       │         ┌──────▼──────┐
       │         │ Compression │ (TokenJuice from openhuman)
       │         │ & Summarize │
       │         └──────┬──────┘
       │                │
       │         ┌──────▼──────┐
       │         │  Episodic   │ (Letta/MemGPT)
       │         │  Memory(L2) │
       │         └──────┬──────┘
       │                │
       │         ┌──────▼──────┐
       │         │  Semantic   │ (Qdrant + Memory Tree)
       │         │  Memory(L3) │
       │         └──────┬──────┘
       │                │
       │         ┌──────▼──────┐
       │         │  Procedural │ (Skill extraction via DSPy)
       │         │  Memory(L4) │
       │         └─────────────┘
       │
       ▼
Agent acts ◄── Memory Retrieval (RAG + Tree traversal)
```

### 6.3 Memory Storage Stack

| Layer | Primary Storage | Backup | Compression | Encryption |
|---|---|---|---|---|
| L1 Working | Process memory | N/A | Token counting | In-process |
| L2 Episodic | SQLite → PostgreSQL | S3/MinIO | TokenJuice summary | AES-256 at rest |
| L3 Semantic | Qdrant vectors | SQLite metadata | HNSW index | AES-256 at rest |
| L4 Procedural | Git repositories | S3/MinIO | Code minification | AES-256 at rest |

---

## 7. Communication Protocols

### 7.1 Protocol Stack

```
┌─────────────────────────────────────────┐
│  Application Layer                      │
│  ┌───────────┐  ┌───────────┐          │
│  │ A2A Proto │  │ MCP Proto │          │
│  │(inter-    │  │(tool      │          │
│  │ colony)   │  │ interface)│          │
│  └─────┬─────┘  └─────┬─────┘          │
│        │              │                 │
│  ┌─────▼──────────────▼─────┐          │
│  │  Internal Message Bus    │          │
│  │  (Redis Streams)         │          │
│  └───────────┬──────────────┘          │
│              │                          │
│  ┌───────────▼──────────────┐          │
│  │  Transport Layer         │          │
│  │  Protocol Buffers (gRPC) │          │
│  │  + SSE (for streaming)   │          │
│  └──────────────────────────┘          │
└─────────────────────────────────────────┘
```

### 7.2 A2A Protocol (Agent-to-Agent)

Based on Google's A2A specification. Used for inter-colony and cross-colony
agent communication.

```python
class A2AMessage(BaseModel):
    """A2A protocol message envelope"""
    message_id: str = Field(default_factory=lambda: uuid4().hex)
    sender_agent_id: str
    sender_colony_id: str
    recipient_agent_id: str  # or "broadcast"
    recipient_colony_id: str  # or "broadcast"
    message_type: Literal["task", "query", "response", "notification", "handoff"]
    payload: dict[str, Any]
    priority: Literal["low", "normal", "high", "critical"] = "normal"
    ttl_seconds: int = 3600
    correlation_id: Optional[str] = None  # For request-response
    created_at: datetime = Field(default_factory=datetime.utcnow)

class A2AHandoff(BaseModel):
    """Agent handoff via A2A - inspired by OpenAI Agents SDK"""
    from_agent: str
    to_agent: str
    context: dict[str, Any]  # Transferred context
    task_description: str
    required_capabilities: list[str]
    priority_override: Optional[str] = None
```

### 7.3 Internal Message Bus

Redis Streams with consumer groups for reliable message delivery:

```python
# Stream naming convention
STREAMS = {
    "colony:{colony_id}:internal": "Messages within a colony",
    "colony:{colony_id}:external": "Messages from outside the colony",
    "ecosystem:broadcast": "System-wide broadcasts",
    "ecosystem:tools": "Tool request/response",
    "ecosystem:memory": "Memory store/retrieve",
}

# Consumer group configuration
CONSUMER_GROUPS = {
    "colony:{colony_id}:agents": {
        "stream": "colony:{colony_id}:internal",
        "consumers": "agent_pool",
        "max_retries": 3,
        "retry_delay_ms": 5000,
    }
}
```

### 7.4 MCP Integration Points

| Integration Point | Protocol | Direction | Purpose |
|---|---|---|---|
| Agent → Tool | MCP (stdio/SSE) | Request | Tool invocation |
| Agent → Memory | MCP (custom) | Request | Memory CRUD |
| Colony → Colony | A2A (HTTP/gRPC) | Bidirectional | Task handoff |
| Orchestrator → Colony | Internal Bus | Bidirectional | Lifecycle management |
| Ecosystem → External | MCP + REST | Request | API calls |

---

## 8. Deployment Architecture

### 8.1 Docker Compose (Development)

```yaml
# docker-compose.yml (simplified)
version: "3.9"

services:
  orchestrator:
    build: ./apps/orchestrator
    ports: ["8000:8000"]
    depends_on: [redis, qdrant, postgres]
    environment:
      - LLM_PRIMARY_PROVIDER=openai
      - MEMORY_BACKEND=qdrant
      - MESSAGE_BUS=redis

  colony-coding:
    build: ./apps/runtime
    command: ["--colony-type", "coding", "--max-agents", "8"]
    depends_on: [orchestrator, redis]
    deploy:
      replicas: 1
      resources:
        limits:
          memory: 4G
          cpus: "2.0"

  colony-research:
    build: ./apps/runtime
    command: ["--colony-type", "research", "--max-agents", "6"]
    depends_on: [orchestrator, redis]
    deploy:
      replicas: 1
      resources:
        limits:
          memory: 2G
          cpus: "1.0"

  sandbox:
    build: ./apps/browser  # CloakBrowser + code execution
    ports: ["9222:9222"]   # Chrome DevTools Protocol
    environment:
      - BROWSER_ENGINE=cloak
      - SANDBOX_MODE=strict

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    volumes: ["redis-data:/data"]

  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]
    volumes: ["qdrant-data:/storage"]

  postgres:
    image: postgres:16-alpine
    ports: ["5432:5432"]
    environment:
      POSTGRES_DB: multicolony
      POSTGRES_USER: colony
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes: ["pg-data:/var/lib/postgresql/data"]

  credential-vault:
    build: ./apps/runtime
    command: ["vault-server"]
    environment:
      - ENCRYPTION_KEY=${VAULT_KEY}
      - VAULT_BACKEND=postgres

volumes:
  redis-data:
  qdrant-data:
  pg-data:
```

### 8.2 Kubernetes (Production)

```yaml
# k8s/colony-deployment.yaml (simplified)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: colony-{{ .Values.colonyType }}
  labels:
    app: multicolony
    colony-type: {{ .Values.colonyType }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      colony-type: {{ .Values.colonyType }}
  template:
    metadata:
      labels:
        colony-type: {{ .Values.colonyType }}
    spec:
      containers:
        - name: runtime
          image: multicolony/runtime:{{ .Values.imageTag }}
          resources:
            requests:
              memory: "{{ .Values.memoryRequest }}"
              cpu: "{{ .Values.cpuRequest }}"
            limits:
              memory: "{{ .Values.memoryLimit }}"
              cpu: "{{ .Values.cpuLimit }}"
          envFrom:
            - configMapRef:
                name: colony-config
            - secretRef:
                name: colony-secrets
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 5
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: colony-{{ .Values.colonyType }}-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: colony-{{ .Values.colonyType }}
  minReplicas: {{ .Values.minReplicas }}
  maxReplicas: {{ .Values.maxReplicas }}
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

### 8.3 Sandbox Architecture

```
┌─────────────────────────────────────┐
│         Host System                 │
│  ┌───────────────────────────────┐  │
│  │  Colony Runtime (Docker)      │  │
│  │  ┌─────────────────────────┐  │  │
│  │  │  Agent Process          │  │  │
│  │  │  ┌───────────────────┐  │  │  │
│  │  │  │  Sandbox Container│  │  │  │
│  │  │  │  (E2B/Daytona)    │  │  │  │
│  │  │  │  - Code execution │  │  │  │
│  │  │  │  - File system    │  │  │  │
│  │  │  │  - Network (limited)│  │  │
│  │  │  └───────────────────┘  │  │  │
│  │  └─────────────────────────┘  │  │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │  Browser Container (Cloak)    │  │
│  │  - Stealth Chromium           │  │
│  │  - 58 C++ patches             │  │
│  │  - Network isolation          │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

---

## 9. Credential Management

Inherited from AI-MultiColony-Ecosystem's AES-256 credential system, extended
to support the broader tool and LLM provider landscape:

```python
class CredentialStore:
    """
    AES-256-GCM encrypted credential store.

    - All credentials encrypted at rest in PostgreSQL
    - Encryption key from environment variable or HashiCorp Vault
    - Per-colony credential isolation
    - Automatic rotation support
    - Audit logging for all access
    """

    ENCRYPTION_ALGORITHM = "AES-256-GCM"
    KEY_DERIVATION = "PBKDF2-SHA256"
    KEY_ITERATIONS = 600_000

    async def store(self, colony_id: str, key: str, value: str) -> None: ...
    async def retrieve(self, colony_id: str, key: str) -> str: ...
    async def rotate(self, colony_id: str, key: str) -> str: ...
    async def audit_log(self, colony_id: str, action: str, key: str) -> None: ...
```

---

## 10. Directory Structure (Target)

```
ai-multicolony/
├── apps/
│   ├── orchestrator/         # LangGraph top-level orchestration
│   │   ├── graph.py          # Main orchestration graph
│   │   ├── router.py         # Colony routing logic
│   │   └── api.py            # REST/gRPC API
│   ├── runtime/              # Colony runtime (shared base)
│   │   ├── colony.py         # Colony lifecycle manager
│   │   ├── agent_pool.py     # Agent spawning and management
│   │   └── health.py         # Health monitoring
│   ├── agents/               # Agent implementations
│   │   ├── base.py           # BaseAgent class
│   │   ├── coding/           # Coding colony agents
│   │   ├── research/         # Research colony agents
│   │   ├── trading/          # Trading colony agents
│   │   ├── ops/              # Operations colony agents
│   │   └── creative/         # Creative colony agents
│   ├── memory/               # Memory subsystem
│   │   ├── working.py        # L1: Working memory
│   │   ├── episodic.py       # L2: Episodic (Letta/MemGPT)
│   │   ├── semantic.py       # L3: Semantic (Qdrant + Memory Tree)
│   │   ├── procedural.py     # L4: Procedural (skills)
│   │   └── compression.py    # TokenJuice compression
│   ├── tools/                # MCP tool servers
│   │   ├── browser/          # CloakBrowser MCP server
│   │   ├── computer-use/     # open-computer-use MCP server
│   │   ├── api/              # Composio + public-apis MCP server
│   │   ├── code/             # Code execution MCP server
│   │   └── filesystem/       # File system MCP server
│   ├── browser/              # CloakBrowser integration
│   │   ├── patches/          # Chromium C++ patches
│   │   ├── stealth/          # Anti-detection config
│   │   └── mcp_server.py     # MCP interface
│   ├── computer-use/         # GUI automation
│   │   ├── capture/          # Screen capture (Swift)
│   │   ├── input/            # Mouse/keyboard (Go)
│   │   └── mcp_server.py     # MCP interface
│   ├── planner/              # Task planning (DSPy)
│   │   ├── decomposer.py     # Task decomposition
│   │   ├── optimizer.py      # Prompt optimization
│   │   └── evaluator.py      # Plan evaluation
│   ├── orchestrator/         # Orchestration logic
│   │   ├── langgraph/        # LangGraph graphs
│   │   ├── a2a/              # A2A protocol
│   │   └── scheduler.py      # Task scheduling
│   ├── skills/               # Skill system
│   │   ├── registry.py       # Skill registry
│   │   ├── loader.py         # Dynamic skill loader
│   │   ├── builtin/          # Built-in skills
│   │   └── community/        # Community skills
│   ├── knowledge/            # Knowledge management
│   │   ├── ingest.py         # Document ingestion
│   │   ├── index.py          # Qdrant indexing
│   │   ├── offline.py        # project-nomad integration
│   │   └── rag.py            # RAG retrieval
│   └── docs/                 # Documentation
│       ├── architecture/
│       ├── api/
│       └── operations/
├── infra/
│   ├── docker/               # Docker files
│   ├── k8s/                  # Kubernetes manifests
│   ├── terraform/            # Infrastructure as code
│   └── monitoring/           # Prometheus + Grafana
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── pyproject.toml
├── Cargo.toml                # Rust components (openfang)
├── Makefile
└── README.md
```

---

## 11. Data Flow: Task Execution

### 11.1 End-to-End Task Flow

```
User Request
     │
     ▼
┌──────────┐     ┌──────────────┐     ┌──────────────┐
│ API      │────►│ Orchestrator │────►│ Task         │
│ Gateway  │     │ (LangGraph)  │     │ Decomposer   │
└──────────┘     └──────┬───────┘     └──────┬───────┘
                        │                     │
                 ┌──────▼──────┐       ┌──────▼──────┐
                 │ Colony      │       │ Sub-tasks   │
                 │ Router      │       │ Queue       │
                 └──────┬──────┘       └──────┬──────┘
                        │                     │
          ┌─────────────┼─────────────┐       │
          ▼             ▼             ▼       │
   ┌────────────┐┌────────────┐┌────────────┐│
   │ Colony A   ││ Colony B   ││ Colony C   ││
   │ ┌────────┐ ││ ┌────────┐ ││ ┌────────┐ ││
   │ │Agent 1 │◄├┤►│Agent 1 │◄├┤►│Agent 1 │◄┘
   │ │        │ ││ │        │ ││ │        │
   │ │Tool ──►│ ││ │Tool ──►│ ││ │Tool ──►│
   │ │MCP     │ ││ │MCP     │ ││ │MCP     │
   │ │Memory─►│ ││ │Memory─►│ ││ │Memory─►│
   │ └────────┘ ││ └────────┘ ││ └────────┘ │
   └────────────┘└────────────┘└────────────┘
          │             │             │
          └─────────────┼─────────────┘
                        ▼
                 ┌──────────────┐
                 │ Result       │
                 │ Aggregator   │
                 └──────┬───────┘
                        │
                        ▼
                 ┌──────────────┐
                 │ Response     │
                 │ to User      │
                 └──────────────┘
```

### 11.2 Timeout and Retry Strategy

```python
TASK_TIMEOUT_CONFIG = {
    "default": 300,           # 5 minutes
    "coding": 600,            # 10 minutes (code generation)
    "research": 900,          # 15 minutes (web research)
    "trading": 60,            # 1 minute (time-sensitive)
    "ops": 1200,              # 20 minutes (deployment)
}

RETRY_STRATEGY = {
    "llm_failure": {"max_retries": 3, "backoff": "exponential", "jitter": True},
    "tool_failure": {"max_retries": 2, "backoff": "linear"},
    "colony_failure": {"max_retries": 1, "backoff": "fixed", "delay": 30},
    "sandbox_failure": {"max_retries": 1, "action": "restart_container"},
}
```

---

## 12. Security Architecture

### 12.1 Security Layers

| Layer | Mechanism | Source |
|---|---|---|
| Network | TLS 1.3, mTLS between colonies | openfang (16 security layers) |
| Transport | Protocol Buffer encryption | openfang |
| Application | PydanticAI input validation | Primary stack |
| Agent sandboxing | Docker/Webscale/E2B isolation | ai-manus, OpenHands |
| Tool access | MCP permission model | MCP protocol |
| Memory access | Colony-scoped access control | Custom |
| Credentials | AES-256-GCM encryption at rest | AI-MultiColony-Ecosystem |
| Audit | Comprehensive logging | openfang (2543+ tests) |

### 12.2 Agent Permission Model

```python
class AgentPermission(BaseModel):
    """Inspired by openfang's 16 security layers"""
    agent_id: str
    colony_id: str

    # Tool permissions
    allowed_tools: list[str] = Field(default_factory=list)
    denied_tools: list[str] = Field(default_factory=list)
    tool_timeout_seconds: int = 60

    # Network permissions
    allowed_domains: list[str] = Field(default_factory=list)
    denied_domains: list[str] = Field(default_factory=list)
    network_access: bool = False

    # File system permissions
    allowed_paths: list[str] = Field(default_factory=list)
    write_access: bool = False
    execute_access: bool = False

    # Resource limits
    max_memory_mb: int = 512
    max_cpu_seconds: int = 300
    max_file_size_mb: int = 10

    # LLM limits
    max_llm_calls_per_minute: int = 30
    max_tokens_per_call: int = 4096
```

---

## 13. Monitoring and Observability

```python
# Metrics collected at each layer
METRICS = {
    "ecosystem": [
        "total_active_colonies",
        "total_active_agents",
        "task_throughput_per_minute",
        "task_latency_p50_p95_p99",
        "error_rate_by_colony_type",
    ],
    "colony": [
        "colony_agent_count",
        "colony_memory_usage_tokens",
        "colony_tool_calls_per_minute",
        "colony_task_queue_depth",
    ],
    "agent": [
        "agent_execution_time",
        "agent_llm_tokens_used",
        "agent_tool_success_rate",
        "agent_state_transitions",
    ],
    "infrastructure": [
        "container_cpu_usage",
        "container_memory_usage",
        "redis_stream_lag",
        "qdrant_query_latency",
    ],
}

# Tracing: OpenTelemetry with LangGraph integration
TRACING_CONFIG = {
    "exporter": "otlp",
    "endpoint": "http://jaeger:4317",
    "sampling_rate": 0.1,  # 10% in production
    "langgraph_integration": True,
}
```

---

## 14. Configuration Management

```python
# config/ecosystem.yaml
ecosystem:
  name: "ai-multicolony"
  version: "0.1.0"

  defaults:
    llm_provider: "openai"
    llm_model: "gpt-4o"
    memory_backend: "qdrant"
    message_bus: "redis"
    sandbox_provider: "e2b"

  colonies:
    coding:
      max_agents: 8
      memory_budget: 200000
      security_level: "sandboxed"
      tools: ["filesystem", "code-execution", "browser", "composio"]
    research:
      max_agents: 6
      memory_budget: 150000
      security_level: "sandboxed"
      tools: ["browser", "composio", "filesystem"]
    trading:
      max_agents: 10
      memory_budget: 300000
      security_level: "elevated"
      tools: ["composio", "filesystem", "code-execution"]

  providers:
    openai:
      api_key_env: "OPENAI_API_KEY"
      models: ["gpt-4o", "gpt-4o-mini"]
      rate_limit: 100  # requests per minute
    anthropic:
      api_key_env: "ANTHROPIC_API_KEY"
      models: ["claude-sonnet-4-20250514"]
      rate_limit: 60
```

---

## Appendix A: Technology Stack Summary

| Layer | Technology | Justification |
|---|---|---|
| Orchestration | LangGraph | Subgraph=colony, native Python, stateful |
| Tool Interface | MCP | Industry standard, transport-agnostic |
| Validation | PydanticAI | Type-safe, integrates with LangGraph |
| Memory | Letta/MemGPT | Layered memory, conversation management |
| Semantic Store | Qdrant | From agentcloud, Rust-based, fast |
| Memory Tree | openhuman | Hierarchical memory, 118+ integrations |
| Communication | A2A Protocol | Inter-agent standard, Google-backed |
| Message Bus | Redis Streams | Reliable, consumer groups, low latency |
| Optimization | DSPy | Prompt optimization, programmatic |
| Sandboxing | E2B/Daytona | Secure code execution, isolation |
| Browser | CloakBrowser | 58 C++ patches, production stealth |
| GUI Automation | open-computer-use | MCP-native, Swift+Go+TS |
| Frontend | Next.js + ReactFlow | From sim, visual workflow builder |
| Runtime | Docker + K8s | Industry standard, scalable |
| Encryption | AES-256-GCM | From AI-MultiColony, proven |
| API Gateway | FastAPI | Python, async, OpenAPI |

## Appendix B: Repository Contribution Map

| Repo | Contribution | Target Module |
|---|---|---|
| AI-MultiColony-Ecosystem | Agent modules, LLM failover, credentials | apps/agents/, apps/runtime/ |
| OpenManus | ReAct agent, browser agent, SWE agent | apps/agents/coding/ |
| OpenHands | SWE-bench agent, code act, enterprise | apps/agents/coding/ |
| openfang | Security layers, channel adapters, WASM sandbox | apps/runtime/ (security) |
| agentcloud | CrewAI backend, Qdrant RAG, UI | apps/memory/, apps/knowledge/ |
| agenticSeek | Local Manus, voice interface, browser | apps/agents/research/ |
| ai-manus | Docker sandbox, VNC, code execution | apps/tools/code/ |
| nanobot | Ultra-lightweight agent core | apps/agents/base.py |
| suna | Full platform, runtime, UI | apps/runtime/, apps/agents/ |
| sim | Visual workflow builder, ReactFlow | apps/orchestrator/ (UI) |
| oh-my-claudecode | Agent router, skills, 28 agents | apps/orchestrator/, apps/skills/ |
| superpowers | Skill methodology, TDD-first | apps/skills/ |
| public-apis | 1400+ API catalog | apps/knowledge/ |
| public-ip-address | IP geolocation library | apps/tools/api/ |
| open-lovable | AI→React app builder | apps/agents/creative/ |
| CloakBrowser | Stealth Chromium, 58 patches | apps/browser/ |
| open-computer-use | MCP GUI automation | apps/computer-use/ |
| nanocode | Minimal agent loop | apps/agents/base.py (reference) |
| openhuman | Memory tree, TokenJuice, integrations | apps/memory/ |
| project-nomad-offline | Offline knowledge server | apps/knowledge/offline/ |
