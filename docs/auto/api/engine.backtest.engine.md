# engine.backtest.engine

## Class: 

Supported market types for backtesting.

*Line: 33*

---

## Class: 

Supported strategy types.

*Line: 42*

---

## Class: 

Configuration for a backtest run.

Attributes:
    initial_capital: Starting capital.
    market: Market type (affects execution rules).
    strategy_type: Type of strategy being tested.
    commission_rate: Commission rate as decimal (e.g. 0.001 = 0.1%).
    slippage_bps: Slippage in basis points (e.g. 5 = 0.05%).
    leverage: Maximum leverage allowed.
    risk_per_trade: Maximum risk per trade as fraction of capital.
    max_positions: Maximum number of simultaneous positions.
    bars_per_year: Number of bars per year for annualisation.
    benchmark: Benchmark ticker for comparison.
    short_enabled: Whether short selling is allowed.

*Line: 51*

---

## Class: 

Core backtesting engine with realistic execution simulation.

Supports:
- Multiple markets (equity, crypto, forex, futures)
- Realistic execution with slippage and commission
- Multiple strategy types
- Position sizing and risk management
- Performance metrics calculation
- Multi-strategy backtesting
- Parameter sensitivity analysis
- Benchmark comparison
- Trade-level analytics
- Custom execution models

Usage:
    engine = BacktestEngine(BacktestConfig())
    results = engine.run(prices_df, signals_df)

**Methods:** __init__, run, run_multi_strategy, run_sensitivity_analysis, run_with_benchmark, run_walk_forward, _get_fill_price, _apply_param, _build_sensitivity_summary, _find_optimal_param, _compute_trade_analytics, _compute_strategy_correlation

*Line: 81*

---

## Function: 

*Line: 101*

---

## Function: 

Run a backtest on price data with trading signals.

Args:
    prices: DataFrame with DatetimeIndex and columns for each symbol.
             Values are close prices.
    signals: DataFrame with same index/columns as prices.
             Values are target position weights (-1 to 1).
    position_sizer: Optional callable for custom position sizing.
        Signature: (signal, capital, price) -> size
    execution_model: Optional callable for custom execution simulation.
        Signature: (price, direction, size, timestamp) -> fill_price

Returns:
    Dict with performance metrics, equity curve, and trade records.

*Line: 114*

---

## Function: 

Run a multi-strategy backtest with portfolio-level aggregation.

Each strategy produces its own signals, which are combined using
the specified weights. The combined signal is then executed.

Args:
    prices: Price data DataFrame.
    strategy_signals: Dict mapping strategy name to signal DataFrame.
    strategy_weights: Optional dict mapping strategy name to weight.
                    Defaults to equal weight for all strategies.
    position_sizer: Optional position sizer callable.

Returns:
    Dict with:
        - combined: Combined backtest result
        - per_strategy: Dict of per-strategy backtest results
        - strategy_correlation: Correlation matrix of strategy returns

*Line: 265*

---

## Function: 

Run parameter sensitivity analysis.

Tests how backtest results change as a parameter varies.

Args:
    prices: Price data.
    signals: Signal data.
    param_name: Name of the parameter to vary.
    param_values: List of parameter values to test.
    param_applier: Optional callable that takes (config, param_name, param_value)
                  and returns a modified BacktestConfig.
    position_sizer: Optional position sizer.

Returns:
    Dict with:
        - results: Dict mapping param_value to backtest result
        - metrics_summary: DataFrame of key metrics across parameter values
        - optimal: Dict with optimal parameter value and metrics

*Line: 359*

---

## Function: 

Run backtest with benchmark comparison.

Args:
    prices: Price data.
    signals: Signal data.
    benchmark_prices: Optional benchmark price series. If not provided,
                    the first column of prices is used.
    position_sizer: Optional position sizer.

Returns:
    Dict with backtest results and benchmark comparison.

*Line: 419*

---

## Function: 

Run walk-forward analysis.

Args:
    prices: Price data.
    signals: Signal data.
    train_window: Training window in bars.
    test_window: Test window in bars.

Returns:
    Walk-forward analysis results.

*Line: 471*

---

## Function: 

Get execution fill price, using custom model or default slippage.

*Line: 501*

---

## Function: 

Apply a parameter value to a BacktestConfig.

Args:
    config: Original config.
    param_name: Parameter name.
    param_value: New value.

Returns:
    Modified BacktestConfig.

*Line: 521*

---

## Function: 

Build a summary DataFrame of metrics across parameter values.

*Line: 556*

---

## Function: 

Find the optimal parameter value based on a given metric.

Args:
    results: Dict mapping param_value to backtest result.
    param_name: Parameter name.
    metric: Metric to optimize (higher is better).

Returns:
    Dict with optimal param value and associated metrics.

*Line: 581*

---

## Function: 

Compute trade-level analytics.

Args:
    trades: List of completed trade records.

Returns:
    Dict of trade analytics.

*Line: 617*

---

## Function: 

Compute correlation matrix between strategy equity curves.

Args:
    equity_curves: Dict mapping strategy name to equity curve Series.

Returns:
    Correlation matrix DataFrame.

*Line: 705*

---

## Function: 

*Line: 659*

---

