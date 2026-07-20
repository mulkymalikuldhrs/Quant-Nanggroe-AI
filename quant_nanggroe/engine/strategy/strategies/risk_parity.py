from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class RiskParityStrategy(BaseStrategy):
    """Risk Parity trading strategy.

    Detects the risk parity candlestick pattern by allocating
    risk equally across a simplified asset universe proxy.
    """


    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="RiskParity", params=params)
        self.lookback: int = int(self.params.get("lookback", 60))
        self.vol_target: float = float(self.params.get("vol_target", 0.15))

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
        vol = float(rets.std()) * np.sqrt(252)
        price = float(close.iloc[-1])
        weight = np.clip(self.vol_target / (vol + 1e-10), 0, 1)
        if weight > 0.5:
            return Signal(symbol=self.name, signal_type=SignalType.BUY,
                confidence=round(weight, 4), price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"Risk parity: vol {vol:.2%}, weight {weight:.2f}",
                evidence={"volatility": round(vol, 4), "weight": round(weight, 4)},
                factors=["hedge_fund", "risk_parity"])
        return None

    def __str__(self) -> str:
        return f"RiskParityStrategy()"

    def __repr__(self) -> str:
        return self.__str__()

