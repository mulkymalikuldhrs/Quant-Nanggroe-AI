# Self-Eval / Evolve Readiness Audit (2026-09-03, Workstream E6)

Scope: `quant_nanggroe/engine/auto_retrain.py`, `engine/agentic/strategy_evaluator.py`,
`engine/agentic/trade_lifecycle.py`, wired through `engine/agentic/autonomous.py`,
`engine/journal_sync.py`, `engine/strategy_allocation.py`, `qna.py`.
All claims verified against `file:line`. No redesign, no live-behavior change.

## 1. Call chain (trade → journal → eval → evolve → allocation)

```
ENTRY (filled order)
  autonomous.py:1280-1283  StrategyEvaluator().record_signal(strategy, symbol, ticket, price)
    │  (only when exec_decision carries a truthy "ticket")
  autonomous.py:1267-1274  journal_sync.record_signal_context(symbol, strategy, sl/tp/conf/atr/lot)
  journal_sync.py:95       → SQLite signal_context (entry snapshot for later linking)
         │
CLOSE (MT5 deal sync, hourly from scheduler thread)
  candle_scheduler.py:301-307 → journal_sync.async_sync_mt5_deals()
  journal_sync.py:363-364,382-383  StrategyEvaluator().record_outcome(ticket, exit_price, pnl)
         │  matched by MT5 ticket
         ▼
EVAL (rolling stats + auto-disable)
  strategy_evaluator.py:144 compute_stats() → Sharpe / win-rate over REVIEW_WINDOW_DAYS=30
  strategy_evaluator.py:190-196  enabled=False when sharpe<0.5 or win_rate<0.35 (MIN_TRADES=5)
  strategy_evaluator.py:218 is_strategy_enabled(strategy, symbol) → read-through gate
  autonomous.py:1403,1504  gate: disabled strategies forced to hold / filtered from candidates
  autonomous.py:2352  review_all() in the periodic evolution scan (auto-disable warnings)
         │
EVOLVE-A (per-trade fast loop)
  autonomous.py:681-686  TradeLifecycleManager(pnl_evaluator, self_correction,
                                               evolve_callback=self._trigger_evolution)
  autonomous.py:1344  process_closed_trade(trade, ctx) on every FILLED order
  trade_lifecycle.py:202-225  PnLEvaluator.evaluate(trade) → recommendation keep/review/evolve
  trade_lifecycle.py:276-295  SelfCorrection.record() for evolve/review-low-quality/low-conf
  trade_lifecycle.py:301-330  if recommendation == 'evolve' → evolve_callback(strategy)
  autonomous.py:2090 _trigger_evolution() → scans PnL stats → StrategyEvolver.evolve()
         │
EVOLVE-B (slow param loop)
  qna.py:449  get_auto_retrainer(fetcher, symbols).start() (12h cadence, env-gated)
  auto_retrain.py:195 allocation_map() → per-asset admitted strategies
  auto_retrain.py:228-231 BayesianOptimizer over ±50% numeric param space
  auto_retrain.py:235-250 persist ONLY if cand_score > 0 and > baseline + 0.05
         │  → data/tuning_results.json + decay ledger data/retrain_report.json
         ▼
ALLOCATION (consume tuning + decay)
  strategy_allocation.py:173 best_params_for() → tuned params (withheld when stale)
  strategy_allocation.py:159 _stale_strategies() → 3× negative baseline ⇒ decay guard
  autonomous.py:1519,1552 best_params_for() applied at strategy construction
```

Verdict on (1): the loop is **structurally closed** — every hop has a real
callsite, no phantom imports. All lazy import targets resolve:
`analytics/pnl_evaluator.py` ✓, `SelfCorrection` (autonomous.py:325) ✓,
`backtest/hyperopt.py:26 BayesianOptimizer` ✓, `strategy_allocation`
(`allocation_map`, `best_params_for`, `_lookup_asset`) ✓,
`strategies/strategy_evolver.py:StrategyEvolver` ✓ (via autonomous_self_loop.py:93).

