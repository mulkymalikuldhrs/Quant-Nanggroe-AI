from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class KellyOptimalStrategy(BaseStrategy):
    """Kelly criterion optimal sizing based on win rate and avg win/loss."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="KellyOptimal", params=params)
        self.lookback: int = int(self.params.get("lookback", 100))
        self.min_trades: int = int(self.params.get("min_trades", 20))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.lookback + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        close = data["close"]
        rets = close.pct_change().dropna().values[-self.lookback:]
        if len(rets) < self.min_trades:
            return None
        wins = rets[rets > 0]
        losses = rets[rets < 0]
        if len(wins) < 3 or len(losses) < 3:
            return None
        win_rate = len(wins) / len(rets)
        avg_win = float(wins.mean())
        avg_loss = abs(float(losses.mean()))
        if avg_loss == 0:
            return None
        kelly = win_rate - (1 - win_rate) / (avg_win / avg_loss + 1e-10)
        kelly = np.clip(kelly, 0, 0.25)
        price = float(close.iloc[-1])
        ret_mom = float(close.iloc[-5:].mean()) / float(close.iloc[-10:-5].mean()) - 1.0
        if kelly > 0.05 and ret_mom > 0:
            return Signal(symbol=self.name, signal_type=SignalType.BUY,
                confidence=round(kelly * 4, 4), price=round(price, 6),
                source_agent=self.name, source_strategy=self.name,
                reasoning=f"Kelly {kelly:.2%}: favorable odds",
                evidence={"kelly": round(float(kelly), 4), "win_rate": round(win_rate, 3)},
                factors=["hedge_fund", "kelly"])
        return None
