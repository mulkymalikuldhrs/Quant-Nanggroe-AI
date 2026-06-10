"""
Portfolio Optimization Module
Advanced portfolio construction and optimization techniques.
Based on Modern Portfolio Theory, Black-Litterman, and Risk Parity approaches.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from enum import Enum

import numpy as np
import pandas as pd
from scipy.optimize import minimize, differential_evolution
from scipy import stats

logger = logging.getLogger(__name__)


class OptimizationMethod(Enum):
    """Portfolio optimization methods"""
    MEAN_VARIANCE = "mean_variance"
    BLACK_LITTERMAN = "black_litterman"
    RISK_PARITY = "risk_parity"
    KELLY_CRITERION = "kelly"
    MIN_VARIANCE = "min_variance"
    MAX_SHARPE = "max_sharpe"
    HRP = "hrp"  # Hierarchical Risk Parity
    MVC = "mvc"  # Minimum Variance Clustered


@dataclass
class PortfolioWeights:
    """Portfolio allocation weights"""
    weights: Dict[str, float]
    method: OptimizationMethod
    expected_return: float
    volatility: float
    sharpe_ratio: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class EfficientFrontierPoint:
    """Point on the efficient frontier"""
    expected_return: float
    volatility: float
    sharpe_ratio: float
    weights: Dict[str, float]


class PortfolioOptimizer:
    """
    Advanced Portfolio Optimizer supporting multiple optimization methods.
    
    Features:
    - Mean-Variance Optimization (Markowitz)
    - Black-Litterman Model
    - Risk Parity
    - Kelly Criterion
    - Hierarchical Risk Parity (HRP)
    - Efficient Frontier generation
    """
    
    def __init__(
        self,
        returns: pd.DataFrame,
        risk_free_rate: float = 0.02,
        allow_short: bool = False,
        max_weight: float = 0.4,
        min_weight: float = 0.0
    ):
        """
        Initialize portfolio optimizer.
        
        Args:
            returns: DataFrame of asset returns (columns = assets)
            risk_free_rate: Annual risk-free rate (default: 2%)
            allow_short: Allow short selling (default: False)
            max_weight: Maximum weight per asset (default: 40%)
            min_weight: Minimum weight per asset (default: 0%)
        """
        self.returns = returns
        self.risk_free_rate = risk_free_rate
        self.allow_short = allow_short
        self.max_weight = max_weight
        self.min_weight = min_weight
        
        self.assets = list(returns.columns)
        self.n_assets = len(self.assets)
        
        # Calculate statistics
        self.mean_returns = returns.mean() * 252  # Annualized
        self.cov_matrix = returns.cov() * 252  # Annualized
        self.corr_matrix = returns.corr()
        
        # Prepare optimization bounds
        if allow_short:
            self.bounds = tuple((-1, 1) for _ in range(self.n_assets))
        else:
            self.bounds = tuple((min_weight, max_weight) for _ in range(self.n_assets))
        
        # Constraints
        self.constraints = {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
    
    def mean_variance_optimization(
        self, 
        target_return: Optional[float] = None
    ) -> PortfolioWeights:
        """
        Mean-Variance Optimization (Markowitz).
        
        Args:
            target_return: Target expected return (optional)
            
        Returns:
            Optimal portfolio weights
        """
        def portfolio_volatility(weights: np.ndarray) -> float:
            return np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix.values, weights)))
        
        def portfolio_return(weights: np.ndarray) -> float:
            return np.dot(weights, self.mean_returns.values)
        
        def portfolio_sharpe(weights: np.ndarray) -> float:
            ret = portfolio_return(weights)
            vol = portfolio_volatility(weights)
            return (ret - self.risk_free_rate) / vol if vol > 0 else 0
        
        # Optimize for maximum Sharpe ratio if no target return
        if target_return is None:
            result = minimize(
                lambda w: -portfolio_sharpe(w),
                x0=np.ones(self.n_assets) / self.n_assets,
                method='SLSQP',
                bounds=self.bounds,
                constraints=self.constraints
            )
            optimal_weights = result.x
        else:
            # Minimize volatility for target return
            constraints = [
                self.constraints,
                {'type': 'eq', 'fun': lambda x: portfolio_return(x) - target_return}
            ]
            result = minimize(
                portfolio_volatility,
                x0=np.ones(self.n_assets) / self.n_assets,
                method='SLSQP',
                bounds=self.bounds,
                constraints=constraints
            )
            optimal_weights = result.x
        
        return self._create_portfolio_weights(optimal_weights, OptimizationMethod.MEAN_VARIANCE)
    
    def min_variance_portfolio(self) -> PortfolioWeights:
        """Find minimum variance portfolio"""
        def portfolio_volatility(weights: np.ndarray) -> float:
            return np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix.values, weights)))
        
        result = minimize(
            portfolio_volatility,
            x0=np.ones(self.n_assets) / self.n_assets,
            method='SLSQP',
            bounds=self.bounds,
            constraints=self.constraints
        )
        
        return self._create_portfolio_weights(result.x, OptimizationMethod.MIN_VARIANCE)
    
    def max_sharpe_portfolio(self) -> PortfolioWeights:
        """Find maximum Sharpe ratio portfolio"""
        return self.mean_variance_optimization()
    
    def risk_parity_portfolio(self) -> PortfolioWeights:
        """
        Risk Parity Optimization.
        Each asset contributes equally to portfolio risk.
        """
        def risk_contribution(weights: np.ndarray) -> np.ndarray:
            portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix.values, weights)))
            marginal_contrib = np.dot(self.cov_matrix.values, weights)
            risk_contrib = weights * marginal_contrib / portfolio_vol
            return risk_contrib
        
        def objective(weights: np.ndarray) -> float:
            rc = risk_contribution(weights)
            target_rc = np.ones(self.n_assets) / self.n_assets
            return np.sum((rc - target_rc) ** 2)
        
        result = minimize(
            objective,
            x0=np.ones(self.n_assets) / self.n_assets,
            method='SLSQP',
            bounds=self.bounds,
            constraints=self.constraints
        )
        
        return self._create_portfolio_weights(result.x, OptimizationMethod.RISK_PARITY)
    
    def kelly_criterion(
        self, 
        max_leverage: float = 2.0
    ) -> PortfolioWeights:
        """
        Kelly Criterion for optimal position sizing.
        
        Args:
            max_leverage: Maximum leverage allowed
            
        Returns:
            Kelly-optimal portfolio weights
        """
        # Kelly formula: f* = (μ - r) / σ²
        # For multiple assets, use Kelly with covariance
        
        def negative_sharpe(weights: np.ndarray) -> float:
            port_return = np.dot(weights, self.mean_returns.values)
            port_vol = np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix.values, weights)))
            return -(port_return - self.risk_free_rate) / port_vol if port_vol > 0 else 0
        
        # Maximize Kelly (minimize negative Sharpe)
        bounds = tuple((-max_leverage, max_leverage) for _ in range(self.n_assets))
        constraints = {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
        
        result = minimize(
            negative_sharpe,
            x0=np.ones(self.n_assets) / self.n_assets,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        # Rescale to sum to 1 (Kelly can exceed 100%)
        weights = result.x
        weights = np.maximum(weights, -max_leverage)
        weights = np.minimum(weights, max_leverage)
        
        return self._create_portfolio_weights(weights, OptimizationMethod.KELLY_CRITERION)
    
    def black_litterman(
        self,
        market_caps: Dict[str, float],
        views: Dict[str, Tuple[float, float]] = None,
        tau: float = 0.05,
        risk_aversion: float = 2.5,
        view_confidence: float = 0.5
    ) -> PortfolioWeights:
        """
        Black-Litterman Model for portfolio optimization.
        
        Args:
            market_caps: Market capitalizations for each asset
            views: Dict of {asset: (expected_return, confidence)} - optional
            tau: Uncertainty in equilibrium (default: 0.05)
            risk_aversion: Market risk aversion coefficient (default: 2.5)
            view_confidence: Confidence in views (default: 0.5)
            
        Returns:
            Black-Litterman optimal portfolio
        """
        # Market cap weights (equilibrium)
        total_mkt_cap = sum(market_caps.values())
        w_market = np.array([market_caps[a] / total_mkt_cap for a in self.assets])
        
        # Equilibrium expected returns
        delta = risk_aversion  # Risk aversion coefficient
        eq_returns = delta * np.dot(self.cov_matrix.values, w_market)
        
        # If no views, use equilibrium
        if views is None or len(views) == 0:
            return self._create_portfolio_weights(w_market, OptimizationMethod.BLACK_LITTERMAN)
        
        # Incorporate views
        n_views = len(views)
        
        # View matrix P (which assets have views)
        P = np.zeros((n_views, self.n_assets))
        Q = np.zeros(n_views)  # View returns
        omega = np.zeros((n_views, n_views))  # View uncertainty
        
        for i, (asset, (view_return, conf)) in enumerate(views.items()):
            asset_idx = self.assets.index(asset)
            P[i, asset_idx] = 1
            Q[i] = view_return
            # Diagonal matrix of view uncertainty
            omega[i, i] = (1 - conf) / conf * tau * self.cov_matrix.values[asset_idx, asset_idx]
        
        # Black-Litterman formula
        # posterior_expected = [(τΣ)^-1 + P'Ω^-1 P]^-1 * [(τΣ)^-1 * π + P'Ω^-1 * Q]
        
        tau_sigma = tau * self.cov_matrix.values
        
        # Compute posterior
        try:
            inv_tau_sigma = np.linalg.inv(tau_sigma)
            M = np.linalg.inv(inv_tau_sigma + P.T @ np.linalg.inv(omega) @ P)
            posterior_returns = M @ (inv_tau_sigma @ eq_returns + P.T @ np.linalg.inv(omega) @ Q)
        except np.linalg.LinAlgError:
            logger.warning("Singular matrix in Black-Litterman, using equilibrium")
            posterior_returns = eq_returns
        
        # Optimize with posterior expected returns
        def portfolio_sharpe(weights: np.ndarray) -> float:
            ret = np.dot(weights, posterior_returns)
            vol = np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix.values, weights)))
            return (ret - self.risk_free_rate) / vol if vol > 0 else 0
        
        result = minimize(
            lambda w: -portfolio_sharpe(w),
            x0=w_market,
            method='SLSQP',
            bounds=self.bounds,
            constraints=self.constraints
        )
        
        return self._create_portfolio_weights(result.x, OptimizationMethod.BLACK_LITTERMAN)
    
    def hierarchical_risk_parity(self) -> PortfolioWeights:
        """
        Hierarchical Risk Parity (HRP) using clustering.
        Based on Marcos Lopez de Prado's methodology.
        
        Returns:
            HRP optimal portfolio
        """
        from scipy.cluster.hierarchy import linkage, leaves_list
        from scipy.spatial.distance import squareform
        
        # Calculate distance matrix from correlation
        corr = self.corr_matrix.values
        dist = np.sqrt(0.5 * (1 - corr))
        dist_condensed = squareform(dist)
        
        # Hierarchical clustering
        link = linkage(dist_condensed, method='ward')
        
        # Get sorted order
        sorted_idx = leaves_list(link)
        
        # Reorder assets
        sorted_assets = [self.assets[i] for i in sorted_idx]
        sorted_cov = self.cov_matrix.loc[sorted_assets, sorted_assets]
        
        # Recursive bisection
        def recursive_bisection(cov_matrix: pd.DataFrame, indices: List[int]) -> np.ndarray:
            n = len(indices)
            if n == 1:
                return np.array([1.0])
            
            # Split into two clusters
            mid = n // 2
            left_idx = indices[:mid]
            right_idx = indices[mid:]
            
            # Calculate inverse variance weights for each cluster
            def cluster_variance(idx_list):
                sub_cov = cov_matrix.iloc[idx_list, idx_list].values
                inv_var = 1 / np.diag(sub_cov)
                return inv_var / inv_var.sum()
            
            left_weights = recursive_bisection(cov_matrix, left_idx)
            right_weights = recursive_bisection(cov_matrix, right_idx)
            
            # Combine weights
            weights = np.zeros(n)
            weights[:mid] = left_weights * 0.5
            weights[mid:] = right_weights * 0.5
            
            return weights
        
        n = self.n_assets
        weights = recursive_bisection(sorted_cov, list(range(n)))
        
        # Remap to original order
        final_weights = np.zeros(n)
        for i, idx in enumerate(sorted_idx):
            final_weights[idx] = weights[i]
        
        # Normalize to sum to 1
        final_weights = final_weights / final_weights.sum()
        
        return self._create_portfolio_weights(final_weights, OptimizationMethod.HRP)
    
    def efficient_frontier(
        self, 
        n_points: int = 50,
        method: str = "max_sharpe"
    ) -> List[EfficientFrontierPoint]:
        """
        Generate efficient frontier points.
        
        Args:
            n_points: Number of points on frontier
            method: Optimization method
            
        Returns:
            List of efficient frontier points
        """
        # Get min and max returns
        min_return = self.mean_returns.min() * 0.5
        max_return = self.mean_returns.max() * 1.5
        
        returns_range = np.linspace(min_return, max_return, n_points)
        
        frontier = []
        for target_ret in returns_range:
            try:
                if method == "min_var":
                    result = self._min_variance_for_return(target_ret)
                else:
                    result = self._min_variance_for_return(target_ret)
                
                weights = result.x
                
                # Calculate metrics
                port_return = np.dot(weights, self.mean_returns.values)
                port_vol = np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix.values, weights)))
                sharpe = (port_return - self.risk_free_rate) / port_vol if port_vol > 0 else 0
                
                frontier.append(EfficientFrontierPoint(
                    expected_return=port_return,
                    volatility=port_vol,
                    sharpe_ratio=sharpe,
                    weights=dict(zip(self.assets, weights))
                ))
            except Exception as e:
                logger.warning(f"Could not compute point at return {target_ret}: {e}")
        
        return frontier
    
    def _min_variance_for_return(self, target_return: float):
        """Helper for minimum variance at target return"""
        def portfolio_volatility(weights: np.ndarray) -> float:
            return np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix.values, weights)))
        
        constraints = [
            self.constraints,
            {'type': 'eq', 'fun': lambda w: np.dot(w, self.mean_returns.values) - target_return}
        ]
        
        return minimize(
            portfolio_volatility,
            x0=np.ones(self.n_assets) / self.n_assets,
            method='SLSQP',
            bounds=self.bounds,
            constraints=constraints
        )
    
    def optimize_with_constraints(
        self,
        constraints: Dict[str, float],
        method: OptimizationMethod = OptimizationMethod.MEAN_VARIANCE
    ) -> PortfolioWeights:
        """
        Optimize with custom constraints.
        
        Args:
            constraints: Dict of {asset: max_weight}
            method: Optimization method
            
        Returns:
            Optimal portfolio weights
        """
        # Update bounds based on constraints
        bounds = []
        for asset in self.assets:
            if asset in constraints:
                bounds.append((self.min_weight, constraints[asset]))
            else:
                bounds.append(self.bounds[0])
        
        # Save original bounds and constraints
        orig_bounds = self.bounds
        self.bounds = tuple(bounds)
        
        # Optimize
        if method == OptimizationMethod.RISK_PARITY:
            result = self.risk_parity_portfolio()
        elif method == OptimizationMethod.MIN_VARIANCE:
            result = self.min_variance_portfolio()
        else:
            result = self.mean_variance_optimization()
        
        # Restore original bounds
        self.bounds = orig_bounds
        
        return result
    
    def _create_portfolio_weights(
        self, 
        weights: np.ndarray, 
        method: OptimizationMethod
    ) -> PortfolioWeights:
        """Create PortfolioWeights dataclass from numpy array"""
        # Clean small weights
        weights = np.where(np.abs(weights) < 0.001, 0, weights)
        weights = weights / weights.sum()
        
        # Create dict
        weight_dict = {asset: float(weights[i]) for i, asset in enumerate(self.assets)}
        
        # Calculate metrics
        port_return = np.dot(weights, self.mean_returns.values)
        port_vol = np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix.values, weights)))
        sharpe = (port_return - self.risk_free_rate) / port_vol if port_vol > 0 else 0
        
        return PortfolioWeights(
            weights=weight_dict,
            method=method,
            expected_return=port_return,
            volatility=port_vol,
            sharpe_ratio=sharpe
        )
    
    def get_diversification_metrics(self, weights: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate portfolio diversification metrics.
        
        Args:
            weights: Portfolio weights
            
        Returns:
            Dict of diversification metrics
        """
        weight_array = np.array([weights.get(a, 0) for a in self.assets])
        
        # Portfolio variance contribution
        marginal_contrib = np.dot(self.cov_matrix.values, weight_array)
        port_vol = np.sqrt(np.dot(weight_array.T, marginal_contrib))
        risk_contrib = weight_array * marginal_contrib / port_vol if port_vol > 0 else np.zeros(self.n_assets)
        
        # Diversification ratio
        weighted_vol = np.sum(weight_array * np.sqrt(np.diag(self.cov_matrix.values)))
        diversification_ratio = weighted_vol / port_vol if port_vol > 0 else 1
        
        # Effective number of assets
        hhi = np.sum(weight_array ** 2)
        effective_assets = 1 / hhi if hhi > 0 else 1
        
        # Correlation-based diversity
        avg_corr = (self.corr_matrix.values.sum() - self.n_assets) / (self.n_assets * (self.n_assets - 1))
        
        return {
            'diversification_ratio': diversification_ratio,
            'effective_number_of_assets': effective_assets,
            'avg_correlation': avg_corr,
            'risk_contribution': dict(zip(self.assets, risk_contrib)),
            'portfolio_volatility': port_vol,
            'portfolio_return': np.dot(weight_array, self.mean_returns.values)
        }


