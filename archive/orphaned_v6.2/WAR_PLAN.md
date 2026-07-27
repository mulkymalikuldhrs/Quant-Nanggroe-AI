# QNA — Autonomous Quant Hedge Fund: Real-Market War Plan
**Version:** 1.2 (War Ready) | **Date:** 2026-07-27 | **Author:** Dhaher Labs
**Status:** EXECUTE — execution/risk system hardened, circuit breaker deployed, audit trail live

---

## 0. DIRECTIVE
"Make our Autonomous Quant Hedge Funds come true." — Mulky (2026-07-25)

QNA is NOT a research toy. It is a production autonomous hedge fund that:
1. Runs 24/7 via Hermes profile crons (all 7 profiles, parallel)
2. Generates signals from 200+ providers + **real quantitative alpha engines**: DCC-GARCH, Causal Macro, COT, MSI, SMT
3. Passes gate (Sharpe > 0.5, Return > 0%, DD > -25%)
4. Executes to MT5 (Valetax demo → real broker)
5. Self-evolves, self-corrects, self-heals — no human babysitting

---

## 1. CURRENT STATE (Verified 2026-07-27)

| Component | Status | Evidence |
|-----------|--------|----------|
| **DCC-GARCH correlation** | ✅ 47 tests | Dynamic cross-asset, auto-fit in live_engine |
| **Causal Macro Engine** | ✅ 5 modules | Bias, MSI (FRED), COT (CFTC), SMT, Thesis Drift |
| **Causal Bias → Signal** | ✅ All providers | boost/reduce/block on 10 core + 200+ evolved |
| **MT5 connector** | ✅ EXISTS + circuit breaker | `quant_nanggroe/connectors/mt5_broker.py`, `mt5_adapter.py` with CB 5-fail/60s/5min recovery |
| **MT5 Symbol Mapping** | ✅ SYMBOL_MAP | `constants.py` dict for 18 pairs — no more naive `.replace()` |
| **Risk guard** | ✅ DCC-GARCH + Thesis Drift + Circuit Breaker | Daily/weekly veto, fail-closed kill switch w/ audit trail |
| **Execution Manager** | ✅ Public API sealed | No private `_brokers`/`_mt5` access from builder or live_engine |
| **Backtest engine** | ✅ EXISTS | `scripts/backtest_dhaher_sltp.py` |
| **Strategy registry** | ✅ EXISTS | AutoRegistry |
| **Strategies** | ✅ 79+ registered | + causal bias filtering on all providers |
| **API server** | ✅ EXISTS | `quant_nanggroe/api/app.py` |
| **Kill Switch** | ✅ Force override + audit trail | Append-only JSONL, cooldown bypass for emergency |
| **Paper Broker** | ✅ Deterministic | Seeded RNG (42) for reproducible tests |
| **Cron runner** | ⚠️ Needs update | Must point to live_engine.py |
| **Profile crons** | ⚠️ PAUSED | 4 pollution crons paused |

**Gap to war:** archive strategies not registered, real MT5 not connected (Valetax IPC timeout), risk guard PnL verified via real MT5 history_deals_get (not phantom) — confirmed alive on Path-A and Path-B. WEEKLY veto ABSENT on both paths (P1 priority).

---

## 2. WAR PHASES

### PHASE 1 — Wire All Strategies (P0)
**Goal:** AutoRegistry discovers ALL 200+ strategies (active + archive).
- [x] AutoRegistry v2 scans `quant_nanggroe/engine/strategies/` + `archive/`
- [x] Register 64 archive-only strategies — AutoRegistry v3 auto-discovers ALL archive subpackages (135 archive classes wired; manual `archive/__init__.py` re-export OBSOLETE)
- [x] Verify: `list_strategies()` returns 208 entries (2026-07-26 cron) — goal ≥200 MET
- [x] Fix: archive strategies import `Strategy` base correctly — all 208 registered classes instantiate; only non-strategy cruft (`examples`, `old-database-root`, `old-strategies`, `web_interface`) has isolated import errors, none affecting registered set
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
- [x] **Wire `_trigger_evolution` to real backtest** — v6.2.0: `_real_backtest()` uses `WalkForwardAnalyzer.analyze_strategy()` with real strategy instantiation (no more mock jitter)
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
| Strategies registered | 200+ | 79+ canonical + legacy bridge |
| Risk guard | Fail-closed | Wired, v6.2.0: `set_broker_handle()` fixed, PnL fractions unified, real PnL connected |
| Strategy evolver | Real backtest | v6.2.0: `WalkForwardAnalyzer.analyze_strategy()` — mock removed |
| SSL verification | Env-guarded | v6.2.0: `QNAI_SSL_VERIFY` across 10 files |
| Credentials | Env vars only | v6.2.0: `.secrets-local/` deleted, YAML deprecated |
| PnL units | Unified fractions | v6.2.0: RiskManager + KillSwitch both use 0-1 |
| Exec bridge | Public API | v6.2.0: `ExecutionManager.set_broker_handle()` |
| Causal wiring | Dataclass | v6.2.0: `CausalContext` replaces env vars |
| Strategies gate-passing | 50+ | ~6 historical |
| MT5 connection | Live (real broker) | Valetax demo (IPC timeout) |
| Daily trades | 3-10 | 0 (SCAN-ONLY) |
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
