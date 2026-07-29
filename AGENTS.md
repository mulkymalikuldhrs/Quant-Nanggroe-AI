# AGENTS.md — Quant Nanggroe AI (Quant Nation) v15.3.0

## Before Anything
Read `docs/QNA_COMPLETE_ARCHITECTURE_2026-07-29.md` first — complete mermaid graph of ALL 678 .py files, 4 remotes, 8 scorers wired, MTF+Evolver, pipeline 7-stage refactor, E:\ sources, dashboard, blockers.
Read `QNA_AGENT_STATE.md` — resume from NEXT ACTIONS.

## Critical Gotchas
- **PYTHONPATH must be empty** — Hermes venv leaks `pydantic_core` crashes.
  Use `launch.bat`, `qna.bat`, or `PYTHONPATH="" .venv/Scripts/python ...`
- **QNAI_JWT_SECRET** required for API boot (fail-closed).
- **Secrets: env vars only** — never hardcode. No `.secrets-local/`, no plaintext YAML.
- **Hardware:** i7-10th gen, 16GB RAM, no GPU. No cloud compute assumed.
- **C5 KillSwitch** — cross-process shared state via `QNA_KILL_SWITCH_STATE_FILE`.
- **numpy broken** in .venv — Python 3.14 removed `np.clip`. Replace with `max(min(x,100),-100)`.
- **pytest env broken** — `langsmith` plugin crashes. `pip uninstall langsmith` or install httpx.

## ⚠️ CRITICAL GAP — Scoring Engine NOT Wired (SESSION 7: FIXED)
7 scorers (90% weight) exist in `quant_nanggroe/core/scoring/` — ✅ **NOW WIRED** in `run_once()` at `main.py:365-437`. FusionEngine.evaluate() called after aggregate(), before ConfluenceScorer. Includes PositioningScorer from hidden-regime COT data.

## Exact Commands
```
# Entry point (single)
python qna.py [unified|api|daemon|hedge|status|stop]

# Run
launch.bat api              # FastAPI on :8000
launch.bat daemon           # Background daemon
guardian_cli.py --once      # Guardian watchtower (1 pass)

# Tests (env broken — fix first)
.venv/Scripts/python -m pytest tests/test_kill_switch.py -v --tb=short
.venv/Scripts/python -m pytest tests/test_risk_checks.py -v --tb=short

# Lint / Typecheck
ruff check quant_nanggroe/           # line-length=120, select E/F/I
mypy quant_nanggroe/ --ignore-missing-imports

# Dashboard
cd dashboard && npm run dev          # Next.js 16 on :3000

# Package management
uv sync                              # not pip, not poetry

# E:\ extraction targets
# E:\hidden-regime\hidden_regime\analysis\regime_evolution.py → COT analyzer
# E:\mue-x\genes\qna_strategies\ → 992 evolved providers
# C:\e\archived\AI-Trader\service\server\market_intel.py → TTL cache
```

## Key Directories
| Path | Purpose |
|------|---------|
| `quant_nanggroe/engine/strategies/` | 84 strategies via `@StrategyRegistry.register` |
| `quant_nanggroe/engine/risk/` | KillSwitch C5, DCC-GARCH, VaR, Kelly, unified constants (25 files) |
| `quant_nanggroe/hedge_fund/portfolio/main.py` | 7-stage pipeline: `run_once()` 310 lines |
| `quant_nanggroe/engine/causal/` | Causal Macro Engine suite (14 files) |
| `quant_nanggroe/pipeline/` | UnifiedPipeline (auto mode-routing, 8 files) |
| `quant_nanggroe/core/scoring/` | 8 scorers + FusionEngine + MTFEngine + WeightEvolver — **ALL WIRED** |
| `quant_nanggroe/engine/guardian/` | Self-healing watchtower (Hermes cron 5min) |
| `quant_nanggroe/exchange/clients/` | 10 REST exchange clients |
| `quant_nanggroe/agents/` | 16 registered agents |
| `E:\hidden-regime\` | COT analysis, regime evolution (untapped) |
| `E:\mue-x\genes\qna_strategies\` | **992 evolved strategy providers** (untapped) |
| `C:\e\archived\AI-Trader\` | TTL cache, news pipeline 1911 lines (untapped) |
| `.bak/py/` | Orphaned code — geopolitics (5 files) worth wiring |
| `archive/` | Orphaned v6.2 artifacts (read-only) |

## Wired Modules (Verified in run_once())
- **ScreenerOrchestrator** — `quant_nanggroe/engine/screener/orchestrator.py` ✅
- **ConfluenceScorer** — `quant_nanggroe/engine/portfolio/confluence_scorer.py` ✅
- **RiskParityAllocator** — `quant_nanggroe/engine/portfolio/risk_parity_bridgewater.py` ✅
- **StressVaRCalculator** — `quant_nanggroe/engine/stress_testing/var_cvar.py` ✅
- **MatrixProfileDetector** — `quant_nanggroe/engine/pattern_recorder/matrix_profile.py` ✅
- **FusionEngine** — `quant_nanggroe/core/scoring/fusion_engine.py` ✅ **WIRED**
- **MultiTimeframeEngine** — `quant_nanggroe/core/scoring/mtf_engine.py` ✅ **WIRED** (Session 8)
- **WeightEvolver** — `quant_nanggroe/core/scoring/evolver.py` ✅ **WIRED** (Session 8)

### Actual 7-Stage Pipeline Order
1. _pipeline_connect — MT5 + walkforward gate
2. _pipeline_discover — symbol, account, positions
3. _pipeline_trail — trail open positions (skip vote if open)
4. _pipeline_vote — causal → screen → agg → fusion → mtf → confluence
5. _pipeline_risk_check — sizing → kill switch → risk guard
6. _pipeline_execute — order placement + post-trade (evolver, var, pattern)
7. _pipeline_cleanup — MT5 shutdown

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

## Next
- Triple registry consolidation (3 registries don't communicate)
- Signal type dedup (5 Signal variants)
- Weekly loss veto on Path-B (P1 gap)
- Verify all 77 strategies instantiate without error