from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class EWMAVolStrategy(BaseStrategy):
    """EWMA volatility — exponentially weighted moving average."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="EWMAVol", params=params)
        self.lambda_val: float = float(self.params.get("lambda", 0.94))
        self.vol_percentile: float = float(self.params.get("vol_percentile", 0.8))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return 50

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data) or len(data) < 50:
            return None
        c = data["close"].values
        rets = np.diff(np.log(c))
        sigma2 = np.var(rets)
        hist = [sigma2]
        for r in rets:
            sigma2 = self.lambda_val * sigma2 + (1 - self.lambda_val) * r ** 2
            hist.append(sigma2)
        hist = np.array(hist)
        cur_vol = np.sqrt(hist[-1])
        rank = (hist < hist[-1]).mean()
        price = float(c[-1])
        if rank > self.vol_percentile:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.5,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"EWMA vol at {rank:.0%} percentile",
                evidence={"ewma_vol": round(float(cur_vol * np.sqrt(252) * 100), 4), "percentile": round(float(rank), 3)},
                factors=["volatility", "ewma"])
        return None

