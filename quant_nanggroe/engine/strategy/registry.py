"""Strategy registry with walk-forward framework.

Central registry for all trading strategies — tracks metadata, validation
results, and performance metrics across walk-forward windows. Single source
of truth for strategy state.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd


@dataclass
class WalkForwardResult:
    window_index: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    train_sharpe: float
    test_sharpe: float
    train_return: float
    test_return: float
    train_max_dd: float
    test_max_dd: float
    parameter_set: Dict[str, Any] = field(default_factory=dict)


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
        "int": int,
        "float": float,
        "str": str,
        "bool": bool,
        "list": list,
        "dict": dict,
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


class StrategyRegistry:
    """Central registry for all trading strategies with walk-forward framework."""

    def __init__(self, alpha_decay: Optional[Any] = None) -> None:
        self._strategies: Dict[str, StrategyMetadata] = {}
        self._alpha_decay = alpha_decay

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
        meta = StrategyMetadata(
            name=name,
            display_name=display_name or name,
            description=description,
            params_schema=params_schema or {},
            timeframe=timeframe,
            asset_classes=asset_classes or [],
            status=status,
        )
        self._strategies[name] = meta
        return meta

    def get(self, name: str) -> Optional[StrategyMetadata]:
        return self._strategies.get(name)

    def list(self, status: Optional[str] = None) -> List[StrategyMetadata]:
        if status is None:
            return list(self._strategies.values())
        return [s for s in self._strategies.values() if s.status == status]

    def record_walk_forward(
        self, name: str, result: WalkForwardResult
    ) -> None:
        meta = self._strategies.get(name)
        if meta is None:
            raise KeyError(f"Strategy '{name}' not registered")
        meta.walk_forward_results.append(result)
        meta.oos_sharpes.append(result.test_sharpe)
        meta.insample_sharpes.append(result.train_sharpe)
        meta.updated_at = datetime.now(timezone.utc).isoformat()

    def summary(self, name: str) -> Dict[str, Any]:
        meta = self._strategies.get(name)
        if meta is None:
            raise KeyError(f"Strategy '{name}' not registered")
        results = meta.walk_forward_results
        if not results:
            return {
                "name": name,
                "n_windows": 0,
                "avg_train_sharpe": 0.0,
                "avg_test_sharpe": 0.0,
                "decay": 0.0,
                "stability": 0.0,
            }
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

    def best_oos(self, n: int = 3) -> List[Dict[str, Any]]:
        candidates = []
        for name, meta in self._strategies.items():
            if meta.oos_sharpes:
                avg = sum(meta.oos_sharpes) / len(meta.oos_sharpes)
                candidates.append((avg, name))
        candidates.sort(key=lambda x: x[0], reverse=True)
        return [self.summary(name) for _, name in candidates[:n]]

    def decayed(self, name: str, threshold: float = 0.5) -> bool:
        meta = self._strategies.get(name)
        if meta is None or not meta.walk_forward_results:
            return False
        avg_train = sum(r.train_sharpe for r in meta.walk_forward_results) / len(meta.walk_forward_results)
        avg_test = sum(r.test_sharpe for r in meta.walk_forward_results) / len(meta.walk_forward_results)
        return avg_test - avg_train < -threshold

    def to_json(self, path: str) -> None:
        data = {
            name: _encode(meta)
            for name, meta in self._strategies.items()
        }
        with open(path, "w") as f:
            json.dump(data, f, cls=_RegistryEncoder, indent=2)

    @classmethod
    def from_json(cls, path: str) -> StrategyRegistry:
        with open(path) as f:
            raw = json.load(f)
        registry = cls()
        for name, meta_dict in raw.items():
            meta = _decode(meta_dict)
            if isinstance(meta, StrategyMetadata):
                registry._strategies[name] = meta
        return registry


# ── Analysis Integration ─────────────────────────────────────────────────


def compute_factor_exposures(
    registry: StrategyRegistry,
    strategy_name: str,
    returns: pd.Series,
    factors: pd.DataFrame,
) -> Dict[str, Any]:
    """Run factor regression on a strategy and store results in registry.

    Args:
        registry: StrategyRegistry instance.
        strategy_name: Name of the registered strategy.
        returns: Strategy returns Series.
        factors: Factor returns DataFrame.

    Returns:
        Dict of factor exposure metrics stored in registry metadata.
    """
    from quant_nanggroe.engine.analysis.factors import FactorModel

    model = FactorModel()
    result = model.fit(returns, factors)

    meta = registry.get(strategy_name)
    if meta is None:
        raise KeyError(f"Strategy '{strategy_name}' not registered")

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
    registry: StrategyRegistry,
    strategy_name: str,
    returns: pd.Series,
    n_bootstrap: int = 5_000,
    confidence: float = 0.95,
) -> Dict[str, Any]:
    """Compute bootstrap CI on Sharpe and store in registry.

    Args:
        registry: StrategyRegistry instance.
        strategy_name: Name of the registered strategy.
        returns: Strategy returns Series.
        n_bootstrap: Number of bootstrap replications.
        confidence: Confidence level.

    Returns:
        Dict of Sharpe CI metrics stored in registry metadata.
    """
    from quant_nanggroe.engine.analysis.bootstrap import BootstrapCI

    ci = BootstrapCI()
    result = ci.sharpe_ci(returns, confidence=confidence, n_bootstrap=n_bootstrap)

    meta = registry.get(strategy_name)
    if meta is None:
        raise KeyError(f"Strategy '{strategy_name}' not registered")

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


# Backwards-compatible alias used by tests / downstream code.
StrategyMetaRegistry = StrategyRegistry
