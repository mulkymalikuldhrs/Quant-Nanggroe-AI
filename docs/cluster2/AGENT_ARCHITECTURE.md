# AI-MultiColony-Ecosystem — Agent Architecture

> Cluster 2 Agent Architecture Document
> Version: 0.1.0-draft | Status: Pre-Implementation | Classification: Internal

---

## 1. Overview

This document defines the unified agent architecture for the AI-MultiColony-Ecosystem.
It merges agent models from 19+ repositories into a coherent taxonomy, lifecycle,
communication pattern, and security model. The design prioritizes composability over
inheritance, explicit contracts over implicit behavior, and observable state machines
over ad-hoc transitions.

---

## 2. Agent Taxonomy

### 2.1 Classification Dimensions

Agents are classified along three axes:

1. **Framework Layer**: Where the agent sits in the hierarchy
2. **Capability Type**: What the agent can do
3. **Autonomy Level**: How independently the agent operates

### 2.2 Framework Agent Taxonomy

```
                    FRAMEWORK AGENTS
                    (infrastructure-provided)
    ┌──────────────────┬──────────────────┐
    │                  │                  │
 ORCHESTRATOR      COLONY           RUNTIME
    AGENTS            AGENTS           AGENTS
    │                  │                  │
    ├─ Router Agent    ├─ Coordinator     ├─ Health Monitor
    ├─ Scheduler       ├─ Task Planner   ├─ Resource Manager
    ├─ Load Balancer   ├─ Memory Mgr     ├─ Log Collector
    └─ Audit Agent     └─ Handoff Mgr    └─ Metrics Agent
```

### 2.3 Colony Agent Taxonomy

```
                    COLONY AGENTS
                    (task-executing)
    ┌──────────┬──────────┬──────────┬──────────┐
    │          │          │          │          │
  CODING    RESEARCH   TRADING    OPS      CREATIVE
    │          │          │          │          │
    ├─ Code    ├─ Search  ├─ Market  ├─ Deploy  ├─ Writer
    │  Writer  │  Agent   │  Analyst ├─ Monitor ├─ Designer
    ├─ Code    ├─ Scraper ├─ Risk    ├─ Debug   ├─ Artist
    │  Reviewer│          │  Manager ├─ Backup  ├─ Video
    ├─ Debugger├─ Analyst ├─ Exec    ├─ Scale   │  Editor
    │          ├─ Summar. │  Trader  ├─ Sec.    ├─ Audio
    ├─ Refactor├─ Fact    │          │  Audit   │  Producer
    │  Agent   │  Checker ├─ Portfolio│         └─ UI
    ├─ Test    ├─ Citation│  Manager ├─ Incident│  Builder
    │  Writer  │  Finder  │          │  Responder│
    └─ Doc     └─ Transl. └─ Compli. └─ Change   └─ Template
       Writer     Agent       Officer   Manager      Designer
```

### 2.4 Specialist Agent Taxonomy

```
                 SPECIALIST AGENTS
                 (cross-colony, single-capability)
    ┌──────────┬──────────┬──────────┬──────────┐
    │          │          │          │          │
  BROWSER   COMPUTER   LLM        DATA      COMM
  SPECIALIST  USE      REASONER   PIPELINE  AGENT
    │          │          │          │          │
    ├─ Nav     ├─ Screen  ├─ Code    ├─ ETL     ├─ Email
    ├─ Click   ├─ Mouse   ├─ Reason ├─ Clean   ├─ Slack
    ├─ Type    ├─ Keybd   ├─ Plan    ├─ Transform├─ Teams
    ├─ Extract ├─ Window  ├─ Summar. ├─ Validate├─ Discord
    └─ Stealth └─ Multi-  └─ Critique└─ Load    └─ Webhook
                  Monitor                    Distrib.
```

### 2.5 Complete Agent Registry

