from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class GARCHVolStrategy(BaseStrategy):
    """GARCH(1,1) volatility estimation for vol-regime trading."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="GARCHVol", params=params)
        self.lookback: int = int(self.params.get("lookback", 252))
        self.omega: float = float(self.params.get("omega", 1e-6))
        self.alpha: float = float(self.params.get("alpha", 0.1))
        self.beta: float = float(self.params.get("beta", 0.85))
        self.vol_percentile: float = float(self.params.get("vol_percentile", 0.8))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.lookback + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        c = data["close"].values[-self.lookback:]
        if len(c) < 100:
            return None
        rets = np.diff(np.log(c))
        sigma2 = np.var(rets)
        hist_sigma2 = np.array([sigma2])
        for r in rets[-100:]:
            sigma2 = self.omega + self.alpha * r ** 2 + self.beta * sigma2
            hist_sigma2 = np.append(hist_sigma2, sigma2)
        cur_vol = np.sqrt(hist_sigma2[-1])
        vol_rank = (hist_sigma2 < hist_sigma2[-1]).mean()
        price = float(c[-1])
        if vol_rank > self.vol_percentile:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.55,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"GARCH vol at {vol_rank:.0%} percentile, mean-reversion expected",
                evidence={"garch_vol": round(float(cur_vol * np.sqrt(252) * 100), 4), "percentile": round(float(vol_rank), 3)},
                factors=["volatility", "garch"])
        return None
