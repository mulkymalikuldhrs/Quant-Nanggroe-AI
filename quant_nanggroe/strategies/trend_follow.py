"""
Multi-Timeframe Trend Following
================================
Ensemble of trend signals across multiple timeframes:
- 20d MA vs 100d MA crossover
- 50d MA slope (linear regression)
- 12-month momentum (skip 1 month)

Combined via sigmoid-weighted ensemble.
"""

import logging
from typing import Dict, List

import numpy as np

log = logging.getLogger("QNA.TrendFollow")


class TrendFollow:
    def __init__(self):
        self.fast_ma = 20
        self.slow_ma = 100
        self.slope_window = 50
        self.momentum_window = 252
        self.momentum_skip = 21

    def _ma_crossover(self, closes: np.ndarray) -> float:
        if len(closes) < self.slow_ma:
            return 0.0
        fast = np.mean(closes[-self.fast_ma:])
        slow = np.mean(closes[-self.slow_ma:])
        if slow == 0:
            return 0.0
        return (fast - slow) / slow

    def _ma_slope(self, closes: np.ndarray) -> float:
        if len(closes) < self.slope_window:
            return 0.0
        y = closes[-self.slope_window:]
        x = np.arange(len(y), dtype=np.float64)
        n = len(y)
        sx, sy = x.sum(), y.sum()
        sxx = (x * x).sum()
        sxy = (x * y).sum()
        slope = (n * sxy - sx * sy) / (n * sxx - sx * sx + 1e-10)
        return slope / (np.mean(y) + 1e-10)

    def _momentum(self, closes: np.ndarray) -> float:
        if len(closes) < self.momentum_window:
            return 0.0
        start = closes[-self.momentum_window + self.momentum_skip]
        if start == 0:
            return 0.0
        return (closes[-1] - start) / start

    def _sigmoid(self, x: float) -> float:
        return 1.0 / (1.0 + np.exp(-4.0 * x))

    def analyze(self, closes: List[float]) -> Dict:
        arr = np.array(closes, dtype=np.float64)
        if len(arr) < self.slow_ma:
            return {"signal": "hold", "confidence": 0.0, "strength": 0.0}

        ma_sig = self._ma_crossover(arr) * 1.0
        slope_sig = self._ma_slope(arr) * 10.0
        mom_sig = self._momentum(arr) * 2.0

        ensemble = (ma_sig + slope_sig + mom_sig) / 3.0
        prob = self._sigmoid(ensemble)
        strength = (prob - 0.5) * 2.0

        sig = "buy" if strength > 0.3 else ("sell" if strength < -0.3 else "hold")
        return {
            "signal": sig,
            "confidence": round(abs(strength), 3),
            "strength": round(float(strength), 3),
            "ma_crossover": round(float(ma_sig), 5),
            "ma_slope": round(float(slope_sig), 5),
            "momentum": round(float(mom_sig), 5),
            "ensemble": round(float(ensemble), 5),
        }

    def __repr__(self):
        return f"TrendFollow(fast={self.fast_ma},slow={self.slow_ma})"
