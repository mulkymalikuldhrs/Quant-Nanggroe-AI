# Quant Nanggroe AI — Changelog

**All notable changes to Quant Nanggroe AI are documented in this file.**

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.3.0] - 2026-03-04 — Agent-3 Massive Upgrade

### Added

#### Agents
- **feat**: Full 9-agent architecture with specialized domain agents (Researcher, Strategist, Risk, Trader, Portfolio, Execution, Macro, Crypto, Forex)
- **feat**: Council debate system with Bull/Bear and Risk (Conservative/Neutral/Aggressive) debates
- **feat**: Council voting with weighted decisions based on historical agent accuracy
- **feat**: Emergency exit node for kill switch activation with automatic position closure
- **feat**: Confidence-based routing to council debate when confidence < 0.65
- **feat**: Agent factory with deep/quick LLM model selection per agent role
- **feat**: Per-agent tool definitions integrated with MCP protocol
- **feat**: Per-agent prompt templates with domain-specific instructions

#### Engine — Factors
- **feat**: `AlphaFactor` base class with `FactorMeta` documentation and `compute(df)` interface
- **feat**: 50+ WorldQuant Alpha101 factor implementations from Kakushadze (2015)
- **feat**: 191 GTJA191 Chinese A-share alpha factor implementations
- **feat**: Barra multi-factor risk model implementation
- **feat**: Technical factor implementations (RSI, MACD, Bollinger, ATR, ADX, etc.)
- **feat**: Fundamental factor implementations (P/E, EPS, Revenue Growth, etc.)
- **feat**: Factor pipeline for composable factor computation
- **feat**: Factor registry for factor discovery and instantiation
- **feat**: Vectorized helper functions (rank, delay, delta, ts_corr, ts_cov, ts_mean, ts_std, ts_sum, ts_min, ts_max, ts_argmax, ts_argmin, ts_rank, decay_linear, safe_div, scale, signed_power, vwap)

#### Engine — Risk
- **feat**: Constitutional risk system with 9 hardcoded, non-overridable checkpoints
- **feat**: Risk assessment with 4 verdict types (APPROVED, VETOED, CONDITIONAL, KILL_SWITCH)
- **feat**: VaR computation (Parametric, Historical, Monte Carlo)
- **feat**: CVaR (Conditional Value at Risk) computation
- **feat**: Kelly criterion for optimal position sizing
- **feat**: Risk parity portfolio construction
- **feat**: Real-time drawdown monitoring with alerting
- **feat**: Kill switch with daily/weekly PnL thresholds
- **feat**: Pairwise correlation monitoring between positions
- **feat**: Emotional lockout mechanism to prevent revenge trading
- **feat**: Position sizing with constitutional limit enforcement

#### Engine — Backtest
- **feat**: Backtest engine with configurable commission, slippage, and market type
- **feat**: Execution reality simulation (dynamic spread, slippage, partial fills, latency)
- **feat**: Comprehensive performance metrics (Sharpe, Sortino, Calmar, max drawdown, win rate, profit factor)
- **feat**: Monte Carlo resampling for confidence intervals
- **feat**: Walk-forward optimization for robustness validation
- **feat**: Benchmark comparison against buy-and-hold and market indices
- **feat**: HTML/JSON backtest report generation
- **feat**: Simulated portfolio with position tracking

#### Engine — Execution
- **feat**: Execution manager with order lifecycle management
- **feat**: Fill processing with partial fill handling
- **feat**: Guard pipeline (cooldown, whitelist, max position)
- **feat**: Paper broker for simulation trading
- **feat**: Order creation, modification, and cancellation

#### Engine — ML Models
- **feat**: Base model interface for ML integration
- **feat**: Feature store for feature engineering and storage
- **feat**: Signal generator for ML-based signal generation
- **feat**: Ensemble model for multi-model predictions

#### Exchange Layer
- **feat**: `ExchangeInterface` abstract base class with full API (connect, trade, market data, WebSocket)
- **feat**: CCXT broker implementation for 100+ crypto exchanges
- **feat**: Alpaca broker implementation for US equities with paper/live toggle
- **feat**: Paper broker with fill simulation
- **feat**: Polymarket broker for prediction market integration
- **feat**: Solana ecosystem integration (Jupiter DEX, RugCheck, Mempool, Wallet, Broker)
- **feat**: Exchange factory for broker instantiation
- **feat**: Exchange manager for connection lifecycle
- **feat**: Guard pipeline for pre-trade validation
- **feat**: Typed error hierarchy (ExchangeError, ConnectionError, OrderError, RateLimitError, AuthenticationError, InsufficientFundsError, MarketDataError)
- **feat**: Exchange configuration with `ExchangeConfig` Pydantic model
- **feat**: Exchange state tracking with `ExchangeState` enum

