# Quant Nanggroe AI — Changelog

## v8.0.5 — Data Layer Audit: Stale Veto + REAL-ONLY Data (2026-08-25)

### 🔴 Fixes (audit round 2 — data layer)
- **STALE-DATA VETO** (`autonomous.py:_reject_stale()`) — `DataFreshnessMonitor` recorded fetches but NOTHING consumed staleness (dead guard). Now the newest bar's age is checked against 4× the timeframe interval; stale/frozen feeds → None → no signal. Malformed index → FAIL-CLOSED.
- **yfinance REMOVED from live path** (REAL-ONLY) — when MT5 rates failed transiently, signals were generated from indicative Yahoo prices and executed on MT5 spread prices. Live path (EM present) now FAIL-CLOSED; yfinance only in research/backtest contexts (no EM).
- **`record_fetch` timeframe fix** — was hardcoded `_TF.D1` for ALL timeframes; freshness monitor now records the actual fetched TF.

### 🧪 Tests
- **NEW: `tests/test_engine/test_stale_data_veto.py`** — 6 tests: fresh passes, frozen M15 vetoed, weekend gap D1 passes, unknown TF default, empty fail-closed, bad index fail-closed.
- **Full battery**: 278 pass.

---

## v8.0.4 — Full Risk Audit: Fail-Closed Everywhere (2026-08-25)

### 🔴 Critical Fixes (audit round 1)
- **FIX: `autonomous.py:_check_risk()`** — was FAIL-OPEN: exception or None execution manager got swallowed and the trade proceeded with NO risk check. Now FAIL-CLOSED: blocks on any gate error, missing EM, missing risk manager, or missing kill switch.
- **FIX: `autonomous.py:_make_decision()`** — referenced phantom variables (`atr_val`, `df`) outside its scope → silent NameError degraded every SL/TP to a fixed 1% ATR guess instead of profile-based SL/TP. Now receives `df`/`atr_value`/`timeframe` from `run()`.
- **FIX:** `pd.concat` used without pandas import in the ATR derivation fallback.

### 🔴 Critical Fixes (audit round 2 — execution path)
- **NEW GUARD: ONE-position-per-symbol enforcement** (`manager.py` step 2.5) — the mandate existed on paper but NOTHING blocked a second entry while a position was already open on that symbol. Now `execute_order()` queries BROKER TRUTH via `get_positions()` and blocks duplicates. Fail-closed: a failed position query BLOCKS the trade.
- **FILL-STATUS GATE** (`manager.py` step 5.5) — a REJECTED order (circuit breaker / MT5 error / zero fill price) used to produce a phantom `Fill(price=0.0)` → fake Telegram "TRADE EXECUTED", trailing stop anchored at 0, polluted cooldown/max-position state. Non-FILLED status now returns None + audit `ORDER_NOT_FILLED`.