def calculate_portfolio_metrics(
    returns: pd.DataFrame,
    weights: Dict[str, float]
) -> Dict[str, float]:
    """
    Calculate comprehensive portfolio metrics.
    
    Args:
        returns: DataFrame of asset returns
        weights: Portfolio weights
        
    Returns:
        Dict of portfolio metrics
    """
    weight_array = np.array([weights.get(c, 0) for c in returns.columns])
    
    # Portfolio returns
    port_returns = (returns * weight_array).sum(axis=1)
    
    # Annualized return
    annual_return = port_returns.mean() * 252
    
    # Annualized volatility
    annual_vol = port_returns.std() * np.sqrt(252)
    
    # Sharpe ratio
    risk_free = 0.02
    sharpe = (annual_return - risk_free) / annual_vol if annual_vol > 0 else 0
    
    # Maximum drawdown
    cumulative = (1 + port_returns).cumprod()
    peak = cumulative.expanding().max()
    drawdown = (cumulative - peak) / peak
    max_drawdown = drawdown.min()
    
    # Skewness and Kurtosis
    skew = stats.skew(port_returns)
    kurt = stats.kurtosis(port_returns)
    
    # VaR and CVaR (95%)
    var_95 = np.percentile(port_returns, 5)
    cvar_95 = port_returns[port_returns <= var_95].mean()
    
    # Win rate
    win_rate = (port_returns > 0).mean()
    
    # Profit factor
    gross_profit = port_returns[port_returns > 0].sum()
    gross_loss = abs(port_returns[port_returns <= 0].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    return {
        'annual_return': annual_return,
        'annual_volatility': annual_vol,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_drawdown,
        'skewness': skew,
        'kurtosis': kurt,
        'var_95': var_95,
        'cvar_95': cvar_95,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'total_return': (1 + port_returns).prod() - 1,
        'num_trades': len(port_returns),
        'avg_win': port_returns[port_returns > 0].mean() if len(port_returns[port_returns > 0]) > 0 else 0,
        'avg_loss': port_returns[port_returns <= 0].mean() if len(port_returns[port_returns <= 0]) > 0 else 0,
    }


# Example usage
if __name__ == "__main__":
    import pandas as pd
    import numpy as np
    
    # Generate sample returns
    np.random.seed(42)
    n_assets = 5
    n_days = 252
    
    returns = pd.DataFrame(
        np.random.randn(n_days, n_assets) * 0.02,
        columns=['AAPL', 'GOOG', 'MSFT', 'AMZN', 'META']
    )
    
    # Initialize optimizer
    optimizer = PortfolioOptimizer(returns)
    
    # Run different optimizations
    print("Portfolio Optimization Results:")
    print("=" * 60)
    
    # Mean-Variance
    mv_portfolio = optimizer.mean_variance_optimization()
    print(f"\nMean-Variance Portfolio:")
    print(f"  Expected Return: {mv_portfolio.expected_return:.2%}")
    print(f"  Volatility: {mv_portfolio.volatility:.2%}")
    print(f"  Sharpe Ratio: {mv_portfolio.sharpe_ratio:.3f}")
    print(f"  Weights: {mv_portfolio.weights}")
    
    # Risk Parity
    rp_portfolio = optimizer.risk_parity_portfolio()
    print(f"\nRisk Parity Portfolio:")
    print(f"  Expected Return: {rp_portfolio.expected_return:.2%}")
    print(f"  Volatility: {rp_portfolio.volatility:.2%}")
    print(f"  Sharpe Ratio: {rp_portfolio.sharpe_ratio:.3f}")
    
    # Min Variance
    mv_portfolio = optimizer.min_variance_portfolio()
    print(f"\nMin Variance Portfolio:")
    print(f"  Expected Return: {mv_portfolio.expected_return:.2%}")
    print(f"  Volatility: {mv_portfolio.volatility:.2%}")
    
    # HRP
    hrp_portfolio = optimizer.hierarchical_risk_parity()
    print(f"\nHierarchical Risk Parity Portfolio:")
    print(f"  Expected Return: {hrp_portfolio.expected_return:.2%}")
    print(f"  Volatility: {hrp_portfolio.volatility:.2%}")
    
    # Diversification metrics
    metrics = optimizer.get_diversification_metrics(mv_portfolio.weights)
    print(f"\nDiversification Metrics:")
    print(f"  Diversification Ratio: {metrics['diversification_ratio']:.3f}")
    print(f"  Effective Assets: {metrics['effective_number_of_assets']:.2f}")
    print(f"  Avg Correlation: {metrics['avg_correlation']:.3f}")
