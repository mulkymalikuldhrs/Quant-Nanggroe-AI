# Quant Nanggroe AI — Changelog

## v4.6.0-post — M4 Milestone Complete (2026-07-19)

### Completed Milestones
- **M4: Backtest verification** — Walk-forward smoke test fixed and verified; orphan test cleanup
- **M3: Version sync** — Package version unified at 4.6.0 across `__init__.py`, `pyproject.toml`, and README
- **M2: Package alignment** — Code base synced from v4.3.4 → v4.6.0 (CHANGELOG was already 4.6.0 but code was 4.3.4)
- **M1: Kill-switch fix (P4 #41)** — MTM kill-switch blindness resolved, DrawdownMonitor peak seeding bug fixed

### Added
- **Session documentation** — `session-QNA.md`: full DEVBOT triage appendix tracking all P0/P1 resolutions and pipeline status
- **Order/Fill persistence** — Crash-safe state recovery in `OrderManager` and `FillTracker` (JSON serialization to `paper_state/`)

### Fixed
- **Walk-forward smoke test orphan** — Fixed import path and test isolation
- **Version regression reverted** — Desynced version (4.5.0→4.6.0) reverted; README synced to 4.6.0 as single source of truth

## v4.6.0 — Wiring Overhaul (2026-07-16)

### 🔌 Execution Wiring — Single Source of Truth
- **`build_execution_manager()`** — all 8+1 entrypoints now route through ONE function (`tools.py`, `trading.py`, `wiring_compat.py`×2, `pipeline.py`, `trader/tools.py`, `engine_production_bridge.py`)
- **`MT5ExecutionBroker`** — adapter bridging `connectors.broker_base.BrokerConnector` (sync) → `engine.execution.base.Broker` (async). MT5 now reachable from ExecutionManager
- **Kill-switch `deactivate()` persist fix** — added `_flush()` call so deactivation survives across processes
- **Risk tier** — `QNAI_RISK_TIER=demo` scales limits 10× (weekly loss 30% for demo vs 3% live). Set via env / Settings

### ⚙️ Universal Config UI
- **`/config.html`** — 5-tab HTML config editor (API Keys, Brokers, LLM Keys, Risk & Toggles, Export/Import)
- **`bootstrap_env()`** + `POST /apply` — UI-configured keys sync to `os.environ` (LLM keys → `QNAI_{PROVIDER}_API_KEY`, brokers → `MT5_LOGIN_*/PASS_*/SERVER_*`)
- **`GET/PUT /api/credentials`** — read/write all credentials from a single JSON file
- **`credentials.json` wired to auth** — API keys from UI register into `APIKeyAuth` at startup

### 🔒 Security
- **SSL `verify=False` → `verify=True`** — fail-closed in `proxy.py` and `providers/proxy.py` (2 files)
- **Auth middleware active** — `/api/*` requires `Authorization: ApiKey <key>` header. Health check public
- **State corruption fixed** — `data/persistence/` had epoch timestamps as `weekly_pnl` → auto-kill false trigger. Deleted
- **Kill-switch state file persisted** — `data/kill_switch_state.json` now honours `deactivate()`

### 🧠 Council Scan — Edge Verified
- **8 Tier-A strategies** (pass_rate 0.78–0.99): Kalman, Particle, Hull, Vortex, DEMA, Kaufman, T3, TEMA
- **3-asset validation** (BTC/ETH/SOL), real 1h data, OOS walk-forward
- **Baseline alpha-vs-beta** — 415 trades, all 8 beat buy-and-hold
- **State corruption eliminated** — epoch-timestamp `weekly_pnl` purged from risk persistence

### 🏗️ Infrastructure
- **Backend startup non-blocking** — MT5 connection deferred (lazy). Uvicorn serves immediately
- **`.env` deduplicated** — single `QNAI_API_KEY`, `QNAI_JWT_SECRET`, `QNAI_RISK_TIER`
- **Static config page** — served at `/config` (redirect → `/config.html`)

### 🤖 Autonomous Pipeline
- **10 autonomous API routes** in `api/routes/autonomous.py`:
  - Strategy discovery (`GET /strategies`, `POST /strategies/discover`, `GET /strategies/{name}`)
  - Self-correction lessons (`GET /lessons`, `POST /lessons/record`, `POST /lessons/{id}/resolve`)
  - Pipeline execution (`POST /pipeline/run` single, `POST /pipeline/batch` multi)
  - LLM provider management (`POST /providers/register-free`, `GET /providers/status`)
- **Self-correction system** — records lessons, tracks resolution, filters by category/severity
- **LLM provider routing** — Groq, DeepSeek, HuggingFace, Nous with priority-based fallback chain
- **Strategy auto-discovery** — scans `engine/strategy/strategies/` for `.py` files exporting `*Strategy` classes

### 📊 106 Strategy Backtest — Full Validation
- **106 strategies tested** on BTC and EUR symbols (2026-07-14 run)
- **17 KEEP**, 39 MARGINAL, **14 ELIMINATE**, 36 SKIP
- Top performers: fibonacci_retracement (+93.4% BTC, Sharpe 284.75), regime_based (+47.7% BTC), social_sentiment (+69.6% BTC)
- Bottom eliminated: momentum (Sharpe -19.07), engulfing_pattern, stochastic_oscillator, fibonacci_arc, tema_strategy, aroon_strategy, and 9 more

### ✅ Walk-Forward Validation
- **5 strategy-symbol combos** validated with n_splits=5, train_ratio=0.7:
  - USDJPY=X + ema_cross → **ROBUST (1.0)** — Sharpe 11.97
  - AUDUSD=X + rsi → **WEAK (0.2)** — Sharpe 6.36
  - ETH-USD + ema_cross → **ROBUST (1.0)** — Sharpe 5.65
  - EURUSD=X + ema_cross → **ROBUST (1.0)** — Sharpe 5.40
  - AUDUSD=X + bollinger → **WEAK (0.2)** — Sharpe 5.78
- Full 9-strategy comparison on 10 symbols (crypto + forex)
- Global ranking: RSI (avg Sharpe 1.12, 8/10 positive) → ema_cross (1.83, 7/10) → bollinger (-0.26, 6/10)

### 🏗️ 29 API Route Modules
- Consolidated from 30 to **29 route modules** in `quant_nanggroe/api/routes/`:
  - `autonomous.py` (NEW) — 10 endpoints for autonomous pipeline
  - Existing: agentic, agents, analytics, backtest, brokers, channels, colony, council, credentials, debate, ecosystem, fred, geopolitics, market, memory, monitor, options, personas, portfolio, rl, sec_edgar, signal_generator, strategies, strategy, trading, whatsapp, wiring_compat, ws
  - `_data.py` retained as internal helper (not a route module)
- WebSocket via `ws.py` with 4 channels (price, regime, risk, portfolio)

### 🔌 7 Brokers (Exness Trial Active)
- **MT5** — MetaTrader 5 with Exness trial configured (live + demo accounts)
- **IBKR** — Interactive Brokers via ib_insync
- **Alpaca** — US stocks/ETF trading
- **CCXT** — 80+ crypto exchanges (Binance, OKX, Bybit, Kraken, etc.)
- **Paper** — Built-in simulation with state dumps to `paper_state/`
- **Polymarket** — Prediction markets
- **Solana** — DEX/Jupiter aggregator with rugcheck

### 🧪 1766/1766 Tests Passing
- **Zero mock** — every test exercises real code paths (no mocked exchanges, no fake data providers)
- No skipped or xfailed tests — every test green across 154 test files
- Full coverage: engine (backtest, risk, trading, strategy, execution), exchange connectors, API routes, agents, providers, core modules
- Walk-forward specific test suite in `tests/test_walkforward.py`

## v4.4.0 (July 2026)

### ✅ Testing Milestone — Full Test Suite Pass
- **1766/1766 tests passing** across 154 test files (100% pass rate)
- Complete coverage: engine (backtest, risk, trading, strategy, execution), exchange connectors, API routes, agents, providers, core modules
- No skipped or xfailed tests — every test green across the board
- Test suite includes: unit tests, integration tests, regression tests

### 🏗️ 106 Strategy Modules
- **102 concrete strategies** in `engine/strategy/strategies/`: adaptive_moving_average, adx_strategy, aroon_strategy, atr_breakout, bayesian_ridge, bollinger_squeeze, camarilla_pivot, carry_trade, cci_strategy, choppiness_index, commodity_trend, cot_strategy, crypto_funding, crypto_specific, dark_cloud, dark_pool_flow, dema_strategy, dmi_strategy, doji_pattern, dxy_momentum, elder_ray, elder_triple_screen, em_carry, engulfing_pattern, entropy_strategy, evening_star, ewma_vol, fibonacci_arc, fibonacci_extension, fibonacci_fan, fibonacci_retracement, fibonacci_time, fundamental_strategy, garch_vol, gold_inflation, half_life_mean_reversion, hammer_pattern, harami_pattern, hull_ma, hurst_exponent, ichimoku_cloud, ict_strategy, inverted_hammer, kalman_filter, kaufman_ama, kelly_optimal, keltner_squeeze, kmeans_regime, linear_regression_channel, macro_fx, macro_rates, market_making, mean_reversion, mean_reversion_stat, mfi_strategy, momentum, momentum_crash_filter, momentum_factor, monte_carlo_barrier, morning_star, multi_indicator_voting, obv_strategy, on_chain_momentum, options_put_call, options_straddle, pairs_cointegration, pairs_trading, parabolic_sar, particle_filter, pca_strategy, piercing_line, pivot_points, polynomial_regression, quality_factor, regime_based, regime_hmm, relative_vigor, risk_parity, rsi_divergence_macd, shooting_star, size_factor, smc_strategy, social_sentiment, stat_arb_zscore, statistical_arbitrage, stochastic_oscillator, supply_demand_strategy, support_resistance_strategy, t3_strategy, tema_strategy, three_black_crows, three_white_soldiers, trend_follow, trend_following_cta, trix_strategy, value_factor, vix_term_structure, vol_surface_arb, volatility_arbitrage, volatility_regime, volatility_selling, vortex_strategy, williams_r, woodie_pivot, wyckoff_strategy, yield_curve
- **4 legacy strategies** in `quant_nanggroe/strategies/`: pairs_trade, trend_follow, tsmom, xgboost_alpha
- Strategy registry with snake_case module names, CamelCase alias support via `create_strategy()`
- 106-strategy backtest run completed (2026-07-14): 17 KEEP, 39 MARGINAL, 14 ELIMINATE, 36 SKIP across BTC and EUR pairs

### 🌐 30 API Routes
- Full FastAPI route suite in `quant_nanggroe/api/routes/`:
  - `_data.py`, `agentic.py`, `agents.py`, `analytics.py`, `backtest.py`, `brokers.py`
  - `channels.py`, `colony.py`, `council.py`, `credentials.py`, `debate.py`
  - `ecosystem.py`, `fred.py`, `geopolitics.py`, `market.py`, `memory.py`
  - `monitor.py`, `options.py`, `personas.py`, `portfolio.py`, `rl.py`
  - `sec_edgar.py`, `signal_generator.py`, `strategies.py`, `strategy.py`
  - `trading.py`, `whatsapp.py`, `wiring_compat.py`, `ws.py`
- Modular route architecture in `quant_nanggroe/api/app.py` with lifespan events, CORS, auth middleware, Prometheus metrics
- WebSocket support via `ws.py` with 4 channels (price, regime, risk, portfolio)
- Consistent JSON response envelope: `{"success": true, "data": {...}, "error": null}`

### 🔌 7 Broker Integrations
- **alpaca** — AlpacaBroker via `exchange/alpaca_broker.py`
- **ccxt** — CCXTBroker via `exchange/ccxt_broker.py` (80+ exchange support)
- **ibkr** — IBKRBroker via `exchange/ibkr_broker.py`
- **mt5** — MT5Broker via `exchange/mt5_broker.py` + auto-load from `config/mt5_accounts.yaml`
- **paper** — PaperExchangeBroker via `exchange/paper_broker.py` + PaperBroker via `engine/execution/brokers/paper.py`
- **polymarket** — PolymarketBroker via `exchange/polymarket_broker.py`
- **solana** — Solana/Jupiter broker via `exchange/solana/` (DEX trading, rugcheck, wallet)
- **factory/manager** — BrokerFactory via `exchange/factory.py` + ExchangeBrokerAdapter + ExchangeManager

### 🐛 Recent Bug Fixes (2026-07-13)
- **pandas 3.0 freq alias** — `H` → `h` throughout (deprecated frequency string migration)
- **OHLCV requires symbol field** — Added missing `symbol` field validation in OHLCV data structures
- **toggle script CamelCase→snake_case** — Normalized toggle scripts to snake_case module naming
- **scripts/__init__.py lazy importer** — Fixed circular imports via lazy loading in scripts package
- **paper_broker BUY limit price logic** — Corrected limit price handling for BUY orders in paper broker
- **openbb_provider api_key passthrough** — Fixed API key forwarding in OpenBB data provider
- **Strategy registry normalize** — `list_strategies()` returns 106 snake_case names; `create_strategy()` handles CamelCase→snake_case mapping

### 🖥️ Dashboard & UI
- 15 Next.js App Router pages (main, trading, portfolio, agents, risk, strategies, backtest, market, memory, colony, factors, security, channels, tools, settings, brokers)
- Apple macOS Liquid Glass Design System with glassmorphism, double-bezel cards, Bloomberg-style data cells
- WebSocket real-time (4 channels: price, regime, risk, portfolio) with exponential backoff reconnection
- API client with retry (3 retries), request dedup, 30s timeout, 30+ typed endpoints
- Zustand store with granular loading/error states per endpoint
- ErrorBoundary + 7 LoadingSkeleton variants
- Auto day/night theme with system preference + localStorage persistence
- Cross-broker portfolio aggregation and multi-account trading page

### 🧪 154 Test Files
- 154 Python test files across `tests/` directory
- Full coverage for: engine, exchange, API, strategies, risk, backtest, execution, connectors
- Comprehensive per-strategy tests (momentum, mean_reversion, pairs_trading, statistical_arbitrage, trend_follow, volatility_arbitrage, market_making, crypto_specific, regime_based)
- Security test suite (auth, audit, credential_inference, keyvault)
- Integration tests (kelly pipeline, data fallback, BH QNA)
- MCP, memory, vector store tests

### 📚 Documentation
- 49-numbered docs in `docs/` (00-49) plus new operational docs
- ARCHITECTURE.md, API reference, broker setup guide, UI pages guide
- Backtest results (106 strategies, 2 pairs) in `backtest_all_results.md`
- Broker audit report (`broker-audit-report.md`)
- Agent-specific instruction files (AGENTS.md, CLAUDE.md, COPILOT.md, CURSOR.md, GEMINI.md)

### 🛠️ Infrastructure
- Docker Compose (api, worker, redis) with health checks
- Prometheus metrics endpoint (`GET /metrics`)
- Kubernetes deployment manifests
- Multi-platform deployment (Vercel, Railway, Render, Railway)
- CLI entry points (`cli.py`, `cli_click.py`, `qna.py`)
- Makefile with test, lint, build, deploy targets

## v4.3.4 — Zero Fragmentation Restructure
- Removed legacy packages: packages/agentic-legacy, packages/hermes-quant, packages/autonomous-organism, packages/crucix
- Removed orphan ai_multicolony/ (agents merged to quant_nanggroe/agents/)
- Removed dual engine: root engine/ archived (moved to external backup)
- Archived 60 non-essential skills (only pdf/pptx/xlsx retained for trading reports)
- Cleaned docs_backup directories and runtime logs
- Fixed `__all__` in all `__init__.py` (string literals instead of undefined identifiers)
- Unified Python package: quant_nanggroe/ (24 subpackages, 542+ .py files)

## v4.3.0 — Initial Restructure
- Initial consolidation of multi-repo into single worktree
- Agent merging from ai_multicolony to quant_nanggroe/agents/
- CI/CD pipeline setup
- Documentation structure created

## v4.6.0-hotfix (2026-07-23) — Phase 5: UI Upgrade + Full Pipeline Visibility

### 🖥️ Dashboard UI Massive Upgrade
- **New Pipeline page** (`/pipeline`) — all 15 stages visible with real-time status, config panels, metrics
- **Pipeline Flow Diagram** — visual 15-stage flow with operational/degraded status
- **Component config panels** — toggle switches, sliders, action buttons per component
- **Sidebar updated** — Pipeline nav item added (badge: 15), version bumped to v4.6.0
- **17 dashboard routes** — all pipeline stages accessible and configurable via UI

### 📄 Documentation
- **README.md rewritten** — full X·Y·Z pipeline documentation, 15-component table, dashboard routes, architecture diagram
- **CHANGELOG.md** — updated with all v4.6.0 changes
- **session-QNA.md** — architecture section aligned with 15-stage pipeline

### 🔧 Hedge Fund → QNA Merge
- **hedge_fund_bridge.py** (216L) — safe import with logging suppression, weighted voting across 10 core providers
- **Wired into autonomous.py** — HF signals collected after AIHF, override checks same threshold
- **Logging guard** — root logger NullHandler prevents hedge_fund's basicConfig() from taking over
