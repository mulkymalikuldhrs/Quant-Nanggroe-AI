#!/usr/bin/env python3
"""
Pressure Normalization Engine (from Quant-Nanggroe-AI)
======================================================
Converts all sensor/agent outputs → BUY_PRESSURE / SELL_PRESSURE
Normalized to 0.0 - 1.0 scale for deterministic decision synthesis.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger("HermesQuantOS.PressureEngine")


class PressureNormalizationEngine:
    """
    Compiles all sensor outputs into normalized pressure vectors.
    
    Source: Quant-Nanggroe-AI v15.2.0 Pressure Normalization Engine
    Adapted for Hermes Quant OS Python backend.
    """

    # Sensor weight configuration
    SENSOR_WEIGHTS = {
        "quant_scanner": 0.30,     # Trend/ADX signals
        "smc_agent": 0.25,         # Smart Money Concepts
        "news_sentinel": 0.20,     # News/sentiment impact
        "flow_agent": 0.25,        # Whale/flow signals
    }

    def __init__(self):
        self.buy_pressure = 0.0
        self.sell_pressure = 0.0
        self.confidence = 0.0
        self.sensor_outputs = {}

    def compile_pressure(self, 
                          trend_direction: str = "neutral",
                          trend_strength: float = 0.0,
                          smc_signal: str = "none",
                          displacement_strength: float = 0.0,
                          liquidity_sweep: bool = False,
                          news_impact: float = 0.0,
                          news_uncertainty: float = 0.5,
                          flow_imbalance: float = 0.0,
                          flow_direction: str = "neutral") -> Dict:
        """
        Compile all sensor outputs into normalized pressure vectors.
        
        Returns:
            Dict with buy_pressure, sell_pressure, confidence, verdict
        """
        buy = 0.0
        sell = 0.0

        # Quant Scanner contribution (trend + ADX)
        weight = self.SENSOR_WEIGHTS["quant_scanner"]
        if trend_direction == "bullish":
            buy += weight * trend_strength
        elif trend_direction == "bearish":
            sell += weight * trend_strength

        # SMC Agent contribution
        weight = self.SENSOR_WEIGHTS["smc_agent"]
        if smc_signal == "bullish_bos" or smc_signal == "bullish_choch":
            buy += weight * displacement_strength
        elif smc_signal == "bearish_bos" or smc_signal == "bearish_choch":
            sell += weight * displacement_strength

        if liquidity_sweep:
            # Liquidity sweep adds to both sides equally (displacement direction unknown)
            buy += weight * 0.2 * displacement_strength
            sell += weight * 0.2 * displacement_strength

        # News Sentinel contribution (logarithmic time decay applied externally)
        weight = self.SENSOR_WEIGHTS["news_sentinel"]
        # News adds pressure based on impact, reduced by uncertainty
        directional_factor = (1.0 - news_uncertainty)
        buy += weight * news_impact * directional_factor
        sell += weight * news_impact * news_uncertainty

        # Flow Agent contribution (whale/COT positioning)
        weight = self.SENSOR_WEIGHTS["flow_agent"]
        if flow_direction == "long":
            buy += weight * flow_imbalance
        elif flow_direction == "short":
            sell += weight * flow_imbalance

        # Normalize pressures to 0.0 - 1.0
        total = buy + sell
        if total > 0:
            self.buy_pressure = buy / total
            self.sell_pressure = sell / total
            self.confidence = max(buy, sell) / total
        else:
            self.buy_pressure = 0.0
            self.sell_pressure = 0.0
            self.confidence = 0.0

        # Determine verdict
        if self.buy_pressure > 0.7:
            verdict = "STRONG_BUY"
        elif self.buy_pressure > 0.55:
            verdict = "BUY"
        elif self.sell_pressure > 0.7:
            verdict = "STRONG_SELL"
        elif self.sell_pressure > 0.55:
            verdict = "SELL"
        else:
            verdict = "NEUTRAL"

        result = {
            "buy_pressure": round(self.buy_pressure, 4),
            "sell_pressure": round(self.sell_pressure, 4),
            "confidence": round(self.confidence, 4),
            "verdict": verdict,
            "raw_buy": round(buy, 4),
            "raw_sell": round(sell, 4),
            "sensor_inputs": {
                "trend": f"{trend_direction} ({trend_strength:.2f})",
                "smc": smc_signal,
                "displacement": f"{displacement_strength:.2f}",
                "liquidity_sweep": liquidity_sweep,
                "news_impact": f"{news_impact:.2f}",
                "flow": f"{flow_direction} ({flow_imbalance:.2f})"
            },
            "timestamp": datetime.now().isoformat()
        }

        self.sensor_outputs = result
        return result

    def get_pressure(self) -> Dict:
        """Get current pressure state"""
        return self.sensor_outputs

    def normalize(self, symbol: str = "XAUUSD") -> str:
        """
        Auto-normalize pressure for a symbol by fetching technical data.
        """
        try:
            from tools.technical_analysis_tool import TechnicalAnalysisTool
            from tools.news_sentinel import NewsSentinelTool

            tat = TechnicalAnalysisTool()
            analysis = json.loads(tat.analyze(symbol, "1h"))

            if "error" in analysis:
                return json.dumps({"error": analysis["error"]})

            smc = analysis.get("smc_structure", {})
            indicators = analysis.get("indicators", {})

            trend_direction = smc.get("trend", "neutral")
            trend_strength = 0.7 if trend_direction != "neutral" else 0.3

            # Get BOS/CHoCH for SMC signal
            bos_list = smc.get("bos", [])
            smc_signal = "none"
            if bos_list:
                latest_bos = bos_list[-1].get("type", "")
                smc_signal = latest_bos

            displacement_strength = 0.6 if bos_list else 0.2
            liquidity_sweep = len(smc.get("liquidity_sweeps", [])) > 0

            result = self.compile_pressure(
                trend_direction=trend_direction,
                trend_strength=trend_strength,
                smc_signal=smc_signal,
                displacement_strength=displacement_strength,
                liquidity_sweep=liquidity_sweep,
            )

            return json.dumps(result, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e)})

    def status(self) -> str:
        """Get pressure engine status"""
        return json.dumps({
            "current_pressure": self.sensor_outputs,
            "weights": self.SENSOR_WEIGHTS,
            "timestamp": datetime.now().isoformat()
        }, indent=2)