## 2. Broken-link table

| # | Link | File:line | Status |
|---|------|-----------|--------|
| B1 | `record_signal` gated on truthy `ticket` | autonomous.py:1280-1283 | **OPEN GAP (by design, do not touch)** — if the broker fill path omits `ticket`, the entry is never recorded and the later `record_outcome(ticket…)` (journal_sync.py:364) matches nothing → `compute_stats` sees zero trades → evaluator can never disable. Fail-safe direction (stays enabled), but the eval leg is data-starved. Fixing requires broker-contract surgery — out of scope. |
| B2 | `process_closed_trade` fires on **entry fills** too | autonomous.py:1308 (`execution == "filled"`) → trade_lifecycle.py:175 | **OPEN GAP (do not touch)** — opens are recorded with `exit_price=0, pnl=0`; PnLEvaluator scores them as breakeven noise and healthy opens skip lesson recording (trade_lifecycle.py:247-265), so pollution is contained, but SLA/cycle counts include non-closes. Renaming/restricting to true closes changes live metrics — out of scope. |
| B3 | `TradeLifecycleManager._gc_lessons` never archives | trade_lifecycle.py:373-385 | **Trivially safe, left as-is** — logs only; no deletion path exists, so no data loss. Wiring real archival is a design decision — out of scope. |
| B4 | `StrategyEvaluator._journal` path (`data/qna_trade_journal.db`) may not exist | strategy_evaluator.py:236-237 | **Already guarded** — returns 0.0 when the journal file is absent. No fix needed. |
| B5 | AutoRetrainer no-ops without CPCV registry | auto_retrain.py:196-198 | **By design (fail-closed)** — returns "no CPCV allocation evidence". No fix needed. |
| B6 | `evolve_callback` un-wired if `_trigger_evolution` missing | autonomous.py:685 vs 2090 | **Verified wired** — `def _trigger_evolution` exists at autonomous.py:2090 and is passed at :685. No fix needed. |

Trivially-safe fixes applied in this pass: **none required** — every import
resolves and every None-path is guarded. No production diff was needed for E6.

## 3. Verdict: READY (v8.1.0 — B1 fixed; B2 contained; B5 by design)

Update 2026-09-04 (v8.1.0 all-workstreams pass):
1. **B1 FIXED — eval leg now fed:** `_make_decision` resolves the MT5 position
   ticket from broker truth after every fill and returns it as
   `exec_decision["ticket"]` (`autonomous.py`, B1-fix block; fail-soft to 0).
   `record_signal` (`autonomous.py:1280-1283`) now fires with a real ticket,
   and `record_outcome(ticket…)` (`journal_sync.py:364`) matches it on close.
   Join verified by construction: entry writes ticket T, close updates WHERE
   ticket=T. Remaining risk: none in code — needs one live round-trip to
   confirm end-to-end (entry ticket → close match in `signal_outcomes`).
2. **B2 CONTAINED (not fixed, by decision):** opens still flow through
   `process_closed_trade` with pnl=0, but `PnLEvaluator` scores them as
   breakeven noise and healthy opens skip lesson recording
   (`trade_lifecycle.py:247-265`). Pollution is bounded; renaming/restricting
   to true closes would change live metrics — deferred to F5-full.
3. **B5 by design (fail-closed):** retrainer no-ops without CPCV registry
   (`auto_retrain.py:196-198`). Correct behavior — no fix needed.

What is live today: journaling, rolling stats, `is_strategy_enabled` gates,
decay-ledger plumbing, SLA metrics, ticket-joined signal outcomes, and the
per-trade evolve callback — i.e. the full **observe → eval → evolve** path.
Recommendation: run one live cycle, then query `signal_outcomes` for matched
ticket pairs as the READY proof.
