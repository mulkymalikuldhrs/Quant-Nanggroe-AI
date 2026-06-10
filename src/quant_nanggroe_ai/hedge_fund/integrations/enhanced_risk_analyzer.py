"""
ENHANCED RISK ANALYZER - Integrates FinceptTerminal risk management
Combines advanced risk metrics with kill-switch protection
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class EnhancedRiskAnalyzer:
    """Enhanced risk analyzer using FinceptTerminal components"""

    def __init__(self):
        self.risk_analyzer = None
        self.performance_metrics = None
        self.kill_switch_active = False
        self.initialized = False
        self.risk_limits = {"max_drawdown": 0.20, "max_var": 0.15, "max_volatility": 0.30}  # 20%  # 15%  # 30%

    def initialize(self):
        """Initialize risk analysis components"""
        try:
            from integrations.fincept_terminal.alternateInvestment.risk_analyzer import RiskAnalyzer
            from integrations.fincept_terminal.alternateInvestment.performance_metrics import PerformanceMetrics

            self.risk_analyzer = RiskAnalyzer()
            self.performance_metrics = PerformanceMetrics()

            print("✅ Enhanced Risk Analyzer initialized")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize risk analyzer: {e}")
            # Fallback to basic implementation
            self.risk_analyzer = None
            self.performance_metrics = None
            return False

    def analyze_portfolio_risk(self, portfolio, market_data):
        """Analyze comprehensive portfolio risk"""
        if self.risk_analyzer and hasattr(self.risk_analyzer, "analyze_portfolio"):
            return self.risk_analyzer.analyze_portfolio(portfolio, market_data)
        else:
            # Basic risk analysis
            positions_value = sum(qty * market_data.get(ticker, {}).get("price", 0) for ticker, qty in portfolio.get("positions", {}).items())

            # Calculate basic metrics
            total_value = portfolio.get("cash", 0) + positions_value
            volatility = self._calculate_portfolio_volatility(portfolio, market_data)
            var_95 = volatility * 1.645  # 95% VaR approximation

            return {"total_value": total_value, "positions_value": positions_value, "volatility": volatility, "var_95": var_95, "max_drawdown": self._calculate_max_drawdown(portfolio), "risk_score": self._calculate_risk_score(volatility, var_95)}

    def calculate_performance_metrics(self, returns_data):
        """Calculate advanced performance metrics"""
        if self.performance_metrics and hasattr(self.performance_metrics, "calculate_metrics"):
            return self.performance_metrics.calculate_metrics(returns_data)
        else:
            # Basic performance metrics
            if not returns_data:
                return {"sharpe_ratio": 0, "sortino_ratio": 0, "max_drawdown": 0}

            returns = [r for r in returns_data if r is not None]
            if not returns:
                return {"sharpe_ratio": 0, "sortino_ratio": 0, "max_drawdown": 0}

            avg_return = sum(returns) / len(returns)
            volatility = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5

            # Sharpe ratio (assuming 2% risk-free rate)
            risk_free_rate = 0.02 / 252  # Daily risk-free rate
            sharpe = (avg_return - risk_free_rate) / volatility if volatility > 0 else 0

            # Sortino ratio (downside deviation)
            downside_returns = [r for r in returns if r < risk_free_rate]
            downside_volatility = (sum((r - risk_free_rate) ** 2 for r in downside_returns) / max(len(downside_returns), 1)) ** 0.5
            sortino = (avg_return - risk_free_rate) / downside_volatility if downside_volatility > 0 else 0

            return {"sharpe_ratio": sharpe, "sortino_ratio": sortino, "volatility": volatility, "avg_return": avg_return}

    def check_kill_switch(self, portfolio_metrics):
        """Check if kill switch should be activated"""
        if self.kill_switch_active:
            return True

        # Check risk limits
        if portfolio_metrics.get("max_drawdown", 0) > self.risk_limits["max_drawdown"]:
            self.kill_switch_active = True
            print("🚨 KILL SWITCH ACTIVATED: Max drawdown exceeded")
            return True

        if portfolio_metrics.get("var_95", 0) > self.risk_limits["max_var"]:
            self.kill_switch_active = True
            print("🚨 KILL SWITCH ACTIVATED: VaR limit exceeded")
            return True

        if portfolio_metrics.get("volatility", 0) > self.risk_limits["max_volatility"]:
            self.kill_switch_active = True
            print("🚨 KILL SWITCH ACTIVATED: Volatility limit exceeded")
            return True

        return False

    def _calculate_portfolio_volatility(self, portfolio, market_data):
        """Calculate portfolio volatility"""
        # Simplified volatility calculation
        positions = portfolio.get("positions", {})
        if not positions:
            return 0.0

        # Assume 20% annual volatility for each position (simplified)
        position_weights = []
        for ticker, qty in positions.items():
            price = market_data.get(ticker, {}).get("price", 100)
            weight = (qty * price) / (portfolio.get("cash", 0) + sum(q * market_data.get(t, {}).get("price", 100) for t, q in positions.items()))
            position_weights.append(weight)

        # Portfolio volatility (simplified weighted average)
        avg_volatility = 0.20  # 20% annual
        portfolio_vol = sum(w * avg_volatility for w in position_weights)

        return portfolio_vol

    def _calculate_max_drawdown(self, portfolio):
        """Calculate maximum drawdown"""
        # Simplified max drawdown calculation
        # In real implementation, this would use historical portfolio values
        return 0.05  # 5% placeholder

    def _calculate_risk_score(self, volatility, var):
        """Calculate overall risk score (0-100)"""
        # Normalize risk metrics to 0-100 scale
        vol_score = min(volatility * 100 / 0.50, 100)  # Max expected vol 50%
        var_score = min(var * 100 / 0.25, 100)  # Max expected VaR 25%

        return (vol_score + var_score) / 2

    def reset_kill_switch(self):
        """Reset kill switch (manual intervention required)"""
        self.kill_switch_active = False
        print("🔄 Kill switch reset - manual intervention required")


# Global instance
enhanced_risk_analyzer = EnhancedRiskAnalyzer()
