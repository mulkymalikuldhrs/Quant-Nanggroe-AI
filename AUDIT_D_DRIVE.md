# AUDIT D: DRIVE — Konsolidasi Konten Quant / HF / Trading ke QNA

**Tanggal audit:** 2026-07-23
**Scope:** Seluruh `D:\` (mount MSYS `/d/`), fokus trading/quant/hedge-fund.
**Metode:** `search_files` (grep/ripgrep) + `find` + `ls -la` via terminal bash.
**Catatan:** Tidak ada modifikasi kode QNA. Tidak butuh MT5/network.

---

## 1. Ringkasan

D: drive memuat ekosistem trading DhaHer Labs yang **sudah mayoritas terserap** ke QNA
(`/d/repositories/Quant-Nanggroe-AI-worktree`), hasil konsolidasi commit `48e8dcc` (2026-07-21/23).
Temuan terkelompok:

| Kategori | Jumlah | Lokasi utama |
|----------|--------|--------------|
| Pine Script (TradingView) | **10** | `/d/tv-indicators/*.pine` |
| Research markdown (HF/quant) | **12** | `Obsidian/.../_full_trading/trading/research/` |
| Python hedge-fund / backtest | **~25** | `Obsidian/.../_full_trading/trading/*.py` (sudah di QNA) |
| Obsidian notes (QNA + trading) | ~8 | `Obsidian/DhaherLabs/Quant-Nanggroe-AI/`, `_trading/` |
| QNA repo (sudah terkonsolidasi) | 1 | `/d/repositories/Quant-Nanggroe-AI-worktree/` |
| Mirror QNA (duplikat) | 1 | `/d/d/repositories/Quant-Nanggroe-AI-worktree/` |
| Config trading (JSON) | 2 | `_full_trading/trading/config/` |
| Data CSV (trades/votes) | 2 | `_full_trading/trading/data/` |

**Inti:** Aset D: yang **belum** ada di QNA = **10 Pine Script** (0 file `.pine` tracked di QNA)
+ 12 research-report markdown (ada di QNA tapi di folder `research/`, belum di `_full_trading` mirror
lokal — redundan). Seluruh Python strategi/backtest sudah ada di QNA (by name, beberapa 2–4 salinan).

---

## 2. Tabel Temuan

| Path (di D:) | Tipe | Size | Relevance ke QNA |
|---|---|---|---|
| `/d/tv-indicators/dhaher-squeeze-breakout.pine` | Pine v5 | 1580 B | **UNIK** — belum di QNA. Bollinger-squeeze + volume breakout. |
| `/d/tv-indicators/dhaher-smart-volume.pine` | Pine v5 | 1126 B | **UNIK** — volume spike + RSI filter, alert buy/sell. |
| `/d/tv-indicators/dhaher-mtf-confluence.pine` | Pine v5 | 1186 B | **UNIK** — multi-timeframe confluence. |
| `/d/tv-indicators/dhaher-bb-rating.pine` | Pine v5 | 598 B | **UNIK** — Bollinger Bands rating. |
| `/d/tv-indicators/dhaher-donchian-break.pine` | Pine v5 | 478 B | **UNIK** — Donchian breakout. |
| `/d/tv-indicators/dhaher-ema-cross.pine` | Pine v5 | 461 B | **UNIK** — EMA cross signal. |
| `/d/tv-indicators/dhaher-keltner-break.pine` | Pine v5 | 537 B | **UNIK** — Keltner channel breakout. |
| `/d/tv-indicators/dhaher-momentum-rank.pine` | Pine v5 | 461 B | **UNIK** — momentum ranking. |
| `/d/tv-indicators/dhaher-rsi-bands.pine` | Pine v5 | 626 B | **UNIK** — RSI bands. |
| `/d/tv-indicators/dhaher-supertrend-macd.pine` | Pine v5 | 624 B | **UNIK** — Supertrend + MACD. |
| `/d/Obsidian/DhaherLabs/_full_trading/trading/*.py` (25 file) | Python HF | ~200 KB | SUDAH di QNA (`hedge_fund.py`, `market_context.py`, `strategy_registry.py`, `sahamid.py`, dll). 0 file unik by name. |
| `/d/Obsidian/DhaherLabs/_full_trading/trading/strategy_registry.py` | Python | 14.8 KB | Plug&play registry strategi. SUDAH di QNA. |
| `/d/Obsidian/DhaherLabs/_full_trading/trading/sahamid.py` | Python | 19.7 KB | **Analisa Saham Indonesia** (SMC+fundamental+broker flow). SUDAH di QNA — aset bernilai tinggi untuk ekspansi IDX. |
| `/d/Obsidian/DhaherLabs/_full_trading/trading/strategy_fixes.py` | Python | 19.2 KB | Monkey-patch MSNR/SMC/QuarterlyTheory. SUDAH di QNA. |
| `/d/Obsidian/DhaherLabs/_full_trading/trading/research/*.md` (12) | Research | ~150 KB | Laporan repo quant/API/market-data. ADA di QNA (`research/`), redundan dg mirror. |
| `/d/Obsidian/DhaherLabs/_full_trading/trading/config/freqtrade.json` | JSON | 813 B | Config Freqtrade. Bisa jadi ref integrasi exchange. |
| `/d/Obsidian/DhaherLabs/_full_trading/trading/config/risk.json` | JSON | 171 B | Parameter risk. |
| `/d/Obsidian/DhaherLabs/_full_trading/trading/data/trades.csv` | CSV | 240 B | Sample trade log (demo). |
| `/d/Obsidian/DhaherLabs/_full_trading/trading/data/votes.csv` | CSV | 245 B | Sample voting log (council). |
| `/d/Obsidian/DhaherLabs/_trading/HedgeFund.md` | MD | 961 B | Deskripsi HF (engine `E:\trading\hedge_fund_mtf.py`, 28 pair, Valetax MT5 1:2000). |
| `/d/Obsidian/DhaherLabs/Quant-Nanggroe-AI/*.md` (7) | MD | — | Doc QNA (Architecture, Gap-Analysis, Production-Status, Risk). SUDAH di QNA. |
| `/d/DHAHER_LABS_FULL_COMPREHENSION.md` | MD | 1757 B | Ringkasan ekosistem DhaHer Labs. |
| `/d/repositories/Quant-Nanggroe-AI-worktree/` | Repo | — | **Repo QNA live** (HEAD `48e8dcc`). Sudah terkonsolidasi. |
| `/d/d/repositories/Quant-Nanggroe-AI-worktree/` | Repo (mirror) | — | **Duplikat** QNA (HEAD sama `48e8dcc`). `/d/d` = subdir asli `D:\d\` (bukan symlink). |
| `/d/d/repositories/ai-multicolony-ecosystem/` | Repo | — | Ekosistem multi-agent (bukan trading murni). Di luar scope QNA. |
| `/d/e/trading/` | Dir | 0 B | **Kosong** — hanya placeholder, tidak ada isi. |

---

## 3. Top 5 Prioritas Migrasi ke QNA

1. **10 Pine Script `/d/tv-indicators/*.pine`** — *Satu-satunya aset D: yang 100% belum ada di QNA.*
   Alasan: Indicator TradingView (squeeze, smart-volume, MTF-confluence, supertrend-MACD, dll)
   adalah sinyal front-end yang bisa dipetakan ke `quant_nanggroe/engine/strategies/` sebagai
   validator/alert. Simpan ke `quant_nanggroe/indicators/pine/` atau `dashboard/`.
2. **`sahamid.py` (Analisa Saham Indonesia)** — modul IDX (SMC + fundamental + broker flow +
   presiden/sebab-akibat). Alasan: QNA saat ini FX/metal-centric; ini pintu masuk ke ekuitas
   Indonesia. Sudah di QNA tapi perlu di-promote jadi strategi kelas-1, bukan sekadar file root.
3. **Research reports (12 md)** — `quant_strategy_repos_report`, `market-data-apis-report`,
   `finance-agent-frameworks-report`, dll. Alasan: intelijensi eksternal untuk roadmap QNA
   (data API, framework agent, repo quant). Pastikan di-`research/` QNA (sudah ada) — bersihkan
   duplikat di `_full_trading`.
4. **Config `freqtrade.json` + `risk.json`** — Alasan: QNA fokus MT5; Freqtrade membuka jalur
   crypto/exchange terpusat. Bisa jadi blueprint konektor kedua.
5. **`HedgeFund.md` + data CSV (trades/votes)** — Alasan: dokumentasi HF & sample trade/vote log
   berguna sebagai fixture test dan baseline performa (Sharpe Wyckoff 3.02, SMC 2.16, dll).

---

## 4. Duplikasi / Konflik dengan Strategi QNA yang Sudah Ada

QNA (`engine/strategies/`) SUDAH memuat: `wyckoff.py`, `smc_strategy.py`, `dhaher_system.py`,
`kronos_wrapper.py`, `tradebobby_smc_scanner.py`, + `smc_strategy_OLD.py`.

| Item D: | Status vs QNA | Catatan |
|---|---|---|
| `wyckoff` | Sudah ada (`engine/strategies/wyckoff.py`, 8.2 KB) | **Konflik nama** dgn `hedge_fund_mtf.py` yang pakai "Wyckoff Volume Spread" (Sharpe 3.022 di `HedgeFund.md`). Verifikasi parametrik sama. |
| `smc` | Sudah ada (`smc_strategy.py` + `smc_strategy_OLD.py`) | `strategy_fixes.py` di D: monkey-patch SMC broken → pastikan patch sudah masuk ke `engine/strategies/smc_strategy.py`. |
| `dhaher_system` | Sudah ada (root + `engine/strategies/dhaher_system.py` 16.4 KB) | 4 salinan by name — risiko drift. Konsolidasi ke 1 canonical. |
| `kronos` | Sudah ada (root + `engine/strategies/kronos_wrapper.py` 14.3 KB) | 4 salinan — konsolidasi. |
| `tradebobby_smc` | Sudah ada (root + `engine/strategies/tradebobby_smc_scanner.py` 22.3 KB) | 4 salinan — konsolidasi. |
| `market_context`, `multi_pair_scanner`, `risk_module` | Sudah ada (2 salinan masing2) | Fundamental/Macro + 37-pair scan + risk. Tidak unik. |
| Mirror `/d/d/repositories/...` | Duplikat penuh | HEAD identik `48e8dcc`. Bukan konflik, tapi redundant — rawat 1 sumber (`/d/repositories`). |
| `_full_trading/trading/*.py` | Redundan dg QNA | Semua 25 file ada by name di QNA. Folder ini sisa mirror `E:\trading` lama. |

**Konflik potensial:** (a) Multi-salinan `dhaher_system`/`kronos`/`tradebobby` (4×) → drift logika.
(b) `wyckoff` QNA vs "Wyckoff Volume Spread" di `HedgeFund.md` bisa beda implementasi.
(c) `strategy_fixes.py` (D:) patch MSNR/SMC/QuarterlyTheory — harus dipastikan sudah di-apply di
QNA agar tidak ada versi broken yang masih dipakai.

---

## 5. Rekomendasi Aksi (singkat)

1. **Copy** 10 Pine → `quant_nanggroe/indicators/pine/`, commit. (Prioritas tertinggi — aset unik).
2. **Dedup** salinan `dhaher_system`/`kronos`/`tradebobby` di QNA jadi 1 canonical per modul.
3. **Verify** `strategy_fixes.py` sudah ter-apply di `engine/strategies/` QNA.
4. **Hapus/arsip** mirror `/d/d/repositories` & `_full_trading` setelah yakin QNA lengkap (hindari drift).
5. **Promote** `sahamid.py` jadi modul strategi IDX resmi.

---
*Generated by subagent audit — D: drive scan. Tidak mengubah kode QNA.*
