"""Native SMC Strategy — uses QNA's own Smart Money Concepts engine.

This replaces the old smc_strategy.py which had negative live edge.
Uses native_smc.py (numpy/pandas) for Order Block, FVG, BOS/CHoCH,
and Liquidity Sweep detection. No external dependency.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategies.base import (
    SignalDirection, SignalStrength, Strategy, StrategyParameters, StrategySignal,
)
from quant_nanggroe.engine.strategies.registry import StrategyRegistry
from quant_nanggroe.engine.smc.native_smc import SMCEngine

logger = logging.getLogger("QNA.NativeSMC")


@StrategyRegistry.register
class NativeSMCStrategy(Strategy):
    """Institutional SMC strategy powered by QNA's native engine.

    Signal logic:
        - Composite score from Order Blocks + FVGs + BOS/CHoCH + Sweeps
        - Requires >= 2 bullish signals for BUY, >= 2 bearish for SELL
        - Confidence scaled by number of confluences
    """

    name = "native_smc"
    description = (
        "Native SMC: Order Block + FVG + BOS/CHoCH + Liquidity Sweep "
        "(QNA engine, numpy-native)"
    )

    def __init__(self, parameters: StrategyParameters | None = None) -> None:
        params = parameters or StrategyParameters()
        if not params.get("swing_length"):
            params.set("swing_length", 10)
        if not params.get("ob_lookback"):
            params.set("ob_lookback", 5)
        super().__init__(parameters=params)

    def generate_signal(self, data, **kwargs) -> StrategySignal:
        """Generate SMC-based signal using the native engine."""
        try:
            if not hasattr(data, "iloc") or len(data) < self.parameters.get("swing_length", 10) * 2:
                return self._hold("Insufficient data")

            engine = SMCEngine(
                swing_length=self.parameters.get("swing_length", 10),
                ob_lookback=self.parameters.get("ob_lookback", 5),
            )
            result = engine.analyze(data)

            direction = result.get("direction", "hold")
            confidence = result.get("confidence", 0.30)
            bull_score = result.get("bull_score", 0)
            bear_score = result.get("bear_score", 0)

            # Require at least 2 confluences for a directional signal
            if direction == "buy" and bull_score >= 2:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    strength=SignalStrength.STRONG if bull_score >= 3 else SignalStrength.MODERATE,
                    confidence=confidence,
                    reasoning=f"SMC: {bull_score} bullish confluences "
                              f"(OB/FVG/BOS/Sweep)",
                    indicators={"bull_score": bull_score, "bear_score": bear_score},
                )
            elif direction == "sell" and bear_score >= 2:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    strength=SignalStrength.STRONG if bear_score >= 3 else SignalStrength.MODERATE,
                    confidence=confidence,
                    reasoning=f"SMC: {bear_score} bearish confluences "
                              f"(OB/FVG/BOS/Sweep)",
                    indicators={"bull_score": bull_score, "bear_score": bear_score},
                )
            else:
                return self._hold(
                    f"No confluence: bull={bull_score} bear={bear_score}")

        except Exception as e:
            return self._hold(f"SMC error: {e}")

    def _hold(self, reason: str) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            symbol="",
            direction=SignalDirection.HOLD,
            strength=SignalStrength.WEAK,
            confidence=0.0,
            reasoning=reason,
        )
