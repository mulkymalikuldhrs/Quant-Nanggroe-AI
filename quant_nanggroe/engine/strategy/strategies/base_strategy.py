"""Compatibility shim for legacy/archive strategies.

Many archive modules import the base class via the legacy path
``quant_nanggroe.engine.strategy.strategies.base_strategy`` (class
``BaseStrategy``). The canonical base lives at
``quant_nanggroe.engine.strategies.base.Strategy``. This module re-exports it so
those 100+ archive modules register under AutoRegistry without editing each file.

// ponytail: single shim fixes all 108 broken import sites at once.
"""
from quant_nanggroe.engine.strategies.base import Strategy as BaseStrategy
from quant_nanggroe.engine.strategies.base import Strategy

__all__ = ["BaseStrategy", "Strategy"]
