"""XGBoost Alpha Strategy — Wrapper for legacy XGBoostAlpha (ML-driven predictions)."""

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
class XGBoostAlphaStrategy(Strategy):
    """XGBoost Alpha Strategy — ML-driven return prediction.

    Wraps the legacy XGBoostAlpha implementation:
    - Engineered features: momentum, volatility, volume, price vs MA
    - XGBoost regression model trained on 70/30 split
    - Falls back to neutral if model not trained
    """

    name = "xgboost_alpha"
    description = "XGBoost ML: feature-engineered return prediction"
    required_indicators = ["close", "high", "low", "volume"]

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())

    def _extract_array(self, data: Any, key: str) -> List[float]:
        if hasattr(data, "iloc"):
            return [float(v) for v in data[key].values]
        elif isinstance(data, dict):
            vals = data.get(key, [])
            return [float(v) for v in vals] if isinstance(vals, (list, tuple)) else []
        return []

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            closes = self._extract_array(data, "close")
            highs = self._extract_array(data, "high")
            lows = self._extract_array(data, "low")
            volumes = self._extract_array(data, "volume")

            if len(closes) < 120:
                return self._hold("Insufficient data (need 120+ bars)")

            from quant_nanggroe.engine.strategy.strategies.xgboost_alpha import XGBoostAlpha

            xgb = XGBoostAlpha()

            # Train on all available data
            import numpy as np
            xgb.train(
                closes=np.array(closes, dtype=np.float64),
                highs=np.array(highs, dtype=np.float64),
                lows=np.array(lows, dtype=np.float64),
                volumes=np.array(volumes, dtype=np.float64),
            )

            # Predict
            result = xgb.predict(closes, highs, lows, volumes)

            signal = result.get("signal", "hold")
            confidence = float(result.get("confidence", 0.0))
            prediction = float(result.get("prediction", 0.0))
            trained = result.get("trained", False)
            current_price = closes[-1]

            indicators = {
                "prediction_pct": prediction,
                "model_trained": trained,
            }

            if not trained:
                indicators["note"] = "Model not trained (xgboost not installed or insufficient data)"

            if signal == "buy":
                direction = SignalDirection.BUY
                sl = current_price * 0.97
                tp = current_price * 1.05
                strength = SignalStrength.MODERATE if confidence < 0.5 else SignalStrength.STRONG
                reasoning = f"XGBoost bullish (pred={prediction:.4f}%, trained={trained})"
            elif signal == "sell":
                direction = SignalDirection.SELL
                sl = current_price * 1.03
                tp = current_price * 0.95
                strength = SignalStrength.MODERATE if confidence < 0.5 else SignalStrength.STRONG
                reasoning = f"XGBoost bearish (pred={prediction:.4f}%, trained={trained})"
            else:
                return self._hold(f"XGBoost neutral (pred={prediction:.4f}%)", indicators)

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
            logger.error("XGBoostAlphaStrategy error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["XGBoostAlphaStrategy"]
