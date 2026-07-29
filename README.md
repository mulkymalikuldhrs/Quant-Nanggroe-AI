# Quant Nanggroe AI — Autonomous Quantitative Hedge Fund

Single-entry autonomous hedge fund: **`python qna.py [mode]`**.

- **678 .py files**, **84 registered strategies** via `@StrategyRegistry.register` (SMC, Wyckoff, MSNR, MeanRev, ICT, Market Profile, TSMOM, etc.)
- **8 scorers, 100% weight** (Macro 30%, Economic 20% FRED live + cache, Bond 10%, Sentiment 10% Fear&Greed live + cache, Technical 10%, Vol 5%, Geo 5%, **Positioning 10% CFTC COT**) — ✅ **ALL WIRED** via FusionEngine
- **Multi-timeframe scoring** (4 frames: Monthly→Macro, Weekly→Macro+Econ, Daily→ALL, Session→Sentiment+Tech) — ConflictResolver: HTF vs LTF alignment → HOLD/REDUCE/PROCEED
- **Self-evolve loop** — WeightEvolver: per-scorer Sharpe after 20 trades, ±5%/cycle, circuit breaker at 50 bad trades
- **7-stage pipeline** — Connect → Discover → Trail/Vote → Risk Check → Execute → Post-Trade → Cleanup
- **Unified KillSwitch (C5)** — cross-process shared state with real daily/weekly PnL feed from MT5 `history_deals_get()`. Fail-closed.
- **10 REST exchange clients** (binance, okx, bybit, kraken, coinbase, kucoin, gate, bitget, bitfinex, longbridge)
- **16 registered agents** (researcher, trader, strategist + 13 more)
- **4 git remotes**: codeberg (primary), github, **github2 (4141 files diverged — v2-dashboard branch extracted)**, gitlab
- **E:\ drive sources**: hidden-regime COT analyzer, mue-x 992 evolved providers (dynamic discovery), AI-Trader cache/TTL

---

## Architecture

```
quant_nanggroe/                                (678 .py files)
├── qna.py                                    → Single unified entry point (962 lines)
├── core/scoring/                             → 8 scorers + FusionEngine + MTFEngine + WeightEvolver (✅ ALL WIRED)
├── pipeline/                                 → UnifiedPipeline (auto mode-routing)
├── api/                                      → FastAPI server
├── engine/
│   ├── strategies/                           → 84 @StrategyRegistry.register strategies
│   ├── risk/                                 → KillSwitch C5, DCC-GARCH, VaR, Kelly, 25 files
│   ├── causal/                               → Causal Macro Engine suite (14 files)
│   ├── backtest/                             → Walk-forward, Monte Carlo
│   ├── execution/                            → Order routing (async wrapper)
│   ├── guardian/                             → Self-healing watchtower
│   └── portfolio/                            → Kelly sizing, risk parity, ConfluenceScorer
├── hedge_fund/                               → Multi-provider aggregator
│   ├── portfolio/main.py:run_once()          → 7-stage pipeline (310 lines, refactored S8)
│   ├── signals/                              → Bayesian-weighted signal voting + MUE-X 992 evolved (dynamic discovery)
│   ├── risk/guard.py                         → Fail-closed risk gate
│   └── execution/                            → trail_sl, orders
├── exchange/clients/                         → 10 REST exchange clients
├── agents/                                   → 16 registered agents
├── tests/                                    → 166 test files (117 passing env-fixed S8)
├── dashboard/                                → Next.js 16 UI (20 pages, proxy to :8000)
└── docs/                                     → 66 canonical + archive docs
```

### 10-Stage Pipeline

| # | Stage | Status |
|---|-------|--------|
| 1 | Gate check (WalkForwardRegistry) | ✅ |
| 2 | MT5 connect / paper auto-fallback | ✅ |
| 3 | Trail existing positions | ✅ |
| 4 | CausalContext (MasterQuantNanggroeEngine) | ✅ |
| 5 | ScreenerOrchestrator | ✅ |
| 6 | Bayesian-weighted signal aggregation | ✅ |
| 7 | **FusionEngine scoring (8 scorers)** | **✅ NOW WIRED** |
| 8 | ConfluenceScorer fusion | ✅ |
| 9 | Position sizing + RiskParityAllocator | ✅ |
| 10 | KillSwitch C5 + risk_guard_approve | ✅ |
| 11 | ExecutionManager.execute_order | ✅ |
| 12 | Post-trade: StressVaR + PatternRecorder | ✅ |

### Scoring Engine (100% Wired — Session 7)

| Scorer | Weight | Data Source | Status |
|--------|--------|-------------|--------|
| MacroScorer | 30% | ctx dict (macro_regime from CausalEngine) | ✅ wired |
| EconomicScorer | 20% | FRED API **LIVE + cached 600s** | ✅ live |
| BondScorer | 10% | ctx dict | ✅ wired |
| SentimentScorer | 10% | Fear & Greed **LIVE + cached 300s** | ✅ live |
| TechnicalScorer | 10% | ctx dict (from strategy) | ✅ wired |
| VolatilityScorer | 5% | ctx dict | ✅ wired |
| GeopoliticalScorer | 5% | ctx dict | ✅ wired |
| **PositioningScorer** | **10%** | **CFTC COT API + hidden-regime** | **✅ wired** |
| **FusionEngine** | — | Weighted sum + override logic | **✅ WIRED** |

