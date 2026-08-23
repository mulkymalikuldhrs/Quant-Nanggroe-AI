"""Wyckoff Strategy — Wyckoff method for accumulation/distribution detection."""

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
class WyckoffStrategy(Strategy):
    """Wyckoff Method Strategy.

    Detects accumulation and distribution phases using:
    - Price/volume analysis (effort vs result)
    - Support/resistance levels
    - Springs and upthrusts
    - Sign of strength / sign of weakness
    - Cause and effect (range projection)

    Phases:
    - Accumulation: A (selling climax) -> B (auto rally) -> C (spring) -> D (sign of strength) -> E (markup)
    - Distribution: A (buying climax) -> B (auto decline) -> C (upthrust) -> D (sign of weakness) -> E (markdown)
    """

    name = "wyckoff"
    description = "Wyckoff accumulation/distribution detection"
    required_indicators = ["close", "high", "low", "volume"]

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        params = parameters or StrategyParameters()
        if not params.get("lookback"):
            params.set("lookback", 50)
        if not params.get("volume_threshold"):
            params.set("volume_threshold", 1.3)
        if not params.get("spring_threshold"):
            params.set("spring_threshold", 0.02)
        super().__init__(parameters=params)

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        """Generate Wyckoff-based trading signal.

        Analyzes price/volume relationships to detect:
        - Springs (bullish): Price dips below support then reverses on high volume
        - Upthrusts (bearish): Price spikes above resistance then reverses
        - Signs of Strength (bullish): Price rises on high volume with wide spread
        - Signs of Weakness (bearish): Price falls on high volume with wide spread
        """
        try:
            if hasattr(data, "iloc"):
                # DataFrame input
                close = data["close"].values if "close" in data else []
                high = data["high"].values if "high" in data else []
                low = data["low"].values if "low" in data else []
                volume = data["volume"].values if "volume" in data else []
            elif isinstance(data, dict):
                close = data.get("close", [])
                high = data.get("high", [])
                low = data.get("low", [])
                volume = data.get("volume", [])
            else:
                return self._hold_signal("No valid data format")

            if len(close) < 20:
                return self._hold_signal("Insufficient data (need 20+ bars)")

            lookback = self._parameters.get("lookback", 20)
            vol_threshold = self._parameters.get("volume_threshold", 1.5)
            spring_threshold = self._parameters.get("spring_threshold", 0.02)

            # Calculate average volume
            avg_vol = sum(volume[-lookback:]) / lookback if len(volume) else 1

            # Find support/resistance
            recent_low = min(low[-lookback:]) if len(low) >= lookback else min(low)
            recent_high = max(high[-lookback:]) if len(high) >= lookback else max(high)
            current_price = close[-1]
            current_vol = volume[-1] if len(volume) else 0

            # Volume ratio
            vol_ratio = current_vol / max(avg_vol, 1)

            indicators = {
                "avg_volume": avg_vol,
                "volume_ratio": round(vol_ratio, 2),
                "support": recent_low,
                "resistance": recent_high,
                "price_position": round((current_price - recent_low) / max(recent_high - recent_low, 0.01), 2),
            }

            # Spring detection: price dipped below support then reversed
            if len(low) >= 3:
                prev_low = low[-2] if len(low) >= 2 else low[-1]
                if (prev_low < recent_low * (1 - spring_threshold)
                        and current_price > recent_low
                        and vol_ratio > vol_threshold):
                    return StrategySignal(
                        strategy_name=self.name,
                        symbol=kwargs.get("symbol", ""),
                        direction=SignalDirection.BUY,
                        strength=SignalStrength.STRONG,
                        confidence=0.75,
                        entry_price=current_price,
                        stop_loss=recent_low * 0.98,
                        take_profit=recent_high,
                        risk_reward=self.calculate_risk_reward(
                            current_price, recent_low * 0.98, recent_high, SignalDirection.BUY
                        ),
                        reasoning="Wyckoff Spring detected: price dipped below support and reversed on high volume",
                        indicators=indicators,
                    )

            # Upthrust detection: price spiked above resistance then reversed
            if len(high) >= 3:
                prev_high = high[-2] if len(high) >= 2 else high[-1]
                if (prev_high > recent_high * (1 + spring_threshold)
                        and current_price < recent_high
                        and vol_ratio > vol_threshold):
                    return StrategySignal(
                        strategy_name=self.name,
                        symbol=kwargs.get("symbol", ""),
                        direction=SignalDirection.SELL,
                        strength=SignalStrength.STRONG,
                        confidence=0.70,
                        entry_price=current_price,
                        stop_loss=recent_high * 1.02,
                        take_profit=recent_low,
                        risk_reward=self.calculate_risk_reward(
                            current_price, recent_high * 1.02, recent_low, SignalDirection.SELL
                        ),
                        reasoning="Wyckoff Upthrust detected: price spiked above resistance and reversed",
                        indicators=indicators,
                    )

            # Sign of Strength: price near support with increasing volume
            if (current_price < recent_low * 1.05
                    and vol_ratio > 1.2
                    and (close[-1] > close[-2] if len(close) >= 2 else False)):
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    strength=SignalStrength.MODERATE,
                    confidence=0.55,
                    entry_price=current_price,
                    stop_loss=recent_low * 0.97,
                    take_profit=current_price + (recent_high - recent_low),
                    risk_reward=self.calculate_risk_reward(
                        current_price, recent_low * 0.97,
                        current_price + (recent_high - recent_low),
                        SignalDirection.BUY,
                    ),
                    reasoning="Wyckoff Sign of Strength: price holding near support with increasing volume",
                    indicators=indicators,
                )

            return self._hold_signal("No Wyckoff pattern detected", indicators)

        except Exception as exc:
            logger.error("Wyckoff strategy error: %s", exc)
            return self._hold_signal(f"Error: {exc}")

    def _hold_signal(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["WyckoffStrategy"]
