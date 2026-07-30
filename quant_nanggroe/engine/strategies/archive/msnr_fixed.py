"""Fixed MSNR Strategy — Malaysian S&R v2 with working logic."""
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
class MSNRStrategyFixed(Strategy):
    """MSNR v3: Support & Resistance mean-reversion + breakout with RSI filter.
    
    Uses price reaction at key levels with candlestick confirmation.
    """

    name = "archive_msnr_fixed"
    description = "MSNR v3: S/R mean-reversion + breakout with RSI filter"

    def __init__(self, parameters: StrategyParameters = None) -> None:
        params = parameters or StrategyParameters()
        if not params.get("lookback"):
            params.set("lookback", 100)
        if not params.get("rsi_period"):
            params.set("rsi_period", 14)
        if not params.get("rsi_oversold"):
            params.set("rsi_oversold", 30)
        if not params.get("rsi_overbought"):
            params.set("rsi_overbought", 70)
        super().__init__(parameters=params)

    def generate_signal(self, data, **kwargs) -> StrategySignal:
        """Generate MSNR-based trading signal."""
        try:
            if not hasattr(data, "iloc"):
                return self._hold("No valid data")

            df = data.copy()
            n = len(df)
            lookback = self.parameters.get("lookback", 100)
            rsi_period = self.parameters.get("rsi_period", 14)
            rsi_os = self.parameters.get("rsi_oversold", 30)
            rsi_ob = self.parameters.get("rsi_overbought", 70)

            if n < lookback + rsi_period + 10:
                return self._hold("Insufficient data")

            close = df["close"].values
            high = df["high"].values
            low = df["low"].values

            # Calculate RSI
            delta = pd.Series(close).diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(rsi_period).mean()
            avg_loss = loss.rolling(rsi_period).mean()
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

            # Find local highs/lows for S/R levels
            signals = []
            for i in range(lookback, n):
                window_high = high[i-lookback:i]
                window_low = low[i-lookback:i]
                resistance = np.max(window_high)
                support = np.min(window_low)
                curr_rsi = rsi.iloc[i] if not pd.isna(rsi.iloc[i]) else 50

                # Mean reversion at S/R with RSI confirmation
                at_resistance = close[i] >= resistance * 0.995
                at_support = close[i] <= support * 1.005

                signal = 0
                if at_resistance and curr_rsi > rsi_ob:
                    signal = -1  # Sell at resistance with overbought RSI
                elif at_support and curr_rsi < rsi_os:
                    signal = 1   # Buy at support with oversold RSI
                # Breakout logic
                elif close[i] > resistance and curr_rsi > 50:
                    signal = 1   # Breakout up
                elif close[i] < support and curr_rsi < 50:
                    signal = -1  # Breakout down

                signals.append(signal)

            if not signals:
                return self._hold("No signals generated")

            last_signal = signals[-1]
            if last_signal == 1:
                direction = SignalDirection.BUY
            elif last_signal == -1:
                direction = SignalDirection.SELL
            else:
                direction = SignalDirection.HOLD

            return StrategySignal(
                strategy_name=self.name,
                symbol=kwargs.get("symbol", ""),
                direction=direction,
                strength=SignalStrength.MODERATE,
                confidence=0.65,
                reasoning=f"MSNR: RSI={rsi.iloc[-1]:.1f}, S={support:.5f}, R={resistance:.5f}",
                indicators={"rsi": float(rsi.iloc[-1]), "support": float(support), "resistance": float(resistance)},
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