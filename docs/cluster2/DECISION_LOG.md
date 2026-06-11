# AI-MultiColony-Ecosystem — Decision Log

> Cluster 2 Evidence-Based Decision Record
> Version: 0.1.0-draft | Status: Pre-Implementation | Classification: Internal

---

## 1. Overview

This document records all architectural, framework, and integration decisions for
Cluster 2 of the AI-MultiColony-Ecosystem mega-merge. Each decision follows the
ADMR (Architecture Decision Metadata Record) format with evidence, alternatives,
and consequences.

**Decision ID format**: `C2-{NNN}` where NNN is sequential.

---

## 2. Repository Disposition Decisions

### C2-001: Keep AI-MultiColony-Ecosystem as Core Repository

| Field | Value |
|---|---|
| **Decision** | AI-MultiColony-Ecosystem serves as the foundational repository for the unified project |
| **Context** | Need a primary codebase to merge into. AI-MultiColony-Ecosystem already has 36 agent modules, 7 LLM providers with failover, AES-256 credentials, and a Flask-based runtime |
| **Alternatives** | (A) Start from scratch, (B) Use OpenHands as base, (C) Use AI-MultiColony-Ecosystem |
| **Evidence** | AI-MultiColony-Ecosystem is the only repo with: (1) multi-agent architecture already, (2) LLM failover chain, (3) credential management, (4) Alpha status with active development. OpenHands is more mature but single-agent focused. Starting from scratch wastes existing code. |
| **Rationale** | AI-MultiColony-Ecosystem already implements the colony model conceptually (36 agents grouped by function). Its LLM failover chain and credential system are production-grade patterns we need. Flask → FastAPI migration is straightforward. |
| **Consequences** | Positive: Faster time-to-first-build, existing agent modules provide reference implementations. Negative: Flask needs migration to FastAPI, some Alpha-quality code needs hardening, test coverage is minimal. |
| **Status** | Accepted |

---

### C2-002: Archive Agentic-AI-System_OLD

| Field | Value |
|---|---|
| **Decision** | Agentic-AI-System_OLD is archived for reference only, no code merged |
| **Context** | This is the predecessor to AI-MultiColony-Ecosystem with 10 agents in PoC state |
| **Alternatives** | (A) Merge useful patterns, (B) Archive entirely, (C) Selectively port code |
| **Evidence** | The repo is explicitly marked as OLD. 10 agents are a subset of AI-MultiColony's 36. Code quality is PoC with no tests. No unique functionality not present in the newer repo. |
| **Rationale** | Zero unique value. Any useful patterns are already refined in AI-MultiColony-Ecosystem. Porting PoC code introduces tech debt. |
| **Consequences** | Positive: No legacy code maintenance burden. Negative: Lose historical context (mitigated by keeping repo in read-only archive). |
| **Status** | Accepted |

---

### C2-003: Adopt OpenHands Agent Architecture for Coding Colony

| Field | Value |
|---|---|
| **Decision** | OpenHands CodeActAgent becomes the primary agent for the Coding colony |
| **Context** | Multiple coding agents exist: OpenHands (5 types, SWE-Bench 77.6%), OpenManus (ReAct/Browser/SWE), nanocode (~250 LOC), AI-MultiColony agents |
| **Alternatives** | (A) OpenHands CodeActAgent, (B) OpenManus SWEAgent, (C) Custom from nanocode, (D) Hybrid |
| **Evidence** | SWE-Bench verified results: OpenHands 77.6% (industry-leading), OpenManus < 50% (no official benchmark). OpenHands has 5 agent types covering coding, browsing, planning. Enterprise features (RBAC, audit). 36K+ GitHub stars, active community. |
| **Rationale** | OpenHands provides the strongest baseline for coding tasks with verified benchmarks. Its CodeActAgent pattern (code-as-action) is more effective than ReAct for software engineering. The 5-agent-type model maps well to our colony agents. |
| **Consequences** | Positive: Best-in-class coding agent, proven benchmarks, enterprise features. Negative: OpenHands is opinionated (Docker sandbox, specific LLM integration), Python-only, heavy dependency. Need to extract agent logic from OpenHands' runtime. |
| **Status** | Accepted |

