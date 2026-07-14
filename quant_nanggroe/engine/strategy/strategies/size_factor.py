from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class SizeFactorStrategy(BaseStrategy):
    """Size Factor trading strategy.

    Detects the size factor candlestick pattern by computing
    the relevant cross-sectional factor return and generating
    long/short signals based on factor score.
    """


    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="SizeFactor", params=params)
        self.lookback: int = int(self.params.get("lookback", 20))

    def required_columns(self) -> List[str]:
        return ["close", "volume"]

    def warmup_period(self) -> int:
        return self.lookback + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        close = data["close"]
        vol = data["volume"]
        avg_vol = float(vol.iloc[-self.lookback:].mean())
        cur_vol = float(vol.iloc[-1])
        price = float(close.iloc[-1])
        if cur_vol < avg_vol * 0.5:
            return None
        liq_score = np.clip(avg_vol / (cur_vol + 1e-10), 0, 1)
        if liq_score > 0.7:
            return Signal(symbol=self.name, signal_type=SignalType.BUY,
                confidence=round(liq_score, 4), price=round(price, 6),
                source_agent=self.name, source_strategy=self.name,
                reasoning=f"Size factor: volume proxy {liq_score:.2f}",
                evidence={"liq_score": round(liq_score, 3)}, factors=["hedge_fund", "size"])
        return None

    def __str__(self) -> str:
        return f"SizeFactorStrategy()"

    def __repr__(self) -> str:
        return self.__str__()

