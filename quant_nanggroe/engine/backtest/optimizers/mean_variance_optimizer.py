"""Mean-variance (max Sharpe) optimizer.

Maximises ``(w'mu - r_f) / sqrt(w'Sigma w)`` subject to
``w >= 0``, ``sum(w) = 1`` (long-only simplex).

Uses scipy SLSQP optimisation. Falls back to equal weight if
optimisation fails or scipy is not available.

Ported from Vibe-Trading's ``backtest.optimizers.mean_variance``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.backtest.optimizers.base_optimizer import BaseOptimizer


class MeanVarianceOptimizer(BaseOptimizer):
    """Maximize Sharpe ratio subject to long-only simplex.

    Uses SLSQP optimisation via scipy. Falls back to equal weight
    if optimisation fails or scipy is unavailable.

    Args:
        lookback: Lookback days for covariance estimation.
        risk_free: Risk-free rate for Sharpe calculation.
        **kwargs: Additional parameters.
    """

    def __init__(
        self, lookback: int = 60, risk_free: float = 0.0, **kwargs: Any
    ) -> None:
        super().__init__(lookback=lookback, **kwargs)
        self.risk_free = risk_free

    def _build_context(
        self, window: pd.DataFrame, active: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Build context with mean vector and covariance.

        Args:
            window: Return window.
            active: Active codes.

        Returns:
            Context with ``cov`` and ``mu``, or None if NaN detected.
        """
        mu = window.mean().values
        cov = window.cov().values
        if np.isnan(cov).any() or np.isnan(mu).any():
            return None
        return {"cov": cov, "mu": mu}

    def _calc_weights(self, ctx: Dict[str, Any]) -> np.ndarray:
        """SLSQP max-Sharpe weights.

        Falls back to equal weight if:
          - scipy is not installed
          - optimisation fails
          - any weight is negative after normalisation

        Args:
            ctx: Context dict with ``cov`` and ``mu``.

        Returns:
            Weight vector summing to 1.
        """
        mu, cov = ctx["mu"], ctx["cov"]
        n = len(mu)
        if n == 0:
            return self._equal_weight(0)

        rf = self.risk_free

        try:
            from scipy.optimize import minimize

            def neg_sharpe(w: np.ndarray) -> float:
                port_vol = np.sqrt(w @ cov @ w)
                if port_vol < 1e-12:
                    return 0.0
                return -(w @ mu - rf) / port_vol

            result = minimize(
                neg_sharpe,
                self._equal_weight(n),
                method="SLSQP",
                bounds=[(0.0, 1.0)] * n,
                constraints={"type": "eq", "fun": lambda w: w.sum() - 1.0},
                options={"maxiter": 200, "ftol": 1e-10},
            )

            if result.success:
                return self._normalize(result.x)
        except ImportError:
            pass  # scipy not available
        except Exception:
            pass  # optimisation failed

        return self._equal_weight(n)


def optimize(
    ret: pd.DataFrame,
    pos: pd.DataFrame,
    dates: pd.DatetimeIndex,
    lookback: int = 60,
    risk_free: float = 0.0,
) -> pd.DataFrame:
    """Module-level entry: max-Sharpe-adjusted positions.

    Args:
        ret: Return matrix (dates x codes).
        pos: Raw signal positions.
        dates: Date index aligned with ``pos``.
        lookback: Lookback window for covariance.
        risk_free: Risk-free rate.

    Returns:
        Adjusted position matrix.
    """
    return MeanVarianceOptimizer(
        lookback=lookback, risk_free=risk_free
    ).optimize(ret, pos, dates)
