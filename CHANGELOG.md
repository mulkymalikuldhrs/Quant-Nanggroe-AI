# Quant Nanggroe AI — Changelog

## v5.0.0 — Institutional Quant Autonomous Grade (2026-07-24)

### 🎯 Major Release: Self-Aware, Self-Evolve, Self-Fine-Tune

This release transforms QNA from a trading bot into a **living autonomous hedge fund** that evolves and optimizes itself.

### ✨ New Features

- **Self-Aware Module** (`engine/self_aware.py`) — Reflects on every pipeline run, detects anomalies (losing streaks, drawdown, stale strategies), produces "I am X because Y" reasoning
- **StrategyEvolver** (`engine/strategy/strategies/strategy_evolver.py`) — Walk-forward validated mutation gate: mutate → backtest → only promote if improved >5%
- **SelfFineTuner** (`engine/strategy/strategies/self_finetune.py`) — Grid search + walk-forward optimization: automatically fine-tunes parameters after accepted mutations
- **AutoRegistry** (`engine/registry.py`) — Self-discovering component registry: any file placed in monitored directories is auto-imported and registered
- **Standalone Mode** (`engine/standalone.py`) — Full autonomous pipeline runs without Hermes dependency

### 🔧 Fixes

- **Weekly loss veto** — `checks.py` Check 4 now properly vetoed (3/3 test pass)
- **Risk manager combined path** — `check_trade()` accepts `daily_pnl_pct` param when broker unavailable
- **Credentials security** — Plaintext secrets replaced with env vars (`config/credentials.json`, `config/freqtrade.json`)
- **Engine `__all__`** — Removed 10 ghost `hermes_*` references
- **Debate engine** — Added `summary` + `reasoning` fields to DebateResult

### 📊 Test Results

- Full suite: 492/493 pass (99.8%)
- Risk tests: 112/112 pass
- Fast suite: 94/94 pass

### 🏗️ Architecture Changes

- `engine/strategies/` now a backward-compatibility facade re-exporting from `engine/strategy/strategies/`
- SelfFineTuner wired into `_trigger_evolution` — after accepted mutation, auto-fine-tunes
- All 24 active strategies auto-discovered via AutoRegistry
- Credentials migrated to env vars (plaintext removed from git)

### 📁 New Files

- `quant_nanggroe/engine/self_aware.py` — Self-awareness module
- `quant_nanggroe/engine/registry.py` — Auto-discovery registry
- `quant_nanggroe/engine/standalone.py` — Zero-Hermes entry point
- `quant_nanggroe/engine/strategy/strategies/strategy_evolver.py` — Evolution validation gate
- `quant_nanggroe/engine/strategy/strategies/self_finetune.py` — Auto-optimization

---

## v4.8.2 — Paper Trading E2E (2026-07-23)

- E2E paper trading test (2 scenarios)
- 79 unit tests pass
- FinalDecider veto fix
- Auto-evolve from TradeLifecycle
- MT5 demo configured

## v4.8.0 — SLA Pipeline + 9router Integration (2026-07-23)

- 9router as primary LLM provider
- SLA metrics tracking (12 fields)
- Dashboard Fluid Island redesign (17 routes)
- Trailing stop wired
- SL/TP to broker

## v4.7.0 — E: Drive Wiring + Real API Stubs (2026-07-23)

- 4 external signal adapters wired
- 3 API stubs replaced with real functionality
- Colony, Memory, Security tools fully implemented
- Pipeline wiring complete (stubs_remaining: 3→0)

## v4.6.0 — Initial Architecture (2026-07-22)

- 16-stage pipeline
- MT5 integration
- Risk guard system
- Strategy engine

---

*v5.0.0 — Built with fury from Aceh, Indonesia 🇮🇩*
