import logging
import numpy as np
from typing import List, Optional
from quant_nanggroe.engine.regime.hmm_detector import RegimeState, Regime

logger = logging.getLogger(__name__)


class VolatilityRegimeDetector:
    def __init__(self, lookback: int = 21):
        self.lookback = lookback
        self.historical_vols: List[float] = []
        self.is_fitted = False

    def fit(self, returns: List[float]) -> "VolatilityRegimeDetector":
        if len(returns) < self.lookback:
            return self
        arr = np.array(returns)
        self.historical_vols = []
        for i in range(self.lookback - 1, len(returns)):
            vol = float(np.std(arr[i - self.lookback + 1: i + 1]))
            self.historical_vols.append(vol)
        self.is_fitted = True
        return self

    def predict(self, returns: List[float]) -> RegimeState:
        if len(returns) < self.lookback:
            return RegimeState(regime=Regime.LOW_VOL, confidence=0.0, method="volatility")
        if not self.is_fitted:
            self.fit(returns)
        current_vol = float(np.std(returns[-self.lookback:]))
        if self.historical_vols:
            mean_vol = np.mean(self.historical_vols)
            std_vol = np.std(self.historical_vols) or 1e-8
            z_score = (current_vol - mean_vol) / std_vol
            if z_score > 1.5:
                regime = Regime.HIGH_VOL
                confidence = min(0.95, 0.5 + abs(z_score) * 0.1)
            elif z_score < -1.0:
                regime = Regime.LOW_VOL
                confidence = min(0.95, 0.5 + abs(z_score) * 0.1)
            else:
                regime = Regime.SIDEWAYS
                confidence = 0.5
        else:
            regime = Regime.SIDEWAYS
            confidence = 0.5
        return RegimeState(
            regime=regime, confidence=confidence, method="volatility",
            features={"current_vol": round(current_vol, 6), "z_score": round(float(z_score) if self.historical_vols else 0.0, 4)},
        )
