# engine.strategy.strategies.base_strategy

## Class: 

Base class for all trading strategies.

Every concrete strategy must:
- Implement generate_signal() to produce trading signals
- Implement required_columns() to declare OHLCV dependencies
- Implement warmup_period() to specify minimum data length

Attributes:
    name: Human-readable strategy name.
    params: Strategy-specific configuration parameters.
    is_warmed_up: Whether the strategy has received enough data.

**Methods:** __init__, generate_signal, required_columns, warmup_period, validate_data, compute_sma, compute_ema, compute_rsi, compute_atr, compute_bollinger_bands, compute_macd, compute_zscore, __repr__

*Line: 22*

---

## Function: 

Initialize the base strategy.

Args:
    name: Strategy name identifier.
    params: Optional dict of strategy parameters.

*Line: 36*

---

## Function: 

Generate a trading signal from market data.

Args:
    data: DataFrame with OHLCV columns and DatetimeIndex.

Returns:
    A Signal object if conditions are met, None otherwise.

*Line: 48*

---

## Function: 

Return required OHLCV columns for this strategy.

Returns:
    List of column names that must be present in the data.

*Line: 60*

---

## Function: 

Return minimum number of bars needed before signal generation.

Returns:
    Minimum number of observations required.

*Line: 69*

---

## Function: 

Validate that data has required columns and sufficient length.

Args:
    data: Market data DataFrame.

Returns:
    True if data is valid and strategy is warmed up.

*Line: 77*

---

## Function: 

Compute Simple Moving Average.

Args:
    series: Price or indicator series.
    period: Lookback window.

Returns:
    SMA series.

*Line: 103*

---

## Function: 

Compute Exponential Moving Average.

Args:
    series: Price or indicator series.
    period: Span parameter.

Returns:
    EMA series.

*Line: 116*

---

## Function: 

Compute Relative Strength Index using Wilder's smoothing.

Args:
    series: Price series.
    period: RSI lookback period (default 14).

Returns:
    RSI values between 0 and 100.

*Line: 129*

---

## Function: 

Compute Average True Range.

Args:
    high: High price series.
    low: Low price series.
    close: Close price series.
    period: ATR lookback period.

Returns:
    ATR series.

*Line: 155*

---

## Function: 

Compute Bollinger Bands.

Args:
    series: Price series.
    period: Moving average period.
    num_std: Number of standard deviations for bands.

Returns:
    Tuple of (upper_band, middle_band, lower_band).

*Line: 176*

---

## Function: 

Compute MACD, signal line, and histogram.

Args:
    series: Price series.
    fast_period: Fast EMA period.
    slow_period: Slow EMA period.
    signal_period: Signal line EMA period.

Returns:
    Tuple of (macd_line, signal_line, histogram).

*Line: 196*

---

## Function: 

Compute rolling Z-score.

Args:
    series: Input series.
    period: Rolling window size.

Returns:
    Z-score series.

*Line: 221*

---

## Function: 

*Line: 235*

---

