# Quant Nanggroe AI v5.1.0 — Architecture

## Overview

Quant Nanggroe AI (QNA) is an **institutional-grade autonomous quantitative hedge fund** platform. Multi-strategy execution, constitutional risk management, cross-process kill switch (C5), hedge fund aggregator, and self-evolving pipeline — all accessible via a single entry point.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      QNA v5.1.0 — Architecture                         │
│              Autonomous Quantitative Hedge Fund                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ENTRY: qna.py (single — all others archived)                           │
│    ├── cli      → Interactive CLI shell                                  │
│    ├── api      → FastAPI server (:8000) + auto-open browser             │
│    ├── daemon   → Background lifecycle daemon                            │
│    ├── web      → Flask legacy UI (:5000) + auto-open browser            │
│    ├── hedge    → Hedge Fund aggregator (multi-provider voting)          │
│    ├── status   → Health check                                           │
│    └── stop     → Stop daemon                                            │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │                    QUANT_NANGNGROE/                              │    │
│  │                                                                  │    │
│  │  ┌──────────────┐  ┌────────────────┐  ┌──────────────────┐     │    │
│  │  │ ENGINE       │→│ RISK          │→│ EXECUTION        │     │    │
│  │  │  19 modules  │  │  9-checkpoint │  │  Builder         │     │    │
│  │  │  Self-Aware  │  │  KillSwitch   │  │  RiskManager     │     │    │
│  │  │  Self-Evolve │  │  C5 cross-proc│  │  Almgren-Chriss  │     │    │
│  │  └──────┬───────┘  └───────────────┘  └──────────────────┘     │    │
│  │         │                                                       │    │
│  │  ┌──────▼───────┐  ┌──────────────┐  ┌──────────────────┐     │    │
│  │  │ STRATEGIES   │→│ BACKTEST    │→│ API (181 eps)    │     │    │
│  │  │  Canonical   │  │  Walk-fwd   │  │  FastAPI         │     │    │
│  │  │  9 registered│  │  Monte Carlo│  │  Dashboard API   │     │    │
│  │  │  @register   │  │  CPCV       │  │  WebSocket       │     │    │
│  │  └──────────────┘  └─────────────┘  └──────────────────┘     │    │
│  │                                                                  │    │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐   │    │
│  │  │ HEDGE_FUND       │  │ AGENTS            │  │ EXCHANGE    │   │    │
│  │  │  Multi-provider  │  │  9+ specialized   │  │  MT5 Bridge │   │    │
│  │  │  Voting engine   │  │  Council/Debate   │  │  CCXT/Crypto│   │    │
│  │  │  HF Runner       │  │  Risk/Compliance  │  │  set_broker │   │    │
│  │  └──────────────────┘  └──────────────────┘  └──────────────┘   │    │
│  └──────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  DEPLOYMENT:                                                              │
│    Source:  D:\repositories\Quant-Nanggroe-AI-worktree                   │
│    Deploy:  E:\trading\quant_nanggroe\                                    │
│    Creds:   MT5_LOGIN, MT5_PASSWORD env vars (NOT hardcoded)             │
│    Kill Sw: QNA_KILL_SWITCH_STATE_FILE (shared cross-process)            │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Entry Point — `qna.py`

| Mode | Command | Port | Auto-Browser |
|------|---------|------|-------------|
| CLI | `python qna.py cli` | — | No |
| API | `python qna.py api` | 8000 | Yes |
| Daemon | `python qna.py daemon` | — | No |
| Web | `python qna.py web` | 5000 | Yes |
| Hedge | `python qna.py hedge` | — | No |
| Status | `python qna.py status` | — | No |
| Stop | `python qna.py stop` | — | No |

Auto-browser disabled via `--no-browser` or `QNA_AUTO_OPEN=0`.

### 2. Engine (`quant_nanggroe/engine/`) — 19 Modules

