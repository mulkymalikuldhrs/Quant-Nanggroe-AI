# Cluster 1 Repo Implementations Audit

**Date:** 2026-03-04  
**Auditor:** Automated Deep Audit  
**Scope:** 15 critical repos in `/home/z/my-project/quant-nanggroe-ai/repos/`

---

## Executive Summary

**TOP 3 MOST VALUABLE REPOS (must-preserve for monorepo):**

| Rank | Repo | Value | Unique Code |
|------|------|-------|-------------|
| 1 | **Vibe-Trading** | ⭐⭐⭐⭐⭐ | 456 alpha factors, 9 backtest engines, 75 skills, 28 tools, ReAct agent loop |
| 2 | **AI-Trader** | ⭐⭐⭐⭐⭐ | Production FastAPI trading server, 30+ DB tables, signal/copy-trade/experiment system |
| 3 | **HermesQuantOS** | ⭐⭐⭐⭐ | 21-agent layered architecture, decision synthesis engine, hardcoded risk framework |

**REPOS WITH UNIQUE NICHE VALUE:**

| Repo | Unique Value |
|------|-------------|
| **SolSniperX** | Real Solana on-chain execution via Jupiter Aggregator + JITO tips |
| **Kronos** | Novel PyTorch tokenizer-based financial time-series model (BSQuantizer) |
| **OpenAlice** | Best TypeScript architecture reference: UTA protocol, IBKR package, domain-driven design |
| **TradingAgents** | LangGraph-based multi-agent trading graph with reflection/propagation |

**REPOS WITH LOWER CONSOLIDATION PRIORITY:**

| Repo | Reason |
|------|--------|
| **ai-hedge-fund** | Standard agent structure, no unique algorithms |
| **Misi-Screener** | Query orchestrator pattern, simple intent mapping |
| **skales** | Multi-platform chat bot (Discord/Telegram/WhatsApp), minimal trading logic |
| **bloomberg-terminal** | Next.js UI shell, no backend trading logic |
| **Pentaract** | Rust web server boilerplate, no trading-specific code |
| **QuantDinger** | Python backend API + Vue frontend, standard CRUD |
| **ai-financial-agent** | Next.js + Drizzle ORM frontend, no core trading logic |
| **AutoTrader** | Established Python trading library (pip-installable), but generic |

---

## Detailed Repo Audits

---

### 1. AI-Trader — Production FastAPI Trading System

**Purpose:** Multi-agent paper-trading platform with signals, copy-trading, experiments, challenges, and team missions.

**Tech Stack:** Python, FastAPI, SQLite/PostgreSQL (dual-backend), Redis cache, React frontend (Vite/TypeScript)

**Key Modules & Implementations:**

| Module | File(s) | Description |
|--------|---------|-------------|
| **Server Entry** | `service/server/main.py` | FastAPI app with startup event, background tasks, cache init |
| **Database** | `service/server/database.py` | Dual-backend (SQLite WAL + PostgreSQL psycopg) with automatic SQL adaptation, `DatabaseCursor`/`DatabaseConnection` wrapper classes, retryable error detection |
| **Trading Routes** | `service/server/routes_trading.py` | `/api/profit/history`, `/api/leaderboard/position-pnl`, `/api/trending`, `/api/price`, `/api/positions`, `/api/agents/{id}/positions`, `/api/agents/{id}/summary`, `/api/signals/follow`, `/api/signals/unfollow` |
| **Services** | `service/server/services.py` | Agent CRUD, token management, position management (buy/sell/short/cover), signal broadcasting to followers |
| **Market Intel** | `service/server/market_intel.py` | Market news snapshots, macro signal snapshots, ETF flow snapshots |
| **Price Fetcher** | `service/server/price_fetcher.py` | Multi-market price fetching |
| **Experiments** | `service/server/experiments.py` | A/B testing framework for trading agents |
| **Challenges** | `service/server/challenges.py` | Trading competition system |
| **Team Missions** | `service/server/team_missions.py` | Collaborative team trading missions |
| **Signal Quality** | `service/server/signal_quality.py` | Signal quality scoring (verifiability, evidence, specificity, novelty) |
| **Rewards** | `service/server/rewards.py` | Agent reward ledger system |
| **Permissions** | `service/server/permissions.py` | Role-based access control |
| **Cache** | `service/server/cache.py` | Redis caching with JSON serialization |
| **Worker** | `service/server/worker.py` | Background worker for price updates, settlements |
| **Skills** | `skills/market-intel/`, `skills/ai4trade/`, `skills/polymarket/`, `skills/copytrade/`, `skills/tradesync/` | Agent skill definitions |