| Agent ID | Type | Colony | Source Repo | Autonomy | Priority |
|---|---|---|---|---|---|
| `orch.router` | Framework | — | oh-my-claudecode | Semi | P0 |
| `orch.scheduler` | Framework | — | sim | Semi | P0 |
| `col.coord` | Framework | Per-colony | OpenHands | Semi | P0 |
| `col.handoff` | Framework | Per-colony | OpenAI Agents SDK | Auto | P0 |
| `code.writer` | Colony | Coding | OpenHands (CodeActAgent) | Semi | P1 |
| `code.reviewer` | Colony | Coding | OpenManus (SWEAgent) | Auto | P1 |
| `code.debugger` | Colony | Coding | OpenHands (BrowsingAgent) | Semi | P1 |
| `code.refactor` | Colony | Coding | OpenManus (ReActAgent) | Semi | P2 |
| `code.tester` | Colony | Coding | OpenHands | Auto | P1 |
| `code.doc_writer` | Colony | Coding | nanocode | Auto | P2 |
| `res.search` | Colony | Research | agenticSeek | Auto | P1 |
| `res.scraper` | Colony | Research | CloakBrowser | Auto | P1 |
| `res.analyst` | Colony | Research | AI-MultiColony (agents) | Semi | P1 |
| `res.summarizer` | Colony | Research | agenticSeek | Auto | P2 |
| `res.fact_checker` | Colony | Research | — (new) | Semi | P2 |
| `res.citation` | Colony | Research | — (new) | Auto | P3 |
| `res.translator` | Colony | Research | AI-MultiColony (agents) | Auto | P3 |
| `trd.market_analyst` | Colony | Trading | AI-MultiColony (agents) | Semi | P1 |
| `trd.risk_manager` | Colony | Trading | AI-MultiColony (agents) | Auto | P0 |
| `trd.executor` | Colony | Trading | AI-MultiColony (agents) | Supervised | P0 |
| `trd.portfolio` | Colony | Trading | AI-MultiColony (agents) | Semi | P1 |
| `trd.compliance` | Colony | Trading | — (new) | Auto | P1 |
| `ops.deployer` | Colony | Ops | openfang | Semi | P1 |
| `ops.monitor` | Colony | Ops | openfang | Auto | P1 |
| `ops.debugger` | Colony | Ops | OpenHands | Semi | P1 |
| `ops.scaler` | Colony | Ops | — (new) | Auto | P2 |
| `ops.sec_audit` | Colony | Ops | openfang (16 layers) | Auto | P1 |
| `ops.incident` | Colony | Ops | — (new) | Semi | P1 |
| `crt.writer` | Colony | Creative | suna | Semi | P2 |
| `crt.designer` | Colony | Creative | open-lovable | Auto | P2 |
| `crt.ui_builder` | Colony | Creative | open-lovable | Semi | P2 |
| `sp.browser` | Specialist | Cross | CloakBrowser | Auto | P0 |
| `sp.computer_use` | Specialist | Cross | open-computer-use | Auto | P1 |
| `sp.llm_reasoner` | Specialist | Cross | — (DSPy) | Auto | P1 |
| `sp.data_pipeline` | Specialist | Cross | agentcloud | Semi | P2 |
| `sp.comm` | Specialist | Cross | nanobot | Auto | P2 |

---

## 3. Agent Lifecycle

### 3.1 State Machine

```
                    ┌────────────┐
                    │  SPAWNING  │
                    └─────┬──────┘
                          │ Load config, allocate resources,
                          │ register with colony, init memory
                          ▼
                    ┌────────────┐
              ┌────►│ CONFIGURING│
              │     └─────┬──────┘
              │           │ Load skills, bind tools,
              │           │ connect MCP servers
              │           ▼
              │     ┌────────────┐
              │     │   READY    │◄────────────────────┐
              │     └─────┬──────┘                      │
              │           │ Task assigned               │
              │           ▼                             │
              │     ┌────────────┐                      │
              │     │ EXECUTING  │──── Task complete ───►│
              │     └─────┬──────┘                      │
              │           │                             │
              │     ┌─────┴──────┐                      │
              │     │            │                      │
              │     ▼            ▼                      │
              │  ┌────────┐  ┌────────┐                │
              │  │WAITING │  │LEARNING│                │
              │  │(input/ │  │(reflect│                │
              │  │ tool)  │  │,adapt) │                │
              │  └───┬────┘  └───┬────┘                │
              │      │           │                      │
              │      └─────┬─────┘                      │
              │            │                            │
              │            ▼                            │
              │     ┌────────────┐   Timeout/resource   │
              │     │ HIBERNATING│─── release ──────────►│
              │     └─────┬──────┘                      │
              │           │ Wake signal                 │
              │           ▼                             │
              │     ┌────────────┐                      │
              └─────│  FAILED    │─── Reconfigure ──────►│
         Retry?    └─────┬──────┘                      │
                          │ Max retries exceeded        │
                          ▼                             │
                    ┌────────────┐                      │
                    │TERMINATING │──────────────────────┘
                    └────────────┘   Cleanup, deregister
```

### 3.2 Lifecycle Phases Detail

#### SPAWNING
```python
class SpawningPhase:
    """
    Duration: 100ms - 5s
    Resources allocated: Agent ID, memory budget, tool bindings
    Failure mode: Resource unavailable → queue for retry
    """
    async def execute(self, config: AgentConfig) -> Agent:
        # 1. Generate unique agent ID
        agent_id = f"{config.agent_type}.{config.colony_id}.{uuid4().hex[:8]}"

        # 2. Allocate memory budget from colony pool
        memory_allocated = await self.memory_manager.allocate(
            colony_id=config.colony_id,
            budget=config.memory_budget
        )

        # 3. Register with colony agent pool
        await self.colony.register_agent(agent_id, config)

        # 4. Initialize agent process
        agent = BaseAgent(config=config)
        agent.state = AgentState.SPAWNING

        # 5. Log spawn event
        await self.audit.log("agent_spawned", agent_id=agent_id)

        return agent
```