---

### C2-004: Integrate openfang Security as Service Layer

| Field | Value |
|---|---|
| **Decision** | openfang's 16 security layers and 40 channel adapters are integrated as independent services accessed via gRPC, not as inline Python code |
| **Context** | openfang is written in Rust (14 crates, 2543+ tests). The ecosystem is Python-based. Direct Rust integration requires PyO3 bindings or process isolation |
| **Alternatives** | (A) PyO3 bindings (inline), (B) gRPC services (separate), (C) Rewrite in Python, (D) Port only security policies |
| **Evidence** | Rust→Python via PyO3 adds deployment complexity (Rust toolchain required). gRPC provides clean isolation, language-agnostic interface. Rewriting 14 crates of Rust in Python loses performance and test coverage (2543+ tests). Porting only policies loses channel adapter functionality. |
| **Rationale** | gRPC keeps Rust components as separate microservices that can be deployed, scaled, and versioned independently. Python agents call security and channel adapter functions via gRPC. This preserves openfang's test coverage and performance while keeping the Python ecosystem clean. |
| **Consequences** | Positive: Rust components run at native speed, isolated deployment, preserved test coverage. Negative: Additional infrastructure (gRPC services), network latency for security checks (~5ms), operational complexity of managing Rust services alongside Python. |
| **Status** | Accepted |

---

### C2-005: Isolate agentcloud Components Due to AGPL License

| Field | Value |
|---|---|
| **Decision** | agentcloud's AGPL-licensed components are isolated in a separate service boundary. Only the Qdrant RAG patterns and UI components are adapted (not copied) |
| **Context** | agentcloud is licensed under AGPL-3.0, which requires any derivative work to also be AGPL. Our target license is MIT/Apache-2.0 |
| **Alternatives** | (A) Fork and re-license (impossible under AGPL), (B) Use as separate AGPL service, (C) Adapt patterns without copying code, (D) Exclude entirely |
| **Evidence** | AGPL-3.0 Section 13: "any modified version" must be licensed under AGPL. Network use constitutes distribution under AGPL. Qdrant itself is Apache-2.0. CrewAI is MIT. The RAG patterns are standard and not unique to agentcloud. |
| **Rationale** | The valuable parts of agentcloud (Qdrant RAG patterns, CrewAI orchestration) are either standard patterns or available under permissive licenses. We implement our own Qdrant integration and CrewAI backend without copying agentcloud code. The Next.js UI components can't be used; we build our own. |
| **Consequences** | Positive: No license contamination, clean MIT/Apache-2.0 codebase. Negative: More development effort for Qdrant integration and UI, can't use agentcloud's ready-made components. |
| **Status** | Accepted |

---

### C2-006: Isolate suna Components Due to KPSL License

| Field | Value |
|---|---|
| **Decision** | suna is excluded from code merge. Only architectural patterns are referenced |
| **Context** | suna uses KPSL (Khoj Personal Software License), a non-standard license that restricts commercial use and requires separate terms for business use |
| **Alternatives** | (A) Negotiate commercial license, (B) Reference patterns only, (C) Rewrite needed features, (D) Include with license compliance |
| **Evidence** | KPSL is not OSI-approved and has ambiguous commercial terms. The runtime patterns (Docker management, desktop/mobile shell) are well-understood and can be reimplemented. The AI orchestration is standard LangChain/CrewAI patterns. No unique algorithm or approach. |
| **Rationale** | The license risk outweighs the code value. Suna's contributions (platform shell, Docker runtime) are commodity patterns that can be implemented from scratch in a week. The legal uncertainty of KPSL is unacceptable for a project that may be commercialized. |
| **Consequences** | Positive: Zero license risk, clean IP. Negative: Additional development time for platform shell (~1 week), Docker runtime management (~3 days). |
| **Status** | Accepted |

---

### C2-007: Adopt CloakBrowser as Primary Browser Engine

