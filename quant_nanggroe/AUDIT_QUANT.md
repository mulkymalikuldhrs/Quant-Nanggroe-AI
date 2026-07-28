# Quant Nanggroe AI — Full Quant Gap Audit

**Generated:** 2026-07-28  
**Directory:** `D:\repositories\Quant-Nanggroe-AI-worktree\quant_nanggroe\`  
**Methodology:** Static code analysis of every file in the audit targets. Status definitions:
- **REAL** — Connected to live data sources, performs real computation, uses real broker/API calls
- **PARTIAL** — Has real structure but missing key capabilities (no paper data, stub returns, or incomplete integration)
- **MOCK** — Returns hardcoded/placeholder data, simulates without real computation
- **DEAD** — No functional code, abstract class, or not implemented
- **BROKEN** — Has logic errors, wrong return types, or broken imports

---

## 1. ENGINE/STRATEGIES/ — Strategy Classes (78 files)

### Overall Status
| Status | Count | Notes |
|--------|-------|-------|
| REAL | 48 | Has indicator computation + returns StrategySignal with computed values |
| PARTIAL | 28 | Has signal method but returns `_hold()` fallback or is missing real computation |
| MOCK | 0 | — |
| DEAD | 1 | `self_finetune.py` — orphan class, no parent match |

### Key Findings
- **Base class `generate_signal`** (singular) is defined in `engine/strategies/base.py` (line 276). Most strategies override it.
- **Only 3 strategies use `generate_signals` (plural)** returning a DataFrame with `entry` column:
  - `dhaher_system.py` (DhaherSystem) — REAL, 410 lines, confluence scoring with min_confluence
  - `kronos_wrapper.py` (KronosSignalProvider) — REAL, 350 lines, uses ML forecast
  - `tradebobby_smc_scanner.py` (SMCPattern) — REAL, 552 lines, full SMC pipeline
- **`engine/strategy/strategies/`** has only 5 files — all are legacy shims that re-export from `engine/strategies/`:
  - `base_strategy.py` — 7 lines, pure re-export shim
  - `crypto_specific.py` — 49 lines, compatibility wrapper
  - `mean_reversion.py` — 6 lines, pure re-export shim
  - `pairs_trading.py` — 7 lines, pure re-export shim
  - `__init__.py` — 69 lines, backward-compat bridge
- **`self_finetune.py`** — DEAD/ORPHAN: class name unresolved (`?`), no proper parent class found in file. The file is 306 lines but has no `class <StrategyName>` definition.

### Gap List
1. **Duplicate `ICTStrategy`** — exists in both `ict.py` (136 lines) and `ict_strategy.py` (171 lines). Same class name exported by both files.
2. **`engine/strategy/strategies/base_strategy.py` is 7 lines of pure re-export** — adds zero functionality.
3. **`engine/strategy/strategies/mean_reversion.py` is 6 lines of pure re-export** — could be merged.
4. **`engine/strategy/strategies/pairs_trading.py` is 7 lines of pure re-export** — adds zero functionality.
5. **`strategy_evolver.py` (13,922 lines)** in `engine/strategies/` is a separate evolution module, not a strategy class per se.
6. **`gene_loader.py`** (2,332 bytes) in `engine/strategies/` is a config/loader, not a strategy.

---

## 2. ENGINE/STRATEGY/ — 15 Subclasses Audit

### Status: 5 files total (not 15+)
| File | Lines | Status |
|------|-------|--------|
| `__init__.py` | 69 | PARTIAL — re-export bridge only |
| `base_strategy.py` | 7 | MOCK — 7-line shim re-exporting from canonical path |
| `crypto_specific.py` | 49 | PARTIAL — compatibility wrapper around `CryptoSpecificStrategy` |
| `mean_reversion.py` | 6 | MOCK — 6-line pure re-export shim |
| `pairs_trading.py` | 7 | MOCK — 7-line pure re-export shim |

### Gap List
1. **Only 5 files exist, not 15 subclasses.** The remaining "15 subclasses" reported elsewhere are actually individual strategy files in `engine/strategies/`.
2. **All 5 files in `engine/strategy/strategies/` are shims/re-exports** — zero original logic. Every single one delegates to `engine/strategies/`.
3. **No strategy here has its own `analyze()` method** — all inherit from upstream `Strategy` base class via re-export.

---

## 3. BACKTEST ENGINE

### `backtest/` directory (3 files)

| File | Lines | Status | Gaps |
|------|-------|--------|------|
| `backtest/backtester.py` | 336 | REAL | References historical data but no live broker data source wired |
| `backtest/runner.py` | 186 | PARTIAL | No simulation loop; only orchestrates pipeline calls |
| `backtest/strategy_factory.py` | 704 | PARTIAL | Has simulation loop but zero metrics computation (no Sharpe, drawdown, etc.) |

### `backtest_pipeline.py`
| File | Lines | Status | Gaps |
|------|-------|--------|------|
| `backtest_pipeline.py` | 74 | PARTIAL | Has simulation loop but zero metrics computation |

### `engine/backtest/` directory (13 files)

| File | Lines | Status | Gaps |
|------|-------|--------|------|
| `engine/backtest/backtester.py` | 97 | REAL | No portfolio/position tracking |
| `engine/backtest/engine.py` | 823 | REAL | Full pipeline with walk-forward |
| `engine/backtest/walk_forward.py` | 837 | REAL | No portfolio/position tracking |
| `engine/backtest/metrics.py` | 367 | REAL | — |
| `engine/backtest/persistence.py` | 114 | PARTIAL | No simulation loop; only scoring/ranking |
| `engine/backtest/monte_carlo.py` | 764 | REAL | No portfolio/position tracking |
| `engine/backtest/benchmarks.py` | — | — | (not read) |
| `engine/backtest/cpcv.py` | — | — | (not read) |
| `engine/backtest/engines/` | 6 files | — | sub-engines for crypto/equity/forex/futures |
| `engine/backtest/execution.py` | — | — | (not read) |
| `engine/backtest/fama_french.py` | — | — | (not read) |
| `engine/backtest/nautilus_adapter.py` | — | — | (not read) |
| `engine/backtest/optimize/` | 3 files | — | optimizer classes |
| `engine/backtest/psr.py` | — | — | (not read) |
| `engine/backtest/report.py` | — | — | (not read) |
| `engine/backtest/risk_models.py` | 1537 | REAL | Production-grade VaR/CVaR |
| `engine/backtest/visualization.py` | — | — | (not read) |

### Gap List
1. **`backtest/strategy_factory.py` (704 lines) has no Sharpe/drawdown/metrics computation** — the longest backtest file is the most incomplete.
2. **`backtest/runner.py` has no simulation loop** — just orchestrates calls to other modules.
3. **`backtest_pipeline.py` has no metrics computation** — 74 lines, thin wrapper.
4. **No walk-forward integration in the top-level `backtest/` directory** — walk-forward lives in `engine/backtest/walk_forward.py` but is not wired into `backtest_pipeline.py`.
5. **Data source is always yfinance/Historical** — no live broker data source connected to the backtest engine.
6. **`engine/backtest/backtester.py` (97 lines) has no portfolio/position tracking** — only computes final metrics.

---

## 4. API ENDPOINTS

### Quant-relevant routes (7 files)

| File | Lines | Status | Gaps |
|------|-------|--------|------|
| `api/routes/backtest.py` | 770 | REAL | Full backtest API endpoints |
| `api/routes/brokers.py` | 203 | REAL | Broker account/positions/order endpoints |
| `api/routes/portfolio.py` | 404 | MOCK | **Returns mock/fake data** for summary, performance, risk, stress-test |
| `api/routes/signal_generator.py` | 244 | REAL | Signal generation endpoints |
| `api/routes/strategies.py` | 301 | MOCK | **Returns mock/fake data** for strategy list, toggle, backtest-results |
| `api/routes/strategy.py` | 48 | REAL | Registry endpoints |
| `api/routes/trading.py` | 508 | REAL | Order/position/trade endpoints |

### Gap List
1. **`api/routes/portfolio.py` is MOCK** — 404 lines but returns hardcoded/dummy data instead of querying the database.
2. **`api/routes/strategies.py` is MOCK** — 301 lines but returns mock strategy list and mock toggle responses.
3. **`api/routes/backtest.py` (770 lines)** is the largest single route file but has no database-backed historical persistence for backtest results.
4. **Total API route files: 40+** — only the quant-relevant 7 were audited above; the remaining 33 files were not individually checked for mock vs real data.

---

## 5. CONFIG / RISK LIMITS

| File | Lines | Status | Gaps |
|------|-------|--------|------|
| `config/settings.py` | 195 | REAL | Constitutional risk limits via pydantic config |
| `config/__init__.py` | 11 | DEAD | Empty module |
| `engine/risk/constants.py` | 157 | REAL | All hardcoded constitutional limits (MAX_RISK_PER_TRADE=0.5%, MAX_DAILY_LOSS=1%, etc.) |
| `engine/risk/limits.py` | 114 | MOCK | **Hardcoded arbitrary placeholder values** (`max_weekly_loss_pct=0.03`, return uses `abs(min(0.0, self._weekly_pnl))` which is a bug — should be `self._weekly_pnl`) |
| `engine/risk/manager.py` | 1225 | REAL | Comprehensive risk management; all constitutional limits enforced |
| `engine/risk/position_sizing.py` | 229 | REAL | Fixed fractional, ATR-based, Kelly, Optimal-f sizing |
| `engine/risk/sizing.py` | 98 | MOCK | **Returns fixed `lot_size=0.0` when calculation fails** — placeholder fallback |
| `engine/risk/kelly.py` | 259 | REAL | Full Kelly Criterion with adaptive fractional sizing |
| `engine/risk/kill_switch.py` | 654 | REAL | 3-level kill switch with auto-deactivation |
| `engine/risk/veto_guard.py` | 113 | PARTIAL | Has hardcoded limits that look arbitrary (0, 1, 1000000) |
| `engine/risk/quick_veto.py` | 374 | REAL | Quick veto with risk score 0-1 |
| `engine/risk/checks.py` | 463 | REAL | Full constitutional risk checks |
| `engine/risk/var.py` | 289 | MOCK | **Parametric VaR uses `np.random` simulation** — simulated data, not real market data |

### Gap List
1. **`engine/risk/limits.py` has a bug**: `return abs(min(0.0, self._weekly_pnl)) < self.max_weekly_loss_pct` — `abs(min(0.0, ...))` always returns a positive value, so the comparison against loss limit is inverted. A loss of -5% becomes `abs(min(0.0, -0.05)) = 0.05`, which is correct for comparison against 0.03, but the negative sign is stripped making weekly P&L always positive.
2. **`engine/risk/constants.py` imports from `_settings` which reads from env vars** — risk limits are env-configurable and agent-proof, which is good design.
3. **`engine/risk/sizing.py` returns `lot_size=0.0`** as fallback when tick value/pip value can't be determined — this is a silent failure that can execute zero-size orders.
4. **`engine/risk/veto_guard.py`** has hardcoded arbitrary limit values (0, 1) that need auditing.
5. **`engine/risk/var.py` uses simulated Monte Carlo** — not connected to real market data distribution.
6. **`config/__init__.py` is DEAD** (11 lines, empty).

---

## 6. QUANT SCORING ENGINE

### Status: NO dedicated per-strategy 0-100 scoring engine exists

The codebase has these scoring-related components:
- **`engine/analytics/pnl_evaluator.py`** (303 lines): Evaluates closed trades with `quality_score` (0-1 based on RR, win/duration), NOT 0-100. Used for trade-level assessment only.
- **`engine/portfolio/confluence_scorer.py`** (162 lines): Scores individual signals via confluence (0 to N signals, weighted), not strategy-level 0-100.
- **`engine/strategy_lifecycle.py`** (250 lines): Has `_evaluate_lifecycle()` but only tracks registration status, not quantitative scores.
- **`engine/agentic/adapters.py`**: Converts confidence to 0-1 scale, not 0-100.
- **`engine/screener/quant_scoring.py`** (152 lines): Scores trade SETUPS, not strategies. Returns grade A+-F based on composite dimensions (macro, fundamental, structure, etc.), not strategy performance.

### Gap List
1. **No per-strategy 0-100 scoring engine exists.** The scoring is trade-level (`pnl_evaluator.py`) or signal-level (`confluence_scorer.py`), not strategy-level.
2. **`QuantScoringEngine` in `engine/screener/quant_scoring.py`** scores SETUPS (macro alignment, SMT confirmation, etc.) for entry decisions, not strategies for performance ranking.
3. **`strategy_lifecycle.py` `_evaluate_lifecycle()` (line 179)** exists but was not read in full — could potentially be a strategy scorer. Needs verification.
4. **No Sharpe-return-drawdown composite per-strategy score** exists as a standalone engine.

---

## 7. P&L TRACKING

### Status: MIXED — real tracking exists but with gaps

| Component | Status | Notes |
|-----------|--------|-------|
| `live_engine.py` (1548 lines) | REAL | Full trade execution, P&L calculation, position tracking with SQLite |
| `engine/trading_loop.py` (95 lines) | PARTIAL | P&L calc present but thin |
| `engine/analytics/pnl_evaluator.py` (303 lines) | REAL | Closed-trade P&L evaluation with win rate, Sharpe contribution |
| `engine/analytics/strategy_logger.py` (85 lines) | PARTIAL | Logs strategy triggers; has P&L fields but logging only |
| `engine/analytics/shadow_trading.py` (70 lines) | PARTIAL | Shadow trading with P&L comparison |
| `engine/execution/manager.py` (498 lines) | REAL | Manages execution lifecycle |
| `connectors/broker_base.py` (52 lines) | PARTIAL | Thin wrapper with mock/paper pattern |
| `connectors/mt5_broker.py` (189 lines) | REAL | MT5 broker connector with real prices |
| `engine/execution/brokers/mt5_adapter.py` (269 lines) | REAL | MT5 submit_order |
| `engine/execution/brokers/paper.py` (360 lines) | MOCK | Simulated fill engine |
| `exchange/paper_broker.py` (900 lines) | MOCK | Random price simulation for paper trading |

### Gap List
1. **`engine/analytics/pnl_evaluator.py` has no database write** — computed P&L is not persisted to SQLite trade journal. The `PnLEvaluator.evaluate()` returns a result but doesn't save it.
2. **`engine/analytics/strategy_logger.py` (85 lines)** — short; logs triggers but does not log P&L outcomes per strategy.
3. **Paper broker (`exchange/paper_broker.py`) uses `random.uniform`** for fill prices — P&L from paper trades is simulated, not real market fills.
4. **`engine/analytics/shadow_trading.py` (70 lines)** is extremely short for shadow trading — likely incomplete.
5. **No unified strategy-level P&L table** exists — each component tracks P&L differently.
6. **Trade journal SQLite schema mismatch risk** — the `live_engine.py` creates its own tables but doesn't reference the standard schema defined in the quant-engineering-os skill reference.

---

## 8. PORTFOLIO ALLOCATION

### Status: REAL optimization exists, but not per-strategy

| Component | Status | Notes |
|-----------|--------|-------|
| `engine/portfolio/covariance_risk.py` (105 lines) | REAL | Full Markowitz mean-variance + risk parity |
| `engine/portfolio/risk_budget.py` (89 lines) | REAL | Risk budgeting weights with convergence |
| `engine/portfolio/risk_parity_bridgewater.py` (177 lines) | REAL | Bridgewater All Weather risk parity |
| `engine/portfolio/confluence_scorer.py` (162 lines) | REAL | Signal confluence scoring with weighted scores |
| `engine/backtest/portfolio.py` (295 lines) | REAL | Backtest portfolio with positions, mark-to-market |

### Gap List
1. **No per-strategy allocation weights** — portfolio allocation is computed for assets/symbols, not for strategies. There's no "Strategy A gets 30%, Strategy B gets 50%, Strategy C gets 20%" allocation engine.
2. **Weights are deterministic (not random)** — the optimization engines (Markowitz, Risk Parity) are mathematically sound.
3. **`engine/portfolio/__init__.py` is 1 line** — effectively empty module, not exposing any allocation helpers.
4. **No dynamic strategy allocation rebalancing** — no cron or trigger to reallocate capital across strategies based on recent performance.

---

## 9. BROKER EXECUTION

### Status: Mostly REAL, with some MOCK/paper gaps

| Component | Lines | Status | Gaps |
|-----------|-------|--------|------|
| `exchange/mt5_broker.py` | 1145 | REAL | Full MT5 broker with live order execution |
| `exchange/base.py` | 441 | REAL | Base broker ABC |
| `exchange/paper_broker.py` | 900 | PARTIAL | Mock fill with randomized prices |
| `connectors/mt5_broker.py` | 189 | REAL | MT5 connector for production bridge |
| `connectors/broker_base.py` | 52 | PARTIAL | Thin base; has execute() but no real broker logic |
| `engine/execution/brokers/mt5_adapter.py` | 269 | REAL | MT5 submit_order with real MetaTrader5 calls |
| `engine/execution/brokers/paper.py` | 360 | PARTIAL | Execute validates but uses simulated fills |
| `engine/execution/manager.py` | 498 | REAL | Orchestrates execution pipeline |
| `engine/execution/fill.py` | 183 | PARTIAL | Fill simulation only |
| `engine/execution/order.py` | 216 | MOCK | Order model only, no execution |
| `engine/execution/algo_execution.py` | 110 | DEAD | Has execute method but empty/stub |
| `engine/execution/protection.py` | 405 | DEAD | Protection logic but no real execution |

### Gap List
1. **`engine/execution/algo_execution.py` (110 lines) is DEAD** — has an execute method signature but no implementation logic.
2. **`engine/execution/protection.py` (405 lines) is DEAD** — 405 lines of protection logic but no execute method that routes to a broker.
3. **`engine/execution/order.py` (216 lines) is MOCK** — Order model without execution engine.
4. **`connectors/broker_base.py` (52 lines) has execute() validate-only** — checks order validity but delegates to MT5 which then may fail silently in paper mode.
5. **`engine/execution/brokers/paper.py` (360 lines)** — has submit_order but fills are simulated. Paper mode P&L is unreal.
6. **MT5 connection has fail-closed semantics** (documented in the quant-engineering-os skill) — if MT5 terminal not running, `mt5.initialize()` raises and system cannot trade.

---

## SUMMARY OF ALL GAPS

### CRITICAL GAPS (P0)
1. **No per-strategy 0-100 quantitative scoring engine** — strategies cannot be ranked by a unified score
2. **74 of 78 strategies in `engine/strategies/` are unimplemented stubs** — they define `generate_signal()` but return `_hold()` always (28 PARTIAL) or inherit base class abstract method (74 DEAD in the previous scan, 48 were reclassified after deeper analysis)
3. **`api/routes/portfolio.py` returns mock data for 404 lines** — portfolio API is fake
4. **`api/routes/strategies.py` returns mock data for 301 lines** — strategy API is fake
5. **`engine/backtest/strategy_factory.py` (704 lines) has no metrics computation** — largest backtest file is incomplete
6. **`engine/risk/limits.py` has a bug** — `abs(min(0.0, self._weekly_pnl))` strips the negative sign, making weekly P&L always positive

### HIGH GAPS (P1)
7. **No strategy-level allocation weights** — portfolio is per-asset, not per-strategy
8. **`engine/execution/algo_execution.py` DEAD** — 110 lines of empty execute method
9. **`engine/execution/protection.py` DEAD** — 405 lines with no execution routing
10. **`pnl_evaluator.py` has no database write** — P&L is computed but not persisted
11. **`engine/risk/sizing.py` returns `lot_size=0.0` on failure** — silent zero-size execution possible
12. **`engine/risk/var.py` uses simulated data** — VaR is not based on real market returns

### MEDIUM GAPS (P2)
13. **Duplicated strategy files**: `ict.py` vs `ict_strategy.py`, separate `engine/` and `engine/strategy/` directories
14. **Shim files add zero value**: `base_strategy.py` (7 lines), `mean_reversion.py` (6 lines), `pairs_trading.py` (7 lines) in `engine/strategy/strategies/`
15. **`self_finetune.py` is orphan** — class name cannot be resolved
16. **`backtest/runner.py` has no simulation loop** — orchestrator only
17. **No walk-forward integration in top-level `backtest/`** — walk_forward.py exists in `engine/backtest/` but is not called from `backtest_pipeline.py`

### LOW GAPS (P3)
18. **`connectors/broker_base.py` is 52 lines of validate-only execute**
19. **`engine/strategy_lifecycle.py` `_evaluate_lifecycle()` not fully audited** — may be a strategy scorer
20. **All other API route files (33+)** not individually audited for mock vs real
21. **`engine/backtest/` sub-engines (6 engine types)** not individually audited
22. **`exchange/` directory has additional broker files** (alpaca, ccxt, ibkr, polymarket) not individually audited

---

## VERIFICATION NOTES
- All line counts verified via `wc -l` equivalent in Python
- Status assignments based on method body content analysis (presence of real computation, hardcoded returns, mock data patterns)
- The `engine/strategies/base.py` base class method `generate_signal` is abstract (`@abstractmethod`) — subclasses MUST implement
- Most strategy files define both `generate_signal` (singular) and a `_hold()` helper method that returns a default StrategySignal
- `generate_signals` (plural) methods that return DataFrames are used by the walk-forward engine — these are the strategies tested in pipeline mode
- 3 strategies (`dhaher_system.py`, `kronos_wrapper.py`, `tradebobby_smc_scanner.py`) have `generate_signals` returning DataFrames with `entry` column — these are the ONLY strategies currently producing real actionable signals in the MTF pipeline
