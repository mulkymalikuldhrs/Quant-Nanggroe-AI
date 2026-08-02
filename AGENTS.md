# AGENTS.md — Quant Nanggroe AI (QNA) v6.1.0

> **LIVE-TRADING OPERATIONAL (REAL-ONLY, 2026-08-01):** No paper/sim/mock. MT5 LIVE verified: ValetaxIntl-Live2, login=372044706, balance=$1122.05.
> **VERDICT (2026-08-03 devbot):** 🟡 AMBER — eksekusi live ✅, **tapi self-eval/attribution/journalling = fragile di prod runtime.** Journal DB 0-byte/0-table (G1 schema init gagal), balance sync fail-open → phantom $10k di log, 9-checkpoint RiskManager = dead di live path (hanya RiskGuard 4-check jalan), dual live loop (autonomous_cycle vs qna.py live) masih berdampingan. Klaim "FASE 0 COMPLETE" overclaim — lihat `QNA_VERIFICATION_2026-08-03.md`.
> **AUDIT 2026-08-02 (clawbot):** 🟡 AMBER — self-eval/attribution dead code + phantom risk. Fix: Rencana.md FASE 0 G1→G12.

## 🤖 ORCHESTRATION RULE (binding — user directive 2026-08-02)
- **`@dhaherautobot` = SATU-SATUNYA orchestrator.** Hanya dia yang boleh `@mention` agent lain.
- Agent lain HANYA boleh `@mention` `@dhaherautobot`.
- **DILARANG KERAS `@mention` sesama agent** (clawbot→devbot, fangbot→hackerbot, dst).
- Semua tugas WAJIB koordinasi lewat `@dhaherautobot`. Brief antar bot via file/forward oleh orchestrator.
- Rule tersimpan juga di: Hermes memory (tiap profile), `D:\Obsidian\DhaherLabs\_docs\QNA_ORCHESTRATION_MANDATE.md`.

## Quick Start
> **Live tickets:** 20188224176 + 20188224713 (BTCUSD.vx). 3 positions confirmed.

## 🏗️ How It Works

```
Market(MT5) + Strategies(77) → SignalFusion → RiskManager(9-gate)
  → Execution(MT5 LIVE ONLY) → Real Ticket
```

## Before Anything
Read in order:
1. `Rencana.md` — roadmap + architecture visual + run commands
2. `QNA_AGENT_STATE.md` — current state + NEXT ACTIONS
3. `docs/STATUS.md` — doc contradictions (STALE vs CURRENT)
4. `QNA_STATUS_REAL.md` — verified live evidence
5. `C:\Users\Hi\Desktop\QuantScience_Archive\QNA_QuantScience_MASTER.md` — full quant science spec

## Critical Gotchas
- **PYTHONPATH must be empty** — `env -u PYTHONPATH PYTHONPATH=. .venv312/Scripts/python.exe`
- **REAL-ONLY:** PaperBroker REMOVED. MT5 connect raises RuntimeError if unavailable.
- **trade_mode=4 = FULL** (not DISABLED) on Valetax. Guard only blocks mode 0.
- **Lot clamp:** min 0.01, step 0.01 enforced. SL/TP omitted if ≤0.
- **QNAI_ENCRYPTION_KEY** required for API boot.
- **Secrets: env vars only** — never hardcode.
- **Symbols:** `.vx` suffix (EURUSD.vx, BTCUSD.vx, XAUUSD.vx)

## ⚠️ AUDIT 2026-08-02 — known dead/broken (fix before trusting live state)

> 📝 **2026-08-03 devbot correction:** Items 1-6 di bawah sudah di-code (G1-G12). Tapi **verified 2026-08-03: kode ada, tapi runtime gagal.** Lihat `QNA_VERIFICATION_2026-08-03.md` untuk detail. Jangan delete section ini — ini riwayat audit asli.

