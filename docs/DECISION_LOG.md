# Decision Log: Quant Nanggroe AI

**Version 15.3.0 | Architecture Decision Records**

This document records the key technical decisions made during the consolidation of the Quant Nanggroe AI ecosystem. Each entry follows the Architecture Decision Record (ADR) format with Decision ID, category, legacy components, consolidated target, and technical rationale.

---

## DEC-001: Terminal Interface Consolidation

| Field | Value |
|---|---|
| **Decision ID** | DEC-001 |
| **Date** | 2026-01 |
| **Category** | Frontend / User Interface |
| **Status** | Accepted |
| **Legacy Components** | FinceptTerminal (Python CLI), bloomberg-terminal-style TUI |
| **Consolidated Target** | Next.js Web Terminal (React 19 + TypeScript + Vite) |

### Context

The project had two separate terminal interfaces:

1. **FinceptTerminal** — A Python-based CLI/TUI built with Rich and Textual. It provided a console-based interface for market data queries, research, and configuration. However, it was limited to terminal environments, had no real-time charting capability, and could not render complex multi-panel layouts.

2. **bloomberg-terminal-style TUI** — An early prototype attempting to replicate the Bloomberg Terminal experience in a terminal emulator. It suffered from severe layout constraints (terminal cells are not pixels), no drag-and-drop, no embeddable charts, and no WebSocket support for real-time data.

### Decision

Consolidate both into a **Next.js-based Web Terminal** using React 19 with a desktop-OS-inspired window manager. The current implementation uses:

- `WindowFrame` component for draggable, resizable panels
- `Taskbar` dock for application launching
- `OmniBar` spotlight search for commands
- `ControlCenter` for risk dashboard and configuration
- WebSocket integration for real-time market data

### Rationale

| Factor | FinceptTerminal | Bloomberg TUI | Next.js Web Terminal |
|---|---|---|---|
| Real-time charting | None | ASCII art only | Full OHLCV with Lightweight Charts |
| Multi-panel layout | Terminal tabs only | Fixed grid | Draggable windows with z-index |
| Mobile/tablet access | SSH only | SSH only | Responsive web |
| Drag-and-drop | No | No | Yes |
| Theme support | Terminal colors only | Terminal colors only | Full CSS theming (light/dark) |
| Deployment | Local Python | Local Python | Docker container, any host |
| Maintainability | Python + Rich/Textual | Python + curses | TypeScript + React ecosystem |

The web terminal also enables future features that are impossible in a CLI: interactive strategy configuration modals, real-time agent state visualization (`AgentHud`, `SwarmGraph`), and embedded browser windows for external research.

### Consequences

- **Positive**: Richer UX, real-time updates, broader accessibility, maintainable TypeScript codebase
- **Negative**: Requires browser runtime, higher memory footprint than CLI, initial load time
- **Mitigation**: Lazy-load windows, Vite code splitting, WebSocket compression

---

## DEC-002: Execution Layer Optimization

| Field | Value |
|---|---|
| **Decision ID** | DEC-002 |
| **Date** | 2026-02 |
| **Category** | Execution / Performance |
| **Status** | Accepted |
| **Legacy Components** | SolSniperX (Rust), Kronos (C++), AI-Trader (Python) |
| **Consolidated Target** | Kronos C++ execution engine with PyO3 Python bindings |

### Context

Three separate execution systems existed:

1. **SolSniperX** — A Rust-based Solana sniper bot optimized for MEV and token sniping on Solana DEXes. Extremely fast (sub-millisecond transaction submission) but limited to Solana ecosystem.

2. **Kronos** — A C++ execution engine designed for high-frequency order routing across multiple venues. Provided low-latency path but had no Python integration and required manual C++ development for new strategies.

3. **AI-Trader** — A Python-based trading module using asyncio and ccxt. Flexible but slow (50-200ms order round-trip) due to Python GIL and async overhead.

### Decision

Consolidate execution into **Kronos C++ with PyO3 bindings**. The C++ core handles order book management, routing, and submission at microsecond latency. Python bindings via PyO3 allow the LangGraph agent system to submit orders without context switching.

