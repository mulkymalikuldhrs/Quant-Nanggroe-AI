# Quant Nanggroe AI v6.2.1 — Autonomous Quantitative Hedge Fund

Autonomous quantitative hedge fund platform with multi-strategy execution, constitutional risk management (9-checkpoint gate), unified pipeline, hedge fund aggregator, self-evolving pipeline, **and real quantitative alpha engines**: DCC-GARCH cross-asset correlation, Causal Macro engine, COT institutional tracking, SMT divergence detection, Macro Surprise Index, and 3-stage Thesis Drift Guard. All modules use **real market data** — no mock, no simulation.

**Single entry point:** `python qna.py [mode]` — `unified` is now the default mode.

---

## Quick Start

```bash
# Set environment
cp .env.example .env
# Edit .env: set QNAI_JWT_SECRET, MT5_LOGIN, MT5_PASSWORD

# Boot API (port 8000)
PYTHONPATH="" .venv/Scripts/python -m uvicorn quant_nanggroe.api.app:app

# Or via unified launcher
python qna.py api

# Test suite (requires PYTHONPATH isolation)
PYTHONPATH="" .venv/Scripts/python -m pytest tests/ -v --tb=short
```

**⚠️ Critical:** Always run with `PYTHONPATH=""` to avoid leaking Hermes venv packages.
**Security:** Set `QNAI_SSL_VERIFY=0` only in isolated environments (never on production brokers). Credentials via env vars only — `.secrets-local/` deleted, `config/mt5_accounts.yaml` deprecated.

---

## CLI Modes

| Mode | Command | Description |
|------|---------|-------------|
| Unified | `python qna.py` (default) | Unified pipeline — auto mode-routing (hedge/crypto/agentic) |
| API | `python qna.py api` | FastAPI server (port 8000) |
| Daemon | `python qna.py daemon` | Background lifecycle daemon |
| Hedge | `python qna.py hedge` | Hedge Fund aggregator (multi-provider voting) |
| Status | `python qna.py status` | System health & status |
| Stop | `python qna.py stop` | Stop running daemon |

**⚠️ Deprecated:** `cli` and `web` modes will be removed in v7.0. Use `unified` (default) instead.

---

## Architecture

```
quant_nanggroe/                          (~700+ .py files, 130K+ lines)
├── pipeline/                            → UnifiedPipeline — auto mode-routing (hedge/crypto/agentic) 🆕 v6.0.0
│   ├── orchestrator.py                  → Pipeline orchestration & lifecycle
│   ├── data.py                          → Data ingestion & normalization
│   ├── signal.py                        → Signal generation & aggregation
│   ├── execution.py                     → Order execution pipeline
│   ├── macro_context.py                 → 🆕 Rewritten: orphan imports fixed, 5-stage stacked filters
│   └── factory.py                       → Pipeline factory with auto mode detection
├── api/                                 → FastAPI server (181 endpoints)
├── engine/                              → Core trading engine (22+ modules)
│   ├── causal/                          → 🆕 Causal macro engine suite (v6.1.0)
│   │   ├── causal_bias.py               → Causal Knowledge Graph bias computation
│   │   ├── macro_surprise.py            → Macro Surprise Index (FRED)
│   │   ├── cot_tracker.py               → Institutional COT positioning tracker
│   │   ├── smt_divergence.py            → SMT divergence (cointegration breakdown)
│   │   └── thesis_drift_guard.py        → 3-stage thesis drift circuit breaker
│   ├── causal/context.py                → 🆕 CausalContext dataclass (v6.2.0) — replaces env-var wiring
│   ├── risk/                            → Constitutional risk + 🆕 DCC-GARCH
│   │   ├── dcc_garch.py                 → 🆕 DCC-GARCH dynamic correlation (R rmgarch wrapper)
│   │   ├── kill_switch.py               → KillSwitch with C5 cross-process shared state
│   │   ├── checks.py                    → ConstitutionalRiskGuard (= RiskCheckGate alias)
│   │   ├── manager.py                   → RiskManager orchestration
│   │   └── constants.py                 → Single source of truth for all risk limits
│   ├── strategies/                      → CANONICAL — 79+ registered strategies (@StrategyRegistry.register)
│   │   └── registry.py                  → StrategyRegistry auto-discovery
│   ├── strategy/strategies/             → LEGACY BRIDGE — backward-compat shim only
│   ├── backtest/                        → Walk-forward, Monte Carlo, multi-market
│   ├── execution/                       → Order routing, Builder, RiskManager, Almgren-Chriss
│   ├── agentic/                         → Autonomous agent lifecycle (LangGraph)
│   ├── portfolio/                       → Kelly sizing, risk parity
│   └── models/                          → ML models and inference
├── hedge_fund/                          → Executive-level multi-provider aggregator
│   ├── hedge_fund.py                    → Hedge fund voting engine (backward-compat shim)
│   ├── signals/
│   │   ├── core.py                      → 10 core providers 🆕 with SYMBOL_TO_FUTURES + apply_causal_bias()
│   │   ├── qna_strategies.py            → 200+ evolved providers 🆕 with causal bias filtering
│   │   └── aggregator.py                → Signal aggregation + DXY context boost
│   ├── risk/                            → gate.py, guard.py (fail-closed)
│   ├── execution/                       → orders.py (trail_sl, execute)
│   └── portfolio/                       → main.py (run_once)
├── signals/                             → TradingSignal model + SignalRepository
├── security/                            → Auth (JWT, API key), credential manager
├── agents/                              → 9+ specialized agent modules
├── dashboard/                           → Next.js 18-page UI
├── tests/                               → 🆕 test_dcc_garch.py (47 tests, comprehensive)
└── archive/                             → Clean archive of legacy/duplicate code
```

