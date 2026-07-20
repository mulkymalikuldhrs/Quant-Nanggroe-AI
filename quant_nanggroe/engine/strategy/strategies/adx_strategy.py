from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class ADXStrategy(BaseStrategy):
    """ADX trend strength — trade direction when ADX > threshold."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="ADXStrategy", params=params)
        self.period: int = int(self.params.get("period", 14))
        self.threshold: float = float(self.params.get("threshold", 25.0))

    def required_columns(self) -> List[str]:
        return ["open", "high", "low", "close"]

    def warmup_period(self) -> int:
        return self.period * 2 + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data) or len(data) < self.period * 2:
            return None
        h, l, c = data["high"], data["low"], data["close"]
        up = h.diff()
        down = -l.diff()
        p_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=h.index)
        n_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=h.index)
        tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        atr = tr.rolling(self.period).mean()
        p_di = 100 * p_dm.rolling(self.period).mean() / (atr + 1e-10)
        n_di = 100 * n_dm.rolling(self.period).mean() / (atr + 1e-10)
        dx = 100 * (p_di - n_di).abs() / (p_di + n_di + 1e-10)
        adx = dx.rolling(self.period).mean()
        if np.isnan(adx.iloc[-1]):
            return None
        adx_val = float(adx.iloc[-1])
        price = float(c.iloc[-1])
        if adx_val > self.threshold:
            sig = 1.0 if float(p_di.iloc[-1]) > float(n_di.iloc[-1]) else -1.0
            return Signal(symbol=self.name, signal_type=SignalType.BUY if sig > 0 else SignalType.SELL,
                confidence=min((adx_val - self.threshold) / 50, 1.0), price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"ADX {adx_val:.1f} > {self.threshold}, trending",
                evidence={"adx": round(adx_val, 2), "p_di": round(float(p_di.iloc[-1]), 2), "n_di": round(float(n_di.iloc[-1]), 2)},
                factors=["technical", "adx"])
        return None
