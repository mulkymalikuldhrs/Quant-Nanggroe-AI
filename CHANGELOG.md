# Quant Nanggroe AI — Changelog

> **SSOT:** `CANONICAL.md` v8.1.3 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, launch.bat 1, manager.py WIB

## v8.1.3 — P0+P1 hygiene + committee UI + quarantine + CI (2026-09-04)

CANONICAL §15.15 is the SSOT detail. Commit `b6485317` (60 files, 5 workstreams).

- WS1 hygiene: duplicated `_overrides` block removed (`execution/manager.py`); `risk_config.py` docstring corrected (minRR/correlated non-editable); CANONICAL header date bumped; `@radix-ui/react-progress` purged from `package.json` + both lockfiles.
- WS2 committee floor UI: `minCommitteeConfidence` in settings (load/save/clamp 0.05–0.65, fallback 0.10) + perRegime option; `tests/test_agentic/test_committee_floor_ui.py` 3/3; default behavior unchanged.
- WS3 quarantine: 6 verified-dead scripts → `archive/scripts_rot_2026-09-05/` + README ledger; 16 candidates kept as needs-manual-review; `renew_docs.py` SDK snippet fixed.
- WS4 CI+store: `ci.yml` covers `quant_nanggroe/tests` + tsc step, pip-vs-uv noted; `store.ts` dead slots removed, defaults EURUSD/mt5 (fixtures synced, vitest 28/28); `qna web` help marked [BROKEN — web_interface/ missing].
- WS5 docs: CHANGELOG v8.1.2 entry + CANONICAL §15.14 (both document parent `03f4ccfb`, 17 files) + versions 8.1.2 (pyproject+qna+pkg) + 80-file footer bump, all code-verified.
- Verification: 256 passed + 8 xfailed; tsc clean; py_compile clean.

---

## v8.1.2 — Residual gaps closed (N1–N8) + committee floor + CPCV trade stats (2026-09-04)

CANONICAL §15.14 is the SSOT detail. Commit `03f4ccfb` (17 files, 5 workstreams).

### 🔌 N1 metadata contract — perStrategy/perRegime live-fill was dead (HIGH)
- Writer: `_make_decision` gains `strategy` param (`autonomous.py:1962`); live-fill `Order.metadata` now sets `strategy` + `strategy_name` (compat) + `regime`, resolved as `strategy or decision.strategy_name or final_decider.strategy or "ensemble"`. Trailing-stop + main exec callsites pass it through.
- Reader: new `metadata_overrides()` (`execution/manager.py:37`) — `strategy` with `strategy_name` legacy fallback, `regime` direct; non-dict/missing → `None` (global defaults apply, fail-closed, never fabricated). `execute_order` forwards the overrides into `check_trade` (`execution/manager.py:369-383`).
- Pin: `tests/test_execution/test_metadata_forwarding.py` — 6 tests (new-key, legacy fallback, new-wins, missing fail-closed, 2 async forwarding).
- Repair: `SyntaxError` in the `execution/manager.py` override block fixed — module compiles, collection unblocked (`py_compile` clean, verified).

### 🗳️ Committee floor — UI-tunable, fail-closed
- `minCommitteeConfidence` in `risk_config.py` (defaults, `risk_config.py:46`; range 0.05–0.65, `_LIMITS`; default 0.10 = legacy `CONFIDENCE_THRESHOLD`); global + per-axis via `get_effective_config`.
- `resolve_committee_threshold()` (`vote_chamber.py:32`) — any error/missing/out-of-range value falls back to 0.10; wired into the buy/sell direction gate. Constitution cites 0.65 — deliberately NOT raised blindly (would halt trading); tune via UI with data instead.
- Pin: 3 new tests in `tests/test_agentic/test_committee_weights.py` (default unchanged, custom blocks weak vote, invalid falls back).
- UI note: `/vector` page renders `warming_up`/`p0_source`/`history_len`/`reason` (`vector/page.tsx`); dead `ui/progress.tsx` deleted (0 importers, verified); trading-page comment corrected to REAL-ONLY no-data guard.

