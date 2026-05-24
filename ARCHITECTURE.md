# Architecture: Quant Nanggroe AI

**Version 15.2.0 | Multi-Agent Decision Intelligence Operating System**

This document provides a comprehensive technical reference for the architecture of Quant Nanggroe AI. It covers the system's layered execution model, data flow pathways, service interactions, component relationships, and the deterministic reasoning framework that governs all decision-making processes.

> Part of the [HermesQuantOS](https://github.com/mulkymalikuldhrs/HermesQuantOS) Unified Project.

---

## 1. Design Philosophy

### Deterministic Reasoning over Subjective AI

Quant Nanggroe AI is built on a fundamentally different premise from conventional AI-assisted trading tools. Rather than treating Large Language Models as advisors that produce qualitative analysis, the system treats them as **Logical Reasoning Engines** operating under strict contracts. These contracts enforce three absolute rules:

1. **No Subjective Opinions** — Agents are forbidden from producing "vibes-based" analysis, sentiment narratives, or qualitative assessments. Every output must be grounded in observable, numerical data.
2. **Mandatory Data Grounding** — All reasoning must originate from Layer 0 data. An agent cannot reason about market conditions without first receiving contextual data from the MarketService. This eliminates hallucination at the architectural level.
3. **Pressure-Based Output** — Agents never produce direct trade signals (BUY/SELL). Instead, they emit normalized pressure values (0.0–1.0) that flow into the Pressure Normalization Engine. Trade decisions are the exclusive domain of the Decision Synthesis Engine.

### Why Determinism Matters

In institutional quantitative trading, every decision must be traceable to its inputs, reproducible under the same conditions, and defensible under audit. Probabilistic AI outputs that vary between runs are unacceptable. The deterministic stack ensures that given identical market data and the same agent configurations, the system will produce identical outputs — a property that is essential for backtesting integrity, compliance, and risk management.

---

## 2. The 5-Layer Execution Stack

The core of Quant Nanggroe AI is a **5-Layer Deterministic Execution Stack**, where each layer acts as a strict filter. Data flows downward through the stack, and each layer either passes data forward or blocks it entirely. No layer can be bypassed, and no agent can override the constraints imposed by layers above it.

```
┌─────────────────────────────────────────────────┐
│  Layer 0: Contextual Neural Grounding           │
│  (Data Foundation — MarketService, AutoSwitch)   │
├─────────────────────────────────────────────────┤
│  Layer 1: Market Regime Engine                   │
│  (Gatekeeper — MarketStateEngine)                │
├─────────────────────────────────────────────────┤
│  Layer 2: Multi-Agent Sensors                    │
│  (Eyes — QuantScanner, SMCAgent, NewsSentinel,   │
│   FlowAgent)                                     │
├─────────────────────────────────────────────────┤
│  Layer 3: Pressure Normalization Engine          │
│  (Compiler — PressureNormalizationEngine)         │
├─────────────────────────────────────────────────┤
│  Layer 4: Decision Synthesis Engine              │
│  (Judge — DecisionSynthesisEngine,               │
│   EntryRiskEngine, RiskManagement)               │
└─────────────────────────────────────────────────┘
```

### Layer 0: Contextual Neural Grounding (Data Foundation)

The bedrock of the entire system. This layer is responsible for harvesting, normalizing, and distributing real-time market data from multiple providers.

**Data Providers:**
- **Binance** — Cryptocurrency L1/L2 data (order book, trades, candles)
- **CoinCap** — Alternative cryptocurrency market data
- **AlphaVantage** — Stock and forex technical data, fundamental indicators
- **Polygon** — US equities and options market data
- **Finnhub** — Real-time forex, crypto, and news data

**Key Service: AutoSwitch Engine**

The `AutoSwitch` service (`services/autoswitch.ts`) provides automatic provider failover with the following capabilities:
- **Exponential backoff retry logic** — When a provider fails, retry intervals increase exponentially (1s, 2s, 4s, 8s, ...) up to a maximum threshold
- **Health-based provider prioritization** — Providers are ranked by their recent success rate and average response latency
- **Cooldown mechanisms** — Providers that fail consecutively enter a cooldown period during which they are not queried, reducing wasted API calls
- **Real-time health reporting** — The system continuously monitors and reports the health status of each data provider

**Key Service: MarketService**

The `MarketService` (`services/market.ts`) orchestrates all data access, providing a unified API that abstracts away the complexity of multiple data providers. It exposes:
- Price tickers and 24-hour statistics
- OHLCV candle data across multiple timeframes
- Real-time news aggregation
- Technical indicator computation via the MathEngine
- Market metadata including trust scores, latency estimates, and update frequencies

**Data Enrichment:**

Every piece of data entering the system is tagged with metadata:
| Field | Type | Description |
|---|---|---|
| `source` | string | Data provider identifier |
| `trustScore` | 0.0–1.0 | Confidence in data accuracy based on provider reliability |
| `latencyEstimate` | ms | Estimated round-trip time to data source |
| `updateFrequency` | string | Expected data refresh rate (e.g., "1s", "1m", "5m") |
| `domainType` | enum | Data category: CRYPTO, EQUITY, FOREX, MACRO, NEWS |

---

### Layer 1: Market Regime Engine (The Gatekeeper)

The `MarketStateEngine` (`services/market_state_engine.ts`) sits above all agents and serves as the system's gatekeeper. It determines the global market condition, which constrains all downstream processing.

**Market States:**

| State | Condition | Effect on System |
|---|---|---|
| `TRENDING` | ADX > 25, directional momentum | Normal operation; trend-following strategies active |
| `RANGE` | ADX < 20, price bounded | Range-trading strategies prioritized; reduced position sizing |
| `MEAN_REVERT` | RSI at extremes, price deviation from mean | Mean-reversion strategies activated |
| `RISK_OFF` | Elevated volatility, deteriorating breadth | Reduced position sizing; defensive positioning |
| `PANIC` | Rapid price decline, extreme volatility | All agents forced to idle; existing positions managed defensively |
| `NO_TRADE` | Insufficient liquidity or data quality | No new entries; system enters monitoring mode |

**Detection Methods:**
- **ADX Trend Strength** — Average Directional Index measures the strength of a trend regardless of direction
- **RSI Extremes** — Relative Strength Index identifies overbought (>70) and oversold (<30) conditions
- **Rapid Price Change Detection** — Monitors for price moves exceeding N standard deviations within a short timeframe

**Hard Constraint:** If the regime is `NO_TRADE` or `PANIC`, all downstream agents are forced into idle mode. This constraint cannot be overridden by any agent, any LLM reasoning, or any configuration change. It is an architectural guarantee of capital protection.

---

### Layer 2: Multi-Agent Sensors (The Eyes)

Four specialized agents operate in parallel as numerical sensors. They do not produce subjective analysis — they produce structured, typed output that feeds into the Pressure Normalization Engine.

#### QuantScanner (`services/quant_scanner.ts`)

The quantitative momentum scanner. It analyzes price and volume data to produce:

| Output | Type | Range | Description |
|---|---|---|---|
| `momentum` | number | -1.0 to 1.0 | Directional momentum strength |
| `adxStrength` | number | 0.0 to 100.0 | ADX trend strength reading |
| `volatilityExpansion` | number | 0.0 to 1.0 | Current volatility relative to historical norm |
| `structureState` | enum | BULL/BEAR/NEUTRAL | Market structure classification |

#### SMCAgent (`services/smc_agent.ts`)

The Smart Money Concepts sensor. It detects institutional footprints in price action:

| Output | Type | Description |
|---|---|---|
| `liquiditySweep` | boolean | Whether a liquidity pool has been swept |
| `displacementStrength` | number | Strength of momentum displacement (0.0–1.0) |
| `poiValidity` | enum | VALID/INVALID/EXPIRED — Point of Interest validity |
| `orderBlockType` | enum | BULL_OB/BEAR_OB/NONE — Detected order block type |
| `marketStructure` | enum | BOS/CHoCH/RANGE — Break of Structure or Change of Character |

#### NewsSentinel (`services/news_sentinel.ts`)

The macroeconomic and news event classifier. It processes news items and economic events:

| Output | Type | Description |
|---|---|---|
| `eventClassification` | enum | MACRO/SCHEDULED/SHOCK/NOISE — Event category |
| `directionalBias` | number | -1.0 to 1.0 — Estimated directional impact |
| `uncertaintyScore` | number | 0.0 to 1.0 — Uncertainty in directional assessment |
| `timeDecay` | function | Logarithmic decay function for event impact over time |
| `affectedAssets` | string[] | List of assets likely affected by the event |

The logarithmic time decay model ensures that recent events carry exponentially more weight than older events, while still preserving a non-zero influence for significant historical events.

#### FlowAgent (`services/flow_agent.ts`)

The institutional flow tracking sensor. It monitors large-order activity and positioning:

| Output | Type | Description |
|---|---|---|
| `whaleFlowDirection` | enum | ACCUMULATING/DISTRIBUTING/NEUTRAL — Large trader behavior |
| `cotBias` | enum | LONG/SHORT/NEUTRAL — Commitment of Traders positioning bias |
| `flowImbalance` | number | -1.0 to 1.0 — Buy/sell flow imbalance ratio |
| `institutionalActivity` | number | 0.0 to 1.0 — Estimated institutional participation level |

---

### Layer 3: Pressure Normalization Engine (The Compiler)

The `PressureNormalizationEngine` (`services/pressure_normalization_engine.ts`) is the central aggregation point for all sensor outputs. It compiles heterogeneous sensor data into a unified pressure field.

**Input:** Structured outputs from all four sensor agents
**Output:** Normalized pressure vector

| Output | Type | Range | Description |
|---|---|---|---|
| `buyPressure` | number | 0.0–1.0 | Aggregated buying pressure |
| `sellPressure` | number | 0.0–1.0 | Aggregated selling pressure |
| `volatilityRisk` | enum | LOW/MEDIUM/HIGH/EXTREME | Volatility classification |
| `liquidityCondition` | enum | THIN/NORMAL/DEEP | Market liquidity assessment |
| `confidence` | number | 0.0–1.0 | Overall confidence in the pressure reading |

**Weight Allocation (Blueprint Final Specification):**

Each sensor contributes a weighted portion to the pressure calculation. The weights are derived from backtested performance and are calibrated to maximize the predictive power of the aggregate signal:

| Sensor | Buy Pressure Weight | Sell Pressure Weight | Domain |
|---|---|---|---|
| QuantScanner | 25% | 25% | Technical momentum |
| SMCAgent | 30% | 30% | Institutional structure |
| NewsSentinel | 20% | 20% | Macro/sentiment |
| FlowAgent | 25% | 25% | Institutional flow |

The Pressure Normalization Engine eliminates the problem of conflicting agent signals by reducing everything to a single, normalized pressure field. An agent producing a strong buy signal does not directly cause a trade — it contributes to the `buyPressure` value, which must then be evaluated by Layer 4.

---

### Layer 4: Decision Synthesis Engine (The Judge)

The `DecisionSynthesisEngine` (`services/decision_synthesis_engine.ts`) is the final authority on all trading decisions. It uses a **Decision Table** — a machine-readable set of rules — to evaluate whether the current state meets the criteria for entry.

**Decision Table Logic:**

The Decision Table evaluates the following conditions simultaneously:

1. **Pressure Confluence** — Is there a meaningful gap between `buyPressure` and `sellPressure`? A minimum threshold (typically 0.15) must be exceeded to indicate genuine directional conviction.
2. **Regime Compatibility** — Does the pressure direction align with the current market regime? Trending buy pressure in a `RANGE` market is discounted.
3. **Volatility Clearance** — Is the volatility risk level acceptable for entry? `EXTREME` volatility blocks all entries regardless of pressure.
4. **Confidence Threshold** — Is the overall confidence score above the minimum threshold (typically 0.60)?

If all four conditions are satisfied, the system proceeds to entry geometry calculation.

**EntryRiskEngine (`services/entry_risk_engine.ts`)**

Once confluence is achieved, the EntryRiskEngine calculates precise entry parameters:

| Parameter | Calculation Method |
|---|---|
| **Entry Price** | Current market price at the time of decision |
| **Stop Loss** | Structural invalidation level — the price point that would invalidate the trade thesis (NOT a percentage-based stop) |
| **TP1** | Nearest significant liquidity level in the direction of the trade |
| **TP2** | Volatility extension (1x ATR-based distance from entry) |
| **TP3** | Volatility extension x2 (2x ATR-based distance from entry) |

**RiskManagement (`services/risk_management.ts`)**

Risk clearance is independently verified by the RiskManagement module, which enforces the Trading Constitution (see Section 3). The RiskManagement module operates as an independent check — it receives the proposed entry parameters and can veto any trade that violates constitutional rules, regardless of what the Decision Synthesis Engine has determined.

---

## 3. Risk Guardian Constitution

The Risk Guardian is a hard-coded, independent risk enforcement layer that is immune to AI reasoning. No agent, no matter how sophisticated its analysis, can override the constitutional rules.

### Constitutional Rules

| Rule | Threshold | Action on Violation |
|---|---|---|
| **Maximum Daily Drawdown** | 4% of account equity | Automatic kill-switch: all positions closed, system enters cooldown for the remainder of the day |
| **Maximum Position Correlation** | 0.70 between any two active positions | New position blocked; warning issued to audit trail |
| **Maximum Exposure Per Asset** | Configurable (default: 10% of portfolio) | Position size reduced to comply |
| **Structural Stop Loss** | Required on every position | No position may be opened without a structural stop loss; percentage-based stops are rejected |
| **Minimum Risk-Reward Ratio** | 1:1.5 (configurable) | Trade rejected if potential reward does not justify risk |

### Correlation Monitor (`services/correlation_monitor.ts`)

The Correlation Monitor continuously tracks the pairwise correlation between all active positions using a rolling window of returns. If the correlation between any two positions exceeds 0.70, the system blocks new entries in correlated assets and issues a warning to the audit trail. This prevents concentration risk that could amplify drawdowns during correlated market moves.

---

## 4. Darwinian Strategy Lifecycle

The `StrategyLifecycleManager` (`services/strategy_lifecycle.ts`) implements a natural selection mechanism for trading strategies.

### Strategy States

| State | Condition | Behavior |
|---|---|---|
| `ACTIVE` | Positive expectancy, drawdown < 10% | Fully operational; allocates capital |
| `HIBERNATING` | Drawdown > 15% OR expectancy approaching zero | Suspended from live trading; continues monitoring |
| `KILLED` | Negative expectancy over >= 20 trades | Permanently deactivated; resources reallocated |
| `INCUBATING` | New strategy under evaluation | Paper trading only; no live capital allocation |

### Evolution Mechanism

1. Every strategy is tracked from its first trade
2. After a minimum of 20 trades, statistical significance is assessed
3. If the **expectancy** (average profit per trade) is negative, the strategy is marked `KILLED`
4. If the drawdown exceeds 15%, the strategy is placed in `HIBERNATING` status
5. Resources (capital allocation, agent attention) shift to `ACTIVE` strategies
6. The `EvolutionMonitor` (`services/evolution_monitor.ts`) tracks the historical performance of all strategies, including killed ones, to identify patterns that may inform future strategy development

---

## 5. Execution Reality Engine

The `BacktestEngine` (`services/backtest_engine.ts`) implements execution reality simulation to ensure that backtested results reflect real-world trading conditions.

### Simulation Parameters

| Parameter | Simulation | Rationale |
|---|---|---|
| **Dynamic Spread** | Volatility-adjusted spread widening | Spread widens during high volatility, just as in live markets |
| **Slippage** | Random slippage within volatility-adjusted bounds | Market orders do not always fill at the displayed price |
| **Partial Fill Probability** | 2–15% depending on volatility regime | Large orders may not fill completely in thin markets |
| **Order Rejection** | Simulated with probability based on market conditions | Exchange rejections occur during extreme volatility or connectivity issues |
| **Latency** | 100–500ms random delay applied to all orders | Decision-to-execution latency in live trading is never zero |

### Impact on Performance Metrics

The Execution Reality Engine typically reduces backtested returns by 15–30% compared to idealized backtesting. This is by design — it prevents the common pitfall of over-optimistic backtests that fail in production. Strategies that remain profitable under execution reality conditions have a significantly higher probability of success in live trading.

---

## 6. Audit Trail System

The `AuditLogger` (`services/audit_logger.ts`) provides comprehensive event logging across all layers of the execution stack.

### Audit Layers

| Layer | Events Logged |
|---|---|
| **Market** | Data provider status, price updates, regime changes, data quality alerts |
| **Sensor** | Agent outputs, sensor readings, anomaly detection, confidence scores |
| **Pressure** | Pressure calculations, weight adjustments, normalization events |
| **Decision** | Decision table evaluations, confluence checks, entry/exit decisions |
| **Risk** | Constitutional rule checks, violations, position sizing, correlation alerts |
| **Execution** | Order placement, fill confirmation, slippage, rejection events |

### Log Structure

Each audit entry contains:
- **Timestamp** — High-precision UTC timestamp
- **Layer** — Which execution layer generated the event
- **Severity** — INFO, WARNING, ERROR, CRITICAL
- **EventType** — Categorized event type for filtering
- **Payload** — Structured data specific to the event type
- **Source** — The service or agent that generated the event

The audit trail is designed to meet institutional compliance requirements, enabling full reconstruction of any trading decision from raw data through to execution.

---

## 7. Hybrid Storage Architecture

The `StorageManager` (`services/storage_manager.ts`) uses an **Adapter Pattern** to manage data across multiple storage backends.

### Storage Backends

| Backend | Purpose | Characteristics |
|---|---|---|
| **IndexedDB** | Primary storage for knowledge bases, market history, research items | High capacity (hundreds of MB), structured queries, persistent across sessions |
| **LocalStorage** | UI preferences, session state, theme configuration | Fast synchronous access, limited capacity (~5MB), key-value pairs |
| **BrowserFS** | Virtual file system for backup/restore operations | Full file system API, supports directories and file operations |
| **Cloud (Ready)** | Prepared for Supabase/PostgreSQL integration | Schema defined, adapter interface ready, not yet connected |

### Data Flow

```
Application Code
       │
       ▼
StorageManager (Orchestrator)
       │
       ├──► StorageAdapter (Interface)
       │        │
       │        ├──► IndexedDB Adapter
       │        ├──► LocalStorage Adapter
       │        └──► FileSystem Adapter
       │
       └──► BackupService (Export/Import)
                │
                └──► .json file generation
```

The `StorageAdapter` (`services/storage_adapter.ts`) defines a common interface that all storage backends implement, allowing the StorageManager to transparently route data to the appropriate backend without the application code needing to know the details.

---

## 8. Multi-LLM Routing

The `LLMRouter` (`services/llm_router.ts`) manages communication with large language models, routing requests to the appropriate model based on the task type and agent requirements.

### Current Integration

- **Google Gemini** (`services/gemini.ts`) — Primary LLM for agent swarm intelligence, research analysis, and conversational AI

### Routing Strategy

The LLM Router selects models based on:
1. **Task Type** — Different tasks (analysis, synthesis, research) may benefit from different model capabilities
2. **Cost Optimization** — Simpler tasks are routed to lighter models when available
3. **Rate Limit Management** — Requests are throttled and queued to stay within API rate limits
4. **Failover** — If the primary model is unavailable, the router can fall back to alternative providers

---

## 9. Frontend Architecture

The frontend is built as a desktop-OS-inspired interface using React 19 and TypeScript, designed to be a complete research and decision-support workstation.

### Component Hierarchy

```
App.tsx (Root)
 ├── Taskbar (Dock)
 │    ├── App Icons
 │    └── System Status Indicators
 │
 ├── OmniBar (Spotlight Search)
 │    ├── Command Parser
 │    └── AI-Powered Search
 │
 ├── ControlCenter (System Panel)
 │    ├── Security Matrix
 │    ├── Risk Guardian Dashboard
 │    ├── Theme Toggle
 │    └── Configuration
 │
 └── WindowFrame (Container) × N
      ├── TradingTerminalWindow
      ├── MarketWindow
      ├── PortfolioWindow
      ├── ResearchAgentWindow
      ├── KnowledgeBaseWindow
      ├── BrowserWindow
      ├── NexusWindow
      ├── SwarmConfigModal
      ├── SystemArchitecture
      └── AgentHud
```

### Key Design Principles

- **Draggable Windows** — All content panels are draggable, resizable, and support z-index management through the `WindowFrame` component
- **Desktop OS Metaphor** — The interface replicates the desktop OS experience with a dock, spotlight search, and window management, reducing the learning curve for users familiar with desktop applications
- **Real-Time Updates** — All market data, agent states, and system metrics update in real-time without requiring page refreshes
- **Theme System** — Every component supports both light and dark themes, with the theme toggle accessible from the ControlCenter

---

## 10. Data Flow Summary

The complete data flow from market data ingestion to trade execution:

```
[Market Data Providers]
        │
        ▼
[AutoSwitch Engine] ──► Provider Health Monitoring
        │
        ▼
[MarketService] ──► Data Normalization & Enrichment
        │
        ▼
[MarketStateEngine] ──► Regime Detection (Layer 1)
        │
        ├── If NO_TRADE/PANIC ──► System Idle
        │
        ▼ (Regime Compatible)
[Sensor Agents] (Parallel Execution)
   │     │     │     │
   │     │     │     └── FlowAgent ──► Institutional Flow Data
   │     │     └──────── NewsSentinel ──► News/Macro Classification
   │     └────────────── SMCAgent ──► Smart Money Structure Data
   └──────────────────── QuantScanner ──► Technical Momentum Data
        │
        ▼
[PressureNormalizationEngine] ──► BUY/SELL Pressure Vectors
        │
        ▼
[DecisionSynthesisEngine] ──► Decision Table Evaluation
        │
        ├── If No Confluence ──► No Action
        │
        ▼ (Confluence Achieved)
[EntryRiskEngine] ──► Entry Geometry Calculation
        │
        ▼
[RiskManagement] ──► Constitutional Rule Verification
        │
        ├── If Violation ──► Trade Vetoed
        │
        ▼ (Risk Cleared)
[Execution Parameters] ──► Entry Price, Stop Loss, TP1, TP2, TP3
        │
        ▼
[AuditLogger] ──► Full Decision Trail Recorded
```

---

## 11. Service Dependency Graph

The following diagram illustrates the primary dependencies between services:

```
MarketService
    ├── AutoSwitch
    ├── MathEngine
    └── Data Providers (Binance, CoinCap, AlphaVantage, Polygon, Finnhub)

MarketStateEngine
    └── MarketService

QuantScanner ─── MarketService + MathEngine
SMCAgent ─────── MarketService
NewsSentinel ─── MarketService
FlowAgent ────── MarketService

PressureNormalizationEngine
    ├── QuantScanner
    ├── SMCAgent
    ├── NewsSentinel
    └── FlowAgent

DecisionSynthesisEngine
    ├── PressureNormalizationEngine
    └── MarketStateEngine

EntryRiskEngine
    ├── DecisionSynthesisEngine
    └── MathEngine

RiskManagement
    ├── EntryRiskEngine
    ├── CorrelationMonitor
    └── StrategyLifecycle

AuditLogger
    └── (All services emit events to AuditLogger)

ResearchAgent
    ├── MarketService
    └── KnowledgeBase

StorageManager
    ├── StorageAdapter
    ├── FileSystem
    └── Drive
```

---

## 12. Related Projects

| Project | Description | Link |
|---|---|---|
| **HermesQuantOS** | Unified Quantitative Intelligence Ecosystem — the parent project integrating Quant Nanggroe AI with backend services, databases, and deployment infrastructure | [https://github.com/mulkymalikuldhrs/HermesQuantOS](https://github.com/mulkymalikuldhrs/HermesQuantOS) |

---

© 2025-2026 Quant Nanggroe AI | Technical Architecture Reference v15.2.0
