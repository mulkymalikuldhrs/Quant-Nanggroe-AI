# Quant Nanggroe AI v6.5.0 — Agent Instructions

## 🚨 PYTHONPATH Contamination (Critical)
Hermes-managed shells leak a `PYTHONPATH` with `pydantic_core` compiled for Python 3.11 ABI, causing `ModuleNotFoundError` on the system Python 3.14+.

- `python qna.py` **is safe** — it self-sanitises (lines 27–33).
- `pytest` / `uvicorn` directly **must** be prefixed: `PYTHONPATH="" uv run python -m pytest tests/`
- `launch.bat` wrappers already clear PYTHONPATH.

## Entry Points
Single entry: `python qna.py [mode]` — default mode is `unified`.

| Mode | Command | What it runs |
|------|---------|-------------|
| Unified | `python qna.py` | UnifiedPipeline auto-routing (hedge/crypto/agentic) |
| API | `python qna.py api` | FastAPI server :8000 |
| Daemon | `python qna.py daemon` | Background lifecycle daemon |
| Hedge | `python qna.py hedge` | Hedge fund multi-provider aggregator |
| Status | `python qna.py status` | System health |
| Stop | `python qna.py stop` | Stop daemon |

**Never create another root-level entry point.** `qna.py` is THE one.

## Commands
```sh
# Run
uv run python qna.py api

# Test (always PYTHONPATH="")
PYTHONPATH="" uv run python -m pytest tests/ -v --tb=short
PYTHONPATH="" uv run python -m pytest tests/path/to_test.py

# Lint / type-check
ruff check .
mypy quant_nanggroe/

# Pre-commit (ruff only)
pre-commit run --all-files

# API endpoints
curl http://localhost:8000/api/causal/status
curl http://localhost:8000/dashboard.html
```

## Package Management
- **`uv`** for local dev (not pip, not poetry).
- CI uses `pip install -e ".[dev]"` — do not change.
- Python 3.11+ required.
- `.venv/` is gitignored; recreate via `uv sync`.

## Architecture Facts (non-obvious)

### Source Tree
```
qna.py                          ← single entry point
quant_nanggroe/
  engine/
    strategies/                 ← canonical: 79+ strategies @StrategyRegistry.register
    strategy/strategies/        ← LEGACY SHIM — empty dir with re-export __init__.py only
    risk/
      constants.py              ← single source of truth for ALL risk limits
      dcc_garch.py              ← DCC-GARCH dynamic correlation
      kill_switch.py            ← C5 file-backed shared state
      checks.py                 ← ConstitutionalRiskGuard (alias RiskCheckGate)
    causal/                     ← 5 modules: bias, MSI, COT, SMT, thesis drift
    agentic/                    ← LangGraph autonomous agent lifecycle
  hedge_fund/
    signals/core.py             ← 10 core providers
    signals/qna_strategies.py   ← 200+ evolved providers
  pipeline/                     ← UnifiedPipeline: orchestrator → data → signal → execution
  api/                          ← FastAPI (181+ endpoints)
  agents/                       ← 9+ agent modules
dashboard/                      ← Next.js (18 pages)
tests/                          ← test suite
```

### Strategy Registry
- Strategies register via `@StrategyRegistry.register` decorator in `engine/strategies/`. The walk-forward metadata registry (`engine/strategy/registry.py`) is `WalkForwardRegistry`.
- The legacy path `engine/strategy/strategies/` is a **backward-compat shim only** — empty directory with a re-export `__init__.py`.
- Old imports via `engine.strategy.strategies` keep working through the shim.
- Numpy-native strategies in `quant_nanggroe/strategies/` (trend_follow, tsmom, pairs_trade, xgboost_alpha) are deprecated — they should migrate to the Strategy base class.

### Pipeline Self-Loop (v6.5.0)
- `UnifiedSignalEngine._try_strategies()` has two-tier fallback: ProductionStrategyRunner → direct StrategyRegistry.
- `ProductionStrategyRunner._load_strategies()` filters by WalkForwardRegistry: strategies with negative OOS Sharpe or decayed are excluded.
- `AutomatedBacktestRunner` stores walk-forward results in WalkForwardRegistry and exposes `is_strategy_viable()`.
- `AutonomousPipeline.run_batch()` triggers `_post_batch_evolution()`: PnL score → StrategyEvolver mutate → WalkForward validate → WalkForwardRegistry update.
- `PipelineScheduler` is wired into `qna.py daemon` (via `QNA_SCHEDULER_ENABLED` env var) and `api/app.py` lifespan.

### Colony (v6.5.0)
- `api/routes/colony.py` uses real `ColonyOrchestrator` from `engine/colony/` with graceful fallback.
- `colony_stub.py` has been deleted.
- Colony workers are wired to: StrategyWorker → StrategyRegistry, RiskWorker → ConstitutionalRiskGuard, DataWorker → ExchangeManager, ExecutionWorker → ProductionExecutionManager.

### Dashboard & API Wiring (v6.5.0)
- `pipeline_status.router` and `config.router` are mounted in `app.py` (were missing — caused 404s).
- `channels.py` returns `Channel[]` array (not dict), discovers channels from env vars (`QNAI_TELEGRAM_BOT_TOKEN`, `QNAI_WHATSAPP_TOKEN`, etc.).
- `ecosystem.py` routes read from real KillSwitch, StrategyRegistry, ExchangeManager — no hardcoded data.
- All dashboard pages show error states instead of mock data when backend is unavailable.
- No "Coming Soon" banners remain. No hardcoded fallback data in any dashboard page.

