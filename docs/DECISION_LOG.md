# Quant Nanggroe AI — Architecture Decision Records

**Version 4.0.0 | ADR Log**

> Complete Architecture Decision Records (ADRs) for all major technical decisions in the Quant Nanggroe AI platform. Each ADR follows the structured format: Context, Decision, Rationale, Consequences.

---

## Decision Summary

| ADR | Title | Category | Status | Key Trade-off |
|-----|-------|----------|--------|---------------|
| ADR-001 | LangGraph StateGraph for Agent Orchestration | Agent Architecture | Accepted | Framework convenience → Deterministic graph + conditional routing |
| ADR-002 | 11-Agent Council Architecture | Agent Architecture | Accepted | Simplicity → Domain-specific expertise + debate mechanism |
| ADR-003 | Constitutional Risk Limits (Hardcoded) | Risk | Accepted | Config flexibility → Immutable safety guarantees |
| ADR-004 | 9-Checkpoint Risk Gate | Risk | Accepted | Speed → Comprehensive validation |
| ADR-005 | CCXT as Unified Exchange Layer | Exchange | Accepted | Exchange-specific APIs → Unified abstraction |
| ADR-006 | Pydantic v2 for All Data Models | Data | Accepted | Migration effort → Type safety + validation |
| ADR-007 | Dual-Bus Architecture | Infrastructure | Accepted | Simplicity → Latency isolation |
| ADR-008 | Python 3.12+ Runtime | Infrastructure | Accepted | Compatibility range → Modern features + performance |
| ADR-009 | FactorRegistry with Dual Pattern Support | Factor Engine | Accepted | Simplicity → Flexibility (class + function factors) |
| ADR-010 | TF-IDF Vector Memory (No External DB) | Memory | Accepted | Semantic quality → Zero dependencies |
| ADR-011 | FastAPI for Backend API | API | Accepted | Flask simplicity → Async + auto-docs + type safety |
| ADR-012 | Next.js Web Terminal (Not CLI) | Frontend | Accepted | CLI simplicity → Rich UX + real-time updates |
| ADR-013 | Council Debate Mechanism | Agent Architecture | Accepted | Single-decider speed → Multi-perspective robustness |
| ADR-014 | ATR-Based Position Sizing | Risk | Accepted | Fixed sizing → Volatility-adaptive sizing |
| ADR-015 | PostgreSQL + TimescaleDB for Storage | Infrastructure | Accepted | Simplicity → Time-series optimization |

---

## ADR-001: LangGraph StateGraph for Agent Orchestration

| Field | Value |
|-------|-------|
| **Date** | 2025-Q1 |
| **Status** | Accepted |
| **Deciders** | Architecture Team |
| **Consulted** | LangGraph docs, CrewAI docs, AutoGen docs |

### Context

Three agent coordination frameworks were evaluated:

1. **CrewAI** — Role-based orchestration with task delegation. Good for collaborative workflows but lacks fine-grained state control, conditional routing, and deterministic execution guarantees. Agents communicate through opaque "task" strings.

2. **AutoGen** (Microsoft) — Conversation-based multi-agent framework. Fundamentally conversational — agents take turns speaking. Wrong for a trading system where parallel sensor execution is required. No built-in veto mechanism.

3. **LangGraph** — StateGraph with explicit `AgentState` schema, conditional edges, and built-in persistence. Supports fan-out/fan-in for parallel agent execution.

### Decision

Use **LangGraph Custom StateGraph** as the single agent coordination layer.

### Rationale

| Factor | CrewAI | AutoGen | LangGraph |
|--------|--------|---------|-----------|
| State management | Implicit (task strings) | Conversation history | Explicit TypedDict |
| Conditional routing | No | No | ✅ `add_conditional_edges()` |
| Veto/gate mechanism | No | No | ✅ Routing functions |
| Parallel execution | Partial | No (conversational) | ✅ Fan-out/fan-in |
| Audit trail | Task logs | Chat history | Full state trace |
| Deterministic | No (LLM-driven) | No (LLM-driven) | ✅ Deterministic nodes + LLM where needed |
| Risk gate support | No | No | ✅ `should_continue_after_risk()` |