#### Memory Layer
- **feat**: Trade journal with entry/exit/reflection recording and PnL calculation
- **feat**: Knowledge graph for entity-relationship storage
- **feat**: Paging system for Letta-style context window management
- **feat**: Session manager for cross-session state persistence

#### MCP Protocol
- **feat**: Full MCP protocol implementation with JSON-RPC 2.0
- **feat**: MCP server with tool registration and execution
- **feat**: MCP client for tool discovery and invocation
- **feat**: Tool definition schemas with input/output JSON Schemas
- **feat**: SSE (Server-Sent Events) streaming for long-running tools
- **feat**: Health check protocol
- **feat**: Standard MCP error codes

#### Security
- **feat**: KeyVault for environment-only secrets management with masking and caching
- **feat**: Authentication module with API key and RBAC support
- **feat**: Audit trail for comprehensive event logging
- **feat**: Credential inference for detecting weak/misconfigured credentials

#### API
- **feat**: FastAPI REST server with OpenAPI docs
- **feat**: WebSocket endpoint for real-time trading updates
- **feat**: Trade execution endpoint (`POST /api/v1/trade`)
- **feat**: Portfolio status endpoint (`GET /api/v1/portfolio`)
- **feat**: Agent listing endpoint (`GET /api/v1/agents`)
- **feat**: Backtest execution endpoint (`POST /api/v1/backtest`)
- **feat**: Risk assessment endpoint (`GET /api/v1/risk/{symbol}`)
- **feat**: Health check endpoint (`GET /api/v1/health`)
- **feat**: Pydantic request/response models for all endpoints
- **feat**: CORS middleware for dashboard integration

#### Data Layer
- **feat**: SQLAlchemy 2.0 ORM models (User, Trade, Position, PortfolioSnapshot, AgentLog, RiskEvent, Strategy, BacktestResult)
- **feat**: Pydantic type system (OHLCV, Ticker, OrderBook, TimeFrame, Order, Position, Portfolio, Signal, Decision)
- **feat**: Multi-provider data access with TTL caching
- **feat**: Database indexes for common query patterns

#### Configuration
- **feat**: Pydantic Settings with `QNAI_` environment variable prefix
- **feat**: Field validators for log levels and risk limit ranges
- **feat**: `.env` file support for local development
- **feat**: Cached settings singleton via `@lru_cache`

#### Documentation
- **feat**: Complete architecture documentation (9 documents)
- **feat**: Research benchmark summary (113 projects, 10 categories)
- **feat**: Architecture Decision Records (10 ADRs)

### Changed
- **refactor**: Migrated from individual repo architecture to monorepo structure
- **refactor**: Replaced simple pass/fail risk checks with 9-checkpoint constitutional gates
- **refactor**: Replaced direct broker calls with `ExchangeInterface` abstraction
- **refactor**: Replaced dict-based agent state with `AgentState` TypedDict
- **refactor**: Replaced function-based factors with `AlphaFactor` class hierarchy
- **refactor**: Replaced simple majority voting with weighted council voting
- **refactor**: Upgraded to Pydantic v2 with `model_config` pattern
- **refactor**: Upgraded to SQLAlchemy 2.0 with `mapped_column` style

### Fixed
- **fix**: Alpha factor lookahead bias — all time-series operations use only past data
- **fix**: Division by zero in factor computation — `safe_div` utility handles zero denominators
- **fix**: Agent crash propagation — all agent nodes wrapped in try/except with safe defaults
- **fix**: Risk assessment bypass — constitutional limits are hardcoded and non-overridable
- **fix**: Kill switch race condition — graph routing ensures atomic emergency exit
- **fix**: Portfolio state inconsistency — ORM models enforce data integrity

---

## [0.2.0] - 2025-12-15 — Production-Ready Overhaul

### Added
- **feat**: LangGraph StateGraph for trading pipeline orchestration
- **feat**: TradingGraph class with 7 nodes and conditional edges
- **feat**: 5 specialized agents (Researcher, Strategist, Risk, Trader, Execution)
- **feat**: Constitutional risk limits as hardcoded constants
- **feat**: FastAPI REST API with 5 endpoints
- **feat**: WebSocket endpoint for real-time updates
- **feat**: SQLAlchemy 2.0 ORM models for 8 tables
- **feat**: Pydantic Settings with environment variable binding
- **feat**: Click CLI for command-line operations
- **feat**: CCXT broker integration for crypto exchanges
- **feat**: Paper broker for simulation trading
- **feat**: Trade journal with entry/exit tracking
- **feat**: KeyVault for secure secrets management
- **feat**: Structured logging with `structlog`

