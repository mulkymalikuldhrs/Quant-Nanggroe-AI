# Development Roadmap: Quant Nanggroe AI

**Version 15.3.0 | Four-Phase Development Plan**

This document outlines the four-phase development roadmap for the Quant Nanggroe AI monorepo. Each phase has clear deliverables, exit criteria, and risk gates.

---

## Phase I: Monorepo Migration

**Timeline: Weeks 1-3**
**Goal: Establish a clean, compiling monorepo from 23 independent repositories**

### 1.1 Deliverables

| Task | Description | Status |
|---|---|---|
| Repository merge | Git subtree merge all 23 repos into monorepo | Pending |
| pyproject.toml consolidation | Single Poetry configuration with all dependencies | Pending |
| package.json consolidation | Single Node.js configuration for frontend | Pending |
| Type system unification | All Pydantic models in `types.py`, TS interfaces in `types.ts` | Pending |
| Import path normalization | All `from quant_nanggroe_ai.xxx` imports resolve | Pending |
| Duplicate code removal | De-duplicate engines, types, config across packages | Pending |
| Pydantic v1→v2 migration | Upgrade all repos from Pydantic 1.x to 2.x | Pending |
| SQLAlchemy 1→2 migration | Upgrade all repos from SQLAlchemy 1.x to 2.x | Pending |

### 1.2 Detailed Steps

```
Week 1: Foundation
  ├── Create monorepo branch from quant-nanggroe-ai main
  ├── Execute git subtree add for active packages (10 repos)
  ├── Consolidate pyproject.toml (resolve version conflicts)
  ├── Run `poetry install` and fix all dependency errors
  └── Run `pytest` for each merged package

Week 2: Cleanup
  ├── Merge remaining packages (research + deprecated)
  ├── De-duplicate type definitions → shared-types
  ├── De-duplicate engine implementations → keep Python, remove TS duplicates
  ├── Remove deprecated packages from import paths
  └── Run `mypy --strict` and fix all type errors

Week 3: Validation
  ├── Full test suite passes (`pytest` across all packages)
  ├── Full lint passes (`ruff check .`)
  ├── Docker build succeeds (`docker-compose build`)
  ├── Frontend build succeeds (`npm run build`)
  ├── No circular imports (verify with `pydeps`)
  └── Create PR for review
```

### 1.3 Exit Criteria

- [ ] `poetry install` completes in a clean Python 3.12 environment
- [ ] `pytest` passes across all test suites with ≥80% coverage
- [ ] `mypy --strict src/` returns 0 errors
- [ ] `ruff check .` returns 0 violations
- [ ] `npm run build` completes for the frontend
- [ ] `docker-compose build` succeeds
- [ ] No `import` errors when running `python -c "from quant_nanggroe_ai import *"`

### 1.4 Risk Gates

| Risk | Mitigation |
|---|---|
| Dependency conflicts block `poetry install` | Pin to minimum compatible versions, upgrade incrementally |
| Pydantic v1→v2 migration breaks legacy repos | Keep legacy repos in deprecated state, don't import them |
| Circular import dependencies | Use lazy imports and `TYPE_CHECKING` pattern |
| Test failures in merged packages | Fix incrementally, mark known failures with `xfail` |

---

## Phase II: Event Bus Integration & State Graph Configuration

**Timeline: Weeks 4-7**
**Goal: Wire the dual-bus architecture and configure the LangGraph state machine**

### 2.1 Deliverables

| Task | Description | Status |
|---|---|---|
| Redis execution bus | Implement low-latency execution event bus via Redis Pub/Sub | Pending |
| Redis agent reasoning bus | Implement high-throughput agent event bus via Redis Pub/Sub | Pending |
| Bus bridge (Trader node) | Connect reasoning bus to execution bus in Trader node | Pending |
| YAML agent configuration | Load agent definitions from `config/agents.yaml` | Pending |
| YAML risk configuration | Load risk parameters from `config/risk.yaml` | Pending |
| YAML exchange configuration | Load exchange settings from `config/exchanges.yaml` | Pending |
| LangGraph conditional routing | Verify regime gate and risk gate routing | Pending |
| Audit trail integration | All events flow to PostgreSQL `audit_events` table | Pending |
| WebSocket real-time events | Stream agent state changes to frontend via WebSocket | Pending |