### Debate System (v6.5.0)
- Three debate modes wired into `/api/debate/`:
  - **TradingDebateGraph** (`agents/debate/graph.py`): Full Bull/Bear research debate + Conservative/Neutral/Aggressive risk debate. POST `/api/debate/new` with `symbol` field.
  - **DebateEngine** (`agents/debate/engine.py`): Weighted multi-agent vote. POST `/api/debate/weighted` with opinions array.
  - **Council** (`engine/agentic/council.py`): 6 investor personas debate low-confidence signals. Wired into autonomous pipeline step 2.5.
- Council debate runs automatically in `AutonomousPipeline.run()` when confidence < 0.65.
- Reflection/Propagator/SignalProcessor in `agents/debate/reflection.py` (requires LLM).

### Self-Evolution Loop (v6.5.0)
- `_post_batch_evolution()` runs real walk-forward backtest via `AutomatedBacktestRunner` with yfinance candles.
- Mutated strategies are instantiated via `StrategyRegistry.create()` with mutated params applied.
- No more zero-value WalkForwardResult records — real backtest engine computes Sharpe, returns, max DD.

### Kill Switch C5
- **File-backed shared state** (`QNA_KILL_SWITCH_STATE_FILE`) — all processes read/write the same file to prevent split-brain across uvicorn workers.
- `configure_kill_switch_file()` must be called at startup.
- Three levels: NONE (trade) → MONITOR (log) → ACTIVE (VETO all).
- Fail-closed: corrupt/unreadable file → halt.
- Thresholds **must** come from `engine/risk/constants.py`, never hardcoded.

### Risk System
- `RiskCheckGate` is an **alias** for `ConstitutionalRiskGuard` (line 461 of `checks.py`). Both names refer to the same class.
- Weekly-loss veto is enforced via `EngineRiskManager.can_trade()` reading real MT5 PnL.
- **Unit convention (v6.2.0):** ALL P&L values are fractions (0–1). The `/100.0` scaling in RiskManager was removed. KillSwitch and RiskManager now agree on units.

### Hedge Fund Causal Bias Filtering
All 10 core + 200+ evolved providers apply 3-level bias: **BOOST** (+0.15), **REDUCE** (-0.15), **BLOCK** (confidence → 0).
Pipeline `macro_context.py` is a safety-net filter for non-HF signals only — not a second filter on HF providers.

## Testing Quirks
- **`conftest.py` overrides `DATABASE_URL`** at import time to `sqlite+aiosqlite:///test_qna.db`.
- `asyncio_mode = "auto"` — no need for `@pytest.mark.asyncio` on async tests.
- Test discovery paths (from `pyproject.toml`): `tests/` and `quant_nanggroe/tests/`.
- 1 ccxt-dependent test is skipped without env setup; core suite passes without it.
- Coverage enforced at 50% in CI (`--cov-fail-under=50`).

## Toolchain Config
| Tool | Setting |
|------|---------|
| ruff | line-length 120, select E/F/I |
| mypy | strict=true, disallow_untyped_defs=true |
| pre-commit | ruff --fix only |
| pytest | asyncio_mode=auto, testpaths=["tests","quant_nanggroe/tests"] |

## Gotchas
- **JWT sentinel:** Default `QNAI_JWT_SECRET=__UNSET_QNAI_JWT_SECRET__` causes boot refusal. Must set a real value.
- **Telegram:** `ensure_telegram()` must be called at startup; fail-closed (`QNAConfigurationError`).
- **Exchange clients:** 10 REST clients lazy-wired via `ExchangeFactory.create_rest_client(name)`. ccxt has a lazy proxy in `exchange/__init__.py`.
- **CircleCI config is stale** (uses node image for a Python project) — GitHub Actions is the real CI.
- **Dashboard Next.js** needs `npm run build` in `dashboard/`; the HTML dashboard at `/dashboard.html` works out of the box.
- **SSL verification:** Controlled via `QNAI_SSL_VERIFY` env var. Default is 1 (verify). Set `QNAI_SSL_VERIFY=0` only in isolated environments. Affects 10+ files (brokers, exchange clients, webhooks).
- **Credentials:** `.secrets-local/` deleted. `config/mt5_accounts.yaml` deprecated. All credentials via env vars. Encryption key `QNAI_ENCRYPTION_KEY` for at-rest secrets.
- **CausalContext:** Causal engine wiring is via `CausalContext` dataclass (not env vars). See `engine/causal/context.py`.
- **ExecutionManager.set_broker_handle():** Public method added in v6.2.0. Builder uses this instead of calling private `_risk_manager.attach_mt5_handle()`. Old method name removed.
- **Evolver backtest:** `StrategyEvolver` now uses `WalkForwardAnalyzer.analyze_strategy()` with real strategy instantiation — no more mock jitter.

## What Not to Change Without Approval
- API response envelope and endpoint paths.
- Risk engine logic (`engine/risk/` — Kelly, VaR, drawdown, kill switch thresholds). Thresholds from `constants.py` only.
- Pipeline mode-routing (`pipeline/orchestrator.py`).
- State file format in `paper_state/`.
- Agent registration in `qna.py` (`DEFAULT_AGENTS` dict).

## Docs
- 58+ numbered docs in `docs/` (00–51 + ADRs).
- Stale docs go to `docs/archive/`.
- Doc changes accompany code changes in the same commit.
- ADR format for architecture decisions in `docs/11_DECISIONS.md`.
