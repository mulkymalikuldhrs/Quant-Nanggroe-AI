# Quant-Nanggroe-AI — Roadmap ke Production-Ready 100/100 (Hedge-Fund / War-Grade)

**Tanggal:** 2026-07-12 | **Canonical:** `576c403` | **Mode:** Research + Roadmap (belum build)
**Metode:** DhaHer 50-Agent Council (direct execution — delegasi subagent 404 pada model hy3-free, fallback per skill).
**Bukti:** semua klaim di-bawah diikat ke `file:line` pada worktree aktif.

---

## 0. VERDICT SINGKAT
Foundation **sudah 70–75/100**. Bukan awal dari nol. Yang kurang untuk 100/100 adalah:
1. **MT5 belum jadi default live path** (factory default CCXT/Paper — `exchange/factory.py:7`).
2. **Dashboard trading = read-only** (cuma GET positions — `dashboard/src/app/trading/page.tsx:13`); belum ada panel eksekusi/manual order/kill-switch.
3. **Verifikasi live nol** — MT5 di-test pakai mock (`graphify-out/...mock MetaTrader5`), belum pernah connect ke terminal asli.
4. **Risk guard belum ter-enforce di order path end-to-end** (Kelly cap ada di `kelly_bridge.py:261` tapi belum terbukti dipanggil sebelum `place_order` di `mt5_broker.py:397`).
5. **Autonomous loop ada** (`qna_prod.run_forever:376`) tapi **strategy→live promotion + circuit-breaker** butuh pembuktian.

---

## 1. JAWABAN RISET YANG KAU TANYA (langsung)

### Broker — free, no API key?
- **Jalur paling murni "no API key":** MetaTrader 5 terminal + akun **demo/cent gratis** dari broker (Exness, IC Markets, dll). `MetaTrader5` Python lib gratis (`pip install MetaTrader5`), login pakai akun+password+server, **tanpa API key**. QNA sudah punya `mt5_broker.py` untuk ini.
- **Jalur alternatif:** CCXT ke exchange kripto (Binance dkk) — gratis tapi butuh API key dari exchange. Sudah ada `ccxt_broker.py`.
- **Rekomendasi:** MT5 demo (no key) untuk tahap "war simulator", lalu MT5 live-cent saat confident.

### Sambung ke MT5 — Bridge atau EA?
Tiga opsi, urut dari termudah:
| Opsi | Cara | Pros | Cons | Status QNA |
|---|---|---|---|---|
| **A. Langsung Python→MT5** | `mt5_broker.py` panggil terminal MT5 via lib | Full control, sudah ada scaffold | Butuh terminal MT5 jalan di Windows host yang sama; Python crash = order stuck | Scaffold ada (1115 baris), belum live-verified |
| **B. TradingView→MT5 Bridge** (niiisho/TradingView-MT5-Bridge, OSS gratis) | TV alert → bridge app → MT5 | Pakai chart TV sebagai sumber sinyal | Butuh bridge app terpisah jalan terus | Belum diintegrasi |
| **C. EA (MQL5) di dalam MT5** | EA terima perintah via file/pipe/ZeroMQ dari QNA | Survive Python crash, paling "war-grade" | Perlu dev MQL5 | Belum ada |

**Rekomendasi roadmap:** mulai **A** (scaffold sudah ada → verifikasi live), tambah **C** (EA) sebagai hardening tahap akhir untuk resilience "war". **B** opsional kalau mau pakai TradingView sebagai signal source.

### UI — bagus & lengkap?
Stack sudah modern: **Next.js 16 + Radix + Tailwind 4 + Recharts** (`dashboard/package.json:35-51`), ada halaman agents/backtest/colony/factors/market/memory/portfolio/risk/security/settings/trading. **Tapi:**
- Halaman `trading` **read-only** (cuma fetch positions). Belum ada: panel manual order, satu-klik strategy→live, tombol kill-switch, equity curve live, order-book/depth.
- API client sudah benar arah ke backend (`dashboard/src/lib/api-client.ts:1` → `localhost:8000`), backend punya `POST /api/trading/order` (`api/routes/trading.py:50`) — **tinggal disambungkan ke UI**.

