# Quant Nanggroe AI — Changelog

## v5.1.0 — Security Sweep + Cleanup + AutoRegistry v3 (2026-07-24)

### 🔒 Security
- **Removed hardcoded MT5 password** from `scripts/qna_autonomous_cycle.py` — now reads `MT5_PASSWORD` env var
- **Removed hardcoded MT5 login** from `hedge_fund.py` and `quant_nanggroe/hedge_fund/hedge_fund.py` — now reads `MT5_LOGIN` env var
- **Plaintext secrets migrated** — `config/credentials.json` → `QNA_ADMIN_API_KEY`, `config/freqtrade.json` → `FREQTRADE_JWT_SECRET` + `FREQTRADE_USERNAME` + `FREQTRADE_PASSWORD`
- `.env.example` documents all required env vars

### 🧹 Cleanup
- **Deleted 6 duplicate directories** (~400K+ freed): `D:\d\`, `D:\e\`, `D:\c\`, `E:\d\`, `E:\e\`, `E:\c\`
- **Unique files preserved** to canonical locations (`QNA_macro_economist_finding.md`, `FINDING_AGENT45_DEADCODE.md`, etc.)
- Canonical: `D:\repositories\Quant-Nanggroe-AI-worktree` (QNA), `D:\repositories\ai-multicolony-worktree` (MultiColony)

### ✨ AutoRegistry v3
- **Scans ENTIRE repo** — all 32 top-level directories, 1017+ .py files (was 736 in `quant_nanggroe/` only)
- **Auto-generates `__init__.py`** for any directory missing one
- **Auto-cleans stale registrations** when files are deleted
- **File hash tracking** for change detection
- **Health check**: reports coverage %, stale entries, missing inits

### 🚀 Push Status
- Codeberg (Dhaher-Labs): ✅ `19fab8d`
- GitLab (mulkymalikuldhr): ✅ `19fab8d`
- GitHub (mulkymalikuldhrs): ✅ Pushed
- GitHub (mulkymalikuldhaher): ❌ Branch protection blocks direct push

---

## v5.0.0 — Institutional Quant Autonomous Grade (2026-07-24)

### 🎯 Major Release: Self-Aware, Self-Evolve, Self-Fine-Tune
This release transforms QNA from a trading bot into a **living autonomous hedge fund** that evolves and optimizes itself.

### ✨ New Features
- **Self-Aware Module** (`engine/self_aware.py`) — Reflects on every pipeline run, detects anomalies
- **StrategyEvolver** (`engine/strategy/strategies/strategy_evolver.py`) — Walk-forward validated mutation gate
- **SelfFineTuner** (`engine/strategy/strategies/self_finetune.py`) — Grid search + walk-forward optimization
- **AutoRegistry** (`engine/registry.py`) — Self-discovering component registry
- **Standalone Mode** (`engine/standalone.py`) — Full autonomous pipeline without Hermes

### 🔧 Fixes
- **Weekly loss veto** — `checks.py` Check 4 properly vetoed (3/3 test pass)
- **Risk manager combined path** — `check_trade()` accepts `daily_pnl_pct` param when broker unavailable
- **Engine `__all__`** — Removed 10 ghost `hermes_*` references
- **Debate engine** — Added `summary` + `reasoning` fields to DebateResult

### 📊 Test Results
- Full suite: 492/493 core tests pass (99.8%)
- Risk tests: 112/112 pass
- Fast suite: 94/94 pass

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

## v4.7.0 — E: Drive Wiring + Real API Stubs (2026-07-23)
- 4 external signal adapters wired
- 3 API stubs replaced with real functionality
- Colony, Memory, Security tools fully implemented

## v4.6.0 — Initial Architecture (2026-07-22)
- 16-stage pipeline
- MT5 integration
- Risk guard system
- Strategy engine

---

*v5.1.0 — Built with fury from Aceh, Indonesia 🇮🇩*
