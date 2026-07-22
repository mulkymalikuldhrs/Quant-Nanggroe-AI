# QNA Backtest/Walk-Forward Validation — 2026-07-23

## Goal
Validate the QNA backtest engine + MeanReversion strategy run end-to-end without crashing, and confirm the API surface (BacktestEngine(BacktestConfig()).run(prices, signals) -> dict of metrics).

## Method
- Synthetic 15-min OHLCV (500 bars, seed=42), random walk around 100.
- Strategy: `MeanReversionStrategy.generate_signal(df)`.
- Engine: `BacktestEngine(BacktestConfig())`, `engine.run(df, signals_df)`.

## Result
- Engine executed in **14.9s**, returned a full metrics dict (final_equity, total_return, sharpe_ratio, max_drawdown, total_trades, win_rate, profit_factor, etc.).
- `total_trades: 0` on the smoke test because only a single end-of-series signal was fed (1-row signals_df). This confirms the engine API works; a real walk-forward needs a per-bar signal series.

## Verdict
✅ Backtest engine is functional and callable. The P0 production path (live MT5 + SL/TP + trailing + risk veto) is the validated live surface; backtest is the R&D surface and is intact.

## Next
- Wire a proper per-bar signal generator (vectorized) for walk-forward on real MT5 historical rates.
- Integrate walk-forward into the strategy selection loop (HF migration: E:/trading best strategies).