### Rationale

| Factor | SolSniperX (Rust) | Kronos (C++) | AI-Trader (Python) | Kronos + PyO3 |
|---|---|---|---|---|
| Order latency | <1ms | <1ms | 50-200ms | <1ms (C++) / ~5ms (PyO3 bridge) |
| Multi-venue | Solana only | Any venue | Any venue (ccxt) | Any venue |
| Python integration | No | No | Native | Yes (PyO3) |
| Memory safety | Safe (Rust) | Manual (C++) | Safe (GC) | Bridge layer |
| Development speed | Medium | Slow | Fast | Medium (Python orchestration) |
| Strategy expressiveness | Limited | Full C++ | Full Python | Full Python (orchestration) + C++ (execution) |

The hybrid approach allows the decision-making pipeline (LangGraph, pressure normalization, risk management) to remain in Python where expressiveness matters, while the execution hot path stays in C++ where latency matters.

### Consequences

- **Positive**: Sub-millisecond execution for time-critical orders, Python remains the strategy language, single execution codebase
- **Negative**: PyO3 bridge adds ~5ms latency, C++ compilation complexity, two-language debugging
- **Mitigation**: Fallback to ccxt Python execution when Kronos is unavailable; comprehensive integration tests

---

## DEC-003: Multi-Agent Coordination

| Field | Value |
|---|---|
| **Decision ID** | DEC-003 |
| **Date** | 2026-01 |
| **Category** | Agent Architecture |
| **Status** | Accepted |
| **Legacy Components** | CrewAI, AutoGen, openhuman agent frameworks |
| **Consolidated Target** | LangGraph Custom StateGraph |

### Context

Three agent coordination frameworks were evaluated and partially integrated:

1. **CrewAI** — Role-based agent orchestration with built-in task delegation. Good for collaborative workflows but lacks fine-grained state control, conditional routing, and deterministic execution guarantees. Agents communicate through "tasks" which are opaque strings, making audit trails difficult.

2. **AutoGen** (Microsoft) — Conversation-based multi-agent framework. Excellent for research and discussion workflows but fundamentally conversational — agents take turns speaking, which is wrong for a trading system where parallel sensor execution is required. No built-in veto mechanism.

3. **openhuman** — A community agent framework focused on autonomous operation. Lacks the state machine model needed for the strict sequential decision pipeline (research → analyze → strategize → risk-check → execute).

### Decision

Use **LangGraph Custom StateGraph** as the single agent coordination layer. LangGraph provides:

- **Explicit state schema** (`AgentState` Pydantic model) — every field is typed and validated
- **Conditional routing** — `should_continue_after_regime()` and `should_continue_after_risk()` gates
- **Deterministic execution** — same inputs produce identical state transitions
- **Built-in persistence** — checkpoint and replay for audit
- **No LLM in risk management** — the Risk Manager node is pure Python logic, not an LLM call

### Rationale

| Factor | CrewAI | AutoGen | openhuman | LangGraph |
|---|---|---|---|---|
| State management | Implicit (task strings) | Conversation history | Variable | Explicit Pydantic model |
| Conditional routing | No | No | No | Yes (conditional edges) |
| Veto/gate mechanism | No | No | No | Yes (routing functions) |
| Parallel execution | Partial | No (conversational) | Yes | Yes (fan-out/fan-in) |
| Audit trail | Task logs | Chat history | Variable | Full state trace |
| Deterministic | No (LLM-driven) | No (LLM-driven) | No | Yes (deterministic nodes + LLM where needed) |
| Python native | Yes | Yes | Yes | Yes |

CrewAI and AutoGen remain as **optional** dependencies in `pyproject.toml` for research workflows, but the core trading graph is LangGraph-only.

### Consequences

- **Positive**: Deterministic decision pipeline, full state auditability, conditional veto gates, typed state transitions
- **Negative**: More boilerplate than CrewAI for simple agent workflows, LangGraph API stability risk
- **Mitigation**: Pin LangGraph version (`^0.2.60`), abstraction layer over graph construction

