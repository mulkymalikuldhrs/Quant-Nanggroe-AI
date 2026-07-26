# Quant Nanggroe AI v6.1.0 — Autonomous Quantitative Hedge Fund

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
│   ├── macro_context.py                 → Macro context provider (causal bias, weather, COT) 🆕 v6.1.0
│   └── factory.py                       → Pipeline factory with auto mode detection
├── api/                                 → FastAPI server (181 endpoints)
├── engine/                              → Core trading engine (22+ modules)
│   ├── causal/                          → 🆕 Causal macro engine suite (v6.1.0)
│   │   ├── causal_bias.py               → Causal Knowledge Graph bias computation
│   │   ├── macro_surprise.py            → Macro Surprise Index (FRED)
│   │   ├── cot_tracker.py               → Institutional COT positioning tracker
│   │   ├── smt_divergence.py            → SMT divergence (cointegration breakdown)
│   │   └── thesis_drift_guard.py        → 3-stage thesis drift circuit breaker
│   ├── risk/                            → Constitutional risk + 🆕 DCC-GARCH
│   │   ├── dcc_garch.py                 → 🆕 DCC-GARCH dynamic correlation (R rmgarch wrapper)
│   │   ├── kill_switch.py               → KillSwitch with C5 cross-process shared state
│   │   ├── checks.py                    → ConstitutionalRiskGuard (= RiskCheckGate alias)
│   │   ├── manager.py                   → RiskManager orchestration
│   │   └── constants.py                 → Single source of truth for all risk limits
│   ├── strategies/                      → CANONICAL — 79+ registered strategies (@register decorator)
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

**Total: 79+ registered strategies** across canonical `engine/strategies/` (including signal adapters, wrappers, experimental modules). Legacy path has 139 frozen strategies in backward-compat shim.

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
- **Last Full Audit:** 2026-07-26
- **Findings:** 56 (6 P0, 9 P1, 8 P2, 10+ P3, 12 P4, 8 P5, 7 P6)
- **Status:** All findings addressed. See CHANGELOG.md for details.

---

## Current Gaps & Known Issues

| Gap | Severity | Status |
|-----|----------|--------|
| PYTHONPATH leak on boot (Hermes venv contamination) | HIGH | Mitigated (env fix documented) |
| Test suite requires environment setup | MEDIUM | 1 skip remaining (ccxt env) — core tests pass |
| 2 strategy hierarchies (canonical + legacy shim) | MEDIUM | Legacy empty, bridge in place |
| No cron-to-live-trade wiring on this host | LOW | Requires MT5 + VPS |
| Dashboard Next.js build not verified on Windows | LOW | Vercel builds in CI |
| Paper broker still DEFAULT execution path | MEDIUM | Inverting: MT5 live = default, paper = opt-in (v6.1.0) |

---

## Project Status

| Domain | Status |
|--------|--------|
| Architecture Health | 9/10 — Clean single entry point + unified pipeline |
| Risk System | Fail-closed, C5 kill switch, 9-checkpoint gate, unified constants, **DCC-GARCH** 🆕 |
| Causal Macro Engine | 🆕 **Causal bias + COT + MSI + SMT + Thesis Drift** — all production-grade |
| Strategies | 79+ registered via StrategyRegistry + legacy bridge |
| Hedge Fund | Multi-provider aggregator + **causal bias filtering** on all providers 🆕 |
| UnifiedPipeline | v6.0.0 — auto mode-routing (hedge/crypto/agentic) + **macro_context.py** 🆕 |
| DCC-GARCH Tests | **47 tests** 🆕 — FX correlation, fit edge cases, VRK weight stability |
| Documentation | 50+ docs files |
| Test Suite | Core tests pass + DCC unit tests |
| Security | Secrets via env vars, Telegram config validated |
| Issues Resolved | 50+ (98%+) |

---

## Ecosystem

```
Dhaher Labs Ecosystem
├── Quant-Nanggroe-AI    🟢 v6.0.0    ← YOU ARE HERE
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
| Broker | MetaTrader5 (via set_broker_handle()) |
| Crypto | CCXT |
| Risk Engine | ConstitutionalRiskGuard, KillSwitch C5, RiskManager, unified constants |
| UnifiedPipeline | `quant_nanggroe/pipeline/` — auto mode-routing (hedge/crypto/agentic) |
| Exchange REST | 10 clients lazy-wired via `ExchangeFactory.create_rest_client()` |
| Telegram | Config-validated (`validate_telegram_config` / `ensure_telegram`) |
| Testing | pytest (107/108 pass — 1 ccxt skip) |
| Credentials | MT5_LOGIN / MT5_PASSWORD env vars (NOT hardcoded) |

---

## Deployment

- **Canonical source:** `D:\repositories\Quant-Nanggroe-AI-worktree\`
- **Deployment copy:** `E:\trading\quant_nanggroe\`
- **Credentials:** MT5_LOGIN, MT5_PASSWORD env vars (not hardcoded)
- **Kill switch state:** Shared file at `QNA_KILL_SWITCH_STATE_FILE` (or `data/kill_switch_state.json`)

---

## License & Credits

Built by Dhaher Labs. Architecture inspired by institutional quant funds, SMC/ICT methodology, and constitutional AI risk management.

*"Wakafa billahi syahidan" — Gas dengan penuh amarah dan presisi.*