**Database Schema (30+ tables):** agents, users, signals, positions, subscriptions, experiments, experiment_assignments, experiment_events, challenges, challenge_participants, challenge_trades, challenge_results, team_missions, teams, team_members, team_messages, team_submissions, team_contributions, team_results, polymarket_settlements, signal_predictions, signal_quality_scores, agent_metric_snapshots, network_edges, profit_history, agent_reward_ledger, rate_limits, market_news_snapshots, macro_signal_snapshots, etf_flow_snapshots, stock_analysis_snapshots

**Unique Code MUST Preserve:**
- Dual SQLite/PostgreSQL database adapter with automatic SQL translation
- Copy-trading signal broadcasting system
- A/B experiment framework for trading agents
- Challenge/competition scoring system
- Signal quality scoring model
- Team mission collaborative framework
- Polymarket settlement logic

**Code Quality:** ★★★★☆ — Production-quality, well-structured, extensive test suite (17+ test files), proper caching, dual-database support. Some Chinese comments.

**Dependencies:** FastAPI, uvicorn, psycopg (optional), redis (optional), bcrypt, yfinance

---

### 2. Vibe-Trading — 456 Alpha Factors & 9 Backtest Engines

**Purpose:** Comprehensive quantitative trading agent platform with the largest factor library, multiple market backtest engines, and a sophisticated ReAct agent loop.

**Tech Stack:** Python, pandas, numpy, React (Vite/TypeScript), Docker, MCP protocol, SSE streaming

**Key Modules & Implementations:**

#### Factor Library (456 factors total)

| Category | Count | Directory | Source |
|----------|-------|-----------|--------|
| **Alpha101** | 101 | `agent/src/factors/zoo/alpha101/` | WorldQuant Alpha101 |
| **GTJA191** | 192 | `agent/src/factors/zoo/gtja191/` | Guotai Junan 191 |
| **Qlib158** | 155 | `agent/src/factors/zoo/qlib158/` | Microsoft Qlib 158 |
| **Academic** | 7 | `agent/src/factors/zoo/academic/` | Fama-French, Carhart |

#### Backtest Engines (9 engines)

| Engine | File | Market | Features |
|--------|------|--------|----------|
| **BaseEngine** | `engines/base.py` | Abstract | Bar-by-bar execution, signal alignment, optimizer loading, artifact writing |
| **ChinaAEngine** | `engines/china_a.py` | A-share | T+1, no short, price limits (10%/20%) |
| **GlobalEquityEngine** | `engines/global_equity.py` | US/HK | Standard equity rules |
| **CryptoEngine** | `engines/crypto.py` | Crypto | Funding fees, liquidation, 24/7 |
| **ForexEngine** | `engines/forex.py` | FX | Spread, swap, high leverage |
| **ChinaFuturesEngine** | `engines/china_futures.py` | CN futures | CFFEX/SHFE/DCE/ZCE/INE, contract multiplier |
| **GlobalFuturesEngine** | `engines/global_futures.py` | Global futures | CME/ICE/Eurex |
| **CompositeEngine** | `engines/composite.py` | Cross-market | Shared capital pool, delegates to sub-engines |
| **OptionsPortfolio** | `engines/options_portfolio.py` | Options | Black-Scholes, IV smile |

#### Portfolio Optimizers (5)

| Optimizer | File | Method |
|-----------|------|--------|
| **Risk Parity** | `optimizers/risk_parity.py` | Equal risk contribution |
| **Mean Variance** | `optimizers/mean_variance.py` | Markowitz |
| **Max Diversification** | `optimizers/max_diversification.py` | Diversification ratio |
| **Equal Volatility** | `optimizers/equal_volatility.py` | Inverse volatility weighting |
| **Base** | `optimizers/base.py` | ABC |

#### Data Loaders (8)

| Loader | File | Source |
|--------|------|--------|
| **CCXT** | `loaders/ccxt_loader.py` | Crypto exchanges |
| **OKX** | `loaders/okx.py` | OKX exchange |
| **FUTU** | `loaders/futu.py` | Futu OpenD |
| **Tushare** | `loaders/tushare.py` | Chinese A-share |
| **Tushare Fundamentals** | `loaders/tushare_fundamentals.py` | Statement data |
| **AKShare** | `loaders/akshare_loader.py` | Chinese market |
| **YFinance** | `loaders/yfinance_loader.py` | Global equities |
| **Registry** | `loaders/registry.py` | Loader selection |

#### Agent System

