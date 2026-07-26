# Quant Nanggroe AI v6.1.0 — Architecture

## Overview

Quant Nanggroe AI (QNA) is an **institutional-grade autonomous quantitative hedge fund** platform. Multi-strategy execution, constitutional risk management, cross-process kill switch (C5), unified pipeline, **real quantitative alpha engines** (DCC-GARCH, Causal Macro, COT, MSI, SMT), and self-evolving pipeline — all accessible via a single entry point.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      QNA v6.1.0 — Architecture                             │
│              Autonomous Quantitative Hedge Fund                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ENTRY: qna.py (single — unified mode default)                              │
│    ├── unified → UnifiedPipeline (auto mode-routing: hedge/crypto/agent)    │
│    ├── api     → FastAPI server (:8000) + auto-open browser                  │
│    ├── daemon  → Background lifecycle daemon                                 │
│    ├── hedge   → Hedge Fund aggregator (multi-provider voting)              │
│    ├── status  → Health check                                                │
│    └── stop    → Stop daemon                                                 │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │                        QUANT_NANGNGROE/                              │    │
│  │                                                                      │    │
│  │  ┌────────────────────────┐  ┌────────────────┐  ┌────────────────┐  │    │
│  │  │ CAUSAL ENGINE 🆕       │  │ ENGINE         │  │ RISK (unified) │  │    │
│  │  │  Causal Bias           │  │  22+ modules   │  │  constants.py  │  │    │
│  │  │  Macro Surprise (FRED) │  │  Strategies    │  │  KillSwitch C5 │  │    │
│  │  │  COT Tracker (CFTC)   │  │  Self-Aware    │  │  9-checkpoint  │  │    │
│  │  │  SMT Divergence       │  │  Self-Evolve   │  │  DCC-GARCH 🆕  │  │    │
│  │  │  Thesis Drift Guard   │  └────────┬────────┘  └────────┬───────┘  │    │
│  │  └────────────────────────┘          │                    │          │    │
│  │                                      ▼                    ▼          │    │
│  │                               ┌──────────────────────────────┐       │    │
│  │                               │        PIPELINE 🆕 v6.0       │       │    │
│  │                               │  orchestrator / data / signal  │       │    │
│  │                               │  execution / macro_context 🆕  │       │    │
│  │                               │  (causal bias env var filter)  │       │    │
│  │                               └──────────────┬───────────────┘       │    │
│  │                                              │                        │    │
│  │  ┌──────────────────┐  ┌─────────────────────▼────┐  ┌────────────┐  │    │
│  │  │ HEDGE_FUND (v6)  │  │ DCC AUTO-FIT + THESIS    │  │ EXCHANGE   │  │    │
│  │  │  core.py (10     │  │ DRIFT GUARD              │  │ 10 REST    │  │    │
│  │  │  providers +     │  │ live_engine.py execute_  │  │ clients    │  │    │
│  │  │  causal bias)    │  │ cycle() → update_corr()  │  │ lazy-wired │  │    │
│  │  │  qna_strategies  │  │ → thesis_drift check     │  │ ccxt proxy │  │    │
│  │  │  (200+ evolved)  │  └──────────────────────────┘  └────────────┘  │    │
│  │  │  aggregator      │                                               │    │
│  │  └──────────────────┘  ┌──────────────┐  ┌──────────────────┐       │    │
│  │                        │ AGENTS       │  │ API (181 eps)   │       │    │
│  │  ┌──────────────────┐  │  9+ special  │  │ FastAPI         │       │    │
│  │  │ BACKTEST         │  │  Council/Dbt │  │ Telegram Guard  │       │    │
│  │  │ walk-fwd/MC/CPCV │  │  Risk/Compl  │  └──────────────────┘       │    │
│  │  └──────────────────┘  └──────────────┘                             │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  DEPLOYMENT:                                                                  │
│    Source:  D:\repositories\Quant-Nanggroe-AI-worktree                       │
│    Deploy:  E:\trading\quant_nanggroe\                                        │
│    Creds:   MT5_LOGIN, MT5_PASSWORD env vars (NOT hardcoded)                 │
│    Kill Sw: QNA_KILL_SWITCH_STATE_FILE (shared cross-process)                │
│    DCC Env: QNA_DCC_MEAN_CORR, QNA_DCC_MEAN_VOL_PCT, QNA_DCC_N_ASSETS       │
│    MSI Env: QNA_MSI_*, QNA_CAUSAL_BIAS_*                                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Entry Point — `qna.py`

