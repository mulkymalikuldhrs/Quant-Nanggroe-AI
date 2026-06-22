"""Kelly Criterion package — lazy imports for fast module loading.

Provides optimal position sizing through Fractional, Bayesian, Drawdown,
Correlation, Adaptive, Multi-Asset Kelly and Optimal F.
"""

from __future__ import annotations

import importlib
from typing import Any

_module_registry = {
    "BaseKelly": ".base",
    "KellyParameters": ".base",
    "KellyResult": ".base",
    "KellyMethod": ".base",
    "FractionalKelly": ".fractional",
    "BayesianKelly": ".bayesian",
    "DrawdownControlledKelly": ".drawdown",
    "CorrelationAwareKelly": ".correlation",
    "AdaptiveKelly": ".adaptive",
    "MultiAssetKelly": ".multi_asset",
    "OptimalF": ".optimal_f",
    "KellyBacktestBridge": ".backtest_integration",
    "KellySignal": ".backtest_integration",
    "StrategyKellyMixin": ".backtest_integration",
}

__all__ = sorted(_module_registry.keys())


def __getattr__(name: str) -> Any:
    if name not in _module_registry:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    mod = importlib.import_module(_module_registry[name], package=__name__)
    attr = getattr(mod, name)
    globals()[name] = attr
    return attr