| Component | File | Description |
|-----------|------|-------------|
| **AgentLoop** | `agent/src/agent/loop.py` | ReAct core loop with 5-layer context management |
| **Context Builder** | `agent/src/agent/context.py` | System prompt + skill + memory assembly |
| **Tool Registry** | `agent/src/agent/tools.py` | 28 tool definitions |
| **Memory** | `agent/src/agent/memory.py` | Workspace memory with state tracking |
| **Trace** | `agent/src/agent/trace.py` | Execution trace writer |
| **Persistent Memory** | `agent/src/memory/persistent.py` | Cross-session recall |

#### 5-Layer Context Management (in AgentLoop)

1. **Microcompact** — silently prunes old tool results
2. **Context collapse** — folds long text blocks (zero LLM cost)
3. **Auto compact** — LLM structured summary with token-budget tail protection
4. **Compact tool** — model explicitly triggers compression
5. **Iterative update** — Nth compression updates previous summary (zero info decay)

#### 28 Agent Tools

| Tool | File | Description |
|------|------|-------------|
| `backtest` | `tools/backtest_tool.py` | Run backtests |
| `alpha_zoo` | `tools/alpha_zoo_tool.py` | Factor library browser |
| `alpha_bench` | `tools/alpha_bench_tool.py` | Factor benchmarking |
| `factor_analysis` | `tools/factor_analysis_tool.py` | IC/IR analysis |
| `shadow_account` | `tools/shadow_account_tool.py` | Paper trading account |
| `trade_journal` | `tools/trade_journal_tool.py` | Trade logging |
| `hypothesis` | `tools/hypothesis_tool.py` | Hypothesis tracking |
| `pattern` | `tools/pattern_tool.py` | Pattern recognition |
| `options_pricing` | `tools/options_pricing_tool.py` | Black-Scholes pricing |
| `remember` | `tools/remember_tool.py` | Persistent memory |
| `compact` | `tools/compact_tool.py` | Context compression |
| `swarm` | `tools/swarm_tool.py` | Multi-agent coordination |
| `skill_writer` | `tools/skill_writer_tool.py` | Dynamic skill creation |
| + 15 more | ... | Web search, file ops, MCP, etc. |

#### 75 Skills

Including: SMC, Elliott Wave, ChanLun (缠论), candlestick, pair-trading, DeFi yield, stablecoin flow, token unlock, earnings revision, dividend analysis, ETF analysis, financial statement, EDGAR SEC filings, volatility, seasonal, hedging strategy, asset allocation, sentiment analysis, ML strategy, etc.

#### Swarm Presets (29 multi-agent team configs)

Including: Investment Committee, Risk Committee, Crypto Trading Desk, Quant Strategy Desk, Pairs Research Lab, Factor Research Committee, Macro Strategy Forum, Geopolitical War Room, etc.

**Unique Code MUST Preserve:**
- All 456 alpha factor implementations with golden test fixtures
- 9-market backtest engine hierarchy (BaseEngine → specialized engines)
- 5-layer context management system in AgentLoop
- Shadow account paper trading system with codegen
- Swarm multi-agent runtime with 29 preset configurations
- 75 skill definitions with Chinese market support (ChanLun, AKShare, Tushare, Futu)
- Options pricing with IV smile
- Backtest validation framework

**Code Quality:** ★★★★★ — Exceptionally well-engineered. Comprehensive test suite (70+ test files), proper ABC inheritance, detailed docstrings, golden test fixtures for factors, security scanning, sandbox tools.

**Dependencies:** pandas, numpy, ccxt, yfinance, tushare, akshare, futu-api, openai, anthropic, flask, fastapi (MCP server), Docker

---

### 3. OpenAlice — Best Architecture Reference

**Purpose:** Universal Trading Agent platform with domain-driven TypeScript architecture, IBKR integration, and workspace-based agent system.

**Tech Stack:** TypeScript, Node.js, Vite, React, Fastify, pnpm workspaces, OpenBB/TypeBB, IBKR, Electron

**Key Modules & Implementations:**

