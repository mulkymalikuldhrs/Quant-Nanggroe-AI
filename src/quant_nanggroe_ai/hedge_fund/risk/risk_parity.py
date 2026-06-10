"""
Risk Parity Portfolio Optimization v2.3.0
Implements risk parity allocation strategy
Agent Constitution v2.3.0 Compliant

Key Components:
- Risk Parity Allocation: Equalize risk contributions
- Covariance Matrix: Asset correlation structure
- Risk Contribution Analysis: Individual asset risk
- Inverse Volatility: Simplified risk parity
- Hierarchical Risk Parity: HRP clustering approach

Principle:
Allocate capital such that each asset contributes equally to
portfolio risk, rather than allocating equal capital.

Risk Budgeting:
w_i = λ * Σ^(-1) * σ / (σ' * Σ^(-1) * σ)

Where:
- w = weight vector
- Σ = covariance matrix
- σ = asset volatilities
- λ = normalization constant
"""

from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple
from enum import Enum
import numpy as np
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RiskParityMethod(Enum):
    """Risk parity calculation methods"""

    INVERSE_VOLATILITY = "INVERSE_VOLATILITY"
    COVARIANCE_BASED = "COVARIANCE_BASED"
    HIERARCHICAL = "HIERARCHICAL"
    EQUAL_RISK_CONTRIBUTION = "EQUAL_RISK_CONTRIBUTION"


@dataclass
class RiskContribution:
    """Risk contribution of an asset"""

    asset: str
    weight: float
    marginal_risk: float
    risk_contribution: float
    risk_budget: float
    deviation: float  # Deviation from target risk budget


@dataclass
class RiskParityResult:
    """Result from risk parity optimization"""

    weights: Dict[str, float]  # Optimized weights
    risk_contributions: Dict[str, float]  # Risk contribution per asset
    portfolio_volatility: float  # Overall portfolio volatility
    expected_return: float  # Expected portfolio return
    sharpe_ratio: float  # Sharpe ratio
    risk_parity_error: float  # Deviation from perfect parity
    method: RiskParityMethod  # Method used
    convergence: bool  # Whether converged to solution