### Strategy Pipeline

The canonical strategy pipeline lives in `quant_nanggroe/engine/strategies/` with **79+ registered strategies** via `@StrategyRegistry.register` decorator. Key strategies include:

| Registered Name | File | Description |
|-----------------|------|-------------|
| smc | `smc_strategy.py` | Smart Money Concepts — OB, FVG, liquidity sweep, BOS/CHOCH |
| wyckoff | `wyckoff.py` | Spring/upthrust, volume ratio, SoS/SoW |
| msnr | `msnr.py` | Multi-timeframe confluence |
| mean_rev | `mean_reversion.py` | OU process, half-life, Bollinger, z-score |
| trend_follow | `trend_follow_strategy.py` | Trend following |
| dhaher_system | `dhaher_system.py` | Meta-strategy / Dhaher System |
| ict | `ict_strategy.py` | ICT concepts |
| market_profile | `market_profile.py` | Market Profile |
| tsmom | `tsmom_strategy.py` | Time-Series Momentum |
| +70+ more .py files | | (See STRATEGY_CATALOG.md for full list) |

**Total: 79+ registered strategies** across canonical `engine/strategies/` (including signal adapters, wrappers, experimental modules). Legacy path had 109 frozen strategies — **all removed in v6.2.1** (only empty compat shim remains).

**Legacy path** `quant_nanggroe/engine/strategy/strategies/` is a backward-compat shim only (empty directory with re-export `__init__.py`).

### Kill Switch C5 — Cross-Process Shared State

The kill switch implements a **C5 convergence model** where every KillSwitch() instance — across any worker, daemon, or production bridge — reads/writes a single shared state file (`QNA_KILL_SWITCH_STATE_FILE` env var). This collapses split-brain scenarios where per-process in-memory kill switches disagree.

- **Three activation levels:** NONE (✓ trade) → MONITOR (log only) → ACTIVE (VETO all)
- **Path-A:** In-memory state via `_auto_check_kill_switch()`
- **Path-B:** Real MT5 PnL via `history_deals_get()` → `_sync_realized_pnl()`
- **C5 convergence:** File-backed state prevents split-brain across uvicorn workers
- **Fail-closed:** Unreadable/corrupt state file ⇒ assumed ACTIVE (halt)
- **Triggers:** daily, weekly, volatility, drawdown auto-activation

---

## Key Features

### Constitutional Risk Management (HARDCODED — no override)

| Limit | Value | Enforcement |
|-------|-------|-------------|
| Per trade risk | 0.5% | Position sizing (Kelly + VaR) |
| Daily loss | 1.0% | 9-checkpoint gate (Check 3) |
| Weekly loss | 3.0% | 9-checkpoint gate (Check 4) |
| Max drawdown | 15% | KillSwitch auto-activation |
| Min risk:reward | 1:2 | Trade proposal rejection |
| Max leverage | 3x | Margin monitor |
| Max trades/day | 5 | Rate limiter |

### 🆕 DCC-GARCH Dynamic Cross-Asset Correlation

- **Python `arch` package** — univariate GARCH(1,1) volatility forecasts
- **Dynamic Conditional Correlation** — time-varying correlation matrix, not static
- **VRK Kelly weights** — volatility-adjusted risk parity portfolio weights with safety caps
- **Auto-fit** — `_update_dcc_garch()` runs every N cycles in `live_engine.py` with market data
- **Env vars exposed** — `QNA_DCC_MEAN_CORR`, `QNA_DCC_MEAN_VOL_PCT`, `QNA_DCC_N_ASSETS`
- **Pre-filter integration** — qna.py's `evaluate_full_pipeline()` passes returns data for live DCC fitting
- **Tests** — 47 unit tests covering FX data, fit edge cases, VRK weight stability (see `quant_nanggroe/tests/test_dcc_garch.py`)

