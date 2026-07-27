# Quant Nanggroe AI — Gemini Instructions v6.2.0

**Autonomous Quantitative Hedge Fund** — Single Entry Point: `qna.py`

## Quick Start
```bash
# Always clear PYTHONPATH to avoid venv contamination
PYTHONPATH="" .venv/Scripts/python -m uvicorn quant_nanggroe.api.app:app --port 8000

# Or use the launcher
launch.bat api
```

## Context
Multi-strategy execution (79+ registered via @StrategyRegistry.register), **real quantitative alpha engines** (DCC-GARCH, Causal Macro, COT, MSI, SMT, Thesis Drift Guard, CausalContext dataclass), constitutional risk management (9-checkpoint gate, C5 Kill Switch, DCC-GARCH dynamic correlation, unified PnL fractions), self-evolving pipeline with real WalkForwardAnalyzer backtest (no mock). Python 3.11 in `.venv`. Security: QNAI_SSL_VERIFY env guard, `.secrets-local/` deleted, env-var credentials only. Walk-forward metadata store renamed to `WalkForwardRegistry` (v6.2.0).

## Architecture — Updated v6.2.0
```
quant_nanggroe/
├── pipeline/         — UnifiedPipeline + macro_context.py
├── engine/
│   ├── causal/       — 5 modules + CausalContext dataclass (v6.2.0)
│   ├── risk/
│   │   ├── dcc_garch.py — DCC-GARCH dynamic correlation (47 tests)
│   │   ├── manager.py   — set_broker_handle() public, PnL fractions unified
│   │   └── ... kill_switch, checks, constants
│   ├── strategies/   — 79+ registered via @StrategyRegistry.register
│   ├── strategy/registry.py — WalkForwardRegistry (renamed v6.2.0)
│   └── backtest/     — Walk-forward, Monte Carlo, CPCV (NameError fixed)
├── hedge_fund/
│   ├── signals/core.py        — 10 providers + SYMBOL_TO_FUTURES + causal bias
│   ├── signals/qna_strategies — 200+ evolved + causal bias
│   └── risk/, execution/, portfolio/
├── qna.py            — Single entry point (standalone.py deleted)
├── dashboard/        — Next.js 18 pages
└── docs/             — 50+ docs files
```

## Audit Grade: A (94/100) — v6.2.0
- **P0 Deep Clean**: A+ - ✅ 8 P0 fixes (Security, Backtest, Architecture, PnL, Naming, Evolver, Execution, Causal)
- **Security**: A - ✅ QNAI_SSL_VERIFY env guard, `.secrets-local/` deleted, env-var creds only
- **Causal Engine**: A+ - ✅ 5 production-grade modules + CausalContext dataclass
- **DCC-GARCH**: A+ - ✅ Dynamic correlation, auto-fit, 47 unit tests
- **Risk Engine**: A+ - ✅ Unified constants + DCC + Thesis Drift Guard + unified PnL fractions
- **Core Strategies**: A - ✅ 79+ via @StrategyRegistry.register
- **Documentation**: A - ✅ All docs updated to v6.2.0

## Known Gaps
1. **MT5 Terminal** must run manually — no cron-to-live wiring
2. **Dashboard build** on Vercel CI only
3. **Git history has stale secrets** — force push after credential rotation
4. **Live COT/MSI auto-fetch** — cron-based data refresh pending

## Single Entry Point
- `python qna.py [unified|api|daemon|hedge|status|stop]`
- `launch.bat [api|cli|daemon|test|status]`

## Critical: PYTHONPATH Contamination
Hermes venv leaks PYTHONPATH → pydantic-core mismatch. RESOLVED via launch.bat.
See AGENTS.md for full documentation.
