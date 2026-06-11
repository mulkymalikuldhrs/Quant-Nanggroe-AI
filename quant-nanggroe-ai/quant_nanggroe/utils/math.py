"""Mathematical utilities for Quant Nanggroe AI.

Pure functions for common mathematical operations used throughout
the codebase. No side effects, no state.
"""

from __future__ import annotations

import numpy as np
from typing import Union


Number = Union[int, float]


def safe_divide(
    numerator: Number,
    denominator: Number,
    default: float = 0.0,
) -> float:
    """Safely divide two numbers, returning default on zero denominator.

    Args:
        numerator: The numerator.
        denominator: The denominator.
        default: Value to return if denominator is zero.

    Returns:
        Division result or default.
    """
    if denominator == 0:
        return default
    return float(numerator / denominator)


def clamp(value: Number, min_val: Number, max_val: Number) -> float:
    """Clamp a value to a range [min_val, max_val].

    Args:
        value: Value to clamp.
        min_val: Minimum allowed value.
        max_val: Maximum allowed value.

    Returns:
        Clamped value.
    """
    return float(max(min_val, min(value, max_val)))


def pct_change(current: Number, previous: Number) -> float:
    """Calculate percentage change from previous to current.

    Args:
        current: Current value.
        previous: Previous value.

    Returns:
        Percentage change. Returns 0.0 if previous is zero.
    """
    if previous == 0:
        return 0.0
    return float((current - previous) / abs(previous))


def rolling_sum(data: np.ndarray, window: int) -> np.ndarray:
    """Calculate rolling sum using cumulative sum for O(n) performance.

    Args:
        data: Input array.
        window: Rolling window size.

    Returns:
        Array of rolling sums with NaN for initial positions.
    """
    arr = np.asarray(data, dtype=float)
    n = len(arr)
    if n < window:
        return np.full(n, np.nan)

    result = np.full(n, np.nan)
    cumsum = np.cumsum(arr)
    result[window - 1:] = cumsum[window - 1:] - np.concatenate([[0], cumsum[:-window]])
    return result


def weighted_mean(values: list[float], weights: list[float]) -> float:
    """Calculate weighted mean of values.

    Args:
        values: List of values.
        weights: List of weights (same length as values).

    Returns:
        Weighted mean. Returns 0.0 if total weight is zero.
    """
    if not values or not weights or len(values) != len(weights):
        return 0.0
    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0
    return float(sum(v * w for v, w in zip(values, weights)) / total_weight)


def normalize_to_range(
    value: Number,
    old_min: Number,
    old_max: Number,
    new_min: Number = 0.0,
    new_max: Number = 1.0,
) -> float:
    """Normalize a value from [old_min, old_max] to [new_min, new_max].

    Args:
        value: Value to normalize.
        old_min: Minimum of original range.
        old_max: Maximum of original range.
        new_min: Minimum of target range.
        new_max: Maximum of target range.

    Returns:
        Normalized value. Returns new_min if old_range is zero.
    """
    old_range = old_max - old_min
    if old_range == 0:
        return float(new_min)
    return float(((value - old_min) / old_range) * (new_max - new_min) + new_min)


def annualized_return(
    total_return: float,
    days: int,
    trading_days_per_year: int = 252,
) -> float:
    """Calculate annualized return from total return over a period.

    Args:
        total_return: Total return as a decimal (e.g., 0.5 for 50%).
        days: Number of calendar days.
        trading_days_per_year: Trading days per year (default 252).

    Returns:
        Annualized return as a decimal.
    """
    if days <= 0:
        return 0.0
    trading_days = days * (trading_days_per_year / 365)
    if trading_days <= 0:
        return 0.0
    return float((1 + total_return) ** (trading_days_per_year / trading_days) - 1)
