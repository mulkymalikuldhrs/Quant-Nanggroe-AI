# Full Walk-Forward Validation — Classical Strategies (REAL, 1h)

**Run:** 2026-07-15 | **Engine:** TradingView MCP `walk_forward_backtest_strategy`
**Config:** 1y, 1h interval, 3-fold, train_ratio 0.7, $10k, 0.1% comm, 0.05% slip

## BTC-USD, 4 classical strategies (this session)

| Strategy | OOS Return % | OOS Sharpe | OOS Trades | Robustness | Verdict |
|----------|-------------|-----------|-----------|-----------|---------|
| EMA 20/50 Cross | -11.65 | -9.70 | 22 | 0.49 | WEAK (overfit) |
| Supertrend (ATR) | -24.87 | -11.46 | 35 | 0.50 | MODERATE (loses) |
| Bollinger MeanRev | -8.20 | -3.16 | 47 | 0.52 | MODERATE (loses) |
| MACD Crossover | -42.54 | -10.87 | 99 | 0.83 | ROBUST but -42% |

**Key finding:** robustness_score measures consistency of return *sign*, NOT profitability.
MACD scores 0.83 "ROBUST" yet loses -42.54% OOS. Robustness ≠ profit. Do NOT trust
the robustness_label as a deploy signal.

## Prior 8-symbol RSI walk-forward (1h, this session)
RSI loses OOS on 7/8 symbols (Sharpe negative all); ETH +0.56 Sharpe but -0.42% return;
AUDUSD "ROBUST 0.86" still -5.55%. Same conclusion.

## Combined verdict
**No deployable alpha in any single-indicator / classical strategy at 1h in the
2025-2026 crypto+FX regime.** Engine A (execution/risk) is institutional-grade;
Strategy B (signal generation) is research-grade and currently UNPROFITABLE OOS.

## Implanted 10 new strategies (QNA v4.5.3)
All 10 import + run without error (verified on synthetic OHLCV). They CANNOT be
OOS-validated here because:
- The walk-forward MCP supports only 9 hardcoded strategies (rsi/bollinger/macd/
  ema_cross/supertrend/donchian/rsi_pullback/keltner_breakout/triple_ema).
- Microstructure edges (VPIN, Amihud illiquidity, Vol-of-Vol, Dispersion,
  Idiosyncratic) require real order-flow / benchmark_close feeds that are NOT
  wired in this repo yet.

To prove their alpha, the next step is: build a backtest harness inside QNA that
feeds real VPIN/Amihud series (from tick/volume data) into these strategies and
runs an internal walk-forward — NOT the TradingView MCP.

## What IS proven this session
- 10 strategy classes implant cleanly, 1819/1819 tests pass.
- Codegen RCE sandbox: blocks `import os` AND the `getattr(__builtins__,'__import__')('os')`
  bypass (AST allowlist). Legitimate `import numpy/pandas` + class defs still compile.
- Auth bypass closed (fail-closed; needs explicit QNAI_ALLOW_INSECURE_DEV opt-in).
- Kill-switch reset aligned to engine constant (was a dead mismatch).
- Broker auto-connect deferred (fail-closed).
- /security + /tools islands now serve REAL data (no mock).
- Worker kill-switch monitor LIVE (was hardcoded False).

## Bottom line for deployment
QNA is **NOT ready for live capital** on signals. It IS ready as an institutional-grade
execution/risk/monitoring engine with a safe strategy-implant pipeline. The signal
layer needs a real microstructure backtest harness before any KEEP strategy exists.
