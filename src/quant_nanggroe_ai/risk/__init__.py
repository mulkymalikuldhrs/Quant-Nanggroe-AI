"""
Risk Management Package — VaR, CVaR, Drawdown, Position Sizing
================================================================
"""

from quant_nanggroe_ai.risk.var import parametric_var, historical_var, monte_carlo_var
from quant_nanggroe_ai.risk.cvar import historical_cvar, parametric_cvar
from quant_nanggroe_ai.risk.drawdown import max_drawdown, current_drawdown, drawdown_duration
from quant_nanggroe_ai.risk.position_sizing import kelly_criterion_size, risk_parity_weights
from quant_nanggroe_ai.risk.portfolio_risk import portfolio_var, portfolio_correlation_risk

# Convenience aliases
VaR = parametric_var
CVaR = historical_cvar
drawdown = max_drawdown

__all__ = [
    # VaR
    "parametric_var",
    "historical_var",
    "monte_carlo_var",
    "VaR",
    # CVaR
    "historical_cvar",
    "parametric_cvar",
    "CVaR",
    # Drawdown
    "max_drawdown",
    "current_drawdown",
    "drawdown_duration",
    "drawdown",
    # Position Sizing
    "kelly_criterion_size",
    "risk_parity_weights",
    # Portfolio Risk
    "portfolio_var",
    "portfolio_correlation_risk",
]