### 2.2 Detailed Steps

```
Week 4: Event Bus
  ├── Implement Redis Pub/Sub channels for execution bus
  │   ├── ORDER_NEW, ORDER_CANCEL, ORDER_FILL messages
  │   ├── KILL_SWITCH message
  │   └── POSITION_SYNC message
  ├── Implement Redis Pub/Sub channels for agent reasoning bus
  │   ├── AGENT_START, AGENT_COMPLETE, AGENT_ERROR messages
  │   ├── STATE_DELTA, REGIME_CHANGE messages
  │   └── PRESSURE_UPDATE, RISK_VETO messages
  └── Write bus integration tests

Week 5: State Graph Configuration
  ├── Implement YAML config loader for agent definitions
  ├── Implement YAML config loader for risk parameters
  ├── Implement YAML config loader for exchange routing
  ├── Verify LangGraph conditional routing:
  │   ├── should_continue_after_regime() → NO_TRADE/PANIC/RISK_OFF blocks
  │   └── should_continue_after_risk() → VETOED blocks
  └── Write configuration integration tests

Week 6: Audit & Observability
  ├── Implement structured audit event logging
  ├── All LangGraph state transitions → audit_events table
  ├── All risk checkpoint results → audit_events table
  ├── All execution results → audit_events table
  └── Implement audit trail query API

Week 7: Real-Time Streaming
  ├── WebSocket endpoint for agent state streaming
  ├── Frontend AgentHud subscription to reasoning bus
  ├── Frontend TradingTerminal subscription to execution bus
  ├── Frontend ControlCenter subscription to risk events
  └── End-to-end integration test: data → agent → decision → execution → UI
```

### 2.3 Exit Criteria

- [ ] Execution bus messages are delivered in < 10ms (local)
- [ ] Agent reasoning bus messages are delivered in < 5s
- [ ] YAML configuration loads without errors
- [ ] LangGraph conditional routing blocks correctly for NO_TRADE/PANIC/RISK_OFF regimes
- [ ] LangGraph conditional routing blocks correctly for VETOED risk
- [ ] All state transitions are persisted to `audit_events` table
- [ ] WebSocket delivers real-time updates to frontend
- [ ] Full pipeline test: symbol → researcher → analyst → strategist → risk → trader → portfolio

### 2.4 Risk Gates

| Risk | Mitigation |
|---|---|
| Redis Pub/Sub message loss | Enable AOF persistence, implement message ACK for execution bus |
| YAML configuration parsing errors | Pydantic validation with detailed error messages |
| WebSocket connection drops | Auto-reconnect with exponential backoff in frontend |
| Audit trail volume overwhelms PostgreSQL | Batch inserts, TimescaleDB compression, 90-day retention policy |

---

## Phase III: Sandbox Compilation & High-Frequency Execution Testing

**Timeline: Weeks 8-12**
**Goal: Validate execution fidelity under realistic conditions**

### 3.1 Deliverables

| Task | Description | Status |
|---|---|---|
| Kronos C++ compilation | Build Kronos execution engine with PyO3 bindings | Pending |
| Kronos-Python bridge test | Verify PyO3 bridge latency < 5ms | Pending |
| Paper trading integration | End-to-end paper trading on Binance testnet | Pending |
| Execution reality simulation | Validate slippage, spread, latency models against live data | Pending |
| Walk-forward validation | Walk-forward test across 12 months of historical data | Pending |
| Kill switch test | Trigger kill switch under controlled conditions | Pending |
| VaR/CVaR backtesting | Validate VaR and CVaR estimates against realized losses | Pending |
| Performance benchmark | Measure decision-to-execution latency under load | Pending |
| Docker security hardening | Apply `no-new-privileges`, `cap_drop ALL`, read-only filesystems | Pending |

### 3.2 Detailed Steps

