# JEUMPA - AI Intelligence Orchestration Layer

Jeumpa is a **AI Operating Intelligence Layer** designed to be the infrastructure behind intelligence, not a chatbot or LLM wrapper.

## Core Architecture

### 1. Single Interface, Hidden Complexity

```
User
  ↓
Jeumpa API (Single Entry)
  ↓
Decision Engine
  ↓
├── Planner (Task Decomposition)
├── Router (Optimize Workflows)
├── Agent Manager (Supervise Execution)
└── Persistence Layer (Knowledge Graph)
  ↓
Adapters (Plugin System)
  ↓
Model Pool (Capability Registry)
  ↓
Responses
```

### 2. Key Components

#### Decision Engine (Core)
- **Purpose**: Orchestrate tasks, select optimal adapters
- **Not**: LLM-bound, prompt-based routing
- **Decides**: which model, when, how, via capabilities matching

#### Planner
- **Task**: Decompose user requests into executable steps
- **Output**: Task DAG (Directed Acyclic Graph)

#### Router  
- **Task**: Optimize workflows
- **Considers**: Cost, quality, latency, health, capabilities
- **Output**: Execution plan

#### Agent Manager
- **Task**: Supervise agent execution
- **Features**: Lifecycle, state persistence, inter-agent comms, quotas

#### Persistence Layer
- **Episodic**: Conversation history, task traces
- **Semantic**: Knowledge graph, entities, relationships  
- **Procedural**: Skills, workflows, best practices

### 3. Adapter Pattern

```
Adapters (Plugins) - Provider-Agnostic
├── OpenAI Compatible (80% coverage)
├── Local Ollama (Zero cost, always available)
├── Pollinations (Free, no auth)
├── LM Studio (Local inference)
├── Web Chat Wrappers (Playwright)
└── Custom Adapters
```

#### Adapter Interface
```python
class ProviderAdapter(ABC):
    @abstractmethod
    def adapter_id(self) -> str: pass
    
    @abstractmethod  
    def display_name(self) -> str: pass
    
    @abstractmethod
    async def list_models(self) -> List[ModelInfo]: pass
    
    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse: pass
    
    @abstractmethod
    async def health_check(self) -> HealthStatus: pass
```

### 4. Model Pool (Capability Registry)

```python
@dataclass
class ModelInfo:
    id: str                    # "gpt-4o-mini", "llama3.1:8b", etc.
    name: str                  # Human readable
    provider: str             # Adapter identifier
    capabilities: List[str]   # ["coding", "reasoning", "fast", "free"]
    context_window: int
    cost_per_1k_input: float   # $/1k tokens
    cost_per_1k_output: float
    latency_p50_ms: float
    supports_tools: bool = False
    supports_streaming: bool = False
```

### 5. Lazy Runtime

```
Runtime Lifecycle:
1. invoke → "jeumpa invoke <prompt>"
2. spawn process (background)
3. serve requests
4. idle timeout (10min default) → graceful shutdown
5. zero RAM when inactive
```

### 6. Configuration-Driven

```yaml
adapters:
  # OpenAI Compatible (covers most providers)
  - id: "openai-compat"
    type: "openai_compatible"
    enabled: true
    priority: 10
    
  # Local Ollama (always available, zero cost)
  - id: "ollama"
    type: "ollama"
    enabled: true
    priority: 5
    
  # Pollinations (free, no auth)
  - id: "pollinations"
    type: "pollinations"
    enabled: true
    priority: 50

models:
  preferences:
    - task: "coding"
      prefer: ["deepseek-coder", "qwen2.5-coder", "gpt-4o-mini"]
      max_cost_per_1k: 0.001
      
    - task: "reasoning"
      prefer: ["gpt-4o", "claude-3.5-sonnet", "gemini-1.5-pro"]
      max_cost_per_1k: 0.01
      
    - task: "fast"
      prefer: ["llama3.1:8b", "gpt-4o-mini"]
      max_latency_ms: 2000
      
    - task: "free"
      prefer: ["pollinations:*", "ollama:*", "openrouter:free"]
      max_cost_per_1k: 0.0001
```

### 7. Integration with Hermes (Fallback Layer)

```python
# Hermes auto-invokes Jeumpa when inference needed
jeumpa = JeumpaClient()

async def hermes_needs_llm(prompt: str, task_type: str = "general"):
    response = await jeumpa.chat_blocking(
        messages=[{"role": "user", "content": prompt}],
        task_type=task_type
    )
    return response
```

---

## Implementation Status

### ✅ Completed
1. Architecture design and interface definition
2. Adapter registry system prototype  
3. Lazy runtime lifecycle concept
4. Configuration schema for provider-agnostic orchestration
5. Model capability registry design
6. Hermes integration approach

### 🔄 In Progress
1. Core Decision Engine implementation
2. Adapter specific implementations (OpenAI Compatible, Ollama)
3. End-to-end workflow testing
4. Health monitoring and circuit breaker systems
5. Task execution and agent supervision

### 📋 Pending
1. Pollinations adapter implementation
2. Web Chat adapter (Playwright-based)
3. Persistence layer (Episodic, Semantic, Procedural)
4. Documentation and developer guides
5. CI/CD pipeline and testing suite

---

## Project Structure

```
jeumpa/
├── jeumpa/
│   ├── __init__.py                    # Core package
│   ├── adapters/                      # Adapter plugin system
│   │   ├── __init__.py
│   │   ├── base.py                    # ProviderAdapter interface
│   │   ├── openai_compat.py
│   │   ├── ollama.py
│   │   └── pollinations.py
│   ├── core/                          # Decision Engine components
│   │   ├── __init__.py
│   │   ├── decision_engine.py
│   │   ├── planner.py
│   │   └── router.py
│   ├── persistence/                   # Knowledge graph system
│   │   ├── __init__.py
│   │   ├── episodic.py
│   │   ├── semantic.py
│   │   └── procedural.py
│   └── runtime/                       # Lifecycle and execution
│       ├── __init__.py
│       ├── lifecycle.py
│       └── server.py
│
├── integrations/
│   ├── __init__.py
│   └── hermes.py
│
├── config/
│   └── jeumpa.yaml.template
│
├── docs/
│   ├── architecture.md
│   ├── adapter_dev_guide.md
│   └── usage_examples.md
│
└── tests/
    ├── test_adapters.py
    ├── test_lifecycle.py
    └── integration_test.py
```

## Key Success Metrics

| Metric | Target |
|--------|--------|
| **Idle RAM** | <10MB when no requests |
| **Startup Time** | <2 seconds |
| **Provider Resolution** | <500ms P99 latency |
| **Cost Efficiency** | 70% cheaper than OpenAI standard |
| **Uptime** | 99.9% (health checks, auto-restart) |
| **Provider Tolerance** | Works even if 3/4 adapters fail |

---

## Next Steps

1. **Design Decision Engine Core** - Orchestrator logic
2. **Implement Adapter Systems** - OpenAI Compatible, Ollama
3. **Build Persistence Layer** - Episodic, Semantic, Procedural
4. **Create Integration Tests** - End-to-end workflows
5. **Document API** - Usage guides for developers

Jeumpa will be the **undetectable intelligence layer** that makes AI inference look like magic to users, while being production-grade infrastructure for providers.
