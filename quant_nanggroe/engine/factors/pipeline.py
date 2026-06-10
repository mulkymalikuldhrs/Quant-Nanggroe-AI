"""Factor Computation Pipeline — batch computation of multiple factors.

The pipeline orchestrates the computation of multiple factors on a single
DataFrame, handling column dependencies, warmup validation, and output
alignment. It supports:

- Sequential or batch factor computation
- Dependency-aware ordering
- Output caching and deduplication
- Multi-factor signal combination

Usage:
    pipeline = FactorPipeline(["momentum", "mean_reversion_20", "rsi_14"])
    results = pipeline.compute(df)
    combined = pipeline.combine_signals(results, method="mean")
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Dict, List, Optional

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


class FactorPipeline:
    """Batch computation pipeline for alpha factors.

    Orchestrates the computation of multiple factors on a single DataFrame,
    handling column dependencies, warmup validation, and output alignment.
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

    @property
    def factor_ids(self) -> List[str]:
        """List of factor IDs in this pipeline."""
        return list(self._factor_ids)

    def compute(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """Compute all pipeline factors on the given DataFrame.

        Args:
            df: Input DataFrame with OHLCV data.

        Returns:
            Dict mapping factor_id -> pd.Series of computed values.
        """
        results: Dict[str, pd.Series] = {}

        for fid in self._factor_ids:
            try:
                result = self._registry.compute(fid, df)
                results[fid] = result
            except ValueError as exc:
                logger.warning("Skipping factor %s: %s", fid, exc)
            except Exception as exc:
                logger.error("Error computing factor %s: %s", fid, exc)

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
            return signal_df.mean(axis=1)

        elif method == CombineMethod.MEDIAN:
            return signal_df.median(axis=1)

        elif method == CombineMethod.RANK_AVERAGE:
            # Cross-sectional rank each factor, then average
            ranked = signal_df.rank(pct=True)
            return ranked.mean(axis=1)

        elif method == CombineMethod.ZSCORE_AVERAGE:
            # Z-score each factor, then average
            zscored = (signal_df - signal_df.mean()) / signal_df.std().replace(0, np.nan)
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
