"""Risk Management Engine for Quant-Nanggroe-AI.

Provides comprehensive risk management with CONSTITUTIONAL limits that
CANNOT be overridden by any agent:

- Max 0.5% risk per trade
- Max 1% daily loss
- Max 3% weekly loss
- Max 10% maximum drawdown

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

from quant_nanggroe.engine.risk.manager import RiskManager
from quant_nanggroe.engine.risk.kelly import KellyCriterion, KellyMethod
from quant_nanggroe.engine.risk.var import VaRCalculator
from quant_nanggroe.engine.risk.risk_parity import RiskParityOptimizer
from quant_nanggroe.engine.risk.position_sizing import PositionSizer
from quant_nanggroe.engine.risk.drawdown import DrawdownMonitor
from quant_nanggroe.engine.risk.correlation import CorrelationMonitor
from quant_nanggroe.engine.risk.checks import RiskCheckGate
from quant_nanggroe.engine.risk.kill_switch import KillSwitch

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