### 📊 CPCV writer extension + full re-run (win_rate stays TBD)
- `build_cpcv_entry()` (`run_cpcv_validation.py:70`) extended fail-soft with `total_trades` (from `oos_trades`), `avg_oos_return`, `max_oos_dd` (worst = min, ≤0 convention), `win_rate` (from `win_rate`/`oos_win_rate` when present, else `None` — never invented). Pre-existing keys byte-identical.
- Pin: `tests/test_cpcv_registry_writer.py` — 5 tests.
- Re-run outcome: 10 strategies / 29 legs rewritten, zero data loss; `win_rate` is `null` on all 29 legs (verified by script against `data/cpcv_registry.json`) — `WalkForwardResult` carries no per-window win_rate, so ALPHA WinRate stays `TBD (FASE 4)` with dated citation (`docs/ALPHA_EVIDENCE.md`).
- ALPHA reword: FASE-4 bar is now `min_sharpe > 0` on every leg (was worst-combo-avg wording); all-zero legs (`archive_amdx`/`archive_wyckoff` EURUSD) noted as no-data sentinels; `native_smc` has no EURUSD leg.

### 🔒 N4/N5/N6/N8 pins (`tests/test_risk/test_governance_refresh.py` — 9 tests)
- N4: `GovernanceVetoGuard._refresh_limits()` (`veto_guard.py:82`) re-reads live `_risk_constants` module attributes on every `check()` (`veto_guard.py:104`); broken config keeps construction-time values (fail-closed).
- N5: `KillSwitchConfig.auto_max_drawdown_pct` derived `0.8 * MAX_DRAWDOWN_PCT` via `default_factory` (`kill_switch.py:185`) — live value at instantiation, so UI hot-reloads propagate to NEW instances only; pre-existing instances keep their stored value.
- N6: `minRiskReward`/`maxCorrelatedPositions` deliberately NOT live-editable — no live enforcement point (consumers read module constants; `checks.py evaluate` enforces only the forwarded size/loss keys). PUT writes rejected 400 (`_NON_EDITABLE_KEYS`, `risk_config.py`); file values fall back to defaults; per-symbol overrides inert.
- N8: `check_cost_affordable` documented accounting-only (`manager.py:1424` docstring) — pure, no state mutation, no halt coupling, no callers in the execution path (pinned by test).

### ✅ Verification
- `py_compile` clean on all touched risk/execution/committee/config/CPCV modules (verified). Coordinator battery per commit message: 78 passed + 5 xfailed — see commit `03f4ccfb`.
- No `TBD` claimed done: the only remaining `TBD` is ALPHA WinRate, explicitly still pending analyzer win-rate propagation.

---

## v8.1.1 — Docs sync + strategy test/API rewrite + risk_reward fix (2026-09-04)

CANONICAL §15.13 is the SSOT detail.

### 🧪 Strategy tests green (was: 48 pre-existing failures)
- `test_crypto_specific.py` rewritten to shipped API → **12/12 pass**.
- `test_pairs_trading.py` (old, fictional API) deleted; `PairsTradingStrategy` exists via shim → canonical `PairsTradeStrategy` (`name = "pairs_trade"`); `test_pairs_trading_comprehensive.py` rewritten → **12/12 pass**.

### 🔧 `risk_reward=` silent-drop fixed (17 sites, 14 files)
- `StrategySignal` has no `risk_reward` field — pydantic silently dropped it → all directional signals carried `risk_reward_ratio = 0.0`. Fixed to `risk_reward_ratio=` across pairs_trade + 13 strategy files. Pinned by RR assertion. Compile OK 14 files; strategy tests 24/24.

### 📝 Docs synced
- §15.12 COT verdict corrected (cot.py archived; cot_provider LIVE, do not archive).
- ALPHA_EVIDENCE FASE-4 table: 0/10 pass strict bar; nothing promoted.
- Lockfiles synced; `tsc` clean.

### ✅ Verification
- Strategy 24/24, test_risk 169+8xf, fill-ticket 2/2, cot_guard 7/7, correlations 58/58, `tsc` + `py_compile` clean.

---

## v8.1.0 — Full-Spectrum Pass: risk truth + API wiring + docs truth + self-evolve READY (2026-09-04)

Six parallel workstreams, one commit. CANONICAL §15.12 is the SSOT detail.

### 🔴 Risk truth (P0 — WS-A, all CLOSED)
- **G1 CLOSED:** effective 4-axis limits forwarded into `check_gate.evaluate()` (fraction→percent); empty config → legacy path.
- **G3 CLOSED:** thresholds read via `_risk_constants.<NAME>` module attribute; stale import-time bindings removed from live path.
- **Latent UnboundLocalError FIXED** (`manager.py` override block) + pinned test.
- **G10 CLOSED:** case-insensitive strategy/regime match + warn on never-matched keys.
- Callsites 7/7 pass strategy/regime. Tests 35/35 + 75/75 regression, ruff clean.

