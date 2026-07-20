from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class MultiIndicatorVotingStrategy(BaseStrategy):
    """Ensemble voting across RSI, MACD, Bollinger, and SMA."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="MultiIndicatorVoting", params=params)
        self.rsi_period: int = int(self.params.get("rsi_period", 14))
        self.bb_period: int = int(self.params.get("bb_period", 20))
        self.sma_fast: int = int(self.params.get("sma_fast", 20))
        self.sma_slow: int = int(self.params.get("sma_slow", 50))
        self.vote_threshold: float = float(self.params.get("vote_threshold", 3))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.sma_slow + self.bb_period + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        c = data["close"]
        price = float(c.iloc[-1])
        votes = 0.0
        # RSI
        rsi = self.compute_rsi(c, self.rsi_period)
        rv = float(rsi.iloc[-1]) if not np.isnan(rsi.iloc[-1]) else 50.0
        if rv < 30: votes += 1.0
        elif rv > 70: votes -= 1.0
        # Bollinger
        upper, _, lower = self.compute_bollinger_bands(c, self.bb_period)
        if not np.isnan(upper.iloc[-1]):
            if price < lower.iloc[-1]: votes += 1.0
            elif price > upper.iloc[-1]: votes -= 1.0
        # SMA crossover
        fast = self.compute_sma(c, self.sma_fast)
        slow = self.compute_sma(c, self.sma_slow)
        if not np.isnan(fast.iloc[-1]) and not np.isnan(slow.iloc[-1]):
            if fast.iloc[-1] > slow.iloc[-1]: votes += 1.0
            else: votes -= 1.0
        # MACD
        _, _, hist = self.compute_macd(c)
        if not np.isnan(hist.iloc[-1]):
            if hist.iloc[-1] > 0: votes += 1.0
            else: votes -= 1.0
        if abs(votes) >= self.vote_threshold:
            sig = SignalType.BUY if votes > 0 else SignalType.SELL
            return Signal(symbol=self.name, signal_type=sig,
                confidence=round(abs(votes) / 4.0, 4), price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"Voting: {votes:.0f}/4 bullish" if votes > 0 else f"Voting: {abs(votes):.0f}/4 bearish",
                evidence={"votes": round(float(votes), 1)}, factors=["ml", "voting"])
        return None
