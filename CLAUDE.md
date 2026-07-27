# Claude-Specific Instructions — Quant Nanggroe AI v6.2.0

## Entry Point
- **Single**: `qna.py` — modes: `unified|api|daemon|hedge|status|stop`
- All legacy launchers archived to `archive/launchers/`

## Key Files — Updated v6.2.0
- `qna.py` — Single entry point (unified launcher).
- `quant_nanggroe/api/app.py` — FastAPI factory (179+ endpoints).
- `quant_nanggroe/engine/agentic/autonomous.py` — Autonomous pipeline orchestration.
- `quant_nanggroe/engine/risk/` — 9-checkpoint risk gate + DCC-GARCH (dynamic correlation). PnL fractions unified.
- `quant_nanggroe/engine/causal/` — Causal engine suite (bias, MSI, COT, SMT, thesis drift) + **CausalContext** dataclass.
- `quant_nanggroe/engine/causal/context.py` — **CausalContext** dataclass (v6.2.0, replaces env-var wiring).
- `quant_nanggroe/engine/strategies/registry.py` — StrategyRegistry (class registry, unchanged).
- `quant_nanggroe/engine/strategy/registry.py` — **WalkForwardRegistry** (renamed from StrategyRegistry in v6.2.0, walk-forward metadata store).
- `quant_nanggroe/engine/strategies/strategy_evolver.py` — Uses **real WalkForwardAnalyzer** (no mock).
- `quant_nanggroe/engine/risk/manager.py` — **set_broker_handle()** public method (v6.2.0).
- `quant_nanggroe/hedge_fund/signals/core.py` — 10 providers with causal bias filtering.
- `quant_nanggroe/pipeline/macro_context.py` — Macro context provider.
- `quant_nanggroe/tests/test_dcc_garch.py` — 47 DCC-GARCH unit tests.
- `pyproject.toml` — Dependencies with `uv`.

## Tools Available
- `docs/` — 58 documents (00-49).
- `archive/` — Legacy files, launchers, reports.
- `dashboard/` — Next.js monitoring UI (needs `npm run build`).

## Response Style
- Always check root-level docs first: README → AGENTS → ARCHITECTURE → CHANGELOG → TODO.
- Start with project state detection per AI-Engineering-OS.
- Reference specific docs by their number prefix in `docs/`.
- Flag uncertainties explicitly.
- Never create new root-level entry points. `qna.py` is THE entry point.

## Audit Status (v6.2.0 — P0 Deep Clean Complete)
- **Last Full Audit:** 2026-07-27
- **Round 1:** 56 findings — ALL FIXED
- **Round 2:** 55+ findings (18 Critical, 22 High, 15 Medium) — 95%+ FIXED
- **Round 3 (v6.2.0):** 8 P0 findings — ALL RESOLVED
  - Security: `.secrets-local/` deleted, `QNAI_SSL_VERIFY` guard, env-var creds
  - Backtest: NameError + return-None fixed
  - Architecture: `__getattr__` removed, `standalone.py` deleted
  - PnL: Fractions (0-1) unified
  - Naming: `StrategyRegistry` → `WalkForwardRegistry`
  - Evolver: Real `WalkForwardAnalyzer.analyze_strategy()` (no mock)
  - Execution: `set_broker_handle()` public API
  - Causal: `CausalContext` dataclass
- **Score:** 87 → 94/100
- **Test Suite:** 107/108 pass (1 ccxt skip)
- **Remaining:** Triple registry consolidation, Signal type dedup (require architectural decisions)
