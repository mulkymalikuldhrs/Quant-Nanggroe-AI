"""Factor Registry — discovery, registration, and factory for alpha factors.

The registry provides a centralized catalog of all available factors,
supporting discovery by theme, zoo, or universe. It also provides
lazy instantiation and output validation.

Supports two factor patterns:
1. Class-based: AlphaFactor subclasses with name/meta/compute properties
2. Function-based: __alpha_meta__ dict + compute(panel) function pairs
   (ported from Vibe-Trading zoo modules)

Design contract:
    FactorRegistry.list(zoo=None, theme=None, universe=None) -> list[str]
    FactorRegistry.get(factor_id) -> FactorHandle
    FactorRegistry.compute(factor_id, panel) -> pd.DataFrame
    FactorRegistry.health() -> dict
    FactorRegistry.export_manifest() -> dict
    FactorRegistry.load_alpha_meta_from_module(module_path) -> dict  # AST, no import
"""

from __future__ import annotations

import ast
import importlib
import logging
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.factors.base import AlphaFactor, FactorMeta

logger = logging.getLogger(__name__)

_ID_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_MAX_PY_BYTES = 200_000


@dataclass(frozen=True, slots=True)
class _LoadError:
    factor_id: str
    reason: str


class FactorHandle:
    """Unified handle for both class-based and function-based factors.

    Provides a common interface regardless of the underlying factor pattern.
    """

    def __init__(
        self,
        factor_id: str,
        zoo: str,
        meta_dict: dict,
        compute_fn=None,
        class_instance: Optional[AlphaFactor] = None,
    ):
        self._id = factor_id
        self._zoo = zoo
        self._meta_dict = meta_dict
        self._compute_fn = compute_fn
        self._class_instance = class_instance

    @property
    def id(self) -> str:
        return self._id

    @property
    def zoo(self) -> str:
        return self._zoo

    @property
    def meta_dict(self) -> dict:
        return self._meta_dict

    @property
    def theme(self) -> list[str]:
        return self._meta_dict.get("theme", [])

    @property
    def universe(self) -> list[str]:
        return self._meta_dict.get("universe", [])

    @property
    def columns_required(self) -> list[str]:
        return self._meta_dict.get("columns_required", [])

    @property
    def formula_latex(self) -> str:
        return self._meta_dict.get("formula_latex", "")

    @property
    def decay_horizon(self) -> int:
        return self._meta_dict.get("decay_horizon", 0)

    @property
    def min_warmup_bars(self) -> int:
        return self._meta_dict.get("min_warmup_bars", 0)

    def compute(self, panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Compute the factor on the given OHLCV+ panel.

        Args:
            panel: Dict mapping column names (open, high, low, close, volume, etc.)
                   to wide DataFrames (index=dates, columns=instruments).

        Returns:
            pd.DataFrame of factor values (same shape as panel columns).
        """
        if self._compute_fn is not None:
            return self._compute_fn(panel)
        elif self._class_instance is not None:
            # Class-based factors take a DataFrame, not a panel dict
            # We need to adapt the interface
            return self._adapt_class_compute(panel)
        raise RuntimeError(f"Factor {self._id} has no compute function")

    def _adapt_class_compute(self, panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Adapt class-based compute(df) to function-based compute(panel)."""
        factor = self._class_instance
        # Create a combined DataFrame from the panel
        # Class-based factors expect a single df with OHLCV columns
        # We need to handle wide (multi-instrument) DataFrames
        close = panel.get("close")
        if close is None:
            raise ValueError(f"Factor {self._id}: panel missing 'close' column")

        # For wide DataFrames, compute per-column
        if isinstance(close, pd.DataFrame) and close.ndim == 2:
            # Use the first available data column to compute
            # This is a simplification - class-based factors may need
            # adaptation for wide panel support
            result_parts = {}
            for col in close.columns:
                col_panel = {k: v[col] if isinstance(v, pd.DataFrame) else v for k, v in panel.items()}
                # Convert to single-instrument DataFrame
                single_df = pd.DataFrame(col_panel)
                try:
                    result = factor.compute(single_df)
                    result_parts[col] = result
                except Exception:
                    result_parts[col] = pd.Series(np.nan, index=close.index)
            return pd.DataFrame(result_parts)
        else:
            # Single instrument
            single_df = pd.DataFrame(panel)
            result = factor.compute(single_df)
            return result


def load_alpha_meta_from_module(module_path: str, meta_var_name: str = "__alpha_meta__") -> dict:
    """AST-extract a metadata dict from a Python module without importing it.

    Searches for an assignment to the variable named by ``meta_var_name`` and
    evaluates it as a literal. No import is performed — purely static parsing.

    Args:
        module_path: Path to the .py file.
        meta_var_name: Name of the metadata variable to extract.

    Returns:
        The metadata dict.

    Raises:
        ValueError: On malformed metadata or missing variable.
    """
    path = Path(module_path)
    size = path.stat().st_size
    if size > _MAX_PY_BYTES:
        raise ValueError(f"{path.name}: {size}B exceeds {_MAX_PY_BYTES}B cap")

    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))

    meta_node: ast.expr | None = None
    for stmt in tree.body:
        if not isinstance(stmt, ast.Assign):
            continue
        targets = [t for t in stmt.targets if isinstance(t, ast.Name)]
        if any(t.id == meta_var_name for t in targets):
            meta_node = stmt.value
            break

    if meta_node is None:
        raise ValueError(f"{path.name}: {meta_var_name} assignment not found")

    try:
        raw = ast.literal_eval(meta_node)
    except (ValueError, SyntaxError) as exc:
        raise ValueError(f"{path.name}: {meta_var_name} not a literal: {exc}") from exc

    if not isinstance(raw, dict):
        raise ValueError(f"{path.name}: {meta_var_name} must be dict, got {type(raw).__name__}")

    return raw