### Consequences

- **Positive**: Deterministic decision pipeline, full state auditability, conditional veto gates, typed state transitions
- **Negative**: More boilerplate than CrewAI for simple workflows, LangGraph API stability risk
- **Mitigation**: Pin LangGraph version, abstraction layer over graph construction via `TradingGraph` class

---

## ADR-002: 11-Agent Council Architecture

| Field | Value |
|-------|-------|
| **Date** | 2025-Q1 |
| **Status** | Accepted |

### Context

The system needed to balance two competing needs:
1. **Domain expertise** — Different asset classes (crypto, forex, equities) and analysis types (technical, fundamental, macro) require specialized knowledge
2. **Decision coherence** — Too many agents can produce contradictory signals

### Decision

Implement an **11-agent council** with clear separation of concerns:

| Agent | Domain | LLM Tier | Rationale |
|-------|--------|----------|-----------|
| Researcher | General market research | Quick | Broad analysis, fast turnaround |
| Macro | Global macroeconomics | Quick | Regime detection, policy analysis |
| Crypto | Cryptocurrency markets | Quick | Sector-specific knowledge |
| Forex | Foreign exchange markets | Quick | Currency-specific analysis |
| Strategist | Signal synthesis | **Deep** | Requires deep reasoning to combine all inputs |
| Risk | Risk validation | **Deep** | Critical function needs best reasoning |
| Portfolio | Portfolio optimization | Quick | Mathematical optimization, less LLM dependency |
| Trader | Trade decision | Quick | Execution-focused, follows strategy |
| Execution | Order routing | Quick | Broker interaction, fast response |
| Council | Debate + voting | **Deep** | Complex multi-agent reasoning |

### Rationale

- **Analysis phase** (Researcher + Macro + Crypto + Forex): Runs in parallel, each producing domain-specific output
- **Synthesis phase** (Strategist): Deep LLM to combine 4 analysis streams into signals
- **Validation phase** (Risk + Council): 9-checkpoint gate + debate for low-confidence signals
- **Execution phase** (Portfolio + Trader + Execution): Fast execution path

### Consequences

- **Positive**: Domain expertise per agent, parallel analysis, structured debate mechanism
- **Negative**: Higher LLM token costs (4 analysis agents + strategist + risk + council), more complex graph
- **Mitigation**: Quick LLM (`gpt-4o-mini`) for analysis agents reduces cost; only 3 agents use Deep LLM

---

## ADR-003: Constitutional Risk Limits (Hardcoded)

| Field | Value |
|-------|-------|
| **Date** | 2025-Q1 |
| **Status** | Accepted |

### Context

In a multi-agent system, any single agent with configuration access could theoretically override risk limits. The system needed risk limits that are **impossible** to override at runtime.

### Decision

All constitutional limits are **Python constants** defined in `engine/risk/constants.py`:

```python
MAX_RISK_PER_TRADE: float = 0.005       # 0.5% — cannot be changed via config
MAX_DAILY_LOSS: float = 0.01            # 1% — cannot be changed via env vars
MAX_WEEKLY_LOSS: float = 0.03           # 3% — cannot be changed at runtime
MIN_RISK_REWARD: float = 2.0            # 1:2 R:R — hardcoded
MAX_CORRELATED_POSITIONS: int = 3       # No override possible
MAX_POSITION_SIZE_PCT: float = 0.10     # 10% cap
MAX_LEVERAGE: float = 3.0               # 3x max
MAX_DRAWDOWN_PCT: float = 0.15          # 15% before kill switch
MAX_DAILY_TRADES: int = 5               # Overtrading prevention
```

The `RiskAssessment` model enforces: `override_possible: bool = Field(False)`

### Rationale

