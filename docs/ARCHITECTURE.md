# QNA Architecture

## System Overview

```mermaid
graph TD
    A[Synthetic Data<br/>GARCH Engine] --> B[8 Strategies<br/>Momentum, Mean-Reversion,<br/>Breakout, Pairs, ML,<br/>Statistical, HFT, Macro]
    B --> C[Backtest Engine<br/>Walk-Forward, CPCV,<br/>Monte Carlo, PSR/DSR]
    C --> D[Risk Layer<br/>KillSwitch, Kelly,<br/>VaR, Drawdown, Regime]
    D --> E[Paper Trading Daemon<br/>PID 6540 — 1h Cycle]
    E --> F[Alpha Audit<br/>Weekly Reports,<br/>Scorecard 45/100]
    E --> G[Dashboard<br/>Static HTML — 441 lines]
    E --> H[PnL CSV<br/>paper_state/pnl.csv]
```

## Test Coverage — 1039/1039 Pass (100%)

```mermaid
pie title Test Distribution by Module
    "Engine Backtest" : 35
    "Risk & Kelly" : 20
    "Execution & Guards" : 15
    "Data Pipeline" : 10
    "Strategies & Decision" : 10
    "SMC & Compliance" : 5
    "Security & Types" : 5
```

## Swarm Evolution — 39 Sub-Agents Across 8 Swarms

```mermaid
gantt
    title QNA Development — 8 Swarms
    dateFormat  YYYY-MM-DD
    section Swarm 1
    Core Engine + 8 Strategies    :done, 2026-06-20, 2d
    section Swarm 2
    Risk + Data Pipeline          :done, 2026-06-21, 1d
    section Swarm 3
    Backtest + Compliance         :done, 2026-06-22, 1d
    section Swarm 4
    SMC + Execution + Dashboard   :done, 2026-06-23, 1d
    section Swarm 5
    Daemon + Exchange + Coverage  :done, 2026-06-24, 1d
    section Swarm 6
    All 598 Tests Green           :done, 2026-06-24, 1d
    section Swarm 7
    Coverage Push 805 Tests       :done, 2026-06-25, 1d
    section Swarm 8
    Renaissance — 1039 Tests      :done, 2026-06-25, 1d
```

## Pipeline Flow

```mermaid
flowchart LR
    subgraph Input
        A[GARCH<br/>Synthetic Data]
        B[CSV Cache<br/>data/cache.db]
    end
    subgraph Engine
        C[8 Strategies]
        D[Backtest Engine]
        E[Risk Layer]
        F[Kelly Sizing]
    end
    subgraph Output
        G[Paper Daemon<br/>PID 6540]
        H[Dashboard<br/>localhost:8080]
        I[Alpha Reports]
    end
    A --> C
    B --> D
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H
    G --> I
```

## Status

- **Tests:** 1039/1039 ALL PASS (100%)
- **Coverage:** ~60-62%
- **Daemon:** LIVE PID 6540, 10+ cycles
- **Scorecard:** 45/100 — needs real trading data
- **Exchange:** Prepped, waiting for API keys
- **Sub-agents:** 39 across 8 swarms
