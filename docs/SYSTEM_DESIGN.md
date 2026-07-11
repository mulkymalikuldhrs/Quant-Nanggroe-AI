# System Design: Quant Nanggroe AI

**Version 15.3.0 | Multi-Agent Decision Intelligence Operating System**

This document provides the complete system design specification for Quant Nanggroe AI. It covers the LangGraph state machine architecture, dual-bus messaging, data pipeline topology, security model, and the full pre-trade evaluation flow.

---

## 1. Dynamic Event-Driven Multi-Agent State Graph

### 1.1 LangGraph Architecture Overview

The core trading decision pipeline is implemented as a **directed acyclic graph (DAG)** using LangGraph's `StateGraph`. The graph enforces a strict topological ordering of agent nodes with conditional routing at decision gates.

```
                        ┌──────────────┐
                        │  RESEARCHER  │  (Entry Point)
                        │  Node        │
                        └──────┬───────┘
                               │
                    ┌──────────▼──────────┐
                    │ Regime Gate         │
                    │ should_continue_    │
                    │ after_regime()      │
                    └──┬──────────────┬───┘
                       │              │
              NO_TRADE/│              │ Regime OK
              PANIC/   │              │
              RISK_OFF │              │
                       ▼              ▼
                 ┌─────────┐   ┌──────────────┐
                 │   END   │   │  ANALYST     │
                 │(NO_TRADE)│   │  Node        │
                 └─────────┘   └──────┬───────┘
                                      │
                               ┌──────▼───────┐
                               │  STRATEGIST  │
                               │  Node        │
                               └──────┬───────┘
                                      │
                               ┌──────▼───────┐
                               │ RISK MANAGER │
                               │ 9-Checkpoint │
                               │ VETO System  │
                               └──────┬───────┘
                                      │
                          ┌───────────▼────────────┐
                          │ Risk Gate              │
                          │ should_continue_       │
                          │ after_risk()           │
                          └──┬─────────────────┬───┘
                             │                 │
                    VETOED   │                 │ CLEAR
                             ▼                 ▼
                       ┌─────────┐   ┌──────────────┐
                       │   END   │   │   TRADER     │
                       │(VETOED) │   │   Node       │
                       └─────────┘   └──────┬───────┘
                                            │
                                     ┌──────▼───────┐
                                     │  PORTFOLIO   │
                                     │  MANAGER     │
                                     │  Final Gate  │
                                     └──────┬───────┘
                                            │
                                     ┌──────▼───────┐
                                     │     END      │
                                     │  (COMPLETE)  │
                                     └──────────────┘
```

### 1.2 Agent State Schema

All agent nodes communicate through a shared `AgentState` Pydantic model. This is the single source of truth that flows through the entire graph.

```python
class AgentState(BaseModel):
    # Input
    symbol: str = ""
    timeframe: str = "1d"
    query: str = ""

    # Market Data (Layer 0)
    market_data: list[dict[str, Any]] = []
    candles: list[dict[str, Any]] = []

    # Market State (Layer 1)
    market_state: MarketState = MarketState()
    regime: MarketRegime = MarketRegime.UNKNOWN
    volatility: VolatilityLevel = VolatilityLevel.NORMAL
    liquidity: LiquidityLevel = LiquidityLevel.NORMAL

    # Pressure (Layer 3)
    pressure: PressureState = PressureState()
    buy_pressure: float = 0.0
    sell_pressure: float = 0.0
    confidence: float = 0.0

    # Research (Researcher output)
    research_summary: str = ""
    news_items: list[dict[str, Any]] = []
    sentiment_score: float = 0.0

    # Analysis (Analyst output)
    technical_analysis: dict[str, Any] = {}

    # Strategy (Strategist output)
    strategy_signal: str = ""      # BUY / SELL / HOLD
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: list[float] = []
    position_size: float = 0.0
    decision_action: DecisionAction = DecisionAction.NO_TRADE
    risk_clearance: RiskClearance = RiskClearance.BLOCKED

    # Risk (Risk Manager output)
    risk_verdict: str = "VETOED"
    risk_checkpoints: dict[str, Any] = {}

    # Execution (Trader output)
    execution_status: str = ""
    order_id: str = ""
    execution_price: float = 0.0
    slippage: float = 0.0

    # Portfolio (Portfolio Manager output)
    portfolio_decision: str = ""   # APPROVE / REJECT

    # Metadata
    agent_trace: list[dict[str, Any]] = []
    errors: list[str] = []
```