| Factor | Config-based | Constitutional (chosen) |
|--------|-------------|------------------------|
| Override protection | Can be changed in config | **Hardcoded constants** |
| Agent override | Possible | **Impossible** |
| Runtime modification | Possible via env vars | **Impossible** |
| Audit trail | Partial | Full 9-checkpoint log |
| Kill switch | Manual | **Automatic** |

### Consequences

- **Positive**: No override of risk limits, full audit trail, automatic kill switch
- **Negative**: Changing limits requires code change + deployment; limits may be too conservative for some strategies
- **Mitigation**: Softer limits (max_open_positions, etc.) are configurable via Settings; only core constitutional limits are hardcoded

---

## ADR-004: 9-Checkpoint Risk Gate

| Field | Value |
|-------|-------|
| **Date** | 2025-Q1 |
| **Status** | Accepted |

### Context

The system needed comprehensive pre-trade validation that covers position sizing, loss limits, risk-reward ratios, and portfolio-level constraints. A simple "max loss" check was insufficient.

### Decision

Every trade must pass all 9 checkpoints in `RiskCheckGate.evaluate()`. Any single failure results in immediate VETO:

1. Risk per trade ≤ 0.5%
2. Daily loss < 1.0%
3. Weekly loss < 3.0%
4. Risk:Reward ratio ≥ 1:2
5. Stop loss exists and is valid
6. Entry price is valid
7. Direction is valid (BUY/SELL/LONG/SHORT)
8. Not overtrading (≤ 5 trades/day)
9. Correlated positions ≤ 3

### Rationale

Each checkpoint addresses a specific failure mode:
- Checkpoints 1-3: Capital preservation (prevents catastrophic loss accumulation)
- Checkpoint 4: Positive expectancy (ensures winners exceed losers when hit)
- Checkpoints 5-7: Data integrity (prevents execution of malformed orders)
- Checkpoint 8: Behavioral control (prevents revenge trading, overtrading)
- Checkpoint 9: Diversification (prevents concentration risk)

### Consequences

- **Positive**: Comprehensive validation, no single point of failure in risk checks, clear audit trail per checkpoint
- **Negative**: More false positives (legitimate trades may be vetoed if close to limits), adds ~10ms to decision latency
- **Mitigation**: CONDITIONAL verdict (future) for trades that fail soft checks but pass hard checks

---

## ADR-005: CCXT as Unified Exchange Layer

| Field | Value |
|-------|-------|
| **Date** | 2025-Q1 |
| **Status** | Accepted |

### Context

The system needed to support 8+ crypto exchanges with varying APIs, authentication methods, and market types. Building individual exchange adapters would result in significant code duplication.

### Decision

Use **CCXT** as the unified exchange library, wrapped in `CCXTBroker` with `ExchangeFactory` for dynamic creation and `ExchangeCapabilities` for feature detection.

### Rationale

| Factor | Custom Adapters | CCXT (chosen) |
|--------|----------------|---------------|
| Exchange coverage | Per-exchange effort | 100+ exchanges |
| API consistency | Custom per exchange | Unified interface |
| Maintenance burden | High (per-exchange) | Low (community-maintained) |
| Feature detection | Manual | ✅ `ExchangeCapabilities` |
| Market type routing | Manual per exchange | ✅ `MarketType` enum |
| Passphrase handling | Ad-hoc | ✅ Auto-warn |

### Consequences

- **Positive**: 8 exchanges from day one, unified API, community maintenance, capability-aware routing
- **Negative**: CCXT adds dependency; CCXT's unified API may not expose exchange-specific features
- **Mitigation**: `ExchangeConfig.options` dict allows CCXT-specific options per exchange; custom brokers for non-CCXT venues (Alpaca, Polymarket, Jupiter)

---

## ADR-006: Pydantic v2 for All Data Models

| Field | Value |
|-------|-------|
| **Date** | 2025-Q1 |
| **Status** | Accepted |

### Context

