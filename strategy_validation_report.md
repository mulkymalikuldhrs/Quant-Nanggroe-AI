# Strategy Validation — 1h Walk-Forward Verdict (REAL, not artifact)

**Run:** 2026-07-15 | **Engine:** TradingView MCP `walk_forward_backtest_strategy`
**Config:** 1y, 1h interval, 3-fold, train_ratio 0.7, $10k, 0.1%/0.05% cost
**Strategy under test:** RSI (only surviving KEEP candidate after daily-2y elimination)

## Per-Symbol Results (OOS = out-of-sample)

| Symbol | OOS trades | OOS Sharpe | OOS return % | Max DD % | Robustness | Verdict |
|--------|-----------|-----------|--------------|----------|-----------|---------|
| BTC-USD | 27 | **-5.91** | -12.13 | -17.34 | 0.72 | MODERATE (losing) |
| ETH-USD | 32 | **+0.56** | -0.42 | -20.26 | 0.67 | MODERATE (flat) |
| SOL-USD | 32 | **-0.62** | -4.76 | -16.52 | 0.30 | WEAK (losing) |
| EURUSD=X | 19 | **-25.9** | -7.73 | -7.91 | 0.63 | MODERATE (losing) |
| GBPUSD=X | 18 | **-24.78** | -7.65 | -7.65 | 0.72 | MODERATE (losing) |
| USDJPY=X | 18 | **-13.27** | -3.31 | -3.31 | 0.27 | WEAK (losing) |
| USDCHF=X | 18 | **-11.25** | -1.86 | -2.02 | 0.21 | WEAK (losing) |
| AUDUSD=X | 21 | **-20.39** | -5.55 | -5.71 | 0.86 | ROBUST (but losing) |

## Conclusion (honest)
- **No KEEP strategy is deployable for real capital.** RSI loses out-of-sample on
  every symbol except ETH (Sharpe +0.56, still -0.42% return).
- **Robustness score ≠ profitability.** AUDUSD "ROBUST 0.86" still lost -5.55%.
- **Engine = A** (correct math, kill-switch, PSR/DSR). **Strategy = B** — 109
  SMC/ICT/retail signals with NO statistically validated alpha at 1h/1y.
- **Next step before live:** research new signal classes (regime-gated, ensemble,
  microstructure) per ADDITIONAL_RESEARCH.md, then re-validate at 1h with ≥20 OOS
  trades/symbol. Current strategies are research-grade, not production-grade.

> Versus daily-2y (0–2 OOS trades, Donchian robustness 1.0 = zero-division artifact),
> the 1h run is the first *real* statistical read: consistently unprofitable OOS.
