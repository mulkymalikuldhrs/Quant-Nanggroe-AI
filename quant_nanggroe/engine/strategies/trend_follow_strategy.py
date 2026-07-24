"""Trend Follow Strategy — Wrapper for legacy TrendFollow (multi-timeframe ensemble)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

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
class TrendFollowStrategy(Strategy):
    """Multi-Timeframe Trend Following.

    Wraps the legacy TrendFollow implementation:
    - 20d MA vs 100d MA crossover
    - 50d MA slope (linear regression)
    - 12-month momentum (skip 1 month)
    Combined via sigmoid-weighted ensemble.
    """

    name = "trend_follow"
    description = "Trend following: MA crossover + slope + momentum ensemble"
    required_indicators = ["close"]

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())

    def _extract_close(self, data: Any) -> List[float]:
        if hasattr(data, "iloc"):
            return [float(v) for v in data["close"].values]
        elif isinstance(data, dict):
            vals = data.get("close", [])
            return [float(v) for v in vals] if isinstance(vals, (list, tuple)) else []
        return []

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            closes = self._extract_close(data)
            if len(closes) < 100:
                return self._hold("Insufficient data (need 100+ bars)")

            from quant_nanggroe.strategies.trend_follow import TrendFollow

            tf = TrendFollow()
            result = tf.analyze(closes)

            signal = result.get("signal", "hold")
            confidence = float(result.get("confidence", 0.0))
            strength_val = float(result.get("strength", 0.0))
            current_price = closes[-1]

            indicators = {
                "ma_crossover": result.get("ma_crossover", 0),
                "ma_slope": result.get("ma_slope", 0),
                "momentum": result.get("momentum", 0),
                "ensemble": result.get("ensemble", 0),
                "strength": strength_val,
            }

            if signal == "buy":
                direction = SignalDirection.BUY
                sl = current_price * 0.97
                tp = current_price * 1.06
                strength = SignalStrength.STRONG if strength_val > 0.6 else SignalStrength.MODERATE
                reasoning = f"TrendFollow bullish (ensemble={result.get('ensemble', 0):.4f})"
            elif signal == "sell":
                direction = SignalDirection.SELL
                sl = current_price * 1.03
                tp = current_price * 0.94
                strength = SignalStrength.STRONG if strength_val < -0.6 else SignalStrength.MODERATE
                reasoning = f"TrendFollow bearish (ensemble={result.get('ensemble', 0):.4f})"
            else:
                return self._hold(f"TrendFollow neutral (strength={strength_val:.3f})", indicators)

            return StrategySignal(
                strategy_name=self.name,
                symbol=kwargs.get("symbol", ""),
                direction=direction,
                strength=strength,
                confidence=confidence,
                entry_price=current_price,
                stop_loss=sl,
                take_profit=tp,
                risk_reward=self.calculate_risk_reward(current_price, sl, tp, direction),
                reasoning=reasoning,
                indicators=indicators,
            )

        except Exception as exc:
            logger.error("TrendFollowStrategy error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["TrendFollowStrategy"]
