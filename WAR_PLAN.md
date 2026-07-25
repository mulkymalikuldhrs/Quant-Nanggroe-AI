# QNA — Autonomous Quant Hedge Fund: Real-Market War Plan
**Version:** 1.0 (War Ready) | **Date:** 2026-07-25 | **Author:** Dhaher Labs
**Status:** EXECUTE — no simulation, real capital path after gate

---

## 0. DIRECTIVE
"Make our Autonomous Quant Hedge Funds come true." — Mulky (2026-07-25)

QNA is NOT a research toy. It is a production autonomous hedge fund that:
1. Runs 24/7 via Hermes profile crons (all 7 profiles, parallel)
2. Generates signals from 100+ providers + 64 archive strategies
3. Passes gate (Sharpe > 0.5, Return > 0%, DD > -25%)
4. Executes to MT5 (Valetax demo → real broker)
5. Self-evolves, self-corrects, self-heals — no human babysitting

---

## 1. CURRENT STATE (Verified 2026-07-25)

| Component | Status | Evidence |
|-----------|--------|----------|
| MT5 connector | ✅ EXISTS | `quant_nanggroe/connectors/mt5_broker.py` (169 lines, fail-closed) |
| Risk guard | ✅ EXISTS | `quant_nanggroe/engine/risk/manager.py` — daily/weekly-loss veto wired |
| Backtest engine | ✅ EXISTS | `scripts/backtest_dhaher_sltp.py` (SL/TP-aware) |
| Strategy registry | ✅ EXISTS | `quant_nanggroe/engine/registry.py` — AutoRegistry v2 (active + archive) |
| Decorator strategies | ✅ 7+ live | `adaptive_moving_average.py`, `dhaher_system.py`, etc. |
| Archive strategies | ✅ 64 orphan | 133 strategy classes in `archive/` (not yet wired) |
| API server | ✅ EXISTS | `quant_nanggroe/api/app.py` — 31 routes |
| Cron runner | ✅ EXISTS | `qna-production-runner.py` (no_agent, silent) |
| Profile crons | ⚠️ PAUSED | 4 pollution crons paused (need resume scoped to QNA) |

**Gap to war:** archive strategies not registered, real MT5 not connected (Valetax IPC timeout), risk guard needs live PnL (not phantom).

---

## 2. WAR PHASES

### PHASE 1 — Wire All Strategies (P0)
**Goal:** AutoRegistry discovers ALL 200+ strategies (active + archive).
- [x] AutoRegistry v2 scans `quant_nanggroe/engine/strategies/` + `archive/`
- [ ] Register 64 archive-only strategies via `archive/__init__.py` re-export
- [ ] Verify: `list_strategies()` returns 200+ entries
- [ ] Fix: archive strategies import `Strategy` base correctly (no broken imports)
- **Owner:** devbot (profile cron, scoped to QNA)
- **Verify:** `python -c "from quant_nanggroe.engine.registry import list_strategies; print(len(list_strategies()))"` → 200+

### PHASE 2 — Real Backtest Validation (P0)
**Goal:** Every strategy passes gate on REAL data (yfinance EURUSD 24.5k M15).
- [ ] Run `scripts/backtest_dhaher_sltp.py` for all 200 strategies
- [ ] Walk-forward 5-fold per strategy
- [ ] Gate: Sharpe > 0.5, Return > 0%, DD > -25%
- [ ] Kill switch: strategies failing gate → archived, not deployed
- **Owner:** traderbot (quant mind) + researchbot (validation)
- **Verify:** `results/gate_status.json` — X/200 pass

### PHASE 3 — MT5 Live Connection (P0)
**Goal:** Connect to Valetax demo, execute real orders.
- [ ] Fix Valetax IPC timeout: two-step init (kill terminal → launch with creds → wait 20s → `mt5.initialize()`)
- [ ] Verify symbol trade_mode (Valetax `.vx` = mode 4 = DISABLED — need real broker)
- [ ] Switch to Exness/real broker with full trading (mode 3)
- [ ] Risk guard reads REAL PnL via `history_deals_get` (not floating equity)
- **Owner:** autobot (orchestrator) + traderbot (execution)
- **Verify:** `mt5.account_info()` returns balance, positions open/close

