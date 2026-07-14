from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class RegimeHMMStrategy(BaseStrategy):
    """Simple 2-regime detection via return mean/variance."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="RegimeHMM", params=params)
        self.lookback: int = int(self.params.get("lookback", 63))
        self.regime_threshold: float = float(self.params.get("regime_threshold", 0.0))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.lookback * 2 + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        close = data["close"]
        rets = close.pct_change().dropna()
        if len(rets) < self.lookback * 2:
            return None
        rets1 = rets.iloc[-self.lookback * 2:-self.lookback]
        rets2 = rets.iloc[-self.lookback:]
        mu1, std1 = float(rets1.mean()), float(rets1.std())
        mu2, std2 = float(rets2.mean()), float(rets2.std())
        price = float(close.iloc[-1])
        if mu2 > mu1 + 0.5 * (std1 + std2):
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.6,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning="Regime shift to high-return state",
                evidence={"mu_recent": round(mu2, 4), "mu_prior": round(mu1, 4)},
                factors=["hedge_fund", "regime_hmm"])
        if mu2 < mu1 - 0.5 * (std1 + std2):
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.6,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning="Regime shift to low-return state",
                evidence={"mu_recent": round(mu2, 4), "mu_prior": round(mu1, 4)},
                factors=["hedge_fund", "regime_hmm"])
        return None
