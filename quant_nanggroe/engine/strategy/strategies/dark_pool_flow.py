from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class DarkPoolFlowStrategy(BaseStrategy):
    """Dark pool flow proxy via block trade detection (large prints)."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="DarkPoolFlow", params=params)
        self.lookback: int = int(self.params.get("lookback", 20))
        self.vol_mult: float = float(self.params.get("vol_mult", 3.0))

    def required_columns(self) -> List[str]:
        return ["close", "volume"]

    def warmup_period(self) -> int:
        return self.lookback + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        c, v = data["close"], data["volume"]
        avg_vol = float(v.iloc[-self.lookback:-1].mean())
        cur_vol = float(v.iloc[-2])
        prev_vol = float(v.iloc[-3]) if len(v) > 3 else 0
        price = float(c.iloc[-1])
        ret = float(c.iloc[-1]) / float(c.iloc[-2]) - 1.0
        # Detect potential block trade: vol spike with direction
        if cur_vol > avg_vol * self.vol_mult and prev_vol < avg_vol * 1.5:
            if ret > 0:
                return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.5,
                    price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                    reasoning="Dark pool: block buy detected",
                    evidence={"vol_ratio": round(float(cur_vol / avg_vol), 2), "return": round(float(ret), 4)},
                    factors=["macro", "dark_pool"])
            if ret < 0:
                return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.5,
                    price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                    reasoning="Dark pool: block sell detected",
                    evidence={"vol_ratio": round(float(cur_vol / avg_vol), 2), "return": round(float(ret), 4)},
                    factors=["macro", "dark_pool"])
        return None