### 🔌 API wiring (P0 — WS-B)
- New: `GET /api/market/candles/{s}` (real MT5 OHLCV), strategies `/params`/`/performance`/`/compare` (WF-backed), backtest `/engines`/`/factors` (introspected).
- Fixed: toggle PUT→POST, OrderFlowMap URL, removed dead client methods. `docs/DEAD_API.md` + 12 DEPRECATED markers. Live smoke 200s, `tsc` clean.

### 🧹 Dashboard + root (WS-C)
- Deleted `shared/cards.tsx`; cleaned unused imports; risk page live-fed (static labeled); 10 Radix deps removed; 4 root junk → `archive/root_junk_2026-09-04/`; 3 empty engine dirs removed. Build 40/40.

### 📝 Docs truth (WS-D)
- §15.9 5 overclaims corrected (observability PLANNED, `/status` not `/health`, extractor:42 withdrawn, 0.5% not 0.08%, threshold not weights). Counts synced (80/31/27). `docs/ALPHA_EVIDENCE.md` (5 WF rows).

### 🧪 Tests + self-evolve (WS-E)
- New: candle-scheduler (8), context-gate (6), committee-weights (7), vector-P0 (4), fill-ticket (2). Deleted 7 dead skipped files. Vector P0 rolling-mean (observability-only). **Verdict READY** (`docs/SELF_EVOLVE_READINESS.md`).

### ⚖️ Consolidation prep (WS-F)
- Veto/Kelly parity tests document splits (percent-vs-decimal, caps, floors). `docs/VOTER_STACKS.md`. COT verdict: `cot_position_guard` live; 2 files safe to archive.

### 🎫 B1 fix (coordinator)
- `_make_decision` resolves MT5 ticket from broker truth → `record_signal` fires → eval leg alive. Fail-soft 0. Pinned 2/2.

### ✅ Verification
- 278 passed + 8 xfailed (risk + new unit + vector + kill-switch); `tsc` clean; `py_compile` clean. Former 48 failures in `test_crypto_specific`/`test_pairs_trading` FIXED in v8.1.1 (rewritten to shipped API).

---

## v8.0.23 — Hardening: 4-Axis Risk + Schema + Hot-Reload (2026-09-03)

### 🔒 Risk Fully Hot-Reloadable (Track A)

- **A1 — perRegime wiring:** `manager.py:check_trade(strategy, regime)` → `get_effective_config(symbol, strategy, regime)`; UI `Per-Regime Risk` card added (`dashboard/src/app/settings/page.tsx`); 6 regimes (trending/ranging/crisis/bullish/bearish/neutral)
- **A2 — schema validation:** `_load()` rejects unknown top-level keys, validates every numeric, stamps `version: 1`; `PUT /risk-config` returns 400 on bad input
- **A3 — weekly kill hot-reload:** `KILL_SWITCH_WEEKLY_PNL = -0.8 * MAX_WEEKLY_LOSS` (was hardcoded `Final[-0.025]`); removed `Final`, re-derived on every `check_trade`
- **A4 — drawdown kill (new):** `KILL_SWITCH_DRAWDOWN_PCT = 0.8 * MAX_DRAWDOWN_PCT`; no drawdown kill trigger existed before
- **A5 — tests:** `tests/test_risk/test_per_symbol_overrides.py` — 21/21 passed (16.49s)

### 🐛 Symbol Normalization Fix

- `EURUSD.vxc` was leaving `EURUSDC` (no match for EURUSD override). Now `_normalize_symbol()` regex matches `.vx`/`.vxc`/`.VX`/`.VXC` + `split("/", 1)[0]`. `EURUSD.vxc`/`EURUSD.vx`/`EURUSD.VX`/`EURUSD.VXC`/`EURUSD/C` all → `EURUSD`.

### 80% Constitutional Buffer

- `KILL_SWITCH_DAILY_PNL = -0.8 * MAX_DAILY_LOSS` (was -0.008)
- `KILL_SWITCH_WEEKLY_PNL = -0.8 * MAX_WEEKLY_LOSS` (was -0.025)
- `KILL_SWITCH_DRAWDOWN_PCT = 0.8 * MAX_DRAWDOWN_PCT` (NEW)
- Bump `maxWeeklyLoss` UI 3%→5% now bumps kill trigger -2.5%→-4.0% (was stuck at -2.5%)

### 4-Axis Risk Layering (last wins)

```
global 0.005 → perSymbol[EURUSD] 0.003 → perStrategy[kaufman_ama] 0.004 → perRegime[trending] 0.006
```

### Verification

