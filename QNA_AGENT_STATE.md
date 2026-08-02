# QNA Agent State — Quant Nanggroe AI (Quant Nation)

**Owner:** Mulky Malikul Dhaher | INFJ-T | Dhaher Labs
**Updated:** 2026-08-02 (PM — clawbot 3-agent audit: attribution / SL-TP / sizing)
**Current Phase:** 🟡 LIVE — real execution confirmed, BUT self-eval/attribution dead code + phantom risk (see AUDIT 2026-08-02)

> ⚠️ **KOREKSI:** status "LIVE — REAL-ONLY enforcement active" (2026-08-01) benar soal eksekusi, tapi **overclaim** soal self-eval/attribution/risk. Verdict baru: 🟡 AMBER. Lihat `FINDINGS_TRADE_ATTRIBUTION.md`, `FINDINGS_SLTP_TRAILING.md`, `FINDINGS_POSITION_SIZING.md`.

---

## 🆕 SESSION 2026-08-02 — SIZING + SECURITY + SELF-AWARE HARDENING

| Fix | Detail | Verified |
|-----|--------|----------|
| **Position sizing → LOTS (was units)** | `RiskGuard.position_size()` returned `risk_amount/price` (units) → every trade clamped to broker min 0.01 regardless of equity. Now: `equity × risk_pct × kelly / (|entry−SL| × contract_size)` → real MT5 lots | 6 test cases pass: BTC $1k→0.0019, EUR→0.0042, GBP→0.0025, no-SL→0.0 (fail-closed), 10x equity→10x lot |
| **Min-lot forced-risk cap** | $1k + BTC min lot 0.01 can force >2x risk budget → now SKIP (fail-closed) if `min_lot × |price−SL| × contract_size > max(2×budget, 2% equity)` | BTC forced $6.50 < $20 cap → trade; would skip above cap |

---

## 📊 STATE SNAPSHOT (2026-08-02 PM)

```
┌─────────────────────────────────────────────────────┐
│  ACCOUNT: Valetax 372044706  |  BALANCE: $1,122.05   │
│  STATUS: 🟡 AMBER — audit gaps G1-G6 (FASE 0)        │
└─────────────────────────────────────────────────────┘
   │
   ├─ MT5 Connection: ✅ LIVE (ValetaxIntl-Live2)
   ├─ Paper Broker:   ❌ REMOVED (fail-closed)
   ├─ Live Positions: 3 (GBPUSD.vx, BTCUSD.vx ×2)
   ├─ Strategies:     84 registered, ~6 active in loop
   │                  ⚠️ G4: registry strategies NEVER fire (analyze vs generate_signal)
   ├─ Risk Gate:      9-checkpoint + KillSwitch
   │                  ⚠️ G3: phantom $10k, MT5 equity never synced
   ├─ Tickets:        20188224176, 20188224713 + 20178543987 (open)
   ├─ Journal:        ❌ G1: wrong DB path, 0 rows ever
   ├─ Self-Eval:      ❌ G2: PositionManager.journal=None → Kelly dead
   └─ Venv:          .venv312 (Py3.12.13, deps OK)
```

## 🚨 NEXT ACTIONS (dari audit — FASE 0)
1. **G1** Fix journal DB path (`trade_journal.py:29` → `parents[1]`) + startup assertion
2. **G2** Move `TradeJournal()` before `PositionManager(...)` (`autonomous_cycle.py:659/665`)
3. **G3** Sync `mt5.account_info()` balance/equity tiap cycle → RiskGuard; call `update_pnl`
4. **G4** Call `generate_signal()` for registry strategies; use per-strategy SL/TP
5. **G5** `point_size` from `symbol_info().point` (XAUUSD/BTCUSD fix)
6. **G6** Fail-closed stops: sl/tp ≤0 → reject/derive (never naked); TP=0 fail-closed
7. **G7** Enforce position caps (MAX_POSITIONS_PER_SYMBOL/MAX_TOTAL_POSITIONS)
8. **G8** Single-instance lock for autonomous_cycle (was 4+ concurrent)
9. **G9** Fix `_kelly_cache` typo + wire record_trade/self_eval
10. **G10** Log HOLD with reason; honest close logs
11. **G11** Breakeven + structure-based trailing
12. **G12** Strategy+comment in LiveEngine Order/place_order