| Module | Directory | Description |
|--------|-----------|-------------|
| **Core** | `src/core/` | Event bus, config, session, tool center, credential inference, AI provider manager, compaction, inbox store |
| **AI Providers** | `src/ai-providers/` | Vercel AI SDK, Agent SDK, Codex, mock provider, preset catalog |
| **Domain: Market Data** | `src/domain/market-data/` | Equity, crypto, commodity, currency, economy sub-domains with type-safe clients |
| **Domain: Analysis** | `src/domain/analysis/` | Technical indicators, statistics, calculator engine |
| **Domain: News** | `src/domain/news/` | RSS collector, archive, store |
| **Domain: Thinking** | `src/domain/thinking/` | Calculate tool (AI reasoning) |
| **Workspaces** | `src/workspaces/` | Session registry, workspace creator, template system, context injector, CLI adapter, Claude/Shell/Codex adapters |
| **WebUI Routes** | `src/webui/routes/` | 20+ API routes (auth, config, news, trading, events, inbox, market, topology, tools, cron, workspaces, persona) |
| **Services: Auth** | `src/services/auth/` | Token store, session store |
| **Services: UTA** | `services/uta/` | Universal Trading Agent — trading order entry, simulator routes, guard pipeline (max position, symbol whitelist, cooldown) |
| **Services: UTA Protocol** | `packages/uta-protocol/` | Shared types for broker, manager, errors, contract extension |
| **Package: IBKR** | `packages/ibkr/` | Full Interactive Brokers integration (order decoder, wrapper, protobuf) |
| **Migrations** | `src/migrations/` | 7 database migrations with runner |
| **Security** | `safe/` | Threat model, playbooks, agent brief, harness |
| **UI** | `ui/` | 25+ pages, demo mode with mock service worker |

**Unique Code MUST Preserve:**
- Domain-driven TypeScript architecture pattern (market-data, analysis, news, thinking)
- IBKR package with protobuf order decoding
- UTA (Universal Trading Agent) service with guard pipeline
- Workspace system with template-based agent creation
- Multi-AI-provider abstraction (Vercel SDK, Agent SDK, Codex)
- Migration framework for database schema evolution
- Security threat model and playbooks

**Code Quality:** ★★★★★ — Enterprise-grade TypeScript. Comprehensive type system, domain-driven design, proper separation of concerns, extensive test coverage, security-first approach.

**Dependencies:** TypeScript, React, Vite, Fastify, pnpm, OpenBB, IBKR API, Electron

---

### 4. HermesQuantOS — 21-Agent Trading System

**Purpose:** Autonomous multi-agent trading & research infrastructure with hardcoded risk rules, Telegram bot interface, and multi-LLM provider failover.

**Tech Stack:** Python, asyncio, aiohttp, SQLite (shared state), Telegram Bot API, NVIDIA/Groq/OpenCode LLM providers

**Key Modules & Implementations:**

#### 21 Agents Across 5 Layers

| Layer | Agents |
|-------|--------|
| **L1: Data** | MarketDataTool, ChartVisionTool |
| **L2: Analysis** | TechnicalAnalysisTool, MacroSentimentTool, SMCAgentEnhanced, NewsSentinelTool, MarketStateEngine |
| **L3: Decision** | StrategyTool, RiskOfficerTool (FULL VETO), PortfolioTool, DecisionSynthesisEngine, PressureNormalizationEngine, StrategyLifecycleManager |
| **L4: Execution** | ExecutionTool, KillSwitchTool, AutoSwitchEngine |
| **L5: Learning** | JournalTool, AuditorResearchTool, AuditLogger, BacktestEngine, MathEngine |

#### Key Implementations

| Component | File | Description |
|-----------|------|-------------|
| **Decision Synthesis Engine** | `tools/decision_engine.py` | Machine-readable decision table (7 rules): maps regime + pressure + confidence → ALLOW_LONG/SHORT/NO_TRADE/WATCH. Risk clearance: CLEAR/BLOCKED/PAUSE |
| **Pressure Normalization** | `tools/pressure_engine.py` | BUY/SELL pressure normalization (0.0-1.0) |
| **Market State Engine** | `tools/market_state_engine.py` | Regime detection: TRENDING/RANGE/MEAN_REVERT/RISK_OFF/PANIC/NO_TRADE |
| **Strategy Lifecycle** | `tools/strategy_lifecycle.py` | Darwinian evolution — auto-KILL negative expectancy strategies |
| **Risk Officer** | `tools/risk_officer_tool.py` | 9-checkpoint system, FULL VETO, hardcoded limits (0.5%/1%/3%) |
| **Shared State** | `tools/shared_state.py` | SQLite-backed shared state for cross-agent coordination |
| **Kill Switch** | `tools/kill_switch_tool.py` | Emergency halt, auto-trigger on limit breach |
| **Auto Switch** | `tools/autoswitch_engine.py` | Seamless LLM provider failover |
| **Watchdog** | `watchdog.py` | Process supervision with restart |

**Unique Code MUST Preserve:**
- Decision Synthesis Engine with machine-readable decision table
- Pressure normalization algorithm (0.0-1.0 scale)
- Strategy Lifecycle Manager (Darwinian auto-kill)
- Shared state SQLite persistence for cross-agent coordination
- Hardcoded risk framework with full veto system
- Multi-LLM provider failover (NVIDIA → Groq → OpenCode)

