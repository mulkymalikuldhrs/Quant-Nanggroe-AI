from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class VIXTermStructureStrategy(BaseStrategy):
    """VIX term structure proxy — short-term vs long-term vol."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="VIXTermStructure", params=params)
        self.short_lookback: int = int(self.params.get("short_lookback", 10))
        self.long_lookback: int = int(self.params.get("long_lookback", 50))
        self.contango_threshold: float = float(self.params.get("contango_threshold", 0.1))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.long_lookback + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        c = data["close"].values
        if len(c) < self.long_lookback:
            return None
        rets = np.diff(np.log(c))
        short_vol = np.std(rets[-self.short_lookback:])
        long_vol = np.std(rets[-self.long_lookback:])
        term_structure = (short_vol - long_vol) / (long_vol + 1e-10)
        price = float(c[-1])
        if term_structure > self.contango_threshold:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.5,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning=f"Vol contango: short {short_vol:.4f} > long {long_vol:.4f}",
                evidence={"term_structure": round(float(term_structure), 4), "short_vol": round(float(short_vol), 4), "long_vol": round(float(long_vol), 4)},
                factors=["volatility", "vix_term"])
        if term_structure < -self.contango_threshold:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.5,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning=f"Vol backwardation: short {short_vol:.4f} < long {long_vol:.4f}",
                evidence={"term_structure": round(float(term_structure), 4), "short_vol": round(float(short_vol), 4), "long_vol": round(float(long_vol), 4)},
                factors=["volatility", "vix_term"])
        return None
