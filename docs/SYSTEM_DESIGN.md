# Quant Nanggroe AI — System Design Document

**Version 0.2.0 | Agentic Trading Intelligence OS**

> This document describes the detailed system design of Quant Nanggroe AI, covering design principles, component interactions, data flows, state management, error handling, configuration, security, performance, and scalability.

---

## Table of Contents

1. [Design Principles and Philosophy](#1-design-principles-and-philosophy)
2. [Component Interaction Diagrams](#2-component-interaction-diagrams)
3. [Data Flow Diagrams](#3-data-flow-diagrams)
4. [State Management Design](#4-state-management-design)
5. [Error Handling Strategy](#5-error-handling-strategy)
6. [Configuration Management](#6-configuration-management)
7. [Security Design](#7-security-design)
8. [Performance Considerations](#8-performance-considerations)
9. [Scalability Design](#9-scalability-design)

---

## 1. Design Principles and Philosophy

### 1.1 Deterministic Reasoning Over Subjective AI

The fundamental design premise of Quant Nanggroe AI is that LLMs are treated as **Logical Reasoning Engines** operating under strict contracts, not as advisors producing qualitative analysis. This principle manifests in three absolute rules:

1. **No Subjective Opinions**: Agents are forbidden from producing "vibes-based" analysis, sentiment narratives, or qualitative assessments. Every output must be grounded in observable, numerical data.
2. **Mandatory Data Grounding**: All reasoning must originate from Layer 0 data. An agent cannot reason about market conditions without first receiving contextual data. This eliminates hallucination at the architectural level.
3. **Constitutional Immutability**: Risk limits are hardcoded and cannot be overridden by any agent, LLM reasoning, or configuration change. This is an architectural guarantee of capital protection.

### 1.2 Principle of Least Privilege for Agents

Each agent operates within a strictly bounded domain:

- **Researcher** can only observe and report — it cannot generate trading signals
- **Strategist** can generate signals but cannot execute trades
- **Risk** can veto trades but cannot create them
- **Trader** can propose decisions but cannot bypass risk checks
- **Execution** can place orders but only within risk-approved parameters

This separation ensures that no single agent failure can lead to uncontrolled capital deployment.

### 1.3 Fail-Safe Defaults

Every system component defaults to the safest possible state:

- If risk assessment fails → trade is VETOED
- If an agent crashes → its output is replaced with a safe default
- If data is unavailable → no trade signal is generated
- If confidence is below threshold → council debate is triggered
- If kill switch activates → all positions are closed immediately

### 1.4 Separation of Concerns

The system maintains strict separation between:

- **Analysis** (agents observing market conditions)
- **Decision** (agents proposing trade actions)
- **Validation** (risk engine checking constitutional compliance)
- **Execution** (exchange layer implementing approved actions)
- **Reflection** (post-trade analysis and learning)

No concern can bypass or subsume another. The pipeline is linear and unidirectional.

### 1.5 Auditability

Every decision must be fully traceable:

- Agent outputs are recorded with confidence scores and reasoning
- Risk assessments include all 9 checkpoint values and limits
- Trade decisions carry the full chain from signal → risk → execution
- The audit trail supports full reconstruction of any trading decision

---

## 2. Component Interaction Diagrams

### 2.1 Trading Pipeline Component Interactions

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Trading Pipeline Run                          │
│                                                                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐     │
│  │ Researcher│───►│Strategist│───►│   Risk   │───►│ Portfolio│     │
│  │          │    │          │    │          │    │          │     │
│  │ • Web    │    │ • Alpha  │    │ • 9-Gate │    │ • Risk   │     │
│  │   Search │    │   Factors│    │   Check  │    │   Parity │     │
│  │ • Fin.   │    │ • Signal │    │ • VaR    │    │ • Rebal. │     │
│  │   Data   │    │   Gen.   │    │ • Kelly  │    │ • Alloc. │     │
│  │ • News   │    │ • Conf.  │    │ • Drawdn │    │          │     │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘     │
│       │               │               │               │            │
│       ▼               ▼               ▼               ▼            │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐     │
│  │  Macro   │    │  Trader  │    │ Council  │    │Execution │     │
│  │          │    │          │    │  Debate  │    │          │     │
│  │ • Regime │    │ • Decisions│   │ • Bull   │    │ • Orders │     │
│  │ • Econ   │    │ • Position│    │ • Bear   │    │ • Fills  │     │
│  │   Cal.   │    │   Sizing │    │ • Judge  │    │ • Guards │     │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘     │
│       │                                               │            │
│       ▼                                               ▼            │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐     │
│  │  Crypto  │    │  Forex   │    │Reflection│    │ Journal  │     │
│  │          │    │          │    │          │    │          │     │
│  │ • On-chain│   │ • FX Rate│    │ • Post   │    │ • Record │     │
│  │ • Whale  │    │ • Carry  │    │   Trade  │    │ • Learn  │     │
│  │ • Sentim.│    │ • CB Pol.│    │ • Review │    │ • PnL    │     │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Agent-Engine Interaction Map

```
Agent Layer                    Engine Layer
─────────────                  ────────────
Researcher  ──────────────────► Data Providers (yfinance, Alpaca, Binance)
Strategist  ──────────────────► Factor Library (Alpha101, GTJA191, Barra)
Strategist  ──────────────────► ML Models (Signal Generator, Ensemble)
Risk        ──────────────────► Risk Engine (VaR, Kelly, Drawdown, KillSwitch)
Trader      ──────────────────► Execution Engine (Order Management, Guards)
Portfolio   ──────────────────► Risk Engine (Risk Parity, Position Sizing)
Execution   ──────────────────► Exchange Layer (CCXT, Alpaca, Paper)
Macro       ──────────────────► Data Providers (FRED, Economic Calendar)
Crypto      ──────────────────► Exchange Layer (Binance, CoinGecko)
Forex       ──────────────────► Data Providers (AlphaVantage, FX Rates)
```

### 2.3 MCP Component Interaction

```
┌─────────────────┐
│  Agent (LLM)    │
│  "Call tool     │
│   market_data   │
│   .get_ohlcv"   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     JSON-RPC 2.0     ┌─────────────────┐
│   MCP Client    │ ◄──────────────────► │   MCP Server    │
│                 │    tools/call         │                 │
│ • Serialize     │    request            │ • Route to      │
│   request       │                       │   handler       │
│ • Handle        │ ◄──────────────────► │ • Execute       │
│   response      │    tool result        │   tool          │
│ • Stream SSE    │                       │ • Return result │
└─────────────────┘                       └─────────────────┘
                                                  │
                                                  ▼
                                          ┌─────────────────┐
                                          │  Tool Handler   │
                                          │  (market_data   │
                                          │   .get_ohlcv)   │
                                          │                 │
                                          │ • Validate args │
                                          │ • Fetch data    │
                                          │ • Format result │
                                          └─────────────────┘
```

### 2.4 Memory Layer Interactions

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Trade       │     │  Knowledge   │     │   Paging     │
│  Journal     │     │  Graph       │     │   System     │
│              │     │              │     │              │
│ • Record     │────►│ • Symbol→    │     │ • Context    │
│   entries    │     │   Sector     │     │   window     │
│ • Record     │────►│ • Strategy→  │     │   mgmt       │
│   exits      │     │   Perf       │     │              │
│ • Calculate  │     │ • Correlation│     │ • Priority   │
│   PnL        │     │   patterns   │     │   eviction   │
│ • Summarize  │────►│ • Regime→    │     │              │
│   perform.   │     │   Behavior   │     │ • Recall     │
│              │     │              │     │   mechanism  │
└──────┬───────┘     └──────────────┘     └──────────────┘
       │
       ▼
┌──────────────┐
│   Session    │
│   Manager    │
│              │
│ • Session    │
│   lifecycle  │
│ • Cross-     │
│   session    │
│   state      │
│ • Pipeline   │
│   run IDs    │
└──────────────┘
```

---

## 3. Data Flow Diagrams

### 3.1 Complete Trading Pipeline Data Flow

```
[Market Data Providers]        [Economic Data]       [On-Chain Data]
   yfinance, Alpaca,             FRED,                Binance,
   Binance, Polygon              AlphaVantage         CoinGecko
         │                           │                     │
         ▼                           ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Data Normalization & Enrichment                │
│  • Provider health scoring  • Trust score tagging                │
│  • Auto-failover            • Latency estimation                  │
│  • TTL caching              • Domain type classification          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Market Analysis Phase                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │Researcher│  │  Macro   │  │  Crypto  │  │  Forex   │       │
│  │  Agent   │  │  Agent   │  │  Agent   │  │  Agent   │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       │              │              │              │              │
│       ▼              ▼              ▼              ▼              │
│   research_output  macro_output  crypto_output  forex_output    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Signal Generation Phase                        │
│  Strategist Agent:                                               │
│  • Synthesizes all analysis outputs                              │
│  • Computes alpha factors (Alpha101, GTJA191, Technical)        │
│  • Generates signals with direction, confidence, entry/exit     │
│  • Output: signals[], strategist_output, confidence              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Risk Assessment Phase                          │
│  Risk Agent:                                                     │
│  • 9-checkpoint constitutional gate                              │
│  • VaR/CVaR computation                                          │
│  • Kelly criterion sizing                                        │
│  • Drawdown monitoring                                           │
│  • Output: risk_assessment, risk_verdict, kill_switch_active     │
│                                                                   │
│  ┌─────────────── Conditional Routing ──────────────┐           │
│  │ VETOED → HALT (END)                               │           │
│  │ KILL_SWITCH → Emergency Exit                      │           │
│  │ confidence < 0.65 → Council Debate                │           │
│  │ APPROVED → Continue to Portfolio Optimization     │           │
│  └───────────────────────────────────────────────────┘           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Portfolio Optimization Phase                   │
│  Portfolio Agent:                                                │
│  • Risk parity allocation                                        │
│  • Position sizing within constitutional limits                  │
│  • Rebalancing recommendations                                   │
│  • Output: portfolio_output                                      │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Execution Decision Phase                       │
│  Trader Agent:                                                   │
│  • Final BUY/SELL/HOLD decisions                                 │
│  • Position sizing and stop-loss/take-profit levels              │
│  • Output: decisions[], trader_output, confidence                │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Order Execution Phase                          │
│  Execution Agent:                                                │
│  • Order routing to appropriate exchange                         │
│  • Guard pipeline (cooldown, whitelist, max position)            │
│  • Fill tracking and slippage monitoring                         │
│  • Output: execution_output, orders_placed                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Reflection Phase                               │
│  Council Debate:                                                 │
│  • Post-trade analysis by all agents                             │
│  • Bull/Bear debate on trade quality                             │
│  • Risk debate (conservative/neutral/aggressive)                 │
│  • Journal recording with reflections                            │
│  • Output: debate_state                                          │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Risk Assessment Data Flow

```
[Proposed Trade]
      │
      ▼
┌──────────────────────────────────┐
│ Checkpoint 1: Per-Trade Risk     │──► risk_amount / portfolio ≤ 0.5%
├──────────────────────────────────┤
│ Checkpoint 2: Daily Loss         │──► daily_pnl_pct ≤ 1.0%
├──────────────────────────────────┤
│ Checkpoint 3: Weekly Loss        │──► weekly_pnl_pct ≤ 3.0%
├──────────────────────────────────┤
│ Checkpoint 4: Risk:Reward        │──► R:R ≥ 1:2
├──────────────────────────────────┤
│ Checkpoint 5: Position Size      │──► position_size ≤ 10% portfolio
├──────────────────────────────────┤
│ Checkpoint 6: Correlation        │──► correlated_positions ≤ 3
├──────────────────────────────────┤
│ Checkpoint 7: Leverage           │──► leverage ≤ 3x
├──────────────────────────────────┤
│ Checkpoint 8: Drawdown           │──► drawdown ≤ 15%
├──────────────────────────────────┤
│ Checkpoint 9: Trade Frequency    │──► trades_today ≤ 5
└──────────────┬───────────────────┘
               │
      ┌────────┼────────┐
      │        │        │
  All Pass  Any Fail  Critical
      │        │        │
      ▼        ▼        ▼
  APPROVED   VETOED  KILL_SWITCH
```

### 3.3 Data Provider Failover Flow

```
[Data Request]
      │
      ▼
[Primary Provider] ──► Success? ──► Yes ──► Return Data
      │
      No (Error/Timeout)
      │
      ▼
[Retry with Backoff] ──► Retry 1 (1s) ──► Retry 2 (2s) ──► Retry 3 (4s)
      │
      All Retries Failed
      │
      ▼
[Fallback Provider] ──► Success? ──► Yes ──► Return Data
      │
      No
      │
      ▼
[Mark Primary as Unhealthy] ──► Cooldown Period
      │
      ▼
[Return Error / Use Cached Data (if available)]
```

---

## 4. State Management Design

### 4.1 LangGraph AgentState

The `AgentState` TypedDict is the central state object that flows through the LangGraph trading pipeline. It is defined in `quant_nanggroe/agents/state.py` and carries all information between nodes.

**State Lifecycle**:

```
create_initial_state()
       │
       ▼
┌──────────────────────────────────────────────┐
│ Initial State:                               │
│   symbols: [...]                             │
│   trade_date: "2026-03-04"                   │
│   market_data: {}                            │
│   risk_verdict: "VETOED" (safe default)      │
│   confidence: 0.0                            │
│   kill_switch_active: False                  │
│   should_halt: False                         │
│   metadata.constitutional_limits: {...}      │
└──────────────────────────────────────────────┘
       │
       ▼  (Each node adds/updates fields)
┌──────────────────────────────────────────────┐
│ After Market Analysis:                       │
│   research_output: "..."                     │
│   macro_output: "..."                        │
│   crypto_output: "..."                       │
│   forex_output: "..."                        │
│   agent_outputs.researcher: {...}            │
│   agent_outputs.macro: {...}                 │
│   iteration: 1                               │
└──────────────────────────────────────────────┘
       │
       ▼  (Signal generation adds)
┌──────────────────────────────────────────────┐
│ After Signal Generation:                     │
│   signals: [{symbol, direction, action,      │
│             confidence, entry, SL, TP}]      │
│   strategist_output: "..."                   │
│   confidence: 0.72                           │
└──────────────────────────────────────────────┘
       │
       ▼  (Risk assessment adds)
┌──────────────────────────────────────────────┐
│ After Risk Assessment:                       │
│   risk_assessment: {verdict, checkpoints,    │
│     var_95, cvar_95, kelly_fraction, ...}    │
│   risk_verdict: "APPROVED"                   │
│   kill_switch_active: False                  │
└──────────────────────────────────────────────┘
```

### 4.2 State Immutability Guarantees

- Each graph node returns a **partial state update** (dictionary), not a mutation of the existing state
- LangGraph merges partial updates into the full state automatically
- The `sender` field tracks which node last modified the state
- The `iteration` field increments with each pipeline pass

### 4.3 Sub-States

The system uses specialized sub-states for different mechanisms:

**DebateState**: Bull/Bear debate with `bull_history`, `bear_history`, `judge_decision`, `count`

**RiskDebateState**: Three-way risk debate with `conservative_history`, `neutral_history`, `aggressive_history`, `judge_decision`, `count`

**CouncilResult**: Vote aggregation with `final_decision`, `votes[]`, `weighted_score`, `consensus_level`, `requires_human_review`

### 4.4 Persistent State

- **Database State**: SQLAlchemy ORM models for trades, positions, portfolio snapshots, agent logs, risk events, strategies, backtest results
- **Journal State**: TradeJournal with in-memory trades list and open positions dict, persisted to JSON
- **Session State**: Session manager for cross-request state continuity
- **Knowledge Graph**: Entity-relationship storage for market knowledge

---

## 5. Error Handling Strategy

### 5.1 Agent-Level Error Handling

Each agent node in the LangGraph graph wraps its execution in a try/except block:

```python
def _market_analysis_node(self, state: AgentState) -> Dict[str, Any]:
    updates = {}
    try:
        researcher = self._factory.create_agent("researcher")
        result = researcher(state)
        updates["research_output"] = result.get("research_output", "")
    except Exception as e:
        logger.error(f"Researcher agent failed: {e}")
        updates["research_output"] = f"Research failed: {e}"
    return updates
```

**Design principle**: Agent failures never crash the pipeline. They produce degraded but safe outputs.

### 5.2 Exchange Error Hierarchy

```
ExchangeError (base)
├── ConnectionError          # Network/connection issues
├── OrderError               # Order submission/cancellation failures
│   └── .order_id           # Associated order ID
├── RateLimitError           # Exchange rate limits
│   └── .retry_after        # Seconds until retry allowed
├── AuthenticationError      # Invalid API keys
├── InsufficientFundsError   # Not enough balance
└── MarketDataError          # Data retrieval failures
```

Each error type carries contextual information (exchange name, order ID, retry delay) to enable intelligent recovery.

### 5.3 Risk Engine Fallback

When the risk engine is unavailable, the system defaults to the safest behavior:

```python
except Exception as risk_err:
    return RiskCheckResponse(
        verdict="CONDITIONAL",
        approved=False,
        veto_reason="Risk engine unavailable - conditional hold",
    )
```

No trade is ever approved when risk assessment cannot be performed.

### 5.4 Graph-Level Error Handling

The top-level `TradingGraph.run()` method catches all exceptions:

```python
try:
    final_state = self._graph.invoke(initial_state)
except Exception as e:
    return {
        **initial_state,
        "error": str(e),
        "should_halt": True,
    }
```

### 5.5 Data Provider Error Handling

- **Exponential backoff**: 1s → 2s → 4s → 8s → max threshold
- **Provider cooldown**: Failed providers enter cooldown period
- **Health-based prioritization**: Providers ranked by success rate and latency
- **Cache fallback**: Stale cached data used when all providers fail

### 5.6 MCP Error Handling

Standardized error codes (MCP-specific and JSON-RPC standard):

- `-32700` to `-32603`: JSON-RPC standard errors
- `-32000` to `-32099`: MCP-specific errors (unknown tool, execution failed, rate limit exceeded)

Tool execution errors return `ToolCallResult.error_result()` with structured error information.

---

## 6. Configuration Management

### 6.1 Pydantic Settings Architecture

All configuration is managed through the `Settings` class in `quant_nanggroe/config/settings.py`:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="QNAI_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
```

### 6.2 Configuration Categories

| Category | Fields | Environment Prefix |
|----------|--------|-------------------|
| **Application** | `app_name`, `version`, `debug` | `QNAI_APP_NAME`, etc. |
| **Database** | `database_url`, `redis_url` | `QNAI_DATABASE_URL`, etc. |
| **LLM API Keys** | `openai_api_key`, `anthropic_api_key`, `google_api_key` | Direct env var names |
| **Trading API Keys** | `alpaca_api_key`, `binance_api_key`, etc. | Direct env var names |
| **LLM Defaults** | `default_llm_provider`, `default_llm_model`, `default_llm_temperature` | `QNAI_DEFAULT_LLM_PROVIDER`, etc. |
| **Logging** | `log_level`, `log_format` | `QNAI_LOG_LEVEL`, etc. |
| **Constitutional Risk** | `risk_max_per_trade`, `risk_max_daily_loss`, etc. | `QNAI_RISK_MAX_PER_TRADE`, etc. |
| **Backtesting** | `backtest_default_commission`, `backtest_default_slippage`, `backtest_default_initial_capital` | `QNAI_BACKTEST_DEFAULT_COMMISSION`, etc. |
| **Data** | `data_cache_ttl`, `data_provider_timeout` | `QNAI_DATA_CACHE_TTL`, etc. |

### 6.3 Validation Rules

- **Log level**: Must be one of {DEBUG, INFO, WARNING, ERROR, CRITICAL}
- **Risk limits**: Ranged with `ge`/`le` constraints (e.g., `risk_max_per_trade` between 0.1 and 2.0)
- **Secrets**: Required for live trading, optional for development
- **API keys**: Validated at runtime when needed, not at startup

### 6.4 Configuration Hierarchy

```
1. Environment variables (highest priority)
2. .env file
3. Default values in Settings class (lowest priority)
4. Constitutional limits are HARDCODED and ignore all of the above
```

---

## 7. Security Design

### 7.1 KeyVault Architecture

The `KeyVault` class provides the single entry point for all secrets:

- **Source**: Environment variables ONLY — no files, no .env parsing, no hardcoded defaults
- **Caching**: In-memory cache for performance with `clear_cache()` for forced re-reads
- **Masking**: `mask_value()` produces safe display strings (e.g., `sk-a1****`)
- **Fail-fast**: `SecretNotFoundError` raised immediately for missing required secrets
- **Never logs values**: Secret values never appear in logs at any level

### 7.2 Authentication and Authorization

- **User model**: Role-based access control with 4 roles:
  - `admin`: Full system access
  - `trader`: Trading operations
  - `analyst`: Read-only analysis
  - `viewer`: Dashboard viewing only
- **API keys**: Per-user API keys for programmatic access
- **Session tracking**: `last_login_at` timestamp per user

### 7.3 Audit Trail

The `AuditLogger` (`security/audit.py`) provides comprehensive event logging:

| Layer | Events Logged |
|-------|---------------|
| Market | Data provider status, price updates, regime changes |
| Agent | Agent outputs, confidence scores, tool calls |
| Decision | Decision table evaluations, confluence checks |
| Risk | Constitutional rule checks, violations, kill switch |
| Execution | Order placement, fill confirmation, slippage |

Each audit entry includes: timestamp, layer, severity, event type, payload, source.

### 7.4 Credential Inference

The `credential_inference.py` module automatically detects:
- Weak or misconfigured API keys
- Expired credentials
- Insecure configurations (e.g., production debug mode)

### 7.5 Constitutional Security

The constitutional risk limits are a security feature:

- **Immutable**: Hardcoded in `agents/state.py` as module-level constants
- **Non-overridable**: `override_possible: False` in every `RiskAssessment`
- **Enforced at architecture level**: The graph conditional routing cannot be bypassed
- **Kill switch**: Independent of any agent or LLM — triggered by raw P&L thresholds

---

## 8. Performance Considerations

### 8.1 LLM Call Optimization

- **Dual-model architecture**: Deep-think (gpt-4o) for Strategist/Risk, Quick-think (gpt-4o-mini) for others
- **Temperature 0.0**: Deterministic outputs for reproducibility
- **Parallel agent execution**: Researcher, Macro, Crypto, Forex run in parallel in the market analysis phase

### 8.2 Data Caching

- **TTL-based caching**: 5-minute default for market data (`data_cache_ttl = 300`)
- **Provider timeout**: 30-second default (`data_provider_timeout = 30`)
- **LRU cache on settings**: `@lru_cache` on `get_settings()` avoids re-parsing

### 8.3 Factor Computation Performance

The factor library is designed for vectorized computation:

- All factors operate on Pandas DataFrames with numpy operations
- Cross-sectional `rank()` uses vectorized pandas ranking
- Time-series operations use rolling windows with optimized implementations
- Safe division (`safe_div`) handles zero denominators without exceptions

### 8.4 Backtesting Performance

- **Vectorized backtesting**: VectorBT-compatible approach for 10-100x speedup over event-driven
- **Execution reality simulation**: Configurable overhead for realism (typically 15-30% return reduction)
- **Monte Carlo resampling**: Bootstrap confidence intervals without full re-computation

### 8.5 Database Performance

- **Indexed queries**: Composite indexes on frequently queried columns (symbol+created_at, status+created_at)
- **Eager loading**: `lazy="selectin"` on relationships to avoid N+1 queries
- **JSON columns**: Flexible metadata storage without schema migrations

---

## 9. Scalability Design

### 9.1 Horizontal Scaling

- **Stateless API pods**: FastAPI instances share no in-memory state
- **Redis pub/sub**: Cross-pod communication for trade events and risk alerts
- **Worker processes**: Independent background workers for long-running tasks (backtests, analysis)

### 9.2 Exchange Connection Pooling

- **Connection reuse**: CCXT exchange instances are reused across requests
- **Rate limiting**: Built-in rate limit management per exchange
- **Health monitoring**: Connection health checks with automatic reconnection

### 9.3 Agent Scalability

- **On-demand creation**: `AgentFactory` creates agents per pipeline run, not persistent
- **LLM provider flexibility**: Supports OpenAI, Anthropic, Google, Ollama, OpenRouter
- **Parallel execution**: Market analysis phase runs 4 agents in parallel

### 9.4 Memory Scalability

- **Paging system**: Letta-style context management prevents unbounded memory growth
- **Automatic summarization**: Long histories compressed before reaching context limits
- **Knowledge graph**: Offloads detailed knowledge from agent context to structured storage

### 9.5 Database Scalability

- **SQLite for development**: Zero-configuration local database
- **PostgreSQL for production**: Full ACID compliance with connection pooling
- **Redis for caching**: High-performance key-value store for market data cache
- **Alembic migrations**: Schema evolution without data loss

### 9.6 Deployment Scaling

- **Docker-first**: All components containerized
- **Docker Compose**: Development and staging environments
- **Kubernetes-ready**: Stateless pods with health checks and readiness probes
- **Environment-based configuration**: No code changes for different deployment targets

---

*© 2025-2026 Quant Nanggroe AI | System Design Reference v0.2.0*