| Field | Value |
|---|---|
| **Decision** | CloakBrowser is the primary browser engine, replacing agenticSeek's Selenium and OpenManus's Playwright defaults |
| **Context** | Three browser solutions exist: CloakBrowser (58 C++ patches, stealth), agenticSeek (Selenium, basic), OpenManus (Playwright, standard) |
| **Alternatives** | (A) CloakBrowser only, (B) Playwright default + CloakBrowser stealth mode, (C) Selenium for compatibility, (D) Multi-engine with auto-selection |
| **Evidence** | CloakBrowser is the only production-grade stealth browser with 58 C++ patches. It supports anti-detection for canvas, WebGL, navigator, timezone, WebRTC, audio, fonts, screen, plugins, battery, and hardware concurrency. Production status indicates stability. Selenium is deprecated for modern web automation. Playwright is good but lacks stealth. |
| **Rationale** | Research agents need stealth browsing to avoid bot detection on target sites. CloakBrowser provides this out of the box. For non-stealth scenarios, CloakBrowser's underlying Playwright still works normally. Having one browser engine simplifies maintenance. |
| **Consequences** | Positive: Single browser engine, production stealth, reduced maintenance. Negative: CloakBrowser requires Chromium build from source (build time ~2h), larger Docker image (~2GB for browser), macOS/Linux only (no Windows). |
| **Status** | Accepted |

---

### C2-008: Use nanobot Core as Minimal Agent Reference

| Field | Value |
|---|---|
| **Decision** | nanobot's ~4K LOC core is used as the reference implementation for BaseAgent, not as the actual agent runtime |
| **Context** | nanobot is ultra-lightweight (~4K LOC) with Telegram/WhatsApp adapters. nanocode is even smaller (~250 LOC) |
| **Alternatives** | (A) Use nanobot code directly, (B) Use as reference only, (C) Use nanocode, (D) Build from scratch |
| **Evidence** | nanobot's core loop is clean and well-structured, but it's designed for single-purpose chatbot agents. It lacks: multi-agent coordination, memory management, tool integration, sandboxing. The ~4K LOC doesn't include the features we need. nanocode's ~250 LOC is too minimal even as reference. |
| **Rationale** | nanobot's agent loop pattern (observe → think → act) is the correct minimal model. We adopt the pattern and implement it with our full feature set (MCP tools, memory layers, skill activation, security). The actual implementation is a superset. |
| **Consequences** | Positive: Clean conceptual model, simple mental model for BaseAgent. Negative: Still need to build the full agent runtime from scratch. |
| **Status** | Accepted |

---

### C2-009: Rewrite project-nomad-offline from AdonisJS to Python

| Field | Value |
|---|---|
| **Decision** | project-nomad-offline's offline knowledge server functionality is rewritten in Python/FastAPI |
| **Context** | project-nomad-offline is written in AdonisJS (TypeScript). The unified ecosystem is Python-based |
| **Alternatives** | (A) Run as separate Node.js service, (B) Rewrite in Python, (C) Exclude offline functionality |
| **Evidence** | Running a separate Node.js service for one feature adds operational complexity (Node.js runtime, npm dependencies, separate deployment). The offline knowledge server is conceptually simple (local RAG + document storage). Python has equivalent libraries (FastAPI + sentence-transformers + SQLite). |
| **Rationale** | Maintaining a single runtime language (Python) significantly reduces operational complexity. The offline server is a small component that doesn't benefit from Node.js's strengths. Rewriting takes ~3 days for equivalent functionality. |
| **Consequences** | Positive: Single runtime language, unified deployment. Negative: 3 days of rewrite effort, may miss edge cases from AdonisJS implementation. |
| **Status** | Accepted |

---

### C2-010: Keep open-computer-use as Cross-Platform Service