| ID | Severity | Finding | Fix | Status 2026-08-02 | Verified 2026-08-03 |
|-----|----------|---------|-----|-------------------|---------------------|
| G1 | CRITICAL | Trade journal DB path wrong (dirname x3 → repo root) + schema never init → 0 rows. **No trade ever attributed.** | `trade_journal.py:30` → `parents[1]` (repo root `data/qna_trade_journal.db`) | ✅ DONE | 🔴 **Residual — DB 0 bytes, 0 tables.** `_init_db()` gagal di prod (multi-process lock). |
| G2 | CRITICAL | `PositionManager(journal=None)` — init journal sebelum pos manager | `autonomous_cycle.py:822` journal → `:825` PositionManager | ✅ DONE | ✅ Verified |
| G3 | CRITICAL | RiskGuard phantom $10k — balance/equity tidak sync ke MT5 | `purified:358-361` sync tiap cycle | ⚠️ PARTIAL | 🔴 **Residual — log cycle #214 masih $10000. `account_balance()` fail-open → seed fallback.** |
| G4 | CRITICAL | Registry strategies never fire — `analyze()` vs `generate_signal()` | `autonomous_cycle.py:282-309` dual-call | ✅ DONE | ✅ Verified (81 strategi loaded 04:03) |
| G5 | CRITICAL | `point_size` hardcoded 0.00001 | `autonomous_cycle.py:322: getattr(info, "point", ...)` | ✅ DONE | ✅ Verified |
| G6 | MAJOR | Naked-fill surface: omit-if-≤0 | `purified:140-145` fail-closed di `execute_order` | ✅ DONE | 🟡 **Partial — `api/routes/trading.py:567` + `engine_production_bridge.py:404` old bridge belum** |
| G7 | MAJOR | Position caps defined, unused | `purified:375-395` enforced | ✅ DONE | ✅ Verified |
| G8 | MAJOR | Multi-instance loop | `autonomous_cycle.py:91-92` single lock | ✅ DONE | ✅ Verified (hanya di loop A) |
| G9 | MAJOR | Kelly typo `_kelly_cache` | `autonomous_cycle.py:771` `kelly_cache` | ✅ DONE | ✅ Verified |
| G10 | MAJOR | Misleading close logs | `autonomous_cycle.py:688` retcode check | ✅ DONE | ✅ Verified |
| G11 | MINOR | No breakeven + structure trailing | `autonomous_cycle.py:635-655` | ✅ DONE | ✅ Verified |
| G12 | MINOR | Order attribution LiveEngine | `purified:157` + `autonomous_cycle.py:925-929` | ✅ DONE | ✅ Verified (tapi journal schema gagal) |


Evolution loop: journal + scheduler + scanner + disabler + weight_updater — all integrated.

## Exact Commands
```
# Entry point (single)
python qna.py [unified|api|daemon|hedge|status|stop]

# Run
launch.bat api              # FastAPI on :8000
launch.bat daemon           # Background daemon
launch.bat dashboard        # Next.js on :3000
guardian_cli.py --once      # Guardian watchtower (1 pass)

# Tests
.venv/Scripts/python -m pytest tests/test_kill_switch.py -v --tb=short
.venv/Scripts/python -m pytest tests/test_risk_checks.py -v --tb=short
.venv/Scripts/python -m pytest tests/test_evolution_journal.py tests/test_evolution_scheduler.py tests/test_performance_scanner.py -v

# Lint / Typecheck
ruff check quant_nanggroe/           # line-length=120, select E/F/I
mypy quant_nanggroe/ --ignore-missing-imports

# Dashboard
cd dashboard && npm run dev          # Next.js 16 on :3000

# Package management
uv sync                              # not pip, not poetry
```

## Key Directories

### ✅ WIRED — Active in Pipeline

| Path | Purpose | Status |
|------|---------|--------|
| `quant_nanggroe/engine/strategies/` | 84 strategies via `@StrategyRegistry.register` | ✅ WIRED |
| `quant_nanggroe/engine/risk/` | KillSwitch C5, DCC-GARCH, VaR, Kelly (25 files) | ✅ WIRED |
| `quant_nanggroe/engine/evolution/` | journal, scheduler, scanner, disabler, updater, config (8 files) | 🔴 4 BUGS |
| `quant_nanggroe/core/scoring/` | 8 scorers + FusionEngine + MTFEngine + WeightEvolver | ✅ ALL WIRED |
| `quant_nanggroe/providers/` | hidden_regime_provider + news_provider (3-tier) | ✅ WIRED |
| `quant_nanggroe/hedge_fund/portfolio/main.py` | run_once() 7-stage + evolution | ✅ WIRED |
| `quant_nanggroe/hedge_fund/signals/` | engine_strategies (1079 providers), aggregator, tracker | ✅ WIRED |
| `quant_nanggroe/engine/guardian/` | Self-healing watchtower | ✅ WIRED |
| `quant_nanggroe/pipeline/` | UnifiedPipeline (7 files) | ✅ WIRED |
| `quant_nanggroe/engine/causal/` | Causal Macro Engine suite (14 files) | ✅ WIRED |
| `quant_nanggroe/api/routes/` | 40 routes including evolution | ✅ ALL REGISTERED |
| `quant_nanggroe/agents/` | 16 registered agents | ✅ WIRED |
| `quant_nanggroe/exchange/solana/` | SolanaBroker + Jupiter V6 | ✅ FUNCTIONAL |

### 🗄️ EXIST — Not Wired to Pipeline

| Path | Purpose | Status |
|------|---------|--------|
| `quant_nanggroe/exchange/clients/` | 10 REST clients | 🗄️ ORPHANED |
| `quant_nanggroe/engine/factors/` | 453+ alpha factors (WorldQuant 101, GTJA 191, Qlib 158) | 🗄️ NOT WIRED |
| `quant_nanggroe/engine/kelly/` | 8 Kelly variants | 🗄️ EXIST |
| `quant_nanggroe/engine/regime/` | HMM, ensemble regime detection | 🗄️ EXIST |
| `quant_nanggroe/engine/macro/` | Macro Surprise Index | 🗄️ EXIST |
| `quant_nanggroe/engine/intermarket/` | SMT divergence | 🗄️ EXIST |
| `quant_nanggroe/engine/fundamental/` | Calendar, COT | 🗄️ EXIST |
| `quant_nanggroe/engine/analysis/` | Bootstrap CI, FactorModel | 🗄️ EXIST |
| `quant_nanggroe/memory/` | KnowledgeGraph, ChromaDB | 🗄️ EXIST |
| `quant_nanggroe/types/` | Pydantic models (signal, agent, risk) | 🗄️ EXIST |
| `quant_nanggroe/security/` | JWT + APIKey auth | 🗄️ EXIST |
| `quant_nanggroe/database/` | SQLAlchemy models | 🗄️ NOT CALLED |