**Code Quality:** ★★★☆☆ — Functional but messy. Single-file monolith (hermes_quant.py ~900 lines), regex-based tool parsing (`[TOOL:name]args[/TOOL]`), Indonesian/English mixed comments. Strong conceptual design, weaker implementation.

**Dependencies:** aiohttp, python-dotenv, numpy, pandas (optional)

---

### 5. SolSniperX — Solana On-Chain Execution

**Purpose:** Solana token sniper with real on-chain execution via Jupiter Aggregator, mempool monitoring, and AI-powered analysis.

**Tech Stack:** Python (Flask + SocketIO + eventlet), React (Vite), Solana/solders, httpx, SQLite

**Key Modules & Implementations:**

| Module | File | Description |
|--------|------|-------------|
| **Trading Service** | `backend/src/services/trading_service.py` | Real Solana execution: Jupiter swap, JITO tip estimation, buy/sell orders, limit orders, transaction confirmation |
| **Mempool Monitor** | `backend/src/services/mempool_monitor.py` | Real-time Solana mempool monitoring for new tokens |
| **Wallet Service** | `backend/src/services/wallet_service.py` | Solana wallet management, keypair handling, token balances |
| **AI Analysis** | `backend/src/services/ai_analysis.py` | AI-powered token analysis |
| **Auto Trader** | `backend/src/services/auto_trader.py` | Autonomous sniping with new-token callbacks, rugpull alerts |
| **Data Fetcher** | `backend/src/services/data_fetcher.py` | Token data aggregation (DexScreener, RugCheck) |
| **Routes** | `backend/src/routes/` | 8 blueprints: tokens, ai, scanner, mempool, trading, wallet, auto_trader, analytics |
| **Database** | `backend/src/utils/db.py` | SQLite with trade recording, limit orders |
| **Frontend** | `frontend/` | React + shadcn/ui, 8 pages (Dashboard, Watchlist, Analytics, Trading, Settings, Wallet, TokenScanner, AI) |

**Unique Code MUST Preserve:**
- Jupiter Aggregator swap execution (buy/sell with SOL pairs)
- Dynamic JITO tip estimation from Block Engine API
- Real Solana transaction signing and confirmation with exponential backoff
- Mempool monitoring for new token detection
- Auto-trader with on_new_token/on_rugpull callbacks
- Limit order system with price-based execution

**Code Quality:** ★★★★☆ — Clean Flask-SocketIO architecture, proper async/sync bridge, real on-chain execution code. Production-ready features.

**Dependencies:** Flask, flask-socketio, eventlet, solana, solders, httpx, sqlite3

---

### 6. Kronos — PyTorch Financial Time-Series Model

**Purpose:** Novel tokenizer-based financial time-series forecasting model using Binary Spherical Quantization (BSQuantizer) and hierarchical token prediction.

**Tech Stack:** Python, PyTorch, HuggingFace Hub (PyTorchModelHubMixin), pandas, numpy

**Key Modules & Implementations:**

| Module | File | Description |
|--------|------|-------------|
| **KronosTokenizer** | `model/kronos.py` | Encoder-decoder tokenizer with BSQuantizer: encodes OHLCV → discrete tokens, decodes back. s1_bits (coarse) + s2_bits (fine) hierarchical quantization |
| **Kronos Model** | `model/kronos.py` | HierarchicalEmbedding + TemporalEmbedding + Transformer + DependencyAwareLayer + DualHead. Predicts s1 and s2 tokens autoregressively |
| **KronosPredictor** | `model/kronos.py` | High-level API: predict(), predict_batch(). Accepts DataFrames with OHLCV, returns prediction DataFrames |
| **Module Components** | `model/module.py` | TransformerBlock, BSQuantizer, HierarchicalEmbedding, TemporalEmbedding, DependencyAwareLayer, DualHead, RMSNorm |
| **Auto-regressive Inference** | `model/kronos.py` | Multi-sample inference with top-k/top-p filtering, sliding context window |
| **Fine-tune** | `finetune/` | Fine-tuning scripts |
| **WebUI** | `webui/` | Visualization interface |

**Unique Code MUST Preserve:**
- BSQuantizer (Binary Spherical Quantization) — novel quantization for financial data
- Hierarchical token prediction (s1 coarse + s2 fine)
- DependencyAwareLayer — conditions s2 on s1 predictions
- TemporalEmbedding — learnable time features
- Auto-regressive inference with multi-sample averaging
- KronosPredictor high-level API for DataFrame-based predictions

