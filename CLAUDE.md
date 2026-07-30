# CLAUDE.md — Quant Nanggroe AI (Quant Nation)

Autonomous quantitative hedge fund. 678 .py files, 84 strategies, 8 scorers, 10 exchange clients, 16 agents.

## Entry & Commands

```
python qna.py [unified|api|daemon|hedge|status|stop]
launch.bat api              # FastAPI on :8000
guardian_cli.py --once      # Guardian watchtower self-heal
ruff check quant_nanggroe/  # line-length=120
uv sync                     # package manager (not pip, not poetry)
cd dashboard && npm run dev # Next.js 16 on :3000
```

**Critical gotchas:**
- `PYTHONPATH=""` mandatory — Hermes venv leaks `pydantic_core` → crash
- `QNAI_JWT_SECRET` env var required for API boot (fail-closed)
- **numpy 2.5.1** ✅ in .venv (reinstalled). System Python 3.14 has working numpy/pandas/scipy.
- **pytest works** ✅ — 173+ tests pass (scoring 31 + kill switch 66 + shared state 6 + risk checks 8 + guard 6 + evolution 68)
- Hardware: i7-10th gen, 16GB RAM, no GPU
- **MT5 live connected** — Valetax demo account, `history_deals_get()` works
- **Evolution loop active** — `engine/evolution/` (8 files), integrated into `run_once()` post-execute
- **1079 providers** — 77 engine strategies + 992 mue-x + 10 core providers feed the aggregator

## Pipeline Wiring Status

```
✅ WIRED   → Active in pipeline, production-tested
🔴 BROKEN  → Wired but has bugs preventing execution
🗄️ EXIST   → Code exists but NOT wired to pipeline
❌ STUB    → Incomplete implementation

qna.py ───→ pipeline/factory ──→ hedge_fund/portfolio/main.py:run_once()
  │                                     │
  │    ┌────────────────────────────────┘
  │    ▼
  │  1. KONEK MT5          │ ✅ WIRED
  │  2. CEK POSISI         │ ✅ WIRED
  │  3. VOTING:
  │     a. Causal Context   │ ✅ WIRED (engine/causal/)
  │     b. Screener         │ ✅ WIRED (engine/screener/)
  │     c. Aggregate        │ ✅ WIRED (1079 providers)
  │     d. FusionEngine     │ ✅ WIRED (8 scorers)
  │     e. MTF Engine       │ ✅ WIRED (4 frames)
  │     f. Confluence       │ ✅ WIRED (confluence_scorer.py)
  │  4. RISK CHECK          │ ✅ WIRED (KillSwitch + RiskGuard)
  │  5. EXECUTE             │ ✅ WIRED (MT5 / Paper)
  │  6. EVOLUTION           │ 🔴 BROKEN (4 bugs)
  │  7. CLEANUP             │ ✅ WIRED
  │
  ├── engine/strategies/    │ ✅ 84 registered, 77 wired via EngineStrategyProvider
  ├── engine/evolution/     │ 🔴 8 files, 4 wiring bugs — evolution never runs
  ├── engine/risk/          │ ✅ 25 files, KillSwitch C5 fail-closed
  ├── engine/causal/        │ ✅ 14 files, MasterQuantNanggroeEngine
  ├── engine/factors/       │ 🗄️ 453+ alpha factors NOT wired
  ├── engine/fl/            │ ❌ Stub — needs PyTorch
  ├── providers/            │ ✅ 2 active (HiddenRegime + News), 6 dead
  ├── exchange/clients/     │ 🗄️ 10 REST clients orphaned
  ├── exchange/solana/      │ ✅ SolanaBroker functional
  ├── api/routes/           │ ✅ 40 routes all registered
  ├── agents/               │ ✅ 16 agents, 13 functional
  └── database/             │ 🗄️ SQLAlchemy models exist, migrations never called
```

### Pipeline (run_once() — hedge_fund/portfolio/main.py)

1. MT5 connect / paper auto-fallback
2. Gate check — WalkForwardRegistry viability
3. Symbol selection / trail existing positions
4. Causal context — DXY/ZB macro via yfinance
5. ScreenerOrchestrator — market screen
6. Bayesian-weighted signal aggregation + SignalTracker
7. **FusionEngine** — 8 scorers (100% weight, ALL WIRED)
8. MultiTimeframeEngine — HTF/LTF veto
9. ConfluenceScorer — fuses aggregator + screener + fusion
10. Position sizing + RiskParityAllocator
11. KillSwitch C5 + risk_guard_approve (fail-closed)
12. ExecutionManager.execute_order (async)
13. Post-trade: WeightEvolver record, StressVaR, MatrixProfileDetector

### 8 Scorers (✅ ALL WIRED)

