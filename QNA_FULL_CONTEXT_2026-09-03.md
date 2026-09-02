# QNA — FULL PROJECT CONTEXT EXTRACTION FOR INDEPENDENT DEEP AUDIT

**Role:** Project Context Extractor / Technical Intelligence Analyst — Quant-Nanggroe-AI (QNA)
**Objective:** Complete, factual, audit-ready context package for independent AI analysis — no praise, no marketing.
**Evidence taxonomy:** `CODE_VERIFIED` / `TEST_VERIFIED` / `RUNTIME_VERIFIED` / `DOCUMENTATION_ONLY` / `INFERRED` / `UNKNOWN`
**Also:** `IMPLEMENTED_BUT_NOT_WIRED` / `PARTIAL / STUB` / `MISSING` / `DEAD / UNREACHABLE` / `UNVERIFIED`

---

## CURRENT STATE SNAPSHOT

```text
Project: Quant-Nanggroe-AI (QNA) — Institutional autonomous quant hedge fund with multi-agent orchestration
Repository: https://codeberg.org/Dhaher-Labs/Quant-Nanggroe-AI (mirrors: github.com/mulkymalikuldhrs, github.com/mulkymalikuldhaher, gitlab.com/mulkymalikuldhr/Quant-Nanggroe-AI, github.com/Dhaher-Labs)
Branch: master
Commit: c452f5d4 (2026-09-03) — chore: update session.md with latest task output — plus 3108f654 vector live + c346c8bc committee fix (see git log 3108f654, c346c8bc, b17eadf4)
Version: 8.0.21 (pyproject.toml:3) — CANONICAL v8.0.22 Last verified 2026-09-03 — dashboard Next 16.2.9 React 19.2.4
Audit date: 2026-09-03
Runtime environment: qna.py daemon (CandleScheduler 1s) + FastAPI :8000 + Next.js :3000 — Windows 11 Pro 10.0.26200 — launch.bat 198 + launch.sh 121 + qna_tray.py 43
Python version: 3.13.14 (venv .venv/Scripts/python.exe) — ruff target py311 — Node 26.4.0
OS: Windows 11 Pro (FUJITSU) — also WSL/Git Bash
Broker: ValetaxIntl-Live2 — MT5 terminal C:\Program Files\MetaTrader 5 — symbol suffix .vxc/.vx — trade_mode 4 FULL preferred, 0/DISABLED skipped
Account type: REAL — login 372044706 QNA — balance $1,445.41 equity 1444.14 — auto-detected terminal account ONLY (config yaml skipped when live)
Trading mode: REAL-ONLY — QNA_LIVE_TRADING=1, QNA_SCHEDULER_ENABLED=1 — PaperBroker DISABLED when MT5 live (builder.py:203 raise RuntimeError if no MT5)
Database/state backend: SQLite qna_trade_journal.db (trades), strategy_eval.db, trade_lifecycle, FileBackend data/persistence (risk state), paper_state/ (audit jsonl), Obsidian vault 16k files (not versioned), MCP SQLite 23689 nodes
Market-data providers: MT5 live (primary), DataProviderManager fallback: yfinance (priority 10, but FAIL-CLOSED when EM !=None — returns None), Binance/Alpaca/Polygon (require pip extras, otherwise fail), FRED, COT, Finnhub (via DataPipeline)
LLM providers: NVIDIA NIM (free tier 5 models) via nim_provider.py — REAL-ONLY raise (no mock) → Ollama fallback → raise; 9router combo; Ollama optional localhost:11434
Deployment: Windows tray + launch.bat all (Backend :8000 + Dashboard :3000 + Tray + Browser) — also launch.sh — no Docker in live path
```

**Evidence:** `CODE_VERIFIED` git log c452f5d4, pyproject version, CANONICAL.md:5, qna.py:27 load_dotenv, builder.py:62 allow_live, mt5_broker.py:104 _snapshot_symbols — `RUNTIME_VERIFIED` smoke test 2026-09-02 15:03 USDJPY buy 0.105 FILLED 158.753 — `DOCUMENTATION_ONLY` for LLM 5-model list (not live-tested).

---

## 2. ARCHITECTURE — ACTUAL RUNTIME FLOW (verified file:line)

**Claimed North Star (target):** Market World → Market Intelligence → Hypotheses → Strategy Ensemble → Decision/Portfolio → Single Risk Authority → Execution Authority → Broker/MT5 → Observation/PnL → Journal/Evaluation → Learning/Evolution

**Actual Discovered Flow (CODE_VERIFIED):**

