# QNA Integration Architecture — Quant-Grade Hedge Fund Blueprint

## Core Insight: Everything Is Already Interconnected

The codebase has **all the pieces** — 15 strategies, 10 data providers, 12 agents, MultiColony swarm, COT, economic calendar, MTF framework, auto-tuning, regime detection, risk management, execution layer, 3 UI systems. The gap is **not** missing code but **wiring** these pieces into a single pipeline.

## The Unified Data → Analysis → Decision Pipeline

```
                    ┌─────────────────────────────┐
                    │       DATA AGGREGATOR        │
                    │  (runs every cycle, caches)  │
                    └──────────┬──────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Price/Volume    │  │  Fundamental    │  │  Alternative    │
│  • Bybit/OKX     │  │  • EconCalendar │  │  • COT Data     │
│  • CoinGecko     │  │  • Macro Data   │  │  • On-Chain     │
│  • WARP/SSH      │  │  • Sentiment    │  │  • Geopolitical │
└────────┬─────────┘  └────────┬────────┘  └────────┬────────┘
         └─────────────────────┼─────────────────────┘
                               ▼
                    ┌─────────────────────────────┐
                    │     MARKET REGIME ENGINE     │
                    │  • HMM (4 states)           │
                    │  • Ensemble voting           │
                    │  • Volatility clustering     │
                    │  Output: bullish/bearish/    │
                    │          ranging/volatile    │
                    └──────────┬──────────────────┘
                               │
                               ▼
                    ┌─────────────────────────────┐
                    │   ADAPTIVE STRATEGY ENGINE   │
                    │                              │
                    │  Strategy Selector           │
                    │  • regime → optimal strategy │
                    │  • rolling Sharpe tracking   │
                    │  • weight-based allocation   │
                    │                              │
                    │  Multi-Timeframe Aligner     │
                    │  • HTF (D1) trend filter     │
                    │  • MTF (H1) confirmation     │
                    │  • LTF (M5) entry timing     │
                    │                              │
                    │  Runs ALL selected strategies│
                    │  → weighted signal fusion    │
                    └──────────┬──────────────────┘
                               │
                               ▼
               ┌─────────────────────────────┐
               │    DECISION SYNTHESIS        │
               │  • 7 rules (DT001-DT007)    │
               │  • Agent council debate      │
               │  • Confidence aggregation    │
               └──────────┬──────────────────┘
                          │
                          ▼
               ┌─────────────────────────────┐
               │      RISK LAYER              │
               │  • Kill switch (all levels) │
               │  • Trailing stop            │
               │  • Kelly position sizing    │
               │  • Drawdown monitor         │
               └──────────┬──────────────────┘
                          │
                          ▼
               ┌─────────────────────────────┐
               │        EXECUTION             │
               │  • SyncPaperBroker          │
               │  • Exchange clients (8)     │
               │  • Order management         │
               └──────────┬──────────────────┘
                          │
                          ▼
               ┌─────────────────────────────┐
               │   FEEDBACK LOOP              │
               │  • Record PnL per strategy  │
               │  • Update rolling Sharpe    │
               │  • Auto-tune if degrading   │
               │  • Re-run backtest (24h)    │
               └─────────────────────────────┘
```

## Production-Ready Components Checklist

### ✅ Data Layer (10/10)
| Component | Status | Integration |
|-----------|--------|-------------|
| Bybit Provider | ✅ | SSH relay bypass |
| OKX Provider | ✅ | SSH relay bypass |
| CoinGecko Provider | ✅ | Direct + fallback |
| Crypto Provider | ✅ | Chain: direct→WARP→SSH |
| COT Data | ✅ NEW | CFTC weekly |
| Econ Calendar | ✅ NEW | Free API + synthetic |
| WARP Proxy | ✅ | Auto-detect + register |
| SSH Relay | ✅ | 10.210.13.229:8022 |
| Fundamental Factors | ✅ | Screener system |
| Alternative Data | ✅ | On-chain, geopolitical |

### ✅ Strategy Layer (15/15)
| Category | Strategies | Status |
|----------|-----------|--------|
| Momentum | Momentum, Trend | ✅ |
| Mean Reversion | MeanReversion, Pairs, StatArb | ✅ |
| Volatility | VolArb, MarketMaking | ✅ |
| Regime | RegimeBased | ✅ |
| Crypto | CryptoSpecific | ✅ |
| Pattern | SMC, ICT, S/R, SnD, Wyckoff | ✅ NEW |
| Fundamental | COT, Fundamental | ✅ NEW |

