"""Signal generation: core providers, MUE-X evolved strategies, provider registry, vote aggregation.

Re-exports all signal_* functions, provider lists, and the aggregate() function.
"""

from quant_nanggroe.hedge_fund.signals.aggregator import aggregate
from quant_nanggroe.hedge_fund.signals.core import (
    signal_aihf,
    signal_aimarketmaker,
    signal_aitrader,
    signal_hidden,
    signal_kronos,
    signal_langalpha,
    signal_pyportfolioopt,
    signal_sma,
    signal_tradingagents,
    signal_wyckoff,
)
from quant_nanggroe.hedge_fund.signals.engine_strategies import (
    ENGINE_STRATEGY_PROVIDERS,
    EngineStrategyProvider,
)
from quant_nanggroe.hedge_fund.signals.registry import (
    ALL_PROVIDERS,
    CORE_PROVIDERS,
)

__all__ = [
    "signal_sma", "signal_wyckoff", "signal_aihf", "signal_hidden",
    "signal_tradingagents", "signal_aitrader", "signal_langalpha",
    "signal_aimarketmaker", "signal_kronos", "signal_pyportfolioopt",
    "CORE_PROVIDERS", "ALL_PROVIDERS",
    "ENGINE_STRATEGY_PROVIDERS", "EngineStrategyProvider",
    "aggregate",
]
