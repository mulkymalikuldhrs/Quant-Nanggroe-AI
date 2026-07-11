"""Portfolio optimizers for backtesting.

Provides weight optimization strategies for portfolio construction:
  - BaseOptimizer: Abstract base with rolling window support
  - RiskParityOptimizer: Equalize marginal risk contributions
  - MeanVarianceOptimizer: Maximize Sharpe ratio (long-only)
  - EqualVolatilityOptimizer: Inverse-volatility weighting

Ported from Vibe-Trading's optimizer architecture.
"""

from quant_nanggroe.engine.backtest.optimizers.base_optimizer import BaseOptimizer
from quant_nanggroe.engine.backtest.optimizers.equal_volatility_optimizer import (
    EqualVolatilityOptimizer,
)
from quant_nanggroe.engine.backtest.optimizers.mean_variance_optimizer import (
    MeanVarianceOptimizer,
)
from quant_nanggroe.engine.backtest.optimizers.risk_parity_optimizer import (
    RiskParityOptimizer,
)

__all__ = [
    "BaseOptimizer",
    "RiskParityOptimizer",
    "MeanVarianceOptimizer",
    "EqualVolatilityOptimizer",
]
