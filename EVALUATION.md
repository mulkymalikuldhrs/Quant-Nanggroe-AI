# 📊 DHAHER HEDGE FUND — PERFORMANCE EVALUATION
## Weekly / Monthly Review

---

## Metrics Summary

| Metric | This Week | This Month | All Time | Target |
|--------|-----------|------------|----------|--------|
| **Total Trades** | 0 (2 rejected) | 0 | 0 | — |
| **Win Rate** | — | — | — | > 60% |
| **Sharpe Ratio** | — | — | — | > 2.0 |
| **Total PnL** | $0.00 | — | — | — |
| **Avg RR** | — | — | — | ≥ 1:3 |
| **Max Drawdown** | 0.00% | — | — | < 25% |
| **Balance** | $1,000.00 | $1,000.00 | $1,000.00 | — |

---

## Strategy Performance

| Strategy | Trades | Win Rate | Avg RR | Sharpe | PnL | Status |
|----------|--------|----------|--------|--------|-----|--------|
| Wyckoff | 0 | — | — | 3.02 (BT) | — | 🟢 Live |
| MeanRev | 0 | — | — | 1.98 (BT) | — | 🟢 Live |
| MSNR | 0 | — | — | 1.89 (BT) | — | 🟢 Fixed |
| SMC | 0 | — | — | 2.16 (BT) | — | 🟢 Fixed |

---

## Monthly Review Format

### ✅ What Worked
- 

### ❌ What Didn't
- 

### 💡 Lessons
- 

### 🎯 Next Month Goals
- 

---

## Notes
- Backtest results: Wyckoff +153% (SR 3.02), MeanRev +116% (SR 1.98)
- Gate passing strategies: 2 (Wyckoff, MeanRev)
- Gate failed strategies: 6 (perlu fine-tune)
- 53 MT5 pairs all enabled (Valetax)
- **2026-07-19:** 2 order EURUSD scalping ditolak MT5 code=10017 (trade disallowed). Root cause: periksa koneksi gateway/context order atau market session. Tidak ada eksekusi = tidak ada PnL. Prioritas: debug mengapa code 10017 muncul berulang — sistem sinyal jalan tapi eksekusi gagal.
