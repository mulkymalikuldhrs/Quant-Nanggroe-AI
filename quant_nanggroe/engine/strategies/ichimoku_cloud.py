"""Ichimoku Cloud — multi-indicator trend/strength."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import numpy as np

from quant_nanggroe.engine.strategies.base import (
    SignalDirection,
    Strategy,
    StrategyParameters,
    StrategySignal,
)
from quant_nanggroe.engine.strategies.registry import StrategyRegistry

logger = logging.getLogger(__name__)


@StrategyRegistry.register
class IchimokuCloudStrategy(Strategy):
    """Ichimoku Cloud — cloud trend / TK cross / lagging span."""

    name = "ichimoku_cloud"
    description = "Ichimoku Cloud: cloud trend, TK cross, lagging span"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.tenkan: int = int(self._parameters.get("tenkan", 9))
        self.kijun: int = int(self._parameters.get("kijun", 26))
        self.senkou_b: int = int(self._parameters.get("senkou_b", 52))

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            h, l, c = data["high"], data["low"], data["close"]
            if len(c) < self.senkou_b + self.kijun + 5:
                return self._hold("Insufficient data")
            tenkan = (h.rolling(self.tenkan).max() + l.rolling(self.tenkan).min()) / 2
            kijun = (h.rolling(self.kijun).max() + l.rolling(self.kijun).min()) / 2
            senkou_a = ((tenkan + kijun) / 2).shift(self.kijun)
            senkou_b = ((h.rolling(self.senkou_b).max() + l.rolling(self.senkou_b).min()) / 2).shift(self.kijun)
            price = float(c.iloc[-1])
            spana = float(senkou_a.iloc[-1]) if not np.isnan(senkou_a.iloc[-1]) else 0.0
            spanb = float(senkou_b.iloc[-1]) if not np.isnan(senkou_b.iloc[-1]) else 0.0
            if spana < spanb:
                cloud_top, cloud_bottom = spanb, spana
            else:
                cloud_top, cloud_bottom = spana, spanb
            if price > cloud_top:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    confidence=0.55,
                    entry_price=round(price, 6),
                    reasoning="Price above Ichimoku cloud (bullish)",
                    indicators={"senkou_a": round(cloud_bottom, 4), "senkou_b": round(cloud_top, 4)},
                )
            if price < cloud_bottom:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    confidence=0.55,
                    entry_price=round(price, 6),
                    reasoning="Price below Ichimoku cloud (bearish)",
                    indicators={"senkou_a": round(cloud_bottom, 4), "senkou_b": round(cloud_top, 4)},
                )
            return self._hold("Price inside Ichimoku cloud")
        except Exception as exc:
            logger.error("IchimokuCloud error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["IchimokuCloudStrategy"]
