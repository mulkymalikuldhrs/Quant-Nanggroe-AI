from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class OptionsPutCallStrategy(BaseStrategy):
    """Options put/call ratio proxy via return skew."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="OptionsPutCall", params=params)
        self.lookback: int = int(self.params.get("lookback", 20))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.lookback + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        c = data["close"]
        rets = c.pct_change().dropna().values[-self.lookback:]
        if len(rets) < 10:
            return None
        neg_days = (rets < 0).mean()
        neg_avg = float(rets[rets < 0].mean()) if np.sum(rets < 0) > 0 else 0.0
        pos_avg = float(rets[rets > 0].mean()) if np.sum(rets > 0) > 0 else 0.0
        pc_ratio = neg_days / (1 - neg_days + 1e-10)
        price = float(c.iloc[-1])
        if pc_ratio > 1.5:
            # Extreme put buying — contrarian bullish
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.5,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"Put/Call ratio {pc_ratio:.2f}: excessive bearishness, contrarian buy",
                evidence={"pc_ratio": round(float(pc_ratio), 3), "neg_freq": round(float(neg_days), 3)},
                factors=["macro", "options"])
        if pc_ratio < 0.5:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.5,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"Put/Call ratio {pc_ratio:.2f}: excessive bullishness, contrarian sell",
                evidence={"pc_ratio": round(float(pc_ratio), 3), "neg_freq": round(float(neg_days), 3)},
                factors=["macro", "options"])
        return None
