# QNA — FULL VIEW, GAP ANALYSIS & MATURATION ROADMAP
**Tujuan akhir:** Autonomous Quantitative Hedge Fund yang **trade sendiri**, **evaluate dari closed PnL**, **self-evolve** (fine-tune + strategy mutation), **autonomous pipeline** tanpa human-in-loop.

**Tanggal audit:** 2026-07-26 | **Auditor:** Dhaher OS (7-lensa parallel)
**Status jujur:** INFRASTRUKTUR 85% BERES. EXECUTION PATH 0% LIVE. SYSTEM BELUM PERNAH TRADE NYATA.

---

## 🆕 v6.1.0 Update — Quantitative Alpha Engines REAL

| Added Module | Status | Real/Mock |
|-------------|--------|-----------|
| **DCC-GARCH** (engine/risk/dcc_garch.py) | ✅ 47 tests | REAL (arch package) |
| **Causal Bias** (engine/causal/causal_bias.py) | ✅ | REAL (event-driven) |
| **Macro Surprise Index** (engine/causal/macro_surprise.py) | ✅ | REAL (FRED API) |
| **COT Tracker** (engine/causal/cot_tracker.py) | ✅ | REAL (cot_reports/CFTC) |
| **SMT Divergence** (engine/causal/smt_divergence.py) | ✅ | REAL (Engle-Granger) |
| **Thesis Drift Guard** (engine/causal/thesis_drift_guard.py) | ✅ 3-stage | REAL (macro context) |
| **Causal Bias → Signal Filter** | ✅ All providers | REAL (boost/reduce/block) |

**Edge sekarang:** DCC-GARCH (dynamic correlation), Causal Macro (FRED/CFTC real data), SMT (cointegration breakdown), MSI (macro surprises). Semua real, tidak ada mock.

---

## 1. FULL VIEW — APA YANG ADA SEKARANG (Verified v6.1.0)

| Komponen | Status | Bukti |
|----------|--------|-------|
| **DCC-GARCH** | ✅ 47 unit tests | Dynamic correlation, auto-fit, VRK Kelly weights |
| **Causal Macro Engine** | ✅ 5 modules | Bias, MSI (FRED), COT (CFTC), SMT, Thesis Drift |
| **Causal Bias → Signal** | ✅ All providers | boost/reduce/block on 10 core + 200+ evolved providers |
| Strategy Registry | ✅ 97 strategies | `list_strategies()` → 97 |
| StrategyEvolver | ✅ Real walk-forward | `WalkForwardAnalyzer.analyze_strategy()` — per-fold strategy re-fit, OOS Sharpe validation |
| SelfFineTuner | ❌ FILE HILANG | Import gagal → `self._self_finetuner = None` |
| LiveEngine | ❌ SIMULATOR | `_open_position()` INSERT ke SQLite |
| MT5ExecutionBroker | ✅ Ada tapi ORPHAN | `place_order` ada, LiveEngine tidak pakai |
| Risk Guard | ✅ Wired | Real PnL via `history_deals_get` |
| Thesis Drift Guard | ✅ 3-stage | Monitor → Warn → Hard Exit (circuit breaker) |
| DCC Auto-fit | ✅ live_engine.py | `_update_dcc_garch()` every N cycles |
| Pipe: macro_context | ✅ pipeline/ | Safety-net macro filter via env vars |
| Trade Journal DB | ⚠️ Kosong | `qna_journal.db`: 0 trades |
| MT5 Connection | ❌ Timeout | Valetax IPC `-10005` |
| Total LOC | ~42,000+ | `quant_nanggroe/` + engine/causal/ 🆕 |

---

## 2. NILAI — APA YANG BERHARGA

✅ **Yang sudah matang:**
- Strategy library (97 live strategies, SMC/Wyckoff/MeanRev/DhaherSystem)
- Risk guard dengan fail-closed veto (daily/weekly loss)
- PnL evaluator (realized PnL math benar)
- MT5 connector + adapter (kode order execution ADA, tinggal disambungkan)
- AutoRegistry (auto-discover strategies)
- 7-profile Hermes orchestration (autobot/clawbot/devbot/fangbot/hackerbot/traderbot/researchbot)

