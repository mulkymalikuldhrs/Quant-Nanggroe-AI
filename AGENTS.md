# AGENTS.md — Quant Nanggroe AI

## Before Anything
Read `docs/QNA_AUDIT_REAL_STRUCTURE_2026-07-28.md` first session — still current.
Read `QNA_AGENT_STATE.md` if exists; resume from NEXT ACTIONS. If not, create it.

## Critical Gotchas
- **PYTHONPATH must be empty** — Hermes venv leaks `pydantic_core` crashes.
  Use `launch.bat`, `qna.bat`, or `PYTHONPATH="" .venv/Scripts/python ...`
- **QNAI_JWT_SECRET** required for API boot (fail-closed).
- **Secrets: env vars only** — never hardcode. No `.secrets-local/`, no plaintext YAML.
- **Hardware:** i7-10th gen, 16GB RAM, no GPU. No cloud compute assumed.
- **C5 KillSwitch** — cross-process shared state via `QNA_KILL_SWITCH_STATE_FILE`.

## Exact Commands
```
# Entry point (single)
python qna.py [unified|api|daemon|hedge|status|stop]

# Run
launch.bat api              # FastAPI on :8000
launch.bat daemon           # Background daemon
launch.bat test             # Full test suite
guardian_cli.py --once      # Guardian watchtower (1 pass)

# Tests (PYTHONPATH="" mandatory)
.venv/Scripts/python -m pytest tests/ -v --tb=short
.venv/Scripts/python -m pytest tests/test_kill_switch.py -v
.venv/Scripts/python -m pytest tests/test_risk_checks.py -v

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
| `quant_nanggroe/engine/strategies/` | 77 strategies via `@StrategyRegistry.register` |
| `quant_nanggroe/engine/risk/` | KillSwitch C5, DCC-GARCH, VaR, Kelly, unified constants |
| `quant_nanggroe/hedge_fund/risk/` | gate.py, guard.py (fail-closed secondary) |
| `quant_nanggroe/hedge_fund/portfolio/main.py` | 9-stage pipeline: `run_once()` |
| `quant_nanggroe/engine/causal/` | Causal Macro Engine suite (5 modules) |
| `quant_nanggroe/pipeline/` | UnifiedPipeline (auto mode-routing) |
| `quant_nanggroe/engine/guardian/` | Self-healing watchtower (Hermes cron 5min) |
| `quant_nanggroe/exchange/clients/` | 10 REST exchange clients |
| `quant_nanggroe/agents/` | 16 registered agents incl. 5 geopolitics |
| `archive/` | Orphaned v6.2 artifacts (read-only) |

## Wired Modules (Verified)
- **ScreenerOrchestrator** — `quant_nanggroe/engine/screener/orchestrator.py`
- **ConfluenceScorer** — `quant_nanggroe/engine/portfolio/confluence_scorer.py`
- **RiskParityAllocator** — `quant_nanggroe/engine/portfolio/risk_parity_bridgewater.py`
- **StressVaRCalculator** — `quant_nanggroe/engine/stress_testing/var_cvar.py`
- **MatrixProfileDetector** — `quant_nanggroe/engine/pattern_recorder/matrix_profile.py`

All wired in `run_once()` (lines 281, 308, 352, 429, 447 respectively). Each degrades gracefully on failure.

### 9-Stage Pipeline Order
1. CausalContext (MasterQuantNanggroeEngine)
2. ScreenerOrchestrator (market screen)
3. Aggregate (Bayesian-weighted signal voting)
4. ConfluenceScorer (multi-signal fusion)
5. Position sizing + RiskParityAllocator
6. KillSwitch C5 check (real PnL from MT5)
7. risk_guard_approve (constitutional gate)
8. execute (MT5 order placement, paper fail-closed)
9. StressVaRCalculator + MatrixProfileDetector (post-trade)

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