from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class EntropyStrategy(BaseStrategy):
    """Market efficiency via entropy of returns distribution."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="EntropyStrategy", params=params)
        self.lookback: int = int(self.params.get("lookback", 50))
        self.bins: int = int(self.params.get("bins", 10))
        self.entropy_threshold: float = float(self.params.get("entropy_threshold", 0.7))

    @staticmethod
    def _entropy(rets: np.ndarray, bins: int) -> float:
        hist, _ = np.histogram(rets, bins=bins, density=True)
        hist = hist[hist > 0]
        return -np.sum(hist * np.log(hist + 1e-10)) / np.log(bins)

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.lookback + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        close = data["close"]
        rets = close.pct_change().dropna().values[-self.lookback:]
        if len(rets) < 20:
            return None
        e = self._entropy(rets, self.bins)
        price = float(close.iloc[-1])
        if e > self.entropy_threshold:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=min(e, 1.0),
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"High entropy {e:.3f}: market inefficient, trend likely",
                evidence={"entropy": round(e, 3)}, factors=["hedge_fund", "entropy"])
        return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=min(1 - e, 1.0),
            price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
            reasoning=f"Low entropy {e:.3f}: market efficient, MR likely",
            evidence={"entropy": round(e, 3)}, factors=["hedge_fund", "entropy"])
