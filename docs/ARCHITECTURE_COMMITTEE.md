# Committee Architecture — Per-Pair Trading Intelligence — v8.0.22 CANONICAL SSOT

> **SSOT:** `CANONICAL.md` v8.1.0 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, launch.bat 1, manager.py WIB

## Overview

Each trading symbol gets a dedicated committee of specialist agents that debate
before every trade decision. Replaces the current flat pipeline with structured
adversarial reasoning.

## Current Flow (flat)

```
Signal Gen → Ensemble → Council → Risk → Execution
```

## New Flow (committee per pair)

```
┌─────────────────────────────────────────────────────────────┐
│                    SYMBOL COMMITTEE                          │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ 🐂 Bull  │  │ 🐻 Bear  │  │ 📊 Macro │  │ ⚖️ Risk  │   │
│  │ Analyst  │  │ Analyst  │  │ Analyst  │  │ Officer  │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │              │              │              │          │
│       └──────────────┴──────────────┴──────────────┘          │
│                          │                                    │
│                    ┌─────┴─────┐                              │
│                    │  🗳️ Vote  │                              │
│                    │  Chamber  │                              │
│                    └─────┬─────┘                              │
│                          │                                    │
│                    ┌─────┴─────┐                              │
│                    │ ⚡ Execute │                              │
│                    └───────────┘                              │
└─────────────────────────────────────────────────────────────┘
```

## Agent Roles

### 🐂 Bull Analyst
- **Input**: OHLCV, volume, momentum indicators, support levels
- **Output**: `{"bias": "bullish", "confidence": 0.0-1.0, "evidence": [...]}`
- **Persona**: Aggressive, looks for reasons TO buy
- **Indicators**: RSI oversold, MACD cross up, volume spike, support bounce

### 🐻 Bear Analyst
- **Input**: OHLCV, volume, momentum indicators, resistance levels
- **Output**: `{"bias": "bearish", "confidence": 0.0-1.0, "evidence": [...]}`
- **Persona**: Skeptical, looks for reasons TO sell
- **Indicators**: RSI overbought, MACD cross down, distribution, resistance rejection

### 📊 Macro Analyst
- **Input**: Economic calendar, DXY, yields, correlations, session data
- **Output**: `{"regime": "risk-on/risk-off/neutral", "confidence": 0.0-1.0, "evidence": [...]}`
- **Persona**: Big picture, cross-asset
- **Data**: News sentiment, COT positioning, yield curve, DXY trend

### ⚖️ Risk Officer (VETO POWER)
- **Input**: Portfolio state, correlation exposure, drawdown, all agent proposals
- **Output**: `{"verdict": "APPROVE/VETO", "reason": "...", "max_lots": N}`
- **Persona**: Conservative, fail-closed
- **Checks**: Max risk/trade, daily drawdown, correlation, portfolio heat, news risk

### ⚡ Execution Agent
- **Input**: Approved trade from Vote Chamber
- **Output**: MT5 order with optimal entry/SL/TP/lot size
- **Persona**: Precise, timing-focused
- **Logic**: ATR-based SL/TP, spread-aware entry, partial close logic

## Vote Chamber Rules

1. Each agent casts: BUY / SELL / HOLD with confidence
2. **Quorum**: At least 3/4 analysts must agree (bull+bear+macro)
3. **Risk Officer has ABSOLUTE VETO**: Can block any trade
4. **Consensus threshold**: Weighted average confidence ≥ 0.6
5. **Tie-breaking**: If bull=bear, HOLD wins (no trade)
6. **Evidence required**: Each vote must include ≥ 1 piece of evidence

## Signal Flow

1. Candle closes → Committee convenes for affected symbols
2. Each analyst runs their analysis (parallel)
3. Votes collected in Vote Chamber
4. Risk Officer reviews
5. If approved → Execution Agent places order
6. Full debate + vote logged to `signal_context` table

## Strategy Evaluation Integration

Each committee tracks per-strategy performance:
- Win rate, Sharpe, profit factor per strategy per symbol
- Auto-disable strategies with Sharpe < 0.5 over 30-day window
- Re-tune strategies via Bayesian optimization
- Roll-forward walk optimization quarterly

## Data Sources

### Per-Committee Data
- **MT5**: OHLCV (M5/H1/D1), tick data, spread, volume
- **Economic Calendar**: High-impact events (NFP, CPI, FOMC)
- **Sentiment**: News sentiment via free APIs (NewsAPI, Finnhub)
- **COT Data**: Commitment of Traders weekly report
- **Correlations**: DXY, yields, S&P500, gold

### Fallback Chain
1. MT5 real-time (primary)
2. Yahoo Finance (backup)
3. Cached data (last resort)

## Implementation Plan

### Phase 1: Core Committee (NOW)
- [ ] Create `committee.py` with agent base class
- [ ] Implement Bull/Bear/Risk analysts
- [ ] Wire Vote Chamber logic
- [ ] Integrate with autonomous pipeline

### Phase 2: Strategy Evaluation (NEXT)
- [ ] Rolling backtest per strategy per symbol
- [ ] Live signal tracking with outcome
- [ ] Auto-disable/enable logic
- [ ] Bayesian re-tune loop

### Phase 3: Data Pipeline (AFTER)
- [ ] News sentiment integration
- [ ] COT data fetcher
- [ ] Economic calendar gate
- [ ] Cross-asset correlation engine

## File Structure

```
quant_nanggroe/engine/agentic/
├── committee/
│   ├── __init__.py
│   ├── agents.py          # Bull, Bear, Macro, Risk, Execution agents
│   ├── vote_chamber.py    # Voting + consensus logic
│   ├── debate.py          # Structured debate format
│   └── per_pair.py        # Per-symbol committee manager
├── autonomous.py          # (existing, modified to use committee)
└── ...
```

---

> **SSOT:** `CANONICAL.md` v8.1.0 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, launch.bat 1, manager.py WIB | Live: ValetaxIntl-Live2 372044706 | 83 strategies, probe 0/32, CPCV 207

---

> **SSOT:** `CANONICAL.md` v8.1.0 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, vector 6 modul live, risk per-symbol