---

## Quick Start

```bash
# Environment
cp .env.example .env
# Edit .env: QNAI_JWT_SECRET required (fail-closed otherwise)

# Single entry point
python qna.py unified                    # Auto-detect mode
python qna.py api                        # FastAPI on :8000
python qna.py hedge --paper EURUSD       # Paper trade EURUSD
python qna.py daemon                     # Background daemon
python qna.py status                     # System health

# OR via launcher
launch.bat api                           # FastAPI on :8000

# Guardian (self-healing watchtower)
guardian_cli.py --once

# Lint / Typecheck
ruff check quant_nanggroe/
mypy quant_nanggroe/ --ignore-missing-imports

# Dashboard
cd dashboard && npm run dev              # Next.js 16 on :3000
```

**⚠️ Critical:** Always run with `PYTHONPATH=""` to avoid Hermes venv leak.

---

## Scorers (All ✅ WIRED)

| Scorer | Weight | File | Data | Status |
|--------|--------|------|------|--------|
| Macro | 30% | `core/scoring/macro_scorer.py` | CausalContext regime | ✅ wired |
| Economic | 20% | `core/scoring/economic_scorer.py` | FRED API live + 600s cache | ✅ wired |
| Bond | 10% | `core/scoring/bond_scorer.py` | ctx dict | ✅ wired |
| Sentiment | 10% | `core/scoring/sentiment_scorer.py` | Fear & Greed live + 300s cache | ✅ wired |
| Technical | 10% | `core/scoring/technical_scorer.py` | ctx dict | ✅ wired |
| Volatility | 5% | `core/scoring/volatility_scorer.py` | ctx dict | ✅ wired |
| Geopolitical | 5% | `core/scoring/geo_scorer.py` | ctx dict | ✅ wired |
| Positioning | 10% | `core/scoring/positioning_scorer.py` | CFTC COT API + hidden-regime | ✅ wired |
| **FusionEngine** | — | `core/scoring/fusion_engine.py` | Weighted sum + override | **✅ WIRED** |

---

## Git Remotes

| Remote | URL | Key Branch |
|--------|-----|------------|
| codeberg (primary) | `Dhaher-Labs/Quant-Nanggroe-AI` | main |
| github | `mulkymalikuldhaher/Quant-Nanggroe-AI` | main |
| **github2 ⚠️** | `mulkymalikuldhrs/Quant-Nanggroe-AI` | **audit/p1-production-hardening** — 4141 files diverged |
| gitlab | `mulkymalikuldhr/Quant-Nanggroe-AI` | main |

**github2 divergence:** 4141 files changed, 743,004 insertions — contains full Next.js dashboard, skills/ directory, web_interface/ with PWA + LLM providers + workflows, Vercel deployment.

---

## E:\ Data Sources

| Path | Content | Value for QNA |
|------|---------|---------------|
| `E:\hidden-regime\` | COT analysis, regime evolution, signal attribution | → PositioningScorer + DataProvider |
| `E:\mue-x\genes\qna_strategies\` | **992 evolved strategy files** | → Filtered top 10% by Sharpe |
| `C:\e\archived\AI-Trader\` | market_intel.py (1911 lines), TTL cache, news pipeline | → DataProvider cache engine |

---

## Blockers (Session 7 Progress)

1. ~~**FusionEngine NOT wired**~~ ✅ **FIXED** — 8 scorers active in `run_once()`
2. **numpy broken** in .venv — Python 3.14 removed `np.clip` (scoring files fixed, other modules may still use numpy)
3. **pytest env broken** — langsmith plugin crash (no httpx)
4. ~~**PositioningScorer 10% gap**~~ ✅ **FIXED** — CFTC COT API + hidden-regime pipeline
5. **github2 4141 files divergence** — dashboard not merged (ADR-007 exists)
6. ~~**No data layer**~~ ✅ **FIXED** — `core/cache.py` with TTLCache + cached decorator, wired to EconomicScorer + SentimentScorer
7. ~~**Weekly loss veto absent** on Path-B~~ ✅ **FIXED** — hard veto using canonical MAX_WEEKLY_LOSS

---

## Stack

| Layer | Choice |
|-------|--------|
| Language | Python 3.14 |
| Package | `uv` |
| API | FastAPI |
| Dashboard | Next.js 16 + React 19 + Recharts |
| Broker | MetaTrader5 (paper fail-closed) |
| Crypto | CCXT |
| Risk | KillSwitch C5 + DCC-GARCH + VaR + Kelly |
| Tests | pytest (env broken — 3 pre-existing failures) |

Built by Dhaher Labs.

*"Wakafa billahi syahidan" — Gas dengan penuh amarah dan presisi.*
