# Comprehensive Backtest Master Ranking

**Date:** 2026-07-13 | **Period:** 2y | **Initial Capital:** $10,000 | **Commission:** 0.1% | **Slippage:** 0.05% | **Interval:** Daily

---

## 1. Full Backtest Results — All 10 Symbols

### Crypto

| Symbol | B&H % | Winner (Strategy) | 1st Sharpe | 2nd Sharpe | 3rd Sharpe |
|--------|-------|-------------------|-----------|-----------|-----------|
| **BTC-USD** | +4.99 | rsi (+32.1%) | rsi 4.95 | ema_cross 4.43 | keltner_breakout 3.23 |
| **ETH-USD** | -44.16 | ema_cross (+36.0%) | ema_cross 5.65 | keltner_breakout 1.46 | — |
| **SOL-USD** | -47.28 | bollinger (+14.7%) | bollinger 2.27 | rsi 0.30 | — |

### Forex

| Symbol | B&H % | Winner (Strategy) | 1st Sharpe | 2nd Sharpe | 3rd Sharpe |
|--------|-------|-------------------|-----------|-----------|-----------|
| **EURUSD=X** | +4.59 | ema_cross (+5.88%) | ema_cross 5.40 | rsi 4.77 | supertrend 0.31 |
| **GBPUSD=X** | +2.94 | bollinger (+2.52%) | bollinger 4.63 | ema_cross 3.35 | rsi -0.83 |
| **USDJPY=X** | +2.60 | ema_cross (+4.36%) | ema_cross 11.97 | supertrend 1.74 | bollinger 0.61 |
| **USDCHF=X** | -9.16 | (all negative/zero) | keltner -7.02 | ema_cross -4.47 | rsi -4.35 |
| **AUDUSD=X** | +2.17 | rsi (+8.21%) | rsi 6.36 | bollinger 5.78 | ema_cross 4.61 |
| **USDCAD=X** | +3.65 | ema_cross (+0.37%) | ema_cross 1.12 | rsi 0.36 | — |
| **NZDUSD=X** | -5.46 | rsi (+5.00%) | rsi 3.25 | bollinger 0.15 | — |

---

## 2. Global Strategy Ranking (by Sharpe across all symbols)

| Rank | Strategy | Avg Sharpe | Positive Symbols | Best Pairing | Worst Pairing |
|-----:|----------|-----------:|:---------------:|-------------|--------------|
| 1 | **rsi** | **1.12** | 8/10 | AUDUSD=X 6.36 | ETH-USD -4.15 |
| 2 | **ema_cross** | **1.83** | 7/10 | USDJPY=X 11.97 | NZDUSD=X -10.88 |
| 3 | **keltner_breakout** | **-7.23** | 4/10 | BTC-USD 3.23 | USDJPY=X -24.16 |
| 4 | **triple_ema** | **-8.71** | 2/10 | AUDUSD=X 7.51 | EURUSD=X -54.22 |
| 5 | **bollinger** | **-0.26** | 6/10 | AUDUSD=X 5.78 | USDCAD=X -6.20 |
| 6 | **supertrend** | **-2.60** | 3/10 | USDJPY=X 1.74 | USDCHF=X -10.19 |
| 7 | **donchian** | **0.00** | 0/10 | — (0 trades on all) | — |
| 8 | **rsi_pullback** | **-5.08** | 2/10 | BTC-USD 0.50 | USDCAD=X -11.91 |
| 9 | **macd** | **-3.17** | 0/10 | BTC-USD -0.32 (least bad) | NZDUSD=X -6.80 |

---

## 3. Elimination Candidates

**Rule:** Strategies with **negative Sharpe on 3+ symbols** are flagged for elimination.

| Strategy | Negative Count | Verdict |
|----------|:-------------:|---------|
| **MACD** | 10/10 ❌ | **ELIMINATE** — negative Sharpe on every single symbol |
| **RSI Pullback** | 8/10 ❌ | **ELIMINATE** — negative on 8/10, severely negative on most |
| **Supertrend** | 7/10 ❌ | **ELIMINATE** — negative on 7/10, only works on USDJPY |
| **Keltner Breakout** | 6/10 ❌ | **ELIMINATE** — negative on 6/10, extreme negatives on forex |
| **Bollinger** | 4/10 ⚠️ | **ELIMINATE** — negative on 4/10; mixed, works on AUD/GBP/SOL |
| **EMA Cross** | 3/10 ⚠️ | **ELIMINATE** — negative on 3/10 (SOL, USDCHF, NZDUSD) but top-tier on others |
| **RSI** | 2/10 ✅ | **KEEP** — best all-rounder, positive on 8/10 |
| **Triple EMA** | 2/10 ✅ | **KEEP** — but very sparse (many zero-trade, high variance) |
| **Donchian** | 0/10 → | **KEEP** — but zero trades on daily forex/crypto (noisy neutral) |

