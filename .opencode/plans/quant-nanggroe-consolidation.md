# QUANT NANGGROE AI — BATTLE PLAN

**Target: 100/100 — Isi saldo, mulai autonomous trading, semua beres.**
**Eksekusi: Parallel via sub-agents + 50 council.**

---

## DIAGNOSIS AWAL

**Fakta:** Codebase ini punya fondasi LUAR BIASA:
- RiskManager 963 lines (VaR, Kelly, drawdown, 9-checkpoint gate) — **tapi tidak dipakai pipeline**
- ExecutionManager 362 lines (guards, kill switch, broker routing) — **real**
- 106 strategies terdaftar — **real**
- 7 broker integrations (MT5, Alpaca, IBKR, CCXT, Paper, Polymarket, Solana) — **real**
- 32 route modules — **semua terdaftar**
- 17 dashboard pages — **arsitektur bagus**
- PaperExchangeBroker 900 lines (slippage, partial fills, P&L) — **real deal**

**Masalah:** Komponen hebat sendiri-sendiri tapi TIDAK TERINTEGRASI.
- RiskManager tidak dipanggil pipeline → risk cek confidence floor doang
- pipeline tidak di-trigger scheduler → cuma jalan via API manual
- `paper_state/` tidak ada → legacy dashboard 100% broken
- KillSwitch UI visual-only → tidak pernah hit backend
- WebSocket stream random fake data
- Doc rot parah: 32 discrepancies, 5 versi numerik berbeda

**Estimasi fungsional aktual: ~40%**

---

## TASK LIST — EKSEKUSI PARALEL

### FASE 0: DOKUMENTASI REALITAS
Target: Semua docs ngomongin realitas, bukan khayalan.

| Task | Deskripsi | Files | Priority |
|------|-----------|-------|----------|
| 0.1 | Konsolidasi versi: 4.3.4 sebagai source of truth | `README.md`, `docs/02_ARCHITECTURE.md`, `docs/04_API.md`, `docs/15_PROJECT_CONTEXT.md`, `docs/16_AI_MEMORY.md`, `docs/48_REPOSITORY_AUDIT.md` | High |
| 0.2 | Fix `16_AI_MEMORY.md`: ganti 18→106 strategies, /api/v1→/api/, hapus phantom Flask | `16_AI_MEMORY.md` | High |
| 0.3 | Fix `48_REPOSITORY_AUDIT.md`: hapus klaim prefix mismatch yang sudah resolved | `docs/48_REPOSITORY_AUDIT.md` | High |
| 0.4 | Update file/route/page counts di docs (661 py files, 32 routes, 17 pages) | `docs/02_ARCHITECTURE.md`, `docs/04_API.md` | Medium |
| 0.5 | Docs: engine/autonomous/ dan mcp/ subsystem tidak terdokumentasi | `docs/02_ARCHITECTURE.md` | Medium |
| 0.6 | Docs: paper_state/ perlu dibuat — update/tambahi dokumentasi | `README.md`, `docs/02_ARCHITECTURE.md` | High |

### FASE 1: NYAMBUNGIN ENGINE (URAT NADI)
Target: Pipeline end-to-end real → data → signal → risk(RiskManager) → execute.

| Task | Deskripsi | Files | Priority |
|------|-----------|-------|----------|
| 1.1 | **Integrasi RiskManager ke AutonomousPipeline.** Ganti `_check_risk()` stub (confidence 0.15) dengan panggilan ke real `RiskManager.check_trade()` + vaR + Kelly + kill switch + constitutional limits | `engine/agentic/autonomous.py`, `engine/risk/manager.py` | **CRITICAL** |
| 1.2 | **Buat Scheduler untuk AutonomousPipeline.** Pipeline berjalan periodik (default 15 menit) tanpa perlu manual trigger. Integrasi dengan daemon_manager.py | `daemon_manager.py`, `engine/agentic/autonomous.py` | **CRITICAL** |
| 1.3 | **Buat `paper_state/` directory.** Engine nulis state files real-time: `state.json`, `pnl.csv`, `kill_switch_state.json`, `positions.json`. Ini yang dibaca legacy dashboard | root level baru: `paper_state/` | **CRITICAL** |
| 1.4 | Wire `build_execution_manager()` agar default ke PaperExchangeBroker (yang 900 lines), bukan broker kosong | `engine/execution/builder.py` | High |
| 1.5 | Pipeline state persistence: state antar run tersimpan (positions, P&L, drawdown) | `engine/agentic/autonomous.py`, `engine/persistence.py` | High |

