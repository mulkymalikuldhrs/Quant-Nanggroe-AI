from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class VolatilityRegimeStrategy(BaseStrategy):
    """Volatility regime — classify market as low/med/high vol."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="VolatilityRegime", params=params)
        self.lookback: int = int(self.params.get("lookback", 63))
        self.low_threshold: float = float(self.params.get("low_threshold", 0.3))
        self.high_threshold: float = float(self.params.get("high_threshold", 0.7))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.lookback * 2 + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data) or len(data) < self.lookback * 2:
            return None
        c = data["close"].values
        rets = np.diff(np.log(c[-self.lookback * 2:]))
        if len(rets) < self.lookback:
            return None
        all_vol = [np.std(rets[i:i+self.lookback]) for i in range(len(rets) - self.lookback)]
        if not all_vol:
            return None
        cur_vol = all_vol[-1]
        rank = (np.array(all_vol) < cur_vol).mean()
        price = float(c[-1])
        if rank < self.low_threshold:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.5,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning="Low vol regime: trend following",
                evidence={"vol_percentile": round(float(rank), 3)}, factors=["volatility", "regime"])
        if rank > self.high_threshold:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.5,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning="High vol regime: mean reversion",
                evidence={"vol_percentile": round(float(rank), 3)}, factors=["volatility", "regime"])
        return None
