# Quant-Nanggroe-AI — Workflow Pipeline

> **Hedge-Fund-Grade Quant Platform** — End-to-end pipeline: data acquisition → signal generation → risk filtering → portfolio allocation → execution → monitoring → reporting.

```mermaid
%%{init: {'theme': 'neutral', 'themeVariables': { 'primaryColor': '#1a1a2e', 'lineColor': '#3b82f6'}}}%%
graph TB
    subgraph DATA["01 — DATA ACQUISITION"]
        A1[Market Data Feeds] --> A2[Yahoo Finance / TV MCP]
        A1 --> A3[FRED Economic Data]
        A1 --> A4[SEC EDGAR Filings]
        A1 --> A5[OSINT / Crucix]
        A2 --> A6[Data Normalization Layer]
        A3 --> A6
        A4 --> A6
        A5 --> A6
    end

    subgraph SIGNAL["02 — SIGNAL GENERATION"]
        B1[Strategy Engine] --> B2[YAML Strategy Parser]
        B2 --> B3[Signal Generators]
        B3 --> B4[Mean Reversion]
        B3 --> B5[Momentum]
        B3 --> B6[Trend Following]
        B3 --> B7[Pairs Trading]
        B3 --> B8[Statistical Arbitrage]
        B3 --> B9[Volatility Arbitrage]
        B3 --> B10[Market Making]
        B3 --> B11[Regime-Based]
        B3 --> B12[Crypto-Specific]
        B4 --> B13[Aggregated Signal Bus]
        B5 --> B13
        B6 --> B13
        B7 --> B13
        B8 --> B13
        B9 --> B13
        B10 --> B13
        B11 --> B13
        B12 --> B13
    end

    subgraph RISK["03 — RISK FILTER"]
        C1[Kelly Position Sizing] --> C4[Risk Manager]
        C2[Diversification Score] --> C4
        C3[Correlation Matrix] --> C4
        C4 --> C5{Pass Risk Gate?}
        C5 -->|Yes| D1
        C5 -->|No| C6[Kill Switch / Alert]
    end

    subgraph PORTFOLIO["04 — PORTFOLIO ALLOCATION"]
        D1[Portfolio Optimizer] --> D2[Mean-Variance Opt]
        D1 --> D3[Risk Parity]
        D2 --> D4[Allocation Engine]
        D3 --> D4
        D4 --> E1
    end

    subgraph EXECUTION["05 — EXECUTION"]
        E1[Order Manager] --> E2{Multi-Broker Router}
        E2 -->|Exness MT5| E3[MT5 Bridge]
        E2 -->|Other Brokers| E4[CCXT / REST]
        E2 -->|Paper Trading| E5[Simulated Execution]
        E3 --> E6[Fill Confirmation]
        E4 --> E6
        E5 --> E6
        E6 --> F1
    end

    subgraph MONITOR["06 — MONITORING & RISK"]
        F1[Position Tracker] --> F2[P&L Monitoring]
        F1 --> F3[Exposure Limits]
        F1 --> F4[Stress Detection]
        F2 --> F5{Breach Threshold?}
        F3 --> F5
        F4 --> F5
        F5 -->|Yes| F6[Auto Hedge / Liquidate]
        F5 -->|No| F7[Normal Operations]
        F6 --> F8[Incident Log]
    end

    subgraph REPORT["07 — REPORTING & ANALYTICS"]
        G1[Performance Metrics] --> G2[Win Rate / RR / Profit Factor]
        G1 --> G3[Sharpe / Sortino / Calmar]
        G1 --> G4[Drawdown Analysis]
        G1 --> G5[Alpha / Beta Attribution]
        G2 --> G6[Dashboard UI]
        G3 --> G6
        G4 --> G6
        G5 --> G6
        G6 --> H1
    end

    subgraph FEEDBACK["08 — FEEDBACK LOOP"]
        H1[RL Engine] --> H2[Policy Update]
        H2 --> H3[Strategy Tuning]
        H3 --> B2
        H1 --> H4[Kelly Calibration]
        H4 --> C1
    end

    A6 --> B13
    B13 --> C4
    C4 --> G1
```

## Pipeline Stages

