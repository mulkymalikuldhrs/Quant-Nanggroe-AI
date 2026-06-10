#!/usr/bin/env python3
"""
Technical Analyst Agent (L2 - Analysis Layer)
SMC Structure Detection: BOS/CHoCH/OB/FVG/Sweeps
Indicators: RSI, EMA, ATR, MACD, Volume Profile
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, List

logger = logging.getLogger("HermesQuantOS.TechnicalAnalysis")


class TechnicalAnalysisTool:
    """L2 Agent: Technical Analyst - SMC & Indicator Analysis"""

    def __init__(self):
        self.analysis_cache = {}

    def analyze(self, symbol: str = "XAUUSD", interval: str = "1h") -> str:
        """
        Full technical analysis including SMC structure detection and indicators.
        """
        try:
            # Get OHLCV data first
            from tools.market_data_tool import MarketDataTool
            mdt = MarketDataTool()
            raw_data = json.loads(mdt.get_ohlcv(symbol, interval, 100))

            if "error" in raw_data:
                return json.dumps(raw_data)

            data = raw_data.get("data", [])
            if len(data) < 20:
                return json.dumps({"error": "Insufficient data for analysis", "bars": len(data)})

            # Run all analysis modules
            smc = self._detect_smc_structure(data)
            indicators = self._calculate_indicators(data)
            thesis = self._generate_technical_thesis(smc, indicators, data)

            result = {
                "symbol": symbol,
                "interval": interval,
                "timestamp": datetime.now().isoformat(),
                "latest_price": data[-1]["close"],
                "smc_structure": smc,
                "indicators": indicators,
                "technical_thesis": thesis
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e), "symbol": symbol})

    def _detect_smc_structure(self, data: List[Dict]) -> Dict:
        """Smart Money Concepts structure detection"""
        closes = [d["close"] for d in data]
        highs = [d["high"] for d in data]
        lows = [d["low"] for d in data]

        structure = {
            "trend": "neutral",
            "swing_highs": [],
            "swing_lows": [],
            "bos": [],  # Break of Structure
            "choch": [],  # Change of Character
            "order_blocks": [],
            "fvgs": [],  # Fair Value Gaps
            "liquidity_sweeps": []
        }

        # Detect swing points (3-candle pattern)
        for i in range(1, len(highs) - 1):
            if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
                structure["swing_highs"].append({
                    "index": i, "price": highs[i],
                    "time": data[i].get("time", "")
                })
            if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
                structure["swing_lows"].append({
                    "index": i, "price": lows[i],
                    "time": data[i].get("time", "")
                })

        # Determine trend from swing structure
        if len(structure["swing_highs"]) >= 2 and len(structure["swing_lows"]) >= 2:
            last_two_highs = [sh["price"] for sh in structure["swing_highs"][-2:]]
            last_two_lows = [sl["price"] for sl in structure["swing_lows"][-2:]]

            if last_two_highs[1] > last_two_highs[0] and last_two_lows[1] > last_two_lows[0]:
                structure["trend"] = "bullish"
            elif last_two_highs[1] < last_two_highs[0] and last_two_lows[1] < last_two_lows[0]:
                structure["trend"] = "bearish"

        # Detect BOS (Break of Structure)
        for i in range(1, len(structure["swing_highs"])):
            prev_high = structure["swing_highs"][i-1]["price"]
            curr_high = structure["swing_highs"][i]["price"]
            if curr_high > prev_high and structure["trend"] == "bullish":
                structure["bos"].append({
                    "type": "bullish_bos",
                    "price": prev_high,
                    "broken_at": structure["swing_highs"][i]["time"]
                })

        for i in range(1, len(structure["swing_lows"])):
            prev_low = structure["swing_lows"][i-1]["price"]
            curr_low = structure["swing_lows"][i]["price"]
            if curr_low < prev_low and structure["trend"] == "bearish":
                structure["bos"].append({
                    "type": "bearish_bos",
                    "price": prev_low,
                    "broken_at": structure["swing_lows"][i]["time"]
                })

        # Detect CHoCH (Change of Character)
        if len(structure["swing_highs"]) >= 2 and len(structure["swing_lows"]) >= 2:
            last_high = structure["swing_highs"][-1]["price"]
            prev_high = structure["swing_highs"][-2]["price"]
            last_low = structure["swing_lows"][-1]["price"]
            prev_low = structure["swing_lows"][-2]["price"]

            if structure["trend"] == "bullish" and last_low < prev_low:
                structure["choch"].append({
                    "type": "bearish_choch",
                    "price": prev_low,
                    "signal": "Potential bearish reversal"
                })
            elif structure["trend"] == "bearish" and last_high > prev_high:
                structure["choch"].append({
                    "type": "bullish_choch",
                    "price": prev_high,
                    "signal": "Potential bullish reversal"
                })

        # Detect Order Blocks (simplified - last opposing candle before impulse)
        for i in range(2, len(data) - 1):
            body = abs(closes[i] - data[i]["open"])
            prev_body = abs(closes[i-1] - data[i-1]["open"])
            if body > prev_body * 2:  # Impulse candle
                if closes[i] > data[i]["open"]:  # Bullish impulse
                    if closes[i-1] < data[i-1]["open"]:  # Previous bearish
                        structure["order_blocks"].append({
                            "type": "bullish_ob",
                            "high": data[i-1]["high"],
                            "low": data[i-1]["low"],
                            "index": i-1
                        })
                else:  # Bearish impulse
                    if closes[i-1] > data[i-1]["open"]:  # Previous bullish
                        structure["order_blocks"].append({
                            "type": "bearish_ob",
                            "high": data[i-1]["high"],
                            "low": data[i-1]["low"],
                            "index": i-1
                        })

        # Detect Fair Value Gaps
        for i in range(2, len(data)):
            # Bullish FVG: gap between candle[i-2].high and candle[i].low
            if lows[i] > highs[i-2]:
                structure["fvgs"].append({
                    "type": "bullish_fvg",
                    "top": lows[i],
                    "bottom": highs[i-2],
                    "size": round(lows[i] - highs[i-2], 5),
                    "index": i-1
                })
            # Bearish FVG: gap between candle[i-2].low and candle[i].high
            if highs[i] < lows[i-2]:
                structure["fvgs"].append({
                    "type": "bearish_fvg",
                    "top": lows[i-2],
                    "bottom": highs[i],
                    "size": round(lows[i-2] - highs[i], 5),
                    "index": i-1
                })

        # Limit results to most recent
        structure["order_blocks"] = structure["order_blocks"][-5:]
        structure["fvgs"] = structure["fvgs"][-5:]

        return structure

    def _calculate_indicators(self, data: List[Dict]) -> Dict:
        """Calculate technical indicators"""
        closes = [d["close"] for d in data]
        highs = [d["high"] for d in data]
        lows = [d["low"] for d in data]
        volumes = [d.get("volume", 0) for d in data]

        indicators = {}

        # RSI (14)
        if len(closes) >= 15:
            indicators["rsi_14"] = self._calculate_rsi(closes, 14)

        # EMA 20, 50, 200
        for period in [20, 50, 200]:
            if len(closes) >= period:
                indicators[f"ema_{period}"] = round(self._calculate_ema(closes, period), 5)

        # ATR (14)
        if len(closes) >= 15:
            indicators["atr_14"] = round(self._calculate_atr(highs, lows, closes, 14), 5)

        # MACD
        if len(closes) >= 26:
            macd_data = self._calculate_macd(closes)
            indicators["macd"] = macd_data

        # Volume analysis
        if volumes and sum(volumes) > 0:
            avg_vol = sum(volumes[-20:]) / 20
            last_vol = volumes[-1]
            indicators["volume"] = {
                "last": last_vol,
                "avg_20": round(avg_vol, 0),
                "ratio": round(last_vol / avg_vol, 2) if avg_vol > 0 else 0,
                "signal": "high" if last_vol > avg_vol * 1.5 else "normal" if last_vol > avg_vol * 0.5 else "low"
            }

        return indicators

    def _calculate_rsi(self, closes: List[float], period: int = 14) -> float:
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return round(rsi, 2)

    def _calculate_ema(self, data: List[float], period: int) -> float:
        multiplier = 2 / (period + 1)
        ema = sum(data[:period]) / period
        for price in data[period:]:
            ema = (price - ema) * multiplier + ema
        return ema

    def _calculate_atr(self, highs: List[float], lows: List[float],
                       closes: List[float], period: int = 14) -> float:
        true_ranges = []
        for i in range(1, len(closes)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            true_ranges.append(tr)

        if len(true_ranges) < period:
            return sum(true_ranges) / len(true_ranges) if true_ranges else 0

        atr = sum(true_ranges[:period]) / period
        for tr in true_ranges[period:]:
            atr = (atr * (period - 1) + tr) / period
        return atr

    def _calculate_macd(self, closes: List[float]) -> Dict:
        ema12 = self._calculate_ema(closes, 12)
        ema26 = self._calculate_ema(closes, 26)
        macd_line = ema12 - ema26
        return {
            "macd_line": round(macd_line, 5),
            "signal": "bullish" if macd_line > 0 else "bearish",
            "histogram_direction": "expanding" if len(closes) > 1 else "unknown"
        }

    def _generate_technical_thesis(self, smc: Dict, indicators: Dict,
                                    data: List[Dict]) -> Dict:
        """Generate technical thesis from all analysis"""
        latest_close = data[-1]["close"]
        trend = smc.get("trend", "neutral")

        # Confluence scoring
        confluences = 0
        total_possible = 5

        # 1. Trend alignment
        if trend != "neutral":
            confluences += 1

        # 2. RSI not overbought/oversold against trend
        rsi = indicators.get("rsi_14", 50)
        if trend == "bullish" and rsi < 70:
            confluences += 1
        elif trend == "bearish" and rsi > 30:
            confluences += 1
        elif trend == "neutral":
            confluences += 0.5

        # 3. EMA alignment
        ema20 = indicators.get("ema_20")
        ema50 = indicators.get("ema_50")
        if ema20 and ema50:
            if trend == "bullish" and ema20 > ema50:
                confluences += 1
            elif trend == "bearish" and ema20 < ema50:
                confluences += 1

        # 4. Order block presence
        obs = smc.get("order_blocks", [])
        if obs:
            confluences += 1

        # 5. FVG presence (means imbalance exists)
        fvgs = smc.get("fvgs", [])
        if fvgs:
            confluences += 1

        bias = "continuation" if smc.get("bos") else "reversal" if smc.get("choch") else "neutral"

        return {
            "bias": f"{trend}_{bias}" if trend != "neutral" else "neutral_no_bias",
            "confluence_score": f"{confluences}/{total_possible}",
            "confluence_pct": round(confluences / total_possible * 100, 0),
            "min_required": 3,
            "tradeable": confluences >= 3,
            "key_levels": {
                "nearest_ob": obs[-1] if obs else None,
                "nearest_fvg": fvgs[-1] if fvgs else None,
                "recent_swing_high": smc["swing_highs"][-1]["price"] if smc["swing_highs"] else None,
                "recent_swing_low": smc["swing_lows"][-1]["price"] if smc["swing_lows"] else None,
            },
            "rsi_status": "overbought" if rsi > 70 else "oversold" if rsi < 30 else "neutral",
            "recommendation": self._make_recommendation(trend, bias, confluences, indicators)
        }

    def _make_recommendation(self, trend: str, bias: str, confluences: float,
                             indicators: Dict) -> str:
        if confluences < 3:
            return "NO TRADE - Insufficient confluence. Wait for better setup."

        rsi = indicators.get("rsi_14", 50)

        if trend == "bullish" and bias == "continuation":
            if rsi < 70:
                return "BULLISH CONTINUATION - Look for pullback to OB/FVG for long entry"
            else:
                return "BULLISH BUT OVERBOUGHT - Wait for RSI pullback before entry"

        if trend == "bearish" and bias == "continuation":
            if rsi > 30:
                return "BEARISH CONTINUATION - Look for pullback to OB/FVG for short entry"
            else:
                return "BEARISH BUT OVERSOLD - Wait for RSI bounce before entry"

        if bias == "reversal":
            return f"REVERSAL SIGNAL - {trend} trend may be reversing. Wait for confirmation."

        return "NEUTRAL - No clear edge. Stay flat."