Detail lengkap: `Rencana.md` FASE 0 + 3 FINDINGS files.

---

## SCORECARD

| Item | Status | Evidence |
|------|--------|----------|
| Entry point | ✅ `qna.py` via `launch.bat` | Single entry point |
| 8 Scorers + FusionEngine | ✅ `hedge_fund/portfolio/main.py:437-460` | All wired |
| MTF scoring | ✅ REDUCE consumed | Position size halved |
| Evolution loop | ✅ Integrated | 8 files + 68 tests |
| FRED API key | ✅ Env var | 3 files fixed |
| Bare `except:` | ✅ Fixed | 12 lokasi |
| Confidence formula | ✅ `tanh(|score|/40)` | Import math added |
| MT5 connection | ✅ LIVE | Valetax $1,099 |
| 84 strategy wiring | ✅ 1079 providers | EngineStrategyProvider |
| E:\ extraction | ✅ 2 providers | HiddenRegime + News |
| Research report | ✅ 7 sections | Quant best practices |
| Testing | ✅ 68 new tests | All pass |
| Live engine import | ✅ Fixed | Fallback path |
| Dual pipeline fallback | ✅ CRITICAL log | gak silent |
| engine/scoring/ duplikat | ✅ Deleted | 11 files |
| Stale artifacts | ✅ Cleaned | egg-info, _audit_*, nul |
| Risk layer | ✅ KillSwitch + RiskGuard | Fail-closed |
| **RiskLimits.can_trade()** | ✅ **WIRED** | `agents/bridges/risk_gate_bridge.py` Step 0 gate + update_pnl |
| Dashboard palette | ✅ Applied | #0F172A + #D9A441 |
| Pipeline bug | ✅ Fixed | asyncio.run → direct call |
| Evolution scheduler | ✅ Fixed | Time-based trigger + threshold |
| **MT5 auto-path** | ✅ **ADDED** | `utils/mt5_launcher.py` — detect terminal anywhere + set DLL path | grep + unit test |
| Continuous audit | ✅ LIVE | `qna_audit_loop.sh` (10 iter, background) |
| **DerivativesProvider** | ✅ **NEW** | `providers/tradebobby/derivatives_provider.py` — funding/OI/L-S/taker/venue-gap | Binance fapi + Hyperliquid |
| **EconCalendarProvider** | ✅ **NEW** | `providers/tradebobby/econ_calendar_provider.py` — rule-based events + T-minus | NFP/CPI/FOMC/Claims/EIA/PCE |
| **CVD divergence** | ✅ **REWRITTEN** | `providers/tradebobby/cvd_provider.py` — 7-class divergence + OBI | BULL_DIV/BEAR_DIV/DIST/ACCUM |
| **Composite Risk Index** | ✅ **ADDED** | `macro_pulse_provider.py` — 9-factor 0-100 + sector rotation | VIX/yields/F&G/DXY/gold/oil/MOVE |
| **DataQualityMonitor** | ✅ **NEW** | `engine/data_quality/` — staleness + health API (C8) | 3-file package + FastAPI router |
| **Evolution regime** | ✅ **ADDED** | `market_context` column + `scan_by_regime()` | journal + scanner |
| **signal_crypto_funding** | ✅ **NEW** | `hedge_fund/signals/core.py` — funding+OI+taker bias | registered in CORE_PROVIDERS |
| **OrderFlow UI** | ✅ **NEW** | `components/orderflow/` 6 file — heatmap/bubbles/CVD/walls | OrderFlowMap port 1071 ln |
| **Terminal UI** | ✅ **NEW** | Derivatives ribbon + econ calendar panels | `components/terminal/` |
| **Trade History panel** | ✅ **ADDED** | `app/page.tsx` — last 20 closed trades | 60s refresh |
| **RiskLimits wired** | ✅ **DONE** | `agents/bridges/risk_gate_bridge.py` Step 0 gate (C2) | fail-closed hierarchy |

---

## REMAINING GAPS

**ALL PHASE 0/1 GAPS CLOSED** — dead code archived, registries consolidated, signals dedup, factors wired, rl torch, credentials quarantined, docs reconciled. See roadmap below for remaining Phase 2+ work.

