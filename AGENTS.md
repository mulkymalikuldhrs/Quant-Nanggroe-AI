# AGENTS.md — Quant Nanggroe AI (Quant Nation) v15.4.0

## Before Anything
Read `docs/QNA_COMPLETE_ARCHITECTURE_2026-07-29.md` — complete mermaid graph of ALL 678 .py files, 4 remotes, 8 scorers wired, MTF+Evolver, pipeline 7-stage refactor, E:\ sources, dashboard, blockers.
Read `QNA_AGENT_STATE.md` — resume from NEXT ACTIONS.
Read `docs/Rencana.md` — execution plan + Session 9 progress + evolution loop blueprint.
Read `docs/STATUS.md` — doc contradictions map (which docs are STALE vs CURRENT).
Read `docs/research_quant_scoring.md` — quant best practices (confidence mapping, walk-forward, COT usage, alt data).

## Critical Gotchas
- **PYTHONPATH must be empty** — Hermes venv leaks `pydantic_core` crashes.
  Use `launch.bat`, `qna.bat`, or `PYTHONPATH="" .venv/Scripts/python ...`
- **QNAI_JWT_SECRET** required for API boot (fail-closed).
- **Secrets: env vars only** — never hardcode. No `.secrets-local/`, no plaintext YAML.
- **Hardware:** i7-10th gen, 16GB RAM, no GPU. No cloud compute assumed.
- **C5 KillSwitch** — cross-process shared state via `QNA_KILL_SWITCH_STATE_FILE`.
- **numpy 2.5.1** ✅ in .venv (reinstalled). np.clip replaced with `_clamp()` in scoring files.
- **pytest works** ✅ — 173+ tests pass (scoring + kill switch + risk + evolution 68 new)
- **MT5 live connected** — Valetax demo account 372044706, `history_deals_get()` works
- **Evolution loop** — 8 files in `engine/evolution/`, integrated into `run_once()` post-execute
- **1079 providers** — 77 engine strategies + 992 mue-x + 10 core feed the aggregator

## ⚠️ CRITICAL GAP — Scoring Engine WIRED (Session 7-8-9)
8 scorers (100% weight) exist in `quant_nanggroe/core/scoring/` — ✅ **WIRED** in `run_once()`.
FusionEngine.evaluate() called after aggregate(), before ConfluenceScorer.
Includes PositioningScorer from CFTC COT API + hidden-regime fallback.
Evolution loop: journal + scheduler + scanner + disabler + weight_updater — all integrated.

## Exact Commands
```
# Entry point (single)
python qna.py [unified|api|daemon|hedge|status|stop]

# Run
launch.bat api              # FastAPI on :8000
launch.bat daemon           # Background daemon
launch.bat dashboard        # Next.js on :3000
guardian_cli.py --once      # Guardian watchtower (1 pass)

# Tests
.venv/Scripts/python -m pytest tests/test_kill_switch.py -v --tb=short
.venv/Scripts/python -m pytest tests/test_risk_checks.py -v --tb=short
.venv/Scripts/python -m pytest tests/test_evolution_journal.py tests/test_evolution_scheduler.py tests/test_performance_scanner.py -v

# Lint / Typecheck
ruff check quant_nanggroe/           # line-length=120, select E/F/I
mypy quant_nanggroe/ --ignore-missing-imports

# Dashboard
cd dashboard && npm run dev          # Next.js 16 on :3000

# Package management
uv sync                              # not pip, not poetry
```