### 🆕 Causal Macro Engine Suite

| Module | Function | Data Source |
|--------|----------|------------|
| **Causal Bias** | Event → asset bias mapping (-1.0 to +1.0) | Event-driven, env vars |
| **Macro Surprise Index** | Standardized surprise deviation (MSI) | FRED API (`fredapi`) |
| **COT Tracker** | Institutional positioning percentile | `cot_reports` (CFTC) |
| **SMT Divergence** | Cointegration breakdown detection | Engle-Granger test on real prices |
| **Thesis Drift Guard** | 3-stage circuit breaker | Live macro context |
| **CME Price Provider** | Futures/spot prices + returns cache | EnginePriceProvider + yfinance |
| **DCCState Singleton** | Shared DCC-GARCH state across modules | Ring buffer, cached correlation |

### 🆕 Causal Engine API (15+ Endpoints)

All causal engine data exposed via FastAPI at `/api/causal/*`:
- `/biases` — Event-driven asset bias scores
- `/weather` — Macro weather classification
- `/dcc/status` — DCC-GARCH correlation matrix + volatilities
- `/dcc/correlation` — Full correlation matrix
- `/dcc/pair` — Pair correlation lookup
- `/dcc/refresh` — Force DCC re-fit with latest data
- `/cme/prices` — Live CME futures prices
- `/cme/returns` — Log returns data
- `/cot` — COT institutional positioning
- `/msi` — Macro Surprise Index (FRED)
- `/smt`, `/smt/pairs` — SMT divergence detection
- `/thesis` — Thesis drift guard status
- `/pipeline` — Full 4-phase pipeline evaluation
- `/status` — Aggregated engine status

### Otto Proxy API (`/api/otto/*`)
Pass‑through proxy to the local Otto MCP service (port 8765). Supports all HTTP methods; queries and bodies are forwarded unchanged.

### 🆕 Unified Dashboard

Single HTML dashboard with the **Tactical Gold palette** (`#1A1D20`, `#0F172A`, `#D9A441`, `#00D1C7`):
- Real-time DCC correlation matrix heatmap
- Causal bias interactive selector (6 event types)
- COT positioning panel
- SMT divergence alerts per pair
- Thesis drift guard status
- CME price feed
- 30-second auto-refresh
- Served at `http://localhost:8000/dashboard.html`

### 🔥 OrderFlowMap (Shared Component)

Bookmap-style visualization for crypto/forex instruments. Shared component with SahamEngineAI.
- Source: `repositories/shared/orderflow-map/OrderFlowMap.tsx`
- Wrapper: `dashboard/src/components/OrderFlowMap.tsx` (BTC-USD defaults, no badge)
- Features: Heatmap, trade bubbles, DOM ladder, CVD, VWAP, keyboard shortcuts
- Page: `/orderflow` with instrument picker (click-outside-to-close)

### 📊 TradeBobby Panels (Daemon API Connected)

- **MacroPulsePanel** — VIX, DXY, Gold, Oil, 10Y, SPX, NAS + regime detection
- **CryptoPulsePanel** — BTC, ETH, SOL, BNB prices + funding rates + Fear & Greed
- **COTPanel** — CFTC Commitment of Traders positioning data
- **AgentBriefPanel** — News sentiment scan with headlines

All panels fetch from Next.js API routes (`/api/macro-pulse`, `/api/crypto-pulse`, `/api/cot-data`, `/api/news-scan`) which read daemon JSON output files.

### 🐍 Python Daemons (`quant_nanggroe/daemons/`)

| Daemon | Data Source | Output File | Interval |
|--------|-----------|-------------|----------|
| `macro_pulse.py` | Yahoo Finance | `data/macro/macro_pulse.json` | 5 min |
| `crypto_pulse.py` | CoinGecko + Binance | `data/crypto/crypto_pulse.json` | 5 min |
| `cot_fetcher.py` | CFTC | `data/cot/cot_data.json` | Weekly |
| `news_scanner.py` | Google News RSS | `data/news/news_scan.json` | 30 min |

### 🆕 Causal Bias → Signal Filter Wiring

