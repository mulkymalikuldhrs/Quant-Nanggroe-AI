from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class MFIStrategy(BaseStrategy):
    """Money Flow Index — volume-weighted RSI."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="MFIStrategy", params=params)
        self.period: int = int(self.params.get("period", 14))
        self.overbought: float = float(self.params.get("overbought", 80.0))
        self.oversold: float = float(self.params.get("oversold", 20.0))

    def required_columns(self) -> List[str]:
        return ["high", "low", "close", "volume"]

    def warmup_period(self) -> int:
        return self.period + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        tp = (data["high"] + data["low"] + data["close"]) / 3
        mf = tp * data["volume"]
        direction = tp.diff().apply(lambda x: 1 if x > 0 else -1 if x < 0 else 0)
        pos_mf = (direction * mf).clip(lower=0).rolling(self.period).sum()
        neg_mf = (-(direction * mf)).clip(lower=0).rolling(self.period).sum()
        mfr = pos_mf / (neg_mf + 1e-10)
        mfi = 100 - 100 / (1 + mfr)
        val = float(mfi.iloc[-1]) if not np.isnan(mfi.iloc[-1]) else 50.0
        price = float(data["close"].iloc[-1])
        if val > self.overbought:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.55,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"MFI {val:.0f} overbought", evidence={"mfi": round(val, 2)},
                factors=["technical", "mfi"])
        if val < self.oversold:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.55,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"MFI {val:.0f} oversold", evidence={"mfi": round(val, 2)},
                factors=["technical", "mfi"])
        return None
