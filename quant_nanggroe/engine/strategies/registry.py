"""Strategy Registry — Auto-discovery and registration of strategies."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Type

from quant_nanggroe.engine.strategies.base import Strategy, StrategyParameters

logger = logging.getLogger(__name__)

_registry: Dict[str, Type[Strategy]] = {}


class StrategyRegistry:
    """Registry for trading strategy implementations.

    Automatically discovers and registers strategies.
    Use the ``register`` decorator to add new strategies.
    """

    @classmethod
    def register(cls, strategy_class: Type[Strategy]) -> Type[Strategy]:
        """Register a strategy class.

        Usage::

            @StrategyRegistry.register
            class WyckoffStrategy(Strategy):
                name = "wyckoff"
                ...
        """
        _registry[strategy_class.name] = strategy_class
        return strategy_class

    @classmethod
    def get(cls, name: str) -> Optional[Type[Strategy]]:
        """Get a registered strategy class by name."""
        return _registry.get(name)

    @classmethod
    def list_strategies(cls) -> List[str]:
        """List all registered strategy names."""
        return list(_registry.keys())

    @classmethod
    def create(cls, name: str, parameters: Optional[StrategyParameters] = None) -> Optional[Strategy]:
        """Create a strategy instance by name."""
        strategy_class = _registry.get(name)
        if strategy_class is None:
            logger.error("Strategy '%s' not registered", name)
            return None
        return strategy_class(parameters=parameters)

    @classmethod
    def create_all(cls) -> Dict[str, Strategy]:
        """Create instances of all registered strategies."""
        strategies = {}
        for name in _registry:
            strategy = cls.create(name)
            if strategy is not None:
                strategies[name] = strategy
        return strategies

    @classmethod
    def count(cls) -> int:
        """Return number of registered strategies."""
        return len(_registry)


__all__ = ["StrategyRegistry"]
