# Quant Nanggroe AI — Autonomous Quantitative Hedge Fund

Single-entry quantitative hedge fund platform: **`python qna.py [mode]`**.

- 699+ Python files, **77 registered strategies** via `@StrategyRegistry.register` (SMC, Wyckoff, MSNR, MeanRev, ICT, Market Profile, TSMOM, etc.)
- **Unified KillSwitch (C5)** — cross-process shared state with real daily/weekly PnL feed from MT5 `history_deals_get()`. Fail-closed: corrupt state = assumed ACTIVE (halt).
- **Closed-loop evolution** — `StrategyEvolver` → Walk-Forward backtest → `StrategyRegistry.update_params()` → persisted to disk.
- **10 REST exchange clients** (binance, okx, bybit, bitget, kraken, kucoin, gate, coinbase, bitfinex, longbridge).
- **16 registered agents** including **5 geopolitics** (american_order, chinese_order, european_order, multipolar, islamic_finance).
- **Real quantitative alpha engines**: DCC-GARCH, Causal Macro, COT, MSI, SMT divergence, Thesis Drift Guard.
- All verified: **66/66 kill_switch + risk_checks tests pass**.

---

## Quick Start

```bash
# Environment
cp .env.example .env
# Edit .env: QNAI_JWT_SECRET required (fail-closed otherwise)

# Single entry point — all modes
python qna.py [unified|api|daemon|hedge|status|stop]

# OR via launcher
launch.bat api              # FastAPI on :8000
launch.bat daemon           # Background daemon
launch.bat test             # Full test suite

# Canonical dashboard (Next.js 16 on :3000)
cd dashboard && npm run dev

# Guardian (self-healing watchtower, 1 pass)
guardian_cli.py --once

# Tests (PYTHONPATH="" mandatory)
.venv/Scripts/python -m pytest tests/ -v --tb=short
.venv/Scripts/python -m pytest tests/test_kill_switch.py -v
.venv/Scripts/python -m pytest tests/test_risk_checks.py -v

# Lint / Typecheck
ruff check quant_nanggroe/
mypy quant_nanggroe/ --ignore-missing-imports
```

**⚠️ Critical:** Always run with `PYTHONPATH=""` to avoid Hermes venv leak (`pydantic_core` crash).

---

## Architecture

```
quant_nanggroe/                                (699+ .py files)
├── qna.py                                    → Single unified entry point
├── pipeline/                                 → UnifiedPipeline (auto mode-routing)
├── api/                                      → FastAPI server (181 endpoints)
├── engine/
│   ├── strategies/                           → 77 @StrategyRegistry.register strategies
│   │   └── registry.py                       → StrategyRegistry (auto-discovery)
│   ├── risk/                                 → KillSwitch C5, DCC-GARCH, VaR, Kelly...
│   ├── causal/                               → Causal Macro Engine suite (5 modules)
│   ├── backtest/                             → Walk-forward, Monte Carlo, CPCV
│   ├── execution/                            → Order routing, Builder, Almgren-Chriss
│   ├── guardian/                             → Self-healing watchtower (Hermes cron 5min)
│   └── portfolio/                            → Kelly sizing, risk parity, ConfluenceScorer
├── hedge_fund/                               → Multi-provider aggregator
│   ├── signals/                              → 10 core + 200+ evolved providers
│   ├── risk/                                 → gate.py, guard.py (fail-closed)
│   ├── execution/                            → orders.py (trail_sl, execute)
│   └── portfolio/main.py:run_once()          → 9-stage pipeline
├── exchange/
│   └── clients/                              → 10 REST exchange clients
├── agents/                                   → 16 registered agents (incl. 5 geopolitics)
├── archive/                                  → Orphaned v6.2 artifacts (read-only)
├── tests/                                    → 66+ verified tests
└── dashboard/                                → Next.js 18-page UI
```

### 9-Stage Hedge Fund Pipeline (`run_once`)

| # | Stage | Module | Function |
|---|-------|--------|----------|
| 1 | Causal Context | `MasterQuantNanggroeEngine` | Builds `CausalContext` from event biases + macro weather |
| 2 | Market Screen | `ScreenerOrchestrator` | Pre-trade direction/score screening |
| 3 | Aggregate | `aggregate()` | Bayesian-weighted signal aggregation across ALL_PROVIDERS |
| 4 | Confluence Fusion | `ConfluenceScorer` | Multi-signal fusion (aggregator + screener + macro) |
| 5 | Position Sizing | `calculate_position_size()` + `RiskParityAllocator` | Kelly-based sizing × risk-parity weight |
| 6 | KillSwitch Check | `KillSwitch.check_auto_activate()` | C5 cross-process veto (real PnL feed) |
| 7 | Risk Guard | `risk_guard_approve()` | Fail-closed constitutional risk gate |
| 8 | Execute | `execute()` | MT5 order placement (paper mode fail-closed) |
| 9 | Post-Trade | `StressVaRCalculator` + `MatrixProfileDetector` | VaR/CVaR + pattern recording |