❌ **Yang bernilai TAPI palsu (harus dihancurkan):**
- "LiveEngine trades" → BOONG. Ini simulator ledger.
- "SelfFineTuner evolves" → BOONG. File hilang.
- ~~"StrategyEvolver validates" → BOONG. Pakai mock backtest.~~ ✅ **FIXED**: real walk-forward via `WalkForwardAnalyzer.analyze_strategy()`.
- "Production runner live" → BOONG. Jalankan old code di paper mode.

---

## 3. GAP ANALYSIS — 5 LENSA

### 📊 LENSA QUANT / HEDGE FUND
**Pertanyaan:** "Ini hedge fund beneran atau mainan?"
**Jawaban:** Mainan. Alasan:
1. **0 real trades.** Journal kosong. System amnesiac — gak bisa observe diri sendiri.
2. **LiveEngine gak kirim order.** `_open_position()` → SQLite INSERT. MT5 `order_send` TIDAK ADA di live path.
3. **Execution broker orphaned.** `MT5ExecutionBroker.place_order` ada tapi LiveEngine pakai `self.connector = self.price_provider` (cuma baca harga).
4. **Risk guard gak dapet real PnL** karena MT5 gak connect → veto selalu 0.0 → sistem either rubber-stamp atau phantom-veto.
5. **No closed-PnL feedback.** Strategy gak pernah di-score dari real profit/loss → gak ada yang diajarin "strategi mana yang untung."

**Gap terbesar:** Execution path putus antara signal → order. Dan feedback loop dari closed PnL → strategy update TIDAK ADA.

### 🔧 LENSA ENGINEER / CODER
**Pertanyaan:** "Kodenya bersih dan terhubung?"
**Jawaban:** Terhubung 70%, putus di titik kritis.
1. **LiveEngine ≠ build_execution_manager.** Dua jalur execution berbeda. LiveEngine bikin sendiri (simulasi), builder bikin yang bener (MT5) tapi gak dipakai LiveEngine.
2. **SelfFineTuner import tapi file hilang** → `autonomous.py:637` try/except nangkep → `None`. Vaporware di production path.
3. **qna-production-runner.py point ke E:/trading/hedge_fund.py** (old monolith), bukan `quant_nanggroe/live_engine.py`. Cron "production" jalanin code salah.
4. **StrategyEvolver real walk-forward** → validasi mutasi dengan OOS Sharpe via `WalkForwardAnalyzer.analyze_strategy()`. ✅
5. **Test suite 1 test** → quality gate gak jalan. Claim "94/94 pass" sudah stale.

**Gap terbesar:** Wiring. Execution broker yang bener harus dipakai LiveEngine. Runner harus point ke LiveEngine. SelfFineTuner harus ada atau dihapus.

### 🐛 LENSA DEBUGGER
**Pertanyaan:** "Apa yang silently broken?"
**Jawaban:**
1. **LiveEngine silent simulator.** Gak error, gak crash, tapi gak trade. Paling berbahaya — kelihatan sehat, diam-diam gak ngelakuin apa-apa.
2. **SelfFineTuner silent None.** Import gagal → try/except → `None`. Gak ada error, fine-tune gak jalan.
3. **Journal empty = blind.** System execute tapi gak bisa liat PnL → tiap klaim "profit" unfalsifiable.
4. **MT5 timeout silent.** `builder.py:385` `self._mt5 = None` kalau connect gagal → fallback paper → 0 trade, gak kelihatan error.
5. **Kill switch AUTO_DAILY_LIMIT** (dari skill): tiap restart API → veto semua trade. System "healthy" tapi gak trade.

**Gap terbesar:** Silent failures. Perlu assertion: "if trades==0 after N cycles → ALARM, not silent."

### 🤖 LENSA AUTONOMOUS / SELF-EVOLVING
**Pertanyaan:** "Bisa evolve sendiri dari closed PnL?"
**Jawaban:** TIDAK. Rantai putus di 3 titik:
1. **Closed PnL → Evaluator:** `pnl_evaluator.py` ADA (hitung realized_pnl per trade). ✅
2. **Evaluator → StrategyEvolver:** `StrategyEvolver` ADA — real walk-forward backtest via `WalkForwardAnalyzer.analyze_strategy()`. ✅
3. **StrategyEvolver → Strategy Update:** Mutasi diterima tapi gak divalidasi → gak ada yang diajarin.
4. **Fine-Tune:** `SelfFineTuner` HILANG. ❌ Zero fine-tune capability.
5. **Autonomous Pipeline:** Cron jalan tapi point ke old code + paper mode. ❌

