# Hedge Fund Trading System Architecture — Research Findings

**Sources searched:** Web search (quant finance blogs, GitHub repos, SSRN-indexed papers,
Electronic Trading Hub, KX/kdb+ docs, techinterview.org, sanj.dev benchmarks, catalyst-tech.uk,
QuantHedgeFund OSS, Michael Brenndoerfer's quant architecture guide)

**Key articles consulted:**
- "Quant Trading Systems: Architecture & Infrastructure" (mbrenndoerfer.com, Jan 2026)
- "Engineering High-Sharpe HFT Systems for Modern Hedge Funds" (Medium, Dec 2025)
- "Why Traditional Trading Infrastructure Fails at 3 AM" (Electronic Trading Hub, Feb 2026)
- "Time-Series Databases for Quant" (techinterview.org, Apr 2026)
- "kdb+ Tick Architecture" (margo.com / Dell InfoHub / KX blog)
- "ClickHouse vs TimescaleDB vs InfluxDB: 2026 Benchmarks" (sanj.dev)
- "Crypto Algo Trading Python: Complete Architecture Blueprint" (kalena.ai)
- "Catalyst Event-Driven Trading Architecture" (catalyst-tech.uk)
- "CQRS & Event Sourcing Architecture" (Touch-Fire Trading)

---

## 5 Specific Architectural Recommendations

### 1. Tick Data: kdb+ for HFT / ClickHouse for mid-frequency; TimescaleDB for positions & orders

**What institutional practice says:**
Institutional quant firms overwhelmingly use **kdb+/q** for tick capture at
high-frequency scales — it is the gold standard for in-memory time-series in
trading. The canonical `kdb+/tick` pattern: Feed Handler → Tickerplant (with
disk log) → Real-Time DB (in-memory) → Historical DB (on-disk columnar).
Tickerplant fans data to subscribers (strategy engines, risk monitors, P&L
calculators) and writes an append-only log for crash recovery.

For mid-frequency / crypto shops that don't have kdb+ licensing budgets:
**ClickHouse** dominates for analytics, backtesting, and compliance queries
on tick data. **TimescaleDB** (PostgreSQL extension) is widely used for
position snapshots, order histories, and reference data where SQL joins with
trading metadata matter.

**The hybrid pattern seen in production (sanj.dev 2026):**
- TimescaleDB for real-time tick capture and order management
- InfluxDB for infrastructure monitoring / metrics
- ClickHouse for backtesting, analytics, and compliance reporting
- Some funds run all three — raw ticks in ClickHouse, positions in
  TimescaleDB, system metrics in InfluxDB

→ **Recommendation:** Use **TimescaleDB** for positions, orders, and
reference data. Use **ClickHouse** (or kdb+ if budget + latency demands it
and you have q expertise) for raw tick data and analytics. Never store tick
data in a row-oriented OLTP database at scale.

---

### 2. Event-Driven Message Bus with Kafka for Order Lifecycle + Circuit Breakers

**What institutional practice says:**
Modern hedge fund architectures are **event-driven**, not request/response.
Kafka is the backbone. Each trading domain owns a topic:
- `market-data.raw` — feed handler publishes ticks
- `signals.generated` — strategy engine publishes trade signals
- `orders.lifecycle` — OMS publishes order submitted/filled/cancelled
- `positions.updated` — position keeper publishes delta updates
- `pnl.calculated` — P&L aggregator publishes attribution snapshots

**Electronic Trading Hub (2026):** "Active-active failover — multiple systems
handle execution simultaneously. Load balancing distributes orders across
active systems. A failed system is automatically removed from rotation."

**Circuit breaker pattern** — used at the exchange gateway level, not just
application code. When an exchange's fill latency exceeds N standard
deviations or error rate > threshold, the gateway circuit-breaks and routes
to the secondary exchange. This is implemented with **Resilience4j** (Java)
or **Polly** (.NET) patterns, often paired with Kafka consumer pause/resume.

→ **Recommendation:** Own your Kafka topology. Topics per domain, compacted
topics for position state (event sourcing), log compaction for audit trail.
Implement circuit breakers on **every exchange gateway** — 3-state (Closed →
Open → Half-Open) with configurable failure thresholds and cooldown periods.
Route orders to backup venues transparently when primary circuit is open.

---

### 3. Position Reconciliation via Event Sourcing + CQRS

**What institutional practice says:**
A position is not stored as a mutable row — it's **derived from an event
stream** of fills, corporate actions, and adjustments. This is the CQRS/ES
pattern used by Touch-Fire Trading, Catalyst, and major funds.

**The pattern:**
```
Order Filled → Position Event Store (immutable append-only)
                       ↓
              Projection → Current Position Snapshot (materialized view)
                       ↓
              Risk Check → Position Limits / Concentration
                       ↓
              P&L Attribution → Mark-to-market + FX conversion
```

**Reconciliation flow** (per Michael Brenndoerfer's quant architecture guide):
1. Internal position book (event-sourced, real-time)
2. Broker/custodian statement (T+1 or real-time API pull)
3. Reconciliation engine compares both — flags breaks by:
   - Symbol mismatch
   - Quantity delta > configurable tolerance
   - Price/VWAP deviation for P&L
4. Breaks go to a human-review queue with auto-correct rules for known
   patterns (split/dividend/corporate action)

**Catalyst (energy trading):** "Event-driven architecture ensures that all
position changes are processed accurately and in order. Pricing and delivery
calendars are checked and tested regularly to prevent errors."

→ **Recommendation:** Implement positions as **event-sourced aggregates**
from the fill stream. Do NOT write to a `positions` table directly. Use a
compacted Kafka topic (`positions.snapshot`) as the source of truth.
Materialize read models into TimescaleDB for fast querying. Schedule
reconciliation every trading cycle (EOD minimum, intraday if broker APIs
allow). Auto-flag any break > 0.5% of position notional.

---

### 4. P&L Attribution Pipeline: Three-Layer Calculation

**What institutional practice says:**
P&L is calculated at three distinct layers with different latencies:

| Layer | Latency | Purpose |
|-------|---------|---------|
| **Real-time P&L** | Sub-second | Trader dashboard, risk limits |
| **EOD P&L** | Batch (post-close) | Official fund NAV, investor reporting |
| **T+1 P&L** | Next-day | Attribution (signal vs execution vs financing) |

**The attribution breakdown pattern** (seen across multiple production systems):
```
P&L = Signal P&L       (strategy return vs benchmark)
    + Execution P&L    (slippage vs arrival price)
    + Financing P&L    (carry/roll/funding)
    + FX Translation   (currency conversion)
    + Residual         (fees, commissions, rebates)
```

**Production pipeline** (QuantHedgeFund OSS + kalena.ai blueprint):
```
Market Data → Signal Engine → Order Generation → Execution
                                                    ↓
                                            Fill Events → Position Keeper
                                                           ↓
                                                    P&L Aggregator
                                                    ├── MTM (mark-to-market)
                                                    ├── Realized (fills vs entry)
                                                    ├── Unrealized (current mark)
                                                    └── Attribution (by factor/sector/strategy)
```

→ **Recommendation:** Separate **MTM P&L** (mark-to-market, continuous) from
**realized P&L** (fills only, discrete). Build a three-tier calculation:
(1) in-memory real-time for dashboards, (2) batch EOD for books and records,
(3) T+1 attribution drill-down. Store attribution results in a columnar DB
(ClickHouse) for slice-and-dice queries by strategy, sector, factor exposure.

---

### 5. Multi-Exchange Failover: Active-Active with Deterministic Order Routing

**What institutional practice says:**
The 2026 standard is **active-active** across exchanges/venues, not
active-passive. Electronic Trading Hub: "Active-Active Failover (24/7
Architecture): Multiple systems handle execution simultaneously. Load
balancing distributes orders across active systems. Failed system is
automatically removed from rotation."

**The five-layer stack** (per NSE nanosecond trading architecture):
1. **Market Data Layer** — consolidated feed, seq# gap detection
2. **Execution Layer** — OMS + smart order router (SOR)
3. **Risk Layer** — pre-trade, real-time, post-trade
4. **Position Keeping Layer** — event-sourced
5. **Reporting Layer** — P&L, TCA, compliance

**Failover specifics:**
- **Exchange gateway circuit breaker:** 3-state, per-venue
- **Smart order router (SOR):** Routes orders based on live fill
  probability, latency, and fee tier
- **Warm standby gateways:** Pre-connected to secondary venues, sharing
  fill-level state via Kafka
- **Session recovery:** Persist order state (seq#, client order ID mapping)
  so a restart doesn't lose in-flight orders
- **Multi-data-center:** Active in two regions; Kafka MirrorMaker for
  cross-region order replication; positions have a primary and shadow copy

→ **Recommendation:** Every exchange connection must be backed by a
**standby gateway** on a different network path/kernel. Deploy **active-active**
across at least 2 exchanges for any traded asset. All strategy engines see a
unified liquidity pool — SOR handles venue selection transparently. Use
Kafka compacted topics for **order state recovery** — on restart, replay the
last offset to rebuild in-flight orders. Every order carries a
UUID + idempotency key so fills can't be double-counted after failover.

---

## Summary: Reference Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│                   P&L Attribution                        │
│         (ClickHouse / kdb+ for analytics)                │
├─────────────────────────────────────────────────────────┤
│                 Position Keeper                          │
│         (Event-sourced, TimescaleDB snapshot)            │
├─────────────────────────────────────────────────────────┤
│                     Risk Layer                           │
│   (Pre-trade limits, real-time VaR, circuit breakers)    │
├─────────────────────────────────────────────────────────┤
│           Smart Order Router / Execution                 │
│   (Active-active gateways, Kafka order lifecycle)        │
├─────────────────────────────────────────────────────────┤
│              Strategy Engine                             │
│   (Signal generation, order generation, position sizing) │
├─────────────────────────────────────────────────────────┤
│            Market Data Layer                             │
│   (Feed handlers, tickerplant, seq# gap detection)       │
├─────────────────────────────────────────────────────────┤
│       Tick DB (ClickHouse)│Positions DB (TimescaleDB)   │
└─────────────────────────────────────────────────────────┘
```

**Key technologies referenced by actual funds:**
- **Tick data:** kdb+ (institutional HFT), ClickHouse (mid-freq/analytics)
- **Positions/orders:** TimescaleDB, PostgreSQL
- **Messaging:** Kafka (Redpanda increasingly seen in crypto funds)
- **Circuit breakers:** Resilience4j (JVM), Polly (.NET), custom (Python)
- **Language:** C++/Java for ultra-low latency paths, Python/PySpark for
  research & batch, Go for gateway services
- **Monitoring:** Prometheus + Grafana for metrics, OpenTelemetry for
  distributed tracing across the order lifecycle
