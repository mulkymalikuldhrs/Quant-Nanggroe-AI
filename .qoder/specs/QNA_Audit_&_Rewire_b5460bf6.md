# QNA Audit & Rewire — Autonomous Quant Hedge Fund

## Ringkasan & Vonis Jujur (Debat Ya/Tidak)

**Apakah ini Autonomous Quant Hedge Fund? Vonis: ~85% infrastruktur nyata, ~15% simulasi/kabel putus.**

- **YA (nyata):** Risk gate konstitusional + kill switch C5 fail-closed benar-benar di-enforce di hot path (`pipeline/execution.py:119-142`); engine kausal (DCC-GARCH, COT, MSI, SMT) real dan ter-wire; agregator hedge fund voting multi-provider real; eksekusi MT5 live via `mt5.order_send()` benar-benar ada (`hedge_fund/execution/orders.py:151`); bug sinkronisasi MT5 di `live_engine.py:705` sudah diperbaiki (pakai `get_mt5_connector()`).
- **TIDAK (putus/palsu):** Registry 79+ strategi **mati total di unified pipeline** karena mismatch interface (`signal.py:167` memanggil `run_strategies()` yang tidak ada di `ProductionStrategyRunner`); hanya 4 strategi di-hardcode dari 79 tersedia (`engine_production_bridge.py:101-106`); `run_once()` menandai `executed=True` walau order gagal/return None (`portfolio/main.py:321-324`); `execute()` malah raise RuntimeError di paper mode tanpa ditangkap; OHLCV palsu disintesis dari harga close (`signal.py:143-157`); balance fallback hardcoded 10000.0 (`execution.py:128`).

Kesimpulan: **bisa dijadikan hedge fund otonom sungguhan** — kabelnya yang harus disambung, bukan arsitekturnya yang harus dirombak.

## Fase 1 — Inventaris & Audit (deliverable dokumen)

Buat satu dokumen audit `docs/QNA_AUDIT_INVENTORY_v6.2.md` berisi:
- Daftar file per ekstensi (exclude `node_modules/`, `.venv/`, `__pycache__/`, build artifacts): ~400 .py sumber, ~100 .ts/.tsx dashboard, ~75 .md docs, ~30 config.
- Daftar orphan terverifikasi: `quant_nanggroe/cli.py`, root `qna-cli.py`, `qna_daemon.py`, `qna-paper-daemon.py`, `bh-cli.py`, `qna-production-runner.py`, `_diag_imports.py`, `_probe_strategy_count.py`, `web_interface/`, `FILE_LISTING.md`, `WAR_PLAN.md`, `DESIGN.md`, `Riset_QNA.md`, `AO_QNA_PROFILE_ACTIVITY_2026-07-25.md`.
- Daftar semua *.md yang harus diperbarui (lihat Fase 6) + yang diarsipkan.
- Tabel mock/stub dengan file:line dan status perbaikan.

## Fase 2 — P0: Sambungkan Registry Strategi ke Pipeline (inti permintaan "satukan semua strategy")

1. **Fix interface mismatch** — `quant_nanggroe/pipeline/signal.py:159-207`: ganti pemanggilan `runner.run_strategies(symbol, price)` (tidak ada) dengan `runner.generate_signals(market_data, prices)` memakai OHLCV candles nyata dari `UnifiedDataProvider` (bukan dict tunggal). Hapus fallback `strat.predict(symbol, data)` yang salah signature.
2. **Muat semua strategi lolos walk-forward** — `quant_nanggroe/engine_production_bridge.py:97-118`: ganti daftar hardcode 4 strategi dengan loop `list_strategies()` yang difilter oleh: (a) hasil `WalkForwardAnalyzer`/gate backtest, (b) `StrategyLifecycleManager.get_active_strategies()` (exclude KILLED). Lazy-load agar cold start tetap cepat; log jumlah `active/available`.
3. **Hapus sintesis OHLCV palsu** — `signal.py:143-157` (`_ohlcv_data`): jika OHLCV tidak lengkap, return None dan skip strategi (fail-closed), jangan memalsukan candle. Audit pemanggil di `orchestrator.py`.

## Fase 3 — P0: Kejujuran Status Eksekusi

4. **`hedge_fund/portfolio/main.py:320-324`**: tangkap return `execute()`; jika None/exception → `status="order_failed"`, `executed=False`. Bungkus dengan try/except agar RuntimeError paper-mode tidak meledakkan `run_once()` — kembalikan status eksplisit `"paper_blocked"`.
5. **`pipeline/execution.py`**: tambah key `"executed": True/False` eksplisit di SEMUA return path (mt5-live, paper, engine, rejected, no_backend). Ganti balance fallback `10000.0` (line 127-128) dengan perilaku fail-closed ketika `allow_live=True` (reject jika balance broker tidak terbaca); untuk paper mode boleh default eksplisit dengan log WARNING.
6. **`engine_production_bridge.py`**: (a) `_record_lesson()` (~line 54-69) log warning sebelum swallow exception; (b) `SyncPaperBroker` (~line 262-327) pakai satu event loop persisten class-level, bukan loop baru tiap call; (c) `RegimeAwareExecution._fallback_detect()` beri docstring "fallback-only, produksi pakai HMM".
7. **Guard reentrancy** — `pipeline/orchestrator.py:126-163`: tambah cek `asyncio.get_running_loop()` dan raise error jelas jika `run()` dipanggil dari konteks async. JANGAN mengubah logika mode-routing (larangan AGENTS.MD).

