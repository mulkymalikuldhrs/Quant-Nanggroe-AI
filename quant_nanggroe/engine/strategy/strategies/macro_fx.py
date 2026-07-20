from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class MacroFXStrategy(BaseStrategy):
    """Macro F X trading strategy.

    Detects the macro f x candlestick pattern by computing
    dual moving average crossover on FX rate proxies.
    """


    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="MacroFX", params=params)
        self.fast: int = int(self.params.get("fast", 20))
        self.slow: int = int(self.params.get("slow", 50))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.slow + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        close = data["close"]
        fast_ma = self.compute_sma(close, self.fast)
        slow_ma = self.compute_sma(close, self.slow)
        if np.isnan(fast_ma.iloc[-1]) or np.isnan(slow_ma.iloc[-1]):
            return None
        price = float(close.iloc[-1])
        if fast_ma.iloc[-1] > slow_ma.iloc[-1]:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.55,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning="FX macro: bullish trend",
                evidence={"fast_ma": round(float(fast_ma.iloc[-1]), 4), "slow_ma": round(float(slow_ma.iloc[-1]), 4)},
                factors=["hedge_fund", "macro_fx"])
        return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.55,
            price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
            reasoning="FX macro: bearish trend",
            evidence={"fast_ma": round(float(fast_ma.iloc[-1]), 4), "slow_ma": round(float(slow_ma.iloc[-1]), 4)},
            factors=["hedge_fund", "macro_fx"])

    def __str__(self) -> str:
        return f"MacroFXStrategy()"

    def __repr__(self) -> str:
        return self.__str__()

