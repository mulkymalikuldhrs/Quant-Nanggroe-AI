from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class RSIDivergenceMACDStrategy(BaseStrategy):
    """RSI divergence confirmed by MACD for high-probability reversals."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="RSIDivergenceMACD", params=params)
        self.rsi_period: int = int(self.params.get("rsi_period", 14))
        self.lookback: int = int(self.params.get("lookback", 20))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return max(self.rsi_period, self.lookback) + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data) or len(data) < self.lookback * 2:
            return None
        c = data["close"]
        rsi = self.compute_rsi(c, self.rsi_period)
        macd_line, _, histogram = self.compute_macd(c)
        if np.isnan(rsi.iloc[-1]) or np.isnan(macd_line.iloc[-1]):
            return None
        price = float(c.iloc[-1])
        # Check divergence: price makes HH but RSI makes LL (bearish), or vice versa
        p1, p2 = float(c.iloc[-self.lookback]), float(c.iloc[-self.lookback//2])
        r1, r2 = float(rsi.iloc[-self.lookback]), float(rsi.iloc[-self.lookback//2])
        cp, cr = float(c.iloc[-1]), float(rsi.iloc[-1])
        macd_pos = float(histogram.iloc[-1]) > 0
        # Bearish divergence: price HH, RSI LH
        if cp > p2 and p2 > p1 and cr < r2 and r2 < r1 and not macd_pos:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.65,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning="Bearish RSI divergence confirmed by MACD",
                evidence={"rsi": round(cr, 2), "macd_hist": round(float(histogram.iloc[-1]), 4)},
                factors=["ml", "rsi_divergence"])
        # Bullish divergence: price LL, RSI HL
        if cp < p2 and p2 < p1 and cr > r2 and r2 > r1 and macd_pos:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.65,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning="Bullish RSI divergence confirmed by MACD",
                evidence={"rsi": round(cr, 2), "macd_hist": round(float(histogram.iloc[-1]), 4)},
                factors=["ml", "rsi_divergence"])
        return None
