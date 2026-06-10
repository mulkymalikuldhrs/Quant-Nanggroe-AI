# Quant Nanggroe AI — Architecture Decision Records

**Version 0.2.0 | ADR-001 through ADR-010**

> This document records the key architecture decisions made during the development of Quant Nanggroe AI. Each ADR follows the Context-Decision-Consequences-Status format.

---

## ADR-001: LangGraph as Orchestration Framework

### Context

The system needs an orchestration framework for coordinating 9 specialized agents in a trading pipeline. The pipeline has conditional routing (risk veto, council debate, kill switch), parallel execution (market analysis), and state management requirements. We evaluated LangGraph, AutoGen, CrewAI, and custom orchestration.

### Decision

**Use LangGraph as the primary agent orchestration framework.**

LangGraph provides native support for:
- **Graph-based workflows**: The trading pipeline is naturally a directed graph with conditional edges
- **State machines**: `AgentState` TypedDict flows through nodes with automatic merging
- **Conditional routing**: `add_conditional_edges()` maps perfectly to risk assessment routing (APPROVED/VETOED/KILL_SWITCH)
- **Streaming**: `graph.stream()` enables real-time pipeline progress updates
- **Human-in-the-loop**: Built-in support for approval gates before execution

### Consequences

**Positive:**
- Trading pipeline maps directly to a StateGraph with 7 nodes and conditional edges
- State management is automatic — no manual state passing between agents
- Graph visualization and debugging through LangGraph Studio
- Growing ecosystem of LangGraph patterns and examples

**Negative:**
- Tight coupling to LangGraph API; migration would require significant refactoring
- LangGraph is evolving rapidly; breaking changes possible between minor versions
- Learning curve for developers unfamiliar with graph-based workflows
- Limited built-in support for parallel node execution (market analysis runs 4 agents sequentially within a single node)

### Status

**Accepted** — Implemented in `quant_nanggroe/agents/graph.py` with `TradingGraph` class.

---

## ADR-002: Constitutional Risk Management Approach

### Context

Trading systems need risk management to prevent catastrophic losses. Existing approaches include: configurable risk parameters (most projects), no risk management (some AI trading bots), and hardcoded limits (rare in open source). The challenge is preventing agents from circumventing risk limits, whether through LLM hallucination, configuration errors, or adversarial prompt injection.

### Decision

**Implement constitutional risk management with 9 hardcoded, non-overridable checkpoints.**

The constitutional approach means:
1. Risk limits are defined as module-level constants (not configuration parameters)
2. No API, agent, or configuration can override these limits
3. Every `RiskAssessment` includes `override_possible: False`
4. Kill switch thresholds are architecturally enforced through graph routing

### The 9 Constitutional Checkpoints

| # | Check | Limit | Rationale |
|---|-------|-------|-----------|
| 1 | Per-Trade Risk | 0.5% | No single trade should risk significant capital |
| 2 | Daily Loss | 1.0% | Prevent cascading losses in a single session |
| 3 | Weekly Loss | 3.0% | Allow recovery time after bad days |
| 4 | Risk:Reward | 1:2 | Only take trades with positive expectancy |
| 5 | Position Size | 10% | Prevent concentration risk |
| 6 | Correlated Positions | 3 | Prevent correlated drawdowns |
| 7 | Leverage | 3x | Limit amplification of losses |
| 8 | Drawdown | 15% | Kill switch trigger for catastrophic loss |
| 9 | Trade Frequency | 5/day | Prevent overtrading and emotional decisions |

### Consequences

**Positive:**
- Capital protection is architecturally guaranteed, not configuration-dependent
- No agent can override limits through prompt injection or hallucination
- Audit trail clearly shows constitutional compliance for every trade
- Institutional-grade risk management suitable for regulated environments

**Negative:**
- Limits cannot be adjusted for different risk appetites without code changes
- Conservative limits may reject profitable trades that would exceed position size or frequency limits
- No "admin override" capability for experienced traders who want higher limits
- Testing requires mock risk checkpoints since limits are hardcoded

### Status

**Accepted** — Implemented in `quant_nanggroe/agents/state.py` and `quant_nanggroe/engine/risk/`.

---

## ADR-003: Multi-Agent Council vs Single Agent

### Context

