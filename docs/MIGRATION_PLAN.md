# Quant Nanggroe AI — Migration Plan

**Version 4.0.0 | Step-by-Step Migration Guide**

> This document provides a detailed step-by-step migration plan for consolidating 20+ repositories into the Quant Nanggroe AI monorepo, covering each phase, rollback procedures, and testing requirements.

---

## Table of Contents

1. [Migration Overview](#1-migration-overview)
2. [Phase 1: Foundation (Complete)](#2-phase-1-foundation-complete)
3. [Phase 2: Core Engines (Complete)](#3-phase-2-core-engines-complete)
4. [Phase 3: Agent Implementations (In Progress)](#4-phase-3-agent-implementations-in-progress)
5. [Phase 4: Exchange Integration (Planned)](#5-phase-4-exchange-integration-planned)
6. [Phase 5: Production Hardening (Planned)](#6-phase-5-production-hardening-planned)
7. [Rollback Procedures](#7-rollback-procedures)
8. [Testing Requirements per Phase](#8-testing-requirements-per-phase)
9. [Migration Checklist](#9-migration-checklist)
10. [Risk Mitigation During Migration](#10-risk-mitigation-during-migration)

---

## 1. Migration Overview

### Migration Philosophy

1. **Never break the build** — Every phase must leave the system in a working state
2. **Tests are the safety net** — All 2504+ tests must pass at every step
3. **Incremental migration** — Small, reviewable changes
4. **Rollback always possible** — Every change can be reverted
5. **Constitutional limits never compromised** — Risk engine integrity at all times

### Migration Statistics

| Phase | Status | Repos | Modules | Tests | Duration |
|---|---|---|---|---|---|
| Phase 1: Foundation | ✅ Complete | 4 | 60+ | 800+ | 4 weeks |
| Phase 2: Core Engines | ✅ Complete | 4 | 50+ | 700+ | 3 weeks |
| Phase 3: Agent Implementations | 🔄 In Progress | 4 | 40+ | 500+ | 3 weeks |
| Phase 4: Exchange Integration | 📋 Planned | 4 | 30+ | 300+ | 2 weeks |
| Phase 5: Production Hardening | 📋 Planned | 5 | 34+ | 204+ | 2 weeks |

---

## 2. Phase 1: Foundation (Complete)

**Timeline**: Weeks 1-4
**Status**: ✅ Complete
**Repositories**: AutoTrader, HermesQuantOS, TradingAgents, Vibe-Trading

### Step 1.1: Monorepo Structure Setup

**Objective**: Create the `quant_nanggroe` package structure.

**Tasks**:
- [x] Create package directory structure
- [x] Set up `pyproject.toml` with dependencies
- [x] Configure ruff, mypy, pytest
- [x] Set up CI pipeline
- [x] Create initial `__init__.py` files

**Validation**:
```bash
pip install -e ".[dev]"
pytest tests/  # Should find and run initial tests
ruff check quant_nanggroe/
mypy quant_nanggroe/
```

### Step 1.2: State and Type System

**Objective**: Define `AgentState` TypedDict and all supporting models.

**Tasks**:
- [x] Define `AgentState` TypedDict in `agents/state.py`
- [x] Define all Pydantic models (Signal, Decision, RiskAssessment, etc.)
- [x] Define all enumerations (TradeAction, RiskVerdict, AssetClass, etc.)
- [x] Define constitutional risk limits as hardcoded constants
- [x] Implement `create_initial_state()` factory

**Source Files**:
- `quant_nanggroe/agents/state.py` — All state definitions
- `quant_nanggroe/engine/risk/constants.py` — Risk constants

**Validation**:
```python
from quant_nanggroe.agents.state import AgentState, create_initial_state
state = create_initial_state(["AAPL"], "2025-01-01")
assert state["symbols"] == ["AAPL"]
assert state["risk_verdict"] == "VETOED"
assert state["metadata"]["constitutional_limits"]["override_possible"] is False
```

### Step 1.3: LangGraph Graph (v1)

**Objective**: Implement the v1 trading graph.

**Tasks**:
- [x] Create `TradingGraph` class with StateGraph
- [x] Implement market_analysis node
- [x] Implement signal_generation node
- [x] Implement risk_assessment node
- [x] Implement portfolio_optimization node
- [x] Implement execution_decision node
- [x] Implement order_execution node
- [x] Implement reflection node
- [x] Implement council_debate node
- [x] Implement emergency_exit node
- [x] Add conditional edges for risk routing
- [x] Add `run()` and `run_stream()` methods

**Source Files**:
- `quant_nanggroe/agents/graph.py` — v1 trading graph

**Validation**:
```python
from quant_nanggroe.agents.graph import TradingGraph
graph = TradingGraph(llm_provider="openai", deep_think_model="gpt-4o")
# Note: Requires API key for full test
# Unit tests verify graph structure without LLM calls
```

### Step 1.4: Risk Engine Foundation

**Objective**: Port HermesQuantOS risk framework.

**Tasks**:
- [x] Implement `RiskCheckGate` with 9 checkpoints
- [x] Implement `KillSwitch` with auto-activation
- [x] Implement `DrawdownMonitor`
- [x] Implement `CorrelationMonitor`
- [x] Implement `VaRCalculator`
- [x] Implement `KellyCriterion`
- [x] Implement `RiskManager` top-level class
- [x] Port constitutional constants

**Source Files**:
- `quant_nanggroe/engine/risk/constants.py`
- `quant_nanggroe/engine/risk/checks.py`
- `quant_nanggroe/engine/risk/kill_switch.py`
- `quant_nanggroe/engine/risk/drawdown.py`
- `quant_nanggroe/engine/risk/correlation.py`
- `quant_nanggroe/engine/risk/var.py`
- `quant_nanggroe/engine/risk/kelly.py`
- `quant_nanggroe/engine/risk/manager.py`

**Validation**:
```python
from quant_nanggroe.engine.risk.manager import RiskManager
rm = RiskManager()
result = rm.check_trade(
    symbol="AAPL", direction="BUY", lot_size=0.1,
    entry=150.0, stop_loss=148.0, account_balance=1_000_000
)
assert result["verdict"] in ("APPROVED", "VETOED")
# VETOED if any checkpoint fails (e.g., risk:reward < 1:2)
```

### Step 1.5: Factor Engine Foundation

**Objective**: Port Vibe-Trading factor zoos.

**Tasks**:
- [x] Implement `AlphaFactor` base class
- [x] Implement `FactorMeta` metadata class
- [x] Implement `FactorHandle` unified wrapper
- [x] Implement `FactorRegistry` with discovery
- [x] Port Alpha101 (101 factors)
- [x] Port GTJA191 (191 factors)
- [x] Port Qlib158 (158 factors)
- [x] Port Academic factors
- [x] Implement technical factors (class-based)
- [x] Implement fundamental factors (class-based)
- [x] Implement Barra factors
- [x] Add output validation (no inf, < 95% NaN)
- [x] Add thread-safe singleton

**Source Files**:
- `quant_nanggroe/engine/factors/base.py`
- `quant_nanggroe/engine/factors/registry.py`
- `quant_nanggroe/engine/factors/alpha101.py`
- `quant_nanggroe/engine/factors/gtja191.py`
- `quant_nanggroe/engine/factors/qlib158.py`
- `quant_nanggroe/engine/factors/academic.py`
- `quant_nanggroe/engine/factors/technical.py`
- `quant_nanggroe/engine/factors/fundamental.py`
- `quant_nanggroe/engine/factors/barra.py`
- `quant_nanggroe/engine/factors/pipeline.py`

**Validation**:
```python
from quant_nanggroe.engine.factors.registry import get_default_registry
registry = get_default_registry()
health = registry.health()
assert health["loaded"] >= 469
assert health["failed"] == 0
```

---

## 3. Phase 2: Core Engines (Complete)

**Timeline**: Weeks 5-7
**Status**: ✅ Complete
**Repositories**: AI-Trader, AutoHedge, QuantDinger, SolSniperX

### Step 2.1: Agent Factory and Base Agent

**Tasks**:
- [x] Implement `create_llm()` with multi-provider support
- [x] Implement `AgentFactory` with agent creation
- [x] Implement base agent class with tool binding
- [x] Add agent role registration

### Step 2.2: Researcher Agent

**Tasks**:
- [x] Port market data analysis from AI-Trader
- [x] Implement researcher-specific tools
- [x] Write researcher system prompt
- [x] Add market data and sentiment tools

### Step 2.3: Solana Module

**Tasks**:
- [x] Port Jupiter swap aggregator from SolSniperX
- [x] Port RugCheck token safety from SolSniperX
- [x] Port wallet management from SolSniperX
- [x] Port mempool monitoring from SolSniperX
- [x] Create Solana broker

### Step 2.4: Risk Parity and Hedging

**Tasks**:
- [x] Port risk parity from AutoHedge
- [x] Port correlation algorithms from AutoHedge
- [x] Implement risk parity optimizer
- [x] Implement mean-variance optimizer
- [x] Implement equal volatility optimizer

### Step 2.5: Backtest Engine

**Tasks**:
- [x] Implement core backtesting engine
- [x] Implement Monte Carlo simulation
- [x] Implement walk-forward optimization
- [x] Implement multi-asset engines (equity, crypto, forex, futures)
- [x] Implement execution simulation (slippage, partial fills)
- [x] Implement data loaders (yfinance, CCXT)
- [x] Implement portfolio optimizers

---

## 4. Phase 3: Agent Implementations (In Progress)

**Timeline**: Weeks 8-10
**Status**: 🔄 In Progress
**Repositories**: FinceptTerminal, OpenAlice, Misi-Screener, PromptForgeAI

### Step 3.1: v2 Graph Architecture

**Tasks**:
- [x] Implement `TradingGraphV2` with multi-path routing
- [x] Implement `AssetRouter` node
- [x] Implement 4 execution paths (crypto, forex, equity, prediction_market)
- [x] Implement `PositionSizer` node with ATR + TP1/TP2/TP3
- [x] Implement `PortfolioValidator` node
- [x] Implement `SmartExecutor` node
- [x] Implement `HumanCheckpoint` node
- [x] Add portfolio validation conditional edges
- [x] Add human checkpoint conditional edges

### Step 3.2: Crypto Agent

**Tasks**:
- [x] Implement crypto agent with Solana tools
- [x] Write crypto-specific system prompt
- [x] Add on-chain analysis tools
- [x] Add DEX monitoring capabilities

### Step 3.3: Forex Agent

**Tasks**:
- [x] Implement forex agent with FX-specific tools
- [x] Write forex-specific system prompt
- [x] Add carry trade calculator
- [x] Add central bank policy tracker

### Step 3.4: Macro Agent

**Tasks**:
- [x] Implement macro agent for regime detection
- [x] Write macro-specific system prompt
- [x] Add FRED economic data tools
- [x] Add market regime classification

### Step 3.5: Council Debate Enhancement

**Tasks**:
- [x] Port bull/bear debate from TradingAgents
- [x] Port risk debate (conservative/neutral/aggressive)
- [x] Implement council voting with weighted scores
- [x] Add consensus threshold and human review trigger

### Step 3.6: API Layer (from FinceptTerminal)

**Tasks**:
- [x] Implement FastAPI application
- [x] Add CORS middleware
- [x] Implement market data route
- [x] Implement trading route
- [x] Implement agents route
- [x] Implement backtest route
- [x] Implement portfolio route
- [x] Implement WebSocket route
- [x] Add health check endpoint
- [x] Add global exception handler

### Step 3.7: Remaining Agent Prompts (from PromptForgeAI)

**Tasks**:
- [ ] Optimize researcher prompts
- [ ] Optimize strategist prompts
- [ ] Optimize risk agent prompts
- [ ] Add chain-of-thought patterns
- [ ] A/B test prompt variations

---

## 5. Phase 4: Exchange Integration (Planned)

**Timeline**: Weeks 11-12
**Status**: 📋 Planned
**Repositories**: Clipper-AI, Kronos, Pentaract, ZeroInject

### Step 4.1: Exchange Factory Enhancement

**Tasks**:
- [ ] Add remaining exchange configurations
- [ ] Implement exchange health monitoring
- [ ] Add automatic failover between exchanges
- [ ] Implement rate limit management per exchange
- [ ] Add exchange-specific error handling

### Step 4.2: Smart Order Routing Enhancement

**Tasks**:
- [ ] Implement real-time venue scoring with live data
- [ ] Add liquidity-based routing
- [ ] Implement TWAP/VWAP order splitting
- [ ] Add dark pool routing (where available)
- [ ] Implement cross-exchange arbitrage detection

### Step 4.3: Paper Trading Enhancement

**Tasks**:
- [ ] Add realistic slippage model
- [ ] Add partial fill simulation
- [ ] Add order rejection simulation
- [ ] Add latency simulation
- [ ] Implement paper trading dashboard

### Step 4.4: Exchange Testing

**Tasks**:
- [ ] Integration tests for each exchange
- [ ] Rate limit testing
- [ ] Error handling testing
- [ ] WebSocket reconnection testing
- [ ] Order lifecycle testing

---

## 6. Phase 5: Production Hardening (Planned)

**Timeline**: Weeks 13-14
**Status**: 📋 Planned
**Repositories**: Crucix, QuantMuse, Dhaher-Corporation, MoneyPrinterTurbo, Trading-Plan-AI-Interactive

### Step 5.1: Security Hardening

**Tasks**:
- [ ] Implement API key authentication
- [ ] Add JWT token management
- [ ] Implement role-based access control
- [ ] Add credential leak prevention
- [ ] Implement audit logging
- [ ] Add rate limiting per user

### Step 5.2: Monitoring and Observability

**Tasks**:
- [ ] Add Prometheus metrics export
- [ ] Add structured logging (JSON format)
- [ ] Implement health check endpoints
- [ ] Add performance profiling
- [ ] Implement alert rules for risk limits

### Step 5.3: Performance Optimization

**Tasks**:
- [ ] Profile and optimize factor computation
- [ ] Add caching for frequently computed factors
- [ ] Optimize database queries
- [ ] Add connection pooling for exchanges
- [ ] Implement async exchange operations

### Step 5.4: Documentation

**Tasks**:
- [ ] Complete API documentation (OpenAPI)
- [ ] Write deployment guide
- [ ] Write operations runbook
- [ ] Write incident response procedures
- [ ] Add inline code documentation

### Step 5.5: Deployment Preparation

**Tasks**:
- [ ] Create Docker images
- [ ] Set up Kubernetes manifests
- [ ] Configure CI/CD pipeline
- [ ] Set up staging environment
- [ ] Create production deployment playbook

---

## 7. Rollback Procedures

### Rollback Principles

1. **Every merge is a git commit** — Can always `git revert`
2. **Tests are the safety net** — If tests fail, don't merge
3. **Feature flags for risky changes** — Can disable without revert
4. **Database migrations are reversible** — Always provide down migration

### Rollback Procedures by Phase

| Phase | Rollback Trigger | Procedure |
|---|---|---|
| Phase 1 | Core state/types broken | `git revert` to last working commit |
| Phase 2 | Factor/risk engine broken | Disable new factors, fall back to v1 |
| Phase 3 | Agent outputs invalid | Disable failing agent, use fallback |
| Phase 4 | Exchange connection broken | Route to paper broker, log error |
| Phase 5 | Security vulnerability | Disable affected endpoint, patch |

### Emergency Rollback

```bash
# Find the last working commit
git log --oneline -10

# Revert to that commit
git revert <commit-hash>

# Or, hard reset (destructive)
git reset --hard <commit-hash>

# Re-run tests to verify
pytest tests/ -x
```

### Kill Switch Rollback

If the kill switch triggers incorrectly:
1. Review the trigger reason in logs
2. Verify the PnL/drawdown calculations
3. If false positive, manual reset via `kill_switch.deactivate()`
4. Adjust thresholds only via code change (constitutional)

---

## 8. Testing Requirements per Phase

### Test Categories

| Category | Description | Coverage Target |
|---|---|---|
| **Unit tests** | Individual function/class testing | 90%+ |
| **Integration tests** | Multi-component testing | 80%+ |
| **End-to-end tests** | Full pipeline testing | Key scenarios |
| **Performance tests** | Latency/throughput testing | Benchmarks |
| **Security tests** | Vulnerability scanning | Critical paths |

### Phase-Specific Test Requirements

#### Phase 1 Tests

| Test | Count | Description |
|---|---|---|
| State model tests | 50+ | AgentState, all Pydantic models |
| Risk engine tests | 100+ | 9 checkpoints, kill switch, VaR, Kelly |
| Factor tests | 200+ | All 469+ factors compute correctly |
| Graph structure tests | 30+ | Nodes, edges, conditional routing |

#### Phase 2 Tests

| Test | Count | Description |
|---|---|---|
| Agent factory tests | 20+ | Agent creation, LLM routing |
| Researcher agent tests | 30+ | Market analysis, tool usage |
| Solana module tests | 40+ | Jupiter, RugCheck, wallet |
| Backtest engine tests | 100+ | Multi-asset, execution simulation |

#### Phase 3 Tests

| Test | Count | Description |
|---|---|---|
| v2 graph tests | 50+ | Multi-path routing, position sizing |
| Crypto/Forex agent tests | 40+ | Asset-specific analysis |
| Council debate tests | 30+ | Bull/bear, risk debate, voting |
| API endpoint tests | 50+ | All routes, WebSocket |

#### Phase 4 Tests

| Test | Count | Description |
|---|---|---|
| Exchange integration tests | 60+ | All 10 exchanges |
| Smart routing tests | 30+ | Venue scoring, order routing |
| Paper trading tests | 20+ | Realistic simulation |
| Failover tests | 20+ | Exchange failover scenarios |

#### Phase 5 Tests

| Test | Count | Description |
|---|---|---|
| Security tests | 40+ | Auth, key vault, audit |
| Performance tests | 30+ | Factor computation, API latency |
| Deployment tests | 20+ | Docker, Kubernetes |
| End-to-end tests | 20+ | Full production scenarios |

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific category
pytest tests/ -m "not slow" -v
pytest tests/ -m integration -v

# Run with coverage
pytest tests/ --cov=quant_nanggroe --cov-report=html

# Run specific module
pytest tests/test_risk.py -v
pytest tests/test_factors.py -v

# Type checking
mypy quant_nanggroe/

# Linting
ruff check quant_nanggroe/
```

---

## 9. Migration Checklist

### Pre-Migration

- [ ] Backup all source repositories
- [ ] Create migration branch
- [ ] Set up CI pipeline
- [ ] Review all dependencies
- [ ] Create test plan

### During Migration

- [ ] All tests pass at every step
- [ ] No circular imports introduced
- [ ] Constitutional limits verified
- [ ] Documentation updated
- [ ] Code reviewed

### Post-Migration

- [ ] Full test suite passes (2504+)
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Performance benchmarks met
- [ ] Security scan clean
- [ ] API backward compatible
- [ ] Documentation complete

---

## 10. Risk Mitigation During Migration

### Migration Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Breaking existing tests** | Medium | High | Run full test suite after every change |
| **Circular imports** | Medium | Medium | Check imports with every module addition |
| **Data model conflicts** | High | High | Unified AgentState TypedDict |
| **Dependency version conflicts** | Medium | Medium | Pin all versions in pyproject.toml |
| **Performance regression** | Low | High | Benchmark after every phase |
| **Security vulnerability** | Low | Critical | Security scan after every phase |
| **Risk engine bypass** | Very Low | Critical | Constitutional limits are hardcoded |

### Continuous Validation

Every commit must pass:

```bash
# 1. Lint
ruff check quant_nanggroe/

# 2. Type check
mypy quant_nanggroe/

# 3. Test
pytest tests/ -x --tb=short

# 4. Security
python -m quant_nanggroe.security.credential_inference

# 5. Factor health
python -c "from quant_nanggroe.engine.factors.registry import get_default_registry; print(get_default_registry().health())"
```

---

© 2025-2026 Quant Nanggroe AI | Migration Plan v4.0.0
