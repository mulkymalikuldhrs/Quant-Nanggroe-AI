"""
Sensitivity Analysis for Portfolio Stress Testing
Analyzes how portfolio value changes under various market condition shifts.
"""
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)

@dataclass
class SensitivityResult:
    parameter: str
    base_value: float
    shocks: List[float]
    impacts: List[float]
    elasticity: float
    linearity: float

class SensitivityAnalyzer:
    """
    Analyzes portfolio sensitivity to market parameter changes.

    Parameters analyzed:
    - Interest rate shifts
    - Volatility changes
    - Correlation changes
    - Sector-specific shocks
    - Factor exposure changes
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

    def interest_rate_sensitivity(self, portfolio_value: float,
                                    duration: float, rate_shocks: List[float]) -> SensitivityResult:
        """Analyze sensitivity to interest rate changes"""
        impacts = [-duration * shock * portfolio_value for shock in rate_shocks]
        elasticity = self._compute_elasticity(rate_shocks, impacts, portfolio_value)
        linearity = self._compute_linearity(np.array(rate_shocks), np.array(impacts))

        return SensitivityResult(
            parameter="interest_rate",
            base_value=0.0,
            shocks=rate_shocks,
            impacts=impacts,
            elasticity=elasticity,
            linearity=linearity,
        )

    def volatility_sensitivity(self, returns: pd.Series,
                                 vol_shocks: List[float]) -> SensitivityResult:
        """Analyze sensitivity to volatility changes"""
        base_vol = returns.std()
        impacts = []

        for shock in vol_shocks:
            impact = -shock * 0.5
            impacts.append(impact)

        elasticity = self._compute_elasticity(vol_shocks, impacts, 1.0)
        linearity = self._compute_linearity(np.array(vol_shocks), np.array(impacts))

        return SensitivityResult(
            parameter="volatility",
            base_value=float(base_vol),
            shocks=vol_shocks,
            impacts=impacts,
            elasticity=elasticity,
            linearity=linearity,
        )

    def correlation_sensitivity(self, portfolio_value: float,
                                  weights: Dict[str, float],
                                  asset_returns: Dict[str, pd.Series],
                                  corr_shocks: List[float]) -> Dict[str, Any]:
        """Analyze sensitivity to correlation changes"""
        assets = list(weights.keys())
        n = len(assets)

        returns_matrix = np.array([asset_returns[a].values for a in assets])
        base_corr = np.corrcoef(returns_matrix)

        results = {}
        for shock in corr_shocks:
            shocked_corr = base_corr + shock * (1 - base_corr)
            np.fill_diagonal(shocked_corr, 1.0)

            weight_vec = np.array([weights[a] for a in assets])
            base_var = weight_vec @ base_corr @ weight_vec
            shocked_var = weight_vec @ shocked_corr @ weight_vec

            impact = (shocked_var / base_var - 1) if base_var > 0 else 0
            results[f"corr_{shock:+.1f}"] = {
                "shock": shock,
                "portfolio_variance_impact": float(impact),
                "diversification_ratio": float(base_var / max(shocked_var, 1e-10)),
            }

        return results

    def what_if_scenario(self, portfolio_value: float,
                          asset_weights: Dict[str, float],
                          asset_shocks: Dict[str, float]) -> Dict[str, Any]:
        """What-if analysis for custom scenario"""
        total_impact = 0.0
        asset_impacts = {}

        for asset, weight in asset_weights.items():
            shock = asset_shocks.get(asset, 0.0)
            impact = weight * shock * portfolio_value
            asset_impacts[asset] = impact
            total_impact += impact

        return {
            "scenario": "custom_what_if",
            "portfolio_value_before": portfolio_value,
            "portfolio_value_after": portfolio_value + total_impact,
            "total_impact": total_impact,
            "total_return_pct": total_impact / portfolio_value if portfolio_value else 0,
            "asset_impacts": asset_impacts,
        }

    def _compute_elasticity(self, shocks: List[float], impacts: List[float],
                              base_value: float) -> float:
        """Compute elasticity (responsiveness measure)"""
        if not shocks or abs(shocks[0]) < 1e-10:
            return 0.0
        pct_change_param = (shocks[-1] - shocks[0]) / abs(shocks[0])
        pct_change_portfolio = (impacts[-1] - impacts[0]) / max(abs(base_value), 1e-10)
        return pct_change_portfolio / max(abs(pct_change_param), 1e-10)

    def _compute_linearity(self, x: np.ndarray, y: np.ndarray) -> float:
        """Compute R-squared of linear fit"""
        if len(x) < 3:
            return 1.0
        A = np.vstack([x, np.ones_like(x)]).T
        if np.linalg.matrix_rank(A) < 2:
            return 0.0
        coeffs, residuals, _, _ = np.linalg.lstsq(A, y, rcond=None)
        y_pred = A @ coeffs
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        return 1.0 - ss_res / max(ss_tot, 1e-10)
