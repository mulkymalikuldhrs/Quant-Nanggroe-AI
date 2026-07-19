# 📓 DHAHER HEDGE FUND — TRADE JOURNAL
## Auto-logged dari pipeline + manual entry

---

## Trade Log Format
```
Entry:
  Date:     YYYY-MM-DD HH:MM
  Pair:     EURUSD
  Style:    scalping/intraday1/swing1/etc
  Signal:   buy/sell (confidence X%)
  Entry:    1.XXXXX
  SL:       1.XXXXX (X pips)
  TP:       1.XXXXX (X pips, RR 1:X)
  Lot:      0.XX ($X risk)
  Reason:   Wyckoff volume spread / HN:NN HH break

Exit:
  Date:     YYYY-MM-DD HH:MM
  Price:    1.XXXXX
  PnL:      +$XX.XX / -$XX.XX
  Reason:   TP hit / SL hit / Manual
  Emotion:  Calm / Nervous / Satisfied

Evaluation:
  Follow plan? Yes/No
  SL management? Good/Bad
  Lesson: ...
```

---

## Trade History

| # | Date | Pair | Style | Signal | Entry | Exit | PnL | RR | Notes |
|---|------|------|-------|--------|-------|------|-----|----|-------|
| — | 2026-07-19 00:36 | EURUSD | scalping | fail_buy | 1.14415 | — | — | — | REJECTED code=10017 (no fill) |
| — | 2026-07-19 01:08 | EURUSD | scalping | fail_buy | 1.14415 | — | — | — | REJECTED code=10017 (no fill) |

> ⚠️ Kedua order ditolak MT5 (code 10017 = trade disallowed / market closed / context error). Tidak ada posisi terbuka, tidak ada PnL terealisasi.
