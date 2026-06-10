# Quant Nanggroe AI — Project Risk Register

**Version 0.2.0 | Comprehensive Risk Assessment**

> This document is the project risk register for Quant Nanggroe AI. It catalogues all identified risks across technical, operational, security, financial, and regulatory domains with probability, impact, mitigation strategies, and current status.

---

## Table of Contents

1. [Risk Register Overview](#1-risk-register-overview)
2. [Technical Risks](#2-technical-risks)
3. [Operational Risks](#3-operational-risks)
4. [Security Risks](#4-security-risks)
5. [Financial Risks](#5-financial-risks)
6. [Regulatory Risks](#6-regulatory-risks)
7. [Risk Heat Map](#7-risk-heat-map)
8. [Risk Mitigation Summary](#8-risk-mitigation-summary)

---

## 1. Risk Register Overview

### 1.1 Risk Scoring

Each risk is scored on two dimensions:

| Score | Probability | Impact |
|-------|------------|--------|
| 1 | Very Low (< 5%) | Negligible — Minor inconvenience |
| 2 | Low (5-20%) | Low — Small delay or cost increase |
| 3 | Medium (20-50%) | Medium — Significant delay or cost increase |
| 4 | High (50-80%) | High — Major project impact |
| 5 | Very High (> 80%) | Critical — Project failure or catastrophic loss |

**Risk Score = Probability × Impact**

| Risk Level | Score Range | Action Required |
|------------|-------------|----------------|
| **Critical** | 16-25 | Immediate mitigation required; escalate to leadership |
| **High** | 10-15 | Active mitigation; regular monitoring |
| **Medium** | 5-9 | Planned mitigation; periodic review |
| **Low** | 1-4 | Accept and monitor |

### 1.2 Risk Status

| Status | Description |
|--------|-------------|
| **Open** | Risk identified, not yet mitigated |
| **Mitigating** | Mitigation in progress |
| **Mitigated** | Risk reduced to acceptable level |
| **Closed** | Risk no longer applicable |
| **Accepted** | Risk accepted without mitigation |

---

## 2. Technical Risks

### TR-001: LLM Hallucination in Agent Decisions

| Field | Value |
|-------|-------|
| **ID** | TR-001 |
| **Category** | Technical |
| **Description** | LLM agents may produce hallucinated analysis — fabricating market data, misinterpreting financial metrics, or generating plausible-sounding but incorrect reasoning. This could lead to trading decisions based on false information. |
| **Probability** | 4 (High) — LLMs are known to hallucinate, especially with complex financial data |
| **Impact** | 5 (Critical) — Trading on false information could cause significant financial losses |
| **Risk Score** | 20 (Critical) |
| **Mitigation** | 1. **Constitutional risk limits** cap maximum loss regardless of agent reasoning. 2. **Data grounding requirement** — agents must reference specific data points, not general narratives. 3. **Risk agent veto** — independent risk assessment cannot be overridden by analyst agents. 4. **Kill switch** — automatic position closure on drawdown thresholds. 5. **Confidence threshold** — low-confidence decisions trigger council debate, not direct execution. |
| **Contingency** | If hallucination is detected post-trade, activate emotional lockout and review all recent trades for similar patterns. |
| **Status** | Mitigating — Constitutional limits implemented; data grounding partially enforced |

---

### TR-002: LangGraph Framework Breaking Changes

| Field | Value |
|-------|-------|
| **ID** | TR-002 |
| **Category** | Technical |
| **Description** | LangGraph is evolving rapidly (currently v0.2). Breaking changes between minor versions could break our TradingGraph implementation, requiring significant refactoring. |
| **Probability** | 3 (Medium) — LangGraph is still pre-1.0 with evolving API |
| **Impact** | 4 (High) — Would require refactoring the entire agent orchestration layer |
| **Risk Score** | 12 (High) |
| **Mitigation** | 1. Pin LangGraph version in `pyproject.toml`. 2. Abstract LangGraph-specific code behind our `TradingGraph` class. 3. Monitor LangGraph changelog for breaking changes. 4. Maintain compatibility layer for API changes. |
| **Contingency** | If breaking change occurs, evaluate migration effort vs. switching to alternative orchestration (custom StateGraph implementation). |
| **Status** | Mitigating — Version pinned; abstraction layer in place |

---

### TR-003: Factor Computation Numerical Instability

| Field | Value |
|-------|-------|
| **ID** | TR-003 |
| **Category** | Technical |
| **Description** | Alpha factors involve complex mathematical operations (ranking, correlation, division, power). Numerical instability (division by zero, NaN propagation, infinity) could produce garbage factor values that lead to incorrect signals. |
| **Probability** | 3 (Medium) — Some Alpha101 formulas inherently involve division by near-zero values |
| **Impact** | 4 (High) — Incorrect factor values lead to incorrect signals and bad trades |
| **Risk Score** | 12 (High) |
| **Mitigation** | 1. `safe_div` utility replaces zero denominators with NaN. 2. All factor outputs replace inf/-inf with NaN. 3. Factor warmup requirements prevent computation with insufficient data. 4. Factor pipeline validates outputs before passing to signal generator. |
| **Contingency** | If instability detected, disable affected factors and fall back to technical indicators only. |
| **Status** | Mitigated — safe_div implemented; NaN/inf handling in place |

---

### TR-004: Exchange API Rate Limiting

| Field | Value |
|-------|-------|
| **ID** | TR-004 |
| **Category** | Technical |
| **Description** | Exchange APIs (Binance, Alpaca, etc.) enforce rate limits. Hitting rate limits during high-frequency analysis or multiple symbol monitoring could cause data gaps or failed order placement. |
| **Probability** | 4 (High) — Rate limits are commonly hit during market volatility |
| **Impact** | 3 (Medium) — Data gaps reduce analysis quality; failed orders miss opportunities |
| **Risk Score** | 12 (High) |
| **Mitigation** | 1. Built-in rate limiting in `ExchangeConfig` (default: 5 req/s). 2. `RateLimitError` with `retry_after` hint for intelligent retry. 3. Exponential backoff with jitter. 4. Provider failover to alternative data sources. 5. TTL caching (5-min default) to reduce API calls. |
| **Contingency** | If all providers rate-limited, use cached data with stale-acceptable flag. |
| **Status** | Mitigating — Rate limiting implemented; caching in place |

---

### TR-005: Agent Pipeline Latency

| Field | Value |
|-------|-------|
| **ID** | TR-005 |
| **Category** | Technical |
| **Description** | The 9-agent pipeline with multiple LLM calls can take 30-120 seconds per run. In fast-moving markets, this latency may cause signals to be stale by the time execution occurs. |
| **Probability** | 4 (High) — LLM calls inherently have 2-10 second latency each |
| **Impact** | 3 (Medium) — Stale signals reduce alpha; may increase slippage |
| **Risk Score** | 12 (High) |
| **Mitigation** | 1. Dual-model architecture (quick-think for most agents, deep-think only for Strategist/Risk). 2. Parallel agent execution in market analysis phase. 3. Streaming via `graph.stream()` for incremental updates. 4. Caching of repeated analysis. 5. Shorter timeframes for frequently traded symbols. |
| **Contingency** | If latency is unacceptable, switch to pre-computed signals with rule-based overrides. |
| **Status** | Mitigating — Dual-model implemented; parallel execution in design |

---

### TR-006: Database Corruption or Loss

| Field | Value |
|-------|-------|
| **ID** | TR-006 |
| **Category** | Technical |
| **Description** | SQLite database corruption (from power loss, disk full, or concurrent writes) could lose trade records, positions, and audit trails. |
| **Probability** | 2 (Low) — SQLite is robust but not immune to corruption |
| **Impact** | 4 (High) — Loss of trade records breaks audit compliance and portfolio tracking |
| **Risk Score** | 8 (Medium) |
| **Mitigation** | 1. Regular database backups. 2. PostgreSQL for production (ACID compliance). 3. Alembic migrations for schema changes. 4. Trade journal JSON backup as secondary storage. |
| **Contingency** | Restore from backup; re-sync positions from exchange APIs. |
| **Status** | Mitigating — PostgreSQL support available; backup procedures documented |

---

## 3. Operational Risks

### OP-001: LLM Provider Outage

| Field | Value |
|-------|-------|
| **ID** | OP-001 |
| **Category** | Operational |
| **Description** | OpenAI, Anthropic, or Google API outage would prevent all agent analysis. Without LLM access, the pipeline cannot generate signals or risk assessments. |
| **Probability** | 3 (Medium) — Major LLM providers have 99.9% uptime but occasional outages |
| **Impact** | 5 (Critical) — Complete pipeline failure; no new trades can be initiated |
| **Risk Score** | 15 (High) |
| **Mitigation** | 1. Multi-provider LLM support (OpenAI, Anthropic, Google, Ollama local). 2. Fallback to local models (Ollama) when cloud providers are down. 3. Pre-computed signals as backup. 4. Automatic provider switching in `create_llm()`. |
| **Contingency** | Switch to local LLM or rule-based trading mode during outage. |
| **Status** | Mitigating — Multi-provider support implemented; Ollama local fallback planned |

---

### OP-002: Exchange Downtime

| Field | Value |
|-------|-------|
| **ID** | OP-002 |
| **Category** | Operational |
| **Description** | Exchange downtime (planned maintenance, DDoS, or infrastructure failure) prevents order placement and market data access. Open positions cannot be managed during downtime. |
| **Probability** | 3 (Medium) — Major exchanges have occasional downtime |
| **Impact** | 4 (High) — Cannot manage positions; potential uncontrolled losses |
| **Risk Score** | 12 (High) |
| **Mitigation** | 1. Multi-exchange support (Binance, Alpaca, CCXT 100+ exchanges). 2. Stop-loss orders placed at exchange level (not just in-system). 3. Health monitoring with `health_check()` per exchange. 4. Connection state tracking with `ExchangeState` enum. 5. Automatic reconnection on `RECONNECTING` state. |
| **Contingency** | If primary exchange is down, switch to backup exchange. If all exchanges down, positions are managed by pre-placed stop-loss orders. |
| **Status** | Mitigating — Multi-exchange support implemented; stop-loss at exchange level |

---

### OP-003: Incorrect Risk Limit Configuration

| Field | Value |
|-------|-------|
| **ID** | OP-003 |
| **Category** | Operational |
| **Description** | If constitutional risk limits were configurable, operators might set them too high (or disable them), leading to excessive risk exposure. |
| **Probability** | 1 (Very Low) — Constitutional limits are hardcoded and cannot be overridden |
| **Impact** | 5 (Critical) — Would remove the primary capital protection mechanism |
| **Risk Score** | 5 (Medium) |
| **Mitigation** | 1. Constitutional limits are hardcoded as module-level constants. 2. `override_possible: False` in every `RiskAssessment`. 3. Graph routing enforces kill switch independently. 4. No configuration parameter to change limits. |
| **Contingency** | N/A — Limits cannot be changed without code modification and redeployment. |
| **Status** | Mitigated — Hardcoded limits with no override mechanism |

---

### OP-004: Overtrading Due to Agent Enthusiasm

| Field | Value |
|-------|-------|
| **ID** | OP-004 |
| **Category** | Operational |
| **Description** | Agents may generate too many signals in volatile markets, leading to excessive trading activity, higher commissions, and whipsaw losses. |
| **Probability** | 3 (Medium) — LLMs tend to be action-biased in volatile conditions |
| **Impact** | 3 (Medium) — Higher costs, potential whipsaw losses |
| **Risk Score** | 9 (Medium) |
| **Mitigation** | 1. `MAX_TRADES_PER_DAY = 5` constitutional limit. 2. Cooldown guard prevents rapid successive trades. 3. Emotional lockout after losses. 4. Confidence threshold requires high conviction for execution. 5. Risk:reward minimum (1:2) filters low-quality setups. |
| **Contingency** | If overtrading detected, activate emotional lockout and review agent configurations. |
| **Status** | Mitigated — Constitutional limits and guard pipeline in place |

---

## 4. Security Risks

### SR-001: API Key Exposure

| Field | Value |
|-------|-------|
| **ID** | SR-001 |
| **Category** | Security |
| **Description** | API keys for exchanges, LLM providers, and data sources could be exposed through logs, error messages, configuration files, or code repository commits. |
| **Probability** | 3 (Medium) — Common security incident in software projects |
| **Impact** | 5 (Critical) — Exposed exchange keys could lead to unauthorized trading and financial loss |
| **Risk Score** | 15 (High) |
| **Mitigation** | 1. KeyVault reads only from environment variables — no config files. 2. Secret values never logged (even at DEBUG level). 3. `mask_value()` for safe display in error messages. 4. `.env` in `.gitignore`. 5. Pre-commit hooks to detect committed secrets. 6. IP restrictions on exchange API keys where supported. |
| **Contingency** | If key is exposed, immediately rotate the key at the provider and audit all recent activity. |
| **Status** | Mitigating — KeyVault implemented; masking in place; pre-commit hooks planned |

---

### SR-002: Prompt Injection Attack

| Field | Value |
|-------|-------|
| **ID** | SR-002 |
| **Category** | Security |
| **Description** | Malicious input (from news feeds, web search results, or user inputs) could contain prompt injection that causes agents to ignore risk limits, generate harmful trades, or leak information. |
| **Probability** | 3 (Medium) — LLMs are susceptible to prompt injection |
| **Impact** | 5 (Critical) — Could bypass risk management and cause unauthorized trades |
| **Risk Score** | 15 (High) |
| **Mitigation** | 1. Constitutional risk limits are hardcoded — even if agents are compromised, risk gates still enforce limits. 2. Kill switch operates independently of agent reasoning. 3. Input sanitization for external data sources. 4. Agent prompts include injection resistance instructions. 5. Risk agent operates independently from analysis agents. |
| **Contingency** | If injection detected, activate kill switch, review all recent trades, and patch the injection vector. |
| **Status** | Mitigating — Constitutional limits provide architectural protection |

---

### SR-003: Unauthorized Access to Trading API

| Field | Value |
|-------|-------|
| **ID** | SR-003 |
| **Category** | Security |
| **Description** | Unauthorized access to the FastAPI trading endpoints could allow external actors to execute trades, modify positions, or access sensitive portfolio information. |
| **Probability** | 2 (Low) — Standard web security practices |
| **Impact** | 5 (Critical) — Unauthorized trading could cause significant financial loss |
| **Risk Score** | 10 (High) |
| **Mitigation** | 1. API key authentication on all trading endpoints. 2. RBAC with 4 roles (admin, trader, analyst, viewer). 3. CORS restrictions in production. 4. Rate limiting on API endpoints. 5. HTTPS enforcement. 6. WebSocket authentication. |
| **Contingency** | If unauthorized access detected, revoke all API keys, audit all recent trades, and enable IP allowlisting. |
| **Status** | Mitigating — Authentication and RBAC implemented; rate limiting planned |

---

## 5. Financial Risks

### FR-001: Cascading Loss from Correlated Positions

| Field | Value |
|-------|-------|
| **ID** | FR-001 |
| **Category** | Financial |
| **Description** | Multiple positions in correlated assets (e.g., BTC and ETH, or tech stocks) could suffer simultaneous drawdowns during market crashes, amplifying losses beyond the per-position risk limits. |
| **Probability** | 3 (Medium) — Correlated drawdowns are common in crypto and equity markets |
| **Impact** | 5 (Critical) — Portfolio drawdown could exceed constitutional limits |
| **Risk Score** | 15 (High) |
| **Mitigation** | 1. `MAX_CORRELATED_POSITIONS = 3` constitutional limit. 2. Correlation monitor tracks pairwise correlation between positions. 3. Risk agent checks correlation before approving new positions. 4. Kill switch activates on portfolio-level drawdown exceeding 15%. 5. Risk parity allocation reduces concentration. |
| **Contingency** | If correlation breakdown occurs, activate kill switch and close most correlated positions first. |
| **Status** | Mitigating — Correlation monitoring implemented; constitutional limit in place |

---

### FR-002: Slippage and Execution Costs

| Field | Value |
|-------|-------|
| **ID** | FR-002 |
| **Category** | Financial |
| **Description** | Real-world execution costs (slippage, spreads, commissions) may be higher than simulated in backtesting, leading to actual returns significantly below backtested expectations. |
| **Probability** | 4 (High) — Execution costs are consistently underestimated |
| **Impact** | 3 (Medium) — Reduces profitability but unlikely to cause catastrophic loss |
| **Risk Score** | 12 (High) |
| **Mitigation** | 1. Execution reality simulation in backtesting (15-30% return reduction). 2. Dynamic spread widening during high volatility. 3. Commission tracking in all trades. 4. Slippage monitoring and reporting. 5. Position sizing accounts for execution costs. |
| **Contingency** | If execution costs consistently exceed estimates, reduce position sizes and increase minimum risk:reward thresholds. |
| **Status** | Mitigating — Execution reality simulation implemented |

---

### FR-003: Model Degradation Over Time

| Field | Value |
|-------|-------|
| **ID** | FR-003 |
| **Category** | Financial |
| **Description** | Trading strategies and alpha factors that work in backtesting may degrade over time as market conditions change (regime shifts, increased competition, structural changes). |
| **Probability** | 4 (High) — All quantitative strategies experience alpha decay |
| **Impact** | 3 (Medium) — Gradual profit reduction, not catastrophic |
| **Risk Score** | 12 (High) |
| **Mitigation** | 1. Walk-forward optimization for ongoing strategy validation. 2. Monte Carlo resampling for robustness testing. 3. Darwinian strategy lifecycle (ACTIVE → HIBERNATING → KILLED). 4. Continuous monitoring of strategy performance metrics. 5. Risk parity allocation reduces dependence on any single strategy. |
| **Contingency** | If strategy performance degrades significantly, hibernate the strategy and shift capital to better-performing alternatives. |
| **Status** | Mitigating — Walk-forward and Monte Carlo implemented; strategy lifecycle planned |

---

## 6. Regulatory Risks

### RR-001: Unregistered Investment Advice

| Field | Value |
|-------|-------|
| **ID** | RR-001 |
| **Category** | Regulatory |
| **Description** | Operating an AI trading system may constitute providing investment advice, which could require registration with financial regulators (SEC, FCA, etc.) depending on jurisdiction and usage. |
| **Probability** | 2 (Low) — Depends on how the system is marketed and used |
| **Impact** | 5 (Critical) — Regulatory action could include fines, cease-and-desist, or criminal liability |
| **Risk Score** | 10 (High) |
| **Mitigation** | 1. Clear disclaimers that the system is for educational/research purposes. 2. No investment advice claims in documentation or marketing. 3. Paper trading as default mode. 4. User acknowledges risks before enabling live trading. 5. Legal review of terms of service. |
| **Contingency** | If regulatory inquiry received, immediately consult legal counsel and suspend live trading. |
| **Status** | Mitigating — Disclaimers in documentation; paper trading default |

---

### RR-002: Data Privacy Compliance

| Field | Value |
|-------|-------|
| **ID** | RR-002 |
| **Category** | Regulatory |
| **Description** | The system collects user data (API keys, trade history, portfolio information) that may be subject to privacy regulations (GDPR, CCPA) depending on jurisdiction. |
| **Probability** | 3 (Medium) — Applicable if serving EU or California users |
| **Impact** | 3 (Medium) — Fines up to 4% of annual revenue under GDPR |
| **Risk Score** | 9 (Medium) |
| **Mitigation** | 1. Minimal data collection — only what's necessary for operation. 2. API keys stored in environment variables, not databases. 3. User data encryption at rest. 4. Data retention policies. 5. Privacy policy documentation. |
| **Contingency** | If privacy concern identified, audit data handling practices and implement necessary changes. |
| **Status** | Open — Privacy policy and data handling procedures need formalization |

---

### RR-003: Market Manipulation Detection

| Field | Value |
|-------|-------|
| **ID** | RR-003 |
| **Category** | Regulatory |
| **Description** | Automated trading systems can trigger market manipulation detection at exchanges or regulators, especially if making rapid trades or operating in low-liquidity markets. |
| **Probability** | 2 (Low) — Our system is not designed for high-frequency or manipulative trading |
| **Impact** | 4 (High) — Account suspension, regulatory investigation, or legal action |
| **Risk Score** | 8 (Medium) |
| **Mitigation** | 1. `MAX_TRADES_PER_DAY = 5` prevents rapid trading patterns. 2. Position sizing limits prevent market impact. 3. No spoofing or layering strategies. 4. Trading only in liquid markets. 5. Compliance monitoring for trade patterns. |
| **Contingency** | If exchange flags suspicious activity, immediately reduce trading frequency and review recent trade patterns. |
| **Status** | Mitigated — Trade frequency and position size limits reduce manipulation risk |

---

## 7. Risk Heat Map

```
                    IMPACT
              1    2    3    4    5
         ┌────┬────┬────┬────┬────┐
    5    │    │    │    │    │    │
         │    │    │    │    │    │
P   ├────┼────┼────┼────┼────┼────┤
R   4    │    │    │TR-5│TR-4│TR-1│
O        │    │    │FR-2│TR-2│FR-1│
B   ├────┼────┼────┼────┼────┼────┤
A   3    │    │    │    │RR-2│OP-1│
B        │    │    │    │FR-3│SR-1│
I   ├────┼────┼────┼────┼────┼────┤
L   2    │    │    │    │RR-3│OP-2│
I        │    │    │    │TR-6│SR-3│
T   ├────┼────┼────┼────┼────┼────┤
Y   1    │    │    │    │    │OP-3│
        │    │    │    │    │    │
         └────┴────┴────┴────┴────┘

         Low ←── RISK LEVEL ──→ Critical
```

### Risk Distribution

| Risk Level | Count | Risk IDs |
|------------|-------|----------|
| **Critical (16-25)** | 1 | TR-001 |
| **High (10-15)** | 8 | TR-002, TR-004, TR-005, OP-001, OP-002, SR-001, SR-002, FR-001, FR-002, FR-003, RR-001 |
| **Medium (5-9)** | 5 | TR-003, TR-006, OP-004, RR-002, RR-003 |
| **Low (1-4)** | 1 | OP-003 |

---

## 8. Risk Mitigation Summary

### 8.1 Mitigation Coverage

| Category | Total Risks | Mitigated | Mitigating | Open | Accepted |
|----------|-------------|-----------|------------|------|----------|
| Technical | 6 | 1 | 5 | 0 | 0 |
| Operational | 4 | 1 | 2 | 0 | 1 |
| Security | 3 | 0 | 3 | 0 | 0 |
| Financial | 3 | 0 | 3 | 0 | 0 |
| Regulatory | 3 | 1 | 1 | 1 | 0 |
| **Total** | **19** | **3** | **14** | **1** | **1** |

### 8.2 Top Priority Mitigations

| Priority | Risk | Mitigation Action | Owner | Target Date |
|----------|------|-------------------|-------|-------------|
| 1 | TR-001 (LLM Hallucination) | Implement data grounding validation in agent prompts | Agent Team | Q1 2026 |
| 2 | SR-001 (API Key Exposure) | Add pre-commit secret detection hooks | Security Team | Q1 2026 |
| 3 | SR-002 (Prompt Injection) | Implement input sanitization for external data | Security Team | Q1 2026 |
| 4 | OP-001 (LLM Provider Outage) | Set up Ollama local model fallback | Ops Team | Q2 2026 |
| 5 | FR-001 (Correlated Loss) | Implement real-time correlation monitoring dashboard | Risk Team | Q2 2026 |

### 8.3 Constitutional Risk as Mitigation

The constitutional risk system serves as a **cross-cutting mitigation** for multiple risks:

| Risk | Constitutional Mitigation |
|------|--------------------------|
| TR-001 (Hallucination) | Risk limits cap losses regardless of agent reasoning |
| SR-002 (Prompt Injection) | Constitutional limits cannot be overridden by any agent |
| FR-001 (Correlated Loss) | Max correlated positions and drawdown limits |
| OP-004 (Overtrading) | Max 5 trades per day |
| FR-002 (Execution Costs) | Max position size and risk:reward limits reduce cost impact |
| RR-003 (Market Manipulation) | Trade frequency limits prevent rapid trading patterns |

---

*© 2025-2026 Quant Nanggroe AI | Risk Register v0.2.0*