#### CONFIGURING
```python
class ConfiguringPhase:
    """
    Duration: 500ms - 10s
    Actions: Load skills, bind MCP tools, connect memory, set LLM provider
    Failure mode: Tool unavailable → degrade gracefully, log warning
    """
    async def execute(self, agent: BaseAgent) -> BaseAgent:
        # 1. Bind tools via MCP
        for tool_name in agent.config.tools:
            try:
                tool = await self.mcp_client.bind_tool(tool_name)
                agent.bound_tools[tool_name] = tool
            except MCPConnectionError:
                agent.degraded_tools.append(tool_name)
                await self.audit.log("tool_bind_failed", tool=tool_name)

        # 2. Load skills from registry
        for skill_name in agent.config.skills:
            skill = await self.skill_registry.load(skill_name)
            agent.skills[skill_name] = skill

        # 3. Connect to memory store
        agent.memory_handle = await self.memory_manager.connect(
            agent_id=agent.config.agent_id,
            colony_id=agent.config.colony_id
        )

        # 4. Configure LLM provider with failover chain
        agent.llm_client = await self.llm_factory.create(
            provider=agent.config.llm_provider,
            model=agent.config.llm_model,
            failover_chain=LLM_FAILOVER_CHAINS.get(
                agent.config.agent_type, "default"
            )
        )

        agent.state = AgentState.READY
        return agent
```

#### EXECUTING
```python
class ExecutingPhase:
    """
    Duration: Variable (1s - 10min based on task)
    Core agent loop: observe → think → act → observe
    Failure mode: LLM timeout → retry with backoff
    """
    async def execute(self, agent: BaseAgent, task: Task) -> TaskResult:
        agent.state = AgentState.EXECUTING
        steps = 0
        max_steps = task.max_steps or 50

        while steps < max_steps:
            # 1. Observe: Get current state
            observation = await self.observe(agent, task)

            # 2. Think: LLM reasoning step
            thought = await agent.llm_client.reason(
                system_prompt=agent.system_prompt,
                context=observation,
                tools=agent.bound_tools,
                max_tokens=agent.config.max_tokens,
            )

            # 3. Act: Execute tool calls or return result
            if thought.tool_calls:
                results = await self.execute_tools(agent, thought.tool_calls)
                agent.context.add_tool_results(results)
            elif thought.final_answer:
                agent.state = AgentState.READY
                return TaskResult(
                    task_id=task.task_id,
                    agent_id=agent.config.agent_id,
                    output=thought.final_answer,
                    steps=steps,
                    tokens_used=agent.llm_client.total_tokens,
                )

            # 4. Memory update: Store episodic memory
            await self.memory_manager.store_episodic(
                agent_id=agent.config.agent_id,
                step=steps,
                observation=observation,
                thought=thought,
            )

            steps += 1
            agent.execution_count += 1

        # Max steps exceeded
        agent.state = AgentState.FAILED
        return TaskResult(task_id=task.task_id, status="max_steps_exceeded")
```

#### LEARNING
```python
class LearningPhase:
    """
    Duration: 1s - 30s
    Actions: Reflect on task outcome, update episodic memory,
             extract procedural knowledge (skills), optimize prompts
    Trigger: After task completion or failure
    """
    async def execute(self, agent: BaseAgent, result: TaskResult) -> None:
        agent.state = AgentState.LEARNING

        # 1. Task outcome reflection
        reflection = await agent.llm_client.reason(
            system_prompt=LEARNING_PROMPT,
            context={
                "task": result.task_id,
                "outcome": result.status,
                "steps": result.steps,
                "tokens_used": result.tokens_used,
            }
        )

        # 2. Store reflection in episodic memory
        await self.memory_manager.store_episodic(
            agent_id=agent.config.agent_id,
            type="reflection",
            content=reflection,
        )

        # 3. Extract procedural knowledge if pattern detected
        if result.status == "success" and result.steps < 5:
            skill_candidate = await self.skill_extractor.extract(
                task=result.task_description,
                steps=result.step_log,
                outcome="success"
            )
            if skill_candidate:
                await self.skill_registry.register_candidate(skill_candidate)

        # 4. Update agent performance metrics
        agent.performance.update(result)

        agent.state = AgentState.READY
```

### 3.3 Lifecycle Configuration Per Agent Type

| Agent Type | Spawn Time | Max Execution | Learning | Hibernate After | Max Retries |
|---|---|---|---|---|---|
| Framework | 1s | N/A (long-running) | Never | Never | 3 |
| Colony (Coding) | 2s | 10min | On completion | 30min idle | 3 |
| Colony (Research) | 2s | 15min | On completion | 30min idle | 3 |
| Colony (Trading) | 1s | 1min | On completion | 5min idle | 2 |
| Colony (Ops) | 3s | 20min | On completion | 60min idle | 2 |
| Colony (Creative) | 2s | 15min | On completion | 30min idle | 2 |
| Specialist | 1s | 5min | Never | 15min idle | 3 |

