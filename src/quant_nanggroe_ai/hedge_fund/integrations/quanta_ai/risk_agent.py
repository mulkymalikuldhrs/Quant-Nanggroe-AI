"""
⚡ QUANTA AI - Risk Manager Agent
==================================
Advanced risk management with institutional-grade
VaR, CVaR, stress testing, and portfolio protection.

Features:
- Value at Risk (VaR) calculation
- Conditional VaR (CVaR)
- Maximum Drawdown monitoring
- Stress testing scenarios
- Position sizing optimization
- Correlation risk assessment

Author: Quanta AI Team
Version: 2.0.0
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from scipy import stats
from .base import BaseAgent, AgentMessage, MessageType, AgentState, AgentType
import logging


class RiskLevel(Enum):
    """Risk level classifications."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskMetrics:
    """Comprehensive risk metrics."""
    # VaR metrics
    var_95: float = 0.0
    var_99: float = 0.0
    cvar_95: float = 0.0
    cvar_99: float = 0.0
    
    # Drawdown metrics
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    recovery_days: int = 0
    
    # Return metrics
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    # Beta/Correlation
    beta: float = 1.0
    correlation_risk: float = 0.0
    
    # Concentration
    concentration_risk: float = 0.0
    largest_position: float = 0.0
    
    # Liquidity
    liquidity_risk: float = 0.0
    avg_spread: float = 0.0
    
    # Overall
    overall_risk_level: RiskLevel = RiskLevel.MEDIUM
    overall_score: float = 0.5
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'var_95': f"{self.var_95:.2%}",
            'var_99': f"{self.var_99:.2%}",
            'cvar_95': f"{self.cvar_95:.2%}",
            'max_drawdown': f"{self.max_drawdown:.2%}",
            'current_drawdown': f"{self.current_drawdown:.2%}",
            'volatility': f"{self.volatility:.2%}",
            'sharpe_ratio': f"{self.sharpe_ratio:.2f}",
            'sortino_ratio': f"{self.sortino_ratio:.2f}",
            'beta': f"{self.beta:.2f}",
            'concentration_risk': f"{self.concentration_risk:.2%}",
            'largest_position': f"{self.largest_position:.2%}",
            'overall_risk_level': self.overall_risk_level.value,
            'overall_score': f"{self.overall_score:.2f}"
        }


@dataclass
class RiskAlert:
    """Risk alert with details."""
    alert_type: str
    level: str  # warning, critical, info
    message: str
    action: str
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.alert_type,
            'level': self.level,
            'message': self.message,
            'action': self.action,
            'timestamp': self.timestamp.isoformat(),
            'acknowledged': self.acknowledged
        }


