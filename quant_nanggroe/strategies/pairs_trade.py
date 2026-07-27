"""
.. deprecated::
   This is a numpy-native strategy used by ``live_engine.py``.  It has a
   different interface than the ``Strategy`` base class in
   ``engine/strategies/``.  Migrate to the Strategy base class and register
   via ``@StrategyRegistry.register`` for walk-forward integration.

Pairs Trading via Cointegration (Gatev, Goetzmann, Rouwenhorst 2006)
====================================================================
Find cointegrated pairs, trade mean reversion of spread.

Simplified: uses correlation proxy + z-score of ratio.
Full cointegration requires statsmodels (available).
"""

import logging
from typing import Dict, List

import numpy as np

log = logging.getLogger("QNA.Pairs")


class PairsTrade:
    def __init__(self, lookback: int = 60, entry_z: float = 2.0,
                 exit_z: float = 0.5):
        self.lookback = lookback
        self.entry_z = entry_z
        self.exit_z = exit_z

    def analyze_pair(self, price_a: List[float], price_b: List[float]) -> Dict:
        a = np.array(price_a, dtype=np.float64)
        b = np.array(price_b, dtype=np.float64)
        n = min(len(a), len(b))
        if n < self.lookback:
            return {"signal": "hold", "confidence": 0.0}

        a, b = a[-n:], b[-n:]
        ratio = a / (b + 1e-10)
        look_ratio = ratio[-self.lookback:]
        mean_r = np.mean(look_ratio)
        std_r = np.std(look_ratio)
        if std_r < 1e-10:
            return {"signal": "hold", "confidence": 0.0}

        current_z = (ratio[-1] - mean_r) / std_r
        conf = min(abs(current_z) / self.entry_z, 1.0)

        if abs(current_z) < self.exit_z:
            return {"signal": "close", "z_score": round(float(current_z), 3),
                    "confidence": round(float(conf), 3)}
        if current_z > self.entry_z:
            return {"signal": "sell", "z_score": round(float(current_z), 3),
                    "confidence": round(float(conf), 3)}
        if current_z < -self.entry_z:
            return {"signal": "buy", "z_score": round(float(current_z), 3),
                    "confidence": round(float(conf), 3)}
        return {"signal": "hold", "z_score": round(float(current_z), 3),
                "confidence": round(float(conf), 3)}

    def __repr__(self):
        return f"PairsTrade(lookback={self.lookback},entry_z={self.entry_z})"