## Key Directories
| Path | Purpose |
|------|---------|
| `quant_nanggroe/engine/strategies/` | 84 strategies via `@StrategyRegistry.register` |
| `quant_nanggroe/engine/risk/` | KillSwitch C5, DCC-GARCH, VaR, Kelly, unified constants (25 files) |
| `quant_nanggroe/hedge_fund/portfolio/main.py` | run_once() with evolution loop post-execute |
| `quant_nanggroe/engine/causal/` | Causal Macro Engine suite (14 files) |
| `quant_nanggroe/pipeline/` | UnifiedPipeline (auto mode-routing, 8 files) |
| `quant_nanggroe/core/scoring/` | 8 scorers + FusionEngine + MTFEngine + WeightEvolver — **ALL WIRED** |
| `quant_nanggroe/engine/evolution/` | **NEW:** journal, scheduler, scanner, disabler, weight_updater, config (8 files) |
| `quant_nanggroe/providers/` | **NEW:** hidden_regime_provider + news_provider (3-tier each) |
| `quant_nanggroe/engine/guardian/` | Self-healing watchtower (Hermes cron 5min) |
| `quant_nanggroe/exchange/clients/` | 10 REST exchange clients |
| `quant_nanggroe/exchange/solana/` | SolanaBroker + Jupiter V6 (functional) |
| `quant_nanggroe/agents/` | 16 registered agents |
| `quant_nanggroe/api/routes/evolution.py` | **NEW:** evolution API endpoints |
| `quant_nanggroe/hedge_fund/signals/engine_strategies.py` | **NEW:** auto-discovers 77 engine strategies |
| `E:\hidden-regime\` | COT analysis, regime evolution — **EXTRACTED** |
| `E:\mue-x\genes\qna_strategies\` | 992 evolved strategy providers — **EXTRACTED** |
| `C:\e\archived\AI-Trader\` | TTL cache, news pipeline — **EXTRACTED** |
| `C:\e\archived\TradingAgents\` | LangGraph multi-agent — **EXTRACTED** (3 components) |

## Wired Modules (Verified in run_once())
- **ScreenerOrchestrator** — `engine/screener/orchestrator.py` ✅
- **ConfluenceScorer** — `engine/portfolio/confluence_scorer.py` ✅
- **RiskParityAllocator** — `engine/portfolio/risk_parity_bridgewater.py` ✅
- **StressVaRCalculator** — `engine/stress_testing/var_cvar.py` ✅
- **MatrixProfileDetector** — `engine/pattern_recorder/matrix_profile.py` ✅
- **FusionEngine** — `core/scoring/fusion_engine.py` ✅ **WIRED**
- **MultiTimeframeEngine** — `core/scoring/mtf_engine.py` ✅ **WIRED** (Session 8)
- **WeightEvolver** — `core/scoring/evolver.py` ✅ **WIRED** (Session 8)
- **EvolutionLoop** — `engine/evolution/*.py` ✅ **WIRED** (Session 9)
- **HiddenRegimeProvider** — `providers/hidden_regime_provider.py` ✅ **WIRED** → PositioningScorer
- **NewsProvider** — `providers/news_provider.py` ✅ **WIRED** → SentimentScorer
- **EngineStrategyProvider** — `hedge_fund/signals/engine_strategies.py` ✅ **77 strategies wired**

### Actual Pipeline Order (post-Session 9)
1. _pipeline_connect — MT5 + walkforward gate
2. _pipeline_discover — symbol, account, positions
3. _pipeline_trail — trail open positions (skip vote if open)
4. _pipeline_vote — causal → screen → agg (1079 providers) → fusion → mtf → confluence
5. _pipeline_risk_check — sizing → kill switch → risk guard
6. _pipeline_execute — order placement + post-trade (evolver, var, pattern)
7. **Evolution loop** — record closed trades, check triggers, scan performance, disable/promote
8. _pipeline_cleanup — MT5 shutdown

## Non-Negotiable Rules
- **Source code is truth. Docs are hearsay.** Verify every doc claim against imports/calls.
- **No silent deletion.** List in `QNA_AGENT_STATE.md` under PROPOSED FOR DELETION + owner sign-off.
- **Wiring > new features.** Connect what exists. Don't create duplicate #5 of anything.
- **No completion claims without evidence** (pytest output, call graph trace, execution log).
- **Single source of truth per concern:** entry point, registry, risk, execution, data provider.
- **State file protocol:** Update `QNA_AGENT_STATE.md` end of every session — verified (file:line), changed, next actions.

## Anti-Patterns
- Writing "vFinal" / "vNext" files instead of fixing existing ones
- Trusting `CLAUDE.md` / `*_STATUS.md` / `*_AUDIT.md` without independent verification
- Expanding scope (new strategies, agents, asset classes) before dedup is complete
- Ending session without updating `QNA_AGENT_STATE.md`

## Communication
End every response to owner with structured format: verified evidence → changed/decided → blocked on owner → next. No celebratory framing.

## Next (Session 9 completed items)
- ✅ P0 fixes (7 items: FRED key, bare except, MTF REDUCE, live engine, engine/scoring/ delete, dual pipeline, confidence)
- ✅ MT5 live connected (Valetax demo, 29 closed trades)
- ✅ 1079 providers wired (77 engine + 992 mue-x + 10 core)
- ✅ Evolution loop integrated (8 files + 68 tests + API + dashboard)
- ✅ E:\ extraction (hidden-regime, news, loop-engineering, tradingagents)
- ✅ qna.py pipeline bug fixed (asyncio.run → direct call, .get() → getattr)
- ✅ Root cleaned, git committed, docs flagged
- ⏳ credentials.md.txt — owner action required (backup + rm + rotate)
- ⏳ engine/factors/ 450+ alpha factors — not wired (enhancement, not blocker)
- ⏳ engine/rl/ — needs PyTorch for real training (scaffold only)
- ⏳ docs cleanup — 107 → ~20 files (STATUS.md has contradiction map)