- `py_compile` clean on 4 risk files
- `tsc --noEmit` clean (settings/page.tsx +85 lines)
- `pytest tests/test_risk/test_per_symbol_overrides.py` → **21/21 passed**

---

## v8.0.22 — Risk Per-Symbol Live Config + Vector Live (2026-09-03)

### 🔓 Risk Fully Configurable via UI — Entire QNA Follows

- **NEW: `config/risk_config.json` + `api/routes/risk_config.py` `GET /risk-config` `PUT` `GET /effective?symbol=EURUSD`** — 9 global fields `maxRiskPerTrade 0.5%` `maxDailyLoss 1%` `maxWeeklyLoss 3%` `maxDrawdown 10%` `maxLeverage 3` `maxPositionSize 10%` `maxDailyTrades 5` `minRiskReward 2` `maxCorrelated 3` + `perSymbol/perStrategy/perRegime` overrides e.g. `EURUSD 0.3%` `XAU 0.7%` `all 28` `C(28,3)=3276`
- **Engine hot-reload:** `engine/risk/constants.py: _reload_from_risk_config()` + `engine/risk/manager.py: check_trade hot-reload per-symbol` `MAX_RISK_PER_TRADE_EFF = eff["maxRiskPerTrade"]` `kill_switch: reload_kill_thresholds()` — **no restart**, next `check_trade` uses new limits
- **UI:** `dashboard/src/app/settings/page.tsx:385` `9 field global` `%`/`x`/`:1` + `Per-Symbol Risk` `Card` `EURUSD/XAU/all 28` `+ Add Override` `Trash2` `PUT /api/risk-config perSymbol` `whole QNA follows` `Constitutional • Live`

### 🎯 Vector 6 Modul Live (Step 4.6)

- `engine/currency_graph.py` `engine/cross_matrix.py` `engine/tri_arb_detector.py` `engine/vector_manifold.py` `engine/euclidean_mispricing.py` `engine/grid_executor.py` `api/routes/vector.py` `GET /vector/status` `dashboard/vector 31p` `sidebar vector NEW` `command-palette vector`

### 📄 Documentation Sync (CANONICAL v8.0.22)

- Bumped `55` md `v8.0.21→v8.0.22` + `pyproject 8.0.22` + `risk per-symbol` `vector live` `MCP 23689` `graphify 28208` `launch 5 remote OK`
- `docs/UI_PLAN_v8.0.21.md:1` `31p` `vector live` `drag 0.05 mesh` `assistant LLM fallback` `auto launch daemon+qna entry`

---

## v8.0.22 — Documentation Sync + Skills Inventory + SSOT Alignment (2026-08-28)

### 📄 Documentation Sync (CANONICAL v8.0.22)
- Synced all 53 md to SSOT: `AGENTS.md` v8.0.16→v8.0.22, `CLAUDE.md` v8.0.10→v8.0.22, `GEMINI.md` v8.0.10→v8.0.22, `WAR_PLAN.md` v5.1.0→v8.0.22, `QNA_AGENT_STATE.md` session9→v8.0.22 BAL 1445, `docs/architecture.md` 15→83 strategies, `README.md` BAL unified
- **Skills:** verified `D:\Obsidian\DhaherLabs\skills` 41 + `E:\skills` 41 + `C:\Users\Hi\.opencode\skill` 29 + 7 MCP — documented in `docs/SKILLS.md`, referenced in `AGENTS.md`
- **CANONICAL sync:** BAL 1445 (ValetaxIntl-Live2 372044706), weekly 0 WIB (`launch.bat weekly-reset`), probe 0/32 (CandleScheduler), CPCV 207 (walk_forward 214), launch.bat 1 (single WIB), manager.py WIB (weekly_pnl_pct)
- Verified via bash timeout 15000 (`Get-ChildItem -Recurse -Filter SKILL.md`, `dir`)

---

## v8.0.16 — Data Pipeline: News + COT + Sentiment Cache (2026-08-27)

### 📡 Committee Data Sources
- **NEW: `engine/committee/data_pipeline.py`** — feeds the committee with structured external intelligence:
  - **Finnhub news** — real-time headline scanning, keyword-filtered for symbol relevance, sentiment-scored per article (bullish/bearish/neutral), aggregated into rolling bias.
  - **CFTC COT** — weekly Commitment of Traders positioning data (leveraged funds, asset managers, commercial), delta computation vs prior week, extreme-positioning alerts (>80th / <20th percentile).
  - **Sentiment cache** — per-symbol sentiment scores cached in `data/sentiment_cache.json` with TTL (configurable via `QNA_SENTIMENT_TTL_MINUTES`, default 30). Avoids redundant API calls within the same candle cycle.