Legacy repos used Pydantic v1 with `@validator`, `class Config`, and `BaseSettings` from `pydantic`. The codebase needed to standardize on one version.

### Decision

Standardize on **Pydantic v2** with `@field_validator`, `model_config = ConfigDict(...)`, and `pydantic-settings` for configuration.

### Rationale

- Pydantic v2 is 5-50x faster than v1 (Rust core)
- `field_validator` with `@classmethod` is more explicit
- `ConfigDict` replaces `class Config` inner class
- `pydantic-settings` separates settings from data models
- `model_config = {"extra": "allow"}` provides backward compatibility

### Consequences

- **Positive**: Performance improvement, modern API, better type inference
- **Negative**: Breaking migration from v1 patterns; `BaseSettings` moved to separate package
- **Mitigation**: `extra="allow"` provides flexibility; automated migration via `bump-pydantic` tool

---

## ADR-007: Dual-Bus Architecture

| Field | Value |
|-------|-------|
| **Date** | 2025-Q1 |
| **Status** | Accepted |

### Context

The system has two distinct communication patterns:
1. **Order execution** — Latency-critical, must not be blocked by agent reasoning
2. **Agent reasoning** — High-throughput, acceptable latency of 100ms-5s

### Decision

Implement **dual-bus** architecture using Redis Pub/Sub:
- **Execution Bus**: Low-latency (<10ms), FIFO ordering, P0 priority, volatile persistence
- **Agent Reasoning Bus**: High-throughput, best-effort ordering, P2 priority, durable (Redis + PostgreSQL)

### Rationale

Mixing execution and reasoning on the same bus creates head-of-line blocking: a slow agent reasoning message could delay an order fill confirmation. The dual-bus isolates latency domains.

### Consequences

- **Positive**: Execution never blocked by reasoning, independent scaling, separate monitoring
- **Negative**: Two bus systems to maintain, bridge complexity in Trader node
- **Mitigation**: Trader node acts as bridge; if reasoning bus is congested, execution continues on last known state

---

## ADR-008: Python 3.12+ Runtime

| Field | Value |
|-------|-------|
| **Date** | 2025-Q1 |
| **Status** | Accepted |

### Context

Legacy repos used Python 3.9-3.11. The codebase needed a single runtime version.

### Decision

Standardize on **Python 3.12+**.

### Rationale

- PEP 695: `type` keyword for generic aliases (`list[str]` not `List[str]`)
- PEP 709: Inline comprehension performance improvement (~40% faster than 3.9)
- Better error messages for debugging
- `typing` module improvements (TypeAliasType, TypeGuard)
- Required by latest Pydantic v2, LangGraph, and LangChain versions

### Consequences

- **Positive**: Consistent runtime, modern syntax, faster execution, single package manager
- **Negative**: Some legacy repos need code changes for 3.12 compatibility
- **Mitigation**: `ruff` automated upgrade rules, `pyupgrade` for syntax modernization

---

## ADR-009: FactorRegistry with Dual Pattern Support

| Field | Value |
|-------|-------|
| **Date** | 2025-Q1 |
| **Status** | Accepted |

### Context

The system needed to support two factor implementation patterns:
1. **Class-based** (`AlphaFactor` subclasses with `name/meta/compute` properties) — Used by Technical and Fundamental factor zoos
2. **Function-based** (`__alpha_meta__` dict + `compute(panel)` function pairs) — Used by Alpha101, GTJA191, Qlib158, Academic zoos (ported from Vibe-Trading)

### Decision

Implement `FactorHandle` as a unified wrapper that normalizes both patterns:

```python
class FactorHandle:
    def __init__(self, factor_id, zoo, meta_dict, compute_fn=None, class_instance=None):
        self._compute_fn = compute_fn        # Function-based
        self._class_instance = class_instance  # Class-based
    
    def compute(self, panel):
        if self._compute_fn is not None:
            return self._compute_fn(panel)
        elif self._class_instance is not None:
            return self._adapt_class_compute(panel)
```

