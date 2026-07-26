# Quant Nanggroe AI v6.0.0 — Autonomous Quantitative Hedge Fund

Autonomous quantitative hedge fund platform with multi-strategy execution, constitutional risk management (9-checkpoint gate), unified pipeline, hedge fund aggregator, and self-evolving pipeline. Runs without human intervention across forex, crypto, and equities.

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
quant_nanggroe/                          (753 .py files, 125K+ lines)
├── pipeline/                            → UnifiedPipeline — auto mode-routing (hedge/crypto/agentic) 🆕 v6.0.0
│   ├── orchestrator.py                  → Pipeline orchestration & lifecycle
│   ├── data.py                          → Data ingestion & normalization
│   ├── signal.py                        → Signal generation & aggregation
│   ├── execution.py                     → Order execution pipeline
│   └── factory.py                       → Pipeline factory with auto mode detection
├── api/                                 → FastAPI server (181 endpoints)
├── engine/                              → Core trading engine (19 modules)
│   ├── strategies/                      → CANONICAL — 9 registered strategies (@register decorator)
│   │   └── registry.py                  → StrategyRegistry auto-discovery
│   ├── strategy/strategies/             → LEGACY BRIDGE — backward-compat shim only (empty, routes via __init__)
│   ├── risk/                            → Constitutional risk: 9-checkpoint gate, KillSwitch, drawdown monitor
│   │   ├── kill_switch.py               → KillSwitch with C5 cross-process shared state (thresholds from constants.py)
│   │   ├── checks.py                    → ConstitutionalRiskGuard (= RiskCheckGate alias)
│   │   ├── manager.py                   → RiskManager orchestration
│   │   └── constants.py                 → Single source of truth for all risk limits
│   ├── backtest/                        → Walk-forward, Monte Carlo, multi-market backtest
│   ├── execution/                       → Order routing, Builder, RiskManager, Almgren-Chriss
│   ├── agentic/                         → Autonomous agent lifecycle (LangGraph orchestration)
│   ├── portfolio/                       → Portfolio construction, Kelly sizing, risk parity
│   └── models/                          → ML models and inference
├── hedge_fund/                          → Executive-level multi-provider aggregator
│   ├── hedge_fund.py                    → Hedge fund voting engine (backward-compat shim)
│   ├── mtf.py                           → Multi-timeframe analysis
│   ├── multipair.py                     → Multi-pair scanner
│   ├── runner.py                        → Hedge fund runner
│   ├── signals/                         → 247 providers: core (10) + evolved (237) + registry + aggregator
│   ├── risk/                            → gate.py, guard.py (fail-closed)
│   ├── execution/                       → orders.py (trail_sl, execute)
│   ├── portfolio/                       → main.py (run_once)
│   ├── utils/                           → data, config, connection, indicators
│   └── tools/                           → Utility tools
├── signals/                             → TradingSignal model + SignalRepository
├── security/                            → Auth (JWT, API key), credential manager
├── agents/                              → 9 specialized agent modules
│   ├── researcher/                      → Market research (ResearcherAgent)
│   ├── trader/                          → Trade execution (TraderAgent)
│   ├── strategist/                      → Strategy generation (StrategistAgent)
│   ├── risk/                            → Risk monitoring agent
│   ├── coder.py                         → Coding agent
│   ├── browser.py                       → Browser agent
│   ├── executor.py                      → Execution agent
│   ├── graph.py                         → Agent graph orchestration
│   ├── colony.py                        → Agent colony management
│   ├── planner.py                       → Planning agent
│   ├── manus.py                         → Manus agent
│   ├── debate_engine.py                 → Multi-agent debate engine
│   ├── chinese_wall.py                  → Information barrier agent
│   └── ...                              + subdirectories (compliance, council, crypto, debate, execution, forex, macro, personas, portfolio)
├── dashboard/                           → Next.js 18-page UI (agents, backtest, risk, portfolio, etc.)
├── tests/                               → 167 test files (env setup required)
└── archive/                             → Clean archive of legacy/duplicate code
```

### Strategy Pipeline

The canonical strategy pipeline lives in `quant_nanggroe/engine/strategies/` with **9 registered strategies** via `@StrategyRegistry.register` decorator:

| Strategy | File | Description |
|----------|------|-------------|
| SMC | `smc_strategy.py` | Smart Money Concepts — OB, FVG, liquidity sweep, BOS/CHOCH |
| Wyckoff | — | Spring/upthrust, volume ratio, SoS/SoW |
| MSNR | `msnr.py` | Multi-timeframe confluence |
| MeanRev | `mean_reversion.py` | OU process, half-life, Bollinger, z-score |
| ADX | `adx_strategy.py` | Trend strength |
| Aroon | `aroon_strategy.py` | Trend change detection |
| Bollinger Squeeze | `bollinger_squeeze.py` | Volatility breakout |
| CCI | `cci_strategy.py` | Commodity Channel Index |
| Choppiness Index | `choppiness_index.py` | Trend vs. ranging market |
| +32 more .py files (signal adapters, wrappers, legacy bridges) | | |

**Total: 9 registered strategies + 35+ additional .py files** including signal adapters, wrappers, and experimental modules.

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

### Hedge Fund Aggregator

The `hedge_fund/` subpackage provides executive-level multi-provider signal aggregation with voting, allowing strategies from multiple sources to converge on a unified trading decision.

### Dashboard (Next.js 18 Pages)

- Real-time WebSocket streaming via `@/lib/websocket`
- API client with retry (3 attempts), backoff, dedup
- 18 route pages: trading, risk, portfolio, backtest, agents, brokers, strategies, etc.
- Next.js API proxy rewrite for same-origin requests
- Glassmorphism design system (Apple macOS Liquid Glass × Bloomberg Terminal)

---

## Current Gaps & Known Issues

| Gap | Severity | Status |
|-----|----------|--------|
| PYTHONPATH leak on boot (Hermes venv contamination) | HIGH | Mitigated (env fix documented) |
| Test suite requires environment setup (pytest env broken) | MEDIUM | 1 skip remaining (ccxt env) — 107/108 pass |
| 2 strategy hierarchies (canonical + legacy shim) | MEDIUM | Legacy empty, bridge in place |
| No cron-to-live-trade wiring on this host | LOW | Requires MT5 + VPS |
| Dashboard Next.js build not verified on Windows | LOW | Vercel builds in CI |
| Option/volatility strategies not live-tested | LOW | Walk-forward validates directional only |

---

## Project Status

| Domain | Status |
|--------|--------|
| Architecture Health | 9/10 — Clean single entry point + unified pipeline |
| Risk System | Fail-closed, C5 kill switch, 9-checkpoint gate, unified constants |
| Strategies | 9 registered via StrategyRegistry + legacy bridge |
| Hedge Fund | Multi-provider aggregator split into real submodules (v6.0.0) |
| UnifiedPipeline | 🆕 v6.0.0 — auto mode-routing (hedge/crypto/agentic) |
| Documentation | 50+ docs files |
| Test Suite | 107/108 pass (1 ccxt skip) |
| Security | Secrets via env vars, Telegram config validated |
| Issues Resolved | 48/49 (98%) |

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
