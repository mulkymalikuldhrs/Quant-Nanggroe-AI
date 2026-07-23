"""
Backward-compatibility shim — old strategy path → new path.

The strategy files moved from quant_nanggroe.engine.strategy.strategies
to quant_nanggroe.engine.strategies in the v15 migration. This shim
re-exports everything so existing imports keep working.
"""
from __future__ import annotations

import logging
from typing import Any, Type

from quant_nanggroe.engine.strategies.base import (
    SignalDirection,
    SignalStrength,
    Strategy as BaseStrategy,  # alias for backward compat
    StrategyParameters,
    StrategySignal,
)
from quant_nanggroe.engine.strategies.registry import (
    StrategyRegistry,
    get_strategy_metadata,
    list_strategies,
)

logger = logging.getLogger(__name__)


def create_strategy(name: str, *args, **kwargs) -> Any:
    """Backward-compatible create_strategy — delegates to StrategyRegistry.create."""
    # The old create_strategy accepted positional args (lookback, volume_mult, etc.)
    # The new StrategyRegistry.create only accepts StrategyParameters.
    # If positional args are passed, package them as StrategyParameters.
    if args or kwargs:
        params = StrategyParameters()
        if args and len(args) > 0:
            params.set("lookback", args[0])
        if len(args) > 1:
            params.set("volume_mult", args[1])
        for k, v in kwargs.items():
            params.set(k, v)
        return StrategyRegistry.create(name, parameters=params)
    return StrategyRegistry.create(name)


__all__ = [
    "BaseStrategy",
    "StrategyParameters",
    "StrategySignal",
    "SignalDirection",
    "SignalStrength",
    "StrategyRegistry",
    "list_strategies",
    "create_strategy",
    "get_strategy_metadata",
]
