"""Signal generation: core providers, MUE-X evolved strategies, provider registry, vote aggregation.

Re-exports all signal_* functions, provider lists, and the aggregate() function.
"""

from quant_nanggroe.hedge_fund.signals.core import (
    signal_sma, signal_wyckoff, signal_aihf, signal_hidden,
    signal_tradingagents, signal_aitrader, signal_langalpha,
    signal_aimarketmaker, signal_kronos, signal_pyportfolioopt,
)
from quant_nanggroe.hedge_fund.signals.registry import (
    CORE_PROVIDERS, QNA_EVOLVED_PROVIDERS, ALL_PROVIDERS,
)
from quant_nanggroe.hedge_fund.signals.aggregator import aggregate, _timeout_call

__all__ = [
    "signal_sma", "signal_wyckoff", "signal_aihf", "signal_hidden",
    "signal_tradingagents", "signal_aitrader", "signal_langalpha",
    "signal_aimarketmaker", "signal_kronos", "signal_pyportfolioopt",
    "CORE_PROVIDERS", "QNA_EVOLVED_PROVIDERS", "ALL_PROVIDERS",
    "aggregate", "_timeout_call",
]
