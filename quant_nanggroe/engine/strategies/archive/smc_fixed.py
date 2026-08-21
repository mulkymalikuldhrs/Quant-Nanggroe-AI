"""Fixed SMC Strategy — corrected inheritance and logic."""
from __future__ import annotations

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
class SMCStrategyFixed(Strategy):
    """Fixed SMC Strategy with proper Strategy base inheritance.

    Correction: Inherit from Strategy instead of plain class.
    """

    name = "archive_smc_fixed"
    description = "Fixed SMC Strategy with correct base class and signal generation"

    def __init__(self, parameters: StrategyParameters = None) -> None:
        params = parameters or StrategyParameters()
        if not params.get("atr_period"):
            params.set("atr_period", 14)
        if not params.get("atr_multiplier"):
            params.set("atr_multiplier", 1.0)
        if not params.get("lookback"):
            params.set("lookback", 20)
        super().__init__(parameters=params)

    def generate_signal(self, data, **kwargs) -> StrategySignal:
        """Generate SMC-based trading signal with proper error handling."""
        try:
            if not hasattr(data, "iloc"):
                return self._hold("No valid data")

            df = data.copy()
            atr_period = self.parameters.get("atr_period", 14)
            atr_multiplier = self.parameters.get("atr_multiplier", 1.0)
            lookback = self.parameters.get("lookback", 20)

            if len(df) < max(atr_period, lookback) + 10:
                return self._hold("Insufficient data")

            # Calculate ATR
            high = df["high"].values
            low = df["low"].values
            close = df["close"].values

            tr1 = high - low
            tr2 = np.abs(high - pd.Series(close).shift().values)
            tr3 = np.abs(low - pd.Series(close).shift().values)
            tr = pd.DataFrame({"tr1": tr1, "tr2": tr2, "tr3": tr3}).max(axis=1)
            atr = pd.Series(tr).rolling(atr_period).mean()

            current_atr = atr.iloc[-1]

            # Market flow signals
            supports = df["low"].rolling(lookback, min_periods=1).max()
            resistances = df["high"].rolling(lookback, min_periods=1).min()

            signals = []
            for i in range(lookback, len(df)):
                current_low = supports.iloc[i]
                current_high = resistances.iloc[i]

                # SMC pattern detection
                strong_bullish = (
                    df["close"].iloc[i] >= current_high.iloc[i - 1]
                    and df["high"].iloc[i] > df["high"].iloc[i - 1]
                    and df["low"].iloc[i] > df["low"].iloc[i - 1]
                )
                strong_bearish = (
                    df["close"].iloc[i] <= current_low.iloc[i - 1]
                    and df["high"].iloc[i] < df["high"].iloc[i - 1]
                    and df["low"].iloc[i] < df["low"].iloc[i - 1]
                )

                signal = 0
                if strong_bullish:
                    signal = 1
                elif strong_bearish:
                    signal = -1

                signals.append(signal)

            if not signals:
                return self._hold("No signals generated")

            last_signal = signals[-1]
            if last_signal == 1:
                direction = SignalDirection.BUY
                strength = SignalStrength.STRONG
                confidence = 0.75
                reasoning = "SMC breakout detected"
            elif last_signal == -1:
                direction = SignalDirection.SELL
                strength = SignalStrength.STRONG
                confidence = 0.75
                reasoning = "SMC breakdown detected"
            else:
                direction = SignalDirection.HOLD
                strength = SignalStrength.WEAK
                confidence = 0.5
                reasoning = "Pattern scanning in progress"

            return StrategySignal(
                strategy_name=self.name,
                symbol=kwargs.get("symbol", ""),
                direction=direction,
                strength=strength,
                confidence=confidence,
                reasoning=reasoning,
                indicators={"atr_trigger": float(current_atr)},
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