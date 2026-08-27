"""Legacy shim for PairsTradingStrategy.

Exports ``PairsTradingStrategy`` as an alias for the canonical ``PairsTradeStrategy``
implemented in ``quant_nanggroe.engine.strategies.pairs_trade_strategy``.
"""

from quant_nanggroe.engine.strategies.pairs_trade_strategy import (
    PairsTradeStrategy as PairsTradingStrategy,  # noqa: F401
)
