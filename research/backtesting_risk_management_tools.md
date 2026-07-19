# Backtesting Engines & Risk Management Tools — Python

> **Task:** Report of Python tools for backtesting, portfolio optimization, risk metrics (VaR, Sharpe, Sortino, drawdown), and walk-forward analysis.  
> **Date:** 2025-07-19

---

## 1. Backtrader
- **URL:** https://www.backtrader.com/
- **GitHub:** https://github.com/mementum/backtrader
- **Type:** Backtesting engine + live trading
- **Fitur:**
  - Event-driven backtesting framework
  - Built-in analyzers: Sharpe Ratio, drawdown, trade-by-trade statistics, equity curve
  - Supports walk-forward analysis (via custom analyzers)
  - Reusable strategy/indicator/analyzer components
  - Data feeds from CSV, Yahoo, Interactive Brokers, Oanda, etc.
  - Commission & slippage models
  - Plotting with matplotlib
  - Live trading support via multiple brokers
- **Best for:** General-purpose algo trading backtesting with rich analytics

---

## 2. Backtesting.py
- **URL:** https://kernc.github.io/backtesting.py/
- **GitHub:** https://github.com/kernc/backtesting.py
- **Type:** Backtesting engine
- **Fitur:**
  - Lightweight, fast, Pandas/NumPy/Bokeh-based
  - Built-in indicators and custom indicator support
  - Commission & slippage simulation
  - Walk-forward optimization (via custom loops)
  - Interactive Bokeh plots (candlestick, equity curve, drawdown)
  - Strategy parameter optimization
  - Simple API — strategies defined as classes with `init()` and `next()`
  - pip-installable
- **Best for:** Rapid prototyping and interactive backtesting

---

## 3. VectorBT (Vector Backtester)
- **URL:** https://vectorbt.dev/
- **GitHub:** https://github.com/polakowo/vectorbt
- **Type:** High-performance backtesting engine
- **Fitur:**
  - **Vectorized** (not event-driven) — operates on Pandas/NumPy arrays with Numba JIT
  - Optional Rust engine for precompiled speed
  - **Extremely fast** — test 10,000+ parameter combinations across 100+ assets simultaneously
  - Portfolio-level backtesting with rebalancing
  - Comprehensive indicator library
  - Walk-forward optimization
  - Risk metrics: Sharpe, Sortino, Calmar, drawdown, VaR
  - Order book simulation, portfolio allocation
  - VectorBT PRO (paid) adds live trading, more data sources
- **Best for:** Parameter optimization at scale, portfolio-level backtesting

---

## 4. Zipline Reloaded
- **URL:** https://zipline.ml4trading.io/
- **GitHub:** https://github.com/stefan-jansen/zipline-reloaded
- **Type:** Event-driven backtesting engine
- **Fitur:**
  - Originally built by Quantopian; community-maintained fork
  - Event-driven pipeline with minute & daily resolution
  - Slippage & commission models
  - Built-in risk metrics (alpha, beta, Sharpe, drawdown)
  - Custom data bundles (CSV, Parquet, custom sources)
  - Works with PyFolio Reloaded for tear sheets
  - Supports futures, equities, crypto
  - Order types: market, limit, stop, stop-limit
- **Best for:** Quantitative research, strategy development at scale

---

