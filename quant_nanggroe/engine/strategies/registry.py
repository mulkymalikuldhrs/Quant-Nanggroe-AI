"""Strategy Registry — Auto-discovery and registration of strategies."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type

from quant_nanggroe.engine.strategies.base import Strategy, StrategyParameters
from quant_nanggroe.types.engine import StrategyStatus

if TYPE_CHECKING:
    from quant_nanggroe.engine.strategy_lifecycle import StrategyLifecycleManager

logger = logging.getLogger(__name__)

_registry: Dict[str, Type[Strategy]] = {}

# Evolved defaults path — persisted across restarts so accepted mutations
# from StrategyEvolver propagate to future Strategy instances.
_EVOLVED_DEFAULTS_PATH = Path("data/evolved_defaults.json")

def _load_evolved_defaults() -> dict[str, dict[str, Any]]:
    if _EVOLVED_DEFAULTS_PATH.exists():
        try:
            return json.loads(_EVOLVED_DEFAULTS_PATH.read_text())
        except Exception:
            pass
    return {}

def _save_evolved_defaults(data: dict[str, dict[str, Any]]) -> None:
    _EVOLVED_DEFAULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _EVOLVED_DEFAULTS_PATH.write_text(json.dumps(data, indent=2, default=str))


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
    def update_params(cls, name: str, params: dict[str, Any]) -> None:
        """Persist evolved parameters for a strategy.

        Called by StrategyEvolver when a mutation is accepted.
        Future calls to ``create()`` merge these defaults on top of
        the strategy's original init-time params.
        """
        data = _load_evolved_defaults()
        data[name] = params
        _save_evolved_defaults(data)
        logger.info("Evolved defaults updated for '%s' (%d params)", name, len(params))

    @classmethod
    def get_evolved_params(cls, name: str) -> dict[str, Any]:
        """Return persisted evolved defaults for a strategy, or empty dict."""
        return _load_evolved_defaults().get(name, {})

    @classmethod
    def create(cls, name: str, parameters: Optional[StrategyParameters] = None,
               lifecycle: Optional[StrategyLifecycleManager] = None) -> Optional[Strategy]:
        """Create a strategy instance by name.

        Args:
            name: Strategy name.
            parameters: Optional strategy parameters.
            lifecycle: Optional lifecycle manager. If provided, only ACTIVE
                strategies are instantiated.

        Returns:
            A Strategy instance or None if not found or not ACTIVE.
        """
        strategy_class = _registry.get(name)
        if strategy_class is None:
            logger.error("Strategy '%s' not registered", name)
            return None
        if lifecycle is not None:
            ls = lifecycle.strategies.get(name)
            if ls is not None and ls.state != StrategyStatus.ACTIVE:
                logger.warning("Strategy '%s' is %s — skipping instantiation", name, ls.state.value)
                return None
        # Merge evolved defaults on top of caller-supplied parameters
        evolved = cls.get_evolved_params(name)
        if evolved:
            merged = dict(evolved)
            if parameters is not None:
                merged.update(parameters.params)
            parameters = StrategyParameters(params=merged)
        return strategy_class(parameters=parameters)

    @classmethod
    def create_all(cls, lifecycle: Optional[StrategyLifecycleManager] = None) -> Dict[str, Strategy]:
        """Create instances of all registered strategies.

        Args:
            lifecycle: Optional lifecycle manager. If provided, only ACTIVE
                strategies are instantiated.

        Returns:
            Dict of strategy name to Strategy instance.
        """
        strategies = {}
        for name in _registry:
            if lifecycle is not None:
                ls = lifecycle.strategies.get(name)
                if ls is not None and ls.state != StrategyStatus.ACTIVE:
                    logger.debug("Strategy '%s' is %s — skipped", name, ls.state.value)
                    continue
            strategy = cls.create(name)
            if strategy is not None:
                strategies[name] = strategy
        return strategies

    @classmethod
    def viable_strategies(cls, lifecycle: Optional[StrategyLifecycleManager] = None) -> List[str]:
        """Return names of strategies eligible for trading.

        Args:
            lifecycle: Optional lifecycle manager. If provided, returns only
                ACTIVE strategy names. Otherwise returns all registered names.

        Returns:
            List of strategy names.
        """
        if lifecycle is None:
            return list(_registry.keys())
        return lifecycle.get_active_strategies()

    @classmethod
    def count(cls) -> int:
        """Return number of registered strategies."""
        return len(_registry)


__all__ = ["StrategyRegistry", "create_strategy", "list_strategies", "get_strategy_metadata"]


# Module-level convenience functions (delegate to class methods)

_registry_instance = StrategyRegistry()


def create_strategy(name: str, lifecycle=None, **kwargs):
    """Create a strategy instance by name.

    Convenience function delegating to StrategyRegistry.create.

    Args:
        name: Strategy name.
        lifecycle: Optional lifecycle manager to enforce ACTIVE-only creation.
        **kwargs: Optional keyword arguments forwarded to the strategy's init.

    Returns:
        A Strategy instance or None if not found or not ACTIVE.
    """
    if kwargs:
        return _registry_instance.create(name, parameters=kwargs, lifecycle=lifecycle)
    return _registry_instance.create(name, lifecycle=lifecycle)


def list_strategies() -> list[str]:
    """List all registered strategy names. Convenience function."""
    return _registry_instance.list_strategies()


def get_strategy_metadata(name: str) -> dict:
    """Get metadata for a strategy. Convenience function.

    Args:
        name: Strategy name.

    Returns:
        Dict with strategy metadata.

    Raises:
        ValueError: If the strategy is not registered.
    """
    strategy_class = StrategyRegistry.get(name)
    if strategy_class is None:
        raise ValueError(f"Strategy '{name}' not found in registry")
    return {
        "name": name,
        "category": getattr(strategy_class, "name", name),
        "description": getattr(strategy_class, "description", ""),
    }