| Mode | Command | Port | Auto-Browser |
|------|---------|------|-------------|
| Unified (default) | `python qna.py` | — | No |
| API | `python qna.py api` | 8000 | Yes |
| Daemon | `python qna.py daemon` | — | No |
| Hedge | `python qna.py hedge` | — | No |
| Status | `python qna.py status` | — | No |
| Stop | `python qna.py stop` | — | No |

**⚠️ Deprecated:** `cli` and `web` modes will be removed in v7.0.Use `unified` (default) instead.
Auto-browser disabled via `--no-browser` or `QNA_AUTO_OPEN=0`.

### 1b. UnifiedPipeline (`quant_nanggroe/pipeline/`) — 🆕 v6.0.0

| Module | Purpose |
|--------|---------|
| `orchestrator.py` | Pipeline orchestration & lifecycle — auto mode-routing |
| `data.py` | Data ingestion & normalization |
| `signal.py` | Signal generation & aggregation |
| `execution.py` | Order execution pipeline |
| `factory.py` | Pipeline factory with auto mode detection |

Auto-routes between hedge, crypto, and agentic modes based on config. Default mode: hedge.

### 2. Engine (`quant_nanggroe/engine/`) — 19 Modules

| Module | Purpose |
|--------|---------|
| `strategies/` | 🔴 CANONICAL — 79+ registered via @StrategyRegistry.register |
| `strategy/` | 🟡 LEGACY BRIDGE — backward-compat shim only (empty dir, re-export) |
| `risk/` | 9-checkpoint constitutional risk gate, KillSwitch C5, RiskManager |
| `risk/checks.py` | ConstitutionalRiskGuard (= RiskCheckGate alias) |
| `risk/kill_switch.py` | C5 cross-process shared state, 3-level activation (thresholds from constants.py) |
| `risk/constants.py` | **Single source of truth** for ALL constitutional limits (v6.0.0) |
| `risk/manager.py` | RiskManager orchestration |
| `backtest/` | Walk-forward, Monte Carlo, CPCV |
| `execution/` | TWAP/VWAP order slicing, Builder, Almgren-Chriss |
| `agentic/` | Autonomous agent pipeline (LangGraph orchestration) |
| `portfolio/` | Portfolio construction, Kelly sizing, risk parity |
| `factors/` | Alpha factor library |
| `self_aware.py` | Self-reflection on every pipeline run |
| `models/` | ML models and inference |
| `correction.py` | Error recording and lesson-based prevention |
| `autoswitch.py` | Strategy auto-switching logic |
| `registry.py` | Auto-discovery component registry |
| `standalone.py` | Zero-dependency autonomous runner |
| `engine_production_bridge.py` | Production bridge with C5 kill switch init |

### 3. Strategy System — StrategyConsolidationGate

```
┌─────────────────────────────────────────────────────────────────┐
│                    STRATEGY SYSTEM                              │
│                                                                │
│  StrategyConsolidationGate:                                     │
│                                                                │
│  CANONICAL PATH (v6.0.0)                                       │
│    quant_nanggroe/engine/strategies/                            │
│    ├── registry.py            ← StrategyRegistry + @register   │
│    ├── smc_strategy.py        ← @StrategyRegistry.register     │
│    ├── mean_reversion.py      ← @StrategyRegistry.register     │
│    ├── msnr.py                ← @StrategyRegistry.register     │
│    ├── adx_strategy.py        ← @StrategyRegistry.register     │
│    ├── aroon_strategy.py      ← @StrategyRegistry.register     │
│    ├── bollinger_squeeze.py   ← @StrategyRegistry.register     │
│    ├── cci_strategy.py        ← @StrategyRegistry.register     │
│    ├── choppiness_index.py    ← @StrategyRegistry.register     │
│    └── +30 more .py files     ← Signal adapters, wrappers      │
│                                                                │
│  LEGACY BRIDGE (backward compat shim)                          │
│    quant_nanggroe/engine/strategy/strategies/                  │
│    └── __init__.py            ← Re-exports from canonical      │
│                                                                │
│  79+ registered strategies in canonical path     │
└─────────────────────────────────────────────────────────────────┘
```