| Module | Purpose |
|--------|---------|
| `strategies/` | 🔴 CANONICAL — 9 registered via @StrategyRegistry.register + 35+ .py files |
| `strategy/` | 🟡 LEGACY BRIDGE — backward-compat shim only (empty dir, re-export) |
| `risk/` | 9-checkpoint constitutional risk gate, KillSwitch C5, RiskManager |
| `risk/checks.py` | ConstitutionalRiskGuard (= RiskCheckGate alias) |
| `risk/kill_switch.py` | C5 cross-process shared state, 3-level activation |
| `risk/constants.py` | Single source of truth for constitutional limits |
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
│  CANONICAL PATH (v5.1.0)                                       │
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
│  9 registered strategies + 35+ .py files in canonical path     │
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

### 5. Hedge Fund Subpackage (`quant_nanggroe/hedge_fund/`)

```
hedge_fund/
├── __init__.py              ← Package init
├── hedge_fund.py            ← Multi-provider voting engine (331K+ lines)
├── runner.py                ← Hedge fund runner CLI entry point
├── mtf.py                   ← Multi-timeframe analysis
├── multipair.py             ← Multi-pair scanner
├── signals/                 ← Signal generation & aggregation
├── risk/                    ← Hedge fund risk management
├── execution/               ← Hedge fund order execution
├── portfolio/               ← Hedge fund portfolio allocation
├── tools/                   ← Utility tools
└── utils/                   ← Utility functions
```

Access via: `python qna.py hedge`

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
Market Data (MT5/CCXT)
    │
    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Strategy     │───▶│ Risk Check   │───▶│ Execution    │
│ Engine (9+   │    │ (9 gates +   │    │ (Builder,    │
│ registered)  │    │  C5 KillSw)  │    │  Almgren)    │
└──────────────┘    └──────────────┘    └──────────────┘
    │                                      │
    ▼                                      ▼
┌──────────────┐                    ┌──────────────┐
│ Self-Aware   │                    │ PnL Track   │
│ Anomaly      │                    │ Journal     │
│ Detection    │                    │ Evolution   │
└──────────────┘                    └──────────────┘
    │                                      │
    ▼                                      ▼
┌──────────────┐                    ┌──────────────┐
│ Hedge Fund   │                    │ Dashboard    │
│ Aggregator   │                    │ WebSocket    │
│ (voting)     │                    │ Streaming    │
└──────────────┘                    └──────────────┘
```

## Key Metrics

| Metric | Value |
|--------|-------|
| Version | 5.1.0 |
| Architecture Health | 9/10 |
| Single Entry Point | `qna.py` (all others archived) |
| Strategy Registration | 9 via @StrategyRegistry.register |
| Strategy Files | 45 .py files in canonical path |
| Hedge Fund | `hedge_fund/` subpackage with multi-provider voting |
| Kill Switch | C5 cross-process shared state, fail-closed |
| Risk Gates | 9-checkpoint + constitutional limits |
| MT5 Bridge | via set_broker_handle() |
| API Endpoints | 181 FastAPI |
| Agent Modules | 9+ specialized agents + subdirectories |
| Python Files | 2,189 total |
| Documentation | 50+ docs files |

## Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| Package Manager | `uv` (not pip, not poetry) |
| API Server | FastAPI (181 endpoints) |
| Legacy UI | Flask |
| Dashboard | Next.js + React + Recharts + Zustand |
| Broker | MetaTrader5 (env vars for credentials) |
| Crypto | CCXT |
| Risk Engine | ConstitutionalRiskGuard, KillSwitch C5, RiskManager |
| Testing | pytest (env setup required) |

## Known Architecture Issues

| Issue | Impact | Mitigation |
|-------|--------|-----------|
| PYTHONPATH leak on Hermes host | ModuleNotFoundError | `PYTHONPATH=""` wrapper |
| 2 strategy hierarchies | Confusion (canonical vs legacy shim) | Legacy empty, re-export only |
| pytest 431 cached failures | Cannot run tests | Environment setup documented |
| Git history has stale secrets | Security exposure | Force-push pending rotation |
| Dashboard build not Windows-verified | Deployment gap | Vercel builds in CI |

---

*v5.1.0 — Built with fury from Aceh, Indonesia 🇮🇩*
