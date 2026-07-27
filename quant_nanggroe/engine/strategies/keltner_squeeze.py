"""Keltner Channel Squeeze — volatility squeeze breakout."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import pandas as pd

from quant_nanggroe.engine.strategies.base import (
    SignalDirection,
    Strategy,
    StrategyParameters,
    StrategySignal,
)
from quant_nanggroe.engine.strategies.registry import StrategyRegistry

logger = logging.getLogger(__name__)


@StrategyRegistry.register
class KeltnerSqueezeStrategy(Strategy):
    """Keltner Squeeze — volatility squeeze breakout."""

    name = "keltner_squeeze"
    description = "Keltner squeeze: volatility squeeze breakout"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.period: int = int(self._parameters.get("period", 20))
        self.mult: float = float(self._parameters.get("mult", 1.5))

    @staticmethod
    def _compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period, min_periods=period).mean()

    @staticmethod
    def _ema(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, min_periods=period, adjust=False).mean()

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            h, l, c = data["high"], data["low"], data["close"]
            if len(c) < self.period + 5:
                return self._hold("Insufficient data")
            ema = self._ema(c, self.period)
            atr = self._compute_atr(h, l, c, self.period)
            upper = ema + self.mult * atr
            lower = ema - self.mult * atr
            price = float(c.iloc[-1])
            if price > float(upper.iloc[-1]):
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    confidence=0.55,
                    entry_price=round(price, 6),
                    reasoning="Price above Keltner upper (breakout)",
                    indicators={"upper": round(float(upper.iloc[-1]), 4), "lower": round(float(lower.iloc[-1]), 4), "atr": round(float(atr.iloc[-1]), 4)},
                )
            if price < float(lower.iloc[-1]):
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    confidence=0.55,
                    entry_price=round(price, 6),
                    reasoning="Price below Keltner lower (breakdown)",
                    indicators={"upper": round(float(upper.iloc[-1]), 4), "lower": round(float(lower.iloc[-1]), 4), "atr": round(float(atr.iloc[-1]), 4)},
                )
            return self._hold("Price inside Keltner channel")
        except Exception as exc:
            logger.error("KeltnerSqueeze error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["KeltnerSqueezeStrategy"]
