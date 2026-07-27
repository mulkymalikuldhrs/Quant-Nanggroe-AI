"""Volume Delta and CVD Analysis Strategy.

Analyzes buying/selling pressure through volume delta and cumulative
volume delta (CVD) to detect institutional accumulation/distribution.

Ported from ai-hedge-fund/src/strategies/unified_retail_strategy.py (VolumeDeltaAnalyzer)
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategies.base import (
    SignalAction,
    Strategy,
    StrategyParameters,
    StrategySignal,
    StrategyType,
)
from quant_nanggroe.engine.strategies.registry import StrategyRegistry

logger = logging.getLogger(__name__)


class VolumeDeltaParameters(StrategyParameters):
    """Volume Delta strategy parameters."""

    cvd_period: int = 20
    delta_trend_period: int = 10
    strong_buying_threshold: float = 65.0
    strong_selling_threshold: float = 35.0
    min_confidence: float = 0.55


@StrategyRegistry.register
class VolumeDeltaStrategy(Strategy):
    """Volume Delta / CVD Analysis Strategy.

    Estimates buying and selling pressure from candle characteristics
    and tracks cumulative volume delta to detect accumulation/distribution
    phases.
    """

    name = "volume_delta"

    def __init__(self, parameters: Optional[VolumeDeltaParameters] = None) -> None:
        self._params = parameters or VolumeDeltaParameters()

    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.VOLUME_DELTA

    @property
    def description(self) -> str:
        return "CVD and volume delta analysis for accumulation/distribution detection"

    def generate_signal(self, df: pd.DataFrame, symbol: str = "UNKNOWN") -> StrategySignal:
        """Generate volume delta-based trading signal."""
        if not self.validate(df):
            return StrategySignal(
                strategy_name=self.name,
                symbol=symbol,
                action=SignalAction.HOLD,
                confidence=0.0,
                reasoning="Insufficient data for volume delta analysis",
            )

        high = df["high"]
        low = df["low"]
        close = df["close"]
        volume = df["volume"] if "volume" in df.columns else pd.Series(np.ones(len(df)), index=df.index)

        current_price = float(close.iloc[-1])

        # Calculate deltas
        deltas = self._calculate_deltas(high, low, close, volume)

        # Calculate buying/selling pressure
        total_volume = np.abs(deltas).sum()
        if total_volume == 0:
            return StrategySignal(
                strategy_name=self.name,
                symbol=symbol,
                action=SignalAction.HOLD,
                confidence=0.0,
                reasoning="No volume data",
            )

        buying_pressure = float(np.sum(deltas[deltas > 0]) / total_volume * 100)
        selling_pressure = float(np.sum(deltas[deltas < 0]) / total_volume * 100)

        # Cumulative delta
        cumulative_delta = float(np.cumsum(deltas)[-1])

        # Delta trend
        recent_deltas = deltas[-self._params.delta_trend_period:]
        delta_trend = "accumulating" if np.mean(recent_deltas) > 0 else "distributing" if np.mean(recent_deltas) < 0 else "neutral"

        # CVD trend
        cvd = np.cumsum(deltas)
        cvd_ma = pd.Series(cvd).rolling(self._params.cvd_period, min_periods=1).mean().values

        # Score
        bullish_score = 0.0
        bearish_score = 0.0
        reasons = []

        # Buying/selling pressure
        if buying_pressure > self._params.strong_buying_threshold:
            bullish_score += 0.35
            reasons.append(f"Strong buying pressure ({buying_pressure:.1f}%)")
        elif buying_pressure < self._params.strong_selling_threshold:
            bearish_score += 0.35
            reasons.append(f"Strong selling pressure ({selling_pressure:.1f}%)")

        # Delta trend
        if delta_trend == "accumulating":
            bullish_score += 0.25
            reasons.append("CVD accumulating")
        elif delta_trend == "distributing":
            bearish_score += 0.25
            reasons.append("CVD distributing")

        # CVD vs price divergence
        if len(cvd) > 20:
            price_trend = float(close.iloc[-1]) - float(close.iloc[-20])
            cvd_trend = cvd[-1] - cvd[-20]

            # Bullish divergence: price down, CVD up
            if price_trend < 0 and cvd_trend > 0:
                bullish_score += 0.3
                reasons.append("Bullish CVD divergence")
            # Bearish divergence: price up, CVD down
            elif price_trend > 0 and cvd_trend < 0:
                bearish_score += 0.3
                reasons.append("Bearish CVD divergence")

        # Determine action
        total_score = bullish_score - bearish_score
        confidence = min(0.9, abs(total_score) + 0.3)

        if total_score > 0.3:
            action = SignalAction.BUY
            stop_loss = current_price * 0.98
            take_profit = current_price * 1.04
        elif total_score < -0.3:
            action = SignalAction.SELL
            stop_loss = current_price * 1.02
            take_profit = current_price * 0.96
        else:
            action = SignalAction.HOLD
            stop_loss = current_price
            take_profit = current_price

        risk = abs(current_price - stop_loss)
        reward = abs(take_profit - current_price)
        rr_ratio = reward / risk if risk > 0 else 0

        if confidence < self._params.min_confidence:
            action = SignalAction.HOLD

        return StrategySignal(
            strategy_name=self.name,
            symbol=symbol,
            action=action,
            confidence=confidence,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=rr_ratio,
            reasoning="; ".join(reasons) if reasons else "No volume delta signal",
            metadata={
                "buying_pressure": buying_pressure,
                "selling_pressure": selling_pressure,
                "cumulative_delta": cumulative_delta,
                "delta_trend": delta_trend,
                "bullish_score": bullish_score,
                "bearish_score": bearish_score,
            },
        )

    def get_parameters(self) -> VolumeDeltaParameters:
        return self._params

    def validate(self, df: pd.DataFrame) -> bool:
        required_cols = {"high", "low", "close"}
        if not required_cols.issubset(df.columns):
            return False
        return len(df) >= 20

    @staticmethod
    def _calculate_deltas(
        high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series
    ) -> np.ndarray:
        """Estimate volume delta from candle characteristics.

        Up candle body = buying pressure; Down candle body = selling pressure.
        """
        deltas = []
        for i in range(len(close)):
            body = abs(float(close.iloc[i]) - float(close.iloc[i - 1] if i > 0 else close.iloc[i]))
            range_val = float(high.iloc[i]) - float(low.iloc[i])
            if range_val == 0:
                range_val = 1.0

            if close.iloc[i] > (close.iloc[i - 1] if i > 0 else close.iloc[i]):
                delta = (body / range_val) * float(volume.iloc[i])
            else:
                delta = -(body / range_val) * float(volume.iloc[i])

            deltas.append(delta)

        return np.array(deltas)