| Scorer | Weight | Data | Cache |
|--------|--------|------|-------|
| MacroScorer | 30% | CausalContext regime | — |
| EconomicScorer | 20% | FRED API live | TTLCache 600s |
| BondScorer | 10% | ctx dict | — |
| SentimentScorer | 10% | Fear & Greed live | TTLCache 300s |
| TechnicalScorer | 10% | ctx dict | — |
| PositioningScorer | 10% | CFTC COT API + hidden-regime | 3600s |
| GeopoliticalScorer | 5% | ctx dict | — |
| VolatilityScorer | 5% | ctx dict | — |

FusionEngine: weighted sum + override logic (confidence >= 60% overrides aggregator).

### Dual Scoring Trees
- `core/scoring/` — primary, wired to pipeline
- `engine/scoring/` — older copy, 10 files, NOT wired. Possibly vestigial.

### 4 Git Remotes

| Remote | URL | Notes |
|--------|-----|-------|
| codeberg | Dhaher-Labs/Quant-Nanggroe-AI | primary |
| github | mulkymalikuldhaher/Quant-Nanggroe-AI | main |
| github2 | mulkymalikuldhrs/Quant-Nanggroe-AI | **4141 files diverged** — contains full Next.js dashboard |
| gitlab | mulkymalikuldhr/Quant-Nanggroe-AI | main |

### E:\ Data Sources

