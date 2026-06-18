# Quant Nanggroe AI — API Reference

## Kelly Criterion (`quant_nanggroe.engine.kelly`)

### Base (`kelly/base.py`)
- `BaseKelly(config)` — Abstract base for all Kelly variants
- Methods: `compute(returns)`, `validate(params)`, `to_dict()`

### Fractional (`kelly/fractional.py`)
- `FractionalKelly(base_kelly, fraction)` — Fractional Kelly with configurable aggressiveness
- `compute(returns, fraction=None)` — Scale full Kelly by fraction

### Bayesian (`kelly/bayesian.py`)
- `BayesianKelly(prior_alpha, prior_beta)` — Bayesian Kelly with posterior updating
- `compute(returns)`, `update_posterior(returns)`

### Drawdown-Controlled (`kelly/drawdown.py`)
- `DrawdownKelly(base_kelly, max_drawdown, lookback)` — DD-limited position sizing
- `compute(returns)`, `current_exposure()`

### Multi-Asset (`kelly/multi_asset.py`)
- `MultiAssetKelly(kelly_models, correlation_threshold)` — Multi-asset allocation
- `compute(returns_matrix)`, `weights()`, `rebalance()`

### Adaptive (`kelly/adaptive.py`)
- `AdaptiveKelly(adaptation_rate)` — Adaptively adjusts fraction based on recent performance
- `compute(returns)`, `adapt(performance_signal)`

### Optimal F (`kelly/optimal_f.py`)
- `OptimalF()` — Ralph Vince optimal-f computation
- `compute(trades)`, `f_value()`

### Correlation (`kelly/correlation.py`)
- `CorrelationKelly(base_kelly, corr_matrix, max_corr)` — Correlation-aware sizing
- `compute(returns)`, `diversification_ratio()`

### Backtest Integration (`kelly/backtest_integration.py`)
- `KellyBacktestBridge(kelly_model, backtest_engine)` — Kelly → backtest bridge
- `run_backtest(returns, params)`, `report()`

## Regime Detection (`quant_nanggroe.engine.regime`)

### HMM Detector (`regime/hmm_detector.py`)
- `HMMRegimeDetector(n_regimes, n_iter)` — Hidden Markov Model regime detection
- `fit(data)`, `predict(data)`, `current_regime()`, `transition_matrix()`

### Ensemble (`regime/ensemble.py`)
- `EnsembleRegimeDetector(detectors, voting)` — Ensemble voting across detectors
- `fit(data)`, `predict(data)`, `confidence()`

### Volatility Clustering (`regime/volatility_clustering.py`)
- `VolatilityClustering(lookback, threshold)` — Volatility-based regime splitter
- `fit(data)`, `current_regime()`

### Correlation Regime (`regime/correlation_regime.py`)
- `CorrelationRegimeDetector(window)` — Correlation-based regime detection
- `fit(returns_matrix)`, `regime_label()`

### Macro Regime (`regime/macro_regime.py`)
- `MacroRegimeDetector()` — Macro indicator-driven regime classifier
- `fit(macro_data)`, `predict(macro_data)`

### Regime Store (`regime/regime_store.py`)
- `RegimeStore()` — Persistent regime state tracking
- `save(regime, timestamp)`, `load()`, `history()`

### Strategy Selector (`regime/strategy_selector.py`)
- `RegimeStrategySelector(regime_detector, strategy_map)` — Maps detected regimes to strategies
- `select(data)`, `add_mapping(regime, strategy)`

## Strategy (`quant_nanggroe.engine.strategy`)

### Regime Strategy (`strategy/regime_strategy.py`)
- `RegimeAdaptiveStrategy(regime_selector, base_strategy)` — Regime-adaptive trading strategy
- `generate_signals(data)`, `adjust_params(regime)`

### Schema (`strategy/schema.py`)
- `StrategySchema()` — Strategy configuration schema and validation
- `validate(config)`, `defaults()`

### Parser (`strategy/parser.py`)
- `StrategyParser()` — Parse strategy definitions from config/dict
- `parse(config)`, `to_dict()`