class RiskAgent(BaseAgent):
    """Agent responsible for comprehensive risk management."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(
            agent_id="quanta_risk_001",
            name="Risk Manager",
            agent_type=AgentType.RISK
        )
        self.capabilities = [
            "var_calculation",
            "cvar_calculation",
            "drawdown_monitoring",
            "concentration_check",
            "liquidity_assessment",
            "stress_testing",
            "risk_alerts",
            "position_sizing",
            "correlation_risk"
        ]
        self.config = config or {
            'var_confidence': 0.95,
            'max_drawdown_limit': 0.15,
            'max_position_size': 0.25,
            'max_correlation': 0.8,
            'liquidity_threshold': 0.01,
            'risk_level': 'moderate'
        }
        self.portfolio_history: List[Dict[str, Any]] = []
        self.current_risk: RiskMetrics = RiskMetrics()
        self.active_alerts: List[RiskAlert] = []
        self.alert_history: List[RiskAlert] = []
        
    def _initialize_impl(self) -> bool:
        """Initialize risk agent."""
        self.logger.info("Risk Manager initializing...")
        self.subscribe(MessageType.RISK_ASSESSMENT)
        self.subscribe(MessageType.RISK_ALERT)
        self.subscribe(MessageType.ORDER_REQUEST)
        self.logger.info("Risk Manager initialized")
        return True
    
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute risk assessment task."""
        task_type = task.get('type', 'assess')
        
        if task_type == 'assess':
            return self._assess_portfolio_risk(task)
        elif task_type == 'check_position':
            return self._check_position_risk(task)
        elif task_type == 'validate_trade':
            return self._validate_trade(task)
        elif task_type == 'stress_test':
            return self._stress_test(task)
        elif task_type == 'calculate_var':
            return self._calculate_var(task)
        elif task_type == 'position_sizing':
            return self._calculate_position_size(task)
        elif task_type == 'correlation_risk':
            return self._assess_correlation_risk(task)
        elif task_type == 'get_alerts':
            return self._get_active_alerts(task)
        else:
            return {
                'status': 'error',
                'message': f'Unknown task type: {task_type}',
                'task_type': task_type
            }
    
    def _assess_portfolio_risk(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall portfolio risk."""
        positions = task.get('positions', [])
        historical_pnl = task.get('historical_pnl', [])
        correlations = task.get('correlations', {})
        benchmark_returns = task.get('benchmark_returns', [])
        
        risk = RiskMetrics()
        
        # Calculate VaR using multiple methods
        if len(historical_pnl) >= 30:
            returns = np.array(historical_pnl)
            
            # Historical VaR
            risk.var_95 = np.percentile(returns, 5)
            risk.var_99 = np.percentile(returns, 1)
            
            # CVaR (Expected Shortfall)
            var_95_idx = int(len(returns) * 0.05)
            risk.cvar_95 = np.mean(returns[:var_95_idx])
            
            var_99_idx = int(len(returns) * 0.01)
            risk.cvar_99 = np.mean(returns[:var_99_idx])
            
            # Volatility (annualized)
            daily_vol = np.std(returns)
            risk.volatility = daily_vol * np.sqrt(252)
            
            # Sharpe Ratio
            mean_return = np.mean(returns)
            if risk.volatility > 0:
                risk.sharpe_ratio = (mean_return / risk.volatility) * np.sqrt(252)
            
            # Sortino Ratio (downside deviation)
            negative_returns = returns[returns < 0]
            if len(negative_returns) > 0:
                downside_vol = np.std(negative_returns) * np.sqrt(252)
                if downside_vol > 0:
                    risk.sortino_ratio = (mean_return * 252) / downside_vol
            
            # Calmar Ratio
            if risk.max_drawdown > 0:
                risk.calmar_ratio = (mean_return * 252) / risk.max_drawdown
        
        # Calculate drawdown
        if len(historical_pnl) > 0:
            cumulative = np.cumsum(historical_pnl)
            running_max = np.maximum.accumulate(cumulative)
            drawdowns = (cumulative - running_max) / (running_max + 1e-10)
            risk.max_drawdown = abs(np.min(drawdowns))
            risk.current_drawdown = abs(drawdowns[-1] if len(drawdowns) > 0 else 0)
            
            # Recovery days
            if risk.current_drawdown > 0:
                risk.recovery_days = self._estimate_recovery_days(drawdowns)
        
        # Calculate beta (market correlation)
        if len(benchmark_returns) >= 30:
            cov = np.cov(historical_pnl[-30:], benchmark_returns[-30:])[0][1]
            bench_var = np.var(benchmark_returns[-30:])
            if bench_var > 0:
                risk.beta = cov / bench_var
        
        # Calculate concentration risk
        if positions:
            weights = np.array([p.get('weight', 0) for p in positions])
            risk.concentration_risk = np.sum(weights ** 2)
            risk.largest_position = np.max(weights)
        
        # Calculate correlation risk
        if correlations:
            corr_values = list(correlations.values())
            risk.correlation_risk = np.mean(corr_values) if corr_values else 0
        
        # Determine overall risk level
        risk.overall_risk_level = self._calculate_overall_risk(risk)
        risk.overall_score = self._calculate_risk_score(risk)
        
        self.current_risk = risk
        
        # Generate alerts
        alerts = self._generate_risk_alerts(risk, positions)
        self.active_alerts = alerts
        self.alert_history.extend(alerts)
        
        return {
            'status': 'success',
            'risk_metrics': risk.to_dict(),
            'alerts': [a.to_dict() for a in alerts],
            'timestamp': datetime.now().isoformat()
        }
    
    def _estimate_recovery_days(self, drawdowns: np.ndarray) -> int:
        """Estimate days to recovery from drawdown."""
        in_drawdown = False
        recovery_count = 0
        
        for i in range(len(drawdowns)):
            if drawdowns[i] < 0:
                in_drawdown = True
            elif in_drawdown and drawdowns[i] >= 0:
                recovery_count = i
                break
        
        return recovery_count
    
    def _calculate_overall_risk(self, risk: RiskMetrics) -> RiskLevel:
        """Calculate overall risk level from metrics."""
        score = 0
        
        # Drawdown contribution (0-3 points)
        if risk.max_drawdown > 0.25:
            score += 3
        elif risk.max_drawdown > 0.20:
            score += 2
        elif risk.max_drawdown > 0.15:
            score += 1
        
        # VaR contribution (0-3 points)
        if abs(risk.var_95) > 0.04:
            score += 3
        elif abs(risk.var_95) > 0.025:
            score += 2
        elif abs(risk.var_95) > 0.015:
            score += 1
        
        # Volatility contribution (0-2 points)
        if risk.volatility > 0.40:
            score += 2
        elif risk.volatility > 0.30:
            score += 1
        
        # Concentration contribution (0-2 points)
        if risk.concentration_risk > 0.5:
            score += 2
        elif risk.concentration_risk > 0.3:
            score += 1
        
        # Sharpe ratio (inverted, 0-2 points)
        if risk.sharpe_ratio < 0:
            score += 2
        elif risk.sharpe_ratio < 1:
            score += 1
        
        # Beta contribution (0-2 points)
        if risk.beta > 1.5:
            score += 2
        elif risk.beta > 1.2:
            score += 1
        
        if score >= 12:
            return RiskLevel.CRITICAL
        elif score >= 8:
            return RiskLevel.HIGH
        elif score >= 4:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _calculate_risk_score(self, risk: RiskMetrics) -> float:
        """Calculate normalized risk score (0-1)."""
        score = 0
        
        # Normalize each component to 0-1 scale
        dd_score = min(risk.max_drawdown / 0.25, 1)
        var_score = min(abs(risk.var_95) / 0.05, 1)
        vol_score = min(risk.volatility / 0.50, 1)
        conc_score = min(risk.concentration_risk / 0.6, 1)
        beta_score = min(max(risk.beta - 1, 0) / 1.0, 1)
        
        # Weighted average
        weights = {'dd': 0.25, 'var': 0.25, 'vol': 0.20, 'conc': 0.15, 'beta': 0.15}
        score = (dd_score * weights['dd'] + 
                var_score * weights['var'] + 
                vol_score * weights['vol'] + 
                conc_score * weights['conc'] + 
                beta_score * weights['beta'])
        
        return score
    
    def _generate_risk_alerts(self, risk: RiskMetrics, 
                             positions: List[Dict]) -> List[RiskAlert]:
        """Generate risk alerts based on current metrics."""
        alerts = []
        
        # Drawdown alert
        if risk.current_drawdown > self.config.get('max_drawdown_limit', 0.15):
            alerts.append(RiskAlert(
                alert_type='drawdown',
                level='warning',
                message=f"Current drawdown {risk.current_drawdown:.2%} exceeds limit",
                action="Consider reducing exposure or stopping new positions"
            ))
        
        # Maximum drawdown alert
        if risk.max_drawdown > 0.20:
            alerts.append(RiskAlert(
                alert_type='max_drawdown',
                level='critical',
                message=f"Maximum drawdown reached {risk.max_drawdown:.2%}",
                action="Implement circuit breaker, reduce risk exposure"
            ))
        
        # VaR alert
        if abs(risk.var_95) > 0.025:
            alerts.append(RiskAlert(
                alert_type='var',
                level='warning',
                message=f"VaR 95% is {risk.var_95:.2%} - High risk exposure",
                action="Monitor positions closely, consider hedging"
            ))
        
        # Volatility alert
        if risk.volatility > 0.35:
            alerts.append(RiskAlert(
                alert_type='volatility',
                level='warning',
                message=f"Portfolio volatility is high: {risk.volatility:.2%}",
                action="Consider reducing position sizes"
            ))
        
        # Concentration alert
        if risk.concentration_risk > 0.4:
            top_position = max(positions, key=lambda p: p.get('weight', 0), default={})
            symbol = top_position.get('symbol', 'N/A')
            alerts.append(RiskAlert(
                alert_type='concentration',
                level='info',
                message=f"High concentration: {symbol} at {top_position.get('weight', 0):.2%}",
                action="Consider diversifying"
            ))
        
        # Beta alert
        if risk.beta > 1.5:
            alerts.append(RiskAlert(
                alert_type='beta',
                level='warning',
                message=f"High beta ({risk.beta:.2f}) - Market sensitive",
                action="Consider reducing market exposure"
            ))
        
        # Correlation alert
        if risk.correlation_risk > 0.7:
            alerts.append(RiskAlert(
                alert_type='correlation',
                level='warning',
                message=f"High average correlation ({risk.correlation_risk:.2f})",
                action="Diversify across uncorrelated assets"
            ))
        
        return alerts
    
    def _check_position_risk(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Check risk for a specific position."""
        symbol = task.get('symbol', '')
        position_size = task.get('position_size', 0)
        current_price = task.get('current_price', 0)
        portfolio_value = task.get('portfolio_value', 100000)
        
        weight = position_size * current_price / portfolio_value
        
        # Position risk score
        risk_score = 0
        
        # Size risk
        if weight > 0.20:
            risk_score += 0.4
        elif weight > 0.10:
            risk_score += 0.2
        
        # VaR contribution
        var_contribution = weight * abs(self.current_risk.var_95) if self.current_risk.var_95 else 0
        risk_score += min(var_contribution * 5, 0.3)
        
        # Concentration
        if self.current_risk.largest_position > 0.15:
            risk_score += 0.1
        
        risk_score = min(risk_score, 1.0)
        
        # Recommendation
        if risk_score > 0.7:
            recommendation = 'REDUCE'
        elif risk_score > 0.4:
            recommendation = 'HOLD'
        else:
            recommendation = 'OK'
        
        return {
            'status': 'success',
            'position_risk': {
                'symbol': symbol,
                'weight': float(weight),
                'var_contribution': float(var_contribution),
                'risk_score': float(risk_score),
                'recommendation': recommendation
            }
        }
    
    def _validate_trade(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a proposed trade against risk limits."""
        trade = task.get('trade', {})
        current_positions = task.get('positions', [])
        portfolio_value = task.get('portfolio_value', 100000)
        
        symbol = trade.get('symbol', '')
        side = trade.get('side', 'buy')
        size = trade.get('size', 0)
        price = trade.get('price', 0)
        
        # Calculate new position weight
        trade_value = size * price
        new_weight = trade_value / portfolio_value
        
        if side.lower() == 'buy':
            final_weight = new_weight
        elif side.lower() == 'sell':
            final_weight = -new_weight  # Short position
        else:
            final_weight = 0
        
        # Get current weight
        current_weight = 0
        for pos in current_positions:
            if pos.get('symbol') == symbol:
                current_weight = pos.get('weight', 0)
                break
        
        max_position = self.config.get('max_position_size', 0.25)
        
        validation_passed = True
        reasons = []
        
        # Check position limit
        if final_weight > max_position:
            validation_passed = False
            reasons.append(f"Position size {final_weight:.2%} exceeds limit {max_position:.2%}")
        
        # Check drawdown limit
        if self.current_risk.current_drawdown > self.config.get('max_drawdown_limit', 0.15):
            validation_passed = False
            reasons.append("Portfolio is in maximum drawdown period")
        
        # Check VaR limit
        if abs(self.current_risk.var_95) > 0.03 and side.lower() == 'buy':
            validation_passed = False
            reasons.append("High VaR - avoiding new long positions")
        
        # Check correlation limit
        if self.current_risk.correlation_risk > 0.8:
            validation_passed = False
            reasons.append("High portfolio correlation - reducing new positions")
        
        # Calculate adjusted risk metrics
        new_var = self.current_risk.var_95 * (1 + final_weight * 0.5)
        
        return {
            'status': 'success',
            'validation': {
                'passed': validation_passed,
                'reasons': reasons,
                'new_weight': float(final_weight),
                'current_weight': float(current_weight),
                'estimated_var_impact': float(new_var - self.current_risk.var_95),
                'timestamp': datetime.now().isoformat()
            }
        }
    
    def _stress_test(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Run stress tests on portfolio."""
        positions = task.get('positions', [])
        scenarios = task.get('scenarios', [
            '2008_crisis', 'covid_crash', 'rate_shock', 'volatility_spike'
        ])
        
        results = {}
        total_weight = sum(p.get('weight', 0) for p in positions)
        
        scenario_impacts = {
            '2008_crisis': -0.45,
            'covid_crash': -0.35,
            'rate_shock': -0.20,
            'volatility_spike': -0.25,
            'flash_crash': -0.15,
            'liquidity_crisis': -0.30,
            'tech_crash': -0.40,
            'inflation_shock': -0.25
        }
        
        for scenario in scenarios:
            impact = scenario_impacts.get(scenario, -0.20)
            
            # Adjust for portfolio composition
            portfolio_impact = impact * min(total_weight, 1.0)
            
            # Calculate estimated loss
            portfolio_value = task.get('portfolio_value', 100000)
            estimated_loss = abs(portfolio_impact * portfolio_value)
            
            # Stress VaR
            stressed_var = abs(self.current_risk.var_95) * abs(impact) * 2
            
            results[scenario] = {
                'shock': f"{impact:.0%}",
                'estimated_impact': f"{portfolio_impact:.2%}",
                'portfolio_loss': float(estimated_loss),
                'stressed_var': f"{stressed_var:.2%}" if stressed_var else 'N/A',
                'severity': 'critical' if abs(impact) > 0.35 else 'high' if abs(impact) > 0.25 else 'moderate'
            }
        
        # Calculate worst case
        worst_scenario = min(results, key=lambda x: float(results[x]['estimated_impact']))
        
        return {
            'status': 'success',
            'stress_test_results': results,
            'worst_case': {
                'scenario': worst_scenario,
                'impact': results[worst_scenario]['estimated_impact'],
                'loss': results[worst_scenario]['portfolio_loss']
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_var(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate Value at Risk."""
        returns = task.get('returns', [])
        confidence = task.get('confidence', 0.95)
        method = task.get('method', 'historical')
        
        if len(returns) < 30:
            return {
                'status': 'error',
                'message': 'Insufficient data for VaR calculation (need 30+ points)'
            }
        
        returns_array = np.array(returns)
        
        # Historical VaR
        var = np.percentile(returns_array, (1 - confidence) * 100)
        
        # CVaR
        var_idx = int(len(returns_array) * (1 - confidence))
        cvar = np.mean(returns_array[:var_idx])
        
        # Parametric VaR (normal distribution)
        mu = np.mean(returns_array)
        sigma = np.std(returns_array)
        z_score = stats.norm.ppf(1 - confidence)
        parametric_var = mu + sigma * z_score
        
        return {
            'status': 'success',
            'var': float(var),
            'cvar': float(cvar),
            'parametric_var': float(parametric_var),
            'confidence': confidence,
            'method': method,
            'sample_size': len(returns),
            'volatility_daily': float(sigma),
            'volatility_annual': float(sigma * np.sqrt(252)),
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_position_size(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate optimal position size."""
        portfolio_value = task.get('portfolio_value', 100000)
        stop_loss = task.get('stop_loss', 0.05)
        risk_tolerance = task.get('risk_tolerance', 0.02)
        confidence = task.get('confidence', 0.5)
        volatility = task.get('volatility', 0.02)
        
        # Risk amount
        risk_amount = portfolio_value * risk_tolerance
        
        # Position size based on stop loss
        position_size_sl = risk_amount / stop_loss if stop_loss > 0 else 0
        
        # Position size based on Kelly Criterion (simplified)
        win_rate = task.get('win_rate', 0.55)
        reward_risk = task.get('reward_risk', 2.0)
        
        kelly_fraction = (win_rate * reward_risk - (1 - win_rate)) / reward_risk
        kelly_size = max(0, kelly_fraction * 0.5)  # Half Kelly for safety
        
        # Volatility-adjusted size
        vol_size = 1 / (volatility * 3) * 0.1  # Target 1/3 ATR position
        
        # Combine methods
        final_size = min(position_size_sl * confidence, 
                        kelly_size * portfolio_value,
                        vol_size * portfolio_value)
        
        # Apply limits
        max_size = portfolio_value * self.config.get('max_position_size', 0.25)
        final_size = min(final_size, max_size)
        
        return {
            'status': 'success',
            'position_size': float(final_size),
            'position_weight': float(final_size / portfolio_value),
            'methods': {
                'stop_loss_based': float(position_size_sl),
                'kelly_based': float(kelly_size * portfolio_value),
                'volatility_based': float(vol_size * portfolio_value)
            },
            'risk_amount': float(risk_amount),
            'kelly_fraction': float(kelly_fraction),
            'timestamp': datetime.now().isoformat()
        }
    
    def _assess_correlation_risk(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Assess correlation risk in portfolio."""
        correlations = task.get('correlations', {})
        threshold = task.get('threshold', 0.8)
        
        high_corr_pairs = []
        correlation_matrix = {}
        
        for pair, corr in correlations.items():
            if abs(corr) > threshold:
                high_corr_pairs.append({
                    'pair': pair,
                    'correlation': float(corr),
                    'level': 'high' if abs(corr) > 0.9 else 'moderate'
                })
        
        # Calculate portfolio correlation average
        if correlations:
            avg_corr = np.mean(list(correlations.values()))
            max_corr = max(correlations.values())
        else:
            avg_corr = 0
            max_corr = 0
        
        return {
            'status': 'success',
            'correlation_risk': {
                'average_correlation': float(avg_corr),
                'maximum_correlation': float(max_corr),
                'high_correlation_pairs': high_corr_pairs,
                'pair_count': len(correlations),
                'high_risk_count': len(high_corr_pairs)
            },
            'recommendation': 'Diversify' if avg_corr > 0.6 else 'Monitor' if avg_corr > 0.4 else 'OK',
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_active_alerts(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Get active risk alerts."""
        include_acknowledged = task.get('include_acknowledged', False)
        alert_type = task.get('type', None)
        
        alerts = self.active_alerts
        
        if not include_acknowledged:
            alerts = [a for a in alerts if not a.acknowledged]
        
        if alert_type:
            alerts = [a for a in alerts if a.alert_type == alert_type]
        
        return {
            'status': 'success',
            'active_alerts': [a.to_dict() for a in alerts],
            'alert_count': len(alerts),
            'critical_count': len([a for a in alerts if a.level == 'critical']),
            'warning_count': len([a for a in alerts if a.level == 'warning'])
        }
    
    def acknowledge_alert(self, alert_type: str) -> bool:
        """Acknowledge an alert."""
        for alert in self.active_alerts:
            if alert.alert_type == alert_type:
                alert.acknowledged = True
                return True
        return False
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get current risk summary."""
        return {
            'overall_level': self.current_risk.overall_risk_level.value,
            'overall_score': self.current_risk.overall_score,
            'var_95': self.current_risk.var_95,
            'var_99': self.current_risk.var_99,
            'max_drawdown': self.current_risk.max_drawdown,
            'current_drawdown': self.current_risk.current_drawdown,
            'sharpe_ratio': self.current_risk.sharpe_ratio,
            'volatility': self.current_risk.volatility,
            'active_alerts': len(self.active_alerts),
            'concentration_risk': self.current_risk.concentration_risk
        }
    
    def _process_message(self, message: AgentMessage) -> bool:
        """Process incoming message."""
        if message.msg_type == MessageType.RISK_ASSESSMENT:
            task = message.payload
            result = self.execute(task)
            
            response = AgentMessage(
                msg_type=MessageType.DATA_RESPONSE,
                sender_id=self.agent_id,
                receiver_id=message.sender_id,
                payload=result,
                priority=message.priority,
                correlation_id=message.correlation_id
            )
            return self.send_message(response)
        
        elif message.msg_type == MessageType.RISK_ALERT:
            alert = RiskAlert(**message.payload)
            self.active_alerts.append(alert)
            self.alert_history.append(alert)
            self.logger.warning(f"Risk alert: {alert.message}")
        
        elif message.msg_type == MessageType.ORDER_REQUEST:
            # Validate trade before execution
            task = {'type': 'validate_trade', **message.payload}
            result = self.execute(task)
            
            if not result.get('validation', {}).get('passed', True):
                # Reject order
                response = AgentMessage(
                    msg_type=MessageType.RISK_ALERT,
                    sender_id=self.agent_id,
                    receiver_id=message.sender_id,
                    payload={
                        'alert_type': 'order_rejected',
                        'level': 'warning',
                        'message': 'Order rejected by risk manager',
                        'reasons': result.get('validation', {}).get('reasons', [])
                    }
                )
                return self.send_message(response)
        
        elif message.msg_type == MessageType.HEARTBEAT:
            self.heartbeat()
            self.state = AgentState.RUNNING
        
        return True
