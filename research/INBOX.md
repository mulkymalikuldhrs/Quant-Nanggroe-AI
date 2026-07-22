# QNA Research Inbox — Bridge dari Researchbot

Sumber: `E:/trading/research/PRIORITY.md` (RESEARCHBOT Cycle 1, 2026-07-19)
Status: Temuan HIGH-IMPACT yang BELUM di-clone/integrasikan ke QNA.
Tujuan: Tiap entry = 1 kandidat masuk ke StrategyRegistry / pipeline QNA.
Catatan: PRIORITY.md mengoreksi klaim clone lama — item di bawah BELUM terverifikasi ada di disk QNA. Verifikasi keberadaan sebelum eksekusi action item.

---

### 1. [TA-Lib (Python)](https://github.com/mrjbq7/ta-lib)
**Relevansi ke StrategyRegistry:** 150+ indikator industri (RSI, MACD, ATR, BBANDS, dll). Semua strategi SMC/Wyckoff/MeanRev butuh indikator ini sebagai sinyal primitif.
**Action item:** Bungkus TA-Lib sebagai modul indikator reusable di `quant_nanggroe/engine/strategy/strategies/indicators_talib.py`; konsumsi via StrategyRegistry agar tiap strategi panggil 1 fungsi, bukan reimplementasi.

### 2. [pandas-ta](https://github.com/twopirllc/pandas-ta)
**Relevansi ke StrategyRegistry:** 130+ indikator + 60 pola candlestick, pandas-native. Melengkapi TA-Lib untuk sinyal yang butuh dataframe (FVG, order-block helpers).
**Action item:** Tambah `indicators_pandasta.py` di `quant_nanggroe/engine/strategy/strategies/`; jadikan fallback bila TA-Lib binary gagal terinstall di Windows.

### 3. [Alphalens-reloaded](https://github.com/stefan-jansen/alphalens-reloaded)
**Relevansi ke StrategyRegistry:** Analisis performa faktor (Sharpe > 2, IC, turnover). Untuk strategi berbasis faktor/alpha sebelum naik ke registry.
**Action item:** Buat gate faktor di pipeline walk-forward: strategi faktor harus lulus alphalens (IC>0, factor-Sharpe>1) sebelum masuk `ALL_PROVIDERS` di `hedge_fund.py`.

### 4. [NoFxAiOS / nofx](https://github.com/NoFxAiOS/nofx)
**Relevansi ke StrategyRegistry:** AI Trading OS — multi-AI debate arena + self-evolution. Mirip pola `quant_nanggroe/engine/agentic/adapters.py` yang sudah ada (sedang dimodifikasi). Bisa jadi sumber debat antar-strategi kandidat.
**Action item:** Extend `quant_nanggroe/engine/agentic/adapters.py` dengan loop debate + self-evolution: tiap kandidat strategi diuji argumen pro/contra antar-model sebelum promosi registry.

### 5. [Riskfolio-Lib](https://github.com/dcajasn/Riskfolio-Lib)
**Relevansi ke StrategyRegistry:** 26 risk measures untuk alokasi bobot antar strategi di portfolio layer (bukan strategi individu).
**Action item:** Tambah layer optimasi portfolio di `quant_nanggroe/hedge_fund/` yang mengalokasikan bobot ke strategi terdaftar pakai risk-parity / mean-CVaR.

### 6. [skfolio](https://github.com/skfolio/skfolio)
**Relevansi ke StrategyRegistry:** scikit-learn API portfolio — kompatibel dengan pipeline ML QNA untuk weight optimization.
**Action item:** Sandingkan dengan Riskfolio-Lib sebagai validator kedua untuk alokasi bobot; bandingkan hasil sebelum pilih satu.

### 7. [VectorBT](https://github.com/polakowo/vectorbt)
**Relevansi ke StrategyRegistry:** Backtesting tercepat (Numba). Validator silang untuk walk-forward registry.
**Action item:** Pasang sebagai secondary backtest engine; cross-check OOS Sharpe/Drawdown tiap strategi registry vs engine internal (`backtest_pipeline.py`).

### 8. [nautilus_trader](https://github.com/nautechsystems/nautilus_trader)
**Relevansi ke StrategyRegistry:** Rust-native, backtest deterministik = live. Untuk audit kecocokan live vs backtest.
**Action item:** Evaluasi sebagai execution/backtest engine pengganti/parallel; verifikasi determinasi sinyal registry sebelum eksekusi real.

### 9. [zipline-reloaded](https://github.com/stefan-jansen/zipline-reloaded)
**Relevansi ke StrategyRegistry:** Factor research backtesting — cocok untuk strategi berbasis faktor di registry.
**Action item:** Gunakan untuk backtest cepat strategi faktor sebelum masuk gate alphalens.

### 10. [bt](https://github.com/pmorissette/bt) & [ffn](https://github.com/pmorissette/ffn)
**Relevansi ke StrategyRegistry:** Portfolio backtesting + financial metrics. Pengganti/pendamping `ffn` internal untuk laporan performa strategi.
**Action item:** Tambah helper metrik di `quant_nanggroe/hedge_fund/` untuk report harian performa tiap strategi terdaftar.

### 11. [QuantLib](https://github.com/QuantLib/quantlib)
**Relevansi ke StrategyRegistry:** Standard industri derivatives pricing — untuk strategi opsi/derivatif di registry.
**Action item:** Jika registry akan punya strategi opsi, integrasi QuantLib-SWIG untuk pricing IV/Greeks.

### 12. [py_vollib](https://github.com/vollib/py_vollib) & [optopsy](https://github.com/michaelcho/optopsy)
**Relevansi ke StrategyRegistry:** Options pricing IV/Greeks + options backtesting. Pendukung #11 untuk strategi derivatif.
**Action item:** Siapkan modul opsi di `quant_nanggroe/engine/strategy/strategies/options/` bila ada strategi opsi masuk registry.

### 13. [mplfinance](https://github.com/matplotlib/mplfinance)
**Relevansi ke StrategyRegistry:** Visualisasi candlestick wajib untuk chart sinyal strategi (debug + laporan).
**Action item:** Tambah util plot di `dashboard/` QNA untuk render sinyal entry/SL/TP per strategi registry.

### 14. [exchange_calendars](https://github.com/generalprogramming/exchange_calendars)
**Relevansi ke StrategyRegistry:** Akurasi sesi trading di backtest — cegah look-ahead bias antar sesi.
**Action item:** Pasang di `backtest_pipeline.py` agar walk-forward pakai sesi riil (bukan 24/7 buatan).

### 15. [OpenBB](https://github.com/OpenBB-finance/OpenBB)
**Relevansi ke StrategyRegistry:** Bloomberg Terminal OS — data backbone tunggal. Gantikan provider tersebar di `market_context.py` (DXY, yield, COT, FX).
**Action item:** Integrasi OpenBB sebagai sumber data unified; refactor `market_context.py` untuk baca dari satu interface OpenBB.

---
## Prioritas Eksekusi (berdasarkan PRIORITY.md Tier 1)
1. 🔴 Data backbone: OpenBB, TA-Lib, pandas-ta (hari 1)
2. 🔴 Factor: Alphalens-reloaded (hari 2)
3. 🔴 AI OS: nofx (hari 3)
4. 🟢 Portfolio/Engine: Riskfolio-Lib, skfolio, VectorBT, nautilus_trader (hari 4-5)
5. 🟢 Support: mplfinance, zipline-reloaded, bt, ffn, py_vollib, optopsy, exchange_calendars (hari 6-7)

Dibuat otomatis oleh cron `qna-bridge-research` — 2026-07-23.