### Loader (`strategy/loader.py`)
- `StrategyLoader()` — Load strategies from files or registry
- `load(name)`, `list_available()`

### Backtest Adapter (`strategy/backtest_adapter.py`)
- `StrategyBacktestAdapter(strategy)` — Bridge strategy to backtest engine
- `run(data)`, `metrics()`

### Hermes Lifecycle (`strategy/hermes_lifecycle.py`)
- `HermesLifecycleManager()` — Strategy lifecycle for Hermes quant system
- `init()`, `start()`, `stop()`, `status()`

## Stress Testing (`quant_nanggroe.engine.stress_testing`)

### Monte Carlo (`stress_testing/monte_carlo.py`)
- `MonteCarloSimulator(n_simulations, horizon, method)` — GBM, jump-diffusion, regime-switching
- `run(params)`, `summary()`, `percentile(level)`

### Historical Scenarios (`stress_testing/historical_scenarios.py`)
- `HistoricalScenarioRunner(scenarios)` — 5 crisis scenario replay
- `run(portfolio)`, `scenario_list()`

### Historical (`stress_testing/historical.py`)
- Legacy wrapper for historical scenario testing

### EWHS (`stress_testing/ewhs.py`)
- `EWHSVaR(decay_factor, confidence)` — Exponentially weighted VaR/CVaR
- `compute(returns)`, `var(level)`, `cvar(level)`

### Sensitivity (`stress_testing/sensitivity.py`)
- `SensitivityAnalyzer(base_params, bounds)` — What-if parameter perturbation
- `analyze(fn, params)`, `tornado_chart()`

### VaR/CVaR (`stress_testing/var_cvar.py`)
- `VaRCVARCalculator(confidence, method)` — Unified VaR/CVaR computation
- `compute(returns)`, `var(level)`, `cvar(level)`

### Scenario Generator (`stress_testing/scenario_generator.py`)
- `ScenarioGenerator()` — Generate synthetic stress scenarios
- `generate(n_scenarios)`, `add_shock(type, magnitude)`

### Stress Reporter (`stress_testing/stress_reporter.py`)
- `StressReporter(results)` — Format stress test results
- `report()`, `to_dataframe()`, `plot()`

## Pattern Recognition (`quant_nanggroe.engine.pattern_recorder`)

### Matrix Profile (`pattern_recorder/matrix_profile.py`)
- `MatrixProfileDetector(window_size)` — STUMPY-based matrix profile
- `fit(data)`, `motifs(n)`, `discords(n)`, `regime_changes(threshold)`

### DTW (`pattern_recorder/dtw.py`)
- `DTWMatcher()` — Dynamic Time Warping similarity search
- `match(query, series)`, `distance(a, b)`, `warp_path()`

### DTW Matcher (`pattern_recorder/dtw_matcher.py`)
- `DTWPatternMatcher()` — Higher-level DTW pattern matching with templates
- `register_template(name, pattern)`, `find_matches(series)`

### Embedding (`pattern_recorder/embedding.py`)
- `EmbeddingSimilarity(encoder, metric)` — Embedding-based pattern similarity
- `embed(series)`, `similarity(a, b)`, `search(query, corpus)`

### Recurrence Plot (`pattern_recorder/recurrence_plot.py`)
- `RecurrencePlotAnalyzer(threshold, dimension)` — RQA for regime change detection
- `compute(series)`, `determinism()`, `laminarity()`, `entropy()`

### Registry (`pattern_recorder/registry.py`)
- `PatternRegistry()` — Central registry of known patterns
- `register(name, pattern)`, `lookup(query)`, `list()`

## Execution (`quant_nanggroe.engine.execution`)

### Base (`execution/base.py`)
- `BaseExecutionModel()` — Abstract execution model
- `schedule(order)`, `cost()`, `market_impact()`

### Almgren-Chriss (`execution/almgren_chriss.py`)
- `AlmgrenChriss(horizon, urgency, participation)` — Optimal execution with market impact
- `schedule(order)`, `trading_trajectory()`, `cost_analysis()`
- Strategies: TWAP, VWAP, Implementation Shortfall, Adaptive

