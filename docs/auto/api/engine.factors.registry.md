# engine.factors.registry

## Class: 

*Line: 45*

---

## Class: 

Unified handle for both class-based and function-based factors.

Provides a common interface regardless of the underlying factor pattern.

**Methods:** __init__, id, zoo, meta_dict, theme, universe, columns_required, formula_latex, decay_horizon, min_warmup_bars, compute, _adapt_class_compute

*Line: 50*

---

## Function: 

AST-extract a metadata dict from a Python module without importing it.

Searches for an assignment to the variable named by ``meta_var_name`` and
evaluates it as a literal. No import is performed — purely static parsing.

Args:
    module_path: Path to the .py file.
    meta_var_name: Name of the metadata variable to extract.

Returns:
    The metadata dict.

Raises:
    ValueError: On malformed metadata or missing variable.

*Line: 157*

---

## Class: 

In-memory registry of all discoverable alpha factors.

Supports both class-based (AlphaFactor subclasses) and function-based
(__alpha_meta__ + compute(panel)) factor patterns. Provides discovery,
lazy instantiation, and output validation.

**Methods:** __init__, _register_builtin_factors, _register_class_factor, _register_function_factors, register, register_function_factor, list, get, get_meta, compute, _validate_output, health, summary, export_manifest

*Line: 204*

---

## Function: 

Return a process-wide cached FactorRegistry.

Thread-safe. First call builds and caches; subsequent calls return the same instance.

*Line: 583*

---

## Function: 

Drop the cached registry (test hook).

*Line: 595*

---

## Function: 

*Line: 56*

---

## Function: 

*Line: 71*

---

## Function: 

*Line: 75*

---

## Function: 

*Line: 79*

---

## Function: 

*Line: 83*

---

## Function: 

*Line: 87*

---

## Function: 

*Line: 91*

---

## Function: 

*Line: 95*

---

## Function: 

*Line: 99*

---

## Function: 

*Line: 103*

---

## Function: 

Compute the factor on the given OHLCV+ panel.

Args:
    panel: Dict mapping column names (open, high, low, close, volume, etc.)
           to wide DataFrames (index=dates, columns=instruments).

Returns:
    pd.DataFrame of factor values (same shape as panel columns).

*Line: 106*

---

## Function: 

Adapt class-based compute(df) to function-based compute(panel).

*Line: 124*

---

## Function: 

*Line: 212*

---

## Function: 

Register all built-in factors from the factor modules.

*Line: 218*

---

## Function: 

Register a class-based AlphaFactor instance.

*Line: 252*

---

## Function: 

Register all function-based factors from a module.

Each factor in the module follows the pattern:
- __alpha_meta_{stem} = { ... }
- def compute_{stem}(panel) -> pd.DataFrame

This is the Vibe-Trading zoo pattern adapted for our codebase.

*Line: 283*

---

## Function: 

Register an alpha factor (class-based).

Args:
    factor: An AlphaFactor instance to register.

Raises:
    ValueError: If a factor with the same name is already registered.

*Line: 345*

---

## Function: 

Register a function-based alpha factor.

Args:
    factor_id: Unique factor identifier.
    zoo: Factor zoo name.
    meta_dict: Metadata dictionary.
    compute_fn: Callable(panel: dict) -> pd.DataFrame.

Raises:
    ValueError: If a factor with the same ID is already registered.

*Line: 356*

---

## Function: 

Return factor IDs matching the optional filters.

Args:
    zoo: Filter by zoo (alpha101, gtja191, qlib158, academic, technical, fundamental).
    theme: Filter by theme (momentum, reversal, volume, volatility, etc.).
    universe: Filter by universe (equity_us, equity_cn, crypto, etc.).

Returns:
    Sorted list of matching factor IDs.

*Line: 400*

---

## Function: 

Get a registered factor handle by ID.

Args:
    factor_id: The unique factor identifier.

Returns:
    The FactorHandle instance.

Raises:
    KeyError: If factor_id is not registered.

*Line: 427*

---

## Function: 

Get metadata for a registered factor.

Args:
    factor_id: The unique factor identifier.

Returns:
    The FactorMeta instance.

*Line: 443*

---

## Function: 

Compute a factor on the given panel.

Args:
    factor_id: The unique factor identifier.
    panel: Dict mapping column names to wide DataFrames.

Returns:
    pd.DataFrame of computed factor values.

Raises:
    KeyError: If factor_id is not registered.
    ValueError: If required columns are missing.

*Line: 456*

---

## Function: 

Validate factor output quality.

*Line: 486*

---

## Function: 

Return registry health status.

Returns:
    Dict with counts and any load errors.

*Line: 506*

---

## Function: 

Return a summary of all registered factors.

Returns:
    Dict mapping factor ID to its metadata dict.

*Line: 528*

---

## Function: 

Return a JSON-serialisable snapshot for external consumers.

Includes all factor metadata grouped by zoo, plus health stats.

*Line: 546*

---

