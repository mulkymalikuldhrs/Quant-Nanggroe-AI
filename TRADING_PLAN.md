# 📋 DHAHER HEDGE FUND — TRADING PLAN
## Updated: 19 Juli 2026

---

## 1. 🎯 VISI
Hedge fund kuantitatif yang konsisten profit dengan Sharpe > 2.0, RR ≥ 1:3, dan drawdown < 25%.

---

## 2. 🏛️ STRATEGI UTAMA

| # | Strategi | Timeframe | Bobot | Status |
|---|----------|-----------|-------|--------|
| 1 | **Wyckoff Volume Spread** | M15→M5→M1 (Scalping) | 60% | ✅ LIVE (Sharpe 3.02) |
| 2 | **Mean Reversion Stochastic** | M15/H1 | 25% | ✅ LIVE (Sharpe 1.98) |
| 3 | **MSNR (Malaysian S&R)** | H1/M15 | 15% | ✅ Fix applied |
| 4 | **SMC (Smart Money)** | H4/H1 | — | ✅ Fix applied |
| 5 | **Algebra Z-Score** | M15 | — | ❌ Gate fail |
| 6 | **AMDX Market Profile** | D1/H4 | — | ❌ Gate fail |

---

## 3. ⏰ TRADING SESSIONS

| Style | HTF Chain | Entry TF | Hold Time | Risk |
|-------|-----------|----------|-----------|------|
| **Scalping** | M15→M5→M1 | M1 | 5-30 menit | 0.5-1% |
| **Intraday 1** | H4→H1→M15 | M15 | 2-8 jam | 1-2% |
| **Intraday 2** | H1→M15→M3 | M3 | 1-4 jam | 0.75-1.5% |
| **Swing 1** | W1→D1→H1 | H1 | 1-7 hari | 2-3% |
| **Swing 2** | D1→H4→M15 | M15 | 12-48 jam | 1.5-2.5% |

---

## 4. 📊 RISK MANAGEMENT

| Parameter | Value |
|-----------|-------|
| **Max risk per trade** | 2% dari balance |
| **Max positions** | 1 per pair, max 3 total |
| **Max daily loss** | 5% dari balance → STOP |
| **Leverage** | 1:2000 |
| **Base lot** | Balance / 10000 (min 0.01) |
| **Max lot** | Balance / 5000 |
| **SL** | ATR(14) × 2 pada M1 |
| **TP** | SL × 2 (RR 1:2 min, target 1:3) |
| **Trailing** | HH/LL break → SL ke entry |

### Position Sizing Formula
```
lot = max(0.01, balance / 10000) + (balance/5000 - balance/10000) * confidence
```

---

## 5. 🚦 GATE (Backtest → Walk-Forward → Demo → Real)

| Gate | Kriteria |
|------|----------|
| **Sharpe** | > 0.5 (target > 2.0) |
| **Return** | > 0% (walk-forward) |
| **Drawdown** | > -25% |
| **Win Rate** | > 30% |
| **Score** | Composite > 50 |

---

## 6. 📌 PAIR UNIVERSE

| Category | Pairs | Max Spread |
|----------|-------|------------|
| **Majors** | EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD | 25 pips |
| **Minors** | EURGBP, EURJPY, EURCHF, EURAUD, EURNZD, EURCAD, GBPJPY, GBPCHF, GBPAUD, GBPCAD, AUDJPY, AUDCHF, NZDJPY, NZDCHF | 35 pips |
| **Excluded** | XAUUSD, XAGUSD, BTCUSD, ETHUSD, TRYJPY, ZARJPY — SL jilat risk | — |

---

## 7. 📅 RUTINITAS

| Waktu | Aktivitas |
|-------|-----------|
| **Setiap 30min** | Hedge fund cron — scan + sinyal + eksekusi |
| **Setiap hari 21:00** | Accountability review — evaluasi harian |
| **Setiap hari** | Update journal — catat tiap trade |
| **Setiap Minggu** | Review mingguan — strategi performance |
| **Setiap Bulan** | Rebalancing — parameter optimization |

---

## 8. 🛑 PSIKOLOGI & DISIPLIN

1. **No revenge trading** — loss = stop, evaluasi, besok lagi
2. **Follow plan** — sinyal dari sistem, trading PLAN not trading MOOD
3. **Cut loss** — SL jangan dipindah manual
4. **Let profit run** — trailing SL biar TP maksimal
5. **Journal WAJIB** — setiap trade dicatat
