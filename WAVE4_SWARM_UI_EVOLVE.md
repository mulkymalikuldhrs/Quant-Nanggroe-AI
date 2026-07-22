# QNA WAVE 4 — SWARM ARCHITECTURE + UI WIRING + SELF-EVOLUTION

> Fokus: (1) arsitektur swarm — 50-agent council + MUE-X + autonomous loop jalan paralel tanpa
> konflik (file-lock / shared-state), (2) wiring dashboard UI ke backend yang benar,
> (3) self-evolution: status bridge MUE-X (`E:/mue-x/bridge_state.json`) dan apakah
> strategi auto-evolve masuk ke QNA registry.
>
> Semua `file:line` di bawah diverifikasi dengan grep/read langsung terhadap worktree ini.
> Bahasa: Indonesia.

---

## 0. STATUS FAKTA (diverifikasi, bukan asumsi)

### A. UI wiring — klarifikasi penting pada premis task
- **Dashboard Next.js (`dashboard/`) TIDAK pakai `/api/v1`**. `dashboard/src/lib/api-client.ts:1`
  mendefinisikan `const API_BASE = process.env.NEXT_PUBLIC_API_URL || ""` dan `:93` memanggil
  `` `${API_BASE}${endpoint}` `` di mana `endpoint` = `/api/...` (no version). Grep `/api/v1` di
  `dashboard/src/**` (ts + html) = **0 hit**. Jadi premis "dashboard reference /api/v1" SALAH.
