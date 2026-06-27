# engine.factors.pipeline

## Class: 

Methods for combining multiple factor signals.

*Line: 40*

---

## Class: 

Batch computation pipeline for alpha factors.

Orchestrates the computation of multiple factors on OHLCV data,
handling column dependencies, warmup validation, and output alignment.
Supports both panel dict (wide DataFrame per column) and single
DataFrame input formats.

**Methods:** __init__, factor_ids, _df_to_panel, compute, compute_panel, compute_as_dataframe, combine_signals, validate_data

*Line: 51*

---

## Function: 

Initialize the pipeline.

Args:
    factor_ids: List of factor IDs to compute. If None, uses all registered.
    registry: FactorRegistry instance. If None, uses default singleton.

*Line: 60*

---

## Function: 

List of factor IDs in this pipeline.

*Line: 78*

---

## Function: 

Convert a long-format DataFrame to a panel dict of wide DataFrames.

The input DataFrame has columns like 'open', 'high', 'low', 'close',
'volume' with a DatetimeIndex. The output is a dict mapping column
names to DataFrames with the same shape.

*Line: 83*

---

## Function: 

Compute all pipeline factors on the given DataFrame.

Legacy method for backward compatibility with class-based factors.
For function-based factors (alpha101, gtja191, etc.), use
compute_panel() instead.

Args:
    df: Input DataFrame with OHLCV data.

Returns:
    Dict mapping factor_id -> pd.Series of computed values.

*Line: 96*

---

## Function: 

Compute all pipeline factors on the given panel dict.

This is the preferred method for function-based factors that use
the panel dict format (wide DataFrames per column).

Args:
    panel: Dict mapping column names to wide DataFrames
           (index=dates, columns=instruments).

Returns:
    Dict mapping factor_id -> pd.DataFrame of computed values.

*Line: 145*

---

## Function: 

Compute all pipeline factors and return as a single DataFrame.

Args:
    df: Input DataFrame with OHLCV data.

Returns:
    DataFrame where each column is a factor's computed values.

*Line: 171*

---

## Function: 

Combine multiple factor signals into a single composite signal.

Args:
    results: Dict mapping factor_id -> pd.Series of values.
    method: Combination method.
    weights: Optional weight dict for weighted averaging.

Returns:
    pd.Series of combined signal values.

*Line: 186*

---

## Function: 

Validate that the panel has required columns for all factors.

Args:
    panel: Dict mapping column names to DataFrames.

Returns:
    Dict with 'ready' (factors that can run) and 'missing' (factors
    that lack required columns, mapped to the missing column names).

*Line: 239*

---

