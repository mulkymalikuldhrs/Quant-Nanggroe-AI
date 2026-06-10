"""Equal-volatility (inverse-volatility) weighting.

Higher weight on lower-volatility names so each asset contributes
similar volatility to the portfolio. Simpler than full risk parity
as it does not require covariance modelling.

Ported from Vibe-Trading's ``backtest.optimizers.equal_volatility``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.backtest.optimizers.base_optimizer import BaseOptimizer


class EqualVolatilityOptimizer(BaseOptimizer):
    """Inverse-volatility weights without a full covariance model.

    Each asset receives weight proportional to the inverse of its
    rolling volatility, so lower-volatility assets get higher weights
    and each asset contributes similar volatility to the portfolio.

    Args:
        lookback: Lookback days for volatility estimation.
        **kwargs: Additional parameters (ignored).
    """

    def _build_context(
        self, window: pd.DataFrame, active: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Build context with rolling per-asset volatilities.

        Args:
            window: Return window.
            active: Active codes.

        Returns:
            Context with ``vols`` or None if any vol is NaN or near-zero.
        """
        vols = window.std()
        if vols.isna().any() or (vols < 1e-12).any():
            return None
        return {"vols": vols}

    def _calc_weights(self, ctx: Dict[str, Any]) -> np.ndarray:
        """Inverse-volatility weights.

        Args:
            ctx: Context dict with ``vols`` key.

        Returns:
            Weight vector summing to 1.
        """
        inv_vol = 1.0 / ctx["vols"]
        return (inv_vol / inv_vol.sum()).values


def optimize(
    ret: pd.DataFrame,
    pos: pd.DataFrame,
    dates: pd.DatetimeIndex,
    lookback: int = 60,
) -> pd.DataFrame:
    """Module-level entry: inverse-volatility-adjusted positions.

    Args:
        ret: Return matrix (dates x codes).
        pos: Raw signal positions.
        dates: Date index aligned with ``pos``.
        lookback: Lookback window for volatility.

    Returns:
        Adjusted position matrix.
    """
    return EqualVolatilityOptimizer(lookback=lookback).optimize(ret, pos, dates)
