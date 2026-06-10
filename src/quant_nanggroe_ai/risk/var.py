"""
Value at Risk (VaR)
====================
Parametric (variance-covariance), Historical, and Monte Carlo methods.
"""

from __future__ import annotations

import math
import random
from typing import Any

import numpy as np


def parametric_var(
    returns: list[float],
    confidence: float = 0.95,
) -> float:
    """
    Parametric VaR using variance-covariance method.

    Assumes returns are normally distributed.
    VaR = μ - z * σ (for the given confidence level)

    Args:
        returns: List of portfolio returns
        confidence: Confidence level (0.95 = 95%)

    Returns:
        VaR as a positive number (the potential loss)
    """
    if not returns:
        return 0.0

    arr = np.array(returns)
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1))

    z_scores = {0.90: 1.282, 0.95: 1.645, 0.99: 2.326}
    z = z_scores.get(confidence, 1.645)

    var = mean - z * std
    return abs(var) if var < 0 else 0.0


def historical_var(
    returns: list[float],
    confidence: float = 0.95,
) -> float:
    """
    Historical VaR using empirical distribution.

    Simply takes the appropriate percentile from historical returns.

    Args:
        returns: List of portfolio returns
        confidence: Confidence level (0.95 = 95%)

    Returns:
        VaR as a positive number
    """
    if not returns:
        return 0.0

    arr = np.array(returns)
    percentile = (1 - confidence) * 100
    var = float(np.percentile(arr, percentile))
    return abs(var) if var < 0 else 0.0


def monte_carlo_var(
    returns: list[float],
    confidence: float = 0.95,
    simulations: int = 10000,
    time_horizon: int = 1,
) -> float:
    """
    Monte Carlo VaR using parametric bootstrap.

    Simulates portfolio returns using fitted normal distribution.

    Args:
        returns: List of portfolio returns
        confidence: Confidence level
        simulations: Number of Monte Carlo simulations
        time_horizon: Time horizon in days

    Returns:
        VaR as a positive number
    """
    if not returns:
        return 0.0

    arr = np.array(returns)
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1))

    # Simulate returns
    simulated = np.random.normal(
        mean * time_horizon,
        std * math.sqrt(time_horizon),
        simulations,
    )

    percentile = (1 - confidence) * 100
    var = float(np.percentile(simulated, percentile))
    return abs(var) if var < 0 else 0.0
