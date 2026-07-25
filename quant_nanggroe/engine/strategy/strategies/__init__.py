"""Legacy bridge shim — re-exports from new canonical path.

This file maintains backward compatibility for code that still imports
from the old strategy path (``quant_nanggroe.engine.strategy.strategies``).
All actual strategy implementations live in ``quant_nanggroe.engine.strategies``.
"""
import logging
from typing import Any

from quant_nanggroe.engine.strategies.registry import (
    list_strategies,
    StrategyRegistry,
)
from quant_nanggroe.engine.strategies.base import (
    Strategy,
    StrategyParameters,
    StrategySignal,
)

# Re-export everything for star imports
from quant_nanggroe.engine.strategies.base import (
    SignalDirection,
    SignalStrength,
    SignalAction,
    StrategyType,
)

log = logging.getLogger(__name__)

# Backward compat: old code uses BaseStrategy, new code uses Strategy
BaseStrategy = Strategy


def create_strategy(name: str, **kwargs: Any):
    """Create a strategy instance by name.

    Args:
        name: Registered strategy name.
        **kwargs: Optional parameters (``parameters`` for StrategyParameters object).

    Returns:
        Strategy instance or None if not found.
    """
    parameters = kwargs.get("parameters")
    return StrategyRegistry.create(name, parameters=parameters)


def get_strategy(name: str):
    """Get a registered strategy class by name.

    Args:
        name: Registered strategy name.

    Returns:
        Strategy class or None if not found.
    """
    return StrategyRegistry.get(name)


__all__ = [
    "BaseStrategy",
    "Strategy",
    "StrategyParameters",
    "StrategySignal",
    "StrategyRegistry",
    "SignalDirection",
    "SignalStrength",
    "SignalAction",
    "StrategyType",
    "list_strategies",
    "create_strategy",
    "get_strategy",
]
