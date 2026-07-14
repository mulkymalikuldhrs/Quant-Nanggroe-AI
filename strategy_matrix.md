# Cross-Symbol Strategy Validation Matrix

**Source:** TradingView MCP `compare_strategies` (real backtest data)
**Period:** 1y · **Interval:** 1d · **Capital:** $10,000 · **Commission:** 0.1% · **Slippage:** 0.05%
**Generated:** 2026-07-14

## Matrix: Symbol x Strategy -> Sharpe Ratio

`0.00` = strategy produced 0 trades (no signal) unless noted. Negative = strategy lost money on a risk-adjusted basis.

| Strategy | BTC-USD | ETH-USD | SOL-USD | EURUSD=X | GBPUSD=X | USDJPY=X | USDCHF=X | AUDUSD=X |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| rsi | -3.50 | -10.38 | -10.16 | 16.26 | 12.40 | 1009.59 | 14.63 | 24.64 |
| bollinger | -5.10 | -11.97 | -2.55 | -3.79 | 3.78 | 94.43 | 8.16 | 8.76 |
| macd | -6.32 | -12.13 | -4.61 | -7.62 | -7.10 | -6.57 | -1.81 | 5.96 |
| ema_cross | -22.71 | -119.01 | -22.95 | -54.22 | -37.42 | 5.49 | -55.19 | 6.50 |
| supertrend | -22.14 | -34.85 | -11.35 | -40.66 | -13.06 | 5.02 | -46.06 | 0.97 |
| donchian | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| rsi_pullback | 0.00 | 0.00 | 0.00 | 0.00 | -10.43 | -13.76 | 0.00 | -9.77 |
| keltner_breakout | -36.72 | -46.34 | -36.11 | 0.00* | 0.00* | -42.30 | 0.00 | 6.18 |
| triple_ema | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| **buy-hold** | -46.04 | -37.81 | -52.40 | -2.23 | -0.76 | 10.16 | 1.59 | 6.05 |

* EURUSD/GBPUSD keltner produced a single losing trade (Sharpe rounds to 0.00); all other `0.00` = 0 trades (no signal triggered in period).

## Per-Symbol Tally and Elimination Rule

**Rule:** count strategies with Sharpe < 0 (neg) and Sharpe > 0 (pos); `0.00` (no signal) is neutral.
- **ELIMINATE** if negative-Sharpe strategies >= 3
- **KEEP** if positive-Sharpe strategies >= 5

| Symbol | neg | pos | neutral | Verdict | Reason |
|---|---:|---:|---:|---|---|
| BTC-USD | 6 | 0 | 3 | **ELIMINATE** | 6 negative strategies (deep bear: B/H -46%) |
| ETH-USD | 6 | 0 | 3 | **ELIMINATE** | 6 negative strategies (B/H -38%) |
| SOL-USD | 6 | 0 | 3 | **ELIMINATE** | 6 negative strategies (B/H -52%) |
| EURUSD=X | 4 | 1 | 4 | **ELIMINATE** | 4 negative strategies |
| GBPUSD=X | 4 | 2 | 3 | **ELIMINATE** | 4 negative strategies |
| USDJPY=X | 3 | 4 | 2 | **ELIMINATE** | 3 negative (rule triggers; pos=4 < 5) |
| USDCHF=X | 3 | 2 | 4 | **ELIMINATE** | 3 negative strategies |
| AUDUSD=X | 1 | 6 | 2 | **KEEP** | 6 positive strategies |

## Verdict Summary

- **KEEP:** `AUDUSD=X` (only symbol passing - RSI/Bollinger/MACD/EMA/Supertrend/Keltner all positive, only RSI-pullback negative).
- **ELIMINATE:** all 7 others. Crypto trio (BTC/ETH/SOL) fail universally in a 1y bear regime (B/H -38% to -52%). FX majors mostly fail except AUDUSD; USDJPY is borderline (4 pos vs 3 neg) but the neg>=3 rule eliminates it.
- **Best single strategy across the board:** `rsi` - positive on all 4 surviving FX majors, negative only on the 3 crypto bear markets.

## Notes
- `donchian`, `rsi_pullback`, `triple_ema` generated 0 trades on every symbol (SMA200 trend filter never engaged in this 1y window) - excluded from neg/pos tallies.
- Outlier Sharpe values (USDJPY rsi=1009.59, bollinger=94.43) stem from 100% win-rate on 2-3 trades with near-zero drawdown -> statistically thin, not robust.
- Data is real MCP output; no deployment performed (per task constraint).