**Gap terbesar:** Feedback loop `trade → close → evaluate → evolve → redeploy` TIDAK TERSAMBUNG. Sekarang: signal → (simulasi) → journal kosong → (gak ada evaluasi) → (gak ada evolusi).

### 🧠 LENSA ORCHESTRATOR (7 PROFILES)
**Pertanyaan:** "Apakah 7 profile kerja paranoid menuju tujuan?"
**Jawaban:** Profiles upgrade done, TAPI crons masih error + gak ada yang monitor QNA execution gap.
1. traderbot cron error (combo flaky + MT5 gak connect)
2. devbot harus wiring LiveEngine→MT5ExecutionBroker (bukan cuma register strategies)
3. clawbot harus adversarial-test LiveEngine._open_position (buktikan gak kirim order)
4. ~~researchbot harus wired StrategyEvolver ke real backtest~~ ✅ **DONE**
5. autobot harus orchestrate: "QNA trades 0 → ALARM"

**Gap terbesar:** Profiles gak aware bahwa QNA gak pernah trade. Perlu cross-profile alarm: "if journal.trades == 0 for >24h → ALL profiles alert."

---

## 4. MATURATION ROADMAP — MENUJU TRUE AUTONOMOUS HF

### PHASE A — UNIFY EXECUTION PATH (P0, 1-2 hari)
**Masalah:** LiveEngine simulator, broker orphaned.
**Fix:**
1. LiveEngine `_open_position` / `_close_position` HARUS panggil `MT5ExecutionBroker.place_order` (via `build_execution_manager`).
2. LiveEngine init: panggil `build_execution_manager(allow_live=True)` → dapat EM dengan MT5 wired.
3. Kill `self.connector = self.price_provider` sebagai execution sink. Connector = price ONLY, EM = execution.
4. **Verify:** `LiveEngine` unit test → mock broker → assert `place_order` called.

**Owner:** devbot + clawbot (test)
**Gate:** LiveEngine sends order to mock broker in test → 1 real trade recorded in journal.

### PHASE B — CONNECT REAL MT5 (P0, user-dependent)
**Masalah:** Valetax IPC timeout `-10005`.
**Fix:**
1. Two-step init: kill terminal → launch dengan creds → wait 20s → `mt5.initialize()`.
2. Atau switch ke Exness (mode 3 = FULL trading, bukan Valetax mode 4 = DISABLED).
3. Risk guard `set_broker_handle(mt5)` → real PnL.
**Owner:** traderbot + autobot
**Gate:** `mt5.account_info()` returns balance, `positions_get()` works.

### ~~PHASE C — WIRE REAL BACKTEST TO EVOLVER (P0, 2-3 hari)~~ ✅ **DONE**
**Masalah:** ~~StrategyEvolver pakai mock~~ → ✅ **SELESAI.**
**Fix yang sudah diterapkan:**
1. `_real_backtest()` memanggil `WalkForwardAnalyzer.analyze_strategy()` — melakukan per-fold strategy re-fit.
2. Strategy di-instantiate per fold via `StrategyRegistry.get(name)` + `StrategyParameters(params=params)` — sinyal real, bukan momentum acak.
3. Mutasi diterima HANYA jika OOS Sharpe walk-forward improves vs baseline (fail-closed).
4. Mock backtest dihapus — `backtest_fn=None` default ke `_real_backtest`, reject langsung jika gagal.
**Owner:** researchbot + devbot ✅
**Gate:** Evolver rejects bad mutation (proven via real backtest), accepts good one. ✅

### PHASE D — BUILD REAL SELF-FINETUNER (P1, 3-5 hari)
**Masalah:** SelfFineTuner file hilang → vaporware.
**Fix (pilih 1):**
- **Option A (param evolution):** SelfFineTuner = wrapper ke StrategyEvolver + grid search. No LLM training needed. Simpel, works.
- **Option B (real LoRA):** Fine-tune tiny model (DistilBERT) on trade outcomes → predict signal. Butuh GPU/time. Overkill untuk sekarang.
- **RECOMMENDED:** Option A. Fine-tune = param mutation + walk-forward. Bukan LLM training. Sesuai "fine-tune" dalam konteks strategy, bukan model.
5. Create `quant_nanggroe/engine/strategy/strategies/self_finetune.py` (atau hapus import di autonomous.py).
**Owner:** devbot + researchbot
**Gate:** SelfFineTuner mutates params, validates via real backtest, registers improved strategy.

