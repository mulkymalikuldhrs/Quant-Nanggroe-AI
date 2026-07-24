"""Portfolio Covariance & Risk Parity Engine.

Computes multi-asset covariance matrices, portfolio volatility, Ledoit-Wolf shrinkage,
and Risk Parity position weights to manage multi-asset portfolio risk.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class CovarianceRiskOptimizer:
    """Multi-asset covariance calculator and Risk Parity weight optimizer."""

    def __init__(self, target_volatility: float = 0.15):
        self.target_volatility = target_volatility

    def calculate_covariance(self, returns_matrix: np.ndarray, shrink: bool = True) -> np.ndarray:
        """Calculate covariance matrix with Ledoit-Wolf shrinkage fallback."""
        if returns_matrix.ndim != 2 or returns_matrix.shape[0] < 2:
            raise ValueError("Returns matrix must be 2D with at least 2 observations.")

        sample_cov = np.cov(returns_matrix, rowvar=False)

        if not shrink or sample_cov.ndim < 2:
            return sample_cov

        # Simple shrinkage toward diagonal variance matrix for numerical stability
        n_assets = sample_cov.shape[0]
        mu = np.trace(sample_cov) / n_assets
        target = mu * np.eye(n_assets)
        delta = 0.2  # Shrinkage intensity
        shrunk_cov = (1 - delta) * sample_cov + delta * target
        return shrunk_cov

    def portfolio_volatility(self, weights: np.ndarray, cov_matrix: np.ndarray) -> float:
        """Calculate annualized portfolio volatility given asset weights and covariance matrix."""
        var = np.dot(weights.T, np.dot(cov_matrix, weights))
        return float(np.sqrt(max(0.0, var)))

    def risk_parity_weights(self, cov_matrix: np.ndarray) -> np.ndarray:
        """Calculate Equal Risk Contribution (Risk Parity) weights across assets."""
        n_assets = cov_matrix.shape[0]
        # Inverse volatility weighting approximation
        variances = np.diag(cov_matrix)
        stdevs = np.sqrt(np.maximum(1e-8, variances))
        inv_stdevs = 1.0 / stdevs
        weights = inv_stdevs / np.sum(inv_stdevs)
        return weights

    def scale_weights_for_target_vol(self, weights: np.ndarray, cov_matrix: np.ndarray) -> Tuple[np.ndarray, float]:
        """Scale position weights to match target portfolio volatility."""
        current_vol = self.portfolio_volatility(weights, cov_matrix)
        if current_vol <= 1e-8:
            return weights, 1.0

        scale_factor = self.target_volatility / current_vol
        # Cap leverage multiplier at 2.0x
        scale_factor = min(scale_factor, 2.0)
        scaled_weights = weights * scale_factor
        return scaled_weights, scale_factor
