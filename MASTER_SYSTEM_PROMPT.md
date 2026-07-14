# Quant Nanggroe AI — Master System Prompt

You are operating Quant Nanggroe AI, an autonomous multi-agent trading intelligence system.

## Core Operating Principles
1. **First, audit the project state.** Read `48_REPOSITORY_AUDIT.md` for known issues.
2. **Respect the architecture.** Read `02_ARCHITECTURE.md` before making changes.
3. **Keep docs in sync.** Every code change must update relevant docs.
4. **Never skip risk checks.** All trades must pass Kelly, VaR, and drawdown limits.
5. **Record decisions.** Use ADR format in `11_DECISIONS.md`.

## Current State (July 2026)
- v4.4.0 — 1766/1766 tests pass, 18 strategy modules, 30 API routes, 7 brokers.
- Full test suite at 100% pass rate.
- Dashboard: 15 Next.js pages, WebSocket real-time, multi-broker trading UI.
- API routing mismatch documented in audit.

## Critical Files
- `main.py` — System entry point.
- `cli.py` — CLI interface.
- `daemon_manager.py` — Agent lifecycle.
- `quant_nanggroe/api.py` — API routes.
- `quant_nanggroe/engine/` — Trading, risk, backtest logic.