### Rationale

| Factor | Class-based Only | Dual Pattern (chosen) |
|--------|-----------------|----------------------|
| Alpha101 (101 factors) | Would require 101 classes | ✅ Function-based with meta dict |
| Technical (25+ factors) | ✅ Natural fit | ✅ Class-based with properties |
| Migration effort | Rewrite all function factors | Zero — both patterns supported |
| Discovery | Inspect class attributes | ✅ `list(zoo=, theme=, universe=)` |

### Consequences

- **Positive**: No rewriting of existing factor implementations, unified `FactorRegistry.list()` API across all zoos
- **Negative**: Two code paths in `FactorHandle.compute()`, class-based adaptation is less efficient for wide DataFrames
- **Mitigation**: Function-based is the preferred pattern for new factors; class-based adapter handles wide DataFrame per-column

---

## ADR-010: TF-IDF Vector Memory (No External DB)

| Field | Value |
|-------|-------|
| **Date** | 2025-Q1 |
| **Status** | Accepted |

### Context

The system needed semantic search for research notes and trade reasoning. Options included:
1. External vector databases (ChromaDB, Pinecone, Weaviate) — Full-featured but add infrastructure dependencies
2. Neural embeddings (OpenAI, sentence-transformers) — Better semantic quality but add API dependency
3. Built-in TF-IDF — Lower semantic quality but zero dependencies

### Decision

Use **built-in TF-IDF** vector memory with cosine similarity for the initial implementation.

### Rationale

| Factor | External Vector DB | Neural Embeddings | TF-IDF (chosen) |
|--------|-------------------|-------------------|-----------------|
| External dependencies | High (DB service) | Medium (API calls) | **Zero** |
| Setup complexity | High | Medium | **Low** |
| Semantic quality | Best | Good | Adequate |
| Latency | Network-dependent | API-dependent | **Local (<1ms)** |
| Capacity | Unlimited | Token-limited | ~100k documents |
| Migration path | — | — | pgvector for scale |

### Consequences

- **Positive**: Zero external dependencies, fast local search, simple implementation
- **Negative**: TF-IDF is less semantically rich than neural embeddings; limited to keyword-level matching
- **Mitigation**: pgvector migration path for production scale; pluggable embedding interface for future upgrade

---

## ADR-011: FastAPI for Backend API

| Field | Value |
|-------|-------|
| **Date** | 2025-Q1 |
| **Status** | Accepted |

### Context

The backend API needed to serve REST endpoints, WebSocket connections, and async background tasks.

### Decision

Use **FastAPI** with 6 route groups: Market, Trading, Agents, Backtest, Portfolio, WebSocket.

### Rationale

- Native async/await support for concurrent API calls
- Automatic OpenAPI documentation
- Pydantic request/response validation (shared models with agent layer)
- WebSocket support via `FastAPI.websocket`
- Uvicorn ASGI server for production

### Consequences

- **Positive**: Auto-docs, type-safe API, async performance, WebSocket support
- **Negative**: FastAPI's dependency injection can be complex; ASGI debugging is harder than WSGI
- **Mitigation**: Structured error handling via global exception handler; lifespan events for eager service initialization

---

## ADR-012: Next.js Web Terminal (Not CLI)

| Field | Value |
|-------|-------|
| **Date** | 2025-Q1 |
| **Status** | Accepted |

### Context

Legacy interfaces included FinceptTerminal (Python CLI) and a Bloomberg-style TUI. Both were limited by terminal constraints.

### Decision

Build a **Next.js Web Terminal** with desktop-OS-inspired window manager (draggable, resizable panels).

### Rationale

| Factor | CLI/TUI | Web Terminal |
|--------|---------|--------------|
| Real-time charting | ASCII art only | Full OHLCV with Lightweight Charts |
| Multi-panel layout | Terminal tabs | Draggable windows with z-index |
| Mobile access | SSH only | Responsive web |
| WebSocket support | Limited | Native |
| Deployment | Local Python | Docker container |

