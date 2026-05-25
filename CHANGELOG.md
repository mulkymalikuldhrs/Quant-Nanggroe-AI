# CHANGELOG - QUANT NANGGROE AI

## [v15.3.0] - 2026-03-05

### Fixed
- Replaced mock chart data with empty fallback in `market.ts` — no more fake OHLCV when APIs unavailable
- Replaced random mock flow/whale data with neutral state in `market.ts`
- Updated `.gitignore` to cover `.env.local`, sensitive files, and `cred`
- Removed `.env.local` and empty `cred` file from version control
- Fixed broken contact links in README
- Updated README with consolidated trilingual disclaimer (EN/ID/CN)
- Added contributor welcome section with specific roles

---

## [v15.2.0] - Previous Release
### Added
- **Contextual Neural Grounding**: Implementasi pemanenan data real-time sebelum penalaran agent untuk eliminasi halusinasi.
- **Latency & Performance Tracking**: Pelacakan timing presisi tinggi pada siklus Neural Swarm untuk kebutuhan audit institusional.
- **Institutional UI Flair**: Peningkatan `ControlCenter` dengan "Security Matrix" dan dashboard kesehatan "Risk Guardian".
- **Neural Inferences Grounding**: Pelabelan eksplisit pada sintesis swarm sebagai `NEURAL_INFERENCE` dengan trust score.

### Changed
- **Institutional Logic (v15.1.0)**: Upgrade kernel prompt untuk mewajibkan penalaran deterministik dan bukti kuantitatif.
- **Stability Patch**: Sinkronisasi konsistensi data (`currentPrice` & `priceChange24h`) di seluruh ekosistem Market & Portfolio.

---

## [v15.0.0] - 2026-01-06 (FINAL MVP: OPERATIONAL READINESS)
### Added
- **Risk Guardian (Constitutional Law)**: Implementasi layer penegakan risiko deterministik (Kill-switch 4% DD & Correlation Monitor).
- **Execution Reality Engine**: Integrasi simulasi trading realistis (Dynamic Spread, Slippage, Latency 100-500ms).
- **Strategy Lifecycle Manager**: Darwinian management yang membunuh strategi non-performan secara otomatis.
- **Audit Traceability**: Integrasi `AuditLogger` di seluruh layer (Market -> Sensor -> Pressure -> Decision -> Risk).

### Completed
- **Full MVP Lifecycle**: Penyelesaian seluruh rencana pembangunan 6 minggu sesuai `BUILD_PLAN.md`.

---

## [v12.0.0] - 2026-01-06 (PROFESSIONAL TRADING EDITION)
### Added
- **Institutional Logic (SMC)**: Implementasi Order Blocks, FVG, dan Market Structure Breaks.
- **Trading Terminal Portfolio**: Redesain Portfolio Management menjadi gaya terminal profesional (Equity, Margin, PnL real-time).
- **Institutional Data Pipeline**: Pipeline proxy-rotator untuk Binance dan sumber institusional.

---
*(Versi sebelumnya tetap tersedia di riwayat audit sistem)*

---

> **Contact:** Mulky Malikul Dhaher — [mulkymalikuldhaher@email.com](mailto:mulkymalikuldhaher@email.com)
>
> **Disclaimer:** This project is for Education Purpose only. Risiko apapun tidak kita tanggung. (We are not responsible for any risks or damages.)