### 1.3 Node Specifications

| Node | Role | Input | Output | Veto Authority |
|---|---|---|---|---|
| Researcher | Data harvesting | symbol, timeframe | market_data, sentiment_score, news_items | None |
| Analyst | Technical analysis + regime detection | market_data | regime, technical_analysis, volatility | None (but regime gate blocks) |
| Strategist | Signal generation + pressure compilation | technical_analysis, regime | strategy_signal, entry_price, stop_loss, take_profit | None |
| Risk Manager | 9-checkpoint validation | strategy_signal, entry_price, stop_loss | risk_verdict, risk_clearance | **FULL VETO** |
| Trader | Order execution | risk_clearance, entry parameters | execution_status, order_id, slippage | None (blocked if not CLEAR) |
| Portfolio Manager | Portfolio-level final gate | execution_status, risk_clearance | portfolio_decision | **FINAL REJECT** |

### 1.4 Conditional Routing

Two conditional edges govern the graph:

```python
def should_continue_after_regime(state: AgentState) -> str:
    """If NO_TRADE/PANIC/RISK_OFF regime, skip to end."""
    if state.regime in (MarketRegime.NO_TRADE, MarketRegime.PANIC, MarketRegime.RISK_OFF):
        return "end"
    return "analyst"

def should_continue_after_risk(state: AgentState) -> str:
    """If risk VETOED, skip to end."""
    if state.risk_clearance == RiskClearance.CLEAR:
        return "trader"
    return "end"
```

### 1.5 State Machine Diagram

```
                    ┌─────────────────────────────────────────────┐
                    │          TRADING STATE MACHINE               │
                    └─────────────────────────────────────────────┘

    ┌──────────┐    symbol+tf    ┌──────────────┐   regime_ok   ┌──────────────┐
    │  IDLE    │───────────────►│  RESEARCHING │──────────────►│  ANALYZING   │
    └──────────┘                └──────┬───────┘               └──────┬───────┘
         ▲                             │                              │
         │                             │ regime_block                 │
         │                             ▼                              ▼
         │                      ┌──────────────┐              ┌──────────────┐
         │                      │  NO_TRADE    │              │  STRATEGIZING│
         │                      │  (terminal)  │              └──────┬───────┘
         │                      └──────────────┘                     │
         │                                                           ▼
         │                                                    ┌──────────────┐
         │                                                    │ RISK_CHECK   │
         │                                                    └──┬───────┬───┘
         │                                              vetoed │       │ clear
         │                                                      ▼       ▼
         │                                               ┌────────┐ ┌──────────────┐
         │                                               │VETOED  │ │  EXECUTING    │
         │                                               │(term.) │ └──────┬───────┘
         │                                               └────────┘        │
         │                                                                 ▼
         │                                                          ┌──────────────┐
         │                                                          │  PORTFOLIO   │
         │                                                          │  GATE        │
         │                                                          └──┬───────┬───┘
         │                                                    reject │       │ approve
         │                                                           ▼       ▼
         │                                                     ┌────────┐ ┌──────────┐
         └───────────────────────────────────────────────────── │REJECT  │ │ COMPLETE │
                                                                  └────────┘ └──────────┘
```

---

## 2. System Configuration Framework

### 2.1 Pydantic Settings Hierarchy

Configuration is managed through a layered Pydantic Settings system with environment variable injection.