### 01 — Data Acquisition
| Component | Role | Source |
|-----------|------|--------|
| Market Data Feeds | Real-time & historical price data | Yahoo Finance, TradingView MCP |
| FRED Data | Macroeconomic indicators | FRED API (via `/api/fred`) |
| SEC EDGAR | Corporate filings | SEC EDGAR MCP |
| OSINT / Crucix | Alternative data / public intelligence | Crucix agent |
| Data Normalization | Unifies formats, timestamps, symbols | `quant_nanggroe/engine/data/` |

### 02 — Signal Generation
| Strategy | Type | Key Parameters | RR Range | Best For |
|----------|------|---------------|----------|----------|
| MeanReversion | Mean Reversion | lookback=20, std=2 | 1:2–1:3 | Range-bound markets |
| Momentum | Trend Following | lookback=50, strength=1.5 | 1:1.5–1:2 | Trending markets |
| TrendFollow | Breakout | ema_short=20, ema_long=50 | 1:2–1:4 | Strong trends |
| PairsTrading | Statistical Arb | window=60, z_entry=2 | 1:1.5–1:2.5 | Mean-reverting pairs |
| StatisticalArbitrage | Cointegration | half_life=20, z_entry=2.5 | 1:2–1:3 | Cointegrated assets |
| VolatilityArbitrage | Vol Arb | lookback=20, vix_threshold=25 | 1:1.5–1:3 | High volatility |
| MarketMaking | Liquidity | spread=0.001, inventory=100 | 1:1–1:1.5 | Liquid markets |
| RegimeBased | Adaptive | volatility_regime, trend_regime | Varies | All markets |
| CryptoSpecific | Crypto | funding_rate, open_interest | 1:2–1:5 | Crypto markets |

### 03 — Risk Filter (Gate)
- **Kelly Position Sizing**: Fractional Kelly (FULL=0.4, HALF=0.2, QUARTER=0.1, ADAPTIVE=0.08)
- **Diversification Score**: 0.0–1.0 based on portfolio correlation matrix
- **Kill Switch**: Auto-activates at 5% daily loss; 30-minute deactivation cooldown
- **Stress Detection**: VaR, max drawdown, sector exposure limits

### 04 — Portfolio Allocation
- Mean-Variance Optimization (Markowitz)
- Risk Parity Allocation
- Target: max Sharpe with constraint-based diversification

### 05 — Execution
- **Multi-Broker Router**: Routes orders to Exness MT5, CCXT-compatible brokers, or paper trading
- **Order Types**: MARKET, LIMIT, STOP, OCO, TRAILING_STOP
- **Execution Modes**: LIVE, PAPER, BACKTEST

### 06 — Monitoring
- Real-time P&L tracking per position and aggregate
- Exposure limits: max 10% per position, 40% per sector
- Auto-hedge on breach; liquidation on critical threshold

### 07 — Reporting
- Performance dashboard with all metrics
- Win rate, RR, profit factor, Sharpe/Sortino/Calmar
- Drawdown analysis, alpha/beta attribution

### 08 — Feedback Loop (RL)
- Reinforcement learning engine tunes strategy parameters
- Kelly fraction calibrated based on historical outcomes
- Strategy weights adjusted via multi-armed bandit

## Execution Modes

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  BACKTEST    │ →  │  PAPER       │ →  │  LIVE        │
│  (historical)│    │  (simulated) │    │  (real money)│
└──────────────┘    └──────────────┘    └──────────────┘
     ↑                    ↑                    ↑
     Validation           Confidence           Production
```

## Data Flow Summary

```
Raw Data → Normalized → Signal → Risk Filter → Allocation → Execution → Monitor → Report → Tune
```

## Related Documents
- [ARCHITECTURE.md](./ARCHITECTURE.md) — System architecture
- [STRATEGY_CATALOG.md](./STRATEGY_CATALOG.md) — Complete strategy reference
- [README.md](./README.md) — Quick start & overview
- [docs/RESEARCH.md](./docs/RESEARCH.md) — Research sources
- [docs/RUNBOOK.md](./docs/RUNBOOK.md) — Operations runbook

---

*Last updated: 2026-07-12 | Quant-Nanggroe-AI v0.9.2*
