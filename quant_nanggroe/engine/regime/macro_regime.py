import logging
from typing import Dict
from quant_nanggroe.engine.regime.hmm_detector import RegimeState, Regime

logger = logging.getLogger(__name__)


class MacroRegimeDetector:
    def __init__(self):
        self.quadrants = ["GROWTH_INFLATION", "GROWTH_DEFLATION", "RECESSION_INFLATION", "RECESSION_DEFLATION"]

    def predict(self, gdp_growth: float, inflation: float) -> RegimeState:
        growth_positive = gdp_growth > 0
        inflation_high = inflation > 2.0
        if growth_positive and inflation_high:
            regime = Regime.BULL
            quadrant = "GROWTH_INFLATION"
            confidence = 0.7
        elif growth_positive and not inflation_high:
            regime = Regime.BULL
            quadrant = "GROWTH_DEFLATION"
            confidence = 0.8
        elif not growth_positive and inflation_high:
            regime = Regime.CRISIS
            quadrant = "RECESSION_INFLATION"
            confidence = 0.75
        else:
            regime = Regime.BEAR
            quadrant = "RECESSION_DEFLATION"
            confidence = 0.65
        return RegimeState(
            regime=regime, confidence=confidence, method="macro",
            features={"gdp_growth": gdp_growth, "inflation": inflation, "quadrant": quadrant},
        )