---

## 4. Agent Communication Patterns

### 4.1 Communication Topology

```
                    ┌─────────────┐
                    │ Orchestrator│
                    └──────┬──────┘
                           │ (command/control)
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼─────┐┌────▼─────┐┌────▼─────┐
        │ Colony A   ││ Colony B ││ Colony C │
        │ ┌───┐ ┌───┐││ ┌───┐   ││ ┌───┐   │
        │ │A1 │◄►│A2 │││ │B1 │   ││ │C1 │   │
        │ └─┬─┘ └─┬─┘││ └─┬─┘   ││ └─┬─┘   │
        │   │     │  ││   │     ││   │     │
        │ ┌─▼─┐ ┌─▼─┐││ ┌─▼─┐   ││ ┌─▼─┐   │
        │ │A3 │◄►│A4 │││ │B2 │   ││ │C2 │   │
        │ └───┘ └───┘││ └───┘   ││ └───┘   │
        └─────────────┘└─────────┘└─────────┘

  Patterns:
  A1◄──►A2  : Peer-to-peer (within colony)
  A1──►A3   : Hierarchical (delegation)
  A1◄──►B1  : Cross-colony (via A2A)
  Orch──►All : Broadcast (system messages)
```

### 4.2 Communication Patterns Reference

| Pattern | Direction | Protocol | Use Case | Latency Target |
|---|---|---|---|---|
| **Peer-to-Peer** | Agent ↔ Agent (same colony) | Internal Bus | Collaborative tasks | <10ms |
| **Hierarchical** | Parent → Child | Internal Bus | Task delegation | <10ms |
| **Handoff** | Agent → Agent (cross-colony) | A2A | Context transfer | <100ms |
| **Broadcast** | Orchestrator → All | Redis Pub/Sub | System announcements | <50ms |
| **Request-Response** | Agent → Tool | MCP | Tool invocation | <1s |
| **Streaming** | Agent → User | SSE | Real-time output | <100ms |
| **Event** | Agent → Monitor | Redis Stream | Telemetry | <10ms |

### 4.3 Message Envelope

```python
class AgentMessage(BaseModel):
    """Unified message format for all agent communication"""
    message_id: str = Field(default_factory=lambda: uuid4().hex)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Routing
    sender: AgentRef
    recipient: AgentRef  # "broadcast" for broadcast
    reply_to: Optional[str] = None  # message_id for correlation

    # Content
    message_type: Literal[
        "task_assign", "task_result", "query", "response",
        "handoff", "notification", "error", "heartbeat"
    ]
    payload: dict[str, Any]

    # Metadata
    priority: Literal["low", "normal", "high", "critical"] = "normal"
    ttl_seconds: int = 3600
    trace_id: Optional[str] = None  # OpenTelemetry trace
    colony_id: Optional[str] = None

class AgentRef(BaseModel):
    """Reference to an agent or agent group"""
    agent_id: str  # or "*" for broadcast within colony
    colony_id: str
    agent_type: Optional[str] = None
```

### 4.4 Conversation Patterns

#### Simple Task Delegation
```
Coordinator                Worker Agent
    │                          │
    │── task_assign ──────────►│
    │                          │── (executing)
    │                          │── (tool calls)
    │                          │── (tool results)
    │◄── task_result ──────────│
    │                          │
```

#### Collaborative Task (Multi-Agent)
```
Coordinator      Worker A      Worker B
    │                │             │
    │── task_assign ─►│             │
    │                 │── query ───►│
    │                 │◄── response─│
    │                 │── (working) │
    │                 │── handoff ─►│
    │                 │             │── (working)
    │◄── task_result ──────────────│
    │                │             │
```

#### Cross-Colony Handoff
```
Colony A               A2A Bus              Colony B
  │                      │                      │
  │── A2A handoff ──────►│                      │
  │   (context, task)    │── A2A handoff ──────►│
  │                      │                      │── (executing)
  │                      │◄── A2A result ───────│
  │◄── A2A result ──────││                      │
  │                      │                      │
```

---

## 5. Agent Capability Registry

### 5.1 Capability Model

```python
class AgentCapability(BaseModel):
    """Declarative capability description"""
    capability_id: str
    name: str
    description: str
    input_schema: dict  # JSON Schema
    output_schema: dict  # JSON Schema
    required_tools: list[str]
    required_skills: list[str]
    memory_requirements: dict  # {"working": 4000, "episodic": 10000}
    autonomy_level: Literal["supervised", "semi", "auto"]
    estimated_duration_seconds: tuple[int, int]  # (min, max)
    cost_estimate: dict  # {"llm_tokens": 1000, "tool_calls": 3}
```