All **10 core hedge fund providers** (signal_sma, signal_ema, signal_macd, etc.) and **200+ evolved providers** (`qna_strategies.py`) now apply 3-level causal bias adjustment:
- **BOOST** (+0.15 confidence) — bias aligned with signal
- **REDUCE** (-0.15 confidence) — bias misaligned with signal
- **BLOCK** (confidence → 0) — bias strongly opposes signal

Pipeline `macro_context.py` provides a safety-net filter for non-HF signals via `QNA_CAUSAL_BIAS_*` env vars.

### Hedge Fund Aggregator

The `hedge_fund/` subpackage provides executive-level multi-provider signal aggregation with voting, allowing strategies from multiple sources to converge on a unified trading decision.

### Dashboard (Next.js 18 Pages)

- Real-time WebSocket streaming via `@/lib/websocket`
- API client with retry (3 attempts), backoff, dedup
- 18 route pages: trading, risk, portfolio, backtest, agents, brokers, strategies, etc.
- Next.js API proxy rewrite for same-origin requests
- Glassmorphism design system (Apple macOS Liquid Glass × Bloomberg Terminal)

---

## Audit Status
- **Last Full Audit:** 2026-07-27 (Round 3 — P0 Deep Clean Complete)
- **Round 1:** 56 findings — **ALL FIXED**
- **Round 2:** 55+ findings — **95%+ FIXED**
- **Round 3 (v6.2.0):** 8 P0 fixes — **ALL RESOLVED**
  - P0 Security: `.secrets-local/` deleted, `CERT_NONE` → `QNAI_SSL_VERIFY` env guard across 10 files
  - P0 Backtest: `engine.py:183` NameError fixed, `portfolio.py:196` return None → return pos
  - P0 Architecture: `__getattr__` removed from `engine/__init__.py`, stale `standalone` removed
  - P0 PnL: Unit convention unified to fractions (0-1), `/100.0` removed from RiskManager
   - P0 Naming: `StrategyRegistry` → `WalkForwardRegistry` in `engine/strategy/registry.py` (deleted in v6.2.1 — was dead code)
  - P0 Evolver: `_real_backtest()` uses `WalkForwardAnalyzer.analyze_strategy()` with real strategy instantiation
  - P0 Execution: `ExecutionManager.set_broker_handle()` public method added, `builder.py` uses public API
  - P0 Causal: wired via `CausalContext` dataclass instead of env vars
- **Score:** 87 → 94/100
- **Status:** All CRITICAL findings addressed. See CHANGELOG.md for details.
- **Remaining:** Triple registry consolidation, Signal type dedup (require architectural decisions)

---

## Current Gaps & Known Issues

