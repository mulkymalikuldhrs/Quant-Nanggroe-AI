# Claude-Specific Instructions — Quant Nanggroe AI v6.1.0

## Entry Point
- **Single**: `qna.py` — modes: `unified|api|daemon|hedge|status|stop`
- All legacy launchers archived to `archive/launchers/`

## Key Files — Updated v6.1.0
- `qna.py` — Single entry point (unified launcher).
- `quant_nanggroe/engine/standalone.py` — Zero-dependency autonomous runner.
- `quant_nanggroe/api/app.py` — FastAPI factory (179+ endpoints).
- `quant_nanggroe/engine/agentic/autonomous.py` — Autonomous pipeline orchestration.
- `quant_nanggroe/engine/risk/` — 9-checkpoint risk gate + **DCC-GARCH** (dynamic correlation) 🆕
- `quant_nanggroe/engine/causal/` — **Causal engine suite** (bias, MSI, COT, SMT, thesis drift) 🆕
- `quant_nanggroe/hedge_fund/signals/core.py` — 10 providers with **causal bias filtering** 🆕
- `quant_nanggroe/pipeline/macro_context.py` — **Macro context provider** 🆕
- `quant_nanggroe/tests/test_dcc_garch.py` — **47 DCC-GARCH unit tests** 🆕
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

## Audit Status (Round 2 Complete)
- **Last Full Audit:** 2026-07-26
- **Round 1:** 56 findings — ALL FIXED
- **Round 2:** 55+ findings (18 Critical, 22 High, 15 Medium) — 95%+ FIXED
  - **Critical fixed this session:** Phantom `from strategy_registry import` imports in 5 files
- **Score:** 52 → 87/100
- **Test Suite:** 107/108 pass (1 ccxt skip)
- **Remaining:** Triple registry consolidation, Signal type dedup, credential encryption (require architectural decisions)
