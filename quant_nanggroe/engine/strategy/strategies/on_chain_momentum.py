from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class OnChainMomentumStrategy(BaseStrategy):
    """On-chain momentum proxy via volume-weighted price action."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="OnChainMomentum", params=params)
        self.lookback: int = int(self.params.get("lookback", 30))

    def required_columns(self) -> List[str]:
        return ["close", "volume"]

    def warmup_period(self) -> int:
        return self.lookback + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        c, v = data["close"], data["volume"]
        vwap = (c * v).rolling(self.lookback).sum() / v.rolling(self.lookback).sum()
        if np.isnan(vwap.iloc[-1]):
            return None
        price = float(c.iloc[-1])
        vol_trend = float(v.iloc[-int(self.lookback/2):].mean()) / (float(v.iloc[-self.lookback:-int(self.lookback/2)].mean()) + 1e-10)
        if price > vwap.iloc[-1] and vol_trend > 1.2:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.55,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning="On-chain: price above VWAP with increasing volume",
                evidence={"vwap": round(float(vwap.iloc[-1]), 4), "vol_trend": round(float(vol_trend), 3)},
                factors=["macro", "onchain"])
        if price < vwap.iloc[-1] and vol_trend < 0.8:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.55,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning="On-chain: price below VWAP with decreasing volume",
                evidence={"vwap": round(float(vwap.iloc[-1]), 4), "vol_trend": round(float(vol_trend), 3)},
                factors=["macro", "onchain"])
        return None

