from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class ValueFactorStrategy(BaseStrategy):
    """Value Factor trading strategy.

    Detects the value factor candlestick pattern by computing
    the relevant cross-sectional factor return and generating
    long/short signals based on factor score.
    """


    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="ValueFactor", params=params)
        self.lookback: int = int(self.params.get("lookback", 252))
        self.entry_z: float = float(self.params.get("entry_z", 1.5))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.lookback + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        close = data["close"]
        zs = self.compute_zscore(close, self.lookback)
        z = float(zs.iloc[-1]) if len(zs) > 0 and not np.isnan(zs.iloc[-1]) else 0.0
        price = float(close.iloc[-1])
        if z < -self.entry_z:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.6,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"Value factor: price z-score {z:.2f}, undervalued",
                evidence={"zscore": round(z, 3)}, factors=["hedge_fund", "value"])
        if z > self.entry_z:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.6,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"Value factor: price z-score {z:.2f}, overvalued",
                evidence={"zscore": round(z, 3)}, factors=["hedge_fund", "value"])
        return None

    def __str__(self) -> str:
        return f"ValueFactorStrategy()"

    def __repr__(self) -> str:
        return self.__str__()