## Fase 4 — Wiring UI/Dashboard

8. Audit endpoint yang dikonsumsi 19 halaman `dashboard/src/app/` vs rute nyata di `quant_nanggroe/api/`: implementasikan handler nyata untuk endpoint yang saat ini stub/kosong (mis. orders → baca dari journal/MT5/paper state, backtest-results → baca hasil `WalkForwardAnalyzer`/gate cache). **Jangan mengubah envelope respons atau path endpoint yang ada** (larangan AGENTS.MD) — hanya isi handler kosong.
9. Verifikasi `dashboard.html` dan Next.js dashboard menampilkan data hidup dari API (bukan dump statis) via Browser agent: start `python qna.py api`, cek halaman strategies/risk/pipeline menampilkan 79+ strategi dan status kill switch nyata.

## Fase 5 — Bersih-bersih Orphan (arsip, bukan hapus)

10. Setelah grep konfirmasi tidak direferensikan runtime/CI: pindahkan orphan entry points & script debug (daftar Fase 1) ke `archive/` + catat di CHANGELOG. `qna.py` tetap satu-satunya entry point. Jangan sentuh `engine/strategy/strategies/` shim (kompat mundur yang disengaja) dan `DEFAULT_AGENTS` di qna.py.

## Fase 6 — Sinkronisasi Dokumentasi (satu commit dengan kode terkait)

11. Update: `docs/02_ARCHITECTURE.md` (jumlah strategi 79+, wiring pipeline baru), `docs/10_ROADMAP.md` (versi), `docs/20_RELEASE_PLAN.md` (rilis ini), `README.md` (status live wiring), `AGENTS.md` (fakta baru bila berubah), merge/arsip duplikat `docs/QNA_DEEP_AUDIT_2026-07-26.md` + `docs/QNA_MASTER_GAP.md`, arsip `docs/12_TASKS.md` jika duplikat TODO.md. Tambah entri ADR di `docs/11_DECISIONS.md` untuk keputusan "registry-to-pipeline unification".

## Rencana Test & Verifikasi

- Test baru: `tests/pipeline/test_signal_runner_wiring.py` (registry→pipeline, semua strategi aktif termuat), `tests/pipeline/test_execution_status.py` (`executed` flag di semua path, fail-closed balance), `tests/hedge_fund/test_run_once_status.py` (order gagal ≠ "executed"; paper mode tidak crash), `tests/pipeline/test_no_fake_ohlcv.py`.
- Jalankan: `PYTHONPATH="" uv run python -m pytest tests/ -v --tb=short`, `ruff check .`, `mypy quant_nanggroe/`.
- Browser E2E: dashboard menampilkan data live (Fase 4 langkah 9).
- Ultra Review: 3 CodeReview paralel (completeness / correctness / impact) setelah Verify lulus.

## Dependensi

- Fase 2 → Fase 3 (execution honesty menguji hasil sinyal nyata) → Verify → Fase 4 (UI butuh API benar) → Browser E2E.
- Fase 1 (dokumen inventaris) dan Fase 5 (arsip orphan) independen, boleh paralel.
- Fase 6 (docs) terakhir, setelah semua fakta kode final.

## Risiko & Mitigasi

- Memuat 79 strategi memperlambat cold start → lazy-load + filter lifecycle; ukur waktu start.
- Menolak OHLCV palsu bisa mengurangi jumlah sinyal → itu memang tujuan (fail-closed); pantau via log.
- Perubahan `executed` flag bisa memengaruhi konsumen hasil dict → hanya menambah key, tidak mengubah key lama.
- Arsip orphan bisa memutus cron/script eksternal → grep referensi + arsip (bukan delete), reversible.
- Larangan AGENTS.MD dijaga ketat: tidak menyentuh logika risk engine, mode-routing orchestrator, format state file, API envelope, DEFAULT_AGENTS.

## Alternatif Ditolak

- **Rewrite async penuh pipeline (usulan perspektif performa):** ditolak untuk rilis ini — risiko regresi tinggi, melanggar prinsip perubahan minimal; cukup guard reentrancy. Streaming WebSocket & health scorer provider dicatat sebagai backlog fase berikutnya.
- **Hapus jalur agentic:** ditolak — masih dipakai sebagai fallback sah di `signal.py:209`; mengarsipkannya mengubah perilaku pipeline.
- **Hapus file orphan permanen:** ditolak — arsip reversible lebih aman.

---


---

> **SSOT:** `CANONICAL.md` v8.1.2 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, vector 6 modul live, risk per-symbol
