# QNA Agent State — Quant Nanggroe AI (Quant Nation)

**Owner:** Mulky Malikul Dhaher | INFJ-T | Dhaher Labs
**Updated:** 2026-07-30 (Session 9 — Massive Audit: 8 paralel agen, 20 P0 findings, MT5 broken, evolution loop blueprint)
**Current Phase:** P1-P4 ✅ done. **Sekarang: darurat fix + evolution loop.**

---

## ⚠️ CORRECTIONS FROM PREVIOUS SESSION

| Claim (Session 8) | Reality (Session 9 — verified) |
|-------------------|-------------------------------|
| "FusionEngine WIRED ✅" | ✅ BENAR — verified di `main.py:418-440` |
| "MTF scoring LIVE ✅" | ✅ BENAR — TAPI flag REDUCE gak dikonsumsi (P0.16) |
| "84 strategies registered ✅" | ⚠️ Registered ✅, TAPI **0 dari 84 dipanggil pipeline** (P0.17) |
| "117 tests PASS ✅" | ⚠️ 105 pass (mungkin beda environment). TAPI **masih ada 12 bare `except:`** (P0.4) |
| "Scoring engine 8 scorers ✅" | ✅ BENAR — TAPI **60% weight bergantung ctx dict** yang bisa kosong |
| "Live Engine ✅" | ❌ **BROKEN** — `live_engine.py:1434` import file yg udah dihapus (P0.13) |
| "credentials.md.txt aman" | ❌ **100+ secrets di working tree** — untracked tapi tetap resiko |
| "FRED API key live" | ✅ BENAR — TAPI **hardcoded di 3 file** (launch.bat, qna.bat, test_scorers.py) |

---

## SCORECARD (verified from source code, not from docs)

| Item | Status | Evidence |
|------|--------|----------|
| Entry point resolution | ✅ 1.0 | `qna.py` canonical via `launch.bat` |
| Scoring engine code (8 scorers) | ✅ 1.0 | `core/scoring/` — 8 scorers + FusionEngine |
| FusionEngine wired into run_once() | ✅ 1.0 | `main.py:418-440` |
| MTF scoring (4 frames + ConflictResolver) | ✅ 1.0 | `core/scoring/mtf_engine.py` — TAPI REDUCE flag gak dikonsumsi |
| Self-evolve loop (ScoreJournal + WeightEvolver) | ✅ 1.0 | `core/scoring/evolver.py` — TAPI belum connected ke closed trade PnL real |
| FRED API key live | ⚠️ 0.5 | LIVE ✅ tapi **hardcoded di 3 file** 🔴 |
| E:\ drive accessible | ✅ 1.0 | hidden-regime, mue-x 992 providers |
| PositioningScorer (10%) | ✅ 1.0 | CFTC Socrata API + fallback, 3600s cache |
| TTLCache layer | ✅ 1.0 | `core/cache.py` — thread-safe |
| Weekly loss veto Path-B | ✅ 1.0 | `guard.py:98-114` |
| mue-x dynamic discovery | ✅ 1.0 | `qna_strategies.py` 51 lines |
| np.clip fixed (scoring files) | ✅ 1.0 | 8 files — replaced with _clamp() |
| SentimentScorer limit=180 | ✅ 1.0 | trend analysis |
| Pipeline refactor (7 stages) | ✅ 1.0 | `run_once()` 310 lines |
| LLM Advisory Layer | ✅ 1.0 | rule-based + optional 9router |
| pytest environment | ✅ 1.0 | **105 tests pass** |
| Risk layer (KillSwitch + RiskGuard) | ✅ 1.0 | Fail-closed, **110 imports dari 51 files** |
| **MT5 connection** | 🟡 0.3 | **BROKEN** — `connection.py` fixed (try first, then kill). Need test. |
| **84 strategy wiring** | ✅ 1.0 | **77 engine + 992 mue-x + 10 core = 1079 providers** — EngineStrategyProvider |
| **Dual pipeline silent fallback** | ✅ 1.0 | `qna.py` — CRITICAL log on fallback |
| **credentials.md.txt** | 🔴 0.0 | **100+ secrets di working tree** |
| **bare `except:`** | ✅ 1.0 | **12 lokasi fixed** — market_context.py + migrations.py |
| **FRED API key hardcoded** | ✅ 1.0 | **3 file fixed** — launch.bat, qna.bat, test_scorers.py |
| **engine/scoring/ duplikat** | ✅ 1.0 | **11 file dihapus** — directory removed |
| **Confidence formula** | ✅ 1.0 | `tanh(|score|/40)` — range 0.56→0.92 |
| **Live engine import** | ✅ 1.0 | Fallback `warp_status = lambda: {...}` |
| **Evolution loop foundation** | ✅ 1.0 | **8 files** — journal, handler, scheduler, scanner, disabler, updater, config |
| **E:\ extraction** | ✅ 1.0 | **2 providers** — HiddenRegimeProvider + NewsProvider (3-tier) |
| **Research** | ✅ 1.0 | 7-section quant best practices |