**Code Quality:** ★★★★☆ — Solid ML engineering, proper PyTorch patterns, HuggingFace Hub integration. Documentation could be stronger.

**Dependencies:** torch, numpy, pandas, huggingface_hub, tqdm

---

### 7. TradingAgents — Multi-Agent Trading Framework

**Purpose:** LangGraph-based multi-agent trading framework with graph-based signal processing, reflection, and propagation.

**Tech Stack:** Python, LangGraph/LangChain, pyproject.toml

**Key Modules & Implementations:**

| Module | Directory | Description |
|--------|-----------|-------------|
| **Graph Core** | `tradingagents/graph/` | TradingAgentsGraph, ConditionalLogic, GraphSetup, Propagator, Reflector, SignalProcessor |
| **Agents** | `tradingagents/agents/` | Multiple specialized agents |
| **Data Flows** | `tradingagents/dataflows/` | Data pipeline definitions |
| **Config** | `tradingagents/default_config.py` | Default configuration |
| **CLI** | `cli/` | Command-line interface |

**Unique Code MUST Preserve:**
- LangGraph-based trading graph with conditional logic
- Propagation and reflection mechanisms for multi-agent coordination
- Signal processing pipeline in graph context

**Code Quality:** ★★★☆☆ — Reasonable structure, LangGraph dependency may limit portability.

**Dependencies:** langchain, langgraph, pydantic

---

### 8. ai-hedge-fund — AI Hedge Fund Implementation

**Purpose:** AI-powered hedge fund with multiple specialist agents (fundamental, technical, sentiment, risk, portfolio, trader).

**Tech Stack:** Python, FastAPI (backend), React (frontend)

**Key Modules & Implementations:**

| Module | File | Description |
|--------|------|-------------|
| **Advanced Orchestrator** | `agents/advanced_orchestrator.py` | Multi-ticker query parsing with intent mapping |
| **Fundamental Analyst** | `agents/fundamental_analyst.py` | Fundamental analysis agent |
| **Technical Analyst** | `agents/technical_analyst.py` | Technical analysis agent |
| **Sentiment Analyst** | `agents/sentiment_analyst.py` | Sentiment analysis agent |
| **Risk Manager** | `agents/risk_manager.py` | Risk assessment agent |
| **Portfolio Manager** | `agents/portfolio_manager.py` | Portfolio optimization agent |
| **Signal Agent** | `agents/signal_agent.py` | Signal generation |
| **Strategy Manager** | `agents/strategy_manager.py` | Strategy lifecycle |
| **Trader Agent** | `agents/trader_agent.py` | Trade execution |
| **Query Orchestrator** | `agents/query_orchestrator.py` | Query routing |
| **Models** | `agents/models.py` | Data models |

**Unique Code:** Standard multi-agent pattern with specialist decomposition. No unique algorithms.

**Code Quality:** ★★★☆☆ — Standard agent structure, some agents are thin wrappers. Documentation-heavy (many .md files).

**Dependencies:** Python, FastAPI, React

---

### 9. QuantDinger — Quantitative Trading Tools

**Purpose:** Python backend API + Vue.js frontend for quantitative trading tools.

**Tech Stack:** Python (Gunicorn), Vue.js, Docker

**Key Modules:**

| Module | Directory | Description |
|--------|-----------|-------------|
| **Backend API** | `backend_api_python/app/` | FastAPI/Flask API server |
| **Vue Frontend** | `quantdinger_vue/` | Vue.js dashboard |
| **Docker** | `backend_api_python/Dockerfile` | Containerized deployment |

**Unique Code:** Standard CRUD trading tool. Limited unique value.

**Code Quality:** ★★☆☆☆ — Boilerplate-heavy, limited domain logic.

**Dependencies:** Python, gunicorn, Vue.js

---

### 10. ai-financial-agent — Financial AI Agent

**Purpose:** Next.js-based financial AI agent with Drizzle ORM.

**Tech Stack:** Next.js, TypeScript, Drizzle ORM, Tailwind CSS, pnpm

**Key Modules:**

| Module | Directory | Description |
|--------|-----------|-------------|
| **App** | `app/` | Next.js app router pages |
| **Components** | `components/` | UI components (shadcn/ui) |
| **Hooks** | `hooks/` | React hooks |
| **Lib** | `lib/` | Utility functions |
| **Drizzle Config** | `drizzle.config.ts` | ORM configuration |

**Unique Code:** Frontend shell only. No trading algorithms.

**Code Quality:** ★★☆☆☆ — UI-focused, no core trading logic.

**Dependencies:** Next.js, drizzle-orm, tailwindcss, pnpm

---

