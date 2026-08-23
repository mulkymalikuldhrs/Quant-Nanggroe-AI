# Quant-Nanggroe-AI

> Autonomous Quantitative Hedge Fund — FX/Commodity/Indices on MT5
> Version: v8.0.0 | Status: LIVE (proof phase)

## Quick Start
```bash
# All-in-one launcher (recommended)
"QNA Launcher.bat"          # Windows
./QNA Launcher.sh           # Linux/Mac

# Or individually
python qna.py daemon        # Live autonomous trading loop
python qna.py api           # FastAPI backend :8000
cd dashboard && npm run dev # Dashboard :3000
```

## What QNA Does
Autonomous quantitative trading system focused on **FX Majors + Gold + Commodities + Indices** via MetaTrader 5.

- **Signal Aggregation**: multiple strategy signals netted into ONE position per symbol at fixed 0.5% risk
- **CPCV Validation**: every strategy validated via Combinatorial Purged Cross-Validation across multiple assets
- **Per-Symbol Allocation**: only strategies with proven combo-profit-share trade each asset class
- **Tuned Params**: grid-search/Bayesian optimized parameters injected per-symbol before signal generation
- **Self-Evaluate**: real scorecards from synced MT5 journal (expectancy/PF/Sharpe/t-stat)
- **Self-Evolve**: lifecycle auto-keep/tune/kill based on live evidence, not backtest promises
- **Trading Profiles**: scalp(M15)/day(H1)/swing(D1) with ATR-adaptive SL/TP + breakeven ratchet

## Full Documentation
See [CANONICAL.md](CANONICAL.md) — Single Source of Truth for ALL claims, verified against file:line.
