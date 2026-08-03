"""Downside deviation risk metric (QuantScience research distillation).

Research basis (QuantScience newsletter "Responsible algorithmic trading with
downside deviation"):
- Downside deviation (DD) only penalizes returns below a threshold MAR (minimal
  acceptable return), unlike std-dev which treats upside/downside symmetrically.
- For skewed/fat-tailed returns (typical in trading PnL), DD is a more honest
  risk measure and feeds Sortino ratio: Sortino = (mean - MAR) / DD.

Design (ponytail):
- Pure numpy/pandas, no heavy deps.
- Eager import is safe (numpy/pandas are core QNA deps).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def downside_deviation(
    returns: pd.Series | np.ndarray,
    mar: float = 0.0,
    annualize: bool = True,
    periods_per_year: int = 252,
) -> float:
    """Compute downside deviation of a return series below MAR.

    Args:
        returns: per-period returns (e.g. daily). Accepts Series or ndarray.
        mar: minimal acceptable return per period (default 0.0).
        annualize: if True, scale by sqrt(periods_per_year).
        periods_per_year: annualization factor (252 trading days typical).

    Returns:
        Non-negative float. 0.0 when no observation is below MAR.
    """
    r = np.asarray(pd.Series(returns).dropna().to_numpy(dtype=float))
    if r.size == 0:
        return 0.0
    downside = np.minimum(r - mar, 0.0)
    dd = float(np.sqrt(np.mean(downside * downside)))
    if annualize:
        dd *= np.sqrt(periods_per_year)
    return dd


def sortino_ratio(
    returns: pd.Series | np.ndarray,
    mar: float = 0.0,
    annualize: bool = True,
    periods_per_year: int = 252,
    floor: float = 1e-9,
) -> float:
    """Sortino ratio = (mean excess return) / downside deviation.

    Returns 0.0 when downside deviation is ~0 (no downside risk measured),
    avoiding division-by-zero blowups.
    """
    r = np.asarray(pd.Series(returns).dropna().to_numpy(dtype=float))
    if r.size == 0:
        return 0.0
    mean_excess = float(np.mean(r - mar))
    dd = downside_deviation(r, mar=mar, annualize=annualize, periods_per_year=periods_per_year)
    if dd <= floor:
        return 0.0
    return mean_excess / dd