### 5.2 Capability Registration

```python
class CapabilityRegistry:
    """
    Central registry for agent capabilities.
    Agents declare capabilities; the orchestrator discovers and routes.
    """

    async def register(self, agent_id: str, capability: AgentCapability) -> None:
        """Register a capability for an agent"""
        ...

    async def discover(self, requirement: dict) -> list[AgentCapability]:
        """Find agents that match a requirement specification"""
        ...

    async def verify(self, agent_id: str, capability_id: str) -> bool:
        """Verify an agent still has the declared capability"""
        ...
```

### 5.3 Capability Matrix

| Capability | code.writer | code.reviewer | res.search | trd.executor | sp.browser |
|---|---|---|---|---|---|
| `code.generate` | ✅ | — | — | — | — |
| `code.review` | — | ✅ | — | — | — |
| `code.debug` | ✅ | ✅ | — | — | — |
| `code.test` | ✅ | — | — | — | — |
| `code.refactor` | ✅ | ✅ | — | — | — |
| `web.search` | — | — | ✅ | — | ✅ |
| `web.scrape` | — | — | ✅ | — | ✅ |
| `web.navigate` | — | — | — | — | ✅ |
| `web.stealth` | — | — | — | — | ✅ |
| `data.analyze` | — | — | ✅ | ✅ | — |
| `trade.execute` | — | — | — | ✅ | — |
| `trade.risk` | — | — | — | ✅ | — |
| `gui.interact` | — | — | — | — | ✅ |
| `doc.write` | ✅ | — | ✅ | — | — |
| `api.call` | ✅ | — | ✅ | ✅ | — |

---

## 6. Agent Sandboxing and Security Model

### 6.1 Sandbox Architecture

```
┌───────────────────────────────────────────────┐
│                    HOST                        │
│  ┌─────────────────────────────────────────┐  │
│  │           Colony Runtime                 │  │
│  │  ┌───────────────────────────────────┐  │  │
│  │  │        Agent Process              │  │  │
│  │  │  ┌─────────────────────────────┐  │  │  │
│  │  │  │     Sandbox Container       │  │  │  │
│  │  │  │  (E2B / Daytona / Docker)   │  │  │  │
│  │  │  │                             │  │  │  │
│  │  │  │  ┌─────────┐ ┌───────────┐  │  │  │  │
│  │  │  │  │ Code    │ │ File      │  │  │  │  │
│  │  │  │  │ Runtime │ │ System    │  │  │  │  │
│  │  │  │  └─────────┘ └───────────┘  │  │  │  │
│  │  │  │  ┌─────────┐ ┌───────────┐  │  │  │  │
│  │  │  │  │ Network │ │ Process   │  │  │  │  │
│  │  │  │  │ (proxy) │ │ Monitor   │  │  │  │  │
│  │  │  │  └─────────┘ └───────────┘  │  │  │  │
│  │  │  └─────────────────────────────┘  │  │  │
│  │  └───────────────────────────────────┘  │  │
│  └─────────────────────────────────────────┘  │
└───────────────────────────────────────────────┘

Security layers (inspired by openfang's 16 security layers):
1. Network isolation (no direct internet, proxy only)
2. File system isolation (chroot/namespace)
3. Process isolation (PID namespace)
4. Memory limits (cgroups)
5. CPU limits (cgroups)
6. IPC isolation
7. Device access restriction
8. Syscall filtering (seccomp)
9. Capabilities dropping
10. Read-only rootfs
11. Resource quotas
12. Network egress filtering
13. Temporary filesystem (/tmp size limit)
14. User namespace (non-root)
15. WASM sandbox for untrusted code
16. Audit logging
```

### 6.2 Security Levels

```python
class SecurityLevel(str, Enum):
    SANDBOXED = "sandboxed"      # No host access, all tools proxied
    ELEVATED = "elevated"        # Limited host access (e.g., read-only FS)
    PRIVILEGED = "privileged"    # Full host access (ops agents only)

SECURITY_PROFILES = {
    SecurityLevel.SANDBOXED: {
        "network": "proxy_only",
        "filesystem": "sandbox_only",
        "process": "isolated",
        "tools": "whitelist",
        "max_memory_mb": 512,
        "max_cpu_seconds": 300,
        "syscall_filter": "strict",
    },
    SecurityLevel.ELEVATED: {
        "network": "filtered",
        "filesystem": "read_only_host",
        "process": "isolated",
        "tools": "whitelist_extended",
        "max_memory_mb": 2048,
        "max_cpu_seconds": 600,
        "syscall_filter": "moderate",
    },
    SecurityLevel.PRIVILEGED: {
        "network": "full",
        "filesystem": "full_host",
        "process": "shared",
        "tools": "all",
        "max_memory_mb": 4096,
        "max_cpu_seconds": 3600,
        "syscall_filter": "none",
    },
}
```

