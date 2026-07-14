from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class ElderTripleScreenStrategy(BaseStrategy):
    """Elder Triple Screen — multi-timeframe trend alignment."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="ElderTripleScreen", params=params)
        self.trend_period: int = int(self.params.get("trend_period", 13))
        self.osc_period: int = int(self.params.get("osc_period", 8))
        self.rsi_period: int = int(self.params.get("rsi_period", 8))

    def required_columns(self) -> List[str]:
        return ["high", "low", "close"]

    def warmup_period(self) -> int:
        return max(self.trend_period, self.osc_period * 3) + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        c, h, l = data["close"], data["high"], data["low"]
        ema = self.compute_ema(c, self.trend_period)
        rsi = self.compute_rsi(c, self.rsi_period)
        # Williams %R as oscillator
        hh = h.rolling(self.osc_period).max()
        ll = l.rolling(self.osc_period).min()
        wr = -100 * (hh - c) / (hh - ll + 1e-10)
        price = float(c.iloc[-1])
        if np.isnan(ema.iloc[-1]) or np.isnan(rsi.iloc[-1]):
            return None
        trend_up = c.iloc[-1] > ema.iloc[-1]
        rsi_val = float(rsi.iloc[-1])
        wr_val = float(wr.iloc[-1])
        if trend_up and rsi_val < 50 and wr_val < -50:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.65,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning="Elder Triple: bullish alignment",
                evidence={"rsi": round(rsi_val, 2), "williams_r": round(wr_val, 2)},
                factors=["technical", "elder_triple"])
        if not trend_up and rsi_val > 50 and wr_val > -50:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.65,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning="Elder Triple: bearish alignment",
                evidence={"rsi": round(rsi_val, 2), "williams_r": round(wr_val, 2)},
                factors=["technical", "elder_triple"])
        return None