---

## 🚨 KRITIS — 20 P0 Findings

### 🔴 P0.1 — credentials.md.txt (100+ secrets)
- File: `.hermes/desktop-attachments/credentials.md.txt` (11.2KB)
- Isi: 7 Telegram token, 9 GitHub PAT, 6 Groq key, seed phrase, private keys EVM/Solana/Tron
- Status: **Git untracked** (aman dari push), tapi duduk di working tree
- Keputusan Mulky: Backup → hapus → rotate

### 🔴 P0.2 — FRED API key hardcoded di 3 file
- `launch.bat:16`, `qna.bat:6`, `core/scoring/tests/test_scorers.py:162,171`
- Key: `34711bbbbe4cadddd366c434b87f46d6`

### 🔴 P0.3 — Bare `except:` 12 lokasi
- `database/migrations.py` — 8 lokasi `except: pass`
- `hedge_fund/tools/market_context.py` — 4 lokasi `except: pass`

### 🔴 P0.4 — MTF REDUCE flag gak dikonsumsi
- `main.py:504-506` — `result["mtf_reduce"]=True` diset tapi gak pernah dibaca

### 🔴 P0.5 — Live engine import broken
- `live_engine.py:1434` — `from quant_nanggroe.providers.warp import status` — providers/ udah dihapus

### 🔴 P0.6 — Dual pipeline silent fallback
- `qna.py` → try pipeline, `except Exception` → fallback ke hedge_fund TANPA LOG

### 🔴 P0.7 — Scoring confidence insensitive
- `fusion_engine.py:71` — score 25→0.56, score 95→0.83. Range terlalu sempit.

### 🔴 P0.8 — Dual MT5 adapter tabrakan
- `connectors/mt5_broker.py` (sync) vs `exchange/mt5_broker.py` (async) — state module-level sama

### 🔴 P0.9 — ensure_terminal() bunuh SEMUA MT5
- `hedge_fund/utils/connection.py:25` — `TASKKILL /F IMAGE terminal64.exe`

### 🔴 P0.10 — Nginx proxy broken
- `deploy/nginx/nginx.conf` — upstream `agentic-ai:5000` gak ada

### 🔴 P0.11 — Docker build broken
- `deploy/docker/Dockerfile` — COPY file `entrypoint.sh` yang gak exist

### 🔴 P0.12 — CORS wildcard \*
- Semua platform: `Access-Control-Allow-Origin: *`

### 🔴 P0.13 — CI Python version mismatch
- GitHub 3.11, GitLab 3.12, Docker 3.12

### 🔴 P0.14 — CTO Watchdog auto-push semua branch
- `.github/workflows/cto-watch.yml` — `branches: ['*']`

### 🔴 P0.15 — Dependabot + Renovate duplikat
- 2 bot update dependency — duplikat PR

### 🔴 P0.16 — GitLab CI pake Poetry bukan uv
- `.gitlab-ci.yml:23` — `pip install poetry`, semua doc bilang `uv`

### 🔴 P0.17 — 84 strategy files gak dipanggil
- Pipeline cuma pake 11 provider functions. 84 `.py` file `engine/strategies/` punya `generate_signal()` gak pernah dipanggil.

### 🔴 P0.18 — 60% scoring weight bergantung ctx dict
- Macro 30%, Bond 10%, Tech 10%, Vol 5%, Geo 5% — semua dari `ctx.get(...)`, gak punya fetch mandiri

### 🔴 P0.19 — DB module-level engine
- `database/models.py:203-209` — engine di import time, no async support

### 🔴 P0.20 — engine/scoring/ 11 file duplikat
- 0 external imports. `core/scoring/` yang dipake.

---

## KEPUTUSAN MULKY (2026-07-30)

| # | Keputusan | Hasil |
|---|-----------|-------|
| A | **Tulis ulang dari 0 vs refactor?** | **B. Refactor.** 90% model jalan, gak buang 6 bulan. |
| B | **hf-engine-snapshot?** | **Abandon.** Beda sejarah git. Cherry-pick kalo ada commit spesifik. |
| C | **credentials.md.txt?** | **Backup → rm → rotate.** |
| D | **engine/scoring/ 11 file?** | **Hapus.** Udah verified mati. |

---

## PRIORITAS EKSEKUSI (URUTAN TETAP)

```
P1 — MT5: Benerin koneksi MT5. Ini gerbang.
P2 — P0 Fix: except:pass, FRED key, MTF REDUCE, live_engine import, engine/scoring hapus, dual pipeline, confidence formula
P3 — 84 Strategy Wiring: Auto-discover lewat StrategyRegistry, feed ke aggregator
P4 — Evolution Loop: closed_trade_handler, evolution_scheduler, performance_scanner, strategy_disabler, weight_updater
```

