# Quant Nanggroe AI — Changelog

**Complete Version History**

> This document records all major versions, features, fixes, and milestones in the Quant Nanggroe AI project.

---

## Table of Contents

1. [v4.0.0 — LangGraph v2 Architecture (Current)](#v400--langgraph-v2-architecture-current)
2. [v3.0.0 — 469 Factors + 10 Engines](#v300--469-factors--10-engines)
3. [v2.0.0 — Security + Type Safety](#v200--security--type-safety)
4. [v1.0.0 — Production-Ready Overhaul](#v100--production-ready-overhaul)
5. [v0.1.0 — Initial Structure](#v010--initial-structure)
6. [Detailed Change Log](#detailed-change-log)

---

## v4.0.0 — LangGraph v2 Architecture (Current)

**Release Date**: 2025-Q2
**Theme**: Multi-path execution, smart order routing, human-in-the-loop

### Major Features

- **Multi-path execution graph**: Asset-class conditional routing with 4 specialized paths
  - `crypto_path` → Solana/Jupiter tools, on-chain analysis
  - `forex_path` → FX-specific analysis, carry trade evaluation
  - `equity_path` → Standard equity flow (researcher + macro)
  - `prediction_market_path` → Polymarket / event-contract integration

- **TradingGraphV2**: Enhanced LangGraph StateGraph with 18 nodes and conditional edges
  - `asset_router` node for symbol classification
  - `position_sizer` node with ATR-based sizing (TP1/TP2/TP3)
  - `portfolio_validation` node with concentration/correlation/Kelly checks
  - `smart_execution` node with venue scoring
  - `human_checkpoint` node for high-risk trade approval

- **ATR-based position sizing**: Fixed-fractional model with three take-profit levels
  - Stop Loss = Entry - 1.5 × ATR
  - TP1 = Entry + 1.0 × ATR (R:R = 0.67)
  - TP2 = Entry + 2.0 × ATR (R:R = 1.33)
  - TP3 = Entry + 3.0 × ATR (R:R = 2.00)

- **Smart order routing**: Venue scoring with fee, fill rate, latency, slippage factors

- **Human-in-the-loop checkpoints**: Automatic human approval for high-risk trades

- **AssetRouter**: Regex-based symbol classification with pattern matching for crypto, forex, equity, prediction market

- **Prediction market support**: Polymarket broker, event contract analysis, mandatory human approval

### New Modules

| Module | Path | Description |
|---|---|---|
| `graph_v2.py` | `agents/graph_v2.py` | v2 multi-path trading graph |
| `asset_router.py` | `agents/nodes/asset_router.py` | Asset class detection and routing |
| `position_sizer.py` | `agents/nodes/position_sizer.py` | ATR-based position sizing |
| `portfolio_validator.py` | `agents/nodes/portfolio_validator.py` | Portfolio concentration/correlation/Kelly |
| `smart_executor.py` | `agents/nodes/smart_executor.py` | Smart order routing with venue scoring |
| `human_checkpoint.py` | `agents/nodes/human_checkpoint.py` | Human-in-the-loop checkpoint |
| `polymarket_broker.py` | `exchange/polymarket_broker.py` | Polymarket CLOB integration |

### State Changes

New fields added to `AgentState` TypedDict:
- `asset_class`, `execution_path` — Multi-path routing
- `position_sizing_result` — ATR-based sizing
- `portfolio_validation` — Validation result
- `venue_scores`, `smart_routing_result` — Smart order routing
- `human_approval_required`, `human_approval_status`, `human_approval_reason` — Human-in-the-loop

### New Data Models

- `PositionSizingResult` — ATR sizing with TP1/TP2/TP3
- `PortfolioValidation` — Concentration/correlation/Kelly checks
- `VenueScore` — Venue scoring for smart order routing
- `SmartOrderRouting` — Smart routing result
- `AssetClass` enum — crypto, forex, equity, prediction_market

### Test Coverage

- 2,504+ tests passing
- New tests for all v2 graph nodes
- Integration tests for multi-path routing
- Position sizing calculation tests
- Portfolio validation edge case tests

---

## v3.0.0 — 469 Factors + 10 Engines

**Release Date**: 2025-Q1
**Theme**: Factor engine, exchange factory, multi-asset backtest

### Major Features

- **469+ alpha factors across 7 zoos**:
  - Alpha101: 101 factors (WorldQuant formulaic alphas)
  - GTJA191: 191 factors (Guotai Junan Chinese A-share)
  - Qlib158: 158 factors (Microsoft Qlib features)
  - Barra: 10+ factors (MSCI risk model)
  - Technical: 20+ factors (RSI, MACD, Bollinger, ATR, etc.)
  - Fundamental: 10+ factors (P/E, P/B, ROE, D/E, etc.)
  - Academic: Variable (literature-derived)

- **FactorRegistry**: Centralized factor discovery, computation, and validation
  - Unified `FactorHandle` for class-based and function-based factors
  - Discovery by zoo, theme, universe
  - Output validation (no ±inf, NaN ratio ≤ 95%)
  - Thread-safe singleton via `get_default_registry()`
  - AST-based metadata extraction (no import needed)

- **ExchangeFactory**: Dynamic exchange client creation with 10 exchanges
  - 8 CCXT-backed exchanges: Binance, OKX, Bybit, Bitget, Kraken, KuCoin, Gate, Coinbase
  - Alpaca broker for US equities and forex
  - Polymarket broker for prediction markets
  - Paper trading broker for simulation
  - ExchangeCapabilities for feature detection
  - Market type routing (spot/futures/perps)

- **Multi-asset backtest engines**:
  - Equity engine, Crypto engine, Forex engine, Futures engine
  - Composite engine for multi-asset portfolios
  - Monte Carlo simulation
  - Walk-forward optimization
  - Performance metrics (Sharpe, Sortino, Calmar, etc.)
  - Execution simulation with slippage, partial fills, latency

- **Portfolio optimizers**:
  - Mean-variance optimizer (Markowitz)
  - Risk parity optimizer
  - Equal volatility optimizer

- **Solana integration**:
  - Jupiter swap aggregator
  - RugCheck token safety
  - Mempool monitoring
  - Wallet management
  - Solana-specific broker

### New Modules

| Module | Path | Description |
|---|---|---|
| `registry.py` | `engine/factors/registry.py` | FactorRegistry singleton |
| `alpha101.py` | `engine/factors/alpha101.py` | 101 WorldQuant factors |
| `gtja191.py` | `engine/factors/gtja191.py` | 191 GTJA factors |
| `qlib158.py` | `engine/factors/qlib158.py` | 158 Qlib factors |
| `barra.py` | `engine/factors/barra.py` | Barra risk factors |
| `academic.py` | `engine/factors/academic.py` | Academic factors |
| `pipeline.py` | `engine/factors/pipeline.py` | Factor pipeline |
| `factory.py` | `exchange/factory.py` | ExchangeFactory |
| `ccxt_broker.py` | `exchange/ccxt_broker.py` | CCXT exchange broker |
| `alpaca_broker.py` | `exchange/alpaca_broker.py` | Alpaca broker |
| `paper_broker.py` | `exchange/paper_broker.py` | Paper trading broker |
| `manager.py` | `engine/risk/manager.py` | RiskManager top-level |
| `checks.py` | `engine/risk/checks.py` | 9-checkpoint gate |
| `kill_switch.py` | `engine/risk/kill_switch.py` | Kill switch |
| `drawdown.py` | `engine/risk/drawdown.py` | Drawdown monitor |
| `kelly.py` | `engine/risk/kelly.py` | Kelly Criterion |
| `var.py` | `engine/risk/var.py` | VaR Calculator |
| `correlation.py` | `engine/risk/correlation.py` | Correlation monitor |
| `engine.py` | `engine/backtest/engine.py` | Backtesting engine |
| `jupiter.py` | `exchange/solana/jupiter.py` | Jupiter swap |
| `rugcheck.py` | `exchange/solana/rugcheck.py` | RugCheck |
| `wallet.py` | `exchange/solana/wallet.py` | Wallet management |
| `mempool.py` | `exchange/solana/mempool.py` | Mempool monitoring |

### Merged Repositories

- Vibe-Trading (469+ factors, function-based pattern) → FULL merge
- HermesQuantOS (9-checkpoint risk gate, strategy lifecycle) → FULL merge
- SolSniperX (Solana/Jupiter/RugCheck) → FULL merge
- AutoHedge (risk parity, correlation) → PARTIAL merge
- QuantDinger (factor patterns, backtesting) → PARTIAL merge

---

## v2.0.0 — Security + Type Safety

**Release Date**: 2024-Q4
**Theme**: Pydantic models, constitutional risk limits, security infrastructure

### Major Features

- **Pydantic v2 data models**: All state and data models converted to Pydantic BaseModel
  - MarketData, Signal, Decision, RiskCheckpoint, RiskAssessment
  - PortfolioState, PositionInfo, AgentOutput
  - DebateState, RiskDebateState, VoteResult, CouncilResult
  - ConfigDict with extra="allow" for forward compatibility

- **Constitutional risk limits (HARDCODED)**: Immutable risk constants
  - MAX_RISK_PER_TRADE = 0.005 (0.5%)
  - MAX_DAILY_LOSS = 0.01 (1%)
  - MAX_WEEKLY_LOSS = 0.03 (3%)
  - MIN_RISK_REWARD = 2.0 (1:2)
  - MAX_CORRELATED_POSITIONS = 3
  - MAX_POSITION_SIZE_PCT = 0.10 (10%)
  - MAX_LEVERAGE = 3.0
  - MAX_DRAWDOWN_PCT = 0.15 (15%)
  - MAX_DAILY_TRADES = 5
  - CONFIDENCE_THRESHOLD = 0.65
  - KILL_SWITCH_DAILY_PNL = -0.02 (-2%)
  - KILL_SWITCH_WEEKLY_PNL = -0.05 (-5%)

- **9-Checkpoint Risk Gate**: From HermesQuantOS
  1. Risk per trade limit
  2. Daily loss limit
  3. Weekly loss limit
  4. Risk:Reward ratio
  5. Stop loss exists
  6. Valid entry price
  7. Valid direction
  8. Not overtrading
  9. Correlated position check

- **Kill switch**: Automatic activation on drawdown/daily/weekly limits

- **Security infrastructure**:
  - Key vault for API key storage
  - Authentication module
  - Audit logging
  - Credential leak prevention

- **Configuration system**:
  - Pydantic Settings for type-safe configuration
  - Environment variable and .env file support
  - Structured logging with structlog

### New Modules

| Module | Path | Description |
|---|---|---|
| `state.py` | `agents/state.py` | Complete AgentState and models |
| `constants.py` | `engine/risk/constants.py` | Constitutional limits |
| `keyvault.py` | `security/keyvault.py` | Secure key storage |
| `auth.py` | `security/auth.py` | Authentication |
| `audit.py` | `security/audit.py` | Security audit |
| `credential_inference.py` | `security/credential_inference.py` | Leak detection |
| `settings.py` | `config/settings.py` | Pydantic Settings |
| `logging_config.py` | `config/logging_config.py` | Structured logging |

---

## v1.0.0 — Production-Ready Overhaul

**Release Date**: 2024-Q3
**Theme**: Monorepo consolidation, LangGraph integration, agent architecture

### Major Features

- **Monorepo consolidation**: 4 critical repos merged into `quant_nanggroe` package
  - AutoTrader → Trading graph and agent framework
  - HermesQuantOS → Risk engine and audit trail
  - TradingAgents → Council debate and stress testing
  - Vibe-Trading → Factor zoos (partial, completed in v3)

- **LangGraph StateGraph**: Trading pipeline as a directed graph
  - 7 core nodes: market_analysis, signal_generation, risk_assessment, portfolio_optimization, execution_decision, order_execution, reflection
  - 2 special nodes: council_debate, emergency_exit
  - Conditional edges for risk routing
  - Streaming execution support

- **5 core agents** (expanded from TradingAgents):
  - Researcher: Market data analysis
  - Trader: Execution decisions
  - Strategist: Signal generation
  - Risk: 9-checkpoint validation
  - Portfolio: Asset allocation

- **Agent factory**: Centralized agent creation with LLM routing
  - Deep think model (gpt-4o) for analysis
  - Quick think model (gpt-4o-mini) for decisions
  - Multi-provider support (OpenAI, Anthropic, Google)

- **Council debate system**:
  - Bull/bear debate mechanism
  - Risk debate (conservative/neutral/aggressive)
  - Weighted voting system
  - Consensus threshold

- **API server** (FastAPI):
  - Market data routes
  - Trading routes
  - Agent status routes
  - WebSocket streaming
  - CORS middleware
  - Health check endpoint

- **Memory system**:
  - Knowledge base (ChromaDB vectors)
  - Session state management
  - Trading journal
  - Memory paging for large contexts

### New Modules

| Module | Path | Description |
|---|---|---|
| `graph.py` | `agents/graph.py` | v1 trading graph |
| `base.py` | `agents/base.py` | Base agent, LLM creation |
| `registry.py` | `agents/registry.py` | AgentFactory |
| `debate.py` | `agents/council/debate.py` | Council debate |
| `voting.py` | `agents/council/voting.py` | Council voting |
| `app.py` | `api/app.py` | FastAPI application |
| `knowledge.py` | `memory/knowledge.py` | Knowledge base |
| `session.py` | `memory/session.py` | Session state |
| `journal.py` | `memory/journal.py` | Trading journal |

---

## v0.1.0 — Initial Structure

**Release Date**: 2024-Q2
**Theme**: Project scaffolding, basic structure

### Features

- **Package structure**: `quant_nanggroe` Python package created
- **pyproject.toml**: Project metadata, dependencies, build configuration
- **Basic agent framework**: Initial agent classes
- **Exchange abstraction**: Early exchange interface design
- **Configuration**: Basic settings management
- **Testing**: Initial test infrastructure with pytest

### Initial Dependencies

```
langgraph>=0.2
langchain>=0.3
langchain-openai>=0.2
pydantic>=2.0
pandas>=2.0
numpy>=1.24
ccxt>=4.0
fastapi>=0.100
uvicorn>=0.24
sqlalchemy>=2.0
redis>=5.0
structlog>=23.0
```

---

## Detailed Change Log

### 2025-Q2 (v4.0.0)

| Date | Change | Module |
|---|---|---|
| 2025-06 | Add TradingGraphV2 with multi-path routing | `agents/graph_v2.py` |
| 2025-06 | Add AssetRouter node | `agents/nodes/asset_router.py` |
| 2025-06 | Add PositionSizer node with ATR + TP1/TP2/TP3 | `agents/nodes/position_sizer.py` |
| 2025-06 | Add PortfolioValidator node | `agents/nodes/portfolio_validator.py` |
| 2025-06 | Add SmartExecutor node | `agents/nodes/smart_executor.py` |
| 2025-06 | Add HumanCheckpoint node | `agents/nodes/human_checkpoint.py` |
| 2025-06 | Add PolymarketBroker | `exchange/polymarket_broker.py` |
| 2025-06 | Add prediction_market_path to graph | `agents/graph_v2.py` |
| 2025-06 | Add PositionSizingResult model | `agents/state.py` |
| 2025-06 | Add PortfolioValidation model | `agents/state.py` |
| 2025-06 | Add VenueScore and SmartOrderRouting models | `agents/state.py` |
| 2025-06 | Add AssetClass enum | `agents/state.py` |
| 2025-06 | Add human_approval fields to AgentState | `agents/state.py` |
| 2025-06 | Portfolio validation conditional edges | `agents/graph_v2.py` |
| 2025-06 | Human checkpoint conditional edges | `agents/graph_v2.py` |
| 2025-06 | Council debate loops back to position_sizer | `agents/graph_v2.py` |
| 2025-06 | CRISIS regime requires confidence ≥ 0.85 | `agents/graph_v2.py` |

### 2025-Q1 (v3.0.0)

| Date | Change | Module |
|---|---|---|
| 2025-03 | Add FactorRegistry with thread-safe singleton | `engine/factors/registry.py` |
| 2025-03 | Add FactorHandle for unified factor interface | `engine/factors/registry.py` |
| 2025-03 | Port Alpha101 (101 factors) from Vibe-Trading | `engine/factors/alpha101.py` |
| 2025-03 | Port GTJA191 (191 factors) from Vibe-Trading | `engine/factors/gtja191.py` |
| 2025-03 | Port Qlib158 (158 factors) from Vibe-Trading | `engine/factors/qlib158.py` |
| 2025-03 | Port Academic factors from Vibe-Trading | `engine/factors/academic.py` |
| 2025-03 | Add Barra risk factors | `engine/factors/barra.py` |
| 2025-03 | Add output validation (no inf, < 95% NaN) | `engine/factors/registry.py` |
| 2025-03 | Add AST-based metadata extraction | `engine/factors/registry.py` |
| 2025-02 | Add ExchangeFactory with 10 exchanges | `exchange/factory.py` |
| 2025-02 | Add CCXTBroker for 8 crypto exchanges | `exchange/ccxt_broker.py` |
| 2025-02 | Add AlpacaBroker for US equities/forex | `exchange/alpaca_broker.py` |
| 2025-02 | Add PaperBroker for simulation | `exchange/paper_broker.py` |
| 2025-02 | Add ExchangeCapabilities feature detection | `exchange/factory.py` |
| 2025-02 | Add market type routing (spot/futures/perps) | `exchange/factory.py` |
| 2025-01 | Port Solana/Jupiter from SolSniperX | `exchange/solana/` |
| 2025-01 | Port RugCheck from SolSniperX | `exchange/solana/rugcheck.py` |
| 2025-01 | Port wallet management from SolSniperX | `exchange/solana/wallet.py` |
| 2025-01 | Add backtest engine with multi-asset support | `engine/backtest/` |
| 2025-01 | Add Monte Carlo simulation | `engine/backtest/monte_carlo.py` |
| 2025-01 | Add walk-forward optimization | `engine/backtest/walk_forward.py` |
| 2025-01 | Add portfolio optimizers | `engine/backtest/optimizers/` |

### 2024-Q4 (v2.0.0)

| Date | Change | Module |
|---|---|---|
| 2024-12 | Convert all data models to Pydantic v2 | `agents/state.py` |
| 2024-12 | Add constitutional risk limits (hardcoded) | `engine/risk/constants.py` |
| 2024-12 | Add 9-checkpoint risk gate from HermesQuantOS | `engine/risk/checks.py` |
| 2024-12 | Add kill switch with auto-activation | `engine/risk/kill_switch.py` |
| 2024-12 | Add drawdown monitor | `engine/risk/drawdown.py` |
| 2024-12 | Add VaR calculator | `engine/risk/var.py` |
| 2024-12 | Add Kelly Criterion calculator | `engine/risk/kelly.py` |
| 2024-12 | Add correlation monitor | `engine/risk/correlation.py` |
| 2024-12 | Add RiskManager top-level class | `engine/risk/manager.py` |
| 2024-12 | Add stress testing (6 scenarios) | `engine/risk/manager.py` |
| 2024-11 | Add security key vault | `security/keyvault.py` |
| 2024-11 | Add authentication module | `security/auth.py` |
| 2024-11 | Add audit logging | `security/audit.py` |
| 2024-11 | Add credential leak prevention | `security/credential_inference.py` |
| 2024-11 | Add Pydantic Settings configuration | `config/settings.py` |
| 2024-11 | Add structured logging | `config/logging_config.py` |

### 2024-Q3 (v1.0.0)

| Date | Change | Module |
|---|---|---|
| 2024-09 | Add TradingGraph with LangGraph StateGraph | `agents/graph.py` |
| 2024-09 | Add AgentFactory for agent creation | `agents/registry.py` |
| 2024-09 | Add base agent with LLM routing | `agents/base.py` |
| 2024-09 | Add Researcher agent | `agents/researcher/` |
| 2024-09 | Add Trader agent | `agents/trader/` |
| 2024-09 | Add Strategist agent | `agents/strategist/` |
| 2024-09 | Add Risk agent | `agents/risk/` |
| 2024-09 | Add Portfolio agent | `agents/portfolio/` |
| 2024-09 | Add Execution agent | `agents/execution/` |
| 2024-09 | Add Macro agent | `agents/macro/` |
| 2024-09 | Add Crypto agent | `agents/crypto/` |
| 2024-09 | Add Forex agent | `agents/forex/` |
| 2024-09 | Add council debate mechanism | `agents/council/debate.py` |
| 2024-09 | Add council voting system | `agents/council/voting.py` |
| 2024-08 | Add FastAPI application | `api/app.py` |
| 2024-08 | Add market data API route | `api/routes/market.py` |
| 2024-08 | Add trading API route | `api/routes/trading.py` |
| 2024-08 | Add agents API route | `api/routes/agents.py` |
| 2024-08 | Add WebSocket route | `api/routes/ws.py` |
| 2024-08 | Add memory system | `memory/` |
| 2024-07 | Monorepo consolidation begins | — |
| 2024-07 | Merge AutoTrader core | — |
| 2024-07 | Merge HermesQuantOS risk framework | — |
| 2024-07 | Merge TradingAgents debate system | — |

### 2024-Q2 (v0.1.0)

| Date | Change | Module |
|---|---|---|
| 2024-06 | Project initialization | — |
| 2024-06 | Create quant_nanggroe package | — |
| 2024-06 | Set up pyproject.toml | — |
| 2024-06 | Set up pytest configuration | — |
| 2024-06 | Set up ruff and mypy configuration | — |
| 2024-06 | Initial agent framework | — |
| 2024-06 | Initial exchange interface | — |

---

## Migration Impact Summary

### Repository Merge Timeline

| Repository | Version Merged | Strategy | Modules Added | Tests Added |
|---|---|---|---|---|
| AutoTrader | v1.0.0 | FULL | 15+ | 200+ |
| HermesQuantOS | v2.0.0 | FULL | 12+ | 180+ |
| TradingAgents | v1.0.0 | FULL | 8+ | 120+ |
| Vibe-Trading | v3.0.0 | FULL | 10+ | 300+ |
| AI-Trader | v2.0.0 | FULL | 8+ | 100+ |
| AutoHedge | v3.0.0 | PARTIAL | 5+ | 60+ |
| QuantDinger | v3.0.0 | PARTIAL | 4+ | 50+ |
| SolSniperX | v3.0.0 | FULL | 6+ | 80+ |
| FinceptTerminal | v4.0.0 | PARTIAL | 3+ | 30+ |
| OpenAlice | v4.0.0 | PARTIAL | 2+ | 20+ |
| Misi-Screener | v4.0.0 | PARTIAL | 2+ | 15+ |
| PromptForgeAI | v4.0.0 | PARTIAL | 2+ | 10+ |

### Test Suite Growth

| Version | Tests | Coverage | Key Additions |
|---|---|---|---|
| v0.1.0 | 50 | ~40% | Basic agent and config tests |
| v1.0.0 | 800+ | ~70% | Graph, agents, API, council |
| v2.0.0 | 1,200+ | ~75% | Risk engine, security, Pydantic models |
| v3.0.0 | 2,100+ | ~80% | Factors, exchanges, backtest |
| v4.0.0 | 2,504+ | ~85% | v2 graph, multi-path, position sizing |

### Module Count Growth

| Version | Modules | Key Additions |
|---|---|---|
| v0.1.0 | 15 | Basic package structure |
| v1.0.0 | 80 | Agents, graph, council, API, memory |
| v2.0.0 | 120 | Risk engine, security, config |
| v3.0.0 | 185 | Factors, exchanges, backtest, Solana |
| v4.0.0 | 214+ | v2 graph nodes, SOR, human checkpoint |

---

## Breaking Changes

### v4.0.0 Breaking Changes

| Change | Impact | Migration |
|---|---|---|
| `AgentState` adds new fields | Code creating states manually must include new fields | Use `create_initial_state()` factory |
| v2 graph has different node names | Code referencing v1 node names must update | New nodes: asset_router, position_sizer, portfolio_validation, smart_execution, human_checkpoint, trade_rejected |
| `AssetClass` enum added | New enum for asset classification | Import from `agents.state` |
| Human checkpoint may block trades | Trades that previously auto-executed may now require approval | Set `human_approval_status="APPROVED"` in initial state |
| Portfolio validation may fail | Portfolios that previously passed may fail validation | Review concentration/correlation limits |

### v3.0.0 Breaking Changes

| Change | Impact | Migration |
|---|---|---|
| FactorRegistry singleton | Factor modules must use registry API | Import from `engine.factors.registry` |
| ExchangeFactory replaces direct CCXT | Code creating CCXT exchanges directly must use factory | Use `ExchangeFactory.create()` |
| Constitutional limits hardcoded | Risk limits can no longer be configured | Accept hardcoded limits |

### v2.0.0 Breaking Changes

| Change | Impact | Migration |
|---|---|---|
| Pydantic v2 models | All model usage must use v2 API | Update from v1 patterns |
| TypedDict for AgentState | State is no longer a Pydantic model | Use dict-style access |
| Constitutional limits | Risk configuration no longer accepted | Use hardcoded constants |

### v1.0.0 Breaking Changes

| Change | Impact | Migration |
|---|---|---|
| Monorepo structure | Import paths changed | Update all imports to `quant_nanggroe.*` |
| LangGraph orchestration | Custom execution loops replaced | Use TradingGraph.run() |
| AgentFactory | Agents created via factory | Use factory instead of direct instantiation |

---

## Deprecation Notices

| Feature | Deprecated In | Removed In | Replacement |
|---|---|---|---|
| v1 graph (graph.py) | v4.0.0 | v5.0.0 | TradingGraphV2 |
| Direct CCXT instantiation | v3.0.0 | v4.1.0 | ExchangeFactory |
| Custom risk configuration | v2.0.0 | v3.0.0 | Constitutional limits |
| Pydantic v1 models | v2.0.0 | v3.0.0 | Pydantic v2 |

---

© 2025-2026 Quant Nanggroe AI | Changelog v4.0.0
