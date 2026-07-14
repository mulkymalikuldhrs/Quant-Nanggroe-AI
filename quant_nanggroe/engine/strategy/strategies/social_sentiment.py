from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class SocialSentimentStrategy(BaseStrategy):
    """Social Sentiment trading strategy.

    Detects the social sentiment candlestick pattern by measuring
    price momentum as a proxy for social sentiment shifts.
    """


    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="SocialSentiment", params=params)
        self.lookback: int = int(self.params.get("lookback", 20))
        self.spike_mult: float = float(self.params.get("spike_mult", 2.0))

    def required_columns(self) -> List[str]:
        return ["close", "volume"]

    def warmup_period(self) -> int:
        return self.lookback + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        c, v = data["close"], data["volume"]
        avg_vol = float(v.iloc[-self.lookback:].mean())
        cur_vol = float(v.iloc[-1])
        ret = float(c.iloc[-1]) / float(c.iloc[-2]) - 1.0
        price = float(c.iloc[-1])
        if cur_vol > avg_vol * self.spike_mult and abs(ret) > 0.01:
            sig = 1.0 if ret > 0 else -1.0
            return Signal(symbol=self.name, signal_type=SignalType.BUY if sig > 0 else SignalType.SELL,
                confidence=min(abs(ret) * 10, 1.0), price=round(price, 6),
                source_agent=self.name, source_strategy=self.name,
                reasoning=f"Sentiment spike: vol {cur_vol/avg_vol:.1f}x, ret {ret:.2%}",
                evidence={"vol_ratio": round(float(cur_vol / avg_vol), 2), "return": round(float(ret), 4)},
                factors=["macro", "sentiment"])
        return None

    def __str__(self) -> str:
        return f"SocialSentimentStrategy()"

    def __repr__(self) -> str:
        return self.__str__()

