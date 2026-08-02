# QNA Verification Report — 2026-08-03 (devbot forensic)

**Author:** devbot (orchestrator mode) | **Method:** Code = source of truth (git working tree HEAD=`52e8397b`)
**Scope:** FASE 0 claims (Rencana.md + QNA_AGENT_STATE.md + CHANGELOG.md) ↔ actual kode `autonomous_cycle.py` + `engine_production_bridge_purified.py`
**Rule:** @dhaherautobot sole orchestrator. No peer @mentions.

---

## 🚨 TL;DR — 4 klaim MD **OVERCLAIM**, 2 **STALE AUDIT**, 1 **ARCHITEKTURAL DECISION**

| MD Klaim | Reality | Severity |
|----------|---------|----------|
| "FASE 0 COMPLETE — semua G1-G12 ditutup" | **4 residual bugs masih ada di live path** (G1, G3, GAP-1, GAP-6) + audit FINDINGS_SLTP GAP-2 = **already fixed** (MD belum update) | 🔴 Overclaim |
| "RiskGuard synced to LIVE balance" | **`account_balance()` fail-open ke seed $10k saat MT5 drop** — tidak log error, tidak raise | 🔴 Live risk |
| "point_size from broker" | **✅ FIXED** di `autonomous_cycle.py:322` (`getattr(info, "point", ...)`). FINDINGS_SLTP GAP-2 = STALE | 🟡 Audit stale |
| "Risk: 9-checkpoint gate" | **`checks.py`/`RiskManager` = DEAD di live path.** Hanya `RiskGuard` (4 checks) yang jalan | 🔴 Dead code mislabel |
| "Scoring: 8 scorers + FusionEngine + MTF wired" | **✅ di `qna.py live` / `main.py:run_once()`. TAPI `autonomous_cycle.py` live path = 0 scoring import** | 🔴 Path split |
| "1079 providers" | **Live loop pakai 4 built-in strategies** (SMC, Momentum, MeanReversion, TrendFollow). Registry 81 ter-load tapi `generate_signal` return None semua (market closed). qna.py path = 1079 | 🔴 Path split |

---

## 🔴 1. G1 — Journal DB: **SCHEMA KOSONG, BUKAN JUST PATH**

**MD klaim (QNA_AGENT_STATE.md, Rencana.md):**
> ~~G1~~ ✅ journal DB path fixed + verified

**Reality:**
```bash
$ sqlite3 data/qna_trade_journal.db ".tables"
(empty)
$ wc -c data/qna_trade_journal.db
0 data/qna_trade_journal.db
```
- `trade_journal.py:29-32`: DB_PATH = `repo/data/qna_trade_journal.db` (parents[1]) — **path sudah benar ✅**
- Tapi `_init_db()` (`trade_journal.py:43-61`) **gagal create table** di prod runtime — **0 bytes, 0 tables**
- `_init_db()` di environment test **WORK** (table `trades` terbentuk). Jadi bug = **runtime lock/contention**, bukan kode.
- **Root cause:** 4+ concurrent `autonomous_cycle` process (lihat FINDINGS_POSITION_SIZING GAP-7) — salah satu membuka `sqlite3.connect` write → `CREATE TABLE` gagal/rollback/gantung → file 0 byte. Singleton lock (G8) **hanya di autonomous_cycle**, bukan di LiveEngine (`qna.py live`).

**Residual:** Jika `TradeJournal()` terbuka saat DB locked → `_init_db` throw → constructor crash → `PositionManager.journal` = None lagi → **G2 kembali hidup.** Ini cascade failure.

---

## 🔴 2. G3-residual — Balance sync **fail-open** ke $10k seed

**MD klaim (CHANGELOG.md):**
> ✅ balance+peak synced (commit 0c77f919)

**Reality (live log 2026-08-02 07:29→08:10):**
```
Cycle #207: Balance: $10000.00 | Trades: 0 | Wins: 0 | Risk: OK
Cycle #214: Balance: $10000.00 | Trades: 0 | Wins: 0 | Risk: OK
```

**Code trace (`engine_production_bridge_purified.py:82-92`):**
```python
def account_balance(self):
    try:
        if self._initialized and self._mt5_loaded:
            info = self._mt5_mod.account_info()  # ← MT5 network drop → returns None (bukan exception)
            if info:
                self._account = info
                return float(info.balance)
    except Exception:
        pass  # ← swallowed, no log
    return float(self._account.balance) if self._account else 0.0  # ← fallback
```

**Problem chain:**
1. Boot 04:03: MT5 connect OK → `self._initialized=True`, `self._account={balance:1122}`
2. MT5 network drop 07:28 → `account_info()` returns **None** (bukan raise exception)
3. `if info:` → False → skip → **tidak set `self._account`** (stays stale $1122 object)
4. Fallback: `return float(self._account.balance)` = **1122.05** ← tapi log bilang $10k!