class RiskParityOptimizer:
    """
    Risk Parity Portfolio Optimizer

    Risk parity aims to allocate capital such that each asset
    contributes equally to portfolio risk.

    Key Features:
    - Inverse volatility weighting (simplest)
    - Covariance-based risk parity
    - Hierarchical risk parity (clustering)
    - Equal risk contribution constraints
    - Risk budget analysis
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize Risk Parity Optimizer

        Config parameters:
        - default_method: Default method (default: COVARIANCE_BASED)
        - max_iterations: Maximum iterations for convergence (default: 1000)
        - tolerance: Convergence tolerance (default: 1e-6)
        - min_weight: Minimum weight constraint (default: 0.01)
        - max_weight: Maximum weight constraint (default: 0.50)
        - risk_free_rate: Risk-free rate for Sharpe (default: 0.02)
        """
        self.config = config or {}
        self.default_method = self.config.get(
            "default_method", RiskParityMethod.COVARIANCE_BASED
        )
        self.max_iterations = self.config.get("max_iterations", 1000)
        self.tolerance = self.config.get("tolerance", 1e-6)
        self.min_weight = self.config.get("min_weight", 0.01)
        self.max_weight = self.config.get("max_weight", 0.50)
        self.risk_free_rate = self.config.get("risk_free_rate", 0.02)

        self.history: List[Dict] = []

    def optimize(
        self,
        returns: np.ndarray,
        asset_names: List[str],
        method: Optional[RiskParityMethod] = None,
    ) -> RiskParityResult:
        """
        Optimize portfolio using risk parity

        Args:
            returns: Returns matrix (n_assets x n_periods)
            asset_names: List of asset names
            method: Risk parity method

        Returns:
            RiskParityResult with optimized weights and metrics
        """
        if method is None:
            method = self.default_method

        n_assets = returns.shape[0]

        if method == RiskParityMethod.INVERSE_VOLATILITY:
            weights = self._inverse_volatility(returns)
        elif method == RiskParityMethod.COVARIANCE_BASED:
            weights = self._covariance_based_risk_parity(returns)
        elif method == RiskParityMethod.HIERARCHICAL:
            weights = self._hierarchical_risk_parity(returns, asset_names)
        elif method == RiskParityMethod.EQUAL_RISK_CONTRIBUTION:
            weights = self._equal_risk_contribution(returns)
        else:
            weights = self._covariance_based_risk_parity(returns)

        # Apply constraints
        weights = self._apply_constraints(weights)

        # Normalize weights
        weights = weights / np.sum(weights)

        # Calculate portfolio metrics
        cov_matrix = np.cov(returns)
        portfolio_volatility = np.sqrt(weights.T @ cov_matrix @ weights)
        expected_return = np.mean(returns, axis=1) @ weights
        sharpe_ratio = (expected_return - self.risk_free_rate) / portfolio_volatility

        # Calculate risk contributions
        risk_contributions = self._calculate_risk_contributions(weights, cov_matrix)

        # Calculate risk parity error
        target_risk = 1.0 / n_assets
        risk_parity_error = np.mean(np.abs(risk_contributions - target_risk))

        # Check convergence
        converged = risk_parity_error < self.tolerance

        # Create result
        weights_dict = {name: float(w) for name, w in zip(asset_names, weights)}
        risk_contrib_dict = {
            name: float(rc) for name, rc in zip(asset_names, risk_contributions)
        }

        result = RiskParityResult(
            weights=weights_dict,
            risk_contributions=risk_contrib_dict,
            portfolio_volatility=float(portfolio_volatility),
            expected_return=float(expected_return),
            sharpe_ratio=float(sharpe_ratio),
            risk_parity_error=float(risk_parity_error),
            method=method,
            convergence=converged,
        )

        # Store in history
        self.history.append(
            {"timestamp": datetime.now(), "method": method, "result": result}
        )

        return result

    def _inverse_volatility(self, returns: np.ndarray) -> np.ndarray:
        """
        Calculate inverse volatility weights

        w_i = σ_i^(-1) / Σ(σ_j^(-1))

        Simplest form of risk parity
        """
        volatilities = np.std(returns, axis=1)
        inv_vol = 1.0 / volatilities
        weights = inv_vol / np.sum(inv_vol)
        return weights

    def _covariance_based_risk_parity(self, returns: np.ndarray) -> np.ndarray:
        """
        Calculate risk parity weights using covariance matrix

        Solve for weights that equalize risk contributions
        using iterative approach
        """
        cov_matrix = np.cov(returns)
        n_assets = cov_matrix.shape[0]

        # Initial equal weights
        weights = np.ones(n_assets) / n_assets

        # Iterative optimization
        for iteration in range(self.max_iterations):
            # Calculate risk contributions
            risk_contributions = self._calculate_risk_contributions(weights, cov_matrix)

            # Calculate scaling factors
            target_risk = 1.0 / n_assets
            scaling_factors = target_risk / risk_contributions

            # Update weights
            new_weights = weights * scaling_factors
            new_weights = new_weights / np.sum(new_weights)

            # Check convergence
            if np.max(np.abs(new_weights - weights)) < self.tolerance:
                break

            weights = new_weights

        return weights

    def _equal_risk_contribution(self, returns: np.ndarray) -> np.ndarray:
        """
        Calculate weights using equal risk contribution constraint

        Solve: minimize ||RC(w) - b||²
        Subject to: sum(w) = 1, w >= 0

        Where:
        - RC = risk contributions
        - b = risk budget vector (equal for all assets)
        """
        cov_matrix = np.cov(returns)
        n_assets = cov_matrix.shape[0]

        # Initial guess: equal weights
        weights = np.ones(n_assets) / n_assets

        # Gradient descent to minimize risk parity error
        for iteration in range(self.max_iterations):
            # Calculate risk contributions
            risk_contributions = self._calculate_risk_contributions(weights, cov_matrix)

            # Target: equal risk contribution
            target = 1.0 / n_assets

            # Gradient of risk parity error
            portfolio_variance = weights.T @ cov_matrix @ weights
            marginal_risk = (cov_matrix @ weights) / np.sqrt(portfolio_variance)

            # Risk contribution gradient
            rc_error = risk_contributions - target

            # Update weights using gradient descent
            gradient = marginal_risk * rc_error
            learning_rate = 0.01

            new_weights = weights - learning_rate * gradient
            new_weights = np.maximum(new_weights, 0)  # Non-negativity
            new_weights = new_weights / np.sum(new_weights)  # Sum to 1

            # Check convergence
            if np.max(np.abs(new_weights - weights)) < self.tolerance:
                break

            weights = new_weights

        return weights

    def _hierarchical_risk_parity(
        self, returns: np.ndarray, asset_names: List[str]
    ) -> np.ndarray:
        """
        Calculate hierarchical risk parity weights

        Uses hierarchical clustering to group assets,
        then allocates risk within clusters
        """
        cov_matrix = np.cov(returns)
        n_assets = cov_matrix.shape[0]

        # Convert covariance to correlation
        volatilities = np.sqrt(np.diag(cov_matrix))
        correlation_matrix = cov_matrix / np.outer(volatilities, volatilities)

        # Calculate distance matrix (1 - |correlation|)
        distance_matrix = 1 - np.abs(correlation_matrix)

        # Simple hierarchical clustering (using correlation linkage)
        clusters = self._simple_hierarchical_clustering(distance_matrix)

        # Allocate weights based on cluster structure
        weights = self._allocate_cluster_weights(clusters, volatilities)

        return weights

    def _simple_hierarchical_clustering(
        self, distance_matrix: np.ndarray
    ) -> List[List[int]]:
        """
        Simple hierarchical clustering using distance matrix

        Returns list of clusters (each cluster is list of asset indices)
        """
        n_assets = distance_matrix.shape[0]

        # Initialize each asset as its own cluster
        clusters = [[i] for i in range(n_assets)]

        # Merge clusters until we have sqrt(n) clusters
        target_clusters = max(1, int(np.sqrt(n_assets)))

        while len(clusters) > target_clusters:
            # Find closest pair of clusters
            min_distance = np.inf
            merge_i, merge_j = 0, 0

            for i in range(len(clusters)):
                for j in range(i + 1, len(clusters)):
                    # Calculate distance between clusters
                    cluster_dist = self._cluster_distance(
                        clusters[i], clusters[j], distance_matrix
                    )

                    if cluster_dist < min_distance:
                        min_distance = cluster_dist
                        merge_i, merge_j = i, j

            # Merge clusters
            clusters[merge_i].extend(clusters[merge_j])
            clusters.pop(merge_j)

        return clusters

    def _cluster_distance(
        self, cluster_a: List[int], cluster_b: List[int], distance_matrix: np.ndarray
    ) -> float:
        """Calculate average distance between clusters"""
        distances = []
        for i in cluster_a:
            for j in cluster_b:
                distances.append(distance_matrix[i, j])
        return np.mean(distances)

    def _allocate_cluster_weights(
        self, clusters: List[List[int]], volatilities: np.ndarray
    ) -> np.ndarray:
        """Allocate weights to assets within clusters"""
        n_assets = len(volatilities)
        weights = np.zeros(n_assets)

        # Allocate equal risk budget to each cluster
        cluster_risk_budget = 1.0 / len(clusters)

        for cluster in clusters:
            # Calculate inverse volatility weights within cluster
            cluster_vols = volatilities[cluster]
            cluster_inv_vol = 1.0 / cluster_vols
            cluster_weights = cluster_inv_vol / np.sum(cluster_inv_vol)

            # Assign weights scaled by cluster risk budget
            for i, asset_idx in enumerate(cluster):
                weights[asset_idx] = cluster_weights[i] * cluster_risk_budget

        return weights

    def _calculate_risk_contributions(
        self, weights: np.ndarray, cov_matrix: np.ndarray
    ) -> np.ndarray:
        """
        Calculate risk contribution of each asset

        RC_i = w_i * (Cov(w, r_i) / Var(w))

        Where:
        - w = weight vector
        - Cov(w, r_i) = covariance of portfolio with asset i
        - Var(w) = portfolio variance
        """
        portfolio_variance = weights.T @ cov_matrix @ weights

        if portfolio_variance == 0:
            return np.zeros(len(weights))

        marginal_risk = (cov_matrix @ weights) / portfolio_variance
        risk_contributions = weights * marginal_risk

        return risk_contributions

    def _apply_constraints(self, weights: np.ndarray) -> np.ndarray:
        """Apply weight constraints"""
        # Min weight constraint
        weights = np.maximum(weights, self.min_weight)

        # Max weight constraint
        weights = np.minimum(weights, self.max_weight)

        return weights

    def get_risk_budget_analysis(
        self, weights: np.ndarray, cov_matrix: np.ndarray, asset_names: List[str]
    ) -> List[RiskContribution]:
        """
        Analyze risk budget for each asset

        Args:
            weights: Portfolio weights
            cov_matrix: Covariance matrix
            asset_names: Asset names

        Returns:
            List of RiskContribution objects
        """
        n_assets = len(weights)
        risk_contributions = self._calculate_risk_contributions(weights, cov_matrix)
        target_risk = 1.0 / n_assets

        analysis = []

        for i, name in enumerate(asset_names):
            marginal_risk = (cov_matrix[i, :] @ weights) / np.sqrt(
                weights.T @ cov_matrix @ weights
            )
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
        """Get summary of risk parity portfolio"""
        n_assets = len(result.weights)

        # Calculate concentration
        weights_array = np.array(list(result.weights.values()))
        herfindahl = np.sum(weights_array**2)
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


