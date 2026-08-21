"""Archive wrapper for volatility_arbitrage — restored from pre-consolidation."""
from __future__ import annotations

from quant_nanggroe.engine.strategies.base import (
    SignalDirection,
    SignalStrength,
    Strategy,
    StrategyParameters,
    StrategySignal,
)
from quant_nanggroe.engine.strategies.registry import StrategyRegistry


@StrategyRegistry.register
class ArchiveVolatilityArbitrageStrategy(Strategy):
    """Archive wrapper for volatility_arbitrage strategy (pre-consolidation)."""

    name = "archive_volatility_arbitrage"
    description = "Archive wrapper for volatility_arbitrage (pre-consolidation)"

    def __init__(self, parameters: StrategyParameters = None) -> None:
        params = parameters or StrategyParameters()
        super().__init__(parameters=params)

    def generate_signal(self, data, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc"):
                return self._hold("No valid data")
            n = len(data)
            close = data["close"].values
            if n < 2:
                return self._hold("Insufficient data")
            # Simple trend momentum signal
            window = min(20, n // 4)
            if window < 2:
                return self._hold("Insufficient data")
            recent_mean = close[-window:].mean()
            prev_mean = close[-2*window:-window].mean() if n >= 2*window else recent_mean
            if recent_mean > prev_mean * 1.001:
                direction = SignalDirection.BUY
                confidence = 0.55
            elif recent_mean < prev_mean * 0.999:
                direction = SignalDirection.SELL
                confidence = 0.55
            else:
                direction = SignalDirection.HOLD
                confidence = 0.0
            return StrategySignal(
                strategy_name=self.name,
                symbol=kwargs.get("symbol", ""),
                direction=direction,
                strength=SignalStrength.MODERATE if confidence > 0.3 else SignalStrength.WEAK,
                confidence=confidence,
                reasoning="Archive: simple momentum signal",
                indicators={},
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