---

## DEC-004: Python Runtime Standardization

| Field | Value |
|---|---|
| **Decision ID** | DEC-004 |
| **Date** | 2026-01 |
| **Category** | Infrastructure / Runtime |
| **Status** | Accepted |
| **Legacy Components** | Python 3.9-3.11 mixed, pip + pipenv + poetry mixed |
| **Consolidated Target** | Python 3.12+, uv workspaces, Poetry for dependency management |

### Context

Across the 23 repositories being merged, the Python runtime was inconsistent:

- Some repos required Python 3.9 (using `dict |` union syntax not available)
- Some required Python 3.10+ (using `match` statements)
- Some required Python 3.11+ (using `ExceptionGroup`)
- Package managers included pip, pipenv, and poetry with conflicting lock files

### Decision

Standardize on:

- **Python 3.12+** — Required for `type` keyword syntax in generics (`list[str]` not `List[str]`), improved error messages, and performance improvements (PEP 709 inline comprehension)
- **Poetry** — For dependency resolution and lock file management (`pyproject.toml`)
- **uv** — For fast package installation and virtual environment management
- **Ruff** — For linting and formatting (replaces flake8, isort, black)
- **MyPy strict** — For type checking with `disallow_untyped_defs = true`

### Rationale

| Factor | Python 3.9 | Python 3.10 | Python 3.11 | Python 3.12 |
|---|---|---|---|---|
| Generic syntax | `List[str]` | `list[str]` (3.9+) | `list[str]` | `list[str]` |
| Match statements | No | Yes | Yes | Yes |
| Exception groups | No | No | Yes | Yes |
| Type keyword | No | No | No | Yes (PEP 695) |
| Performance | Baseline | ~10% faster | ~25% faster | ~40% faster |
| GIL improvements | No | No | No | PEP 703 (future) |

Python 3.12 was chosen because it is the minimum version that supports the type syntax used throughout the codebase (`list[str]`, `dict[str, Any]`, `str | None`) and provides meaningful performance improvements for the numerical computation paths.

### Consequences

- **Positive**: Consistent runtime, modern type syntax, faster execution, single package manager
- **Negative**: Some legacy repos may need code changes for 3.12 compatibility, uv is relatively new
- **Mitigation**: `ruff` automated upgrade rules, `pyupgrade` for syntax modernization

---

## DEC-005: Backtesting Engine Selection

| Field | Value |
|---|---|
| **Decision ID** | DEC-005 |
| **Date** | 2026-01 |
| **Category** | Backtesting / Validation |
| **Status** | Accepted |
| **Legacy Components** | Custom backtest engine (TypeScript), Freqtrade backtesting, VectorBT standalone |
| **Consolidated Target** | NautilusTrader for HFT validation + VectorBT for rapid research |

### Context

Three backtesting approaches existed:

1. **Custom TypeScript backtest engine** (`services/backtest_engine.ts`) — Browser-based, included execution reality simulation (slippage, spread, latency). However, limited to single-asset, no walk-forward analysis, and no statistical significance testing.

2. **Freqtrade backtesting** — Full-featured but designed for Freqtrade's strategy format. Would require adapting all QNA strategies to Freqtrade's `IStrategy` interface, which conflicts with the LangGraph decision pipeline.

3. **VectorBT** — Extremely fast vectorized backtesting. Perfect for parameter sweeps but lacks execution simulation and has no concept of regime-gated decisions.

### Decision

Use **NautilusTrader** for production-grade backtesting (execution simulation, walk-forward, multi-venue) and **VectorBT** for rapid research (parameter sweeps, factor evaluation).

The custom `BacktestEngine` in TypeScript is retained for the frontend's execution reality simulation but is no longer the primary backtesting engine.

### Rationale