### Consequences

- **Positive**: Rich UX, real-time updates, broader accessibility, maintainable TypeScript
- **Negative**: Higher memory footprint, requires browser runtime
- **Mitigation**: Lazy-load windows, Vite code splitting, WebSocket compression

---

## ADR-013: Council Debate Mechanism

| Field | Value |
|-------|-------|
| **Date** | 2025-Q1 |
| **Status** | Accepted |

### Context

When confidence is below `CONFIDENCE_THRESHOLD` (0.65), a single-agent decision is unreliable. The system needed a mechanism to resolve uncertainty.

### Decision

Implement **structured debate** with two formats:
1. **Investment Debate**: Bull Researcher vs. Bear Researcher → Investment Judge
2. **Risk Debate**: Conservative vs. Neutral vs. Aggressive → Risk Judge

Followed by **weighted council voting** where each agent's vote is weighted by historical accuracy.

### Rationale

Inspired by TradingAgents' multi-debate framework. Key advantages:
- **Forced perspective diversity**: Agents must argue from opposing viewpoints
- **Structured reasoning**: Judges produce explicit summaries before decisions
- **Weighted voting**: Historically accurate agents have more influence
- **Human review flag**: Low consensus (`consensus_level < 0.65`) triggers human review

### Consequences

- **Positive**: Better decisions under uncertainty, structured reasoning trail, built-in checks and balances
- **Negative**: Additional LLM costs (6-10 extra LLM calls for debate), latency (adds 5-15s for debate)
- **Mitigation**: Debate only triggered when `confidence < 0.65`; max 2 rounds per debate

---

## ADR-014: ATR-Based Position Sizing

| Field | Value |
|-------|-------|
| **Date** | 2025-Q1 |
| **Status** | Accepted |

### Context

Fixed lot sizing ignores market volatility. The same position size that's appropriate during low volatility becomes dangerous during high volatility.

### Decision

Use **ATR (Average True Range) based position sizing** with 2×ATR stop distance:

```python
stop_distance = 2 * atr
position_size = risk_amount / stop_distance
stop_loss = entry_price - stop_distance  # For BUY
```

Risk amount is capped at `MAX_RISK_PER_TRADE` (0.5%) regardless of input.

### Rationale

- ATR adapts to current volatility: larger stops in volatile markets, smaller in calm markets
- 2×ATR is a standard swing trading stop distance
- Position automatically scales down in volatile markets (higher ATR = larger stop = fewer units)
- Constitutional cap prevents exceeding 0.5% risk regardless of ATR

### Consequences

- **Positive**: Volatility-adaptive sizing, consistent risk across market conditions
- **Negative**: Requires ATR calculation (needs OHLCV data), may produce very small positions in extreme volatility
- **Mitigation**: `position_size = max(0.01, round(lot_size * 100) / 100)` ensures minimum lot size

---

## ADR-015: PostgreSQL + TimescaleDB for Storage

| Field | Value |
|-------|-------|
| **Date** | 2025-Q1 |
| **Status** | Accepted |

### Context

The system needed storage for:
- Agent state (relational)
- OHLCV data (time-series, high-volume)
- Audit events (append-only, high-volume)
- Factor values (time-series)

### Decision

Use **PostgreSQL with TimescaleDB extension** as the primary database.

### Rationale

- TimescaleDB provides hypertable optimization for OHLCV and factor data
- Same PostgreSQL instance handles both relational and time-series workloads
- No separate time-series database to manage
- pgvector extension available for future vector search migration

### Consequences

- **Positive**: Single database technology, mature ecosystem, TimescaleDB compression for historical data
- **Negative**: TimescaleDB extension adds deployment complexity; not as fast as specialized TSDBs (QuestDB) for ingestion
- **Mitigation**: QuestDB available as optional high-frequency ingestion path; PostgreSQL remains primary query engine

---

*© 2025-2026 Quant Nanggroe AI | Decision Log v4.0.0*