### 11. AutoTrader — Auto Trading System

**Purpose:** Established Python trading library (pip-installable) with broker integration, strategy framework, and plotting.

**Tech Stack:** Python, setuptools

**Key Modules:**

| Module | File | Description |
|--------|------|-------------|
| **AutoTrader** | `autotrader/autotrader.py` | Main trading engine |
| **AutoBot** | `autotrader/autobot.py` | Bot framework |
| **AutoPlot** | `autotrader/autoplot.py` | Visualization |
| **Strategy** | `autotrader/strategy.py` | Strategy base class |
| **Indicators** | `autotrader/indicators.py` | Technical indicators |
| **Brokers** | `autotrader/brokers/` | Broker integrations |
| **Comms** | `autotrader/comms/` | Communication (email, etc.) |
| **Utilities** | `autotrader/utilities.py` | Utility functions |

**Unique Code:** Established library with broker abstraction. Generic trading framework, not specialized.

**Code Quality:** ★★★★☆ — Well-structured Python package, proper setup.py, pip-installable.

**Dependencies:** pandas, matplotlib, numpy

---

### 12. bloomberg-terminal — Terminal Implementation

**Purpose:** Next.js-based financial terminal UI with Discord/Telegram/WhatsApp bot integrations.

**Tech Stack:** Next.js, TypeScript, Tailwind CSS, Discord.js, node-telegram-bot-api

**Key Modules:**

| Module | Directory | Description |
|--------|-----------|-------------|
| **App** | `app/` | Next.js app (minimal: api + layout) |
| **Discord Bot** | `discord-bot.js` | Discord integration |
| **Telegram Bot** | `telegram-bot.js` | Telegram integration |
| **WhatsApp Bot** | `whatsapp-bot.js` | WhatsApp integration |

**Unique Code:** Multi-platform bot integration pattern. Minimal trading logic.

**Code Quality:** ★★☆☆☆ — UI shell with chat bot integrations.

**Dependencies:** Next.js, discord.js, node-telegram-bot-api

---

### 13. Pentaract — Rust Web Server

**Purpose:** Rust-based web server with Docker deployment. No trading-specific logic.

**Tech Stack:** Rust (Axum/Actix), Docker, Vue.js (UI)

**Key Modules:**

| Module | Directory | Description |
|--------|-----------|-------------|
| **Rust Server** | `pentaract/src/` | Rust web server with models, repositories, routers, schemas, services |
| **UI** | `ui/` | Vue.js frontend |

**Unique Code:** Clean Rust web architecture. Could serve as template for high-performance services. No trading logic.

**Code Quality:** ★★★☆☆ — Clean Rust code, proper module separation.

**Dependencies:** Rust, Docker, Vue.js

---

### 14. skales — Multi-Platform Chat Bot

**Purpose:** Multi-platform bot (Discord, Telegram, WhatsApp) with Next.js web interface.

**Tech Stack:** Next.js, TypeScript, Discord.js, node-telegram-bot-api, pnpm

**Key Modules:**

| Module | Directory | Description |
|--------|-----------|-------------|
| **Web App** | `apps/web/` | Next.js web interface |
| **Discord Bot** | `discord-bot.js` | Discord integration |
| **Telegram Bot** | `telegram-bot.js` | Telegram integration |
| **WhatsApp Bot** | `whatsapp-bot.js` | WhatsApp integration |

**Unique Code:** Multi-platform bot integration. No trading logic.

**Code Quality:** ★★☆☆☆ — Boilerplate chat bot code.

**Dependencies:** Next.js, discord.js, node-telegram-bot-api

---

### 15. Misi-Screener — Screening Tool

**Purpose:** Stock/crypto screening tool with AI agents for fundamental analysis, technical analysis, sentiment, risk management, and portfolio management.

**Tech Stack:** Python, Docker, FastAPI (backend), React (frontend)

**Key Modules:**

| Module | File | Description |
|--------|------|-------------|
| **Advanced Orchestrator** | `agents/advanced_orchestrator.py` | Multi-ticker query parsing |
| **AI Agent** | `agents/advanced_orchestrator.py` | Agent with app registry pattern |
| **Fundamental Analyst** | `agents/fundamental_analyst.py` | Fundamental analysis |
| **Technical Analyst** | `agents/technical_analyst.py` | Technical analysis |
| **Sentiment Analyst** | `agents/sentiment_analyst.py` | Sentiment analysis |
| **Risk Manager** | `agents/risk_manager.py` | Risk assessment |
| **Portfolio Manager** | `agents/portfolio_manager.py` | Portfolio optimization |
| **Signal Agent** | `agents/signal_agent.py` | Signal generation |
| **Strategy Manager** | `agents/strategy_manager.py` | Strategy lifecycle |
| **Trader Agent** | `agents/trader_agent.py` | Trade execution |
| **API** | `api/` | FastAPI backend |
| **Frontend** | `frontend/` | React dashboard |
| **Data Sources** | `data_sources/` | Market data providers |
| **Execution** | `execution/` | Trade execution |
| **Docs** | `docs/` | Documentation |

