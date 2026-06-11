# Quant Nanggroe AI — Risk Register

**Version 4.0.0 | 25+ Risks Across 8 Categories**

> Comprehensive risk register identifying 25+ operational, technical, and strategic risks with mitigation strategies, residual risk assessments, and implementation status.

---

## Table of Contents

1. [Risk Summary Matrix](#1-risk-summary-matrix)
2. [Execution Risks](#2-execution-risks)
3. [Security Risks](#3-security-risks)
4. [Reliability Risks](#4-reliability-risks)
5. [Financial Risks](#5-financial-risks)
6. [Data Risks](#6-data-risks)
7. [Infrastructure Risks](#7-infrastructure-risks)
8. [Compliance Risks](#8-compliance-risks)
9. [Strategic Risks](#9-strategic-risks)
10. [Mitigation Implementation Priority](#10-mitigation-implementation-priority)

---

## 1. Risk Summary Matrix

| ID | Category | Risk | Likelihood | Impact | Overall | Primary Mitigation |
|----|----------|------|-----------|--------|---------|-------------------|
| RSK-001 | Execution | Order latency spikes | Medium | High | **High** | Kronos C++ + exchange-side stops |
| RSK-002 | Security | Prompt injection | Medium | Critical | **Critical** | No LLM in risk/decision |
| RSK-003 | Security | Private key leakage | Medium | Critical | **Critical** | No keys in client + Docker secrets |
| RSK-004 | Reliability | Infinite agent loops | Low | High | **Medium** | DAG enforcement + iteration counter |
| RSK-005 | Security | Host system compromise | Low | Critical | **High** | Docker isolation + no socket mount |
| RSK-006 | Reliability | Execution parity failures | High | High | **Critical** | Execution Reality Engine + paper trading |
| RSK-007 | Financial | Daily loss limit breach | Low | Critical | **High** | Constitutional limits + kill switch |
| RSK-008 | Financial | Flash crash exposure | Medium | High | **High** | Exchange-side stop losses |
| RSK-009 | Financial | Overtrading | Medium | Medium | **Medium** | MAX_DAILY_TRADES = 5 |
| RSK-010 | Financial | Correlated position blowup | Medium | High | **High** | MAX_CORRELATED_POSITIONS = 3 |
| RSK-011 | Data | Stale market data | Medium | Medium | **Medium** | Redis cache TTL + AutoSwitch |
| RSK-012 | Data | Factor computation errors | Low | Medium | **Low** | FactorRegistry output validation |
| RSK-013 | Data | Lookahead bias in factors | Low | High | **Medium** | `validate_lookahead()` per factor |
| RSK-014 | Infrastructure | Redis failure | Low | High | **Medium** | AOF persistence + fallback to direct API |
| RSK-015 | Infrastructure | PostgreSQL downtime | Low | High | **Medium** | Connection pooling + retry logic |
| RSK-016 | Infrastructure | Docker container crash | Medium | Medium | **Medium** | Auto-restart + health checks |
| RSK-017 | Infrastructure | Network partition | Low | High | **Medium** | Kill switch auto-activates on disconnect |
| RSK-018 | Compliance | Regulatory violation | Low | Critical | **High** | Paper trading until legal review |
| RSK-019 | Compliance | Audit trail gaps | Medium | High | **High** | Event-sourced PostgreSQL audit |
| RSK-020 | Compliance | Data residency violation | Low | Medium | **Low** | Self-hosted infrastructure |
| RSK-021 | Strategic | Factor decay | High | Medium | **High** | Walk-forward validation + Darwinian evolution |
| RSK-022 | Strategic | LLM provider outage | Medium | Medium | **Medium** | Multi-provider LLM routing |
| RSK-023 | Strategic | Exchange API deprecation | Medium | Medium | **Medium** | CCXT community maintenance |
| RSK-024 | Strategic | Model hallucination | Medium | High | **High** | Pressure normalization + no LLM in risk |
| RSK-025 | Strategic | Team knowledge concentration | Medium | Medium | **Medium** | Documentation + ADR records |

---

## 2. Execution Risks

### RSK-001: Order Latency Spikes

| Field | Value |
|-------|-------|
| **Category** | Execution |
| **Likelihood** | Medium |
| **Impact** | High |
| **Overall** | **High** |

**Description**: Order submission latency exceeds acceptable thresholds due to Python GIL contention, Redis Pub/Sub queue congestion, or exchange API degradation. A delay between the decision to enter and the actual fill could result in execution at a significantly worse price.

**Decision-to-Execution Path**:
```
LangGraph (Python, ~1-3s) → Redis Pub/Sub (~1-10ms) → ExecutionTool (~10-50ms) → Exchange API (~50-200ms)
Total expected: 1-3.5 seconds
During high-volatility: 5-10+ seconds
```

**Mitigation Controls**:

| Control | Implementation | Status |
|---------|---------------|--------|
| Kronos C++ fast path | PyO3 bridge bypasses Python GIL; target <55ms total | In Progress |
| Exchange-side stop losses | All stops submitted as GTC orders on exchange | Active |
| Latency monitoring | Every order records decision_timestamp + fill_timestamp; >2s = WARNING, >5s = CRITICAL | Active |
| AutoSwitch for execution | Route to backup venue if primary latency > 1s | Active |
| Max 5 trades/day | Checkpoint 8 prevents overtrading during volatility | Active |

**Residual Risk**: LangGraph decision pipeline is Python-based (~1-3s). Accepted because system targets swing trading, not HFT.

---

### RSK-008: Flash Crash Exposure

| Field | Value |
|-------|-------|
| **Category** | Execution |
| **Likelihood** | Medium |
| **Impact** | High |
| **Overall** | **High** |

**Description**: During a flash crash, prices can drop 10-30% in seconds. The system's 1-3s decision latency means it cannot react fast enough to close positions before significant loss occurs.

**Mitigation Controls**:

| Control | Implementation | Status |
|---------|---------------|--------|
| Exchange-side stop losses | Stops are GTC orders on the exchange, executed by the exchange even if our system is offline | Active |
| ATR-based stop distance | 2×ATR adapts stop distance to current volatility | Active |
| Maximum position size | 10% of portfolio per position (MAX_POSITION_SIZE_PCT = 0.10) | Active |
| Kill switch | Auto-activates at -2% daily PnL (KILL_SWITCH_DAILY_PNL = -0.02) | Active |
| Maximum drawdown | 15% drawdown triggers kill switch (MAX_DRAWDOWN_PCT = 0.15) | Active |

**Residual Risk**: Stop losses can be gapped over during extreme moves. Maximum theoretical loss per position = 10% × (gap distance). Accepted as inherent market risk.

---

## 3. Security Risks

### RSK-002: Prompt Injection / Malicious Tool Execution

| Field | Value |
|-------|-------|
| **Category** | Security |
| **Likelihood** | Medium |
| **Impact** | Critical |
| **Overall** | **Critical** |

**Description**: An attacker could craft market data, news headlines, or sentiment scores containing prompt injection payloads, causing LLM-based agents to produce manipulated signals.

**Attack Vectors**:
1. News headline injection from compromised news sources
2. Sentiment API manipulation returning crafted scores
3. Symbol field injection containing prompt directives
4. Timeframe field injection

**Mitigation Controls**:

| Control | Implementation | Status |
|---------|---------------|--------|
| No LLM in risk management | `RiskCheckGate` is pure Python logic — manipulated signals can still be VETOED | Active |
| No LLM in decision synthesis | Decision table is deterministic 7-rule table | Active |
| Agent output validation | Pydantic schemas validate all outputs; strings are bounded in length | Active |
| MCP tool registry | Agents can only execute tools from `REGISTERED_TOOLS` | Active |
| LLM temperature = 0.0 | Reduces (not eliminates) chance of following injected instructions | Active |
| Pressure normalization | Single agent influence diluted: SMCAgent 30%, QuantScanner 25%, FlowAgent 25%, NewsSentinel 20% | Active |
| Structural stop loss | Every trade has bounded maximum loss (0.5% per trade) | Active |
| Input sanitization | Symbol whitelist, timeframe enum validation | Partial |

**Residual Risk**: Researcher and Analyst nodes DO use LLMs to process external data. If injection causes extreme pressure values (e.g., buy_pressure = 1.0), it could trigger a trade if other sensors agree. NewsSentinel influence is limited to 20%.

---

### RSK-003: Private Key Leakage

| Field | Value |
|-------|-------|
| **Category** | Security |
| **Likelihood** | Medium |
| **Impact** | Critical |
| **Overall** | **Critical** |

**Description**: Exchange API keys, wallet private keys (for Polymarket EIP-712 signing), and LLM API keys could be exposed through logging, error messages, or client-side bundles.

**Historical Incidents**:

| Date | Incident | Resolution |
|------|----------|------------|
| Pre-v15.3.1 | `GEMINI_API_KEY` embedded in Vite client bundle | Removed from `define`, keys managed via runtime Settings only |

**Mitigation Controls**:

| Control | Implementation | Status |
|---------|---------------|--------|
| No keys in client bundle | Keys never in Vite `define` config | Active |
| Environment variable injection | Pydantic Settings loads from `.env` | Active |
| Docker secrets | Keys injected via mounted files (not env vars) | Planned |
| Log redaction | structlog redacts `*_api_key`, `*_secret`, `*_password`, `*_token` | Partial |
| Polymarket key isolation | `_wallet_key` stored as private attribute, never logged, only used for EIP-712 signing | Active |
| IP-restricted API keys | Exchange-side IP whitelisting | Recommended |

**Residual Risk**: Shell access to API container allows reading environment variables. `read_only: true` Docker config mitigates exfiltration but not `/proc/<pid>/environ` reading.

---

### RSK-005: Host System Compromise

| Field | Value |
|-------|-------|
| **Category** | Security |
| **Likelihood** | Low |
| **Impact** | Critical |
| **Overall** | **High** |

**Description**: A vulnerability in the application could allow container escape and host system access, exposing all containers, databases, and API keys.

**Attack Surface**:

| Surface | Risk | Protection |
|---------|------|------------|
| FastAPI endpoints | SQL injection, SSRF | Pydantic validation, parameterized queries |
| WebSocket connections | DoS, auth bypass | Planned: JWT auth |
| External data parsing | Malformed JSON | orjson parser, input size limits |
| npm/PyPI dependencies | Supply chain attacks | pip-audit, npm audit in CI |
| Docker socket | Container escape | Socket not mounted in any container |

**Mitigation Controls**:

| Control | Implementation | Status |
|---------|---------------|--------|
| Docker isolation | `no-new-privileges:true`, `cap_drop: ALL` | Planned |
| Read-only filesystem | API container `read_only: true` | Planned |
| No Docker socket mount | `/var/run/docker.sock` never mounted | Active |
| Network isolation | Only port 8000 exposed | Active |
| Resource limits | CPU + memory limits on containers | Planned |
| Container image scanning | Trivy scans before deployment | Planned |

---

## 4. Reliability Risks

### RSK-004: Infinite Agent Execution Loops

| Field | Value |
|-------|-------|
| **Category** | Reliability |
| **Likelihood** | Low |
| **Impact** | High |
| **Overall** | **Medium** |

**Description**: The LangGraph state graph could enter an infinite loop if conditional routing has a bug. Current graph is a strict DAG — no cycles are possible structurally.

**Mitigation Controls**:

| Control | Implementation | Status |
|---------|---------------|--------|
| DAG enforcement | Current graph has no backward edges | Active |
| Maximum iteration counter | Force END if `iteration > 20` | Planned |
| LLM call budget | Maximum 10 LLM calls per graph invocation | Planned |
| Execution timeout | Maximum 30 seconds per graph invocation | Planned |
| Max 5 trades/day | Checkpoint 8 caps damage from any loop | Active |

---

### RSK-006: Execution Parity Failures

| Field | Value |
|-------|-------|
| **Category** | Reliability |
| **Likelihood** | High |
| **Impact** | High |
| **Overall** | **Critical** |

**Description**: Backtested performance may not replicate in live trading due to slippage, spread, fill rate, latency, and order rejection differences.

**Known Parity Gaps**:

| Gap | Backtest Assumption | Live Reality | Impact |
|-----|-------------------|--------------|--------|
| Slippage | Fixed 5bps | Variable 0-50bps | -5% to -30% |
| Spread | Fixed 2bps | 5-50bps during news | -3% to -15% |
| Fill rate | 100% | 85-98% | -2% to -10% |
| Latency | 0ms | 100-500ms | -5% to -20% |
| Order rejection | 0% | 1-5% | -1% to -5% |
| Partial fills | Not modeled | 2-15% | -1% to -8% |

**Mitigation Controls**:

| Control | Implementation | Status |
|---------|---------------|--------|
| Execution Reality Engine | Dynamic spread, random slippage, partial fills, 100-500ms latency | Active |
| Walk-forward validation | Rolling out-of-sample testing | Active |
| Paper trading before live | 48-hour paper session required | Planned |
| Conservative sizing | Quarter Kelly (fraction=0.25) | Active |
| Kill switch | Auto-halt at 1% daily / 3% weekly loss | Active |

---

## 5. Financial Risks

### RSK-007: Daily Loss Limit Breach

| Field | Value |
|-------|-------|
| **Category** | Financial |
| **Likelihood** | Low |
| **Impact** | Critical |
| **Overall** | **High** |

**Description**: Portfolio loses more than the constitutional daily loss limit (1%).

**Constitutional Enforcement**:
```python
MAX_DAILY_LOSS: float = 0.01  # 1% max daily loss (HARDCODED)
KILL_SWITCH_DAILY_PNL: float = -0.02  # Kill switch at -2% daily PnL
```

**Mitigation Controls**:

| Control | Implementation | Status |
|---------|---------------|--------|
| 9-checkpoint gate | Checkpoint 2: daily_loss_pct < MAX_DAILY_LOSS | Active |
| Kill switch auto-activation | `RiskManager._auto_check_kill_switch()` runs after every trade | Active |
| Exchange-side stops | All stop losses are GTC on exchange | Active |
| Max risk per trade | 0.5% (checkpoint 1) | Active |
| Max 5 trades/day | Checkpoint 8 | Active |

**Residual Risk**: Gap risk (stops gapped over), correlated positions moving simultaneously, overnight risk for 24/7 crypto markets.

---

### RSK-009: Overtrading

| Field | Value |
|-------|-------|
| **Category** | Financial |
| **Likelihood** | Medium |
| **Impact** | Medium |
| **Overall** | **Medium** |

**Description**: Excessive trading leads to commission drag, emotional decisions, and increased exposure.

**Mitigation Controls**:

| Control | Implementation | Status |
|---------|---------------|--------|
| MAX_DAILY_TRADES = 5 | Checkpoint 8 in RiskCheckGate | Active |
| Commission tracking | PaperExchangeBroker tracks commission per trade | Active |
| High-conviction only | Council debate required when confidence < 0.65 | Active |
| Risk per trade cap | 0.5% per trade limits damage from any single trade | Active |

---

### RSK-010: Correlated Position Blowup

| Field | Value |
|-------|-------|
| **Category** | Financial |
| **Likelihood** | Medium |
| **Impact** | High |
| **Overall** | **High** |

**Description**: Multiple positions in correlated assets move together during market stress, amplifying losses beyond the expected diversification benefit.

**Mitigation Controls**:

| Control | Implementation | Status |
|---------|---------------|--------|
| MAX_CORRELATED_POSITIONS = 3 | Checkpoint 9 in RiskCheckGate | Active |
| CorrelationMonitor | `count_correlated_positions()` checks pairwise correlations | Active |
| Max position size | 10% per position limits concentration | Active |
| Kill switch | Auto-halt on aggregate drawdown | Active |

---

## 6. Data Risks

### RSK-011: Stale Market Data

| Field | Value |
|-------|-------|
| **Category** | Data |
| **Likelihood** | Medium |
| **Impact** | Medium |
| **Overall** | **Medium** |

**Description**: Agents make decisions based on outdated market data due to cache staleness, API rate limits, or data provider outages.

**Mitigation Controls**:

| Control | Implementation | Status |
|---------|---------------|--------|
| Redis cache TTL | OHLCV: 300s, Current price: 60s | Active |
| AutoSwitch failover | Routes to backup provider on primary failure | Active |
| Timestamp validation | MarketData.timestamp checked against current time | Planned |
| Staleness alert | WARNING if data > 60s old for active positions | Planned |

---

### RSK-012: Factor Computation Errors

| Field | Value |
|-------|-------|
| **Category** | Data |
| **Likelihood** | Low |
| **Impact** | Medium |
| **Overall** | **Low** |

**Description**: Factor computations produce incorrect values (inf, >95% NaN, or wrong values) that corrupt signal generation.

**Mitigation Controls**:

| Control | Implementation | Status |
|---------|---------------|--------|
| Output validation | FactorRegistry rejects inf and >95% NaN | Active |
| Lookahead validation | `validate_lookahead()` per factor | Active |
| Factor health check | `registry.health()` reports failures | Active |
| Per-factor testing | Unit tests for each factor's expected output | Partial |

---

### RSK-013: Lookahead Bias in Factors

| Field | Value |
|-------|-------|
| **Category** | Data |
| **Likelihood** | Low |
| **Impact** | High |
| **Overall** | **Medium** |

**Description**: Factor implementations inadvertently use future data (e.g., using `shift(-1)` instead of `shift(1)`), producing unrealistically good backtest results.

**Mitigation Controls**:

| Control | Implementation | Status |
|---------|---------------|--------|
| `validate_lookahead()` | Each factor must pass lookahead validation during registration | Active |
| Walk-forward validation | Out-of-sample testing detects unrealistic performance | Active |
| Rolling window enforcement | All factor computations use only past data | Active |

---

## 7. Infrastructure Risks

### RSK-014: Redis Failure

| Field | Value |
|-------|-------|
| **Category** | Infrastructure |
| **Likelihood** | Low |
| **Impact** | High |
| **Overall** | **Medium** |

**Description**: Redis failure disrupts cache, Pub/Sub channels, and rate limiting.

**Mitigation Controls**:

| Control | Implementation | Status |
|---------|---------------|--------|
| AOF persistence | Redis writes to disk for crash recovery | Planned |
| Fallback to direct API | If Redis is down, API calls go directly to PostgreSQL | Planned |
| Health check | Redis PING in API startup | Planned |
| Auto-restart | Docker restart policy: `unless-stopped` | Active |

---

### RSK-015: PostgreSQL Downtime

| Field | Value |
|-------|-------|
| **Category** | Infrastructure |
| **Likelihood** | Low |
| **Impact** | High |
| **Overall** | **Medium** |

**Description**: PostgreSQL failure disrupts agent state storage, audit trail, and trade history.

**Mitigation Controls**:

| Control | Implementation | Status |
|---------|---------------|--------|
| Connection pooling | SQLAlchemy pool_size=10, max_overflow=20 | Active |
| Retry logic | tenacity retry decorator on DB operations | Planned |
| WAL archiving | PostgreSQL write-ahead logging for crash recovery | Planned |
| Regular backups | pg_dump scheduled daily | Planned |

---

### RSK-016: Docker Container Crash

| Field | Value |
|-------|-------|
| **Category** | Infrastructure |
| **Likelihood** | Medium |
| **Impact** | Medium |
| **Overall** | **Medium** |

**Description**: API container crashes due to OOM, unhandled exception, or resource exhaustion.

**Mitigation Controls**:

| Control | Implementation | Status |
|---------|---------------|--------|
| Memory limits | Docker memory limit (4G) prevents OOM | Planned |
| Global exception handler | FastAPI catches all unhandled exceptions | Active |
| Auto-restart | Docker restart policy: `unless-stopped` | Active |
| Health check endpoint | `/health` returns 200 if service is running | Active |
| Exchange-side stops | Positions protected even if system is down | Active |

---

### RSK-017: Network Partition

| Field | Value |
|-------|-------|
| **Category** | Infrastructure |
| **Likelihood** | Low |
| **Impact** | High |
| **Overall** | **Medium** |

**Description**: Network partition between API and exchange, or between internal services, prevents order execution and position monitoring.

**Mitigation Controls**:

| Control | Implementation | Status |
|---------|---------------|--------|
| Exchange-side stops | Stop losses execute on exchange even without system connectivity | Active |
| Kill switch on disconnect | Auto-activate kill switch if exchange connection lost for >30s | Planned |
| Position reconciliation | Sync positions on reconnect | Planned |
| Network monitoring | Alert on connection loss | Planned |

---

## 8. Compliance Risks

### RSK-018: Regulatory Violation

| Field | Value |
|-------|-------|
| **Category** | Compliance |
| **Likelihood** | Low |
| **Impact** | Critical |
| **Overall** | **High** |

**Description**: Automated trading may violate jurisdiction-specific regulations (e.g., SEC, CFTC, MAS, FCA) regarding algorithmic trading, market manipulation, or unauthorized financial advice.

**Mitigation Controls**:

| Control | Implementation | Status |
|---------|---------------|--------|
| Paper trading default | `ENABLE_LIVE_TRADING = False` by default | Active |
| Jurisdiction review | Legal review before enabling live trading in any jurisdiction | Pending |
| No market making | System does not provide liquidity or make markets | Active |
| Kill switch | Immediate halt capability | Active |
| Audit trail | Complete decision reconstruction | Active |

---

### RSK-019: Audit Trail Gaps

| Field | Value |
|-------|-------|
| **Category** | Compliance |
| **Likelihood** | Medium |
| **Impact** | High |
| **Overall** | **High** |

**Description**: Incomplete audit trail makes it impossible to reconstruct trading decisions for compliance review.

**Mitigation Controls**:

| Control | Implementation | Status |
|---------|---------------|--------|
| Event-sourced audit | PostgreSQL `audit_events` table (append-only) | Active |
| Full state trace | LangGraph state transitions persisted per node | Active |
| Risk checkpoint logging | All 9 checkpoints logged per trade | Active |
| Execution logging | Order submission, fill, slippage recorded | Active |
| No deletion policy | audit_events are append-only, no deletes | Active |

---

## 9. Strategic Risks

### RSK-021: Factor Decay

| Field | Value |
|-------|--------|
| **Category** | Strategic |
| **Likelihood** | High |
| **Impact** | Medium |
| **Overall** | **High** |

**Description**: Alpha factors lose predictive power over time as markets adapt and more participants discover the same signals.

**Mitigation Controls**:

| Control | Implementation | Status |
|---------|---------------|--------|
| Walk-forward validation | Detects factor decay in out-of-sample testing | Active |
| Factor health monitoring | Track factor IC (Information Coefficient) over time | Planned |
| Darwinian evolution | Auto-kill strategies with negative expectancy | Planned |
| Factor diversity | 469 factors across 7 zoos provides diversification | Active |
| GpLearn symbolic regression | Discover new alpha factors automatically | Planned |

---

### RSK-022: LLM Provider Outage

| Field | Value |
|-------|--------|
| **Category** | Strategic |
| **Likelihood** | Medium |
| **Impact** | Medium |
| **Overall** | **Medium** |

**Description**: OpenAI, Anthropic, or other LLM providers experience outages, preventing agent reasoning.

**Mitigation Controls**:

| Control | Implementation | Status |
|---------|---------------|--------|
| Multi-provider LLM | `create_llm()` supports 5 providers (OpenAI, Anthropic, Google, Ollama, OpenRouter) | Active |
| Local LLM fallback | Ollama provides fully offline LLM capability | Planned |
| Risk-only mode | If all LLMs fail, risk manager still enforces constitutional limits (no LLM needed) | Active |
| Kill switch on LLM failure | Halt trading if reasoning is unavailable | Planned |

---

### RSK-024: Model Hallucination

| Field | Value |
|-------|--------|
| **Category** | Strategic |
| **Likelihood** | Medium |
| **Impact** | High |
| **Overall** | **High** |

**Description**: LLM-based agents produce confident but incorrect analysis (hallucination), leading to poor trading decisions.

**Mitigation Controls**:

| Control | Implementation | Status |
|---------|---------------|--------|
| No LLM in risk management | RiskCheckGate is pure Python | Active |
| Pressure normalization | Single agent hallucination diluted by weighted aggregation | Active |
| Council debate | Multiple perspectives reduce hallucination impact | Active |
| Confidence scoring | Low confidence triggers debate, not direct execution | Active |
| Data grounding requirement | Agents must reference specific data, not vibes | Active |
| Temperature = 0.0 | Reduces (not eliminates) hallucination | Active |

---

## 10. Mitigation Implementation Priority

### Priority 1 — Critical (Implement Immediately)

| Risk ID | Risk | Mitigation | Effort |
|---------|------|------------|--------|
| RSK-002 | Prompt Injection | Complete input sanitization for all external data | 3 days |
| RSK-003 | Key Leakage | Docker secrets + complete log redaction | 2 days |
| RSK-006 | Execution Parity | Paper trading validation before live capital | 5 days |
| RSK-007 | Daily Loss Breach | Verify kill switch auto-activation under all conditions | 1 day |

### Priority 2 — High (Implement Before Live Trading)

| Risk ID | Risk | Mitigation | Effort |
|---------|------|------------|--------|
| RSK-001 | Latency Spikes | Kronos C++ integration | 10 days |
| RSK-005 | Host Compromise | Docker hardening (read_only, cap_drop, resource limits) | 3 days |
| RSK-008 | Flash Crash | Verify exchange-side stops on all positions | 2 days |
| RSK-010 | Correlated Blowup | Implement correlation heatmap in portfolio view | 3 days |
| RSK-019 | Audit Gaps | Verify all state transitions persisted | 2 days |
| RSK-024 | Hallucination | Implement confidence-weighted signal aggregation | 3 days |

### Priority 3 — Medium (Implement in Q4 2025)

| Risk ID | Risk | Mitigation | Effort |
|---------|------|------------|--------|
| RSK-004 | Infinite Loops | Add iteration counter + LLM call budget + timeout | 2 days |
| RSK-009 | Overtrading | Add commission drag tracking + alerting | 2 days |
| RSK-011 | Stale Data | Timestamp validation + staleness alerts | 2 days |
| RSK-014 | Redis Failure | AOF persistence + fallback to direct API | 3 days |
| RSK-015 | PostgreSQL Downtime | WAL archiving + backup schedule | 3 days |
| RSK-016 | Container Crash | Memory limits + structured error handling | 2 days |
| RSK-017 | Network Partition | Kill switch on disconnect + position reconciliation | 3 days |
| RSK-022 | LLM Outage | Ollama fallback + local LLM cache | 5 days |

### Priority 4 — Low (Implement in Q1 2026)

| Risk ID | Risk | Mitigation | Effort |
|---------|------|------------|--------|
| RSK-012 | Factor Errors | Complete per-factor unit test coverage | 5 days |
| RSK-013 | Lookahead Bias | Automated lookahead detection in CI | 3 days |
| RSK-020 | Data Residency | Self-hosted infrastructure compliance | 2 days |
| RSK-021 | Factor Decay | Factor IC monitoring + Darwinian evolution | 10 days |
| RSK-023 | API Deprecation | Version pinning + migration automation | 3 days |
| RSK-025 | Knowledge Concentration | Documentation + ADR records | Ongoing |

---

*© 2025-2026 Quant Nanggroe AI | Risk Register v4.0.0*
