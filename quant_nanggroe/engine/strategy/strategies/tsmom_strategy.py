"""TSMOM Strategy — Wrapper for legacy TSMOM (time-series momentum)."""

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
class TSMOMStrategy(Strategy):
    """Time-Series Momentum (Moskowitz, Ooi, Pedersen 2012).

    Wraps the legacy TSMOM implementation:
    - Signal = sign(return over past 12 months, skip 1 month)
    - Vol-scaling to target annualized volatility (40 %)
    """

    name = "tsmom"
    description = "Time-series momentum: 12-month return + vol-scaling"
    required_indicators = ["close"]

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        params = parameters or StrategyParameters()
        if not params.get("lookback"):
            params.set("lookback", 252)
        if not params.get("skip"):
            params.set("skip", 21)
        if not params.get("vol_target"):
            params.set("vol_target", 0.40)
        super().__init__(parameters=params)

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
            if len(closes) < self._parameters.get("lookback", 252) + 1:
                return self._hold(f"Insufficient data (need {self._parameters.get('lookback', 252) + 1}+ bars)")

            from quant_nanggroe.engine.strategy.strategies.tsmom import TSMOM

            ts = TSMOM(
                lookback=self._parameters.get("lookback", 252),
                skip=self._parameters.get("skip", 21),
                vol_target=self._parameters.get("vol_target", 0.40),
            )
            result = ts.analyze(closes)

            signal = result.get("signal", "hold")
            confidence = float(result.get("confidence", 0.0))
            strength_val = float(result.get("strength", 0.0))
            current_price = closes[-1]

            indicators = {
                "raw_return": result.get("raw_return", 0),
                "vol": result.get("vol", 0),
                "strength": strength_val,
            }

            if signal == "buy":
                direction = SignalDirection.BUY
                sl = current_price * 0.96
                tp = current_price * 1.08
                strength = SignalStrength.STRONG if strength_val > 0.6 else SignalStrength.MODERATE
                reasoning = f"TSMOM bullish (strength={strength_val:.3f}, ret={result.get('raw_return', 0):.4f})"
            elif signal == "sell":
                direction = SignalDirection.SELL
                sl = current_price * 1.04
                tp = current_price * 0.92
                strength = SignalStrength.STRONG if strength_val < -0.6 else SignalStrength.MODERATE
                reasoning = f"TSMOM bearish (strength={strength_val:.3f}, ret={result.get('raw_return', 0):.4f})"
            else:
                return self._hold(f"TSMOM neutral (strength={strength_val:.3f})", indicators)

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
            logger.error("TSMOMStrategy error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["TSMOMStrategy"]