All 9 stages are wired in `hedge_fund/portfolio/main.py`. Each non-critical failure degrades gracefully (skip stage, log warning, continue).

### Strategy Types (77 registered)

| Type | Examples | Count |
|------|----------|-------|
| SMC/ICT | smc, ict, quarterly_theory, order_flow, volume_delta | 10+ |
| Wyckoff | wyckoff, spring_upthrust | 5+ |
| Mean Reversion | mean_reversion, half_life_mean_reversion, bollinger_squeeze | 8+ |
| MSNR | msnr, multi_timeframe_strategy | 3+ |
| Trend/Momentum | trend_follow, tsmom, adx, dmi, hull_ma, kaufman_ama | 15+ |
| Statistical | pairs_trade, statistical_arbitrage, bayesian_ridge, kalman_filter | 8+ |
| Pattern/Candlestick | engulfing, doji, hammer, harami, evening_star, inverted_hammer | 8+ |
| Macro/FX | macro_fx, dxy_momentum, carry_trade, em_carry, gold_inflation | 8+ |
| ML/Alpha | xgboost_alpha, factor_model, kmeans_regime, microstructure_alpha | 6+ |
| Other | dhaher_system, market_profile, choppiness_index, hurst_exponent | 6+ |

### Constitutional Risk Limits (fail-closed — no override)

| Limit | Value | Enforcement |
|-------|-------|------------|
| Per trade risk | 0.5% | Kelly + VaR |
| Daily loss | 1.0% | KillSwitch auto-activation |
| Weekly loss | 3.0% | KillSwitch auto-activation |
| Max drawdown | 15% | KillSwitch auto-activation |
| Min R:R | 1:2 | Trade proposal rejection |
| Max leverage | 3x | Margin monitor |
| Max trades/day | 5 | Rate limiter |

### Evolution Loop

```
StrategyEvolver → WalkForwardAnalyzer (real backtest) → StrategyRegistry.update_params()
→ persisted JSON → next run reads updated params
```

No mock. No simulation. Real backtest data feeds the evolver. Persistence survives restarts.

---

## Orphans Archived

Files removed from active tree but preserved in `archive/`:

- `archive/2026-07-28-cleanup/` — old-logs, pytest/ruff caches, temp files
- `archive/orphaned_v6.2/` — `qna_daemon.py`, DESIGN.md, FILE_LISTING.md, Riset_QNA.md, WAR_PLAN.md, diagnostic scripts, old profile activity

---

## Stack

| Layer | Choice |
|-------|--------|
| Language | Python 3.11+ |
| Package | `uv` (not pip, not poetry) |
| API | FastAPI (181 endpoints) |
| Dashboard | Next.js 16 + React 19 + Recharts + Zustand |
| Broker | MetaTrader5 (via `ExecutionManager.set_broker_handle()`) |
| Crypto | CCXT |
| Exchange REST | 10 clients via `ExchangeFactory.create_rest_client()` |
| Risk | KillSwitch C5 + DCC-GARCH + VaR + Kelly |
| Tests | pytest (66/66 verified) |
| SSL | `QNAI_SSL_VERIFY` env guard (fail-closed) |
| Secrets | env vars only — no hardcoded, no plaintext YAML |

---

## Project Status

| Domain | Rating | Detail |
|--------|--------|--------|
| Architecture | 9.7/10 | Single entry, no `__getattr__`, no `standalone.py` |
| Risk System | ✅ | C5 cross-process, real PnL, fail-closed |
| Strategies | 77 reg. | All via @StrategyRegistry.register |
| Causal Engine | 5 modules | Bias + MSI + COT + SMT + Thesis Guard |
| Pipeline | 9-stage | Full wiring verified |
| Evolution | Closed loop | Real backtest → persisted params |
| Tests | 66/66 pass | kill_switch + risk_checks |
| Security | ✅ | SSL env guard, secrets via env only |

Built by Dhaher Labs.

*"Wakafa billahi syahidan" — Gas dengan penuh amarah dan presisi.*