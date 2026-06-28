"""Strategy performance analysis — factor regression & bootstrap inference.

Components:
    FactorModel  — Multi-factor OLS regression for returns attribution
    BootstrapCI  — Stationary bootstrap confidence intervals on Sharpe/alpha
"""

from quant_nanggroe.engine.analysis.factors import FactorModel, FactorResult
from quant_nanggroe.engine.analysis.bootstrap import BootstrapCI

__all__ = [
    "FactorModel",
    "FactorResult",
    "BootstrapCI",
]