| Field | Value |
|---|---|
| **Decision** | open-computer-use (Swift+Go+TS) runs as a separate service with MCP interface |
| **Context** | open-computer-use uses Swift (macOS screen capture), Go (input simulation), and TypeScript (MCP server). It's inherently platform-specific |
| **Alternatives** | (A) Separate service with MCP, (B) Python-only rewrite, (C) Include as optional dependency |
| **Evidence** | Swift and Go components use platform-specific APIs (CGWindowListCreateImage, CGEvent) with no Python equivalents. Rewriting would lose the native performance and reliability. The MCP interface already provides clean abstraction. |
| **Rationale** | Computer-use is a specialist capability that not all deployments need. Running it as a separate MCP service allows: (1) platform-specific deployment, (2) optional installation, (3) clean isolation. The MCP interface means agents don't need to know the implementation language. |
| **Consequences** | Positive: Clean MCP interface, platform-optimized, optional deployment. Negative: Requires macOS for full functionality, multiple language toolchains in development, additional service to manage. |
| **Status** | Accepted |

---

## 3. Architecture Pattern Decisions

### C2-011: Adopt LangGraph for Orchestration

| Field | Value |
|---|---|
| **Decision** | LangGraph is the primary orchestration framework |
| **Context** | Need a framework for defining agent workflows with state management, branching, and cycles |
| **Alternatives** | (A) LangGraph, (B) CrewAI, (C) AutoGen, (D) Custom state machine, (E) Temporal |
| **Evidence** | LangGraph: Native subgraph support (maps to colony model), built-in state management, Python-native, integrates with LangChain ecosystem, supports cycles (agent loops), 9K+ GitHub stars. CrewAI: Simpler, but limited workflow complexity. AutoGen: Conversation-focused, no subgraph concept. Custom: Maximum flexibility, maximum development time. Temporal: Overkill for agent orchestration, Go-based. |
| **Rationale** | LangGraph's subgraph feature directly maps to our colony model. Each colony is a subgraph with its own state. The orchestrator is the top-level graph. Native Python integration means no language boundary. LangGraph's checkpointing provides automatic state persistence. |
| **Consequences** | Positive: Subgraph=colony mapping, Python-native, state checkpointing, active community. Negative: LangChain dependency (heavy), LangGraph is still evolving (breaking changes), learning curve for LangGraph's graph model, performance overhead for graph execution. |
| **Status** | Accepted |

---

### C2-012: Adopt MCP as Universal Tool Interface

| Field | Value |
|---|---|
| **Decision** | All tools are exposed via Model Context Protocol (MCP) |
| **Context** | Need a standard interface for agent-tool communication |
| **Alternatives** | (A) MCP, (B) OpenAI function calling, (C) Custom REST API, (D) gRPC |
| **Evidence** | MCP is emerging as the industry standard for agent-tool communication. Anthropic, OpenHands, and OpenManus all support MCP. It provides: transport abstraction (stdio/SSE/HTTP), schema validation (JSON Schema), capability negotiation, and server composition. OpenAI function calling is provider-locked. Custom REST lacks standardization. gRPC is overkill for tool calls. |
| **Rationale** | MCP provides the right abstraction level for tools. It's provider-agnostic (works with any LLM), transport-flexible (stdio for local, SSE for remote), and schema-driven (input/output validation). The growing MCP ecosystem means we can leverage existing tool servers. |
| **Consequences** | Positive: Industry standard, growing ecosystem, transport-agnostic. Negative: MCP is still evolving (spec changes), some overhead vs direct function calls, limited streaming support. |
| **Status** | Accepted |

---

### C2-013: Adopt PydanticAI for Validation

| Field | Value |
|---|---|
| **Decision** | PydanticAI is used for type-safe agent I/O validation |
| **Context** | Need type safety and validation for agent inputs, outputs, and tool calls |
| **Alternatives** | (A) PydanticAI, (B) Raw Pydantic, (C) msgspec, (D) No validation |
| **Evidence** | PydanticAI extends Pydantic with LLM-specific features: structured output parsing, tool call validation, dependency injection, and streaming support. It integrates with LangGraph. Raw Pydantic lacks LLM integration. msgspec is faster but less feature-rich. No validation leads to runtime errors. |
| **Rationale** | PydanticAI provides the bridge between LLM text output and structured Python types. It validates tool call arguments, agent outputs, and dependency graphs. Integration with LangGraph means we get type safety throughout the orchestration pipeline. |
| **Consequences** | Positive: Type safety, LLM integration, LangGraph compatibility. Negative: Additional dependency, PydanticAI is relatively new (may have bugs), validation overhead. |
| **Status** | Accepted |