### Changed
- **refactor**: Migrated from JavaScript/TypeScript to Python
- **refactor**: Replaced custom agent loop with LangGraph StateGraph
- **refactor**: Replaced in-memory state with SQLAlchemy ORM
- **refactor**: Replaced simple risk check with constitutional 9-gate system
- **refactor**: Upgraded from Express.js to FastAPI

### Fixed
- **fix**: Agent state loss between pipeline stages
- **fix**: Risk limits could be overridden by configuration
- **fix**: No audit trail for agent decisions
- **fix**: Exchange errors not properly typed

---

## [0.1.0] - 2025-10-01 — Initial Foundation

### Added
- **feat**: Initial project structure with Python package
- **feat**: Basic agent system with 4 agents (Researcher, Strategist, Risk, Trader)
- **feat**: Simple trading pipeline: analysis → signal → risk → execution
- **feat**: Basic risk management with configurable limits
- **feat**: CCXT exchange integration
- **feat**: SQLite database for trade records
- **feat**: Simple REST API with 3 endpoints
- **feat**: Basic backtesting with event-driven engine
- **feat**: Configuration via YAML files
- **feat**: Logging with Python stdlib

### Known Issues
- Risk limits were configurable and could be overridden
- No council debate or voting mechanism
- Single LLM model for all agents (no deep/quick split)
- No WebSocket support
- No MCP protocol integration
- No paper/live toggle
- No kill switch or emergency exit
- No emotional lockout mechanism
- No factor library (Alpha101, GTJA191, etc.)
- No VaR/CVaR computation
- No Monte Carlo or walk-forward backtesting
- No exchange interface abstraction
- No KeyVault for secrets
- No audit trail
- No macro, crypto, or forex specialized agents
- No portfolio optimization agent
- No Solana/DEX integration
- No prediction market integration
- No structured logging (only Python stdlib)
- No Click CLI

---

## Detailed Version Comparison

### Version 0.1.0 → 0.2.0 Migration Summary

The v0.2.0 release was a complete rewrite from JavaScript/TypeScript to Python, driven by the need for better ML ecosystem support and more robust type safety.

**Breaking Changes from v0.1.0 to v0.2.0:**

| Area | v0.1.0 | v0.2.0 | Migration Impact |
|------|--------|--------|-----------------|
| Language | TypeScript/JavaScript | Python 3.11+ | Complete rewrite required |
| Agent Framework | Custom loop | LangGraph StateGraph | New orchestration model |
| Risk Management | Configurable limits | Constitutional (hardcoded) | Limits can no longer be changed at runtime |
| API Server | Express.js | FastAPI | New API structure and endpoints |
| Database | MongoDB (Mongoose) | SQLite/PostgreSQL (SQLAlchemy) | Data migration required |
| State Management | In-memory dicts | AgentState TypedDict | New state model |
| Configuration | YAML files | Pydantic Settings + env vars | Config migration required |
| Logging | Winston | structlog | New log format |

**New Capabilities in v0.2.0:**
- LangGraph StateGraph with 7 nodes and conditional edges for flexible pipeline routing
- Constitutional risk limits as hardcoded, non-overridable constants for capital protection
- FastAPI REST API with automatic OpenAPI documentation and WebSocket support
- SQLAlchemy 2.0 ORM models with proper indexes, relationships, and timestamp tracking
- Pydantic Settings with environment variable binding and validation
- CCXT broker integration supporting 100+ crypto exchanges
- Paper broker for zero-risk simulation trading
- Trade journal with entry/exit tracking and PnL calculation
- KeyVault for environment-only secrets management with masking
- Structured logging with JSON output via structlog

### Version 0.2.0 → 0.3.0 Migration Summary

The v0.3.0 release (Agent-3 Massive Upgrade) expanded the system from 5 agents to 9, added the council debate system, implemented the full factor library, and integrated MCP protocol.

**Breaking Changes from v0.2.0 to v0.3.0:**

| Area | v0.2.0 | v0.3.0 | Migration Impact |
|------|--------|--------|-----------------|
| Agent Count | 5 agents | 9 agents | New agent modules to configure |
| Risk Assessment | Simple pass/fail | 9-checkpoint constitutional gate | New risk assessment data model |
| Council System | None | Debate + Voting | New debate and voting nodes in graph |
| Factor Library | None | Alpha101 + GTJA191 + Barra + Technical + Fundamental | New factor computation pipeline |
| Exchange Layer | CCXT + Alpaca + Paper | + Polymarket + Solana ecosystem | New exchange adapters |
| MCP Protocol | None | Full JSON-RPC 2.0 implementation | New tool integration layer |
| LLM Models | Single model | Dual model (deep/quick) | New configuration parameters |
| Memory | Journal only | Journal + Knowledge Graph + Paging + Session | New memory subsystems |
| Security | KeyVault + Auth | + Credential Inference | Enhanced security checks |