def optimize_risk_parity(
    returns_matrix: List[List[float]],
    asset_names: List[str],
    method: Optional[RiskParityMethod] = None,
    config: Optional[Dict] = None,
) -> RiskParityResult:
    """
    Convenience function to optimize risk parity portfolio

    Args:
        returns_matrix: Returns matrix (list of lists)
        asset_names: List of asset names
        method: Risk parity method
        config: Configuration dictionary

    Returns:
        RiskParityResult with optimized weights
    """
    optimizer = RiskParityOptimizer(config)

    returns = np.array(returns_matrix)

    return optimizer.optimize(returns, asset_names, method)


def main():
    """Example usage"""
    optimizer = RiskParityOptimizer()

    # Generate sample returns for 4 assets
    np.random.seed(42)
    n_assets = 4
    n_periods = 252

    # Correlated returns
    mean_returns = [0.08, 0.10, 0.12, 0.09]
    volatilities = [0.15, 0.20, 0.25, 0.18]

    # Create correlation matrix
    corr_matrix = np.array(
        [
            [1.00, 0.50, 0.30, 0.60],
            [0.50, 1.00, 0.40, 0.50],
            [0.30, 0.40, 1.00, 0.35],
            [0.60, 0.50, 0.35, 1.00],
        ]
    )

    # Generate correlated returns
    chol = np.linalg.cholesky(corr_matrix)
    random_factors = np.random.randn(n_periods, n_assets)
    correlated_factors = random_factors @ chol.T

    returns = np.zeros((n_assets, n_periods))
    for i in range(n_assets):
        returns[i, :] = (
            mean_returns[i] / 252
            + volatilities[i] / np.sqrt(252) * correlated_factors[:, i]
        )

    asset_names = ["Stock A", "Stock B", "Stock C", "Stock D"]

    # Optimize using different methods
    methods = [
        RiskParityMethod.INVERSE_VOLATILITY,
        RiskParityMethod.COVARIANCE_BASED,
        RiskParityMethod.EQUAL_RISK_CONTRIBUTION,
    ]

    for method in methods:
        print(f"\n{method.value}")
        print("=" * 50)

        result = optimizer.optimize(returns, asset_names, method)

        print(f"Converged: {result.convergence}")
        print(f"Portfolio Volatility: {result.portfolio_volatility:.4f}")
        print(f"Expected Return: {result.expected_return:.4f}")
        print(f"Sharpe Ratio: {result.sharpe_ratio:.4f}")
        print(f"Risk Parity Error: {result.risk_parity_error:.6f}")

        print("\nWeights:")
        for asset, weight in result.weights.items():
            print(f"  {asset}: {weight:.4f}")

        print("\nRisk Contributions:")
        for asset, rc in result.risk_contributions.items():
            print(f"  {asset}: {rc:.4f}")


if __name__ == "__main__":
    main()
