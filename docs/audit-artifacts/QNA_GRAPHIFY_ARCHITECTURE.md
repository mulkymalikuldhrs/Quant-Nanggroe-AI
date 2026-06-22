# QNA Architecture — Adaptive Integration Pipeline

```mermaid
graph TB
    subgraph Data["Data Layer"]
        EP[EnginePriceProvider]
        DM[DataManager]
        COT[COTProvider]
        EC[EconomicCalendar]
        SR[SSH Relay]
        WP[WARP Proxy]
        CG[CoinGecko]
        PL[Polygon.io]
    end

    subgraph Strategy["15 Strategies"]
        MR[MeanReversion]
        MO[Momentum]
        PT[PairsTrading]
        VA[VolatilityArbitrage]
        SA[StatisticalArbitrage]
        MM[MarketMaking]
        RB[RegimeBased]
        CS[CryptoSpecific]
        SMC[SMC]
        ICT[ICT]
        SR_S[Support/Resistance]
        SND[Supply/Demand]
        WY[Wyckoff]
        COT_S[COT]
        FD[Fundamental]
    end

    subgraph Pipeline["Adaptive Pipeline"]
        REG[Regime Detection]
        SEL[Strategy Selector]
        MTF[Multi-Timeframe Alignment]
        SG[Signal Generator]
    end

    subgraph Risk["Risk Layer"]
        KS[Kill Switch]
        DD[Drawdown Monitor]
        PS[Position Sizer]
        RG[RiskGate]
        TS[Trailing Stop]
    end

    subgraph Execution["Execution Layer"]
        PE[Production Execution]
        PB[PaperBroker]
        OM[Order Manager]
        EX[Exchange Clients]
    end

    subgraph Storage["Persistence"]
        DB[(SQLite)]
        PH[Portfolio History]
        BT[Backtest Results]
        SS[Strategy Stats]
    end

    subgraph API["API / UI"]
        FA[FastAPI Routes]
        ND[Next.js Dashboard]
        PY[Plotly Dashboard]
        TG[Telegram Notifier]
    end

    subgraph Engine["Live Engine"]
        LE[LiveEngine]
        AC[AutoAware]
        NP[Numpy Strategies]
        HL[Heartbeat Logger]
    end

    Data --> Pipeline
    COT --> Pipeline
    EC --> Pipeline
    Pipeline --> SG
    SG --> RG
    RG --> LE
    LE --> PE
    LE --> Engine
    PE --> PB
    PE --> EX
    EX <--> SR
    EX <--> WP
    LE <--> DB
    DB --> API
    Engine --> TG
```

## Component Flow

1. **Data Providers** → fetch live prices (SSH relay bypasses Telkomsel block)
2. **Adaptive Pipeline** → regime detection → strategy selection (15 strategies) → MTF alignment → signals
3. **Risk Gate** → kill switch / drawdown / position sizing pre-trade checks
4. **Live Engine** → execute signals via PaperBroker or exchange clients
5. **Persistence** → SQLite stores candles, positions, trades, portfolio history
6. **API/UI** → 5 FastAPI endpoints + Plotly dashboard + Telegram heartbeat

## Key Files

| Layer | File | Lines |
|-------|------|-------|
| Live Engine | `quant_nanggroe/live_engine.py` | 1199 |
| Adaptive Pipeline | `quant_nanggroe/engine/live/adaptive_integration.py` | 348 |
| Strategy Registry | `quant_nanggroe/engine/strategy/strategies/__init__.py` | 269 |
| Production Bridge | `quant_nanggroe/engine_production_bridge.py` | 535 |
| SSH Proxy | `quant_nanggroe/providers/proxy.py` | — |
| COT Provider | `quant_nanggroe/engine/data/cot_provider.py` | 263 |
| Risk Manager | `quant_nanggroe/engine/risk/manager.py` | 673 |
| Strategy Selector | `quant_nanggroe/engine/strategy/strategy_selector.py` | 356 |
| Multi-Timeframe | `quant_nanggroe/engine/strategy/multi_timeframe.py` | 237 |

## 15 Strategies

| Name | Category | Asset Classes |
|------|----------|---------------|
| MeanReversion | mean_reversion | stocks, forex, crypto |
| Momentum | momentum | stocks, forex, crypto, futures |
| PairsTrading | pairs_trading | stocks, crypto |
| VolatilityArbitrage | volatility | stocks, futures, options |
| StatisticalArbitrage | statistical_arbitrage | stocks, crypto |
| MarketMaking | market_making | crypto, forex |
| RegimeBased | regime_detection | stocks, forex, crypto |
| CryptoSpecific | crypto | crypto |
| SMC | pattern | crypto, forex, stocks |
| ICT | pattern | crypto, forex, stocks |
| S/R | supply_demand | crypto, forex, stocks, futures |
| SnD | supply_demand | crypto, forex, stocks |
| Wyckoff | wyckoff | crypto, stocks, futures |
| COT | cot | futures, forex |
| Fundamental | fundamental | forex, stocks, futures, crypto |
