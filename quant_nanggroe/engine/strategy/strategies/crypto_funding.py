from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class CryptoFundingStrategy(BaseStrategy):
    """Crypto Funding trading strategy.

    Detects the crypto funding candlestick pattern by analyzing
    perpetual swap funding rates to gauge market positioning.
    """


    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="CryptoFunding", params=params)
        self.fast: int = int(self.params.get("fast", 8))
        self.slow: int = int(self.params.get("slow", 24))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.slow + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        c = data["close"]
        fast_ret = float(c.iloc[-1]) / float(c.iloc[-self.fast]) - 1.0
        slow_ret = float(c.iloc[-1]) / float(c.iloc[-self.slow]) - 1.0
        price = float(c.iloc[-1])
        if fast_ret > 0.02 and slow_ret > 0:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.5,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning="Crypto funding positive: fast momentum up",
                evidence={"fast_ret": round(float(fast_ret), 4), "slow_ret": round(float(slow_ret), 4)},
                factors=["macro", "crypto"])
        if fast_ret < -0.02 and slow_ret < 0:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.5,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning="Crypto funding negative: fast momentum down",
                evidence={"fast_ret": round(float(fast_ret), 4), "slow_ret": round(float(slow_ret), 4)},
                factors=["macro", "crypto"])
        return None

    def __str__(self) -> str:
        return f"CryptoFundingStrategy()"

    def __repr__(self) -> str:
        return self.__str__()

