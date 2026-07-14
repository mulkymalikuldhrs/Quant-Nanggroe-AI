from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class BollingerSqueezeStrategy(BaseStrategy):
    """Bollinger Band squeeze — low vol precedes breakout."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="BollingerSqueeze", params=params)
        self.period: int = int(self.params.get("period", 20))
        self.squeeze_threshold: float = float(self.params.get("squeeze_threshold", 0.05))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.period * 2 + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        c = data["close"]
        upper, mid, lower = self.compute_bollinger_bands(c, self.period)
        bbw = (upper - lower) / (mid + 1e-10)
        bbw_hist = bbw.dropna().values[-self.period:]
        if len(bbw_hist) < 5:
            return None
        cur_bbw = float(bbw.iloc[-1])
        bbw_rank = (bbw_hist < cur_bbw).mean()
        price = float(c.iloc[-1])
        if bbw_rank < self.squeeze_threshold:
            # Squeeze detected — anticipate breakout
            ret = float(c.iloc[-1]) / float(c.iloc[-5]) - 1.0
            sig = 1.0 if ret > 0 else -1.0
            return Signal(symbol=self.name, signal_type=SignalType.BUY if sig > 0 else SignalType.SELL,
                confidence=0.5, price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"Bollinger squeeze: BBW at {bbw_rank:.0%}",
                evidence={"bbw": round(float(cur_bbw), 6), "bbw_rank": round(float(bbw_rank), 3)},
                factors=["volatility", "bollinger_squeeze"])
        return None