| Path | Content | Used By |
|------|---------|---------|
| `E:\hidden-regime\` | COT analysis, regime evolution | PositioningScorer |
| `E:\mue-x\genes\qna_strategies\` | 992 evolved strategy files | Dynamic MueXSignalProvider |
| `C:\e\archived\AI-Trader\` | market_intel.py (1911 lines), TTL cache | DataProvider cache engine |

## Core Principles
- **Source code is truth** — docs are hearsay. Verify every claim against imports/calls.
- **Wiring > new features** — connect what exists before creating anything new.
- **Single source of truth** per concern: entry point (qna.py), risk, execution, registries.
- No silent deletion — all removals logged in QNA_AGENT_STATE.md.
- End every session updating QNA_AGENT_STATE.md with verified evidence.

## Tech Stack

| Layer | Choice |
|-------|--------|
| Language | Python >=3.11 |
| Package | `uv` |
| API | FastAPI |
| Dashboard | Next.js 16 + React 19 + Recharts |
| Broker | MetaTrader5 (paper fail-closed) |
| Crypto | CCXT |
| Agent framework | LangGraph |
| Risk | KillSwitch C5 + DCC-GARCH + VaR + Kelly |
| DB | SQLAlchemy + Alembic |

Built by Dhaher Labs.

---

## 🎯 100/100/100 Roadmap — Dari OpenCode Audit (2026-07-30)

### Target Matrix: 3 Dimensi

| Score | Arti | Target | Estimasi Waktu |
|-------|------|--------|---------------|
| **A 100** | Bisa dinikmati — evolution jalan, error kedengeran, dashboard meaningful | ✅ Pipeline sehat, evolution beneran belajar, error gak silent | **1 hari** |
| **B 100** | Quant-grade — single source of truth, statistical rigor, no data corruption | ✅ Weight governance, signal/registry dedup, test coverage >80% | **3-4 hari** |
| **C 100** | Institutional — zero silent fail, audit trail, multi-account, SLA | ✅ Paper=production, alerting, replay, 80% coverage, multi-broker | **2-4 minggu** |
| **Total** | **300/300** | **Fully autonomous quant nation** | **~6 minggu** |

### Detail Gap per Score (Dari Audit 8 Task Agent)

#### A 100 — Enjoyable & Reliable

| # | Gap | Fix | Estimasi |
|---|-----|-----|----------|
| A1 | **Evolution loop dead** — 4 wiring bugs di `main.py:847-854` | scan_strategy→scan_all, evaluate() pake list | **2 jam** |
| A2 | **Silent error 20+ titik** — semua `log.debug()` | Upgrade ke `log.error` + propagate | **1 jam** |
| A3 | **`np` undefined** — StressVaR selalu throw NameError | `import numpy as np` di main.py | **5 menit** |
| A4 | **`get_valid_pairs` missing** — always throws AttributeError | Fix import atau remove dead call | **15 menit** |
| A5 | **Dashboard build stale + color config gak ada** | Rebuild + color picker | **2 jam** |
| A6 | **PnL attribution gak ada** — dashboard gak tampilin evolution journal | Wire dashboard API ke journal SQLite | **1 jam** |
| | **Total A fix** | | **~6 jam** |

#### B 100 — Quant-Grade

| # | Gap | Fix | Estimasi |
|---|-----|-----|----------|
| B1 | **WeightEvolver vs WeightUpdater fight** — beda data source, beda formula, gak sync | Eliminate satu. Rekomendasi: WeightEvolver (circuit breaker) | **3 jam** |
| B2 | **Weight total 1.03 + 2 scorers missing dari evolver** | Tambah CryptoScorer & NewsScorer ke DEFAULT, normalize | **30 menit** |
| B3 | **8 Signal classes, 3 field name conflicts** — signal_type vs direction vs side vs bias | Pilih canonical (`types/signals.py`), delete sisanya | **2 jam** |
| B4 | **3 registries gak sync** — StrategyRegistry vs AutoRegistry vs WalkForwardRegistry | StrategyRegistry = canonical, AutoRegistry delete for strategies | **2 jam** |
| B5 | **4/10 scorers untested** — Crypto, News, Positioning, Confluence | Tambah test class + mock external APIs | **3 jam** |
| B6 | **6/8 evolution modules untested** — config, handler, scanner, disabler, updater, evolver | Tambah test class | **4 jam** |
| | **Total B fix** | | **~14.5 jam** |

#### C 100 — Institutional/Hedge Fund

| # | Gap | Fix | Estimasi |
|---|-----|-----|----------|
| C1 | **Paper mode = dead risk** — PnL hardcoded 0.0, balance 1000 | Simulasi PnL real dari MT5/fallback | **2 jam** |
| C2 | **RiskLimits class unwired** — `limits.py:48` can_trade() zero callers | Wire ke `_pipeline_risk_check` | **1 jam** |
| C3 | **Audit trail write-only** — evolution journal nulis tapi gak dibaca | Dashboard timeline + PnL attribution | **4 jam** |
| C4 | **No alert system** — error silent total | Telegram alert on subsystem fail | **3 jam** |
| C5 | **Test coverage rendah** — estimasi 20-30% | Target 80%. Prioritaskan risk + scoring + evolution + pipeline | **3-4 hari** |
| C6 | **Multi-account MT5** — single session, gak bisa multi-broker | Multi-process architecture | **1 minggu** |
| C7 | **~15K lines dead code** — 10 REST clients, 453 alphas, RL stub, live_engine.py | Hapus/archive file terverifikasi | **3 jam** |
| C8 | **Data quality framework** — gak ada SLA monitoring, staleness detection | Data health check + status endpoint + dashboard | **2 hari** |
| | **Total C fix** | | **~6-10 hari** |

### Timeline Eksekusi

```
Hari 1:     A1 + A2 + A3 + A4 + B1 + B2          → Score A ~90, B ~60
Hari 2-3:   B3 + B4 + B5 + B6 + A5 + A6          → Score A 100, B ~90
Minggu 2:   C1 + C2 + C3 + C7 + C8               → Score C ~70
Minggu 3-4: C4 + C5 + C6                         → Score C ~90
Minggu 5-6: Last mile hardening                  → Score C 100
```

### Keputusan Arsitektur yang Perlu Diambil Mulky

| Keputusan | Opsi A | Opsi B | Rekomendasi |
|-----------|--------|--------|-------------|
| **Weight tuner** | WeightEvolver (circuit breaker, normalized) | WeightUpdater (Bayesian, SQLite) | **WeightEvolver** — safety circuit breaker |
| **Registry main** | StrategyRegistry (decorator-driven) | AutoRegistry (scan semua subclass) | **StrategyRegistry** — explicit > implicit |
| **Signal canonical** | `types/signals.py` (20 fields, BaseModel) | `pipeline/signal.py` (8 fields, dataclass) | **`types/signals.py`** — Pydantic validation |
| **Alerts** | Telegram | Email | **Telegram** — sudah ada bot |
| **Multi-account MT5** | Multi-process (1 per broker) | Docker containers | **Multi-process** — 16GB RAM cukup |

### Catatan Realistis

Estimasi 6 minggu tapi bisa molor karena:
1. **Testing time** — tiap perubahan perlu ruff + mypy + pytest. Kena typo = backtrack
2. **Refactor domino effect** — signal dedup → 8 file berubah → 5 file impor patah → fix lagi
3. **Mental energy** — baca 83 strategy files, 24 risk files, 20 provider files buat mastiin gak ada yang kehapus

**Realistis: 6-8 minggu** untuk 300/300.

---

## 🧬 E:\ Integration — 12-Agent Council Plan (2026-07-31)

**136 jam / 4-6 minggu** — Port TradeBobbyTerminal + OrderFlowMap ke QNA pipeline.

| Phase | Hours | Deliverable |
|-------|-------|-------------|
| Phase 0 — Pre-work | 8h | Delete dead code, dedup signal/registry/COT |
| Phase 1 — Week 1 | 24h | 5 Python providers + pipeline wiring |
| Phase 2 — Week 2 | 32h | 9 dashboard panels + risk gates + evolution |
| Phase 3 — Week 3 | 40h | 80% tests + alerts + data quality |
| Phase 4 — Future | 32h | Node sidecars + multi-account + backtest |

Lihat `docs/Rencana.md` untuk detail lengkap.
