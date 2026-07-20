from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class MomentumCrashFilterStrategy(BaseStrategy):
    """Momentum with volatility crash filter — exit when vol spikes."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="MomentumCrashFilter", params=params)
        self.mom_lookback: int = int(self.params.get("mom_lookback", 126))
        self.vol_lookback: int = int(self.params.get("vol_lookback", 20))
        self.vol_mult: float = float(self.params.get("vol_mult", 2.0))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return max(self.mom_lookback, self.vol_lookback * 2) + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        close = data["close"]
        rets = close.pct_change().dropna()
        if len(rets) < self.vol_lookback * 2:
            return None
        hist_vol = rets.rolling(self.vol_lookback).std().mean() * np.sqrt(252)
        cur_vol = float(rets.iloc[-self.vol_lookback:].std()) * np.sqrt(252)
        price = float(close.iloc[-1])
        ret_mom = float(close.iloc[-1]) / float(close.iloc[-self.mom_lookback]) - 1.0
        if cur_vol > hist_vol * self.vol_mult:
            return None
        if ret_mom > 0.05:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.55,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"Crash-filtered momentum: ret={ret_mom:.2%}, vol OK",
                evidence={"momentum": round(float(ret_mom), 4), "cur_vol": round(float(cur_vol), 4)},
                factors=["hedge_fund", "crash_filter"])
        if ret_mom < -0.05:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.55,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"Crash-filtered momentum: ret={ret_mom:.2%}, vol OK",
                evidence={"momentum": round(float(ret_mom), 4), "cur_vol": round(float(cur_vol), 4)},
                factors=["hedge_fund", "crash_filter"])
        return None