- **Mismatch `/api/v1` ada di CLI, bukan dashboard**: `quant_nanggroe/cli.py:406`
  `httpx.get("http://localhost:8000/api/v1/portfolio")` → backend serve `/api/portfolio` → **404
  silent fallback** (ini temuan #24 di WAVE_COUNCIL). Perbaiki di CLI, bukan di FE.
- **Dua dashboard bentrok**: root `dashboard.py` adalah FastAPI STUB (hardcode 6 strategi,
  `dashboard.py:34-56`) dan `autonomous-loop.bat` menjalankannya via `uvicorn dashboard:app --port 5050`.
  Sementara dashboard ASLI adalah Next.js di `dashboard/` (pakai `api-client.ts`, `store.ts`).
  Backend ASLI adalah `quant_nanggroe/api/app.py` di port 8000. `dashboard/.env.local`:
  `NEXT_PUBLIC_API_URL=http://localhost:8000`. → Ada dual-dashboard + port ambiguity yang membingungkan wiring.
- **Bug nyata di backend**: `quant_nanggroe/api/app.py:374-379` memanggil
  `include_router(memory_stub/colony_stub/security_tools_stub)` **DUA KALI** (duplikat).
  FastAPI mendaftarkan route ganda → route stub menimpa route asli (shadowing) + warning startup.

### B. Self-evolution / MUE-X bridge
- `E:/mue-x/bridge_state.json` AKTIF: `total_mutations: 136`, `last_evolved.qna` timestamp ada,
  `created_genes` berisi `qna_*Strategy_mut_*` (MSNR/SMC/MeanReversion/Fibo/EMAADX/AMDX/Algebra/Wyckoff).
- **Bridge MUE-X → QNA ADA tapi di jalur LEGACY**: root `hedge_fund.py:332` (dan ~25 fn
  `signal_qna_*`) melakukan `sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")` lalu
  `from qna_*Strategy_mut_* import generate_signal, PARAMS`. Jalur ini dipakai `autonomous-loop.bat`
  (`hedge_fund_mtf.run_mtf_cycle()` dari `E:/trading`, lalu `xcopy` ke QNA).
- **TAPI genes TIDAK masuk QNA registry asli**: `quant_nanggroe/engine/strategy/registry.py`
  grep `mue-x|bridge_state|qna_strategies|created_genes` = **0 hit**. Genes dipanggil via wrapper
  ad-hoc `signal_qna_*` (bypass `StrategyRegistry.register` di `strategy_registry.py:14`),
  bypass validasi/walk-forward/kill-switch. → auto-evolve jalan di monolit legacy, tidak di engine QNA.

### C. Swarm paralel / koordinasi
- 50-agent council (`quant_nanggroe/agents/council/`, `debate/`, `colony.py`), MUE-X (eksternal
  `E:/mue-x`), autonomous loop (`autonomous-loop.bat` + `quant_nanggroe/engine/scheduler.py:111`
  `asyncio.create_task`).
- **C5 (split-brain) belum beres**: `engine/hermes_shared_state.py:62` `_restore_state()` hanya di
  `__init__`, `reconcile` = 0 repo hit. Kill-switch per-proses tidak sinkron. Ini inti masalah
  "jalankan paralel tanpa conflict".
- `colony.py` spawn agent via single `create_task` tanpa `Semaphore`/`asyncio.Lock` → tidak ada
  batas konkurensi atau mutual-exclusion tulis ke state file.

---

## 1. ARSITEKTUR SWARM QNA (desain target)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        SWARM COORDINATOR (single writer)                 │
│  quant_nanggroe/engine/swarm/coordinator.py  (BARU)                       │
│  - FileLock registry: .qna-swarm/agents.lock  (filelock, cross-process)  │
│  - SharedState: Redis atau SQLite WAL + busy_timeout (bukan in-memory)   │
│  - Semaphore global: max 8 agent berjalan konkuren per siklus            │
└───────────────┬───────────────────────────────────────┬──────────────────┘
                │                                        │
   ┌────────────▼─────────┐                ┌─────────────▼──────────────┐
   │ 50-AGENT COUNCIL     │                │ MUE-X BRIDGE (ext E:/mue-x)│
   │ council/debate/      │                │ swarm/muex_bridge.py       │
   │ colony.py            │                │ baca bridge_state.json     │
   │ (debate, voting,     │                │ → daftarkan gene ke        │
   │  personas, macro...) │                │ StrategyRegistry (engine)  │
   └────────────┬─────────┘                └─────────────┬──────────────┘
                │                                        │
                └───────────────┬────────────────────────┘
                                ▼
                ┌───────────────────────────────┐
                │ AUTONOMOUS LOOP (scheduler.py) │
                │ cycle 15m: debate→signal→risk  │
                │ →(MUE-X gene)→paper/live       │
                └───────────────┬───────────────┘
                                ▼
                ┌───────────────────────────────┐
                │ SHARED STATE (single source)  │
                │ kill_switch / positions /     │
                │ lessons / gene_registry       │
                │ → filelock + SQLite WAL       │
                └───────────────────────────────┘
```

**Prinsip anti-konflik:**
1. **Single-writer shared state** — semua proses (api, daemon, bridge, loop) baca/tulis state lewat
   satu modul `swarm/state.py` yang pakai SQLite `WAL` + `busy_timeout=5000` + `filelock` per write.
   Menyelesaikan C5 (kill-switch split-brain, `hermes_shared_state.py:62`).
2. **FileLock per agent** — setiap agent yang menulis file (council log, gene, lesson) ambil
   `filelock` bernama (`agent_id.lock`) sebelum tulis. Mencegah race antar 50 agent.
3. **Semaphore konkurensi** — `asyncio.Semaphore(8)` di coordinator; agent yang spawn task lewat
   coordinator, bukan `create_task` langsung (`colony.py`).
4. **Gene registry terpusat** — MUE-X genes masuk `StrategyRegistry` (engine), bukan wrapper ad-hoc,
   agar dapat validasi + walk-forward + kill-switch.

---

## 2. REKOMENDASI PER-AGENT (24 roles, 1 konkret + file:line)

### 1. DevOps
- **Rekomendasi**: Hapus dual-dashboard. `autonomous-loop.bat` jangan jalankan `uvicorn dashboard:app`
  (stub root `dashboard.py`); ganti ke `next start` (Next.js `dashboard/`) atau reverse-proxy ke :8000.
  Satu otoritas UI.
- **file:line**: `autonomous-loop.bat:18` (`start ... uvicorn dashboard:app --port 5050`); stub di
  `dashboard.py:34-56`.

### 2. Systems Architect
- **Rekomendasi**: Buat `quant_nanggroe/engine/swarm/coordinator.py` sebagai single-writer shared-state
  (SQLite WAL + `filelock`) dan ganti singleton mati `hermes_shared_state.py` dengan delegasi ke sana.
- **file:line**: `engine/hermes_shared_state.py:62` (`_restore_state()` hanya di `__init__`, `reconcile`
  tidak dipanggil); target baru `engine/swarm/coordinator.py`.

### 3. Frontend
- **Rekomendasi**: Pastikan `NEXT_PUBLIC_API_URL` di-build time benar dan tambahkan healthcheck di
  `api-client.ts` (retry + fallback ke `/health`). FE sudah benar pakai `/api/` (bukan `/api/v1`) —
  jangan diubah ke `/api/v1`.
- **file:line**: `dashboard/src/lib/api-client.ts:1,93`; `dashboard/.env.local`
  (`NEXT_PUBLIC_API_URL=http://localhost:8000`).

### 4. API Designer
- **Rekomendasi**: Perbaiki CLI yang pakai `/api/v1/portfolio` → `/api/portfolio` (atau tambahkan
  router compat `/api/v1/*` di `wiring_compat.py`). Ini mata rantai `/api/v1` yang sesungguhnya.
- **file:line**: `quant_nanggroe/cli.py:406`
  (`httpx.get("http://localhost:8000/api/v1/portfolio")` → 404).

### 5. Data Pipeline
- **Rekomendasi**: Genes MUE-X yang diimpor (`hedge_fund.py:332`) harus melewati validasi data
  (NaN/inf/UTC) sebelum `generate_signal`. Pasang pydantic-validation gate di bridge, bukan raw dict.
- **file:line**: `hedge_fund.py:332-348` (`sys.path.insert` + `from qna_* import generate_signal`);
  lihat juga validasi mati di `data/providers/*` (WAVE2 #16).

### 6. Agent Framework
- **Rekomendasi**: Ganti spawn `asyncio.create_task` langsung di colony dengan `coordinator.spawn()`
  ber-`Semaphore(8)` + `filelock` per agent, sehingga 50 agent tidak race menulis state.
- **file:line**: `quant_nanggroe/agents/colony.py` (spawn tanpa lock); `engine/scheduler.py:111`
  (`asyncio.create_task(self._run_loop())`).

### 7. MLOps
- **Rekomendasi**: Daftarkan MUE-X genes ke `StrategyRegistry` engine (bukan wrapper `signal_qna_*`),
  agar gene ikut pipeline walk-forward + kill-switch. Buat `swarm/muex_bridge.py` yang baca
  `bridge_state.json` → `registry.register(gene)`.
- **file:line**: `strategy_registry.py:14` (`def register`); `quant_nanggroe/engine/strategy/registry.py`
  (0 hit mue-x); `hedge_fund.py:332` (jalur legacy).

### 8. Research Scientist
- **Rekomendasi**: Genes MUE-X (`created_genes` di `bridge_state.json`) tidak boleh dianggap OOS —
  terapkan walk-forward per-fold saat didaftarkan (perbaiki `run_walk_forward` leaky, #1/#50).
- **file:line**: `engine.py:451` (`run_walk_forward` → `analyzer.analyze` backtest whole-series);
  `bridge_state.json:6` (`total_mutations: 136`).

### 9. Macro
- **Rekomendasi**: Sambungkan `MacroRegimeDetector` ke `monitor/regime` agar sinyal macro masuk
  dashboard dan memengaruhi sizing (bukan detector mati #3).
- **file:line**: `engine/regime/ensemble.py:34-35` (kwargs dibuang, `predict` swallow TypeError);
  `dashboard/src/lib/api-client.ts:306` (`/api/monitor/regime`).

### 10. Portfolio
- **Rekomendasi**: Samakan `max_weight` risk-parity (0.50) dengan cap 10% di prompt agent (#6);
  baca equity lewat `portfolio/summary` bukan stub.
- **file:line**: `risk/risk_parity.py:93,139` (`max_weight=0.50`); `agents/portfolio/prompts.py:13`
  ("Max 10%"); `app.py:346` (`/api/portfolio`).

### 11. Quant Dev
- **Rekomendasi**: Hidupkan autonomous pipeline mati (`engine/autonomous/pipeline.py:113` SyntaxError)
  atau hapus; jangan biarkan `autonomous-loop.bat` hanya generate sinyal tanpa eksekusi (NC3).
- **file:line**: `engine/autonomous/pipeline.py:113` (`await broker.connect()` di sync method);
  `autonomous-loop.bat` (loop hanya `run_mtf_cycle`).

### 12. Blockchain
- **Rekomendasi**: Wire `GuardPipeline` ke `Solana place_order` (C4) dan pasang Jito bundle / MEV
  protection sebelum gene on-chain dijalankan.
- **file:line**: `exchange/guards.py:454` (0 impor luar); `exchange/solana/broker.py:290` (place_order
  tanpa guard); `jupiter.py:379-383` (`skip_preflight=True`, slippage 50).

### 13. Business Strategist
- **Rekomendasi**: Dokumentasikan batas "live vs paper" secara jujur ke user — C2 (MT5 fail-open)
  membuat user percaya live padahal paper. Tambahkan banner status di dashboard.
- **file:line**: `engine_production_bridge.py:385-389` (return `self._paper.place_order` sebelum
  `_mt5`); `dashboard/src/lib/store.ts:409` (`/api/trading/positions`).

### 14. Dhaher Specialist #1 (Swarm/Colony)
- **Rekomendasi**: Implementasi `reconcile()` di shared-state agar kill-switch antar-proses konsisten
  (fencing token + version row).
- **file:line**: `engine/hermes_shared_state.py:62`; `app.py:209` (`configure_kill_switch_file`).

### 15. Dhaher Specialist #2 (MUE-X Bridge)
- **Rekomendasi**: Baca `bridge_state.json` secara berkala (polling 60s) di `muex_bridge.py` dan
  daftarkan gene baru ke `StrategyRegistry` + catat ke `gene_registry.json` (single source).
- **file:line**: `E:/mue-x/bridge_state.json:2-6`; `strategy_registry.py:14`.

### 16. Dhaher Specialist #3 (Autonomous Loop)
- **Rekomendasi**: Ganti xcopy mentah `autonomous-loop.bat:43` dengan sync terverifikasi + register
  ke engine registry, bukan sekadar salin `.py` ke `engine/strategies/`.
- **file:line**: `autonomous-loop.bat:43` (`xcopy /E /I /Y ... strategies\*.py`);
  `quant_nanggroe/engine/strategies/`.

### 17. Dhaher Specialist #4 (Risk Gate)
- **Rekomendasi**: Feed mark-to-market equity ke `DrawdownMonitor` (bukan hanya realized PnL) agar
  kill-switch cut posisi terbuka (C2/#2).
- **file:line**: `engine/risk/manager.py:243` (`update_pnl` hanya di trade close);
  `KillSwitch.check_auto_activate`.

### 18. Dhaher Specialist #5 (Council/Debate)
- **Rekomendasi**: Cache hasil debate + kurangi 24 LLM call (reflection simpan vote) + baca
  `CostRecord` untuk cap harian (#11/#41).
- **file:line**: `agents/debate/graph.py:697,724` (dua `run_full_debate` 12 call);
  `llm_router.py:317` (CostRecord tak dibaca).

### 19. Dhaher Specialist #6 (UI/Dashboard wiring)
- **Rekomendasi**: Hapus `include_router` duplikat di `app.py:374-379` (stub menimpa route asli) dan
  pastikan Next.js dashboard di-build ke `quant_nanggroe/api/static` atau di-serve terpisah konsisten.
- **file:line**: `quant_nanggroe/api/app.py:374-379`; `app.py:434-436` (static mount).

### 20. Security
- **Rekomendasi**: Enkripsi `config/credentials.json` at-rest (fernet) — C3 masih terbuka.
- **file:line**: `api/routes/credentials.py:36` (`p.write_text(json.dumps(data))` cleartext);
  `KeyVault` ada tapi tak dipakai.

### 21. Risk / Compliance
- **Rekomendasi**: Aktifkan `StrategyCorrelationMonitor` (HERDING) sebagai input kill-switch — saat ini
  0 call-site (#10).
- **file:line**: `hermes_risk_officer.py:174` (grup hardcoded); `StrategyCorrelationMonitor` 0 impor.

### 22. Scheduler / Orchestration
- **Rekomendasi**: Jalankan council + MUE-X + loop dalam satu event-loop terorkestrasi lewat
  `coordinator`, bukan 3 proses terpisah tanpa lock (saat ini api/daemon/loop = 3 proses).
- **file:line**: `engine/scheduler.py:111`; `autonomous-loop.bat` (proses terpisah); `qna.py api`+`daemon`.

### 23. Council / Debate Coordinator
- **Rekomendasi**: Batasi konkurensi debate dengan `Semaphore` + tulis `council_log` pakai `filelock`
  agar 50 agent tidak tulis file sama berbarengan.
- **file:line**: `agents/debate/council_logger.py` (tulis tanpa lock);
  `agents/council/voting.py`.

### 24. Self-Evolution / Autonomy
- **Rekomendasi**: Sambungkan `qna_lessons.json` (MUE-X + autonomous) ke loop koreksi nyata
  (retry/replan), bukan hanya append + re-raise (#39 theater). Buat `swarm/self_evolve.py`.
- **file:line**: `engine_production_bridge.py:50,365` (catch → append → re-raise, 0 reader);
  `E:/mue-x/bridge_state.json` (`registered_signals` opportunity).

---

## 3. SELF-EVOLUTION — STATUS & NEXT STEP (ringkas)

| Item | Status | Bukti |
|------|--------|-------|
| MUE-X generate genes | ✅ jalan | `bridge_state.json:6` (136 mutations) |
| Genes dibaca QNA (legacy) | ✅ | `hedge_fund.py:332` (`sys.path.insert E:/mue-x/genes`) |
| Genes masuk QNA engine registry | ❌ | `engine/strategy/registry.py` grep mue-x = 0 hit |
| Genes lolos walk-forward/kill-switch | ❌ | wrapper `signal_qna_*` bypass `StrategyRegistry.register` |
| Auto-evolve → live QNA | ⚠️ | hanya via xcopy `autonomous-loop.bat:43`, tak terdaftar |

**Kesimpulan**: Bridge MUE-X → QNA **eksis tapi tidak lengkap**. Genes berevolusi di `E:/mue-x`
dan dikonsumsi monolit legacy `hedge_fund.py`, lalu di-xcopy ke QNA — namun **tidak pernah
didaftarkan ke `StrategyRegistry` engine QNA**, sehingga tidak mewarisi validasi, walk-forward,
atau kill-switch. Rekomendasi agent #7 + #15 + #16 menyambungkan ini lewat `swarm/muex_bridge.py`.

---

## 4. PRIORITY FIXES (urutan)

1. **C5 kill-switch split-brain** — `engine/hermes_shared_state.py:62` → `engine/swarm/coordinator.py`
   (single-writer SQLite WAL + filelock). *Safety, core.*
2. **Duplicate router** — `quant_nanggroe/api/app.py:374-379` hapus 3 baris duplikat. *1 menit.*
3. **CLI /api/v1** — `quant_nanggroe/cli.py:406` → `/api/portfolio`. *1 menit.*
4. **Dual-dashboard** — `autonomous-loop.bat:18` ganti stub `dashboard:app` → Next.js. *Wiring.*
5. **MUE-X → registry** — `swarm/muex_bridge.py` baca `bridge_state.json` → `registry.register`.
   *Self-evolution nyata.*
6. **Autonomous pipeline mati** — `engine/autonomous/pipeline.py:113` fix atau hapus (NC3).

---

*Dokumen ini ditulis oleh subagent desain swarm. Semua `file:line` diverifikasi terhadap worktree
`D:/repositories/Quant-Nanggroe-AI-worktree` pada sesi 2026-07-23. WAVE1/2/3 tidak ada di worktree
ini (hanya `archive/reports/WAVE2_AUDIT_REPORT.md` + `WAVE_COUNCIL_REPORT.md` yang dipakai sebagai
baseline).*
