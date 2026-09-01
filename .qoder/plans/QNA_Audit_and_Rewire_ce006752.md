# QNA Deep Code Audit -- Every Stub, Mock, and Broken Wiring

## Category 1: API Route Stubs (FIXME in code)

Two API endpoints explicitly marked `FIXME: Stub` returning hardcoded zeros:

**File: `quant_nanggroe/api/routes/portfolio.py` line 136-150**
- `get_portfolio_performance()` returns `{"total_return": 0.0, "_stub": True}` 
- Fix: Wire to `engine/analytics/pnl_evaluator.py` (already has `realized_pnl` calculation) and `engine/portfolio/` for equity curve data

**File: `quant_nanggroe/api/routes/market.py` line 182-194**
- `get_pressure()` returns `{"buy_pressure": 0.55, "_stub": True}`
- Fix: Wire to `engine/strategies/volume_delta.py` (VolumeDelta/CVD strategy already computes buy/sell pressure)

## Category 2: Colony Workers -- ALL 4 Are Stubs

**File: `quant_nanggroe/engine/colony/worker.py`**
All 4 concrete workers do nothing (`asyncio.sleep(0.01)` + return fake data):
- `StrategyWorker.execute()` -- returns `{"signal": "hold", "confidence": 0.5}` (fake)
- `RiskWorker.execute()` -- returns `{"passed": True, "score": 0.0}` (fake)
- `DataWorker.execute()` -- returns `{"rows": 0, "columns": []}` (fake)
- `ExecutionWorker.execute()` -- returns `{"filled": False, "order_id": None}` (fake)

Fix: Wire each worker to real engine modules:
- StrategyWorker -> `ProductionStrategyRunner.generate_signals()`
- RiskWorker -> `RiskEnforcer` (kill switch, drawdown, position sizing)
- DataWorker -> `UnifiedDataProvider` / `DataManager`
- ExecutionWorker -> `UnifiedExecutionRouter.execute()`

## Category 3: Duplicate COT Provider -- One Is Broken

**Broken: `quant_nanggroe/engine/data/cot_provider.py`** (54 lines)
- `COTProvider.fetch()` raises `NotImplementedError`
- `COTAnalyzer.generate_signal()` always returns `"neutral", 0.0`
- Still imported by 3 modules:
  - `engine/live/adaptive_integration.py:439` -> `COTProvider()`
  - `engine/fundamental/cot.py:22` -> `COTDataProvider`
  - `engine/strategies/cot_strategy.py:39` -> `COTProvider(), COTAnalyzer`

**Working: `quant_nanggroe/engine/cot/`** (real COTAnalyzer + COTFetcher with `cot_reports`)
- Used correctly by: `engine_production_bridge.py`, `engine/causal/master_engine.py`

Fix: Redirect the 3 broken imports from `engine/data/cot_provider.py` to `engine/cot/` (the real one). Then delete or deprecate `engine/data/cot_provider.py`.

## Category 4: Daemon COT Fetcher -- NotImplementedError

**File: `quant_nanggroe/daemons/cot_fetcher.py` line 67-74**
- `_parse_cftc_response()` raises `NotImplementedError` -- HTML parsing not implemented
- Fix: Implement with BeautifulSoup4 (already a dependency) OR redirect to `engine/cot/cot_fetcher.py` which already has working CFTC parsing via `cot_reports`

## Category 5: Agentic Adapters -- TradingAdapter Is Placeholder

**File: `quant_nanggroe/engine/agentic/adapters.py` line 601-614**
- `TradingAdapter.fetch_signal()` always returns `Signal(Bias.NEUTRAL, 0.1, "trading")`
- Listed in `ALL_ADAPTERS` -- contributes a useless NEUTRAL vote to every signal
- Fix: Wire to real `hedge_fund/signals/aggregator.py` aggregate() OR remove from ALL_ADAPTERS

## Category 6: Model Registry Stubs

**File: `quant_nanggroe/engine/model_registry.py`**
- `XGBoostModel` (line 450) -- falls back to "simple approximation" when xgboost not installed
- `SimpleTransformerStub` (line 699) -- "simplified transformer stub for demonstration"
- `SimpleTransformerStub` docstring says "Do not use for live trading"
- Fix: Mark these clearly as non-production, or remove from model registry if not usable

## Category 7: Signal Duck-Type Hack

