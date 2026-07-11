#!/usr/bin/env python3
"""
Strategy Agent (L3 - Decision Layer)
3-Scenario Generator: Bullish / Bearish / Neutral
Confluence Scoring: Min 3/5 required
"""

import json
import logging
from datetime import datetime

logger = logging.getLogger("HermesQuantOS.Strategy")


class StrategyTool:
    """L3 Agent: Strategy - Multi-scenario analysis & confluence scoring"""

    def __init__(self):
        self.active_strategies = {}
        self.scenario_history = []

    def generate_scenarios(self, symbol: str = "XAUUSD", interval: str = "1h") -> str:
        """
        Generate 3 scenarios (Bullish/Bearish/Neutral) with confluence scoring.
        """
        # Get technical analysis via SharedState to avoid creating new instances per call
        from tools.shared_state import SharedState
        ta = SharedState().technical_analysis
        analysis = json.loads(ta.analyze(symbol, interval))

        if "error" in analysis:
            return json.dumps({"error": analysis["error"]})

        smc = analysis.get("smc_structure", {})
        indicators = analysis.get("indicators", {})
        thesis = analysis.get("technical_thesis", {})

        latest_close = analysis.get("latest_price", 0)
        trend = smc.get("trend", "neutral")

        # Get ATR for target calculation
        atr = indicators.get("atr_14", latest_close * 0.005)

        # Generate scenarios
        scenarios = {
            "bullish": self._build_scenario(
                "bullish", symbol, latest_close, atr, smc, indicators
            ),
            "bearish": self._build_scenario(
                "bearish", symbol, latest_close, atr, smc, indicators
            ),
            "neutral": self._build_scenario(
                "neutral", symbol, latest_close, atr, smc, indicators
            )
        }

        # Score confluence for each scenario
        for name, scenario in scenarios.items():
            scenario["confluence_score"] = self._score_confluence(
                name, smc, indicators, thesis
            )

        # Determine preferred scenario
        preferred = max(scenarios, key=lambda x: scenarios[x]["confluence_score"]["total"])
        if scenarios[preferred]["confluence_score"]["total"] < 3:
            preferred = "neutral"

        result = {
            "symbol": symbol,
            "interval": interval,
            "timestamp": datetime.now().isoformat(),
            "current_price": latest_close,
            "current_trend": trend,
            "scenarios": scenarios,
            "preferred_scenario": preferred,
            "tradeable": scenarios[preferred]["confluence_score"]["total"] >= 3,
            "recommendation": self._make_strategy_recommendation(
                preferred, scenarios[preferred], thesis
            )
        }

        self.scenario_history.append(result)
        return json.dumps(result, indent=2)

    def _build_scenario(self, direction: str, symbol: str, price: float,
                        atr: float, smc: dict, indicators: dict) -> dict:
        """Build a scenario with entry, SL, TP"""
        if direction == "bullish":
            entry = price
            sl = price - atr * 1.5
            tp1 = price + atr * 2.0
            tp2 = price + atr * 3.0
            bias = "continuation" if smc.get("trend") == "bullish" else "reversal"
        elif direction == "bearish":
            entry = price
            sl = price + atr * 1.5
            tp1 = price - atr * 2.0
            tp2 = price - atr * 3.0
            bias = "continuation" if smc.get("trend") == "bearish" else "reversal"
        else:  # neutral
            entry = price
            sl = price + atr * 2.0
            tp1 = price - atr * 1.0
            tp2 = price + atr * 1.0
            bias = "ranging"

        rr1 = abs(tp1 - entry) / abs(sl - entry) if abs(sl - entry) > 0 else 0
        rr2 = abs(tp2 - entry) / abs(sl - entry) if abs(sl - entry) > 0 else 0

        return {
            "direction": direction,
            "bias": bias,
            "entry": round(entry, 5),
            "stop_loss": round(sl, 5),
            "take_profit_1": round(tp1, 5),
            "take_profit_2": round(tp2, 5),
            "rr_ratio_1": f"1:{rr1:.1f}",
            "rr_ratio_2": f"1:{rr2:.1f}",
            "key_levels": {
                "nearest_ob": smc.get("order_blocks", [{}])[-1] if smc.get("order_blocks") else None,
                "nearest_fvg": smc.get("fvgs", [{}])[-1] if smc.get("fvgs") else None,
                "swing_high": smc.get("swing_highs", [{}])[-1].get("price") if smc.get("swing_highs") else None,
                "swing_low": smc.get("swing_lows", [{}])[-1].get("price") if smc.get("swing_lows") else None,
            }
        }

    def _score_confluence(self, scenario: str, smc: dict, indicators: dict,
                          thesis: dict) -> dict:
        """Score confluences (0-5 scale, need 3 minimum)"""
        score = 0
        details = []

        # 1. Trend alignment
        trend = smc.get("trend", "neutral")
        if (scenario == "bullish" and trend == "bullish") or \
           (scenario == "bearish" and trend == "bearish"):
            score += 1
            details.append("Trend aligned")
        elif scenario == "neutral" and trend == "neutral":
            score += 0.5
            details.append("Neutral trend - neutral scenario")

        # 2. BOS confirmation
        bos_list = smc.get("bos", [])
        if bos_list:
            latest_bos = bos_list[-1].get("type", "")
            if (scenario == "bullish" and "bullish" in latest_bos) or \
               (scenario == "bearish" and "bearish" in latest_bos):
                score += 1
                details.append("BOS confirmed")

        # 3. Order Block present
        obs = smc.get("order_blocks", [])
        if obs:
            latest_ob = obs[-1].get("type", "")
            if (scenario == "bullish" and "bullish" in latest_ob) or \
               (scenario == "bearish" and "bearish" in latest_ob):
                score += 1
                details.append("Order block present")

        # 4. RSI supports scenario
        rsi = indicators.get("rsi_14", 50)
        if scenario == "bullish" and rsi < 70:
            score += 1
            details.append(f"RSI supports ({rsi:.1f})")
        elif scenario == "bearish" and rsi > 30:
            score += 1
            details.append(f"RSI supports ({rsi:.1f})")

        # 5. EMA alignment
        ema20 = indicators.get("ema_20")
        ema50 = indicators.get("ema_50")
        if ema20 and ema50:
            if (scenario == "bullish" and ema20 > ema50) or \
               (scenario == "bearish" and ema20 < ema50):
                score += 1
                details.append("EMA alignment confirmed")

        return {
            "total": score,
            "min_required": 3,
            "passed": score >= 3,
            "details": details
        }

    def _make_strategy_recommendation(self, preferred: str, scenario: dict,
                                       thesis: dict) -> str:
        if not scenario["confluence_score"]["passed"]:
            return "NO TRADE - Insufficient confluence. Wait for better setup."

        direction = scenario["direction"].upper()
        entry = scenario["entry"]
        sl = scenario["stop_loss"]
        tp1 = scenario["take_profit_1"]
        rr = scenario["rr_ratio_1"]

        return (
            f"{direction} SETUP - Confluence {scenario['confluence_score']['total']}/5\n"
            f"Entry: {entry} | SL: {sl} | TP1: {tp1}\n"
            f"R:R = {rr}\n"
            f"Confluences: {', '.join(scenario['confluence_score']['details'])}\n"
            f"REQUIRES: Risk Officer approval before execution."
        )
