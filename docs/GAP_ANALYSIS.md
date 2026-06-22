# QNA Gap Analysis — Hedge Fund Quant Head Perspective

## 8-Dimension Assessment

### 1. Alpha Generation — 0/100

**Current:** Zero validated alpha. 3 strategies × 4 coins × 5-fold walk-forward = 180 combos all fail. MACD also fails. Original "Sharpe 1.57" = in-sample curve-fitting on 92 candles.

**Gap:** 100 points. A quant fund without alpha = a car without an engine.

**What's needed:**
- Shift from daily to intraday data (15m/1h/4h) for crypto's 24/7 nature
- Feature engineering: order flow, market microstructure, volatility surface
- ML-based strategies: gradient boosting, transformers, reinforcement learning
- Alternative data: on-chain analytics, exchange flows, whale tracking
- Multi-asset factors: carry, term structure, cross-asset momentum

### 2. Data Pipeline — 40/100

**Current:** CoinGecko primary, Bybit/OKX via DNS bypass, 366 candles per coin. HTTP-based with retry + circuit breaker.

**Gap:** No real-time streaming, no level-2 order book, no trade-and-quote (TAQ) data, no alternative data.

**What's needed:**
- WebSocket streaming for real-time prices (Bybit/OKX WebSocket)
- Level-2 order book with full depth
- TAQ data for microstructure analysis
- On-chain data (Glassnode, Nansen, Dune)
- Exchange WebSocket for WebSocket-native market data (`websockets` library, pip install)
- Proper data warehouse (TimescaleDB or QuestDB for time series)

### 3. Risk Management — 60/100

**Current:** 9-checkpoint constitutional risk gate, Kelly sizing, ATR stops, kill switch, drawdown monitor. All deterministic, hardcoded limits.

**Gap:** No dynamic risk budgeting, no portfolio-level optimization, no correlation regime detection, no tail-risk hedging.

**What's needed:**
- Risk parity / volatility targeting portfolio construction
- Dynamic risk budgeting (not just per-trade caps)
- Correlation regime detection (all correlations → 1 in crisis)
- Tail-risk hedging (VIX, put options, tail ETFs)
- Stress testing with full revaluation
- Scenario analysis (2008, COVID, 2022 crash) on live portfolio
- CVaR optimization for position sizing (beyond Kelly)

### 4. Execution — 30/100

**Current:** PaperExchangeBroker (902 lines, slippage + commission). Alpaca paper (1032 lines, untested). Zero real trades executed.

**Gap:** No real exchange connection, no smart order routing, no execution algorithms.

**What's needed:**
- Broker API keys registered and tested (Alpaca, Bybit)
- Smart Order Routing (SOR) across venues
- TWAP / VWAP / Implementation Shortfall algos
- Latency measurement and optimization
- Fill quality tracking and venue selection
- Partial fill handling and order lifecycle management

### 5. Portfolio Management — 10/100

**Current:** Kelly sizing per position, constitutional cap (max 10%/position). No portfolio optimization.

**Gap:** No mean-variance optimization, no factor exposure targeting, no rebalancing engine.

**What's needed:**
- Mean-Variance Optimization (Markowitz)
- Black-Litterman model for views-based allocation
- Factor exposure targeting (momentum, value, carry, vol)
- Rebalancing engine with transaction cost modeling
- Multi-period optimization (not just single-period)
- CVaR / Risk Parity as alternative target functions
- Margin and leverage optimization

### 6. Infrastructure — 50/100

**Current:** Docker multi-stage build, docker-compose (3 services), .env.template, fastapi. Zero CI/CD, no monitoring.

**Gap:** No CI/CD, no monitoring, no alerting, no disaster recovery.

**What's needed:**
- CI/CD pipeline (GitHub Actions: lint → test → build → deploy)
- Monitoring: Grafana dashboards for PnL, risk, execution quality, system health
- Alerting: PagerDuty / Telegram alerts on risk breaches, execution failures
- Database backup and disaster recovery plan
- Infrastructure as Code (Terraform / Ansible)
- Staging environment for testing before production deployment

