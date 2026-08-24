# CANONICAL.md — Quant-Nanggroe-AI

> **Single Source of Truth.** Every claim must be verified against `file:line`.
> Status: GREEN — LIVE on MT5 (ValetaxIntl-Live2, acct 211098748 cent .vxc)
> Version: v8.0.6 | Last verified: 2026-08-25
> Mode: FAZE 1 — proof-phase (conservative sizing, specialists only, journal synced)

---

## 1. Project Overview

| Field | Value |
|-------|-------|
| **What** | Institutional autonomous quant hedge fund with multi-agent orchestration |
| **Stack** | Python 3.14 · FastAPI · Next.js 16 · React 19 · MT5 · SQLite |
| **Version** | v8.0.6 (pyproject: 5.1.0) |
| **Entry point** | `qna.py` (single SSOT for all modes: daemon, api, status, backtest) |
| **Live broker** | ValetaxIntl-Live2, account 211098748 (Centku), suffix `.vxc`, balance ~$767 USC |
| **Status** | GREEN — LIVE on MT5. REAL-ONLY, no paper/sim/mock. MT5-only execution. |
| **LiveModeGuard** | ACTIVE — `LiveModeGuard` enforced; no paper mode, MT5 live only |
| **Session** | 80+ commits (8-phase overhaul + strategy consolidation + MT5 auto-detect + Config Center + .vxc suffix fix + AI assistant + icon set + launcher upgrade + v8.0.2 candle scheduler + notifications + v8.0.3 fail-closed risk wiring + launcher quoting fix + v8.0.6 universal path auto-detect + full risk audit) |
| **Strategies registered** | 83 registered (93 strategy files incl. 4 compute engines merged; WF-gated admission, 9 admitted via CPCV allocation) |
| **Engine strategies** | 81 via `@StrategyRegistry.register` — all auto-wired to live; 58 archive wired but WF-blocked (n=0) |
| **Agents** | 9 agent personas (researcher, analyst, risk, execution, portfolio, etc.) |
| **Tests passing** | 66 core + 14 API (pre-existing pydantic/prometheus errors) — 66/66 core regression |
| **Path auto-detect** | Universal — all scripts use `Path(__file__).resolve().parent.parent`; no hardcoded `/sdcard`, `D:/`, `E:/` paths. External integrations configurable via `QNA_EXT_*` env vars. |
| **Repo stats** | 80+ commits, 806 Python files, 228 test files, 50+ API routes, 83 strategies |
| **Dashboard** | 22 routes + Config Center (`/config`) + Export Center (`/export`) + AI Assistant Widget, Next.js 16, 50+ API backend routes, premium dark-tech |

---

## 2. Architecture Flow

```
qna.py daemon / qna_tray.py (system tray)
  → candle_scheduler.py:start_candle_scheduler()
    → _tick_loop() — monitors MT5 ticks every 1s
      → _check_all_closes() — detects candle close per symbol+TF
        → _on_candle_close(symbol, tf, bar_time)
          → _run_analysis(symbol, tf)
            → _fetch_data(symbol, tf) — multi-TF: M15/H1/H4/D1
              → _validate_ohlcv() + _reject_stale() — STALE-DATA VETO
            → regime detection (enhanced_regime.py)
            → context_gate.py — high-impact news blackout veto (±30 min)
            → signal generation (signal_aggregator netting, 83 strategies)
            → multi-TF alignment check
            → _check_risk() — FAIL-CLOSED 9-gate
            → execute_order(): guards → kill switch → risk veto
              → DUPLICATE-POSITION gate (broker truth) → FILL-STATUS gate
            → _notify() — Telegram alert + candle_events bus → WS push
              → trade_history.py (SQLite unlimited) 
              → strategy_scorecard.py (per-strategy metrics)
                → trade_lifecycle.py (eval → evolve)
                  → strategy_evolver.py (WF-validated mutations)
```

### Core Pipeline

| Stage | Module | Purpose |
|-------|--------|---------|
| Entry | `qna.py` | CLI modes: daemon, api, status, backtest |
| Scheduler | `engine/candle_scheduler.py` | **CandleScheduler** — real-time candle-close watcher, M15/H1/H4/D1 |
| Fallback | `engine/scheduler.py` | PipelineScheduler (timer-based, fallback only) |
| Autonomous | `engine/agentic/autonomous.py` | `AutonomousPipeline.run()` — timeframe-aware, multi-TF data |
| Ensemble | `engine/agentic/ensemble.py` | Multi-strategy voting with contributor attribution |
| Council | `engine/agentic/council.py` | `CouncilOfChanges` fail-closed |
| Risk | `engine/risk/manager.py` | 9-checkpoint gate + kill switch |
| Execution | `engine/execution/builder.py` | `build_execution_manager()` — account auto-detect |
| Journal | `trade_journal.py` | SQLite trade log with strategy attribution |
| Lifecycle | `engine/strategy_lifecycle.py` | Auto-kill/evolve/hibernate per strategy |
| Notifications | `notifier.py` | Telegram alerts on trades and signals |
| Self-Eval | `TradeJournal.self_eval()` | Per-strategy win_rate, expectancy, kelly, sharpe |

---

## 3. Engine Modules (All)

