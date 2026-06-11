# CHANGELOG - QUANT NANGGROE AI

## [v2.1.0] - 2026-06-11 — C1 FULL CONSOLIDATION & BRANCH MERGE

### Overview
Full consolidation of all C1 branches and `quant_nanggroe/` package merge. All 25 C1 repos audited, all branch implementations (cl1-agent-1, cl1-agent-3, cl1-agent-4, Julecl1-session) merged into Julecl1, and `quant_nanggroe/` package (154 files) consolidated into `src/quant_nanggroe_ai/`.

### Added — Branch Consolidation
- **cl1-agent-1 branch** → Agent nodes (execution, prediction_market), tools, exchange layer
- **cl1-agent-3 branch** → Engine risk/strategy submodules, event_bus, models, regime, simulation
- **cl1-agent-4 branch** → Memory expansion, MCP module, security expansion
- **Julecl1-session branch** → Models, regime, simulation, types

### Added — 7 Unique Python Modules from Branches
- `agents/nodes/execution.py` — Order execution agent node
- `agents/nodes/prediction_market.py` — Prediction market analysis node
- `engine/event_bus.py` — Event-driven message bus
- `engine/models.py` — Shared engine model definitions
- `engine/regime.py` — Advanced regime detection
- `engine/simulation.py` — Monte Carlo simulation engine
- Type definitions across modules

### Added — New Modules
- **MCP Module** (`mcp/`) — Model Context Protocol: client, server, protocol, tools (5 files)
- **Exchange Module** (`exchange/`) — Exchange abstraction layer: base, factory, manager, guards, order_types, paper_broker, alpaca_broker, ccxt_broker, solana/ submodule (15 files)
- **Engine Strategy** (`engine/strategy/`) — Strategy schema, loader, parser, backtest_adapter (5 files)
- **Engine Risk** (`engine/risk/`) — Constitutional rules hardcoded in constants.py, checks, manager, position_sizing, kelly, var, drawdown, correlation, risk_parity, emotional_lockout, kill_switch (11 files)
- **Security** (expanded `security/`) — auth, scanner, audit, keyvault, credential_inference (6 files)
- **Memory** (expanded `memory/`) — knowledge, knowledge_graph, journal, session, compression, paging (10 files)
- **MultiColony** (`multicolony/`) — C2 AI MultiColony Ecosystem: colony, runtime, skills, tools, memory, knowledge (22 files, 6,613 lines)

### Added — quant_nanggroe/ Package Merge
- 154 files from `quant_nanggroe/` package consolidated into `src/quant_nanggroe_ai/`
- All `from quant_nanggroe.*` imports refactored to `from quant_nanggroe_ai.*`
- Module deduplication: overlapping code merged, not duplicated

### Changed — Key Metrics
- **Agent nodes**: 7 → 9+ (added execution, prediction_market)
- **Agent tools**: 5 → 11 (added trading_plan, file_ops, financial_data, portfolio_simulator, query_router, token_reducer)
- **Alpha factors**: 456+ → 452 (alpha101=101, qlib158=154, gtja191=191, academic=7)
- **Execution brokers**: 4 → 5 (added Kalshi)
- **Test count**: 175+ → 766+
- **Python packages**: 20 → 27+

### Architecture Highlights
- **4-layer agent stack**: LangGraph → CrewAI → PydanticAI → DSPy
- **9-agent trading council**: Researcher, Trader, Strategist, Risk, Portfolio, Execution, Macro, Crypto, Forex
- **452 alpha factors**: alpha101 + qlib158 + gtja191 + academic
- **Constitutional rules** hardcoded in `engine/risk/constants.py` (NON-NEGOTIABLE)
- **NautilusTrader adapter** integrated
- **Fama-French 5-factor model** implemented

### Documentation Updated
- **README.md** — Updated project structure with all new modules
- **ARCHITECTURE.md** — v2.1.0 with new module descriptions (MCP, Exchange, Engine Risk/Strategy, Security, Memory)
- **MONOREPO_STATUS.md** — Updated to 80% production-ready, all C1 repos consolidated
- **CLUSTER1_CONSOLIDATION_REPORT.md** — Added Section 10: Branch Consolidation & quant_nanggroe/ Package Merge

