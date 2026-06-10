# Quant Nanggroe AI — Decision Log

**Architecture Decision Records (ADR)**

> This document records the key architecture decisions made during the development of Quant Nanggroe AI, including the rationale, alternatives considered, and consequences of each decision.

---

## Table of Contents

1. [ADR-001: LangGraph-Style Graph Architecture](#adr-001-langgraph-style-graph-architecture)
2. [ADR-002: Multi-Path Routing](#adr-002-multi-path-routing)
3. [ADR-003: Constitutional Risk Limits](#adr-003-constitutional-risk-limits)
4. [ADR-004: 11-Agent Council System](#adr-004-11-agent-council-system)
5. [ADR-005: Pydantic for Data Models](#adr-005-pydantic-for-data-models)
6. [ADR-006: CCXT for Exchanges](#adr-006-ccxt-for-exchanges)
7. [ADR-007: 9-Checkpoint Risk Gate](#adr-007-9-checkpoint-risk-gate)
8. [ADR-008: Factor Registry Pattern](#adr-008-factor-registry-pattern)
9. [ADR-009: ATR-Based Position Sizing](#adr-009-atr-based-position-sizing)
10. [ADR-010: FastAPI for API Layer](#adr-010-fastapi-for-api-layer)
11. [ADR-011: Kill Switch Design](#adr-011-kill-switch-design)
12. [ADR-012: Dual Graph Version Strategy](#adr-012-dual-graph-version-strategy)
13. [ADR-013: Python 3.11 Minimum](#adr-013-python-311-minimum)
14. [ADR-014: Monorepo Structure](#adr-014-monorepo-structure)
15. [ADR-015: Function-Based Factor Pattern](#adr-015-function-based-factor-pattern)
16. [Merge Decisions per Repo](#merge-decisions-per-repo)

---

## ADR-001: LangGraph-Style Graph Architecture

**Date**: 2024-Q4
**Status**: Adopted
**Decision**: Use LangGraph StateGraph as the primary orchestration mechanism for the trading pipeline.

### Context

The system needs to orchestrate multiple AI agents in a deterministic workflow where:
- Agents execute in a specific order (analysis → signal → risk → execution)
- Conditional routing is required (risk verdict determines next step)
- State must be shared between agents
- Human-in-the-loop checkpoints are needed
- Emergency exits must be possible from any node

### Alternatives Considered

| Alternative | Pros | Cons |
|---|---|---|
| **LangGraph StateGraph** | Conditional edges, streaming, human-in-loop, stateful, LangChain ecosystem | Learning curve, coupling to LangChain |
| **CrewAI** | Simple role-based agents, built-in collaboration | No conditional routing, no graph structure, too abstract |
| **AutoGen** | Conversation patterns, human participation | Non-deterministic, no graph structure, no risk gates |
| **Custom DAG** | Full control, no dependencies | Reinventing the wheel, no ecosystem, more maintenance |
| **Prefect/Airflow** | Mature workflow engines | Not designed for LLM agents, too heavy, wrong abstraction |

### Decision

Use LangGraph StateGraph because:
1. **Conditional edges** are the core abstraction we need for risk routing
2. **Stateful execution** with TypedDict matches our AgentState design
3. **Human-in-the-loop** is a built-in feature
4. **Streaming** support for real-time updates
5. **LangChain ecosystem** integration for LLM tools
6. **Graph visualization** for debugging and auditing

### Consequences

- **Positive**: Deterministic execution, excellent debugging, clean separation of concerns
- **Negative**: Coupling to LangChain ecosystem, learning curve for new developers
- **Risk**: LangGraph API changes may require refactoring (mitigated by pinning version)

---

## ADR-002: Multi-Path Routing

**Date**: 2025-Q1
**Status**: Adopted (v2 graph)
**Decision**: Implement asset-class conditional routing with 4 specialized execution paths.

### Context

Different asset classes require fundamentally different analysis:
- Crypto needs on-chain analysis, Solana/Jupiter tools, rug checks
- Forex needs carry trade analysis, CB policy tracking, cross-currency dynamics
- Equities need SEC filings, earnings calendars, insider trades
- Prediction markets need probability estimation, event contract pricing

A one-size-fits-all pipeline would be suboptimal for each asset class.

### Alternatives Considered

| Alternative | Pros | Cons |
|---|---|---|
| **Multi-path routing** | Specialized analysis per asset, optimal tools per domain | More graph nodes, more maintenance |
| **Single path with conditional tools** | Simpler graph, fewer nodes | Tool explosion, agent confusion, harder to debug |
| **Separate graphs per asset** | Maximum specialization | Code duplication, no shared infrastructure |
| **Plugin-based tools** | Flexible, extensible | No graph-level routing, runtime complexity |

### Decision

Implement multi-path routing with the `AssetRouter` node that:
1. Classifies symbols using regex pattern matching
2. Routes to the appropriate specialized path
3. All paths converge at `signal_generation` for unified processing

### Consequences

- **Positive**: Domain-specific analysis, clean separation, extensible for new asset classes
- **Negative**: 4 additional graph nodes, must maintain path parity
- **Risk**: Symbol misclassification (mitigated by defaulting to equity path)

---

## ADR-003: Constitutional Risk Limits

**Date**: 2024-Q4
**Status**: Adopted (inviolable)
**Decision**: Hardcode all risk limits as Python constants that cannot be overridden at runtime.

### Context

In institutional trading, risk limits must be absolute. No agent, no matter how confident, should be able to override risk limits. The system needs to guarantee capital protection even in the face of:
- LLM hallucination (agent believes a trade is "sure thing")
- Configuration errors (someone sets risk to 50%)
- Runtime modification (API call to change limits)
- Cascading failures (one bad trade leads to revenge trading)

### Alternatives Considered

| Alternative | Pros | Cons |
|---|---|---|
| **Hardcoded constants** | Impossible to override, audit-proof, simple | Not configurable, requires code change to modify |
| **Configuration file** | Flexible, easy to adjust | Can be modified at runtime, no guarantee |
| **Environment variables** | Deployment-specific | Can be changed without code review |
| **Database-stored limits** | Dynamic, admin-adjustable | Can be changed by any process with DB access |
| **Hybrid (hardcoded + config)** | Some flexibility | Override mechanism creates loopholes |

### Decision

Hardcode all constitutional risk limits as module-level Python constants:

```python
MAX_RISK_PER_TRADE: float = 0.005       # CANNOT be overridden
MAX_DAILY_LOSS: float = 0.01            # CANNOT be overridden
MAX_WEEKLY_LOSS: float = 0.03           # CANNOT be overridden
# ... etc.
```

The `override_possible` field in AgentState is hardcoded to `False`.

### Consequences

- **Positive**: Absolute capital protection, audit-proof, no override possible
- **Negative**: Cannot adjust limits without code deployment, may be too conservative
- **Risk**: If limits are wrong, requires code change and redeployment (acceptable trade-off)

---

## ADR-004: 11-Agent Council System

**Date**: 2024-Q4 (initial 5), 2025-Q1 (expanded to 11)
**Status**: Adopted
**Decision**: Implement 11 specialized agents with distinct roles, tools, and LLM configurations.

### Context

A single "super-agent" cannot effectively handle all aspects of trading. Different tasks require different expertise, different data sources, and different levels of analysis depth.

### Agent Evolution

| Phase | Agents | Rationale |
|---|---|---|
| v0.1 | Researcher, Trader, Risk | Minimal viable agent set |
| v1.0 | + Strategist, Portfolio | Signal generation and allocation |
| v2.0 | + Macro, Crypto, Forex | Asset-class specialization |
| v2.1 | + Council, Prediction Market | Debate mechanism and new asset class |
| v3.0 | + Execution | Separate execution from trading decision |

### Alternatives Considered

| Alternative | Pros | Cons |
|---|---|---|
| **11 specialized agents** | Domain expertise, clean separation, parallel execution | More maintenance, more LLM calls |
| **5 general agents** | Simpler, fewer LLM calls | Lack of specialization, tool overload |
| **Single agent with tools** | Simplest, cheapest | Context overload, no parallelism |
| **Dynamic agent creation** | Flexible, adaptable | Unpredictable, hard to debug |

### Decision

11 specialized agents because:
1. Each agent has focused system prompts and tools
2. Asset-class agents can run in parallel
3. Risk agent operates independently with full veto authority
4. Council agent provides governance for low-confidence decisions
5. Deep vs Quick LLM selection optimizes cost/performance

### Consequences

- **Positive**: Specialization, parallelism, clear responsibility, independent risk
- **Negative**: More LLM API calls, more maintenance, higher cost
- **Risk**: Agent coordination complexity (mitigated by LangGraph state management)

---

## ADR-005: Pydantic for Data Models

**Date**: 2024-Q4
**Status**: Adopted
**Decision**: Use Pydantic BaseModel and TypedDict for all data models throughout the system.

### Context

The system handles complex nested data structures (market data, signals, decisions, risk assessments) that flow between agents and through the graph. Without strict type definitions, data corruption would be inevitable.

### Alternatives Considered

| Alternative | Pros | Cons |
|---|---|---|
| **Pydantic v2** | Runtime validation, serialization, JSON schema, IDE support | Performance overhead for hot paths |
| **dataclasses** | Built-in, fast, simple | No validation, no JSON schema, no serialization |
| **TypedDict only** | LangGraph compatible, no overhead | No runtime validation, no defaults |
| **msgspec** | Very fast, validation | Small ecosystem, less IDE support |
| **attrs** | Mature, validation | Less common in modern Python |

### Decision

Use **Pydantic v2 for data models** and **TypedDict for AgentState**:
- Pydantic for all structured data that needs validation (Signal, Decision, RiskAssessment, etc.)
- TypedDict for AgentState (required by LangGraph)
- Pydantic's `ConfigDict(extra="allow")` for forward-compatible models

### Consequences

- **Positive**: Type safety, runtime validation, JSON schema generation, excellent IDE support
- **Negative**: Slight performance overhead (acceptable for trading frequencies)
- **Risk**: Pydantic v1→v2 migration was disruptive (now resolved)

---

## ADR-006: CCXT for Exchanges

**Date**: 2024-Q4
**Status**: Adopted
**Decision**: Use CCXT as the primary exchange abstraction layer for all crypto exchanges.

### Context

The system needs to support 8+ cryptocurrency exchanges with a unified API. Each exchange has different:
- Authentication methods (some require passphrases)
- Market types (spot, futures, perps)
- Order types and parameters
- Rate limits and error handling
- WebSocket protocols

### Alternatives Considered

| Alternative | Pros | Cons |
|---|---|---|
| **CCXT** | 100+ exchanges, unified API, well-maintained, Python native | Python overhead, some exchange quirks |
| **Individual SDKs** | Native features, best support | 8 different APIs to maintain, no consistency |
| **Hummingbot connectors** | Trading-specific | Crypto-only, Hummingbot-specific patterns |
| **Custom abstraction** | Full control | Massive development effort, ongoing maintenance |

### Decision

Use CCXT with our `CCXTBroker` wrapper that:
1. Adds `ExchangeConfig` for configuration management
2. Adds `ExchangeCapabilities` for feature detection
3. Adds market type routing (spot/futures/perps)
4. Adds configuration validation
5. Adds sandbox mode support

Non-CCXT exchanges (Alpaca, Polymarket) have dedicated brokers.

### Consequences

- **Positive**: Unified API, 8 exchanges supported, community-maintained
- **Negative**: CCXT overhead, exchange-specific quirks require workarounds
- **Risk**: CCXT breaking changes (mitigated by pinning version >=4.0)

---

## ADR-007: 9-Checkpoint Risk Gate

**Date**: 2024-Q4 (adapted from HermesQuantOS)
**Status**: Adopted
**Decision**: Implement a 9-checkpoint risk validation gate that every trade must pass before execution.

### Context

A single risk check (e.g., "is the stop loss set?") is insufficient. Multiple failure modes exist:
- Overtrading (too many trades per day)
- Concentration (too much in one asset)
- Correlation (all positions move together)
- Missing stop loss (no downside protection)
- Poor risk:reward (negative expectancy)
- Daily/weekly drawdown limits

### The 9 Checkpoints

| # | Checkpoint | Why It Matters |
|---|---|---|
| 1 | Risk per trade ≤ 0.5% | Limits single-trade impact |
| 2 | Daily loss ≤ 1% | Prevents catastrophic daily drawdowns |
| 3 | Weekly loss ≤ 3% | Prevents cascading weekly losses |
| 4 | Risk:Reward ≥ 1:2 | Ensures positive expectancy |
| 5 | Stop loss exists | No unprotected positions |
| 6 | Valid entry price | Prevents erroneous orders |
| 7 | Valid direction | Prevents malformed orders |
| 8 | Not overtrading | Prevents emotional/revenge trading |
| 9 | Correlated positions < 3 | Prevents concentration risk |

### Alternatives Considered

| Alternative | Pros | Cons |
|---|---|---|
| **9 checkpoints** | Comprehensive, failsafe | More complexity |
| **5 core checkpoints** | Simpler | Misses edge cases (correlation, overtrading) |
| **3 critical checkpoints** | Minimal | Insufficient protection |
| **Configurable checkpoints** | Flexible | Can be disabled, defeats purpose |
| **LLM-based risk assessment** | Contextual | Non-deterministic, can be convinced to approve |

### Decision

9 hard checkpoints because:
1. Each addresses a distinct failure mode
2. ALL must pass for approval (AND logic, not OR)
3. If ANY fails, the trade is VETOED
4. No override possible (constitutional guarantee)

### Consequences

- **Positive**: Comprehensive protection, clear audit trail, deterministic outcomes
- **Negative**: Some good trades may be vetoed (acceptable: safety over profit)
- **Risk**: Checkpoint rigidity may need adjustment over time (requires code change)

---

## ADR-008: Factor Registry Pattern

**Date**: 2025-Q1
**Status**: Adopted
**Decision**: Implement a centralized FactorRegistry with unified FactorHandle for both class-based and function-based factors.

### Context

Factors come from multiple sources with different patterns:
- Technical/Fundamental: Class-based (AlphaFactor subclass)
- Alpha101/GTJA191/Qlib158/Academic: Function-based (meta dict + compute function)

A unified interface is needed for:
- Discovery (list by zoo, theme, universe)
- Computation (compute any factor from a panel)
- Validation (output quality checks)
- Health monitoring (track load errors)

### Alternatives Considered

| Alternative | Pros | Cons |
|---|---|---|
| **FactorRegistry + FactorHandle** | Unified interface, lazy loading, validation | More abstraction |
| **Direct module imports** | Simple, no abstraction | No discovery, no validation, no health check |
| **Plugin system** | Dynamic, extensible | Runtime complexity, security concerns |
| **Separate registries per zoo** | Isolation | No cross-zoo discovery, code duplication |

### Decision

Single `FactorRegistry` with `FactorHandle` that:
1. Wraps both class-based and function-based factors
2. Provides unified `compute(panel)` interface
3. Validates output quality (no inf, < 95% NaN)
4. Supports discovery by zoo, theme, universe
5. Thread-safe singleton via `get_default_registry()`
6. AST-based metadata extraction (no import needed for discovery)

### Consequences

- **Positive**: Unified API, lazy loading, output validation, health monitoring
- **Negative**: More abstraction, FactorHandle indirection
- **Risk**: Factor format divergence (mitigated by FactorHandle adapter)

---

## ADR-009: ATR-Based Position Sizing

**Date**: 2025-Q1
**Status**: Adopted (v2 graph)
**Decision**: Implement fixed-fractional ATR-based position sizing with three take-profit levels.

### Context

Position sizing is critical for risk management. Fixed lot sizes don't account for volatility differences between assets. ATR (Average True Range) provides a volatility-adjusted measure that:
- Adapts to each asset's volatility
- Provides consistent risk across different instruments
- Naturally sets stop-loss and take-profit levels

### Alternatives Considered

| Alternative | Pros | Cons |
|---|---|---|
| **Fixed-fractional ATR** | Volatility-adapted, consistent risk, TP levels | Requires ATR calculation, may be too conservative |
| **Kelly Criterion** | Optimal growth rate | Requires accurate win rate, can be aggressive |
| **Fixed lot size** | Simple | Ignores volatility, inconsistent risk |
| **Risk parity** | Equal risk contribution | Complex, requires correlation matrix |
| **Volatility targeting** | Portfolio-level risk control | Doesn't set stop/take-profit levels |

### Decision

Fixed-fractional ATR with TP1/TP2/TP3 because:
1. ATR adapts to each asset's volatility profile
2. Fixed-fractional ensures consistent risk per trade
3. Three TP levels allow partial profit-taking
4. Stop loss at 1.5×ATR provides structural invalidation
5. Risk:Reward at TP3 = 1:2.00 meets constitutional minimum

### Consequences

- **Positive**: Volatility-adapted, consistent risk, multiple exit levels
- **Negative**: Requires ATR data, may underperform in low-vol regimes
- **Risk**: ATR may be too wide/narrow for some assets (multipliers are configurable)

---

## ADR-010: FastAPI for API Layer

**Date**: 2024-Q4
**Status**: Adopted
**Decision**: Use FastAPI as the API server with uvicorn for ASGI.

### Context

The system needs an HTTP API for:
- Market data queries
- Trading execution
- Agent status monitoring
- Backtest management
- Real-time WebSocket streaming

### Alternatives Considered

| Alternative | Pros | Cons |
|---|---|---|
| **FastAPI** | Async, OpenAPI docs, Pydantic integration, WebSocket | Relatively new, less middleware |
| **Flask** | Mature, simple | Synchronous, no native async, no OpenAPI |
| **Django** | Full-featured, ORM | Too heavy, synchronous, wrong abstraction |
| **Starlette** | Lightweight, async | No built-in OpenAPI, more boilerplate |

### Decision

FastAPI because:
1. Native async support (critical for trading operations)
2. Automatic OpenAPI documentation
3. Pydantic integration for request/response validation
4. WebSocket support for real-time streaming
5. High performance (comparable to Node.js/Go)

### Consequences

- **Positive**: Async, documented, validated, fast
- **Negative**: Less middleware ecosystem than Flask/Django
- **Risk**: Breaking changes in FastAPI (mitigated by pinning version)

---

## ADR-011: Kill Switch Design

**Date**: 2024-Q4
**Status**: Adopted
**Decision**: Implement an automatic kill switch that triggers on drawdown, daily loss, and weekly loss thresholds.

### Context

In extreme market conditions, the system must automatically halt all trading and close positions. This cannot depend on:
- Agent judgment (agents may disagree)
- Human monitoring (may not be watching)
- Network connectivity (may be down)

The kill switch must be an independent, automatic mechanism.

### Kill Switch Triggers

| Trigger | Threshold | Action |
|---|---|---|
| Daily PnL | ≤ -2% | Activate kill switch |
| Weekly PnL | ≤ -5% | Activate kill switch |
| Max Drawdown | ≥ 15% | Activate kill switch |

### Alternatives Considered

| Alternative | Pros | Cons |
|---|---|---|
| **Automatic kill switch** | Instant response, no human delay | May trigger on false positives |
| **Manual kill switch only** | Human judgment | Too slow in fast-moving markets |
| **Configurable thresholds** | Flexible | Can be misconfigured |
| **Gradual wind-down** | Less disruptive | Too slow for catastrophic scenarios |

### Decision

Automatic kill switch with hardcoded thresholds because:
1. Speed is critical (markets can move 5% in minutes)
2. No human dependency (24/7 operation)
3. Hardcoded thresholds (cannot be misconfigured)
4. Manual reset required (forces human review)

### Consequences

- **Positive**: Immediate capital protection, no human dependency
- **Negative**: May trigger unnecessarily in volatile but recoverable situations
- **Risk**: False positive triggers (mitigated by conservative thresholds)

---

## ADR-012: Dual Graph Version Strategy

**Date**: 2025-Q1
**Status**: Adopted
**Decision**: Maintain both v1 (`graph.py`) and v2 (`graph_v2.py`) trading graphs during the transition period.

### Context

The v2 graph introduces significant new features (multi-path routing, position sizing, portfolio validation, smart order routing, human checkpoints). Rather than replacing v1 immediately, both versions coexist during the transition.

### Alternatives Considered

| Alternative | Pros | Cons |
|---|---|---|
| **Dual graphs (v1 + v2)** | Backward compatible, gradual migration | Code duplication, maintenance burden |
| **Replace v1 with v2** | Single codebase | Breaking changes, no rollback |
| **Feature flags** | Single graph, configurable | Complex conditional logic |
| **v2 only, deprecate v1** | Clean break | No backward compatibility |

### Decision

Dual graphs during transition because:
1. v1 is battle-tested (2504+ tests pass)
2. v2 adds new features that need validation
3. Users can choose which graph to use
4. Gradual migration reduces risk

### Consequences

- **Positive**: Backward compatibility, safe migration
- **Negative**: Code duplication, must maintain both
- **Risk**: Divergence between v1 and v2 (mitigated by shared AgentState)

---

## ADR-013: Python 3.11 Minimum

**Date**: 2024-Q4
**Status**: Adopted
**Decision**: Require Python 3.11 as the minimum version.

### Context

The system needs modern Python features for performance, type safety, and developer experience.

### Key Features Used

| Feature | Python Version | Usage |
|---|---|---|
| `tomllib` | 3.11 | Built-in TOML parsing |
| `ExceptionGroup` | 3.11 | Multiple exception handling |
| `Self` type | 3.11 | Recursive type annotations |
| `TaskGroup` | 3.11 | Structured concurrency |
| `TypedDict` with `Annotated` | 3.9+ | AgentState definition |
| `match` statement | 3.10 | Pattern matching (potential) |

### Alternatives Considered

| Version | Pros | Cons |
|---|---|---|
| **3.11** | Modern features, performance, good compatibility | Not available on older systems |
| **3.10** | Wider availability | Missing 3.11 features |
| **3.12** | Latest features | Some libraries not compatible |
| **3.9** | Maximum compatibility | Missing important features |

### Decision

Python 3.11 because:
1. Significant performance improvements (10-60% faster than 3.10)
2. Modern type system features
3. Good library compatibility
4. `tomllib` built-in (no PyPI dependency)

### Consequences

- **Positive**: Performance, features, type safety
- **Negative**: Not available on some older systems
- **Risk**: Some deployment environments may not support 3.11 (decreasing risk)

---

## ADR-014: Monorepo Structure

**Date**: 2024-Q4
**Status**: Adopted
**Decision**: Consolidate 20+ repositories into a single monorepo under the `quant_nanggroe` package.

### Context

The project evolved from 20+ independent repositories, each with its own:
- Directory structure
- Dependency management
- Testing framework
- Documentation
- Configuration format

Maintaining 20+ repos was unsustainable for:
- Cross-repo refactoring
- Dependency management
- Consistent testing
- Documentation alignment

### Alternatives Considered

| Alternative | Pros | Cons |
|---|---|---|
| **Monorepo** | Unified deps, single CI, easy refactoring | Large repo, complex tooling |
| **Multi-repo** | Isolation, independent releases | Cross-repo coordination, dependency hell |
| **Meta-repo (git submodules)** | Some isolation | Submodule complexity, sync issues |
| **Workspace (like Cargo)** | Best of both | No Python-native workspace tool |

### Decision

Monorepo because:
1. Single dependency tree (no version conflicts)
2. Single test suite (easy cross-module testing)
3. Single CI pipeline (simplified DevOps)
4. Easy cross-module refactoring
5. Consistent code style and tooling

### Consequences

- **Positive**: Unified deps, easy refactoring, consistent testing
- **Negative**: Large repo, longer CI times
- **Risk**: Merge conflicts (mitigated by clear module boundaries)

---

## ADR-015: Function-Based Factor Pattern

**Date**: 2025-Q1
**Status**: Adopted
**Decision**: Support both class-based and function-based factor patterns, with function-based as the preferred pattern for new factors.

### Context

The Alpha101 and GTJA191 factor zoos were ported from Vibe-Trading, which uses a function-based pattern:
```python
__alpha_meta_xxx = { "id": "xxx", "zoo": "alpha101", ... }
def compute_xxx(panel) -> pd.DataFrame: ...
```

This pattern is simpler than the class-based pattern:
```python
class MyFactor(AlphaFactor):
    name = "xxx"
    meta = FactorMeta(...)
    def compute(self, df) -> pd.DataFrame: ...
```

### Decision

Support both patterns via `FactorHandle`:
- Class-based: For factors with complex state or inheritance
- Function-based: For simple formulaic factors (preferred for new additions)

### Consequences

- **Positive**: Flexibility, simpler factor authoring, compatible with existing zoos
- **Negative**: Two patterns to maintain, FactorHandle indirection
- **Risk**: Pattern divergence (mitigated by FactorHandle adapter)

---

## Merge Decisions per Repo

### AI-Trader

| Attribute | Decision |
|---|---|
| **Priority** | HIGH |
| **Strategy** | FULL |
| **What We Keep** | Agent architecture, trading logic, exchange abstraction |
| **What We Reject** | Legacy Python 3.8 code, custom LLM wrappers |
| **Rationale** | Core trading agent patterns formed the basis of our agent system |

### AutoHedge

| Attribute | Decision |
|---|---|
| **Priority** | HIGH |
| **Strategy** | PARTIAL |
| **What We Keep** | Hedging strategies, risk parity, correlation monitoring |
| **What We Reject** | Custom database layer, outdated API |
| **Rationale** | Hedging and correlation concepts adopted into risk engine |

### AutoTrader

| Attribute | Decision |
|---|---|
| **Priority** | CRITICAL |
| **Strategy** | FULL |
| **What We Keep** | Auto-trading loop, signal generation, execution framework |
| **What We Reject** | Monolithic architecture, no multi-agent support |
| **Rationale** | Core auto-trading loop is the foundation of TradingGraph |

### Clipper-AI

| Attribute | Decision |
|---|---|
| **Priority** | MEDIUM |
| **Strategy** | PARTIAL |
| **What We Keep** | Quick-profit strategies, scalping indicators |
| **What We Reject** | No risk management, aggressive position sizing |
| **Rationale** | Fast-execution patterns adopted for execution engine |

### Crucix

| Attribute | Decision |
|---|---|
| **Priority** | MEDIUM |
| **Strategy** | REFERENCE |
| **What We Keep** | Cross-validation approach, signal quality metrics |
| **What We Reject** | Proprietary data format, no factor framework |
| **Rationale** | Referenced for signal validation patterns |

### FinceptTerminal

| Attribute | Decision |
|---|---|
| **Priority** | HIGH |
| **Strategy** | PARTIAL |
| **What We Keep** | Terminal UI patterns, data visualization, WebSocket streaming |
| **What We Reject** | Frontend-only, no backend trading logic |
| **Rationale** | UI patterns and real-time streaming adopted for API layer |

### HermesQuantOS

| Attribute | Decision |
|---|---|
| **Priority** | CRITICAL |
| **Strategy** | FULL |
| **What We Keep** | Risk Officer (9-checkpoint gate), strategy lifecycle, audit trail, 5-layer execution stack |
| **What We Reject** | TypeScript components, browser-only architecture |
| **Rationale** | Risk framework and constitutional limits directly adopted |

### Kronos

| Attribute | Decision |
|---|---|
| **Priority** | MEDIUM |
| **Strategy** | REFERENCE |
| **What We Keep** | Time-series analysis patterns |
| **What We Reject** | Custom framework, no multi-agent |
| **Rationale** | Referenced for time-series factor computation |

### Misi-Screener

| Attribute | Decision |
|---|---|
| **Priority** | MEDIUM |
| **Strategy** | PARTIAL |
| **What We Keep** | Stock screening logic, fundamental analysis |
| **What We Reject** | Limited to Malaysian market |
| **Rationale** | Screening patterns adopted for researcher agent |

### MoneyPrinterTurbo

| Attribute | Decision |
|---|---|
| **Priority** | LOW |
| **Strategy** | REFERENCE |
| **What We Keep** | Yield farming concepts |
| **What We Reject** | DeFi-only, no risk management |
| **Rationale** | Referenced for yield optimization patterns |

### OpenAlice

| Attribute | Decision |
|---|---|
| **Priority** | MEDIUM |
| **Strategy** | PARTIAL |
| **What We Keep** | Open order management, exchange connectivity |
| **What We Reject** | Limited exchange support |
| **Rationale** | Order management patterns adopted for execution engine |

### Pentaract

| Attribute | Decision |
|---|---|
| **Priority** | LOW |
| **Strategy** | REFERENCE |
| **What We Keep** | Multi-dimensional analysis concept |
| **What We Reject** | Academic-only, no production code |
| **Rationale** | Conceptual reference for multi-factor analysis |

### QuantDinger

| Attribute | Decision |
|---|---|
| **Priority** | HIGH |
| **Strategy** | PARTIAL |
| **What We Keep** | Factor computation, alpha generation, backtesting |
| **What We Reject** | Proprietary data pipeline |
| **Rationale** | Factor computation patterns adopted for FactorRegistry |

### QuantMuse

| Attribute | Decision |
|---|---|
| **Priority** | MEDIUM |
| **Strategy** | REFERENCE |
| **What We Keep** | Research methodology, factor documentation |
| **What We Reject** | No production infrastructure |
| **Rationale** | Research methodology for factor development |

### SolSniperX

| Attribute | Decision |
|---|---|
| **Priority** | HIGH |
| **Strategy** | FULL |
| **What We Keep** | Solana integration, Jupiter swap, rug check, wallet management |
| **What We Reject** | Meme-coin-only focus |
| **Rationale** | Solana tools directly adopted into exchange/solana/ module |

### Trading-Plan-AI-Interactive

| Attribute | Decision |
|---|---|
| **Priority** | MEDIUM |
| **Strategy** | REFERENCE |
| **What We Keep** | Interactive trading plan generation |
| **What We Reject** | No execution capability |
| **Rationale** | Referenced for human-in-the-loop patterns |

### TradingAgents

| Attribute | Decision |
|---|---|
| **Priority** | CRITICAL |
| **Strategy** | FULL |
| **What We Keep** | Multi-agent debate, bull/bear, risk debate, stress testing |
| **What We Reject** | Simple risk management, no constitutional limits |
| **Rationale** | Agent debate and stress testing directly adopted |

### Vibe-Trading

| Attribute | Decision |
|---|---|
| **Priority** | CRITICAL |
| **Strategy** | FULL |
| **What We Keep** | Factor zoo modules (Alpha101, GTJA191, Qlib158), function-based factor pattern |
| **What We Reject** | Custom orchestration (replaced by LangGraph) |
| **Rationale** | 469+ factors and function-based pattern directly adopted |

### ZeroInject

| Attribute | Decision |
|---|---|
| **Priority** | LOW |
| **Strategy** | REFERENCE |
| **What We Keep** | Zero-latency execution concept |
| **What We Reject** | Custom exchange protocol |
| **Rationale** | Referenced for low-latency execution patterns |

### Dhaher-Corporation

| Attribute | Decision |
|---|---|
| **Priority** | MEDIUM |
| **Strategy** | REFERENCE |
| **What We Keep** | Enterprise patterns, security practices |
| **What We Reject** | Java/TypeScript components |
| **Rationale** | Enterprise security and audit patterns referenced |

### PromptForgeAI

| Attribute | Decision |
|---|---|
| **Priority** | MEDIUM |
| **Strategy** | PARTIAL |
| **What We Keep** | Prompt engineering patterns, LLM optimization |
| **What We Reject** | General-purpose focus (we need trading-specific) |
| **Rationale** | Prompt patterns adopted for agent system prompts |

---

© 2025-2026 Quant Nanggroe AI | Decision Log v4.0.0