```
Week 8-9: Kronos Integration
  ├── Build Kronos C++ library
  ├── Generate PyO3 bindings
  ├── Write Python wrapper for Kronos order submission
  ├── Benchmark: Python → PyO3 → C++ → Exchange round-trip
  └── Fallback: verify ccxt Python execution still works when Kronos unavailable

Week 10: Paper Trading
  ├── Configure Binance testnet API keys
  ├── Deploy paper trading configuration
  ├── Run 48-hour continuous paper trading session
  ├── Verify:
  │   ├── Orders submitted and filled correctly
  │   ├── Stop losses triggered correctly
  │   ├── Kill switch activates on daily loss limit
  │   └── Risk checkpoints VETO invalid trades
  └── Analyze paper trading results

Week 11: Execution Reality Validation
  ├── Compare backtested slippage model vs. actual slippage from paper trading
  ├── Compare backtested spread model vs. actual spread from paper trading
  ├── Compare backtested latency model vs. actual decision-to-execution latency
  ├── Adjust simulation parameters if deviation > 20%
  └── Re-run backtests with calibrated parameters

Week 12: Security & Performance
  ├── Docker security hardening
  │   ├── read_only: true on API container
  │   ├── security_opt: no-new-privileges
  │   ├── cap_drop: ALL (add back only NET_BIND_SERVICE)
  │   └── Resource limits (CPU, memory)
  ├── Performance benchmark
  │   ├── Single-symbol decision cycle: < 2s
  │   ├── Multi-symbol (5 symbols) parallel: < 5s
  │   ├── Execution bus message latency: < 10ms
  │   └── WebSocket update frequency: ≥ 1 Hz
  └── Penetration test checklist
```

### 3.3 Exit Criteria

- [ ] Kronos C++ compiles and PyO3 bridge latency < 5ms
- [ ] Paper trading runs continuously for 48 hours without crash
- [ ] Kill switch activates correctly when daily loss limit is reached
- [ ] All 9 risk checkpoints VETO invalid trades correctly
- [ ] Execution reality model deviation from paper trading < 20%
- [ ] Walk-forward Sharpe ratio ≥ 1.0 (risk-adjusted profitability threshold)
- [ ] VaR 95% confidence: realized losses exceed VaR < 5% of the time
- [ ] Docker containers run with `no-new-privileges` and dropped capabilities
- [ ] Single-symbol decision cycle completes in < 2 seconds

### 3.4 Risk Gates

| Risk | Mitigation |
|---|---|
| Kronos C++ compilation fails on target platform | Pre-built wheels via CI/CD, fallback to ccxt |
| Paper trading reveals systematic execution errors | Debug with audit trail, fix, re-test |
| Execution reality model is inaccurate | Recalibrate from paper trading data |
| Walk-forward Sharpe < 1.0 | Investigate factor decay, adjust strategy parameters |
| Kill switch fails to activate | Hard kill switch at OS level (SIGTERM handler) |

---

## Phase IV: Production Deployment & Live Trading

**Timeline: Weeks 13-16+**
**Goal: Deploy to production and enable live trading with controlled risk**

### 4.1 Deliverables

| Task | Description | Status |
|---|---|---|
| Production Docker images | Hardened, minimal Docker images for all services | Pending |
| Binance live trading | Live crypto trading on Binance with $500 initial capital | Pending |
| Bybit live trading | Live crypto trading on Bybit (secondary venue) | Pending |
| Kalshi live trading | Live prediction market trading on Kalshi | Pending |
| Polymarket live trading | Live prediction market trading on Polymarket | Pending |
| Monitoring & alerting | Prometheus metrics + Grafana dashboards + PagerDuty alerts | Pending |
| Disaster recovery | Automated backup, failover, and recovery procedures | Pending |
| Compliance documentation | Full risk disclosure, audit trail procedures, kill switch documentation | Pending |

### 4.2 Detailed Steps