### 4. Risk Engine — C5 Kill Switch Architecture

```
Kill Switch C5 — Cross-Process Convergence
===========================================

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  API Worker 1   │     │  API Worker 2   │     │  Daemon Proc    │
│  KillSwitch()   │     │  KillSwitch()   │     │  KillSwitch()   │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   SHARED STATE FILE      │
                    │  kill_switch_state.json  │
                    │  QNA_KILL_SWITCH_STATE   │
                    │  _FILE env var           │
                    │                          │
                    │  {                       │
                    │    "level": "ACTIVE",    │
                    │    "trigger": "drawdown",│
                    │    "activated_at": "..." │
                    │  }                       │
                    └─────────────────────────┘

Levels:
  NONE    → Normal operation (trades pass)
  MONITOR → Watch only (log violations, no blocking)
  ACTIVE  → Full halt (VETO all trades)

Triggers:
  - daily_loss: Daily P&L exceeds threshold
  - weekly_loss: Weekly P&L exceeds threshold
  - volatility: Volatility spike detected
  - drawdown_detected: Max drawdown breached
  - manual: Human operator invocation

Fail-closed: Unreadable/corrupt state file ⇒ ACTIVE
```

### 5. Hedge Fund Subpackage (`quant_nanggroe/hedge_fund/`) — v6.0.0 Refactored

**Monolith (~6600 lines) split into real submodules with backward-compat shim.**

```
hedge_fund/
├── __init__.py              ← Package init
├── hedge_fund.py            ← BACKWARD-COMPAT SHIM (re-exports from submodules)
├── runner.py                ← Hedge fund runner CLI entry point
├── mtf.py                   ← Multi-timeframe analysis
├── multipair.py             ← Multi-pair scanner
├── utils/                   ← Extracted: data, config, connection, indicators
├── signals/                 ← 4 active providers (core) + 237 evolved (experimental) + registry + aggregator
├── risk/                    ← gate.py, guard.py (fail-closed)
├── execution/               ← orders.py (trail_sl, execute)
├── portfolio/               ← main.py (run_once)
└── tools/                   ← Utility tools
```

Access via: `python qna.py hedge` or `python qna.py unified` (default auto-routes to hedge).

### 6. Agent System (`quant_nanggroe/agents/`)

```
agents/
├── researcher/              → Market research agent (ResearcherAgent)
│   ├── agent.py
│   ├── prompts.py
│   └── tools.py
├── trader/                  → Trade execution agent (TraderAgent)
├── strategist/              → Strategy generation agent (StrategistAgent)
├── risk/                    → Risk monitoring agent
├── coder.py                 → Code generation
├── browser.py               → Web browsing
├── executor.py              → Task execution
├── gold_trader.py           → Gold-specific
├── colony.py                → Agent colony
├── graph.py                 → Agent orchestration graph
├── debate_engine.py         → Multi-agent debate
├── chinese_wall.py          → Information barriers
├── manus.py                 → General purpose
├── planner.py               → Multi-step planning
├── aihf_bridge.py           → AIHF integration
├── hedge_fund_bridge.py     → Hedge fund bridge
├── security.py              → Security monitoring
├── telega_bot.py            → Telegram notifications
├── voice.py                 → Voice interaction
├── marketplace.py           → Agent marketplace
├── state.py                 → Agent state management
├── registry.py              → Agent registry
├── base.py                  → Abstract base class
├── bridges/                 → External system bridges
├── compliance/              → Compliance monitoring
├── council/                 → Agent council
├── crypto/                  → Cryptocurrency agents
├── debate/                  → Debate extensions
├── execution/               → Execution modules
├── forex/                   → Forex agents
├── geopolitics/             → Geopolitical analysis
├── macro/                   → Macroeconomic agents
├── personas/                → Agent personas
└── portfolio/               → Portfolio agents
```

### 7. Data Flow

