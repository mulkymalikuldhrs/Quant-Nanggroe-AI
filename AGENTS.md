# Quant Nanggroe AI v6.1.0 — Agent Instructions

## How to Read This Repo
Read in this order before making changes:
```
README → AGENTS → ARCHITECTURE → CHANGELOG → TODO → docs/00_VISION → docs/01_PRD
→ docs/02_ARCHITECTURE → docs/04_API → docs/19_RISK_REGISTER → docs/50_AGENT_COUNCIL
```
`docs/` has 58+ documents (numbered 00-51 plus ADRs), covering architecture, API, risk, security, testing, roadmap, and more.

**New in v6.1.0:**
- Causal Engine Suite (`engine/causal/`) — 6 modules (bias, MSI, COT, SMT, thesis drift, CME provider)
- DCCState Singleton (`engine/risk/dcc_state.py`) — Shared DCC-GARCH state across modules
- CME Price Provider (`engine/causal/cme_provider.py`) — 17 futures↔spot pairs, Yahoo Finance compatible
- DCC-GARCH (`engine/risk/dcc_garch.py`) — Dynamic cross-asset correlation with 47 tests
- Causal Bias → Signal Filter — All HF providers apply boost/reduce/block
- Pipeline `macro_context.py` — ORPHAN FIX: replaced non-existent imports with real modules
- Causal Engine API (`api/routes/causal_engine.py`) — 15+ endpoints at `/api/causal/*`
- Dashboard (`api/static/dashboard.html`) — Unified UI with Tactical Gold palette

## Audit Status (Round 2 Complete)
- **Last Full Audit:** 2026-07-26
- **Round 1:** 56 findings (6 P0, 9 P1, 8 P2, 10+ P3, 12 P4, 8 P5, 7 P6) — **ALL FIXED**
- **Round 2:** 55+ findings (18 Critical, 22 High, 15 Medium) — **95%+ FIXED**
  - **Critical fixed this session:** Phantom `from strategy_registry import` imports in 5 files
  - **All other critical/high findings:** Already fixed in prior sessions
- **Score:** 52 → 87/100
- **Test Suite:** 107/108 pass (1 ccxt skip)

## Entry Points
- **Primary**: `qna.py` — single unified launcher (modes: `unified`, `api`, `daemon`, `hedge`, `status`, `stop`). `unified` is the default mode (no subcommand needed). All others archived.
- **Unified (default)**: `python qna.py` — UnifiedPipeline with auto mode-routing (hedge/crypto/agentic).
- **API**: `python qna.py api` — FastAPI server on port 8000. Auto-opens browser.
- **Daemon**: `python qna.py daemon` — background lifecycle daemon.
- **Hedge**: `python qna.py hedge` — multi-provider hedge fund aggregator.
- **Status**: `python qna.py status` — system health check.
- **Stop**: `python qna.py stop` — stop running daemon.
- **⚠️ Deprecated:** `cli` and `web` modes (removed in v7.0).

## 🚨 Critical: PYTHONPATH Contamination

**This repo MUST be run with `PYTHONPATH=""` when launched from a Hermes-managed shell.**

Root cause: Hermes venv has packages compiled for Python 3.11 ABI. System Python is 3.14.6. The Hermes process inherits `PYTHONPATH` which forces `import pydantic` to load a stale `pydantic_core._pydantic_core` compiled for 3.11 → `ModuleNotFoundError`.

**Always use:**
```bash
PYTHONPATH="" .venv/Scripts/python -m uvicorn quant_nanggroe.api.app:app   # API
PYTHONPATH="" .venv/Scripts/python -m pytest tests/                        # Tests
```

## Agent Modules (`quant_nanggroe/agents/`)

| Agent | Path | Description |
|-------|------|-------------|
| Researcher | `researcher/` (agent.py, prompts.py, tools.py) | Market research & analysis |
| Trader | `trader/` | Trade execution & decision making |
| Strategist | `strategist/` | Strategy generation & optimization |
| Risk | `risk/` | Risk monitoring & compliance |
| Coder | `coder.py` | Code generation & maintenance |
| Browser | `browser.py` | Web browsing & data collection |
| Executor | `executor.py` | Task execution & orchestration |
| Planner | `planner.py` | Multi-step planning |
| Manus | `manus.py` | General-purpose agent |
| Gold Trader | `gold_trader.py` | Gold-specific trading agent |
| Colony | `colony.py` | Agent colony management |
| Graph | `graph.py` | Agent graph orchestration |
| Debate Engine | `debate_engine.py` | Multi-agent debate framework |
| Chinese Wall | `chinese_wall.py` | Information barrier enforcement |
| AIHF Bridge | `aihf_bridge.py` | AIHF integration bridge |
| Hedge Fund Bridge | `hedge_fund_bridge.py` | Hedge fund aggregator bridge |
| Security | `security.py` | Security monitoring |
| Telegram Bot | `telegram_bot.py` | Telegram notification agent |
| Voice | `voice.py` | Voice interaction agent |
| Marketplace | `marketplace.py` | Agent marketplace |
| State | `state.py` | Agent state management |
| Registry | `registry.py` | Agent registration & discovery |
| Protocols | `protocols.py` | Agent communication protocols |
| Base | `base.py` | Abstract base agent class |

