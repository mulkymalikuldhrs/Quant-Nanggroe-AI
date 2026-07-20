from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class OptionsStraddleStrategy(BaseStrategy):
    """Straddle proxy — long when vol low, short when vol high."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="OptionsStraddle", params=params)
        self.lookback: int = int(self.params.get("lookback", 20))
        self.low_vol_percentile: float = float(self.params.get("low_vol_percentile", 0.2))
        self.high_vol_percentile: float = float(self.params.get("high_vol_percentile", 0.8))

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
        hist_vol = rets.rolling(self.lookback).std().dropna()
        if len(hist_vol) < 2:
            return None
        cur_vol = float(hist_vol.iloc[-1])
        vol_rank = (hist_vol < cur_vol).mean()
        price = float(close.iloc[-1])
        if vol_rank < self.low_vol_percentile:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.5,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"Straddle long: vol at {vol_rank:.0%} percentile (low)",
                evidence={"vol_percentile": round(float(vol_rank), 3)}, factors=["hedge_fund", "straddle"])
        if vol_rank > self.high_vol_percentile:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.5,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"Straddle short: vol at {vol_rank:.0%} percentile (high)",
                evidence={"vol_percentile": round(float(vol_rank), 3)}, factors=["hedge_fund", "straddle"])
        return None