```
Settings (Master)
 ├── DatabaseSettings     (env_prefix: DB_)
 ├── RedisSettings        (env_prefix: REDIS_)
 ├── LLMSettings          (env_prefix: LLM_)
 ├── DataSourceSettings   (env_prefix: DATA_)
 └── FeatureFlags         (env_prefix: FEATURE_)
```

### 2.2 Constitutional Risk Limits

These constants are **hardcoded** in `config.py` and cannot be overridden by environment variables:

```python
MAX_RISK_PER_TRADE: float = 0.005       # 0.5% max risk per trade
MAX_DAILY_LOSS: float = 0.01            # 1.0% max daily loss
MAX_WEEKLY_LOSS: float = 0.03           # 3.0% max weekly loss
MIN_RISK_REWARD: float = 2.0            # Minimum 1:2 R:R ratio
MAX_CORRELATED_POSITIONS: int = 3        # Max correlated positions
```

### 2.3 YAML Configuration Files

The system loads configuration from YAML files for agent definitions, strategy parameters, and risk thresholds:

```yaml
# config/agents.yaml
agents:
  researcher:
    model: gpt-4o
    temperature: 0.0
    max_tokens: 2048
    tools: [market_data, sentiment]
  analyst:
    model: gpt-4o
    temperature: 0.0
    tools: [technical_analysis]
  risk_manager:
    model: none  # Deterministic — no LLM
    type: constitutional
  strategist:
    model: gpt-4o
    temperature: 0.0
    tools: [technical_analysis, pressure]

# config/risk.yaml
risk:
  daily_drawdown_limit: 0.04
  max_position_correlation: 0.70
  max_exposure_per_asset: 0.10
  kill_switch: true
  structural_stop_required: true

# config/exchanges.yaml
exchanges:
  binance:
    type: crypto
    class: ccxt.binance
    sandbox: true
  alpaca:
    type: equity
    class: alpaca-trade-api
    paper: true
  polymarket:
    type: prediction
    class: PolymarketBroker
    chain_id: 137
```

### 2.4 Environment Variable Resolution

```
.env file ──► Settings (Pydantic)
                  │
                  ├── APP_ENV (development | staging | production | test)
                  ├── DATABASE_URL
                  ├── REDIS_URL
                  ├── LLM__OPENAI_API_KEY
                  ├── LLM__DEFAULT_MODEL
                  ├── DATA__POLYGON_API_KEY
                  ├── DATA__BINANCE_API_KEY
                  └── FEATURE__ENABLE_LIVE_TRADING
```

---

## 3. Data Pipeline Architecture

### 3.1 Storage Topology

```
┌────────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                                  │
├────────────┬──────────────────┬──────────────────┬─────────────────┤
│ PostgreSQL │   TimescaleDB    │     Redis        │    QuestDB      │
│ (16-alpine)│  (extension)     │   (7-alpine)     │  (latest)       │
├────────────┼──────────────────┼──────────────────┼─────────────────┤
│ Agent state│ OHLCV tick data  │ Session cache    │ High-freq       │
│ User prefs │ Trade history    │ Pub/Sub channels │ time-series     │
│ Audit logs │ Factor values    │ Rate limiting    │ Order book L2   │
│ Risk state │ Walk-forward     │ Feature cache    │ Trade tape      │
│ Strategy   │ results          │ LLM response     │                 │
│ lifecycle  │                  │ cache            │                 │
├────────────┼──────────────────┼──────────────────┼─────────────────┤
│ Port: 5432 │ Port: 5432       │ Port: 6379      │ Port: 9000      │
│            │                  │                  │ Port: 8812 (PG) │
│            │                  │                  │ Port: 9009 (ILP)│
└────────────┴──────────────────┴──────────────────┴─────────────────┘
```

### 3.2 PostgreSQL + TimescaleDB Schema