---

## [v2.0.0] - 2026-03-06 — C1 MONOREPO CONSOLIDATION

### Overview
Konsolidasi seluruh Cluster 1 ke dalam monorepo terpadu. 25+ repositori digabungkan, semua import path diperbaiki, dan dokumentasi dikonsolidasikan.

### Added — Repository Merges
- **SolSniperX v3.3.0** → `solana_scanner/` + `execution/solsniperx_service.py` + React components
  - v3.3.0 "Ultimate Intelligence Upgrade" dari 9 remote branches
  - Service watchdog, advanced mempool filtering, RugCheck retry, social metadata
  - Limit orders, trailing stop-loss, multiple take-profit tiers
  - SQLite database schema (trades, positions, limit_orders, system_stats)
  - 7 existing files updated, 7 new files created (~1,115 lines)
- **ai-manus (feat/auth + feature/agent-file-oprate + tmp)** → `api/auth.py` + `agents/tools/file_ops.py` + `agents/mcp_config.py`
  - JWT authentication with PBKDF2-SHA256 (100K rounds)
  - Role-based access control (ADMIN, TRADER, VIEWER)
  - File operations with Local + MongoDB GridFS storage
  - MCP configuration with 5 default servers
  - ~1,280 lines merged and adapted
- **Trading-Plan-AI-Interactive v11.1.4** → `api/client.py` + `agents/tools/trading_plan.py` + `integrations/whatsapp_bot.py` + `integrations/__init__.py`
  - Trading Plan API client with API key auth
  - CFTC commitment-of-traders data, trade journal, emotional lockout
  - WhatsApp bot with command handlers
  - ~1,235 lines of Python ported from TypeScript/Node.js/GAS
- **sim (Kalshi + Polymarket tools)** → `execution/kalshi.py` (new) + `execution/polymarket.py` (enhanced)
  - Kalshi broker: 12 Pydantic models, 17 async methods, RSA-PSS auth (~1,272 lines)
  - Polymarket broker: 9 new models, 15 new async methods, Gamma + CLOB + Data APIs (+789 lines)
  - ~2,067 net new lines from 38 TypeScript source files

### Fixed — Import Path Corrections
- **73+ files** had broken `from src.*` imports (241+ import lines)
- All imports refactored from `from src.X` → `from quant_nanggroe_ai.X`
- 50+ string literal class_path references fixed in `hedge_fund/strategies/comprehensive_registry.py`
- 6 modules given graceful ImportError guards for optional dependencies
- `CompiledGraph → CompiledStateGraph` langgraph API compatibility fix
- Full import verification: `import quant_nanggroe_ai` → OK

### Fixed — Core Engine Bugs (from Task 1)
- Enum comparisons in `agents/graph.py` (MarketRegime, RiskClearance)
- Pydantic `.get()` → attribute access
- Broken expectancy calculation in `strategy_lifecycle.py`
- `alpha020` missing low parameter, `alpha003` wrong parameter
- Floating point precision in R:R ratio in `risk_guard.py`

### Added — New Infrastructure (from Task 1)
- Data layer: `database.py` (SQLAlchemy 2.0 async), `cache.py` (Redis), `models.py` (7 ORM), `worker.py` (5-async-loop)
- Shared singletons: KillSwitch, RiskGuard, MarketEngine, DecisionEngine
- All 6 API route modules using shared singletons
- Alembic infrastructure (alembic.ini, env.py, versions/)
- Docker configs fixed (Dockerfile, docker-compose.yml, setup_dev.sh)

### Documentation
- **README.md** — Rewritten to reflect monorepo structure, 9-agent council, 456+ factors, 5 brokers
- **ARCHITECTURE.md** — Updated with 4-layer agent stack, LangGraph graph, MCP+A2A, storage layer
- **CONTRIBUTING.md** — Updated with monorepo contribution guidelines
- **CLUSTER1_CONSOLIDATION_REPORT.md** — New comprehensive report documenting all C1 merges
- **CONVENTIONS.md** — Updated with monorepo coding conventions
- Merge logs: SOLSNIPERX_MERGE_LOG.md, AI_MANUS_MERGE_LOG.md, TRADING_PLAN_MERGE_LOG.md, SIM_MERGE_LOG.md, IMPORT_FIX_LOG.md
- Audit reports: MONOREPO_STATUS.md, C2_AUDIT_STATUS.md, BRANCH_AUDIT_COMPLETE.md

