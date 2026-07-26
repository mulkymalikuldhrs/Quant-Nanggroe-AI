from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class WeatherRegime(Enum):
    RISK_ON = "RISK_ON"
    RISK_OFF = "RISK_OFF"
    STAGFLATION = "STAGFLATION"
    LIQUIDITY_CRUNCH = "LIQUIDITY_CRUNCH"
    NEUTRAL = "NEUTRAL"


@dataclass
class WeatherProfile:
    regime: WeatherRegime
    description: str
    bullish_assets: list[str]
    bearish_assets: list[str]
    confidence: float


WEATHER_PROFILES: dict[WeatherRegime, WeatherProfile] = {
    WeatherRegime.RISK_ON: WeatherProfile(
        regime=WeatherRegime.RISK_ON,
        description="Risk appetite high, capital flowing into growth assets",
        bullish_assets=["ES1!", "NQ1!", "BTC1!", "6A1!", "NZDUSD"],
        bearish_assets=["GC1!", "ZB1!", "DXY"],
        confidence=0.8,
    ),
    WeatherRegime.RISK_OFF: WeatherProfile(
        regime=WeatherRegime.RISK_OFF,
        description="Capital flight to safety — geopolitical or economic crisis",
        bullish_assets=["GC1!", "ZB1!", "ZN1!", "DXY", "USDJPY"],
        bearish_assets=["ES1!", "NQ1!", "BTC1!", "6E1!", "AUDUSD"],
        confidence=0.85,
    ),
    WeatherRegime.STAGFLATION: WeatherProfile(
        regime=WeatherRegime.STAGFLATION,
        description="Stagnation + inflation — gold positive, bonds negative, equities mixed",
        bullish_assets=["GC1!", "SI1!", "DXY"],
        bearish_assets=["ZB1!", "ZN1!", "ES1!"],
        confidence=0.7,
    ),
    WeatherRegime.LIQUIDITY_CRUNCH: WeatherProfile(
        regime=WeatherRegime.LIQUIDITY_CRUNCH,
        description="Systemic liquidity contraction — USD surges, everything else sells off",
        bullish_assets=["DXY", "USDJPY"],
        bearish_assets=["ES1!", "NQ1!", "GC1!", "BTC1!", "6E1!", "6A1!"],
        confidence=0.9,
    ),
    WeatherRegime.NEUTRAL: WeatherProfile(
        regime=WeatherRegime.NEUTRAL,
        description="No clear macro signal — mixed conditions",
        bullish_assets=[],
        bearish_assets=[],
        confidence=0.3,
    ),
}


class MacroWeatherEngine:
    def __init__(self):
        self._history: list[WeatherRegime] = []

    def classify(
        self,
        dxy_change_pct: float,
        bond_zb_change_pct: float,
        bond_zn_change_pct: float = 0.0,
        es_change_pct: float = 0.0,
        vix_level: float | None = None,
        gold_change_pct: float = 0.0,
    ) -> WeatherRegime:
        regime: WeatherRegime = WeatherRegime.NEUTRAL

        # Liquidity crunch: DXY surging, equities crashing, bonds flat/down
        if dxy_change_pct > 0.5 and es_change_pct < -1.0 and bond_zb_change_pct < 0.1 and vix_level is not None and vix_level > 30:
            regime = WeatherRegime.LIQUIDITY_CRUNCH

        # Risk-off: DXY up, bonds up, equities down
        elif dxy_change_pct > 0.3 and bond_zb_change_pct > 0.2 and es_change_pct < -0.3:
            regime = WeatherRegime.RISK_OFF

        # Risk-on: DXY down, bonds down, equities up
        elif dxy_change_pct < -0.3 and bond_zb_change_pct < -0.1 and es_change_pct > 0.3:
            regime = WeatherRegime.RISK_ON

        # Stagflation: gold up, bonds down, equities flat/down
        elif gold_change_pct > 0.3 and bond_zb_change_pct < -0.2 and (vix_level is None or vix_level > 25):
            regime = WeatherRegime.STAGFLATION

        self._history.append(regime)
        return regime

    def get_profile(self, regime: WeatherRegime | None = None) -> WeatherProfile | None:
        key = regime or (self._history[-1] if self._history else None)
        if key is None:
            return None
        return WEATHER_PROFILES.get(key)

    def signal_for_asset(self, symbol: str) -> str | None:
        regime = self._history[-1] if self._history else None
        if regime is None:
            return None
        profile = WEATHER_PROFILES.get(regime)
        if not profile:
            return None
        if symbol in profile.bullish_assets:
            return "buy"
        if symbol in profile.bearish_assets:
            return "sell"
        return None

    def bias_for_asset(self, symbol: str) -> float:
        regime = self._history[-1] if self._history else None
        if regime is None:
            return 0.0
        profile = WEATHER_PROFILES.get(regime)
        if not profile:
            return 0.0
        if symbol in profile.bullish_assets:
            return profile.confidence
        if symbol in profile.bearish_assets:
            return -profile.confidence
        return 0.0

    def to_dict(self) -> dict[str, Any]:
        regime = self._history[-1] if self._history else None
        profile = self.get_profile(regime)
        return {
            "current_regime": regime.value if regime else "UNKNOWN",
            "description": profile.description if profile else "No data",
            "confidence": profile.confidence if profile else 0.0,
            "history": [r.value for r in self._history[-20:]],
        }