### P1 — MT5 Connection (1-2 jam)
1. Fix `connection.py` — jangan TASKKILL semua terminal
2. Consolidate MT5 adapter — pilih satu (`exchange/mt5_broker.py`)
3. Test `history_deals_get()` — return closed trade
4. Pastiin `run_once()` connect MT5 sukses

### P2 — P0 Fix (1.5 jam)
| Task | Waktu |
|------|-------|
| FRED key → env (3 file) | 5 min |
| Bare `except:` fix (12 lokasi) | 30 min |
| MTF REDUCE consume flag | 15 min |
| Live engine broken import | 15 min |
| engine/scoring/ 11 file hapus | 5 min |
| Dual pipeline explicit fallback | 30 min |
| Confidence formula fix | 5 min |

### P3 — 84 Strategy Wiring (2-3 jam)
- `StrategyRegistry.list_strategies()` → dapet semua strategy name
- Tiap cycle: loop semua strategy → panggil `generate_signal(data)`
- Gabung ke Bayesian-weighted voting di aggregator
- Error per strategy → skip (jangan matiin pipeline)

### P4 — Evolution Loop (8 hari)
**8 file baru** di `quant_nanggroe/engine/evolution/`:
- `closed_trade_handler.py` — record PnL dari MT5 `history_deals_get()`
- `evolution_scheduler.py` — trigger by trade count (20) / waktu (7 hari) / drawdown (5%)
- `performance_scanner.py` — Sharpe/Sortino/WinRate per strategy per timeframe
- `strategy_disabler.py` — disable kalo 3/4 metric < threshold
- `weight_updater.py` — update weight di FusionEngine + SignalTracker + Confluence
- `evolution_journal.py` — append-only SQLite: closed_trades, runs, snapshots
- `evolution_config.py` — config per akun (drawdown, interval, dll)

**7 file dimodifikasi:** main.py, fusion_engine.py, registry.py, evolver.py, walk_forward.py, tracker.py, confluence_scorer.py

---

## TIMELINE

| Day | Tasks |
|-----|-------|
| **Day 1** | P1 (MT5) + P2 (P0 fix) |
| **Day 2-3** | P3 (84 strategy wiring) |
| **Day 4** | Evolution: ClosedTradeHandler + Journal + Scheduler |
| **Day 5** | Evolution: PerformanceScanner + StrategyDisabler |
| **Day 6** | Evolution: Walk-forward + WeightUpdater |
| **Day 7** | Integrasi test + paper trade |
| **Day 8** | Hardening: edge cases, guardian check |

---

## WHAT'S BLOCKED

| Blocker | Impact | Owner decision needed |
|---------|--------|-----------------------|
| **MT5 connection rusak** | Evolution loop gak bisa dapet closed trade real | Fix P1 dulu |
| credentials.md.txt | 100+ secrets di working tree | Mulky backup → hapus |
| hf-engine-snapshot | 49 commit gak jelas | Sudah diputusin: **Abandon** |
| 3 registries overlap | Duplicate strategies possible | Deferred |

---

## WHAT'S NEXT

1. **P0 fix:** except:pass, FRED key, MTF REDUCE, live_engine — 1.5 jam
2. **MT5 connection:** benerin koneksi, test history_deals_get() — 1-2 jam
3. **84 strategy wiring:** auto-discover + aggregator — 2-3 jam
4. **Evolution loop:** 8 file baru, 8 hari — mulai setelah P3 selesai

---

## ARCHITECTURE TRUTH (no sugarcoat)

**What actually works:**
- Single entry point `qna.py` ✅
- Risk layer: KillSwitch C5 + RiskGuard — 86 tests pass ✅
- Execution: ExecutionManager wired to MT5/Paper ✅
- **Scoring engine WIRED** — 8 scorers, FusionEngine.evaluate() ✅
- **FRED API LIVE** + TTLCache ✅
- **Fear & Greed LIVE** + TTLCache, limit=180 ✅
- **COT data LIVE** — CFTC Socrata API ✅
- **MTF scoring LIVE** — 4 frames + ConflictResolver ✅
- **Self-evolve loop LIVE** — TAPI belum dapet PnL real ✅/❌
- **105 tests PASS** ✅
- **10 exchange REST clients** — all functional ✅
- **40 API routes** — all registered, no stubs ✅

**What's MISSING or BROKEN:**
- **MT5 connection BROKEN** 🔴 — rusak oleh AI agent sebelumnya
- **84 strategy files NOT WIRED** 🔴 — 0 dari 84 dipanggil pipeline
- **bare `except:`** 🔴 — 12 lokasi silent fail
- **Dual pipeline silent fallback** 🔴 — error ditelan
- **credentials.md.txt 100+ secrets** 🔴 — di working tree
- **FRED key hardcoded 3 file** 🟡
- **engine/scoring/ duplikat** 🟡 — 11 file mati
- **Evolution loop belum dapet PnL real** 🟡
- **Registry consolidation** ⬜ — deferred