**File: `quant_nanggroe/pipeline/execution.py` line 279-290**
- `_SignalStub` class exists because `ProductionExecutionManager.execute_signal()` expects a duck-typed signal object instead of a proper type
- Fix: Replace `_SignalStub` with the real `Signal` dataclass from `pipeline/signal.py` and update `execute_signal()` to accept it

## Category 8: Strategy Registration Gap (59 strategies not registered)

84 strategy files in `engine/strategies/` but only ~25 have `@StrategyRegistry.register`.
Files WITHOUT registration (not loaded by ProductionStrategyRunner):
- adaptive_moving_average, adx_strategy, algebra, alternative_data_signals, amdx, aroon_strategy, atr_breakout, bayesian_ridge, bollinger_squeeze, camarilla_pivot, carry_trade, cci_strategy, choppiness_index, commodity_trend, cot_strategy, crypto_funding, crypto_specific, dark_cloud, dark_pool_flow, dema_strategy, dmi_strategy, doji_pattern, dxy_momentum, elder_ray, elder_triple_screen, em_carry, ema_adx, engulfing_pattern, entropy_strategy, evening_star, ewma_vol, factor_model_strategy, fibo_strategy, fibonacci, fibonacci_arc, fibonacci_extension, fibonacci_fan, fibonacci_retracement, fibonacci_time, fundamental_strategy, garch_vol, gene_loader, gold_inflation, ict, microstructure_alpha, msnr, pairs_trade_strategy, self_finetune, statistical_arbitrage, strategy_evolver, tsmom_strategy, unified_retail, dhaher_system (loaded explicitly in __init__.py but check registration)

Fix: Add `@StrategyRegistry.register` decorator to each strategy class that lacks it. Each file already has a class extending `Strategy` -- just needs the decorator.

## Category 9: live_engine.py Uses Deprecated Strategy Path

**File: `quant_nanggroe/live_engine.py` line 51-52**
```python
from quant_nanggroe.strategies.trend_follow import TrendFollow
from quant_nanggroe.strategies.tsmom import TSMOM
```
- `quant_nanggroe/strategies/` has only 5 files (trend_follow, tsmom, pairs_trade, xgboost_alpha)
- The real 84 strategies live in `quant_nanggroe/engine/strategies/`
- `QNA_USE_ADAPTIVE_PIPELINE` flag (line 24) enables adaptive pipeline, but the base imports are still from the deprecated path
- Fix: Verify adaptive pipeline loads from `engine/strategies/` registry. If so, remove the deprecated direct imports.

## Category 10: Credential Manager Stub References

**File: `quant_nanggroe/security/credential_manager.py`**
- Line 126: `"quant_nanggroe/connectors/web3_plugin.py (stub)"` -- references non-existent file
- Line 135: `"quant_nanggroe/connectors/github_integration.py (stub)"` -- references non-existent file
- Fix: Remove these ServiceDef entries or create the actual connector modules

## Category 11: hedge_fund/utils/indicators.py -- Minimal (17 lines)

Only has `calc_atr()` which requires live MT5. No fallback, no real value.
- Fix: Either wire to `quant_nanggroe/indicators/` module (if exists) or remove and let callers use strategy-level indicators

## Category 12: Exchange Broker Doc Placeholders

Multiple exchange files use `<placeholder>` in docstring examples:
- `exchange/factory.py` -- docstrings show `api_key="<placeholder>"`
- `exchange/mt5_broker.py` -- fallback init uses placeholder keys
- `exchange/solana/broker.py`, `exchange/polymarket_broker.py`, `exchange/ccxt_broker.py`

These are documentation/fallback defaults, not runtime issues. The real keys come from env vars.
- Fix: Replace `<placeholder>` with clear `""` + comment explaining env var requirement

## Execution Order (by impact)

1. **Category 8** -- Register all 59 unregistered strategies (biggest alpha unlock)
2. **Category 3** -- Fix duplicate COT provider (3 modules broken)
3. **Category 1** -- Wire 2 API stubs to real engines
4. **Category 2** -- Wire 4 colony workers to real engines
5. **Category 4** -- Fix daemon COT fetcher NotImplementedError
6. **Category 5** -- Fix TradingAdapter placeholder
7. **Category 9** -- Clean up live_engine.py deprecated imports
8. **Category 7** -- Replace _SignalStub with proper Signal type
9. **Category 6** -- Audit model registry stubs
10. **Category 10** -- Clean credential manager stub references
11. **Category 11** -- Fix indicators.py
12. **Category 12** -- Clean exchange placeholder docs

---

> **SSOT:** `CANONICAL.md` v8.0.19 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, launch.bat 1, vector 6 modul
