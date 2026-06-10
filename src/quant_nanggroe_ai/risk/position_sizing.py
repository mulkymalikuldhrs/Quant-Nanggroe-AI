"""
Position Sizing — Kelly Criterion, Risk Parity
================================================
"""

from __future__ import annotations

from typing import Any

import numpy as np


def kelly_criterion_size(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    fraction: float = 0.25,
    account_balance: float = 10000.0,
) -> dict[str, Any]:
    """
    Kelly Criterion position sizing with fractional Kelly.

    Args:
        win_rate: Win rate (0-1)
        avg_win: Average winning trade amount
        avg_loss: Average losing trade amount
        fraction: Fractional Kelly (0.25 = quarter Kelly for safety)
        account_balance: Current account balance

    Returns:
        Dict with position size and details
    """
    if avg_loss == 0 or win_rate <= 0 or win_rate >= 1:
        return {
            "position_size": 0.0,
            "kelly_pct": 0.0,
            "recommendation": "NO_TRADE",
        }

    r = avg_win / avg_loss
    full_kelly = win_rate - ((1 - win_rate) / r)
    fractional_kelly = full_kelly * fraction

    # Ensure non-negative
    fractional_kelly = max(0.0, fractional_kelly)

    position_size = account_balance * fractional_kelly

    return {
        "position_size": round(position_size, 2),
        "kelly_pct": round(full_kelly, 4),
        "fractional_kelly_pct": round(fractional_kelly, 4),
        "fraction": fraction,
        "recommendation": f"Risk {fractional_kelly:.2%} of capital",
    }


def risk_parity_weights(
    returns_matrix: list[list[float]],
    target_risk: float = 0.01,
) -> list[float]:
    """
    Risk Parity position sizing.

    Allocates capital such that each position contributes
    equally to overall portfolio risk.

    Args:
        returns_matrix: List of return series for each asset
        target_risk: Target portfolio risk (annualized)

    Returns:
        List of weight allocations (sums to 1.0)
    """
    n_assets = len(returns_matrix)
    if n_assets == 0:
        return []

    # Calculate volatility for each asset
    vols = []
    for returns in returns_matrix:
        if returns:
            vols.append(float(np.std(returns, ddof=1)))
        else:
            vols.append(1.0)

    # Inverse volatility weighting
    inv_vols = [1.0 / v if v > 0 else 0.0 for v in vols]
    total_inv_vol = sum(inv_vols)

    if total_inv_vol == 0:
        return [1.0 / n_assets] * n_assets

    weights = [iv / total_inv_vol for iv in inv_vols]
    return weights