### 7. Testing — 20/100

**Current:** Partial unit tests, walk-forward backtest framework exists but alpha fails. No integration tests, no regression tests.

**Gap:** No systematic testing regime.

**What's needed:**
- Unit tests for all strategy modules
- Integration tests for end-to-end pipeline
- Regression test suite with known-good outputs
- CI gate: tests must pass before merge
- Coverage target: minimum 70%
- Historical replay testing (feed historical data through live engine)
- Monte Carlo simulation of strategy performance

### 8. Monitoring — 45/100

**Current:** Telegram heartbeat every 10 cycles, error alerts. SQLite persistence of all signals and cycles.

**Gap:** No real-time dashboard, no performance analytics, no A/B testing framework.

**What's needed:**
- Real-time PnL dashboard (Grafana + ClickHouse/QuestDB)
- Performance analytics: Sharpe, Sortino, Calmar, Max DD, Win Rate, Profit Factor
- Strategy-level PnL attribution
- Factor contribution analysis
- Execution quality analytics
- A/B testing framework for strategy variants
- Anomaly detection on PnL, execution, data quality

## Overall Score: 32/100

**Verdict:** Solid research prototype with excellent architecture, zero production track record.

## Priority Fixes Ranked by Impact

| Rank | Fix | Dimension | Effort | Impact | Why |
|------|-----|-----------|--------|--------|-----|
| P0 | **Find alpha on intraday data** | Alpha | 2-3 weeks | 100/100 | Without alpha, nothing else matters. Move from daily to 1h/15m data. |
| P1 | **Register exchange keys + execute 1 real paper trade** | Execution | 1 day | 30/100 | QNA has never traded. Break the zero barrier. |
| P2 | **Fix pydantic v1/v2 incompatibility** | Infrastructure | 2 hours | 20/100 | Blocks all pydantic-based imports across modules. #1 code blocker. |
| P3 | **Wire WebSocket data streaming** | Data | 3-5 days | 30/100 | Real-time data is table stakes. HTTP polling is not viable for production. |
| P4 | **CI/CD pipeline (GitHub Actions)** | Infrastructure | 1-2 days | 20/100 | No testing regime = no confidence in changes. |
| P5 | **Portfolio optimization engine** | Portfolio | 1-2 weeks | 30/100 | Kelly sizing alone is not portfolio management. |
| P6 | **Grafana + monitoring stack** | Monitoring | 2-3 days | 20/100 | Can't improve what you can't measure. |
| P7 | **Smart order routing + TWAP/VWAP** | Execution | 1-2 weeks | 20/100 | Execution quality directly impacts PnL. |
| P8 | **On-chain alternative data** | Data | 1-2 weeks | 20/100 | Crypto-specific edge that most quant funds lack. |
| P9 | **Stress testing + tail-risk hedging** | Risk | 1 week | 15/100 | Important but premature until alpha exists. |

## Recommendation

**Short-term (next 30 days):**
1. Abandon daily data entirely — crypto 24/7 markets need intraday
2. Get on-chain data: Glassnode free tier, Dune API, or blockchain node
3. Wire Bybit WebSocket for real-time 1h/15m data
4. Execute 1 real paper trade on Alpaca or Bybit testnet
5. Fix pydantic v1/v2 — the #1 codebase blocker

**Medium-term (30-90 days):**
1. Build ML-based strategy on intraday data (gradient boosting / LSTM / transformer)
2. CI/CD pipeline with test coverage gates
3. Portfolio optimization engine (Black-Litterman or Risk Parity)
4. Grafana monitoring with real-time PnL tracking

**QNA is not a hedge fund. It's a quant research platform. That's fine. Stop pretending otherwise and build the research infrastructure properly.**