**Agent subdirectories:**
- `bridges/` — External system bridges
- `compliance/` — Compliance monitoring agents
- `council/` — Agent council/consensus
- `crypto/` — Cryptocurrency agents
- `debate/` — Debate engine extensions
- `execution/` — Execution agent modules
- `forex/` — Forex-specific agents
- `geopolitics/` — Geopolitical analysis agents
- `macro/` — Macroeconomic agents
- `personas/` — Agent persona definitions
- `portfolio/` — Portfolio management agents

## UnifiedPipeline (`quant_nanggroe/pipeline/`) — 🆕 v6.0.0
- **Auto mode-routing**: `orchestrator.py` detects mode from config (hedge → default, crypto, agentic)
- **Pipeline stages**: `data.py` → `signal.py` → `execution.py`, orchestrated by `orchestrator.py`
- **Factory**: `factory.py` auto-creates the right pipeline for the detected mode
- **Default**: `python qna.py` runs the unified pipeline in hedge mode

## Hedge Fund Subpackage (`quant_nanggroe/hedge_fund/`) — v6.1.0
- **Monolith split**: `hedge_fund.py` (~6600 lines) → real submodules:
  - `utils/` — data, config, connection, indicators
  - **`signals/core.py`** — 10 core providers with **SYMBOL_TO_FUTURES** mapping + **`apply_causal_bias()`** 🆕
  - **`signals/qna_strategies.py`** — 200+ evolved providers with **causal bias filtering** 🆕
  - `signals/aggregator.py` — Signal voting + DXY context boost
  - `risk/` — gate.py, guard.py (fail-closed)
  - `execution/` — orders.py (trail_sl, execute)
  - `portfolio/` — main.py (run_once)
- **Causal bias levels**: BOOST (+0.15 confidence), REDUCE (-0.15), BLOCK (confidence → 0)
- **Backward-compat**: `hedge_fund.py` is now a thin re-export shim. All old imports keep working.

## Risk System — v6.1.0
- **Single source of truth**: `engine/risk/constants.py` for ALL constitutional limits
- **DCC-GARCH** (`engine/risk/dcc_garch.py`): Dynamic cross-asset correlation via `arch` package 🆕
  - GARCH(1,1) volatility forecasts
  - Dynamic Conditional Correlation matrix
  - VRK Kelly weight computation with safety caps
  - Auto-fit in `live_engine.py` every N cycles
  - 47 unit tests
- **Thesis Drift Guard** (`engine/causal/thesis_drift_guard.py`): 3-stage circuit breaker 🆕
- **KillSwitch** reads thresholds from `constants.py`
- **Weekly loss veto**: EngineRiskManager.can_trade() checks weekly + daily loss

## Exchange REST Clients — v6.0.0 Lazy Wiring
- **10 clients** lazy-wired into `ExchangeFactory.create_rest_client()`: binance, bybit, coinbase, crypto_com, gemini, kraken, kucoin, okx, bitget, gate
- **ccxt isolation**: lazy proxy in `exchange/__init__.py` prevents bootstrap crash when ccxt not installed

## Telegram Config Validation — v6.0.0
- `validate_telegram_config()` — validates all required env vars at init
- `ensure_telegram()` — fail-closed: raises `QNAConfigurationError` with clear message

## Strategy System
- **Canonical:** `quant_nanggroe/engine/strategies/` (79+ registered via `@StrategyRegistry.register`)
- **Legacy (archived):** Path is a backward-compat shim — `quant_nanggroe/engine/strategy/strategies/` (empty directory with re-export `__init__.py`)
- **Registry pattern:** `@StrategyRegistry.register` decorator on each strategy class
- All imports via `engine.strategy.strategies` keep working transparently through the shim

