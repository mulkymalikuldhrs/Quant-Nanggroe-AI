"""Legacy bridge shim — re-exports from new canonical path.

This file maintains backward compatibility for code that still imports
from the old strategy path (``quant_nanggroe.engine.strategy.strategies``).
All actual strategy implementations live in ``quant_nanggroe.engine.strategies``.
"""
from __future__ import annotations

import logging
from typing import Any

from quant_nanggroe.engine.strategies.registry import (
    list_strategies,
    StrategyRegistry,
    get_strategy_metadata,
)
from quant_nanggroe.engine.strategies.base import (
    Strategy,
    StrategyParameters,
    StrategySignal,
)
from quant_nanggroe.engine.strategies.base import (
    SignalDirection,
    SignalStrength,
    SignalAction,
    StrategyType,
)

# Backward compat: old code uses BaseStrategy, new code uses Strategy
BaseStrategy = Strategy

log = logging.getLogger(__name__)


def create_strategy(name: str, *args, **kwargs) -> Any:
    """Backward-compatible create_strategy — delegates to StrategyRegistry.create."""
    if args or kwargs:
        params = StrategyParameters()
        for k, v in kwargs.items():
            params.set(k, v)
        return StrategyRegistry.create(name, parameters=params)
    return StrategyRegistry.create(name)


def get_strategy(name: str):
    """Get a registered strategy class by name."""
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
    "get_strategy_metadata",
]
