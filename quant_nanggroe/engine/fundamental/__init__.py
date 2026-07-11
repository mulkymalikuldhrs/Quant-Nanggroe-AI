"""Fundamental Analysis — News, COT, and Sentiment modules.

Based on research:
- RavenPack Sentiment Inflection Points (IR=1.61)
- Day Trading Bab 14-15: Forex Factory + COT
- n8n pipeline: News + COT analysis branch
"""

from __future__ import annotations

import importlib
from typing import Any

_module_registry = {
    "SentimentAnalyzer": ".sentiment",
    "COTParser": ".cot",
    "EconomicCalendar": ".calendar",
}

__all__ = sorted(_module_registry.keys())


def __getattr__(name: str) -> Any:
    if name not in _module_registry:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    mod = importlib.import_module(_module_registry[name], package=__name__)
    attr = getattr(mod, name)
    globals()[name] = attr
    return attr