- **Circuit breaker**: if Finnhub is down, pipeline returns `None` (not `[]`) so committee treats it as unavailable, not neutral. Fail-closed against silent data starvation.

### 🧪 Tests
- **NEW: `tests/test_engine/test_data_pipeline.py`** — 6 tests: news fetch + sentiment scoring, COT delta parsing, cache TTL expiry, circuit breaker on API failure, empty-response handling.

---

## v8.0.15 — Strategy Evaluator: Rolling Backtest + Auto-Disable (2026-08-27)

### 📊 Strategy Health Monitoring
- **NEW: `engine/strategy_evaluator.py`** — continuous per-strategy performance tracking:
  - **Rolling Sharpe ratio** — 30-trade window, recomputed every N trades (configurable via `QNA_EVAL_WINDOW_TRADES`, default 30).
  - **Win rate tracking** — 30-trade rolling window, compared against strategy-specific threshold.
  - **Auto-disable** — strategy flagged DISABLED if rolling Sharpe < -0.5 OR win rate < 40% for 3 consecutive evaluation windows. Disabled strategies still appear in reports but never generate signals.
  - **Re-enable** — manual via `python qna.py enable-strategy <name>`, or automatic after 7 days of no trades (decay guard integration).
- **SQLite backing** — evaluation history in `data/strategy_eval.db`, queryable by strategy/symbol/window.

### 🧪 Tests
- **NEW: `tests/test_engine/test_strategy_evaluator.py`** — 8 tests: Sharpe computation correctness, win rate threshold, auto-disable trigger, re-enable flow, disabled strategy blocks signal generation.

---

## v8.0.14 — Committee Architecture: Per-Pair Specialist Agents (2026-08-27)

### 🤖 Multi-Agent Decision Engine
- **NEW: `engine/committee/agents.py`** — 5 specialist agents per symbol:
  - **BullAgent** — identifies bullish catalysts (breakout, momentum, positive flow)
  - **BearAgent** — identifies bearish catalysts (breakdown, divergence, negative flow)
  - **RiskAgent** — position sizing, correlation exposure, portfolio heat, drawdown proximity
  - **MacroAgent** — economic calendar alignment, intermarket correlation, regime detection
  - **ExecutionAgent** — order type selection, spread assessment, slippage estimation
- **Each agent** returns a structured `AgentVerdict` with `bias`, `confidence`, `evidence`, and `dissent` fields. No agent can overrule the RiskAgent (fail-closed).
- **NEW: `engine/committee/vote_chamber.py`** — weighted consensus:
  - BullAgent/BearAgent/MacroAgent each carry configurable weight (default 1.0).
  - RiskAgent carries weight 2.0 (double-weighted, VETO-capable).
  - ExecutionAgent carries weight 0.5 (execution quality modifier, never blocks).
  - **Consensus threshold**: weighted average confidence ≥ 0.65 to proceed.
  - **RiskAgent VETO** is absolute — no override. Fail-closed: committee always defers to risk on conflict.

### 🧪 Tests
- **NEW: `tests/test_engine/test_committee.py`** — 10 tests: agent verdict structure, weighted consensus math, RiskAgent VETO blocks all, ExecutionAgent cannot block, consensus threshold enforcement.

---

## v8.0.13 — Signal Context Logging (SL/TP/Confidence Linked to MT5 Deals) (2026-08-27)

### 📝 Trade Audit Trail
- **NEW: `engine/signal_context.py`** — every executed order now carries the full decision context:
  - **SL/TP rationale** — ATR multiplier, profile name, risk-reward ratio at time of entry.
  - **Confidence score** — raw signal confidence + committee consensus (when available).
  - **Strategy origin** — which strategy generated the signal, with parameter snapshot.
  - **Linked to MT5 deals** — `deal_id` stored alongside context in `data/signal_context.jsonl`.
- **Journal enrichment** — `qna_trade_journal.db` now includes `context_json` column with full signal snapshot. Trade history queries return context for post-trade analysis.
- **No latency** — context logging is non-blocking; fire-and-forget in executor thread.

### 🧪 Tests
- **NEW: `tests/test_engine/test_signal_context.py`** — 5 tests: context JSON structure, deal_id linkage, missing context fails closed, journal context column, concurrent writes safe.

---

## v8.0.11 — Autonomous Pipeline + Candle Close + JournalSync Thread-Safe (2026-08-26)

> Root cause: system ran 3+ hours with zero trades despite $1,720 live balance. 4 chained bugs blocked entire autonomous pipeline.

