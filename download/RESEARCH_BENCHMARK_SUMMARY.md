# Quant-Nanggroe-AI Research Benchmark Summary

## Agentic Trading Intelligence OS — 113 Projects Benchmarked

**Date**: 2026-03-04  
**Version**: 2.0  
**Total Projects**: 113 across 10 categories  
**Task ID**: 2-b

---

## Executive Summary

This research benchmark evaluates 113 open-source and commercial projects across 10 critical categories for building the **Quant-Nanggroe-AI** monorepo — an Agentic Trading Intelligence OS that merges 20+ trading/quant repositories into a production-grade system.

### Key Findings

1. **LangGraph is the definitive agent orchestration layer** — graph-based workflows, state machines, human-in-the-loop, and multi-agent voting patterns map perfectly to trading system requirements
2. **NautilusTrader + CCXT form the execution backbone** — Rust-native performance for latency-critical paths, unified exchange API for 100+ venues
3. **Qlib + FinRL provide the AI/ML core** — Microsoft's expression engine for alpha factors, AI4Finance's DRL framework for adaptive trading
4. **PyPortfolioOpt + Riskfolio-Lib cover portfolio construction** — from mean-variance to CVaR optimization with 13+ risk measures
5. **The "AI Hedge Fund" pattern (45K stars) validates multi-agent trading** — persona-based agents, council voting, and multi-perspective analysis are the dominant paradigm

---

## Category Breakdown & Top Recommendations

### 1. Trading Frameworks (16 projects)

| Project | Stars | Relevance | Key Takeaway |
|---------|-------|-----------|--------------|
| **CCXT** | 35K | CRITICAL | Unified exchange API — our exchange adapter layer |
| **Freqtrade** | 35K | HIGH | Production crypto trading with dry-run + hyperopt |
| **NautilusTrader** | 4.5K | CRITICAL | Rust-native execution engine, actor model architecture |
| **Qlib (Microsoft)** | 16K | CRITICAL | AI quant platform, expression engine, model zoo |
| **Zipline** | 18K | MEDIUM | Pipeline API for factor computation (gold standard) |
| **Backtrader** | 14K | MEDIUM | Classic event-driven reference (unmaintained) |
| **VectorBT** | 4.5K | HIGH | 10-100x faster vectorized backtesting |
| **Hummingbot** | 8.5K | HIGH | Market making engine, connector architecture V2 |
| **Lean Engine** | 10K | HIGH | Enterprise-grade C#/Python, Alpha→Portfolio→Risk→Execution pipeline |
| **Jesse** | 6K | MEDIUM | Clean strategy API, local-first design |
| **Gekko** | 12K | LOW | Deprecated, historical reference only |
| **Zenbot** | 8.5K | LOW | Node.js, limited Python relevance |
| **PyAlgoTrade** | 4.4K | LOW | Mature but unmaintained |
| **Catalyst** | 2.5K | LOW | Abandoned Zipline crypto fork |
| **OctoBot** | 3.5K | MEDIUM | Tentacle plugin architecture |
| **Backtesting.py** | 5K | MEDIUM | Lightweight, interactive viz |

**RECOMMENDATION**: Use NautilusTrader as execution core (Rust performance), CCXT for exchange connectivity, Qlib for AI quant pipeline, VectorBT for fast prototyping.

---

### 2. AI/Agent Trading (16 projects)

