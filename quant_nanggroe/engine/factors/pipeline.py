"""Factor Computation Pipeline — batch computation of multiple factors.

The pipeline orchestrates the computation of multiple factors on a single
DataFrame, handling column dependencies, warmup validation, and output
alignment. It supports:

- Sequential or batch factor computation
- Factor neutralization (cross-sectional and industry)
- Factor combination (weighted, rank-based)
- Outlier handling (winsorization, z-score)
- Missing data handling (forward-fill, interpolation)
- Factor standardization

Usage:
    pipeline = FactorPipeline(["momentum", "mean_reversion_20", "rsi_14"])
    results = pipeline.compute(df)
    combined = pipeline.combine_signals(results, method="mean")
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from quant_nanggroe.engine.factors.base import AlphaFactor
from quant_nanggroe.engine.factors.registry import FactorRegistry, get_default_registry

logger = logging.getLogger(__name__)


class CombineMethod(str, Enum):
    """Methods for combining multiple factor signals."""

    MEAN = "mean"
    MEDIAN = "median"
    RANK_AVERAGE = "rank_average"
    ZSCORE_AVERAGE = "zscore_average"
    MAX = "max"
    MIN = "min"
    WEIGHTED = "weighted"


class OutlierMethod(str, Enum):
    """Methods for handling outliers in factor values."""

    NONE = "none"
    WINSORIZE = "winsorize"
    ZSCORE_CLIP = "zscore_clip"
    PERCENTILE_CLIP = "percentile_clip"


class MissingDataMethod(str, Enum):
    """Methods for handling missing data in factor values."""

    NONE = "none"
    FILLNA = "fillna"
    FORWARD_FILL = "forward_fill"
    INTERPOLATE = "interpolate"


class NeutralizationMethod(str, Enum):
    """Methods for neutralizing factor exposures."""

    NONE = "none"
    CROSS_SECTIONAL = "cross_sectional"
    INDUSTRY = "industry"
    MARKET = "market"


class FactorPipeline:
    """Batch computation pipeline for alpha factors.

    Orchestrates the computation of multiple factors on a single DataFrame,
    handling column dependencies, warmup validation, and output alignment.

    Enhanced with:
    - Factor neutralization (cross-sectional, industry, market)
    - Outlier handling (winsorization, z-score clipping)
    - Missing data handling (forward-fill, interpolation)
    - Factor standardization
    - Pre/post computation hooks
    """

    def __init__(
        self,
        factor_ids: Optional[List[str]] = None,
        registry: Optional[FactorRegistry] = None,
    ) -> None:
        """Initialize the pipeline.

        Args:
            factor_ids: List of factor IDs to compute. If None, uses all registered.
            registry: FactorRegistry instance. If None, uses default singleton.
        """
        self._registry = registry or get_default_registry()
        if factor_ids is not None:
            self._factor_ids = factor_ids
        else:
            self._factor_ids = self._registry.list()

        self._outlier_method: OutlierMethod = OutlierMethod.NONE
        self._missing_method: MissingDataMethod = MissingDataMethod.NONE
        self._neutralization: NeutralizationMethod = NeutralizationMethod.NONE
        self._outlier_params: Dict = {}
        self._missing_params: Dict = {}
        self._industry_dummies: Optional[pd.DataFrame] = None
        self._pre_hooks: List[Callable] = []
        self._post_hooks: List[Callable] = []

    @property
    def factor_ids(self) -> List[str]:
        """List of factor IDs in this pipeline."""
        return list(self._factor_ids)

    def set_outlier_handling(
        self,
        method: OutlierMethod = OutlierMethod.WINSORIZE,
        **kwargs,
    ) -> "FactorPipeline":
        """Configure outlier handling for computed factors.

        Args:
            method: Outlier handling method.
            **kwargs: Method-specific parameters:
                - winsorize: lower_pct (default 0.01), upper_pct (default 0.99)
                - zscore_clip: threshold (default 3.0)
                - percentile_clip: lower (default 0.01), upper (default 0.99)

        Returns:
            Self for method chaining.
        """
        self._outlier_method = method
        self._outlier_params = kwargs
        return self

    def set_missing_data_handling(
        self,
        method: MissingDataMethod = MissingDataMethod.FORWARD_FILL,
        **kwargs,
    ) -> "FactorPipeline":
        """Configure missing data handling for computed factors.

        Args:
            method: Missing data handling method.
            **kwargs: Method-specific parameters:
                - fillna: value (default 0)
                - forward_fill: limit (default None)
                - interpolate: method (default 'linear')

        Returns:
            Self for method chaining.
        """
        self._missing_method = method
        self._missing_params = kwargs
        return self

    def set_neutralization(
        self,
        method: NeutralizationMethod = NeutralizationMethod.CROSS_SECTIONAL,
        industry_dummies: Optional[pd.DataFrame] = None,
    ) -> "FactorPipeline":
        """Configure factor neutralization.

        Args:
            method: Neutralization method.
            industry_dummies: One-hot industry dummy matrix for industry neutralization.

        Returns:
            Self for method chaining.
        """
        self._neutralization = method
        self._industry_dummies = industry_dummies
        return self

    def add_pre_hook(self, hook: Callable) -> "FactorPipeline":
        """Add a pre-computation hook.

        The hook receives the input DataFrame and returns a (possibly modified) DataFrame.

        Args:
            hook: Callable that takes pd.DataFrame and returns pd.DataFrame.

        Returns:
            Self for method chaining.
        """
        self._pre_hooks.append(hook)
        return self

    def add_post_hook(self, hook: Callable) -> "FactorPipeline":
        """Add a post-computation hook.

        The hook receives the results dict and returns a (possibly modified) results dict.

        Args:
            hook: Callable that takes Dict[str, pd.Series] and returns same.

        Returns:
            Self for method chaining.
        """
        self._post_hooks.append(hook)
        return self

    def compute(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """Compute all pipeline factors on the given DataFrame.

        Args:
            df: Input DataFrame with OHLCV data.

        Returns:
            Dict mapping factor_id -> pd.Series of computed values.
        """
        # Apply pre-hooks
        input_df = df.copy()
        for hook in self._pre_hooks:
            input_df = hook(input_df)

        results: Dict[str, pd.Series] = {}

        for fid in self._factor_ids:
            try:
                result = self._registry.compute(fid, input_df)
                # Apply post-processing
                result = self._handle_outliers(result)
                result = self._handle_missing_data(result)
                result = self._neutralize(result)
                results[fid] = result
            except ValueError as exc:
                logger.warning("Skipping factor %s: %s", fid, exc)
            except Exception as exc:
                logger.error("Error computing factor %s: %s", fid, exc)

        # Apply post-hooks
        for hook in self._post_hooks:
            results = hook(results)

        return results

    def compute_as_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute all pipeline factors and return as a single DataFrame.

        Args:
            df: Input DataFrame with OHLCV data.

        Returns:
            DataFrame where each column is a factor's computed values.
        """
        results = self.compute(df)
        if not results:
            return pd.DataFrame(index=df.index)

        return pd.DataFrame(results, index=df.index)

    def combine_signals(
        self,
        results: Dict[str, pd.Series],
        method: CombineMethod = CombineMethod.RANK_AVERAGE,
        weights: Optional[Dict[str, float]] = None,
    ) -> pd.Series:
        """Combine multiple factor signals into a single composite signal.

        Args:
            results: Dict mapping factor_id -> pd.Series of values.
            method: Combination method.
            weights: Optional weight dict for weighted averaging.

        Returns:
            pd.Series of combined signal values.
        """
        if not results:
            return pd.Series(dtype=float)

        # Align all series to same index
        signal_df = pd.DataFrame(results)
        signal_df = signal_df.replace([np.inf, -np.inf], np.nan)

        if method == CombineMethod.MEAN:
            if weights:
                weight_series = pd.Series(weights)
                for col in signal_df.columns:
                    if col in weight_series.index:
                        signal_df[col] *= weight_series[col]
                # Normalize by weight sum
                total_weight = sum(weights.get(col, 0) for col in signal_df.columns)
                if total_weight > 0:
                    return signal_df.sum(axis=1) / total_weight
            return signal_df.mean(axis=1)

        elif method == CombineMethod.WEIGHTED:
            if weights is None:
                return signal_df.mean(axis=1)
            weight_series = pd.Series(weights)
            weighted = signal_df.mul(weight_series, axis=1)
            total_weight = sum(weights.get(col, 0) for col in signal_df.columns)
            if total_weight > 0:
                return weighted.sum(axis=1) / total_weight
            return weighted.sum(axis=1)

        elif method == CombineMethod.MEDIAN:
            return signal_df.median(axis=1)

        elif method == CombineMethod.RANK_AVERAGE:
            # Cross-sectional rank each factor, then average
            ranked = signal_df.rank(pct=True)
            if weights:
                weight_series = pd.Series(weights)
                for col in ranked.columns:
                    if col in weight_series.index:
                        ranked[col] *= weight_series[col]
                total_weight = sum(weights.get(col, 0) for col in ranked.columns)
                if total_weight > 0:
                    return ranked.sum(axis=1) / total_weight
            return ranked.mean(axis=1)

        elif method == CombineMethod.ZSCORE_AVERAGE:
            # Z-score each factor, then average
            means = signal_df.mean()
            stds = signal_df.std().replace(0, np.nan)
            zscored = (signal_df - means) / stds
            return zscored.mean(axis=1)

        elif method == CombineMethod.MAX:
            return signal_df.max(axis=1)

        elif method == CombineMethod.MIN:
            return signal_df.min(axis=1)

        else:
            raise ValueError(f"Unknown combine method: {method}")

    def validate_data(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """Validate that the DataFrame has required columns for all factors.

        Args:
            df: Input DataFrame.

        Returns:
            Dict with 'ready' (factors that can run) and 'missing' (factors
            that lack required columns, mapped to the missing column names).
        """
        ready: List[str] = []
        missing: Dict[str, List[str]] = {}

        for fid in self._factor_ids:
            try:
                meta = self._registry.get_meta(fid)
                missing_cols = [c for c in meta.columns_required if c not in df.columns]
                if missing_cols:
                    missing[fid] = missing_cols
                else:
                    ready.append(fid)
            except KeyError:
                missing[fid] = ["factor_not_registered"]

        return {"ready": ready, "missing": missing}

    # ─── Outlier Handling ─────────────────────────────────────────────────────

    def _handle_outliers(self, series: pd.Series) -> pd.Series:
        """Apply configured outlier handling to a factor series.

        Args:
            series: Factor values.

        Returns:
            Series with outliers handled.
        """
        if self._outlier_method == OutlierMethod.NONE:
            return series

        if self._outlier_method == OutlierMethod.WINSORIZE:
            lower_pct = self._outlier_params.get("lower_pct", 0.01)
            upper_pct = self._outlier_params.get("upper_pct", 0.99)
            lower = series.quantile(lower_pct)
            upper = series.quantile(upper_pct)
            return series.clip(lower=lower, upper=upper)

        elif self._outlier_method == OutlierMethod.ZSCORE_CLIP:
            threshold = self._outlier_params.get("threshold", 3.0)
            mean = series.mean()
            std = series.std()
            if std == 0 or np.isnan(std):
                return series
            z_scores = (series - mean) / std
            clipped = series.copy()
            clipped[z_scores > threshold] = mean + threshold * std
            clipped[z_scores < -threshold] = mean - threshold * std
            return clipped

        elif self._outlier_method == OutlierMethod.PERCENTILE_CLIP:
            lower = self._outlier_params.get("lower", 0.01)
            upper = self._outlier_params.get("upper", 0.99)
            lower_val = series.quantile(lower)
            upper_val = series.quantile(upper)
            return series.clip(lower=lower_val, upper=upper_val)

        return series

    # ─── Missing Data Handling ────────────────────────────────────────────────

    def _handle_missing_data(self, series: pd.Series) -> pd.Series:
        """Apply configured missing data handling to a factor series.

        Args:
            series: Factor values.

        Returns:
            Series with missing data handled.
        """
        if self._missing_method == MissingDataMethod.NONE:
            return series

        if self._missing_method == MissingDataMethod.FILLNA:
            value = self._missing_params.get("value", 0)
            return series.fillna(value)

        elif self._missing_method == MissingDataMethod.FORWARD_FILL:
            limit = self._missing_params.get("limit", None)
            return series.ffill(limit=limit)

        elif self._missing_method == MissingDataMethod.INTERPOLATE:
            method = self._missing_params.get("method", "linear")
            return series.interpolate(method=method)

        return series

    # ─── Neutralization ───────────────────────────────────────────────────────

    def _neutralize(self, series: pd.Series) -> pd.Series:
        """Apply configured neutralization to a factor series.

        Args:
            series: Factor values.

        Returns:
            Neutralized factor values.
        """
        if self._neutralization == NeutralizationMethod.NONE:
            return series

        if self._neutralization == NeutralizationMethod.CROSS_SECTIONAL:
            # Subtract cross-sectional mean (demeaning)
            mean_val = series.mean()
            if np.isnan(mean_val):
                return series
            return series - mean_val

        elif self._neutralization == NeutralizationMethod.INDUSTRY:
            if self._industry_dummies is None:
                logger.warning("Industry neutralization requested but no industry dummies provided")
                return series
            from quant_nanggroe.engine.factors.barra import industry_neutralize
            return industry_neutralize(series, self._industry_dummies)

        elif self._neutralization == NeutralizationMethod.MARKET:
            # Subtract market-wide average (same as cross-sectional for single-asset)
            mean_val = series.mean()
            if np.isnan(mean_val):
                return series
            return series - mean_val

        return series

    # ─── Standardization ──────────────────────────────────────────────────────

    @staticmethod
    def zscore(series: pd.Series) -> pd.Series:
        """Z-score standardize a factor series.

        Args:
            series: Factor values.

        Returns:
            Z-scored series with mean ~0, std ~1.
        """
        mean = series.mean()
        std = series.std()
        if std == 0 or np.isnan(std):
            return pd.Series(0.0, index=series.index, name=series.name)
        return (series - mean) / std

    @staticmethod
    def rank_normalize(series: pd.Series) -> pd.Series:
        """Rank-normalize a factor series to [0, 1].

        Args:
            series: Factor values.

        Returns:
            Rank-normalized series in [0, 1].
        """
        return series.rank(pct=True, na_option="keep")

    @staticmethod
    def quantile_transform(
        series: pd.Series,
        n_quantiles: int = 10,
    ) -> pd.Series:
        """Quantile-transform a factor series into discrete bins.

        Args:
            series: Factor values.
            n_quantiles: Number of quantile bins.

        Returns:
            Series of quantile labels (1 to n_quantiles).
        """
        return pd.qcut(series, n_quantiles, labels=False, duplicates="drop") + 1