### 6.3 Security Level Assignment

| Agent Type | Default Security Level | Justification |
|---|---|---|
| Framework agents | ELEVATED | Need system access for coordination |
| Coding agents | SANDBOXED | Code execution must be isolated |
| Research agents | SANDBOXED | Browser access must be proxied |
| Trading agents | ELEVATED | Need API access to exchanges |
| Ops agents | PRIVILEGED | Need full system access for deployment |
| Creative agents | SANDBOXED | Limited to output generation |
| Browser specialist | SANDBOXED | Stealth browser in isolated container |
| Computer-use specialist | ELEVATED | Needs screen access |

---

## 7. Agent Handoff Protocols

### 7.1 Handoff Model (Inspired by OpenAI Agents SDK)

```python
class AgentHandoff(BaseModel):
    """
    Structured handoff between agents.
    Based on OpenAI Agents SDK guardrail model with additions
    for colony context and memory transfer.
    """
    handoff_id: str = Field(default_factory=lambda: uuid4().hex)
    from_agent: str
    to_agent: str
    from_colony: str
    to_colony: str

    # Context transfer
    task_context: dict[str, Any]        # Current task state
    conversation_summary: str           # Summarized conversation
    pending_tool_calls: list[dict]      # Unfinished tool invocations
    memory_references: list[str]        # IDs of relevant memories

    # Capability requirements
    required_capabilities: list[str]    # What the receiving agent must support
    required_tools: list[str]          # What tools the receiving agent needs
    required_security_level: SecurityLevel

    # Handoff metadata
    reason: str                         # Why the handoff is happening
    urgency: Literal["low", "normal", "high", "critical"] = "normal"
    auto_accept: bool = False          # Can the target auto-accept?
    timeout_seconds: int = 300
```

### 7.2 Handoff Flow

```
Agent A (source)                   Handoff Manager                    Agent B (target)
     │                                  │                                  │
     │── handoff_request ──────────────►│                                  │
     │   (context, capabilities)        │                                  │
     │                                  │── capability_check ──────────────►│
     │                                  │◄── capability_match ──────────────│
     │                                  │                                  │
     │                                  │── handoff_offer ─────────────────►│
     │                                  │                                  │
     │                                  │        ┌─── Guardrails ───┐      │
     │                                  │        │ Input validation │      │
     │                                  │        │ Context check    │      │
     │                                  │        │ Security review  │      │
     │                                  │        └──────────────────┘      │
     │                                  │                                  │
     │                                  │◄── handoff_accept ───────────────│
     │                                  │                                  │
     │── context_transfer ──────────────│── context_deliver ──────────────►│
     │                                  │                                  │
     │◄── handoff_complete ─────────────│                                  │
     │                                  │                                  │
     │  (Agent A: READY)                │                    (Agent B: EXECUTING)
```

### 7.3 Guardrail System

```python
class HandoffGuardrail(BaseModel):
    """
    Safety checks for agent handoffs.
    Inspired by OpenAI Agents SDK guardrails.
    """
    guardrail_id: str
    name: str
    check_type: Literal["input", "output", "context", "security"]

    async def check(self, handoff: AgentHandoff) -> GuardrailResult:
        """Returns PASS, FAIL, or REQUIRES_REVIEW"""
        ...

class GuardrailResult(BaseModel):
    status: Literal["pass", "fail", "requires_review"]
    reason: Optional[str] = None
    suggested_alternative: Optional[str] = None

# Built-in guardrails
BUILTIN_GUARDRAILS = {
    "context_size": ContextSizeGuardrail(max_tokens=16000),
    "security_escalation": SecurityEscalationGuardrail(),
    "pii_check": PIIDetectionGuardrail(),
    "tool_permission": ToolPermissionGuardrail(),
    "colony_boundary": ColonyBoundaryGuardrail(),
    "cost_limit": CostLimitGuardrail(max_cost_per_handoff=1.00),
}
```

---

## 8. Repository-to-Architecture Mapping

### 8.1 Agent Contributions by Repository

#### AI-MultiColony-Ecosystem (Core)
```
Contributes: 36 agent modules, 7 LLM providers, AES-256 credentials
Mapping:
  agents/1-10  →  apps/agents/trading/   (market agents)
  agents/11-20 →  apps/agents/research/  (analysis agents)
  agents/21-30 →  apps/agents/ops/       (system agents)
  agents/31-36 →  apps/agents/creative/  (content agents)
  credentials  →  apps/runtime/vault.py
  llm_failover →  apps/runtime/llm_factory.py
```

#### Agentic-AI-System_OLD (Archived)
```
Contributes: 10 agents (PoC reference only)
Mapping: Design patterns archived, not directly merged
Status: ARCHIVED - reference only for backward compatibility
```

