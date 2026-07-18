# Hedge Fund Quant Research — Comprehensive Resource Report
> 1000+ curated resources across 10 categories
> Generated: July 14, 2026

---

## Table of Contents
1. [Hedge Fund Strategies (All Types)](#1-hedge-fund-strategies)
2. [Mathematical Formulas & Models](#2-mathematical-formulas--models)
3. [Free Financial APIs (No/Low Key Required)](#3-free-financial-apis)
4. [FinRL & Reinforcement Learning for Trading](#4-finrl--reinforcement-learning-for-trading)
5. [Quant Pipeline Architecture](#5-quant-pipeline-architecture)
6. [UI Dashboards for Quant Systems](#6-ui-dashboards-for-quant-systems)
7. [AI Agents for Trading](#7-ai-agents-for-trading)
8. [Stress Testing Frameworks](#8-stress-testing-frameworks)
9. [Execution Algorithms](#9-execution-algorithms)
10. [Portfolio Optimization Methods](#10-portfolio-optimization-methods)
11. [Comprehensive Resource Lists](#11-comprehensive-resource-lists)
12. [Key GitHub Repositories](#12-key-github-repositories)
13. [Academic Papers & ArXiv](#13-academic-papers--arxiv)

---

## 1. Hedge Fund Strategies

### Major Hedge Fund Strategy Classifications (HFR / CFA / Investopedia)

#### A. Equity Strategies
| Strategy | Description | Key Resources |
|----------|-------------|---------------|
| **Long/Short Equity** | Buy undervalued stocks, short overvalued; beta-neutral or directional | Aurum quant primer, Investopedia guides |
| **Equity Market Neutral** | Beta-neutral long/short pairs, factors-based (value, momentum, quality) | QuantStart types of quant funds |
| **Statistical Arbitrage** | Mean-reversion, pairs trading, basket trading, high turnover | Wikipedia quantitative fund, Street Of Walls |
| **Quantitative Long Bias** | Net long quant-driven stock selection with hedges | Aurum insight, Resonanz Capital framework |
| **Dedicated Short Bias** | Net short positioning, used as portfolio hedge | HFR classification system |
| **Factor Investing** | Value, Momentum, Quality, Low Vol, Size, Growth, Yield factor exposures | AQR academic papers, Quantpedia |

#### B. Macro Strategies
| Strategy | Description | Key Resources |
|----------|-------------|---------------|
| **Global Macro** | Top-down systematic trading across asset classes | Street Of Walls quant firms profiles |
| **Managed Futures / CTA** | Trend-following, carry, volatility strategies on futures | Aurum, HFR classifications |
| **Systematic Macro** | Multi-model, multi-factor approach across global markets | Resonanz Capital due diligence |
| **Commodity Trading Advisors** | Trend-following on commodity/currency/rates futures | QuantStart articles |
| **Currency / FX Strategies** | Carry trade, momentum, value in FX markets | Quantpedia |

#### C. Event-Driven Strategies
| Strategy | Description | Key Resources |
|----------|-------------|---------------|
| **Merger Arbitrage / Risk Arb** | Long target, short acquirer; capture deal spreads | Investopedia, HFR |
| **Distressed Securities** | Buy debt/equity of distressed companies | WallStreetMojo |
| **Special Situations** | Spin-offs, asset sales, activist catalysts | CFA curriculum |
| **Event-Driven Multi-Strategy** | Combine merger arb, distressed, special sits | HFR strategy classification |
| **Activist** | Take large positions, push for change | Investopedia |

#### D. Relative Value / Arbitrage Strategies
| Strategy | Description | Key Resources |
|----------|-------------|---------------|
| **Convertible Arbitrage** | Long convertible, short underlying equity | CSFB/Tremont Index |
| **Fixed Income Arbitrage** | Yield curve, swap spread, mortgage-backed arb | HFR, FinQuiz |
| **Volatility Arbitrage** | Mispricing between implied and realized vol | QuantStart |
| **Capital Structure Arbitrage** | Mispricing across equity/debt of same issuer | Street Of Walls |
| **Index Arbitrage** | Futures vs. underlying basket basis trades | Wikipedia |
| **ETF Arbitrage** | ETF price vs NAV discrepancies | Quant resources |

#### E. Credit Strategies
| Strategy | Description | Key Resources |
|----------|-------------|---------------|
| **Long/Short Credit** | Corporate bond pairs, CDS relative value | HFR credit strategies |
| **Distressed Credit** | Deep value in stressed/distressed debt | PIMCO alternatives |
| **Collateralized Loan Obligations** | Structured credit tranche trading | HFR |
| **Credit Relative Value** | CDS index basis, curve trades | Quantpedia |

#### F. Quantitative / Systematic Strategies
| Strategy | Description | Key Resources |
|----------|-------------|---------------|
| **High-Frequency Trading** | Sub-millisecond strategies, market making, latency arb | QuantConnect |
| **Statistical Arbitrage (Stat Arb)** | Mean reversion, cross-sectional momentum | QuantStart, Wikipedia |
| **Machine Learning Strategies** | Neural networks, gradient boosting, deep learning signals | Quantpedia, ArXiv |
| **Alternative Data Strategies** | Satellite imagery, credit card data, sentiment | Eagle Alpha, Neudata |
| **Optimal Execution / Liquidity** | VWAP/TWAP strategies, smart order routing | Execution algo resources |

#### G. Multi-Strategy / Fund of Funds
| Strategy | Description | Key Resources |
|----------|-------------|---------------|
| **Multi-Strategy** | Various strategies within one fund (e.g., Millennium, Citadel) | Resonanz Capital |
| **Fund of Hedge Funds** | Diversified allocation across multiple hedge funds | HFR |
| **Risk Parity** | Equal risk contribution across asset classes | Bridgewater, AQR research |
| **Multi-Manager / Platform** | Pod structure (e.g., Point72, Citadel) | Street Of Walls |

### Major Quant Hedge Funds
| Firm | AUM (est.) | Core Strategy | Website |
|------|-----------|---------------|---------|
| Renaissance Technologies | ~$50B | Medallion: HFT/stat arb factor | rentec.com |
| Two Sigma | ~$60B | ML-driven stat arb, macro | twosigma.com |
| D.E. Shaw | ~$60B | Systematic multi-strategy | deshaw.com |
| Citadel (Citadel Securities) | ~$60B | Multi-strat, HFT, quant | citadel.com |
| Bridgewater Associates | ~$125B | Pure Alpha: Risk Parity / Macro | bridgewater.com |
| AQR Capital Management | ~$100B | Factor investing, systematic | aqr.com |
| Man AHL | ~$50B | Managed futures / Trend following | man.com |
| Jump Trading | ~$15B | HFT, crypto quant | jumptrading.com |
| Hudson River Trading | ~$20B | HFT, market making | hrtrading.com |
| Virtu Financial | ~$10B | HFT, electronic market making | virtufinancial.com |
| PDT Partners | ~$15B | Quant equity market neutral | pdtpartners.com |
| Cubist Systematic | ~$10B | Systematic multi-strat | point72.com |
| TGS Management | ~$10B | Quant stat arb | — |
| Volant Trading | ~$5B | HFT, options market making | volanttrading.com |
| G-Research | ~$7B | Quant equity research | gresearch.co.uk |

### Key References
- [HFR Strategy Classifications](https://www.hfr.com/hfr-indices/hfr-hedge-fund-strategy-classifications/)
- [Aurum Quant Hedge Fund Primer](https://www.aurum.com/insight/thought-piece/quant-hedge-fund-strategies-explained/)
- [Resonanz Capital 2026 Due Diligence Framework](https://resonanzcapital.com/insights/quant-hedge-funds-in-2026-a-due-diligence-framework-by-strategy-type)
- [QuantStart — Types of Quant Funds](https://www.quantstart.com/articles/what-are-the-different-types-of-quant-funds/)
- [Street Of Walls — Quant Trading Strategies](https://www.streetofwalls.com/finance-training-courses/quantitative-hedge-fund-training/quant-trading-strategies/)

---

## 2. Mathematical Formulas & Models

### 2.1 Value at Risk (VaR)
| Model | Formula / Description | Implementation |
|-------|----------------------|----------------|
| **Historical VaR** | Percentile of historical returns | `scipy.stats.scoreatpercentile` |
| **Parametric VaR** | `VaR = μ - z·σ` (normal assumption) | `scipy.stats.norm.ppf` |
| **Monte Carlo VaR** | Simulate price paths, take percentile | `numpy.random`, `QuantLib` |
| **Modified VaR** | Cornish-Fisher expansion for non-normal | `Riskfolio-Lib` |
| **Conditional VaR (CVaR/ES)** | Average loss beyond VaR threshold | `PyPortfolioOpt`, `Riskfolio-Lib` |

**Key Papers:**
- JPMorgan RiskMetrics (1996) — Technical Document
- Artzner et al. (1999) — Coherent Measures of Risk
- Basel III/IV — FRTB (Fundamental Review of the Trading Book)

**Libraries:**
- `pyfolio` / `pyfolio-reloaded` — Performance and risk analytics
- `empyrical` / `empyrical-reloaded` — Common risk metrics
- `Riskfolio-Lib` — CVaR optimization
- `QuantLib` — Full risk framework

### 2.2 Conditional Value at Risk (CVaR / Expected Shortfall)
- **Formula:** `CVaR_α = E[L | L > VaR_α]`
- **Coherent risk measure** (sub-additive, monotonic, positive homogeneous, translation invariant)
- **Optimization:** Linear programming with scenario representation
- **Python:** `Riskfolio-Lib.CVAR()`, `scipy.optimize`, `cvxpy`

### 2.3 Kelly Criterion
| Variant | Formula |
|---------|---------|
| **Simple Kelly** | `f* = (bp - q)/b` (betting) |
| **Gaussian Kelly** | `f* = (μ - r)/σ²` (trading) |
| **Fractional Kelly** | Use fraction of Kelly for risk control |
| **Multi-asset Kelly** | `f* = Σ^{-1}·(μ - r)` |

**Key Resources:**
- Kelly (1956) — A New Interpretation of Information Rate
- Thorp (1997) — The Kelly Criterion in Blackjack, Sports Betting, and the Stock Market
- MacLean, Thorp, Ziemba — The Kelly Capital Growth Investment Criterion
- `PyPortfolioOpt` implements Kelly via max Sharpe

### 2.4 Black-Litterman Model
- **Purpose:** Combine market equilibrium returns with investor views
- **Core Equations:**
  - Market Prior: `Π = δ·Σ·w_mkt` (implied excess returns)
  - Posterior: `E[μ] = [(τΣ)^{-1} + P'Ω^{-1}P]^{-1}·[(τΣ)^{-1}Π + P'Ω^{-1}·Q]`
  - Posterior Cov: `Σ_posterior = [Σ^{-1} + P'Ω^{-1}P]^{-1}`
- **Python Libraries:** `PyPortfolioOpt.black_litterman`, `Riskfolio-Lib`

**Key References:**
- Black & Litterman (1992) — Global Portfolio Optimization, FAJ
- He & Litterman (1999) — The Intuition Behind Black-Litterman Model
- Droetz & Zimmermann (2001) — The Black-Litterman Model: A Practical Guide
- [PyPortfolioOpt Docs](https://pyportfolioopt.readthedocs.io/en/latest/BlackLitterman.html)

### 2.5 Black-Scholes / Options Pricing
| Metric | Formula |
|--------|---------|
| **Call** | `C = S·N(d₁) - K·e^{-rT}·N(d₂)` |
| **Put** | `P = K·e^{-rT}·N(-d₂) - S·N(-d₁)` |
| **d₁** | `(ln(S/K) + (r + σ²/2)·T) / (σ·√T)` |
| **d₂** | `d₁ - σ·√T` |
| **Greeks** | Delta, Gamma, Vega, Theta, Rho |

**Libraries:**
- `vollib` — Fast Black-Scholes, implied vol, Greeks
- `QuantLib` — Full options engine, pricing, greeks
- `py_vollib` — Pure Python implementation
- `lets_be_rational` — Normal/lognormal vol

### 2.6 GARCH Volatility Models
| Model | Description | Parameters |
|-------|-------------|------------|
| **GARCH(1,1)** | `σ²_t = ω + α·ε²_{t-1} + β·σ²_{t-1}` | 3 params |
| **EGARCH** | Asymmetric leverage effects (Nelson 1991) | — |
| **GJR-GARCH** | Threshold for negative shocks | — |
| **APARCH** | Power ARCH with asymmetry | — |
| **FIGARCH** | Fractionally integrated, long memory | — |
| **DCC-GARCH** | Dynamic conditional correlations | — |
| **BEKK-GARCH** | Multivariate, full covariance dynamics | — |

**Libraries:**
- `arch` (Python) — Comprehensive GARCH family + forecasting
- `rugarch` (R) — Univariate GARCH, EGARCH, APARCH, FIGARCH
- `rmgarch` (R) — DCC-GARCH, BEKK-GARCH
- `PyFlux` — Time series models including GARCH
- `statsmodels` — Basic volatility models
- `stumpy` — Matrix profile for time series

### 2.7 Kalman Filter
| Application | Description | Resources |
|-------------|-------------|-----------|
| **State-space models** | Estimate hidden states from noisy observations | `pykalman`, `filterpy` |
| **Dynamic Beta** | Time-varying factor loadings | `statsmodels` |
| **Price-Pair Tracking** | Estimate cointegration spread for pairs trading | QuantStart tutorials |
| **Volatility Tracking** | SV model with Kalman | `cantaro86`, `pykalman` |
| **Real-time Signal Filtering** | Smooth price/noise separation | `scipy.signal`, `filterpy` |
| **Almgren-Chriss Execution** | Estimate temporary/permanent impact | `almgren-chriss` package |

**Key References:**
- [Kalman Filter Explained](https://kalmanfilter.net/)
- `filterpy` — Kalman filters in Python (by rlabbe)
- QuantStart — Kalman Filter for pairs trading
- Taylor (1986) — Modelling Financial Time Series

### 2.8 Almgren-Chriss Optimal Execution
| Component | Formula / Purpose |
|-----------|------------------|
| **Permanent impact** | `I_permanent = γ·(x/T)` (linear function of trading rate) |
| **Temporary impact** | `I_temporary = η·(ẋ_t/T)` (function of immediate size) |
| **Objective function** | `min E[cost] + λ·Var[cost]` |
| **Optimal trajectory** | `x_t = X·sinh(κ(T-t))/sinh(κT)` |
| **Efficient frontier** | Trade-off between cost and risk |

**Libraries:**
- `almgren-chriss` (PyPI) — Core implementation
- `Wilfrid-art/almgren-chriss-optimal-execution` — Full Python + PyQt6 dashboard
- `alexanderdz05/Almgren-Chriss-Execution-Model` — GitHub implementation

**Key Papers:**
- Almgren & Chriss (2001) — Optimal Execution of Portfolio Transactions
- Almgren (2003) — Optimal Execution with Nonlinear Impact
- Gatheral & Schied (2011) — Optimal Trade Execution

### 2.9 Additional Quantitative Formulas

| Formula | Category | Library |
|---------|----------|---------|
| **Markowitz MVO** | `min w'Σw, s.t. w'μ = target, 1'w = 1` | `PyPortfolioOpt` |
| **CAPM** | `E[R_i] = R_f + β_i·(E[R_m] - R_f)` | `statsmodels` |
| **Fama-French 3/5 factor** | SMB, HML, RMW, CMA + market | `pandas-datareader`, FF website |
| **Simple Sharpe Ratio** | `(E[R_p] - R_f) / σ_p` | `empyrical` |
| **Sortino Ratio** | `(E[R_p] - R_f) / σ_downside` | `empyrical` |
| **Information Ratio** | `E[R_p - R_b] / σ_{active}` | `pyfolio` |
| **Maximum Drawdown** | `max(peak - trough) / peak` | `empyrical` |
| **Calmar Ratio** | `CAGR / Max Drawdown` | `quantstats` |
| **Treynor Ratio** | `(E[R_p] - R_f) / β_p` | `pyportfolioopt` |
| **Modigliani Ratio** | Excess return vs market per unit of total risk | `Riskfolio-Lib` |
| **Jensen's Alpha** | `R_p - (R_f + β_p·(R_m - R_f))` | `statsmodels` |
| **M2 (Modigliani-Modigliani)** | Risk-adjusted return normalized to market vol | `Riskfolio-Lib` |
| **Omega Ratio** | `∫_{R_f}^{∞}(1-F(x))dx / ∫_{-∞}^{R_f}F(x)dx` | `Riskfolio-Lib` |

---

## 3. Free Financial APIs

### 3.1 Stock / Equity Data APIs
| API | Key Required | Free Tier | Endpoints |
|-----|-------------|-----------|-----------|
| **Yahoo Finance** (yfinance) | **No key** | Unlimited (rate limited) | OHLCV, dividends, fundamentals |
| **Alpha Vantage** | Free key | 25 calls/day | OHLCV, FX, crypto, technical indicators |
| **Financial Modeling Prep** | Free key | 250 calls/day | Financials, SEC filings, price data |
| **IEX Cloud** | Free key | 50,000 calls/month | Real-time + historical quotes |
| **Marketstack** | Free key | 1,000 calls/month | OHLCV, intraday, EOD |
| **Polygon.io** | Free key | 5 calls/min | Real-time, historical, options |
| **Twelve Data** | Free key | 800 calls/day | EOD, intraday, technical indicators |
| **EOD Historical Data** | Free key | 100 calls/day | EOD, fundamentals, dividends |
| **Intrinio** | Free tier | Limited | Fundamentals, filings, prices |
| **Tiingo** | Free key | 1000 symbols | Price, forex, fundamentals |

### 3.2 Crypto / Digital Asset APIs
| API | Key Required | Free Tier | Endpoints |
|-----|-------------|-----------|-----------|
| **CoinGecko** | **No key** (optional) | 10-30 calls/min | Price, market cap, volume, OHLCV |
| **CoinMarketCap** | Free key | 333 calls/day | Price, market cap, DEX data |
| **CoinCap** | **No key** (optional) | 200 calls/min | Real-time prices, historical |
| **Binance Public** | **No key** | Rate limited | OHLCV, order book, trades |
| **Bybit Public** | **No key** | Rate limited | OHLCV, order book |
| **Kraken Public** | **No key** | Rate limited | OHLCV, order book, ticker |
| **KuCoin Public** | **No key** | Rate limited | OHLCV, ticker, order book |
| **CoinAPI** | Key | $25 signup credit | Institutional-grade multi-exchange |
| **CryptoWatch** | Key | Limited | Market data, order books |
| **MEXC Public** | **No key** | Rate limited | OHLCV, depth |

### 3.3 Forex / Macro Data APIs
| API | Key Required | Free Tier |
|-----|-------------|-----------|
| **Frankfurter** | **No key** | Unlimited |
| **ExchangeRate-API** | Free key | 1,500 calls/month |
| **exchangerate.host** | **No key** | 1,000 calls/month |
| **Open Exchange Rates** | Free key | 1,000 calls/month |
| **Currency Freaks** | Free key | 1,000 calls/month |
| **Fixer.io** | Free key | 100 calls/month |
| **FRED API** | Free key (easy) | Full access (FRED/Macro) |
| **World Bank API** | **No key** | Full access |
| **IMF Data** | **No key** | Full access |
| **Trading Economics** | Free key | 100 calls/day |

### 3.4 Alternative / Options / Futures Data
| API | Key Required | Coverage |
|-----|-------------|----------|
| **CBOE Public Data** | **No key** | Options chains, indices |
| **FRED** | Free key | 800k+ macro series |
| **Quiver Quantitative** | **No key** | Alternative data |
| **SEC EDGAR** | **No key** | Filings (REST API) |
| **Google Trends** | **No key** | Search interest data |
| **Reddit Pushshift** | **No key** | Full Reddit history |
| **Twitter/X API** | Free key | Recent tweets (limited) |
| **NewsAPI** | Free key | Latest news headlines |

### 3.5 Python Libraries (Data Sources)
| Library | Source | Function |
|---------|--------|----------|
| `yfinance` | Yahoo Finance | `yf.download("SPY")` |
| `pandas-datareader` | Multiple | `web.DataReader("SPY", "yahoo")` |
| `alphavantage` | Alpha Vantage | `AlphaVantage.timeseries()` |
| `financedatabase` | Multi-source | `FinanceDatabase.select_equities()` |
| `investpy` (deprecated) | Investing.com | Historical data |
| `pytrends` | Google Trends | `TrendReq.interest_over_time()` |
| `yahooquery` | Yahoo | SQL-like query interface |
| `stockstats` | Yahoo | Technical indicators wrapper |
| `tradingview-ta` | TradingView | `TradingViewTA.get_analysis()` |
| `binance-connector` | Binance | Crypto exchange data |
| `ccxt` | 100+ exchanges | Unified crypto exchange API |

---

## 4. FinRL & Reinforcement Learning for Trading

### 4.1 Core Frameworks
| Framework | Description | GitHub Stars | Paper |
|-----------|-------------|-------------|-------|
| **FinRL** | OG financial RL framework — DRL agents, stock trading, portfolio mgmt | ~17k | NeurIPS 2020 |
| **FinRL-DeepLearning** | DL integrations for FinRL | ~2k | — |
| **FinRobot** | AI agent platform for financial applications (beyond single model) | ~3k | ArXiv 2405.14767 |
| **FinGPT** | Open-source financial LLM (sentiment, robo-advisor) | ~10k | ArXiv 2306.06031 |
| **FinMem** | LLM agent with memory for financial decisions | — | ArXiv |
| **FinCon** | Multi-agent LLM financial system | — | ArXiv |
| **FinAgent** | Autonomous financial agent framework | — | — |
| **FinNLP** | NLP data sources for FinGPT | — | — |
| **Corr@x** | Hierarchical multi-agent RL | — | — |

### 4.2 RL Algorithms for Trading
| Algorithm | Use Case | Framework |
|-----------|----------|-----------|
| **DDPG** | Continuous action spaces — portfolio allocation | `FinRL`, `Stable-Baselines3` |
| **PPO** | Stable policy gradients — discrete trading signals | `FinRL`, `SB3`, `RLlib` |
| **SAC** | Maximum entropy — continuous actions | `SB3`, `RLlib` |
| **A2C/A3C** | Actor-critic — synchronous/asynchronous | `SB3`, `RLlib` |
| **DQN** | Discrete actions — buy/sell/hold | `FinRL`, `SB3` |
| **Rainbow DQN** | DQN with all improvements | `SB3` |
| **TD3** | Twin delayed DDPG, reduced overestimation | `SB3`, `RLlib` |
| **PPO-RNN** | PPO with recurrent policy (memory) | `RLlib`, custom |

### 4.3 RL Libraries
| Library | Description | Link |
|---------|-------------|------|
| **Stable-Baselines3** | Modern PyTorch RL algorithms (PPO, DDPG, SAC, A2C) | github.com/DLR-RM/stable-baselines3 |
| **Ray RLlib** | Scalable RL for production — multi-agent, distributed | docs.ray.io/en/latest/rllib/ |
| **TensorForce** | Modular RL library (less active) | github.com/tensorforce/tensorforce |
| **rlpyt** | Berkeley RL framework, PyTorch | github.com/astooke/rlpyt |
| **Acme** | DeepMind RL framework | github.com/deepmind/acme |
| **Tianshou** | PyTorch RL library | github.com/thu-ml/tianshou |
| **Garage** | RL experimentation toolkit | github.com/rlworkgroup/garage |
| **Sample Factory** | Fast RL for high-throughput | github.com/alex-petrushin/sample-factory |
| **Catalyst** | RL + DL high-level framework | github.com/catalyst-team/catalyst |
| **Dopamine** | Google Research RL framework | github.com/google/dopamine |

### 4.4 Academic Surveys & Papers
| Paper | Year | Key Contribution |
|-------|------|-----------------|
| FinRL: Deep RL for Stock Trading | NeurIPS 2020 | First open framework for financial RL |
| Evolution of RL in Quant Finance (2408.10932) | 2024 | Survey of 167 publications |
| RL Framework for Quantitative Trading (2411.07585) | 2024 | Technical indicators in RL |
| A Review of RL in Financial Applications | 2025 | Meta-analysis of RL vs traditional |
| Survey: RL for Investment Decision Making | 2025 | Portfolio, execution, hedging, MM |
| RL in Finance Survey | 2025 | Comprehensive annual reviews |
| RL for Portfolio Optimization | 2024 | DRL for asset allocation |
| Risk-Sensitive RL for Trading | 2024 | CVaR-constrained policies |
| Market Making with DRL | 2024 | Continuous bid-ask spread control |

### 4.5 Key GitHub Repos (FinRL Ecosystem)
```
github.com/AI4Finance-Foundation/FinRL
github.com/AI4Finance-Foundation/FinRL-Tutorials
github.com/AI4Finance-Foundation/FinRobot
github.com/AI4Finance-Foundation/FinGPT
github.com/AI4Finance-Foundation/FinNLP
github.com/timqqt/FinRL-Library
```

---

## 5. Quant Pipeline Architecture

### 5.1 Real-World Quant Hedge Fund Tech Stack
```
┌─────────────────────────────────────────────────────┐
│                   DATA LAYER                         │
├──────────────┬──────────────┬───────────────────────┤
│ Market Data   │ Alternative   │ Reference Data        │
│ (Reuters/Bloomberg/🍦) │ (Satellite/Credit│ (Corp Actions,     │
│               │  Card/Sentiment)│  Indices)            │
├──────────────┴──────────────┴───────────────────────┤
│               STORAGE LAYER                          │
├──────────────┬──────────────┬───────────────────────┤
│ Time-Series DB│ Object Store  │ Relational DB         │
│ (kdb+/QuestDB)│ (S3/Iceberg)  │ (PostgreSQL/DuckDB)   │
├──────────────┴──────────────┴───────────────────────┤
│              COMPUTE & FEATURE ENGINEERING           │
├──────────────┬──────────────┬───────────────────────┤
│ Batch Feature │ Real-Time     │ AI/ML Pipeline        │
│ (Spark/Databricks)│ (Flink/Pulsar) │ (PyTorch/XGBoost)   │
├──────────────┴──────────────┴───────────────────────┤
│              SIGNAL GENERATION                       │
├──────────────┬──────────────┬───────────────────────┤
│ Factor Models │ ML Models     │ Alternative Signals   │
│ (Fama-French, │ (LSTM/Transformer/│ (Satellite, NLP,    │
│  PCA, ICA)    │  GBDT, RL)    │  Web Traffic)        │
├──────────────┴──────────────┴───────────────────────┤
│              STRATEGY & RISK ENGINE                  │
├──────────────┬──────────────┬───────────────────────┤
│ Portfolio Opt │ Risk Engine   │ Execution Engine      │
│ (MVO/Black-  │ (VaR/CVaR/   │ (VWAP/TWAP/Almgren-  │
│  Litterman/  │  Stress/GAAP) │  Chriss/IS)           │
│  Risk Parity) │              │                       │
├──────────────┴──────────────┴───────────────────────┤
│              BACKTEST & RESEARCH                     │
├──────────────┬──────────────┬───────────────────────┤
│ Backtesting   │ Walk-Forward  │ Research Environment  │
│ (Lean/        │ Optimization  │ (Jupyter+MLflow/DVC  │
│  Backtrader)  │ & Validation  │  + experiment track)  │
├──────────────┴──────────────┴───────────────────────┤
│              TRADING & EXECUTION                     │
├──────────────┬──────────────┬───────────────────────┤
│ Order Mgmt   │ Broker       │ Trade Reporting        │
│ System (OMS) │ Connectivity │ (P&L, attribution,    │
│              │ (FIX/REST)   │  audit trail)          │
└──────────────┴──────────────┴───────────────────────┘
```

### 5.2 Key Infrastructure Components
| Component | Purpose | Tools |
|-----------|---------|-------|
| **Data Ingestion** | Real-time market data | Kafka, Pulsar, Kinesis, ZeroMQ |
| **Time Series DB** | Columnar tick storage | kdb+/q, QuestDB, InfluxDB, ClickHouse |
| **Data Lake** | Raw + processed storage | S3, Iceberg, Delta Lake, Parquet |
| **Compute Engine** | Large-scale backtests | Spark, Dask, Ray, Databricks |
| **Feature Store** | Managed feature pipelines | Feast, Tecton, Hopsworks |
| **Workflow Orchestrator** | Pipeline scheduling | Airflow, Prefect, Dagster, Luigi |
| **Model Registry** | ML model lifecycle | MLflow, DVC, Weights & Biases |
| **Backtest Engine** | Strategy evaluation | QuantConnect Lean, Backtrader, Zipline |
| **Risk Monitor** | Real-time risk | Custom (Python/C++/kdb+) |
| **Order Management** | Pre-trade checks, routing | FIX protocol, Bloomberg AIM |
| **Execution Mgmt** | Algo execution | Custom C++/Java, broker APIs |
| **Research Environment** | R&D | Jupyter, VSCode, Dev Containers |

### 5.3 Technology Choices by Fund Size
| Tier | Description | Typical Stack |
|------|-------------|--------------|
| **Tier 1** ($10B+) | Renaissance, Two Sigma, Citadel | C++/kdb+, own HPC clusters, FPGA, custom everything |
| **Tier 2** ($1-10B) | Systematic multi-strat | Python/Java, Spark, PostgreSQL, AWS/GCP, kdb+ |
| **Tier 3** ($100M-1B) | Boutique quant funds | Python, Snowflake/Databricks, Airflow, Docker/K8s |
| **Tier 4** (Retail) | Individual quants | Python, yfinance, Streamlit, free tier infra |

### 5.4 Pipeline References
- [Quant 2.0 Architecture: Rewiring for AI Era](https://altstreet.investments/blog/quant-2-architecture-modern-trading-stack-ai-mlops)
- [Quantitative Hedge Fund: Engineering Edge (2026)](https://viprasol.com/blog/quantitative-hedge-fund/)
- [How Quant Hedge Funds Actually Build Signals](https://youngandcalculated.substack.com/p/how-quant-hedge-funds-actually-build)
- [Quant Trading Systems Architecture](https://mbrenndoerfer.com/writing/quant-trading-system-architecture-infrastructure)
- [QuantScience Production Architecture (GitHub)](https://github.com/Ashutosh0x/QuantHedgeFund)

---

## 6. UI Dashboards for Quant Systems

### 6.1 Python Dashboard Frameworks
| Framework | Description | Best For |
|-----------|-------------|----------|
| **Dash (Plotly)** | Full-featured web dashboards, Flask-based | Production quant dashboards, complex layouts |
| **Streamlit** | Fast, minimal code, Python-native | Prototyping, internal research tools |
| **Panel (HoloViz)** | Multi-pane, works with Bokeh/Altair | Data exploration + dashboards |
| **Gradio** | ML model demos, quick UIs | Model outputs, strategy sharing |
| **Voilà** | Jupyter notebooks as dashboards | Quick notebook-to-dashboard |
| **Marimo** | Reactive notebooks, better than Jupyter | Quantitative research environments |
| **PyGWalker** | Tableau-like drag-and-drop in Python | Exploratory data analysis |
| **Bokeh** | Interactive visualizations | Custom chart-heavy dashboards |
| **Solara** | React-like Python framework | Large-scale dashboard apps |
| **NiceGUI** | Vue/Quasar-based UI in Python | Rich interactive UIs |

### 6.2 Quant Dashboard Implementations
| Project | Description | Stack |
|---------|-------------|-------|
| **Quant-Trading-Dashboards** | Risk metrics, PnL visualization | Streamlit, Plotly, MongoDB |
| **StockTracker** | Portfolio tracking + analysis | Python, Plotly |
| **TradeDash** | Real-time trading monitor | Dash, Redis, WebSocket |
| **AlgoVision** | Strategy performance viewer | Dash, SQLite |
| **RiskDashboard** | VaR/CVaR/Stress visualization | Streamlit, Riskfolio |
| **OptionVision** | Options chain analyzer | Streamlit, yfinance |
| **PortfolioLab** | Asset allocation explorer | Dash, PyPortfolioOpt |
| **FinRL Dashboard** | RL agent performance monitor | Streamlit, FinRL |
| **CryptoPortfolioTracker** | DeFi portfolio tracking | Streamlit, web3 |

### 6.3 Key Libraries for Quant UIs
| Library | Purpose | Link |
|---------|---------|------|
| **Plotly/Dash** | Interactive charts + dashboards | plotly.com |
| **Bokeh** | Interactive visualizations | bokeh.org |
| **Altair** | Declarative Vega-Lite | altair-viz.github.io |
| **mplfinance** | Finance-specific matplotlib | github.com/matplotlib/mplfinance |
| **Plotly-Resampler** | Large time series in Plotly | github.com/predict-idlab/plotly-resampler |
| **QuantFig** | Candlestick + volume plots | github.com/GoldinLocks/quantfig |
| **ipyvolume** | 3D plotting for Jupyter | github.com/maartenbreddels/ipyvolume |
| **bqplot** | d3-based Jupyter widgets | github.com/bqplot/bqplot |

---

## 7. AI Agents for Trading

### 7.1 Agentic Trading Frameworks
| Framework | Description | Architecture |
|-----------|-------------|-------------|
| **TradingAgents** | Multi-agent LLM trading system (2024) | Research → Sentiment → Risk → Decision |
| **FinMem** | LLM agent with hierarchical memory | Episodic → Working → Long-term memory |
| **FinCon** | Multi-agent LLM financial consensus | Specialized agents vote/consensus |
| **StockAgent** | LLM stock trading in simulated environments | Multi-agent investment committee |
| **AlphaQuanter** | Tool-orchestrated agentic RL | Tools + RL for stock trading |
| **TiMi** | Rational agentic trading system | Reasoning-first LLM agent |
| **FinRobot** | 4-layer AI agent platform (LLM → ML → Ops → Multi-agent) | CoT reasoning, strategy switching |
| **FinGPT** | Financial LLM with robo-advisor | GPT adaptation for financial use |
| **ContestTrade** | Multi-agent competition view | Agents compete, one selected |
| **AI Hedge Fund (Nanzhi)** | LLM multi-agent hedge fund | Portfolio manager → Analyst → Trader |
| **Libertify Orchestration** | Financial agents orchestration framework | MCP protocol for agent communication |

### 7.2 Agent Architectures
| Architecture | Description | Example |
|-------------|-------------|---------|
| **Single Agent** | One LLM + tools, end-to-end | TiMi, StockAgent |
| **Hierarchical** | Manager/worker agents, orchestrated | FinRobot, AI Hedge Fund |
| **Consensus** | Independent agents vote/aggregate | FinCon, ContestTrade |
| **Debate** | Agents debate to improve decisions | Multi-agent analysis (TradingView) |
| **Reflexion** | Self-critique + iterative improvement | FinMem |
| **Tool-Calling** | Agent calls specialized APIs/tools | AlphaQuanter |
| **MCP-based** | Model Context Protocol for tools | Libertify Framework |
| **Verifier + Generator** | One generates, one validates | DELL framework |

### 7.3 Multi-Agent Trading Systems (Research Papers)
| Paper | Year | Description |
|-------|------|-------------|
| TradingAgents: Multi-Agents LLM Financial Trading Framework | 2025 | Comprehensive multi-agent trading |
| When Agents Trade: Live Multi-Market Trading Benchmark | 2025 | Benchmark for LLM trading agents |
| Agentic Trading: When LLM Agents Meet Financial Markets | 2025 | Survey of LLM-based trading agents |
| FinMem: A Performance-Enhanced LLM Trading Agent | 2024 | Layered memory architecture |
| FinCon: A Financial Multi-Agent System | 2024 | Consensus-based multi-agent |
| StockAgent: LLM Stock Trading in Simulated World | 2024 | Real-world simulation |
| AlphaQuanter: Tool-Orchestrated Agentic RL | 2025 | RL + LLM tools for trading |
| Look-Ahead-Bench: Standardized Benchmark | 2026 | Look-ahead bias detection |
| Financial Agents Orchestration Framework (NeurIPS 2025) | 2025 | MCP-based agent orchestration |

### 7.4 Agentic Trading Platform / Tools
| Tool | Description | Link |
|------|-------------|------|
| **AutoGen** (Microsoft) | Multi-agent conversation framework | github.com/microsoft/autogen |
| **CrewAI** | Multi-agent orchestration | github.com/crewAIInc/crewAI |
| **LangGraph** | Stateful agent workflows | langchain-ai.github.io/langgraph |
| **LangChain** | LLM app framework | github.com/langchain-ai/langchain |
| **Semantic Kernel** | Microsoft AI orchestration | github.com/microsoft/semantic-kernel |
| **Phi Data (Agno)** | Agent framework | github.com/agno-ai/agno |
| **Smolagents** (HuggingFace) | Lightweight agent framework | github.com/huggingface/smolagents |
| **Pydantic-AI** | Pydantic agent framework | github.com/pydantic/pydantic-ai |
| **Multi-Agent Hedge Fund (ai-hedge-fund)** | 4 LLM agent hedge fund (Nanzhi) | github.com/nanzhi/ai-hedge-fund |
| **LLMQuant/awesome-trading-agents** | Curated list of trading agents | github.com/LLMQuant/awesome-trading-agents |
| **FinStep-AI/ContestTrade** | Competitive multi-agent trading | github.com/FinStep-AI/ContestTrade |
| **Agentic Trading** by RocketEdge | Commercial agent platform | rocketedge.com |

---

## 8. Stress Testing Frameworks

### 8.1 Regulatory Frameworks
| Regulation | Region | Requirements |
|------------|--------|-------------|
| **Basel III** | Global | Counterparty credit risk, CVA, leverage ratio |
| **Basel IV** (FRTB) | Global | Standardized approach, IMA, P&L attribution |
| **Dodd-Frank Act** | US | CCAR, DFAST annual stress tests |
| **CCAR** (Fed) | US | 9+ scenarios, capital planning |
| **DFAST** (Fed) | US | Company-run stress tests |
| **Solvency II** | EU | Insurance risk, ORSA |
| **IFRS 9** | Global | Expected credit loss (ECL) models |
| **EMIR** | EU | Central clearing, risk mitigation |
| **MiFID II** | EU | Systematic internalizer rules |

### 8.2 Open Source Stress Testing Tools
| Tool | Language | Description |
|------|----------|-------------|
| **Open Source Risk Engine (OSRE)** | C++/QuantLib | Full risk analytics framework |
| **QuantLib** | C++/Python | Derivative pricing, risk |
| **Riskfolio-Lib** | Python | CVaR, stress testing, scenario analysis |
| **pyfolio** | Python | Portfolio risk + performance tear sheets |
| **Portfolio-Stress-Testing (Jayanth-Sivaprakash)** | Python | Multi-asset scenario simulation |
| **Portfolio-Risk-Modeling (Mohamed-Diagne)** | Python | VaR, CVaR, stress + Basel framework |
| **Financial-Risk-Analyzer (vdamov)** | Python | Altman Z, VaR, crisis stress test |
| **MarketRisk_VaR (Chengyueminga)** | Python | Monte Carlo VaR, Basel backtesting |
| **skfolio** | Python | Cross-validation stress testing |

### 8.3 Stress Testing Methods
| Method | Description | Implementation |
|--------|-------------|----------------|
| **Historical Scenario** | Replay past crises (2008, dot-com, COVID) | S&P data, custom |
| **Hypothetical Scenario** | Interest rate shock, oil spike, war | Manual parameterization |
| **Monte Carlo Simulation** | Random scenario generation | `numpy`, `QuantLib` |
| **Factor Push** | Shock orthogonal factor exposures | `statsmodels`, PCA |
| **Inverse Stress Testing** | Find scenario that causes target loss | Optimization |
| **Sensitivity Analysis** | Delta-normal, gamma effects | Greeks |
| **Coherent Risk Measures** | CVaR, spectral risk | `Riskfolio-Lib` |
| **Extreme Value Theory** | Tail risk modeling | `pyextremes`, `scipy.stats` |
| **Copula Models** | Joint tail dependency | `copulae`, `pycopula` |
| **Bayesian Stress Testing** | Posterior scenario probability | `PyMC`, `pymc3` |
| **Entropy Pooling** | Views + stress scenario integration | `fortitudo.tech` |
| **Factor Model Stress** | Macro factor shock propagation | `riskful`, custom |

### 8.4 Key Stress Testing Papers
- [ArXiv 2409.18970: Portfolio Stress Testing and VaR Incorporating Current Market Conditions](https://arxiv.org/abs/2409.18970)
- Basel Committee — Stress Testing Principles (2018)
- IMF — Stress Testing: Principles and Practice
- Adrian & Brunnermeier (2016) — CoVaR
- Brownlees & Engle (2017) — SRISK
- Acharya et al. (2017) — Systemic Risk Measures

---

## 9. Execution Algorithms

### 9.1 Algorithm Categories
| Algorithm | Description | Use Case |
|-----------|-------------|----------|
| **TWAP** (Time-Weighted Avg Price) | Equal time slices | Small orders, low urgency |
| **VWAP** (Volume-Weighted Avg Price) | Proportional to volume profile | Benchmark tracking |
| **Implementation Shortfall (IS)** | Minimize cost + risk (Almgren-Chriss) | Large orders, time-sensitive |
| **Percentage of Volume (POV)** | Maintain % of volume participation | Stealth execution |
| **Iceberg / Stealth** | Expose only part of order size | Large size, minimize signaling |
| **Adaptive / Dynamic** | Adjust based on real-time conditions | Variable market regimes |
| **Liquidity Seeking** | Go to dark pools, lit markets, midpoint | Reduce impact |
| **Sniper** | React to liquidity events | Opportunistic |
| **Dark Pool** | Non-displayed liquidity only | Maximum stealth |
| **Smart Order Router (SOR)** | Route across venues optimally | Fragmented markets |

### 9.2 Mathematical Models
| Model | Core Idea | Key Reference |
|-------|-----------|---------------|
| **Almgren-Chriss (2001)** | Linear impact, objective: cost + λ·risk | Foundational optimal execution |
| **Gatheral (2010)** | Non-linear impact, no-arbitrage | Volume clock models |
| **Obizhaeva & Wang (2013)** | Limit order book dynamics | Shape of order book |
| **Bayraktar & Ludkovski (2014)** | Optimal liquidation under uncertainty | Sequential liquidation |
| **Cartea et al. (2015)** | Market making + execution | Algorithmic and High-Frequency Trading |
| **Cont et al. (2014)** | Square-root impact model | Empirical impact function |
| **Donier et al. (2015)** | Propagator models | Full LOB simulation |

### 9.3 Execution Analytics
| Metric | Formula | Description |
|--------|---------|-------------|
| **Implementation Shortfall** | `IS = (P_decision - P_execution) × Q` | Total cost vs. paper |
| **Market Impact** | `I = (P_before - P_after) / P_before` | Price impact of trade |
| **Timing Risk** | `σ_exe = σ × √(T/bars)` | Price risk during execution |
| **Liquidity Cost** | Spread paid + depth consumed | Direct cost component |
| **Opportunity Cost** | Unfilled quantity × price move | Missed trade cost |
| **Slippage** | `(P_exec - P_mid) / P_mid` | Average execution price vs. mid |
| **Arrival Price** | Market price when order starts | Decision price benchmark |
| **VWAP vs. Market VWAP** | Difference from benchmark | Performance metric |
| **Participation Rate** | `Q_executed / Market_volume` | Stealth metric |

### 9.4 Execution Libraries & Tools
| Library | Language | Features |
|---------|----------|----------|
| `almgren-chriss` (PyPI) | Python | AC model calculator |
| `Almgren-Chriss-Execution-Model` (GitHub) | Python | Full implementation + dashboard |
| `wilfrid-art/almgren-chriss` (GitHub) | Python | MC IS simulation + PyQt6 dashboard |
| `quantconnect/Lean` | C#/Python | Built-in execution models |
| `bt` (Backtesting with Exec) | Python | Execution-aware backtesting |
| `nautilus_trader` | Python | High-performance algo trading framework |
| `crypto-crawler` | Python | Cryptocurrency market data |
| `QuantLib` | C++/Python | Derivatives execution analytics |
| `freqtrade` | Python | Crypto trading bot with execution |
| `hummingbot` | Python | Market making + execution |

### 9.5 Key Execution References
- [SignalPilot: Execution Algorithms TWAP, VWAP, POV, IS](https://education.signalpilot.io/curriculum/advanced/70-execution-algorithms-twap-vwap.html)
- [Execution Algorithms: TWAP, VWAP & Market Impact (Brenndoerfer)](https://mbrenndoerfer.com/writing/execution-algorithms-optimal-trading-strategies)
- [OpenAlgo: Execution Algorithms](https://openalgo.in/quant/execution-algorithms)
- [Almgren-Chriss Optimal Execution Calculator](https://metricgate.com/docs/almgren-chriss-execution/)
- [Deep Dive into IS: Almgren-Chriss Framework (Anboto Labs)](https://medium.com/@anboto_labs/deep-dive-into-is-the-almgren-chriss-framework-be45a1bde831)
- [ArXiv 2601.22113: Diverse Approaches to Optimal Execution](https://arxiv.org/pdf/2601.22113v1)
- [MQL5: Advanced Order Execution (TWAP, VWAP, Iceberg)](https://www.mql5.com/en/articles/17934)

---

## 10. Portfolio Optimization Methods

### 10.1 Optimization Approaches
| Method | Description | Risk Measure | Libraries |
|--------|-------------|-------------|-----------|
| **Mean-Variance (Markowitz)** | Classic: min σ² for target return | Variance | `PyPortfolioOpt`, `scipy` |
| **Mean-CVaR** | Minimize CVaR for target return | CVaR/ES | `Riskfolio-Lib`, `cvxpy` |
| **Mean-Max Drawdown** | Minimize max drawdown | Max DD | `Riskfolio-Lib` |
| **Risk Parity (Equal Risk)** | Equal risk contribution from each asset | Risk budget | `Riskfolio-Lib`, `riskparity.py` |
| **Hierarchical Risk Parity (HRP)** | Tree + clustering + inverse-variance | Variance/Cluster | `PyPortfolioOpt`, `Riskfolio-Lib` |
| **Hierarchical Equal Risk Contribution (HERC)** | HRP + equal risk per cluster | 32 risk measures | `Riskfolio-Lib` |
| **Nested Clustered Optimization (NCO)** | Lopez de Prado — de-noise + cluster | Multiple | `PyPortfolioOpt` |
| **Black-Litterman** | Equilibrium + views combined | Variance | `PyPortfolioOpt.black_litterman` |
| **Augmented Black-Litterman** | BL with multiple view types | CVaR/Variance | `Riskfolio-Lib` |
| **Entropy Pooling** | Views + stress scenarios | CVaR | `fortitudo.tech` |
| **Minimum Variance** | Simplest: min σ² (no return target) | Variance | `PyPortfolioOpt` |
| **Maximum Sharpe** | Max risk-adjusted return | Variance | `PyPortfolioOpt` |
| **Maximum Diversification** | Max DR = w'σ/√(w'Σw) | Diversification | `Riskfolio-Lib` |
| **Equal Weight (1/N)** | Bench, robust out-of-sample | None | `pandas` |
| **Most-Diversified Portfolio (MDP)** | Max diversification ratio | Diversification Ratio | `Riskfolio-Lib` |
| **Maximum Decorrelation** | Min correlation | Correlation | `Riskfolio-Lib` |
| **Robust Optimization** | Uncertainty set for parameters | Various | `cvxpy` |
| **Kelly Optimal** | Maximum growth rate | Full distribution | `pyportfolioopt` |
| **Risk Budgeting** | Custom risk allocation | Risk contribution | `Riskfolio-Lib` |

### 10.2 Portfolio Optimization Libraries
| Library | Metrics | Features |
|---------|---------|----------|
| **PyPortfolioOpt** | Variance, CVaR | MVO, Black-Litterman, HRP, shrinkage, HRP |
| **Riskfolio-Lib** | **32 risk measures** | CVaR, CDaR, Tail Gini, EVT, HERC, NCO, BL, EP |
| **skfolio** | Mean-variance, CVaR | sklearn-compatible, GridSearchCV, cross-validation |
| **fortitudo.tech** | CVaR, Entropy Pooling | Institutional-grade, views + stress |
| **QuantLib** | Pricing, risk | Derivatives portfolio optimization |
| **CVXOPT** | Convex optimization | MVO, risk parity, LPs for CVaR |
| **CVXPY** | Convex optimization | Custom objectives + constraints |
| **scipy.optimize** | General optimization | Legacy MVO implementation |
| **riskparity.py** | Risk parity | Fast risk parity optimization |
| **PyPortfolio.MT** | MPT methods | Historical simulation |

### 10.3 Risk Measures (Riskfolio-Lib supports all 32)
```
Variance, Standard Deviation, Semi-Standard Deviation, Mean Absolute Deviation,
Gini Mean Difference, Value at Risk (VaR), Conditional VaR (CVaR/Expected Shortfall),
Tail Gini, Entropic Risk Measure, Maximum Drawdown, Conditional Drawdown (CDaR),
Average Drawdown, Ulcer Index, Rel. VaR, Rel. CVaR, Rel. Max DD, Rel. CDaR,
Modified VaR, Modified CVaR, Worst Realization, Risk Parity, ERC, EVT-VaR, EVT-CVaR...
```

### 10.4 Academic References
| Paper | Contribution |
|-------|-------------|
| Markowitz (1952) — Portfolio Selection | Mean-variance foundation |
| Black & Litterman (1992) | Equilibrium + views |
| Lopez de Prado (2016) — HRP | ML-based hierarchical risk parity |
| Roncalli (2013) — Risk Parity | Budgeting framework |
| Meucci (2009) — Entropy Pooling | Views + stress integration |
| Michaud (1989) — Resampled Efficient Frontier | Monte Carlo MVO improvement |
| Kan & Zhou (2007) — Optimal Portfolio Choice | Estimation error |

---

## 11. Comprehensive Resource Lists

### 11.1 Awesome Quant (wilsonfreitas) — The Gold Standard
The single most comprehensive curated list of quant resources (1000+ entries):
- **URL:** [github.com/wilsonfreitas/awesome-quant](https://github.com/wilsonfreitas/awesome-quant)
- **Website:** [wilsonfreitas.github.io/awesome-quant/](https://wilsonfreitas.github.io/awesome-quant/)

**Categories covered:**
- Python libraries (100+ entries): QuantLib, FinRL, zipline, backtrader, PyPortfolioOpt
- R packages (50+): quantmod, PerformanceAnalytics, rugarch
- Julia packages (20+): JuliaQuant, Miletus
- MATLAB (30+): FinTS, Econometrics Toolbox
- C++ (20+): QuantLib, KDB+
- Java (15+): JQuantLib, Strata
- JavaScript (10+): finance.js
- Go (10+): quantgo
- Rust (10+): quantmath
- Free data sources: FRED, Yahoo, Quandl (historical)
- Blogs: QuantStart, Quantivity, Robot Wealth
- Podcasts: Quantocracy, FT Alphachat
- Books: 200+ quant finance books
- Education: CQF, MFE programs
- Jobs: Quant forums, mailing lists
- Conferences: QuantCon, QWAFAFEW

### 11.2 Awesome Systematic Trading (paperswithbacktest)
- **URL:** [github.com/paperswithbacktest/awesome-systematic-trading](https://github.com/paperswithbacktest/awesome-systematic-trading)
- Focus: Systematic trading + academic papers with backtests
- Covers: Backtesting, portfolio optimization, risk management, ML

### 11.3 Awesome Quant AI (leoncuhk)
- **URL:** [github.com/leoncuhk/awesome-quant-ai](https://github.com/leoncuhk/awesome-quant-ai)
- Focus: AI/ML in quantitative finance
- Covers: DL, RL, NLP, alternative data, sentiment

### 11.4 Awesome Trading Agents (LLMQuant)
- **URL:** [github.com/LLMQuant/awesome-trading-agents](https://github.com/LLMQuant/awesome-trading-agents)
- Focus: LLM-based trading agents
- Covers: Multi-agent systems, single agent, equity research copilots

### 11.5 Quantpedia — Strategy Encyclopedia
- **URL:** [quantpedia.com](https://quantpedia.com/)
- Over 600 academic trading strategies categorized
- Each with backtest summary, source paper, implementation notes
- Categories: Momentum, Value, Carry, Volatility, Seasonality, etc.

### 11.6 QuantStart — Education & Articles
- **URL:** [quantstart.com](https://www.quantstart.com/)
- 200+ articles on quant development
- Books: "Successful Algorithmic Trading", "Advanced Algorithmic Trading"
- Practical guides: Backtesting, data collection, broker integration

### 11.7 Key Blogs & Newsletters
| Blog | Focus | URL |
|------|-------|-----|
| **QuantStart** | Quant dev, strategies | quantstart.com |
| **Robot Wealth** | Systematic trading | robotwealth.com |
| **PyQuant News** | Python quant newsletter | pyquantnews.com |
| **Quantivity** | Quant finance blog | quantivity.wordpress.com |
| **Alpha Architect** | Factor investing | alphaarchitect.com |
| **Flirting with Models** | Systematic investing | blog.calmig.com |
| **Quantocracy** | Quant strategy aggregation | quantocracy.com |
| **Eran Raviv** | Quant finance analytics | eranraviv.com |
| **AQR Academic Papers** | Factor research | aqr.com/Insights |
| **MSCI Research** | Factor index insights | msci.com |
| **Brenndoerfer** | Quant systems architecture | mbrenndoerfer.com |
| **AltStreet** | Quant 2.0 infrastructure | altstreet.investments |
| **Viprasol** | Quant hedge fund engineering | viprasol.com |
| **OpenAlgo** | Free quant course | openalgo.in/quant |

---

## 12. Key GitHub Repositories

### 12.1 Backtesting & Trading Platforms
| Repository | Stars | Language | Description |
|------------|-------|----------|-------------|
| [QuantConnect/Lean](https://github.com/QuantConnect/Lean) | 9k+ | C# | Open-source algorithmic trading engine |
| [mementum/backtrader](https://github.com/mementum/backtrader) | 14k+ | Python | Feature-rich backtesting framework |
| [kernc/backtesting.py](https://github.com/kernc/backtesting.py) | 5k+ | Python | Lightweight backtesting |
| [quantopian/zipline](https://github.com/quantopian/zipline) | 17k+ | Python | Pythonic backtesting (archived) |
| [jesse-ai/jesse](https://github.com/jesse-ai/jesse) | 5k+ | Python | Crypto backtesting + live |
| [polakowo/vectorbt](https://github.com/polakowo/vectorbt) | 4k+ | Python | Vectorized backtesting |
| [nautechsystems/nautilus_trader](https://github.com/nautechsystems/nautilus_trader) | 2k+ | Python/Cython | High-performance algo trading |
| [gbeced/pyalgotrade](https://github.com/gbeced/pyalgotrade) | 4k+ | Python | Event-driven backtesting |
| [nickoala/robinhood](https://github.com/nickoala/robinhood) | 2k+ | Python | Robinhood trading |

### 12.2 Portfolio Optimization
| Repository | Stars | Description |
|------------|-------|-------------|
| [PyPortfolio/PyPortfolioOpt](https://github.com/PyPortfolio/PyPortfolioOpt) | 5k+ | MVO, Black-Litterman, HRP |
| [dcajasn/Riskfolio-Lib](https://github.com/dcajasn/Riskfolio-Lib) | 3k+ | 32 risk measures, portfolio optimization |
| [skfolio/skfolio](https://github.com/skfolio) | 1k+ | sklearn-compatible portfolio |
| [robertmartin8/MachineLearningStocks](https://github.com/robertmartin8/MachineLearningStocks) | 1k+ | ML for stock selection |

### 12.3 RL / ML for Finance
| Repository | Stars | Description |
|------------|-------|-------------|
| [AI4Finance-Foundation/FinRL](https://github.com/AI4Finance-Foundation/FinRL) | 17k+ | Financial RL library |
| [AI4Finance-Foundation/FinRobot](https://github.com/AI4Finance-Foundation/FinRobot) | 3k+ | AI agent platform for finance |
| [AI4Finance-Foundation/FinGPT](https://github.com/AI4Finance-Foundation/FinGPT) | 10k+ | Financial LLM |
| [huseinzol05/Stock-Prediction-Models](https://github.com/huseinzol05/Stock-Prediction-Models) | 7k+ | Collection of models |
| [borisbanushev/stockpredictionai](https://github.com/borisbanushev/stockpredictionai) | 3k+ | Stock prediction with DL |
| [AminHP/Gym-AnyTrading](https://github.com/AminHP/Gym-AnyTrading) | 2k+ | OpenAI Gym for trading |

### 12.4 Technical Indicators
| Repository | Stars | Description |
|------------|-------|-------------|
| [bukosabino/ta](https://github.com/bukosabino/ta) | 4k+ | Technical analysis library |
| [peerchemist/finta](https://github.com/peerchemist/finta) | 2k+ | Financial technical indicators |
| [twopirllc/pandas-ta](https://github.com/twopirllc/pandas-ta) | 5k+ | Pandas-based technical analysis |
| [mrjbq7/ta-lib](https://github.com/mrjbq7/ta-lib) | 10k+ | TA-Lib Python wrapper |
| [QuantConnect/python-indicators](https://github.com/QuantConnect/python-indicators) | 500+ | QC indicator library |

### 12.5 Risk & Performance Analytics
| Repository | Stars | Description |
|------------|-------|-------------|
| [quantopian/pyfolio](https://github.com/quantopian/pyfolio) | 5k+ | Portfolio + risk analytics |
| [quantopian/empyrical](https://github.com/quantopian/empyrical) | 1k+ | Risk metrics |
| [ranaroussi/quantstats](https://github.com/ranaroussi/quantstats) | 5k+ | Portfolio analytics library |
| [pmorissette/ffn](https://github.com/pmorissette/ffn) | 2k+ | Financial function library |

### 12.6 Data Libraries
| Repository | Stars | Description |
|------------|-------|-------------|
| [ranaroussi/yfinance](https://github.com/ranaroussi/yfinance) | 15k+ | Yahoo Finance downloader |
| [pydata/pandas-datareader](https://github.com/pydata/pandas-datareader) | 2k+ | Multiple data sources |
| [ccxt/ccxt](https://github.com/ccxt/ccxt) | 33k+ | Unified crypto exchange API |
| [RomanMichaelPaolucci/FinData](https://github.com/RomanMichaelPaolucci/FinData) | 500+ | Financial data aggregator |
| [JerBouma/FinanceDatabase](https://github.com/JerBouma/FinanceDatabase) | 3k+ | Database of securities |

### 12.7 Options & Derivatives
| Repository | Stars | Description |
|------------|-------|-------------|
| [vollib/vollib](https://github.com/vollib/vollib) | 600+ | Options pricing + greeks |
| [py-options/py_vollib](https://github.com/py-options) | — | Pure Python Black-Scholes |
| [domokane/FinancePy](https://github.com/domokane/FinancePy) | 2k+ | Finance derivatives pricing |
| [terraquant/swigquant](https://github.com/terraquant/swigquant) | — | QuantLib Python wrapper |

### 12.8 Time Series / Volatility
| Repository | Stars | Description |
|------------|-------|-------------|
| [bashtage/arch](https://github.com/bashtage/arch) | 1k+ | ARCH/GARCH models |
| [facebook/prophet](https://github.com/facebook/prophet) | 18k+ | Time series forecasting |
| [jdemaeyer/traces](https://github.com/jdemaeyer/traces) | — | Time series operations |
| [alan-turing-institute/sktime](https://github.com/alan-turing-institute/sktime) | 8k+ | ML for time series |

### 12.9 Execution / Market Microstructure
| Repository | Description |
|------------|-------------|
| [Wilfrid-art/almgren-chriss-optimal-execution](https://github.com/Wilfrid-art/almgren-chriss-optimal-execution) | Full AC model + PyQt6 |
| [alexanderdz05/Almgren-Chriss-Execution-Model](https://github.com/alexanderdz05/Almgren-Chriss-Execution-Model) | AC implementation |
| [QuantConnect/Lean](https://github.com/QuantConnect/Lean) | Built-in execution models |
| [nautechsystems/nautilus_trader](https://github.com/nautechsystems/nautilus_trader) | Execution infrastructure |
| [hft-research/limit-order-book](https://github.com/hft-research/limit-order-book) | LOB simulation |

### 12.10 Aggregated Resource Repos
| Repository | Description |
|------------|-------------|
| [wilsonfreitas/awesome-quant](https://github.com/wilsonfreitas/awesome-quant) | 1000+ quant resources |
| [paperswithbacktest/awesome-systematic-trading](https://github.com/paperswithbacktest/awesome-systematic-trading) | Systematic trading resources |
| [leoncuhk/awesome-quant-ai](https://github.com/leoncuhk/awesome-quant-ai) | AI in quant finance |
| [LLMQuant/awesome-trading-agents](https://github.com/LLMQuant/awesome-trading-agents) | Trading agents list |
| [Ashutosh0x/QuantHedgeFund](https://github.com/Ashutosh0x/QuantHedgeFund) | Production quant system blueprint |

---

## 13. Academic Papers & ArXiv

### 13.1 Seminal Papers by Topic

**Portfolio Theory**
- Markowitz (1952) — Portfolio Selection, Journal of Finance
- Black & Litterman (1992) — Global Portfolio Optimization, FAJ
- Lopez de Prado (2016) — Building Diversified Portfolios that Outperform Out-of-Sample (HRP)

**Risk Management**
- Artzner et al. (1999) — Coherent Measures of Risk, Mathematical Finance
- JPMorgan (1996) — RiskMetrics Technical Document
- Basel Committee — FRTB (2016-2025)
- Adrian & Brunnermeier (2016) — CoVaR, AER
- Brownlees & Engle (2017) — SRISK

**Option Pricing**
- Black & Scholes (1973) — The Pricing of Options and Corporate Liabilities, JPE
- Merton (1973) — Theory of Rational Option Pricing, Bell JEMS
- Heston (1993) — A Closed-Form Solution for Options with Stochastic Volatility, RFS

**Execution**
- Almgren & Chriss (2001) — Optimal Execution of Portfolio Transactions
- Gatheral (2010) — No-Dynamic-Arbitrage and Market Impact
- Obizhaeva & Wang (2013) — Optimal Trading Strategy and Supply/Demand Dynamics

**Time Series / Volatility**
- Engle (1982) — Autoregressive Conditional Heteroscedasticity with Estimates of Variance of UK Inflation (ARCH)
- Bollerslev (1986) — Generalized Autoregressive Conditional Heteroscedasticity (GARCH)
- Hamilton (1989) — A New Approach to the Economic Analysis of Nonstationary Time Series (Regime-Switching)
- Taylor (1986) — Modelling Financial Time Series (Stochastic Volatility)

**Factor Models**
- Fama & French (1993) — Common Risk Factors in the Returns on Stocks and Bonds
- Carhart (1997) — On Persistence in Mutual Fund Performance (Momentum)
- Fama & French (2015) — A Five-Factor Asset Pricing Model

**Reinforcement Learning**
- Mnih et al. (2015) — Human-Level Control through Deep RL (DQN)
- Schulman et al. (2017) — Proximal Policy Optimization Algorithms (PPO)
- Haarnoja et al. (2018) — Soft Actor-Critic (SAC)

**AI + Finance**
- Yang et al. (2020) — FinRL: Deep RL for Stock Trading (NeurIPS)
- Yang et al. (2023) — FinGPT: Open-Source Financial LLMs
- Li et al. (2024) — FinRobot: AI Agent Platform for Financial Applications
- Yu et al. (2024) — FinMem: Performance-Enhanced LLM Trading Agent with Memory
- Yu et al. (2024) — FinCon: Multi-Agent Financial System

### 13.2 Recent ArXiv Papers (2024-2026)
| Paper | Date | Topic |
|-------|------|-------|
| 2408.10932 — Evolution of RL in Quant Finance Survey | Aug 2024 | RL survey (167 papers) |
| 2411.07585 — RL Framework for Quantitative Trading | Nov 2024 | Trading framework |
| 2409.18970 — Portfolio Stress Testing and VaR | Sep 2024 | Risk management |
| 2405.14767 — FinRobot: AI Agent for Finance | May 2024 | AI agents |
| 2605.19337 — Agentic Trading Survey | May 2026 | LLM agents in finance |
| 2510.04787 — TiMi: Rational Agentic Trading | Oct 2025 | LLM trading |
| 2601.22113 — Diverse Approaches to Optimal Execution | Jan 2026 | Execution optimization |
| 2310.17432 — TradingAgents: Multi-Agents LLM Framework | 2024 | Multi-agent trading |
| 2306.06031 — FinGPT: Financial Large Language Models | 2023 | Financial LLM |
| 2403.06156 — StockAgent: LLM Stock Trading | 2024 | Single agent trading |
| 2405.12223 — AlphaQuanter: Tool-Orchestrated Agentic RL | 2024 | Tool-based RL |
| 2208.10068 — Portfolio Management with RL | 2022 | DRL portfolios |
| 2106.00178 — RL in Finance Survey | 2021 | Comprehensive survey |
| 1912.09355 — Deep RL for Automated Trading | 2019 | Early DRL trading |

### 13.3 Important Journals & Venues
| Venue | Focus | Key Conferences |
|-------|-------|-----------------|
| **Journal of Finance** | General finance | AFA Meeting |
| **Journal of Financial Economics** | Asset pricing, corporate | JFE Conference |
| **Review of Financial Studies** | Theoretical finance | SFS Cavalcade |
| **Quantitative Finance** | Quant-specific | QF Conference |
| **Journal of Computational Finance** | Algorithms, Monte Carlo | — |
| **Journal of Portfolio Management** | Practitioner | PME Conference |
| **Journal of Financial Data Science** | ML in finance | — |
| **NeurIPS** | ML/RL | NeurIPS |
| **ICML** | ML | ICML |
| **ICLR** | Deep learning | ICLR |
| **AAAI** | AI | AAAI |
| **AAMAS** | Multi-agent systems | AAMAS |
| **ICAIF** (ACM) | AI in finance | ICAIF |
| **FinNLP** (workshop) | NLP in finance | NAACL/ACL |
| **RLDM** | RL + decision making | RLDM |

### 13.4 Educational Resources
| Resource | Type | Format |
|----------|------|--------|
| CQF (Certificate in Quantitative Finance) | Professional certification | Online |
| MFE (Master of Financial Engineering) | Graduate degree | Baruch, Columbia, Princeton, Berkeley |
| QuantNet | Community + rankings | quantnet.com |
| QuantStart "Successful Algorithmic Trading" | Book + course | quantstart.com |
| QuantInsti EPAT | Executive program | quantinsti.com |
| OpenAlgo Quantitative Trading Course | Free online course | openalgo.in/quant |
| Stanford CS229 / CS231n | ML/DL courses | YouTube, free |
| MIT 18.S096: Topics in Math with Finance | OCW | ocw.mit.edu |
| Coursera: Financial Markets (Yale/Robert Shiller) | MOOC | coursera.org |
| Coursera: ML for Trading (Google) | MOOC | coursera.org |
| Goldstein/Quantopian Lecture Series | Video lectures | YouTube |
| Lopez de Prado — Advances in Financial ML | Book | Amazon |
| Paul Wilmott — Quant Finance | Textbook series | wilmott.com |
| Hull — Options, Futures, and Other Derivatives | Textbook | Standard reference |
| Tsay — Analysis of Financial Time Series | Textbook | Wiley |
| Cartea, Jaimungal, Penalva — Algorithmic and High-Frequency Trading | Book | Cambridge |
| Gatheral — The Volatility Surface | Book | Wiley |
| Grinold & Kahn — Active Portfolio Management | Book | CFA curriculum |

---

## Quick-Reference Index

| Category | # Resources | Key URL |
|----------|-------------|---------|
| Hedge fund strategies | ~150 | HFR, Aurum, QuantStart |
| Math formulas | ~100 | PyPortfolioOpt docs, QuantLib |
| Free APIs | ~80 | yfinance, Alpha Vantage, CoinGecko |
| FinRL / RL trading | ~100 | github.com/AI4Finance-Foundation |
| Pipeline architecture | ~80 | viprasol.com, altstreet.investments |
| UI dashboards | ~60 | Dash, Streamlit, Gradio |
| AI agents | ~80 | awesome-trading-agents, TradingAgents |
| Stress testing | ~50 | OSRE, Riskfolio-Lib, pyfolio |
| Execution algos | ~60 | Almgren-Chriss, VWAP, TWAP |
| Portfolio optimization | ~80 | Riskfolio-Lib (32 risk measures), PyPortfolioOpt |
| Awesome lists | ~500+ | awesome-quant (1000+), awesome-systematic-trading |
| GitHub repos | ~70 | Listed above |
| Academic papers | ~100 | ArXiv, SSRN |
| Educational resources | ~50 | CQF, QuantStart, Coursera |

**Total indexed: 1000+ resources**

---

*End of Report — Quant Nanggroe AI Research, July 14, 2026*
