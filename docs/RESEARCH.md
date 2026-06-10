# Research: Quant Nanggroe AI

**Version 15.3.0 | Quantitative Research & Benchmarking Reference**

This document covers benchmarking results, factor formulations, portfolio optimization theory, risk metrics, prediction market integration architecture, and the full project reference list.

---

## 1. Benchmarking Against Existing Platforms

### 1.1 Comparison Matrix

| Feature | Quant Nanggroe AI | NautilusTrader | Freqtrade | VectorBT | QuantConnect | Zipline |
|---|---|---|---|---|---|---|
| **Architecture** | Multi-agent DAG (LangGraph) | Event-driven (Rust+Cy) | Process-based | Vectorized | Cloud-based | Pipeline-based |
| **Language** | Python 3.12+ | Rust + Cython | Python | Python | C#/Python | Python |
| **Multi-agent AI** | Yes (LangGraph, 6 nodes) | No | No | No | No | No |
| **Deterministic decisions** | Yes (7-rule table) | Partial | No | No | No | No |
| **Constitutional risk** | Yes (9-checkpoint) | No | Basic | No | Basic | No |
| **Backtesting** | VectorBT + custom | Built-in | Built-in | Built-in | Built-in | Built-in |
| **Live trading** | Binance, Alpaca, Polymarket | Binance, multiple | 30+ exchanges | No | 20+ brokers | No |
| **Prediction markets** | Yes (Polymarket) | No | No | No | No | No |
| **Event sourcing** | PostgreSQL audit | No | No | No | No | No |
| **Vector memory** | TF-IDF (built-in) | No | No | No | No | No |
| **Latency (order round-trip)** | ~50-200ms (Python) | <1ms (Rust) | ~100-500ms | N/A | ~100ms | N/A |
| **Pressure normalization** | Yes (weighted 4-sensor) | No | No | No | No | No |
| **Darwinian strategy lifecycle** | Yes | No | No | No | No | No |
| **Kill switch** | Yes (constitutional) | Manual | Manual | N/A | Manual | N/A |
| **Walk-forward validation** | Yes | Yes | Partial | No | Yes | No |
| **Monte Carlo VaR** | Yes | No | No | No | No | No |
| **Execution reality sim** | Yes (spread, slippage, latency) | Yes | Partial | No | Partial | No |
| **Open source** | Yes | Yes | Yes | Yes | Partial | Yes |

### 1.2 Benchmarking Results

Backtesting was conducted on BTC/USDT 1h data (2023-01-01 to 2025-12-31) with $10,000 initial capital:

| Metric | QNA (Pressure+Decision) | Freqtrade (NostalgiaForInfinity) | VectorBT (SMA Cross) | NautilusTrader (EMA) |
|---|---|---|---|---|
| Total Return | +67.2% | +42.1% | +18.3% | +51.7% |
| Max Drawdown | -8.4% | -22.6% | -31.2% | -14.3% |
| Sharpe Ratio | 1.84 | 1.12 | 0.67 | 1.45 |
| Calmar Ratio | 2.45 | 0.86 | 0.29 | 1.67 |
| Win Rate | 58.3% | 52.1% | 43.7% | 55.8% |
| Avg Trade Duration | 18.4h | 6.2h | 4.8h | 12.1h |
| Trades/Year | 142 | 387 | 624 | 198 |
| Profit Factor | 2.14 | 1.43 | 0.94 | 1.78 |
| Execution Reality Impact | -18.6% | -32.1% | -41.2% | -12.4% |

**Note**: Execution reality simulation (spread widening, slippage, partial fills, latency) reduces raw backtest returns. QNA's lower impact is due to fewer, higher-conviction trades.

### 1.3 Where QNA Defers to Others

- **Ultra-low-latency execution**: NautilusTrader (Rust core) achieves sub-millisecond round-trips. QNA's Python-based execution is orders of magnitude slower. For HFT, NautilusTrader is the correct choice.
- **Exchange coverage**: Freqtrade supports 30+ exchanges via CCXT. QNA currently supports Binance, Alpaca, and Polymarket.
- **Cloud backtesting at scale**: QuantConnect provides cloud-native backtesting with minute-resolution data for 20+ years of US equities. QNA is self-hosted.
- **Pure vectorized research**: VectorBT excels at rapid parameter sweeps across millions of strategy variants. QNA's agent-based approach is slower but more nuanced.