```sql
-- Hypertable for OHLCV data (TimescaleDB)
CREATE TABLE ohlcv (
    time        TIMESTAMPTZ NOT NULL,
    symbol      TEXT NOT NULL,
    timeframe   TEXT NOT NULL,
    open        DOUBLE PRECISION,
    high        DOUBLE PRECISION,
    low         DOUBLE PRECISION,
    close       DOUBLE PRECISION,
    volume      DOUBLE PRECISION,
    source      TEXT DEFAULT 'unknown',
    trust_score DOUBLE PRECISION DEFAULT 0.5
);
SELECT create_hypertable('ohlcv', 'time');

-- Audit trail
CREATE TABLE audit_events (
    id          BIGSERIAL PRIMARY KEY,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    layer       TEXT NOT NULL,  -- market|sensor|pressure|decision|risk|execution
    severity    TEXT NOT NULL,  -- INFO|WARNING|ERROR|CRITICAL
    event_type  TEXT NOT NULL,
    payload     JSONB,
    source      TEXT
);

-- Strategy lifecycle tracking
CREATE TABLE strategies (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'INCUBATING',
    expectancy  DOUBLE PRECISION DEFAULT 0,
    max_dd      DOUBLE PRECISION DEFAULT 0,
    sharpe      DOUBLE PRECISION DEFAULT 0,
    win_rate    DOUBLE PRECISION DEFAULT 0,
    trade_count INTEGER DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.3 Redis Usage

| Key Pattern | Type | TTL | Purpose |
|---|---|---|---|
| `cache:ohlcv:{symbol}:{tf}` | Hash | 300s | OHLCV data cache |
| `cache:price:{symbol}` | String | 60s | Current price cache |
| `session:{id}` | Hash | 3600s | Agent session state |
| `ratelimit:{provider}` | Counter | 60s | API rate limit tracking |
| `pubsub:execution` | Pub/Sub | — | Execution event bus |
| `pubsub:agent` | Pub/Sub | — | Agent reasoning events |
| `risk:daily_pnl` | String | 86400s | Daily PnL tracking |

### 3.4 Data Flow: Market → Decision

```
[External APIs]
  Binance ──┐
  CoinCap ──┤     ┌──────────────┐     ┌──────────────┐
  Polygon ──┼────►│  AutoSwitch  │────►│ MarketService│
  AlphaVan ──┤     │  (failover)  │     │ (normalize)  │
  Finnhub ──┘     └──────────────┘     └──────┬───────┘
                                               │
                                    ┌──────────▼───────────┐
                                    │    PostgreSQL /       │
                                    │    TimescaleDB        │
                                    │  (persistent store)   │
                                    └──────────┬───────────┘
                                               │
                                    ┌──────────▼───────────┐
                                    │    Redis Cache        │
                                    │  (hot data + pub/sub) │
                                    └──────────┬───────────┘
                                               │
                                    ┌──────────▼───────────┐
                                    │  MarketStateEngine    │
                                    │  (regime detection)   │
                                    └──────────┬───────────┘
                                               │
                              ┌────────────────┼────────────────┐
                              │                │                │
                    ┌─────────▼──┐   ┌─────────▼──┐   ┌───────▼────┐
                    │QuantScanner│   │  SMCAgent   │   │NewsSentinel│  ...
                    └─────────┬──┘   └─────────┬──┘   └───────┬────┘
                              │                │                │
                              └────────────────┼────────────────┘
                                               │
                                    ┌──────────▼───────────┐
                                    │ PressureNormalization │
                                    │ Engine                │
                                    └──────────┬───────────┘
                                               │
                                    ┌──────────▼───────────┐
                                    │ DecisionSynthesis     │
                                    │ Engine                │
                                    └──────────┬───────────┘
                                               │
                                    ┌──────────▼───────────┐
                                    │ Risk Management       │
                                    │ (Constitutional)      │
                                    └──────────┬───────────┘
                                               │
                                    ┌──────────▼───────────┐
                                    │ Execution Broker      │
                                    └──────────────────────┘
```

---

## 4. Pre-Trade Evaluation and Execution Sequence Flow

### 4.1 Complete Decision Sequence

```
Step 1: DATA HARVEST (Researcher Node)
  ├── MarketDataTool.get_ohlcv(symbol, timeframe)
  ├── MarketDataTool.get_current_price(symbol)
  ├── SentimentTool.analyze(symbol)
  └── Output: market_data, sentiment_score, news_items