### PHASE E — CLOSED-PnL FEEDBACK LOOP (P0, 2 hari)
**Masalah:** Trade tertutup gak pernah diajarin strategi.
**Fix:**
1. `_close_position` → `pnl_evaluator.record_trade_result(strategy, realized_pnl)` ✅ (sudah ada).
2. Daily: aggregate per-strategy closed PnL → rank strategies by expectation.
3. Weekly: strategies dengan negative expectation → trigger StrategyEvolver (mutate params) atau disable.
4. Strategies dengan positive expectation → promote ke BEST_STRATEGIES.
**Owner:** traderbot + researchbot
**Gate:** After 20 closed trades, strategy ranking updates automatically.

### PHASE F — AUTONOMOUS PIPELINE (P0, 1 hari)
**Masalah:** Cron runner jalanin old code + paper mode.
**Fix:**
1. `qna-production-runner.py` → point ke `quant_nanggroe/live_engine.py` (bukan E:/trading/hedge_fund.py).
2. `PAPER_TRADE` → `false` (atau `QNA_MT5_LIVE=1`) setelah MT5 connect (Phase B).
3. Cron → LiveEngine.execute_cycle() → trade → close → evaluate → evolve → redeploy (no human).
4. Kill-switch: daily loss > 5% → halt ALL, notify Telegram.
**Owner:** autobot + devbot
**Gate:** Cron runs LiveEngine, real trade appears in journal, PnL reported to Telegram.

### PHASE G — CROSS-PROFILE ALARM (P1, 1 hari)
**Masalah:** Profiles gak aware QNA gak trade.
**Fix:**
1. autobot cron: check `journal.trades` count. If 0 for >24h → ALL profiles alert via vault_connector.
2. clawbot: adversarial-test LiveEngine ogni cycle (buktikan order keluar).
3. hackerbot: audit MT5 credential handling (redact).
**Owner:** autobot + clawbot + hackerbot
**Gate:** 0-trade alarm fires within 24h of silence.

---

## 5. PRIORITAS (P0 → P3)

| Phase | Priority | Effort | Impact |
|-------|----------|--------|--------|
| A. Unify execution | P0 | 1-2d | CRITICAL — tanpa ini, 0 trade |
| B. Connect MT5 | P0 | user | CRITICAL — tanpa ini, paper only |
| C. Real backtest→evolver | P0 | ✅ DONE | CRITICAL — ✅ SELESAI |
| E. Closed-PnL loop | P0 | 2d | CRITICAL — gak ada yang diajarin |
| F. Autonomous pipeline | P0 | 1d | CRITICAL — cron salah target |
| D. SelfFineTuner | P1 | 3-5d | HIGH — fine-tune vaporware |
| G. Cross-profile alarm | P1 | 1d | HIGH — silent failure |

---

## 6. TRUTH SUMMARY

**QNA belum "autonomous hedge fund yang trade sendiri."**
- Infrastructure: 70% (strategies, risk, evaluator, connector, orchestration)
- Execution: 0% (LiveEngine simulator, broker orphaned)
- Evolution: 40% (evolver real walk-forward, finetune hilang)
- Feedback: 0% (journal kosong, gak ada closed-PnL loop)
- Real trades: **0**

**Rute ke tujuan:**
1. Phase A (unify execution) → Phase B (MT5) → Phase F (pipeline) = TRADE NYATA dalam 1 minggu.
2. Phase C (done ✅) + Phase E = self-evaluate dari closed PnL.
3. Phase D = fine-tune nyata.
4. Phase G = paranoid cross-profile monitoring.

**Setelah Phase A+B+E+F:** QNA = autonomous hedge fund yang trade sendiri, evaluate dari closed PnL, evolve strategi. Itu tujuan lo. Sekarang kita di 70% infrastructure, 0% execution.

---
*Generated by Dhaher OS — 7-lens parallel audit. No simulation. Real evidence only.*
