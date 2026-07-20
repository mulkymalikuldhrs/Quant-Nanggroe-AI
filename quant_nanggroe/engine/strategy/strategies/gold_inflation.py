from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class GoldInflationStrategy(BaseStrategy):
    """Gold as inflation hedge — momentum + volatility regime."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="GoldInflation", params=params)
        self.mom_lookback: int = int(self.params.get("mom_lookback", 63))
        self.vol_lookback: int = int(self.params.get("vol_lookback", 20))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return max(self.mom_lookback, self.vol_lookback * 2) + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        c = data["close"]
        ret_mom = float(c.iloc[-1]) / float(c.iloc[-self.mom_lookback]) - 1.0
        rets = c.pct_change().dropna().values[-self.vol_lookback:]
        vol = float(np.std(rets)) if len(rets) > 5 else 0.0
        price = float(c.iloc[-1])
        if ret_mom > 0.03 and vol < 0.02:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.6,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"Gold inflation hedge: mom {ret_mom:.2%}, low vol",
                evidence={"momentum": round(float(ret_mom), 4), "volatility": round(float(vol), 4)},
                factors=["macro", "gold"])
        if ret_mom < -0.03 and vol > 0.02:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.5,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"Gold weak: mom {ret_mom:.2%}, high vol",
                evidence={"momentum": round(float(ret_mom), 4), "volatility": round(float(vol), 4)},
                factors=["macro", "gold"])
        return None