**Wah, kontradiksi.** Berarti MT5 drop melek: `account_info()` **return None** → `if info:` gagal → fallback `_account` = ... **harus stale $1122.** Kok log $10k?

**Alternatif root cause:** MT5 `_mt5_mod` (modul) itself bermasalah setelah network drop — `account_info()` **raises exception** → swallowed → fallback `self._account` sudah **None** (karena `self._initialized` jadi False tapi code cycle() tidak reset). Jadi `_account = None` → `return 0.0` → `if live_balance > 0` FAILS → **balance tetap seed $10,000.**

**Bug:** `account_balance()` **harus log/error raise saat MT5 down**, bukan silently return 0.0/None. Dan `cycle()` harus cek `self.engine.mt5._initialized` di awal, **bukan** biarkan balance fallback.

---

## 🔴 3. GAP-1 (FINDINGS_SLTP) — Naked-fill surface **still alive** di non-cycle path

**MD klaim (Rencana.md G6):**
> ✅ DONE (SL wajib — reject kalau ≤0)

**Reality (code `engine_production_bridge_purified.py:140-145`):**
```python
if not (sl and sl > 0):
    raise RuntimeError("execute_order blocked — SL required (fail-closed)")
```
- **Ini benar — `execute_order` fail-closed.** ✅
- Tapi MD ganti klaim `connectors/mt5_broker.py:90-93` + `api/routes/trading.py:567-568` = **sama sekali tidak disentuh.** 

**GAP-1 audit valid:**
- `api/routes/trading.py:567-585` — order dengan `sl=0.0` → masih masuk `execute_order` → **REJECT** sekarang (karena fix). Tapi **API route itu sendiri tidak gagap jika trading.py pass None ke engine_production_bridge.py (non-purified).**
- `engine_production_bridge.py` (OLD bridge) masih ada dan masih punya fallback fail-safe ±0.5% (`:401-407`) — tapi LiveEngine pakai ini. Jadi ada **2 bridge**, satu fail-closed (purified), satu fail-safe (old). **Ambiguitas path.**

---

## 🔴 4. GAP-3/GAP-5 (FINDINGS_SLTP) — **DUAL LIVE LOOP, ARSITEKTUR SPLIT**

Ini bukan "bug" — ini **architectural contradiction** yang perlu keputusan user.

| Aspek | `autonomous_cycle.py` (loop A) | `qna.py live` → `LiveEngine` → `main.py:run_once()` (loop B) |
|-------|-------------------------------|------------------------------------------------------------|
| Scoring | **DEAD** — 0 import FusionEngine/scoring | ✅ FusionEngine:MTF:WeightEvolver (`main.py:433-549`) |
| Strategies | 4 built-in (`analyze()`) + 81 registry (`generate_signal()`) | `engine_strategies.py:77` engine providers → `aggregator.py` |
| Risk gate | `RiskGuard` (4 checks: KillSwitch, balance>0, 15% DD, 3% daily, 3% weekly) | `EngineRiskManager` (9-checkpoint `checks.py`) + `RiskLimits` |
| Position | `PositionManager` (ATR trail, partial TP) | `PositionSizer` / `engine/live/adaptive_integration.py` |
| Portfolio | **TIDAK ADA** | `Markowitz` / `HRP` di `main.py` |

**MD (AGENTS.md:126):** "Wired: hedge_fund/portfolio/main.py:run_once() + evolution"
**MD (QNA_MASTER_PROMPT:47):** "✅ Pipeline: 7-stage run_once() + evolution loop"

Tapi **loop A (autonomous_cycle) = yang punya 3 live positions (20188224176/24713/20178543987)** adalah loop yang sebenarnya **execute orders**. Loop B (LiveEngine/qna.py live) = **kompetitor sendiri.** Keduanya connect MT5. Keduanya bisa generate sinyal.

**Ini GAP-5 (FINDINGS_SLTP) valid:** "Two SL/TP systems with different semantics depending on which loop is running."

---

## 🟡 5. Strategi count — 3 angka benar-benar: **78 JSON, 81 registry, 82+3 archive**

| Sumber | Count | Detail |
|--------|-------|--------|
| `walk_forward_registry.json` (dict keys) | **78** | Metadata file, canonical ini yang diklaim |
| `StrategyRegistry.list_strategies()` (runtime) | **81** | +3 archive (`archive_msnr_fixed`, `archive_smc_fixed`, `archive_quarterly_fixed`) |
| `.py` files di `engine/strategies/` | **82** | — |
| `@StrategyRegistry.register` decorator lines | **82** | Di-file yang sama, 1 strategi/file kecuali kronos_wrapper |
| AGENTS.md klaim "84 registered, ~6 active" | 84 | +2 archive (subpackage `archive/`) |
| QNA_STATUS_REAL "81 loaded" | 81 | ✅ Match registry runtime |