### 🔴 Trading unblocked (zero-trades root causes)
- **Candle close detection broken** — `_check_all_closes_sync` used bare `mt5.copy_rates_from_pos` which loses IPC connection between probes. Self-heal single-pair probe succeeded (2 bars) but batch 32/32 returned EMPTY. Fix: use `broker.get_rates()` as primary data source (handles suffixes + reconnection); init states also use broker. Result: candle closes now detected.
- **Autonomous pipeline `discover_all` missing** — `AutoRegistry` has `scan_all()` not `discover_all()`. AttributeError silently disabled all auto-discovery → zero signals generated. Fix: `discover_all()` → `scan_all()`. 15/15 tests pass.
- **MT5 data fetch numpy boolean** — `if raw:` on numpy array with >1 element raises `ValueError: truth value ambiguous`. Every MT5 data fetch silently failed → zero data for strategies. Fix: `if raw:` → `if raw is not None and len(raw) >= 50:`. 15/15 tests pass.

### 🟠 JournalSync thread-safe
- **MT5 C-API not thread-safe** — daemon thread called `mt5.history_deals_get()` which crashed silently (no output, no exception). `qna_trade_journal.db` remained 0 bytes despite 147 deals on MT5. Fix: moved JournalSync into CandleScheduler's asyncio event loop (runs on scheduler thread where MT5 is initialized). Added `async_sync_mt5_deals()` wrapper + `deals` parameter for pre-fetched data. Removed broken daemon thread from `qna.py`.

### 🧪 Tests
- **15/15 candle scheduler tests pass**
- **15/15 ML pipeline tests pass**
- All compile checks pass

---

## v8.0.10 — MT5 Data Pipeline + Candle Scheduler Thread Fix (2026-08-25)

> Root cause analysis: QNA was not trading due to 5 chained critical issues across the data pipeline.

### 🔴 Trading unblocked (data pipeline root causes)
- **get_rates() numpy return** — `mt5_broker.get_rates()` returned `list(raw)` which destroyed numpy structured array `dtype.names` needed by `autonomous._fetch_data()` for DataFrame construction. Error: "Shape of passed values is (500, 1), indices imply (500, 8)" → ALL autonomous cycle fetches failed → zero signals → zero trades. Fix: return `np.asarray(raw)` to preserve dtype.
- **CandleScheduler executor thread** — `_check_all_closes_sync` ran via `loop.run_in_executor` which spawns a fresh thread with NO MT5 handle. MT5 C-API is not thread-safe — `copy_rates_from_pos` returns None in uninitialized threads → zero candle close detections for 6900+ consecutive ticks. Fix: run probe directly in scheduler thread which already has MT5 initialized.
- **Symbol discovery dedup** — `_discover_symbols` found 16 symbols (8 bare + 8 `.vxc`) because it matched both suffixed and unsuffixed variants. Bare names are disabled on ValetaxIntl-Live2 (trade_mode=4) → MT5 returns None → silent failures. Fix: deduplicate by base name, prefer suffixed variants, only use visible symbols.

### 🟠 Pipeline fixes
- **Lot size mismatch** — `_check_risk()` computed `balance*0.005/price` but `_make_decision()` used `confidence*0.05`. Risk gate validated different sizing than execution used. Fix: pass `risk_lot_size` from `_check_risk` to `_make_decision`.
- **`MT5Broker.detect_active_account` broken** — called as class method in `builder.py` but it's an instance method. Fix: simplified logging, removed broken call.
- **Legacy `total_weight` NameError** — undefined in ensemble fallback path. Fix: defined `total_weight = sum of all weights`.
- **`result.success` True on exception** — `_make_decision()` caught exceptions internally, returned error dict, but outer handler never fired → `s5.status` stayed "running". Fix: check `exec_decision.error` and set `s5.status = "failed"`.

### 🧪 Tests
- **33/33 targeted regression tests pass** (risk gate, context gate, signal aggregator, strategy allocation).

---

## v8.0.9 — Full-Stack Parallel Audit Fixes (2026-08-25)

> 4-agent parallel audit (backend/UI/runtime/docs): 50+ findings, all P0/P1 fixed same-session.

