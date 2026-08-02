# CLAUDE.md

> Claude Code guidance for Quant Nanggroe AI — codebase truth, not docs hearsay.

---

## ◈ v6.1.0 · Quant Nation — REAL-ONLY LIVE

Autonomous quant hedge fund. Python 3.12.13 (.venv312) · Windows · i7-10th · 16GB · no GPU.
**Live MT5:** ValetaxIntl-Live2, login=372044706, balance=$1122.05. **REAL trades, no paper.**

> **Source of truth**: `qna.py:__version__` + `Rencana.md`
> README/AGENTS say v6.1.0 — consistent. Old docs (v4.8.0) are stale.

---

## ▸ How It Works

```
MT5 LIVE (BTC/EUR/XAU.vx) ─┐
                           ├─→ SignalFusion (weighted vote) ─→ RiskManager (9-gate, KillSwitch)
Strategies (77, 6 active) ─┘                                    │ APPROVED
                                                            ┌───┴───┐
                                                            ▼       ▼
                                                  Execution (MT5)   BLOCKED
                                                  Real Ticket
```

**REAL-ONLY:** `SyncPaperBroker` deleted. MT5 down → RuntimeError (fail-closed).

---

## ▸ Commands (VERIFIED)

| Action | Command |
|--------|---------|
| **Run (purified)** | `env -u PYTHONPATH PYTHONPATH=. QNAI_ENCRYPTION_KEY="..." .venv312/Scripts/python.exe -m quant_nanggroe.autonomous_cycle` |
| **Run (LiveEngine)** | `env -u PYTHONPATH PYTHONPATH=. QNAI_ENCRYPTION_KEY="..." .venv312/Scripts/python.exe qna.py live` |
| **Lint** | `ruff check quant_nanggroe/` (line-length=120) |
| **Test** | `.venv312/Scripts/python.exe tests/unit/test_risk_sortino.py` |
| **Deps** | `uv pip install --python .venv312/Scripts/python.exe -r requirements_qna.txt` |


| **Install** | `uv sync` _(not pip, not poetry)_ |

### ▹ Tests

```bash
uv run pytest                              # full suite (~173+ pass, ~150 files)
uv run pytest tests/test_lead_lag.py       # single file
uv run pytest tests/ -k "kill_switch"      # filter
uv run pytest -m "not integration"         # skip API-key tests
```

`asyncio_mode = "auto"` · Fixtures: `sample_closes`, `sample_ohlcv`, `risk_guard`, `kill_switch`

### ⚠ Gotchas

- **`PYTHONPATH=""`** mandatory — Hermes venv leaks `pydantic_core` → crash
- **`QNAI_JWT_SECRET`** required for API boot _(fail-closed)_
- **Sizing (2026-08-02):** `RiskGuard.position_size()` = `equity×risk×kelly / (|entry−SL|×contract_size)` in **LOTS** (was units → always 0.01). No-SL → 0 → fail-closed.
- **SL/TP:** ATR+structure based (`quant_nanggroe/risk_levels.py`), not hardcoded ±%. Clamped to broker `trade_stops_level`.
- **Auth:** `/api/otto/*` no longer excluded from auth (2026-08-02). All `/api/*` behind JWT/API-key.
- **MT5 live** connected · Valetax demo · `history_deals_get()` works
- **Evolution loop** ✅ fixed · `engine/evolution/` 8 files · wired `main.py:922-966`

---

## ▸ Pipeline

```
qna.py ──→ pipeline/factory ──→ hedge_fund/portfolio/main.py:run_once()

  1  MT5 connect / paper fallback         ✅
  2  Gate check — WalkForward             ✅
  3  Symbol selection / trail positions    ✅
  4  Causal context — DXY/ZB macro        ✅  engine/causal/
  5  ScreenerOrchestrator                  ✅  engine/screener/
  6  Aggregate — 1077 providers            ✅  77 engine + 992 mue-x + 8 core
  7  FusionEngine — 10 scorers 100% weight ✅
  8  MultiTimeframeEngine — 4 frames       ✅  HTF/LTF veto
  9  ConfluenceScorer                      ✅
 10  Position sizing + RiskParity          ✅
 11  KillSwitch C5 + RiskGuard             ✅  fail-closed
 12  ExecutionManager.execute_order        ✅  async
 13  Evolution loop                        ✅
```

---

## ▸ Scorers — 10 wired, 100% weight

| Scorer | W% | Data | File |
|--------|----|------|------|
| Macro | 30 | CausalContext regime | `macro_scorer.py` |
| Economic | 20 | FRED API live | `economic_scorer.py` |
| Bond | 10 | ctx dict | `bond_scorer.py` |
| Sentiment | 10 | Fear & Greed live | `sentiment_scorer.py` |
| Technical | 10 | ctx dict | `technical_scorer.py` |
| Positioning | 10 | CFTC COT + hidden-regime | `positioning_scorer.py` |
| Geopolitical | 5 | ctx dict | `geo_scorer.py` |
| Volatility | 5 | ctx dict | `volatility_scorer.py` |
| Crypto | — | crypto-specific | `crypto_scorer.py` |
| News | — | news feed | sentiment sub-module |

> FusionEngine: weighted sum · override if confidence ≥ 60%

---

## ▸ Kill Switch C5

