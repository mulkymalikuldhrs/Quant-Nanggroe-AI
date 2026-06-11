# Quant Nanggroe AI — Changelog

**Version 4.0.0 | Complete Version History**

> Complete version history from v0.1.0 to v4.0.0 with detailed changes for each release.

---

## [4.0.0] — 2025-Q3 (Current)

### Added
- **11-Agent Council Architecture**: Full LangGraph StateGraph with 9 nodes and conditional edges
  - Researcher, Macro, Crypto, Forex, Strategist, Risk, Portfolio, Trader, Execution agents
  - Council Debate node with Bull/Bear + Conservative/Neutral/Aggressive debates
  - Emergency Exit node with automatic position closure on kill switch
- **469 Factor Models** across 7 zoos (Alpha101, GTJA191, Barra, Qlib158, Technical, Fundamental, Academic)
  - `FactorRegistry` with dual-pattern support (class-based + function-based)
  - `FactorHandle` unified wrapper for all factor patterns
  - AST-based metadata extraction via `load_alpha_meta_from_module()`
  - Output validation: rejects inf values, >95% NaN factors
- **9-Checkpoint Constitutional Risk Gate** (`RiskCheckGate`)
  - Checkpoint 1: Risk per trade ≤ 0.5%
  - Checkpoint 2: Daily loss < 1.0%
  - Checkpoint 3: Weekly loss < 3.0%
  - Checkpoint 4: Risk:Reward ratio ≥ 1:2
  - Checkpoint 5: Stop loss exists and valid
  - Checkpoint 6: Valid entry price > 0
  - Checkpoint 7: Valid direction (BUY/SELL/LONG/SHORT)
  - Checkpoint 8: Not overtrading (≤ 5 trades/day)
  - Checkpoint 9: Correlated positions ≤ 3
- **Constitutional Risk Limits** (12 hardcoded constants in `engine/risk/constants.py`)
  - `MAX_RISK_PER_TRADE = 0.005`, `MAX_DAILY_LOSS = 0.01`, `MAX_WEEKLY_LOSS = 0.03`
  - `MIN_RISK_REWARD = 2.0`, `MAX_CORRELATED_POSITIONS = 3`, `MAX_POSITION_SIZE_PCT = 0.10`
  - `MAX_LEVERAGE = 3.0`, `MAX_DRAWDOWN_PCT = 0.15`, `MAX_DAILY_TRADES = 5`
  - `CONFIDENCE_THRESHOLD = 0.65`, `KILL_SWITCH_DAILY_PNL = -0.02`, `KILL_SWITCH_WEEKLY_PNL = -0.05`
- **ExchangeFactory** with 8 CCXT exchanges (Binance, OKX, Bybit, Bitget, Kraken, KuCoin, Gate, Coinbase)
  - Market type routing (Spot, Futures, Perps) with capability validation
  - Passphrase validation for OKX/KuCoin/Bitget/Coinbase
  - `PaperExchangeBroker` for simulated trading
- **FastAPI Backend** with 6 route groups
  - `/api/market` — Market data endpoints
  - `/api/trading` — Order management + execution
  - `/api/agents` — Agent orchestration + monitoring
  - `/api/backtest` — Strategy validation
  - `/api/portfolio` — Portfolio management
  - `/api/ws` — WebSocket real-time streaming
- **AgentState TypedDict** — Complete shared state schema for LangGraph graph
- **BaseAgent ABC** — Abstract base class with multi-provider LLM support (OpenAI, Anthropic, Google, Ollama, OpenRouter)
- **AgentRegistry + AgentFactory** — Dynamic agent creation with LLM configuration
- **CouncilDebate** — Structured debate mechanism (Bull/Bear + Risk 3-way)
- **CouncilVoting** — Weighted voting with historical accuracy weights
- **RiskManager** — Top-level risk orchestrator with 5 position sizing methods
- **KillSwitch** — Automatic system halt on constitutional limit breach
- **DrawdownMonitor** — Maximum drawdown tracking
- **KellyCriterion** — Full/Half/Quarter Kelly position sizing
- **VaRCalculator** — Parametric, Historical, and Monte Carlo VaR
- **CorrelationMonitor** — Pairwise correlation checking
- **Stress Testing** — 6 scenarios (2008 Crisis, COVID, Rate Hike, Tech Crash, Recovery, Bull Market)
- **ATR Position Sizing** — 2×ATR stop distance with constitutional cap
- **Three-Layer Memory System** — Episodic, Pattern, Knowledge Graph
- **Next.js Dashboard** — Web terminal with draggable, resizable window panels

