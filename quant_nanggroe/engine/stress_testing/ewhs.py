"""
Exponentially Weighted Historical Simulation (EWHS)
Computes VaR and CVaR using exponentially weighted historical returns.
Gives more weight to recent observations for faster adaptation to market changes.
"""
import logging
from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

@dataclass
class EWHSResult:
    var_95: float
    var_99: float
    cvar_95: float
    cvar_99: float
    half_life_days: int
    effective_sample_size: float
    expected_shortfall: float
    max_loss: float

class EWHSVARCalculator:
    """
    Exponentially Weighted Historical Simulation for VaR and CVaR.

    Features:
    - Configurable half-life for decay factor
    - Rolling window computation
    - Portfolio-level VaR
    - Marginal VaR contribution per asset
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.half_life = self.config.get("half_life_days", 60)
        self.lambda_decay = 2.0 ** (-1.0 / self.half_life)
        self.min_window = self.config.get("min_window", 252)

    def compute(self, returns: pd.Series) -> EWHSResult:
        """Compute EWHS VaR/CVaR for a return series"""
        returns_array = returns.dropna().values

        if len(returns_array) < self.min_window:
            logger.warning(f"Only {len(returns_array)} returns, minimum is {self.min_window}")

        n = len(returns_array)
        weights = np.array([self.lambda_decay ** (n - 1 - i) for i in range(n)])
        weights = weights / weights.sum()

        sorted_indices = np.argsort(returns_array)
        sorted_returns = returns_array[sorted_indices]
        sorted_weights = weights[sorted_indices]
        cumulative_weights = np.cumsum(sorted_weights)

        idx_95 = np.searchsorted(cumulative_weights, 0.05)
        idx_99 = np.searchsorted(cumulative_weights, 0.01)

        var_95 = sorted_returns[max(0, idx_95 - 1)]
        var_99 = sorted_returns[max(0, idx_99 - 1)]

        cvar_95 = np.mean(sorted_returns[:max(1, idx_95)])
        cvar_99 = np.mean(sorted_returns[:max(1, idx_99)])

        effective_n = 1.0 / np.sum(weights ** 2)

        return EWHSResult(
            var_95=float(var_95),
            var_99=float(var_99),
            cvar_95=float(cvar_95),
            cvar_99=float(cvar_99),
            half_life_days=self.half_life,
            effective_sample_size=float(effective_n),
            expected_shortfall=float(np.mean(returns_array[returns_array < np.percentile(returns_array, 5)])),
            max_loss=float(np.min(returns_array)),
        )
