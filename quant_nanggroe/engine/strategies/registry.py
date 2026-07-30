"""Strategy Registry — Canonical source for strategy registration and walk-forward metadata."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type

import pandas as pd

from quant_nanggroe.engine.strategies.base import Strategy, StrategyParameters
from quant_nanggroe.types.engine import StrategyStatus

if TYPE_CHECKING:
    from quant_nanggroe.engine.strategy_lifecycle import StrategyLifecycleManager

logger = logging.getLogger(__name__)

_registry: Dict[str, Type[Strategy]] = {}

# ── Walk-Forward Metadata ─────────────────────────────────────────────

@dataclass
class WalkForwardResult:
    window_index: int
    train_start: str = ""
    train_end: str = ""
    test_start: str = ""
    test_end: str = ""
    train_sharpe: float = 0.0
    test_sharpe: float = 0.0
    train_return: float = 0.0
    test_return: float = 0.0
    train_max_dd: float = 0.0
    test_max_dd: float = 0.0
    parameter_set: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.parameter_set, dict) and not self.parameter_set:
            pass


@dataclass
class StrategyMetadata:
    name: str
    display_name: str = ""
    description: str = ""
    params_schema: Dict[str, type] = field(default_factory=dict)
    timeframe: str = ""
    asset_classes: List[str] = field(default_factory=list)
    status: str = "active"
    walk_forward_results: List[WalkForwardResult] = field(default_factory=list)
    oos_sharpes: List[float] = field(default_factory=list)
    insample_sharpes: List[float] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    custom_metrics: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now
        if not self.display_name:
            self.display_name = self.name


def _serialize_type(t: type) -> str:
    return t.__name__


def _deserialize_type(name: str) -> type:
    mapping: Dict[str, type] = {
        "int": int, "float": float, "str": str, "bool": bool,
        "list": list, "dict": dict,
    }
    return mapping.get(name, str)


def _encode(obj: Any) -> Any:
    if isinstance(obj, WalkForwardResult):
        return {"__walk_forward_result__": True, **asdict(obj)}
    if isinstance(obj, StrategyMetadata):
        return {
            "__strategy_metadata__": True,
            "name": obj.name,
            "display_name": obj.display_name,
            "description": obj.description,
            "params_schema": {k: _serialize_type(v) for k, v in obj.params_schema.items()},
            "timeframe": obj.timeframe,
            "asset_classes": obj.asset_classes,
            "status": obj.status,
            "walk_forward_results": [_encode(r) for r in obj.walk_forward_results],
            "oos_sharpes": obj.oos_sharpes,
            "insample_sharpes": obj.insample_sharpes,
            "created_at": obj.created_at,
            "updated_at": obj.updated_at,
            "custom_metrics": obj.custom_metrics,
        }
    return obj


def _decode(obj: Any) -> Any:
    if isinstance(obj, dict):
        if obj.get("__walk_forward_result__"):
            d = {k: v for k, v in obj.items() if not k.startswith("__")}
            return WalkForwardResult(**d)
        if obj.get("__strategy_metadata__"):
            d = {k: v for k, v in obj.items() if not k.startswith("__")}
            d["params_schema"] = {k: _deserialize_type(v) for k, v in d["params_schema"].items()}
            d["walk_forward_results"] = [_decode(r) for r in d["walk_forward_results"]]
            return StrategyMetadata(**d)
    return obj


class _RegistryEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        encoded = _encode(obj)
        if encoded is not obj:
            return encoded
        return super().default(obj)


# In-memory walk-forward metadata store
_wf_metadata: Dict[str, StrategyMetadata] = {}

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

    Canonical source for strategy registration (decorator-driven),
    lifecycle management, and walk-forward metadata tracking.
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
        evolved = cls.get_evolved_params(name)
        if evolved:
            merged = dict(evolved)
            if parameters is not None:
                merged.update(parameters.params)
            parameters = StrategyParameters(params=merged)
        return strategy_class(parameters=parameters)

    @classmethod
    def create_all(cls, lifecycle: Optional[StrategyLifecycleManager] = None) -> Dict[str, Strategy]:
        """Create instances of all registered strategies."""
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
        """Return names of strategies eligible for trading."""
        if lifecycle is None:
            return list(_registry.keys())
        return lifecycle.get_active_strategies()

    @classmethod
    def count(cls) -> int:
        """Return number of registered strategies."""
        return len(_registry)

    # ── Walk-Forward Metadata API ──────────────────────────────────────

    @classmethod
    def get_or_create_metadata(cls, name: str) -> StrategyMetadata:
        if name not in _wf_metadata:
            _wf_metadata[name] = StrategyMetadata(name=name)
        return _wf_metadata[name]

    @classmethod
    def register_metadata(
        cls,
        name: str,
        display_name: str = "",
        description: str = "",
        params_schema: Optional[Dict[str, type]] = None,
        timeframe: str = "",
        asset_classes: Optional[List[str]] = None,
        status: str = "active",
    ) -> StrategyMetadata:
        meta = StrategyMetadata(
            name=name,
            display_name=display_name or name,
            description=description,
            params_schema=params_schema or {},
            timeframe=timeframe,
            asset_classes=asset_classes or [],
            status=status,
        )
        _wf_metadata[name] = meta
        return meta

    @classmethod
    def get_metadata(cls, name: str) -> Optional[StrategyMetadata]:
        return _wf_metadata.get(name)

    @classmethod
    def list_metadata(cls, status: Optional[str] = None) -> List[StrategyMetadata]:
        if status is None:
            return list(_wf_metadata.values())
        return [s for s in _wf_metadata.values() if s.status == status]

    @classmethod
    def record_walk_forward(cls, name: str, result: WalkForwardResult) -> None:
        meta = _wf_metadata.get(name)
        if meta is None:
            meta = cls.register_metadata(name)
        meta.walk_forward_results.append(result)
        meta.oos_sharpes.append(result.test_sharpe)
        meta.insample_sharpes.append(result.train_sharpe)
        meta.updated_at = datetime.now(timezone.utc).isoformat()

    @classmethod
    def walk_forward_summary(cls, name: str) -> Dict[str, Any]:
        meta = _wf_metadata.get(name)
        if meta is None:
            return {"name": name, "n_windows": 0}
        results = meta.walk_forward_results
        if not results:
            return {"name": name, "n_windows": 0, "avg_train_sharpe": 0.0,
                    "avg_test_sharpe": 0.0, "decay": 0.0, "stability": 0.0}
        avg_train = sum(r.train_sharpe for r in results) / len(results)
        avg_test = sum(r.test_sharpe for r in results) / len(results)
        decay = avg_train - avg_test
        test_sharpes = [r.test_sharpe for r in results]
        stability = float(__import__("numpy").std(test_sharpes)) if len(test_sharpes) > 1 else 0.0
        return {
            "name": name,
            "n_windows": len(results),
            "avg_train_sharpe": round(avg_train, 4),
            "avg_test_sharpe": round(avg_test, 4),
            "decay": round(decay, 4),
            "stability": round(stability, 4),
        }

    @classmethod
    def best_oos(cls, n: int = 3) -> List[Dict[str, Any]]:
        candidates = []
        for name, meta in _wf_metadata.items():
            if meta.oos_sharpes:
                avg = sum(meta.oos_sharpes) / len(meta.oos_sharpes)
                candidates.append((avg, name))
        candidates.sort(key=lambda x: x[0], reverse=True)
        return [cls.walk_forward_summary(name) for _, name in candidates[:n]]

    @classmethod
    def decayed(cls, name: str, threshold: float = 0.5) -> bool:
        meta = _wf_metadata.get(name)
        if meta is None or not meta.walk_forward_results:
            return False
        avg_train = sum(r.train_sharpe for r in meta.walk_forward_results) / len(meta.walk_forward_results)
        avg_test = sum(r.test_sharpe for r in meta.walk_forward_results) / len(meta.walk_forward_results)
        return avg_test - avg_train < -threshold

    @classmethod
    def to_json(cls, path: str) -> None:
        data = {name: _encode(meta) for name, meta in _wf_metadata.items()}
        with open(path, "w") as f:
            json.dump(data, f, cls=_RegistryEncoder, indent=2)

    @classmethod
    def from_json(cls, path: str) -> None:
        with open(path) as f:
            raw = json.load(f)
        for name, meta_dict in raw.items():
            meta = _decode(meta_dict)
            if isinstance(meta, StrategyMetadata):
                _wf_metadata[name] = meta


__all__ = [
    "StrategyRegistry", "StrategyMetadata", "WalkForwardResult",
    "create_strategy", "list_strategies", "get_strategy_metadata",
    "compute_factor_exposures", "sharpe_ci_to_registry",
]


# Module-level convenience functions (delegate to class methods)

_registry_instance = StrategyRegistry()


def create_strategy(name: str, lifecycle=None, **kwargs):
    """Create a strategy instance by name."""
    if kwargs:
        return _registry_instance.create(name, parameters=kwargs, lifecycle=lifecycle)
    return _registry_instance.create(name, lifecycle=lifecycle)


def list_strategies() -> list[str]:
    """List all registered strategy names."""
    return _registry_instance.list_strategies()


def get_strategy_metadata(name: str) -> dict:
    """Get metadata for a strategy, including walk-forward results if available.

    Returns:
        Dict with strategy metadata.

    Raises:
        ValueError: If the strategy is not registered.
    """
    strategy_class = StrategyRegistry.get(name)
    if strategy_class is None:
        raise ValueError(f"Strategy '{name}' not found in registry")
    result = {
        "name": name,
        "category": getattr(strategy_class, "name", name),
        "description": getattr(strategy_class, "description", ""),
    }
    meta = _wf_metadata.get(name)
    if meta is not None:
        result["wf_summary"] = StrategyRegistry.walk_forward_summary(name)
        result["asset_classes"] = meta.asset_classes
        result["timeframe"] = meta.timeframe
        result["status"] = meta.status
        result["custom_metrics"] = meta.custom_metrics
    return result


# ── Analysis Integration ──────────────────────────────────────────────


def compute_factor_exposures(
    strategy_name: str,
    returns: pd.Series,
    factors: pd.DataFrame,
) -> Dict[str, Any]:
    """Run factor regression on a strategy and store results in registry metadata."""
    from quant_nanggroe.engine.analysis.factors import FactorModel

    model = FactorModel()
    result = model.fit(returns, factors)

    meta = _wf_metadata.get(strategy_name)
    if meta is None:
        meta = StrategyRegistry.register_metadata(strategy_name)

    exposures = {
        "alpha": round(result.alpha, 6),
        "alpha_t_stat": round(result.alpha_t_stat, 6),
        "alpha_p_value": round(result.alpha_p_value, 6),
        "r_squared": round(result.r_squared, 6),
        "adj_r_squared": round(result.adj_r_squared, 6),
        "f_stat": round(result.f_stat, 6),
        "n_obs": result.n_obs,
        "factors": {k: round(v, 6) for k, v in result.factors.items()},
        "factor_t_stats": {k: round(v, 6) for k, v in result.t_stats.items()},
        "factor_p_values": {k: round(v, 6) for k, v in result.p_values.items()},
    }
    meta.custom_metrics["factor_exposures"] = exposures
    meta.updated_at = datetime.now(timezone.utc).isoformat()
    return exposures


def sharpe_ci_to_registry(
    strategy_name: str,
    returns: pd.Series,
    n_bootstrap: int = 5_000,
    confidence: float = 0.95,
) -> Dict[str, Any]:
    """Compute bootstrap CI on Sharpe and store in registry metadata."""
    from quant_nanggroe.engine.analysis.bootstrap import BootstrapCI

    ci = BootstrapCI()
    result = ci.sharpe_ci(returns, confidence=confidence, n_bootstrap=n_bootstrap)

    meta = _wf_metadata.get(strategy_name)
    if meta is None:
        meta = StrategyRegistry.register_metadata(strategy_name)

    meta.custom_metrics["sharpe_ci"] = {
        "lower": result["lower"],
        "upper": result["upper"],
        "point_estimate": result["point_estimate"],
        "std_error": result["std_error"],
        "confidence": confidence,
        "n_bootstrap": n_bootstrap,
        "block_size": result.get("block_size", 0),
    }
    meta.updated_at = datetime.now(timezone.utc).isoformat()
    return result