### 🔴 Trading unblocked (runtime root causes)
- **MT5 data fetch shape bug** — get_rates returns numpy structured records; pd.DataFrame(raw, columns=8) raised "Shape (500,1) != (500,8)" → ZERO live data → zero signals since boot. Now builds from dtype field names (+ tick_volume→volume fallback).
- **Kill-switch test pollution** — pytest activation leaked into production shared state file, blocking all orders all day. conftest autouse isolation added.
- **TZ bug in stale veto** — naive-UTC bars vs naive-local now inflated age by UTC offset (+7h WIB); M15/H1 permanently "stale". Now TZ-safe.
- **Trailing-exit UnboundLocalError (F1)** — regime referenced before assignment killed every GATE-7 protective exit silently; tracking was already removed → never retried. Fixed init order.
- **Duplicate gate blocked CLOSES** — one-position gate blocked opposite-side orders too; trailing exits could never execute. Now blocks only same-side pyramiding; reduce_only passes; suffix variants normalized (F8).
- **Side inversion (F2)** — engine enum BUY ("BUY") vs connector literal ("buy") always False → every direct-MT5 order sent as SELL. Normalized at connector boundary; invalid sides raise.
- **PnL zeroing chain (F3)** — history_deals_get swallowed read failures → real −4% day became 0.00 → loss vetoes blind. Connector raises; RiskManager keeps last-known values + vetoes PNL_SYNC_STALE until recovery.
- **False "TRADE EXECUTED" (F10)** — rejected orders reported success; scheduler derived traded=True → fake Telegram fills. Now verdict-driven.

### 🟠 Backend P1
- F4: context-gate circuit breaker — calendar outage NEUTRAL for ≤2 consecutive failures, then VETO until recovery (uncached).
- F5: env-flag convergence QNA_LIVE_TRADING/QNA_MT5_LIVE = single live intent (bridge); deleted un-awaited async execute_order phantom-executed branches; pipeline router awaits properly (thread-loop when sync context).
- F9: JournalSync thread hourly in daemon (scorecard/lifecycle feedback no longer starves).
- F12/F14: NameError cleanups (run_batch result refs), execute_order pulls real PnL fractions from wired RiskManager internally.
- PID file name unified: data/daemons/qna_daemon.pid (tray now matches daemon).

### 🖥️ Dashboard (UI agent)
- WS auth: new POST /api/auth/token endpoint (API-key → JWT); websocket.ts caches token, appends ?token=, stops reconnect on 4001/4003.
- Candle channel key aligned (data payload); scheduler state now persists events[] (50) for REST fallback.
- trade-history route: shell-injection fixed (execFileSync argv, sanitized).
- autonomous/pipeline pages routed through authenticated apiRequest; fabricated cash_balance removed; ErrorBoundary wrapped on all pages; sidebar/footer/version strings updated.

### 🧪 Tests
- NEW test_v809_parallel_fixes.py (12 tests): duplicate-gate side semantics, connector side normalization, PNL_SYNC_STALE veto, circuit breaker, structured-rates shape.
- Battery: ~900 tests (893 pass + 6 pre-existing failures unrelated to this batch: walk-forward window assertions, observability default flag, ict→ict_ote registry rename).

---

## v8.0.8 — HOTFIX: Trading Blocked Root Causes (2026-08-25)

> Incident: "QNA ga trading" — two independent blockers found via runtime diagnosis.

### 🔴 ROOT CAUSE 1: Kill switch poisoned by test run
- A pytest activation (`"reason": "test"`, level_1) leaked into the PRODUCTION cross-process state file `data/kill_switch_state.json` at 00:02 UTC. Same-day level_1 has no auto-expiry → **every order blocked all day**.
- **FIX: `tests/conftest.py` autouse isolation** — `QNA_KILL_SWITCH_STATE_FILE` + `QNA_KILL_SWITCH_AUDIT_LOG` now point at a per-test temp dir (set at import time AND per-test via monkeypatch). Tests can never touch production state again.
- **NOTE:** pytest's own `tmp_path` is deliberately avoided in the fixture — its shared root can be access-denied when created by an elevated process.
- Production state cleared manually (inactive).

### 🔴 ROOT CAUSE 2: Timezone bug in stale-data veto
- MT5 epochs become naive-UTC timestamps; `_reject_stale` compared them against naive LOCAL time (WIB = UTC+7). Every age inflated by +7h → M15 (budget 60m) and H1 (budget 240m) **permanently vetoed since v8.0.5 → zero signals**.
- **FIX: TZ-safe comparison** — naive index explicitly localized to UTC; now always taken as `Timestamp.now(tz="UTC")`.
- New regression test: fresh naive-UTC bar must pass regardless of local TZ.

### 🧪 Verification
- **294 tests pass** (full battery).
- Kill switch state file verified INACTIVE after a full test run — isolation proven.

---

