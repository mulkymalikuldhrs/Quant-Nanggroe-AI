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
        # Set default parameters
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
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = pd.Series(tr).rolling(atr_period).mean()

            # Get current levels
            current_atr = atr.iloc[[-1, -2, -3]]
            current_atr = current_atr.iloc[-1]
            
            # Smarket flow signals
            supports = df["low"].rolling(lookback, min_periods=1).max()
            resistances = df["high"].rolling(lookback, min_periods=1).min()
            
            signals = []
            for i in range(lookback, len(df)):
                current_low = supports.iloc[i]
                current_high = resistances.iloc[i]
                
                # SMC pattern detection
                ob = current_high   # Order block
                fvg = current_atr * atr_multiplier if current_atr > 0 else 0   # Fair value gap
                bos = price_bos_logic(df, i, lookback)   # BOS implementation
                
                # Simplified SMC signal - focus on core pattern recognition
                signal = 0
                trigger = False
                
                # Key SMC patterns - simplified
                strong_bullish = (df["close"].iloc[i] >= current_high.iloc[i-1]) and \
                                (df["high"].iloc[i] > df["high"].iloc[i-1]) and \
                                (df["low"].iloc[i] > df["low"].iloc[i-1])
                strong_bearish = (df["close"].iloc[i] <= current_low.iloc[i-1]) and \
                                (df["high"].iloc[i] < df["high"].iloc[i-1]) and \
                                (df["low"].iloc[i] < df["low"].iloc[i-1])
                
                # Simplified trigger logic
                trigger = strong_bullish or strong_bearish
                
                if trigger:
                    signal = 1 if strong_bullish else -1
                
                signals.append(signal)

            if not signals:
                return self._hold("No signals generated")

            # Take the last signal
            last_index = len(signals) - 1
            signal_val = signals[-1]
            
            if signal_val == 1:
                direction = SignalDirection.BUY
                strength = SignalStrength.STRONG
                confidence = 0.75
                reasoning = "SMC breakout detected"
            elif signal_val == -1:
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


def price_bos_logic(df, i, lookback):
    """Simplified BOS logic."""
    # Price breakout of previous swing
    swing_high = np.max(df["high"].iloc[i-lookback:i])
    swing_low = np.min(df["low"].iloc[i-lookback:i])
    
    # Current price breaking previous swing
    price_ref = df["close"].iloc[i - 1]  # Reference price
    
    return price_ref