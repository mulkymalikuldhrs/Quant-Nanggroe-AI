"""Bridges — lazy imports for fast module loading.

Connects the deterministic engine layer to the LLM agent layer.
"""

from __future__ import annotations

import importlib
from typing import Any

_module_registry = {
    "RiskGateBridge": ".risk_gate_bridge",
    "KellyBridge": ".kelly_bridge",
}

__all__ = sorted(_module_registry.keys())


def __getattr__(name: str) -> Any:
    if name not in _module_registry:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    mod = importlib.import_module(_module_registry[name], package=__name__)
    attr = getattr(mod, name)
    globals()[name] = attr
    return attr
