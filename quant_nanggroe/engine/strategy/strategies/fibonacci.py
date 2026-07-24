"""Fibonacci Strategy — Fibonacci retracement and extension trading."""

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

# Key Fibonacci levels
FIB_LEVELS = {
    0.236: "23.6%",
    0.382: "38.2%",
    0.500: "50.0%",
    0.618: "61.8%",
    0.786: "78.6%",
}

FIB_EXTENSION_LEVELS = {
    1.272: "127.2%",
    1.414: "141.4%",
    1.618: "161.8%",
    2.618: "261.8%",
}


@StrategyRegistry.register
class FibonacciStrategy(Strategy):
    """Fibonacci Retracement/Extension Strategy.

    Identifies key Fibonacci levels and generates signals
    when price interacts with these levels:
    - Retracement entries at 38.2%, 50%, 61.8%
    - Extension targets at 127.2%, 161.8%, 261.8%
    - Confluence with other levels strengthens signals
    """

    name = "fibonacci"
    description = "Fibonacci retracement and extension levels"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        params = parameters or StrategyParameters()
        if not params.get("proximity_pct"):
            params.set("proximity_pct", 0.005)  # 0.5% proximity to level
        if not params.get("trend_lookback"):
            params.set("trend_lookback", 50)
        super().__init__(parameters=params)

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        """Generate Fibonacci-based trading signal."""
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

            proximity = self._parameters.get("proximity_pct", 0.005)
            lookback = self._parameters.get("trend_lookback", 50)

            # Find swing high/low for Fibonacci calculation
            lb = min(lookback, len(close))
            swing_high = max(high[-lb:])
            swing_low = min(low[-lb:])
            current_price = close[-1]
            range_val = swing_high - swing_low

            if range_val <= 0:
                return self._hold("Zero range")

            # Calculate Fibonacci levels (for uptrend retracement)
            fib_levels = {}
            for level, name in FIB_LEVELS.items():
                fib_price = swing_high - range_val * level
                fib_levels[name] = round(fib_price, 4)

            # Extension levels (for price targets)
            ext_levels = {}
            for level, name in FIB_EXTENSION_LEVELS.items():
                ext_price = swing_high + range_val * (level - 1)
                ext_levels[name] = round(ext_price, 4)

            indicators = {
                "swing_high": swing_high,
                "swing_low": swing_low,
                "fib_retracement": fib_levels,
                "fib_extensions": ext_levels,
                "current_price": current_price,
            }

            # Determine trend direction
            is_uptrend = close[-1] > close[-lb] if len(close) >= lb else True

            if is_uptrend:
                # Look for buy at Fibonacci support levels
                for level, name in FIB_LEVELS.items():
                    fib_price = swing_high - range_val * level
                    distance_pct = abs(current_price - fib_price) / max(current_price, 0.01)

                    if distance_pct <= proximity:
                        # Calculate extension targets
                        tp_1618 = swing_high + range_val * 0.618
                        confidence = 0.6 if level >= 0.618 else 0.5
                        strength = SignalStrength.STRONG if level in (0.618, 0.786) else SignalStrength.MODERATE

                        return StrategySignal(
                            strategy_name=self.name,
                            symbol=kwargs.get("symbol", ""),
                            direction=SignalDirection.BUY,
                            strength=strength,
                            confidence=confidence,
                            entry_price=current_price,
                            stop_loss=swing_low * 0.995,
                            take_profit=tp_1618,
                            risk_reward=self.calculate_risk_reward(
                                current_price, swing_low * 0.995, tp_1618, SignalDirection.BUY
                            ),
                            reasoning=f"Fibonacci Buy: price at {name} retracement level ({fib_price:.2f})",
                            indicators=indicators,
                        )
            else:
                # Look for sell at Fibonacci resistance levels
                for level, name in FIB_LEVELS.items():
                    fib_price = swing_low + range_val * level
                    distance_pct = abs(current_price - fib_price) / max(current_price, 0.01)

                    if distance_pct <= proximity:
                        tp_1618 = swing_low - range_val * 0.618
                        confidence = 0.6 if level >= 0.618 else 0.5
                        strength = SignalStrength.STRONG if level in (0.618, 0.786) else SignalStrength.MODERATE

                        return StrategySignal(
                            strategy_name=self.name,
                            symbol=kwargs.get("symbol", ""),
                            direction=SignalDirection.SELL,
                            strength=strength,
                            confidence=confidence,
                            entry_price=current_price,
                            stop_loss=swing_high * 1.005,
                            take_profit=tp_1618,
                            risk_reward=self.calculate_risk_reward(
                                current_price, swing_high * 1.005, tp_1618, SignalDirection.SELL
                            ),
                            reasoning=f"Fibonacci Sell: price at {name} retracement level ({fib_price:.2f})",
                            indicators=indicators,
                        )

            return self._hold("Price not at Fibonacci level", indicators)

        except Exception as exc:
            logger.error("Fibonacci strategy error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["FibonacciStrategy"]