### Changed
- **BREAKING**: `AgentState` is now a `TypedDict` (not Pydantic `BaseModel`) for LangGraph compatibility
- **BREAKING**: All constitutional limits hardcoded — no longer configurable via environment variables
- **BREAKING**: Pydantic v2 required — `@validator` → `@field_validator`, `class Config` → `model_config`
- **BREAKING**: Python 3.12+ required — no support for 3.9-3.11
- Upgraded CCXT from 3.x to 4.4+
- Upgraded LangChain from 0.1.x to 0.3+
- Upgraded SQLAlchemy from 1.4.x to 2.0+
- Upgraded FastAPI from 0.100.x to 0.115+

### Security
- Removed `GEMINI_API_KEY` from Vite client bundle (was in `define` config)
- API keys loaded only from environment variables via Pydantic Settings
- Structlog processors redact `*_api_key`, `*_secret`, `*_password`, `*_token` fields
- `RiskAssessment.override_possible` always `False`

---

## [3.0.0] — 2025-Q1

### Added
- **FactorRegistry** — Centralized catalog of all alpha factors
  - `FactorHandle` wrapper for both class-based and function-based factors
  - Discovery API: `list(zoo=, theme=, universe=)`
  - Health check: `health()` returns loaded/failed counts
  - Export: `export_manifest()` for external consumers
- **ExchangeFactory** with initial 5 CCXT exchanges (Binance, OKX, Bybit, Kraken, Gate)
- **RiskManager** with constitutional limits enforcement
- **RiskCheckGate** with 9-checkpoint validation
- **KillSwitch** with auto-activation on limit breach
- **DrawdownMonitor** for maximum drawdown tracking
- **KellyCriterion** position sizing (Full/Half/Quarter Kelly)
- **VaRCalculator** (Parametric + Historical)
- **CorrelationMonitor** for pairwise correlation checks
- **BaseAgent** abstract class with tool binding
- **AgentRegistry** for dynamic agent registration
- **AgentFactory** for LLM-configured agent creation
- **FastAPI application** with initial route groups (Market, Trading, Agents)
- **Docker Compose** configuration (API + PostgreSQL + Redis)

### Changed
- Migrated from Flask to FastAPI for async support + auto-docs
- Consolidated exchange adapters into `CCXTBroker`
- Replaced TA-Lib C dependency with numpy-native implementations

### Removed
- Flask API server (replaced by FastAPI)
- Direct Binance API adapter (replaced by CCXT)
- InfluxDB storage adapter (replaced by TimescaleDB)

---

## [2.0.0] — 2024-Q4

### Added
- **TradingGraph** — LangGraph StateGraph with conditional routing
  - `market_analysis` → `signal_generation` → `risk_assessment` → `portfolio_optimization` → `execution_decision` → `order_execution` → `reflection`
  - Conditional edges: risk VETOED → halt, low confidence → council_debate, kill switch → emergency_exit
- **AgentState** schema with all Pydantic models
  - `MarketData`, `Signal`, `Decision`, `RiskCheckpoint`, `RiskAssessment`
  - `PortfolioState`, `PositionInfo`, `AgentOutput`
  - `DebateState`, `RiskDebateState`, `VoteResult`, `CouncilResult`
- **Enumerations**: `TradeAction`, `SignalDirection`, `RiskVerdict`, `MarketRegime`, `AgentRole`
- **create_llm()** multi-provider factory (OpenAI, Anthropic, Google, Ollama, OpenRouter)
- **CouncilDebate** — Bull/Bear researcher debate + Conservative/Neutral/Aggressive risk debate
- **CouncilVoting** — Weighted voting with consensus measurement
- **PaperExchangeBroker** — Simulated trading with commission + slippage
- **Redis Pub/Sub** channels for execution bus + agent reasoning bus
- **PostgreSQL audit_events** table for event sourcing

### Changed
- Migrated agent coordination from CrewAI to LangGraph
- Upgraded Pydantic from v1 to v2
- Replaced single-agent decision with 11-agent council

### Removed
- CrewAI agent orchestration (replaced by LangGraph)
- AutoGen conversation framework (replaced by LangGraph)

---

## [1.5.0] — 2024-Q3

