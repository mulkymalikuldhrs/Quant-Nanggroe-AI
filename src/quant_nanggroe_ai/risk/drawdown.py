"""
Maximum Drawdown Tracking
==========================
"""

from __future__ import annotations

import numpy as np


def max_drawdown(equity_curve: list[float]) -> float:
    """
    Calculate maximum drawdown from an equity curve.

    Args:
        equity_curve: List of portfolio equity values

    Returns:
        Maximum drawdown as a positive percentage (e.g., 0.15 = 15%)
    """
    if not equity_curve or len(equity_curve) < 2:
        return 0.0

    arr = np.array(equity_curve)
    peak = np.maximum.accumulate(arr)
    drawdown = (peak - arr) / peak
    return float(np.max(drawdown))


def current_drawdown(equity_curve: list[float]) -> float:
    """Calculate current drawdown from peak."""
    if not equity_curve:
        return 0.0

    peak = max(equity_curve)
    current = equity_curve[-1]
    return (peak - current) / peak if peak > 0 else 0.0


def drawdown_duration(equity_curve: list[float]) -> int:
    """Calculate the number of periods since last peak."""
    if not equity_curve:
        return 0

    peak = equity_curve[0]
    duration = 0
    for i, val in enumerate(equity_curve):
        if val >= peak:
            peak = val
            duration = 0
        else:
            duration += 1
    return duration