AI trading systems can use either a single monolithic agent or multiple specialized agents. Single agents are simpler but lack perspective diversity. Multi-agent systems add complexity but enable debate, voting, and specialized expertise. The AI-Hedge-Fund (45K stars) and TradingAgents (Princeton) projects demonstrate the multi-agent approach.

### Decision

**Use 9 specialized agents with council debate and weighted voting for decision-making.**

The 9 agents are organized by domain expertise:
- **Market Analysis**: Researcher, Macro, Crypto, Forex
- **Strategy**: Strategist (signal generation)
- **Risk**: Risk Agent (9-checkpoint gate)
- **Portfolio**: Portfolio Agent (allocation)
- **Trading**: Trader Agent (decisions)
- **Execution**: Execution Agent (orders)

When confidence falls below 0.65, a council debate is triggered:
1. Bull/Bear debate on trade direction
2. Risk debate (conservative/neutral/aggressive)
3. Weighted voting by all agents based on historical accuracy

### Consequences

**Positive:**
- Multiple perspectives reduce single-point-of-failure in analysis
- Council debate forces consideration of opposing viewpoints
- Specialized agents can use domain-specific tools and prompts
- Weighted voting accounts for agent track records

**Negative:**
- 9 agents × LLM calls = higher cost per pipeline run
- Longer execution time due to sequential agent calls in pipeline
- More complex debugging when agents disagree
- Potential for groupthink if agents converge on similar analysis

### Status

**Accepted** — Implemented in `quant_nanggroe/agents/` with 9 agent modules and `council/` debate system.

---

## ADR-004: Data Provider Abstraction Layer

### Context

The system needs data from multiple providers (yfinance, Alpaca, Binance, Polygon, FRED, CoinGecko, etc.) with different APIs, rate limits, and data formats. Without abstraction, each component would need provider-specific code, making it difficult to switch providers or add failover.

### Decision

**Implement a multi-provider abstraction layer with automatic failover and health-based prioritization.**

The abstraction layer provides:
- **Unified interface**: Common API regardless of underlying provider
- **Auto-failover**: Automatic retry with exponential backoff and provider cooldown
- **Health monitoring**: Providers ranked by success rate and latency
- **Trust scoring**: Each data point tagged with source and confidence
- **TTL caching**: 5-minute default cache to reduce API calls

### Consequences

**Positive:**
- Adding new providers requires only a new adapter, no changes to consumer code
- Automatic failover ensures continuity when providers go down
- Trust scores enable weighted aggregation of multi-source data
- Caching reduces API costs and improves performance

**Negative:**
- Abstraction layer adds complexity and potential performance overhead
- Provider-specific features may be lost in the common interface
- Cache staleness could lead to decisions based on outdated data
- Health monitoring adds background processing overhead

### Status

**Accepted** — Implemented in `quant_nanggroe/exchange/` with `ExchangeInterface` and in settings with provider API keys.

---

## ADR-005: Paper Trading First, Live Trading Later

### Context

Deploying a trading system directly to live markets carries significant financial risk. Bugs in risk management, execution logic, or agent reasoning could lead to real capital losses. The system needs a safe testing environment that mirrors live conditions.

### Decision

**Implement paper trading as the default mode with identical code paths for paper and live trading.**

The approach:
1. `ExchangeInterface` abstract base class defines the same API for all broker types
2. `PaperBroker` implements the interface with simulation instead of real orders
3. `AlpacaBroker` has `paper=True` default setting
4. Configuration flag `alpaca_paper: bool = True` in Settings
5. The TradingGraph and all agents are unaware of whether they're running paper or live

### Consequences

**Positive:**
- Safe testing environment with zero financial risk
- Identical code paths ensure paper results are representative of live behavior
- Easy toggle between paper and live via configuration
- Gradual confidence building before live deployment

**Negative:**
- Paper trading cannot simulate all market conditions (liquidity gaps, exchange outages)
- Slippage and fill simulation may not match real-world conditions
- Psychological differences — traders may behave differently with real money
- Risk of "it works in paper but not in live" due to simulation gaps

### Status

**Accepted** — Implemented in `exchange/paper_broker.py` and `engine/execution/brokers/paper.py`.

---

## ADR-006: Factor Library Architecture

### Context