**Eliminated:** MACD, RSI Pullback, Supertrend, Keltner Breakout, Bollinger, EMA Cross

**Surviving strategies:** RSI, Triple EMA, Donchian

---

## 4. Walk-Forward Backtest — Top 5 Strategy-Symbol Combos

Runs with n_splits=5, train_ratio=0.7 to detect overfitting.

| # | Combo | Full Sharpe | Walk-Forward Verdict | OOS Trades | OOS Return | Note |
|:-:|-------|:-----------:|:--------------------:|:----------:|:----------:|------|
| 1 | **USDJPY=X + ema_cross** | **11.97** | ROBUST (1.0) | 0 | 0% | Very few signals — 3 trades in 2y all fell in-train. Robust by absence. |
| 2 | **AUDUSD=X + rsi** | **6.36** | WEAK (0.2) | 0 | 0% | 1 train trade per fold, 0 OOS. Overfitted signal. |
| 3 | **ETH-USD + ema_cross** | **5.65** | ROBUST (1.0) | 0 | 0% | 4 trades total, all in-train. |
| 4 | **EURUSD=X + ema_cross** | **5.40** | ROBUST (1.0) | 0 | 0% | 3 trades total, all in-train. |
| 5 | **AUDUSD=X + bollinger** | **5.78** | WEAK (0.2) | 0 | 0% | 5 train trades, 0 OOS. |

**Key insight:** These strategies trade too infrequently (3–10 trades over 2y) for 5-fold walk-forward to produce meaningful OOS signal. The high Sharpe ratios come from a tiny number of winning trades. For reliable walk-forward validation on daily data, consider extending to 3y–5y periods to increase sample size, or switching to 1h interval for more signal density.

---

## 5. Master Ranking Table (All Strategy × Symbol)

| Symbol | RSI | Bollinger | MACD | EMA Cross | Supertrend | Donchian | RSI Pullback | Keltner | Triple EMA |
|--------|:---:|:---------:|:----:|:---------:|:----------:|:--------:|:------------:|:-------:|:----------:|
| BTC-USD | **4.95** | 0.57 | -0.32 | **4.43** | -1.79 | 0.00 | 0.50 | **3.23** | -0.52 |
| ETH-USD | -4.15 | -4.06 | -0.84 | **5.65** | -0.17 | 0.00 | -3.98 | 1.46 | 0.00 |
| SOL-USD | 0.30 | **2.27** | -0.87 | -2.88 | -4.38 | 0.00 | -4.88 | -4.05 | 0.00 |
| EURUSD=X | **4.77** | -1.24 | -6.58 | **5.40** | 0.31 | 0.00 | -5.97 | -7.62 | -54.22 |
| GBPUSD=X | -0.83 | **4.63** | -3.00 | **3.35** | -1.55 | 0.00 | -7.19 | -20.92 | -40.25 |
| USDJPY=X | 0.66 | 0.61 | -1.81 | **11.97** | 1.74 | 0.00 | -0.04 | -24.16 | 0.00 |
| USDCHF=X | -4.35 | -5.08 | -5.37 | -4.47 | -10.19 | 0.00 | 0.00 | -7.02 | 0.00 |
| AUDUSD=X | **6.36** | **5.78** | -3.12 | **4.61** | -0.57 | 0.00 | -9.67 | 2.49 | **7.51** |
| USDCAD=X | 0.36 | -6.20 | -2.95 | 1.12 | -2.18 | 0.00 | -11.91 | -0.24 | 0.00 |
| NZDUSD=X | **3.25** | 0.15 | -6.80 | -10.88 | -4.90 | 0.00 | -6.66 | -15.57 | 0.00 |

*Values in bold = top 3 positive Sharpe for that symbol.*

---

## 6. Recommended Path Forward

| Action | Details |
|--------|---------|
| **Eliminate** | MACD, RSI Pullback, Supertrend, Keltner Breakout, Bollinger, EMA Cross |
| **Keep (monitor)** | RSI, Triple EMA, Donchian |
| **Next step** | Re-run RSI on forex pairs at 1h interval for higher signal density; extend backtest period to 3–5y for meaningful walk-forward validation |

---

*Past performance does not guarantee future results. For educational use only.*
