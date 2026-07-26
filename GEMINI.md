# Quant Nanggroe AI — Gemini Instructions v6.0.0

**Autonomous Quantitative Hedge Fund** — Single Entry Point: `qna.py`

## Quick Start
```bash
# Always clear PYTHONPATH to avoid venv contamination
PYTHONPATH="" .venv/Scripts/python -m uvicorn quant_nanggroe.api.app:app --port 8000

# Or use the launcher
launch.bat api
```

## Context
Multi-strategy execution (79+ registered strategies via @StrategyRegistry, 139 legacy strategies archived), constitutional risk management (9-checkpoint gate, Kill Switch dual-path, weekly loss veto), self-evolving pipeline. Python 3.11 in `.venv`.

## Architecture
```
quant_nanggroe/
├── api/              — FastAPI (179 endpoints, JWT-guarded, fail-closed)
├── engine/
│   ├── backtest/     — Walk-forward (CPCV/rolling/anchored, 806 lines)
│   ├── risk/         — 108/108 checks, KillSwitch dual-path, weekly veto
│   ├── strategies/   — Canonical: 28 strategies (SMC/Wyckoff/MSNR/MeanRev — ALL REAL)
│   └── strategy/
│       └── strategies/  ← Bridge shim (backward compat → canonical)
├── archive/          — strategies_legacy/ (138 archived), root-dirs/, creds/
├── qna.py            — Single entry point
├── launch.bat        — Clean env launcher
├── dashboard/        — Next.js 18 pages (build on Vercel CI)
└── docs/             — 50 docs (00-49), 20 stubs filled in latest audit
```

## Audit Grade: A- (91/100)
- **Risk Engine**: A - ✅ 108/108 checks, fail-closed, dual-path KillSwitch
- **Core Strategies**: A - ✅ SMC/Wyckoff/MSNR/MeanRev REAL full signal gen
- **Walk-forward**: A - ✅ 806 lines CPCV/rolling/anchored, smoke test passes
- **Documentation**: A - ✅ 50/50 docs filled
- **Security**: B+ - ⚠️ GIT PURGE NEEDED (stale secrets in history)

## Known Gaps
1. **MT5 Terminal** must run manually — no cron-to-live wiring on this host
2. **Dashboard build** on Vercel CI only (not Windows-tested)
3. **Stale secrets in git history** — force push after credential rotation
4. **Walk-forward fine-tuning** for core 4 strategies needs market data fetch on this host

## Single Entry Point
- `python qna.py [unified|api|daemon|hedge|status|stop]` — primary entry point
- `launch.bat [api|cli|daemon|test|status]` — clean PYTHONPATH launcher
- `PYTHONPATH="" .venv/Scripts/python -m ...` — raw alternative

## Critical: PYTHONPATH Contamination
Hermes venv leaks PYTHONPATH → pydantic-core mismatch. RESOLVED via launch.bat.
See AGENTS.md for full documentation.