### Statistics
- **17,203+ lines** added across 71+ files (Task 1 core overhaul)
- **5,697+ lines** added from branch merges (SolSniperX, ai-manus, Trading-Plan, sim)
- **73+ files** fixed with correct import paths (241+ import lines)
- **5 execution brokers** registered (paper, alpaca, jupiter, polymarket, kalshi)
- **456+ alpha factors** (101 alpha101 + 154 qlib158 + 7 academic + 192 GTJA191)
- **9 agent nodes** in LangGraph graph
- **175+ tests** passing

---

## [v15.3.1] - 2026-03-06

### Security Fixes
- **CRITICAL**: Removed API key injection from `vite.config.ts` — `GEMINI_API_KEY` and `GOOGLE_DRIVE_FOLDER_ID` were being embedded into the client-side bundle via `define`, making them accessible in browser DevTools. API keys are now managed exclusively through the runtime Settings panel.
- **MEDIUM**: Fixed `ErrorBoundary` leaking internal error messages to end users in production. Now only shows generic error text in production mode; full details reserved for development.

### Bug Fixes
- **CRITICAL**: Fixed `App.tsx` using wrong property names `data.current_price` and `data.price_change_percentage_24h` — the `MarketTicker` type defines `currentPrice` and `priceChange24h`. This caused `/scan` market commands to crash with `undefined.toLocaleString()`.
- **CRITICAL**: Fixed `research_agent.ts` using wrong property names `btc?.current_price` and `btc?.price_change_percentage_24h` — same type mismatch as above.
- **CRITICAL**: Added missing `MathEngine.calculateCorrelation()` method — `CorrelationMonitor` was calling it but it didn't exist, causing runtime crash when `RiskManagement.validateTrade()` was invoked.
- **HIGH**: Fixed `AuditLogger` calling non-existent `BrowserFS.loadFile()` and `BrowserFS.saveFile()` — correct method names are `readFile()` and `writeFile()`.
- **HIGH**: Fixed `DecisionSynthesisEngine.synthesize()` calling `RiskManagement.validateTrade()` with 3 arguments when it expects 5 — replaced with `checkKillSwitch()` which matches the available data.
- **HIGH**: Fixed `backtest_engine.ts` argument order mismatch in `PressureNormalizationEngine.normalize()` call — reordered to match the function signature `(market, quant, smc, news, flow)`.
- **MEDIUM**: Added missing type definitions to `types.ts`: `StrategySignal`, `ConsensusReport`, `VirtualDiskNode`, `NeuralWeights`, `EvolutionState`.
- **MEDIUM**: Updated `TechnicalIndicators` type to include `stoch`, `cci`, `adx`, `bollinger`, `vwap`, `ma10`, `ma100` — matching what `MathEngine.analyzeSequence()` actually returns.

### Version Alignment
- Aligned all version strings across the codebase to **15.3.0**:
  - `package.json`: 2.0.0 → 15.3.0
  - `README.md` badge: 15.2.0 → 15.3.0
  - `metadata.json`: 15.1.0 → 15.3.0
  - `App.tsx` system prompt: v11.5.0 → v15.3.0
  - `gemini.ts` system prompt: v15.1.0 → v15.3.0
  - `ControlCenter.tsx`: v15.1.0 → v15.3.0
  - `SystemUpdater` prop: v11.5.0 → v15.3.0
  - `ARCHITECTURE.md`: v15.2.0 → v15.3.0
  - Terminal welcome text: v11.5 → v15.3
  - ResearchAgent log: v11.4 → v15.3.0