### Added
- **Alpha101 factors** — 101 formulaic alphas from WorldQuant research paper
- **GTJA191 factors** — 191 alpha factors from GuoTaiJunAn Securities
- **Technical indicators** — 25+ class-based technical factors (RSI, MACD, Bollinger, ATR, etc.)
- **Fundamental factors** — 20+ class-based fundamental factors (EP, BP, ROE, ROA, etc.)
- **FactorMeta** — Metadata schema for factor documentation
- **AlphaFactor** base class with `validate_lookahead()` method
- **BacktestEngine** with execution reality simulation (slippage, spread, latency)
- **Walk-forward validation** with expanding window
- **AutoSwitch** provider failover for market data
- **Docker containerization** with multi-stage build

### Changed
- Replaced hardcoded indicator calculations with `FactorRegistry` pattern
- Upgraded numpy from 1.24 to 2.1
- Upgraded pandas from 1.5 to 2.2

### Fixed
- Lookahead bias in rolling factor calculations
- NaN propagation in factor output for short history windows

---

## [1.0.0] — 2024-Q2

### Added
- **Initial release** of Quant Nanggroe AI
- **TradingGraph v1** — Simple linear pipeline: research → analyze → strategize → risk → trade
- **Researcher agent** — Market data harvesting + sentiment analysis
- **Strategist agent** — Signal generation with pressure normalization
- **Risk Manager** — Basic risk checks (max loss, position size)
- **Trader agent** — Order execution via ccxt
- **Market data tools** — OHLCV, current price, order book
- **Sentiment analysis tool** — News + social media sentiment scoring
- **Technical analysis tool** — RSI, MACD, Bollinger Bands, ATR
- **Execution tool** — Order submission via ccxt Binance adapter
- **CCXT integration** — Binance spot trading
- **PostgreSQL database** — Agent state + trade history storage
- **Redis cache** — Market data + session caching
- **Python 3.9+ compatibility**

### Known Issues
- No council debate mechanism
- Risk checks are ad-hoc (no 9-checkpoint gate)
- No kill switch
- Single-agent decision (no debate + voting)
- Limited to Binance crypto spot trading

---

## [0.5.0] — 2024-Q1

### Added
- **HermesQuantOS integration** — Parent project components
  - `RiskOfficerTool` — Basic risk validation
  - `BacktestEngine` — Simple backtesting with slippage simulation
  - `DrawdownMonitor` — Maximum drawdown tracking
- **Pressure normalization engine** — 4-sensor weighted aggregation
  - QuantScanner (25%), SMCAgent (30%), NewsSentinel (20%), FlowAgent (25%)
- **Decision synthesis engine** — 7-rule deterministic decision table
- **Market state engine** — Regime detection (RISK_ON, RISK_OFF, TRENDING, RANGE, CRISIS)

### Changed
- Consolidated from HermesQuantOS standalone to Quant Nanggroe AI module

---

## [0.3.0] — 2023-Q4

### Added
- **Multi-debate framework** from TradingAgents
  - Bull vs. Bear researcher debate
  - Conservative vs. Neutral vs. Aggressive risk debate
  - Judge decision rendering
- **AI hedge fund patterns** from ai-hedge-fund
  - Stress testing (6 scenarios)
  - Optimal-F position sizing
  - VaR-based position sizing
- **Vibe-Trading factors** — Sentiment + vibe-based factor models
  - `__alpha_meta__` + `compute(panel)` function-based pattern

### Changed
- Adopted TradingAgents' debate architecture for low-confidence decisions

---

## [0.2.0] — 2023-Q3

### Added
- **FinceptTerminal** — Python CLI/TUI interface (Rich + Textual)
- **Market data pipeline** — Binance, Polygon, AlphaVantage, Finnhub providers
- **AutoSwitch** failover for data providers
- **Execution brokers** — Initial ccxt wrapper for Binance

### Changed
- Moved from hardcoded data sources to configurable pipeline

### Deprecated
- Direct Binance API calls (replaced by ccxt wrapper)

---

## [0.1.0] — 2023-Q2

### Added
- **Initial prototype** of the trading intelligence system
- Basic LLM integration (OpenAI GPT-4) for market analysis
- Simple buy/sell signal generation
- Binance spot trading via direct API calls
- PostgreSQL for trade history storage
- Basic risk check (max position size, daily loss limit)

### Known Issues
- No multi-agent architecture
- No backtesting engine
- No kill switch
- No audit trail
- Single LLM provider (OpenAI only)
- No frontend dashboard

---

## Release Naming Convention

- **Major (X.0.0)**: Breaking architecture changes (new agent council, new risk engine)
- **Minor (0.X.0)**: New features (new agents, new factors, new exchanges)
- **Patch (0.0.X)**: Bug fixes, security patches, documentation updates

---

*© 2025-2026 Quant Nanggroe AI | Changelog v4.0.0*
