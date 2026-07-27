"""
.. deprecated::
   This is a numpy-native strategy used by ``live_engine.py``.  It has a
   different interface than the ``Strategy`` base class in
   ``engine/strategies/``.  Migrate to the Strategy base class and register
   via ``@StrategyRegistry.register`` for walk-forward integration.

Time-Series Momentum (Moskowitz, Ooi, Pedersen 2012)
=====================================================
Signal = sign(return over past 12 months, skip 1 month)
Vol-scaling to target annualized volatility
Works on any asset: stocks, crypto, FX, futures

Reference: Moskowitz, Ooi, Pedersen (2012), Journal of Financial Economics
"""

import logging
from typing import Dict, List

import numpy as np

log = logging.getLogger("QNA.TSMOM")


class TSMOM:
    def __init__(self, lookback: int = 252, skip: int = 21,
                 vol_target: float = 0.40, vol_halflife: int = 60):
        self.lookback = lookback
        self.skip = skip
        self.vol_target = vol_target
        self.vol_halflife = vol_halflife

    def _ewm_vol(self, returns: np.ndarray) -> float:
        alpha = 1 - np.exp(-np.log(2) / self.vol_halflife)
        w = (1 - alpha) ** np.arange(len(returns))[::-1]
        w /= w.sum()
        mean = np.average(returns, weights=w)
        var = np.average((returns - mean) ** 2, weights=w)
        return np.sqrt(var)

    def analyze(self, closes: List[float]) -> Dict:
        if len(closes) < self.lookback + 1:
            return {"signal": "hold", "confidence": 0.0, "strength": 0.0}
        prices = np.array(closes, dtype=np.float64)
        rets = np.diff(prices) / prices[:-1]

        period_return = (prices[-1] - prices[-self.lookback + self.skip]) / prices[-self.lookback + self.skip]
        vol = self._ewm_vol(rets[-self.vol_halflife * 3:])
        if vol < 1e-10:
            return {"signal": "hold", "confidence": 0.0, "strength": 0.0}

        raw_signal = np.sign(period_return)
        vol_scaled = self.vol_target / (vol * np.sqrt(252))
        capped = np.clip(vol_scaled, 0.0, 2.0)
        strength = raw_signal * capped
        confidence = min(abs(period_return) / (vol * np.sqrt(self.lookback / 252)), 1.0)

        sig = "buy" if strength > 0.3 else ("sell" if strength < -0.3 else "hold")
        return {"signal": sig, "confidence": round(confidence, 3),
                "strength": round(float(strength), 3),
                "raw_return": round(float(period_return), 5),
                "vol": round(float(vol), 6)}

    def __repr__(self):
        return f"TSMOM(lookback={self.lookback},skip={self.skip},vol_target={self.vol_target})"