| Project | Stars | Relevance | Key Takeaway |
|---------|-------|-----------|--------------|
| **AI-Hedge-Fund** | 45K | CRITICAL | Multi-agent with persona-based investors, council voting |
| **AutoGen (Microsoft)** | 45K | HIGH | Multi-agent conversations, group chat orchestration |
| **FinRL** | 12K | CRITICAL | SOTA DRL for trading (PPO, SAC, TD3, A2C) |
| **FinGPT** | 15K | HIGH | Open-source financial LLM, LoRA fine-tuning |
| **TradingAgents** | 5K | CRITICAL | Princeton multi-agent debate/consensus for trading |
| **FinRobot** | 3.5K | HIGH | Multi-agent financial analysis platform |
| **BloombergGPT** | — | MEDIUM | Proprietary, benchmark for financial LLM quality |
| **Portfoliopilot** | 2.5K | MEDIUM | LLM-based portfolio management |
| **Alpha_Vantage_AI** | 4.5K | MEDIUM | ML-ready data access layer |
| **DeepTrader** | 600 | MEDIUM | Transformer cross-asset attention |
| **AI4Finance Foundation** | — | HIGH | Ecosystem (FinRL + FinGPT + FinRobot) |
| **AutoTrader-AI** | 800 | LOW | Small ML prediction pipeline |
| **QuantGPT** | 500 | MEDIUM | LLM-as-coder for strategy generation |
| **TradeAI** | 300 | LOW | Hybrid AI-quant concept |
| **Stock-Trading-Agent** | 1.5K | MEDIUM | RL agent environment design |
| **Intrinio/Kensho** | — | LOW | Proprietary, architecture reference only |

**RECOMMENDATION**: Adopt TradingAgents' debate/consensus pattern + AI-Hedge-Fund's council voting for decision-making. Use FinRL for DRL trading agents, FinGPT for financial NLP, FinRobot for multi-agent financial analysis.

---

### 3. Factor/Alpha Libraries (11 projects)

| Project | Stars | Relevance | Key Takeaway |
|---------|-------|-----------|--------------|
| **WorldQuant Alpha101** | 3.5K | CRITICAL | 101 formulaic alphas — foundation factor library |
| **Alphalens** | 3.2K | CRITICAL | IC analysis, quantile returns, factor tear sheets |
| **GTJA191** | 800 | HIGH | 191 Chinese A-share alpha factors |
| **Barra Risk Model** | 1.2K | HIGH | MSCI Barra multi-factor risk decomposition |
| **Pyfolio** | 5.5K | HIGH | Bayesian cone analysis, tear sheets |
| **Empyrical** | 1.3K | HIGH | All standard risk/return metrics |
| **Riskfolio-Lib** | 3.5K | HIGH | 13 risk measures, HRP, risk parity |
| **AlphaTrading** | 1.5K | MEDIUM | Dynamic multi-factor model |
| **Toraniko** | 300 | MEDIUM | Complete Barra-style risk model |
| **Smart-Beta Framework** | 400 | MEDIUM | Factor screening + weighting |
| **WorldQuant BRAIN** | — | MEDIUM | Proprietary alpha simulation platform |

**RECOMMENDATION**: Build factor engine on Alpha101 + GTJA191 formulas. Use Alphalens for validation, Empyrical for metrics, Pyfolio for reporting. Implement Barra risk model for institutional-grade risk decomposition.

---

### 4. Risk Management (10 projects)

| Project | Stars | Relevance | Key Takeaway |
|---------|-------|-----------|--------------|
| **PyPortfolioOpt** | 5K | CRITICAL | Modular returns→risk→optimizer pipeline |
| **QuantStats** | 5.5K | HIGH | Monte Carlo simulation + professional tear sheets |
| **Riskfolio-Lib** | 3.5K | HIGH | 13 risk measures, CVaR/CDaR/EVaR optimization |
| **Skfolio** | 1.2K | HIGH | Scikit-learn API for portfolio optimization with CV |
| **ffn** | 2K | MEDIUM | Lightweight drawdown + performance stats |
| **PyRisk** | 500 | MEDIUM | VaR/CVaR computation (parametric/historical/MC) |
| **riskparity.py** | 400 | MEDIUM | Equal risk contribution optimization |
| **Kelly Criterion** | 200 | MEDIUM | Optimal position sizing based on edge |
| **Stress-Testing** | 300 | MEDIUM | Scenario analysis framework |
| **CVaR Portfolio** | 250 | MEDIUM | Rockafellar-Uryasev CVaR optimization |

**RECOMMENDATION**: Use PyPortfolioOpt as core optimizer, Riskfolio-Lib for advanced risk measures, QuantStats for Monte Carlo and reporting, Skfolio for cross-validated portfolio construction.

