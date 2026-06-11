# Quant Nanggroe AI — Migration Plan

**Version 4.0.0 | 5-Phase Step-by-Step Migration**

> 5-phase migration plan with tasks, validation criteria, and rollback procedures for consolidating 21 repositories into a single production-grade monorepo.

---

## Table of Contents

1. [Migration Overview](#1-migration-overview)
2. [Phase 1: Foundation & Subtree Merge](#2-phase-1-foundation--subtree-merge)
3. [Phase 2: Code Integration & De-duplication](#3-phase-2-code-integration--de-duplication)
4. [Phase 3: Dependency Resolution & Testing](#4-phase-3-dependency-resolution--testing)
5. [Phase 4: Event Bus & API Integration](#5-phase-4-event-bus--api-integration)
6. [Phase 5: Production Readiness Validation](#6-phase-5-production-readiness-validation)
7. [Rollback Procedures](#7-rollback-procedures)
8. [Migration Timeline](#8-migration-timeline)

---

## 1. Migration Overview

### Migration Principles

1. **Never break the build** — Every phase must result in a compiling, passing system
2. **Incremental integration** — Merge one repo at a time, validate after each
3. **Preserve history** — Use `git subtree` to retain commit history
4. **Fail fast** — Surface import errors eagerly at startup, not at runtime
5. **Constitutional limits are immutable** — Risk constants must match across all modules

### Pre-Migration Checklist

- [x] Create target branch from `main`
- [x] Verify all existing tests pass (175+ tests)
- [ ] Complete dependency audit across all 21 repos
- [ ] Generate dependency graph before any code changes
- [ ] Backup all repository data

### Repository Classification

| Classification | Count | Action |
|---------------|-------|--------|
| Active — Full Integration | 16 | Merge code into `quant_nanggroe/` |
| Research — Reference Only | 2 | Archive in `contrib/` |
| Deprecated — Frozen | 3 | Freeze in `contrib/` with DEPRECATED.md |

---

## 2. Phase 1: Foundation & Subtree Merge

**Timeline: Week 1-2**
**Goal: Establish clean monorepo with all repos merged as subtrees**

### 2.1 Tasks

| Task ID | Task | Priority | Status | Validation |
|---------|------|----------|--------|------------|
| P1-001 | Create monorepo branch from `main` | P0 | Pending | Branch exists |
| P1-002 | Set up git remotes for all 21 repos | P0 | Pending | All remotes configured |
| P1-003 | Merge P0 repos (langgraph-trading, risk-guardian, alpha-factors, api-server) | P0 | Pending | `git subtree add` succeeds |
| P1-004 | Merge P1 repos (HermesQuantOS, market-data, execution-brokers, TradingAgents, ai-hedge-fund) | P1 | Pending | `git subtree add` succeeds |
| P1-005 | Merge P2 repos (pressure-engine, decision-engine, vibe-trading, vector-memory, shared-types) | P2 | Pending | `git subtree add` succeeds |
| P1-006 | Merge P3 repos (SolSniperX, Kronos, prediction-markets, dexter, OpenAlice) | P3 | Pending | `git subtree add` succeeds |
| P1-007 | Merge deprecated repos (FinceptTerminal, crewai-agents, autogen-workflows) | P3 | Pending | `git subtree add` succeeds |
| P1-008 | Consolidate `pyproject.toml` | P0 | Pending | `poetry install` succeeds |
| P1-009 | Consolidate `package.json` | P1 | Pending | `npm install` succeeds |
| P1-010 | Verify directory structure matches target | P0 | Pending | `ls -R` matches spec |

### 2.2 Detailed Steps — Week 1

```
Day 1-2: Foundation
  ├── Create branch `monorepo-migration` from main
  ├── Configure git remotes for all 21 repos
  ├── Execute `git subtree add` for P0 repos (4 repos)
  ├── Run `poetry install` and resolve dependency errors
  └── Run `pytest` for each P0 package

Day 3-4: P1 Repos
  ├── Execute `git subtree add` for P1 repos (5 repos)
  ├── Resolve any merge conflicts
  ├── Update pyproject.toml with new dependencies
  └── Run `pytest` for each P1 package

Day 5: P2 + P3 Repos
  ├── Execute `git subtree add` for P2 repos (5 repos)
  ├── Execute `git subtree add` for P3 repos (5 repos)
  ├── Execute `git subtree add` for deprecated repos (3 repos)
  └── Run `poetry install` and verify
```

### 2.3 Detailed Steps — Week 2

```
Day 6-7: Import Path Normalization
  ├── Update all `import xxx` → `from quant_nanggroe.xxx import ...`
  ├── Fix circular imports using `TYPE_CHECKING` pattern
  ├── Remove old `sys.path` hacks from legacy repos
  └── Verify all imports resolve: `python -c "from quant_nanggroe import *"`

Day 8-9: Configuration Consolidation
  ├── Merge all config files into single Settings hierarchy
  ├── Remove per-repo `config.py` files
  ├── Update environment variable prefixes
  └── Verify Settings loads: `python -c "from quant_nanggroe.config import get_settings"`

Day 10: Validation
  ├── Run full test suite: `pytest tests/ -v`
  ├── Run type checking: `mypy src/`
  ├── Run linting: `ruff check .`
  └── Create checkpoint commit
```

### 2.4 Exit Criteria

- [ ] All 21 repos merged as subtrees
- [ ] `poetry install` completes in clean Python 3.12 environment
- [ ] `python -c "from quant_nanggroe import *"` succeeds
- [ ] No import errors across the codebase
- [ ] `pytest` passes for all existing tests (≥175 tests)

---

## 3. Phase 2: Code Integration & De-duplication

**Timeline: Week 3-4**
**Goal: Extract useful code from subtrees, remove duplicates, normalize patterns**

### 3.1 Tasks

| Task ID | Task | Priority | Status | Validation |
|---------|------|----------|--------|------------|
| P2-001 | Extract `TradingGraph` from langgraph-trading → `agents/graph.py` | P0 | Pending | Graph compiles + runs |
| P2-002 | Extract `RiskCheckGate` from risk-guardian → `engine/risk/checks.py` | P0 | Pending | 9-checkpoint test passes |
| P2-003 | Extract `FactorRegistry` from alpha-factors → `engine/factors/registry.py` | P0 | Pending | `registry.health()["loaded"] >= 400` |
| P2-004 | Extract `ExchangeFactory` from execution-brokers → `exchange/factory.py` | P0 | Pending | `factory.create("binance")` works |
| P2-005 | Extract `CouncilDebate` from TradingAgents → `agents/council/debate.py` | P1 | Pending | Debate runs without errors |
| P2-006 | Extract stress test from ai-hedge-fund → `engine/risk/manager.py` | P1 | Pending | `rm.stress_test(returns)` returns dict |
| P2-007 | De-duplicate market data tools | P1 | Pending | Single `MarketDataTool` class |
| P2-008 | De-duplicate sentiment tools | P2 | Pending | Single `SentimentTool` class |
| P2-009 | De-duplicate risk checks | P0 | Pending | Single `RiskCheckGate` with 9 checkpoints |
| P2-010 | De-duplicate exchange connectors | P0 | Pending | Single `CCXTBroker` + `ExchangeFactory` |
| P2-011 | De-duplicate config loading | P1 | Pending | Single `Settings` class |
| P2-012 | De-duplicate logging setup | P2 | Pending | Single `structlog` config |
| P2-013 | De-duplicate type definitions | P0 | Pending | Single `AgentState` + Pydantic models |
| P2-014 | Port Vibe-Trading factors → `engine/factors/academic.py` | P2 | Pending | Factors register in `FactorRegistry` |
| P2-015 | Port Polymarket adapter → `exchange/polymarket_broker.py` | P3 | Pending | Broker creates + validates |

### 3.2 De-duplication Execution Order

```
Step 1: Type System Unification
  ├── Merge all type definitions into agents/state.py
  ├── Remove duplicate Pydantic models from contrib/
  ├── All other packages import from quant_nanggroe.agents.state
  └── Validate: mypy passes with no "duplicate definition" errors

Step 2: Engine Consolidation
  ├── Keep Python risk engine (engine/risk/)
  ├── Keep Python factor engine (engine/factors/)
  ├── Remove TypeScript engine duplicates (if any)
  ├── Verify test parity between implementations
  └── Validate: pytest passes for all engine tests

Step 3: Exchange Layer Unification
  ├── Keep CCXTBroker as the single exchange adapter
  ├── Keep ExchangeFactory for dynamic creation
  ├── Remove per-repo ccxt wrappers
  └── Validate: factory.create() works for all 8 exchanges

Step 4: Tool Consolidation
  ├── Merge all agent tools into agents/tools/
  ├── Remove duplicate MarketDataTool, SentimentTool, etc.
  └── Validate: all agent tools accessible from registry
```

### 3.3 Exit Criteria

- [ ] No duplicate class definitions across the codebase
- [ ] `FactorRegistry.health()["loaded"] >= 400` (469 target)
- [ ] `ExchangeFactory.list_supported_exchanges()` returns 8 exchanges
- [ ] `RiskCheckGate.evaluate()` runs all 9 checkpoints
- [ ] `CouncilDebate.run_full_debate()` completes without errors
- [ ] All imports resolve through `quant_nanggroe.xxx`

---

## 4. Phase 3: Dependency Resolution & Testing

**Timeline: Week 5-6**
**Goal: Resolve all dependency conflicts, achieve green test suite**

### 4.1 Tasks

| Task ID | Task | Priority | Status | Validation |
|---------|------|----------|--------|------------|
| P3-001 | Upgrade Pydantic v1 → v2 across all code | P0 | Pending | `mypy` passes |
| P3-002 | Upgrade SQLAlchemy 1.x → 2.x | P1 | Pending | DB queries work |
| P3-003 | Upgrade numpy to 2.1+ | P1 | Pending | Factor computation works |
| P3-004 | Upgrade ccxt to 4.4+ | P1 | Pending | Exchange connections work |
| P3-005 | Upgrade langchain to 0.3+ | P1 | Pending | LLM calls work |
| P3-006 | Upgrade pandas to 2.2+ | P2 | Pending | Data processing works |
| P3-007 | Fix all `mypy --strict` errors | P0 | Pending | `mypy` returns 0 errors |
| P3-008 | Fix all `ruff check` violations | P0 | Pending | `ruff` returns 0 violations |
| P3-009 | Write missing tests for new integrations | P1 | Pending | Coverage ≥ 80% |
| P3-010 | Validate constitutional limits match across modules | P0 | Pending | `constants.py` == `state.py` values |
| P3-011 | Run full integration test | P0 | Pending | End-to-end pipeline works |

### 4.2 Dependency Upgrade Order

```
Phase 3a: Core Dependencies
  ├── Upgrade Pydantic (most breaking changes)
  ├── Fix all @validator → @field_validator
  ├── Fix all class Config → model_config = ConfigDict(...)
  └── Run pytest after each upgrade

Phase 3b: Data Dependencies
  ├── Upgrade numpy, pandas
  ├── Fix any deprecated numpy API calls
  └── Verify factor computations produce same results

Phase 3c: API Dependencies
  ├── Upgrade ccxt, fastapi, sqlalchemy
  ├── Fix SQLAlchemy 1→2 query patterns
  └── Verify API endpoints work

Phase 3d: AI Dependencies
  ├── Upgrade langchain, langgraph
  ├── Fix any deprecated LangChain API calls
  └── Verify LLM integration works
```

### 4.3 Exit Criteria

- [ ] `poetry install` completes without errors in clean env
- [ ] `pytest` passes across all test suites (≥175 tests + new tests)
- [ ] `mypy --strict src/` returns 0 errors
- [ ] `ruff check .` returns 0 violations
- [ ] Constitutional limits match between `constants.py` and `state.py`
- [ ] `FactorRegistry.health()["failed"] == 0`
- [ ] `ExchangeFactory.list_supported_exchanges()` returns 8+ exchanges
- [ ] End-to-end pipeline runs: symbols → analysis → signal → risk → execution

---

## 5. Phase 4: Event Bus & API Integration

**Timeline: Week 7-8**
**Goal: Wire dual-bus architecture, API routes, and WebSocket streaming**

### 5.1 Tasks

| Task ID | Task | Priority | Status | Validation |
|---------|------|----------|--------|------------|
| P4-001 | Implement Redis execution bus | P0 | Pending | Messages delivered < 10ms |
| P4-002 | Implement Redis agent reasoning bus | P1 | Pending | Messages delivered < 5s |
| P4-003 | Wire API routes (6 groups) | P0 | Pending | All endpoints respond |
| P4-004 | Implement WebSocket streaming | P1 | Pending | Real-time updates work |
| P4-005 | Implement audit trail (PostgreSQL) | P1 | Pending | All events persisted |
| P4-006 | Implement structured logging (structlog) | P2 | Pending | All events logged with context |
| P4-007 | Docker Compose full stack | P0 | Pending | All services start |
| P4-008 | Frontend builds + connects to API | P1 | Pending | Dashboard loads |

### 5.2 API Route Validation

```bash
# Health check
curl http://localhost:8000/health
# → {"status": "healthy", "service": "quant-nanggroe-ai"}

# Market data
curl http://localhost:8000/api/market/ohlcv?symbol=BTCUSDT&timeframe=1h

# Agent status
curl http://localhost:8000/api/agents/status

# Portfolio state
curl http://localhost:8000/api/portfolio/state

# Risk status
curl http://localhost:8000/api/trading/risk-status
```

### 5.3 Exit Criteria

- [ ] All 6 API route groups respond to requests
- [ ] WebSocket delivers real-time agent state updates
- [ ] Redis execution bus delivers messages in < 10ms
- [ ] PostgreSQL audit_events table records all state transitions
- [ ] `docker-compose up` starts all services without errors
- [ ] Frontend builds and connects to backend

---

## 6. Phase 5: Production Readiness Validation

**Timeline: Week 9-10**
**Goal: Validate the complete system under realistic conditions**

### 6.1 Tasks

| Task ID | Task | Priority | Status | Validation |
|---------|------|----------|--------|------------|
| P5-001 | Run 48-hour paper trading session | P0 | Pending | No crashes, orders fill correctly |
| P5-002 | Validate kill switch activation | P0 | Pending | Kill switch activates on limit breach |
| P5-003 | Validate 9-checkpoint risk gate | P0 | Pending | All checkpoints VETO invalid trades |
| P5-004 | Validate council debate mechanism | P1 | Pending | Debate produces structured decisions |
| P5-005 | Performance benchmark: decision cycle < 2s | P1 | Pending | Measured latency |
| P5-006 | Performance benchmark: multi-symbol < 5s | P2 | Pending | 5 symbols parallel |
| P5-007 | Docker security hardening | P1 | Pending | `no-new-privileges`, `cap_drop ALL` |
| P5-008 | Walk-forward validation (12 months) | P1 | Pending | Sharpe ≥ 1.0 |
| P5-009 | VaR backtesting (95% confidence) | P1 | Pending | Violation rate < 5% |
| P5-010 | Stress test (6 scenarios) | P2 | Pending | All scenarios produce results |

### 6.2 Paper Trading Validation Checklist

```
48-Hour Paper Trading Session:
  ├── Deploy with PaperExchangeBroker
  ├── Initial capital: $100,000
  ├── Symbols: BTCUSDT, ETHUSDT, SOLUSDT
  ├── Monitor:
  │   ├── Orders submitted and filled correctly
  │   ├── Stop losses triggered correctly
  │   ├── Kill switch activates at daily loss limit
  │   ├── Risk checkpoints VETO invalid trades
  │   ├── Council debate triggers on low confidence
  │   └── Factor computation produces valid signals
  ├── Verify:
  │   ├── No unhandled exceptions in logs
  │   ├── All audit events persisted
  │   ├── WebSocket updates reach frontend
  │   └── Memory system stores + retrieves episodes
  └── Document results
```

### 6.3 Exit Criteria

- [ ] Paper trading runs continuously for 48 hours without crash
- [ ] Kill switch activates correctly when daily loss limit is reached
- [ ] All 9 risk checkpoints VETO invalid trades correctly
- [ ] Council debate produces structured decisions
- [ ] Single-symbol decision cycle completes in < 2 seconds
- [ ] Walk-forward Sharpe ratio ≥ 1.0
- [ ] VaR 95% confidence: realized losses exceed VaR < 5% of the time
- [ ] Docker containers run with security hardening

---

## 7. Rollback Procedures

### 7.1 Per-Phase Rollback

| Phase | Rollback Strategy |
|-------|------------------|
| Phase 1 | `git revert` the subtree merge commit; fix conflicts in separate branch |
| Phase 2 | `git checkout` specific files from pre-dedup commit |
| Phase 3 | `poetry lock --no-update` to restore previous lock file |
| Phase 4 | Disable Redis bus; fall back to direct API calls |
| Phase 5 | Stop paper trading; review audit trail for root cause |

### 7.2 Emergency Rollback Script

```bash
#!/bin/bash
# rollback_migration.sh
set -euo pipefail

echo "CRITICAL BUILD FAILURE. INITIALIZING ROLLBACK..."

# Reset to pre-merge state
git reset --hard HEAD
git clean -fd

# Remove temporary remotes
for REMOTE in $(git remote | grep "^temp_"); do
  git remote remove "$REMOTE"
done

# Force checkout last known good commit
git checkout -B stable-recovery origin/main

echo "ROLLBACK COMPLETE. System returned to stable recovery point."
```

### 7.3 Rollback Triggers

| Trigger | Action |
|---------|--------|
| `poetry install` fails | Rollback to previous `pyproject.toml` + `poetry.lock` |
| `pytest` failure rate > 20% | Rollback to last passing commit |
| Import cycle detected | Rollback to pre-import-normalization commit |
| Constitutional limits mismatch | STOP. Fix immediately. No rollback — this is a safety issue. |
| API endpoint returns 500 | Rollback to previous API commit |
| Paper trading crashes | Rollback to last stable build |

---

## 8. Migration Timeline

| Phase | Week | Key Milestone | Risk Level | Go/No-Go |
|-------|------|---------------|------------|----------|
| Phase 1 | 1-2 | All subtrees merged, imports resolve | Medium (dependency conflicts) | All exit criteria met |
| Phase 2 | 3-4 | Code integrated, duplicates removed | Medium (breaking changes) | No duplicate classes |
| Phase 3 | 5-6 | All tests green, type checking passes | High (Pydantic v1→v2) | `mypy --strict` passes |
| Phase 4 | 7-8 | API + event bus operational | Low (well-understood patterns) | All API endpoints work |
| Phase 5 | 9-10 | Paper trading validated | Medium (real conditions) | 48-hour session passes |

### Phase Transition Criteria

Each phase transition requires:
1. **All exit criteria met** — No partial completions
2. **No open P0/P1 bugs** — Critical issues must be resolved
3. **Test coverage ≥ 80%** — For the phase's deliverables
4. **Security review passed** — For infrastructure changes
5. **Documentation updated** — All changes reflected in docs/

---

*© 2025-2026 Quant Nanggroe AI | Migration Plan v4.0.0*
