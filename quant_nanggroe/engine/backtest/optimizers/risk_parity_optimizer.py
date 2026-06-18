"""Risk parity optimizer: equalize marginal risk contributions.

Iterative refinement so ``w_i * MRC_i`` is approximately equal across assets.
Uses Spinu (2013)-style inverse-vol seed + Newton-style refinement.

Ported from Vibe-Trading's ``backtest.optimizers.risk_parity``.
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd

from quant_nanggroe.engine.backtest.optimizers.base_optimizer import BaseOptimizer


class RiskParityOptimizer(BaseOptimizer):
    """Risk parity: equalize risk contributions across assets.

    Uses inverse-volatility seeding with Newton-style refinement
    to ensure each asset contributes equally to portfolio risk.

    Args:
        lookback: Lookback days for covariance estimation.
        **kwargs: Additional parameters (ignored).
    """

    def _calc_weights(self, ctx: Dict[str, Any]) -> np.ndarray:
        """Equal risk contribution weights.

        Args:
            ctx: Context dict with ``cov`` key.

        Returns:
            Weight vector summing to 1.
        """
        cov = ctx["cov"]
        n = cov.shape[0]
        if n == 0:
            return self._equal_weight(0)

        vols = np.sqrt(np.diag(cov))
        if np.any(vols < 1e-12):
            return self._equal_weight(n)

        # Seed: inverse-volatility
        inv_vol = 1.0 / vols
        w = inv_vol / inv_vol.sum()

        # Newton-style refinement (5 iterations)
        for _ in range(5):
            port_vol = np.sqrt(w @ cov @ w)
            if port_vol < 1e-12:
                break
            mrc = (cov @ w) / port_vol  # Marginal risk contribution
            rc = w * mrc  # Risk contribution
            target = port_vol / n
            w = w * (target / (rc + 1e-12))
            w = w / w.sum()

        return w


def optimize(
    ret: pd.DataFrame,
    pos: pd.DataFrame,
    dates: pd.DatetimeIndex,
    lookback: int = 60,
) -> pd.DataFrame:
    """Module-level entry: risk-parity-adjusted positions.

    Args:
        ret: Return matrix (dates x codes).
        pos: Raw signal positions.
        dates: Date index aligned with ``pos``.
        lookback: Lookback window for covariance.

    Returns:
        Adjusted position matrix.
    """
    return RiskParityOptimizer(lookback=lookback).optimize(ret, pos, dates)
