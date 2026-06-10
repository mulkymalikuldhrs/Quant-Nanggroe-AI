"""
Advanced Risk Management Framework
Comprehensive risk analysis and management for quant trading.
Supports VaR, CVaR, stress testing, and position sizing.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from enum import Enum
from functools import lru_cache

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize

logger = logging.getLogger(__name__)


class RiskMetric(Enum):
    """Types of risk metrics"""
    VAR = "var"
    CVAR = "cvar"
    MAX_DRAWDOWN = "max_drawdown"
    VOLATILITY = "volatility"
    BETA = "beta"
    TRACKING_ERROR = "tracking_error"
    INFORMATION_RATIO = "information_ratio"


@dataclass
class RiskLimit:
    """Risk limit configuration"""
    metric: RiskMetric
    limit_value: float
    warning_threshold: float = 0.8  # Warn at 80% of limit
    is_hard_limit: bool = True


@dataclass
class RiskReport:
    """Comprehensive risk report"""
    timestamp: datetime
    current_risk: Dict[str, float]
    limits: Dict[str, Dict]
    breach_count: int
    warnings: List[str]
    recommendations: List[str]
    risk_score: float  # 0-100


@dataclass
class PositionRisk:
    """Risk metrics for a single position"""
    ticker: str
    position_size: float
    notional_value: float
    var_95: float
    var_99: float
    cvar_95: float
    beta: float
    correlation_risk: float
    liquidity_risk: str  # LOW, MEDIUM, HIGH
    max_loss: float


class RiskManagementFramework:
    """
    Advanced Risk Management Framework.
    
    Features:
    - Value at Risk (VaR) - Historical, Parametric, Monte Carlo
    - Conditional VaR (CVaR / Expected Shortfall)
    - Maximum Drawdown analysis
    - Stress testing
    - Position sizing optimization
    - Risk limit monitoring
    - Correlation-based risk
    """
    
    def __init__(
        self,
        initial_capital: float = 1000000,
        risk_free_rate: float = 0.02,
        confidence_levels: List[float] = [0.95, 0.99]
    ):
        """
        Initialize risk management framework.
        
        Args:
            initial_capital: Starting capital
            risk_free_rate: Annual risk-free rate
            confidence_levels: VaR confidence levels
        """
        self.initial_capital = initial_capital
        self.risk_free_rate = risk_free_rate
        self.confidence_levels = confidence_levels
        
        self.risk_limits: List[RiskLimit] = []
        self.position_history: List[Dict] = []
    
    def add_risk_limit(
        self,
        metric: RiskMetric,
        limit_value: float,
        warning_threshold: float = 0.8,
        is_hard_limit: bool = True
    ):
        """Add a risk limit to monitor"""
        self.risk_limits.append(RiskLimit(
            metric=metric,
            limit_value=limit_value,
            warning_threshold=warning_threshold,
            is_hard_limit=is_hard_limit
        ))
    
    # ==================== VaR CALCULATIONS ====================
    
    def calculate_historical_var(
        self,
        returns: pd.Series,
        confidence: float = 0.95,
        holding_period: int = 1
    ) -> float:
        """
        Calculate Value at Risk using historical method.
        
        Args:
            returns: Series of returns
            confidence: Confidence level (e.g., 0.95)
            holding_period: Holding period in days
            
        Returns:
            VaR as a positive number (loss)
        """
        var = np.percentile(returns, (1 - confidence) * 100)
        return abs(var * np.sqrt(holding_period))
    
    def calculate_parametric_var(
        self,
        returns: pd.Series,
        confidence: float = 0.95,
        holding_period: int = 1
    ) -> float:
        """
        Calculate Value at Risk using parametric (variance-covariance) method.
        
        Assumes normal distribution.
        """
        mu = returns.mean()
        sigma = returns.std()
        
        z_score = stats.norm.ppf(1 - confidence)
        var = -(mu * holding_period + z_score * sigma * np.sqrt(holding_period))
        return abs(var)
    
    def calculate_monte_carlo_var(
        self,
        returns: pd.Series,
        portfolio_value: float,
        confidence: float = 0.95,
        n_simulations: int = 10000,
        holding_period: int = 1
    ) -> float:
        """
        Calculate VaR using Monte Carlo simulation.
        
        Args:
            returns: Historical returns
            portfolio_value: Current portfolio value
            confidence: Confidence level
            n_simulations: Number of simulations
            holding_period: Holding period in days
            
        Returns:
            VaR as a positive number
        """
        mu = returns.mean() * holding_period
        sigma = returns.std() * np.sqrt(holding_period)
        
        # Simulate returns
        simulated_returns = np.random.normal(mu, sigma, n_simulations)
        
        # Calculate portfolio values
        simulated_values = portfolio_value * (1 + simulated_returns)
        
        # VaR is the loss at confidence level
        var = portfolio_value - np.percentile(simulated_values, (1 - confidence) * 100)
        return var
    
    def calculate_var(
        self,
        returns: pd.Series,
        portfolio_value: float,
        method: str = "historical",
        confidence: float = 0.95,
        holding_period: int = 1
    ) -> float:
        """
        Calculate VaR using specified method.
        
        Args:
            returns: Series of returns
            portfolio_value: Current portfolio value
            method: 'historical', 'parametric', 'monte_carlo'
            confidence: Confidence level
            holding_period: Holding period
            
        Returns:
            VaR as percentage of portfolio
        """
        if method == "historical":
            var_pct = self.calculate_historical_var(returns, confidence, holding_period)
        elif method == "parametric":
            var_pct = self.calculate_parametric_var(returns, confidence, holding_period)
        elif method == "monte_carlo":
            var_pct = self.calculate_monte_carlo_var(
                returns, portfolio_value, confidence, holding_period=holding_period
            ) / portfolio_value
        else:
            raise ValueError(f"Unknown VaR method: {method}")
        
        return var_pct
    
    # ==================== CVAR CALCULATIONS ====================
    
    def calculate_cvar(
        self,
        returns: pd.Series,
        portfolio_value: float,
        confidence: float = 0.95,
        method: str = "historical"
    ) -> float:
        """
        Calculate Conditional Value at Risk (CVaR / Expected Shortfall).
        
        CVaR is the expected loss given that the loss exceeds VaR.
        """
        if method == "historical":
            var_threshold = np.percentile(returns, (1 - confidence) * 100)
            tail_losses = returns[returns <= var_threshold]
            cvar = abs(tail_losses.mean())
        elif method == "parametric":
            # For normal distribution, CVaR = mu + (sigma * n(d2) / (1 - confidence))
            # where d2 is related to the normal distribution
            mu = returns.mean()
            sigma = returns.std()
            z = stats.norm.ppf(1 - confidence)
            n = stats.norm.pdf(z) / (1 - confidence)
            cvar = abs(mu + sigma * n)
        else:
            raise ValueError(f"Unknown CVaR method: {method}")
        
        return cvar * portfolio_value
    
    # ==================== MAX DRAWDOWN ====================
    
    def calculate_max_drawdown(self, returns: pd.Series) -> Tuple[float, float, datetime, datetime]:
        """
        Calculate maximum drawdown and related metrics.
        
        Returns:
            Tuple of (max_drawdown, max_drawdown_duration, peak_date, trough_date)
        """
        cumulative = (1 + returns).cumprod()
        peak = cumulative.expanding().max()
        drawdown = (cumulative - peak) / peak
        
        max_dd = drawdown.min()
        trough_idx = drawdown.idxmin()
        
        # Find peak before trough
        peak_idx = peak[:trough_idx].idxmax()
        
        # Calculate duration
        duration = trough_idx - peak_idx
        
        return abs(max_dd), duration, peak_idx, trough_idx
    
    def calculate_avg_drawdown(self, returns: pd.Series) -> float:
        """Calculate average drawdown"""
        cumulative = (1 + returns).cumprod()
        peak = cumulative.expanding().max()
        drawdown = (cumulative - peak) / peak
        return abs(drawdown.mean())
    
    def calculate_drawdown_series(self, returns: pd.Series) -> pd.Series:
        """Calculate drawdown series"""
        cumulative = (1 + returns).cumprod()
        peak = cumulative.expanding().max()
        drawdown = (cumulative - peak) / peak
        return drawdown
    
    # ==================== STRESS TESTING ====================
    
    def stress_test(
        self,
        returns: pd.Series,
        scenarios: Dict[str, Tuple[float, float]] = None
    ) -> Dict[str, Dict[str, float]]:
        """
        Run stress tests on portfolio.
        
        Args:
            returns: Historical returns
            scenarios: Dict of {scenario_name: (return_change, vol_change)}
            
        Returns:
            Dict of scenario results
        """
        if scenarios is None:
            scenarios = {
                '2008_Crisis': (-0.40, 2.0),
                'COVID_Crash': (-0.30, 1.5),
                'Rate_Hike': (-0.15, 1.2),
                'Tech_Crash': (-0.25, 1.5),
                'Recovery': (0.20, 0.8),
                'Bull_Market': (0.30, 0.9)
            }
        
        results = {}
        base_return = returns.mean() * 252
        base_vol = returns.std() * np.sqrt(252)
        
        for scenario, (ret_change, vol_change) in scenarios.items():
            stressed_return = base_return * ret_change
            stressed_vol = base_vol * vol_change
            
            # Assuming normal distribution for stressed scenario
            var_95 = stressed_return - 1.645 * stressed_vol
            cvar_95 = stressed_return - stressed_vol * stats.norm.pdf(1.645) / 0.05
            
            results[scenario] = {
                'expected_return': stressed_return,
                'volatility': stressed_vol,
                'var_95': var_95,
                'cvar_95': cvar_95,
                'sharpe_ratio': (stressed_return - self.risk_free_rate) / stressed_vol if stressed_vol > 0 else 0
            }
        
        return results
    
    # ==================== POSITION SIZING ====================
    
    def kelly_position_size(
        self,
        returns: pd.Series,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        max_kelly: float = 0.25  # Fractional Kelly
    ) -> float:
        """
        Calculate optimal position size using Kelly Criterion.
        
        f* = (bp - q) / b
        
        Where:
        b = odds received (avg_win / abs(avg_loss))
        p = probability of win (win_rate)
        q = probability of loss (1 - p)
        """
        if avg_loss == 0:
            return 0
        
        b = avg_win / abs(avg_loss)
        p = win_rate
        q = 1 - p
        
        kelly = (b * p - q) / b
        
        # Apply fractional Kelly
        kelly = kelly * max_kelly
        
        # Bound to reasonable range
        kelly = max(0, min(kelly, max_kelly))
        
        return kelly
    
    def optimal_f_position_size(
        self,
        returns: pd.Series,
        target_volatility: float = 0.10,
        lookback: int = 252
    ) -> float:
        """
        Calculate position size to target volatility.
        
        Uses volatility targeting approach.
        """
        recent_returns = returns.tail(lookback)
        current_vol = recent_returns.std() * np.sqrt(252)
        
        if current_vol == 0:
            return 1.0
        
        # Scale position to target volatility
        position_size = target_volatility / current_vol
        
        # Bound position
        position_size = max(0.1, min(position_size, 3.0))
        
        return position_size
    
    def atr_position_size(
        self,
        entry_price: float,
        atr: float,
        account_balance: float,
        risk_per_trade: float = 0.02,
        max_risk_per_trade: float = 0.05
    ) -> Tuple[int, float, float]:
        """
        Calculate position size using ATR (Average True Range).
        
        Args:
            entry_price: Entry price
            atr: Average True Range
            account_balance: Account balance
            risk_per_trade: Fraction of account to risk
            max_risk_per_trade: Maximum risk per trade
            
        Returns:
            Tuple of (position_size, stop_loss, risk_amount)
        """
        # Calculate risk amount
        risk_amount = min(
            account_balance * risk_per_trade,
            account_balance * max_risk_per_trade
        )
        
        # Calculate stop loss distance (2 ATR)
        stop_distance = 2 * atr
        
        # Calculate position size
        if stop_distance == 0:
            return 0, 0, 0
        
        position_size = risk_amount / stop_distance
        
        # Calculate stop loss price
        stop_loss = entry_price - stop_distance
        
        return position_size, stop_loss, risk_amount
    
    def calculate_position_size_with_var(
        self,
        returns: pd.Series,
        portfolio_value: float,
        max_var_pct: float = 0.02,
        confidence: float = 0.95
    ) -> float:
        """
        Calculate position size based on VaR limit.
        
        Args:
            returns: Historical returns
            portfolio_value: Current portfolio value
            max_var_pct: Maximum VaR as percentage of portfolio
            confidence: VaR confidence level
            
        Returns:
            Position size as fraction of portfolio
        """
        var_pct = self.calculate_var(returns, portfolio_value, confidence=confidence)
        
        if var_pct == 0:
            return 1.0
        
        # Scale position to meet VaR limit
        position_size = min(1.0, max_var_pct / var_pct)
        
        return position_size
    
    # ==================== RISK LIMITS ====================
    
    def check_risk_limits(
        self,
        portfolio_value: float,
        positions: Dict[str, float],
        returns: pd.Series
    ) -> RiskReport:
        """
        Check all risk limits and generate report.
        
        Args:
            portfolio_value: Current portfolio value
            positions: Dict of {ticker: position_value}
            returns: Portfolio returns
            
        Returns:
            RiskReport with limit status
        """
        warnings = []
        breach_count = 0
        current_risk = {}
        
        # Calculate current risk metrics
        for limit in self.risk_limits:
            if limit.metric == RiskMetric.VAR:
                var = self.calculate_var(returns, portfolio_value, confidence=0.95)
                var_pct = var / portfolio_value
                current_risk['var_95'] = var_pct
                
                if var_pct > limit.limit_value:
                    if limit.is_hard_limit:
                        breach_count += 1
                        warnings.append(f"VaR limit breached: {var_pct:.2%} > {limit.limit_value:.2%}")
                    else:
                        warnings.append(f"VaR warning: {var_pct:.2%} approaching limit")
            
            elif limit.metric == RiskMetric.CVAR:
                cvar = self.calculate_cvar(returns, portfolio_value, confidence=0.95)
                cvar_pct = cvar / portfolio_value
                current_risk['cvar_95'] = cvar_pct
            
            elif limit.metric == RiskMetric.MAX_DRAWDOWN:
                max_dd, _, _, _ = self.calculate_max_drawdown(returns)
                current_risk['max_drawdown'] = max_dd
                
                if max_dd > limit.limit_value:
                    breach_count += 1
                    warnings.append(f"Max drawdown breached: {max_dd:.2%} > {limit.limit_value:.2%}")
        
        # Check concentration limits
        total_value = sum(positions.values()) if positions else portfolio_value
        for ticker, value in positions.items():
            concentration = value / total_value if total_value > 0 else 0
            if concentration > 0.25:  # 25% max per position
                warnings.append(f"Position concentration high: {ticker} = {concentration:.2%}")
                breach_count += 1
        
        # Calculate risk score (0-100)
        risk_score = 100 - min(100, breach_count * 20 + len(warnings) * 5)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(current_risk, positions)
        
        return RiskReport(
            timestamp=datetime.now(),
            current_risk=current_risk,
            limits={l.metric.value: {'limit': l.limit_value, 'current': current_risk.get(l.metric.value, 0)} 
                   for l in self.risk_limits},
            breach_count=breach_count,
            warnings=warnings,
            recommendations=recommendations,
            risk_score=risk_score
        )
    
    def _generate_recommendations(
        self, 
        current_risk: Dict[str, float], 
        positions: Dict[str, float]
    ) -> List[str]:
        """Generate risk management recommendations"""
        recommendations = []
        
        if current_risk.get('var_95', 0) > 0.02:
            recommendations.append("Consider reducing position sizes to lower VaR")
        
        if current_risk.get('max_drawdown', 0) > 0.15:
            recommendations.append("Implement or tighten stop-losses to limit drawdown")
        
        if len(positions) > 0:
            total = sum(positions.values())
            for ticker, value in positions.items():
                if value / total > 0.2:
                    recommendations.append(f"Diversify away from {ticker} (overweight)")
        
        if len(positions) < 5:
            recommendations.append("Consider adding more positions for diversification")
        
        return recommendations
    
    # ==================== BETA & RISK DECOMPOSITION ====================
    
    def calculate_beta(
        self,
        asset_returns: pd.Series,
        market_returns: pd.Series
    ) -> float:
        """Calculate asset beta relative to market"""
        covariance = asset_returns.cov(market_returns)
        market_var = market_returns.var()
        
        if market_var == 0:
            return 1.0
        
        return covariance / market_var
    
    def calculate_risk_contribution(
        self,
        weights: np.ndarray,
        cov_matrix: pd.DataFrame
    ) -> np.ndarray:
        """
        Calculate risk contribution of each asset.
        
        Args:
            weights: Portfolio weights
            cov_matrix: Covariance matrix
            
        Returns:
            Risk contribution of each asset
        """
        portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix.values, weights)))
        marginal_contrib = np.dot(cov_matrix.values, weights)
        risk_contrib = weights * marginal_contrib / portfolio_vol if portfolio_vol > 0 else np.zeros(len(weights))
        
        return risk_contrib
    
    # ==================== CORRELATION ANALYSIS ====================
    
    def calculate_correlation_matrix(
        self,
        returns: pd.DataFrame
    ) -> pd.DataFrame:
        """Calculate rolling correlation matrix"""
        return returns.corr()
    
    def find_high_correlation_pairs(
        self,
        returns: pd.DataFrame,
        threshold: float = 0.8
    ) -> List[Tuple[str, str, float]]:
        """
        Find pairs of assets with high correlation.
        
        Returns:
            List of (asset1, asset2, correlation) tuples
        """
        corr_matrix = returns.corr()
        high_corr = []
        
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                corr = corr_matrix.iloc[i, j]
                if abs(corr) > threshold:
                    high_corr.append((
                        corr_matrix.columns[i],
                        corr_matrix.columns[j],
                        corr
                    ))
        
        return sorted(high_corr, key=lambda x: abs(x[2]), reverse=True)
    
    # ==================== LIQUIDITY RISK ====================
    
    def estimate_liquidity_risk(
        self,
        avg_daily_volume: float,
        position_size: float,
        avg_daily_return: float
    ) -> str:
        """
        Estimate liquidity risk for a position.
        
        Args:
            avg_daily_volume: Average daily trading volume
            position_size: Size of position
            avg_daily_return: Average daily return
            
        Returns:
            Liquidity risk level: LOW, MEDIUM, HIGH
        """
        if avg_daily_volume == 0:
            return "HIGH"
        
        turnover_ratio = position_size / avg_daily_volume
        
        if turnover_ratio < 0.1:
            return "LOW"
        elif turnover_ratio < 0.5:
            return "MEDIUM"
        else:
            return "HIGH"
    
    def estimate_market_impact(
        self,
        position_size: float,
        avg_daily_volume: float,
        avg_daily_return: float,
        asset_volatility: float
    ) -> float:
        """
        Estimate market impact of executing a position.
        
        Uses Almgren-Chriss model approximation.
        
        Returns:
            Estimated market impact as fraction of price
        """
        if avg_daily_volume == 0:
            return 0.1
        
        lambda_param = 0.1  # Impact coefficient
        
        # Participation rate
        theta = position_size / avg_daily_volume
        
        # Market impact estimate
        impact = lambda_param * theta * asset_volatility / np.sqrt(theta)
        
        return min(impact, 0.5)  # Cap at 50%
    
    # ==================== COMPREHENSIVE RISK REPORT ====================
    
    def generate_comprehensive_risk_report(
        self,
        portfolio_returns: pd.Series,
        asset_returns: pd.DataFrame,
        portfolio_value: float,
        positions: Dict[str, float],
        market_returns: pd.Series = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive risk analysis report.
        
        Args:
            portfolio_returns: Portfolio return series
            asset_returns: Individual asset returns
            portfolio_value: Current portfolio value
            positions: Current positions
            market_returns: Benchmark returns
            
        Returns:
            Comprehensive risk report
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'portfolio_value': portfolio_value,
            'var': {},
            'cvar': {},
            'drawdown': {},
            'stress_test': {},
            'correlation_analysis': {},
            'risk_contribution': {},
            'liquidity': {},
            'recommendations': []
        }
        
        # VaR calculations
        for confidence in [0.95, 0.99]:
            var = self.calculate_var(portfolio_returns, portfolio_value, confidence=confidence)
            cvar = self.calculate_cvar(portfolio_returns, portfolio_value, confidence=confidence)
            report['var'][f'{confidence:.0%}'] = var
            report['cvar'][f'{confidence:.0%}'] = cvar
        
        # Drawdown analysis
        max_dd, duration, peak, trough = self.calculate_max_drawdown(portfolio_returns)
        report['drawdown'] = {
            'max_drawdown': max_dd,
            'max_drawdown_duration_days': duration.days if hasattr(duration, 'days') else duration,
            'peak_date': str(peak),
            'trough_date': str(trough),
            'avg_drawdown': self.calculate_avg_drawdown(portfolio_returns)
        }
        
        # Stress testing
        report['stress_test'] = self.stress_test(portfolio_returns)
        
        # Correlation analysis
        high_corr = self.find_high_correlation_pairs(asset_returns)
        report['correlation_analysis'] = {
            'high_correlation_pairs': high_corr[:10],
            'correlation_matrix': asset_returns.corr().to_dict()
        }
        
        # Risk contribution
        if len(positions) > 0 and len(asset_returns.columns) > 0:
            weights = np.array([positions.get(c, 0) for c in asset_returns.columns])
            weights = weights / weights.sum()
            risk_contrib = self.calculate_risk_contribution(weights, asset_returns.cov())
            report['risk_contribution'] = dict(zip(asset_returns.columns, risk_contrib))
        
        # Liquidity assessment
        for ticker, value in positions.items():
            report['liquidity'][ticker] = {
                'notional': value,
                'liquidity_risk': self.estimate_liquidity_risk(
                    avg_daily_volume=value * 0.1,  # Assume 10% ADV
                    position_size=value,
                    avg_daily_return=0.001
                )
            }
        
        # Generate recommendations
        risk_report = self.check_risk_limits(portfolio_value, positions, portfolio_returns)
        report['recommendations'] = risk_report.recommendations
        report['risk_score'] = risk_report.risk_score
        report['warnings'] = risk_report.warnings
        
        return report


# Convenience functions
def calculate_sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.02
) -> float:
    """Calculate Sharpe ratio"""
    annual_return = returns.mean() * 252
    annual_vol = returns.std() * np.sqrt(252)
    return (annual_return - risk_free_rate) / annual_vol if annual_vol > 0 else 0


def calculate_sortino_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.02
) -> float:
    """Calculate Sortino ratio (uses downside deviation)"""
    annual_return = returns.mean() * 252
    downside = returns[returns < 0]
    downside_vol = downside.std() * np.sqrt(252) if len(downside) > 0 else 1e-10
    return (annual_return - risk_free_rate) / downside_vol if downside_vol > 0 else 0


def calculate_calmar_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.02
) -> float:
    """Calculate Calmar ratio (return / max drawdown)"""
    annual_return = returns.mean() * 252
    
    cumulative = (1 + returns).cumprod()
    peak = cumulative.expanding().max()
    drawdown = (cumulative - peak) / peak
    max_dd = abs(drawdown.min())
    
    return annual_return / max_dd if max_dd > 0 else 0


# Example usage
if __name__ == "__main__":
    import pandas as pd
    import numpy as np
    
    # Generate sample returns
    np.random.seed(42)
    n_days = 252
    n_assets = 5
    
    # Create correlated returns
    base_returns = np.random.randn(n_days, 1) * 0.01
    asset_returns = pd.DataFrame(
        base_returns + np.random.randn(n_days, n_assets) * 0.02,
        columns=['AAPL', 'GOOG', 'MSFT', 'AMZN', 'META']
    )
    
    portfolio_returns = asset_returns.mean(axis=1)
    
    # Initialize risk framework
    risk_framework = RiskManagementFramework(initial_capital=1000000)
    
    # Add risk limits
    risk_framework.add_risk_limit(RiskMetric.VAR, 0.02, warning_threshold=0.015)
    risk_framework.add_risk_limit(RiskMetric.MAX_DRAWDOWN, 0.20)
    
    # Generate comprehensive report
    positions = {'AAPL': 200000, 'GOOG': 150000, 'MSFT': 250000, 'AMZN': 200000, 'META': 200000}
    
    report = risk_framework.generate_comprehensive_risk_report(
        portfolio_returns=portfolio_returns,
        asset_returns=asset_returns,
        portfolio_value=1000000,
        positions=positions
    )
    
    print("Risk Management Report")
    print("=" * 60)
    print(f"Portfolio Value: ${report['portfolio_value']:,.0f}")
    print(f"\nVaR (95%): ${report['var']['95%']:,.0f}")
    print(f"CVaR (95%): ${report['cvar']['95%']:,.0f}")
    print(f"Max Drawdown: {report['drawdown']['max_drawdown']:.2%}")
    print(f"Risk Score: {report['risk_score']}/100")
    
    print("\nStress Test Results:")
    for scenario, results in report['stress_test'].items():
        print(f"  {scenario}: Return={results['expected_return']:.2%}, VaR={results['var_95']:.2%}")
    
    print("\nRisk Contribution:")
    for asset, contrib in report['risk_contribution'].items():
        print(f"  {asset}: {contrib:.2%}")
    
    print("\nRecommendations:")
    for rec in report['recommendations']:
        print(f"  - {rec}")