#### OpenManus
```
Contributes: ReActAgent, BrowserAgent, SWEAgent
Mapping:
  ReActAgent   →  apps/agents/base.py (reasoning loop pattern)
  BrowserAgent →  apps/agents/research/res.scraper.py
  SWEAgent     →  apps/agents/coding/code.reviewer.py
  MCP client   →  apps/tools/ (MCP integration pattern)
  A2A client   →  apps/orchestrator/a2a/
```

#### OpenHands
```
Contributes: 5 agent types, SWE-Bench 77.6%, enterprise features
Mapping:
  CodeActAgent     →  apps/agents/coding/code.writer.py
  BrowsingAgent    →  apps/agents/coding/code.debugger.py
  PlannerAgent     →  apps/planner/decomposer.py
  JupyterAgent     →  apps/tools/code/mcp_server.py (jupyter mode)
  ConversationImpl →  apps/runtime/conversation.py
  SandboxManager   →  apps/runtime/sandbox.py
```

#### openfang
```
Contributes: 14 crates, 2543+ tests, 16 security layers, 40 channel adapters
Mapping:
  security layers   →  apps/runtime/security/ (Python wrappers)
  channel adapters   →  apps/tools/api/adapters/ (protocol translation)
  WASM sandbox       →  apps/runtime/sandbox_wasm.py
  test patterns      →  tests/unit/ (test methodology reference)
  Note: Rust crates remain as separate services, accessed via gRPC
```

#### agentcloud
```
Contributes: CrewAI backend, Qdrant RAG, Next.js UI
Mapping:
  CrewAI backend  →  apps/agents/ (crew coordination pattern)
  Qdrant RAG      →  apps/memory/semantic.py
  Next.js UI      →  apps/orchestrator/ (dashboard component)
  Note: AGPL license requires careful isolation (see RISK_REGISTER.md)
```

#### agenticSeek
```
Contributes: 100% local Manus alternative, voice, Selenium browser
Mapping:
  Local execution pattern →  apps/runtime/local_runner.py
  Voice interface         →  apps/agents/research/voice_input.py
  Selenium browser        →  apps/tools/browser/ (fallback for CloakBrowser)
```

#### ai-manus
```
Contributes: Docker sandbox with VNC, code execution
Mapping:
  Docker sandbox  →  apps/runtime/sandbox.py (Docker provider)
  VNC viewer      →  apps/browser/vnc_viewer.py
  Code execution  →  apps/tools/code/mcp_server.py
```

#### nanobot
```
Contributes: Ultra-lightweight ~4K LOC, Telegram/WhatsApp
Mapping:
  Core agent loop →  apps/agents/base.py (minimal reference)
  Telegram adapter→  apps/tools/api/adapters/telegram.py
  WhatsApp adapter→  apps/tools/api/adapters/whatsapp.py
```

#### suna
```
Contributes: Full platform, Docker runtime, web+desktop+mobile
Mapping:
  Platform shell  →  apps/orchestrator/ (UI components)
  Docker runtime  →  apps/runtime/ (Docker management)
  Note: KPSL license requires isolation (see RISK_REGISTER.md)
```

#### sim
```
Contributes: Visual workflow builder (ReactFlow), SDKs
Mapping:
  ReactFlow builder →  apps/orchestrator/ui/ (workflow editor)
  TypeScript SDKs   →  apps/orchestrator/sdk/
  Graph executor    →  apps/orchestrator/langgraph/ (visual→LangGraph)
```

#### oh-my-claudecode
```
Contributes: Claude Code plugin, 28 agents, 30 skills
Mapping:
  Agent router  →  apps/orchestrator/router.py
  28 agents     →  apps/agents/ (reference implementations)
  30 skills     →  apps/skills/builtin/ (skill definitions)
  Plugin system →  apps/skills/loader.py
```

#### superpowers
```
Contributes: Platform-agnostic methodology, TDD-first, skill format
Mapping:
  SKILL.md format  →  apps/skills/registry.py (canonical format)
  TDD methodology  →  tests/ (test strategy)
  Skill templates  →  apps/skills/builtin/ (template reference)
```

#### CloakBrowser
```
Contributes: Stealth Chromium, 58 C++ patches
Mapping:
  Chromium patches →  apps/browser/patches/
  Stealth config   →  apps/browser/stealth/
  MCP interface    →  apps/tools/browser/mcp_server.py
```

#### open-computer-use
```
Contributes: MCP GUI automation (Swift+Go+TS)
Mapping:
  Swift capture  →  apps/computer-use/capture/
  Go input       →  apps/computer-use/input/
  TS MCP server  →  apps/tools/computer-use/mcp_server.py
```

#### nanocode
```
Contributes: Minimal agent loop (~250 LOC)
Mapping:
  Agent loop →  apps/agents/base.py (minimal reference implementation)
  Note: PoC only, not production code
```