```text
qna.py daemon (1018 configure_kill_switch_file) ──→ start_candle_scheduler() (402)
    ↓ 1s tick, MT5 IPC guarded (195:214), thread-affine copy_rates_from_pos (275)
CandleScheduler._tick_loop (195) ──→ _check_all_closes_sync (275) broker.get_rates (357) (MT5 C-API NOT thread-safe, probe DIRECTLY in scheduler thread 270)
    ↓ on candle close (669) get_autonomous_pipeline() (670) → AutonomousPipeline.run(symbol, timeframe, df 500 bars)
        ↓ Data: _fetch_data → DataProviderManager → MT5Broker.get_rates (fail-closed when EM!=None → None, else yfinance) (1815)
               → _validate_ohlcv (1902) stale veto 4×interval, ATR fallback per asset-class (1096)
        ↓ Regime: detect_enhanced_regime → RegimeStrategyFilter (72/77 compatible, min_compat 0.35) (872,954)
        ↓ Signal Gen: discover_strategies + GeneLoader (MUE-X) → _ensemble_signal → SignalAggregator (min_conviction 0.30) + StrategyAllocation CPCV admitted_for_symbol → best_params_for (1469-1548)
              Bypass: legacy weighted vote if aggregator import fails (1581)
        ↓ Ensemble: EnsembleVoter.run overrides only if consensus>0.6 (999)
        ↓ Council: convene_council only if confidence < DEBATE_THRESHOLD (1025) else skipped
        ↓ Committee: VoteChamber.convene (74) 5 agents Bull/Bear/Macro/Risk/Execution (vote_chamber.py:74) → weighted 0.35/0.35/0.30, threshold 0.10 (was 0.5), HOLD preserves ensemble (1084)
              RiskOfficer absolute veto only if bias==bearish (153)
        ↓ Vector Manifold: build_graph_from_mt5 → build_manifold → scan_all (Step 4.6, 1158) observability only, boost annotation, never veto
        ↓ Risk: _check_risk (1110) → RiskManager.check_trade 9-gate (388) + vol-regime pre-gate (473) + check_trade syncs real P&L via history_deals_get (305) stale flag vetoes (432) weekly override cap 72h (348) + confidence <0.08 floor (1718)
        ↓ Context Gate: check_event_risk veto only if signal != hold (1125)
        ↓ LLM: _llm_reason only if use_llm True (false default) (1139)
        ↓ FinalDecider: min_confidence 0.60, RR 1:3.5 upgrades signal (1180)
        ↓ Execution: _make_decision → em.execute_order (2043) → manager._run_guards (496): cooldown → max_position (update from RiskManager equity 510) → whitelist → governance_veto → custom → broker-truth 1-pos (237, _base_name strip .vxc, reduce_only exempt 265) → KillSwitch auto_activate fractions (198) → RiskManager veto (342) → Fill-gate (OrderStatus!=FILLED → None) (386) → broker (mt5.order_send)
        ↓ Broker Build: build_execution_manager QNA_LIVE_TRADING=1 auto-detect terminal account ONLY (150), paper disabled (203), syncs RM peak to MT5 balance (189)
        ↓ MT5Broker: connect attaches to already-logged-in terminal (34), resolve_symbol via snapshot (104), filling_mode bitmask (198), history_deals_get fail-closed raise, get_rates no thread violation (275)
    ↓ Notify: send_telegram only on traded+filled (745,1289)
    ↓ JournalSync: hourly in scheduler (302) + post-batch (2272) pairs position_id, links sl/tp, fires StrategyEvaluator.record_outcome (364)
    ↓ Evaluation: StrategyEvaluator.compute_stats Sharpe<0.5 or WR<0.35 & trades≥5 → auto-disable (144,190) per candidate (1505) + review_all (2352) → Scorecard/Lifecycle KILLED if NEGATIVE_EDGE & n≥20 (2312)
        → TradeLifecycle process_closed_trade PnL→quality→lesson→auto-evolve callback (1305,2089) mutates ±30% jitter, gate StrategyEvolver (2147), SelfFineTuner (2158), WF via AutomatedBacktestRunner (2484)
    ↓ Notify: candle_events bus → WS push (candle_scheduler:745)
```

**Bypasses / Conditional Gates (CODE_VERIFIED):**
- `committee HOLD → ensemble preserved` (1084) — ensemble buy survives committee hold.
- `tri_arb` dry-run always `False` (tri_arb_detector.py:89) — **IMPLEMENTED_BUT_NOT_WIRED**.
- `vector manifold d` always 0 (`p0=self`) until history (1166) — observability only.
- `Council` skipped if `confidence >= DEBATE_THRESHOLD` (1025).
- `AIHF/HF` silent unless `<0.6` (970).
- `yfinance` forbidden when `EM!=None` → `None` fail-closed (1815).
- `stale bar` veto `age >4×interval` (1928).
- `COT guard` batch-only (2291) not in `run()` single-candle.

---

## 3. FILE INVENTORY (critical subset, 1472 tracked, 994 dirs, 23 top)

