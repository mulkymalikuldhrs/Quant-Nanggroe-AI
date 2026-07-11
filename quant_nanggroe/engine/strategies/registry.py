"""Strategy Registry — Auto-discovery and registration of strategies.

Bridges class-based strategy registration with the WalkForward metadata
registry (StrategyMetaRegistry) so every decorated strategy automatically
gets metadata tracking, factor exposure analysis, and walk-forward validation.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Type

from quant_nanggroe.engine.strategies.base import Strategy, StrategyParameters
from quant_nanggroe.engine.strategy.registry import StrategyMetaRegistry

logger = logging.getLogger(__name__)

_registry: Dict[str, Type[Strategy]] = {}

# ── Bridge: shared metadata registry instance ────────────────────────
_meta_registry: StrategyMetaRegistry = StrategyMetaRegistry()


class StrategyRegistry:
    """Registry for trading strategy implementations.

    Automatically discovers and registers strategies.
    Use the ``register`` decorator to add new strategies.

    Each registered strategy is also bridged to the StrategyMetaRegistry
    for walk-forward analysis, factor exposures, and performance tracking.
    """

    @classmethod
    def register(cls, strategy_class: Type[Strategy]) -> Type[Strategy]:
        """Register a strategy class.

        Usage::

            @StrategyRegistry.register
            class WyckoffStrategy(Strategy):
                name = "wyckoff"
                ...

        Also auto-registers metadata with the WalkForward meta-registry.
        """
        _registry[strategy_class.name] = strategy_class

        # Bridge: auto-register metadata for the new strategy
        display = getattr(strategy_class, "display_name", strategy_class.name)
        desc = getattr(strategy_class, "__doc__", "") or ""
        _meta_registry.register(
            name=strategy_class.name,
            display_name=display,
            description=desc.strip(),
            timeframe=getattr(strategy_class, "timeframe", ""),
            asset_classes=getattr(strategy_class, "asset_classes", []),
            status="active",
        )

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

    # ── Bridge methods ───────────────────────────────────────────────

    @classmethod
    def get_meta_registry(cls) -> StrategyMetaRegistry:
        """Access the shared StrategyMetaRegistry bridge instance."""
        return _meta_registry

    @classmethod
    def list_metadata(cls) -> List[Dict]:
        """List all registered strategies with their walk-forward metadata.

        Returns:
            List of dicts with name, display_name, status, and headless
            summary for each strategy tracked by the meta-registry.
        """
        return [
            {
                "name": meta.name,
                "display_name": meta.display_name,
                "status": meta.status,
                "description": meta.description,
                "timeframe": meta.timeframe,
                "asset_classes": meta.asset_classes,
                "n_walk_forward_windows": len(meta.walk_forward_results),
            }
            for meta in _meta_registry.list()
        ]


__all__ = ["StrategyRegistry"]
