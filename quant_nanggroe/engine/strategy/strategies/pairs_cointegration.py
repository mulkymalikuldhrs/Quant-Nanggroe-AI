from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class PairsCointegrationStrategy(BaseStrategy):
    """Pairs trading via cointegration z-score on a synthetic pair spread."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="PairsCointegration", params=params)
        self.entry_z: float = float(self.params.get("entry_z", 2.0))
        self.exit_z: float = float(self.params.get("exit_z", 0.5))
        self.lookback: int = int(self.params.get("lookback", 60))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.lookback + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        close = data["close"]
        close_arr = close.values
        # Synthetic pair spread using two halves of the series
        mid = len(close_arr) // 2
        if mid < self.lookback:
            return None
        p1 = close_arr[-self.lookback:] / close_arr[-self.lookback]
        p2 = close_arr[-self.lookback:] / close_arr[mid] if mid < len(close_arr) else p1
        spread = np.log(p1 + 1e-10) - np.log(p2 + 1e-10)
        z = (spread[-1] - np.mean(spread)) / (np.std(spread) + 1e-10)
        price = float(close.iloc[-1])
        if z > self.entry_z:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.7,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning=f"Spread z-score {z:.2f} > {self.entry_z}, short spread",
                evidence={"zscore": round(float(z), 3)}, factors=["hedge_fund", "pairs"])
        if z < -self.entry_z:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.7,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning=f"Spread z-score {z:.2f} < {-self.entry_z}, long spread",
                evidence={"zscore": round(float(z), 3)}, factors=["hedge_fund", "pairs"])
        return None
