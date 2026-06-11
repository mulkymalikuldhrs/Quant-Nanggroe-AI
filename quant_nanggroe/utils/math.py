"""Mathematical utility functions for Quant Nanggroe AI.

Pure functions for common financial calculations.
No external API calls, no side effects, fully deterministic.
"""

from __future__ import annotations

import math
from typing import Optional, Sequence

import numpy as np
import pandas as pd


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safe division that returns default on zero denominator.

    Args:
        numerator: Numerator value
        denominator: Denominator value
        default: Default value when denominator is zero

    Returns:
        Division result or default if denominator is zero
    """
    if denominator == 0 or not math.isfinite(denominator):
        return default
    return numerator / denominator


def round_price(price: float, tick_size: float = 0.01) -> float:
    """
    Round price to the nearest tick size.

    Args:
        price: Price to round
        tick_size: Minimum price increment

    Returns:
        Rounded price
    """
    if tick_size <= 0:
        return price
    return round(price / tick_size) * tick_size


def pct_change(current: float, previous: float) -> float:
    """
    Calculate percentage change between two values.

    Args:
        current: Current value
        previous: Previous value

    Returns:
        Percentage change as decimal (e.g., 0.05 for 5%)
    """
    return safe_divide(current - previous, previous, default=0.0)


def rolling_max_drawdown(prices: pd.Series) -> pd.Series:
    """
    Calculate rolling maximum drawdown for a price series.

    Args:
        prices: Price series

    Returns:
        Series of drawdown percentages
    """
    cumulative_max = prices.cummax()
    drawdown = (prices - cumulative_max) / cumulative_max
    return drawdown


def compute_sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    Compute annualized Sharpe ratio.

    Args:
        returns: Series of periodic returns
        risk_free_rate: Annual risk-free rate
        periods_per_year: Number of return periods per year

    Returns:
        Annualized Sharpe ratio
    """
    if returns.empty or returns.std() == 0:
        return 0.0
    excess_returns = returns - risk_free_rate / periods_per_year
    return float(
        np.sqrt(periods_per_year) * excess_returns.mean() / excess_returns.std()
    )


def compute_sortino_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    Compute annualized Sortino ratio (downside deviation only).

    Args:
        returns: Series of periodic returns
        risk_free_rate: Annual risk-free rate
        periods_per_year: Number of return periods per year

    Returns:
        Annualized Sortino ratio
    """
    if returns.empty:
        return 0.0
    excess_returns = returns - risk_free_rate / periods_per_year
    downside = excess_returns[excess_returns < 0]
    if downside.empty or downside.std() == 0:
        return 0.0
    return float(
        np.sqrt(periods_per_year) * excess_returns.mean() / downside.std()
    )


def wilders_smoothing(series: pd.Series, period: int) -> pd.Series:
    """
    Wilders Smoothing (exponential with alpha = 1/period).

    Used for proper ADX calculation instead of simple SMA proxy.

    Args:
        series: Input series
        period: Smoothing period

    Returns:
        Smoothed series
    """
    return series.ewm(alpha=1.0 / period, adjust=False).mean()
