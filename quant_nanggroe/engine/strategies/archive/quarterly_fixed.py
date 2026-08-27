"""Fixed Quarterly Theory Strategy — corrected inheritance and logic."""
from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategies.base import (
    SignalDirection,
    SignalStrength,
    Strategy,
    StrategyParameters,
    StrategySignal,
)
from quant_nanggroe.engine.strategies.registry import StrategyRegistry


@StrategyRegistry.register
class QuarterlyTheoryStrategyFixed(Strategy):
    """Fixed Quarterly Theory strategy with proper Strategy base inheritance."""

    name = "archive_quarterly_fixed"
    description = "Fixed Quarterly Theory: seasonal pattern with Q1-Q4 rotation"

    def __init__(self, parameters: StrategyParameters = None) -> None:
        params = parameters or StrategyParameters()
        if not params.get("lookback"):
            params.set("lookback", 60)
        if not params.get("min_confidence"):
            params.set("min_confidence", 0.6)
        super().__init__(parameters=params)

    def generate_signal(self, data, **kwargs) -> StrategySignal:
        """Generate Quarterly Theory signal with proper error handling."""
        try:
            if not hasattr(data, "iloc"):
                return self._hold("No valid data")

            n = len(data)
            lookback = self.parameters.get("lookback", 60)
            min_conf = self.parameters.get("min_confidence", 0.6)

            if n < lookback + 20:
                return self._hold("Insufficient data for quarterly analysis")

            close = data["close"].values
            high = data["high"].values
            low = data["low"].values

            # Quarterly analysis: use moving average crossover as seasonal proxy
            q_short = int(lookback * 0.25)  # ~3 months equivalent
            q_long = int(lookback * 0.75)   # ~9 months equivalent

            ma_short = pd.Series(close).rolling(q_short, min_periods=1).mean()
            ma_long = pd.Series(close).rolling(q_long, min_periods=1).mean()
            volume = pd.Series(data["volume"].values if "volume" in data else np.ones(n)).rolling(q_short).mean()

            # Quarterly signal
            last_ma_short = ma_short.iloc[-1]
            last_ma_long = ma_long.iloc[-1]
            prev_ma_short = ma_short.iloc[-2] if n > 1 else last_ma_short
            prev_ma_long = ma_long.iloc[-2] if n > 1 else last_ma_long

            # Crossover detection
            current_cross_up = (prev_ma_short <= prev_ma_long) and (last_ma_short > last_ma_long)
            current_cross_down = (prev_ma_short >= prev_ma_long) and (last_ma_short < last_ma_long)

            # Seasonal momentum
            momentum = (last_ma_short - last_ma_long) / last_ma_long if last_ma_long > 0 else 0
            vol_mult = volume.iloc[-1] / (volume.mean() if volume.mean() > 0 else 1)

            confidence = 0.5 + abs(momentum) * 0.3 + min(vol_mult - 1, 0.3)
            confidence = max(0.0, min(1.0, confidence))

            signal = 0
            if current_cross_up and confidence >= min_conf:
                signal = 1
            elif current_cross_down and confidence >= min_conf:
                signal = -1
            elif momentum > 0.02 and confidence >= min_conf:  # Uptrend
                signal = 1
            elif momentum < -0.02 and confidence >= min_conf:  # Downtrend
                signal = -1

            if signal == 1:
                direction = SignalDirection.BUY
                strength = SignalStrength.STRONG if confidence > 0.8 else SignalStrength.MODERATE
                reasoning = f"Quarterly bullish: cross_up={current_cross_up}, mom={momentum:.4f}"
            elif signal == -1:
                direction = SignalDirection.SELL
                strength = SignalStrength.STRONG if confidence > 0.8 else SignalStrength.MODERATE
                reasoning = f"Quarterly bearish: cross_down={current_cross_down}, mom={momentum:.4f}"
            else:
                direction = SignalDirection.HOLD
                strength = SignalStrength.WEAK
                confidence = 0.0
                reasoning = f"No quarterly signal (mom={momentum:.4f}, conf={confidence:.2f})"

            return StrategySignal(
                strategy_name=self.name,
                symbol=kwargs.get("symbol", ""),
                direction=direction,
                strength=strength,
                confidence=confidence,
                reasoning=reasoning,
                indicators={
                    "ma_short": float(last_ma_short),
                    "ma_long": float(last_ma_long),
                    "momentum": float(momentum),
                    "vol_multiplier": float(vol_mult),
                    "quarter": datetime.now().quarter,
                },
            )

        except Exception as e:
            return self._hold(f"Error: {e}")

    def _hold(self, reason: str) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            symbol="",
            direction=SignalDirection.HOLD,
            strength=SignalStrength.WEAK,
            confidence=0.0,
            reasoning=reason,
        )