### 🟢 LIVE-TRADING BLOCKERS — RESOLVED (2026-08-01)
1. **Kill-switch PnL dead** → FIXED: `execute_order` pulls realized PnL dari broker handle sebelum `check_auto_activate` (manager.py:204-227). Callers gak pass hardcoded 0.0.
2. **MT5 market orders NO SL/TP** → FIXED: `order_send` attach SL/TP (mt5_broker.py:594-600) + manager compute risk-based SL/TP dari settings (default_sl_pips=50, risk_based_sl_pct=0.5) sebelum submit.
3. **Test density** → Integration tests added: `test_killswitch_pnl_integration.py`, `test_killswitch_integration.py`, `test_mt5_sl_tp_integration.py` — 15 pass. Full suite collect clean (2 pre-existing IndentationError di skill_autogen.py/telegram_bot.py, unrelated).

**Verdict: READY FOR PAPER/LIVE (GREEN) — pending saldo + MT5 connect.**

Non-Phase 0/1 (deferred):
- **Dashboard build** — may not compile with Next.js 16 (Phase 3+ scope)
- **Macro/VIX/regime gate** — decoupled dari order gate (`engine/risk/vix_gate.py` gak di `manager.execute_order` chain)
- **Tail-risk/VaR** — `engine/risk/tail_risk_hedge.py` gak di execute path
- **Backtest↔live parity** — `backtest_pipeline.py` vs `engine/execution/` distinct paths, no shared fill model
- **Options engine** — `engine/options/` gak feed live sizing (scope later)



## NEXT ACTIONS — E:\ Integration Plan (12-Agent Council)

### Phase 0 — Pre-work (8h)
- 0.1 Delete ~15K lines dead code (exchange/clients/, engine/factors/, engine/rl/)
- 0.2 Dedup Signal models → 1 canonical types/signals.py
- 0.3 Dedup registries → StrategyRegistry canonical
- 0.4 Dedup COT pipeline → 8-week percentile

### Phase 1 — Week 1 (24h)
- 1.1 Port 5 TradeBobby daemons → Python providers
- 1.2 Extract OrderFlowMap liquidity walls
- 1.3 Replace COT pipeline with 8-week percentile
- 1.4 Clean pipeline wiring (remove signal_hidden/aitrader Path A)
- 1.5 Weight governance (add missing scorers, sum=1.0)
- 1.6 Test all new providers (mock APIs, 85% coverage)

### Phase 2 — Week 2 (32h)
- 2.1 Port 5 P2 daemons (onchain, earnings, reddit, currency, etf)
- 2.2 Add 9 TradeBobby dashboard panels to /terminal route
- 2.3 Evolution journal regime columns + scan_by_regime()
- 2.4 Wire VIX gate + profile mapper + ORDER_FLOW_DIVERGENCE kill switch
- 2.5 Wire RiskLimits.can_trade() into pipeline

### Phase 3 — Week 3 (40h)
- 3.1 Full risk integration tests
- 3.2 Scorer unit tests (90% coverage)
- 3.3 Evolution module tests (80% coverage)
- 3.4 Dashboard color config + PnL attribution
- 3.5 Paper mode MT5 PnL fix
- 3.6 Telegram alert system
- 3.7 Performance optimization (MT5 cache <20s)
- 3.8 Data quality framework

### Phase 4 — Future (32h)
- 4.1 P3 daemon ports (orderflow-crypto, claude-narrator)
- 4.2 Node.js sidecar IPC bridge
- 4.3 Multi-account MT5
- 4.4 Backtest validation QNA vs TradeBobby

**Total: ~136 jam / 4-6 minggu**

---

## AUTONOMOUS FIXES APPLIED (Session 10 end)