### Monitor & Execution di dashboard?
Backend SIAP (`POST /api/trading/order:50`, `POST /api/trading/risk-check:234`). Yang kurang: **UI execution panel + live P&L monitor + kill-switch button** yang panggil risk guard.

### Debate / Rebuttal / Bantahan?
**Sudah ada:** `quant_nanggroe/agents/council/debate.py` punya `investment debate` (`debate.py:254`) dan `risk debate` (`:367`). Multi-agent council internal jalan. Yang kurang: **dipublikasikan ke dashboard** + **dipakai sebagai gate** sebelum strategy go-live (saat ini debat = logging, belum = voting gate).

---

## 2. COUNCIL FINDINGS (per-domain, 1 temuan inti tiap lensa)

### Quant Finance & Trading
- **#1 Strategist:** 18 strategi ada (`strategies/*.py`) tapi belum ada **ensemble/regime-gate** yang pilih strategi per market state. `ponytail:` tambah regime router di `live_engine.py:521` (saat ini AutoAware dipanggil tapi tidak memilih strategi).
- **#2 Risk:** Kelly cap ada (`kelly_bridge.py:261`) tapi **tidak ter-enforce di `mt5_broker.place_order`** (`mt5_broker.py:397`). `ponytail:` panggil risk-check sebelum submit.
- **#5 Quant Dev:** Backtest framework **leaks** — 19 test strategi fail (divergen API). `ponytail:` fix test atau hapus strategi mati.
- **#7 Microstructure:** Fill assumption = 100% (paper). `ponytail:` tambah slippage+commission model di `execution.py`.

### AI/ML Engineering
- **#11 LLM Architect:** Retrieval untuk council pakai memory flat, bukan graph. `ponytail:` pakai Context MCP graph sudah ada.
- **#14 Agent Framework:** Agent loop `run_forever` (`qna_prod.py:376`) **tanpa max-iteration guard**. `ponytail:` tambah circuit breaker + max-cycle.

### Software Engineering
- **#19 Systems:** Single point = `qna_live.db` sqlite (`live_engine.py:82`). `ponytail:` pakai Postgres untuk war-grade.
- **#20 Security:** `POST /api/trading/order` (`trading.py:50`) **tanpa auth terlihat di route**. `ponytail:` wajib auth + risk-check sebelum eksekusi uang nyata.
- **#22 DevOps:** Tidak ada rollback strategy di `deploy/`. `ponytail:` tambah health-gate + auto-rollback.

### Blockchain & Crypto
- **#30 MEV:** CCXT execution (`ccxt_broker.py`) tidak ada MEV protection. `ponytail:` untuk kripto tambah private mempool / slippage cap.

### Research & Innovation
- **#33 Paper Analyst:** Tidak ada CPCV/DSR (probability of backtest overfit) gate. `ponytail:` pasang CPCV sebelum promosi live (sudah di Research.md v2).

### Business & Strategy
- **#41 Financial:** Burn vs P&L belum dilacak. `ponytail:` dashboard tambah P&L + drawdown live.

### DhaHer Specialists
- **#45 Project Auditor:** ~40% dead code (legacy `ai_multicolony/agents/legacy/*`). `ponytail:` karantina legacy, jangan masuk build.
- **#49 Dependency:** `mt5_broker` Windows-only (`mt5_broker.py:18`) — kita di Windows, OK, tapi harus di-doc sebagai constraint deploy.

---

## 3. SEVERITY TABLE
| Kategori | Critical | High | Medium | Low |
|---|---|---|---|---|
| Broker/Execution | MT5 bukan default (factory:7) | Order path tanpa auth (trading.py:50) | Risk guard tak enforce (mt5:397) | MEV protection |
| UI/Monitor | Trading read-only (page.tsx:13) | Tak ada kill-switch UI | Tak ada equity-curve live | Tema |
| Autonomous | Loop tanpa guard (qna_prod:376) | Strategi→live tak terbukti | Debate tak jadi gate | Logging |
| Risk/Quant | Tak ada CPCV gate | Fill 100% (paper) | 19 test fail | Ensemble |