---

### C2-014: Adopt A2A Protocol for Inter-Colony Communication

| Field | Value |
|---|---|
| **Decision** | Google's A2A (Agent-to-Agent) protocol is used for cross-colony communication |
| **Context** | Need a standard for agent-to-agent communication across colony boundaries |
| **Alternatives** | (A) A2A Protocol, (B) Custom message bus, (C) gRPC direct calls, (D) Shared database |
| **Evidence** | A2A is Google's proposed standard for inter-agent communication. It provides: message envelope, handoff protocol, capability discovery, and security model. OpenManus already has A2A support. Custom message bus requires designing a protocol from scratch. gRPC is transport-level only. Shared database creates coupling. |
| **Rationale** | A2A provides the standard that the industry is converging on. It already handles the key use cases (handoff, discovery, security). Having A2A support means compatibility with other A2A-implementing systems. |
| **Consequences** | Positive: Industry standard, cross-system compatibility, OpenManus already implements it. Negative: A2A is still a draft specification (may change), Google-driven (not community-governed), limited real-world deployments to learn from. |
| **Status** | Accepted |

---

### C2-015: Use DSPy for Prompt Optimization

| Field | Value |
|---|---|
| **Decision** | DSPy is used for programmatic prompt optimization and procedural memory extraction |
| **Context** | Need to optimize LLM prompts and extract reusable procedures from agent executions |
| **Alternatives** | (A) DSPy, (B) Manual prompt engineering, (C) LangSmith evaluation, (D) No optimization |
| **Evidence** | DSPy provides: automatic prompt optimization (MIPROv2), few-shot example selection, module composition, and evaluation metrics. It's the only framework that treats prompts as programmable artifacts. Manual prompt engineering doesn't scale. LangSmith is evaluation-only. No optimization leaves performance on the table. |
| **Rationale** | DSPy's programmatic approach to prompt optimization is essential for an agent ecosystem where each agent type needs different prompts. As agents execute tasks, DSPy can optimize their prompts based on outcomes. This creates a feedback loop that improves agent performance over time. |
| **Consequences** | Positive: Automated prompt optimization, measurable improvement, procedural memory extraction. Negative: DSPy has a learning curve, optimization runs consume LLM tokens (cost), optimization is batch (not real-time). |
| **Status** | Accepted |

---

## 4. Framework Choice Decisions

### C2-016: FastAPI Over Flask for Runtime

| Field | Value |
|---|---|
| **Decision** | Migrate from Flask (AI-MultiColony-Ecosystem) to FastAPI for the runtime API |
| **Context** | AI-MultiColony-Ecosystem uses Flask. Need async support for concurrent agent operations |
| **Alternatives** | (A) Keep Flask, (B) Migrate to FastAPI, (C) Use Django, (D) Use Litestar |
| **Evidence** | FastAPI: Native async/await, automatic OpenAPI docs, Pydantic integration, WebSocket support, 77K+ GitHub stars. Flask: No native async (Flask 2.x added limited async), no Pydantic integration, simpler but less capable for concurrent workloads. Django: Overkill for API-only service. Litestar: Good but smaller community. |
| **Rationale** | The ecosystem needs concurrent request handling (multiple agents, tools, and colonies operating simultaneously). FastAPI's native async support and Pydantic integration align perfectly with our stack (PydanticAI, MCP). The migration from Flask is mechanical (route decorators → APIRouter, request parsing → Pydantic models). |
| **Consequences** | Positive: Async support, OpenAPI docs, Pydantic integration, WebSocket support. Negative: Migration effort (~2-3 days), Flask extensions need replacement, team learning curve for FastAPI patterns. |
| **Status** | Accepted |

---

### C2-017: Redis Streams for Internal Message Bus

