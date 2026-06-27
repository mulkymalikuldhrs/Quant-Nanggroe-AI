# engine.factors.base

## Class: 

Market identifier for market-specific formulas.

*Line: 30*

---

## Class: 

Metadata for a registered alpha factor.

*Line: 42*

---

## Class: 

Abstract base class for all alpha factors.

Every factor must:
- Inherit from AlphaFactor
- Implement compute(df: pd.DataFrame) -> pd.Series
- Be AST-pure (no external API calls, no randomness)
- Have proper docstring with formula reference
- Include lookahead-banned validation

The compute method receives a DataFrame with OHLCV columns and returns
a Series of factor values aligned with the input index.

**Methods:** name, meta, compute, validate_lookahead, validate_output

*Line: 57*

---

## Function: 

Convert DataFrame to float64 if needed.

*Line: 158*

---

## Function: 

Cross-sectional percentile rank per row (axis=1, ties=average, pct=True).

NaN inputs stay NaN. An all-NaN row returns an all-NaN row.
Accepts both DataFrame and Series inputs.

*Line: 165*

---

## Function: 

Per-row L1 normalize so sum of absolute values equals ``a``.

Rows whose abs-sum is 0 (or all-NaN) become NaN — never silent zero.

*Line: 176*

---

## Function: 

Rolling rank (last value's rank within the n-window), per column.

Warmup (first ``n-1`` rows per column) returns NaN. Result is a percentile
in [0, 1] so it is compositionally compatible with cross-sectional rank.

*Line: 187*

---

## Function: 

Rolling Pearson correlation per column, min_periods=n.

Constant series in the window → NaN (no silent zero).

*Line: 213*

---

## Function: 

Rolling sample covariance per column, min_periods=n.

*Line: 229*

---

## Function: 

Rolling mean per column, warmup → NaN.

*Line: 242*

---

## Function: 

Rolling sample std (ddof=1) per column, warmup → NaN.

*Line: 249*

---

## Function: 

Rolling max per column, warmup → NaN.

*Line: 256*

---

## Function: 

Rolling min per column, warmup → NaN.

*Line: 263*

---

## Function: 

*Line: 270*

---

## Function: 

*Line: 277*

---

## Function: 

Rolling argmax (0-based index into the window), warmup → NaN.

*Line: 284*

---

## Function: 

Rolling argmin (0-based index into the window), warmup → NaN.

*Line: 291*

---

## Function: 

First difference at lag ``d``: ``df - df.shift(d)``.

Lookahead ban: ``d >= 1`` strictly. Negative lag forbidden.

*Line: 298*

---

## Function: 

Linear decay-weighted moving average, weights ``n, n-1, ..., 1`` normalized.

Warmup (first ``n-1`` rows) → NaN.

*Line: 308*

---

## Function: 

``sign(df) * |df|**p`` — preserves sign; never produces complex output.

Accepts both DataFrame and Series inputs, returning the same type.

*Line: 326*

---

## Function: 

Safe division: ``a / (b + eps * sign(b))``.

Where ``b == 0`` exactly (or NaN), result is NaN — never silently inf or 0.

*Line: 338*

---

## Function: 

Rolling sum per column, warmup → NaN.

*Line: 352*

---

## Function: 

Rolling product per column, warmup → NaN.

*Line: 359*

---

## Function: 

Per-row z-score: (x - row_mean) / row_std; zero/NaN std rows → NaN.

This is a cross-sectional operator (operates across columns per row),
useful for creating long-short rankings of factor values.

*Line: 366*

---

## Function: 

Market-aware VWAP-equivalent reference price.

- ``equity_cn``: ``(amount * 1000) / (volume * 100 + 1)``
- ``equity_us`` / ``equity_hk`` / ``futures``: typical price ``(H + L + C + O) / 4``
- ``crypto``: prefer ``panel["vwap"]`` if provided, else typical price.

*Line: 379*

---

## Function: 

Unique identifier for this factor.

*Line: 73*

---

## Function: 

Factor metadata.

*Line: 79*

---

## Function: 

Compute the factor values.

Args:
    df: DataFrame with OHLCV data. Index is DatetimeIndex,
        columns include 'open', 'high', 'low', 'close', 'volume',
        and optionally 'vwap', 'amount'.

Returns:
    pd.Series of factor values aligned with the input index.
    Must not contain +/- inf. NaN in warmup periods is expected.

*Line: 84*

---

## Function: 

Validate that this factor has no lookahead bias.

Scans the compute method's AST for negative shift operations
or future-data access patterns.

Returns:
    True if the factor is lookahead-free.

*Line: 98*

---

## Function: 

Validate factor output quality.

Ensures:
- No +/- inf values
- Not >95% NaN
- Proper alignment with expected index

Args:
    result: Factor output series.

Returns:
    Validated series (inf replaced with NaN).

Raises:
    ValueError: If output fails validation.

*Line: 125*

---

## Function: 

*Line: 196*

---

## Function: 

*Line: 318*

---

