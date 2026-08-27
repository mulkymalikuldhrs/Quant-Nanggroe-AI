"""Provider registry — lists of all signal providers used by the aggregator.

CORE_PROVIDERS: hand-crafted strategies (AI-driven, classical, etc.)
MUE-X providers: 992 dynamically discovered from external/mue_x (lazy-loaded on call)
ALL_PROVIDERS: combined list for the aggregator.
"""

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
from quant_nanggroe.hedge_fund.signals.qna_strategies import MUE_X_PROVIDERS

# Engine strategies bridge — wraps 77 registered @StrategyRegistry classes
# as aggregator-compatible callables. Guarded so environments without MT5
# (which triggers hedge_fund.__init__ -> execution -> mt5 attr error) degrade
# gracefully — the list is simply empty, and no provider crashes the pipeline.
try:
    from quant_nanggroe.hedge_fund.signals.engine_strategies import ENGINE_STRATEGY_PROVIDERS
except Exception:
    ENGINE_STRATEGY_PROVIDERS = []

CORE_PROVIDERS = [
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
]

ALL_PROVIDERS = (
    CORE_PROVIDERS
    + list(MUE_X_PROVIDERS.values())
    + ENGINE_STRATEGY_PROVIDERS
)