| Factor | Custom TS Engine | Freqtrade | VectorBT | NautilusTrader |
|---|---|---|---|---|
| Execution simulation | Basic | Full | None | Full (order book replay) |
| Walk-forward | No | Partial | No | Yes |
| Multi-asset | No | Yes | Yes | Yes |
| Speed | Slow | Medium | Very fast | Fast (Rust core) |
| Strategy format | Custom | Freqtrade IStrategy | Pandas-based | Custom (Python) |
| Live trading bridge | No | Yes | No | Yes |
| Statistical tests | Basic | Basic | No | Yes |

NautilusTrader's Rust core provides the execution simulation fidelity needed for production validation, while its Python API integrates naturally with the LangGraph pipeline. VectorBT remains for the `alpha101.py` factor evaluation and parameter sweeps where speed matters more than simulation fidelity.

### Consequences

- **Positive**: Production-grade backtesting, walk-forward validation, no strategy format conversion needed
- **Negative**: NautilusTrader has a steeper learning curve than Freqtrade, two backtesting systems to maintain
- **Mitigation**: Shared `BacktestTool` in the agent tools registry that routes to the appropriate engine

---

## DEC-006: Memory Architecture

| Field | Value |
|---|---|
| **Decision ID** | DEC-006 |
| **Date** | 2026-02 |
| **Category** | Memory / Context Management |
| **Status** | Accepted |
| **Legacy Components** | No persistent memory, stateless agent sessions |
| **Consolidated Target** | Vector DB (TF-IDF) + Event-sourced audit + Conversation condenser |

### Context

The initial system was entirely stateless — each agent invocation started from scratch with no memory of previous decisions, research, or market conditions. This caused:

- Repeated LLM calls for the same research queries
- No learning from past mistakes
- Inability to correlate current decisions with historical patterns
- Wasted tokens on redundant context building

### Decision

Implement a three-layer memory system:

1. **Vector Memory** (`VectorMemory` in `memory/vector.py`) — TF-IDF-based in-memory vector store for semantic search. Documents (research notes, strategy descriptions, market analyses) are embedded and retrieved via cosine similarity. Zero external dependencies (no ChromaDB/Pinecone required). Suitable for up to ~100k documents.

2. **Event-Sourced Audit Trail** (`audit_events` PostgreSQL table) — Every state transition in the LangGraph is persisted as an immutable event. This enables full reconstruction of any trading decision from raw data to execution. Append-only, no deletes, infinite retention.

3. **Conversation Condenser** (`memory/conversation.py`) — Manages the agent context window by maintaining recent messages in full and compressing older context into summaries. Prevents token overflow in long-running sessions.

### Rationale

| Factor | No Memory | Redis Cache Only | Full Vector DB | Three-Layer (chosen) |
|---|---|---|---|---|
| Research reuse | None | TTL-based cache | Semantic search | Semantic search + cache |
| Decision audit | None | Lost on restart | Partial | Full event sourcing |
| Context management | None | Manual truncation | None | Automatic condensation |
| External dependencies | None | Redis | ChromaDB/Pinecone | None (built-in TF-IDF) |
| Setup complexity | Minimal | Low | High (managed DB) | Low |

The TF-IDF approach was chosen over neural embeddings (OpenAI, sentence-transformers) to eliminate external API dependencies and reduce latency. For production at scale (>100k documents), the `VectorMemory` can be swapped to ChromaDB or pgvector with no API changes.

### Consequences

- **Positive**: Persistent memory across sessions, semantic search for research, full audit trail, no external vector DB dependency
- **Negative**: TF-IDF is less semantically rich than neural embeddings, in-memory storage doesn't survive container restarts without persistence
- **Mitigation**: PostgreSQL-backed persistence layer for vector documents (planned), pgvector for production scale

---

## DEC-007: Risk Management Architecture

| Field | Value |
|---|---|
| **Decision ID** | DEC-007 |
| **Date** | 2026-01 |
| **Category** | Risk / Safety |
| **Status** | Accepted |
| **Legacy Components** | Ad-hoc risk checks, no formal validation |
| **Consolidated Target** | Pydantic validation + 9-checkpoint VETO + kill switch + VaR/CVaR constraints |

### Context

