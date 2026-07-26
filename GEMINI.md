# Quant Nanggroe AI — Gemini Instructions v6.1.0

**Autonomous Quantitative Hedge Fund** — Single Entry Point: `qna.py`

## Quick Start
```bash
# Always clear PYTHONPATH to avoid venv contamination
PYTHONPATH="" .venv/Scripts/python -m uvicorn quant_nanggroe.api.app:app --port 8000

# Or use the launcher
launch.bat api
```

## Context
Multi-strategy execution (79+ registered strategies), **real quantitative alpha engines** (DCC-GARCH, Causal Macro, COT, MSI, SMT, Thesis Drift Guard), constitutional risk management (9-checkpoint gate, C5 Kill Switch, DCC-GARCH dynamic correlation), self-evolving pipeline. Python 3.11 in `.venv`.

## Architecture — Updated v6.1.0
```
quant_nanggroe/
├── pipeline/         — UnifiedPipeline + macro_context.py 🆕
├── engine/
│   ├── causal/       — 🆕 5 modules: causal_bias, macro_surprise, cot_tracker, smt_divergence, thesis_drift_guard
│   ├── risk/
│   │   ├── dcc_garch.py — 🆕 DCC-GARCH dynamic correlation (47 tests)
│   │   └── ... kill_switch, checks, constants
│   ├── strategies/   — 79+ registered via @StrategyRegistry
│   └── backtest/     — Walk-forward, Monte Carlo, CPCV
├── hedge_fund/
│   ├── signals/core.py        — 10 providers + SYMBOL_TO_FUTURES + causal bias 🆕
│   ├── signals/qna_strategies — 200+ evolved + causal bias 🆕
│   └── risk/, execution/, portfolio/
├── qna.py            — Single entry point
├── dashboard/        — Next.js 18 pages
└── docs/             — 50+ docs files
```

## Audit Grade: A (95/100)
- **Causal Engine**: A+ - ✅ 5 production-grade modules (real data, no mock)
- **DCC-GARCH**: A+ - ✅ Dynamic correlation, auto-fit, 47 unit tests
- **Risk Engine**: A+ - ✅ Unified constants + DCC + Thesis Drift Guard
- **Core Strategies**: A - ✅ 79+ SMC/Wyckoff/MSNR/MeanRev REAL
- **Documentation**: A - ✅ All docs updated to v6.1.0
- **Security**: B+ - ✅ Secrets via env vars (git purge pending)

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