### Code Quality Improvements
- Fixed `package.json` name from `quant-nanggroe-ai-|-autonomous-hedge-fund` to `quant-nanggroe-ai` (pipe character is non-standard for npm package names)
- Added `description`, `author`, `license` fields to `package.json`
- Added `typecheck` and `lint` scripts to `package.json`
- Build script now runs `tsc --noEmit && vite build` for type-safe builds
- Added `@types/react` and `@types/react-dom` devDependencies (were missing)
- Enabled TypeScript strict mode with `noUnusedLocals`, `noUnusedParameters`, `noFallthroughCasesInSwitch`
- Removed unnecessary `experimentalDecorators` and `useDefineForClassFields` from `tsconfig.json` (no decorators used)
- Added `.env.example` template with all configurable environment variables documented
- Enhanced `.gitignore` with better organization, `.env.example` exclusion, certificate files, coverage, TypeScript build info
- Removed `requestFramePermissions` from `metadata.json` (Framer-specific, unnecessary)
- Rewrote `SECURITY.md` with comprehensive policy including API key protection, input validation, known limitations

---

## [v15.3.0] - 2026-03-05

### Fixed
- Replaced mock chart data with empty fallback in `market.ts` — no more fake OHLCV when APIs unavailable
- Replaced random mock flow/whale data with neutral state in `market.ts`
- Updated `.gitignore` to cover `.env.local`, sensitive files, and `cred`
- Removed `.env.local` and empty `cred` file from version control
- Fixed broken contact links in README
- Updated README with consolidated trilingual disclaimer (EN/ID/CN)
- Added contributor welcome section with specific roles

---

## [v15.2.0] - Previous Release
### Added
- **Contextual Neural Grounding**: Implementasi pemanenan data real-time sebelum penalaran agent untuk eliminasi halusinasi.
- **Latency & Performance Tracking**: Pelacakan timing presisi tinggi pada siklus Neural Swarm untuk kebutuhan audit institusional.
- **Institutional UI Flair**: Peningkatan `ControlCenter` dengan "Security Matrix" dan dashboard kesehatan "Risk Guardian".
- **Neural Inferences Grounding**: Pelabelan eksplisit pada sintesis swarm sebagai `NEURAL_INFERENCE` dengan trust score.

### Changed
- **Institutional Logic (v15.1.0)**: Upgrade kernel prompt untuk mewajibkan penalaran deterministik dan bukti kuantitatif.
- **Stability Patch**: Sinkronisasi konsistensi data (`currentPrice` & `priceChange24h`) di seluruh ekosistem Market & Portfolio.

---

## [v15.0.0] - 2026-01-06 (FINAL MVP: OPERATIONAL READINESS)
### Added
- **Risk Guardian (Constitutional Law)**: Implementasi layer penegakan risiko deterministik (Kill-switch 4% DD & Correlation Monitor).
- **Execution Reality Engine**: Integrasi simulasi trading realistis (Dynamic Spread, Slippage, Latency 100-500ms).
- **Strategy Lifecycle Manager**: Darwinian management yang membunuh strategi non-performan secara otomatis.
- **Audit Traceability**: Integrasi `AuditLogger` di seluruh layer (Market -> Sensor -> Pressure -> Decision -> Risk).

### Completed
- **Full MVP Lifecycle**: Penyelesaian seluruh rencana pembangunan 6 minggu sesuai `BUILD_PLAN.md`.

---

## [v12.0.0] - 2026-01-06 (PROFESSIONAL TRADING EDITION)
### Added
- **Institutional Logic (SMC)**: Implementasi Order Blocks, FVG, dan Market Structure Breaks.
- **Trading Terminal Portfolio**: Redesain Portfolio Management menjadi gaya terminal profesional (Equity, Margin, PnL real-time).
- **Institutional Data Pipeline**: Pipeline proxy-rotator untuk Binance dan sumber institusional.

---
*(Versi sebelumnya tetap tersedia di riwayat audit sistem)*

---

> **Contact:** Mulky Malikul Dhaher — [mulkymalikuldhaher@email.com](mailto:mulkymalikuldhaher@email.com)
>
> **Disclaimer:** This project is for Education Purpose only. Risiko apapun tidak kita tanggung. (We are not responsible for any risks or damages.)