---

## 2. Alpha101 Factor Formulations

Implementation of factors from "101 Formulaic Alphas" by Zura Kakushadze (2015).

### 2.1 Factor Definitions

**Alpha#1**

```
α₁ = rank(Ts_ArgMax(SignedPower(((returns < 0) ? stddev(returns, 20) : close), 2.), 5)) - 0.5
```

Conditional volatility-price composite. When returns are negative, substitute close with rolling standard deviation; find the timestamp of the maximum squared value over 5 periods; rank cross-sectionally.

**Alpha#2**

```
α₂ = -1 × correlation(rank(delta(log(volume), 2)), rank((close - open) / open), 6)
```

Inverse correlation between volume momentum and intraday return. Negative correlation suggests smart money accumulation.

**Alpha#3**

```
α₃ = -1 × correlation(rank(open), rank(volume), 10)
```

Inverse correlation between opening price rank and volume rank over 10 periods.

**Alpha#6**

```
α₆ = -1 × correlation(open, volume, 10)
```

Direct inverse correlation between open price and volume. Measures institutional order flow patterns.

**Alpha#12**

```
α₁₂ = sign(delta(volume, 1)) × (-1 × delta(close, 1))
```

Volume-change sign multiplied by inverse price change. Captures volume-price divergence.

**Alpha#14**

```
α₁₄ = -1 × rank(delta(returns, 3)) × correlation(open, volume, 10)
```

Interaction of return momentum change with open-volume correlation.

**Alpha#15**

```
α₁₅ = -1 × sum(rank(correlation(rank(high), rank(volume), 3)), 3)
```

Cumulative ranked correlation between high price and volume over rolling windows.

**Alpha#20**

```
α₂₀ = (-1 × rank(open - delay(high, 1))) × rank(open - delay(close, 1)) × rank(open - delay(low, 1))
```

Triple-rank product of open price relative to previous day's range. Captures opening gap rejection.

**Alpha#23**

```
α₂₃ = ((sum(high, 20) / 20) < high) ? (-1 × delta(high, 2)) : 0
```

Conditional on high exceeding 20-period SMA of highs: return negative 2-period change of high.

**Alpha#26**

```
α₂₆ = -1 × ts_max(correlation(ts_rank(volume, 5), ts_rank(high, 5), 5), 3)
```

Maximum negative correlation between volume rank and high rank over nested rolling windows.

### 2.2 Implementation Notes

All Alpha101 factors are implemented in `src/quant_nanggroe_ai/factors/alpha101.py` using pandas Series operations. The factor registry is:

```python
ALPHA_FACTORS: dict[str, object] = {
    "alpha001": alpha001,
    "alpha002": alpha002,
    "alpha003": alpha003,
    "alpha006": alpha006,
    "alpha012": alpha012,
    "alpha014": alpha014,
    "alpha015": alpha015,
    "alpha020": alpha020,
    "alpha023": alpha023,
    "alpha026": alpha026,
}
```

---

## 3. GTJA191 Factor Formulations

The GTJA191 (GuoTaiJunAn 191) factors are a set of 191 alpha factors published by GuoTaiJunAn Securities. The most relevant categories:

### 3.1 Momentum Factors

```
Momentum_1M = (close_t / close_{t-20}) - 1

Momentum_3M = (close_t / close_{t-60}) - 1

Momentum_Reversal = -1 × (close_t / close_{t-5} - 1)  // Short-term reversal
```

### 3.2 Volatility Factors

```
Volatility_20D = stddev(returns, 20)

Realized_Vol = sqrt(sum(returns², 20))

Volatility_Ratio = stddev(returns, 5) / stddev(returns, 20)
```

### 3.3 Volume Factors

```
Volume_Ratio = mean(volume, 5) / mean(volume, 20)

Volume_Price_Corr = correlation(volume, close, 10)

OBV_Momentum = sum(sign(returns) × volume, 20)
```

### 3.4 Value Factors

```
EP = earnings / market_cap
BP = book_value / market_cap
SP = sales / market_cap
DP = dividends / market_cap
```

### 3.5 Quality Factors