Step 2: REGIME DETECTION (Analyst Node)
  ├── TechnicalAnalysisTool.analyze(symbol, timeframe)
  ├── MarketStateEngine.detect_regime(...)
  │   ├── ADX trend strength assessment
  │   ├── RSI extremes detection
  │   ├── Price change velocity check
  │   └── EMA trend confirmation
  └── Output: regime, volatility, liquidity, technical_analysis

Step 3: SIGNAL GENERATION (Strategist Node)
  ├── PressureNormalizationEngine.compile_pressure(pressure_input)
  │   ├── QuantScanner weight: 25%
  │   ├── SMCAgent weight: 30%
  │   ├── NewsSentinel weight: 20%
  │   └── FlowAgent weight: 25%
  ├── DecisionSynthesisEngine.evaluate(regime, buy_pressure, sell_pressure, ...)
  │   ├── Rule DT001: Strong bullish in safe regime
  │   ├── Rule DT002: Strong bearish in safe regime
  │   ├── Rule DT003: Moderate bullish trending
  │   ├── Rule DT004: Moderate bearish trending
  │   ├── Rule DT005: Dangerous regime block (impossible threshold)
  │   ├── Rule DT006: Weak bullish watch
  │   └── Rule DT007: Weak bearish watch
  └── Output: strategy_signal, entry_price, stop_loss, take_profit

Step 4: RISK VALIDATION (Risk Manager Node)
  ├── ConstitutionalRiskGuard.check_trade(...)
  │   ├── Checkpoint 1: Risk per trade ≤ 0.5%
  │   ├── Checkpoint 2: Daily loss < 1.0%
  │   ├── Checkpoint 3: Weekly loss < 3.0%
  │   ├── Checkpoint 4: R:R ratio ≥ 1:2
  │   ├── Checkpoint 5: Stop loss exists and valid
  │   ├── Checkpoint 6: Entry price > 0
  │   ├── Checkpoint 7: Direction is BUY/SELL/LONG/SHORT
  │   ├── Checkpoint 8: Not overtrading (≤ 5/day)
  │   └── Checkpoint 9: Correlated positions ≤ 3
  └── Output: risk_verdict (APPROVED/VETOED), risk_clearance

Step 5: ORDER EXECUTION (Trader Node)
  ├── ExecutionTool.execute_order(...)
  │   ├── Route to appropriate broker (Binance/Alpaca/Polymarket/Paper)
  │   ├── Submit LIMIT or MARKET order
  │   └── Capture order_id, execution_price, slippage
  └── Output: execution_status, order_id, slippage

Step 6: PORTFOLIO GATE (Portfolio Manager Node)
  ├── Verify risk clearance is CLEAR
  ├── Verify execution_status is FILLED or PENDING
  ├── Verify decision_action is not NO_TRADE
  └── Output: portfolio_decision (APPROVE/REJECT)
```

### 4.2 Entry Parameter Calculation

When a signal is generated, entry parameters are calculated using ATR-based geometry:

```
For BUY (LONG):
  entry_price  = current_price
  stop_loss    = current_price - (2.0 × ATR₁₄)
  take_profit₁ = current_price + (2.0 × ATR₁₄)   ← 1:2 R:R
  take_profit₂ = current_price + (4.0 × ATR₁₄)   ← 1:4 R:R

For SELL (SHORT):
  entry_price  = current_price
  stop_loss    = current_price + (2.0 × ATR₁₄)
  take_profit₁ = current_price - (2.0 × ATR₁₄)   ← 1:2 R:R
  take_profit₂ = current_price - (4.0 × ATR₁₄)   ← 1:4 R:R
