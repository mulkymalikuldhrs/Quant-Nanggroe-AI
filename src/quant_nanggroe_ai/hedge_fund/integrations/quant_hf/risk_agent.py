"""
🌟 ORCHID QUANTUM AI - Risk Agent
==================================
Specialized agent for risk management and monitoring.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from scipy import stats
from .base import BaseAgent, AgentMessage, MessageType, AgentState
import logging


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskMetrics:
    """Risk metrics for a portfolio."""
    var_95: float = 0.0
    var_99: float = 0.0
    cvar_95: float = 0.0
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    beta: float = 1.0
    correlation_risk: float = 0.0
    concentration_risk: float = 0.0
    liquidity_risk: float = 0.0
    overall_risk_level: RiskLevel = RiskLevel.MEDIUM


@dataclass
class PositionRisk:
    """Risk assessment for a single position."""
    symbol: str
    position_size: float
    var_contribution: float
    correlation_risk: float
    liquidity_score: float
    risk_score: float
    recommendation: str


class RiskAgent(BaseAgent):
    """Agent responsible for risk management and monitoring."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(
            agent_id="risk_agent_001",
            name="Risk Agent"
        )
        self.capabilities = [
            "var_calculation",
            "drawdown_monitoring",
            "concentration_check",
            "liquidity_assessment",
            "risk_alerts",
            "stress_testing"
        ]
        self.config = config or {
            'var_confidence': 0.95,
            'max_drawdown_limit': 0.15,
            'max_position_size': 0.25,
            'max_correlation': 0.8,
            'liquidity_threshold': 0.01
        }
        self.portfolio_history: List[Dict[str, Any]] = []
        self.current_risk: RiskMetrics = RiskMetrics()
        self.active_alerts: List[Dict[str, Any]] = []
        
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the risk agent."""
        self.config.update(config)
        self.logger.info("Risk Agent initialized")
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
        else:
            return {'status': 'error', 'message': f'Unknown task type: {task_type}'}
    
    def _assess_portfolio_risk(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall portfolio risk."""
        positions = task.get('positions', [])
        historical_pnl = task.get('historical_pnl', [])
        correlations = task.get('correlations', {})
        
        risk = RiskMetrics()
        
        # Calculate VaR
        if len(historical_pnl) > 30:
            returns = np.array(historical_pnl)
            risk.var_95 = np.percentile(returns, 5)
            risk.var_99 = np.percentile(returns, 1)
            risk.cvar_95 = np.mean(returns[returns <= risk.var_95])
            risk.volatility = np.std(returns) * np.sqrt(252)
            
            # Calculate Sharpe ratio
            mean_return = np.mean(returns)
            if risk.volatility > 0:
                risk.sharpe_ratio = (mean_return / risk.volatility) * np.sqrt(252)
        
        # Calculate drawdown
        if len(historical_pnl) > 0:
            cumulative = np.cumsum(historical_pnl)
            running_max = np.maximum.accumulate(cumulative)
            drawdowns = (cumulative - running_max) / (running_max + 1e-10)
            risk.max_drawdown = abs(np.min(drawdowns))
            risk.current_drawdown = abs(drawdowns[-1] if len(drawdowns) > 0 else 0)
        
        # Calculate concentration risk
        if positions:
            sizes = np.array([p.get('weight', 0) for p in positions])
            risk.concentration_risk = np.sum(sizes ** 2)
        
        # Calculate correlation risk
        if correlations:
            corr_values = list(correlations.values())
            risk.correlation_risk = np.mean(corr_values) if corr_values else 0
        
        # Determine overall risk level
        risk.overall_risk_level = self._calculate_overall_risk(risk)
        
        self.current_risk = risk
        
        # Check for alerts
        alerts = self._generate_risk_alerts(risk, positions)
        self.active_alerts = alerts
        
        return {
            'status': 'success',
            'risk_metrics': {
                'var_95': float(risk.var_95),
                'var_99': float(risk.var_99),
                'cvar_95': float(risk.cvar_95),
                'max_drawdown': float(risk.max_drawdown),
                'current_drawdown': float(risk.current_drawdown),
                'volatility': float(risk.volatility),
                'sharpe_ratio': float(risk.sharpe_ratio),
                'concentration_risk': float(risk.concentration_risk),
                'correlation_risk': float(risk.correlation_risk),
                'overall_risk_level': risk.overall_risk_level.value
            },
            'alerts': alerts,
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_overall_risk(self, risk: RiskMetrics) -> RiskLevel:
        """Calculate overall risk level from metrics."""
        score = 0
        
        # Drawdown contribution
        if risk.max_drawdown > 0.20:
            score += 3
        elif risk.max_drawdown > 0.15:
            score += 2
        elif risk.max_drawdown > 0.10:
            score += 1
        
        # VaR contribution
        if abs(risk.var_95) > 0.03:
            score += 3
        elif abs(risk.var_95) > 0.02:
            score += 2
        elif abs(risk.var_95) > 0.01:
            score += 1
        
        # Volatility contribution
        if risk.volatility > 0.40:
            score += 3
        elif risk.volatility > 0.30:
            score += 2
        elif risk.volatility > 0.20:
            score += 1
        
        # Concentration contribution
        if risk.concentration_risk > 0.5:
            score += 2
        elif risk.concentration_risk > 0.3:
            score += 1
        
        # Sharpe ratio (lower is riskier)
        if risk.sharpe_ratio < 0:
            score += 3
        elif risk.sharpe_ratio < 1:
            score += 2
        elif risk.sharpe_ratio < 1.5:
            score += 1
        
        if score >= 10:
            return RiskLevel.CRITICAL
        elif score >= 7:
            return RiskLevel.HIGH
        elif score >= 4:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _generate_risk_alerts(self, risk: RiskMetrics, 
                             positions: List[Dict]) -> List[Dict[str, Any]]:
        """Generate risk alerts."""
        alerts = []
        
        # Drawdown alert
        if risk.current_drawdown > self.config.get('max_drawdown_limit', 0.15):
            alerts.append({
                'type': 'drawdown',
                'level': 'warning',
                'message': f"Current drawdown {risk.current_drawdown:.2%} exceeds limit",
                'action': 'Consider reducing exposure'
            })
        
        # VaR alert
        if abs(risk.var_95) > 0.02:
            alerts.append({
                'type': 'var',
                'level': 'warning',
                'message': f"VaR 95% is {risk.var_95:.2%}",
                'action': 'Monitor positions closely'
            })
        
        # Concentration alert
        if risk.concentration_risk > 0.3:
            top_position = max(positions, key=lambda p: p.get('weight', 0)) if positions else {}
            alerts.append({
                'type': 'concentration',
                'level': 'info',
                'message': f"High concentration risk: {top_position.get('symbol', 'N/A')}",
                'action': 'Consider diversifying'
            })
        
        # Volatility alert
        if risk.volatility > 0.30:
            alerts.append({
                'type': 'volatility',
                'level': 'warning',
                'message': f"Portfolio volatility is high: {risk.volatility:.2%}",
                'action': 'Consider reducing position sizes'
            })
        
        return alerts
    
    def _check_position_risk(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Check risk for a specific position."""
        symbol = task.get('symbol', '')
        position_size = task.get('position_size', 0)
        current_price = task.get('current_price', 0)
        portfolio_value = task.get('portfolio_value', 100000)
        
        weight = position_size * current_price / portfolio_value
        
        position_risk = PositionRisk(
            symbol=symbol,
            position_size=weight,
            var_contribution=weight * self.current_risk.var_95 if self.current_risk.var_95 else 0,
            correlation_risk=0.5,  # Simplified
            liquidity_score=0.8,
            risk_score=0.0,
            recommendation=''
        )
        
        # Calculate risk score
        risk_score = weight * 2  # Base risk from size
        risk_score += abs(position_risk.var_contribution) * 10
        risk_score += (1 - position_risk.liquidity_score) * 0.5
        risk_score += position_risk.correlation_risk * 0.3
        
        position_risk.risk_score = min(risk_score / 3, 1.0)
        
        # Generate recommendation
        if position_risk.risk_score > 0.7:
            position_risk.recommendation = 'REDUCE'
        elif position_risk.risk_score > 0.4:
            position_risk.recommendation = 'HOLD'
        else:
            position_risk.recommendation = 'OK'
        
        return {
            'status': 'success',
            'position_risk': {
                'symbol': position_risk.symbol,
                'weight': float(position_risk.position_size),
                'var_contribution': float(position_risk.var_contribution),
                'liquidity_score': float(position_risk.liquidity_score),
                'risk_score': float(position_risk.risk_score),
                'recommendation': position_risk.recommendation
            }
        }
    
    def _validate_trade(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a proposed trade."""
        trade = task.get('trade', {})
        current_positions = task.get('positions', [])
        
        symbol = trade.get('symbol', '')
        side = trade.get('side', 'buy')
        size = trade.get('size', 0)
        price = trade.get('price', 0)
        
        portfolio_value = task.get('portfolio_value', 100000)
        new_weight = size * price / portfolio_value
        
        # Get current weight
        current_weight = 0
        for pos in current_positions:
            if pos.get('symbol') == symbol:
                current_weight = pos.get('weight', 0)
                break
        
        if side == 'buy':
            final_weight = current_weight + new_weight
        else:
            final_weight = current_weight - new_weight
        
        # Check limits
        max_position = self.config.get('max_position_size', 0.25)
        validation_passed = True
        reasons = []
        
        if final_weight > max_position:
            validation_passed = False
            reasons.append(f"Position size {final_weight:.2%} exceeds limit {max_position:.2%}")
        
        # Check if trade would exceed drawdown
        if self.current_risk.current_drawdown > self.config.get('max_drawdown_limit', 0.15):
            validation_passed = False
            reasons.append("Portfolio is in maximum drawdown")
        
        # Check VaR impact (simplified)
        if abs(self.current_risk.var_95) > 0.02:
            if side == 'buy':
                validation_passed = False
                reasons.append("High VaR, avoiding new long positions")
        
        return {
            'status': 'success',
            'validation': {
                'passed': validation_passed,
                'reasons': reasons,
                'new_weight': float(final_weight),
                'current_weight': float(current_weight)
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def _stress_test(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Run stress tests."""
        positions = task.get('positions', [])
        scenarios = task.get('scenarios', [
            '2008_crisis',
            'covid_crash',
            'rate_shock'
        ])
        
        results = {}
        
        for scenario in scenarios:
            if scenario == '2008_crisis':
                shock = -0.40  # 40% drop
            elif scenario == 'covid_crash':
                shock = -0.30  # 30% drop
            elif scenario == 'rate_shock':
                shock = -0.20  # 20% drop
            elif isinstance(scenario, dict):
                shock = scenario.get('shock', -0.20)
            else:
                shock = -0.20
            
            # Calculate impact
            total_exposure = sum(p.get('weight', 0) for p in positions)
            impact = total_exposure * shock
            
            results[scenario] = {
                'shock': shock,
                'estimated_impact': float(impact),
                'portfolio_loss': float(abs(impact) * 100000)  # Assuming $100k portfolio
            }
        
        return {
            'status': 'success',
            'stress_test_results': results,
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_var(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate Value at Risk."""
        returns = task.get('returns', [])
        confidence = task.get('confidence', 0.95)
        
        if len(returns) < 30:
            return {
                'status': 'error',
                'message': 'Insufficient data for VaR calculation'
            }
        
        returns_array = np.array(returns)
        var = np.percentile(returns_array, (1 - confidence) * 100)
        cvar = np.mean(returns_array[returns_array <= var])
        
        return {
            'status': 'success',
            'var': float(var),
            'cvar': float(cvar),
            'confidence': confidence,
            'sample_size': len(returns),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get current risk summary."""
        return {
            'overall_level': self.current_risk.overall_risk_level.value,
            'var_95': float(self.current_risk.var_95),
            'var_99': float(self.current_risk.var_99),
            'max_drawdown': float(self.current_risk.max_drawdown),
            'current_drawdown': float(self.current_risk.current_drawdown),
            'sharpe_ratio': float(self.current_risk.sharpe_ratio),
            'volatility': float(self.current_risk.volatility),
            'active_alerts': len(self.active_alerts)
        }
    
    def _process_message(self, message: AgentMessage) -> None:
        """Process incoming message."""
        if message.msg_type == MessageType.RISK_ALERT:
            # Handle risk alert
            alert = message.payload
            self.active_alerts.append(alert)
            self.logger.warning(f"Risk alert received: {alert.get('message', 'Unknown')}")
        
        elif message.msg_type == MessageType.HEARTBEAT:
            self.heartbeat()
            self.state = AgentState.RUNNING