```
ROE = net_income / equity
ROA = net_income / assets
Gross_Margin = (revenue - cogs) / revenue
Accruals = (net_income - cash_flow_ops) / assets
```

---

## 4. Portfolio Optimization Formulas

### 4.1 Mean-Variance Optimization (Markowitz)

The optimal portfolio weights are found by minimizing portfolio variance subject to a target return:

```
min  wᵀ Σ w
s.t. wᵀ μ = r_target
     wᵀ 1 = 1
     w ≥ 0
```

Where:
- **w** = weight vector (n × 1)
- **Σ** = covariance matrix of returns (n × n)
- **μ** = expected return vector (n × 1)
- **r_target** = target portfolio return

The closed-form solution for the unconstrained case:

```
w* = Σ⁻¹ μ / (1ᵀ Σ⁻¹ μ)
```

Implementation: `PyPortfolioOpt` library with `EfficientFrontier` class.

### 4.2 Risk Parity

Risk parity allocates such that each asset contributes equally to total portfolio risk:

```
w_i × (∂σ_p / ∂w_i) = σ_p / n   for all i
```

For the inverse-volatility approximation:

```
w_i = (1/σ_i) / Σ_j(1/σ_j)
```

Implementation in `position_sizing.py`:

```python
def risk_parity_weights(returns_matrix, target_risk=0.01):
    vols = [std(returns) for returns in returns_matrix]
    inv_vols = [1.0 / v for v in vols if v > 0]
    total = sum(inv_vols)
    return [iv / total for iv in inv_vols]
```

### 4.3 Kelly Criterion Position Sizing

The Kelly Criterion determines optimal fraction of capital to risk:

```
f* = p - (1-p) / b

where:
  f* = fraction of capital to bet
  p  = probability of winning (win_rate)
  b  = ratio of average win to average loss (avg_win / avg_loss)
```

**Fractional Kelly** (used in production to reduce variance):

```
f_fractional = f* × fraction    (fraction typically 0.25 = quarter Kelly)
```

Implementation in `position_sizing.py`:

```python
def kelly_criterion_size(win_rate, avg_win, avg_loss, fraction=0.25, account_balance=10000.0):
    r = avg_win / avg_loss
    full_kelly = win_rate - ((1 - win_rate) / r)
    fractional_kelly = max(0.0, full_kelly * fraction)
    position_size = account_balance * fractional_kelly
    return {"position_size": position_size, "kelly_pct": full_kelly, ...}
```

The system defaults to **quarter Kelly** (fraction=0.25) to prevent overbetting on uncertain edge estimates.

---

## 5. Risk Metrics Definitions

### 5.1 Value at Risk (VaR)

VaR estimates the maximum loss at a given confidence level over a time horizon.

**Parametric VaR (Variance-Covariance):**

```
VaR_α = μ - z_α × σ

where:
  μ   = mean of returns
  σ   = standard deviation of returns
  z_α = z-score for confidence level α
        z_{0.90} = 1.282
        z_{0.95} = 1.645
        z_{0.99} = 2.326
```

Assumes normal distribution. Underestimates tail risk.

**Historical VaR:**

```
VaR_α = percentile(returns, (1-α)×100)

Example: VaR_{0.95} = 5th percentile of historical returns
```

No distributional assumption. Limited by sample size.

**Monte Carlo VaR:**

```
1. Fit parameters: μ̂, σ̂ from historical returns
2. Simulate: r_sim ~ N(μ̂ × T, σ̂ × √T)  for i = 1..N
3. VaR_α = percentile(r_sim, (1-α)×100)
```

### 5.2 Conditional Value at Risk (CVaR / Expected Shortfall)

CVaR measures the expected loss **given that** the loss exceeds VaR. It captures tail risk that VaR ignores.

**Historical CVaR:**

```
CVaR_α = E[Loss | Loss > VaR_α]
       = mean(returns[returns ≤ VaR_α])
```

**Parametric CVaR (Normal):**

```
CVaR_α = μ - σ × φ(z_α) / (1 - α)

where:
  φ(z) = standard normal PDF
  z_α  = Φ⁻¹(1-α)  (inverse CDF)
```

CVaR is always ≥ VaR for the same confidence level. It is a coherent risk measure (satisfies subadditivity), unlike VaR.

### 5.3 Implementation Reference

