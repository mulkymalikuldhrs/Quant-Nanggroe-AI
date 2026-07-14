from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class QualityFactorStrategy(BaseStrategy):
    """Quality Factor trading strategy.

    Detects the quality factor candlestick pattern by computing
    the relevant cross-sectional factor return and generating
    long/short signals based on factor score.
    """


    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="QualityFactor", params=params)
        self.lookback: int = int(self.params.get("lookback", 63))
        self.sharpe_threshold: float = float(self.params.get("sharpe_threshold", 0.5))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.lookback + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        close = data["close"]
        rets = close.pct_change().dropna().iloc[-self.lookback:]
        if len(rets) < 20:
            return None
        sharpe = np.sqrt(252) * float(rets.mean()) / (float(rets.std()) + 1e-10)
        vol_rank = float(rets.std()) / float(close.iloc[-self.lookback])
        price = float(close.iloc[-1])
        if sharpe > self.sharpe_threshold and vol_rank < float(rets.std() / close.iloc[-1]):
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=min(sharpe / 2, 1.0),
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning=f"Quality factor: Sharpe {sharpe:.2f}",
                evidence={"sharpe": round(sharpe, 3)}, factors=["hedge_fund", "quality"])
        return None

    def __str__(self) -> str:
        return f"QualityFactorStrategy()"

    def __repr__(self) -> str:
        return self.__str__()

