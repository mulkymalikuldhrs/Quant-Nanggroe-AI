from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class KeltnerSqueezeStrategy(BaseStrategy):
    """Keltner Channel squeeze — Bollinger inside Keltner = squeeze."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="KeltnerSqueeze", params=params)
        self.period: int = int(self.params.get("period", 20))
        self.atr_mult: float = float(self.params.get("atr_mult", 1.5))

    def required_columns(self) -> List[str]:
        return ["high", "low", "close"]

    def warmup_period(self) -> int:
        return self.period + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        h, l, c = data["high"], data["low"], data["close"]
        ema = self.compute_ema(c, self.period)
        atr = self.compute_atr(h, l, c, self.period)
        if np.isnan(ema.iloc[-1]) or np.isnan(atr.iloc[-1]):
            return None
        kc_upper = ema + self.atr_mult * atr
        kc_lower = ema - self.atr_mult * atr
        bb_upper, bb_mid, bb_lower = self.compute_bollinger_bands(c, self.period)
        squeeze = (bb_upper < kc_upper) & (bb_lower > kc_lower)
        price = float(c.iloc[-1])
        if squeeze.iloc[-1]:
            ret = float(c.iloc[-1]) / float(c.iloc[-5]) - 1.0
            sig = 1.0 if ret > 0 else -1.0
            return Signal(symbol=self.name, signal_type=SignalType.BUY if sig > 0 else SignalType.SELL,
                confidence=0.5, price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning="Keltner squeeze detected",
                evidence={"kc_upper": round(float(kc_upper.iloc[-1]), 4), "kc_lower": round(float(kc_lower.iloc[-1]), 4)},
                factors=["volatility", "keltner_squeeze"])
        return None
