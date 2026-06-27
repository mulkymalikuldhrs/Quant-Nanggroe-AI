# engine.strategy.backtest_adapter

## Class: 

Adapts a StrategyConfig for use with the BacktestEngine.

Converts declarative strategy rules (entry/exit conditions) into
pandas-based signal computations that produce position weight
DataFrames compatible with the BacktestEngine.run() method.

The adapter supports:
- Indicator computation (RSI, SMA, EMA, MACD, Bollinger, ADX, etc.)
- Volume ratio computation (volume / rolling average volume)
- Multi-timeframe strategies (rules on different timeframes)
- Position sizing from risk rules
- Trailing stop and take profit exits
- Price comparison indicators (price vs SMA, EMA crossover)

Example:
    >>> adapter = StrategyBacktestAdapter(config)
    >>> signals_df = adapter.generate_signals(price_df)
    >>> # signals_df is a DataFrame of position weights (-1 to 1)
    >>> from quant_nanggroe.engine.backtest.engine import BacktestEngine
    >>> engine = BacktestEngine()
    >>> result = engine.run(prices_df, signals_df)

**Methods:** __init__, config, universe, risk_rules, generate_signals, generate_signals_with_prices, _compute_entry_signals, _compute_exit_signals, _compute_indicator, _compute_rsi, _compute_atr, _compute_adx, _compute_factor, _estimate_volume, _evaluate_rule, _apply_state_machine, _apply_state_machine_full, to_backtest_config, get_generated_code, clear_cache

*Line: 49*

---

## Function: 

Initialize the backtest adapter.

Args:
    config: StrategyConfig defining the strategy rules.

*Line: 73*

---

## Function: 

The strategy configuration.

*Line: 83*

---

## Function: 

Trading universe symbols.

*Line: 88*

---

## Function: 

Risk rules from the strategy config.

*Line: 93*

---

## Function: 

Generate position weight signals for the backtest engine.

Computes entry and exit signals for each symbol in the universe,
then applies a state machine to determine position weights.
Uses close prices and estimated OHLCV when full data is unavailable.

Args:
    df: Price data DataFrame with DatetimeIndex and columns
        for each symbol. Values are close prices. Can also
        contain MultiIndex columns with OHLCV data.

Returns:
    DataFrame with same index/columns as input, values are
    position weights: -1.0 (short), 0.0 (flat), or positive
    for long position size (capped by max_position_pct).

*Line: 97*

---

## Function: 

Generate signals with full OHLCV data for trailing stop/take profit.

This is the full-featured signal generation that uses real volume
data and proper OHLCV for indicator computation.

Args:
    ohlcv_dict: Dict mapping symbol to OHLCV DataFrame with columns:
                open, high, low, close, volume.

Returns:
    DataFrame of position weights with DatetimeIndex and symbol columns.

*Line: 156*

---

## Function: 

Compute entry signals from all entry rules.

All entry rules are evaluated with AND logic: a signal is generated
only when ALL rules are satisfied.

Args:
    df: OHLCV-like DataFrame for a single symbol.

Returns:
    Boolean Series: True when all entry conditions are met.

*Line: 209*

---

## Function: 

Compute exit signals from all exit rules.

Exit rules are evaluated with OR logic: a signal is generated
when ANY exit condition is triggered.

Args:
    df: OHLCV-like DataFrame for a single symbol.

Returns:
    Boolean Series: True when any exit condition is triggered.

*Line: 235*

---

## Function: 

Compute indicator values for a rule.

Supports a wide range of indicators and comparison modes.

Args:
    rule: Entry or exit rule with indicator specification.
    df: OHLCV-like DataFrame.

Returns:
    Series of indicator values.

*Line: 270*

---

## Function: 

Compute Relative Strength Index.

Uses Wilder's smoothing method for proper RSI calculation.

Args:
    prices: Price series.
    period: RSI period.

Returns:
    RSI values (0-100).

*Line: 390*

---

## Function: 

Compute Average True Range.

Args:
    df: OHLCV DataFrame.
    period: ATR period.

Returns:
    ATR values.

*Line: 414*

---

## Function: 

Compute Average Directional Index (ADX).

Measures trend strength regardless of direction.
ADX > 25 indicates a strong trend.

Args:
    df: OHLCV DataFrame.
    period: ADX period.

Returns:
    ADX values.

*Line: 437*

---

## Function: 

Compute custom factor scores for factor-based strategies.

Args:
    df: OHLCV DataFrame.
    factor_type: Type of factor to compute.
    lookback: Lookback period for factor computation.

Returns:
    Factor score Series (typically -1 to 1).

*Line: 484*

---

## Function: 

Estimate volume from price data when actual volume is unavailable.

Uses a proxy based on dollar volume (price * 1000) to allow
volume ratio calculations. This is a rough estimate — real
volume data should be used via generate_signals_with_prices().

Args:
    price_series: Close price series.

Returns:
    Estimated volume Series.

*Line: 539*

---

## Function: 

Evaluate a comparison rule against indicator values.

Args:
    values: Indicator values.
    operator: Comparison operator.
    threshold: Threshold value.

Returns:
    Boolean Series where the rule is satisfied.

*Line: 562*

---

## Function: 

Apply a position state machine to entry/exit signals.

Implements trailing stop, take profit, and stop loss logic
in addition to indicator-based exit signals.

Args:
    entry: Boolean Series of entry signals.
    exit_signal: Boolean Series of indicator-based exit signals.
    df: OHLCV DataFrame with close prices.

Returns:
    Series of position weights (0.0 or 1.0).

*Line: 597*

---

## Function: 

Full state machine with trailing stop and take profit.

This is identical to _apply_state_machine but provided for
backward compatibility with generate_signals_with_prices().

Args:
    entry: Boolean entry signals.
    exit_signal: Boolean indicator-based exit signals.
    df: OHLCV DataFrame with close prices.

Returns:
    Position weight Series.

*Line: 675*

---

## Function: 

Convert strategy config to BacktestConfig-compatible parameters.

Returns:
    Dict of BacktestConfig parameters derived from the strategy.

*Line: 696*

---

## Function: 

Get the generated Python code for this strategy.

Returns:
    Python code string implementing the strategy.

*Line: 711*

---

## Function: 

Clear the indicator computation cache.

*Line: 719*

---