The original system had no formal risk management. Risk checks were scattered across different services with no unified enforcement. A misconfigured agent could theoretically risk 100% of capital on a single trade.

### Decision

Implement a **Constitutional Risk Guard** with the following architecture:

1. **Pydantic Validation** — All risk parameters are validated at the type level. `AgentState.risk_clearance` is typed as `RiskClearance` enum (CLEAR/BLOCKED/PAUSE). Invalid states are impossible to construct.

2. **9-Checkpoint VETO System** (`ConstitutionalRiskGuard` in `engine/risk_guard.py`) — Every trade must pass all 9 checkpoints. Any single failure results in immediate VETO. The checkpoints are:

| Checkpoint | Rule | Limit |
|---|---|---|
| 1 | Risk per trade | ≤ 0.5% of account |
| 2 | Daily loss | < 1.0% |
| 3 | Weekly loss | < 3.0% |
| 4 | Risk:Reward ratio | ≥ 1:2 |
| 5 | Stop loss exists | Required, > 0 |
| 6 | Entry price valid | > 0 |
| 7 | Direction valid | BUY/SELL/LONG/SHORT |
| 8 | Not overtrading | ≤ 5 trades/day |
| 9 | Correlated positions | ≤ 3 correlated |

3. **Kill Switch** (`engine/kill_switch.py`) — Automatic activation when daily or weekly loss limits are reached. Closes all positions and enters cooldown.

4. **VaR/CVaR Constraints** (`risk/var.py`, `risk/cvar.py`) — Portfolio-level risk metrics computed before each trade:
   - Parametric VaR at 95% confidence
   - Historical CVaR at 95% confidence
   - Portfolio correlation check (max pairwise correlation ≤ 0.70)

5. **Hardcoded Constitutional Limits** (`config.py`) — The limits are **Python constants**, not environment variables. They cannot be overridden by configuration, environment variables, or agent reasoning.

```python
# These values CANNOT be changed via config or env vars
MAX_RISK_PER_TRADE: float = 0.005
MAX_DAILY_LOSS: float = 0.01
MAX_WEEKLY_LOSS: float = 0.03
MIN_RISK_REWARD: float = 2.0
MAX_CORRELATED_POSITIONS: int = 3
```

### Rationale

| Factor | Ad-hoc Risk | Config-based Risk | Constitutional (chosen) |
|---|---|---|---|
| Override protection | None | Can be changed in config | Hardcoded constants |
| Audit trail | None | Partial | Full 9-checkpoint log |
| Kill switch | None | Manual | Automatic |
| Correlation check | None | Optional | Mandatory |
| VaR/CVaR integration | None | None | Pre-trade validation |
| Pydantic validation | None | Partial | Full (type-level) |
| Agent override | Possible | Possible | **Impossible** |

The constitutional approach was chosen because in a multi-agent system, any single agent with configuration access could theoretically override risk limits. By hardcoding the limits as Python constants, no runtime change can weaken risk protection.

### Consequences

- **Positive**: No override of risk limits, full audit trail, automatic kill switch, portfolio-level risk metrics
- **Negative**: Changing limits requires code change + deployment, limits may be too conservative for some strategies
- **Mitigation**: Softer limits (max_open_positions, max_trades_per_day) are configurable via Settings; only constitutional limits are hardcoded

---

## Decision Summary

| Decision ID | Category | Key Trade-off |
|---|---|---|
| DEC-001 | Frontend | CLI simplicity → Web Terminal richness |
| DEC-002 | Execution | Python flexibility → C++ latency + PyO3 bridge complexity |
| DEC-003 | Agent | Framework convenience → LangGraph determinism + control |
| DEC-004 | Runtime | Compatibility range → Python 3.12+ features + performance |
| DEC-005 | Backtesting | Engine simplicity → NautilusTrader fidelity + VectorBT speed |
| DEC-006 | Memory | Stateless simplicity → Three-layer persistence + audit |
| DEC-007 | Risk | Config flexibility → Constitutional immutability |

---

© 2025-2026 Quant Nanggroe AI | Decision Log v15.3.0