**Unique Code:** Structured agent decomposition pattern. Similar to ai-hedge-fund.

**Code Quality:** ★★★☆☆ — Reasonable structure, some agents are thin.

**Dependencies:** Python, FastAPI, React, Docker

---

## Consolidation Recommendations

### Must Consolidate (Highest Priority)

1. **Vibe-Trading factor library** → `libs/factors/` — All 456 factors with test fixtures
2. **Vibe-Trading backtest engines** → `libs/backtest/` — 9 engines + 5 optimizers + 8 loaders
3. **Vibe-Trading agent loop** → `libs/agent/` — 5-layer context management, tool registry, memory
4. **AI-Trader server** → `services/trading-server/` — FastAPI server, DB schema, signal/copy-trade system
5. **HermesQuantOS decision engine** → `libs/decision/` — Decision synthesis, pressure normalization, market state
6. **SolSniperX execution** → `libs/execution/solana/` — Jupiter swap, JITO tips, mempool monitoring

### Should Consolidate (Medium Priority)

7. **OpenAlice architecture** → Use as TypeScript monorepo reference pattern
8. **OpenAlice IBKR package** → `packages/ibkr/` — Interactive Brokers integration
9. **OpenAlice UTA** → `services/uta/` — Universal Trading Agent with guard pipeline
10. **Kronos model** → `libs/models/kronos/` — BSQuantizer, KronosPredictor
11. **Vibe-Trading skills** → `skills/` — 75 skill definitions (can be selectively migrated)
12. **Vibe-Trading swarm** → `libs/swarm/` — Multi-agent runtime with presets
13. **HermesQuantOS risk framework** → `libs/risk/` — Hardcoded risk rules, kill switch

### Can Skip (Low Priority)

14. **ai-financial-agent** — Frontend shell only
15. **bloomberg-terminal** — UI shell + chat bots
16. **Pentaract** — Rust boilerplate
17. **skales** — Chat bot integration
18. **QuantDinger** — Standard CRUD
19. **ai-hedge-fund** — Redundant with HermesQuantOS/Misi-Screener agents
20. **Misi-Screener** — Redundant agent structure
21. **AutoTrader** — Generic pip library, can be used as dependency

### Dependency Map

```
Vibe-Trading factors ←── used by backtest engines ←── used by agent loop
AI-Trader server ←── uses signals/positions ←── feeds from agents
HermesQuantOS tools ←── decision engine ←── feeds from market data
SolSniperX execution ←── Jupiter Aggregator ←── Solana RPC
Kronos model ←── PyTorch ←── standalone predictor
OpenAlice UTA ←── IBKR package ←── domain types
TradingAgents ←── LangGraph ←── trading graph
```

### Overlap Analysis

| Overlapping Area | Repos | Best Implementation | Merge Strategy |
|------------------|-------|---------------------|----------------|
| **Agent Loop** | Vibe-Trading, HermesQuantOS | Vibe-Trading (5-layer context) | Use Vibe-Trading's AgentLoop, extract Hermes decision logic as tools |
| **Backtest** | Vibe-Trading, HermesQuantOS | Vibe-Trading (9 engines) | Use Vibe-Trading's engines, extract Hermes backtest tool as lightweight wrapper |
| **Risk Management** | HermesQuantOS, AI-Trader, ai-hedge-fund | HermesQuantOS (hardcoded veto) | Use Hermes risk framework as core, adapt AI-Trader's experiment-based risk checks |
| **Market Data** | Vibe-Trading, OpenAlice, HermesQuantOS | Vibe-Trading (8 loaders) | Use Vibe-Trading's loader registry, add OpenAlice's TypeBB client |
| **Execution** | SolSniperX, AI-Trader, HermesQuantOS | SolSniperX (real on-chain) | Use SolSniperX for Solana, AI-Trader for paper trading, Hermes for MT5/OANDA |
| **Multi-Agent Orchestration** | Vibe-Trading (swarm), TradingAgents (graph), HermesQuantOS (layers) | Vibe-Trading (swarm runtime) | Use Vibe-Trading's swarm, consider TradingAgents' graph for complex workflows |

---

*End of audit report.*