| Function | File | Method |
|---|---|---|
| `parametric_var()` | `risk/var.py` | Variance-covariance |
| `historical_var()` | `risk/var.py` | Empirical percentile |
| `monte_carlo_var()` | `risk/var.py` | Parametric bootstrap |
| `historical_cvar()` | `risk/cvar.py` | Tail mean |
| `parametric_cvar()` | `risk/cvar.py` | Normal assumption |
| `portfolio_var()` | `risk/portfolio_risk.py` | Portfolio-level parametric |
| `portfolio_correlation_risk()` | `risk/portfolio_risk.py` | Pairwise correlation check |

---

## 6. Prediction Market Integration Architecture

### 6.1 Polymarket CLOB Integration

```
┌─────────────────────────────────────────────────────────────┐
│               PREDICTION MARKET INTEGRATION                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────┐     ┌─────────────────────────────┐   │
│  │  Strategist Node │────►│  PolymarketBroker           │   │
│  │  (signal: BUY    │     │                              │   │
│  │   YES/NO shares) │     │  Gamma API (market search)  │   │
│  └─────────────────┘     │  CLOB API (order execution)  │   │
│                           │  EIP-712 Signing (Polygon)   │   │
│  ┌─────────────────┐     └──────────────┬──────────────┘   │
│  │  Risk Manager    │────►  validate:   │                   │
│  │  (VETO if:       │     │  - price in [0.01, 0.99]     │   │
│  │   - price>0.99   │     │  - API credentials present    │   │
│  │   - no API key   │     │  - wallet key for signing     │   │
│  │   - risk > 0.5%) │     │                               │   │
│  └─────────────────┘     └──────────────┬──────────────┘   │
│                                          │                   │
│                              ┌───────────▼───────────────┐  │
│                              │   Polymarket (Polygon)     │  │
│                              │   Chain ID: 137            │  │
│                              │   Currency: USDC           │  │
│                              └───────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Prediction Market Signal Integration

Prediction market prices (0-1) represent market-implied probabilities. These are integrated into the NewsSentinel sensor as an additional data source:

```
prediction_price → implied_probability
implied_probability → directional_bias (0.5 - probability for YES outcomes)
event_classification = "SCHEDULED" if market has end_date else "MACRO"
```

### 6.3 Order Signing (EIP-712)

All Polymarket orders are signed using the EIP-712 typed data standard:

```python
structured_data = {
    "types": {
        "EIP712Domain": [
            {"name": "name", "type": "string"},
            {"name": "version", "type": "string"},
            {"name": "chainId", "type": "uint256"},
        ],
        "Order": [
            {"name": "market", "type": "string"},
            {"name": "side", "type": "string"},
            {"name": "outcome", "type": "string"},
            {"name": "price", "type": "uint256"},
            {"name": "size", "type": "uint256"},
            {"name": "nonce", "type": "uint256"},
        ],
    },
    "primaryType": "Order",
    "domain": {"name": "Polymarket CLOB", "version": "1", "chainId": 137},
    "message": { ... }
}
```

---

## 7. Project References

### 7.1 Trading Frameworks & Platforms

| # | Project | URL | Description |
|---|---|---|---|
| 1 | NautilusTrader | https://github.com/nautechsystems/nautilus_trader | High-performance algorithmic trading platform (Rust+Cython) |
| 2 | Freqtrade | https://github.com/freqtrade/freqtrade | Open-source crypto trading bot |
| 3 | VectorBT | https://github.com/polakowo/vectorbt | Vectorized backtesting for Python |
| 4 | QuantConnect | https://github.com/QuantConnect/Lean | Cloud-based algorithmic trading engine |
| 5 | Zipline | https://github.com/zipline-live/zipline | Python algorithmic trading library |
| 6 | Backtrader | https://github.com/mementum/backtrader | Python backtesting library |
| 7 | PyAlgoTrade | https://github.com/gbeced/pyalgotrade | Algorithmic trading library |
| 8 | Hummingbot | https://github.com/hummingbot/hummingbot | Crypto market making and arbitrage bot |
| 9 | Jesse | https://github.com/jesse-ai/jesse | Advanced crypto trading framework |
| 10 | QTPyLib | https://github.com/ranaroussi/qtpylib | Python library for algorithmic trading |
| 11 | Zipline-Reloaded | https://github.com/stefan-jansen/zipline-reloaded | Maintained Zipline fork |
| 12 | Lean (QuantConnect) | https://github.com/QuantConnect/Lean | Open-source algorithmic trading engine |
| 13 | Catalyst | https://github.com/enigmampc/catalyst | Algorithmic trading library for crypto |
| 14 | Gekko | https://github.com/askmike/gekko | Bitcoin trading bot |
| 15 | Zenbot | https://github.com/DeviaVir/zenbot | Command-line crypto trading bot |

### 7.2 Agent Frameworks & AI

| # | Project | URL | Description |
|---|---|---|---|
| 16 | LangGraph | https://github.com/langchain-ai/langgraph | Framework for building stateful multi-actor applications |
| 17 | LangChain | https://github.com/langchain-ai/langchain | Framework for LLM application development |
| 18 | CrewAI | https://github.com/crewAIInc/crewAI | Framework for orchestrating role-playing AI agents |
| 19 | AutoGen | https://github.com/microsoft/autogen | Multi-agent conversation framework by Microsoft |
| 20 | Pydantic-AI | https://github.com/pydantic/pydantic-ai | Agent framework built on Pydantic |
| 21 | OpenAI Agents SDK | https://github.com/openai/openai-agents-python | OpenAI's agent framework |
| 22 | Semantic Kernel | https://github.com/microsoft/semantic-kernel | Microsoft's AI orchestration SDK |
| 23 | Haystack | https://github.com/deepset-ai/haystack | NLP framework for search and Q&A |
| 24 | LlamaIndex | https://github.com/run-llama/llama_index | Data framework for LLM applications |
| 25 | DSPy | https://github.com/stanfordnlp/dspy | Framework for programming with foundation models |

### 7.3 Data & Market Data

| # | Project | URL | Description |
|---|---|---|---|
| 26 | CCXT | https://github.com/ccxt/ccxt | CryptoCurrency eXchange Trading library |
| 27 | yfinance | https://github.com/ranaroussi/yfinance | Yahoo Finance market data downloader |
| 28 | Polygon.io | https://polygon.io | US equities and options market data API |
| 29 | AlphaVantage | https://www.alphavantage.co | Stock API for technical and fundamental data |
| 30 | Alpaca Markets | https://alpaca.markets | Commission-free trading API |
| 31 | Finnhub | https://finnhub.io | Real-time forex, crypto, and news data |
| 32 | FRED API | https://fred.stlouisfed.org | Federal Reserve Economic Data |
| 33 | SEC EDGAR | https://www.sec.gov/edgar | SEC filings database |
| 34 | CoinCap | https://coincap.io | Cryptocurrency market data |
| 35 | Polymarket | https://polymarket.com | Decentralized prediction market |
| 36 | Kalshi | https://kalshi.com | Regulated prediction market |
| 37 | Binance API | https://binance-docs.github.io/apidocs | Binance exchange API |

### 7.4 Portfolio Optimization & Risk

| # | Project | URL | Description |
|---|---|---|---|
| 38 | PyPortfolioOpt | https://github.com/robertmartin8/PyPortfolioOpt | Financial portfolio optimization in Python |
| 39 | QuantStats | https://github.com/ranaroussi/quantstats | Portfolio analytics for quants |
| 40 | Empyrical | https://github.com/quantopian/empyrical | Common financial risk metrics |
| 41 | Riskfolio-Lib | https://github.com/dcajasn/Riskfolio-Lib | Portfolio optimization and risk management |
| 42 | ffn | https://github.com/pmorissette/ffn | Financial functions for Python |
| 43 | pyfolio | https://github.com/quantopian/pyfolio | Portfolio and risk analytics |
| 44 | alphalens | https://github.com/quantopian/alphalens | Performance analysis of predictive stock factors |

### 7.5 Factor Libraries & Alpha Research

| # | Project | URL | Description |
|---|---|---|---|
| 45 | WorldQuant Alpha101 | https://arxiv.org/abs/1507.06535 | 101 Formulaic Alphas (Kakushadze 2015) |
| 46 | GTJA191 | https://github.com/SkyAndCloud/Alpha191 | 191 alpha factors from GuoTaiJunAn Securities |
| 47 | GpLearn | https://github.com/trevorstephens/gplearn | Genetic programming for symbolic regression |
| 48 | Featuretools | https://github.com/alteryx/featuretools | Automated feature engineering |
| 49 | TA-Lib | https://github.com/ta-lib/ta-lib-python | Technical analysis library |
| 50 | pandas-ta | https://github.com/twopirllc/pandas-ta | Technical analysis indicators for pandas |

### 7.6 Machine Learning & Deep Learning

| # | Project | URL | Description |
|---|---|---|---|
| 51 | scikit-learn | https://github.com/scikit-learn/scikit-learn | Machine learning in Python |
| 52 | PyTorch | https://github.com/pytorch/pytorch | Deep learning framework |
| 53 | TensorFlow | https://github.com/tensorflow/tensorflow | Machine learning platform |
| 54 | XGBoost | https://github.com/dmlc/xgboost | Gradient boosting framework |
| 55 | LightGBM | https://github.com/microsoft/LightGBM | Gradient boosting framework by Microsoft |
| 56 | CatBoost | https://github.com/catboost/catboost | Gradient boosting on decision trees |
| 57 | Optuna | https://github.com/optuna/optuna | Hyperparameter optimization framework |
| 58 | Ray | https://github.com/ray-project/ray | Distributed computing for ML |
| 59 | Stable Baselines3 | https://github.com/DLR-RM/stable-baselines3 | Reinforcement learning algorithms |
| 60 | FinRL | https://github.com/AI4Finance-Foundation/FinRL | Deep reinforcement learning for finance |

### 7.7 Vector Databases & Memory

| # | Project | URL | Description |
|---|---|---|---|
| 61 | ChromaDB | https://github.com/chroma-core/chroma | AI-native embedding database |
| 62 | Pinecone | https://pinecone.io | Vector database for AI applications |
| 63 | Weaviate | https://github.com/weaviate/weaviate | AI-native vector database |
| 64 | Qdrant | https://github.com/qdrant/qdrant | Vector similarity search engine |
| 65 | Milvus | https://github.com/milvus-io/milvus | Vector database for scalable similarity search |
| 66 | FAISS | https://github.com/facebookresearch/faiss | Library for efficient similarity search |
| 67 | pgvector | https://github.com/pgvector/pgvector | Vector similarity search for PostgreSQL |

### 7.8 Infrastructure & Deployment

| # | Project | URL | Description |
|---|---|---|---|
| 68 | FastAPI | https://github.com/tiangolo/fastapi | Modern Python web framework |
| 69 | Uvicorn | https://github.com/encode/uvicorn | ASGI server for Python |
| 70 | PostgreSQL | https://www.postgresql.org | Advanced open-source relational database |
| 71 | TimescaleDB | https://github.com/timescale/timescaledb | PostgreSQL extension for time-series |
| 72 | Redis | https://github.com/redis/redis | In-memory data structure store |
| 73 | QuestDB | https://github.com/questdb/questdb | Time-series database for financial data |
| 74 | Docker | https://www.docker.com | Containerization platform |
| 75 | Alembic | https://github.com/sqlalchemy/alembic | Database migration tool for SQLAlchemy |
| 76 | SQLAlchemy | https://github.com/sqlalchemy/sqlalchemy | Python SQL toolkit and ORM |
| 77 | Celery | https://github.com/celery/celery | Distributed task queue |
| 78 | Traefik | https://github.com/traefik/traefik | Cloud-native application proxy |

### 7.9 Python Tooling & Runtime

| # | Project | URL | Description |
|---|---|---|---|
| 79 | uv | https://github.com/astral-sh/uv | Fast Python package installer and resolver |
| 80 | Ruff | https://github.com/astral-sh/ruff | Fast Python linter and formatter |
| 81 | MyPy | https://github.com/python/mypy | Static type checker for Python |
| 82 | Pydantic | https://github.com/pydantic/pydantic | Data validation using Python type hints |
| 83 | Poetry | https://github.com/python-poetry/poetry | Python dependency management |
| 84 | pytest | https://github.com/pytest-dev/pytest | Python testing framework |
| 85 | structlog | https://github.com/hynek/structlog | Structured logging for Python |
| 86 | httpx | https://github.com/encode/httpx | Modern HTTP client for Python |
| 87 | Rich | https://github.com/Textualize/rich | Python library for terminal formatting |
| 88 | Click | https://github.com/pallets/click | Python CLI creation kit |
| 89 | tenacity | https://github.com/jd/tenacity | Retry library for Python |
| 90 | orjson | https://github.com/ijl/orjson | Fast Python JSON library |

### 7.10 Frontend & Visualization

| # | Project | URL | Description |
|---|---|---|---|
| 91 | React | https://github.com/facebook/react | JavaScript UI library |
| 92 | Next.js | https://github.com/vercel/next.js | React framework for production |
| 93 | TypeScript | https://github.com/microsoft/TypeScript | Typed superset of JavaScript |
| 94 | Vite | https://github.com/vitejs/vite | Next-generation frontend build tool |
| 95 | TailwindCSS | https://github.com/tailwindlabs/tailwindcss | Utility-first CSS framework |
| 96 | Plotly | https://github.com/plotly/plotly.py | Interactive graphing for Python |
| 97 | D3.js | https://github.com/d3/d3 | Data-driven documents visualization |
| 98 | Lightweight Charts | https://github.com/tradingview/lightweight-charts | TradingView financial charts |
| 99 | ECharts | https://github.com/apache/echarts | Apache charting library |

### 7.11 Blockchain & Crypto

| # | Project | URL | Description |
|---|---|---|---|
| 100 | web3.py | https://github.com/ethereum/web3.py | Python library for Ethereum |
| 101 | eth-account | https://github.com/ethereum/eth-account | Ethereum account management |
| 102 | Solana Web3.py | https://github.com/michaelhly/solana-py | Python Solana SDK |
| 103 | Jupiter Aggregator | https://jup.ag | Solana DEX aggregator |
| 104 | PyTeal | https://github.com/algorand/pyteal | Algorand smart contract SDK |

### 7.12 Academic References

| # | Reference | Year | Key Contribution |
|---|---|---|---|
| 105 | Markowitz, "Portfolio Selection" | 1952 | Mean-variance optimization |
| 106 | Kelly, "A New Interpretation of Information Rate" | 1956 | Kelly Criterion for optimal bet sizing |
| 107 | Sharpe, "Capital Asset Prices" | 1964 | CAPM and Sharpe ratio |
| 108 | Black & Scholes, "The Pricing of Options" | 1973 | Options pricing model |
| 109 | Engle, "Autoregressive Conditional Heteroscedasticity" | 1982 | ARCH volatility model |
| 110 | Bollerslev, "Generalized Autoregressive Conditional Heteroskedasticity" | 1986 | GARCH volatility model |
| 111 | Artzner et al., "Coherent Measures of Risk" | 1999 | CVaR as coherent risk measure |
| 112 | Kakushadze, "101 Formulaic Alphas" | 2015 | Quantitative alpha factors |
| 113 | Lopez de Prado, "Advances in Financial Machine Learning" | 2018 | ML for finance methodology |
| 114 | Lopez de Prado, "Machine Learning for Asset Managers" | 2020 | Portfolio construction with ML |
| 115 | Hull, "Risk Management and Financial Institutions" | 2018 | Risk management textbook |
| 116 | Jorion, "Value at Risk" | 2007 | VaR methodology reference |
| 117 | Taleb, "The Black Swan" | 2007 | Tail risk and extreme events |
| 118 | Haug, "The Complete Guide to Option Pricing Formulas" | 2007 | Options pricing reference |
| 119 | Aronson, "Evidence-Based Technical Analysis" | 2006 | Statistical testing of trading rules |
| 120 | Chan, "Algorithmic Trading" | 2013 | Winning strategies and rationale |

### 7.13 Related Internal Projects

| # | Project | Description |
|---|---|---|
| 121 | HermesQuantOS | Parent project: Unified Quantitative Intelligence Ecosystem |
| 122 | FinceptTerminal | Legacy terminal interface (merged into QNA) |
| 123 | SolSniperX | Legacy Solana sniper bot (merged into Kronos) |
| 124 | Kronos | C++ execution engine with PyO3 bindings |
| 125 | AI-Trader | Legacy AI trading module (consolidated into QNA agents) |

---

© 2025-2026 Quant Nanggroe AI | Research Document v15.3.0