```
Market Data (MT5/CCXT / exchange REST clients)
    │
    ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ PIPELINE (v6)   │───▶│ ENGINE           │───▶│ RISK (unified)  │
│  orchestrator   │    │  Strategies (79+)│    │  constants.py   │
│  data→signal→exe│    │  Self-Aware      │    │  KillSwitch C5  │
│  auto mode-rt   │    │  Self-Evolve     │    │  9-checkpoint   │
└──────────────────┘    └──────────────────┘    └────────┬─────────┘
    │                                                      │
    ▼                                                      ▼
┌──────────────────┐                              ┌──────────────────┐
│ HEDGE_FUND (v6) │                              │ EXECUTION       │
│  utils/signals/ │                              │  Builder        │
│  risk/exec/port │                              │  Almgren-Chriss │
│  (monolith→mods)│                              │  Paper/MT5      │
└──────────────────┘                              └──────────────────┘
    │                                                      │
    ▼                                                      ▼
┌──────────────────┐                              ┌──────────────────┐
│ API (181 eps)   │                              │ PnL Track       │
│ Telegram Guard  │                              │ Journal         │
│ WebSocket       │                              │ Self-Evolution  │
└──────────────────┘                              └──────────────────┘
```
**v6.0.0 Changes:**
- Pipeline is now the default entry path (orchestrator auto-routes mode)
- Hedge fund submodules extracted from monolithic hedge_fund.py
- Risk thresholds unified under constants.py single source
- Exchange REST clients lazy-wired (10 clients, ccxt failure isolated)
- Telegram config validated at init (fail-closed on missing env vars)

## Key Metrics

| Metric | Value |
|--------|-------|
| Version | 6.1.0 |
| Architecture Health | 9.5/10 — All quantitative engines real, no mock |
| Single Entry Point | `qna.py` (unified mode default) |
| UnifiedPipeline | `pipeline/` module — auto mode-routing + macro_context 🆕 |
| Causal Engine | 5 modules (bias, MSI, COT, SMT, thesis drift) 🆕 |
| DCC-GARCH | Dynamic correlation + auto-fit + 47 unit tests 🆕 |
| Strategy Registration | 79+ via @StrategyRegistry.register |
| Hedge Fund | Submodules + causal bias on all 200+ providers 🆕 |
| Risk Limits | Unified single source `constants.py` + DCC-GARCH correlation |
| Exchange Clients | 10 REST clients lazy-wired + ccxt proxy |
| Kill Switch | C5 cross-process shared state, fail-closed |
| Risk Gates | 9-checkpoint + constitutional limits + thesis drift guard |
| Telegram Guard | Config-validated at init |
| MT5 Bridge | via set_broker_handle() (live = default, paper = opt-in) |
| API Endpoints | 181 FastAPI |
| Python Files | 2,200+ total |
| Documentation | 50+ docs files + graphify + updated README/CHANGELOG/ARCHITECTURE |

## Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| Package Manager | `uv` (not pip, not poetry) |
| API Server | FastAPI (181 endpoints) |
| Pipeline | `quant_nanggroe/pipeline/` — auto mode-routing 🆕 |
| Dashboard | Next.js + React + Recharts + Zustand |
| Broker | MetaTrader5 (env vars for credentials) |
| Crypto | CCXT + 10 REST clients (lazy-wired) |
| Risk Engine | ConstitutionalRiskGuard, KillSwitch C5, RiskManager, unified constants |
| Telegram | Config-validated (`validate_telegram_config` + `ensure_telegram`) 🆕 |
| Testing | pytest (107/108 pass — 1 ccxt skip) |

## Known Architecture Issues

| Issue | Impact | Mitigation |
|-------|--------|-----------|
| PYTHONPATH leak on Hermes host | ModuleNotFoundError | `PYTHONPATH=""` wrapper |
| 2 strategy hierarchies | Confusion (canonical vs legacy shim) | Legacy empty, re-export only |
| Git history has stale secrets | Security exposure | Force-push pending rotation |
| Dashboard build not Windows-verified | Deployment gap | Vercel builds in CI |

---

*v6.0.0 — Built with fury from Aceh, Indonesia 🇮🇩*