### Order (`execution/order.py`)
- `Order(symbol, side, quantity, order_type)` — Order data model
- `to_dict()`, `validate()`

### Fill (`execution/fill.py`)
- `Fill(order_id, price, quantity, timestamp)` — Fill data model
- `cost()`, `slippage(reference_price)`

### Manager (`execution/manager.py`)
- `ExecutionManager(model, broker)` — High-level execution orchestrator
- `execute(order)`, `cancel(order_id)`, `status(order_id)`

### Hermes Execution (`execution/hermes_execution.py`)
- `HermesExecutionEngine()` — Hermes-integrated execution with lifecycle
- `start()`, `stop()`, `submit(order)`, `orders()`

## Data Providers (`quant_nanggroe.engine.data`)

### Provider Interface (`data/provider_interface.py`)
- `DataProviderInterface()` — Abstract base for all providers
- `fetch(symbol, start, end)`, `available_symbols()`, `health()`

### Base Provider (`data/providers/base_provider.py`)
- `BaseDataProvider(config)` — Common provider logic with rate limiting
- `fetch()`, `rate_limit()`, `cache_key()`

### Provider Registry (`data/provider_registry.py`)
- `ProviderRegistry()` — Registry of available data providers
- `register(name, provider)`, `get(name)`, `list()`, `prioritize(order)`


### Supported Providers
| Provider | Module | Asset Classes |
|----------|--------|---------------|
| Yahoo Finance | `providers/yfinance.py` | Stocks, ETFs, FX |
| Alpha Vantage | `providers/alpha_vantage.py` | Stocks, FX, Crypto |
| Binance | `providers/binance.py` | Crypto |
| CoinGecko | `providers/coingecko.py` | Crypto |
| CCXT (FMP) | `providers/fmp.py` | Crypto, FX |
| Finnhub | `providers/finnhub.py` | Stocks, ETFs |
| Polygon | `providers/polygon.py` | Stocks, Options |
| Twelve Data | `providers/twelevedata.py` | Stocks, ETFs, FX |
| FRED | `providers/fred.py` | Macroeconomic |
| World Bank | `providers/worldbank.py` | Macroeconomic |
| BLS | `providers/bls.py` | Labor statistics |
| GDELT | `providers/gdelt.py` | News/events sentiment |

### Data Manager (`data/data_manager.py`)
- `DataManager(provider_registry)` — Unified data interface
- `get(symbol, start, end, source)`, `available_sources()`, `clear_cache()`

### Fallback Chain (`data/fallback_chain.py`)
- `FallbackChain(providers, circuit_breaker)` — Automatic provider fallback with circuit breaker
- `fetch(symbol, start, end)`, `status()`, `reset()`

### Caching (`data/caching.py`)
- `DataCache(ttl, backend)` — Multi-tier caching (memory + disk)
- `get(key)`, `set(key, value)`, `invalidate(pattern)`

### Normalizer (`data/normalizer.py`)
- `DataNormalizer()` — Standardize data across providers
- `normalize(data, target_format)`, `column_map()`

### Rate Limiter (`data/rate_limiter.py`)
- `RateLimiter(max_calls, period)` — Token bucket rate limiter
- `acquire()`, `release()`, `wait_time()`

### Hermes Market Data (`data/hermes_market_data.py`)
- `HermesMarketData(data_manager)` — Hermes-integrated market data layer
- `get_price(symbol)`, `get_history(symbol, period)`, `stream(symbol)`

## Visualization (`quant_nanggroe.engine.visualization`)

### Chart Factory (`visualization/chart_factory.py`)
- `ChartFactory()` — Plotly chart generation
- `line(data, title)`, `candlestick(ohlc)`, `heatmap(matrix)`, `histogram(data, bins)`

### Charts (`visualization/charts.py`)
- `Charts()` — Additional chart types and utilities
- `portfolio_performance()`, `drawdown_chart()`, `correlation_heatmap()`

### Dashboard (`visualization/dashboard.py`)
- `QNADashboard(config)` — Interactive QNA monitoring dashboard
- `serve(port)`, `add_panel(name, chart)`, `update(snapshot)`