| Gap | Severity | Status |
|-----|----------|--------|
| PYTHONPATH leak on boot (Hermes venv contamination) | HIGH | Mitigated (env fix documented) |
| Test suite requires environment setup | MEDIUM | 1 skip remaining (ccxt env) — core tests pass |
| 2 strategy hierarchies (canonical + legacy shim) | MEDIUM | Legacy empty, bridge in place (triple registry consolidation needed) |
| No cron-to-live-trade wiring on this host | LOW | Requires MT5 + VPS |
| Dashboard Next.js build not verified on Windows | LOW | Vercel builds in CI |
| Triple registry architecture | MEDIUM | Architectural decision needed (3 registries don't communicate) |
| 5 Signal type variants | MEDIUM | Architectural decision needed (Signal dedup) |
| `.secrets-local/` deleted, `master.key`/`salt.key` deleted | FIXED v6.2.0 | P0 Security — all secrets via env vars now |
| `QNAI_SSL_VERIFY` env guard across 10 files | FIXED v6.2.0 | Replaced `ssl.CERT_NONE` with env-var-gated SSL verification |
| `engine.py:183` NameError, `portfolio.py:196` return None | FIXED v6.2.0 | P0 Backtest — both bugs resolved |
| `__getattr__` removed from `engine/__init__.py` | FIXED v6.2.0 | P0 Architecture — phantom imports eliminated |
| Stale `standalone.py` deleted | FIXED v6.2.0 | P0 Architecture — no more dead entry point |
| PnL unit convention unified (fractions 0-1) | FIXED v6.2.0 | P0 PnL — `/100.0` removed from RiskManager |
| `StrategyRegistry` → `WalkForwardRegistry` renamed in `engine/strategy/registry.py` | FIXED v6.2.0 | P0 Naming (file deleted v6.2.1 — was dead code) |
| Evolver uses real backtest (not mock) | FIXED v6.2.0 | P0 Evolver — `WalkForwardAnalyzer.analyze_strategy()` with real instantiation |
| `set_broker_handle()` public method added | FIXED v6.2.0 | P0 Execution — builder.py now uses public API |
| Causal engine wired via CausalContext dataclass | FIXED v6.2.0 | P0 Causal — replaces brittle env-var wiring |
| Phantom `from strategy_registry import` | FIXED v6.1.0 | All 5 files fixed |

---

## Project Status

| Domain | Status |
|--------|--------|
| Architecture Health | 9.7/10 — `__getattr__` removed, `standalone` deleted, P0 architecture clean |
| Risk System | Fail-closed, C5 kill switch, 9-checkpoint gate, unified constants, **DCC-GARCH + DCCState** |
| Risk PnL Units | Fractions (0-1) unified — `/100.0` removed from RiskManager |
| Causal Macro Engine | **Bias + MSI + COT + SMT + Thesis + CME Provider** — all production-grade |
| Causal Context | **CausalContext dataclass** — replaces env-var wiring |
| Dashboard | **Unified HTML dashboard** with Tactical Gold palette, auto-refresh |
| Strategies | 79+ registered via StrategyRegistry (legacy bridge — empty shim, dead files removed) |
| Strategy Evolver | **Real backtest** via `WalkForwardAnalyzer.analyze_strategy()` — no more mock |
| Hedge Fund | Multi-provider aggregator + **causal bias filtering** on all providers |
| UnifiedPipeline | v6.2.0 — auto mode-routing + macro_context.py orphan fix |
| DCC-GARCH Tests | **47 tests** — FX correlation, fit edge cases, VRK weight stability |
| Pipeline Orphans | **All fixed** — macro_context.py imports real modules |
| Documentation | 50+ docs files + **full v6.2.1 sync** |
| Test Suite | Core tests pass + DCC unit tests + causal engine integration |
| Security | `QNAI_SSL_VERIFY` env guard, `.secrets-local/` deleted, env-var credentials only |
| Issues Resolved | 60+ (99%+) |

---

## Ecosystem

```
Dhaher Labs Ecosystem
├── Quant-Nanggroe-AI    🟢 v6.2.1    ← YOU ARE HERE
├── Autonomous-Organism  🟢 v5.4.1    Live on Vercel
├── BlackHornet          🟢            110+ agents, Codeberg sync
├── Seulanga-RAG         🟢            Merged GitLab
├── BioWallet            🟢            Synced Codeberg
├── JeumpaLLM            🟢            Merged 2+9 commits
├── HeadlessX            🟢 v2.1.2    1,989 stars
└── GStack               🟢            122,860 stars, 23 AI tools
```

---

## Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| Package Manager | `uv` (not pip, not poetry) |
| API Server | FastAPI (181 endpoints) |
| Legacy UI | Flask |
| Dashboard | Next.js 16 + React 19 + Recharts + Zustand |
| Broker | MetaTrader5 (via `ExecutionManager.set_broker_handle()`) |
| Crypto | CCXT |
| Risk Engine | ConstitutionalRiskGuard, KillSwitch C5, RiskManager, unified constants |
| UnifiedPipeline | `quant_nanggroe/pipeline/` — auto mode-routing (hedge/crypto/agentic) |
| Exchange REST | 10 clients lazy-wired via `ExchangeFactory.create_rest_client()` |
| Telegram | Config-validated (`validate_telegram_config` / `ensure_telegram`) |
| Testing | pytest (107/108 pass — 1 ccxt skip) |
| Credentials | MT5_LOGIN / MT5_PASSWORD env vars (NOT hardcoded, no plaintext YAML) |
| SSL | `QNAI_SSL_VERIFY` env guard (CERT_NONE only when explicitly set) |
| Encryption | `QNAI_ENCRYPTION_KEY` for credentials at rest |

---

## Deployment

- **Canonical source:** `D:\repositories\Quant-Nanggroe-AI-worktree\`
- **Deployment copy:** `E:\trading\quant_nanggroe\`
- **Credentials:** MT5_LOGIN, MT5_PASSWORD env vars (not hardcoded, no plaintext YAML)
- **SSL:** `QNAI_SSL_VERIFY` env var (default 1, set 0 only in isolated environments)
- **Encryption:** `QNAI_ENCRYPTION_KEY` for credentials at rest
- **Kill switch state:** Shared file at `QNA_KILL_SWITCH_STATE_FILE` (or `data/kill_switch_state.json`)
- **Causal context:** `CausalContext` dataclass (not env vars) — see `engine/causal/context.py`

---

## License & Credits

Built by Dhaher Labs. Architecture inspired by institutional quant funds, SMC/ICT methodology, and constitutional AI risk management.

*"Wakafa billahi syahidan" — Gas dengan penuh amarah dan presisi.*