### 🗄️ E:\ Data Sources

| Path | Status | Used By |
|------|--------|---------|
| `E:\hidden-regime\` | ✅ **EXTRACTED** | PositioningScorer |
| `E:\mue-x\genes\qna_strategies\` | ✅ **EXTRACTED** | MueXSignalProvider |
| `C:\e\archived\AI-Trader\` | ✅ **EXTRACTED** | NewsProvider |
| `C:\e\archived\TradingAgents\` | ✅ **EXTRACTED** | 3 components |

## Wired Modules (Verified in run_once())
- **ScreenerOrchestrator** — `engine/screener/orchestrator.py` ✅
- **ConfluenceScorer** — `engine/portfolio/confluence_scorer.py` ✅
- **RiskParityAllocator** — `engine/portfolio/risk_parity_bridgewater.py` ✅
- **StressVaRCalculator** — `engine/stress_testing/var_cvar.py` ✅
- **MatrixProfileDetector** — `engine/pattern_recorder/matrix_profile.py` ✅
- **FusionEngine** — `core/scoring/fusion_engine.py` ✅ **WIRED**
- **MultiTimeframeEngine** — `core/scoring/mtf_engine.py` ✅ **WIRED** (Session 8)
- **WeightEvolver** — `core/scoring/evolver.py` ✅ **WIRED** (Session 8)
- **EvolutionLoop** — `engine/evolution/*.py` ✅ **WIRED** (Session 9)
- **HiddenRegimeProvider** — `providers/hidden_regime_provider.py` ✅ **WIRED** → PositioningScorer
- **NewsProvider** — `providers/news_provider.py` ✅ **WIRED** → SentimentScorer
- **EngineStrategyProvider** — `hedge_fund/signals/engine_strategies.py` ✅ **77 strategies wired**

### Actual Pipeline Order (post-Session 9)
1. _pipeline_connect — MT5 + walkforward gate
2. _pipeline_discover — symbol, account, positions
3. _pipeline_trail — trail open positions (skip vote if open)
4. _pipeline_vote — causal → screen → agg (1079 providers) → fusion → mtf → confluence
5. _pipeline_risk_check — sizing → kill switch → risk guard
6. _pipeline_execute — order placement + post-trade (evolver, var, pattern)
7. **Evolution loop** — record closed trades, check triggers, scan performance, disable/promote
8. _pipeline_cleanup — MT5 shutdown

## Non-Negotiable Rules
- **Source code is truth. Docs are hearsay.** Verify every doc claim against imports/calls.
- **No silent deletion.** List in `QNA_AGENT_STATE.md` under PROPOSED FOR DELETION + owner sign-off.
- **Wiring > new features.** Connect what exists. Don't create duplicate #5 of anything.
- **No completion claims without evidence** (pytest output, call graph trace, execution log).
- **Single source of truth per concern:** entry point, registry, risk, execution, data provider.
- **State file protocol:** Update `QNA_AGENT_STATE.md` end of every session — verified (file:line), changed, next actions.

## Anti-Patterns
- Writing "vFinal" / "vNext" files instead of fixing existing ones
- Trusting `CLAUDE.md` / `*_STATUS.md` / `*_AUDIT.md` without independent verification
- Expanding scope (new strategies, agents, asset classes) before dedup is complete
- Ending session without updating `QNA_AGENT_STATE.md`

## Communication
End every response to owner with structured format: verified evidence → changed/decided → blocked on owner → next. No celebratory framing.

## Next (Session 9 completed items)
- ✅ P0 fixes (7 items: FRED key, bare except, MTF REDUCE, live engine, engine/scoring/ delete, dual pipeline, confidence)
- ✅ MT5 live connected (Valetax demo, 29 closed trades)
- ✅ 1079 providers wired (77 engine + 992 mue-x + 10 core)
- ✅ Evolution loop integrated (8 files + 68 tests + API + dashboard)
- ✅ E:\ extraction (hidden-regime, news, loop-engineering, tradingagents)
- ✅ qna.py pipeline bug fixed (asyncio.run → direct call, .get() → getattr)
- ✅ Root cleaned, git committed, docs flagged
- ✅ credentials.md.txt — QUARANTINED: 100+ secrets moved to `C:\Users\Hi\.qna-secrets\credentials.md.txt` (out of repo, not in git). Repo holds placeholder only. Rotate secrets at owner discretion.
- ⏳ engine/factors/ 450+ alpha factors — not wired (enhancement, not blocker)
- ⏳ engine/rl/ — needs PyTorch for real training (scaffold only)
- ⏳ docs cleanup — 107 → ~20 files (STATUS.md has contradiction map)


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
