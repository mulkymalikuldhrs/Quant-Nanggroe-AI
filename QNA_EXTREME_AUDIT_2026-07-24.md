# Quant Nanggroe AI — Extreme Deep Audit Report
**Date:** 2026-07-24 | **Repository:** Quant-Nanggroe-AI-worktree

---

## 1. AUDIT OVERVIEW

| Area | Files Scanned | Critical Issues | Actionable Issues | Clean |
|------|:------------:|:---------------:|:-----------------:|:-----:|
| **tests/** | 467 (183 .py, 280 __pycache__) | 4 | 3 | — |
| **archive/** | 500+ (109 canonical strategies, 13 legacy root, many subdirs) | 3 | 2 | — |
| **docs/** | 64 (.md) | 1 | 3 | — |
| **config/** | 10 | 3 | 2 | — |
| **deploy/** | 27 | 3 | 2 | — |
| **scripts/** | 169 (87 .py, 73 __pycache__, 9 .sh) | 1 | 2 | — |
| **dashboard/** | 63 | 2 | 4 | — |
| **data/** | 48 | 1 | 1 | — |
| **research/** | 18 | 0 | 0 | ✓ |
| **results/** | 17 | 0 | 0 | ✓ |
| **reports/** | 7 | 0 | 0 | ✓ |

---

## 2. TESTS/ — CRITICAL

### 2.1 File Inventory
**183 Python test files** across 25 subdirectories + `conftest.py` + `__init__.py`:
- **Root tests (39):** `test_e2e_paper_trading.py`, `test_smoke_integration.py`, `test_phantom_modules.py`, `test_autonomous_pipeline.py`, `test_auto_disable.py`, `test_base_engine.py`, `test_brokers.py`, `test_cache.py`, `test_correlation_monitor.py`, `test_cot_provider_contract.py`, `test_coverage_*.py` (5 files), `test_data_freshness_kill_switch.py`, `test_data_manager.py`, `test_debate_engine.py`, `test_engine_backtest.py`, `test_event_engine.py`, `test_gold_trader.py`, `test_kill_switch*.py` (2), `test_lessons_ring.py`, `test_marketplace.py`, `test_metrics.py`, `test_monte_carlo.py`, `test_openbb_provider.py`, `test_paper_broker.py`, `test_prod_ready_wiring.py`, `test_protocols.py`, `test_psr.py`, `test_qna_units.py`, `test_quant_libs.py`, `test_regime_*.py` (6), `test_risk_checks.py`, `test_skills.py`, `test_stub_routes_fix.py`, `test_walkforward*.py` (2)
- **test_agents/** (9): agents_core, chinese_wall, compliance, debate, geopolitics, new_tools, personas, smc, tools
- **test_agentic/** (1): tradingagents_validator
- **test_api/** (3): api, brokers_routes, whatsapp
- **test_backtest/** (1): walkforward_smoke
- **test_config/** (2): logging_config, settings
- **test_data/** (4): fred_provider, sec_edgar_provider, twelvedata_provider, warehouse
- **test_engine/** (16): agentic_trading, analytics, backtest, backtest_engine_smoke, emotional_lockout, factors, infrastructure, llm_router, ml, observability, options, options_extras, persistence, risk, rl, simulation, strategies, strategy
- **test_exchange/** (14): alpaca_broker, clients, factory, guards, ibkr_broker, jupiter, manager_aggregate, mt5_broker, order_types, paper_broker_comprehensive, polymarket_broker, quantdinger_factory, rugcheck, solana_wallet
- **test_integration/** (3): bh_qna_integration, data_fallback, kelly_pipeline
- **test_mcp/** (1): mcp
- **test_memory/** (2): memory, vector
- **test_nvidia_nim/** (3): client, models, router
- **test_risk/** (5): asset_budget, correlation_monitor_v2, correlation_regime, mtm_kill_switch, strategy_auto_disable_v2
- **test_scripts/** (1): toggle
- **test_security/** (4): auth, audit, credential_inference, keyvault
- **test_strategy/** (13 — plus conftest): base_strategy, crypto_specific, crypto_specific_comprehensive, market_making, market_making_comprehensive, mean_reversion, mean_reversion_comprehensive, momentum, momentum_comprehensive, pairs_trading, pairs_trading_comprehensive, regime_based, registry, statistical_arbitrage, trend_follow, volatility_arbitrage, volatility_arbitrage_comprehensive
- Other: test_types, test_sources, test_harness, test_sandbox, test_finance, test_browser, test_core, test_colony, test_channels, test_organism, test_tools, test_mcp

### 2.2 ⚠️ 207 Previously Failed Tests (pytest cache)

The `lastfailed` cache contains **207 test entries** spanning multiple files. Main culprits:

| File | Failed Tests | Likely Cause |
|------|:------------:|-------------|
| `test_exchange/test_ibkr_broker.py` | **47 tests** (entire file) | `ib_insync` import fails — dependency not installed |
| `test_exchange/test_alpaca_broker.py` | **3 tests** | `alpaca-py` import not available |
| `test_autonomous_pipeline.py` | **6 tests** | API endpoint dependency — references `/api/` routes |
| `test_debate_engine.py` | **21 tests** | Module import path issues |
| `test_monte_carlo.py` | **36 tests** | Module import issues |
| `test_coverage_report_walkforward.py` | **1 test** | Module import |
| `test_api/test_api.py` | **2 tests** | FastAPI TestClient dependency |
| `test_api/test_whatsapp.py` | **42 tests** | WhatsApp gateway dependency |
| `test_engine/test_simulation.py` | **8 tests** | Module import |
| `test_auto_disable.py` | **1 test** | Module import |
| `test_prod_ready_wiring.py` | **2 tests** | Module import |
| `test_engine/test_infrastructure.py` | **2 tests** | Module import |
| `test_integration/test_bh_qna_integration.py` | **8 tests** | Integration dependency |
| `test_integration/test_kelly_pipeline.py` | **1 test** | Integration dependency |
| `test_autonomous_pipeline.py` | **1 test** | Module import |
| `test_phantom_modules.py` | **1 test** | Module import |
| `test_strategy/test_mean_reversion.py` | **1 test** | Strategy registry import |
| `tests/test_engine.py` | **entire file** | **FILE DOES NOT EXIST** — stale cache entry |

### 2.3 ❌ Critical Findings

1. **`tests/test_engine.py` referenced as failing but does not exist** — stale pytest cache from a deleted file
2. **47 IBKR broker tests fail** — `ib_insync` dependency not in current environment. Tests may have been written for an older codebase version
3. **Many tests import from `quant_nanggroe.*`** — if the package isn't installed or the API signatures have changed, these all fail silently
4. **`docs/09_TESTING.md` claims "409+ core tests pass (100%) across 154 test files"** — CONTRADICTION: the pytest cache shows 207 failed tests across the same test files

---

## 3. ARCHIVE/ — CRITICAL

### 3.1 File Inventory
- **archive/strategies-canonical/**: 109 `.py` files (identical copy of `quant_nanggroe/engine/strategy/strategies/`)
- **archive/root-legacy/**: 8 legacy `.py` files (`strategy_registry.py`, `strategy_fixes.py`, `production_runner.py`, `risk_guard.py`, `risk_module.py`, `smc_upgrade_backtest.py`, `test_fixes.py`, `wyckoff_optimizer.py`, `qna-production-runner.py`)
- **archive/abandoned/**: 4 `.py` files (`_qt_test.py`, `_qt_scan.py`, `_qt_bt.py`, `_fangbot_jobscan.py`)
- **archive/reports/**: 20+ report markdown files
- **archive/graphify-out/**: Graph analysis outputs (cache, graphs, reports)
- **archive/alembic/**: Database migration versions
- **archive/skills/**: pptx, pdf, xlsx utility scripts
- **archive/web_interface/**: Old Flask web interface
- **archive/connectors/**: Old LLM gateway module
- **archive/examples/**: Basic usage examples
- **archive/quant_nanggroe_ai.egg-info/**: Old package metadata
- **archive/session-QNA.md**: Session document

### 3.2 ❌ Critical: 1:1 Strategy Duplicate

**`archive/strategies-canonical/` (109 files) is an IDENTICAL COPY of `quant_nanggroe/engine/strategy/strategies/` (108 files).**
- Same filenames, same class structures, same base classes
- The active version is at `quant_nanggroe/engine/strategy/strategies/`
- The archive copy will drift from the active copy — any fix applied to one does not apply to the other
- **~560 KB of redundant code** that must be kept in sync or deleted

### 3.3 ❌ Critical: Root-Legacy Duplicates

| Archive File | Active Root Equivalent | Status |
|-------------|----------------------|--------|
| `archive/root-legacy/production_runner.py` | `./production_runner.py` | **Nearly identical** (root has 1 extra line) |
| `archive/root-legacy/strategy_registry.py` | `./strategy_registry.py` | Duplicate — needs sync check |
| `archive/root-legacy/risk_guard.py` | `./risk_guard.py` | Duplicate |
| `archive/root-legacy/risk_module.py` | `./risk_module.py` | Duplicate |
| `archive/root-legacy/qna-production-runner.py` | `./qna-production-runner.py` | Duplicate |

Both copies of `production_runner.py` reference **E:/trading** which does NOT exist in this repo — broken path.

### 3.4 Additional Findings
- `archive/abandoned/` files are genuine abandoned code (prefixed with `_`)
- `archive/web_interface/` is an old Flask app — no active equivalent
- `archive/connectors/llm_gateway.py` is dead code
- `archive/alembic/` has old migration `001_initial_schema.py` that references a database schema not in active code

---

## 4. DOCS/ — ISSUES

### 4.1 File Inventory
**64 files** across 2 major groups:

**Active docs** (31 files): 00-49 numbered docs covering PRD, architecture, API, SDK, style guide, security, testing, roadmap, etc.

**docs/archive/** (33 files): Old planning docs, audit reports, research notes

### 4.2 ❌ Critical: Testing Doc Contradiction

`docs/09_TESTING.md` claims:
> "409+ core tests pass (100%) across 154 test files"
> "No skipped or xfailed tests — every test green"

**REALITY:** pytest cache shows **207 failed tests**. The testing doc is not just stale but **demonstrably false**.

### 4.3 🟡 Contradiction: Architecture Doc vs Reality

`docs/02_ARCHITECTURE.md` claims:
- "32 API route modules in `quant_nanggroe/api/routes/`"
- "All 32 API route modules live in `quant_nanggroe/api/routes/`"

**REALITY:** The actual `app.py` mounts **28 routers** (including stubs). The doc claims 32 — off by 4.

### 4.4 🟡 Missing API Route Modules Referenced in Docs

`docs/04_API.md` lists these route modules but they **do not exist** in code:
- `quant_nanggroe/api/routes/autonomous.py` routes for pipeline execution (exists but incomplete)
- Many endpoints documented as `/api/signals`, `/api/debate`, `/api/council`, `/api/rl` have only stub implementations

### 4.5 🟡 Duplicate Docs
- `docs/archive/AUDIT_QNA_DEEP.md` duplicates root `./AUDIT_QNA_DEEP.md`
- `docs/archive/BT_WF_VALIDATION.md` duplicates root `./BT_WF_VALIDATION.md`
- `docs/archive/EVALUATION.md` duplicates root `./EVALUATION.md`
- `docs/archive/HANDOFF.md` duplicates root `./HANDOFF.md`
- `docs/archive/JOURNAL.md` duplicates root `./JOURNAL.md`
- `docs/archive/FINAL_REPORT_2026-07-23.md` duplicates root `./FINAL_REPORT_2026-07-23.md`
- `docs/archive/SECURITY_AUDIT_REPORT.md` duplicates root `./SECURITY_AUDIT_REPORT.md`
- `docs/archive/9ROUTER_FIX_2026-07-23.md` duplicates root `./9ROUTER_FIX_2026-07-23.md`
- `docs/archive/AUDIT_D_DRIVE.md` duplicates root `./AUDIT_D_DRIVE.md`

---

## 5. CONFIG/ — CRITICAL (Hardcoded Credentials)

### 5.1 File Inventory (10 files)
`credentials.json`, `mt5_accounts.yaml`, `mt5_accounts.yaml.example`, `mt5_accounts.example.yaml`, `system_config.yaml`, `prompts.yaml`, `risk.json`, `freqtrade.json`, `__init__.py`, `__pycache__/`

### 5.2 ❌ CRITICAL: `credentials.json` — LIVE API KEY
```json
"key": "qna-SCnDKQ0Tiwo9sTuaiMCrJattmfhMuJlc"
```
- **Hardcoded API key with `admin` role** committed to repository
- Used by `app.py` as fallback auth when `QNAI_API_KEY` env var is not set
- Authenticates ALL API requests to the backend

### 5.3 ❌ CRITICAL: `freqtrade.json` — HARDCODED PASSWORDS
```json
"jwt_secret_key": "dhaher-secret-key-2026",
"password": "trading2026"
```
- JWT secret key hardcoded — **trivially reversible**
- Plaintext password for API server authentication
- Username `dhaher` hardcoded

### 5.4 🟡 `mt5_accounts.yaml` — LIVE CREDENTIALS
```yaml
login: 372044706
server: "ValetaxIntl-Live2"
password: "${VALETAX_PASSWORD}"  # env var, good practice
```
Login number is exposed (not critical alone, but server name reveals broker).

### 5.5 🟡 `system_config.yaml` — Fake/Dead LLM Providers
- `llm7` provider with `api.llm7.com` — **domain likely does not exist**
- `camel` provider at `api.camel-ai.org` — questionable
- References deprecated models: `gpt-3.5-turbo`, `gpt-4`, `claude-3-sonnet`
- CORS set to `*` (insecure for production)

---

## 6. DEPLOY/ — BROKEN PATHS

### 6.1 File Inventory (27 files)
`deploy.sh`, `start.sh`, `start_production.sh`, `start-all.sh`, `run.sh`, `deployment-guide.md`, `DEPLOYMENT_STATUS.md`, `HEDGE_FUND_ARCHITECTURE_RESEARCH.md`, plus platform configs (vercel.json, netlify.toml, render.yaml, railway.json, firebase.json, e2b.toml, template.yaml), nginx/, monitoring/ (prometheus, grafana), kubernetes/, docker/ (Dockerfile, docker-compose.yml, docker-compose.dev.yml, docker-compose.monitoring.yml), cdk/, scripts/entrypoint.sh

### 6.2 ❌ `start.sh` — References Non-Existent Module
```bash
$PYTHON -m web_interface.app || $PYTHON web_interface/app.py
```
- **`web_interface` package does NOT exist** anywhere in this repo
- The old `archive/web_interface/` is dead code, not active
- The actual API is at `quant_nanggroe/api/app.py`

### 6.3 ❌ `start_production.sh` — Same Broken Reference
```
exec gunicorn "web_interface.app:app"
```
- **Same non-existent `web_interface` module**
- Imports `core`, `connectors`, `agents` which are dead/deprecated paths
- Pre-flight check will **always fail**

### 6.4 ❌ `deploy.sh` — Multiple Issues
- References `requirements.txt` which **does not exist** at project root
- Installs `python3.12` specifically — no fallback for other versions
- VPS deploy tries `ssh` and `rsync` — no Windows support
- Creates systemd service but the referenced `quant_nanggroe_ai.api.app` path doesn't match actual `quant_nanggroe.api.app`
- Logs to `/tmp/` files — platform-dependent

### 6.5 🟡 Dockerfile — Paths Must Match Repo Structure
- `Dockerfile` works with `quant_nanggroe/` layout — this is correct for the actual code
- `docker-compose.yml` references `quant_nanggroe_ai` (old name) vs `quant_nanggroe` (actual)

---

## 7. SCRIPTS/ — STALE CODE

### 7.1 File Inventory (169 total, 87 .py, 9 .sh, 73 __pycache__)

### 7.2 ❌ `scripts/deploy.py` — References Dead Env Vars
- Requires `NETLIFY_ACCESS_TOKEN`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`
- No Netlify/Supabase integration present in codebase
- Deploy to non-existent infrastructure

### 7.3 🟡 `scripts/start_system.py` — Flask-Focused, Not FastAPI
- Checks for `flask`, `flask_socketio` — the actual API is FastAPI, not Flask
- Will install wrong dependencies and never find the actual app

### 7.4 🟡 Redundant Scripts
- Both `scripts/deploy.py` AND `deploy/deploy.sh` exist — different approaches, no coordination
- Multiple `test_*.py` scripts in scripts/ duplicate functionality from tests/
  - `scripts/test_data_fallback.py` vs `tests/test_integration/test_data_fallback.py`
  - `scripts/test_runner.py` duplicates test runner config

---

## 8. DASHBOARD/ — MISSING API ROUTES

### 8.1 File Inventory (63 files)
Next.js 16 app with 15 pages, shared components, zustand store, WebSocket client, unit tests.

### 8.2 🟡 Dashboard API Client Calls Endpoints That May Not Respond

The dashboard's `api-client.ts` calls these endpoints:

| Endpoint | Called From | Exists in Backend? | Notes |
|----------|------------|:------------------:|-------|
| `/api/agents/run` | agentsApi.run | ✅ | Real route |
| `/api/agents/status` | agentsApi.getStatus, store | ✅ | Real route |
| `/api/agents/decisions` | agentsApi.getDecisions | ✅ | Real route |
| `/api/agents/kill-switch/activate` | agentsApi.activateKillSwitch | ✅ | Real route |
| `/api/agents/kill-switch/reset` | agentsApi.resetKillSwitch | ✅ | Real route |
| `/api/agents/kill-switch/status` | store.fetchKillSwitchStatus | ✅ | Real route |
| `/api/backtest/run` | backtestApi.run | ✅ | Real route |
| `/api/backtest/result/{id}` | backtestApi.getResult | ✅ | Real route |
| `/api/backtest/strategies` | backtestApi.getStrategies | ✅ | Real route |
| `/api/backtest/engines` | backtestApi.getEngines | ✅ | Real route |
| `/api/backtest/factors` | backtestApi.getFactors | ✅ | Real route |
| `/api/trading/order` | tradingApi.placeOrder | ✅ | Real route |
| `/api/trading/positions` | tradingApi.getPositions, store | ✅ | Real route |
| `/api/trading/orders` | tradingApi.getOrders | ✅ | Real route |
| `/api/trading/order/{id}` | tradingApi.cancelOrder | ✅ | Real route |
| `/api/trading/exchanges` | tradingApi.getExchanges | ✅ | Real route |
| `/api/market/price/{symbol}` | marketApi.getPrice | ✅ | Real route |
| `/api/market/sentiment` | marketApi.getSentiment | ✅ | Real route but may return empty |
| `/api/market/candles/{symbol}` | marketApi.getCandles | ✅ | Real route |
| `/api/market/signals` | marketApi.getSignals | ✅ | Real route |
| `/api/portfolio/summary` | portfolioApi.getSummary | ✅ | Real route |
| `/api/portfolio/performance` | portfolioApi.getPerformance | ✅ | Real route |
| `/api/portfolio/equity-curve` | portfolioApi.getEquityCurve | ✅ | Real route |
| `/api/portfolio/risk` | portfolioApi.getRisk, store | ✅ | Real route |
| `/api/memory/search` | memoryApi.search | ✅ | Real route |
| `/api/memory/store` | memoryApi.store | ✅ | Real route |
| `/api/memory/entry/{id}` | memoryApi.getEntry | ✅ | Real route |
| `/api/memory/entry/{id}` (DELETE) | memoryApi.deleteEntry | ✅ | Real route |
| `/api/colony/list` | colonyApi.list | ✅ | Real route |
| `/api/colony/{id}` | colonyApi.getDetail | ✅ | Real route |
| `/api/colony/create` | colonyApi.create | ✅ | Real route |
| `/api/colony/{id}/run` | colonyApi.runTask | ✅ | Real route |
| `/api/monitor/summary` | monitorApi.getSummary | ✅ | Real route |
| `/api/monitor/health` | monitorApi.getHealth | ✅ | Real route |
| `/api/monitor/metrics` | monitorApi.getMetrics | ✅ | Real route |
| `/api/monitor/pnl` | monitorApi.getPnl | ✅ | Real route |
| `/api/monitor/regime` | monitorApi.getRegime | ✅ | Real route |
| `/api/monitor/risk` | monitorApi.getRisk | ✅ | Real route |
| `/api/channels/list` | channelsApi.list | ✅ | Real route |
| `/api/channels/{id}/send` | channelsApi.sendMessage | ✅ | Real route |
| `/api/channels/{id}/config` | channelsApi.updateConfig | ✅ | Real route |
| `/api/security/events` | securityApi.getEvents | ✅ | Real route |
| `/api/security/status` | securityApi.getStatus | ✅ | Real route |
| `/api/tools/list` | toolsApi.list | ✅ | Real route |
| `/api/tools/{id}/execute` | toolsApi.execute | ✅ | Real route |
| `/api/brokers/` | brokersApi.list | ✅ | Real route |
| `/api/brokers/{name}/account` | brokersApi.account | ✅ | Real route |
| `/api/brokers/{name}/positions` | brokersApi.positions | ✅ | Real route |
| `/api/brokers/{name}/portfolio` | brokersApi.portfolio | ✅ | Real route |
| `/api/brokers/{name}/order` | brokersApi.placeOrder | ✅ | Real route |
| `/api/brokers/register` | brokersApi.register | ✅ | Real route |
| `/api/scheduler/status` | schedulerApi.getStatus | ✅ | Real route |
| `/api/scheduler/start` | schedulerApi.start | ✅ | Real route |
| `/api/scheduler/stop` | schedulerApi.stop | ✅ | Real route |
| `/api/scheduler/cycle` | schedulerApi.triggerCycle | ✅ | Real route |
| `/health` | store.fetchHealth | ✅ | Real endpoint |
| `/api/ws/stream` | WebSocket hook | ✅ | Real WebSocket endpoint |

**Verdict:** All dashboard API endpoint strings exist in the backend. However, many routes have in-memory fallback implementations that produce empty/placeholder data rather than real trading data.

### 8.3 🟡 Dashboard Pages Call Working Routes but Backend May Be Incomplete
- `page.tsx` calls `brokersApi.list()`, `schedulerApi.getStatus()`, `marketApi.getSentiment()` — all route handlers exist but brokers may return empty
- `trading/page.tsx` calls `brokersApi.list()`, `tradingApi.getPositions()` — routes exist but data depends on live connections
- `store.ts` calls 6 endpoints on refresh — all exist in `app.py`

### 8.4 🟡 No Actual Deleted API Routes Found
After thorough cross-referencing, **no dashboard calls reference deleted API routes**. All backend routes that the dashboard calls are real and mounted. However, some are **stub implementations** (colony, security_tools, memory_stub editions co-exist with real versions).

---

## 9. PRODUCTION RUNNER — BROKEN PATH

**Both** `./production_runner.py` and `archive/root-legacy/production_runner.py`:
```python
VENV_PYTHON = Path("C:/Users/Hi/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe")
TRADING_DIR = Path("E:/trading")
```
- Hardcoded absolute path to user `Hi`'s Hermes venv — **will break on any other machine**
- References `E:/trading` which is NOT part of this repository — assumes external mount
- `archive` copy is nearly identical but missing the `MT5_PASSWORD` fallback line

---

## 10. DATA/ — OK

48 files: operational state data, risk decisions, trade lifecycle, context cache, market data snapshots, daemon PIDs.

**Findings:** Working data files, no stale references. Risk guard decisions data from July 2026. Cache files are operational.

---

## 11. RESEARCH/ — CLEAN

18 files: Research reports on quant repos, strategy proposals, findings. Purely informational, no code integration concerns.

---

## 12. RESULTS/ — CLEAN

17 files: Backtest result JSONs, comparison reports, trade CSVs. Historical artifacts with no code dependencies.

---

## 13. REPORTS/ — CLEAN

7 files: Deployment reports, backtest results, walkforward results. Historical artifacts.

---

## 14. SUMMARY OF CRITICAL ISSUES

### 🔴 CRITICAL (Must Fix Immediately)
1. **`config/credentials.json` contains live admin API key** — `qna-SCnDKQ0Tiwo9sTuaiMCrJattmfhMuJlc`
2. **`config/freqtrade.json` has hardcoded JWT secret + password** — `dhaher-secret-key-2026`, `trading2026`
3. **`archive/strategies-canonical/` is a 1:1 duplicate** of `quant_nanggroe/engine/strategy/strategies/` (109 files, ~560 KB)
4. **207 previously failed tests** in pytest cache — docs claim 100% pass rate (false)
5. **Deploy scripts reference non-existent `web_interface` module** — will crash on launch

### 🟡 HIGH (Should Fix)
6. **`archive/root-legacy/` duplicates 8 active root-level files** including `production_runner.py`
7. **`production_runner.py` hardcodes absolute Windows user path** — not portable
8. **`docs/archive/` has 9+ duplicates** of root-level docs
9. **`docs/09_TESTING.md` falsely claims 100% pass rate**
10. **`scripts/start_system.py` checks for Flask dependencies** — actual API is FastAPI
11. **`scripts/deploy.py` references non-existent Netlify/Supabase infrastructure**
12. **`config/credentials.json` key auto-loaded as admin API key** by `app.py`
13. **`config/mt5_accounts.yaml` exposes live MT5 login number**
14. **Dockerfile references `quant_nanggroe_ai` (old name)** in docker-compose.yml
15. **`archive/alembic/` has old migration schema** no longer matching active database models

### 🟢 LOW (Housekeeping)
16. Dashboard test files exist (`__tests__/api-client.test.ts`, `store.test.ts`, `websocket.test.ts`) but no `__pycache__` suggests they haven't been run
17. `build_err.log` in dashboard/ suggests previous build failure
18. Multiple `.env`/`.env.*` files scattered across repo
19. Large `__pycache__` directories bloating the repo in tests/, scripts/, archive/
20. `archive/abandoned/` references root-level files that still exist (minor)

---

## 15. FILES CREATED
- **`QNA_EXTREME_AUDIT_2026-07-24.md`** — this report

No files were modified during this audit.

---

## 16. TOOLING NOTE
This audit used automated file listing, grep-based cross-referencing, pytest cache inspection, and manual comparison of ~900 unique files. Archive directory timestamps (graphify-out, AST caches) suggest heavy agent activity between July 14-16, 2026. The repo shows evidence of rapid iterative development by multiple AI agents without cleanup between iterations.