## v8.0.7 — Auto-Retrain Loop + Decay Guard (2026-08-25)

### 🔄 Closed-Loop Parameter Freshness
- **NEW: `engine/auto_retrain.py`** — the tuning loop that was MANUAL (`scripts/run_param_tuning.py`) is now autonomous: fetch broker bars → Bayesian-optimize numeric params (±50% around current) → fold-validated holdout scoring (no lookahead) → **persist ONLY when candidate beats incumbent by >0.05 margin AND is positive** → atomic write to `data/tuning_results.json`.
- **Background schedule**: thread inside daemon, first pass after 5-min grace; cadence via `QNA_RETRAIN_INTERVAL_HOURS` (default 12, `0` = off). Wired in `qna.py daemon` next to CandleScheduler with lazy pipeline fetcher.
- **Decay ledger**: `data/retrain_report.json` keeps last 50 baselines per strategy:symbol.
- **DECAY GUARD (WF refresh)**: a strategy flagged stale (≥3 consecutive negative baselines) has its tuned params WITHHELD by `best_params_for()` → falls back to defaults until fresh evidence arrives. Fail-closed against alpha decay.

### 🧪 Tests
- **NEW: `tests/test_engine/test_auto_retrain.py`** — 8 tests: space discovery, broken-strategy reject, signal-shape handling, no-allocation noop, singleton contract, disabled interval, stale-withhold gate, ledger flagging.
- Fixed `_append_report` structure-corruption bug on reload (top-level keys treated as strategy entries).
- **Full battery**: 287 pass.

---

## v8.0.6 — News Gate + WebSocket Live + System Tray (2026-08-25)

### 📰 Macro/News Context Gate (wired into live path)
- **FIX: phantom calendar** (`fundamental/calendar.py`) — wrapper imported `engine/data/economic_calendar.EconomicCalendarData` which DOES NOT EXIST → silently returned [] forever. Now points at the real provider (`engine/macro/economic_calendar.EconomicCalendarProvider`).
- **NEW: `engine/agentic/context_gate.py`** — pre-trade event-risk veto: a high-importance release within ±30 min blocks NEW entries. Calendar unavailable → NEUTRAL (context filter, not constitutional); real data showing imminent event → VETO. Result cached 5 min.
- Wired into pipeline `run()` as Step 3.5, after risk check.

### 📡 WebSocket Candle-Close Events (real-time push)
- **NEW: `engine/candle_events.py`** — thread-safe event bus bridging CandleScheduler thread → async WS world. Bounded queues per subscriber + 200-event ring buffer for REST fallback.
- **CandleScheduler** publishes every candle-close event (signal/confidence/traded/duration).
- **ws.py**: new `"candles"` channel + drain task; clients subscribe via standard protocol; heartbeat/ping unchanged.
- **Dashboard `/candle-monitor`**: consumes WS pushes instantly (badge shows WS LIVE vs POLLING); REST polling kept as fallback.

### 🖥️ System Tray (`qna_tray.py`)
- Windows tray icon: green = daemon running, red = stopped (auto-refreshes every 3s from PID-file broker truth).
- Menu: Start/Stop Daemon · Open Dashboard · Open API Docs · Quit. Run: `python qna_tray.py`.

### 🧪 Tests
- **NEW: `tests/test_engine/test_context_gate.py`** — 7 tests: no-events allow, imminent/recent veto, distant allow, broken feed NEUTRAL, unparsable time ignored, wrapper reaches REAL provider.
- **Full battery**: 285 pass · Dashboard build clean (36 pages).

---

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

### 🌐 Universal Path Auto-Detect
- **FIX: All `/sdcard` hardcoded paths** — `security_audit.py`, `qna-watchdog.py`, `ensemble_walk_forward.py` now use `Path(__file__).resolve().parent.parent`
- **FIX: All `D:/repositories/Quant-Nanggroe-AI-worktree` hardcoded paths** — 15 scripts now use `Path(__file__).resolve().parent.parent`
- **FIX: All `E:/trading` hardcoded paths** — `backtest_dhaher.py`, `test_dhaher_live.py`, `tune_dhaher.py`, `backtest_all_strategies.py` now use auto-detected root
- **FIX: External integrations** — `adapters.py` and `core.py` now use env vars (`QNA_EXT_*`) for external project paths with fallback to known locations
- **NEW: `scripts/_path_utils.py`** — shared PROJECT_ROOT auto-detection (finds pyproject.toml or .git)

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

---

> **SSOT:** `CANONICAL.md` v8.1.3 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, vector 6 modul live, risk per-symbol