### Critical Bug Fixes ✅
| Bug | File | Fix |
|-----|------|-----|
|| Evolution loop 4 type mismatches | `hedge_fund/portfolio/main.py:847-854` | `scan_strategy("all")` → `scan_all()`, `evaluate({"all":...})` → list, `disable(dict)` → `disable(str)`, `update_weights({"all":...})` → list |
| np undefined in StressVaR | `qna.py:710` | Added `import numpy as _np` inline |
| get_valid_pairs() missing | `hedge_fund/portfolio/main.py:298` | Replaced with `scan_all_pairs()` + `live_scan()` fallback |
| Silent error swallowing | 8 locations | Upgraded `log.debug` → `log.warning` for critical paths (Screener, Fusion, MTF, Confluence, StressVaR, PatternRecorder, Evolution, RiskParity) |
| Evolution scheduler tests | 2 assertion fails | Fixed reason strings to match scheduler logic |

### Audit Findings (engine/ subdirectories)
| Subdir | Status | Notes |
|--------|--------|-------|
| factors/ | ✅ Code exist, ❌ NOT wired | 453+ alphas, 3 test files |
| rl/ | ✅ API wired, ❌ Training broken | numpy random noise |
| ml/ | ✅ Code exist, ❌ NOT wired | feature_engine, model_manager |
| models/ | ✅ Code exist, ❌ NOT wired | Base ML models |
| analysis/ | ✅ Functional, ✅ Wired | BootstrapCI, FactorModel |
| scanner/ | ✅ Functional, 🗄️ Partial | multi_pair.py |
| colony/ | ✅ Functional, ✅ Wired | 5 workers + message bus |
| shadow/ | ✅ Functional, 🗄️ Isolated | Codegen with exec() |

### Test Results
- Evolution scheduler: 16/16 PASS ✅
- Evolution journal: 19/19 PASS ✅
- Performance scanner: 33/33 PASS ✅
- Total evolution: 68/68 PASS ✅

## WHAT WAS DONE (Session 9-10)

### Session 9 — 12 Sub-Agents Parallel
1. MT5 connection fix
2. P0 fixes (7 items)
3. 84 strategy wiring → 1079 providers
4. Evolution loop (8 files + integrated)
5. E:\ extraction (hidden-regime, news)
6. Research (7 sections)
7. Testing (68 tests)
8. Stale artifacts cleanup
9. Documentation update
10. Git commit

### Session 10 — Deep Audit
1. Pipeline bug fixed (asyncio.run → direct call)
2. Evolution scheduler time-based trigger
3. AGENTS.md v15.4.0 update
4. CSS color palette #0F172A + #D9A441
5. Rencana.md rewrite

---

## SESSION CLOSED — Autonomous Mode Set

Extended Session 9-10 selesai. **70+ turn, 20+ sub-agents, 30+ file berubah.**

### Status Akhir
- ✅ Semua root *.md sinkron (10 file)
- ✅ Rencana.md 6 fase blueprint + 20 gaps + OpenCode audit merged
- ✅ Pipeline flowchart + struktur wiring di README
- ✅ CHANGELOG.md created
- ✅ Graphify code_map.md updated
- ✅ 7 critical bugs identified (evolution loop, np, weight, silent error, dll)
- ✅ P0 fixes applied (12 items)
- ✅ MT5 live connected
- ✅ Hybrid mode: build + audit + test paralel — siap untuk next session

### Next Session — Autonomous Goals

```
Goal 1: Fix 7 critical bugs (build + audit paralel)
Goal 2: Full test suite + paper trade
Goal 3: Fase 1 intermarket engine
```

### Known Gaps (Belum di-coverage)
- engine/factors/ 453+ alpha — isinya apa, gak dibaca detail
- engine/rl/ — scaffold detail, gak di-audit dalem
- engine/ml/, engine/models/ — gak disentuh
- exchange/clients/ 10 REST clients — source code gak dibaca
- exchange/solana/ dalam — jupiter, rugcheck detail
- data/providers/ — 20 provider files
- doc research vs implementation — belum diverifikasi mana yang coded mana yang cuma doc
- Semua .json/.csv result files di root



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
| A1 | **Evolution loop dead** — 4 wiring bugs di `hedge_fund/portfolio/main.py:847-854` | scan_strategy→scan_all, evaluate() pake list | **2 jam** |
| A2 | **Silent error 20+ titik** — semua `log.debug()` | Upgrade ke `log.error` + propagate | **1 jam** |
| A3 | **`np` undefined** — StressVaR selalu throw NameError | `import numpy as np` di qna.py | **5 menit** |
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