```
Week 13: Production Infrastructure
  ├── Build hardened Docker images
  │   ├── Multi-stage build (builder → runtime)
  │   ├── Distroless base image
  │   └── Security scan with Trivy
  ├── Deploy to production server
  │   ├── PostgreSQL with TimescaleDB extension
  │   ├── Redis with AOF persistence and password
  │   ├── QuestDB for high-frequency time-series
  │   └── API server behind reverse proxy
  ├── Configure monitoring
  │   ├── Prometheus metrics endpoint
  │   ├── Grafana dashboards (PnL, positions, risk, agents)
  │   └── PagerDuty alerts for: kill switch, daily loss > 0.5%, API errors
  └── Smoke test all services

Week 14: Controlled Live Trading
  ├── Deploy with $500 initial capital
  ├── Feature flags:
  │   ├── ENABLE_LIVE_TRADING = true
  │   ├── ENABLE_PAPER_TRADING = false
  │   ├── ENABLE_KILL_SWITCH = true
  │   └── MAX_RISK_PER_TRADE = 0.005 (hardcoded)
  ├── Run with conservative settings for 72 hours:
  │   ├── Max 3 trades per day
  │   ├── Max 1 open position at a time
  │   ├── Daily loss limit: 1%
  │   └── All trades require both risk clearance AND portfolio approval
  ├── Monitor continuously:
  │   ├── Execution quality (slippage, fill rate)
  │   ├── Decision quality (win rate, R:R achieved)
  │   ├── System health (latency, error rate, memory)
  │   └── Risk metrics (VaR, CVaR, drawdown)
  └── Daily review and parameter adjustment

Week 15: Multi-Venue Expansion
  ├── Enable Bybit as secondary crypto venue
  ├── Enable Kalshi for prediction market trading
  ├── Enable Polymarket for prediction market trading
  ├── Cross-venue arbitrage detection (informational only)
  └── Portfolio-level risk management across all venues

Week 16: Scaling & Optimization
  ├── Increase capital allocation based on performance
  ├── Enable multi-position mode (max 3 concurrent)
  ├── Enable multi-symbol trading (BTC, ETH, SOL)
  ├── Walk-forward parameter updates
  └── Automated strategy lifecycle management (Darwinian)
```

### 4.3 Exit Criteria

- [ ] Live trading runs continuously for 30 days without system failure
- [ ] Daily loss limit (1%) is never breached
- [ ] Weekly loss limit (3%) is never breached
- [ ] Kill switch activates correctly within 5 seconds of limit breach
- [ ] All audit events are persisted and queryable
- [ ] VaR 95% backtest violation rate < 5%
- [ ] Monitoring dashboards are live and accurate
  - [ ] PagerDuty alerts fire for critical events
  - [ ] System survives container restart without data loss
- [ ] Full disaster recovery test passes (stop all containers → restore from backup → verify state)

### 4.4 Risk Gates

| Risk | Mitigation |
|---|---|
| Live trading loses more than daily limit | Kill switch auto-activates, manual review required to re-enable |
| Exchange API outage | AutoSwitch failover to backup provider, pause trading if no provider available |
| Private key leakage | Keys stored in environment variables only, Docker secrets, no logging |
| System crash during open position | Stop losses are exchange-side (GTC), not system-dependent |
| Regulatory compliance | Paper trading only until legal review complete, jurisdiction-specific controls |

### 4.5 Production Feature Flags

```python
# Production feature flags (configurable via environment)
class FeatureFlags(BaseSettings):
    paper_trading: bool = True        # Paper mode (default safe)
    live_trading: bool = False        # Live mode (requires explicit enable)
    agents: bool = True               # Enable agent reasoning
    backtest: bool = True             # Enable backtesting
    kill_switch: bool = True          # Kill switch always enabled
    autoswitch: bool = True           # Provider failover
```

**CRITICAL**: `ENABLE_LIVE_TRADING` defaults to `False`. Live trading requires explicit environment variable setting and is protected by the constitutional risk guard. No configuration change can disable the kill switch.

---

## Phase Summary

| Phase | Timeline | Key Milestone | Risk Level |
|---|---|---|---|
| I: Monorepo Migration | Weeks 1-3 | Clean compile, all tests pass | Medium (dependency conflicts) |
| II: Event Bus & State Graph | Weeks 4-7 | Dual-bus operational, audit trail complete | Low (well-understood patterns) |
| III: Sandbox & HFT Testing | Weeks 8-12 | Paper trading validated, kill switch tested | Medium (Kronos C++ complexity) |
| IV: Production Deployment | Weeks 13-16+ | Live trading with controlled risk | High (real capital at risk) |

### Go/No-Go Criteria Between Phases

Each phase transition requires explicit approval based on:

1. **All exit criteria met** — No partial completions
2. **No open P0/P1 bugs** — Critical issues must be resolved
3. **Test coverage ≥ 80%** — For the phase's deliverables
4. **Security review passed** — For infrastructure changes
5. **Documentation updated** — All changes reflected in docs/

---

© 2025-2026 Quant Nanggroe AI | Development Roadmap v15.3.0