class FactorRegistry:
    """In-memory registry of all discoverable alpha factors.

    Supports both class-based (AlphaFactor subclasses) and function-based
    (__alpha_meta__ + compute(panel)) factor patterns. Provides discovery,
    lazy instantiation, and output validation.
    """

    def __init__(self) -> None:
        self._handles: Dict[str, FactorHandle] = {}
        self._meta: Dict[str, FactorMeta] = {}
        self._load_errors: List[_LoadError] = []
        self._register_builtin_factors()

    def _register_builtin_factors(self) -> None:
        """Register all built-in factors from the factor modules."""
        # Register class-based factors (existing pattern)
        from quant_nanggroe.engine.factors.fundamental import get_all_fundamental_factors
        from quant_nanggroe.engine.factors.technical import get_all_technical_factors

        class_factor_lists = [
            get_all_technical_factors(),
            get_all_fundamental_factors(),
        ]

        for factor_list in class_factor_lists:
            for factor in factor_list:
                try:
                    self._register_class_factor(factor)
                except Exception as exc:
                    self._load_errors.append(_LoadError(factor_id=factor.name, reason=str(exc)))
                    logger.warning("Failed to register factor %s: %s", factor.name, exc)

        # Register function-based factors (Vibe-Trading pattern)
        function_modules = [
            ("alpha101", "quant_nanggroe.engine.factors.alpha101"),
            ("gtja191", "quant_nanggroe.engine.factors.gtja191"),
            ("qlib158", "quant_nanggroe.engine.factors.qlib158"),
            ("academic", "quant_nanggroe.engine.factors.academic"),
        ]

        for zoo_name, module_path in function_modules:
            try:
                self._register_function_factors(zoo_name, module_path)
            except Exception as exc:
                self._load_errors.append(_LoadError(factor_id=module_path, reason=str(exc)))
                logger.warning("Failed to load module %s: %s", module_path, exc)

    def _register_class_factor(self, factor: AlphaFactor) -> None:
        """Register a class-based AlphaFactor instance."""
        if factor.name in self._handles:
            raise ValueError(f"Factor {factor.name!r} is already registered")

        # Validate lookahead-free
        if not factor.validate_lookahead():
            raise ValueError(f"Factor {factor.name!r} contains lookahead bias")

        meta = factor.meta
        handle = FactorHandle(
            factor_id=factor.name,
            zoo=meta.zoo,
            meta_dict={
                "id": meta.id,
                "zoo": meta.zoo,
                "theme": meta.theme,
                "formula_latex": meta.formula_latex,
                "columns_required": meta.columns_required,
                "universe": meta.universe,
                "frequency": meta.frequency,
                "decay_horizon": meta.decay_horizon,
                "min_warmup_bars": meta.min_warmup_bars,
                "notes": meta.notes,
            },
            class_instance=factor,
        )

        self._handles[factor.name] = handle
        self._meta[factor.name] = meta

    def _register_function_factors(self, zoo_name: str, module_path: str) -> None:
        """Register all function-based factors from a module.

        Each factor in the module follows the pattern:
        - __alpha_meta_{stem} = { ... }
        - def compute_{stem}(panel) -> pd.DataFrame

        This is the Vibe-Trading zoo pattern adapted for our codebase.
        """
        try:
            module = importlib.import_module(module_path)
        except ImportError as exc:
            raise ValueError(f"Cannot import {module_path}: {exc}") from exc

        # Get the list of (meta, compute) tuples
        get_all_fn_name = f"get_all_{zoo_name}_factors"
        get_all_fn = getattr(module, get_all_fn_name, None)
        if get_all_fn is None:
            logger.warning("Module %s has no %s function", module_path, get_all_fn_name)
            return

        factor_list = get_all_fn()
        for meta_dict, compute_fn in factor_list:
            try:
                factor_id = meta_dict.get("id", "")
                if not factor_id:
                    raise ValueError("meta dict missing 'id' field")

                if factor_id in self._handles:
                    raise ValueError(f"Factor {factor_id!r} is already registered")

                handle = FactorHandle(
                    factor_id=factor_id,
                    zoo=zoo_name,
                    meta_dict=meta_dict,
                    compute_fn=compute_fn,
                )

                # Create a FactorMeta for backward compatibility
                factor_meta = FactorMeta(
                    id=factor_id,
                    zoo=zoo_name,
                    theme=meta_dict.get("theme", []),
                    formula_latex=meta_dict.get("formula_latex", ""),
                    columns_required=meta_dict.get("columns_required", []),
                    universe=meta_dict.get("universe", []),
                    frequency=meta_dict.get("frequency", ["1D"]),
                    decay_horizon=meta_dict.get("decay_horizon", 0),
                    min_warmup_bars=meta_dict.get("min_warmup_bars", 0),
                    notes=meta_dict.get("notes", ""),
                )

                self._handles[factor_id] = handle
                self._meta[factor_id] = factor_meta

            except Exception as exc:
                self._load_errors.append(_LoadError(
                    factor_id=meta_dict.get("id", "unknown"),
                    reason=str(exc),
                ))
                logger.warning("Failed to register factor %s: %s", meta_dict.get("id", "?"), exc)

    def register(self, factor: AlphaFactor) -> None:
        """Register an alpha factor (class-based).

        Args:
            factor: An AlphaFactor instance to register.

        Raises:
            ValueError: If a factor with the same name is already registered.
        """
        self._register_class_factor(factor)

    def register_function_factor(
        self,
        factor_id: str,
        zoo: str,
        meta_dict: dict,
        compute_fn,
    ) -> None:
        """Register a function-based alpha factor.

        Args:
            factor_id: Unique factor identifier.
            zoo: Factor zoo name.
            meta_dict: Metadata dictionary.
            compute_fn: Callable(panel: dict) -> pd.DataFrame.

        Raises:
            ValueError: If a factor with the same ID is already registered.
        """
        if factor_id in self._handles:
            raise ValueError(f"Factor {factor_id!r} is already registered")

        handle = FactorHandle(
            factor_id=factor_id,
            zoo=zoo,
            meta_dict=meta_dict,
            compute_fn=compute_fn,
        )

        factor_meta = FactorMeta(
            id=factor_id,
            zoo=zoo,
            theme=meta_dict.get("theme", []),
            formula_latex=meta_dict.get("formula_latex", ""),
            columns_required=meta_dict.get("columns_required", []),
            universe=meta_dict.get("universe", []),
            frequency=meta_dict.get("frequency", ["1D"]),
            decay_horizon=meta_dict.get("decay_horizon", 0),
            min_warmup_bars=meta_dict.get("min_warmup_bars", 0),
            notes=meta_dict.get("notes", ""),
        )

        self._handles[factor_id] = handle
        self._meta[factor_id] = factor_meta

    def list(
        self,
        zoo: Optional[str] = None,
        theme: Optional[str] = None,
        universe: Optional[str] = None,
    ) -> List[str]:
        """Return factor IDs matching the optional filters.

        Args:
            zoo: Filter by zoo (alpha101, gtja191, qlib158, academic, technical, fundamental).
            theme: Filter by theme (momentum, reversal, volume, volatility, etc.).
            universe: Filter by universe (equity_us, equity_cn, crypto, etc.).

        Returns:
            Sorted list of matching factor IDs.
        """
        result: List[str] = []
        for name, handle in self._handles.items():
            if zoo is not None and handle.zoo != zoo:
                continue
            if theme is not None and theme not in handle.theme:
                continue
            if universe is not None and universe not in handle.universe:
                continue
            result.append(name)
        return sorted(result)

    def get(self, factor_id: str) -> FactorHandle:
        """Get a registered factor handle by ID.

        Args:
            factor_id: The unique factor identifier.

        Returns:
            The FactorHandle instance.

        Raises:
            KeyError: If factor_id is not registered.
        """
        if factor_id not in self._handles:
            raise KeyError(f"Factor {factor_id!r} not found in registry")
        return self._handles[factor_id]

    def get_meta(self, factor_id: str) -> FactorMeta:
        """Get metadata for a registered factor.

        Args:
            factor_id: The unique factor identifier.

        Returns:
            The FactorMeta instance.
        """
        if factor_id not in self._meta:
            raise KeyError(f"Factor {factor_id!r} not found in registry")
        return self._meta[factor_id]

    def compute(self, factor_id: str, panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Compute a factor on the given panel.

        Args:
            factor_id: The unique factor identifier.
            panel: Dict mapping column names to wide DataFrames.

        Returns:
            pd.DataFrame of computed factor values.

        Raises:
            KeyError: If factor_id is not registered.
            ValueError: If required columns are missing.
        """
        handle = self.get(factor_id)

        # Check required columns
        missing = [c for c in handle.columns_required if c not in panel]
        if missing:
            raise ValueError(
                f"Factor {factor_id} requires columns {missing} not present in panel"
            )

        # Compute
        result = handle.compute(panel)

        # Validate output
        return self._validate_output(factor_id, result, panel)

    @staticmethod
    def _validate_output(
        factor_id: str,
        result: Any,
        panel: dict[str, pd.DataFrame],
    ) -> pd.DataFrame:
        """Validate factor output quality."""
        if not isinstance(result, pd.DataFrame):
            raise ValueError(
                f"{factor_id}: compute() returned {type(result).__name__}, expected DataFrame"
            )
        arr = result.to_numpy(dtype=np.float64, na_value=np.nan)
        if np.isinf(arr).any():
            raise ValueError(f"{factor_id}: output contains +/- inf")
        nan_ratio = float(np.isnan(arr).mean()) if arr.size > 0 else 1.0
        if nan_ratio > 0.95:
            raise ValueError(
                f"{factor_id}: output >95% NaN (nan_ratio={nan_ratio:.3f})"
            )
        return result

    def health(self) -> Dict:
        """Return registry health status.

        Returns:
            Dict with counts and any load errors.
        """
        return {
            "loaded": len(self._handles),
            "failed": len(self._load_errors),
            "errors": [
                {"factor_id": e.factor_id, "reason": e.reason} for e in self._load_errors
            ],
            "by_zoo": {
                zoo: len([1 for h in self._handles.values() if h.zoo == zoo])
                for zoo in set(h.zoo for h in self._handles.values())
            },
            "by_theme": {
                theme: len([1 for h in self._handles.values() if theme in h.theme])
                for theme in set(t for h in self._handles.values() for t in h.theme)
            },
        }

    def summary(self) -> Dict:
        """Return a summary of all registered factors.

        Returns:
            Dict mapping factor ID to its metadata dict.
        """
        return {
            name: {
                "zoo": handle.zoo,
                "theme": handle.theme,
                "formula": handle.formula_latex,
                "columns_required": handle.columns_required,
                "universe": handle.universe,
                "min_warmup_bars": handle.min_warmup_bars,
            }
            for name, handle in self._handles.items()
        }

    def export_manifest(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot for external consumers.

        Includes all factor metadata grouped by zoo, plus health stats.
        """
        from datetime import datetime, timezone

        zoos: Dict[str, list[dict]] = {}
        for handle in self._handles.values():
            zoos.setdefault(handle.zoo, []).append(
                {
                    "id": handle.id,
                    "theme": handle.theme,
                    "formula_latex": handle.formula_latex,
                    "columns_required": handle.columns_required,
                    "universe": handle.universe,
                    "decay_horizon": handle.decay_horizon,
                    "min_warmup_bars": handle.min_warmup_bars,
                }
            )

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_factors": len(self._handles),
            "zoos": {
                zoo_id: sorted(items, key=lambda x: x["id"])
                for zoo_id, items in sorted(zoos.items())
            },
            "health": self.health(),
        }


# Process-wide singleton for hot paths
_registry_cache: Optional[FactorRegistry] = None
_registry_cache_lock = threading.Lock()


def get_default_registry() -> FactorRegistry:
    """Return a process-wide cached FactorRegistry.

    Thread-safe. First call builds and caches; subsequent calls return the same instance.
    """
    global _registry_cache
    with _registry_cache_lock:
        if _registry_cache is None:
            _registry_cache = FactorRegistry()
        return _registry_cache


def reset_default_registry() -> None:
    """Drop the cached registry (test hook)."""
    global _registry_cache
    with _registry_cache_lock:
        _registry_cache = None