| Field | Value |
|---|---|
| **Decision** | Redis Streams with consumer groups for the internal message bus |
| **Context** | Need reliable message delivery between agents within and across colonies |
| **Alternatives** | (A) Redis Streams, (B) RabbitMQ, (C) Apache Kafka, (D) NATS, (E) ZeroMQ |
| **Evidence** | Redis Streams: Consumer groups for reliable delivery, lightweight (already using Redis for caching), sub-ms latency, simple ops. RabbitMQ: More features but heavier, separate deployment. Kafka: Overkill for agent messaging, high latency for small messages. NATS: Good but less common, additional deployment. ZeroMQ: No persistence, no consumer groups. |
| **Rationale** | We're already deploying Redis for caching and session storage. Redis Streams adds reliable messaging without additional infrastructure. Consumer groups ensure each message is delivered to exactly one consumer per group. The latency profile (<5ms) meets our requirements. |
| **Consequences** | Positive: No additional infrastructure, sub-ms latency, consumer groups, familiar Redis ops. Negative: Redis Streams has message retention limits, not designed for very high throughput (millions of msgs/sec), single Redis point of failure (mitigated by Redis Cluster). |
| **Status** | Accepted |

---

### C2-018: Qdrant for Vector Storage

| Field | Value |
|---|---|
| **Decision** | Qdrant is the primary vector storage engine for semantic memory |
| **Context** | Need vector storage for semantic memory (L3) and knowledge base |
| **Alternatives** | (A) Qdrant, (B) Pinecone, (C) Weaviate, (D) Milvus, (E) pgvector |
| **Evidence** | Qdrant: Rust-based (fast), supports filtering, on-premise or cloud, agentcloud already uses it, Apache-2.0 license. Pinecone: Cloud-only, not self-hostable, costs scale with data. Weaviate: Good but heavier, Go-based. Milvus: Complex deployment, designed for larger scale. pgvector: Simpler but less performant, ties vectors to PostgreSQL. |
| **Rationale** | Qdrant is already validated by agentcloud's RAG implementation. It's Rust-based (performance), self-hostable (no vendor lock-in), supports filtering (for path-based queries), and has a simple API. The HNSW index provides fast approximate nearest neighbor search. |
| **Consequences** | Positive: Fast, self-hosted, filterable, already validated. Negative: Separate service to deploy, Qdrant's own learning curve, migration needed if scaling beyond single-node. |
| **Status** | Accepted |

---

## 5. Integration Approach Decisions

### C2-019: Gradual Merge Strategy Over Big Bang

| Field | Value |
|---|---|
| **Decision** | Merge repositories gradually over 6 phases, not all at once |
| **Context** | 19+ repositories need to be merged into a unified codebase |
| **Alternatives** | (A) Big bang merge (all at once), (B) Gradual merge (phased), (C) Federated (separate repos, shared API) |
| **Evidence** | Big bang merges have high failure rates in practice (integration issues, test failures, team confusion). The Linux kernel, Kubernetes, and other large projects use gradual integration. Federated approaches create deployment complexity and version coordination challenges. |
| **Rationale** | Gradual merge allows: (1) testing each integration incrementally, (2) rolling back specific merges, (3) maintaining a working system throughout, (4) learning from early merges to improve later ones. The 6-phase approach (Foundation → Runtime → Agents → Tools → Intelligence → Production) ensures each layer is stable before building on it. |
| **Consequences** | Positive: Lower risk, incremental value delivery, learning opportunity. Negative: Longer total integration time (~16 weeks vs ~8 weeks for big bang), temporary inconsistencies between phases, need for compatibility layers. |
| **Status** | Accepted |

---

### C2-020: Adopt Composio as External Integration Layer