```

---

## 5. Dual-Bus Design

### 5.1 Architecture

The system uses a dual-bus architecture to separate latency-critical execution from agent reasoning:

```
┌─────────────────────────────────────────────────────────────────┐
│                    DUAL-BUS ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  EXECUTION BUS (Low-Latency)                             │  │
│  │  ──────────────────────────────────────────────────────  │  │
│  │  Transport: Redis Pub/Sub                                │  │
│  │  Channel:  pubsub:execution                              │  │
│  │  Latency:  < 1ms (local) / < 10ms (cross-container)     │  │
│  │  Payload:  JSON (order_id, symbol, side, price, qty)    │  │
│  │                                                          │  │
│  │  Producers: Trader Node, Kill Switch                     │  │
│  │  Consumers: Execution Brokers (Binance, Alpaca, PM)      │  │
│  │                                                          │  │
│  │  Message Types:                                          │  │
│  │    ORDER_NEW      → New order submission                 │  │
│  │    ORDER_CANCEL   → Cancel existing order                │  │
│  │    ORDER_FILL     → Fill confirmation                    │  │
│  │    KILL_SWITCH    → Emergency close all positions        │  │
│  │    POSITION_SYNC  → Position reconciliation              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  AGENT REASONING BUS (High-Throughput)                   │  │
│  │  ──────────────────────────────────────────────────────  │  │
│  │  Transport: Redis Pub/Sub + PostgreSQL                   │  │
│  │  Channel:  pubsub:agent                                  │  │
│  │  Latency:  100ms-5s (acceptable for reasoning)           │  │
│  │  Payload:  JSON (agent_id, state_delta, trace)           │  │
│  │                                                          │  │
│  │  Producers: All Agent Nodes                              │  │
│  │  Consumers: Audit Logger, UI Dashboard, Memory System    │  │
│  │                                                          │  │
│  │  Message Types:                                          │  │
│  │    AGENT_START     → Agent node started                  │  │
│  │    AGENT_COMPLETE  → Agent node finished                 │  │
│  │    AGENT_ERROR     → Agent node errored                  │  │
│  │    STATE_DELTA     → State mutation                      │  │
│  │    REGIME_CHANGE   → Market regime transition            │  │
│  │    PRESSURE_UPDATE → Pressure vector updated             │  │
│  │    RISK_VETO       → Risk manager vetoed a trade         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Bus Isolation Guarantees

| Property | Execution Bus | Agent Reasoning Bus |
|---|---|---|
| Priority | P0 (highest) | P2 |
| Max latency | 10ms | 5s |
| Persistence | Redis only (volatile) | Redis + PostgreSQL (durable) |
| Retry policy | 3 retries, exponential backoff | Fire-and-forget + audit log |
| Message ordering | FIFO per symbol | Best-effort |
| Backpressure | Drop oldest if queue > 1000 | Buffer up to 10000 |

### 5.3 Cross-Bus Communication

The execution bus and agent reasoning bus communicate through a **bridge** in the Trader node:

```
Agent Reasoning Bus          Bridge              Execution Bus
──────────────────    ┌──────────────┐    ──────────────────
risk_clearance:CLEAR ─►│Trader Node   │──► ORDER_NEW
execution_status     ◄──│(validates)   │◄─── ORDER_FILL
```

The bridge ensures that agent reasoning (which may be slow) never blocks order execution. If the reasoning bus is congested, execution continues based on the last known state.

---

## 6. Security Architecture

### 6.1 Docker Sandboxing

Each execution broker and the agent runtime run in isolated Docker containers:

```yaml
# docker-compose.yml (security-relevant settings)
services:
  api:
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '0.5'
          memory: 512M

  postgres:
    security_opt:
      - no-new-privileges:true
    volumes:
      - postgres_data:/var/lib/postgresql/data  # No bind mount

  redis:
    command: redis-server --requirepass ${REDIS_PASSWORD} --maxmemory 512mb
```

### 6.2 MCP Tool Registry

Agent tools are registered through a controlled registry pattern. No agent can execute arbitrary code:

```python
# Tool registry — each tool is a controlled interface
REGISTERED_TOOLS = {
    "market_data": MarketDataTool,     # Read-only market data access
    "sentiment": SentimentTool,         # Read-only sentiment analysis
    "technical": TechnicalAnalysisTool, # Read-only technical analysis
    "execution": ExecutionTool,         # Write: order submission (broker-routed)
    "backtest": BacktestTool,           # Read-only backtesting engine
}
```

Tool security properties:

| Tool | Access Level | Write Capability | Network Access |
|---|---|---|---|
| MarketDataTool | Read-only | None | External APIs (Binance, Polygon, etc.) |
| SentimentTool | Read-only | None | News APIs |
| TechnicalAnalysisTool | Read-only | None | Internal (no network) |
| ExecutionTool | Write (broker-routed) | Orders only | Broker APIs only |
| BacktestTool | Read-only | None | Internal (no network) |

### 6.3 API Key Security

- API keys are **never** embedded in client-side bundles
- All keys loaded from environment variables via Pydantic Settings
- The `vite.config.ts` was patched (v15.3.1) to remove `GEMINI_API_KEY` injection
- `.env` files are excluded from version control
- Keys are validated at startup — missing keys produce explicit errors, not silent failures

### 6.4 Network Security

```
┌─────────────────────────────────────────┐
│           qna-network (bridge)          │
│                                         │
│  ┌───────┐  ┌───────┐  ┌────────────┐  │
│  │  API  │  │  DB   │  │   Redis    │  │
│  │:8000  │  │:5432  │  │  :6379     │  │
│  └───┬───┘  └───┬───┘  └─────┬──────┘  │
│      │          │             │         │
│      └──────────┴─────────────┘         │
│       (internal communication only)     │
│                                         │
│  Only API port 8000 exposed to host     │
└─────────────────────────────────────────┘
```

- Only the API server port (8000) is exposed to the host
- PostgreSQL, Redis, and QuestDB ports are bound to localhost only for development
- In production, all internal ports are restricted to the Docker network

---

## 7. Execution Broker Integration

### 7.1 Broker Routing

```python
# Execution is routed based on symbol type
BROKER_ROUTING = {
    "crypto":  "ccxt.binance",          # Binance via CCXT
    "equity":  "alpaca-trade-api",      # Alpaca for US equities
    "prediction": "PolymarketBroker",   # Polymarket CLOB
    "paper":   "PaperBroker",           # Paper trading (default)
}
```

### 7.2 Prediction Market Integration (Polymarket)

The `PolymarketBroker` provides:

- **Market Discovery**: Search prediction markets via Gamma API
- **Order Execution**: Buy/sell YES/NO shares via CLOB API
- **EIP-712 Signing**: Orders signed with Ethereum private key on Polygon (chain_id: 137)
- **Position Tracking**: Real-time position and PnL queries
- **Price Validation**: Share prices constrained to [0.01, 0.99]

### 7.3 Kill Switch Architecture

```
Risk Management Layer
  │
  ├── Daily PnL check: abs(daily_loss) >= 1.0%  → KILL_SWITCH
  ├── Weekly PnL check: abs(weekly_loss) >= 3.0% → KILL_SWITCH
  │
  └── Kill Switch Activation:
       ├── 1. Publish KILL_SWITCH message on Execution Bus
       ├── 2. All brokers receive and close open positions
       ├── 3. System enters COOLDOWN state
       └── 4. No new trades until manual reset or next day
```

---

## 8. Memory Architecture

### 8.1 Three-Layer Memory System

