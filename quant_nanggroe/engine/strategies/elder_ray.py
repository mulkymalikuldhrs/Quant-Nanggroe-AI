"""Elder Ray Index — bull/bear power with trend filter."""

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
class ElderRayStrategy(Strategy):
    """Elder Ray Index — bull/bear power with trend filter."""

    name = "elder_ray"
    description = "Elder Ray: bull/bear power with trend filter"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.period: int = int(self._parameters.get("period", 13))

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
            bull_power = h - ema
            bear_power = l - ema
            bp, bp_p = float(bull_power.iloc[-1]), float(bull_power.iloc[-2])
            bn, bn_p = float(bear_power.iloc[-1]), float(bear_power.iloc[-2])
            price = float(c.iloc[-1])
            if bp > 0 and bp > bp_p and bn > bn_p:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    confidence=0.6,
                    entry_price=round(price, 6),
                    reasoning="Elder Ray bullish: bull/bear power rising",
                    indicators={"bull_power": round(bp, 4), "bear_power": round(bn, 4)},
                )
            if bn < 0 and bn < bn_p and bp < bp_p:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    confidence=0.6,
                    entry_price=round(price, 6),
                    reasoning="Elder Ray bearish: bull/bear power falling",
                    indicators={"bull_power": round(bp, 4), "bear_power": round(bn, 4)},
                )
            return self._hold("Elder Ray neutral")
        except Exception as exc:
            logger.error("ElderRay error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["ElderRayStrategy"]