Cross-process via `QNA_KILL_SWITCH_STATE_FILE` JSON · Fail-closed: bad file → ACTIVE

| Level | Action | Reset |
|-------|--------|-------|
| L1 | Block new positions | Auto-expires next day |
| L2 | Close all | `CONFIRM_RESET_AFTER_REVIEW` |
| L3 | Full shutdown | `CONFIRM_RESET_AFTER_REVIEW` |

| Threshold | Value |
|-----------|-------|
| Daily loss | **0.8%** _(not 1.5% as docs claim)_ |
| Weekly loss | 3% |
| Drawdown | 15% |
| Max risk/trade | 0.5% |
| Max position | 10% |
| Max leverage | 3× |
| Max trades/day | 5 |

> Auto-triggers: `engine/risk/constants.py` · Audit: append-only JSONL

---

## ▸ Strategies & Providers

| | Count | Source |
|---|-------|--------|
| Strategy files | 83 | `engine/strategies/` |
| Registered | 83 | `@StrategyRegistry.register` |
| Wired | 77 | `EngineStrategyProvider` |
| MueX providers | 992 | `E:\mue-x\` |
| Core providers | 8 | `registry.py` |
| **Total** | **~1077** | |

---

## ▸ Architecture

### Pipeline entry points _(don't confuse)_

- `pipeline/factory.py` → `create_pipeline()` → `UnifiedPipeline` _(orchestrator.py)_
- `hedge_fund/portfolio/main.py:run_once()` → production path _(module-level singletons)_

### Risk checks

7 checks in `checks.py` _(docs say 9 — correlation & concentration don't exist)_  
`manager.py` is a **6-line stub** — real logic in `checks.py` + `kill_switch.py`

### Registered agents

9 via `@AgentRegistry.register` _(docs say 16 — 7 phantom)_

### Auth roles

`ADMIN` · `TRADER` · `ANALYST` · `VIEWER` — `security/auth.py`

### Asset classes

8: FOREX_MAJOR · FOREX_MINOR · FOREX_EXOTIC · CRYPTO · EQUITY · COMMODITY · INDEX · BOND

### BaseAgent

`run()` · `__call__()` · `invoke_llm()` · `create_output()`  
NO `initialize()` · NO `health_check()` · NO `stop()`

### Types

`quant_nanggroe/types/` — canonical Pydantic v2 · prefer over `pipeline/signal.py`

---

## ▸ Dashboard — Next.js 16

> `dashboard/CLAUDE.md` + `dashboard/AGENTS.md` — read first.  
> **WARNING**: `PRODUCTION_READY.md` has fabricated claims.

| | |
|---|---|
| Framework | Next.js 16.2.9 · React 19.2.4 · Tailwind v4 |
| State | Zustand v5 |
| Charts | Recharts **3** _(not 2 as docs claim)_ |
| Tests | vitest |
| Pages | 24 `page.tsx` |
| API modules | 14 _(docs say 8)_ |

---

## ▸ Phantom References

> Things docs claim exist but **don't**.

| Phantom | Claimed in |
|---------|-----------|
| `engine/factors/` | AGENTS, CLAUDE, COPILOT, CURSOR, GEMINI |
| `config/qna.yaml` · `strategies.yaml` · `risk.yaml` | docs/25 |
| `backups/` · `logs/` · `data/logs/` | docs/24, 31, 33 |
| `FactorRegistry` · `PatternRegistry` | docs/29 |
| `MemoryBus` · `DaemonManager` classes | docs/15, 18 |
| `TELEMETRY_ENABLED` · `QNAI_ALLOW_INSECURE_DEV` env | docs/25, 30 |
| `qna_*` Prometheus metrics | docs/23 |
| `/health/ready` · `/health/deps` endpoints | docs/23, 37 |
| 100/100/100 Roadmap block | 10 files _(copy-paste boilerplate)_ |

---

## ▸ Conventions

- **`ponytail:`** — deliberate simplifications + upgrade path
- **Pydantic v2** — `ConfigDict`, `Field`
- **Source code is truth** — docs are hearsay
- **Wiring > new features** — connect what exists first
- **Single source of truth** — one per concern
- **No silent deletion** — log in `QNA_AGENT_STATE.md`
- **End of session** — update `QNA_AGENT_STATE.md`

---

## ▸ Git Remotes

| Remote | Owner | Notes |
|--------|-------|-------|
| codeberg | Dhaher-Labs | primary |
| github | mulkymalikuldhaher | main |
| github2 | mulkymalikuldhrs | 4141 files diverged — Next.js dashboard |
| gitlab | mulkymalikuldhr | main |

## ▸ E:\ Data

| Path | Content |
|------|---------|
| `E:\hidden-regime\` | COT analysis → PositioningScorer |
| `E:\mue-x\genes\qna_strategies\` | 992 evolved strategies → MueXSignalProvider |

---

## ▸ Stack

| | |
|---|---|
| Language | Python ≥3.11 |
| Package | `uv` |
| API | FastAPI |
| Dashboard | Next.js 16 · React 19 · Recharts 3 |
| Broker | MetaTrader5 _(paper fail-closed)_ |
| Crypto | CCXT |
| Agents | LangGraph |
| Risk | KillSwitch C5 · DCC-GARCH · VaR · Kelly |
| DB | SQLAlchemy · Alembic |

---

_Built by Dhaher Labs._