### 🟠 Risk Fixes
- **MTM kill-switch blindness (pitfall #41 regression)** — open-position unrealized loss now trips the daily kill switch (LEVEL_1) mid-crash, not only at trade close. Safe to re-enable because LEVEL_1 auto-expires on a new day via `_reconcile()`; weekly/drawdown breaches still require explicit human review.
- **`StrategyCorrelationMonitor.paper_mode`** — stored but IGNORED: `check_and_act()` activated the LIVE kill switch from paper data. Suppressed in paper mode now (observes, logs, never acts).
- **`AutoDisableManager._paper_mode`** — ignored: strategies were auto-disabled from paper P&L. `update()` no longer flips enable/disable state in paper mode.

### 🧪 Tests
- **NEW: `tests/test_engine/test_risk_gate_failclosed.py`** — 10 tests: fail-closed contract (None EM, missing gates, exceptions, VETOED verdict, hold signal, low confidence), `_make_decision` signature.
- **NEW: `tests/test_engine/test_one_position_per_symbol.py`** — 6 tests: duplicate symbol blocked, different symbol allowed, empty book allowed, query failure fail-closed, rejected submit → no phantom fill.
- **Risk suite**: 211 pass (was 197 pass / 4 FAIL).
- **Full battery**: 272 pass (risk + kill-switch + core regression + new suites).

---

## v8.0.3 — Fail-Closed Risk Wiring + Launcher Fix (2026-08-25)

### 🔒 Fail-Closed Risk Guard
- **FIX: `autonomous.py:_check_risk()`** — Fail-closed when execution manager / risk gates not wired (was silently allowing trades through)
- **FIX: `autonomous.py:_make_decision()`** — Accept `df`, `atr_value`, `timeframe` params properly (was using broken `atr_val in dir()` check)
- **ATR fallback chain**: param → derive from df → 1% of price (no more `NameError`)

### 🚀 Launcher Fix
- **FIX: `QNA Launcher.bat`** — Use `/D` flag for `start` (no nested quote bug), auto-generate `.env` with JWT secret, verify `logs/` dir exists

### 📦 Version
- **Version bump** 8.0.2 → 8.0.3 (qna.py + CANONICAL.md)

## v8.0.2 — Candle Scheduler + Dashboard + Critical Fixes (2026-08-25)

### 🕯️ Real-Time Candle-Close Scheduler
- **NEW: `engine/candle_scheduler.py`** — Monitors MT5 ticks every 1s, detects candle close per symbol+TF
- **M15/H1/H4/D1 analysis pyramid** with HTF alignment check
- **Delegates to `pipeline.run()`** for end-to-end execution (data→signal→risk→trade)
- **Telegram notifications** on every trade/signal
- **SQLite trade history** (unlimited storage, replaces 500-event JSON buffer)
- **State persistence** to `data/` for dashboard consumption

### 🖥️ Dashboard Upgrades
- **NEW: `/candle-monitor`** — Live TF performance, event history, per-symbol breakdown
- **NEW: `/notifications`** — Signal/trade notification feed with filtering
- **NEW: `/trading/history`** — Unlimited trade history with pagination
- **NEW: `/api/candle-monitor`** — Paginated candle close events
- **NEW: `/api/notifications`** — Notification stats and history
- **NEW: `/api/trade-history`** — SQLite-backed trade history API
- **36 pages, 10 API routes** — all clean build

### 🐛 Critical Fixes
- **FIX: `candle_scheduler.py:474`** — `regime` undefined in `_notify()` (every Telegram notification crashed)
- **FIX: `autonomous.py:1747`** — `strategy_name` undefined in `_make_decision()` (every trade execution crashed)
- **FIX: `brokers/paper.py:23`** — `from __future__` not at top of file (broke AutoRegistry)
- **FIX: `assistant-widget.tsx:40`** — `window.innerWidth` in `useState` (SSR crash on `/_not-found`)
- **FIX: `qna.py`** — PID_DIR relative path → absolute path using PROJECT_ROOT
- **FIX: `qna.py`** — Version sync 5.1.0 → 8.0.2
- **FIX: `QNA Launcher.bat`** — Nested quote issues + added `mkdir logs`

### 🧪 Tests
- **NEW: `test_candle_scheduler.py`** — 15 tests (constants, state, alignment, persistence, singleton)
- **REWRITE: `test_ml.py`** — Matches actual `engine.models.signal_generator` API
- **61/61 core regression tests pass**

### 📦 Remotes
- Codeberg, GitHub ×3, GitLab — all synced + tagged

---

## v8.0.1 — MT5 Suffix Fix + Scheduler Ungating (2026-08-25)

### 🐛 Fixes
- **FIX: MT5 `.vxc` suffix** — resolve_symbol() probing bug, dynamic symbol discovery
- **FIX: Scheduler ungated** — removed `QNA_SCHEDULER_ENABLED` env var gate
- **FIX: `_fetch_data()`** — MT5-primary/yfinance-fallback data path
- **66/66 core tests pass**

---

## v8.0.0 — Full Autonomous Pipeline Overhaul (2026-08-25)

### 🏗️ Architecture
- **Signal Aggregation** — ONE position per symbol, fixed 0.5% risk
- **Native SMC** — OrderBlock/FVG/BOS/Sweep detection
- **Bayesian Hyperopt** — Parameter optimization
- **Trading Profiles** — Scalp(M15)/Day(H1)/Swing(D1) SL-TP profiles
- **Trailing Stop** — Breakeven ratchet + ATR trail
- **Trade Awareness** — What/why/how/lesson per trade
- **Strategy Scorecard** — Per-strategy expectancy/PF/Sharpe
- **Config Center** — Dashboard-based configuration
- **Export Center** — xlsx/pdf trade export
- **AI Assistant** — Floating copilot widget

---

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
