# CHANGELOG - QUANT NANGGROE AI

## [v16.0.0-alpha] - 2026-06-11 — CL1-AGENT-4 MASSIVE UPGRADE

### Architecture — Full Agent Council with Domain-Specific Routing
- **BREAKING**: Replaced `trader_node` in graph with dedicated `execution_node` (Smart Order Routing)
- **NEW**: Asset-class conditional routing — Researcher now routes to Crypto/Forex/PredictionMarket/Analyst based on symbol
- **NEW**: All domain nodes converge to Strategist → Risk Manager → Execution → Portfolio Manager

### Agent Nodes — 4 New Domain-Specific Agents
- **Crypto Agent** (`agents/nodes/crypto.py`): Mempool monitoring (Solana/BSC/ETH), SolSniperX fast-scoring, DEX routing (Jupiter/Raydium/PancakeSwap/Uniswap), 6-check anti-rug protection
- **Forex Agent** (`agents/nodes/forex.py`): Currency pair classification (major/minor/exotic), 8 central bank tracking, carry trade identification, CB risk assessment
- **Execution Agent** (`agents/nodes/execution.py`): Smart Order Routing with multi-venue scoring (Binance/Bybit/Alpaca/Jupiter/Polymarket/Paper), slippage management, pre-trade risk checks, latency monitoring
- **Prediction Market Agent** (`agents/nodes/prediction_market.py`): Polymarket/Kalshi integration, multi-source probability estimation, cross-market hedging, smart contract interaction

### Engine — 4 New Core Modules
- **Monte Carlo Simulation** (`engine/simulation.py`): GBM price paths, regime-aware simulation (HMM), walk-forward simulation, VaR/CVaR estimation
- **Factor Models** (`engine/models.py`): Fama-French 3/5 factor, Barra multi-factor, z-score normalization, factor return decomposition, Alpha101/technical integration
- **Regime Detection** (`engine/regime.py`): Gaussian HMM fitting, real-time probabilistic regime detection, transition probability matrix, cross-validation with MarketStateEngine
- **Event Bus** (`engine/event_bus.py`): Redis pub/sub integration, in-memory fallback, typed events (MarketData/AgentSignal/ExecutionCommand/RiskAlert), dead letter queue, correlation ID tracking

### Documentation — 7 New Architecture Documents
- **SYSTEM_DESIGN.md**: Full LangGraph state machine, dual-bus architecture, data pipeline topology, security architecture, pre-trade sequence flow
- **RESEARCH.md**: Benchmarking (NautilusTrader/Freqtrade/VectorBT/QuantConnect/Zipline), Alpha101/GTJA191 formulas, Kelly Criterion, VaR/CVaR, 125 project references
- **DECISION_LOG.md**: 7 documented decisions (terminal consolidation, execution optimization, agent coordination, runtime standardization, backtesting engine, memory architecture, risk management)
- **MERGE_PLAN.md**: All 23 repos with targets, git subtree merge script, dependency conflict resolution, de-duplication plan
- **MIGRATION_PLAN.md**: Step-by-step migration with classification, execution script, rollback plan, post-migration validation
- **ROADMAP.md**: 4-phase roadmap (Consolidation → Runtime → Agents → Production), weekly breakdowns, exit criteria
- **RISK_REGISTER.md**: 6 risk entries with vulnerability analysis, mitigation controls, residual risk, priority matrix

### Graph — Upgraded Trading Graph
- Replaced 6-node linear graph with 9-node conditional routing graph
- Asset-class-aware routing after Researcher node
- All domain paths converge at Strategist for unified decision synthesis

---

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
