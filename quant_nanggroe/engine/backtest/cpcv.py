"""Combinatorial Purged Cross-Validation (CPCV) — de Prado Backtesting Method.

Implements the CPCV backtesting method from Marcos López de Prado's
*Advances in Financial Machine Learning* (Chapter 12).  CPCV addresses
the fundamental flaw of walk-forward backtesting — overfitting to a
single train/test path — by evaluating a strategy across **all**
combinations of test groups, with purging and embargo to prevent
information leakage.

Key Concepts
------------
* **Groups**: The dataset is divided into *n_groups* contiguous groups.
* **Combinations**: For each combination of *n_test_groups* test groups,
  the remaining groups form the training set.
* **Purging**: Remove training samples within *purge_gap* timestamps of
  any test boundary to prevent label leakage.
* **Embargo**: Remove training samples after each test set ends for
  *embargo* timestamps to account for serial correlation.
* **Evaluation**: Run the strategy on every train/test split and compute
  the mean Sharpe ratio with a confidence interval.

Usage::

    from quant_nanggroe.engine.backtest.cpcv import CombinatorialPurgedCV

    cpcv = CombinatorialPurgedCV(n_groups=8, n_test_groups=2, purge_gap=5, embargo=3)
    splits = list(cpcv.split(timestamps))
    result = await cpcv.evaluate_strategy(strategy_fn, data)
    print(f"Sharpe: {result.mean_sharpe:.2f} ± {result.sharpe_ci:.2f}")
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from itertools import combinations
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


# ── Pydantic Models ─────────────────────────────────────────────────────


class CPCVSplitResult(BaseModel):
    """Result from a single CPCV train/test split.

    Attributes:
        split_id: Unique identifier for this split.
        train_indices: Indices of training samples.
        test_indices: Indices of test samples.
        test_groups: Which group numbers are in the test set.
        n_train: Number of training samples (after purging/embargo).
        n_test: Number of test samples.
        n_purged: Number of samples removed by purging.
        n_embargoed: Number of samples removed by embargo.
    """

    model_config = ConfigDict(frozen=False)

    split_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    train_indices: List[int] = Field(default_factory=list)
    test_indices: List[int] = Field(default_factory=list)
    test_groups: List[int] = Field(default_factory=list)
    n_train: int = 0
    n_test: int = 0
    n_purged: int = 0
    n_embargoed: int = 0


class CPCVEvaluationResult(BaseModel):
    """Result from evaluating a strategy across all CPCV splits.

    Attributes:
        result_id: Unique identifier.
        n_splits: Total number of CPCV splits evaluated.
        mean_sharpe: Mean Sharpe ratio across all splits.
        std_sharpe: Standard deviation of Sharpe ratios.
        sharpe_ci_lower: 95% confidence interval lower bound.
        sharpe_ci_upper: 95% confidence interval upper bound.
        sharpe_ci_width: Width of the confidence interval.
        per_split_sharpes: Sharpe ratio for each individual split.
        per_split_returns: Mean return for each individual split.
        strategy_passes: Whether mean Sharpe exceeds the threshold.
        timestamp: UTC timestamp of evaluation.
    """

    model_config = ConfigDict(frozen=False)

    result_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    n_splits: int = 0
    mean_sharpe: float = 0.0
    std_sharpe: float = 0.0
    sharpe_ci_lower: float = 0.0
    sharpe_ci_upper: float = 0.0
    sharpe_ci_width: float = 0.0
    per_split_sharpes: List[float] = Field(default_factory=list)
    per_split_returns: List[float] = Field(default_factory=list)
    strategy_passes: bool = False
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_api_dict(self) -> Dict[str, Any]:
        """Convert to API-safe dictionary."""
        return {
            "result_id": self.result_id,
            "n_splits": self.n_splits,
            "mean_sharpe": round(self.mean_sharpe, 4),
            "std_sharpe": round(self.std_sharpe, 4),
            "sharpe_ci": [round(self.sharpe_ci_lower, 4), round(self.sharpe_ci_upper, 4)],
            "sharpe_ci_width": round(self.sharpe_ci_width, 4),
            "strategy_passes": self.strategy_passes,
            "timestamp": self.timestamp.isoformat(),
        }


# ── CPCV Implementation ────────────────────────────────────────────────


class CombinatorialPurgedCV:
    """Combinatorial Purged Cross-Validation (de Prado, AFML Ch.12).

    Divides data into *n_groups* contiguous groups, then generates all
    C(n_groups, n_test_groups) train/test splits.  For each split,
    training samples within *purge_gap* of test boundaries and within
    *embargo* after test ends are removed to prevent information leakage.

    Args:
        n_groups: Number of groups to divide data into.
        n_test_groups: Number of groups in each test set.
        purge_gap: Number of timestamps to purge around test boundaries.
        embargo: Number of timestamps to embargo after test set ends.
        min_train_fraction: Minimum fraction of data required in training set.

    Example::

        cpcv = CombinatorialPurgedCV(n_groups=8, n_test_groups=2, purge_gap=5, embargo=3)
        for train_idx, test_idx in cpcv.split(timestamps):
            model.fit(X[train_idx], y[train_idx])
            predictions = model.predict(X[test_idx])
    """

    def __init__(
        self,
        n_groups: int = 8,
        n_test_groups: int = 2,
        purge_gap: int = 5,
        embargo: int = 3,
        min_train_fraction: float = 0.3,
    ) -> None:
        if n_groups <= 0:
            raise ValueError("n_groups must be positive")
        if n_test_groups <= 0 or n_test_groups >= n_groups:
            raise ValueError(
                "n_test_groups must be in [1, n_groups - 1]"
            )
        if purge_gap < 0:
            raise ValueError("purge_gap must be non-negative")
        if embargo < 0:
            raise ValueError("embargo must be non-negative")
        if not 0.0 < min_train_fraction < 1.0:
            raise ValueError("min_train_fraction must be in (0, 1)")

        self.n_groups = n_groups
        self.n_test_groups = n_test_groups
        self.purge_gap = purge_gap
        self.embargo = embargo
        self.min_train_fraction = min_train_fraction

    # ── Split Generation ─────────────────────────────────────────────

    def split(
        self,
        timestamps: Sequence[Any],
    ) -> List[Tuple[np.ndarray, np.ndarray]]:
        """Generate train/test index pairs for all CPCV splits.

        Args:
            timestamps: Sequence of timestamps (or indices) for each
                sample.  Used to determine group boundaries and purge
                distances.

        Yields:
            Tuples of (train_indices, test_indices) as numpy arrays.

        Raises:
            ValueError: If timestamps is shorter than n_groups.
        """
        n_samples = len(timestamps)
        if n_samples < self.n_groups:
            raise ValueError(
                f"Cannot split {n_samples} samples into {self.n_groups} groups"
            )

        # Divide samples into groups
        group_boundaries = self._compute_group_boundaries(n_samples)

        # Generate all combinations of test groups
        all_combos = list(combinations(range(self.n_groups), self.n_test_groups))

        results: List[Tuple[np.ndarray, np.ndarray]] = []

        for test_group_combo in all_combos:
            test_indices = self._get_indices_for_groups(
                test_group_combo, group_boundaries
            )

            # Get all non-test groups as candidate training set
            train_groups = [
                g for g in range(self.n_groups) if g not in test_group_combo
            ]
            train_indices = self._get_indices_for_groups(
                tuple(train_groups), group_boundaries
            )

            # Apply purging: remove training samples within purge_gap of test boundaries
            purged_train, n_purged = self._apply_purging(
                train_indices, test_indices, timestamps
            )

            # Apply embargo: remove training samples after test ends
            embargoed_train, n_embargoed = self._apply_embargo(
                purged_train, test_indices, timestamps
            )

            # Check minimum training set size
            if len(embargoed_train) < self.min_train_fraction * n_samples:
                logger.debug(
                    "cpcv_split_skipped_insufficient_train",
                    extra={
                        "test_groups": test_group_combo,
                        "n_train": len(embargoed_train),
                        "min_required": int(self.min_train_fraction * n_samples),
                    },
                )
                continue

            results.append(
                (np.array(embargoed_train), np.array(test_indices))
            )

        return results

    def split_detailed(
        self,
        timestamps: Sequence[Any],
    ) -> List[CPCVSplitResult]:
        """Generate detailed split results with metadata.

        Same as ``split()`` but returns CPCVSplitResult objects with
        purge/embargo counts.

        Args:
            timestamps: Sequence of timestamps for each sample.

        Returns:
            List of CPCVSplitResult objects.
        """
        n_samples = len(timestamps)
        group_boundaries = self._compute_group_boundaries(n_samples)
        all_combos = list(combinations(range(self.n_groups), self.n_test_groups))

        results: List[CPCVSplitResult] = []

        for test_group_combo in all_combos:
            test_indices = self._get_indices_for_groups(
                test_group_combo, group_boundaries
            )

            train_groups = [
                g for g in range(self.n_groups) if g not in test_group_combo
            ]
            train_indices = self._get_indices_for_groups(
                tuple(train_groups), group_boundaries
            )

            purged_train, n_purged = self._apply_purging(
                train_indices, test_indices, timestamps
            )
            embargoed_train, n_embargoed = self._apply_embargo(
                purged_train, test_indices, timestamps
            )

            if len(embargoed_train) < self.min_train_fraction * n_samples:
                continue

            results.append(
                CPCVSplitResult(
                    train_indices=embargoed_train,
                    test_indices=test_indices,
                    test_groups=list(test_group_combo),
                    n_train=len(embargoed_train),
                    n_test=len(test_indices),
                    n_purged=n_purged,
                    n_embargoed=n_embargoed,
                )
            )

        return results

    # ── Strategy Evaluation ──────────────────────────────────────────

    async def evaluate_strategy(
        self,
        strategy_fn: Callable[
            [np.ndarray, np.ndarray], Tuple[float, float]
        ],
        data: np.ndarray,
        sharpe_threshold: float = 0.5,
        annualize_factor: float = 252.0,
    ) -> CPCVEvaluationResult:
        """Evaluate a strategy across all CPCV splits.

        Runs the strategy function on every train/test split and computes
        the mean Sharpe ratio with a 95% confidence interval.

        Args:
            strategy_fn: Async or sync function that takes
                (train_indices, test_indices) and returns
                (sharpe_ratio, mean_return) for the test period.
            data: Full dataset (used to generate splits).
            sharpe_threshold: Minimum acceptable mean Sharpe ratio.
            annualize_factor: Annualization factor (default: 252 trading days).

        Returns:
            CPCVEvaluationResult with aggregated performance metrics.
        """
        import asyncio

        timestamps = list(range(len(data)))
        splits = self.split(timestamps)

        if not splits:
            logger.warning("cpcv_no_valid_splits")
            return CPCVEvaluationResult(n_splits=0)

        sharpes: List[float] = []
        returns_list: List[float] = []

        for train_idx, test_idx in splits:
            try:
                result = strategy_fn(train_idx, test_idx)
                # Handle both sync and async strategy functions
                if asyncio.iscoroutine(result):
                    sharpe, mean_ret = await result
                else:
                    sharpe, mean_ret = result

                # Annualize Sharpe
                annualized_sharpe = sharpe * np.sqrt(annualize_factor) if sharpe != 0 else 0.0
                sharpes.append(annualized_sharpe)
                returns_list.append(mean_ret)

            except Exception as exc:
                logger.warning(
                    "cpcv_strategy_failed_on_split",
                    extra={"error": str(exc)},
                )
                continue

        if not sharpes:
            return CPCVEvaluationResult(n_splits=len(splits))

        sharpes_arr = np.array(sharpes)
        mean_sharpe = float(np.mean(sharpes_arr))
        std_sharpe = float(np.std(sharpes_arr, ddof=1)) if len(sharpes) > 1 else 0.0

        # 95% confidence interval (t-distribution for small samples)
        n = len(sharpes)
        if n > 1:
            # Use t-value for 95% CI
            from scipy import stats as scipy_stats
            try:
                t_value = float(scipy_stats.t.ppf(0.975, df=n - 1))
            except ImportError:
                t_value = 1.96  # Fallback to normal approximation
            margin = t_value * std_sharpe / np.sqrt(n)
        else:
            margin = 0.0

        ci_lower = mean_sharpe - margin
        ci_upper = mean_sharpe + margin

        return CPCVEvaluationResult(
            n_splits=len(splits),
            mean_sharpe=mean_sharpe,
            std_sharpe=std_sharpe,
            sharpe_ci_lower=ci_lower,
            sharpe_ci_upper=ci_upper,
            sharpe_ci_width=float(margin * 2),
            per_split_sharpes=sharpes,
            per_split_returns=returns_list,
            strategy_passes=mean_sharpe > sharpe_threshold,
        )

    # ── Internal Methods ─────────────────────────────────────────────

    def _compute_group_boundaries(
        self, n_samples: int
    ) -> List[Tuple[int, int]]:
        """Compute (start, end) index boundaries for each group.

        Groups are contiguous and approximately equal in size.

        Args:
            n_samples: Total number of samples.

        Returns:
            List of (start, end) tuples for each group.
        """
        group_size = n_samples // self.n_groups
        remainder = n_samples % self.n_groups

        boundaries: List[Tuple[int, int]] = []
        start = 0
        for i in range(self.n_groups):
            # Distribute remainder across first groups
            size = group_size + (1 if i < remainder else 0)
            end = start + size
            boundaries.append((start, end))
            start = end

        return boundaries

    def _get_indices_for_groups(
        self,
        groups: Tuple[int, ...],
        boundaries: List[Tuple[int, int]],
    ) -> List[int]:
        """Get all sample indices belonging to the specified groups.

        Args:
            groups: Tuple of group numbers.
            boundaries: Group boundaries from _compute_group_boundaries.

        Returns:
            Sorted list of sample indices.
        """
        indices: List[int] = []
        for g in groups:
            if 0 <= g < len(boundaries):
                start, end = boundaries[g]
                indices.extend(range(start, end))
        return sorted(indices)

    def _apply_purging(
        self,
        train_indices: List[int],
        test_indices: List[int],
        timestamps: Sequence[Any],
    ) -> Tuple[List[int], int]:
        """Remove training samples within purge_gap of test boundaries.

        Purging prevents label leakage by removing training samples
        whose labels might overlap with the test period.

        Args:
            train_indices: Candidate training indices.
            test_indices: Test set indices.
            timestamps: Full timestamp sequence.

        Returns:
            Tuple of (purged_train_indices, n_purged_count).
        """
        if self.purge_gap == 0 or not test_indices or not train_indices:
            return train_indices, 0

        test_start = min(test_indices)
        test_end = max(test_indices)

        # Remove training samples within purge_gap of test boundaries
        purged: List[int] = []
        n_purged = 0

        for idx in train_indices:
            # Check if this sample is too close to test boundaries
            # Purge before test start
            if idx < test_start and (test_start - idx) <= self.purge_gap:
                n_purged += 1
                continue
            # Purge after test end (but this is embargo's job)
            # Only purge samples that overlap with test range
            if idx >= test_start and idx <= test_end:
                n_purged += 1
                continue
            purged.append(idx)

        return purged, n_purged

    def _apply_embargo(
        self,
        train_indices: List[int],
        test_indices: List[int],
        timestamps: Sequence[Any],
    ) -> Tuple[List[int], int]:
        """Remove training samples after test ends for embargo period.

        Embargo addresses serial correlation by removing training
        samples that immediately follow the test period, as their
        labels may depend on test-period outcomes.

        Args:
            train_indices: Training indices (post-purging).
            test_indices: Test set indices.
            timestamps: Full timestamp sequence.

        Returns:
            Tuple of (embargoed_train_indices, n_embargoed_count).
        """
        if self.embargo == 0 or not test_indices or not train_indices:
            return train_indices, 0

        test_end = max(test_indices)
        embargo_limit = test_end + self.embargo

        embargoed: List[int] = []
        n_embargoed = 0

        for idx in train_indices:
            # Remove training samples in the embargo window after test
            if idx > test_end and idx <= embargo_limit:
                n_embargoed += 1
                continue
            embargoed.append(idx)

        return embargoed, n_embargoed

    # ── Properties ───────────────────────────────────────────────────

    @property
    def n_combinations(self) -> int:
        """Total number of train/test combinations.

        Equals C(n_groups, n_test_groups).
        """
        from math import comb
        return comb(self.n_groups, self.n_test_groups)

    @property
    def config_dict(self) -> Dict[str, Any]:
        """Configuration as a dictionary."""
        return {
            "n_groups": self.n_groups,
            "n_test_groups": self.n_test_groups,
            "purge_gap": self.purge_gap,
            "embargo": self.embargo,
            "n_combinations": self.n_combinations,
            "min_train_fraction": self.min_train_fraction,
        }


# ═══════════════════════════════════════════════════════════════════════
# Demo
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import asyncio

    # Generate synthetic price data
    np.random.seed(42)
    n_days = 500
    returns = np.random.normal(0.0005, 0.015, n_days)
    prices = 100 * np.exp(np.cumsum(returns))
    timestamps = list(range(n_days))

    # Initialize CPCV
    cpcv = CombinatorialPurgedCV(
        n_groups=8,
        n_test_groups=2,
        purge_gap=5,
        embargo=3,
    )

    print(f"CPCV Configuration: {cpcv.config_dict}")
    print(f"Total combinations: {cpcv.n_combinations}")

    # Generate splits
    splits = cpcv.split(timestamps)
    print(f"\nGenerated {len(splits)} valid splits")

    # Show first few splits
    for i, (train_idx, test_idx) in enumerate(splits[:3]):
        print(f"  Split {i}: train={len(train_idx)} samples, test={len(test_idx)} samples")

    # Detailed splits
    detailed = cpcv.split_detailed(timestamps)
    for ds in detailed[:3]:
        print(
            f"  Detailed {ds.split_id}: train={ds.n_train}, "
            f"test={ds.n_test}, purged={ds.n_purged}, "
            f"embargoed={ds.n_embargoed}, test_groups={ds.test_groups}"
        )

    # Evaluate a simple strategy
    def simple_strategy(
        train_idx: np.ndarray, test_idx: np.ndarray
    ) -> Tuple[float, float]:
        """Simple momentum strategy: long if recent return > 0."""
        test_returns = returns[test_idx]
        mean_ret = float(np.mean(test_returns))
        std_ret = float(np.std(test_returns))
        sharpe = mean_ret / std_ret if std_ret > 0 else 0.0
        return sharpe, mean_ret

    result = asyncio.run(
        cpcv.evaluate_strategy(simple_strategy, returns)
    )

    print(f"\nStrategy Evaluation:")
    print(f"  Mean Sharpe: {result.mean_sharpe:.4f}")
    print(f"  Std Sharpe: {result.std_sharpe:.4f}")
    print(f"  95% CI: [{result.sharpe_ci_lower:.4f}, {result.sharpe_ci_upper:.4f}]")
    print(f"  Passes threshold: {result.strategy_passes}")
    print(f"  API dict: {result.to_api_dict()}")