### FASE 2: BENERIN FRONTEND
Target: UI showing real data, semua wiring aman.

| Task | Deskripsi | Files | Priority |
|------|-----------|-------|----------|
| 2.1 | **Wire KillSwitch toggle → Backend.** Ganti local-only state di store dengan API call ke `POST /api/agents/kill-switch/activate` dan `/reset` | `dashboard/src/lib/store.ts`, `dashboard/src/app/agents/page.tsx`, `dashboard/src/app/risk/page.tsx` | **CRITICAL** |
| 2.2 | **Wire WebSocket ke data real.** Ganti `random.uniform()` di ws.py dengan data dari ExchangeManager / RiskManager. Price dari exchange, regime dari detector, portfolio dari position manager | `quant_nanggroe/api/routes/ws.py` | **CRITICAL** |
| 2.3 | Fix hardcoded path: `D:/repositories/...` → `process.cwd()` | `dashboard/src/app/api/qna-status/route.ts` | High |
| 2.4 | Fix trading page CSS: `bg-profit`/`bg-loss` undefined | `dashboard/src/app/trading/page.tsx` | Medium |
| 2.5 | Fix Memory page: "Store" button tidak punya onClick handler | `dashboard/src/app/memory/page.tsx` | Medium |
| 2.6 | Hapus/arsip dead code: `ecosystem.ts`, `data-hook.ts` | `dashboard/src/lib/ecosystem.ts`, `dashboard/src/lib/data-hook.ts` | High |
| 2.7 | Hapus hardcoded `cash_balance = total_value * 0.3` — ganti real dari broker | `dashboard/src/lib/store.ts` | Medium |
| 2.8 | Legacy HTML: update `paper_state/` fetch path atau redirect ke API endpoints | `quant_nanggroe/api/static/index.html`, `dashboard/qnai_dashboard.html` | Medium |

### FASE 3: KONSOLIDASI
Target: Satu canonical path untuk setiap fungsi, zero duplikasi.

| Task | Deskripsi | Files | Priority |
|------|-----------|-------|----------|
| 3.1 | Konsolidasi PaperBroker: pilih `exchange/paper_broker.py` (900 lines, full sim) sebagai canonical, deprecate/redirect dari `engine/execution/brokers/` | `exchange/paper_broker.py`, `engine/execution/brokers/` | High |
| 3.2 | Arsipkan orphan strategies di `quant_nanggroe/strategies/` — integrasikan ke registry atau hapus | `quant_nanggroe/strategies/` | Medium |
| 3.3 | Pastikan tidak ada circular imports di engine layer (trace dependency graph) | Multiple engine files | Medium |
| 3.4 | Update AGENTS.md dengan wiring diagram aktual | `AGENTS.md` | Medium |

### FASE 4: VERIFIKASI
Target: 100/100 — semua test pass, build clean, E2E verified.

| Task | Deskripsi | Files | Priority |
|------|-----------|-------|----------|
| 4.1 | Run test suite: `pytest tests/` — fix failures | `tests/` | **CRITICAL** |
| 4.2 | Run Next.js build: `cd dashboard && npm run build` — fix errors | `dashboard/` | **CRITICAL** |
| 4.3 | E2E test: POST /api/autonomous/pipeline/run → verified trade di paper_state/ | API → Engine → Broker | **CRITICAL** |
| 4.4 | E2E test: KillSwitch toggle UI → backend verified block | UI → API → Engine | High |
| 4.5 | E2E test: WebSocket show real price data (not random) | WS → ExchangeManager | High |
| 4.6 | Final audit: verifikasi semua wiring, update task status | All | High |

---

## ARCHITECTURE DECISIONS

**AD-1: RiskManager adalah single gate untuk semua trade.** Tidak ada jalan pintas. Baik manual API, autonomous pipeline, agent — semua lewat `RiskManager.check_trade()`.

**AD-2: `paper_state/` adalah single source of truth untuk state.** Engine nulis, dashboard baca. Format: JSON untuk state, CSV untuk timeseries.

**AD-3: PaperExchangeBroker (`exchange/paper_broker.py`) adalah canonical paper broker.** Yang di `engine/execution/brokers/` adalah legacy, diarahkan ke sini.

**AD-4: Scheduler built-in (bukan cron eksternal).** `daemon_manager.py` mengatur interval, pipeline jalan via asyncio loop.

---

## OPEN QUESTIONS
- (none — semua sudah teridentifikasi)

---


---

> **SSOT:** `CANONICAL.md` v8.1.4 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, vector 6 modul live, risk per-symbol
