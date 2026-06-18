import logging
import numpy as np
from typing import Optional
from quant_nanggroe.engine.regime.hmm_detector import RegimeState, Regime

logger = logging.getLogger(__name__)


class CorrelationRegimeDetector:
    def __init__(self, window: int = 63):
        self.window = window

    def predict(self, returns_matrix: np.ndarray) -> RegimeState:
        n = returns_matrix.shape[0]
        if n < self.window:
            return RegimeState(regime=Regime.SIDEWAYS, confidence=0.0, method="correlation")
        recent = returns_matrix[-self.window:]
        corr = np.corrcoef(recent.T)
        n_assets = corr.shape[0]
        if n_assets < 2:
            return RegimeState(regime=Regime.SIDEWAYS, confidence=0.5, method="correlation")
        upper_tri = corr[np.triu_indices_from(corr, k=1)]
        avg_corr = float(np.mean(upper_tri))
        if avg_corr > 0.7:
            regime = Regime.CRISIS
            confidence = 0.8
        elif avg_corr > 0.4:
            regime = Regime.BEAR
            confidence = 0.6
        elif avg_corr < 0.1:
            regime = Regime.BULL
            confidence = 0.7
        else:
            regime = Regime.SIDEWAYS
            confidence = 0.5
        return RegimeState(
            regime=regime, confidence=confidence, method="correlation",
            features={"avg_correlation": round(avg_corr, 4), "n_assets": n_assets},
        )