| Field | Value |
|---|---|
| **Decision** | Composio provides the 250+ external service integrations via MCP gateway |
| **Context** | Need integrations with 250+ external services (GitHub, Slack, Stripe, etc.) |
| **Alternatives** | (A) Composio, (B) Build each integration, (C) Use openfang channel adapters only, (D) Use n8n/Make as middleware |
| **Evidence** | Composio: 250+ pre-built integrations, OAuth management, MCP support, maintained SDK. Building each: ~2 days per integration × 250 = 500 days of work. openfang adapters: Only 40 adapters, Rust-based, different interface. n8n/Make: Workflow automation, not designed for programmatic agent access. |
| **Rationale** | Composio eliminates 250+ integration efforts. Its MCP support means we don't need custom wrappers. OAuth management is particularly valuable (handling tokens for 250+ services is complex). The per-request pricing model aligns with our usage patterns. |
| **Consequences** | Positive: 250+ integrations out of the box, OAuth management, MCP native. Negative: External dependency (Composio availability), per-request costs, Composio could change pricing/API, limited customization per integration. |
| **Status** | Accepted |

---

### C2-021: Sim Visual Builder as Optional UI Component

| Field | Value |
|---|---|
| **Decision** | sim's ReactFlow visual workflow builder is integrated as an optional UI component, not required for operation |
| **Context** | sim provides a TypeScript/Next.js visual workflow builder using ReactFlow |
| **Alternatives** | (A) Required UI, (B) Optional UI, (C) Separate project, (D) No UI (API only) |
| **Evidence** | Many deployments will be headless (API-only, CI/CD integration). Visual builders add complexity and a TypeScript build step. ReactFlow is well-suited for LangGraph visualization. The visual builder is valuable for debugging and demonstration but not essential for production operation. |
| **Rationale** | Making the UI optional means: (1) headless deployments are simpler, (2) the core system has zero TypeScript dependencies, (3) the visual builder can be developed and deployed independently. When needed, it provides powerful workflow visualization and debugging. |
| **Consequences** | Positive: Clean separation, optional complexity, independent deployment. Negative: UI and backend may drift in feature parity, need API contract between them, two deployment targets. |
| **Status** | Accepted |

---

### C2-022: oh-my-claudecode Skills as Reference, Not Runtime

| Field | Value |
|---|---|
| **Decision** | oh-my-claudecode's 28 agents and 30 skills serve as reference implementations and design patterns, not as direct code imports |
| **Context** | oh-my-claudecode is a Claude Code plugin with 28 agents and 30 skills |
| **Alternatives** | (A) Direct code import, (B) Reference only, (C) Fork and adapt |
| **Evidence** | oh-my-claudecode is tightly coupled to Claude Code's plugin API. Its agents use Claude-specific patterns (system prompts, tool calling). Direct import would create Claude dependency. The skill concepts and routing logic are valuable but implementation is Claude-specific. |
| **Rationale** | The value is in the design patterns: agent routing, skill activation, and the 28-agent taxonomy. We implement these patterns using our LangGraph + MCP + PydanticAI stack. This gives us the same functionality without Claude dependency. |
| **Consequences** | Positive: No Claude dependency, patterns adapted to our stack, better integration. Negative: More development effort, may miss nuanced Claude optimizations. |
| **Status** | Accepted |

---

## 6. Security Decisions

### C2-023: Multi-Layer Security Model from openfang

| Field | Value |
|---|---|
| **Decision** | Adopt openfang's 16-layer security model as the reference architecture, implemented across Python and Rust services |
| **Context** | Need comprehensive security for agent sandboxing, tool access, and data protection |
| **Alternatives** | (A) openfang 16-layer model, (B) Docker-only sandbox, (C) Minimal security + audit, (D) SELinux/AppArmor |
| **Evidence** | openfang's 16 layers cover: network, transport, application, sandboxing, memory, CPU, IPC, device, syscall, capabilities, filesystem, resource, egress, temp, user namespace, WASM, and audit. Docker-only sandboxing has known escape vectors. SELinux/AppArmor are OS-level only, not application-level. |
| **Rationale** | Agents executing arbitrary code (coding, research) need comprehensive isolation. openfang's model is the most complete we've audited. Implementing it across Python (agent-level) and Rust (infrastructure-level) provides defense in depth. |
| **Consequences** | Positive: Comprehensive security, defense in depth, proven model. Negative: Implementation complexity, performance overhead (security checks on every tool call), some layers require platform-specific code. |
| **Status** | Accepted |

