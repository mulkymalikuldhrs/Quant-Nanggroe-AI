# CLAUDE.md — Quant Nanggroe AI (Quant Nation)

Autonomous quantitative hedge fund. 800+ .py files, 83 strategies, 9 agents, 10 API routes, 36 dashboard pages.

## Entry & Commands

```
python qna.py daemon           # autonomous trading loop (candle-close scheduler)
python qna.py api              # FastAPI on :8000
python qna.py status           # system status
cd dashboard && npm run dev    # Next.js 16 on :3000
python -m pytest tests/test_engine/test_strategy_allocation.py tests/test_risk/test_trailing_stop_gate7.py tests/test_engine/test_analytics.py tests/test_engine/test_signal_aggregator.py tests/test_engine/test_ml.py tests/test_engine/test_candle_scheduler.py -q  # core regression battery
```

**Critical gotchas:**
- `PYTHONPATH=""` mandatory — Hermes venv leaks `pydantic_core` → crash
- `QNAI_JWT_SECRET` env var required for API boot (fail-closed)
- **numpy 2.5.1** ✅ in .venv (reinstalled). System Python 3.14 has working numpy/pandas/scipy.
- **pytest works** ✅ — core battery green (see CHANGELOG)
- Hardware: i7-10th gen, 16GB RAM, no GPU

## Architecture

```
quant_nanggroe/
  qna.py                          ← single entry point (962 lines)
  core/scoring/                   ← 8 scorers + FusionEngine + MTFEngine + WeightEvolver + TTLCache
  hedge_fund/portfolio/main.py    ← 7-stage pipeline: run_once()
  engine/
    strategies/                   ← 84 @StrategyRegistry.register strategies
    risk/                         ← KillSwitch C5, DCC-GARCH, VaR, Kelly, constants (25 files)
    causal/                       ← Causal Macro Engine suite (14 files)
    execution/                    ← Order routing + broker adapters
    portfolio/                    ← Kelly sizing, risk parity, ConfluenceScorer
    backtest/                     ← Walk-forward, Monte Carlo
    guardian/                     ← Self-healing watchtower (Hermes cron 5min)
    screener/                     ← ScreenerOrchestrator
  exchange/clients/               ← 10 REST clients (binance, okx, bybit, kraken, coinbase, etc.)
  agents/                         ← 16 agents
  api/                            ← FastAPI server
  pipeline/                       ← UnifiedPipeline (auto mode-routing)
  tests/                          ← ~150+ test files (**pytest green** ✅ — see CHANGELOG for latest count)
  dashboard/                      ← Next.js 16 + React 19 + Recharts
```

### Pipeline (run_once() — hedge_fund/portfolio/main.py)

1. MT5 connect / paper auto-fallback
2. Gate check — WalkForwardRegistry viability
3. Symbol selection / trail existing positions
4. Causal context — DXY/ZB macro via yfinance
5. ScreenerOrchestrator — market screen
6. Bayesian-weighted signal aggregation + SignalTracker
7. **FusionEngine** — 8 scorers (100% weight, ALL WIRED)
8. MultiTimeframeEngine — HTF/LTF veto
9. ConfluenceScorer — fuses aggregator + screener + fusion
10. Position sizing + RiskParityAllocator
11. KillSwitch C5 + risk_guard_approve (fail-closed)
12. ExecutionManager.execute_order (async)
13. Post-trade: WeightEvolver record, StressVaR, MatrixProfileDetector

### 8 Scorers (✅ ALL WIRED)

| Scorer | Weight | Data | Cache |
|--------|--------|------|-------|
| MacroScorer | 30% | CausalContext regime | — |
| EconomicScorer | 20% | FRED API live | TTLCache 600s |
| BondScorer | 10% | ctx dict | — |
| SentimentScorer | 10% | Fear & Greed live | TTLCache 300s |
| TechnicalScorer | 10% | ctx dict | — |
| PositioningScorer | 10% | CFTC COT API + hidden-regime | 3600s |
| GeopoliticalScorer | 5% | ctx dict | — |
| VolatilityScorer | 5% | ctx dict | — |

FusionEngine: weighted sum + override logic (confidence >= 60% overrides aggregator).

### Dual Scoring Trees
- `core/scoring/` — primary, wired to pipeline
- `engine/scoring/` — older copy, 10 files, NOT wired. Possibly vestigial.

### 4 Git Remotes

| Remote | URL | Notes |
|--------|-----|-------|
| codeberg | Dhaher-Labs/Quant-Nanggroe-AI | primary |
| github | mulkymalikuldhaher/Quant-Nanggroe-AI | main |
| github2 | mulkymalikuldhrs/Quant-Nanggroe-AI | **4141 files diverged** — contains full Next.js dashboard |
| gitlab | mulkymalikuldhr/Quant-Nanggroe-AI | main |

### E:\ Data Sources

| Path | Content | Used By |
|------|---------|---------|
| `E:\hidden-regime\` | COT analysis, regime evolution | PositioningScorer |
| `E:\mue-x\genes\qna_strategies\` | 992 evolved strategy files | Dynamic MueXSignalProvider |
| `C:\e\archived\AI-Trader\` | market_intel.py (1911 lines), TTL cache | DataProvider cache engine |

## Core Principles
- **Source code is truth** — docs are hearsay. Verify every claim against imports/calls.
- **Wiring > new features** — connect what exists before creating anything new.
- **Single source of truth** per concern: entry point (qna.py), risk, execution, registries.
- No silent deletion — all removals logged in QNA_AGENT_STATE.md.
- End every session updating QNA_AGENT_STATE.md with verified evidence.

## Tech Stack

| Layer | Choice |
|-------|--------|
| Language | Python >=3.11 |
| Package | `uv` |
| API | FastAPI |
| Dashboard | Next.js 16 + React 19 + Recharts |
| Broker | MetaTrader5 (paper fail-closed) |
| Crypto | CCXT |
| Agent framework | LangGraph |
| Risk | KillSwitch C5 + DCC-GARCH + VaR + Kelly |
| DB | SQLAlchemy + Alembic |

Built by Dhaher Labs.