### PHASE 4 — Risk Guard Hardening (P0)
**Goal:** Fail-closed, no phantom veto, no rubber stamp.
- [x] Daily/weekly-loss veto wired (reads real PnL)
- [x] Remove floating-equity fallback (phantom veto source) — verified: manager.py has no account_info()/float(mt5) fallback; `_sync_realized_pnl` uses history_deals_get only
- [x] Add weekly-loss veto — verified BOTH paths present: constitutional Check 4 (3% hard limit) + kill-switch AUTO_WEEKLY_LIMIT (-2.5% early warning) in `_auto_check_kill_switch`
- [x] Kill switch: AUTO_DAILY_LIMIT resets after restart — kill_switch.py `_reconcile` auto-expires stale level_1 (daily) on new day; weekly/drawdown require RESET_CONFIRMATION
- **Owner:** clawbot (tester) + hackerbot (security audit)
- **Verify:** Force daily loss > 5% → veto fires, blocks ALL orders

### PHASE 5 — Parallel Profile Orchestration (P1)
**Goal:** All 7 profiles run QNA war in parallel, no conflicts.
- [ ] Resume 4 paused crons (devbot, clawbot, hackerbot, researchbot) — scoped to QNA ONLY
- [ ] autobot: orchestrator (deploy decisions)
- [ ] traderbot: execution (MT5 orders)
- [ ] devbot: strategy wiring (AutoRegistry)
- [ ] clawbot: adversarial test (break own output)
- [ ] hackerbot: security audit (risk guard)
- [ ] researchbot: validation (walk-forward)
- [ ] fangbot: OpenFang optimization (param tuning)
- **Owner:** autobot (coordinator)
- **Verify:** All 7 crons healthy, no version drift, no file spam

### PHASE 6 — Self-Evolution Loop (P1)
**Goal:** QNA improves without human input.
- [x] StrategyEvolver module exists
- [ ] Wire `_trigger_evolution` to real backtest (not mock)
- [ ] MUE-X bridge: 60+ genes → strategy mutations → register
- [ ] Self-aware: detect regime, adapt risk
- **Owner:** devbot + researchbot
- **Verify:** Evolution cycle runs, new strategy registered, backtest passes

---

## 3. EXECUTION RULES (Ponytail + RTK + Caveman)

1. **One fix per run.** Don't touch 5 files when 1 breaks the build.
2. **Real evidence only.** `File:line` or live endpoint. No "should work".
3. **Gate before deploy.** Strategy not walk-forward validated = not traded.
4. **Fail-closed.** Risk guard blocks by default. A guard that warns is dead.
5. **No mock.** Paper mode is for testing, not claiming "live".
6. **Parallel, not serial.** 7 profiles = 7 workers. Use them.
7. **No babysitting.** Cron runs autonomous. Human only for broker creds.

---

## 4. BLACKHORNET INTEGRATION

BlackHornet = colony orchestrator (PSO swarm, ABC role-switching).
**Role in QNA war:** Distributed strategy evolution + cross-agent signal voting.

- [x] BlackHornet startup wired (Hermes ecosystem, port 8080)
- [ ] Bridge: BlackHornet `EcosystemOrchestrator` → QNA `StrategyEvolver`
- [ ] BlackHornet `BHQuant` → QNA `RiskGuard` (shared veto)
- [ ] BlackHornet colony = 7 Hermes profiles (1:1 mapping)
- **Verify:** BlackHornet boots, `/api/v1/quant` returns QNA status

---

## 5. SUCCESS METRICS

| Metric | Target | Current |
|--------|--------|---------|
| Strategies registered | 200+ | 7 active + 64 archive (wired: 7) |
| Strategies gate-passing | 50+ | ~6 historical |
| MT5 connection | Live (real broker) | Valetax demo (IPC timeout) |
| Daily trades | 3-10 | 0 (SCAN-ONLY) |
| Risk guard | Fail-closed | Wired, needs live PnL |
| Profile crons | 7 healthy | 4 paused |
| BlackHornet bridge | Live | Startup wired |

---

## 6. IMMEDIATE ACTIONS (Next 24h)

1. **devbot:** Register 64 archive strategies → AutoRegistry returns 200+
2. **traderbot:** Run backtest on all 200 → `results/gate_status.json`
3. **autobot:** Resume 4 paused crons (scoped to QNA)
4. **traderbot:** Fix Valetax IPC → switch to Exness real broker
5. **clawbot:** Adversarial test risk guard (force daily loss → veto)
6. **hackerbot:** Security audit MT5 connector (cred handling)
7. **researchbot:** Walk-forward validation of gate-passing strategies
8. **fangbot:** OpenFang param optimization (Kelly, lot sizing)

**War starts now. No simulation. Real market. Autonomous.**
