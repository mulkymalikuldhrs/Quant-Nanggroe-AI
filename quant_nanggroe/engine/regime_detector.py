"""
Market Regime Detection — Backward-Compatible Shim
===================================================
Re-exports from ``engine/regime/`` package for legacy callers.

All new development should use ``quant_nanggroe.engine.regime`` directly::

    from quant_nanggroe.engine.regime import HMMRegimeDetector, Regime, RegimeState

This module maintains backward compatibility for::

    from quant_nanggroe.engine.regime_detector import HMMRegimeDetector
"""

from __future__ import annotations

from quant_nanggroe.engine.regime import (
    HMMRegimeDetector,
    Regime,
    RegimeState,
)

__all__ = [
    "HMMRegimeDetector",
    "Regime",
    "RegimeState",
]