---

### C2-024: AES-256-GCM for Credential Encryption

| Field | Value |
|---|---|
| **Decision** | Continue using AES-256-GCM for credential encryption (from AI-MultiColony-Ecosystem) |
| **Context** | Need encryption for stored API keys, tokens, and other credentials |
| **Alternatives** | (A) AES-256-GCM (existing), (B) HashiCorp Vault, (C) AWS KMS, (D) ChaCha20-Poly1305 |
| **Evidence** | AES-256-GCM is already implemented in AI-MultiColony-Ecosystem with PBKDF2-SHA256 key derivation. It's NIST-approved, widely supported, and hardware-accelerated (AES-NI). Vault/KMS add external dependencies and cost. ChaCha20 is faster in software but less widely audited. |
| **Rationale** | The existing implementation works and is well-tested. AES-256-GCM with PBKDF2-SHA256 (600K iterations) meets current security standards. No reason to change what's already built. Optional Vault integration can be added later for enterprise deployments. |
| **Consequences** | Positive: Existing implementation, NIST-approved, hardware-accelerated. Negative: Vault provides additional features (rotation, audit, access control) that we need to implement separately. |
| **Status** | Accepted |

---

## Appendix A: Decision Summary Table

| ID | Decision | Status | Impact |
|---|---|---|---|
| C2-001 | AI-MultiColony-Ecosystem as core | Accepted | High |
| C2-002 | Archive Agentic-AI-System_OLD | Accepted | Low |
| C2-003 | OpenHands for Coding colony | Accepted | High |
| C2-004 | openfang as gRPC service layer | Accepted | High |
| C2-005 | Isolate agentcloud (AGPL) | Accepted | Medium |
| C2-006 | Exclude suna code (KPSL) | Accepted | Medium |
| C2-007 | CloakBrowser as primary browser | Accepted | High |
| C2-008 | nanobot as reference only | Accepted | Low |
| C2-009 | Rewrite project-nomad in Python | Accepted | Medium |
| C2-010 | open-computer-use as MCP service | Accepted | Medium |
| C2-011 | LangGraph for orchestration | Accepted | Critical |
| C2-012 | MCP as tool interface | Accepted | Critical |
| C2-013 | PydanticAI for validation | Accepted | High |
| C2-014 | A2A for inter-colony comm | Accepted | High |
| C2-015 | DSPy for prompt optimization | Accepted | Medium |
| C2-016 | FastAPI over Flask | Accepted | High |
| C2-017 | Redis Streams message bus | Accepted | High |
| C2-018 | Qdrant for vector storage | Accepted | Medium |
| C2-019 | Gradual merge strategy | Accepted | Critical |
| C2-020 | Composio for 250+ integrations | Accepted | High |
| C2-021 | Sim UI as optional component | Accepted | Medium |
| C2-022 | oh-my-claudecode as reference | Accepted | Medium |
| C2-023 | 16-layer security model | Accepted | High |
| C2-024 | AES-256-GCM credentials | Accepted | Medium |

## Appendix B: Deferred Decisions

| ID | Decision | Reason for Deferral | Expected Resolution |
|---|---|---|---|
| C2-D01 | E2B vs Daytona for sandboxing | Need cost analysis and self-hosting requirements | Phase 2 |
| C2-D02 | Letta cloud vs self-hosted | Depends on data sensitivity requirements | Phase 2 |
| C2-D03 | Primary LLM provider default | Depends on cost/quality tradeoffs at implementation time | Phase 1 |
| C2-D04 | Observability stack (Jaeger vs Tempo) | Need performance benchmarking | Phase 3 |
| C2-D05 | Multi-tenancy model | Depends on deployment model (single-org vs SaaS) | Phase 5 |
| C2-D06 | Community skill marketplace launch | Depends on user adoption metrics | Phase 6+ |
| C2-D07 | Windows support for computer-use | Low priority, macOS/Linux first | Phase 4 |
| C2-D08 | Formal A2A spec compliance | A2A is still in draft, wait for stable spec | Phase 3 |
