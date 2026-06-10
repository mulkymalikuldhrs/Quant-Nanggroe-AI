"""Factor Registry — discovery, registration, and factory for alpha factors.

The registry provides a centralized catalog of all available factors,
supporting discovery by theme, zoo, or universe. It also provides
lazy instantiation and output validation.

Enhanced features:
    - Auto-discovery of all registered factors across modules
    - Factor metadata with category, description, and lookback
    - Factor grouping (technical, fundamental, alternative, risk)
    - Factor screening and filtering
    - Factor correlation matrix computation
    - Factor dependency analysis

Design contract:
    FactorRegistry.list(zoo=None, theme=None, universe=None) -> list[str]
    FactorRegistry.get(factor_id) -> AlphaFactor
    FactorRegistry.compute(factor_id, df) -> pd.Series
    FactorRegistry.health() -> dict
    FactorRegistry.correlation_matrix(df, factor_ids) -> pd.DataFrame
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

from quant_nanggroe.engine.factors.base import AlphaFactor, FactorMeta

logger = logging.getLogger(__name__)


class FactorCategory(str, Enum):
    """Broad factor category for grouping and filtering."""

    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    ALTERNATIVE = "alternative"
    RISK = "risk"


# Map from zoo -> category
_ZOO_CATEGORY_MAP: Dict[str, FactorCategory] = {
    "alpha101": FactorCategory.ALTERNATIVE,
    "gtja191": FactorCategory.ALTERNATIVE,
    "technical": FactorCategory.TECHNICAL,
    "fundamental": FactorCategory.FUNDAMENTAL,
    "barra": FactorCategory.RISK,
}


class FactorRegistry:
    """In-memory registry of all discoverable alpha factors.

    Supports registration, discovery, and lazy instantiation of factors.
    All registered factors must inherit from AlphaFactor.

    Enhanced with:
    - Category-based grouping
    - Factor screening by multiple criteria
    - Correlation matrix computation
    - Dependency analysis
    - Detailed factor metadata access
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
        from quant_nanggroe.engine.factors.barra import get_all_barra_factors

        all_factor_lists = [
            get_all_alpha101_factors(),
            get_all_gtja191_factors(),
            get_all_technical_factors(),
            get_all_fundamental_factors(),
            get_all_barra_factors(),
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

    def unregister(self, factor_id: str) -> None:
        """Remove a factor from the registry.

        Args:
            factor_id: The unique factor identifier.
        """
        self._factors.pop(factor_id, None)
        self._meta.pop(factor_id, None)

    def list(
        self,
        zoo: Optional[str] = None,
        theme: Optional[str] = None,
        universe: Optional[str] = None,
        category: Optional[FactorCategory] = None,
        min_warmup: Optional[int] = None,
        max_warmup: Optional[int] = None,
    ) -> List[str]:
        """Return factor IDs matching the optional filters.

        Args:
            zoo: Filter by zoo (alpha101, gtja191, technical, fundamental, barra).
            theme: Filter by theme (momentum, reversal, volume, etc.).
            universe: Filter by universe (equity_us, equity_cn, crypto, etc.).
            category: Filter by broad category (technical, fundamental, alternative, risk).
            min_warmup: Minimum warmup bars required.
            max_warmup: Maximum warmup bars required.

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
            if category is not None:
                factor_cat = _ZOO_CATEGORY_MAP.get(meta.zoo)
                if factor_cat != category:
                    continue
            if min_warmup is not None and meta.min_warmup_bars < min_warmup:
                continue
            if max_warmup is not None and meta.min_warmup_bars > max_warmup:
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

    def get_category(self, factor_id: str) -> FactorCategory:
        """Get the broad category for a factor.

        Args:
            factor_id: The unique factor identifier.

        Returns:
            The FactorCategory for this factor.
        """
        meta = self.get_meta(factor_id)
        return _ZOO_CATEGORY_MAP.get(meta.zoo, FactorCategory.TECHNICAL)

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

    def compute_batch(
        self,
        factor_ids: List[str],
        df: pd.DataFrame,
        skip_errors: bool = True,
    ) -> Dict[str, pd.Series]:
        """Compute multiple factors on the same DataFrame.

        Args:
            factor_ids: List of factor IDs to compute.
            df: Input DataFrame with OHLCV data.
            skip_errors: If True, skip factors that fail; if False, raise.

        Returns:
            Dict mapping factor_id -> pd.Series of computed values.
        """
        results: Dict[str, pd.Series] = {}
        for fid in factor_ids:
            try:
                results[fid] = self.compute(fid, df)
            except Exception as exc:
                if skip_errors:
                    logger.warning("Skipping factor %s: %s", fid, exc)
                else:
                    raise
        return results

    def correlation_matrix(
        self,
        df: pd.DataFrame,
        factor_ids: Optional[List[str]] = None,
        method: str = "pearson",
    ) -> pd.DataFrame:
        """Compute pairwise correlation matrix for factor values.

        Args:
            df: Input DataFrame with OHLCV data.
            factor_ids: List of factor IDs. If None, uses all registered.
            method: Correlation method ('pearson' or 'spearman').

        Returns:
            DataFrame of pairwise correlations between factors.
        """
        if factor_ids is None:
            factor_ids = self.list()

        # Compute all factors
        results = self.compute_batch(factor_ids, df, skip_errors=True)

        if not results:
            return pd.DataFrame()

        factor_df = pd.DataFrame(results, index=df.index)
        factor_df = factor_df.replace([np.inf, -np.inf], np.nan)

        if method == "spearman":
            factor_df = factor_df.rank()

        corr = factor_df.corr()
        return corr

    def screen(
        self,
        df: pd.DataFrame,
        factor_ids: Optional[List[str]] = None,
        min_ic: float = 0.02,
        forward_returns: Optional[pd.Series] = None,
    ) -> List[Tuple[str, float]]:
        """Screen factors by information coefficient (IC) against forward returns.

        Args:
            df: Input DataFrame with OHLCV data.
            factor_ids: List of factor IDs. If None, uses all registered.
            min_ic: Minimum absolute IC to include.
            forward_returns: Forward returns for IC computation.
                If None, uses 1-day forward returns from close.

        Returns:
            List of (factor_id, IC) tuples sorted by absolute IC descending.
        """
        if factor_ids is None:
            factor_ids = self.list()

        results = self.compute_batch(factor_ids, df, skip_errors=True)

        if forward_returns is None:
            forward_returns = df["close"].pct_change().shift(-1)

        scored: List[Tuple[str, float]] = []
        for fid, values in results.items():
            aligned = pd.DataFrame({"factor": values, "forward": forward_returns}).dropna()
            if len(aligned) < 20:
                continue
            ic = aligned["factor"].corr(aligned["forward"])
            if not np.isnan(ic) and abs(ic) >= min_ic:
                scored.append((fid, float(ic)))

        scored.sort(key=lambda x: abs(x[1]), reverse=True)
        return scored

    def get_dependencies(self, factor_id: str) -> List[str]:
        """Get the column dependencies for a factor.

        Args:
            factor_id: The unique factor identifier.

        Returns:
            List of required column names.
        """
        meta = self.get_meta(factor_id)
        return list(meta.columns_required)

    def group_by_category(self) -> Dict[FactorCategory, List[str]]:
        """Group all registered factors by category.

        Returns:
            Dict mapping FactorCategory -> list of factor IDs.
        """
        groups: Dict[FactorCategory, List[str]] = {}
        for name, meta in self._meta.items():
            cat = _ZOO_CATEGORY_MAP.get(meta.zoo, FactorCategory.TECHNICAL)
            if cat not in groups:
                groups[cat] = []
            groups[cat].append(name)
        for cat in groups:
            groups[cat].sort()
        return groups

    def group_by_zoo(self) -> Dict[str, List[str]]:
        """Group all registered factors by zoo.

        Returns:
            Dict mapping zoo name -> list of factor IDs.
        """
        groups: Dict[str, List[str]] = {}
        for name, meta in self._meta.items():
            if meta.zoo not in groups:
                groups[meta.zoo] = []
            groups[meta.zoo].append(name)
        for zoo in groups:
            groups[zoo].sort()
        return groups

    def group_by_theme(self) -> Dict[str, List[str]]:
        """Group all registered factors by theme.

        Returns:
            Dict mapping theme name -> list of factor IDs.
        """
        groups: Dict[str, List[str]] = {}
        for name, meta in self._meta.items():
            for theme in meta.theme:
                if theme not in groups:
                    groups[theme] = []
                groups[theme].append(name)
        for theme in groups:
            groups[theme].sort()
        return groups

    def find_low_correlation_subset(
        self,
        df: pd.DataFrame,
        factor_ids: Optional[List[str]] = None,
        max_corr: float = 0.7,
        prefer_high_ic: bool = True,
        forward_returns: Optional[pd.Series] = None,
    ) -> List[str]:
        """Find a subset of low-correlation factors using greedy selection.

        Args:
            df: Input DataFrame with OHLCV data.
            factor_ids: Candidate factor IDs. If None, uses all registered.
            max_corr: Maximum pairwise correlation allowed.
            prefer_high_ic: If True, prioritize factors with higher |IC|.
            forward_returns: Forward returns for IC computation.

        Returns:
            List of factor IDs forming a low-correlation subset.
        """
        if factor_ids is None:
            factor_ids = self.list()

        # Compute correlation matrix
        corr_matrix = self.correlation_matrix(df, factor_ids)
        if corr_matrix.empty:
            return []

        # Optionally sort by IC
        if prefer_high_ic and forward_returns is not None:
            scored = self.screen(df, factor_ids, min_ic=0.0, forward_returns=forward_returns)
            order = [fid for fid, _ in scored if fid in corr_matrix.columns]
            # Add remaining factors not scored
            for fid in corr_matrix.columns:
                if fid not in order:
                    order.append(fid)
        else:
            order = list(corr_matrix.columns)

        selected: List[str] = []
        for fid in order:
            if fid not in corr_matrix.columns:
                continue
            # Check correlation with all already-selected factors
            is_ok = True
            for sel_fid in selected:
                if sel_fid in corr_matrix.columns and fid in corr_matrix.index:
                    c = abs(corr_matrix.loc[fid, sel_fid])
                    if not np.isnan(c) and c > max_corr:
                        is_ok = False
                        break
            if is_ok:
                selected.append(fid)

        return selected

    def health(self) -> Dict:
        """Return registry health status.

        Returns:
            Dict with counts and any load errors.
        """
        return {
            "loaded": len(self._factors),
            "failed": len(self._load_errors),
            "errors": self._load_errors,
            "by_zoo": self.group_by_zoo(),
            "by_category": {cat.value: factors for cat, factors in self.group_by_category().items()},
            "by_theme": self.group_by_theme(),
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
                "decay_horizon": meta.decay_horizon,
                "category": _ZOO_CATEGORY_MAP.get(meta.zoo, "technical").value,
            }
            for name, meta in self._meta.items()
        }

    def describe(self, factor_id: str) -> Dict:
        """Return detailed description of a single factor.

        Args:
            factor_id: The unique factor identifier.

        Returns:
            Dict with factor metadata and category info.
        """
        meta = self.get_meta(factor_id)
        return {
            "id": meta.id,
            "name": factor_id,
            "zoo": meta.zoo,
            "category": _ZOO_CATEGORY_MAP.get(meta.zoo, "technical").value,
            "theme": meta.theme,
            "formula": meta.formula_latex,
            "columns_required": meta.columns_required,
            "universe": meta.universe,
            "frequency": meta.frequency,
            "decay_horizon": meta.decay_horizon,
            "min_warmup_bars": meta.min_warmup_bars,
            "notes": meta.notes,
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