## 5. QuantConnect (LEAN Engine)
- **URL:** https://www.quantconnect.com/
- **GitHub:** https://github.com/QuantConnect/Lean
- **Type:** Cloud + local backtesting platform (LEAN engine)
- **Fitur:**
  - Industrial-grade algorithmic trading engine (C# core, Python/C# API)
  - Multi-asset (equities, options, futures, forex, crypto)
  - Walk-forward optimization support
  - Built-in risk metrics: Sharpe, drawdown, VaR
  - Cloud-backtesting with massive historical data library
  - Local LEAN CLI for Docker-based backtesting
  - Live trading via multiple brokers
  - Portfolio optimization & risk management framework
  - Paper trading, alpha stream
- **Best for:** Professional-grade multi-asset backtesting in the cloud

---

## 6. PyAlgoTrade
- **URL:** https://gbeced.github.io/pyalgotrade/
- **GitHub:** https://github.com/gbeced/pyalgotrade
- **Type:** Event-driven backtesting + live trading
- **Fitur:**
  - Mature, well-documented event-driven backtesting
  - Data support: Yahoo Finance, Google Finance, CSV, NinjaTrader
  - Order types: market, limit, stop, stop-limit
  - Broker commission models, slippage
  - Technical indicators (SMA, RSI, MACD, etc.)
  - Paper trading & live trading support
  - Optimizer for parameter tuning
  - Statistical analysis tools
- **Best for:** Beginners, classic event-driven backtesting

---

## 7. Riskfolio-Lib
- **URL:** https://riskfolio-lib.readthedocs.io/
- **GitHub:** https://github.com/dcajasn/Riskfolio-Lib
- **Type:** Portfolio optimization & risk management library
- **Fitur:**
  - **13 risk measures:** Std Dev, Semi-Deviation, Mean Absolute Deviation, Conditional Value at Risk (CVaR), Entropic Value at Risk (EVaR), Worst Case Realization (WCR), Max Drawdown, Conditional Drawdown at Risk (CDaR), etc.
  - **4 objective functions:** Minimum Risk, Maximum Return, Maximum Risk-Adjusted Return Ratio, Maximum Utility
  - Portfolio optimization with constraints (weight bounds, turnover, sector limits)
  - Black-Litterman model, HRP (Hierarchical Risk Parity), NCO (Nested Clustered Optimization)
  - Sharpe, Sortino, Calmar ratios built-in
  - Jupyter notebook & Excel reports
  - Factor models (CAPM, Fama-French)
  - pip-installable
- **Best for:** Portfolio construction, asset allocation, risk-return optimization

---

## 8. skfolio
- **URL:** https://skfolio.org/
- **GitHub:** https://github.com/skfolio/skfolio
- **Type:** Portfolio optimization & risk management (scikit-learn compatible)
- **Fitur:**
  - Built on scikit-learn API (fit/predict/predict_proba pattern)
  - Portfolio optimization: Mean-Variance, CVaR, HRP, NCO, Black-Litterman
  - Risk measures: VaR, CVaR, drawdown, semi-deviation, entropy pooling
  - **Cross-validation** for portfolio models
  - **Stress testing** and scenario analysis
  - Transaction costs, management fees, budget constraints
  - Risk parity, risk budgeting
  - Sharpe ratio maximization, risk minimization
  - Feature importance & model selection
  - Integrated with scikit-learn pipelines
- **Best for:** Machine learning practitioners, robust portfolio model selection

---

## 9. PyFolio (Reloaded)
- **URL:** https://github.com/quantopian/pyfolio (original)
- **GitHub (Reloaded):** https://github.com/stefan-jansen/pyfolio-reloaded
- **Type:** Performance & risk analysis (tear sheets)
- **Fitur:**
  - **Tear sheets** — single-function comprehensive performance reports
  - Risk metrics: Sharpe ratio, Sortino ratio, Calmar ratio, Max Drawdown
  - Rolling beta, alpha, volatility
  - Factor exposure analysis (Fama-French)
  - Drawdown periods, monthly returns heatmap
  - Annual returns, cumulative returns
  - Turnover, market impact analysis
  - Tail risk metrics (VaR, CVaR, kurtosis)
  - Works directly with Zipline/QuantConnect output
- **Best for:** Post-backtest performance reporting and risk decomposition

---

## 10. QuantLib / QuantLib-Python
- **URL:** https://www.quantlib.org/
- **Type:** Quantitative finance library (derivatives pricing, risk)
- **Fitur:**
  - Derivatives pricing (options, swaps, bonds, credit)
  - Yield curve construction & bootstrapping
  - Risk analytics: Greeks, VaR, sensitivity
  - Monte Carlo simulation, finite difference methods
  - Fixed-income analytics (duration, convexity, OAS)
  - Market convention handling (day counts, calendars)
  - C++ core with Python bindings (quantlib-python)
  - **Not a backtesting engine** — risk/pricing analytics backbone
- **Best for:** Derivatives pricing, fixed-income risk, quantitative risk analytics

---

## 11. bt (Backtesting for Python)
- **URL:** https://github.com/pmorissette/bt
- **Type:** Backtesting engine with focus on portfolio-level backtesting
- **Fitur:**
  - Designed for **portfolio-level** backtesting and asset allocation strategies
  - Built-in risk metrics: Sharpe, drawdown, CAGR
  - Support for rebalancing schedules (monthly, quarterly, yearly)
  - Walk-forward optimization
  - Performance attribution
  - Integrated with PyFolio
  - Multiple asset class support
  - Reporting and plotting
- **Best for:** Portfolio allocation strategy backtesting

---

## 12. Freqtrade
- **URL:** https://www.freqtrade.io/
- **GitHub:** https://github.com/freqtrade/freqtrade
- **Type:** Crypto backtesting + live trading bot
- **Fitur:**
  - Full backtesting engine for crypto markets
  - Built-in risk management: trailing stop-loss, profit/loss ratio stop, minimal ROI, max drawdown
  - Walk-forward analysis via backtest-mode + parameter files
  - Over 20 built-in strategies
  - Custom strategy writing in Python
  - Hyperopt (hyperparameter optimization via algorithms)
  - Edge positioning (position sizing based on risk)
  - Telegram integration for live trading
  - Supports 30+ exchanges via CCXT
- **Best for:** Crypto algorithmic trading with built-in risk management

---

## 13. NautilusTrader
- **URL:** https://nautilustrader.io/
- **GitHub:** https://github.com/nautechsystems/nautilus_trader
- **Type:** High-performance backtesting & live trading framework
- **Fitur:**
  - Rust-accelerated core for high-throughput backtesting
  - Event-driven, multi-asset (crypto, FX, equities, futures, options)
  - Built-in risk engines (position limits, order filters, drawdown limits)
  - Live trading via multiple exchange adapters
  - Backtesting with realistic fill models and latency simulation
  - Modular risk management system
  - Performance analytics (Sharpe, Sortino, Calmar, drawdown)
  - Order book reconstruction and L2/L3 data support
- **Best for:** High-frequency / low-latency trading systems

---

## 14. FinQuant
- **URL:** https://github.com/fmilthaler/FinQuant
- **Type:** Portfolio optimization & risk management
- **Fitur:**
  - Portfolio optimization (Mean-Variance, Efficient Frontier)
  - Risk measures: VaR, CVaR, drawdown
  - Sharpe ratio, Sortino ratio
  - Time-series analysis (rolling statistics, correlations)
  - Monte Carlo simulations for portfolio projections
  - Backtesting of trading strategies
  - Reporting and visualization
- **Best for:** Desktop quant analysis and portfolio management

---

## Quick Comparison Matrix

| Tool                | Category              | Walk-Forward | VaR/CVaR | Sharpe | Sortino | Drawdown | Portfolio Opt. |
|---------------------|-----------------------|:---:|:---:|:---:|:---:|:---:|:---:|
| **Backtrader**       | Backtesting           | ✅* | ⬜ | ✅ | ⬜ | ✅ | ⬜ |
| **Backtesting.py**   | Backtesting           | ✅* | ⬜ | ✅ | ⬜ | ✅ | ⬜ |
| **VectorBT**         | Backtesting           | ✅  | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Zipline Reloaded** | Backtesting           | ⬜ | ⬜ | ✅ | ⬜ | ✅ | ⬜ |
| **QuantConnect**     | Backtesting Platform  | ✅  | ✅ | ✅ | ✅ | ✅ | ✅ |
| **PyAlgoTrade**      | Backtesting           | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| **Riskfolio-Lib**    | Risk Management       | N/A | ✅ | ✅ | ✅ | ✅ | ✅ |
| **skfolio**          | Risk Management       | N/A | ✅ | ✅ | ✅ | ✅ | ✅ |
| **PyFolio**          | Risk/Perf Analytics   | N/A | ✅ | ✅ | ✅ | ✅ | ⬜ |
| **QuantLib**         | Quant Finance Library | N/A | ✅ | ⬜ | ⬜ | ⬜ | ⬜ |
| **bt**               | Backtesting           | ✅  | ⬜ | ✅ | ⬜ | ✅ | ✅ |
| **Freqtrade**        | Backtesting (Crypto)  | ✅* | ⬜ | ✅ | ⬜ | ✅ | ⬜ |
| **NautilusTrader**   | Backtesting           | ⬜ | ⬜ | ✅ | ✅ | ✅ | ⬜ |
| **FinQuant**         | Portfolio + Backtest  | ⬜ | ✅ | ✅ | ✅ | ✅ | ✅ |

> ✅* = Walk-forward can be implemented via custom code/loops (not natively exposed as a single function)  
> N/A = Not applicable (risk-only library, no backtesting engine)  
> ⬜ = Not a primary feature

---

## Summary

This report covers **14 Python tools** spanning two categories:

**Backtesting Engines (8):** Backtrader, Backtesting.py, VectorBT, Zipline Reloaded, QuantConnect/LEAN, PyAlgoTrade, bt, NautilusTrader, Freqtrade — each offering different trade-offs between speed, features, asset coverage, and ease of use.

**Risk Management & Portfolio Optimization (6):** Riskfolio-Lib, skfolio, PyFolio, QuantLib, FinQuant — providing risk metrics (VaR, CVaR, Sharpe, Sortino, drawdown), portfolio optimization (Mean-Variance, HRP, Black-Litterman, risk parity), and performance analytics.

For a complete trading system, a common stack pairs **VectorBT** or **Backtrader** (backtesting) with **Riskfolio-Lib** or **skfolio** (portfolio optimization) and **PyFolio** (performance reporting).
