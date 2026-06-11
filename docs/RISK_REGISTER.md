# Quant Nanggroe AI — Risk Register

**Version 4.0.0 | Project Risk Management**

> This document identifies, assesses, and provides mitigation strategies for all risks associated with the Quant Nanggroe AI trading system, covering technical, operational, market, security, and compliance dimensions.

---

## Table of Contents

1. [Risk Assessment Framework](#1-risk-assessment-framework)
2. [Technical Risks](#2-technical-risks)
3. [Operational Risks](#3-operational-risks)
4. [Market Risks](#4-market-risks)
5. [Security Risks](#5-security-risks)
6. [Compliance Risks](#6-compliance-risks)
7. [Agent-Specific Risks](#7-agent-specific-risks)
8. [Data Risks](#8-data-risks)
9. [Infrastructure Risks](#9-infrastructure-risks)
10. [Risk Heat Map](#10-risk-heat-map)
11. [Mitigation Strategy Summary](#11-mitigation-strategy-summary)

---

## 1. Risk Assessment Framework

### Risk Scoring

Each risk is assessed on two dimensions:

| Dimension | Scale | Description |
|---|---|---|
| **Likelihood** | 1-5 | Probability of occurrence (1=Very Low, 5=Very High) |
| **Impact** | 1-5 | Severity of consequences (1=Negligible, 5=Catastrophic) |
| **Risk Score** | L × I | 1-25 (prioritized by score) |

### Risk Categories

| Category | Code | Description |
|---|---|---|
| Technical | T | Software bugs, architecture failures, performance issues |
| Operational | O | Process failures, human errors, communication gaps |
| Market | M | Market movements, liquidity, volatility |
| Security | S | Cyber attacks, credential leaks, unauthorized access |
| Compliance | C | Regulatory, legal, audit requirements |
| Agent | A | AI/LLM-specific risks (hallucination, bias, etc.) |
| Data | D | Data quality, availability, integrity |
| Infrastructure | I | Hardware, network, cloud services |

### Risk Severity Levels

| Score | Level | Action Required |
|---|---|---|
| 20-25 | **CRITICAL** | Immediate action, escalate to leadership |
| 12-19 | **HIGH** | Urgent mitigation, weekly monitoring |
| 6-11 | **MEDIUM** | Planned mitigation, monthly monitoring |
| 1-5 | **LOW** | Accept or monitor, quarterly review |

---

## 2. Technical Risks

### T-001: LLM API Failure

| Attribute | Details |
|---|---|
| **Risk ID** | T-001 |
| **Category** | Technical |
| **Description** | OpenAI/Anthropic/Google API becomes unavailable, causing all LLM-dependent agents to fail |
| **Likelihood** | 3 (Occasional outages) |
| **Impact** | 5 (Complete trading halt) |
| **Score** | 15 (HIGH) |
| **Affected Components** | All agents, TradingGraphV2 |

**Mitigation Strategies**:
1. **Multi-provider failover**: `create_llm()` supports OpenAI, Anthropic, and Google
2. **Graceful degradation**: Agents return structured error outputs, pipeline can continue with reduced capability
3. **Caching**: Previous agent outputs cached for similar market conditions
4. **Kill switch**: If no agents can function, kill switch activates automatically
5. **Pre-computed signals**: Strategist can use technical factors as fallback signals

**Monitoring**: API response time, error rate, provider status pages

---

### T-002: LangGraph State Corruption

| Attribute | Details |
|---|---|
| **Risk ID** | T-002 |
| **Category** | Technical |
| **Description** | AgentState TypedDict gets corrupted between nodes, causing downstream failures |
| **Likelihood** | 2 (Well-typed, Pydantic validation) |
| **Impact** | 4 (Incorrect decisions, risk bypass) |
| **Score** | 8 (MEDIUM) |
| **Affected Components** | TradingGraphV2, all nodes |

**Mitigation Strategies**:
1. **TypedDict with Annotated fields**: Type hints prevent field name errors
2. **Pydantic model validation**: All structured data validated at creation
3. **Initial state factory**: `create_initial_state()` ensures all fields populated
4. **Risk verdict defaults to VETOED**: If state is corrupted, risk assessment defaults to safe state
5. **Constitutional limits in metadata**: Limits embedded in state for verification

**Monitoring**: State validation assertions in each node, hash verification

---

### T-003: Factor Computation Error

| Attribute | Details |
|---|---|
| **Risk ID** | T-003 |
| **Category** | Technical |
| **Description** | Factor produces incorrect values (NaN, inf, wrong sign), leading to bad signals |
| **Likelihood** | 3 (469 factors, edge cases possible) |
| **Impact** | 3 (Bad signals, but risk gate catches most) |
| **Score** | 9 (MEDIUM) |
| **Affected Components** | FactorRegistry, Strategist agent |

**Mitigation Strategies**:
1. **Output validation**: No ±inf, NaN ratio ≤ 95%
2. **Lookahead bias validation**: Class-based factors checked for lookahead
3. **Factor health monitoring**: `registry.health()` reports failures
4. **Fallback to technical factors**: If zoo factors fail, basic technical indicators are always available
5. **Factor smoke tests**: Automated tests for all 469+ factors

**Monitoring**: Factor health endpoint, output validation failures logged

---

### T-004: Graph Execution Deadlock

| Attribute | Details |
|---|---|
| **Risk ID** | T-004 |
| **Category** | Technical |
| **Description** | TradingGraphV2 enters an infinite loop (e.g., council debate → position_sizer → risk → council debate) |
| **Likelihood** | 2 (Iteration counter prevents this) |
| **Impact** | 4 (System hangs, no trades executed) |
| **Score** | 8 (MEDIUM) |
| **Affected Components** | TradingGraphV2 |

**Mitigation Strategies**:
1. **Iteration counter**: `state["iteration"]` tracks graph iterations
2. **Maximum iteration limit**: Graph halts after configurable max iterations
3. **Council debate rounds**: Limited to `max_debate_rounds` (default: 2)
4. **Risk rounds**: Limited to `max_risk_rounds` (default: 2)
5. **Timeout**: Graph execution has configurable timeout
6. **Emergency exit**: Kill switch can break any cycle

**Monitoring**: Iteration count in state, execution time monitoring

---

### T-005: Memory Leak in Long-Running Process

| Attribute | Details |
|---|---|
| **Risk ID** | T-005 |
| **Category** | Technical |
| **Description** | Agent outputs accumulate in AgentState, causing memory exhaustion in long-running processes |
| **Likelihood** | 3 (agent_outputs grows unbounded) |
| **Impact** | 3 (Performance degradation, eventual crash) |
| **Score** | 9 (MEDIUM) |
| **Affected Components** | AgentState, memory system |

**Mitigation Strategies**:
1. **Memory paging**: `memory/paging.py` implements LRU cache with size limits
2. **State size monitoring**: Track AgentState size after each node
3. **Periodic cleanup**: Stale agent outputs purged after reflection phase
4. **Redis offloading**: Large state moved to Redis instead of in-memory
5. **Process restarts**: Worker process restarted daily (fresh state)

**Monitoring**: Memory usage, state size metrics, Redis memory

---

### T-006: Race Condition in FactorRegistry

| Attribute | Details |
|---|---|
| **Risk ID** | T-006 |
| **Category** | Technical |
| **Description** | Concurrent access to FactorRegistry singleton causes data corruption |
| **Likelihood** | 2 (Thread-safe singleton) |
| **Impact** | 3 (Incorrect factor values) |
| **Score** | 6 (MEDIUM) |
| **Affected Components** | FactorRegistry |

**Mitigation Strategies**:
1. **Thread-safe singleton**: `_registry_cache_lock` protects initialization
2. **Immutable after init**: Registry is read-only after construction
3. **No concurrent writes**: Registry is built once, never modified
4. **Reset only in tests**: `reset_default_registry()` only for test isolation

**Monitoring**: Registry health check, concurrent access logging

---

## 3. Operational Risks

### O-001: Human Operator Error

| Attribute | Details |
|---|---|
| **Risk ID** | O-001 |
| **Category** | Operational |
| **Description** | Human operator misconfigures system, approves bad trade, or disables safety feature |
| **Likelihood** | 3 (Humans make mistakes) |
| **Impact** | 4 (Significant financial loss possible) |
| **Score** | 12 (HIGH) |
| **Affected Components** | Human checkpoint, configuration, kill switch |

**Mitigation Strategies**:
1. **Constitutional limits**: Cannot be changed by operators
2. **Kill switch**: Automatic, not manual
3. **Audit logging**: All human actions logged
4. **Human checkpoint for high-risk only**: Reduces operator fatigue
5. **Two-person rule**: (Planned) Critical operations require two approvals

**Monitoring**: Audit log review, configuration change alerts

---

### O-002: Kill Switch False Positive

| Attribute | Details |
|---|---|
| **Risk ID** | O-002 |
| **Category** | Operational |
| **Description** | Kill switch triggers incorrectly, halting trading unnecessarily |
| **Likelihood** | 2 (Conservative thresholds) |
| **Impact** | 3 (Missed trading opportunities, operational overhead) |
| **Score** | 6 (MEDIUM) |
| **Affected Components** | KillSwitch, RiskManager |

**Mitigation Strategies**:
1. **Conservative thresholds**: -2% daily, -5% weekly are well-calibrated
2. **Manual reset required**: Forces human review before resuming
3. **False positive logging**: All kill switch activations logged with reason
4. **Graduated response**: Daily loss limit doesn't trigger kill switch, only halt (weekly and drawdown do)

**Monitoring**: Kill switch activation rate, false positive analysis

---

### O-003: Deployment Failure

| Attribute | Details |
|---|---|
| **Risk ID** | O-003 |
| **Category** | Operational |
| **Description** | Deployment of new version fails, causing downtime |
| **Likelihood** | 3 (Common in production) |
| **Impact** | 3 (Temporary trading halt) |
| **Score** | 9 (MEDIUM) |
| **Affected Components** | Entire system |

**Mitigation Strategies**:
1. **Blue-green deployment**: Zero-downtime deployments
2. **Health checks**: `/health` endpoint for load balancer
3. **Rollback procedure**: Git revert + redeploy
4. **Staging environment**: All changes tested in staging first
5. **Canary releases**: Gradual rollout to production

**Monitoring**: Deployment success rate, health check failures

---

### O-004: Monitoring Gap

| Attribute | Details |
|---|---|
| **Risk ID** | O-004 |
| **Category** | Operational |
| **Description** | Critical system issue not detected because monitoring is insufficient |
| **Likelihood** | 3 (Monitoring is still being built) |
| **Impact** | 4 (Undetected losses, delayed response) |
| **Score** | 12 (HIGH) |
| **Affected Components** | All components |

**Mitigation Strategies**:
1. **Structured logging**: All events logged with severity and context
2. **Health endpoints**: `/health` for infrastructure monitoring
3. **Risk status**: `RiskManager.status()` provides real-time risk state
4. **Factor health**: `FactorRegistry.health()` reports factor issues
5. **Alert rules**: (Planned) Prometheus alerting for risk limit breaches

**Monitoring**: Log aggregation, alert system, dashboard

---

## 4. Market Risks

### M-001: Flash Crash

| Attribute | Details |
|---|---|
| **Risk ID** | M-001 |
| **Category** | Market |
| **Description** | Sudden extreme market movement causing rapid position losses |
| **Likelihood** | 2 (Rare but devastating) |
| **Impact** | 5 (Catastrophic if not protected) |
| **Score** | 10 (MEDIUM) |
| **Affected Components** | All positions, RiskManager |

**Mitigation Strategies**:
1. **Kill switch**: Triggers at -2% daily PnL
2. **Stop losses**: Required on every position (Checkpoint 5)
3. **Drawdown monitor**: 15% max drawdown triggers kill switch
4. **Emergency exit**: All positions closed immediately
5. **Position sizing**: ATR-based sizing limits exposure per trade
6. **Max 5 trades/day**: Prevents compounding losses through overtrading

**Monitoring**: Real-time PnL, drawdown, market volatility

---

### M-002: Liquidity Crisis

| Attribute | Details |
|---|---|
| **Risk ID** | M-002 |
| **Category** | Market |
| **Description** | Market becomes illiquid, making it impossible to exit positions at fair prices |
| **Likelihood** | 2 (Rare in major markets, more common in crypto) |
| **Impact** | 4 (Significant slippage, inability to close) |
| **Score** | 8 (MEDIUM) |
| **Affected Components** | Execution agent, SmartExecutor |

**Mitigation Strategies**:
1. **Smart order routing**: Routes to highest-liquidity venue
2. **Fill rate monitoring**: Venues with low fill rates scored lower
3. **Position size limits**: 10% max per position
4. **Multi-venue execution**: Can split orders across exchanges
5. **Paper trading mode**: Can simulate before committing real capital

**Monitoring**: Venue fill rates, order book depth, slippage

---

### M-003: Correlation Breakdown

| Attribute | Details |
|---|---|
| **Risk ID** | M-003 |
| **Category** | Market |
| **Description** | Historically uncorrelated assets become highly correlated during crisis, concentrating risk |
| **Likelihood** | 3 (Common during crises) |
| **Impact** | 4 (Diversification fails) |
| **Score** | 12 (HIGH) |
| **Affected Components** | Portfolio agent, CorrelationMonitor |

**Mitigation Strategies**:
1. **Correlation monitor**: Rolling pairwise correlation tracked
2. **Max 3 correlated positions**: Checkpoint 9 enforces limit
3. **Regime detection**: CRISIS regime triggers stricter confidence requirements
4. **Dynamic rebalancing**: Portfolio agent adjusts allocation based on correlations
5. **Kill switch**: Drawdown-based trigger catches correlation-driven losses

**Monitoring**: Correlation matrix, regime state, position concentration

---

### M-004: Gap Risk

| Attribute | Details |
|---|---|
| **Risk ID** | M-004 |
| **Category** | Market |
| **Description** | Market gaps through stop loss, causing larger-than-expected loss |
| **Likelihood** | 3 (Common in crypto and around news events) |
| **Impact** | 3 (Single trade loss exceeds risk budget) |
| **Score** | 9 (MEDIUM) |
| **Affected Components** | RiskManager, Execution agent |

**Mitigation Strategies**:
1. **0.5% max risk per trade**: Small enough to absorb a gap
2. **Position size limits**: 10% max per position
3. **Diversification**: Multiple uncorrelated positions
4. **Kill switch**: Catches cascading gap losses
5. **Avoid trading around major events**: (Planned) News calendar integration

**Monitoring**: Gap events, actual vs. expected loss, slippage

---

## 5. Security Risks

### S-001: API Key Compromise

| Attribute | Details |
|---|---|
| **Risk ID** | S-001 |
| **Category** | Security |
| **Description** | Exchange or LLM API keys stolen or leaked, allowing unauthorized trading |
| **Likelihood** | 2 (Multiple safeguards) |
| **Impact** | 5 (Complete financial compromise) |
| **Score** | 10 (MEDIUM) |
| **Affected Components** | ExchangeFactory, LLM connections |

**Mitigation Strategies**:
1. **KeyVault**: Secure key storage, never in code or config files
2. **Credential inference**: `credential_inference.py` scans for leaked keys
3. **Environment variables**: Keys loaded from env, not hardcoded
4. **IP whitelisting**: Exchange API keys restricted to known IPs
5. **Read-only keys**: Market data API keys don't need write access
6. **Key rotation**: (Planned) Automatic key rotation schedule

**Monitoring**: Credential scan results, key usage audit logs

---

### S-002: Unauthorized API Access

| Attribute | Details |
|---|---|
| **Risk ID** | S-002 |
| **Category** | Security |
| **Description** | Unauthorized user accesses the trading API and executes trades |
| **Likelihood** | 2 (Auth planned) |
| **Impact** | 5 (Unauthorized trading) |
| **Score** | 10 (MEDIUM) |
| **Affected Components** | FastAPI API layer |

**Mitigation Strategies**:
1. **API authentication**: (Planned) JWT or API key auth
2. **Rate limiting**: (Planned) Per-user rate limits
3. **CORS configuration**: Restricted in production
4. **HTTPS only**: TLS encryption in transit
5. **Audit logging**: All API calls logged

**Monitoring**: Authentication failures, unusual API patterns

---

### S-003: Supply Chain Attack

| Attribute | Details |
|---|---|
| **Risk ID** | S-003 |
| **Category** | Security |
| **Description** | Compromised dependency (e.g., CCXT, LangChain) injects malicious code |
| **Likelihood** | 2 (Rare but increasing) |
| **Impact** | 5 (Complete system compromise) |
| **Score** | 10 (MEDIUM) |
| **Affected Components** | All dependencies |

**Mitigation Strategies**:
1. **Version pinning**: All dependencies pinned in pyproject.toml
2. **Hash verification**: (Planned) Package hash verification
3. **Dependency audit**: Regular `pip audit` or `safety check`
4. **Minimal dependencies**: Only essential dependencies included
5. **Private registry**: (Planned) Internal PyPI mirror

**Monitoring**: Dependency vulnerability scans, version change alerts

---

### S-004: Data Poisoning

| Attribute | Details |
|---|---|
| **Risk ID** | S-004 |
| **Category** | Security |
| **Description** | Market data provider compromised, feeding false prices |
| **Likelihood** | 1 (Very rare for major providers) |
| **Impact** | 5 (Bad decisions based on false data) |
| **Score** | 5 (LOW) |
| **Affected Components** | MarketService, AutoSwitch |

**Mitigation Strategies**:
1. **Multi-provider cross-validation**: Compare prices across providers
2. **AutoSwitch**: Failover to backup provider if anomalies detected
3. **Price sanity checks**: Outlier detection on incoming data
4. **Stale data detection**: Reject data older than threshold

**Monitoring**: Price deviation between providers, data freshness

---

## 6. Compliance Risks

### C-001: Regulatory Violation

| Attribute | Details |
|---|---|
| **Risk ID** | C-001 |
| **Category** | Compliance |
| **Description** | System operates in a jurisdiction where algorithmic trading requires specific licenses or registration |
| **Likelihood** | 3 (Varies by jurisdiction) |
| **Impact** | 5 (Fines, legal action, forced shutdown) |
| **Score** | 15 (HIGH) |
| **Affected Components** | Entire system |

**Mitigation Strategies**:
1. **Jurisdiction review**: Legal review before operating in new markets
2. **Paper trading**: Always available for testing without regulatory exposure
3. **Audit trail**: Complete decision trail for regulatory review
4. **Kill switch**: Can halt all trading immediately
5. **Compliance officer**: (Planned) Designated compliance role

**Monitoring**: Regulatory changes, compliance audit schedule

---

### C-002: Market Manipulation Detection

| Attribute | Details |
|---|---|
| **Risk ID** | C-002 |
| **Category** | Compliance |
| **Description** | Trading patterns flagged as potential market manipulation (spoofing, layering) |
| **Likelihood** | 2 (System doesn't spoof, but pattern matching may flag) |
| **Impact** | 4 (Investigation, account suspension) |
| **Score** | 8 (MEDIUM) |
| **Affected Components** | Execution agent, SmartExecutor |

**Mitigation Strategies**:
1. **No spoofing strategies**: System doesn't implement spoofing or layering
2. **Genuine order intent**: All orders are intended to be filled
3. **Order cancellation tracking**: (Planned) Monitor cancellation rates
4. **Max 5 trades/day**: Prevents high-frequency patterns that look manipulative
5. **Audit trail**: Can demonstrate genuine trading intent

**Monitoring**: Order cancellation rate, trade frequency, exchange warnings

---

### C-003: Insider Trading

| Attribute | Details |
|---|---|
| **Risk ID** | C-003 |
| **Category** | Compliance |
| **Description** | Agent makes trading decisions based on material non-public information (e.g., from SEC filings before public release) |
| **Likelihood** | 2 (Data sources are public) |
| **Impact** | 5 (Criminal liability) |
| **Score** | 10 (MEDIUM) |
| **Affected Components** | Researcher agent, data providers |

**Mitigation Strategies**:
1. **Public data only**: All data sources are public APIs
2. **No pre-release data**: SEC filings accessed after public release
3. **Data source tagging**: Each data source labeled with public/non-public
4. **Compliance review**: (Planned) Regular review of data sources

**Monitoring**: Data source audit, information barrier verification

---

## 7. Agent-Specific Risks

### A-001: LLM Hallucination

| Attribute | Details |
|---|---|
| **Risk ID** | A-001 |
| **Category** | Agent |
| **Description** | LLM produces fabricated market data, prices, or analysis that has no basis in reality |
| **Likelihood** | 4 (LLMs hallucinate frequently) |
| **Impact** | 3 (Bad decisions, but risk gate mitigates) |
| **Score** | 12 (HIGH) |
| **Affected Components** | All agents |

**Mitigation Strategies**:
1. **Constitutional risk limits**: Even if agent hallucinates a "sure thing", risk limits prevent over-exposure
2. **9-checkpoint gate**: Validates trade parameters against reality
3. **Stop loss required**: Every trade must have a stop loss
4. **Risk:Reward minimum: 1:2**: Prevents obviously bad trades
5. **Council debate**: Low-confidence decisions trigger multi-agent review
6. **Data grounding**: Agents receive real market data as context
7. **Structured output**: Pydantic models validate agent outputs

**Monitoring**: Agent output validation, confidence score tracking

---

### A-002: Agent Coordination Failure

| Attribute | Details |
|---|---|
| **Risk ID** | A-002 |
| **Category** | Agent |
| **Description** | Agents produce conflicting signals, causing the system to freeze or make inconsistent decisions |
| **Likelihood** | 3 (Common in multi-agent systems) |
| **Impact** | 3 (Suboptimal decisions, missed opportunities) |
| **Score** | 9 (MEDIUM) |
| **Affected Components** | Strategist, Council, Trader |

**Mitigation Strategies**:
1. **Council debate**: Resolves disagreements through structured debate
2. **Weighted voting**: Historical accuracy weights agent votes
3. **Strategist synthesis**: Single agent synthesizes all inputs into unified signals
4. **Confidence threshold**: Low confidence triggers additional review
5. **Risk gate**: Independent check regardless of agent agreement

**Monitoring**: Agent agreement rate, debate frequency, confidence scores

---

### A-003: Prompt Injection

| Attribute | Details |
|---|---|
| **Risk ID** | A-003 |
| **Category** | Agent |
| **Description** | Malicious input (from news, filings, or user) manipulates LLM into making specific trading decisions |
| **Likelihood** | 2 (Limited attack surface) |
| **Impact** | 4 (Unauthorized trading decisions) |
| **Score** | 8 (MEDIUM) |
| **Affected Components** | All agents using LLMs |

**Mitigation Strategies**:
1. **System prompts**: Strict agent behavior boundaries
2. **Structured output**: Pydantic models limit what agents can produce
3. **Risk gate**: Independent of agent reasoning
4. **Human checkpoint**: High-risk trades require human approval
5. **Input sanitization**: Market data is numerical, not free-text
6. **No direct user input to agents**: User requests go through API validation

**Monitoring**: Agent output anomaly detection, unexpected trade patterns

---

### A-004: Model Degradation

| Attribute | Details |
|---|---|
| **Risk ID** | A-004 |
| **Category** | Agent |
| **Description** | LLM provider changes model behavior (quiet update), causing agents to produce different outputs |
| **Likelihood** | 3 (Models are frequently updated) |
| **Impact** | 3 (Inconsistent behavior) |
| **Score** | 9 (MEDIUM) |
| **Affected Components** | All agents |

**Mitigation Strategies**:
1. **Model version pinning**: Pin specific model versions (e.g., gpt-4o-2024-08-06)
2. **Regression testing**: Agent output comparison between model versions
3. **Constitutional limits**: Risk limits protect regardless of model quality
4. **Multi-provider**: Can switch providers if one degrades
5. **Confidence tracking**: Detect drops in agent confidence

**Monitoring**: Agent output quality metrics, confidence trends

---

## 8. Data Risks

### D-001: Data Provider Outage

| Attribute | Details |
|---|---|
| **Risk ID** | D-001 |
| **Category** | Data |
| **Description** | Primary data provider (Alpaca, Binance, etc.) becomes unavailable |
| **Likelihood** | 3 (Occasional outages) |
| **Impact** | 3 (Cannot analyze markets, no trading) |
| **Score** | 9 (MEDIUM) |
| **Affected Components** | MarketService, AutoSwitch |

**Mitigation Strategies**:
1. **AutoSwitch**: Automatic failover to backup providers
2. **Exponential backoff**: Retry with increasing delay
3. **Health monitoring**: Provider health tracked in real-time
4. **Cooldown**: Failed providers enter cooldown to avoid wasted API calls
5. **Multiple providers**: 7+ data providers available

**Monitoring**: Provider health status, failover events

---

### D-002: Stale Data

| Attribute | Details |
|---|---|
| **Risk ID** | D-002 |
| **Category** | Data |
| **Description** | System makes decisions based on outdated market data |
| **Likelihood** | 2 (Timestamp validation) |
| **Impact** | 3 (Bad decisions from stale data) |
| **Score** | 6 (MEDIUM) |
| **Affected Components** | MarketData, agents |

**Mitigation Strategies**:
1. **Timestamp validation**: All data has timestamps, stale data rejected
2. **Data freshness requirements**: Minimum data update frequency
3. **Kill switch for no data**: If no fresh data available, halt trading
4. **Real-time WebSocket**: (Planned) Streaming data for live trading

**Monitoring**: Data age metrics, stale data alerts

---

### D-003: Historical Data Bias

| Attribute | Details |
|---|---|
| **Risk ID** | D-003 |
| **Category** | Data |
| **Description** | Backtested strategies overfit to historical data, failing in live trading |
| **Likelihood** | 4 (Very common) |
| **Impact** | 3 (Strategy underperforms expectations) |
| **Score** | 12 (HIGH) |
| **Affected Components** | BacktestEngine, Strategist |

**Mitigation Strategies**:
1. **Execution reality simulation**: Slippage, partial fills, latency
2. **Walk-forward optimization**: Out-of-sample testing
3. **Monte Carlo simulation**: Randomized scenario testing
4. **Constitutional risk limits**: Protect even if strategy underperforms
5. **Strategy lifecycle management**: Kill underperforming strategies

**Monitoring**: Live vs. backtest performance divergence, strategy lifecycle metrics

---

## 9. Infrastructure Risks

### I-001: Server Failure

| Attribute | Details |
|---|---|
| **Risk ID** | I-001 |
| **Category** | Infrastructure |
| **Description** | Server hosting the trading system fails |
| **Likelihood** | 2 (Cloud providers are reliable) |
| **Impact** | 4 (Trading halted, positions unprotected) |
| **Score** | 8 (MEDIUM) |
| **Affected Components** | Entire system |

**Mitigation Strategies**:
1. **Cloud hosting**: Multiple availability zones
2. **Auto-restart**: Systemd or Kubernetes auto-restart on failure
3. **Kill switch persistence**: If server dies, positions should have stop losses on exchange
4. **Exchange-side stop losses**: (Planned) Place SL on exchange, not just locally
5. **Monitoring**: Uptime monitoring with automatic alerts

**Monitoring**: Server health, uptime, auto-restart events

---

### I-002: Network Latency

| Attribute | Details |
|---|---|
| **Risk ID** | I-002 |
| **Category** | Infrastructure |
| **Description** | Network latency causes orders to be executed at worse prices than expected |
| **Likelihood** | 3 (Common, especially in crypto) |
| **Impact** | 2 (Small per-trade impact) |
| **Score** | 6 (MEDIUM) |
| **Affected Components** | Execution agent, SmartExecutor |

**Mitigation Strategies**:
1. **Smart order routing**: Considers latency in venue scoring
2. **Limit orders**: Use limit orders instead of market orders where possible
3. **Co-location**: (Planned) Co-locate servers near exchange data centers
4. **Latency monitoring**: Track execution latency per venue

**Monitoring**: Execution latency, slippage per venue

---

## 10. Risk Heat Map

```
Impact →   1          2          3          4          5
         ┌──────────┬──────────┬──────────┬──────────┬──────────┐
    5    │          │          │          │ S-001    │ T-001    │
         │          │          │          │ C-001    │ M-001    │
         │          │          │          │          │ C-003    │
         ├──────────┼──────────┼──────────┼──────────┼──────────┤
    4    │          │          │          │ O-004    │ O-001    │
L   │          │          │          │ C-002    │ M-002    │
i   │          │          │          │          │ M-003    │
k   ├──────────┼──────────┼──────────┼──────────┼──────────┤
e   3    │          │          │ T-003    │ T-001    │ D-003    │
l   │          │          │ T-005    │ A-001    │          │
i   │          │          │ O-003    │ A-004    │          │
h   │          │          │ D-001    │ I-001    │          │
o   ├──────────┼──────────┼──────────┼──────────┼──────────┤
d   2    │          │          │ T-002    │ T-004    │ A-003    │
    │          │          │ T-006    │ O-002    │ D-002    │
    │          │          │ S-003    │ M-004    │          │
    │          │          │ A-002    │          │          │
    ├──────────┼──────────┼──────────┼──────────┼──────────┤
    1    │          │          │ S-004    │          │          │
         │          │          │          │          │          │
         └──────────┴──────────┴──────────┴──────────┴──────────┘
```

### Risk Distribution

| Severity | Count | Risk IDs |
|---|---|---|
| **CRITICAL** (20-25) | 0 | — |
| **HIGH** (12-19) | 5 | T-001, A-001, O-001, O-004, M-003, D-003, C-001 |
| **MEDIUM** (6-11) | 13 | T-002, T-003, T-004, T-005, T-006, O-002, O-003, M-002, M-004, S-001, S-002, S-003, A-002, A-003, A-004, D-001, D-002, I-001, I-002 |
| **LOW** (1-5) | 2 | S-004, C-002 |

---

## 11. Mitigation Strategy Summary

### Constitutional Safety Net (Always Active)

The following protections are **always active** and cannot be disabled:

| Protection | Limit | Coverage |
|---|---|---|
| Max risk per trade | 0.5% | Limits single-trade impact |
| Max daily loss | 1% | Prevents catastrophic daily drawdowns |
| Max weekly loss | 3% | Prevents cascading weekly losses |
| Max drawdown | 15% | Kill switch trigger |
| Max position size | 10% | Diversification enforcement |
| Max leverage | 3x | Conservative leverage cap |
| Max daily trades | 5 | Anti-overtrading |
| Min risk:reward | 1:2 | Positive expectancy |
| Max correlated positions | 3 | Concentration risk limit |
| Kill switch daily PnL | -2% | Auto halt |
| Kill switch weekly PnL | -5% | Auto halt |
| Confidence threshold | 0.65 | Council debate trigger |

### Defense-in-Depth Strategy

```
Layer 1: Constitutional Limits (always active, cannot override)
    ↓
Layer 2: 9-Checkpoint Risk Gate (every trade validated)
    ↓
Layer 3: Kill Switch (automatic on breach)
    ↓
Layer 4: Council Debate (low-confidence review)
    ↓
Layer 5: Human Checkpoint (high-risk approval)
    ↓
Layer 6: Audit Trail (full decision traceability)
```

### Risk Review Schedule

| Frequency | Activity |
|---|---|
| **Real-time** | Risk limits, kill switch, PnL monitoring |
| **Daily** | Risk status review, kill switch check, trade review |
| **Weekly** | Risk register review, performance vs. backtest |
| **Monthly** | Full risk assessment update, strategy lifecycle review |
| **Quarterly** | Compliance audit, security audit, dependency audit |
| **Annually** | Full system review, regulatory review, insurance review |

---

© 2025-2026 Quant Nanggroe AI | Risk Register v4.0.0
