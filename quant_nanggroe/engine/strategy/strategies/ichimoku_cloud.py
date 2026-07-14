from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class IchimokuCloudStrategy(BaseStrategy):
    """Ichimoku Cloud — trend direction, support/resistance, crossovers."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="IchimokuCloud", params=params)
        self.tenkan: int = int(self.params.get("tenkan", 9))
        self.kijun: int = int(self.params.get("kijun", 26))
        self.senkou_b: int = int(self.params.get("senkou_b", 52))

    def required_columns(self) -> List[str]:
        return ["high", "low", "close"]

    def warmup_period(self) -> int:
        return self.senkou_b + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        h, l, c = data["high"], data["low"], data["close"]
        tenkan = (h.rolling(self.tenkan).max() + l.rolling(self.tenkan).min()) / 2
        kijun = (h.rolling(self.kijun).max() + l.rolling(self.kijun).min()) / 2
        senkou_a = ((tenkan + kijun) / 2).shift(self.kijun)
        senkou_b = ((h.rolling(self.senkou_b).max() + l.rolling(self.senkou_b).min()) / 2).shift(self.kijun)
        cloud_top = pd.concat([senkou_a, senkou_b], axis=1).max(axis=1)
        cloud_bot = pd.concat([senkou_a, senkou_b], axis=1).min(axis=1)
        price = float(c.iloc[-1])
        if np.isnan(cloud_top.iloc[-1]):
            return None
        above_cloud = price > cloud_top.iloc[-1]
        below_cloud = price < cloud_bot.iloc[-1]
        tk_cross_bull = tenkan.iloc[-1] > kijun.iloc[-1] and tenkan.iloc[-2] <= kijun.iloc[-2]
        tk_cross_bear = tenkan.iloc[-1] < kijun.iloc[-1] and tenkan.iloc[-2] >= kijun.iloc[-2]
        if above_cloud and tk_cross_bull:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.7,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning="Ichimoku: above cloud + TK bull cross",
                evidence={"tenkan": round(float(tenkan.iloc[-1]), 4), "kijun": round(float(kijun.iloc[-1]), 4)},
                factors=["technical", "ichimoku"])
        if below_cloud and tk_cross_bear:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.7,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning="Ichimoku: below cloud + TK bear cross",
                evidence={"tenkan": round(float(tenkan.iloc[-1]), 4), "kijun": round(float(kijun.iloc[-1]), 4)},
                factors=["technical", "ichimoku"])
        return None
