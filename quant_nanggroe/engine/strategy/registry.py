"""Backward-compat shim — re-exports from canonical quant_nanggroe.engine.strategies.registry

WalkForwardRegistry and StrategyMetadata now live in the canonical
StrategyRegistry at quant_nanggroe.engine.strategies.registry.

This file remains for backward compatibility. All new code should import
from quant_nanggroe.engine.strategies.registry directly.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from quant_nanggroe.engine.strategies.registry import (
    StrategyMetadata,
    WalkForwardResult,
    compute_factor_exposures,
    get_strategy_metadata,
    list_strategies,
    sharpe_ci_to_registry,
)
from quant_nanggroe.engine.strategies.registry import (
    StrategyRegistry as _StrategyRegistry,
)

# Re-export dataclasses and functions
__all__ = [
    "WalkForwardRegistry",
    "StrategyMetaRegistry",
    "StrategyMetadata",
    "WalkForwardResult",
    "compute_factor_exposures",
    "sharpe_ci_to_registry",
    "get_strategy_metadata",
    "list_strategies",
]


class WalkForwardRegistry:
    """Backward-compat shim that delegates to StrategyRegistry.

    Previously the canonical walk-forward metadata tracker.
    Now delegates all calls to StrategyRegistry classmethods.
    """

    def __init__(self, alpha_decay: Optional[Any] = None) -> None:
        self._alpha_decay = alpha_decay

    @property
    def _strategies(self) -> Dict[str, StrategyMetadata]:
        return _StrategyRegistry._wf_metadata  # type: ignore[attr-defined]

    def register(
        self,
        name: str,
        display_name: str = "",
        description: str = "",
        params_schema: Optional[Dict[str, type]] = None,
        timeframe: str = "",
        asset_classes: Optional[List[str]] = None,
        status: str = "active",
    ) -> StrategyMetadata:
        return _StrategyRegistry.register_metadata(
            name, display_name, description, params_schema or {},
            timeframe, asset_classes or [], status,
        )

    def get(self, name: str) -> Optional[StrategyMetadata]:
        return _StrategyRegistry.get_metadata(name)

    def list(self, status: Optional[str] = None) -> List[StrategyMetadata]:
        return _StrategyRegistry.list_metadata(status)

    def record_walk_forward(self, name: str, result: WalkForwardResult) -> None:
        _StrategyRegistry.record_walk_forward(name, result)

    def summary(self, name: str) -> Dict[str, Any]:
        return _StrategyRegistry.walk_forward_summary(name)

    def best_oos(self, n: int = 3) -> List[Dict[str, Any]]:
        return _StrategyRegistry.best_oos(n)

    def decayed(self, name: str, threshold: float = 0.5) -> bool:
        return _StrategyRegistry.decayed(name, threshold)

    def to_json(self, path: str) -> None:
        _StrategyRegistry.to_json(path)

    @classmethod
    def from_json(cls, path: str) -> WalkForwardRegistry:
        _StrategyRegistry.from_json(path)
        reg = cls()
        return reg


StrategyMetaRegistry = WalkForwardRegistry


def __getattr__(name: str) -> Any:
    if name == "StrategyRegistry":
        return _StrategyRegistry
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