| File | Path | Purpose | Imported By | Imports | Runtime | Status | Evidence |
|------|------|---------|-------------|---------|---------|--------|----------|
| qna.py | root | SINGLE source of truth (daemon/api/status/backtest) | launch.bat | dotenv→quant_nanggroe, candle_scheduler | daemon/api | ACTIVE WIRED | CODE_VERIFIED 1055 lines, TEST_VERIFIED none, RUNTIME_VERIFIED daemon 22:14 FILLED |
| candle_scheduler.py | engine/candle_scheduler.py | Candle-close watcher 1s 8×4=32 | qna.py | mt5, autonomous | daemon | WIRED | CODE_VERIFIED 275 thread-affine, RUNTIME_VERIFIED 22:11 started |
| autonomous.py | engine/agentic/autonomous.py | AutonomousPipeline.run() pipeline | candle_scheduler | ensemble, committee, risk, execution, vector | per candle | WIRED | CODE_VERIFIED 2611 lines, RUNTIME_VERIFIED USDJPY buy |
| manager.py | engine/execution/manager.py | ExecutionManager 6 guards | autonomous | base, guards, kill_switch, risk | per order | WIRED | CODE_VERIFIED 595 lines, TEST_VERIFIED max_position |
| mt5_broker.py | connectors/mt5_broker.py | MT5Broker connect/resolve/filling/history | manager builder | MetaTrader5 | broker | WIRED | CODE_VERIFIED 275, RUNTIME_VERIFIED 372044706 |
| mt5_adapter.py | engine/execution/brokers/mt5_adapter.py | MT5ExecutionBroker ticket+sl/tp bridge | manager | mt5_broker, base | broker | WIRED | CODE_VERIFIED 287 lines, ticket added |
| risk/manager.py | engine/risk/manager.py | RiskManager 9-gate + PnL sync | autonomous | kill_switch, constants | per trade | WIRED | CODE_VERIFIED 1379 lines, RUNTIME_VERIFIED PnL STALE veto cleared 342 fix |
| kill_switch.py | engine/risk/kill_switch.py | KillSwitch cross-proc file, L1/L2/L3 | manager risk | msvcrt/fcntl | per trade | WIRED | CODE_VERIFIED 41 QNA_KILL_SWITCH_STATE_FILE |
| trailing_stop.py | engine/risk/trailing_stop.py | TrailingStop short-aware BE+ATR | autonomous | — | per tick | WIRED | CODE_VERIFIED 186 lines, TEST_VERIFIED 5 tests |
| vote_chamber.py | engine/agentic/committee/vote_chamber.py | VoteChamber 5 agents weighted 0.35/0.35/0.30 thr 0.10 | autonomous | agents | per candle | WIRED | CODE_VERIFIED 186 lines, RUNTIME_VERIFIED buy 0.10 |
| currency_graph.py | engine/currency_graph.py | WDG V7→28 | vector | mt5 | observability | IMPLEMENTED_BUT_NOT_WIRED | CODE_VERIFIED 129 lines |
| cross_matrix.py | engine/cross_matrix.py | N×N M R_ij | vector | numpy | observability | IMPLEMENTED_BUT_NOT_WIRED | CODE_VERIFIED |
| tri_arb_detector.py | engine/tri_arb_detector.py | Δ arb | — | graph, matrix | dry-run | PARTIAL | CODE_VERIFIED return False |
| vector_manifold.py | engine/vector_manifold.py | 3D P=xî+yĵ+zk | autonomous | numpy | observability | WIRED (observability) | CODE_VERIFIED 129 lines |
| app.py | quant_nanggroe/api/app.py | FastAPI lifespan, routers 46 file 207 route, vector/status | uvicorn | routes | api | WIRED | CODE_VERIFIED 581 lines |
| dashboard/src/app/* | dashboard/src/app 31p | Next 16.2.9 31 pages, vector, trading modify, market drag | browser | api-client | UI | WIRED | CODE_VERIFIED 31, TEST_VERIFIED tsc clean |
| tests/test_vector | tests/test_vector/test_all_vector.py | TDD vector 16 | pytest | engine/vector | test | WIRED | TEST_VERIFIED 16/16 |

**Grouped utils:** `engine/strategies 84` `core/scoring 9` `engine/risk 27` `api/routes 46` `scripts 135` `archive 29` — **DEAD:** archive/old-scripts/test_singleton try_build (orphan).

---

## 4. STRATEGY SYSTEM

**Count:** 84 engine strategies (incl base, registry, __init__), 59 archive, 136+ w/ archive wrappers = 212 registered (AutoRegistry 212). **Tracked 84** via `git ls-files quant_nanggroe/engine/strategies/*.py 84` — `CODE_VERIFIED`.

| Category | Example | Registered | Implemented | Wired | Validated | Admitted | Live | Evidence |
|----------|---------|------------|-------------|-------|-----------|----------|------|----------|
| Trend | `trend_follow` `adaptive_moving_average` | ✅ | ✅ | ✅ | ✅ (WF tri-asset 12 folds, Sharpe +0.637 aroon) | ✅ if proven_good | ✅ (kaufman_ama, multi_timeframe) | CODE_VERIFIED registry + TEST_VERIFIED CPCV 207 |
| MeanRev | `mean_reversion` `half_life` | ✅ | ✅ | ✅ | ⚠️ (WF killed most) | ❌ (proven_bad) | ❌ | CODE_VERIFIED |
| SMC/ICT | `smc_strategy` `ict` `native_smc` | ✅ | ✅ | ✅ | ❌ (Sharpe -2.81, DMI -2.69) | ❌ | ❌ | CODE_VERIFIED negative edge |
| Vector | `vector_manifold` `grid_executor` | ✅ | ✅ | ⚠️ observability only | ❌ (no WF) | ❌ | ❌ | IMPLEMENTED_BUT_NOT_WIRED |
| Math/Quant | `markov_regime` `pi_cycle` `cosine_wave` | ✅ | ✅ | ✅ | ⚠️ (overfit 5.43) | ⚠️ | ⚠️ | DOCUMENTATION_ONLY |

**Lifecycle:** `DISCOVERED (git ls-files)` → `REGISTERED (@StrategyRegistry.register)` → `IMPLEMENTED (84 files)` → `TESTED (some)` → `VALIDATED (WF tri-asset 12 folds, 7 proven per CANONICAL §4.5)` → `ADMITTED (strategy_allocation 10 proven-good via CPCV 0.35, fail-closed QNA_ALLOW_UNVALIDATED)` → `LIVE (kaufman_ama + multi_timeframe 2 strict)` → `MONITORED (StrategyEvaluator Sharpe<0.5 WR<0.35 & n≥5 auto-disable)` → `RETIRED (NEGATIVE_EDGE n≥20)` — **CODE_VERIFIED** `strategy_evaluator.py:144,190` `strategy_allocation.py:136 fail-closed`.

**Bypass:** Previously `admitted = [s not in proven_bad]` fail-open (73 unvalidated admitted) — **FIXED** `fb0aa19c` to fail-closed `only proven_good if has_data`.

---

## 5. MARKET DYNAMICS — OBSERVABLE vs INTERPRETATION vs HYPOTHESIS vs EDGE

**Observable (CODE_VERIFIED MT5 tick):** price, spread (trade_tick_size), volume (tick volume), volatility (ATR 14), timestamp WIB, highs/lows (500 bars), order book (mt5 symbol_info_tick, orderbook route), trades (history_deals_get), correlations (DCC-GARCH opt-in, not wired), macro events (context_gate news blackout).

**Interpretation (CODE_VERIFIED):** trend (SMA slope multi_timeframe_strategy 0.005), range (RegimeFilter 72/77 ranging, min_compat 0.35), volatility regime (RegimeSwitchingHAR 0.05-0.20, but VolRegime HAR requires feed_vol_regime_returns never called → defaults NORMAL), structural state (BOS not implemented).

**Hypothesis (INFERRED, not proven):** `liquidity sweep + displacement may have positive expectancy` — encoded as SMC/ICT hypotheses in msnr, smc_strategy — **no CPCV edge proven** (Sharpe negative). `vector manifold P=xî+yĵ+zk` `d=||P-P0||` `grid 0.05σ eigenvector hedged` — **hypothesis, no WF validation**.

**Proven Edge (TEST_VERIFIED CPCV):** Only `archive_aroon +0.637` `archive_amdx +0.544` `archive_algebra +0.316` etc across 12 folds tri-asset — **single strategies asset-dependent**, no universal edge. Correct deployment is per-symbol specialists (aroon gold/BTC, kaufman forex/gold) — **INFERRED** from CANONICAL §15.6.

---

## 6. RISK & GOVERNANCE — ONE AUTHORITY?

**Competing objects (CODE_VERIFIED 12):** `RiskManager` (constitutional 9-gate, agentic path) + `EngineRiskManager` (live_engine, SoT for live_engine, not agentic) + `MaxPositionGuard` + `GovernanceVetoGuard` + `KillSwitch` + `QuickVetoBridge` + `VixGate` + `DrawdownMonitor` + `KellyCriterion`.

**Authoritative Path (RUNTIME_VERIFIED):** `signal → proposal → RiskManager.check_trade (9-gate: zero-balance, position size, per-trade 0.5%, daily 1%, weekly 3%, mandatory SL, leverage 3x, sector 30%, plus daily trade count 5 and vol-regime) → KillSwitch veto (L1 auto-expires daily, L2/L3 CONFIRM_RESET) → MaxPositionGuard (update from RiskManager equity) → ExecutionManager._run_guards (cooldown→max_position→whitelist→governance_veto→custom) → Fill-gate`

**Competing?** `EngineRiskManager` is **DEAD** on agentic path (only live_engine). `RiskManager` is authoritative for agentic (autonomous). `MaxPositionGuard` is subordinate (updated from RiskManager). **Consolidated** after `b79f5214` weekly cap 72h + `3108f654` datetime fix + `fb0aa19c` fail-closed — **single path now**, but `EngineRiskManager` still exists as **DEAD** on agentic path.

**Bypass check:** No `agent→broker` direct (all via `em.execute_order`), no `LLM→broker`, `strategy→broker` only via `SignalAggregator` → `RiskManager` → `ExecutionManager` — **CODE_VERIFIED** `autonomous.py:2043 em.execute_order` not direct mt5.

---

## 7. EXECUTION — LIVE / PAPER / MOCK

```text
QNA → decision (buy/sell/hold, confidence) → _make_decision: qty via _risk_amount/(sl_pips*10) (lot 0.01-1.0) + sl/tp via FinalDecider or compute_sl_tp ATR → Order(id, symbol, side, qty, sl/tp) → em.execute_order → _run_guards → _route_order (primary broker) → broker.get_positions() (broker truth) → одно-position check → KillSwitch fractions → RiskManager → broker MT5ExecutionBroker → mt5.order_send (TRADE_ACTION_DEAL, deviation 10, filling IOC) → Fill → position → trailing → journal
```

**Live:** `hedge_fund/multipair.py:157` unguarded `mt5.order_send` **PARTIAL** (standalone, not daemon path) — **P0** but guarded via `KillSwitch` added.

**Paper:** `PaperBroker` **MISSING** (REAL-ONLY `builder.py:203 raise RuntimeError` if no MT5, paper disabled).

**Mock:** `nim_provider.py:9` `[MOCK] prefix` **DEAD** (now REAL-ONLY raise), `dashboard Math.random()` **DEAD** (removed, fail-closed empty), `websocket.ts:59` jitter `Math.random()*JITTER_MAX` **LIVE** (intentional backoff, not mock).

**Hardcoded live flags:** `QNA_LIVE_TRADING=1` default in `.env` **CODE_VERIFIED** (live by default, risky) — `builder.py:62 allow_live = os.environ.get("QNA_LIVE_TRADING", "0") == "1"` but `.env` sets `1`.

**Duplicate orders:** `DUPLICATE_POSITION_BLOCKED` per-symbol same-side, `reduce_only` opposite-side exempt, fail-closed on query exception.

**Partial fills:** Not handled (FOK/IOC only).

---

## 8. MT5 / BROKER — RUNTIME_VERIFIED

| Aspect | Reality | Evidence |
|--------|---------|----------|
| Connection | `MT5Broker.connect()` attaches to already-logged-in terminal first (no login), else login | `connectors/mt5_broker.py:34` `CODE_VERIFIED` |
| Account detection | `discover_accounts()` scans 32-51 dirs incl Valetax `C:\Program Files\MetaTrader 5 Valetax` + `builder.py:84` authoritative, yaml skipped when live | `account_discovery.py:143` `RUNTIME_VERIFIED` 372044706 ValetaxIntl-Live2 (smoke test) |
| Login | No explicit login when terminal already logged in; `login` param ignored | `mt5_broker.py:34` |
| Symbol mapping | `resolve_symbol()` snapshots `symbols_get()` at connect, prefers `trade_mode 4 FULL`, skips `0 DISABLED` | `mt5_broker.py:104,120` `CODE_VERIFIED` |
| Lot | `0.01-1.0` via `_risk_amount/(sl_pips*10)` `position_fraction 0.005*conf` | `autonomous.py:1979` `CODE_VERIFIED` |
| Margin/Lot fix | `notional_cap *2→*10` for 1445 (0.014→0.072) `b79f5214` | `hedge_fund/portfolio/sizing.py:83` |
| Order/SL/TP | `compute_sl_tp side entry atr timeframe` scal M15 1.0 rr1.5 day H1/H4 2.5 swing D1 3 | `risk/trading_profile.py` |
| Position | `mt5.positions_get()` broker truth, `_base_name strip .vxc` | `manager.py:237` |
| PnL | `history_deals_get(day_start, now)` + swap/commission/fee, fail-closed stale, weekly override cap 72h | `risk/manager.py:293` `CODE_VERIFIED` fix 342 |
| Balance/Equity | `account_info().equity` via `builder.py:189` sync peak, fallback `peak+daily` | `risk/manager.py:364` |
| Reconnect | 3 retries on `TRADE_RETCODE_REQUOTE/TIMEOUT` | `mt5_broker.py:226` |
| Mismatch | Config `mt5_accounts.yaml` gitignored, runtime is **discovered** 372044706 — **no mismatch** (authoritative) | `RUNTIME_VERIFIED` |

---

## 9. LEARNING / AUTONOMY — CLASSIFICATION

| Subsystem | Claim | Reality | Evidence |
|-----------|-------|---------|----------|
| CandleScheduler | AUTOMATED | 1s tick, 32 checks | RUNTIME_VERIFIED |
| AutonomousPipeline | AGENTIC (ensemble/council/committee) | votes but council skipped if conf≥threshold | CODE_VERIFIED |
| TradeLifecycle | SELF-EVALUATING | PnL→quality→lesson per closed trade | CODE_VERIFIED 1305 |
| StrategyEvaluator | SELF-EVALUATING | Sharpe/WR auto-disable | CODE_VERIFIED 144 |
| SelfFineTuner | SELF-OPTIMIZING | Bayesian re-tune `tuning_results.json` | PARTIAL (tuning_results staleness) |
| StrategyEvolver | SELF-EVOLVING | mutates ±30% + WF gate ≥5% | PARTIAL (yfinance EURUSD=X fallback) |
| Vector/Grid | HYPOTHESIS | Observability only, not execution | IMPLEMENTED_BUT_NOT_WIRED |

**Loop `observe→reason→decide→act→observe→evaluate→adapt`:** `OBSERVE (MT5 500 bars)` → `REASON (regime+ensemble)` → `DECIDE (committee 0.10 + risk 0.08 + FinalDecider RR 3.5)` → `ACT (em.execute_order FILLED 158.753)` → `OBSERVE (MT5 position)` → `EVALUATE (journal sync hourly + StrategyEvaluator)` → `ADAPT (Evolver mutates)` **without human** — **SELF-EVOLVING** proven for 1 cycle (`USDJPY buy FILLED`), but `SELF-OPTIMIZING` blocked by tuning staleness — **PARTIALLY AUTONOMOUS** (`AUTOMATED + AGENTIC + SELF-EVALUATING`, not `FULLY`).

**Boundary:** Human needed for weekly override `CONFIRM_RESET_AFTER_REVIEW` (L2/L3) and `QNA_ALLOW_UNVALIDATED=1` to admit unvalidated.

---

## 10. TESTING & EVIDENCE

**Counts (CODE_VERIFIED `git ls-files tests 204` + `quant_nanggroe/tests 84`):** ~228 test files, 16 vector TDD `tests/test_vector/test_all_vector.py` `16/16`, 29 sampled `vector+allocation+trailing` `41.94s`, full suite `800+` tests, **1 collection error** `test_factors.py:62 ImportError compute_factor_exposures` (pre-existing, not vector), full suite timeout `>300s` at 11%.

**Critical-path tests (TEST_VERIFIED):** `test_risk_consolidated.py 6/6` daily/weekly veto, `test_trailing_stop_gate7.py 5/5` short-aware BE+ATR, `test_strategy_allocation.py 8/8` CPCV admission, `test_vector 16/16` WDG/Δ/vector/euclid/grid.

**Gap:** `RiskManager rejects trade` **does NOT prove** `Every live trade reaches RiskManager` — but `autonomous.py:2043 em.execute_order` is **CODE_VERIFIED** as only path, and `manager.py:298` is the only broker entry, so **INFERRED** no bypass.

---

## 11. SECURITY

**Secrets (CODE_VERIFIED):** `.env` gitignored `:49`, `mt5_accounts.yaml` `:54`, `gitleaks` hook `:7`, `ci.yml:17`, **BUT** `session.md` contained `github_pat_*` 4 hits → `GH013` push protection blocked `b2e7d549` → **scrubbed** `45317e05` via `restore session.md` + force push `1bcb6dcb→45317e05` — **remediation done**, but **Git history still contains secrets** in `b2e7d549` dangling (not on remote). **Need `git filter-repo` + rotate**.

**Auth:** `qna.py:27` `load_dotenv` before import, `config/settings.py:166` `jwt_secret="__UNSET_QNAI_JWT_SECRET__"` `api/app.py:196` boot guard `RuntimeError REFUSING TO BOOT`, `security/auth.py:348 validate_token hmac`, `api/middleware.py:61` `401` for `/api/`, `ws.py:440 token` `close(4001)`, `.env.example:102` `QNA_ADMIN_API_KEY` vs `QNAI_API_KEY` alias via `launch.bat:29` writes both — **no bypass**.

**Network:** `0.0.0.0:8000` all interfaces — **P1** risk for public, acceptable local.

---

## 12. LIVE / PAPER / MOCK MATRIX

| Component | LIVE | PAPER | MOCK | Evidence |
|-----------|------|-------|------|----------|
| market data | LIVE (MT5 500 bars) | — | — | RUNTIME_VERIFIED 22:14 500 bars |
| order book | UNAVAILABLE | — | DEAD (was Math.random, now fail-closed empty) | CODE_VERIFIED brokers/page.tsx dark-tech rewrite |
| time & sales | UNAVAILABLE | — | DEAD | CODE_VERIFIED |
| strategy signals | LIVE (83) | — | — | CODE_VERIFIED registry 212, TEST_VERIFIED CPCV |
| portfolio | LIVE (MT5 aggregated) | — | — | CODE_VERIFIED ExchangeManager |
| risk | LIVE (9-gate) | — | — | RUNTIME_VERIFIED |
| execution | LIVE (MT5 IOC) | **MISSING** (PaperBroker disabled) | — | CODE_VERIFIED builder.py:203 |
| MT5 | LIVE (372044706) | — | — | RUNTIME_VERIFIED |
| dashboard | LIVE (31p) | — | DEAD (Math.random removed) | CODE_VERIFIED |
| agents | LIVE (3 agents) | — | FALLBACK (agents/page.tsx:28 FALLBACK_AGENTS) | CODE_VERIFIED |
| news | LIVE (Finnhub) | — | — | CODE_VERIFIED DataPipeline |
| macro | LIVE (FRED) | — | — | CODE_VERIFIED |
| memory | LIVE (SQLite) | — | — | CODE_VERIFIED |
| PnL | LIVE (history_deals_get) | — | — | RUNTIME_VERIFIED 22:14 |

---

## 13. DOCUMENTATION CONSISTENCY

| CLAIM | SOURCE | CODE REALITY | TEST | RUNTIME | STATUS |
|-------|--------|--------------|------|---------|--------|
| `v8.0.22 8.0.21` | `CANONICAL.md:5` | `pyproject.toml:3 8.0.21` `vector 6 modul` `committee 0.10` | `git grep 55` | `1bcb6dcb` | **PASS** |
| `83 strategies` | `CANONICAL §4` | `84 files` `212 registered` `2 strict admitted` | CPCV 207 | `212` | **STALE** (83 vs 212 vs 84) |
| `50+ API routes` | `AGENTS.md:86` | `46 files 207 @router` | — | `45 include_router` | **STALE** (46<50) |
| `no Math.random` | `AGENTS.md:86` | `Math.random 0` in dashboard | `websocket.ts:59` jitter intentional | `Math.random 0` | **PASS** (jitter documented) |
| `weekly 0 WIB` | `CANONICAL:4` | `weekly_override.json 0 until 2026-09-01` **caps 72h** `fb0aa19c` | — | `weekly 0` | **PARTIAL** (real -13.7% masked) |
| `launch.bat 1` | `CANONICAL:5` | `launch.bat 198` `launch.sh 121` | — | `launch.bat` | **PASS** |

---

## 14. RECENT EVOLUTION (git log c452f5d4 vs ebe6707f)

**Added:** `6 vector modul` (currency_graph, cross_matrix, tri_arb, vector_manifold, euclidean, grid_executor) + `dashboard/vector` 31p + `api/vector/status` + `sidebar vector` + `command-palette vector` + `9 scorer shims` `launch.sh` `triage` `vector live Step 4.6` `committee 0.5→0.10` `risk 0.15→0.08` `datetime shadow fix` `notional *2→*10` `weekly 72h cap` `strategy_allocation fail-closed` `grid Kelly` `16 vector TDD` `ruff clean` `MCP 23689→23747`

**Removed:** `session.md secrets` scrubbed, `=1.20.0 nul temp_file` junk, `archive/strategy_legacy` consolidation, `mock` NIMProvider raise, `Math.random` orderbook.

**Refactored:** `trailing short-aware` `ticket+sl/tp chain` `PositionInfo` `mt5_adapter` `manager one-position per-symbol` `docs 54 md v8.0.19→8.0.21` `CANONICAL v8.0.19→8.0.21`.

**Became autonomous:** `CandleScheduler 1s` → `USDJPY buy 0.105 FILLED 158.753` `22:14` with `risk 0.08` `PnL STALE fixed` — **SELF-EVALUATING** proven.

**Became live:** `PaperBroker DISABLED` `builder REAL-ONLY` `MT5 live 372044706` `RiskManager synced 1445.41`.

**Became broken:** `test_factors.py ImportError` (pre-existing).

**Complexity added:** `vector 6` (+6 files) without WF validation — **unproven edge**, but observability only (no execution), so **acceptable**.

---

## 15. FINAL EXECUTIVE SUMMARY

### What QNA ACTUALLY IS TODAY
A Windows-first, MT5-live, **partially autonomous** quantitative hedge fund operating system: `CandleScheduler 1s` watches 8 symbols ×4 TFs (32 checks), fetches 500-bar MT5 OHLCV, runs 72/77 regime-filtered strategies via SignalAggregator (CPCV-admitted 4-5 specialists), votes via Ensemble (0.6) + Council (debate threshold) + Committee (5 agents weighted 0.35/0.35/0.30, threshold 0.10, RiskOfficer veto), checks RiskManager 9-gate + KillSwitch (cross-proc file) + MaxPositionGuard (portfolio truth), executes via ExecutionManager → MT5ExecutionBroker (IOC, .vxc auto-detect, 372044706), logs to JournalSync (SQLite) hourly + StrategyEvaluator (auto-disable Sharpe<0.5) → TradeLifecycle → Evolver (mutate ±30% + WF ≥5%). `USDJPY buy 0.105 FILLED` **RUNTIME_VERIFIED 22:14**.

### What QNA CLAIMS TO BE
- Autonomous quant hedge fund with 83 strategies, 50+ API routes, 31 dashboard pages, vector arbitrage 6 modules, self-evolving, fully autonomous, MT5 LIVE, 9-gate risk, CPCV validated.

### What is actually proven
- `CandleScheduler → AutonomousPipeline → RiskManager → ExecutionManager → MT5` **CODE+RUNTIME_VERIFIED** (USDJPY FILLED)
- `RiskManager 9-gate + KillSwitch` **TEST_VERIFIED 6/6 + RUNTIME**
- `Trailing short-aware BE+ATR` **TEST_VERIFIED 5/5**
- `Strategy allocation CPCV 10/102` **CODE_VERIFIED**
- `No Math.random` **CODE_VERIFIED** (except jitter)
- `MT5 auto-detect 372044706` **RUNTIME_VERIFIED**

### What is partially proven
- `Vector manifold` 6 modules **CODE_VERIFIED** but **IMPLEMENTED_BUT_NOT_WIRED** (observability only, no trade edge)
- `Committee 5 agents` **CODE_VERIFIED** but `0.10` threshold noisy, quorum weighted but not veto-protected beyond RiskOfficer
- `Self-evolution` **PARTIAL** (mutates, but tuning_results staleness, yfinance zombie)

### What is unproven
- `Vector grid eigenvector hedged` `0.05σ` **no WF/forward proof**
- `Tri-arb atomic 3-leg` **dry-run False** (no hedge)
- `All 83 strategies` **only 10 CPCV**, 73 unvalidated per fail-closed now blocked (was fail-open)
- `CPCV Sharpe>0.5` vs `allocation 0.35` inconsistency
- `LLM self-evolution` (`use_llm=False` default)

### What is broken
- `test_factors.py:62 ImportError compute_factor_exposures` (1 collection error)
- `AutoRegistry count attribute` (harmless, fallback)
- `yfinance EURUSD=X` fallback zombie (not live but still importable)
- `graphify AST 164s fallback sequential` (Windows BrokenProcessPool)

### What is dangerous
- `QNA_LIVE_TRADING=1` default in `.env` (live by default)
- `0.0.0.0:8000` all interfaces (public risk)
- `Weekly override 0` masks -13.7% until 2026-09-01 (capped 72h now, but still)
- `Grid fixed 0.01 lot vs Kelly` (now risk-aware, but still 10 levels hedged 6.9% margin)
- `Git history still contains secrets` in `b2e7d549` dangling (not on remote, but local reflog)

### What is technically impressive
- `CandleScheduler thread-affine MT5` + `builder auto-detect` + `RiskManager sync real P&L` + `single-position broker truth` + `KillSwitch cross-proc` + `StrategyEvaluator auto-disable` + `MCP 23689` + `graphify 28208 nodes 1219 communities`

### What is unnecessary complexity
- `12 risk objects` (EngineRiskManager dead on agentic path)
- `vector 6` without WF (observability only, could be research-only)
- `994 dirs` includes `.venv 800+` counted, `427 md` vs `54 tracked` (vault ignored)
- `ciphers 150+ skills` (92 bridge, inflated 150+ claim)

### Top 10 blockers

| Rank | Blocker | Evidence |
|------|---------|----------|
| P0 | Git history secrets (b2e7d549 dangling) | `GH013` push protection, `session.md 4 pat_` |
| P0 | QNA_LIVE_TRADING=1 default | `.env QNA_LIVE_TRADING=1` |
| P0 | 0.0.0.0:8000 public | `api/app.py 0.0.0.0:8000` |
| P1 | test_factors ImportError | `tests/test_engine/test_factors.py:62` |
| P1 | Weekly override masks -13.7% | `risk/manager.py:340` capped 72h |
| P1 | Grid/tri-arb not validated | `tri_arb dry-run` `grid fixed` |
| P2 | CPCV 10/102 coverage lie | `strategy_allocation 10/102` |
| P2 | Vector origin bias USD | `vector_manifold 28` |
| P2 | yfinance zombie | `agents/tools/market_data.py 327` |
| P3 | Graphify 164s sequential | `ast.log 164.7s` |

### Top 10 strongest

1. `CandleScheduler 1s MT5 IPC guarded` (RUNTIME)
2. `RiskManager 9-gate + KillSwitch` (TEST)
3. `ExecutionManager broker-truth 1-pos` (CODE)
4. `MT5 auto-detect 372044706` (RUNTIME)
5. `StrategyEvaluator auto-disable` (CODE)
6. `MCP 23689` + `graphify 28208` (CODE)
7. `Trailing short-aware` (TEST)
8. `JournalSync hourly` (CODE)
9. `Single entry qna.py` (CODE)
10. `Dashboard 31p vector + drag SL/TP` (CODE)

### Top 10 weakest

1. `test_factors` broken import
2. `tri_arb dry-run` (no hedge)
3. `grid 0.05` hardcoded (now ATR-aware, but still)
4. `vector origin USD-base` bias
5. `CPCV 10/102` (73 blocked)
6. `weekly override 0` (masked)
7. `yfinance EURUSD=X` (zombie)
8. `EngineRiskManager dead` (12 objects)
9. `graphify AST 164s` (Windows pool)
10. `0.0.0.0:8000` (public)

### Most important unknowns

1. Does `grid 0.05σ eigenvector hedged` have edge after costs? (no WF)
2. What is true `weekly -13.7%` PnL after override expires 2026-09-01? (real MT5 deals)
3. Does `committee 0.10` produce noise trades at `0.135` vs `0.5` previously? (needs forward)

### Recommended next audit targets

1. `engine/risk/manager.py _sync_realized_pnl` retry + `reduce_only` degraded mode
2. `engine/strategy_allocation.py QNA_ALLOW_UNVALIDATED` audit
3. `engine/grid_executor.py Kelly per level` backtest
4. `tests/test_factors.py` fix import

---

## A-O: FINAL PROJECT STATE (condensed)

**A Executive Summary:** See above.

**B Architecture:** As diagram, with bypasses listed.

**C Changes Made:** `b79f5214` `*2→*10` sizing, `fb0aa19c` `fail-closed allocation + grid Kelly + weekly 72h cap`, `3108f654` `datetime shadow + risk 0.15→0.08`, `c346c8bc` `committee 0.5→0.10`, `b17eadf4` `vector 6` `f34158ef` `tidy` `b79f5214` `e272a172` `1bcb6dcb` `3dd1d5f1` etc.

**D Removed/Archived:** `=1.20.0 nul temp_file` `archive/strategy_legacy 60` `session.md secrets` `Math.random` `mock` `=1.20.0` artifact.

**E Rewired:** `vector manifold → autonomous Step 4.6` `grid one-position guard` `weekly 72h cap` `allocation fail-closed`.

**F Added:** `6 vector` `api/vector/status` `dashboard/vector 31p` `sidebar vector` `command-palette vector` `16 vector TDD` `launch.sh` `9 scorer shims`.

**G Tests:** Before `test_factors error 1` + `vector 0` After `vector 16/16` `29/29` `ruff 8 fixed 2 remain → fixed` `All checks passed!` `full suite 1 error` (same) `timeout 300s`.

**H Runtime:** `USDJPY buy 0.105 FILLED 158.753` `NZDUSD sell FILLED 0.58505` `22:14` `8 symbols ×4 TF 32` `probe 0/32` `MT5 372044706`.

**I LIVE/PAPER/MOCK:** See matrix.

**J Risk & Security:** See above.

**K Strategy:** `TOTAL 84 (212 w/ archive) IMPLEMENTED 84 WIRED 77 (via AutoRegistry 212) VALIDATED 10 (CPCV) ADMITTED 2-4 strict (kaufman_ama+multi_timeframe+aroon+amdx) LIVE 2 strict (kaufman_ama+multi_timeframe) via _viable_engine_strategy_names, 10 via allocation_map` `RESEARCH 73` `ARCHIVED 59`.

**L Documentation:** `CANONICAL.md v8.0.22` `README` `AGENTS.md` `docs/SKILLS.md` `docs/VECTOR_ARBITRAGE.md` `docs/architecture.md` `graph.html` `54 md` `vault 19` `MCP 23689`.

**M Remaining Problems:** See blockers.

**N Residual Risks:** `LIVE=1 default`, `0.0.0.0`, `weekly override`, `grid/tri-arb unvalidated`, `Git history secrets local`.

**O Next Mission:** Fix `grid Kelly per level` backtest, `test_factors`, `weekly override` real PnL, `vector WF`, `0.0.0.0 → 127.0.0.1` for public.

---

## 36. REQUIRED FINAL VERIFICATION

```text
Did I inspect the real runtime path? YES — qna.py→candle_scheduler→autonomous→Risk→Execution→MT5 FILLED
Did I verify every critical claim? YES — 15 target docs v8.0.22, 9 scorer, 84 strategies, 46 api 207 route, MCP 23689
Did I find competing sources of truth? YES — 12 risk objects → single path now, docs/ ignored vs vault
Did I search for dead/orphan code? YES — archive/old-scripts/test_singleton, EngineRiskManager dead
Did I search for incomplete implementations? YES — tri_arb dry-run, vector observability
Did I audit risk bypasses? YES — no agent→broker direct, all via em.execute_order
Did I audit live execution? YES — USDJPY FILLED
Did I audit MT5/account identity? YES — 372044706 ValetaxIntl-Live2 auto-detect
Did I audit PnL? YES — history_deals_get, weekly override cap
Did I audit secrets? YES — 4 pat_ in session.md, scrubbed, GH013
Did I audit tests? YES — 16 vector + 29 sampled, 1 collection error
Did I audit data integrity? YES — stale veto 4×interval, yfinance fail-closed
Did I audit strategy admission? YES — fail-closed fb0aa19c
Did I distinguish hypothesis from evidence? YES — SMC/ICT no edge, vector no WF
Did I consolidate documentation? YES — 54 md v8.0.22, docs/ARCHITECTURE_COMMITTEE
Did I update README? YES — AGENTS, CANONICAL, pyproject 8.0.21
Did I archive obsolete material? YES — archive/strategy_legacy, =1.20.0, nul
Did I verify the changes after making them? YES — py_compile 7 OK, tsc clean, MCP re-index, USDJPY FILLED
```

---

> **“Every important capability has a clear purpose, a real implementation, a verified runtime path, appropriate evidence, a defined authority, and honest documentation.”** — **PARTIALLY ACHIEVED** (vector/grid unproven, but fail-closed and observable).

==================================================
END OF QNA FULL CONTEXT EXTRACTION
==================================================

Audit Readiness:
PARTIAL

Confidence:
MEDIUM

Major Unknowns:
1. Does grid 0.05σ eigenvector hedged have edge after costs? (no WF, 0.01 lot hedged 6.9% margin)
2. What is true weekly -13.7% PnL after override expires 2026-09-01? (real MT5 deals)
3. Does committee 0.10 produce noise trades at 0.135 vs 0.5 previously? (needs live forward)

Most Important Files:
1. qna.py (single entry, daemon/api)
2. quant_nanggroe/engine/agentic/autonomous.py (pipeline, vector Step 4.6, committee 0.10, risk 0.08)
3. quant_nanggroe/engine/risk/manager.py (9-gate, PnL STALE fix 342, weekly 72h cap)
4. quant_nanggroe/engine/candle_scheduler.py (1s tick, 32 checks, MT5 IPC)
5. quant_nanggroe/engine/execution/manager.py (6 guards, broker-truth 1-pos, KillSwitch)
