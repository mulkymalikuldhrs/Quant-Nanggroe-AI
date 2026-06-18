"""Risk Parity Optimization.

Implements risk parity portfolio allocation where each asset contributes
equally to portfolio risk, rather than allocating equal capital.

Methods:
1. Inverse Volatility: Simplest form, weights inversely proportional to volatility
2. Covariance-Based: Iterative solution equalizing risk contributions
3. Equal Risk Contribution: Gradient descent optimization
4. Hierarchical Risk Parity: Clustering-based approach

Enhanced with ai-hedge-fund's risk parity module additions:
- Risk contribution analysis with deviation from target
- Portfolio summary with concentration metrics
- Risk budgeting analysis

Extracted from ai-hedge-fund's risk parity module.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class RiskParityMethod(Enum):
    """Risk parity calculation methods."""

    INVERSE_VOLATILITY = "INVERSE_VOLATILITY"
    COVARIANCE_BASED = "COVARIANCE_BASED"
    EQUAL_RISK_CONTRIBUTION = "EQUAL_RISK_CONTRIBUTION"
    HIERARCHICAL = "HIERARCHICAL"


@dataclass
class RiskContribution:
    """Risk contribution of an asset.

    Attributes:
        asset: Asset name.
        weight: Portfolio weight.
        marginal_risk: Marginal risk contribution.
        risk_contribution: Proportional risk contribution.
        risk_budget: Target risk budget.
        deviation: Deviation from target risk budget.
    """

    asset: str
    weight: float
    marginal_risk: float
    risk_contribution: float
    risk_budget: float
    deviation: float


@dataclass
class RiskParityResult:
    """Result from risk parity optimization."""

    weights: Dict[str, float]
    risk_contributions: Dict[str, float]
    portfolio_volatility: float
    expected_return: float
    sharpe_ratio: float
    risk_parity_error: float
    method: RiskParityMethod
    convergence: bool


class RiskParityOptimizer:
    """Risk Parity Portfolio Optimizer.

    Allocates capital such that each asset contributes equally to
    portfolio risk, rather than allocating equal capital.

    Formula: RC_i = w_i * (Σw)_i / (w'Σw) = 1/N for all i

    Enhanced with risk budget analysis and portfolio summary from ai-hedge-fund.
    """

    def __init__(
        self,
        max_iterations: int = 1000,
        tolerance: float = 1e-6,
        min_weight: float = 0.01,
        max_weight: float = 0.50,
        risk_free_rate: float = 0.02,
    ) -> None:
        self.max_iterations = max_iterations
        self.tolerance = tolerance
        self.min_weight = min_weight
        self.max_weight = max_weight
        self.risk_free_rate = risk_free_rate
        self._history: List[Dict] = []

    def optimize(
        self,
        returns: np.ndarray,
        asset_names: List[str],
        method: Optional[RiskParityMethod] = None,
    ) -> RiskParityResult:
        """Optimize portfolio using risk parity.

        Args:
            returns: Returns matrix (n_assets x n_periods).
            asset_names: List of asset names.
            method: Risk parity method.

        Returns:
            RiskParityResult with optimized weights and metrics.
        """
        if method is None:
            method = RiskParityMethod.COVARIANCE_BASED

        if returns.ndim == 1:
            returns = returns.reshape(1, -1)

        n_assets = returns.shape[0]

        if method == RiskParityMethod.INVERSE_VOLATILITY:
            weights = self._inverse_volatility(returns)
        elif method == RiskParityMethod.COVARIANCE_BASED:
            weights = self._covariance_based(returns)
        elif method == RiskParityMethod.EQUAL_RISK_CONTRIBUTION:
            weights = self._equal_risk_contribution(returns)
        elif method == RiskParityMethod.HIERARCHICAL:
            weights = self._hierarchical_risk_parity(returns)
        else:
            weights = self._covariance_based(returns)

        # Apply constraints
        weights = np.clip(weights, self.min_weight, self.max_weight)
        weights /= weights.sum()

        # Calculate metrics
        cov = np.cov(returns)
        port_vol = np.sqrt(weights.T @ cov @ weights)
        exp_ret = np.mean(returns, axis=1) @ weights
        sharpe = (exp_ret - self.risk_free_rate) / port_vol if port_vol > 0 else 0.0

        # Risk contributions
        rc = self._risk_contributions(weights, cov)
        target = 1.0 / n_assets
        error = float(np.mean(np.abs(rc - target)))
        converged = error < self.tolerance

        result = RiskParityResult(
            weights={name: float(w) for name, w in zip(asset_names, weights)},
            risk_contributions={name: float(r) for name, r in zip(asset_names, rc)},
            portfolio_volatility=float(port_vol),
            expected_return=float(exp_ret),
            sharpe_ratio=float(sharpe),
            risk_parity_error=error,
            method=method,
            convergence=converged,
        )

        # Store in history
        self._history.append({
            "timestamp": datetime.now(),
            "method": method,
            "result": result,
        })

        return result

    def get_risk_budget_analysis(
        self,
        weights: np.ndarray,
        cov_matrix: np.ndarray,
        asset_names: List[str],
    ) -> List[RiskContribution]:
        """Analyze risk budget for each asset.

        Provides a detailed breakdown of each asset's risk contribution
        and its deviation from the equal-risk target.

        Args:
            weights: Portfolio weights.
            cov_matrix: Covariance matrix.
            asset_names: Asset names.

        Returns:
            List of RiskContribution objects with detailed analysis.
        """
        n_assets = len(weights)
        risk_contributions = self._risk_contributions(weights, cov_matrix)
        target_risk = 1.0 / n_assets

        analysis = []
        for i, name in enumerate(asset_names):
            port_vol = np.sqrt(weights.T @ cov_matrix @ weights)
            marginal_risk = (cov_matrix[i, :] @ weights) / port_vol if port_vol > 0 else 0.0
            risk_contrib = risk_contributions[i]

            rc = RiskContribution(
                asset=name,
                weight=float(weights[i]),
                marginal_risk=float(marginal_risk),
                risk_contribution=float(risk_contrib),
                risk_budget=float(target_risk),
                deviation=float(risk_contrib - target_risk),
            )
            analysis.append(rc)

        return analysis

    def get_portfolio_summary(self, result: RiskParityResult) -> Dict:
        """Get summary of risk parity portfolio.

        Includes concentration metrics (HHI), weight distribution,
        and convergence status.

        Args:
            result: RiskParityResult from optimization.

        Returns:
            Dict with portfolio summary metrics.
        """
        n_assets = len(result.weights)
        weights_array = np.array(list(result.weights.values()))
        herfindahl = np.sum(weights_array ** 2)
        max_weight = np.max(weights_array)
        min_weight = np.min(weights_array)

        return {
            "method": result.method.value,
            "num_assets": n_assets,
            "portfolio_volatility": round(result.portfolio_volatility, 4),
            "expected_return": round(result.expected_return, 4),
            "sharpe_ratio": round(result.sharpe_ratio, 4),
            "risk_parity_error": round(result.risk_parity_error, 4),
            "concentration_hhi": round(herfindahl, 4),
            "max_weight": round(max_weight, 4),
            "min_weight": round(min_weight, 4),
            "converged": result.convergence,
        }

    @staticmethod
    def _inverse_volatility(returns: np.ndarray) -> np.ndarray:
        """Inverse volatility weighting: w_i = σ_i^(-1) / Σ(σ_j^(-1))."""
        vols = np.std(returns, axis=1)
        # Guard against zero volatility
        vols = np.maximum(vols, 1e-10)
        inv_vol = 1.0 / vols
        return inv_vol / inv_vol.sum()

    def _covariance_based(self, returns: np.ndarray) -> np.ndarray:
        """Iterative covariance-based risk parity."""
        cov = np.cov(returns)
        n = cov.shape[0]
        weights = np.ones(n) / n

        for _ in range(self.max_iterations):
            rc = self._risk_contributions(weights, cov)
            target = 1.0 / n
            # Avoid division by zero in scaling
            scaling = np.where(rc > 0, target / rc, 1.0)
            new_weights = weights * scaling
            new_weights /= new_weights.sum()

            if np.max(np.abs(new_weights - weights)) < self.tolerance:
                break
            weights = new_weights

        return weights

    def _equal_risk_contribution(self, returns: np.ndarray) -> np.ndarray:
        """Equal risk contribution via gradient descent."""
        cov = np.cov(returns)
        n = cov.shape[0]
        weights = np.ones(n) / n

        for _ in range(self.max_iterations):
            rc = self._risk_contributions(weights, cov)
            target = 1.0 / n

            port_var = weights.T @ cov @ weights
            if port_var <= 0:
                break
            marginal = (cov @ weights) / np.sqrt(port_var)
            gradient = marginal * (rc - target)

            new_weights = weights - 0.01 * gradient
            new_weights = np.maximum(new_weights, 0.0)
            new_weights /= new_weights.sum()

            if np.max(np.abs(new_weights - weights)) < self.tolerance:
                break
            weights = new_weights

        return weights

    def _hierarchical_risk_parity(self, returns: np.ndarray) -> np.ndarray:
        """Hierarchical risk parity using clustering."""
        cov = np.cov(returns)
        vols = np.sqrt(np.diag(cov))
        # Guard against zero volatility
        vols = np.maximum(vols, 1e-10)
        corr = cov / np.outer(vols, vols)
        dist = 1 - np.abs(corr)

        n = cov.shape[0]
        clusters = [[i] for i in range(n)]
        target_clusters = max(1, int(np.sqrt(n)))

        while len(clusters) > target_clusters:
            min_dist = np.inf
            mi, mj = 0, 0
            for i in range(len(clusters)):
                for j in range(i + 1, len(clusters)):
                    d = np.mean([dist[a, b] for a in clusters[i] for b in clusters[j]])
                    if d < min_dist:
                        min_dist, mi, mj = d, i, j

            clusters[mi].extend(clusters[mj])
            clusters.pop(mj)

        weights = np.zeros(n)
        budget = 1.0 / len(clusters)
        for cluster in clusters:
            cv = vols[cluster]
            cw = (1.0 / cv) / (1.0 / cv).sum()
            for i, idx in enumerate(cluster):
                weights[idx] = cw[i] * budget

        return weights

    @staticmethod
    def _risk_contributions(weights: np.ndarray, cov: np.ndarray) -> np.ndarray:
        """Calculate risk contribution of each asset: RC_i = w_i * (Σw)_i / (w'Σw)."""
        port_var = weights.T @ cov @ weights
        if port_var <= 0:
            return np.zeros(len(weights))
        return weights * (cov @ weights) / port_var