#### openhuman (from Cluster 1)
```
Contributes: Memory tree, TokenJuice, 118+ integrations
Mapping:
  Memory tree    →  apps/memory/semantic.py (tree structure)
  TokenJuice     →  apps/memory/compression.py
  Integrations   →  apps/tools/api/adapters/ (118+ adapters)
```

#### project-nomad-offline (from Cluster 1)
```
Contributes: Offline knowledge server (AdonisJS)
Mapping:
  Knowledge server →  apps/knowledge/offline/ (offline RAG)
  Note: AdonisJS → Python/FastAPI rewrite for unified stack
```

### 8.2 Agent Deduplication Strategy

| Agent Role | Overlapping Repos | Chosen Primary | Rationale |
|---|---|---|---|
| Code writer | OpenHands, OpenManus, nanocode | OpenHands (CodeActAgent) | SWE-Bench 77.6% |
| Browser agent | OpenManus, agenticSeek, CloakBrowser | CloakBrowser | 58 C++ patches, production |
| SWE agent | OpenManus, OpenHands | OpenHands | Better benchmark scores |
| General agent | nanobot, nanocode, AI-MultiColony | nanobot core + AI-MultiColony modules | Minimal core + modular extensions |
| Coordinator | agentcloud (CrewAI), oh-my-claudecode | LangGraph + oh-my-claudecode router | Native subgraph support |
| Voice agent | agenticSeek | agenticSeek | Only voice implementation |

---

## 9. Agent Testing Strategy

### 9.1 Test Pyramid

```
        ┌─────────────┐
        │   E2E Tests │   ← Full colony simulation
        │   (5%)      │      Real LLM calls, real tools
        ├─────────────┤
        │ Integration │   ← Agent + MCP + Memory
        │   (15%)     │      Mocked LLM, real infrastructure
        ├─────────────┤
        │  Unit Tests │   ← Agent logic in isolation
        │   (80%)     │      All external deps mocked
        └─────────────┘
```

### 9.2 Agent Benchmark Suite

```python
AGENT_BENCHMARKS = {
    "code_generation": {
        "dataset": "HumanEval+",
        "metrics": ["pass@1", "pass@10", "tokens_per_solution"],
        "baseline": "OpenHands CodeActAgent",
    },
    "code_review": {
        "dataset": "SWE-Bench Lite",
        "metrics": ["resolved_rate", "avg_steps", "avg_cost"],
        "baseline": "OpenHands (77.6%)",
    },
    "web_research": {
        "dataset": "GAIA Benchmark",
        "metrics": ["accuracy", "completeness", "time_seconds"],
        "baseline": "Manual benchmark",
    },
    "browser_automation": {
        "dataset": "WebArena",
        "metrics": ["success_rate", "steps", "detection_rate"],
        "baseline": "CloakBrowser",
    },
}
```

---

## Appendix A: Agent Template Reference

```python
# Template for creating a new agent
AGENT_TEMPLATE = """
# Agent: {agent_name}
# Colony: {colony_type}
# Autonomy: {autonomy_level}

class {ClassName}(BaseAgent):
    \"\"\"Agent description\"\"\"

    CAPABILITIES = [
        AgentCapability(
            capability_id="{agent_id}.{capability}",
            name="{capability_name}",
            description="{capability_description}",
            input_schema={{ ... }},
            output_schema={{ ... }},
            required_tools=[{tools}],
            required_skills=[{skills}],
            autonomy_level="{autonomy_level}",
        ),
    ]

    SYSTEM_PROMPT = \"\"\"
    You are a {role_description}.
    You have access to the following tools: {tool_list}
    You must follow these rules:
    1. {rule_1}
    2. {rule_2}
    \"\"\"

    async def execute(self, task: Task) -> TaskResult:
        # Implementation
        ...
"""
```

## Appendix B: LLM Provider Configuration Per Agent Type

| Agent Type | Primary Provider | Primary Model | Fallback Chain |
|---|---|---|---|
| code.writer | anthropic | claude-sonnet-4-20250514 | openai → deepseek → google |
| code.reviewer | openai | gpt-4o | anthropic → google → deepseek |
| code.debugger | anthropic | claude-sonnet-4-20250514 | openai → deepseek |
| res.search | google | gemini-2.0-flash | openai → groq → ollama |
| res.analyst | openai | gpt-4o | anthropic → google |
| trd.market_analyst | openai | gpt-4o | anthropic → google |
| trd.executor | groq | llama-3.3-70b | openai → deepseek |
| trd.risk_manager | anthropic | claude-sonnet-4-20250514 | openai → google |
| ops.deployer | openai | gpt-4o | anthropic → ollama |
| ops.monitor | groq | llama-3.3-70b | deepseek → ollama |
| crt.writer | anthropic | claude-sonnet-4-20250514 | openai → google |
| crt.ui_builder | openai | gpt-4o | anthropic → google |
| sp.browser | google | gemini-2.0-flash | groq → deepseek |
| sp.computer_use | google | gemini-2.0-flash | openai → groq |
