"""Risk Management Engine for Quant-Nanggroe-AI.

Provides comprehensive risk management with CONSTITUTIONAL limits that
CANNOT be overridden by any agent:

- Max 0.5% risk per trade
- Max 1% daily loss
- Max 3% weekly loss
- Max 15% maximum drawdown

Includes:
- 9-checkpoint risk gate (from HermesQuantOS)
- Kelly Criterion (4 variants)
- Value at Risk (parametric, historical, Monte Carlo)
- Risk Parity optimization
- Position sizing algorithms
- Drawdown monitoring (CVaR as primary metric)
- Correlation monitoring
- Kill switch for emergency halt

Extracted from HermesQuantOS's Risk Officer and ai-hedge-fund's risk modules.
"""

# Import constants first (no circular dependency)
from quant_nanggroe.engine.risk.constants import *

# Lazy imports to avoid circular dependencies
def __getattr__(name: str):
    """Lazy import to break circular dependencies."""
    _lazy_imports = {
        "RiskManager": ".manager",
        "KellyCriterion": ".kelly",
        "KellyMethod": ".kelly",
        "VaRCalculator": ".var",
        "RiskParityOptimizer": ".risk_parity",
        "PositionSizer": ".position_sizing",
        "DrawdownMonitor": ".drawdown",
        "CorrelationMonitor": ".correlation",
        "RiskCheckGate": ".checks",
        "KillSwitch": ".kill_switch",
        # Deflated Sharpe Ratio (Bailey & de Prado 2014)
        "DeflatedSharpeResult": ".deflated_sharpe",
        "OverfittingReport": ".deflated_sharpe",
        "deflated_sharpe_ratio": ".deflated_sharpe",
        "minimum_track_record_length": ".deflated_sharpe",
        "probability_of_backtest_overfitting": ".deflated_sharpe",
        "generate_overfitting_report": ".deflated_sharpe",
        # Risk of Ruin (Monte Carlo)
        "RiskOfRuinConfig": ".risk_of_ruin",
        "RiskOfRuinResult": ".risk_of_ruin",
        "RiskOfRuinReport": ".risk_of_ruin",
        "simulate_risk_of_ruin": ".risk_of_ruin",
        "kelly_risk_of_ruin": ".risk_of_ruin",
        "optimal_position_size": ".risk_of_ruin",
        "generate_risk_of_ruin_report": ".risk_of_ruin",
    }
    if name in _lazy_imports:
        import importlib
        module = importlib.import_module(_lazy_imports[name], __package__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "RiskManager",
    "KellyCriterion",
    "KellyMethod",
    "VaRCalculator",
    "RiskParityOptimizer",
    "PositionSizer",
    "DrawdownMonitor",
    "CorrelationMonitor",
    "RiskCheckGate",
    "KillSwitch",
    # Deflated Sharpe Ratio
    "DeflatedSharpeResult",
    "OverfittingReport",
    "deflated_sharpe_ratio",
    "minimum_track_record_length",
    "probability_of_backtest_overfitting",
    "generate_overfitting_report",
    # Risk of Ruin
    "RiskOfRuinConfig",
    "RiskOfRuinResult",
    "RiskOfRuinReport",
    "simulate_risk_of_ruin",
    "kelly_risk_of_ruin",
    "optimal_position_size",
    "generate_risk_of_ruin_report",
]
