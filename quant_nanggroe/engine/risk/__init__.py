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
]
