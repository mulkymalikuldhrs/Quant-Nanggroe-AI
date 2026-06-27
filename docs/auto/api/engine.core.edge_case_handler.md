# engine.core.edge_case_handler

## Function: 

Safe division with zero-divisor protection.

Args:
    a: Numerator.
    b: Denominator.
    default: Value returned if division is unsafe.
    allow_zero: If True, returns 0.0 when denominator is zero.

Returns:
    Result of a / b, or default on failure.

*Line: 53*

---

## Function: 

Safe square root — returns default for negative inputs.

*Line: 87*

---

## Function: 

Safe natural log — returns default for non-positive inputs.

*Line: 100*

---

## Function: 

Safe power operation with overflow protection.

*Line: 111*

---

## Function: 

Clamp a value to [low, high].

*Line: 128*

---

## Function: 

Validate and sanitize a DataFrame input.

Args:
    df: Input DataFrame.
    required_columns: Columns that must be present.
    min_rows: Minimum number of rows required.
    name: Name for error messages.

Returns:
    Validated and sanitized DataFrame.

Raises:
    ValueError: If DataFrame is empty or missing required columns.

*Line: 140*

---

## Function: 

Validate a price DataFrame with common OHLCV columns.

Replaces inf with NaN and ensures a DatetimeIndex.

*Line: 180*

---

## Function: 

Sanitize a numeric Series: replace inf, handle NaN, clip extremes.

*Line: 200*

---

## Function: 

Validate and sanitize a return series.

- Replaces inf with NaN
- Drops NaN
- Clips extreme values beyond 10 standard deviations

Raises:
    ValueError: If insufficient data after sanitization.

*Line: 231*

---

## Function: 

Validate a single price value.

Returns None if price is invalid.

*Line: 275*

---

## Function: 

Validate a volume value. Returns None if invalid.

*Line: 295*

---

## Function: 

Validate and clamp a Kelly fraction to [0.0, 1.0].

*Line: 310*

---

## Function: 

Validate and normalize a weights dictionary.

Normalizes weights to sum to 1.0. Raises on empty or all-zero.

*Line: 323*

---

## Function: 

Validate a trade history list for Kelly calculations.

*Line: 353*

---

## Function: 

Compute cumulative product with overflow protection.

*Line: 392*

---

## Function: 

Safe summation with overflow protection.

*Line: 403*

---

## Function: 

Decorator that wraps a function with defensive error handling.

Catches exceptions and returns a fallback value instead of crashing.

Args:
    fallback_value: Value to return on exception.
    log_errors: Whether to log the exception.
    reraise: If True, re-raise after logging.
    max_retries: Number of retries on transient failures.
    retry_delay: Base delay between retries in seconds.

Example::

    @defensive_wrapper(fallback_value=0.0)
    def compute_sharpe(returns):
        return returns.mean() / returns.std()

*Line: 420*

---

## Function: 

Execute a DataFrame operation with defensive fallback.

Returns fallback (empty DataFrame by default) on any error.

*Line: 482*

---

## Function: 

Validate paired market data + signals inputs at module boundaries.

Args:
    prices: Price DataFrame.
    signals: Signal DataFrame.
    operation: Operation name for error messages.

Returns:
    Tuple of (validated_prices, validated_signals).

Raises:
    ValueError: If inputs are invalid.

*Line: 504*

---

## Function: 

Validate and cap position size relative to equity.

*Line: 542*

---

## Function: 

*Line: 444*

---

## Function: 

*Line: 446*

---

