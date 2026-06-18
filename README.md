# Quant Nanggroe AI — Quantitative Trading & Analysis Framework

Advanced quantitative finance platform featuring Kelly criterion variants, regime detection, stress testing, pattern recognition, and optimal execution.

## Architecture

```
quant_nanggroe/engine/
├── kelly/              # Position sizing
│   ├── fractional.py         # Fractional Kelly
│   ├── bayesian.py           # Bayesian Kelly
│   ├── drawdown.py           # Drawdown-controlled Kelly
│   ├── multi_asset.py        # Multi-asset Kelly
│   └── backtest_integration.py # Kelly → Backtest bridge (NEW)
├── regime/            # Market regime detection
│   ├── hmm.py                # Hidden Markov Model
│   ├── ensemble.py           # Ensemble voting
│   └── strategy_selector.py  # Regime → Strategy mapper (NEW)
├── strategy/          # Trading strategies
│   └── regime_strategy.py    # Regime-adaptive strategy (NEW)
├── stress_testing/    # Risk analysis (ENHANCED)
│   ├── monte_carlo.py        # GBM, jump-diffusion, regime-switching
│   ├── historical.py         # 5 crisis scenarios
│   ├── ewhs.py               # EWHS VaR/CVaR
│   └── sensitivity.py        # What-if analysis
├── pattern_recorder/  # Pattern discovery (ENHANCED)
│   ├── matrix_profile.py     # Matrix Profile (STUMPY + numpy)
│   ├── dtw.py                # Dynamic Time Warping
│   ├── embedding.py          # Embedding similarity
│   └── recurrence_plot.py    # RQA regime change detection
├── execution/         # Trade execution (ENHANCED)
│   └── almgren_chriss.py     # TWAP, VWAP, IS, Adaptive
├── data/              # Data layer (NEW)
│   ├── providers/            # 12 data providers
│   ├── fallback_chain.py     # Circuit breaker fallback
│   └── data_manager.py       # Unified data interface
├── visualization/     # Dashboard (NEW)
│   ├── chart_factory.py      # Plotly chart generation
│   └── dashboard.py          # QNA Dashboard
└── hermes_quant.py    # Backward-compat entry point
```

## Key Features

- **Kelly Advanced**: Fractional, Bayesian, drawdown-controlled, multi-asset
- **Regime Detection**: HMM, ensemble voting, volatility clustering
- **Stress Testing**: Monte Carlo 100K sims, 5 historical crises, EWHS VaR/CVaR
- **Pattern Recognition**: Matrix Profile, DTW, embedding similarity, recurrence plots
- **Optimal Execution**: Almgren-Chriss TWAP/VWAP/IS/Adaptive
- **Data Layer**: 12 providers with automatic fallback and circuit breaker
- **Visualization**: Interactive Plotly dashboard

## Quick Start

```bash
pip install numpy pandas scipy pydantic>=2.5
pip install yfinance ccxt plotly httpx
python scripts/test_qna_imports.py  # Smoke test
```

## Dependencies

- numpy, pandas, scipy
- pydantic >= 2.5
- yfinance, ccxt (data)
- plotly, matplotlib (visualization)
- hmmlearn, stumpy (ML)

## License

MIT