---

### 5. Data Providers (13 projects)

| Project | Stars | Relevance | Key Takeaway |
|---------|-------|-----------|--------------|
| **Alpaca Markets** | — | CRITICAL | Trading + data + paper trading in one API |
| **Binance API** | — | CRITICAL | Primary crypto exchange with testnet |
| **Polygon.io** | — | HIGH | Institutional-grade tick data, WebSocket |
| **Yahoo Finance (yfinance)** | 15K | HIGH | Free stock data, no API key, backtesting fallback |
| **Bybit API** | — | HIGH | Crypto derivatives, high throughput |
| **CoinGecko** | — | MEDIUM | 10K+ crypto assets, market overview |
| **AlphaVantage** | — | MEDIUM | Free tier, sentiment API |
| **TwelveData** | — | MEDIUM | Built-in technical indicators |
| **SEC EDGAR** | — | MEDIUM | Corporate filings for fundamental analysis |
| **FRED** | — | MEDIUM | 800K+ macroeconomic series |
| **Quandl/Nasdaq** | — | MEDIUM | Alternative data + futures |
| **Tiingo** | — | LOW | Niche alternative source |
| **IEX Cloud** | — | LOW | Complex pricing |

**RECOMMENDATION**: Alpaca for equity trading+data, Binance for crypto, Polygon.io for institutional data, yfinance for free backtesting data, SEC EDGAR for fundamental analysis, FRED for macro signals.

---

### 6. Agent Frameworks (11 projects)

| Project | Stars | Relevance | Key Takeaway |
|---------|-------|-----------|--------------|
| **LlamaIndex** | 40K | HIGH | RAG pipeline for financial documents |
| **AutoGen** | 45K | HIGH | Multi-agent conversations |
| **CrewAI** | 25K | HIGH | Crew-Agent-Task model for role-based agents |
| **Semantic Kernel** | 24K | MEDIUM | Planner pattern for automatic orchestration |
| **DSPy** | 22K | HIGH | Declarative LM programming, auto prompt optimization |
| **LangGraph** | 20K | CRITICAL | Graph-based workflow engine, state machines |
| **Agno** | 18K | MEDIUM | High-performance agent runtime |
| **SmolAgents** | 15K | MEDIUM | Lightweight code-generating agents |
| **Haystack** | 19K | MEDIUM | Pipeline-based RAG framework |
| **PydanticAI** | 10K | HIGH | Type-safe agents with validation |
| **OpenManus** | 35K | MEDIUM | RL-based agent tuning |

**RECOMMENDATION**: LangGraph as primary orchestration (graph-based workflows), CrewAI for role-based agent composition, PydanticAI for type safety, DSPy for prompt optimization, LlamaIndex for RAG over financial documents.

---

### 7. LangGraph Patterns (10 patterns)

| Pattern | Relevance | Application |
|---------|-----------|-------------|
| **Multi-Agent Orchestration** | CRITICAL | Supervisor → Analyst/Trader/Risk Manager hierarchy |
| **Graph-Based Workflows** | CRITICAL | Data→Analysis→Decision→Execution→Risk as graph |
| **Council/Voting Patterns** | CRITICAL | Bull/Bear/Risk agents vote on trade decisions |
| **Tool-Calling Patterns** | CRITICAL | Market data, order placement, risk calc as tools |
| **Human-in-the-Loop** | CRITICAL | Approval gates before trade execution |
| **State Machine (ReAct)** | HIGH | Observe→Think→Act→Verify trading cycle |
| **Memory Management** | HIGH | Trade history, market condition memory across sessions |
| **Subgraph Composition** | HIGH | Analysis/Execution/Risk as composable subgraphs |
| **Parallel Execution** | HIGH | Parallel technical+fundamental+sentiment analysis |
| **Self-Correcting Agents** | HIGH | Position size validation, risk limit checks |

**RECOMMENDATION**: Implement the entire trading workflow as a LangGraph StateGraph with supervisor pattern for multi-agent orchestration, council voting for decisions, and human-in-the-loop for safety.

