# Quant Nanggroe AI — Research Benchmark

**Version 4.0.0 | Comprehensive Survey of 100+ Projects**

> This document benchmarks Quant Nanggroe AI against the broader ecosystem of trading frameworks, agent frameworks, quant libraries, risk libraries, and data providers. For each project we assess its relevance, how we compare, and what we adopt.

---

## Table of Contents

1. [Trading Frameworks](#1-trading-frameworks)
2. [Agent Frameworks](#2-agent-frameworks)
3. [Quant Libraries](#3-quant-libraries)
4. [Risk Libraries](#4-risk-libraries)
5. [Data Providers & APIs](#5-data-providers--apis)
6. [Exchange Libraries](#6-exchange-libraries)
7. [Backtesting Frameworks](#7-backtesting-frameworks)
8. [AI/ML for Finance](#8-aiml-for-finance)
9. [Comparison Matrix](#9-comparison-matrix)
10. [Adoption Summary](#10-adoption-summary)

---

## 1. Trading Frameworks

### 1.1 Freqtrade

| Attribute | Details |
|---|---|
| **Name** | Freqtrade |
| **URL** | https://github.com/freqtrade/freqtrade |
| **Language** | Python |
| **License** | GPL v3 |
| **Stars** | 28k+ |
| **Description** | Open-source crypto trading bot with strategy backtesting, paper trading, and live trading via exchange APIs |

**Features:**
- Strategy writing in Python with pandas/numpy
- Backtesting engine with detailed metrics
- Edge positioning for position sizing
- Dry-run (paper trading) mode
- Telegram/Web UI for monitoring
- Support for multiple exchanges via CCXT

**How We Compare:**
- ✅ We support 10 exchanges vs Freqtrade's ~15 (similar CCXT backbone)
- ✅ We have 469+ alpha factors vs Freqtrade's user-written strategies
- ✅ We have 11 AI agents vs Freqtrade's single-strategy approach
- ✅ We have constitutional risk limits vs Freqtrade's configurable stop-loss
- ❌ Freqtrade has a more mature live trading loop
- ❌ Freqtrade has better community strategy sharing

**What We Adopt:**
- CCXT as the exchange abstraction layer (already adopted)
- Edge positioning concept → our Kelly Criterion implementation
- Dry-run / paper trading mode (already implemented as PaperBroker)

---

### 1.2 NautilusTrader

| Attribute | Details |
|---|---|
| **Name** | NautilusTrader |
| **URL** | https://github.com/nautechsystems/nautilus_trader |
| **Language** | Rust + Python |
| **License** | LGPL v3 |
| **Stars** | 3k+ |
| **Description** | High-performance algorithmic trading platform built with Rust core and Python interface, designed for backtesting and live trading |

**Features:**
- Rust core for nanosecond-level performance
- Event-driven architecture
- Full order book simulation
- Multiple venue support
- Professional-grade backtesting

**How We Compare:**
- ✅ We have richer factor library (469 vs NautilusTrader's built-in indicators)
- ✅ We have multi-agent AI decision making (NautilusTrader is rule-based)
- ❌ NautilusTrader is orders of magnitude faster (Rust core)
- ❌ NautilusTrader has deeper order book simulation

**What We Adopt:**
- Event-driven architecture concept (adapted for LangGraph nodes)
- Venue abstraction pattern → our ExchangeFactory
- Professional-grade backtesting validation principles

---

### 1.3 Backtrader

| Attribute | Details |
|---|---|
| **Name** | Backtrader |
| **URL** | https://github.com/mementum/backtrader |
| **Language** | Python |
| **License** | MIT |
| **Stars** | 14k+ |
| **Description** | Python backtesting library for trading strategies with live trading support |

**Features:**
- Cerebro engine for strategy orchestration
- Indicator framework with built-in ta-lib integration
- Broker simulation with commission modeling
- Analyzer framework for metrics
- Plotting capabilities

**How We Compare:**
- ✅ We have AI-driven strategy generation vs Backtrader's manual strategies
- ✅ We have multi-asset support vs Backtrader's primarily equity focus
- ✅ We have production risk management vs Backtrader's basic stops
- ❌ Backtrader has a simpler, more intuitive API for strategy development
- ❌ Backtrader has extensive community indicators

**What We Adopt:**
- Cerebro-style orchestration → our TradingGraphV2
- Indicator framework concept → our FactorRegistry
- Analyzer pattern → our backtest metrics module

---

### 1.4 QuantConnect

| Attribute | Details |
|---|---|
| **Name** | QuantConnect |
| **URL** | https://www.quantconnect.com/ |
| **Language** | Python, C# |
| **License** | Commercial (LEAN engine is Apache 2.0) |
| **Description** | Cloud-based algorithmic trading platform with LEAN open-source engine |

**Features:**
- LEAN engine (open-source)
- Cloud backtesting with institutional data
- Multi-asset support (equity, forex, crypto, futures, options)
- Alpha streams marketplace
- Live trading with multiple brokerages

**How We Compare:**
- ✅ We have AI agent decision-making (QuantConnect is code-based)
- ✅ We have constitutional risk limits (QuantConnect relies on user code)
- ✅ We are fully open-source and self-hosted
- ❌ QuantConnect has institutional-grade data feeds
- ❌ QuantConnect has options and futures support
- ❌ QuantConnect has alpha streams marketplace

**What We Adopt:**
- Multi-asset universe concept → our multi-path routing
- Algorithm framework pattern → our strategy lifecycle
- Data feed normalization → our AutoSwitch engine

---

### 1.5 Zipline

| Attribute | Details |
|---|---|
| **Name** | Zipline |
| **URL** | https://github.com/quantopian/zipline |
| **Language** | Python |
| **License** | Apache 2.0 |
| **Stars** | 17k+ |
| **Description** | Quantopian's backtesting engine, now community-maintained |

**Features:**
- Event-driven backtesting
- Pipeline API for factor computation
- Bundles for data ingestion
- Slippage and commission models
- Integration with Pyfolio for analytics

**How We Compare:**
- ✅ We have AI-driven decisions vs Zipline's code-driven
- ✅ We have live trading support (Zipline is backtesting-only)
- ✅ We support crypto and forex (Zipline is equity-focused)
- ❌ Zipline's Pipeline API is more sophisticated for factor computation
- ❌ Zipline has better data bundle management

**What We Adopt:**
- Pipeline API concept → our FactorPipeline
- Bundle pattern → our data loaders
- Slippage/commission models → our execution simulation

---

### 1.6 Hummingbot

| Attribute | Details |
|---|---|
| **Name** | Hummingbot |
| **URL** | https://github.com/hummingbot/hummingbot |
| **Language** | Python |
| **License** | Apache 2.0 |
| **Stars** | 8k+ |
| **Description** | Open-source crypto market making and arbitrage bot |

**Features:**
- Market making strategies
- Arbitrage across exchanges
- Liquidity mining
- Connector framework for exchanges
- Dashboard and monitoring

**How We Compare:**
- ✅ We have broader asset class support (Hummingbot is crypto-only)
- ✅ We have AI-driven decisions (Hummingbot is rule-based)
- ❌ Hummingbot has more sophisticated market-making strategies
- ❌ Hummingbot has better exchange connector coverage

**What We Adopt:**
- Connector framework pattern → our ExchangeFactory
- Market making strategy concepts (future: market-making agent)
- Dashboard monitoring approach → our WebSocket API

---

### 1.7 Jesse

| Attribute | Details |
|---|---|
| **Name** | Jesse |
| **URL** | https://github.com/jesse-ai/jesse |
| **Language** | Python |
| **License** | MIT |
| **Stars** | 6k+ |
| **Description** | Advanced crypto trading bot focused on clean code and research |

**Features:**
- Clean strategy API
- Detailed backtesting reports
- Drive mode for research (Jupyter integration)
- Multiple exchange support
- Optimizer for parameter tuning

**How We Compare:**
- ✅ We have multi-agent AI (Jesse is single-strategy)
- ✅ We support forex and equities (Jesse is crypto-only)
- ✅ We have 469+ factors (Jesse has basic indicators)
- ❌ Jesse has cleaner strategy API for rapid prototyping
- ❌ Jesse has better parameter optimization

**What We Adopt:**
- Research mode concept → our Jupyter-compatible API
- Clean strategy interface pattern
- Optimization approach → our walk-forward analysis

---

### 1.8 VectorBT

| Attribute | Details |
|---|---|
| **Name** | VectorBT |
| **URL** | https://github.com/polakowo/vectorbt |
| **Language** | Python |
| **License** | MIT |
| **Stars** | 4k+ |
| **Description** | Vectorized backtesting library for ultra-fast strategy evaluation |

**Features:**
- NumPy-accelerated portfolio simulation
- Fully vectorized operations
- Millions of parameter combinations in seconds
- Flexible indicator and signal generation
- Interactive Jupyter widgets

**How We Compare:**
- ✅ We have production trading capability (VectorBT is backtesting-only)
- ✅ We have risk management (VectorBT has none)
- ✅ We have AI agents (VectorBT has no agent system)
- ❌ VectorBT is orders of magnitude faster for backtesting
- ❌ VectorBT has better parameter sweep capabilities

**What We Adopt:**
- Vectorized computation patterns for factor engine
- Portfolio simulation approach (adapted for our BacktestEngine)
- Performance optimization principles

---

### 1.9 Qlib

| Attribute | Details |
|---|---|
| **Name** | Microsoft Qlib |
| **URL** | https://github.com/microsoft/qlib |
| **Language** | Python |
| **License** | MIT |
| **Stars** | 16k+ |
| **Description** | AI-oriented quantitative investment platform by Microsoft Research |

**Features:**
- 158 built-in alpha factors (Qlib158)
- ML-based prediction models (LightGBM, LSTM, Transformer)
- Portfolio optimization
- Backtesting with market-neutral strategies
- Data server for Chinese and US markets

**How We Compare:**
- ✅ We have LangGraph agent architecture (Qlib is pipeline-based)
- ✅ We have constitutional risk limits (Qlib has basic risk)
- ✅ We have multi-exchange live trading (Qlib is research-focused)
- ❌ Qlib has more sophisticated ML models for prediction
- ❌ Qlib has better data infrastructure for Chinese markets
- ❌ Qlib's 158 factors are battle-tested at Microsoft

**What We Adopt:**
- **Qlib158 factors directly** (already in our factor registry)
- ML model patterns → our ensemble model module
- Data server concept → our AutoSwitch provider management
- Feature engineering pipeline → our FactorPipeline

---

### 1.10 TradingAgents (AI Trader)

| Attribute | Details |
|---|---|
| **Name** | TradingAgents (AI-Hedge-Fund) |
| **URL** | https://github.com/AI4Finance-Foundation/TradingAgents |
| **Language** | Python |
| **License** | MIT |
| **Description** | LLM-powered trading agents framework with multiple specialized agents |

**Features:**
- Multiple LLM agents (analyst, trader, risk manager)
- Bull/bear debate mechanism
- Signal aggregation
- Risk management via agent
- OpenAI integration

**How We Compare:**
- ✅ We have 11 agents vs TradingAgents' 4-5
- ✅ We have constitutional risk limits (TradingAgents relies on LLM judgment)
- ✅ We have multi-exchange execution (TradingAgents is analysis-only)
- ✅ We have 469+ factors (TradingAgents has none)
- ❌ TradingAgents has simpler setup
- ❌ TradingAgents pioneered the multi-agent debate concept

**What We Adopt:**
- **Bull/bear debate mechanism** (already adopted in CouncilDebate)
- **Risk debate (conservative/neutral/aggressive)** (adopted in RiskDebateState)
- **Stress testing scenarios** (adopted in RiskManager.stress_test())
- Agent role pattern (analyst, trader, risk)

---

## 2. Agent Frameworks

### 2.1 LangGraph

| Attribute | Details |
|---|---|
| **Name** | LangGraph |
| **URL** | https://github.com/langchain-ai/langgraph |
| **Language** | Python |
| **License** | MIT |
| **Description** | Framework for building stateful, multi-actor applications with LLMs |

**Features:**
- StateGraph for defining agent workflows
- Conditional edges for dynamic routing
- Checkpointing for state persistence
- Human-in-the-loop support
- Streaming execution
- Built on LangChain primitives

**How We Compare:**
- We USE LangGraph directly as our orchestration layer
- Our TradingGraphV2 is a LangGraph StateGraph
- Our conditional edges leverage LangGraph's routing system
- Our AgentState TypedDict is a LangGraph-compatible state

**What We Adopt:**
- **StateGraph as the core orchestration mechanism** (primary dependency)
- **Conditional edges** for risk routing, asset routing, human checkpoints
- **Streaming execution** for real-time updates
- **Human-in-the-loop** checkpoint pattern

---

### 2.2 CrewAI

| Attribute | Details |
|---|---|
| **Name** | CrewAI |
| **URL** | https://github.com/crewAIInc/crewAI |
| **Language** | Python |
| **License** | MIT |
| **Stars** | 20k+ |
| **Description** | Framework for orchestrating role-playing autonomous AI agents |

**Features:**
- Role-based agent definitions
- Task delegation and collaboration
- Sequential and hierarchical processes
- Tool integration
- Memory and context sharing

**How We Compare:**
- ✅ We use LangGraph (more flexible) vs CrewAI's role-play model
- ✅ We have domain-specific tools (trading, risk, exchange)
- ✅ We have constitutional limits (CrewAI has none)
- ❌ CrewAI has simpler agent definition (decorator-based)
- ❌ CrewAI has better agent collaboration patterns

**What We Adopt:**
- Role-based agent concept → our AgentRole enum
- Task delegation pattern → our graph node structure
- Memory sharing concept → our shared AgentState

---

### 2.3 AutoGen

| Attribute | Details |
|---|---|
| **Name** | Microsoft AutoGen |
| **URL** | https://github.com/microsoft/autogen |
| **Language** | Python |
| **License** | MIT |
| **Stars** | 40k+ |
| **Description** | Framework for building multi-agent conversations with LLMs |

**Features:**
- Multi-agent conversation patterns
- Human participation in agent loops
- Code execution sandbox
- Configurable agent behaviors
- Group chat management

**How We Compare:**
- ✅ We have deterministic graph execution (AutoGen is conversation-based)
- ✅ We have domain-specific risk limits
- ✅ We have production trading infrastructure
- ❌ AutoGen has more flexible conversation patterns
- ❌ AutoGen has better code execution capabilities

**What We Adopt:**
- Multi-agent conversation pattern → our council debate
- Human participation concept → our human checkpoints
- Group chat management → our council voting system

---

### 2.4 PydanticAI

| Attribute | Details |
|---|---|
| **Name** | PydanticAI |
| **URL** | https://github.com/pydantic/pydantic-ai |
| **Language** | Python |
| **License** | MIT |
| **Description** | Agent framework built on Pydantic for type-safe LLM applications |

**Features:**
- Pydantic model validation for agent inputs/outputs
- Type-safe dependency injection
- Structured response models
- Multiple model support (OpenAI, Gemini, etc.)

**How We Compare:**
- ✅ We also use Pydantic extensively for all data models
- ✅ We have more complex orchestration (LangGraph)
- ❌ PydanticAI has cleaner type-safe agent definitions

**What We Adopt:**
- **Pydantic BaseModel for all data models** (already adopted)
- Type-safe agent interface patterns
- Structured response validation

---

### 2.5 DSPy

| Attribute | Details |
|---|---|
| **Name** | DSPy |
| **URL** | https://github.com/stanfordnlp/dspy |
| **Language** | Python |
| **License** | MIT |
| **Stars** | 20k+ |
| **Description** | Framework for programming language models with declarative modules |

**Features:**
- Declarative module composition
- Automatic prompt optimization
- Metric-driven compilation
- Typed predictors

**How We Compare:**
- ✅ We have domain-specific structure (DSPy is general-purpose)
- ✅ We have production infrastructure
- ❌ DSPy has better prompt optimization
- ❌ DSPy has metric-driven compilation

**What We Adopt:**
- Typed predictor pattern → our Pydantic-validated agent outputs
- Metric-driven approach → our strategy lifecycle evaluation
- Module composition concept → our graph node composition

---

### 2.6 SmolAgents

| Attribute | Details |
|---|---|
| **Name** | HuggingFace SmolAgents |
| **URL** | https://github.com/huggingface/smolagents |
| **Language** | Python |
| **License** | Apache 2.0 |
| **Description** | Lightweight agent framework from HuggingFace |

**Features:**
- Minimal agent abstraction
- Tool-based agent actions
- Code generation agents
- Multi-step reasoning

**How We Compare:**
- ✅ We have richer domain-specific tools
- ✅ We have production risk management
- ❌ SmolAgents is simpler and more lightweight

**What We Adopt:**
- Tool-based agent pattern (already using LangChain tools)
- Minimal agent abstraction principles

---

## 3. Quant Libraries

### 3.1 Alpha101 (WorldQuant)

| Attribute | Details |
|---|---|
| **Name** | 101 Formulaic Alphas |
| **Source** | WorldQuant (Zura Kakushadze, 2016) |
| **URL** | https://arxiv.org/abs/1601.00991 |
| **Description** | 101 formulaic alpha factors for US equities |

**Our Implementation:** `quant_nanggroe/engine/factors/alpha101.py`

- All 101 factors implemented as function-based factors
- Each factor has `__alpha_meta_*` dict and `compute_*` function
- Registered in FactorRegistry under zoo="alpha101"
- Themes: momentum, reversal, volume, volatility

**What We Adopt:**
- **All 101 factors directly** (full implementation in our codebase)
- Function-based factor pattern with metadata dicts
- Panel-based computation interface (wide DataFrames)

---

### 3.2 GTJA191 (Guotai Junan)

| Attribute | Details |
|---|---|
| **Name** | GTJA 191 Alpha Factors |
| **Source** | Guotai Junan Securities |
| **Description** | 191 alpha factors developed for Chinese A-share market |

**Our Implementation:** `quant_nanggroe/engine/factors/gtja191.py`

- All 191 factors implemented
- Registered in FactorRegistry under zoo="gtja191"
- Applicable to both Chinese and global markets
- Themes: momentum, reversal, technical, fundamental

**What We Adopt:**
- **All 191 factors directly** (full implementation)
- Chinese market factor patterns
- Cross-sectional factor computation approach

---

### 3.3 Barra Risk Model (MSCI)

| Attribute | Details |
|---|---|
| **Name** | MSCI Barra Risk Model |
| **Source** | MSCI (formerly Barra) |
| **Description** | Industry-standard risk factor model for equity portfolio risk analysis |

**Our Implementation:** `quant_nanggroe/engine/factors/barra.py`

- Key Barra-style risk factors implemented
- Registered in FactorRegistry under zoo="barra"
- Style factors: value, momentum, size, volatility, liquidity
- Industry factors for sector exposure

**What We Adopt:**
- **Barra risk factor framework** (adapted for our factor registry)
- Style and industry factor decomposition
- Risk attribution methodology

---

### 3.4 Qlib158 (Microsoft)

| Attribute | Details |
|---|---|
| **Name** | Qlib 158 Alpha Features |
| **Source** | Microsoft Research Qlib |
| **Description** | 158 alpha features used in Qlib's ML-based prediction models |

**Our Implementation:** `quant_nanggroe/engine/factors/qlib158.py`

- All 158 factors implemented
- Registered in FactorRegistry under zoo="qlib158"
- Compatible with Qlib's data format
- Optimized for ML model feature engineering

**What We Adopt:**
- **All 158 factors directly** (full implementation)
- ML-oriented feature engineering patterns
- Data normalization and cross-sectional ranking

---

### 3.5 TA-Lib

| Attribute | Details |
|---|---|
| **Name** | TA-Lib |
| **URL** | https://github.com/ta-lib/ta-lib-python |
| **Language** | C + Python |
| **License** | BSD |
| **Description** | Technical analysis library with 150+ indicators |

**Our Implementation:** `quant_nanggroe/engine/factors/technical.py`

- Key technical indicators implemented in pure Python (no C dependency)
- Registered as class-based factors under zoo="technical"
- Includes: RSI, MACD, Bollinger, ATR, ADX, Stochastic, etc.

**What We Adopt:**
- Technical indicator computation patterns
- ATR for position sizing (core dependency)
- ADX for regime detection

---

## 4. Risk Libraries

### 4.1 PyPortfolioOpt

| Attribute | Details |
|---|---|
| **Name** | PyPortfolioOpt |
| **URL** | https://github.com/robertmartin8/PyPortfolioOpt |
| **Language** | Python |
| **License** | MIT |
| **Stars** | 4k+ |
| **Description** | Financial portfolio optimization library |

**Features:**
- Mean-variance optimization (Markowitz)
- Black-Litterman model
- Efficient frontier computation
- Risk parity optimization
- Hierarchical risk parity (HRP)

**How We Compare:**
- ✅ We have constitutional risk limits (PyPortfolioOpt has no risk limits)
- ✅ We have kill switch (PyPortfolioOpt has no circuit breaker)
- ✅ We have real-time risk monitoring
- ❌ PyPortfolioOpt has more sophisticated optimization algorithms
- ❌ PyPortfolioOpt has HRP which we don't have yet

**What We Adopt:**
- Mean-variance optimization → our mean_variance_optimizer
- Risk parity optimization → our risk_parity_optimizer
- Equal volatility weighting → our equal_volatility_optimizer

---

### 4.2 Riskfolio-Lib

| Attribute | Details |
|---|---|
| **Name** | Riskfolio-Lib |
| **URL** | https://github.com/dcajasn/Riskfolio-Lib |
| **Language** | Python |
| **License** | BSD 3-Clause |
| **Stars** | 3k+ |
| **Description** | Portfolio optimization and risk management library |

**Features:**
- Modern portfolio theory
- Risk measures (VaR, CVaR, CDaR, EVaR)
- Optimization with constraints
- Factor models
- Black-Litterman

**How We Compare:**
- ✅ We have hardcoded constitutional limits (Riskfolio is configurable)
- ✅ We have real-time monitoring (Riskfolio is batch-oriented)
- ❌ Riskfolio has more risk measures (CDaR, EVaR)

**What We Adopt:**
- VaR and CVaR calculation methods → our VaRCalculator
- Risk budgeting concept → our portfolio validation
- Constraint-based optimization patterns

---

## 5. Data Providers & APIs

### 5.1 Alpaca Markets

| Attribute | Details |
|---|---|
| **Name** | Alpaca |
| **URL** | https://alpaca.markets/ |
| **Type** | Broker + Data API |
| **Coverage** | US Equities, Forex |
| **Free Tier** | Paper trading + delayed data |

**Our Integration:** `quant_nanggroe/exchange/alpaca_broker.py`

- Full broker integration via alpaca-py SDK
- Market data via REST API
- Paper trading by default (sandbox=True)
- Supports stocks, ETFs, and forex pairs

**What We Adopt:**
- **AlpacaBroker** for US equity and forex execution
- Paper trading as the default safe mode
- alpaca-py SDK as optional dependency

---

### 5.2 Polygon.io

| Attribute | Details |
|---|---|
| **Name** | Polygon.io |
| **URL** | https://polygon.io/ |
| **Type** | Market Data API |
| **Coverage** | US Equities, Options, Forex, Crypto |
| **Free Tier** | 15-min delayed data |

**Our Integration:** Data loader in backtest infrastructure

- OHLCV data via polygon-api-client
- Options chain data (planned)
- Real-time WebSocket streaming (planned)

**What We Adopt:**
- polygon-api-client as optional dependency
- Data loader for US equity backtesting
- Options data integration (future)

---

### 5.3 Binance API

| Attribute | Details |
|---|---|
| **Name** | Binance |
| **URL** | https://www.binance.com/ |
| **Type** | Exchange + Data |
| **Coverage** | Crypto |
| **Free Tier** | Rate-limited public data |

**Our Integration:** Via CCXT in `quant_nanggroe/exchange/ccxt_broker.py`

- Spot, futures, and perpetual swap trading
- L1/L2 order book data
- WebSocket streaming
- Highest liquidity for crypto pairs

**What We Adopt:**
- **CCXTBroker** with Binance as primary crypto venue
- Spot, futures, and perps market type routing
- 125x max leverage (constitutionally capped to 3x)

---

### 5.4 FRED (Federal Reserve Economic Data)

| Attribute | Details |
|---|---|
| **Name** | FRED |
| **URL** | https://fred.stlouisfed.org/ |
| **Type** | Economic Data API |
| **Coverage** | US Macro |
| **Free Tier** | Full access (rate-limited) |

**Our Integration:** Used by Macro agent for economic indicators

- Interest rates, GDP, CPI, unemployment
- Fed funds rate, treasury yields
- Consumer sentiment indices

**What We Adopt:**
- Economic data feeds for macro agent
- Regime detection input (interest rates, inflation)
- Central bank policy tracking

---

### 5.5 SEC EDGAR

| Attribute | Details |
|---|---|
| **Name** | SEC EDGAR |
| **URL** | https://www.sec.gov/edgar |
| **Type** | Regulatory Filings |
| **Coverage** | US Public Companies |
| **Free Tier** | Full access (rate-limited) |

**Our Integration:** Used by Researcher agent for fundamental analysis

- 10-K, 10-Q, 8-K filings
- Form 4 insider trades
- Proxy statements
- Ownership disclosures

**What We Adopt:**
- Fundamental data extraction for equity analysis
- Insider trading signals
- Earnings report analysis

---

### 5.6 TwelveData

| Attribute | Details |
|---|---|
| **Name** | TwelveData |
| **URL** | https://twelvedata.com/ |
| **Type** | Market Data API |
| **Coverage** | Multi-asset |
| **Free Tier** | 800 API calls/day |

**Our Integration:** Optional data provider via twelvedata SDK

- Stocks, forex, crypto, ETFs, indices
- Real-time and historical data
- Technical indicators API
- Fundamentals

**What We Adopt:**
- twelvedata as optional dependency
- Alternative data source for cross-validation
- Forex and international market data

---

### 5.7 Yahoo Finance (yfinance)

| Attribute | Details |
|---|---|
| **Name** | yfinance |
| **URL** | https://github.com/ranaroussi/yfinance |
| **Type** | Unofficial API |
| **Coverage** | Multi-asset |
| **Free Tier** | Full access (unofficial) |

**Our Integration:** `quant_nanggroe/engine/backtest/loaders/yfinance_loader.py`

- OHLCV data download
- Fundamental data (limited)
- Used primarily for backtest data loading
- Not suitable for production live trading

**What We Adopt:**
- yfinance as core dependency for data loading
- Backtest data provider (free and accessible)
- Quick data exploration in development

---

## 6. Exchange Libraries

### 6.1 CCXT

| Attribute | Details |
|---|---|
| **Name** | CCXT |
| **URL** | https://github.com/ccxt/ccxt |
| **Language** | JavaScript, Python, PHP |
| **License** | MIT |
| **Stars** | 33k+ |
| **Description** | CryptoCurrency eXchange Trading Library |

**Our Integration:** `quant_nanggroe/exchange/ccxt_broker.py`

- Unified API for 8 exchanges (Binance, OKX, Bybit, Bitget, Kraken, KuCoin, Gate, Coinbase)
- Spot, futures, and perpetual swap support
- Market type routing
- Sandbox/testnet mode

**What We Adopt:**
- **CCXT as the primary exchange abstraction** (core dependency)
- Unified API pattern for multi-exchange support
- Market type routing (spot/futures/perps)

---

### 6.2 Polymarket CLOB API

| Attribute | Details |
|---|---|
| **Name** | Polymarket |
| **URL** | https://polymarket.com/ |
| **Type** | Prediction Market |
| **Coverage** | Event contracts |

**Our Integration:** `quant_nanggroe/exchange/polymarket_broker.py`

- CLOB (Central Limit Order Book) API
- Ethereum-based condition tokens
- Binary outcome markets
- No sandbox mode (real money only)

**What We Adopt:**
- **PolymarketBroker** for prediction market trading
- Conditional token trading
- Event contract integration

---

## 7. Backtesting Frameworks

### 7.1 Backtrader (revisited)
See section 1.3 above.

### 7.2 Zipline Reloaded

| Attribute | Details |
|---|---|
| **Name** | Zipline Reloaded |
| **URL** | https://github.com/stefan-jansen/zipline-reloaded |
| **Description** | Community-maintained fork of Quantopian's Zipline |

**What We Adopt:**
- Pipeline API patterns
- Data bundle concepts
- Performance tracking approach

### 7.3 Our Custom Backtest Engine

Our backtest engine (`quant_nanggroe/engine/backtest/`) provides:

| Feature | Implementation |
|---|---|
| Multi-asset engines | equity, crypto, forex, futures, composite |
| Monte Carlo simulation | MonteCarlo module |
| Walk-forward optimization | WalkForward module |
| Execution simulation | Slippage, partial fills, latency |
| Portfolio tracking | Real-time PnL, positions, allocation |
| Performance metrics | Sharpe, Sortino, Calmar, max drawdown |
| Data loaders | yfinance, CCXT, custom |
| Portfolio optimizers | Mean-variance, risk parity, equal vol |

---

## 8. AI/ML for Finance

### 8.1 FinGPT

| Attribute | Details |
|---|---|
| **Name** | FinGPT |
| **URL** | https://github.com/AI4Finance-Foundation/FinGPT |
| **Description** | Open-source financial large language model |

**What We Adopt:**
- Financial NLP patterns for news/sentiment analysis
- Financial text understanding for agent reasoning

### 8.2 FinRL

| Attribute | Details |
|---|---|
| **Name** | FinRL |
| **URL** | https://github.com/AI4Finance-Foundation/FinRL |
| **Description** | Deep reinforcement learning for finance |

**What We Adopt:**
- RL-based strategy optimization concepts (future)
- Multi-agent RL patterns
- Market environment design patterns

### 8.3 ChatDev

| Attribute | Details |
|---|---|
| **Name** | ChatDev |
| **URL** | https://github.com/OpenBMB/ChatDev |
| **Description** | Communicative agents for software development |

**What We Adopt:**
- Multi-agent communication patterns → our council debate
- Role-based agent collaboration → our 11-agent system
- Iterative refinement concept → our reflection phase

---

## 9. Comparison Matrix

### Feature Comparison: Trading Frameworks

| Feature | Quant Nanggroe | Freqtrade | NautilusTrader | Backtrader | QuantConnect | Jesse |
|---|---|---|---|---|---|---|
| AI Agents | ✅ 11 | ❌ | ❌ | ❌ | ❌ | ❌ |
| Alpha Factors | ✅ 469 | ❌ | ❌ | ❌ | ❌ | ❌ |
| Constitutional Risk | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Kill Switch | ✅ | ⚠️ Basic | ❌ | ❌ | ❌ | ❌ |
| Multi-Asset | ✅ 4 | ✅ Crypto | ✅ | ⚠️ Equity | ✅ | ❌ Crypto |
| Live Trading | ✅ 10 exchanges | ✅ | ✅ | ⚠️ | ✅ | ✅ |
| Paper Trading | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Council Debate | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Human-in-Loop | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Smart Order Routing | ✅ | ❌ | ⚠️ | ❌ | ⚠️ | ❌ |
| Backtesting | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| LangGraph | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

### Feature Comparison: Agent Frameworks

| Feature | Quant Nanggroe | LangGraph | CrewAI | AutoGen | PydanticAI |
|---|---|---|---|---|---|
| Graph Orchestration | ✅ | ✅ | ❌ | ❌ | ❌ |
| Domain-Specific | ✅ Trading | ❌ General | ❌ General | ❌ General | ❌ General |
| Risk Limits | ✅ Constitutional | ❌ | ❌ | ❌ | ❌ |
| Multi-Path Routing | ✅ | ✅ | ❌ | ❌ | ❌ |
| Human-in-Loop | ✅ | ✅ | ❌ | ✅ | ❌ |
| Type Safety | ✅ Pydantic | ⚠️ | ❌ | ❌ | ✅ Pydantic |
| Council Debate | ✅ | ❌ | ❌ | ❌ | ❌ |
| Exchange Integration | ✅ 10 | ❌ | ❌ | ❌ | ❌ |
| Factor Engine | ✅ 469 | ❌ | ❌ | ❌ | ❌ |

---

## 10. Adoption Summary

### Directly Adopted (Code in Our Codebase)

| Source | What We Adopted | Module |
|---|---|---|
| **Alpha101** | All 101 factors | `engine/factors/alpha101.py` |
| **GTJA191** | All 191 factors | `engine/factors/gtja191.py` |
| **Qlib158** | All 158 factors | `engine/factors/qlib158.py` |
| **Barra** | Risk factors | `engine/factors/barra.py` |
| **LangGraph** | StateGraph orchestration | `agents/graph.py`, `agents/graph_v2.py` |
| **CCXT** | Exchange abstraction | `exchange/ccxt_broker.py` |
| **Pydantic** | All data models | `agents/state.py`, throughout |
| **FastAPI** | API server | `api/app.py` |

### Conceptually Adopted (Design Patterns)

| Source | Pattern | Where Applied |
|---|---|---|
| **Freqtrade** | CCXT exchange pattern | ExchangeFactory |
| **NautilusTrader** | Event-driven architecture | Graph node pattern |
| **Backtrader** | Cerebro orchestration | TradingGraphV2 |
| **TradingAgents** | Bull/bear debate | CouncilDebate |
| **TradingAgents** | Risk debate | RiskDebateState |
| **TradingAgents** | Stress testing | RiskManager.stress_test() |
| **CrewAI** | Role-based agents | AgentRole enum |
| **AutoGen** | Human participation | HumanCheckpoint |
| **PyPortfolioOpt** | Optimization algorithms | Backtest optimizers |
| **Riskfolio-Lib** | VaR/CVaR methods | VaRCalculator |
| **Zipline** | Pipeline API | FactorPipeline |

### Planned Adoption (Future)

| Source | What | Timeline |
|---|---|---|
| **FinRL** | RL-based strategy optimization | Q4 2025 |
| **FinGPT** | Financial NLP for sentiment | Q4 2025 |
| **Hummingbot** | Market-making strategies | Q1 2026 |
| **PyPortfolioOpt** | HRP optimization | Q3 2025 |
| **Riskfolio-Lib** | CDaR, EVaR risk measures | Q4 2025 |

---

© 2025-2026 Quant Nanggroe AI | Research Benchmark v4.0.0