**New Capabilities in v0.3.0:**

The Agent-3 upgrade represents the largest single release in the project's history, adding over 15,000 lines of code across 100+ new files. Key additions include:

1. **4 New Specialized Agents**: Macro (macroeconomic analysis, regime detection), Crypto (on-chain data, whale tracking, sentiment analysis), Forex (FX rates, carry trade analysis, central bank policy monitoring), and Portfolio (risk parity allocation, rebalancing, position optimization)

2. **Council Debate System**: Bull/Bear debate for trade direction analysis, Risk debate with Conservative/Neutral/Aggressive perspectives, and weighted voting by all 9 agents based on historical accuracy metrics

3. **Comprehensive Factor Library**: 50+ Alpha101 factors from Kakushadze (2015) with AST-pure computation and lookahead banning, 191 GTJA191 Chinese A-share alpha factors, Barra multi-factor risk model for institutional-grade risk decomposition, technical indicators (RSI, MACD, Bollinger Bands, ATR, ADX), and fundamental factors (P/E, EPS, Revenue Growth)

4. **MCP Protocol Integration**: Full Model Context Protocol implementation with JSON-RPC 2.0 messaging, tool discovery and registration, SSE streaming for long-running tools, and standardized error codes

5. **Enhanced Exchange Layer**: Polymarket broker for prediction market signal integration, Solana ecosystem support (Jupiter DEX aggregator, RugCheck token safety, mempool monitoring, wallet management), and comprehensive error hierarchy with typed exceptions

6. **Advanced Risk System**: 9 constitutional checkpoints (per-trade risk, daily loss, weekly loss, risk:reward, position size, correlation, leverage, drawdown, trade frequency), VaR/CVaR computation with parametric/historical/Monte Carlo methods, Kelly criterion for optimal position sizing, emotional lockout to prevent revenge trading, and real-time drawdown monitoring with automatic kill switch

---

## Statistics

### Code Metrics by Version

| Metric | v0.1.0 | v0.2.0 | v0.3.0 |
|--------|--------|--------|--------|
| Python Files | 12 | 45 | 110+ |
| Lines of Code | ~2,000 | ~8,000 | ~25,000 |
| Agent Count | 4 | 5 | 9 |
| Factor Count | 0 | 0 | 250+ |
| Risk Checkpoints | 1 (pass/fail) | 4 | 9 |
| Exchange Adapters | 1 (CCXT) | 3 | 6+ |
| API Endpoints | 3 | 5 | 7 |
| ORM Models | 3 | 5 | 8 |
| Dependencies | 8 | 18 | 28 |

### Feature Completeness

| Feature | v0.1.0 | v0.2.0 | v0.3.0 |
|---------|--------|--------|--------|
| Multi-Agent Trading | ❌ | ✅ (5 agents) | ✅ (9 agents) |
| Constitutional Risk | ❌ | ✅ (4 checkpoints) | ✅ (9 checkpoints) |
| Council Debate | ❌ | ❌ | ✅ |
| Factor Library | ❌ | ❌ | ✅ (250+ factors) |
| MCP Protocol | ❌ | ❌ | ✅ |
| Paper/Live Toggle | ❌ | ✅ | ✅ |
| Kill Switch | ❌ | ✅ | ✅ |
| WebSocket | ❌ | ✅ | ✅ |
| KeyVault | ❌ | ✅ | ✅ |
| Audit Trail | ❌ | ❌ | ✅ |
| Knowledge Graph | ❌ | ❌ | ✅ |
| Solana/DEX | ❌ | ❌ | ✅ |
| Prediction Markets | ❌ | ❌ | ✅ |

---

## Version Summary

| Version | Date | Codename | Summary |
|---------|------|----------|---------|
| 0.1.0 | 2025-10-01 | Foundation | Initial project with basic agents and trading pipeline |
| 0.2.0 | 2025-12-15 | Production Overhaul | LangGraph orchestration, constitutional risk, FastAPI, full ORM |
| 0.3.0 | 2026-03-04 | Agent-3 Upgrade | 9 agents, council debate, factor library, MCP protocol, full exchange layer |

---

*© 2025-2026 Quant Nanggroe AI | Changelog v0.2.0*