Alpha factors are the foundation of quantitative trading strategies. The system needs a factor library that supports multiple factor sources (Alpha101, GTJA191, Barra, Technical, Fundamental) with consistent computation, validation, and composition. The design must prevent lookahead bias, ensure numerical stability, and support factor pipeline composition.

### Decision

**Implement a class-based factor library with `AlphaFactor` base class, `FactorMeta` documentation, and pipeline composition.**

The architecture:
- **`AlphaFactor` base class**: Abstract base with `name`, `meta`, and `compute(df)` interface
- **`FactorMeta`**: Rich metadata including formula LaTeX, theme tags, universe, warmup requirements, decay horizon
- **`FactorRegistry`**: Central registry for factor discovery and instantiation
- **`FactorPipeline`**: Composable pipeline for chaining factor computations
- **Helper functions**: `rank`, `delay`, `delta`, `ts_corr`, `ts_cov`, `ts_mean`, `ts_std`, `safe_div`, etc.
- **AST-pure computation**: No side effects, no global state
- **Lookahead banning**: All time-series operations use only past data

### Consequences

**Positive:**
- Consistent interface across all factor sources
- Self-documenting factors with rich metadata (formula, themes, universe)
- Composable pipeline enables factor combination and IC analysis
- Safe division and numerical stability prevent runtime errors
- Lookahead banning ensures backtesting integrity

**Negative:**
- Class-based approach is more verbose than expression-based (e.g., Qlib DSL)
- No runtime factor validation (must test separately)
- Pandas-based computation may be slower than NumPy-only approaches
- Factor warmup requirements must be managed by the pipeline user

### Status

**Accepted** — Implemented in `quant_nanggroe/engine/factors/` with Alpha101 (50+ factors), GTJA191, Barra, Technical, and Fundamental factor modules.

---

## ADR-007: Asset-Class Conditional Routing

### Context

The system trades across multiple asset classes (equities, crypto, forex) with fundamentally different market dynamics, data sources, and trading rules. A single analysis pipeline may not be optimal for all asset classes.

### Decision

**Implement asset-class conditional routing through specialized agents.**

The approach:
- **Crypto Agent**: Activated when symbols contain crypto pairs (e.g., BTC/USDT)
- **Forex Agent**: Activated when symbols contain forex pairs (e.g., EUR/USD)
- **Macro Agent**: Always activated for macro regime detection
- **Researcher Agent**: Always activated for general market research

The market analysis node runs all relevant agents based on the symbol list:

```python
# All 4 agents run during market analysis phase
researcher = self._factory.create_agent("researcher")
macro = self._factory.create_agent("macro")
crypto = self._factory.create_agent("crypto")
forex = self._factory.create_agent("forex")
```

### Consequences

**Positive:**
- Domain-specific expertise for each asset class
- Crypto agent uses on-chain data, whale tracking, and sentiment
- Forex agent uses central bank policy, carry trade analysis, and FX rates
- Macro agent provides cross-asset regime detection
- Easy to add new asset classes by creating new agents

**Negative:**
- More LLM calls per pipeline run (4 market analysis agents)
- Agent outputs must be synthesized by the Strategist, which may struggle with conflicting signals
- No explicit symbol→agent routing logic (all 4 agents always run)
- Risk of redundant analysis across agents

### Status

**Accepted** — Implemented with 9 agents including Crypto and Forex specialists. Future enhancement: symbol-based agent activation.

---

## ADR-008: Memory Architecture (Journal + Knowledge Graph + Paging)

### Context

AI trading agents need memory to learn from past trades, recall market patterns, and maintain context across sessions. Without memory, each pipeline run starts from scratch. Different memory types serve different purposes: structured trade records, relational market knowledge, and bounded context windows.

### Decision

**Implement a three-tier memory architecture: Trade Journal, Knowledge Graph, and Paging System.**

1. **Trade Journal** (`memory/journal.py`): Structured trade logging with entry/exit tracking, PnL calculation, and reflection/review
2. **Knowledge Graph** (`memory/knowledge_graph.py`): Entity-relationship storage for market structure (symbol→sector, strategy→performance, regime→behavior)
3. **Paging System** (`memory/paging.py`): Letta-style context window management with priority-based eviction, recall mechanism, and automatic summarization
4. **Session Manager** (`memory/session.py`): Cross-session state persistence and pipeline run tracking

### Consequences