## Kill Switch C5 — Cross-Process Convergence
- **Single shared state file** (`QNA_KILL_SWITCH_STATE_FILE` env var) read/written by every KillSwitch() instance
- **configure_kill_switch_file()** — call at startup to wire all workers to one truth
- **Fail-closed:** corrupt/unreadable state file → halt all trading
- **Three-level activation:** NONE → MONITOR → ACTIVE
- **Triggers:** daily loss (0.8%), weekly loss (2.5%), volatility spike, drawdown
- **Thresholds from `constants.py`** (v6.0.0): `DAILY_LOSS_LIMIT = 0.008`, `WEEKLY_LOSS_LIMIT = 0.025`

## What Not to Change Without Approval
- API contract (response envelope, endpoint paths).
- Risk engine logic (`engine/risk/` — Kelly, VaR, drawdown limits, sector limits, kill switch thresholds). Thresholds MUST come from `constants.py` — do not hardcode.
- Pipeline mode-routing logic (`pipeline/orchestrator.py`).
- State file format in `paper_state/`.
- Agent registration in `qna.py` (`DEFAULT_AGENTS` dict).

## How to Update Docs
- `docs/` has 58+ active files (numbered 00-51 plus ADRs). Stale docs are in `archive/docs/`.
- Doc changes must accompany code changes in same PR.
- Use ADR format for architecture decisions (`docs/11_DECISIONS.md`).

## Commands
```sh
# Test (requires PYTHONPATH isolation) — 107/108 pass (1 ccxt skip)
PYTHONPATH="" uv run python -m pytest tests/ -v --tb=short   # full suite
PYTHONPATH="" uv run python -m pytest tests/path/to_test.py   # single file

# Causal Engine API endpoints (15+)
curl http://localhost:8000/api/causal/status           # Aggregated engine status
curl http://localhost:8000/api/causal/dcc/status        # DCC correlation matrix
curl http://localhost:8000/api/causal/cme/prices        # Live CME futures prices
curl http://localhost:8000/api/causal/biases?event=RATE_CUT  # Causal biases

# Dashboard (served by API server)
open http://localhost:8000/dashboard.html

# Run
uv run python qna.py                    # UnifiedPipeline (default mode, auto hedge routing)
uv run python qna.py api                # API server + dashboard + auto browser
uv run python qna.py api --no-browser   # no auto-open
uv run python qna.py status             # health check
uv run python qna.py hedge              # hedge fund aggregator
```

## Architecture Pitfalls
- **`RiskCheckGate` is an alias** for `ConstitutionalRiskGuard` (line 461 of `checks.py`). Both names refer to the same class.
- **Kill switch unit mismatch**: RiskManager passes P&L as percentages (0-100), but KillSwitch expects fractions (0-1).
- **Kill Switch C5**: Shared state file prevents split-brain across uvicorn workers. Call `configure_kill_switch_file()` at startup.
- **Kill Switch thresholds MUST come from constants.py**: Do NOT hardcode daily/weekly limits.
- **DCC-GARCH env vars**: `QNA_DCC_MEAN_CORR`, `QNA_DCC_MEAN_VOL_PCT`, `QNA_DCC_N_ASSETS` — set by auto-fit cycle, read by risk engine 🆕
- **Causal bias env vars**: `QNA_CAUSAL_BIAS_*` — set by qna.py pre-filter, read by pipeline/macro_context.py 🆕
- **MSI env vars**: `QNA_MSI_*` — set by Macro Surprise Index module 🆕
- **Strategy auto-discovery**: Engine scans `engine/strategy/strategies/` for re-exports from canonical `engine/strategies/`.
- **`conftest.py` overrides `DATABASE_URL`** at import time to `sqlite+aiosqlite:///test_qna.db`.
- **JWT_SECRET sentinel**: Default `__UNSET_QNAI_JWT_SECRET__` causes boot refusal.
- **Risk limits**: Single source of truth is `engine/risk/constants.py`.
- **Telegram `ensure_telegram()`**: Call at startup.
- **Exchange clients**: Use `ExchangeFactory.create_rest_client(exchange_name)`. ccxt lazy proxy in `exchange/__init__.py`.
- **causal bias double-filtering**: HF providers self-filter; pipeline filter is safety net for non-HF signals only.

## Constraints
- `asyncio_mode = "auto"` for pytest (no need for `@pytest.mark.asyncio` on async tests).
- mypy: `strict = true`, `disallow_untyped_defs = true`. Every function must be typed.
- ruff: line length 120.
- Python 3.11+ recommended (3.14+ on Hermes host).
- Project uses `uv` for package management (not pip, not poetry).
