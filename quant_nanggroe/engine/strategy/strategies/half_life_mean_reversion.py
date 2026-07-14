from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class HalfLifeMeanReversionStrategy(BaseStrategy):
    """Mean reversion with half-life speed adjustment for position sizing."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="HalfLifeMeanReversion", params=params)
        self.lookback: int = int(self.params.get("lookback", 60))
        self.entry_z: float = float(self.params.get("entry_z", 1.5))

    @staticmethod
    def _half_life(series: pd.Series) -> float:
        lagged = series.shift(1).dropna()
        delta = series.diff().dropna()
        idx = lagged.index.intersection(delta.index)
        if len(idx) < 10:
            return np.inf
        x, y = lagged.loc[idx].values, delta.loc[idx].values
        beta = np.polyfit(x, y, 1)[0]
        if beta >= 0:
            return np.inf
        return max(-np.log(2) / beta, 1.0)

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.lookback + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        close = data["close"]
        zs = self.compute_zscore(close, self.lookback)
        z = float(zs.iloc[-1]) if not np.isnan(zs.iloc[-1]) else 0.0
        hl = self._half_life(close)
        if hl == np.inf:
            return None
        price = float(close.iloc[-1])
        size = np.clip(self.lookback / (hl + 1e-10), 0.5, 2.0)
        if z > self.entry_z:
            return Signal(symbol=self.name, signal_type=SignalType.SELL,
                confidence=round(min(abs(z) / self.entry_z * size, 1.0), 4),
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning=f"Half-life MR: z={z:.2f}, hl={hl:.0f} bars",
                evidence={"zscore": round(z, 3), "half_life": round(float(hl), 1)},
                factors=["hedge_fund", "half_life_mr"])
        if z < -self.entry_z:
            return Signal(symbol=self.name, signal_type=SignalType.BUY,
                confidence=round(min(abs(z) / self.entry_z * size, 1.0), 4),
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning=f"Half-life MR: z={z:.2f}, hl={hl:.0f} bars",
                evidence={"zscore": round(z, 3), "half_life": round(float(hl), 1)},
                factors=["hedge_fund", "half_life_mr"])
        return None