**Positive:**
- Trade journal enables post-trade analysis and agent learning
- Knowledge graph captures relational market knowledge
- Paging system prevents context window overflow
- Session manager enables pipeline run correlation
- Reflection mechanism supports continuous improvement

**Negative:**
- Four memory systems add implementation and maintenance complexity
- Knowledge graph requires manual or semi-automated population
- Paging system adds latency for context recall
- No unified memory query interface — each system has its own API
- Persistence format (JSON for journal) may not scale to high-frequency trading

### Status

**Accepted** — Implemented in `quant_nanggroe/memory/` with all four components.

---

## ADR-009: MCP Protocol for Tool Integration

### Context

Agents need tools to interact with market data, execute trades, compute risk metrics, and access external APIs. Custom tool interfaces create tight coupling and prevent reuse. The Model Context Protocol (MCP) is an emerging standard for LLM-tool communication with JSON-RPC 2.0, tool discovery, and SSE streaming.

### Decision

**Implement MCP protocol for all agent-tool communication.**

The MCP implementation:
- **Protocol** (`mcp/protocol.py`): JSON-RPC 2.0 messages, tool schemas, health checks, SSE events
- **Server** (`mcp/server.py`): Tool registration and execution handler
- **Client** (`mcp/client.py`): Tool discovery and invocation from agents
- **Tools** (`mcp/tools.py`): Built-in tool implementations

Tool definitions include:
- `ToolInputSchema` / `ToolOutputSchema`: JSON Schema validation
- `ToolDefinition`: Name, description, schemas, annotations
- `ToolCallResult`: Content, timing, metadata, error handling

### Consequences

**Positive:**
- Standardized tool interface compatible with MCP ecosystem
- Tool discovery enables dynamic agent capability expansion
- JSON-RPC 2.0 provides structured error handling and correlation
- SSE streaming supports long-running tool execution
- Type-safe tool definitions with Pydantic validation

**Negative:**
- MCP adds a communication layer between agents and tools
- JSON-RPC overhead for in-process tool calls
- MCP specification is still evolving (2024-11-05 version)
- Limited ecosystem of MCP-compatible trading tools
- Debugging through the MCP layer adds complexity

### Status

**Accepted** — Implemented in `quant_nanggroe/mcp/` with full protocol support.

---

## ADR-010: Repository Consolidation Strategy

### Context

Quant Nanggroe AI merges 20+ trading/quant repositories into a single monorepo. Source repositories include trading frameworks, AI agent systems, factor libraries, risk management tools, data providers, and backtesting engines. The challenge is integrating diverse codebases while maintaining quality, consistency, and avoiding duplication.

### Decision

**Adopt a selective consolidation strategy: keep the best implementation from each domain, discard redundant or unmaintained code, and rewrite interfaces for consistency.**

The consolidation approach:
1. **Inventory**: Catalog all 20+ source repositories with functionality mapping
2. **Prioritize**: Rank by code quality, maintenance status, and relevance
3. **Select**: Keep the best implementation for each functional domain
4. **Discard**: Remove redundant, unmaintained, or low-quality code
5. **Harmonize**: Rewrite interfaces for consistency with our architecture
6. **Validate**: Ensure all merged code passes our quality standards

### Consolidation Principles

| Principle | Description |
|-----------|-------------|
| **Best-of-breed** | Keep the highest-quality implementation for each function |
| **No duplication** | One implementation per feature (e.g., one exchange abstraction, one factor base class) |
| **Interface consistency** | All components follow our Pydantic/async/type-hinted patterns |
| **Test coverage** | Merged code must have test coverage or be tested before merge |
| **Documentation** | All merged code must be documented with docstrings |

### Consequences

**Positive:**
- Single source of truth for all trading functionality
- Consistent API design across all components
- Easier deployment with one dependency tree
- Shared testing and CI/CD infrastructure
- No version compatibility issues between integrated components

**Negative:**
- Loss of independent evolution — changes to one component may affect others
- Larger codebase is harder to navigate and understand
- Merge conflicts during consolidation require careful resolution
- Some useful features from merged repos may be lost if they don't fit our architecture
- Heavier dependency tree than individual repos

### Status

**Accepted** — Consolidation complete for core components (agents, engine, exchange, memory, MCP). Ongoing for ML models and advanced features.

---

*© 2025-2026 Quant Nanggroe AI | Architecture Decision Records v0.2.0*