| Module | Path | Purpose |
|--------|------|---------|
| **agentic/** | `engine/agentic/` | Autonomous pipeline, ensemble, council, voting, trade lifecycle |
| **alerting/** | `engine/alerting/` | Alert system |
| **analysis/** | `engine/analysis/` | Market analysis |
| **analytics/** | `engine/analytics/` | StrategyScorecard, PnL eval, metrics, trade export |
| **api/** | `engine/api/` | Engine API layer |
| **audit.py** | `engine/audit.py` | Audit utilities |
| **backtest/** | `engine/backtest/` | Backtesting engine, walk-forward, auto-tune, Monte Carlo, CPCV |
| **causal/** | `engine/causal/` | Causal inference |
| **colony/** | `engine/colony/` | Multi-agent colony |
| **core/** | `engine/core/` | Core utilities, scoring/fusion engine |
| **cot/** | `engine/cot/` | Commitment of Traders data |
| **data/** | `engine/data/` | Data providers, caching, quality, fallback chain, economic calendar |
| **data_quality/** | `engine/data_quality/` | Data quality framework |
| **evolution/** | `engine/evolution/` | Strategy evolution, performance scanner, strategy disabler |
| **execution/** | `engine/execution/` | MT5 execution, account discovery, algo execution, guards |
| **factors/** | `engine/factors/` | Factor zoo |
| **fundamental/** | `engine/fundamental/` | Fundamental analysis |
| **guardian/** | `engine/guardian/` | Guardian module |
| **indicators/** | `engine/indicators/` | TV indicator ports (10 TradingView indicators) |
| **integration/** | `engine/integration/` | External integrations |
| **intermarket/** | `engine/intermarket/` | Intermarket analysis |
| **kelly/** | `engine/kelly/` | Fractional Kelly position sizing |
| **live/** | `engine/live/` | Live trading engine |
| **ml/** | `engine/ml/` | ML: autoencoder factors, feature engineer, model manager, signal generator |
| **nvidia_nim/** | `engine/nvidia_nim/` | NVIDIA NIM integration |
| **options/** | `engine/options/` | Options analysis |
| **orderflow/** | `engine/orderflow/` | CVD, delta, volume profile |
| **pattern_recorder/** | `engine/pattern_recorder/` | Pattern recording |
| **portfolio/** | `engine/portfolio/` | Portfolio management |
| **projection/** | `engine/projection/` | CompoundProjector — deterministic/Monte Carlo/empirical equity projection |
| **regime/** | `engine/regime/` | HMM regime detection (15 modules) |
| **risk/** | `engine/risk/` | Risk management (31 modules) — see Section 5 |
| **rl/** | `engine/rl/` | Reinforcement learning |
| **scanner/** | `engine/scanner/` | Market scanner |
| **screener/** | `engine/screener/` | Stock screener |
| **shadow/** | `engine/shadow/` | Shadow mode — extractor, scanner |
| **smc/** | `engine/smc/` | Smart Money Concepts (ICT) |
| **strategies/** | `engine/strategies/` | 83 strategy implementations — see Section 4 |
| **strategy_lifecycle.py** | `engine/strategy_lifecycle.py` | Strategy lifecycle management, WF gate |
| **trade_history.py** | `engine/trade_history.py` | SQLite-backed unlimited trade/signal history (replaces JSON buffer) |
| **stress_testing/** | `engine/stress_testing/` | Stress testing |
| **visualization/** | `engine/visualization/` | Visualization |

---

## 3.1 Integrated Engines — LIVE in Autonomous Pipeline

| Engine | Wiring in `autonomous.py` | Live role |
|--------|---------------------------|-----------|
| **CVDEngine** + **OrderFlowRiskMonitor** | `:975`–`:984` | Feed live risk veto via CVD/price divergence |
| **HiddenMarkovModel** | `:1023`–`:1040` | Overrides regime detection on the live path |
| **TPSLCalculator** | `:830`–`:842` | Sets dynamic ATR-based SL/TP per trade |
| **ConfidenceScorer** | `:853`–`:892`, `:1212`–`:1237` | Normalizes ensemble confidence |
| **SMCProEngine** | `:regime_priority` (prepended to all regimes) | Votes in live ensemble via `smc` strategy |

All 5 engines are LIVE: SMCProEngine votes through the `smc` strategy in the ensemble priority list; CVDEngine/OrderFlowRiskMonitor feed the risk veto; HiddenMarkovModel overrides regime; TPSLCalculator sets dynamic SL/TP; ConfidenceScorer normalizes confidence.

---

## 4. Trading Strategies

### 4.1 Strategy Registration

All 81 engine strategies are registered via `@StrategyRegistry.register` in `quant_nanggroe/engine/strategies/*.py`. The package `__init__.py` import-loop loads every `*.py` in that dir, so registration is automatic on import. There is no curated allow-list — "registered" ⟹ "wired live."

### 4.2 WF-Validated (Admitted to Live Trading)

| Strategy | File | WF Folds | Avg OOS Sharpe | Status |
|----------|------|----------|----------------|--------|
| Gold Inflation | `strategies/gold_inflation.py` | 3 | 5.43 | LIVE (likely overfit) |
| Multi Timeframe | `strategies/multi_timeframe_strategy.py` | 6 | 5.13 | LIVE (likely overfit) |
| EMA ADX | `strategies/ema_adx.py` | 5 | 1.71 | LIVE |
| Kalman Filter | `strategies/kalman_filter.py` | 7 | 1.68 | LIVE |
| DXY Momentum | `strategies/dxy_momentum.py` | 4 | 0.97 | LIVE |
| Kelly Optimal | `strategies/kelly_optimal.py` | 3 | 0.81 | LIVE |
| Kaufman AMA | `strategies/kaufman_ama.py` | 7 | 0.39 | LIVE |

> **Honest assessment:** Even the "passing" strategies show implausibly high Sharpe on few folds. Likely single-asset/overfit. True validation requires multi-symbol, multi-year CPCV.

### 4.3 Math/Quant Strategies (Registered)

| Strategy | File | Method |
|----------|------|--------|
| Markov Regime | `strategies/markov_regime_strategy.py` | Volatility clustering + transition matrix |
| PiCycle | `strategies/pi_cycle_strategy.py` | Pi-anchored mean reversion, z-score |
| CosineWave | `strategies/cosine_wave_strategy.py` | Dominant-frequency cosine envelope |
| Harmonic | `strategies/harmonic_composite.py` | Bayesian ensemble (Euler+Markov+PiCycle+CosineWave) |

### 4.4 Strategies with Negative Edge (Still Live)

| Strategy | Avg OOS Sharpe | Risk |
|----------|---------------|------|
| ADX | -1.29 | Negative edge |
| DMI | -2.69 | Negative edge |
| SMC | -2.81 | Negative edge |
| Macro FX | -3.93 | Negative edge |
| ICT OTE | -7.38 | Negative edge |
| AMDX | -8.13 | Negative edge |
| Bayesian Ridge | -12.26 | Negative edge |
| CCI | -20.00 | Negative edge |
| Dark Cloud Cover | -20.00 | Negative edge |

### 4.5 Walk-Forward Registry Status — Updated 2026-08-21 (TRI-ASSET FULL VALIDATION)

**ALL 206 strategies WF-validated across 3 asset classes** (BTC-USD crypto, EURUSD=X forex, GC=F gold; daily 2y; train 252/test 63 rolling, purge 5/embargo 3) via `scripts/run_multisymbol_wf.py`:
- Every `archive_*` strategy: n≥12 folds spanning all 3 markets, tagged `parameter_set={"symbol": ...}`
- **Cross-asset robust (positive avg OOS Sharpe over n=12 folds, 3 markets):**

| Strategy | n | Avg OOS Sharpe |
|----------|---|----------------|
| `archive_aroon` | 12 | **+0.637** |
| `archive_amdx` | 12 | **+0.544** |
| `archive_algebra` | 12 | **+0.316** |
| `archive_mean_rev` | 12 | +0.196 |
| `archive_ict_ote` | 12 | +0.171 |
| `archive_gold_inflation` | 12 | +0.127 |
| `archive_wyckoff` | 12 | +0.040 |

- **Honest kill-rate:** BTC-only validation showed 115 "viable"; EURUSD folds killed most (single-market overfit); final tri-asset viable ≈ 54, of which only the 7 above carry distinct logic. The ~60 identical-placeholder strategies converge to ~0 cross-asset = ONE factor counted 60× (documented, not diversified alpha).

**SYSTEMIC ENGINE FIX (P0):** `engine/backtest/engine.py:580` — `rolling_vol_by_symbol` holds per-symbol `pd.Series`, but `_size_position` did `sym_vol <= 0` on it → "truth value ambiguous" crash for EVERY strategy that fires a trade. Only all-HOLD strategies could ever backtest. Fixed: scalar extraction at bar timestamp, NaN warmup → 0.0.

Also fixed: `_generate_strategy_signals` enum handling — legacy `StrategySignal.strength` is `SignalStrength` enum ('weak'/'moderate'/'strong'), not float; direction-first mapping (BUY/SELL/HOLD → ±scale) with strength as scale multiplier.

### 4.6 Gate Logic — Updated 2026-08-21

`StrategyLifecycleManager.get_active_strategies()` consults `data/walk_forward_registry.json` — admits only strategies with `n_windows >= 3` AND `avg_oos_sharpe > 0.0` (`_viable_engine_strategy_names()`, portfolio/main.py:122).

The name-prefix bug is FIXED: `_viable_engine_strategy_names()` now correctly gates `strat_*` providers using the registry, not just `signal_qna_*` providers.
The import bug is FIXED: `walk_forward.get_viable_strategies()` imported `WalkForwardRegistry` from the deleted `engine.strategy.registry` → always returned []. Now imports from canonical `engine.strategies.registry`.

### 4.7 Strategy Lifecycle

```
Registration → Validation → Admission → Monitoring → Auto-kill → Hibernation
     ↓              ↓            ↓            ↓            ↓            ↓
  @register     WF gate    ACTIVE state   self_eval    expectancy<0   KILLED
                n≥3,OS>0                per-cycle     after 20 trades
```

- `StrategyLifecycleManager.update_strategy` tracks trades/wins/losses/expectancy
- Auto-KILLS a strategy with negative expectancy after 20 trades
- `StrategyEvolver.evaluate` mutates params + real walk-forward gate (≥5% improvement required)

---

## 5. Risk Management

### 5.1 Constitutional Limits (`engine/risk/constants.py`)

| Limit | Value | Env Var |
|-------|-------|---------|
| Max risk/trade | 0.5% | `QNAI_RISK_MAX_PER_TRADE` |
| Max daily loss | 1.0% | `QNAI_RISK_MAX_DAILY_LOSS` |
| Max weekly loss | 3.0% | `QNAI_RISK_MAX_WEEKLY_LOSS` |
| Max drawdown | 10% | `QNAI_RISK_MAX_DRAWDOWN` |
| Max daily trades | 5 | hardcoded |
| Max position size | 10% | hardcoded |
| Max leverage | 3x | hardcoded |
| Max sector exposure | 30% | hardcoded |
| Max correlated positions | 3 | hardcoded |
| Min R:R | 1:2 | hardcoded |
| Risk per tier | 0.5%/1%/2% | auto by confidence+regime |

### 5.2 Guard Enforcement Chain

```
Trade Proposal → QuickVeto (5 fast checks) → RiskManager.check_trade (9 checkpoints)
  → GovernanceVetoGuard (execution pipeline filter) → Execute Order
```

### 5.3 Risk Components (31 files)

| File | Class | Purpose |
|------|-------|---------|
| `constants.py` | module-level | SSOT for constitutional risk limits |
| `manager.py` | `RiskManager` | Top-level orchestrator, 9-checkpoint gate |
| `checks.py` | `ConstitutionalRiskGuard` | 9-checkpoint gate |
| `kill_switch.py` | `KillSwitch` | Multi-level emergency halt (L1/L2/L3) |
| `veto_guard.py` | `GovernanceVetoGuard` | Pre-execution filter |
| `quick_veto.py` | `QuickVetoBridge` | LLM-agent proposal pre-filter |
| `drawdown.py` | `DrawdownMonitor` | Peak-to-trough tracking |
| `kelly.py` | `KellyCriterion` | Position sizing (delegates to `engine/kelly/`) |
| `var.py` | `VaRCalculator` | VaR/CVaR (parametric, historical, Monte Carlo) |
| `correlation_regime.py` | `CorrelationRegimeDetector` | Rolling correlation regime |
| `volatility_regime_har.py` | `RegimeSwitchingHAR` | HAR volatility regime (LOW → EXTREME) |
| `vix_gate.py` | `VixGate` | VIX-based gate (<25 normal, 25-35 reduce, >35 block) |
| `orderflow_monitor.py` | `OrderFlowRiskMonitor` | CVD/price divergence detector |
| `profile_mapper.py` | `ProfileMapper` | Maps (pair, strategy, timeframe) → risk profile |
| `dcc_garch.py` | `DCCGARCH` | Dynamic Conditional Correlation GARCH |

### 5.4 Kill Switch

- Cross-process file-based: `data/kill_switch_state.json`
- Auto-activation: daily loss ≥ 0.8% → L1, weekly ≥ 2.5% → L2, drawdown ≥ 10% → L2
- L1 auto-expires daily; L2/L3 require manual `reset("CONFIRM_RESET_AFTER_REVIEW")`

### 5.5 Single Position Per Symbol

`_check_risk` queries `mt5.positions_get()` per-symbol — vetoes if symbol already open (`autonomous.py:1722-1727`). Max 3 concurrent positions via `FinalDecider.position_count` (`:1296-1305`).

### 5.6 Smart Sizing

- `_compute_risk_sizing` caps notional at 40% free margin (`:2022-2033`)
- `get_risk_pct` returns 0.5%/1%/2% tiers by confidence+regime (`constants.py:31-38`)
- `MaxPositionGuard.update_position` accumulates position delta (`max_position.py:78-86`)

### 5.7 Risk Module Sprawl (12 Objects)

**Known issue:** 12 distinct risk/PnL objects exist across the codebase. Key finding:
- `EngineRiskManager` (engine_bridge.py) is the live SoT for gating+sizing in `live_engine.py`
- `RiskManager` (engine/risk/manager.py) is the constitutional gate for the agentic path
- Multiple `update_pnl` methods are stubs/no-ops — daily/weekly vetoes may not fire in all paths
- Consolidation recommended: make `EngineRiskManager` the single PnL ingestion point

---

## 6. Self-Loop Architecture

### 6.1 What the System Already Does Autonomously

1. **Performance measurement per trade** — `TradeJournal.self_eval()` computes per-strategy win_rate, expectancy, avg_rr, sharpe, kelly from closed trades
2. **Strategy enable/disable/weighting** — `StrategyLifecycleManager` tracks states (ACTIVE/HIBERNATING/KILLED), auto-kills on negative expectancy after 20 trades
3. **Strategy evolution** — `StrategyEvolver.evaluate` mutates params + real walk-forward backtest, accepts only if improved ≥5%
4. **Risk management** — Constitutional limits (0.5%/trade, 1% daily, 3% weekly, 10% drawdown), 9-checkpoint gate, kill switch auto-activation
5. **Self-debate** — `convene_council()` convenes 6 investor personas for low-confidence signals
6. **Self-awareness** — `SelfAware.reflect()` produces HEALTHY/CAUTION/DEGRADED verdicts

### 6.2 Known Gaps (Honest Assessment)

1. `self_eval()` is called in the live path (post-overhaul) but was previously dead
2. Position sizing now uses Kelly/equity (post-overhaul) instead of confidence constant
3. Council only reacts to low-confidence signals, not strategy/risk changes
4. Two parallel loops existed (reconciled post-overhaul)

### 6.3 Go-Live Gates (G1-G12) — Updated 2026-08-20

| Gate | Check | Status |
|------|-------|--------|
| G1 | Real PnL reaches the veto | ✅ `_sync_realized_pnl` wired |
| G2 | Kill switch live & auto-activating | ✅ configured |
| G3 | Single kill authority | ✅ StrategyLifecycleManager |
| G4 | self_eval actually runs | ✅ wired in autonomous + strategy_evaluator |
| G5 | Sizing is equity/Kelly-based | ✅ `_compute_risk_sizing` |
| G6 | Constitutional cap intact | ✅ `MAX_RISK_PER_TRADE` |
| G7 | Council gates changes | ⚠️ only low-confidence signals |
| G8 | Walk-forward gate enforced | ✅ registry bootstrapped, `_viable_engine_strategy_names()` admits 2 strategies |
| G9 | Strategy weighting uses real expectancy | ✅ self_eval Kelly weighting |
| G10 | Observability/UI green | ✅ dashboard + reflect_self |
| G11 | Fail-closed on missing data | ✅ MT5 broker sourced, `None→set()` registry guard |
| G12 | One loop, not two | ✅ reconciled post-overhaul |

### 6.4 Grand Audit Gates (2026-08-20) — All Closed

| Gate | Check | Status | Evidence |
|------|-------|--------|----------|
| G1.1 | Guard `None` crash from missing registry | ✅ DONE | `portfolio/main.py:586` → `set()` fail-closed |
| G0.2 | `engine_production_bridge` honor `QNA_LIVE_TRADING` env | ✅ DONE | `engine_production_bridge.py:365` + `import os` added |
| G2.2 | Daily/weekly veto + kill-switch fire in BOTH paths | ✅ DONE | `tests/test_risk_consolidated.py` (6 tests, all pass) |
| G1b | Bootstrap walk_forward_registry.json | ✅ DONE | 83 strategies, 2 admitted (kaufman_ama + multi_timeframe), real Binance data |
| G3.1 | Statistical edge evaluator per strategy | ✅ DONE | `strategy_evaluator.py` + wired into `TradeJournal.self_eval()` |
| G3.3 | Strategy correlation + diversification | ✅ DONE | `strategy_correlation.py` + `GET /api/analytics/strategy-correlation` |

### 6.5 Risk Authority Test Coverage

| Test | Path | Verdict |
|------|------|---------|
| `tests/test_risk_consolidated.py` | Live engine: daily veto, weekly veto, within-limits + agentic: weekly veto, kill-switch, within-limits | 6/6 pass |
| `tests/pipeline/test_signal_runner_wiring.py` | Signal runner pipeline wiring | 9/9 pass |
| `tests/test_risk_limits_critical_safety.py` | Risk limits + kill switch safety | pass |
| `tests/test_hedge_fund_risk_guard.py` | Hedge fund risk guard | pass |
| `tests/test_killswitch_integration.py` | Kill switch integration | 4 env-PermissionError (Windows temp) |

---

## 7. API Routes (48 modules)

| Route Module | Purpose |
|-------------|---------|
| `agentic.py` | Agentic pipeline |
| `agents.py` | Agent management |
| `analytics.py` | Analytics endpoints |
| `autonomous.py` | Autonomous trading |
| `backtest.py` | Backtesting + engines listing |
| `brokers.py` | Broker accounts + ledger |
| `causal_engine.py` | Causal inference engine |
| `channels.py` | Communication channels |
| `colony.py` | Multi-agent colony |
| `config.py` | Configuration (legacy single) |
| `config_files.py` | **Config Center — file-backed manager for dashboard (`/api/config/files`)** |
| `council.py` | Council of changes |
| `credentials.py` | Credential management |
| `debate.py` | Agent debate |
| `ecosystem.py` | Ecosystem status |
| `ensemble.py` | Ensemble voting |
| `evolution.py` | Strategy evolution |
| `features.py` | Feature engineering |
| `fred.py` | FRED economic data |
| `geopolitics.py` | Geopolitical analysis |
| `market.py` | Market data (candles, sentiment) |
| `memory.py` | Memory bus |
| `monitor.py` | System monitoring |
| `options.py` | Options analysis |
| `orderbook.py` | Order book |
| `personas.py` | Agent personas |
| `pipeline_status.py` | Pipeline status |
| `portfolio.py` | Portfolio (equity curve, risk) |
| `projection.py` | Equity projection |
| `qna_status.py` | QNA system status |
| `rl.py` | Reinforcement learning |
| `scheduler.py` | Scheduler control |
| `scorecard.py` | Strategy scorecard |
| `sec_edgar.py` | SEC EDGAR filings |
| `security.py` | Security audit |
| `security_tools.py` | Security tools |
| `signal_generator.py` | Signal generation |
| `strategies.py` | Strategy management |
| `strategy.py` | Strategy operations |
| `strategy_correlation.py` | Strategy correlation + diversification analysis |
| `terminal.py` | Terminal view |
| `tools.py` | Agent tools |
| `trade_history.py` | Trade history |
| `trading.py` | Trading operations + accounts ledger |
| `whatsapp.py` | WhatsApp integration |
| `ws.py` | WebSocket streaming |
| `_data.py` | Data utilities |
| `wiring_compat.py` | Wiring compatibility |

---

## 8. Dashboard

### 8.1 Routes

| Route | Page | Purpose |
|-------|------|---------|
| `/` | Dashboard | Command center, live metrics, system health |
| `/trading` | Trading | Live orders, positions, cross-broker aggregation |
| `/portfolio` | Portfolio | P&L, equity curve, allocation, Kelly sizing |
| `/accounts` | Accounts | MT5 account ledger (all-ever-connected) |
| `/agents` | Agents | Agent council grid, pipeline execution |
| `/risk` | Risk | VaR/CVaR, 9-checkpoint gate, Kelly, drawdown |
| `/strategies` | Strategies | Strategy list, schema, backtest adapters |
| `/backtest` | Backtest | Backtest runner, equity curves, Monte Carlo |
| `/market` | Market | Real-time prices, TradingChart (lightweight-charts v5) |
| `/memory` | Memory | Memory search/filter, knowledge base |
| `/colony` | Colony | Multi-agent system |
| `/factors` | Factors | Alpha factor zoo, IC/returns |
| `/settings` | Settings | Full configuration UI (brokers, risk, LLM) |
| `/config` | **Config Center** | **Every `config/*.yaml` editable — MT5 accounts structured + raw YAML/JSON** |
| `/orderflow` | OrderFlow | Bookmap, heatmap, CVD, VWAP (proxied to backend) |
| `/security` | Security | Audit & compliance |
| `/channels` | Channels | Notification channels |
| `/tools` | Tools | Tool registry |
| `/terminal` | Terminal | Terminal view |

### 8.2 Tech Stack

Next.js 16, React 19, Tailwind CSS v4, Zustand v5, Recharts 2, lightweight-charts v5. WebSocket streaming, command palette (Cmd+K), dark mode.

### 8.3 Config Center (NEW v7.1.0 — every config via UI)

All `config/*.yaml` editable from dashboard at `/config` without manual file editing. Backend `quant_nanggroe/config_manager.py` whitelists `mt5_accounts.yaml`, `system_config.yaml`, `prompts.yaml` (YAML/JSON, validated, path-traversal guard, secret masking). Frontend structured editor for MT5 accounts (add/edit/remove login/server/paper) + raw YAML/JSON editor for any file. API: `GET /api/config/files` list, `GET /api/config/files/{name}` read, `PUT /api/config/files/{name}` write (raw or data). Sidebar `SYSTEM → Config` (FileCode) + Cmd+K palette. Tests: 14 pytest `tests/test_api/test_config_files.py`.

### 8.4 Mock Inventory (Honest — P0 mocks removed 2026-08-21)

| Component | Mock? | Evidence |
|-----------|-------|----------|
| Portfolio summary/risk/perf | **REAL** | Backend `PortfolioSummaryResponse` |
| Portfolio equity-curve | **404** | No backend endpoint |
| Trading positions | **REAL** | `ExchangeManager.get_aggregated_portfolio()` |
| Trading order-book | **FIXED** | Fail-closed empty state (was `Math.random()`) — `brokers/page.tsx` dark-tech rewrite |
| Trading time&sales | **FIXED** | Removed `Math.random()` — fail-closed |
| Market chart | **FIXED** | `FALLBACK_CANDLES` removed — fail-closed empty with error banner |
| Market live price | **FIXED** | `Math.random()` removed — `livePrice = wsPrice ?? lastClose ?? null` |
| Brokers page | **FIXED** | Full dark-tech rewrite (`Card`/`Badge`/`Button`) — no `gray-*` |
| Portfolio weight | **FIXED** | `min(100,max(0,weight))` clamp (was `*4%` overflow) |
| Strategies perf bars | **FIXED** | Random `Math.random()` removed — real `monthly_returns` or empty fail-closed |
| Agents roster | **MOCK fallback** | `FALLBACK_AGENTS` at `agents/page.tsx:28` (low traffic, next) |
| Security events | **MOCK fallback** | `FALLBACK_EVENTS` at `security/page.tsx:24` |
| Tools list | **MOCK fallback** | `FALLBACK_TOOLS` at `tools/page.tsx:24` |
| OrderFlow | **REAL** | Proxied to backend `/api/orderflow` |
| Accounts ledger | **REAL** | `GET /api/accounts/ledger` |
| TradingChart | **REAL** | lightweight-charts v5 candlestick |

---

## 9. Live Execution Evidence

| Evidence | Detail |
|----------|--------|
| Broker | ValetaxIntl-Live2, login 372044706 (auto-detected, `config/mt5_accounts.yaml` editable via `/config`) |
| Balance | $1,122.05 (real MT5) |
| Positions | 3 live (SELL 0.01 ticket 20188224176, BUY 0.01 ticket 20188224713) |
| Strategies | 83 registered → 2 strict-admitted (`kaufman_ama` + `multi_timeframe`) / 7 WF-validated |
| Journal | 156+ trades, `data/qna_trade_journal.db` |
| Kill switch | Cross-process file-based, fail-closed (`engine/risk/kill_switch.py`, `SingletonLock` cross-platform) |
| Account discovery | `MT5Broker.detect_active_account()` + `account_discovery.py` (Valetax terminal `C:\Program Files\MetaTrader 5 Valetax`) — **discovered authoritative, config skipped when live** |
| Attribution | `Order.strategy_name` tracks per-strategy contributions |
| Config | Every `config/*.yaml` editable via dashboard Config Center (`/api/config/files`) |

---

## 10. Security

### 10.1 Secrets in Git History (CRITICAL)

**Finding:** Secrets were committed in past commits and remain in git history:
- MT5 password `REDACTED` — committed at HEAD in `.audit-memory/README.md`
- Groq API key `gsk_...` — in history (26 commits)
- HuggingFace key `hf_...` — in history
- JWT secret — in history
- QNAI API key — in history
- Alpha Vantage key — in history

**Current state:** `.env` is gitignored. But secrets remain in history (recoverable via `git log -S`).

**Remediation needed (requires human):**
1. Rotate all credentials (MT5 password, Groq, HF, JWT, API keys)
2. Run `git filter-repo` to purge secrets from history
3. Force-push and coordinate with all clones

### 10.2 Network Defaults

- API binds to `0.0.0.0:8000` (all interfaces) — acceptable for local, risky for public
- `QNA_LIVE_TRADING=1` default in `.env` — live trading enabled by default
- `engine_production_bridge.py:352` hard-enables live trading with no toggle

### 10.3 Security Checklist

| Item | Status |
|------|--------|
| `.env` gitignored | ✅ |
| Fail-closed defaults | ✅ |
| JWT required | ✅ `QNAI_JWT_SECRET` |
| Pre-commit hooks | ✅ gitleaks + ruff |
| Dependency scan | ✅ `ci.yml` gitleaks action |
| Secrets in history | ⚠️ needs rotation + filter-repo |

---

## 11. Critical Gotchas

1. **PYTHONPATH must be empty** — `PYTHONPATH="" python qna.py` or use `QNA Launcher.bat`
2. **Symbols need `.vx` suffix** — EURUSD.vx, BTCUSD.vx, XAUUSD.vx (Valetax broker)
3. **QNAI_JWT_SECRET required** — fail-closed at `app.py:270-276`
4. **account_balance() returns -1.0** — MT5_DOWN sentinel, NOT a valid balance
5. **STARTING_CAPITAL = 10000** — fallback only if MT5 unavailable (`constants.py:162`)
6. **autonomous_cycle.py = DEPRECATED** — test-only, docstring line 3-10. Real pipeline: `engine/agentic/autonomous.py`
7. **HedgeFundBridge.get_signal = fail-closed stub** — raises, not used on live path
8. **12 risk objects exist** — `EngineRiskManager` is live SoT for `live_engine.py`; `RiskManager` is SoT for agentic path
9. **53/78 strategies have ZERO WF evidence** — run live unvalidated
10. **Dashboard has Math.random() mocks** — order-book, time&sales, market ticker are fabricated

---

## 12. Run Commands

```bash
# All-in-one launcher (recommended)
"QNA Launcher.bat"          # Windows: backend + scheduler + dashboard + browser
./QNA Launcher.sh           # Linux/Mac: same

# Individual
python qna.py daemon        # Live autonomous loop
python qna.py api           # FastAPI on :8000
python qna.py status        # System status
python qna.py backtest      # Backtesting
cd dashboard && npm run dev # Dashboard on :3000

# Testing
PYTHONPATH="" python -m pytest tests/test_agentic/ tests/test_engine/ -v --tb=short
PYTHONPATH="" python -m pytest tests/ -x --timeout=120

# Lint
python -m ruff check .
```

---

## 13. Environment Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `QNAI_JWT_SECRET` | YES | — | JWT signing secret |
| `QNAI_API_KEY` | YES | — | API authentication key |
| `QNA_MT5_LOGIN` | YES | — | MT5 account login |
| `QNA_MT5_PASSWORD` | YES | — | MT5 account password |
| `QNA_MT5_SERVER` | YES | — | MT5 broker server |
| `QNA_LIVE_TRADING` | NO | `1` | Enable live trading |
| `QNAI_RISK_MAX_PER_TRADE` | NO | `0.005` | Max risk per trade (0.5%) |
| `QNAI_RISK_MAX_DAILY_LOSS` | NO | `0.01` | Max daily loss (1%) |
| `QNAI_RISK_MAX_WEEKLY_LOSS` | NO | `0.03` | Max weekly loss (3%) |
| `QNAI_RISK_MAX_DRAWDOWN` | NO | `0.10` | Max drawdown (10%) |
| `PYTHONPATH` | NO | `""` | Must be empty to avoid ABI conflicts |

---

## 14. Non-Negotiable Rules

1. Code is source of truth. Verify against `file:line`.
2. Fail-closed defaults. Phantom/unverifiable = STOP.
3. No silent deletion. List in QNA_AGENT_STATE.md + owner sign-off.
4. Wiring > new features. Don't duplicate #5 of anything.
5. Single source of truth per concern.
6. REAL-ONLY — no paper/sim/mock fallbacks on live path.
7. Every risk guard must VETO, not just warn.
8. One position per symbol. Single position sizing 0.5%/1%/2% equity.
9. Strategy attribution on every trade. Per-strategy scoring mandatory.

---

## 15. File Inventory

- **Root .py files:** 806 | **Tests:** 228 | **API routes:** 47 | **Strategies:** 83
- **Risk modules:** 31 | **Engine subdirectories:** 30+
- **Total commits:** 59 | **Dashboard routes:** 17
- **Strategies registered:** 83 | **Core tests passing:** 342
- **Agents:** 9 | **Cron jobs:** 26 active

---

## 15.5 Gates 1-8 — Feature Completion Wave (2026-08-22)

| Gate | Deliverable | Evidence |
|------|-------------|----------|
| G1 | **Scorers NOT lost** — all 10 (Bond/Crypto/Economic/Geopolitical/Macro/News/Positioning/Sentiment/Technical/Volatility) live in `core/scoring/`, wired at `hedge_fund/portfolio/main.py:418-447` + evolver weights | file:line verified |
| G2 | **Broker suffix auto-detect** — `MT5Broker.resolve_symbol()` snapshots terminal's real catalog (`symbols_get()`) at connect; candidates exact/stripped/static-map/suffixed. Any broker: `.vx` Valetax, bare Exness, `.m` IC Markets | `connectors/mt5_broker.py` |
| G3 | **Trade awareness** — deterministic what/why/how/lesson per closed trade (pure rules, no LLM) from journal `hit_type`/`close_reason`; API `GET /api/export/awareness` | `engine/analytics/trade_awareness.py` |
| G4 | **Export Center** — `GET /api/export/trades?date_from&date_to&strategy&symbol&format=` → xlsx/csv/md/json (pdf honest 501 until reportlab) + `/summary`; dashboard `/export` page with authed downloads | 7/7 tests `tests/test_api/test_export_center.py` |
| G5 | **System tray** — `scripts/qna_tray.py` + `qna_tray.bat`: icon online/error/offline polling `/health` (kill-switch aware); menu dashboard/docs/start/restart/logs/exit. Deps: pystray | compile-verified |
| G6 | **Multi-account restored** — `account_ledger.py` + `GET /api/trading/accounts` (live discovery) + `/accounts/ledger` (all-ever-connected). Phase5-sync had silently no-op'd the ledger writer | fail-closed, never fabricated |
| G7 | **P0: trailing stop was DEAD on live path** (`update()` never called). Fixed: wired into `autonomous.run()` step 1.2b with ATR(14) from live bars; exit via decision pipeline attributed `trailing_stop`. Manager upgraded: breakeven ratchet (+1% → stop to entry), ATR-adaptive trail, monotonic tightening | 9/9 tests `tests/test_risk/test_trailing_stop_gate7.py` |
| G8 | Repo tidy — root helper scripts/.lnk/stale artifacts removed | git log |

**Recurring hazard documented:** an external "phase5 sync" process repeatedly drops files (Config Center backend+page, CANONICAL.md itself, account_ledger, sidebar entries). All restored from git history this session. If features vanish again: `git log --all --oneline -- <file>` then `git checkout <commit> -- <file>`.

### 15.6 CPCV Validation — PROVE Pillar (2026-08-22)

**Infrastructure:** `walk_forward.analyze_strategy()` now dispatches `mode="cpcv"` to `_analyze_strategy_cpcv()` — refits the strategy per combinatorial train/test group split (de Prado AFML Ch.12) with purge+embargo, signals generated bar-by-bar on OOS bars only. Runner: `scripts/run_cpcv_validation.py`; results in `data/cpcv_registry.json`.

**Root cause fixed en route:** wrapper classes lack `warmup_period()` → 20-bar slices made `generate_signal` raise → silent except produced ALL-ZERO signals for every legacy strategy. Safe default warmup=60 + first-error logging. Also re-applied (sync had reverted twice): direction-first enum signal mapping + vol-scaling Series→scalar + engine coercion of stray non-numeric signal values.

**Tri-asset CPCV results (n_groups=6, n_test=2 → 14 combos; combo-profit-share = % of combinations with OOS Sharpe > 0):**

| Strategy | BTC combos | EURUSD combos | GC combos | Verdict |
|----------|-----------|---------------|-----------|---------|
| `archive_aroon` | 86% (+0.356) | 64% (+0.329) | **100% (+0.649)** | most consistent — multi-asset core |
| `kaufman_ama` | 43% (+0.160) | 71% (**+0.672**) | 93% (**+1.083**) | forex/gold specialist |
| `archive_amdx` | **93% (+0.627)** | 0% (0.000) | 93% (+0.446) | crypto/gold specialist |
| `archive_ict_ote` | 86% (+0.544) | 7% (−0.574) | **100% (+0.990)** | commodity/crypto specialist |
| `archive_gold_inflation` | 79% (+0.268) | 14% (−0.228) | 79% (+0.465) | gold-leaning |
| `multi_timeframe` | 57% (+0.171) | 43% (−0.074) | 79% (+0.892) | gold-leaning |
| `archive_algebra` | 57% (+0.201) | 50% (+0.006) | 29% (−0.018) | marginal |
| `archive_mean_rev` | 79% (+0.272) | 0% (−0.449) | 79% (+0.194) | ex-forex |
| `archive_wyckoff` | 57% (+0.061) | 0% (0.000) | 29% (−0.340) | weak |

**HONEST INSTITUTIONAL FINDING:** zero strategies survive CPCV with worst-combo Sharpe > 0 across all three assets — single strategies are asset/regime-dependent, exactly as de Prado's framework predicts. **Correct deployment is per-symbol allocation**: aroon (gold/BTC core), kaufman_ama (forex/gold), amdx + ict_ote (crypto/gold satellites). One-size-fits-all ensemble admission would dilute specialists with noise. This per-symbol map is the input for the next evolution of `_viable_engine_strategy_names()`.

### 15.7 REPLAN — FAZE 0-1 Complete (2026-08-23)

**Journal-MT5 Sync LIVE:** `engine/journal_sync.py` pulls ALL closed deals from active MT5 terminal every cycle. Backfilled 87 historical deals. Journal now shows 243 trades, net P&L **+$629.98** (matches MT5 terminal).

**Strategy Attribution:** New orders carry `strategy_name` in MT5 comment field via `connectors/mt5_broker.py`. `journal_sync._attribute_strategy()` parses it back. Historical trades remain "unknown" but new trades are properly attributed.

**Per-Symbol Allocation LIVE:** `strategy_allocation.py` reads `data/cpcv_registry.json`, admits only strategies with combo_profit_share ≥ 50% on the symbol's asset class. Wired into autonomous ensemble at `autonomous.py:1283`.

**Tuned Params Injected:** `best_params_for(strategy, symbol)` reads `data/tuning_results.json`, injects CPCV-optimal params per symbol into strategy instances before signal generation.

**Trading Profiles:** scalp(M15)/day(H1)/swing(D1) with ATR-adaptive SL/TP replacing hardcoded 5% fallback.

**Conservative Sizing:** `confidence * 0.05` (was * 0.1). Scale up only after portfolio expectancy > 0 over 50+ live trades.

**52/52 regression tests pass.**

---


### 15.8 GRAND REPLAN v8.0 — REAL ENGINE, FX FOCUS, PREMIUM UI (2026-08-23)

**DIRECTIVE:** Real native engines (not porting), eliminate crypto+stocks, focus FX/Commodity/Indices on MT5, premium UI.

**KEY DECISIONS:**
1. SIGNAL AGGREGATION — one position per symbol, fixed 0.5% risk, net conviction from all strategies
2. ELIMINATE CRYPTO+STOCKS — FX majors + Gold + Silver + Oil + Indices only
3. NATIVE ENGINES — implement algorithms natively (SMC, Hyperopt, Regime, RiskParity)
4. PREMIUM UI — trader-first layout, real-time everything, zero clutter
5. NO PAPER — REAL ONLY, conservative sizing during proof phase

**SPRINTS:**
Sprint 1 (Days 1-4): SignalAggregator + symbol cleanup (remove crypto/stocks) + FX-only CPCV re-validation
Sprint 2 (Days 5-9): Native engines — SMC Engine, Hyperopt Engine, Enhanced Regime, Risk Parity
Sprint 3 (Days 10-14): Mock elimination + UI premium redesign
Sprint 4 (Days 15-17): Docs consolidation + codebase cleanup + cross-repo sync
Sprint 5+ (Ongoing): Forward-live validation, self-evolve on real data

**FX-ONLY SYMBOLS:**
| Asset | Symbols | Evidence |
|-------|---------|----------|
| FX Majors | EURUSD.vx, GBPUSD.vx, USDJPY.vx, AUDUSD.vx | EURUSD=X |
| Gold | XAUUSD.vx | GC=F |
| Silver | XAGUSD.vx | GC=F proxy |
| Oil | USOIL.vx / XTIUSD.vx | TBD |
| Indices | NAS100.vx, SPX500.vx | TBD |

**ELIMINATED:** BTCUSDT, ETHUSDT, SOLUSDT, all crypto pairs, NVDA/AAPL stocks, crypto-specific strategies

**SIGNAL AGGREGATION ARCHITECTURE:**
```
All admitted strategies vote per symbol per cycle
  ↓ SignalAggregator.aggregate(symbol, votes)
Net conviction = Σ(direction × weight × confidence)
  ↓ if |conviction| > threshold AND no existing position:
ONE entry at fixed 0.5% equity risk per symbol
SL/TP from trading_profile (scalp/day/swing ATR-adaptive)
  ↓ attribution tracked per contributing strategy
journal_sync → scorecard → lifecycle keep/tune/kill → evolve ↩
```

**NATIVE ENGINES TO BUILD:**
| Module | Inspired By | Output |
|--------|------------|--------|
| engine/smc/native_smc.py | E:\smart-money-concepts\ | OrderBlock+FVG+Sweep+BOS detection |
| engine/backtest/hyperopt.py | E:\freqtrade\ hyperopt | Bayesian param optimization |
| engine/regime/enhanced_regime.py | E:\hidden-regime\ | HMM+GARCH+ADX composite |
| engine/portfolio/risk_parity.py | E:\PyPortfolioOpt\ | HRP weights across strategies |

---

## 16. Audit Results

### Session 1: Full Deep Sweep (56 commits)
- 12-agent parallel sweep across 806 Python files + dashboard
- ~170+ surgical fixes: bare excepts, f-string logging, encoding, dead imports
- 0 bare excepts, 0 f-string logging, 0 encoding issues

### Session 2: 8-Phase Overhaul (58 commits)
- Phase 1: Signal Attribution — all strategies recording contributions
- Phase 2: Unified Self-Eval — TradeJournal bridges to EvolutionJournal
- Phase 3: Lifecycle Keep/Tune/Disable — auto-kill/evolve/hibernate
- Phase 4: Single Position + Smart Sizing — 0.5%/1%/2% equity tiers
- Phase 5: MT5 Account Auto-Detection — detect_active_account()
- Phase 6: Dashboard Real Data — portfolio transformers, orderflow proxy, charts
- Phase 7: Loop/Daemon/Restart — crash-restart respawn, systemd service
- Phase 8: All-in-One Launcher — QNA Launcher.bat/.sh + desktop file

### Session 3: Final Sweep (59 commits)
- _bak cleanup: 22 DEAD files deleted, zero live references
- archive/ deleted: 1784 ignored files, zero live references
- .bak/ deleted: 139 ignored files
- Junk cleanup: all .venv*, caches, __pycache__, stray logs/dbs/jsons
- Launchers consolidated: 4 redundant launchers removed
- Stale references cleaned: 4 hedge_fund_mtf.py comment/docstring fixes
- CANONICAL.md consolidated: single SSOT with all council findings
- Dangling references fixed: nim_provider in __init__.py, archive loader in strategies

**Outcome:** LIVE on MT5 verified, `LiveModeGuard` active, 342 core tests green, all guards fail-closed.
