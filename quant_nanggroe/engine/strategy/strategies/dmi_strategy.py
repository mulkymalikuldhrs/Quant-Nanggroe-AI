from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class DMIStrategy(BaseStrategy):
    """Directional Movement Index — +DI/-DI crossover."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="DMIStrategy", params=params)
        self.period: int = int(self.params.get("period", 14))

    def required_columns(self) -> List[str]:
        return ["high", "low", "close"]

    def warmup_period(self) -> int:
        return self.period * 2 + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        h, l, c = data["high"], data["low"], data["close"]
        up = h.diff()
        dn = -l.diff()
        p_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=h.index)
        n_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=h.index)
        tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        atr = tr.rolling(self.period).mean()
        p_di = 100 * p_dm.rolling(self.period).mean() / (atr + 1e-10)
        n_di = 100 * n_dm.rolling(self.period).mean() / (atr + 1e-10)
        if np.isnan(p_di.iloc[-1]):
            return None
        price = float(c.iloc[-1])
        if p_di.iloc[-1] > n_di.iloc[-1] and p_di.iloc[-2] <= n_di.iloc[-2]:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.6,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning="DMI bullish +DI cross", evidence={"p_di": round(float(p_di.iloc[-1]), 2), "n_di": round(float(n_di.iloc[-1]), 2)},
                factors=["technical", "dmi"])
        if n_di.iloc[-1] > p_di.iloc[-1] and n_di.iloc[-2] <= p_di.iloc[-2]:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.6,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning="DMI bearish -DI cross", evidence={"p_di": round(float(p_di.iloc[-1]), 2), "n_di": round(float(n_di.iloc[-1]), 2)},
                factors=["technical", "dmi"])
        return None