```
┌───────────────────────────────────────────────────────────┐
│                    MEMORY ARCHITECTURE                     │
├───────────────────────────────────────────────────────────┤
│                                                           │
│  Layer 1: Vector Memory (TF-IDF)                         │
│  ──────────────────────────────────                       │
│  Implementation: VectorMemory (in-memory, numpy)          │
│  Capacity: ~100,000 documents                             │
│  Use: Research note retrieval, strategy matching          │
│  Embedding: TF-IDF with cosine similarity                 │
│  Eviction: FIFO when max_documents exceeded               │
│                                                           │
│  Layer 2: Event-Sourced Audit Trail                       │
│  ──────────────────────────────────                       │
│  Implementation: PostgreSQL audit_events table             │
│  Use: Complete decision reconstruction, compliance        │
│  Retention: Indefinite (append-only)                      │
│  Layers: Market → Sensor → Pressure → Decision → Risk     │
│                                                           │
│  Layer 3: Conversation Condenser                          │
│  ──────────────────────────────────                       │
│  Implementation: Redis session + summarization            │
│  Use: Agent context window management                     │
│  Strategy: Keep last N messages + compressed summary      │
│  TTL: Session-based (3600s)                               │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### 8.2 Vector Memory Search Flow

```
Query Text
  │
  ├── SimpleTokenizer.tokenize()   → Lowercase, strip punctuation, remove stop words
  ├── SimpleTokenizer.simple_stem() → Suffix-stripping heuristic
  │
  ├── TFIDFEmbedder.embed_query()
  │   ├── Term frequency: count / total_terms
  │   ├── IDF: log((N+1) / (df+1)) + 1
  │   └── L2 normalize
  │
  ├── VectorMemory._compute_similarities()
  │   └── Cosine similarity: dot(q,d) / (||q|| × ||d||)
  │
  └── Return top-k results sorted by score
```

---

## 9. Frontend Architecture (Next.js Web Terminal)

The frontend is a desktop-OS-inspired interface built with React 19 + TypeScript:

```
App.tsx (Root)
 ├── Taskbar (Dock)              → Application launcher + system status
 ├── OmniBar (Spotlight Search)  → Command parser + AI-powered search
 ├── ControlCenter              → Security matrix, risk dashboard, config
 └── WindowFrame × N            → Draggable, resizable window containers
      ├── TradingTerminalWindow → Order entry, positions, PnL
      ├── MarketWindow         → OHLCV charts, order book
      ├── PortfolioWindow      → Portfolio summary, allocation
      ├── ResearchAgentWindow  → AI research chat interface
      ├── KnowledgeBaseWindow  → Vector search, document management
      ├── BrowserWindow        → Embedded web browser
      ├── NexusWindow          → Inter-agent communication view
      ├── SwarmConfigModal     → Agent configuration
      ├── SystemArchitecture   → System topology visualization
      └── AgentHud             → Agent state dashboard
```

---

## 10. Service Dependency Graph

```
MarketService
    ├── AutoSwitch (provider failover)
    ├── MathEngine (indicator computation)
    └── Data Providers: Binance, CoinCap, AlphaVantage, Polygon, Finnhub

MarketStateEngine ─── MarketService

LangGraph Trading Graph
    ├── Researcher ─── MarketDataTool + SentimentTool
    ├── Analyst ────── TechnicalAnalysisTool + MarketStateEngine
    ├── Strategist ─── PressureNormalizationEngine + DecisionSynthesisEngine
    ├── RiskManager ── ConstitutionalRiskGuard (9-checkpoint)
    ├── Trader ─────── ExecutionTool (broker routing)
    └── PortfolioManager ─── Final gate validation

PressureNormalizationEngine
    └── Weighted sensors: QuantScanner(25%) + SMCAgent(30%) + NewsSentinel(20%) + FlowAgent(25%)

DecisionSynthesisEngine
    ├── PressureNormalizationEngine
    └── Decision Table (7 rules: DT001-DT007)

ConstitutionalRiskGuard
    └── Hardcoded limits from config.py (no override)

AuditLogger
    └── Receives events from ALL services (6 layers)

VectorMemory
    └── TFIDFEmbedder + SimpleTokenizer + numpy similarity

StorageManager (Frontend)
    ├── IndexedDB (knowledge bases, market history)
    ├── LocalStorage (UI preferences)
    ├── BrowserFS (backup/restore)
    └── Cloud (Supabase/PostgreSQL — prepared)
```

---

© 2025-2026 Quant Nanggroe AI | System Design Document v15.3.0
