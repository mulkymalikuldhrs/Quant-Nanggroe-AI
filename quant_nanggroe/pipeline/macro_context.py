from __future__ import annotations

import logging
from typing import Any

from quant_nanggroe.engine.causal.master_engine import MasterQuantNanggroeEngine
from quant_nanggroe.engine.causal.lead_lag import FuturesLeadLagMatrix
from quant_nanggroe.engine.causal.weather_matrix import MacroWeatherEngine, WeatherRegime
from quant_nanggroe.engine.causal.cot_provider import COTProvider
from quant_nanggroe.engine.causal.thesis_guard import ThesisDriftGuard

logger = logging.getLogger("QNA-MacroContext")


class MacroContextProvider:
    """Integrates all macro engines into the pipeline as upstream context."""

    def __init__(self):
        self.master = MasterQuantNanggroeEngine()
        self.lead_lag = FuturesLeadLagMatrix()
        self.weather = MacroWeatherEngine()
        self.cot = COTProvider()
        self.thesis = ThesisDriftGuard()

    def get_signal_context(self, symbol: str) -> dict[str, Any]:
        spot = self.lead_lag.resolve_spot(symbol) or symbol
        futures_pair = self.lead_lag.get_pair(symbol) or self.lead_lag.get_pair(spot)

        context: dict[str, Any] = {
            "macro_bias": 0.0,
            "macro_weather": "UNKNOWN",
            "cot_signal": "neutral",
            "lead_lag": {},
            "weather_profile": {},
            "thesis_ok": True,
        }

        weather_bias = self.weather.bias_for_asset(symbol)
        if weather_bias != 0:
            context["macro_bias"] = weather_bias
        context["macro_weather"] = self.weather.to_dict()["current_regime"]
        context["weather_profile"] = self.weather.to_dict()

        cot_pos = self.cot.evaluate_positioning(symbol)
        context["cot_signal"] = cot_pos.get("signal", "neutral")

        if futures_pair:
            context["lead_lag"] = {
                "futures": futures_pair.futures,
                "spot": futures_pair.spot,
                "asset_class": futures_pair.asset_class.value,
                "lead_lag_type": futures_pair.lead_lag.value,
                "correlated_pairs": futures_pair.correlated_pairs or [],
            }

        thesis_check = self.thesis.check_macro_surprise_thesis(0.0, symbol, "HOLD")
        context["thesis_ok"] = not thesis_check.get("alarm", False)

        return context

    def apply_macro_filter(self, symbol: str, signal_side: str, confidence: float) -> tuple[str, float, str]:
        context = self.get_signal_context(symbol)

        # Macro weather override
        weather_signal = self.weather.signal_for_asset(symbol)
        if weather_signal and weather_signal != signal_side:
            weather_bias = self.weather.bias_for_asset(symbol)
            if abs(weather_bias) > 0.6:
                return ("hold", 0.0, f"Weather {context['macro_weather']} blocks {signal_side} ({weather_signal} preferred)")

        # COT extreme filter
        cot_signal = context["cot_signal"]
        if cot_signal in ("extremely_overbought", "extremely_oversold"):
            if (cot_signal == "extremely_overbought" and signal_side == "buy") or (cot_signal == "extremely_oversold" and signal_side == "sell"):
                confidence = confidence * 0.5
                return (signal_side, confidence, f"COT {cot_signal} reduces confidence for {signal_side}")

        # Thesis check blocks trades if macro surprise contradicts
        if not context["thesis_ok"]:
            return ("hold", 0.0, "Macro surprise contradicts trade direction")

        return (signal_side, confidence, "Macro filter passed")