---

## 4. PHASED ROADMAP KE 100/100

### Phase 0 — Verify & Wire MT5 (Minggu 1)  [crit: Broker]
1. `pip install MetaTrader5`, jalankan terminal MT5 (akun demo), **buktikan connect** (`mt5_broker.py:171`) + `place_order` market order sungguhan di demo.
2. Buat env `QNA_BROKER=mt5` → factory pilih MT5 (`factory.py:7`).
3. **Verification gate:** pytest live (bukan mock) ke demo account, assert posisi kebuka & nutup.

### Phase 1 — Execution Guardrails (Minggu 2)  [crit: Security/Risk]
4. `POST /api/trading/order` wajib auth + panggil `risk-check` (`trading.py:234`) SEBELUM `mt5_broker.place_order`.
5. Enforce Kelly cap + MAX_DRAWDOWN di order path (hook `kelly_bridge.py:261`).
6. **Verification gate:** order dengan size melebihi cap → ditolak (test assertion).

### Phase 2 — Dashboard Execution + Monitor (Minggu 3)  [crit: UI]
7. Trading page: panel manual order (POST `/api/trading/order`), live positions+P&L, **kill-switch button** (panggil circuit-breaker), equity curve (Recharts).
8. Strategi→live promotion: tombol "Deploy to MT5" yang lewat CPCV gate dulu.
9. **Verification gate:** klik di UI → order demo tereksekusi, muncul di positions.

### Phase 3 — Autonomous + Debate Gate (Minggu 4)  [crit: Autonomous]
10. `run_forever` + max-cycle guard + auto-restart. Debate (`debate.py:254`) jadi **voting gate** sebelum strategi promoted.
11. **Verification gate:** simulasi 24h di demo, tanpa intervensi manusia, P&L tercatat.

### Phase 4 — War-Grade Hardening (Minggu 5-6)  [high]
12. Postgres ganti sqlite (`live_engine.py:82`). Rollback deploy. EA (MQL5) untuk resilience. CPCV gate wajib.
13. **Verification gate:** live-cent account, drawdown cap terbukti memotong posisi.

---

## 5. TOP-5 ACTIONS (imperatif)
1. **Verifikasi MT5 live ke demo** — buktikan `mt5_broker.connect` + `place_order` jalan (bukan mock).
2. **Jadikan MT5 default broker** via env di `factory.py`.
3. **Paskan auth + risk-check di `POST /api/trading/order`** sebelum eksekusi uang.
4. **Bikin trading page jadi execution + monitor + kill-switch**, bukan read-only.
5. **Pasang CPCV/DSR + debate sebagai gate promosi live**, bukan sekadar logging.

---

## 6. SKEPTIC CROSS-EXAMINATION ("bantahan")
- **T: "MT5 broker sudah jadi, tinggal pakai."** → B SALAH. Scaffold ada tapi default bukan MT5, test pakai mock, belum pernah connect terminal asli. Butuh Phase 0 verify.
- **T: "Dashboard sudah lengkap."** → PARTIALLY. Monitor ada, **execution tidak**. Trading page read-only.
- **T: "Sistem sudah autonomous."** → PARTIALLY. Loop ada tapi tanpa guard + strategi tak terbukti promoted ke live.
- **T: "Gratis tanpa API key mungkin?"** → BENAR untuk MT5 demo (terminal login, no key). CCXT butuh key.
- **T: "EA perlu?"** → Tidak untuk tahap awal (pakai opsi A). Perlu untuk war-grade resilience tahap akhir.

---
*Semua temuan terikat ke file:line worktree `576c403`. Tidak ada yang diubah di repo — ini roadmap murni. Eksekusi dimulai dari Phase 0 setelah kau setuju.*