---

### 8. Execution Systems (11 projects)

| Project | Stars | Relevance | Key Takeaway |
|---------|-------|-----------|--------------|
| **NautilusTrader OMS** | 4.5K | CRITICAL | Actor-based order management, Rust performance |
| **CCXT Pro** | 35K | CRITICAL | Unified trading API across 100+ exchanges |
| **Lean Execution** | 10K | HIGH | Transaction handler pipeline, brokerage abstraction |
| **Freqtrade Execution** | 35K | HIGH | Dry-run simulation, order timeout management |
| **Hummingbot Connectors** | 8.5K | HIGH | CEX + DEX gateway architecture |
| **Alpaca Trading** | — | HIGH | Paper/Live switching, bracket orders |
| **Fill Simulation (Nautilus)** | 4.5K | HIGH | Order book depth + latency simulation |
| **Paper Trading (Lean)** | 10K | HIGH | Real-time paper trading with same API |
| **Slippage Models (Zipline)** | 18K | MEDIUM | Volume share slippage for realistic backtesting |
| **Smart Order Router** | 8.5K | MEDIUM | Multi-venue price comparison, order splitting |
| **IBKR TWS API** | — | MEDIUM | Global market access, professional execution |

**RECOMMENDATION**: Build execution on NautilusTrader's actor-based OMS, use CCXT for exchange connectivity, implement dry-run simulation following Freqtrade's pattern, add order book depth simulation for realistic backtesting.

---

### 9. Prediction Markets (5 projects)

| Project | Stars | Relevance | Key Takeaway |
|---------|-------|-----------|--------------|
| **Polymarket** | — | HIGH | Largest crypto prediction market, CLOB API |
| **Kalshi** | — | HIGH | CFTC-regulated US prediction market |
| **Metaculus** | — | MEDIUM | Aggregated human forecasts, accuracy tracking |
| **Augur** | 500 | LOW | Decentralized, Ethereum-based |
| **Manifold Markets** | 300 | LOW | Play-money, social forecasting |

**RECOMMENDATION**: Integrate Polymarket API for event probability signals and Kalshi for regulated US event contracts. Prediction market odds provide unique alpha for event-driven trading.

---

### 10. Backtesting Engines (10 projects)

| Project | Stars | Relevance | Key Takeaway |
|---------|-------|-----------|--------------|
| **VectorBT** | 4.5K | CRITICAL | 10-100x faster vectorized backtesting |
| **NautilusTrader Backtest** | 4.5K | HIGH | Order book simulation, tick-level resolution |
| **Lean Backtesting** | 10K | HIGH | Alpha→Portfolio→Risk→Execution pipeline |
| **Qlib Backtesting** | 16K | HIGH | ML-integrated backtesting pipeline |
| **FinRL Backtesting** | 12K | HIGH | DRL agent evaluation with gym environments |
| **Backtrader** | 14K | MEDIUM | Classic event-driven reference |
| **Zipline Reloaded** | 1.5K | MEDIUM | Maintained fork with Pipeline API |
| **Backtesting.py** | 5K | MEDIUM | Lightweight, interactive HTML reports |
| **Walk-Forward Optimization** | — | HIGH | Robustness testing via rolling window |
| **Monte Carlo (QuantStats)** | 5.5K | HIGH | Bootstrap resampling for confidence intervals |

**RECOMMENDATION**: Dual backtesting approach — VectorBT for rapid prototyping/optimization, NautilusTrader for production-grade simulation. Implement walk-forward optimization and Monte Carlo resampling for robustness validation.

---

## Architecture Recommendations for Quant-Nanggroe-AI

### Layer 1: Agent Orchestration (LangGraph)
```
[Supervisor Agent]
├── [Analysis Subgraph]
│   ├── Technical Analyst Agent
│   ├── Fundamental Analyst Agent
│   └── Sentiment Analyst Agent
├── [Decision Subgraph]
│   ├── Bull Agent (optimistic view)
│   ├── Bear Agent (pessimistic view)
│   └── Risk Manager Agent
├── [Execution Subgraph]
│   ├── Order Router
│   ├── Position Sizer
│   └── Human-in-the-Loop Gate
└── [Monitoring Subgraph]
    ├── Performance Tracker
    ├── Risk Monitor
    └── Alert System
```

