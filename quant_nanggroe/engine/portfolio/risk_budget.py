"""Risk Budgeting Engine with Near-Singular Covariance Guard.

Allocates capital proportional to user-defined risk budgets while guarding
against ill-conditioned covariance matrices.
"""

from __future__ import annotations

import logging
from typing import Dict

import numpy as np

logger = logging.getLogger(__name__)

EIGENVALUE_THRESHOLD = 1e-10


def _validate_covariance(cov_matrix: np.ndarray) -> np.ndarray:
    """Check for near-singular covariance matrix.

    Returns the (possibly pseudoinverse) covariance to use for allocation.
    """
    eigenvalues = np.linalg.eigvalsh(cov_matrix)
    min_eig = float(eigenvalues.min())

    if min_eig < EIGENVALUE_THRESHOLD:
        logger.warning(
            "Covariance matrix is near-singular (min eigenvalue=%.2e < %.0e). "
            "Using pseudoinverse for risk budget allocation.",
            min_eig,
            EIGENVALUE_THRESHOLD,
        )
        return np.linalg.pinv(cov_matrix)

    return cov_matrix


def risk_budget_weights(
    cov_matrix: np.ndarray,
    risk_budgets: Dict[int, float],
) -> np.ndarray:
    """Compute weights that match user-defined risk budgets.

    Parameters
    ----------
    cov_matrix : np.ndarray
        Covariance matrix of asset returns.
    risk_budgets : dict[int, float]
        Mapping of asset index → target risk fraction (must sum to 1.0).

    Returns
    -------
    np.ndarray
        Asset weights achieving the target risk budget allocation.
    """
    cov = _validate_covariance(cov_matrix)
    n = cov.shape[0]

    budget_vec = np.zeros(n)
    for idx, frac in risk_budgets.items():
        budget_vec[idx] = frac
    budget_sum = budget_vec.sum()
    if budget_sum > 0:
        budget_vec = budget_vec / budget_sum
    else:
        budget_vec = np.ones(n) / n

    weights = np.ones(n) / n
    for _ in range(300):
        port_var = weights @ cov @ weights
        if port_var < 1e-24:
            return np.ones(n) / n
        port_vol = np.sqrt(port_var)
        mrc = cov @ weights / port_vol
        rc = weights * mrc
        total_rc = rc.sum()
        if total_rc < 1e-24:
            return np.ones(n) / n
        rc_frac = rc / total_rc
        diff = budget_vec - rc_frac
        weights = weights * (1.0 + diff)
        weights = np.maximum(weights, 0.0)
        w_sum = weights.sum()
        if w_sum > 0:
            weights = weights / w_sum

    logger.warning("Risk budget allocation did not converge after 300 iterations")
    return weights
