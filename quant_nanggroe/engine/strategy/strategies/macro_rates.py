from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class MacroRatesStrategy(BaseStrategy):
    """Macro Rates trading strategy.

    Detects the macro rates candlestick pattern by comparing
    short and long momentum to proxy interest rate direction.
    """


    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="MacroRates", params=params)
        self.lookback: int = int(self.params.get("lookback", 63))
        self.momentum_threshold: float = float(self.params.get("momentum_threshold", 0.02))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.lookback + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        close = data["close"]
        ret_momentum = float(close.iloc[-1]) / float(close.iloc[-self.lookback]) - 1.0
        price = float(close.iloc[-1])
        if ret_momentum > self.momentum_threshold:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.55,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning=f"Rates momentum long: {ret_momentum:.2%}",
                evidence={"momentum": round(float(ret_momentum), 4)}, factors=["hedge_fund", "macro_rates"])
        if ret_momentum < -self.momentum_threshold:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.55,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning=f"Rates momentum short: {ret_momentum:.2%}",
                evidence={"momentum": round(float(ret_momentum), 4)}, factors=["hedge_fund", "macro_rates"])
        return None

    def __str__(self) -> str:
        return f"MacroRatesStrategy()"

    def __repr__(self) -> str:
        return self.__str__()