### Layer 2: Trading Engine (NautilusTrader + CCXT)
- Rust-native execution core for sub-millisecond latency
- CCXT adapter layer for 100+ exchange connectivity
- Actor-based OMS with message passing
- Order book depth simulation for realistic backtesting

### Layer 3: AI/ML Pipeline (Qlib + FinRL + FinGPT)
- Qlib expression engine for alpha factor computation
- FinRL for DRL trading agents (PPO, SAC, TD3)
- FinGPT for financial NLP (sentiment, news analysis)
- DSPy for automatic prompt optimization

### Layer 4: Risk Management (PyPortfolioOpt + Riskfolio-Lib)
- Modular returns → risk model → optimizer pipeline
- 13+ risk measures including CVaR, CDaR, EVaR
- Monte Carlo simulation for confidence intervals
- Walk-forward optimization for robustness

### Layer 5: Data Infrastructure (Alpaca + Binance + Polygon + yfinance)
- Alpaca for equity trading + data
- Binance for crypto trading
- Polygon.io for institutional-grade data
- yfinance for free backtesting data
- SEC EDGAR + FRED for fundamental/macro data

### Layer 6: Factor Library (Alpha101 + Alphalens + Barra)
- Alpha101 + GTJA191 formula implementations
- Alphalens for IC analysis and factor validation
- Barra risk model for institutional risk decomposition
- Empyrical + Pyfolio for metrics and reporting

---

## Critical Integration Priorities

### P0 (Must Have — Sprint 1-2)
1. **LangGraph** — Agent orchestration engine
2. **CCXT** — Exchange connectivity layer
3. **NautilusTrader** — Execution engine core
4. **PydanticAI** — Type-safe agent validation
5. **yfinance** — Free data for development

### P1 (Should Have — Sprint 3-4)
6. **FinRL** — DRL trading agents
7. **Qlib** — AI quant pipeline
8. **Alpaca** — Equity trading + paper trading
9. **VectorBT** — Fast backtesting
10. **PyPortfolioOpt** — Portfolio optimization

### P2 (Nice to Have — Sprint 5-6)
11. **CrewAI** — Role-based agent composition
12. **DSPy** — Prompt optimization
13. **LlamaIndex** — RAG for financial documents
14. **FinGPT** — Financial NLP
15. **Alpha101 + Alphalens** — Factor library

### P3 (Future — Sprint 7+)
16. **Polymarket/Kalshi** — Prediction market signals
17. **Riskfolio-Lib** — Advanced risk measures
18. **Hummingbot** — Market making strategies
19. **QuantStats** — Professional reporting
20. **Skfolio** — CV-optimized portfolios

---

## Key Architecture Patterns to Adopt

1. **Supervisor Pattern** (from LangGraph) — Portfolio manager supervises specialist agents
2. **Council Voting** (from AI-Hedge-Fund) — Multiple agents vote with confidence-weighted decisions
3. **Pipeline API** (from Zipline/Qlib) — Composable factor computation pipeline
4. **Actor Model** (from NautilusTrader) — Message-passing for concurrent execution
5. **Exchange Adapter** (from CCXT) — Unified interface over heterogeneous exchanges
6. **Graph Workflow** (from LangGraph) — Trading decisions as conditional graph traversal
7. **Factor Expression Engine** (from Qlib) — Declarative alpha factor definitions
8. **Dry-Run Toggle** (from Freqtrade) — Same code path for paper and live trading
9. **Tentacle Plugin** (from OctoBot) — Modular strategy/indicator plugins
10. **Tear Sheet Generation** (from Pyfolio/QuantStats) — Standardized performance reporting

---

*Generated by Task 2-b — Quant-Nanggroe-AI Research Benchmark*
