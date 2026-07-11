# QNA Architecture Report

**Generated:** 2026-07-10 (refreshed)
**Tool:** `scripts/qna-architect.py` (pure stdlib, AST-parser) + manual reconciliation
**Repo:** Quant-Nanggroe-AI

> **Single source of truth:** [`ARCHITECTURE.md`](../ARCHITECTURE.md) (root) — comprehensive
> design, 5-layer stack, data flow, deployment topology. This report is the quantitative
> snapshot; `docs/ARCHITECTURE.md` is a redirect stub to the root doc.

---

## 1. Overview

| Metric | Value |
|--------|-------|
| Python files scanned | 429 |
| Total LOC | 117,695 |
| API route modules | 22 |
| API endpoints | 83 (GET/POST across market, trading, portfolio, backtest, options, signals, agents, monitor, etc.) |
| Circular imports | **0** |
| Missing imports | **0** |
| Test files | 100+ (`tests/`), 5,237 collected |
| Test status | 115 core smoke/backtest/risk pass; legacy persona/colony/organism tests removed |

The codebase is a mature autonomous quant hedge-fund OS: clean import graph (no cycles),
layered deterministic decision stack, multi-agent council, paper-trading daemon with
regime awareness, and a zero-build vanilla-JS dashboard served at `/`.

---

## 2. Package Structure

| Package | Files | LOC | % of Codebase |
|---------|-------|-----|---------------|
| `engine/` | 187 | 54,827 | 46.6% |
| `agents/` | 92 | 21,539 | 18.3% |
| `exchange/` | 24 | 13,567 | 11.5% |
| `mcp/` | 5 | 3,981 | 3.4% |
| `memory/` | 8 | 3,669 | 3.1% |
| `api/` | 30 | 4,458 | 3.8% |
| `data/` | 20 | 4,356 | 3.7% |
| `security/` | 6 | 1,861 | 1.6% |
| `database/` | 7 | 1,425 | 1.2% |
| `types/` | 8 | 844 | 0.7% |
| `connectors/` | 4 | 753 | 0.6% |
| `core/` | 3 | 422 | 0.4% |

---

## 3. Runtime Topology

```
                        ┌─────────────────────────────┐
   Browser / Telegram → │  FastAPI (app.py, :8000)   │
                        │  ├─ AuthMiddleware (dev-mode)│
                        │  ├─ 22 route modules (83 API)│
                        │  └─ StaticFiles → / (dashboard)
                        └──────────────┬──────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              ▼                        ▼                        ▼
      ┌──────────────┐       ┌─────────────────┐      ┌──────────────────┐
      │ Agent Council │       │  Quant Engine   │      │  Paper Daemon    │
      │ (risk+compli- │       │  (regime, strat,│      │  (qna-paper-     │
      │  ance loops)  │       │   risk, portfolio)│     │   daemon.py)     │
      └──────────────┘       └─────────────────┘      └──────────────────┘
              │                        │                        │
              └────────────────────────┼────────────────────────┘
                                       ▼
                          ┌─────────────────────────┐
                          │ Graphify KG · Memory MCP │
                          │ SQLite warehouse (.qna)  │
                          └─────────────────────────┘
```

---

## 4. Decision Stack (canonical)

1. **Layer 0 — Contextual Grounding**: MarketService feeds observable numeric data.
2. **Layer 1 — Regime Engine**: bear/bull/sideways gate; scales risk multiplier.
3. **Layer 2 — Multi-Agent Sensors**: emit normalized pressure (0.0–1.0), no BUY/SELL.
4. **Layer 3 — Pressure Normalization**: compiles agent outputs into a single signal.
5. **Layer 4 — Decision Synthesis**: exclusive trade-decision authority.
6. **Risk Guardian**: constitutional rules + correlation monitor bound every action.

---

## 5. Open Concerns (from 50-Agent Council — see council output)

- Synthetic data path warns PnL is meaningless without `--live-data` + valid key.
- `archive/` (352 files) removed; consolidate `docs/auto/*` audit artifacts.
- 162 ruff lint findings (I001/E402 dominant) — non-blocking, scheduled for fix.
- `.env` exchange keys still placeholder — paper daemon runs simulated only.

---

*Regenerate: `python scripts/qna-architect.py` (updates `docs/auto/graphs/architecture.mmd`).*
