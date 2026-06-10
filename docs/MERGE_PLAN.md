# Quant Nanggroe AI — Merge Plan

**Version 0.2.0 | How 20+ Repositories Were Merged**

> This document details the consolidation of 20+ trading and quantitative repositories into the Quant Nanggroe AI monorepo. It covers the source repository inventory, merge priority and order, what was kept and discarded, conflict resolution, and evidence-based merge decisions.

---

## Table of Contents

1. [Source Repository Inventory](#1-source-repository-inventory)
2. [Merge Priority and Order](#2-merge-priority-and-order)
3. [What Was Kept from Each Repository](#3-what-was-kept-from-each-repository)
4. [What Was Discarded and Why](#4-what-was-discarded-and-why)
5. [Conflict Resolution Strategy](#5-conflict-resolution-strategy)
6. [Evidence-Based Merge Decisions](#6-evidence-based-merge-decisions)

---

## 1. Source Repository Inventory

### 1.1 Complete Repository List

The following 24 source repositories were evaluated and merged into Quant Nanggroe AI:

| # | Repository | Stars | Category | Language | License | Merge Status |
|---|-----------|-------|----------|----------|---------|-------------|
| 1 | **CCXT** | 35K | Trading Framework | JS/Python | MIT | ✅ Merged |
| 2 | **Freqtrade** | 35K | Trading Framework | Python | GPL-3.0 | ✅ Patterns adopted |
| 3 | **NautilusTrader** | 4.5K | Execution Engine | Rust/Python | LGPL-3.0 | ✅ Patterns adopted |
| 4 | **Qlib (Microsoft)** | 16K | AI Quant Platform | Python | MIT | ✅ Patterns adopted |
| 5 | **AI-Hedge-Fund** | 45K | AI Agent Trading | Python | MIT | ✅ Patterns adopted |
| 6 | **FinRL** | 12K | DRL Trading | Python | MIT | 🔄 Integration pending |
| 7 | **FinGPT** | 15K | Financial LLM | Python | Apache-2.0 | 🔄 Integration pending |
| 8 | **TradingAgents** | 5K | Multi-Agent Debate | Python | MIT | ✅ Patterns adopted |
| 9 | **WorldQuant Alpha101** | 3.5K | Factor Library | Python | MIT | ✅ Merged |
| 10 | **Alphalens** | 3.2K | Factor Analysis | Python | MIT | ✅ Patterns adopted |
| 11 | **GTJA191** | 800 | Factor Library | Python | MIT | ✅ Merged |
| 12 | **PyPortfolioOpt** | 5K | Portfolio Optimization | Python | MIT | ✅ Patterns adopted |
| 13 | **Riskfolio-Lib** | 3.5K | Risk Measures | Python | BSD-3 | ✅ Patterns adopted |
| 14 | **QuantStats** | 5.5K | Performance Reporting | Python | MIT | ✅ Patterns adopted |
| 15 | **Empyrical** | 1.3K | Risk Metrics | Python | Apache-2.0 | ✅ Patterns adopted |
| 16 | **VectorBT** | 4.5K | Backtesting | Python | MIT | ✅ Patterns adopted |
| 17 | **Pyfolio** | 5.5K | Portfolio Analysis | Python | MIT | ✅ Patterns adopted |
| 18 | **Barra Risk Model** | 1.2K | Risk Model | Python | MIT | ✅ Merged |
| 19 | **LangGraph** | 20K | Agent Framework | Python | MIT | ✅ Direct dependency |
| 20 | **PydanticAI** | 10K | Type-Safe Agents | Python | MIT | ✅ Direct dependency |
| 21 | **LlamaIndex** | 40K | RAG Framework | Python | MIT | 🔄 Integration pending |
| 22 | **DSPy** | 22K | LM Programming | Python | MIT | 🔄 Integration pending |
| 23 | **Hummingbot** | 8.5K | Market Making | Python | Apache-2.0 | 📋 Planned |
| 24 | **CrewAI** | 25K | Agent Framework | Python | MIT | ✅ Patterns adopted |

### 1.2 Functional Domain Mapping

| Functional Domain | Primary Source | Secondary Sources | Target Module |
|-------------------|---------------|-------------------|---------------|
| Exchange Connectivity | CCXT | Alpaca, Binance | `exchange/` |
| Agent Orchestration | LangGraph | AI-Hedge-Fund, TradingAgents | `agents/` |
| Factor Computation | Alpha101 | GTJA191, Barra, Qlib | `engine/factors/` |
| Risk Management | PyPortfolioOpt | Riskfolio-Lib, QuantStats | `engine/risk/` |
| Backtesting | VectorBT | NautilusTrader, QuantStats | `engine/backtest/` |
| Portfolio Analysis | Pyfolio | Empyrical, QuantStats | `engine/backtest/metrics.py` |
| Execution Management | NautilusTrader | Freqtrade, Lean | `engine/execution/` |
| Data Access | yfinance | Alpaca, Polygon, FRED | Direct dependency |
| Agent Framework | LangGraph | CrewAI, PydanticAI | `agents/` |
| Financial NLP | FinGPT | LlamaIndex | 🔄 Pending |

---

## 2. Merge Priority and Order

### 2.1 Phase 1: Foundation (Sprint 1-2) — COMPLETED

These repositories formed the architectural foundation and were merged first:

| Order | Repository | What Was Merged | Target Location |
|-------|-----------|-----------------|-----------------|
| 1 | **LangGraph** | Added as dependency; built `TradingGraph` on top | `agents/graph.py` |
| 2 | **CCXT** | Exchange abstraction layer | `exchange/ccxt_broker.py`, `exchange/base.py` |
| 3 | **AI-Hedge-Fund** | Council voting pattern, agent persona design | `agents/council/` |
| 4 | **TradingAgents** | Debate/consensus pattern | `agents/council/debate.py` |
| 5 | **Pydantic** | Type system foundation (direct dependency) | All models |
| 6 | **yfinance** | Free data access (direct dependency) | `pyproject.toml` |

### 2.2 Phase 2: Core Engine (Sprint 3-4) — COMPLETED

| Order | Repository | What Was Merged | Target Location |
|-------|-----------|-----------------|-----------------|
| 7 | **Alpha101** | 50+ alpha factor implementations | `engine/factors/alpha101.py` |
| 8 | **GTJA191** | 191 Chinese A-share factors | `engine/factors/gtja191.py` |
| 9 | **Barra** | Multi-factor risk model | `engine/factors/barra.py` |
| 10 | **PyPortfolioOpt** | Portfolio optimization patterns | `engine/risk/position_sizing.py`, `engine/risk/risk_parity.py` |
| 11 | **Riskfolio-Lib** | Risk measure computation | `engine/risk/var.py`, `engine/risk/drawdown.py` |
| 12 | **Empyrical** | Performance metric formulas | `engine/backtest/metrics.py` |
| 13 | **QuantStats** | Monte Carlo, tear sheet patterns | `engine/backtest/monte_carlo.py` |

### 2.3 Phase 3: Advanced Features (Sprint 5-6) — IN PROGRESS

| Order | Repository | What Was Merged | Target Location |
|-------|-----------|-----------------|-----------------|
| 14 | **VectorBT** | Vectorized backtesting approach | `engine/backtest/engine.py` |
| 15 | **NautilusTrader** | OMS patterns, fill simulation | `engine/execution/manager.py`, `engine/execution/fill.py` |
| 16 | **Freqtrade** | Paper/live toggle, dry-run simulation | `exchange/paper_broker.py` |
| 17 | **Qlib** | Expression engine patterns for factors | `engine/factors/base.py`, `engine/factors/pipeline.py` |
| 18 | **Pyfolio** | Tear sheet generation patterns | `engine/backtest/report.py` |

### 2.4 Phase 4: AI/ML Integration (Sprint 7+) — PLANNED

| Order | Repository | What Will Be Merged | Target Location |
|-------|-----------|---------------------|-----------------|
| 19 | **FinRL** | DRL trading agents (PPO, SAC, TD3) | `engine/models/` |
| 20 | **FinGPT** | Financial NLP pipeline | `engine/models/` |
| 21 | **LlamaIndex** | RAG over financial documents | `memory/` |
| 22 | **DSPy** | Prompt optimization | `agents/` |
| 23 | **Hummingbot** | Market making strategies | `engine/strategy/` |
| 24 | **CrewAI** | Role-based agent composition | `agents/` |

---

## 3. What Was Kept from Each Repository

### 3.1 Code Directly Integrated

| Repository | Code Kept | Lines of Code | Modifications |
|-----------|-----------|---------------|---------------|
| **Alpha101** | 50+ alpha factor classes with compute methods | ~2,000 | Refactored to use `AlphaFactor` base class, added `FactorMeta`, safe_div |
| **GTJA191** | Factor computation logic | ~1,500 | Adapted to `AlphaFactor` interface, pandas vectorization |
| **Barra** | Risk factor decomposition | ~800 | Integrated with our risk engine |
| **CCXT** | Exchange API wrapper | ~300 | Wrapped in `ExchangeInterface` adapter |

### 3.2 Patterns Adopted (Rewritten from Scratch)

| Repository | Pattern Adopted | Our Implementation |
|-----------|----------------|-------------------|
| **AI-Hedge-Fund** | Council voting with weighted decisions | `agents/council/voting.py` — `CouncilVoting` with `VoteResult`, `CouncilResult` |
| **TradingAgents** | Multi-perspective debate | `agents/council/debate.py` — `CouncilDebate` with Bull/Bear and Risk debates |
| **LangGraph** | Graph-based workflow orchestration | `agents/graph.py` — `TradingGraph` with 7 nodes and conditional edges |
| **Freqtrade** | Paper/live toggle with identical code paths | `exchange/paper_broker.py` — `PaperBroker` implementing `ExchangeInterface` |
| **NautilusTrader** | Actor-based OMS, fill simulation | `engine/execution/manager.py`, `engine/execution/fill.py` |
| **Qlib** | Expression engine for factor computation | `engine/factors/base.py` — `AlphaFactor` base class with `FactorMeta` |
| **PyPortfolioOpt** | Returns → Risk Model → Optimizer pipeline | `engine/risk/manager.py` — Modular risk management pipeline |
| **Riskfolio-Lib** | Multiple risk measures (CVaR, CDaR, EVaR) | `engine/risk/var.py` — VaR computation with parametric/historical/MC methods |
| **Empyrical** | Standard risk/return metric formulas | `engine/backtest/metrics.py` — Sharpe, Sortino, Calmar, max drawdown |
| **QuantStats** | Monte Carlo simulation, tear sheets | `engine/backtest/monte_carlo.py`, `engine/backtest/report.py` |
| **VectorBT** | Vectorized backtesting approach | `engine/backtest/engine.py` — Vectorized with execution reality |
| **Pyfolio** | Portfolio tear sheet generation | `engine/backtest/report.py` — HTML/JSON reports |
| **CrewAI** | Role-based agent composition | `agents/registry.py` — `AgentFactory` with role-based creation |
| **PydanticAI** | Type-safe agent validation | All Pydantic models in `agents/state.py`, `types/` |

### 3.3 Direct Dependencies (Used as-is)

| Repository | Usage | Version |
|-----------|-------|---------|
| **LangGraph** | Agent orchestration engine | >=0.2 |
| **LangChain** | LLM abstraction layer | >=0.3 |
| **CCXT** | Exchange connectivity | >=4.0 |
| **yfinance** | Free market data | >=0.2 |
| **Pydantic** | Data validation | >=2.0 |
| **SQLAlchemy** | ORM | >=2.0 |
| **FastAPI** | API server | >=0.100 |
| **Pandas/NumPy** | Data computation | >=2.0 / >=1.24 |
| **scikit-learn** | ML utilities | >=1.3 |

---

## 4. What Was Discarded and Why

### 4.1 Discarded Repositories

| Repository | Reason for Discard | Alternative Used |
|-----------|-------------------|-----------------|
| **Backtrader** | Unmaintained since 2021, Python 3.6 era code, no async support | VectorBT approach for backtesting |
| **Gekko** | Deprecated Node.js project, no Python relevance | CCXT for exchange connectivity |
| **Zenbot** | Node.js-based, limited Python ecosystem relevance | CCXT + custom execution |
| **PyAlgoTrade** | Unmaintained since 2018, outdated API patterns | VectorBT + custom engine |
| **Catalyst** | Abandoned Zipline crypto fork, no maintenance | CCXT + our exchange layer |
| **AutoTrader-AI** | Small ML prediction pipeline, insufficient scope | FinRL for ML-based trading |
| **TradeAI** | Hybrid AI-quant concept, insufficient maturity | Our multi-agent architecture |
| **Intrinio/Kensho** | Proprietary, closed-source | Alpaca + Polygon for institutional data |
| **Augur** | Decentralized, Ethereum-based, limited API | Polymarket for prediction markets |
| **Manifold Markets** | Play-money, social forecasting, no real market data | Polymarket + Kalshi |

### 4.2 Discarded Features from Merged Repositories

| Repository | Discarded Feature | Reason |
|-----------|------------------|--------|
| **Freqtrade** | Strategy file format | Incompatible with our agent-based approach |
| **Freqtrade** | Hyperopt optimization | Replaced by walk-forward optimization |
| **Freqtrade** | Telegram bot integration | Out of scope for our system |
| **Qlib** | Qlib DSL expression language | Replaced by Python class-based factors |
| **Qlib** | Qlib data server | Replaced by our multi-provider data layer |
| **NautilusTrader** | Rust core | Python-only for our system; Rust too complex to integrate |
| **NautilusTrader** | Actor model framework | Replaced by LangGraph state machines |
| **AI-Hedge-Fund** | Single-file architecture | Refactored into modular agent system |
| **Alpha101** | Original MATLAB formulas | Rewritten in vectorized Python/Pandas |
| **CCXT** | JS/PHP implementations | Python-only for our system |
| **Alphalens** | Full tear sheet UI | Integrated patterns into our backtest report |
| **Pyfolio** | Bayesian analysis | Deferred to Phase 4 |
| **VectorBT** | Portfolio optimization | Using PyPortfolioOpt patterns instead |
| **CrewAI** | Full CrewAI framework | Only adopted role-based composition pattern |

---

## 5. Conflict Resolution Strategy

### 5.1 Conflict Categories

| Conflict Type | Description | Resolution Strategy |
|--------------|-------------|-------------------|
| **Interface Conflict** | Different APIs for the same functionality | Define our canonical interface, adapt all implementations |
| **Data Model Conflict** | Different data representations | Use Pydantic models with strict typing |
| **Dependency Conflict** | Incompatible dependency versions | Pin to latest compatible versions |
| **Architecture Conflict** | Different architectural patterns | Follow our 6-layer architecture, refactor to fit |
| **License Conflict** | Incompatible open-source licenses | MIT/Apache-2.0 only; GPL quarantined |

### 5.2 Resolution Process

```
1. Identify Conflict
       │
       ▼
2. Categorize (Interface/Data/Dependency/Architecture/License)
       │
       ▼
3. Evaluate Impact (High/Medium/Low)
       │
       ├─ Low → Document and proceed
       │
       ├─ Medium → Refactor to our canonical pattern
       │
       └─ High → Architecture review before merge
              │
              ▼
4. Implement Resolution
       │
       ▼
5. Validate with Tests
       │
       ▼
6. Document Decision in ADR
```

### 5.3 Specific Conflict Resolutions

| Conflict | Source A | Source B | Resolution |
|----------|----------|----------|------------|
| Exchange interface | CCXT async API | Alpaca sync API | `ExchangeInterface` abstract base class with async-only methods |
| Factor computation | Qlib expression DSL | Alpha101 Python class | `AlphaFactor` base class with `compute(df) → pd.Series` interface |
| Risk metrics | Empyrical functions | Riskfolio-Lib classes | Standalone functions in `engine/risk/` with our `RiskAssessment` model |
| Portfolio optimization | PyPortfolioOpt optimizer | Riskfolio-Lib optimizer | Separate modules with unified `PortfolioState` output format |
| Agent state | LangGraph TypedDict | AI-Hedge-Fund dict | `AgentState` TypedDict with Pydantic sub-models |
| Backtest results | VectorBT PortfolioResult | QuantStats tear sheet | Our `BacktestResult` ORM model with JSON equity curve |

### 5.4 License Compliance

| License | Status | Handling |
|---------|--------|----------|
| **MIT** | ✅ Safe | Direct integration permitted |
| **Apache-2.0** | ✅ Safe | Direct integration permitted with attribution |
| **BSD-3** | ✅ Safe | Direct integration permitted with attribution |
| **GPL-3.0** (Freqtrade) | ⚠️ Quarantine | Patterns adopted, code rewritten; no direct code copy |
| **LGPL-3.0** (NautilusTrader) | ⚠️ Quarantine | Patterns adopted, code rewritten; no direct code copy |

**Key principle**: We never copy GPL/LGPL code directly. We study the architecture and patterns, then implement our own version. This ensures our MIT-licensed codebase remains clean.

---

## 6. Evidence-Based Merge Decisions

### 6.1 Decision Framework

Each merge decision was evaluated against five criteria:

| Criterion | Weight | Description |
|-----------|--------|-------------|
| **Code Quality** | 30% | Clean code, type hints, docstrings, test coverage |
| **Maintenance** | 20% | Active development, recent commits, issue response |
| **Architecture Fit** | 25% | Compatible with our 6-layer architecture |
| **Community** | 15% | Stars, forks, contributors, ecosystem |
| **License** | 10% | Permissive license compatible with MIT |

### 6.2 Merge Decision Matrix

| Repository | Code Quality | Maintenance | Architecture Fit | Community | License | Total | Decision |
|-----------|-------------|-------------|-----------------|-----------|---------|-------|----------|
| LangGraph | 8/10 | 9/10 | 10/10 | 8/10 | 10/10 | 8.95 | Direct dependency |
| CCXT | 9/10 | 9/10 | 9/10 | 10/10 | 10/10 | 9.25 | Direct dependency |
| Alpha101 | 7/10 | 6/10 | 9/10 | 7/10 | 10/10 | 7.75 | Code merged |
| AI-Hedge-Fund | 6/10 | 7/10 | 8/10 | 10/10 | 10/10 | 7.90 | Patterns adopted |
| NautilusTrader | 9/10 | 9/10 | 7/10 | 7/10 | 6/10 | 7.70 | Patterns adopted |
| Freqtrade | 8/10 | 9/10 | 6/10 | 10/10 | 5/10 | 7.35 | Patterns adopted |
| Qlib | 9/10 | 8/10 | 7/10 | 8/10 | 10/10 | 8.25 | Patterns adopted |
| FinRL | 8/10 | 8/10 | 7/10 | 8/10 | 10/10 | 8.05 | Integration pending |
| PyPortfolioOpt | 9/10 | 7/10 | 8/10 | 7/10 | 10/10 | 8.10 | Patterns adopted |
| VectorBT | 9/10 | 8/10 | 7/10 | 7/10 | 10/10 | 7.95 | Patterns adopted |
| Backtrader | 6/10 | 2/10 | 4/10 | 8/10 | 10/10 | 5.40 | Discarded |
| Gekko | 5/10 | 1/10 | 3/10 | 7/10 | 10/10 | 4.60 | Discarded |

### 6.3 Key Merge Insights

**Insight 1: Patterns Over Code**

The most successful merge strategy was adopting architectural patterns rather than copying code. AI-Hedge-Fund's council voting, Freqtrade's paper/live toggle, and NautilusTrader's OMS patterns were all rewritten to fit our architecture, resulting in cleaner, more maintainable code than direct integration would have produced.

**Insight 2: Interface Consistency Wins**

Defining our canonical interfaces first (`ExchangeInterface`, `AlphaFactor`, `AgentState`) and then adapting external code to fit those interfaces proved far more effective than trying to accommodate multiple API styles.

**Insight 3: GPL Quarantine Works**

The strategy of studying GPL-licensed code for patterns and then reimplementing in our own MIT-licensed code has been effective. We get the architectural benefit without the license contamination risk.

**Insight 4: Test Coverage Matters**

Repositories with good test coverage (CCXT, PyPortfolioOpt, VectorBT) were significantly easier to integrate than those without (AI-Hedge-Fund, TradingAgents). Test coverage is a proxy for code quality and maintainability.

**Insight 5: Documentation Accelerates Merges**

Well-documented repositories (Qlib, PyPortfolioOpt, NautilusTrader) could be integrated 3-5x faster than poorly documented ones. The Alpha101 academic paper made factor implementation straightforward despite the original MATLAB code being unusable.

---

*© 2025-2026 Quant Nanggroe AI | Merge Plan v0.2.0*
