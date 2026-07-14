from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class VolatilitySellingStrategy(BaseStrategy):
    """Volatility Selling trading strategy.

    Detects the volatility selling candlestick pattern by modeling
    volatility dynamics and generating vol-regime signals.
    """


    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="VolatilitySelling", params=params)
        self.lookback: int = int(self.params.get("lookback", 20))
        self.vol_percentile: float = float(self.params.get("vol_percentile", 0.8))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.lookback + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        close = data["close"]
        rets = close.pct_change().dropna().iloc[-self.lookback * 3:]
        if len(rets) < self.lookback:
            return None
        hist_vol = rets.rolling(self.lookback).std().dropna()
        if len(hist_vol) < 2:
            return None
        cur_vol = float(hist_vol.iloc[-1])
        vol_rank = (hist_vol > cur_vol).mean()
        price = float(close.iloc[-1])
        if vol_rank > self.vol_percentile:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.6,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning=f"Vol selling: vol at {vol_rank:.0%} percentile",
                evidence={"vol_percentile": round(float(vol_rank), 3)}, factors=["hedge_fund", "vol_sell"])
        return None

    def __str__(self) -> str:
        return f"VolatilitySellingStrategy()"

    def __repr__(self) -> str:
        return self.__str__()

