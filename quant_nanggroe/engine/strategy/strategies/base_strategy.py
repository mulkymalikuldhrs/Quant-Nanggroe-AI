"""
Backward-compatibility shim for legacy import::

    from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy

Original module has been absorbed into
``quant_nanggroe.engine.strategies.base.Strategy``. This shim re-exports
so existing imports keep working.
"""
from quant_nanggroe.engine.strategies.base import (
    Strategy as BaseStrategy,
    StrategyParameters,
    StrategySignal,
    SignalDirection,
    SignalStrength,
)

__all__ = [
    "BaseStrategy",
    "StrategyParameters",
    "StrategySignal",
    "SignalDirection",
    "SignalStrength",
]
