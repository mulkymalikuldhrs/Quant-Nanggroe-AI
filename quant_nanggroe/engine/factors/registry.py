"""Factor Registry — discovery, registration, and factory for alpha factors.

The registry provides a centralized catalog of all available factors,
supporting discovery by theme, zoo, or universe. It also provides
lazy instantiation and output validation.

Design contract:
    FactorRegistry.list(zoo=None, theme=None, universe=None) -> list[str]
    FactorRegistry.get(factor_id) -> AlphaFactor
    FactorRegistry.compute(factor_id, df) -> pd.Series
    FactorRegistry.health() -> dict
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Type

import numpy as np
import pandas as pd

from quant_nanggroe.engine.factors.base import AlphaFactor, FactorMeta

logger = logging.getLogger(__name__)


class FactorRegistry:
    """In-memory registry of all discoverable alpha factors.

    Supports registration, discovery, and lazy instantiation of factors.
    All registered factors must inherit from AlphaFactor.
    """

    def __init__(self) -> None:
        self._factors: Dict[str, AlphaFactor] = {}
        self._meta: Dict[str, FactorMeta] = {}
        self._load_errors: List[Dict[str, str]] = []
        self._register_builtin_factors()

    def _register_builtin_factors(self) -> None:
        """Register all built-in factors from the factor modules."""
        from quant_nanggroe.engine.factors.alpha101 import get_all_alpha101_factors
        from quant_nanggroe.engine.factors.gtja191 import get_all_gtja191_factors
        from quant_nanggroe.engine.factors.technical import get_all_technical_factors
        from quant_nanggroe.engine.factors.fundamental import get_all_fundamental_factors

        all_factor_lists = [
            get_all_alpha101_factors(),
            get_all_gtja191_factors(),
            get_all_technical_factors(),
            get_all_fundamental_factors(),
        ]

        for factor_list in all_factor_lists:
            for factor in factor_list:
                try:
                    self.register(factor)
                except Exception as exc:
                    self._load_errors.append({
                        "factor_id": factor.name,
                        "reason": str(exc),
                    })
                    logger.warning("Failed to register factor %s: %s", factor.name, exc)

    def register(self, factor: AlphaFactor) -> None:
        """Register an alpha factor.

        Args:
            factor: An AlphaFactor instance to register.

        Raises:
            ValueError: If a factor with the same name is already registered.
        """
        if factor.name in self._factors:
            raise ValueError(f"Factor {factor.name!r} is already registered")

        # Validate lookahead-free
        if not factor.validate_lookahead():
            raise ValueError(f"Factor {factor.name!r} contains lookahead bias")

        self._factors[factor.name] = factor
        self._meta[factor.name] = factor.meta

    def list(
        self,
        zoo: Optional[str] = None,
        theme: Optional[str] = None,
        universe: Optional[str] = None,
    ) -> List[str]:
        """Return factor IDs matching the optional filters.

        Args:
            zoo: Filter by zoo (alpha101, gtja191, technical, fundamental).
            theme: Filter by theme (momentum, reversal, volume, etc.).
            universe: Filter by universe (equity_us, equity_cn, crypto, etc.).

        Returns:
            Sorted list of matching factor IDs.
        """
        result: List[str] = []
        for name, meta in self._meta.items():
            if zoo is not None and meta.zoo != zoo:
                continue
            if theme is not None and theme not in meta.theme:
                continue
            if universe is not None and universe not in meta.universe:
                continue
            result.append(name)
        return sorted(result)

    def get(self, factor_id: str) -> AlphaFactor:
        """Get a registered factor by ID.

        Args:
            factor_id: The unique factor identifier.

        Returns:
            The AlphaFactor instance.

        Raises:
            KeyError: If factor_id is not registered.
        """
        if factor_id not in self._factors:
            raise KeyError(f"Factor {factor_id!r} not found in registry")
        return self._factors[factor_id]

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

    def compute(self, factor_id: str, df: pd.DataFrame) -> pd.Series:
        """Compute a factor on the given DataFrame.

        Args:
            factor_id: The unique factor identifier.
            df: Input DataFrame with OHLCV data.

        Returns:
            pd.Series of computed factor values.

        Raises:
            KeyError: If factor_id is not registered.
            ValueError: If required columns are missing.
        """
        factor = self.get(factor_id)
        meta = self.get_meta(factor_id)

        # Check required columns
        missing = [c for c in meta.columns_required if c not in df.columns]
        if missing:
            raise ValueError(
                f"Factor {factor_id} requires columns {missing} not present in DataFrame"
            )

        # Compute and validate
        result = factor.compute(df)
        return factor.validate_output(result)

    def health(self) -> Dict:
        """Return registry health status.

        Returns:
            Dict with counts and any load errors.
        """
        return {
            "loaded": len(self._factors),
            "failed": len(self._load_errors),
            "errors": self._load_errors,
            "by_zoo": {
                zoo: len([1 for m in self._meta.values() if m.zoo == zoo])
                for zoo in set(m.zoo for m in self._meta.values())
            },
            "by_theme": {
                theme: len([1 for m in self._meta.values() if theme in m.theme])
                for theme in set(t for m in self._meta.values() for t in m.theme)
            },
        }

    def summary(self) -> Dict:
        """Return a summary of all registered factors.

        Returns:
            Dict mapping factor ID to its metadata dict.
        """
        return {
            name: {
                "zoo": meta.zoo,
                "theme": meta.theme,
                "formula": meta.formula_latex,
                "columns_required": meta.columns_required,
                "universe": meta.universe,
                "min_warmup_bars": meta.min_warmup_bars,
            }
            for name, meta in self._meta.items()
        }


# Process-wide singleton for hot paths
_registry_cache: Optional[FactorRegistry] = None


def get_default_registry() -> FactorRegistry:
    """Return a process-wide cached FactorRegistry.

    Thread-safe. First call builds and caches; subsequent calls return the same instance.
    """
    global _registry_cache
    if _registry_cache is None:
        _registry_cache = FactorRegistry()
    return _registry_cache


def reset_default_registry() -> None:
    """Drop the cached registry (test hook)."""
    global _registry_cache
    _registry_cache = None
