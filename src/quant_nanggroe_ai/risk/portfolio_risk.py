"""
Portfolio-level Risk Management
================================
"""

from __future__ import annotations

from typing import Any

import numpy as np


def portfolio_var(
    weights: list[float],
    returns_matrix: list[list[float]],
    confidence: float = 0.95,
) -> float:
    """
    Calculate portfolio VaR using parametric method.

    Args:
        weights: Portfolio weights
        returns_matrix: List of return series for each asset
        confidence: Confidence level

    Returns:
        Portfolio VaR as a positive number
    """
    if not weights or not returns_matrix:
        return 0.0

    arr = np.array(returns_matrix).T  # Shape: (n_periods, n_assets)
    if arr.ndim != 2 or arr.shape[1] != len(weights):
        return 0.0

    # Portfolio returns
    w = np.array(weights)
    port_returns = arr @ w

    mean = float(np.mean(port_returns))
    std = float(np.std(port_returns, ddof=1))

    z_scores = {0.90: 1.282, 0.95: 1.645, 0.99: 2.326}
    z = z_scores.get(confidence, 1.645)

    var = mean - z * std
    return abs(var) if var < 0 else 0.0


def portfolio_correlation_risk(
    returns_matrix: list[list[float]],
    threshold: float = 0.7,
) -> dict[str, Any]:
    """
    Check portfolio for excessive correlation between assets.

    Args:
        returns_matrix: List of return series for each asset
        threshold: Correlation threshold for warning

    Returns:
        Dict with correlation analysis
    """
    if len(returns_matrix) < 2:
        return {"max_correlation": 0.0, "high_correlation_pairs": [], "risk_level": "LOW"}

    arr = np.array(returns_matrix)
    corr_matrix = np.corrcoef(arr)

    # Find high correlation pairs
    high_corr_pairs: list[dict[str, Any]] = []
    max_corr = 0.0
    n_assets = len(returns_matrix)

    for i in range(n_assets):
        for j in range(i + 1, n_assets):
            corr = abs(float(corr_matrix[i, j]))
            max_corr = max(max_corr, corr)
            if corr > threshold:
                high_corr_pairs.append({"asset_i": i, "asset_j": j, "correlation": round(corr, 4)})

    risk_level = "HIGH" if max_corr > 0.8 else "MEDIUM" if max_corr > threshold else "LOW"

    return {
        "max_correlation": round(max_corr, 4),
        "high_correlation_pairs": high_corr_pairs,
        "risk_level": risk_level,
        "threshold": threshold,
    }