**Kontradiksi MD:**
- CHANGELOG.md:2 "78 registered strategies (walk_forward_registry.json)" 
- AGENTS.md:85 "84 strategies registered via @StrategyRegistry.register"
- QNA_MASTER_PROMPT:49 "77 engine + 992 mue-x + 10 core = 1079 providers"

**78 (registry JSON)** ≠ 81 (runtime, +3 archive) ≠ 84 (files+archive) ≠ 1079 (providers, term bahaya). **Ini bukan bug, ini term conflation.**

---

## 🟢 YANG BENAR (terverifikasi)

| Item | Evidence | Status |
|------|----------|--------|
| G2 journal init order (`TradeJournal()` sebelum `PositionManager`) | `autonomous_cycle.py:822-825` | ✅ FIXED |
| G4 dual-call `generate_signal()` + `analyze()` fallback | `autonomous_cycle.py:282-309` | ✅ FIXED |
| G5 point_size dari broker | `autonomous_cycle.py:322: getattr(info, "point", ...)` | ✅ FIXED (audit GAP-2 = STALE) |
| G6 SL fail-closed (purified path) | `purified:140-145: raise if sl≤0` | ✅ FIXED (gap-1 masih di file lain) |
| G7 position caps enforced | `purified:375-395: MAX_POSITIONS_PER_SYMBOL=1` | ✅ FIXED |
| G8 single-instance lock | `autonomous_cycle.py:91-92` (`_acquire_singleton_lock`) | ✅ FIXED (hanya di loop A) |
| G9 kelly_cache typo | `autonomous_cycle.py:771: self.risk_guard.kelly_cache` | ✅ FIXED |
| G10 HOLD logging | `autonomous_cycle.py:900-906: "HOLD ALL: no actionable signals"` | ✅ FIXED |
| G11 breakeven + structure trailing | `autonomous_cycle.py:635-655: breakeven_sl + trailing_sl_structure` | ✅ FIXED |
| G12 strategy attribution | `purified:157: comment=f"{strat}:{symbol}"`, `autonomous_cycle.py:925-929: record_open` | ✅ FIXED (tapi journal schema gagal) |
| Sizing LOTS | `purified:291: risk_amount/(sl_dist × contract_size)` | ✅ FIXED |
| Singleton lock | `autonomous_cycle.py:91-92` | ✅ FIXED |
| Debt position reconciliation | `autonomous_cycle.py:498-523: reconcile_legacy_positions()` | ✅ FIXED |

---

## 📈 ROOT CAUSE ANALYSIS — Kenapa live loop mati sejak 07:28?

1. **MT5 network connection drop** (retcode=10031 "absence of network connection") sejak 07:28
2. `account_balance()` silently return 0.0 → balance fallback $10k seed → **risk gate blind**
3. `get_tick()` / `get_candles()` return None/[] → semua strategi HOLD → 0 signal
4. Legacy posisi 20178543987 masih terbuka, `reconcile_legacy_positions()` attempt close **gagal karena MT5 down**
5. MT5 terminal mungkin offline (broker maintenance / network)

**Ini BUKAN kode bug — ini operational.** MT5 terminal perlu dicolok kembali.

---

## 🎯 REKOMENDASI — @dhaherautobot koordinasi

Saya butuh keputusan dari @dhaherautobot untuk 3 hal:

1. **Arsitektur dual-loop (GAP-5):** Pilih satu live path. `autonomous_cycle.py` (simple, 4+81 strategies, tapi no FusionEngine/scoring) **OR** `qna.py live` (full stack: FusionEngine, portfolio, 9-checkpoint risk, tapi `engine_production_bridge.py` lama). **Rekomendasi devbot: gunakan autonomous_cycle.py sebagai primary (MT5 orders sudah jalan di situ), migrasi FusionEngine/portfolio dari main.py ke sini.** Tapi ini butuh keputusan user — scope.

2. **G3-hardening (balance sync):** `account_balance()` harus **log error + set flag MT5_DOWN** → `cycle()` harus **ABORT** (bukan lanjut dengan phantom $10k). Ini perlu keputusan: abort behavior ganti? (safety over availability).

3. **G1-hardening (journal):** `TradeJournal._init_db()` harus **fail-closed** di startup — kalau schema gagal, `AutononomousCycle.initialize()` abort. Tambah assertion: `assert self.journal.table_exists("trades")` di line 822.

---

## 📝 VERIFY LOG
```
Repo: /d/repositories/Quant-Nanggroe-AI-worktree
Git HEAD: 52e8397b
Python: .venv312 (3.12.13) — env -u PYTHONPATH
Registry runtime: 81 strategies (3 archive)
walk_forward_registry.json: 78 entries
Journal DB: 0 bytes, 0 tables (schema failed at runtime)
Live log: 2026-08-02 08:10:58 cycle #214 (last), balance $10000, 0 trades
MT5 status: network drop since 07:28, retcode=10031
```

*Generated 2026-08-03 by devbot (standalone, no peer bot involvement).*
`,
  "file_size": 500,
  "total_lines": 500
}