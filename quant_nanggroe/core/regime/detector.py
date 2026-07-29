from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class RegimeLabel(str, Enum):
    RISK_ON = "RISK_ON"
    RISK_OFF = "RISK_OFF"
    CRISIS = "CRISIS"
    TRANSITION = "TRANSITION"
    NEUTRAL_MIXED = "NEUTRAL_MIXED"


@dataclass
class RegimeResult:
    label: RegimeLabel
    confidence: float
    signals: dict[str, float]


class RegimeDetector:
    def __init__(self, vol_threshold: float = 0.3, trend_threshold: float = 0.02):
        self.vol_threshold = vol_threshold
        self.trend_threshold = trend_threshold

    def detect(self, ctx: dict[str, Any]) -> RegimeResult:
        volatility = abs(ctx.get("volatility", 0.0))
        trend = ctx.get("trend", 0.0)
        dxy_change = ctx.get("dxy_change_pct", 0.0)
        vix_level = ctx.get("vix", 20.0)
        bond_yield_change = ctx.get("bond_zb_change_pct", 0.0)

        signals: dict[str, float] = {}

        is_high_vol = volatility > self.vol_threshold
        is_crisis_vol = volatility > self.vol_threshold * 2.5
        is_bullish_trend = trend > self.trend_threshold
        is_bearish_trend = trend < -self.trend_threshold
        dxy_falling = dxy_change < -0.5
        dxy_rising = dxy_change > 0.5
        vix_spike = vix_level > 30
        vix_crisis = vix_level > 45
        bonds_rising = bond_yield_change < -0.3
        bonds_falling = bond_yield_change > 0.3

        signals["volatility"] = volatility
        signals["trend"] = trend
        signals["dxy_change"] = dxy_change
        signals["vix"] = vix_level
        signals["bond_yield_change"] = bond_yield_change

        if is_crisis_vol and vix_crisis and (is_bearish_trend or dxy_rising):
            return RegimeResult(
                label=RegimeLabel.CRISIS,
                confidence=min(0.95, 0.5 + volatility * 0.5),
                signals=signals,
            )

        if is_high_vol and vix_spike:
            return RegimeResult(
                label=RegimeLabel.TRANSITION,
                confidence=min(0.8, 0.3 + volatility * 0.3),
                signals=signals,
            )

        if is_bullish_trend and dxy_falling and bonds_rising:
            return RegimeResult(
                label=RegimeLabel.RISK_ON,
                confidence=min(0.9, 0.4 + abs(trend) * 5),
                signals=signals,
            )

        if is_bearish_trend and (dxy_rising or bonds_falling):
            return RegimeResult(
                label=RegimeLabel.RISK_OFF,
                confidence=min(0.85, 0.3 + abs(trend) * 5),
                signals=signals,
            )

        return RegimeResult(
            label=RegimeLabel.NEUTRAL_MIXED,
            confidence=0.3,
            signals=signals,
        )
