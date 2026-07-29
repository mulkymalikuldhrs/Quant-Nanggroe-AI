from __future__ import annotations

import logging
from typing import Any, Optional

from quant_nanggroe.core.scoring.base import BaseScorer, ScorerResult, _clamp

logger = logging.getLogger(__name__)

MACRO_WEATHER_BIAS: dict[str, dict[str, float]] = {
    "RISK_ON": {
        "GC1!": -0.4, "ES1!": 0.8, "DXY": -0.5,
        "ZB1!": -0.3, "6E1!": 0.5, "SI1!": 0.6,
    },
    "RISK_OFF": {
        "GC1!": 0.7, "ES1!": -0.8, "DXY": 0.5,
        "ZB1!": 0.6, "6E1!": -0.5, "SI1!": -0.4,
    },
    "NEUTRAL_MIXED": {
        "GC1!": 0.0, "ES1!": 0.0, "DXY": 0.0,
        "ZB1!": 0.0, "6E1!": 0.0, "SI1!": 0.0,
    },
}


class MacroScorer(BaseScorer):
    weight: float = 0.30

    def __init__(self, surprise_threshold: float = 1.5):
        self.surprise_threshold = surprise_threshold

    def score(self, ctx: dict[str, Any]) -> ScorerResult:
        macro_weather = ctx.get("macro_regime", "NEUTRAL_MIXED")
        dxy_change = ctx.get("dxy_change_pct", 0.0)
        zb_change = ctx.get("bond_zb_change_pct", 0.0)

        weather_bias = MACRO_WEATHER_BIAS.get(macro_weather, MACRO_WEATHER_BIAS["NEUTRAL_MIXED"])

        dxy_component = -_clamp(dxy_change / 2.0, -1.0, 1.0)
        composite = dxy_component * 0.5 + (weather_bias["ES1!"] - weather_bias["GC1!"]) * 0.5

        macro_regime = ctx.get("macro_regime", "NEUTRAL_MIXED")
        forecast_score = _clamp(composite * 100, -100.0, 100.0)
        confidence = min(abs(forecast_score) / 100.0, 1.0)

        if macro_regime == "NEUTRAL_MIXED":
            confidence *= 0.5

        return ScorerResult(
            score=forecast_score,
            confidence=confidence,
            metadata={
                "macro_weather": macro_weather,
                "dxy_component": dxy_component,
                "weather_bias": weather_bias,
                "macro_regime": macro_regime,
            },
        )
