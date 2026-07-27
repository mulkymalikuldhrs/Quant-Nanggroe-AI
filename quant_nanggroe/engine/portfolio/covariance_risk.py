"""Portfolio Covariance & Risk Parity Engine.

Computes multi-asset covariance matrices, portfolio volatility, Ledoit-Wolf shrinkage,
and Risk Parity position weights to manage multi-asset portfolio risk.
"""

from __future__ import annotations

import logging
from typing import Tuple

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
        """Calculate Equal Risk Contribution (Risk Parity) weights across assets.

        Uses the full covariance matrix so correlated assets (e.g. BTC/ETH)
        are not overweighted.  Falls back to diagonal-only when the matrix is
        singular or unavailable.
        """
        n_assets = cov_matrix.shape[0]

        if cov_matrix is None or cov_matrix.size == 0:
            logger.warning(
                "cov_matrix is None/empty — falling back to inverse-volatility weighting"
            )
            return self._diagonal_risk_parity_weights(cov_matrix)

        eigenvalues = np.linalg.eigvalsh(cov_matrix)
        if np.any(eigenvalues < 1e-10):
            logger.warning(
                "Covariance matrix near-singular (min eigenvalue=%.2e) — "
                "falling back to diagonal risk parity",
                eigenvalues.min(),
            )
            return self._diagonal_risk_parity_weights(cov_matrix)

        weights = np.ones(n_assets) / n_assets
        for _ in range(200):
            port_vol = np.sqrt(weights @ cov_matrix @ weights)
            if port_vol < 1e-12:
                return np.ones(n_assets) / n_assets
            mrc = cov_matrix @ weights / port_vol
            risk_contrib = weights * mrc
            avg_rc = np.mean(risk_contrib)
            if avg_rc < 1e-12:
                return np.ones(n_assets) / n_assets
            target_rc = np.full(n_assets, avg_rc)
            weights = weights * (target_rc / (risk_contrib + 1e-15))
            weights = weights / np.sum(weights)

        logger.warning("Risk parity did not converge after 200 iterations")
        return weights

    def _diagonal_risk_parity_weights(self, cov_matrix: np.ndarray) -> np.ndarray:
        """Fallback: inverse-volatility weighting using only the diagonal."""
        n_assets = cov_matrix.shape[0]
        variances = np.diag(cov_matrix)
        stdevs = np.sqrt(np.maximum(1e-8, variances))
        inv_stdevs = 1.0 / stdevs
        return inv_stdevs / np.sum(inv_stdevs)

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
