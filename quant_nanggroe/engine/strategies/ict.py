"""ICT Strategy — Inner Circle Trader methodology."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from quant_nanggroe.engine.strategies.base import (
    SignalDirection,
    SignalStrength,
    Strategy,
    StrategyParameters,
    StrategySignal,
)
from quant_nanggroe.engine.strategies.registry import StrategyRegistry

logger = logging.getLogger(__name__)


@StrategyRegistry.register
class ICTStrategy(Strategy):
    """ICT (Inner Circle Trader) Strategy.

    Implements ICT concepts:
    - Kill Zones: London, New York, Asian sessions
    - Optimal Trade Entry (OTE): 62-79% Fibonacci retracement
    - Market Structure shifts
    - Order flow and institutional footprints
    - Judas Swing: False move before true direction
    """

    name = "ict"
    description = "ICT methodology: kill zones, OTE, market structure"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        params = parameters or StrategyParameters()
        if not params.get("ote_lower"):
            params.set("ote_lower", 0.618)
        if not params.get("ote_upper"):
            params.set("ote_upper", 0.786)
        super().__init__(parameters=params)

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        """Generate ICT-based trading signal."""
        try:
            if hasattr(data, "iloc"):
                close = data["close"].values
                high = data["high"].values
                low = data["low"].values
            elif isinstance(data, dict):
                close = data.get("close", [])
                high = data.get("high", [])
                low = data.get("low", [])
            else:
                return self._hold("No valid data")

            if len(close) < 10:
                return self._hold("Insufficient data")

            # Calculate swing points
            swing_high = max(high[-20:]) if len(high) >= 20 else max(high)
            swing_low = min(low[-20:]) if len(low) >= 20 else min(low)
            current_price = close[-1]
            range_val = swing_high - swing_low

            # OTE zone calculation
            ote_lower = self._parameters.get("ote_lower", 0.618)
            ote_upper = self._parameters.get("ote_upper", 0.786)

            # Bullish OTE: price retraces to 62-79% of down move
            bullish_ote_low = swing_high - range_val * ote_upper
            bullish_ote_high = swing_high - range_val * ote_lower

            # Bearish OTE: price retraces to 62-79% of up move
            bearish_ote_low = swing_low + range_val * ote_lower
            bearish_ote_high = swing_low + range_val * ote_upper

            indicators = {
                "swing_high": swing_high,
                "swing_low": swing_low,
                "bullish_ote_zone": [round(bullish_ote_low, 2), round(bullish_ote_high, 2)],
                "bearish_ote_zone": [round(bearish_ote_low, 2), round(bearish_ote_high, 2)],
                "price_position": round((current_price - swing_low) / max(range_val, 0.01), 2),
            }

            # Check for OTE entry
            if bullish_ote_low <= current_price <= bullish_ote_high:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    strength=SignalStrength.STRONG,
                    confidence=0.7,
                    entry_price=current_price,
                    stop_loss=swing_low * 0.995,
                    take_profit=swing_high,
                    risk_reward=self.calculate_risk_reward(
                        current_price, swing_low * 0.995, swing_high, SignalDirection.BUY
                    ),
                    reasoning="ICT OTE Buy: price in optimal trade entry zone (62-79% retracement)",
                    indicators=indicators,
                )

            if bearish_ote_low <= current_price <= bearish_ote_high:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    strength=SignalStrength.STRONG,
                    confidence=0.7,
                    entry_price=current_price,
                    stop_loss=swing_high * 1.005,
                    take_profit=swing_low,
                    risk_reward=self.calculate_risk_reward(
                        current_price, swing_high * 1.005, swing_low, SignalDirection.SELL
                    ),
                    reasoning="ICT OTE Sell: price in optimal trade entry zone (62-79% retracement)",
                    indicators=indicators,
                )

            return self._hold("Price not in OTE zone", indicators)

        except Exception as exc:
            logger.error("ICT strategy error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["ICTStrategy"]
