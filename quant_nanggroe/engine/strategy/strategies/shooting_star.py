from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class ShootingStarStrategy(BaseStrategy):
    """Shooting Star trading strategy.

    Detects the shooting star candlestick pattern by computing
    technical indicators and generating trading signals.
    """


    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="ShootingStar", params=params)
        self.wick_ratio: float = float(self.params.get("wick_ratio", 2.0))
        self.lookback_trend: int = int(self.params.get("lookback_trend", 10))

    def required_columns(self) -> List[str]:
        return ["open", "high", "low", "close"]

    def warmup_period(self) -> int:
        return self.lookback_trend + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        o, c, h, l = data["open"], data["close"], data["high"], data["low"]
        body = abs(c - o)
        upper_wick = h - o.max(c)
        lower_wick = o.min(c) - l
        star = (upper_wick > body * self.wick_ratio) & (lower_wick < body * 0.3)
        if not star.iloc[-1]:
            return None
        trend = (c.iloc[-1] - c.iloc[-self.lookback_trend]) / c.iloc[-self.lookback_trend]
        if trend <= 0:
            return None
        return Signal(
            symbol=self.name, signal_type=SignalType.SELL, confidence=0.6,
            price=round(float(c.iloc[-1]), 6), source_agent=self.name,
            source_strategy=self.name, reasoning="Shooting star at uptrend top",
            evidence={"trend_pct": round(float(trend * 100), 2)}, factors=["candlestick", "shooting_star"],
        )

    def __str__(self) -> str:
        return f"ShootingStarStrategy()"

    def __repr__(self) -> str:
        return self.__str__()

