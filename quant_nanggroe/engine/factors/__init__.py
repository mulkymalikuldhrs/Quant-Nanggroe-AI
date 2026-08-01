"""
Factor analysis subpackage.

Exposes the Alphalens-compatible tear-sheet adapter (IC, quantile spread,
turnover) and the factor registry integration point.
"""

from quant_nanggroe.engine.factors.alphalens_adapter import (
    FactorData,
    factor_information_coefficient,
    factor_turnover,
    get_factor_panel,
    mean_information_coefficient,
    quantile_spread,
    run_tear_sheets,
    to_alphalens_factor_data,
)

__all__ = [
    "FactorData",
    "to_alphalens_factor_data",
    "factor_information_coefficient",
    "mean_information_coefficient",
    "quantile_spread",
    "factor_turnover",
    "get_factor_panel",
    "run_tear_sheets",
]
