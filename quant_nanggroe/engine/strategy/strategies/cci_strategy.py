from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class CCIStrategy(BaseStrategy):
    """Commodity Channel Index — overbought/oversold with trend."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="CCIStrategy", params=params)
        self.period: int = int(self.params.get("period", 20))
        self.overbought: float = float(self.params.get("overbought", 100.0))
        self.oversold: float = float(self.params.get("oversold", -100.0))

    def required_columns(self) -> List[str]:
        return ["open", "high", "low", "close"]

    def warmup_period(self) -> int:
        return self.period + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        tp = (data["high"] + data["low"] + data["close"]) / 3
        sma = tp.rolling(self.period).mean()
        mad = tp.rolling(self.period).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
        cci = (tp - sma) / (0.015 * mad + 1e-10)
        val = float(cci.iloc[-1]) if not np.isnan(cci.iloc[-1]) else 0.0
        price = float(data["close"].iloc[-1])
        if val > self.overbought:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.55,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning=f"CCI {val:.0f} overbought", evidence={"cci": round(val, 2)},
                factors=["technical", "cci"])
        if val < self.oversold:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.55,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning=f"CCI {val:.0f} oversold", evidence={"cci": round(val, 2)},
                factors=["technical", "cci"])
        return None

