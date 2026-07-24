# Quant Nanggroe AI — Institutional Master TODO & Roadmap

Dokumen ini adalah **peta jalan resmi (Master TODO)** pengembangan platform **Quant-Nanggroe-AI** menuju sistem **Autonomous Quantitative Hedge Fund Institusional (v5.0.0)**.

---

## 🎯 Status Rilis Saat Ini: `v5.0.0 — 100/100 Institutional Quant OS`

```
[ Data Layer ]          ██████████ 100% (OHLCV, CCXT, MT5, Order Book Imbalance Ratio)
[ Strategy Engine ]     ██████████ 100% (219+ Strategi Terhubung via AutoRegistry)
[ Risk Engine ]         ██████████ 100% (3-Layer Guard, Kill Switch, Covariance Risk Parity)
[ Execution Layer ]     ██████████ 100% (Paper Broker, TWAP/VWAP Slicer, Smart Router)
[ API & Frontend UI ]   ██████████ 100% (FastAPI & Next.js React Dashboard v5.0.0 + Live UI Config)
```

---

## 📋 Prioritas Tugas Terjadwal (Institutional Roadmap)

### Phase 1: Core Engine Consolidation (✅ Completed in v4.9.0 & v5.0.0)
- [x] **Unifikasi Peluncur Utama**: `qna.py` sebagai Single Entry Point tunggal.
- [x] **Unifikasi Strategi**: Seluruh 219+ strategi disatukan di bawah `quant_nanggroe/engine/strategy/strategies/`.
- [x] **Unifikasi Data Provider**: Seluruh provider disatukan di bawah `quant_nanggroe/data/providers/`.
- [x] **AutoRegistry Integration**: Registrasi otomatis 219+ strategi tanpa manual import.
- [x] **Pembersihan Dead Code**: Mengarsipkan modul `jeumpa/` ke `archive/jeumpa/`.
- [x] **Single UI Consolidation**: Mengarsipkan `qnai_dashboard.html` ke `archive/legacy-ui/`, Next.js React UI (`dashboard/`) sebagai UI tunggal.
- [x] **Dynamic UI Config**: Endpoint `/api/config` & `/api/credentials` untuk pengeditan konfigurasi langsung dari UI.

### Phase 2: Institutional Execution & Risk Upgrades (✅ Completed in v4.9.0)
- [x] **TWAP & VWAP Order Slicing**: Modul `quant_nanggroe/engine/execution/algo_execution.py` untuk pemotongan order besar.
- [x] **Matriks Kovariansi Multi-Aset**: Modul `quant_nanggroe/engine/portfolio/covariance_risk.py` untuk penyeimbang risiko portofolio (Risk Parity).
- [x] **Order Book Imbalance Ratio**: Perhitungan mikrostruktur pasar pada `data_manager.py`.

### Phase 3: Live Broker & Alternative Data Expansion (🚀 In Progress)
- [ ] **Real-time CFTC COT Integration**: Menghubungkan provider COT langsung ke feed API mentah CFTC.
- [ ] **Automated MT5 Reconnection**: Auto-reconnect daemon untuk MetaTrader 5 terminal.
- [ ] **L2/L3 Tick Stream Handler**: Penanganan streaming tick realtime dengan latensi sub-detik via WebSocket.

### Phase 4: AI & Deep Learning Ensemble
- [ ] **Online Reinforcement Learning Fine-tuning**: Integrasi model PPO/SAC ke loop eksekusi `AutonomousPipeline`.
- [ ] **NLP Sentiment Processing**: Parsing otomatis SEC 10-K/10-Q filings dan FRED macro metrics via LLM.

---

## 📌 Aturan Pengoperasian
1. **Single Entry Point**: Gunakan `python qna.py status` atau `python qna.py api` untuk peluncuran.
2. **Fail-Closed Safety**: Jangan pernah mematikan Risk Guard atau Kill Switch di lingkungan produksi.
3. **Evidence-Based**: Semua strategi wajib divalidasi dengan backtest sebelum eksekusi live.