### ✅ Analysis Layer (4/4)
| Component | Status |
|-----------|--------|
| Multi-Timeframe (HTF/MTF/LTF) | ✅ NEW |
| Auto Fine-Tuning | ✅ NEW |
| Adaptive Strategy Selector | ✅ NEW |
| HMM Regime Ensemble | ✅ |

### ✅ Decision Layer (2/2)
| Component | Status |
|-----------|--------|
| Decision Synthesis Engine | ✅ |
| Agent Council (12 agents) | ✅ |

### ✅ Risk Layer (5/5)
| Component | Status |
|-----------|--------|
| Kill Switch | ✅ 0.8%/2.5%/10% |
| Trailing Stop | ✅ NEW |
| Kelly Position Sizing | ✅ |
| Drawdown Monitor | ✅ |
| Emotional Lockout | ✅ |

### ✅ Execution Layer (3/3)
| Component | Status |
|-----------|--------|
| Sync Paper Broker | ✅ |
| Exchange Clients (8) | ✅ |
| Order Management | ✅ |

### ⚠️ UI Layer (80%)
| Component | Status |
|-----------|--------|
| Python Plotly Dashboard | ✅ |
| FastAPI Routes (strategies) | ✅ NEW |
| Next.js Dashboard Pages | ✅ (mock data) |
| Strategy Toggles in UI | ⏳ (needs API wiring) |
| Backtest Viz in UI | ⏳ (mock data) |
| COT Panel in UI | ⏳ (new page) |

## The Feedback Loop That Makes It Autonomous

```
┌─────────────────────────────────────────────────────────┐
│                    AUTONOMOUS LOOP                        │
│                                                          │
│  ┌─────────┐   ┌──────────┐   ┌────────┐   ┌─────────┐ │
│  │ Trade   │ → │ Record   │ → │ Update │ → │ Re-tune │ │
│  │ Executes│   │ PnL per  │   │ Rolling│   │ if      │ │
│  │         │   │ Strategy │   │ Sharpe │   │ Sharpe< │ │
│  └─────────┘   └──────────┘   └────────┘   │ 0.5    │ │
│                                            └─────────┘ │
│                                                │        │
│  ┌─────────┐   ┌──────────┐   ┌────────┐      │        │
│  │ Auto-   │ ← │ Re-select│ ← │ Regime │ ←────┘        │
│  │ Execute │   │ Strategy │   │ Change │                │
│  └─────────┘   └──────────┘   └────────┘                │
│                                                          │
│  Every 24h: Re-run backtest with latest data             │
│  Every 100 cycles: Walk-forward validation               │
│  On regime change: Re-select optimal strategies          │
│  On Sharpe < 0.5: Auto-tune parameters                   │
│  On drawdown > 10%: Kill switch → manual review          │
└──────────────────────────────────────────────────────────┘
```

## Remaining Gaps to Close (Priority Order)

### P1 — Wire Dashboard to API (1 session)
- Connect Next.js pages to FastAPI backend
- Remove mock data from all pages
- Add strategy toggle switches
- Add COT data panel

### P2 — Wire Live Engine to AdaptiveStrategyEngine (1 session)
- Replace inline strategy logic in live_engine.py with AdaptiveStrategyEngine
- Connect regime detection → strategy selector → MTF → execution
- Add feedback loop (record PnL per strategy)

### P3 — Agent Integration (1 session)
- Wire AgentCouncil to vote on conflicting signals from different strategies
- Connect MultiColony to provide fundamental/macro analysis
- Set up cron for BH bridge (every 5min)

### P4 — Multi-Asset Backtest (1 session)
- Run full backtest on all 8 coins × 15 strategies × parameter variants
- Deploy best combinations
- Persist to SQLite

### P5 — Production Deployment (1 session)
- systemd/openrc init script
- Environment config (.env) finalization
- API key setup for real exchange trading
- Load testing

## Production Readiness Summary

| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| Strategies | 15 | 15 | ✅ |
| Data Providers | 10 | 10 | ✅ |
| Risk Checks | 5 | 5 | ✅ |
| Execution Paths | 3 | 3 | ✅ |
| UI Pages | 7 | 12 | ⏳ 5 more |
| API Endpoints | 35+ | 50+ | ⏳ Live trading |
| Backtest Coverage | 3 coins | 8 coins | ⏳ 5 more |
| Auto-Tuning | ✅ | ✅ | ✅ |
| Feedback Loop | ⏳ Live PnL | Live tracking | ⏳ Wire to engine |
| Agent Integration | ✅ Code | ✅ Live | ⏳ Wire council |
| System Health | 9.5/10 | 10/10 | ⏳ UI + live wire |
