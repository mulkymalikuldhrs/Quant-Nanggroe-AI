"""
Conditional Value at Risk (CVaR / Expected Shortfall)
======================================================
The expected loss GIVEN that the loss exceeds VaR.
More conservative than VaR — captures tail risk.
"""

from __future__ import annotations

import numpy as np


def historical_cvar(
    returns: list[float],
    confidence: float = 0.95,
) -> float:
    """
    Historical Conditional VaR (Expected Shortfall).

    CVaR = E[Loss | Loss > VaR]

    Args:
        returns: List of portfolio returns
        confidence: Confidence level (0.95 = 95%)

    Returns:
        CVaR as a positive number
    """
    if not returns:
        return 0.0

    arr = np.array(returns)
    percentile = (1 - confidence) * 100
    var_threshold = float(np.percentile(arr, percentile))

    # Average of returns worse than VaR
    tail_returns = arr[arr <= var_threshold]
    if len(tail_returns) == 0:
        return abs(var_threshold) if var_threshold < 0 else 0.0

    cvar = float(np.mean(tail_returns))
    return abs(cvar) if cvar < 0 else 0.0


def parametric_cvar(
    returns: list[float],
    confidence: float = 0.95,
) -> float:
    """
    Parametric CVaR assuming normal distribution.

    CVaR = μ - σ * φ(z) / (1 - α)

    where φ is the standard normal PDF and α is the confidence level.

    Args:
        returns: List of portfolio returns
        confidence: Confidence level

    Returns:
        CVaR as a positive number
    """
    if not returns:
        return 0.0

    arr = np.array(returns)
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1))

    from scipy.stats import norm

    z = norm.ppf(1 - confidence)
    cvar = mean - std * norm.pdf(z) / (1 - confidence)

    return abs(cvar) if cvar < 0 else 0.0
