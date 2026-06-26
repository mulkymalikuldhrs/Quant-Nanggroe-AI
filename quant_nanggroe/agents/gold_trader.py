"""AI-XAUUSD-Trading inspired gold trading agent."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import numpy as np


@dataclass
class GoldSignal:
    timestamp: datetime
    direction: str  # long/short/neutral
    confidence: float
    reasons: List[str] = field(default_factory=list)


class GoldTrader:
    """XAUUSD trading agent using technical + fundamental analysis."""

    def __init__(self, lookback_days: int = 30):
        self.lookback_days = lookback_days
        self.prices: List[float] = []
        self.signals: List[GoldSignal] = []

    def update_prices(self, prices: List[float]):
        self.prices = prices[-self.lookback_days:] if len(prices) > self.lookback_days else prices

    def analyze(self) -> GoldSignal:
        if len(self.prices) < 20:
            return GoldSignal(datetime.now(), "neutral", 0.0, ["insufficient data"])

        sma_5 = np.mean(self.prices[-5:])
        sma_20 = np.mean(self.prices[-20:])
        latest = self.prices[-1]

        rsi = self._calc_rsi()

        reasons = []
        confidence = 0.5
        direction = "neutral"

        if sma_5 > sma_20 and rsi < 70:
            direction = "long"
            confidence = min(0.8, 0.5 + (sma_5 - sma_20) / sma_20)
            reasons.append(f"SMA5({sma_5:.2f}) > SMA20({sma_20:.2f})")
            reasons.append(f"RSI({rsi:.1f}) not overbought")
        elif sma_5 < sma_20 and rsi > 30:
            direction = "short"
            confidence = min(0.8, 0.5 + (sma_20 - sma_5) / sma_20)
            reasons.append(f"SMA5({sma_5:.2f}) < SMA20({sma_20:.2f})")
            reasons.append(f"RSI({rsi:.1f}) not oversold")

        signal = GoldSignal(datetime.now(), direction, confidence, reasons)
        self.signals.append(signal)
        return signal

    def _calc_rsi(self, period: int = 14) -> float:
        if len(self.prices) < period + 1:
            return 50.0
        deltas = np.diff(self.prices[-period - 1:])
        gains = np.sum(deltas[deltas > 0])
        losses = abs(np.sum(deltas[deltas < 0]))
        if losses == 0:
            return 100.0
        rs = gains / losses
        return 100.0 - (100.0 / (1.0 + rs))
