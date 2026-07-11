# QNA Architecture

> **Canonical architecture: [`/ARCHITECTURE.md`](../ARCHITECTURE.md)** (root, 536 lines — comprehensive design, 5-layer stack, data flow, deployment topology, design decisions).

> **Quantitative snapshot: [`ARCHITECTURE_REPORT.md`](ARCHITECTURE_REPORT.md)** (fresh stats: 429 files, 117k LOC, 83 API endpoints, package breakdown, runtime topology).

This file is the navigation stub. Always read the root `ARCHITECTURE.md` for system design.

## Quick Links
- [`ARCHITECTURE.md`](../ARCHITECTURE.md) — Full architecture (source of truth)
- [`ARCHITECTURE_REPORT.md`](ARCHITECTURE_REPORT.md) — Quantitative snapshot
- [`README.md`](../README.md) — Overview, quick start, API reference
- [`docs/RUNBOOK.md`](RUNBOOK.md) — Operations runbook
- [`docs/API.md`](API.md) — API documentation

## System At A Glance
- **FastAPI backend** — 83 API endpoints across 22 route modules, auth middleware, Prometheus metrics
- **Zero-build dashboard** — vanilla HTML/JS at `/` (dev-mode auth when no `QNAI_API_KEY`)
- **Paper trading daemon** — regime-based strategy, risk + compliance agent loops
- **Multi-agent AI council** — governance, debate, pressure-based decision synthesis
- **Graphify knowledge graph** — 1,433 source files indexed
- **Test suite** — 5,237 collected; core smoke/backtest/risk critical path green
