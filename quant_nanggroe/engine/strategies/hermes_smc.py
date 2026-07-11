#!/usr/bin/env python3
"""
SMC Agent Enhanced (from AI-MultiColony-Ecosystem SmartMoneyTradingAgent)
=========================================================================
Proper data models: MarketStructurePoint, OrderBlock, FairValueGap,
LiquidityLevel, SmartMoneySetup, TradeExecution
ICT Concepts: Power of 3, Optimal Trade Entry (OTE)
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("HermesQuantOS.SMCAgentEnhanced")


@dataclass
class MarketStructurePoint:
    """Represents a swing point in market structure"""
    index: int
    price: float
    point_type: str  # HH, HL, LH, LL
    timestamp: str = ""
    strength: float = 1.0  # How significant (1-10)


@dataclass
class OrderBlock:
    """Institutional order block"""
    index: int
    high: float
    low: float
    ob_type: str  # bullish_ob, bearish_ob
    strength: float = 0.5  # 0-1 based on volume and displacement
    mitigated: bool = False
    mitigation_index: int = -1


@dataclass
class FairValueGap:
    """Fair Value Gap / Imbalance"""
    index: int
    top: float
    bottom: float
    fvg_type: str  # bullish_fvg, bearish_fvg
    size: float = 0.0
    filled: bool = False


@dataclass
class LiquidityLevel:
    """Liquidity pool at key price level"""
    price: float
    liq_type: str  # buy_side, sell_side
    strength: float = 0.5
    swept: bool = False
    sweep_index: int = -1


@dataclass
class SmartMoneySetup:
    """Complete SMC trade setup"""
    setup_type: str  # OTE, BOS, MSS, FVG_OB
    direction: str  # BULLISH, BEARISH
    entry_zone: tuple  # (low, high)
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    probability: float  # 0-1
    confluences: List[str] = field(default_factory=list)
    invalidation_level: float = 0.0


class SMCAgentEnhanced:
    """
    Enhanced Smart Money Concepts agent with proper data models.
    
    Source: AI-MultiColony-Ecosystem SmartMoneyTradingAgent
    Features:
    - Full ICT methodology (BOS, CHoCH, OB, FVG, Liquidity, OTE)
    - Proper data structures for each concept
    - Multi-timeframe analysis
    - Setup generation with probability scoring
    """

    # Supported symbols
    SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD",
               "BTCUSD", "ETHUSD", "XAUUSD", "US30", "NAS100"]

    # Risk parameters (aligned with Hermes Quant OS hardcoded rules)
    RISK_PER_TRADE = 0.005  # 0.5%
    MAX_DAILY_RISK = 0.01   # 1%
    MIN_RR_RATIO = 1.5

    def __init__(self):
        self.swing_points: List[MarketStructurePoint] = []
        self.order_blocks: List[OrderBlock] = []
        self.fair_value_gaps: List[FairValueGap] = []
        self.liquidity_levels: List[LiquidityLevel] = []
        self.setups: List[SmartMoneySetup] = []

    def analyze(self, data: List[Dict], symbol: str = "XAUUSD") -> Dict:
        """
        Full SMC analysis with proper data models.
        """
        if len(data) < 20:
            return {"error": "Insufficient data for SMC analysis"}

        closes = [d["close"] for d in data]
        highs = [d["high"] for d in data]
        lows = [d["low"] for d in data]
        volumes = [d.get("volume", 0) for d in data]

        # 1. Market Structure Analysis
        self._detect_swing_points(highs, lows, data)
        trend = self._determine_trend()

        # 2. Order Block Detection
        self._detect_order_blocks(closes, highs, lows, volumes, data)

        # 3. Fair Value Gap Detection
        self._detect_fair_value_gaps(highs, lows, data)

        # 4. Liquidity Analysis
        self._detect_liquidity_levels(highs, lows, data)

        # 5. Setup Generation (OTE, BOS, FVG+OB)
        self._generate_setups(closes[-1], trend)

        return {
            "symbol": symbol,
            "latest_price": closes[-1],
            "trend": trend,
            "swing_points_count": len(self.swing_points),
            "recent_swings": [asdict(sp) for sp in self.swing_points[-5:]],
            "order_blocks_count": len(self.order_blocks),
            "active_order_blocks": [asdict(ob) for ob in self.order_blocks
                                     if not ob.mitigated][-5:],
            "fvgs_count": len(self.fair_value_gaps),
            "unfilled_fvgs": [asdict(fvg) for fvg in self.fair_value_gaps
                               if not fvg.filled][-5:],
            "liquidity_levels": [asdict(ll) for ll in self.liquidity_levels[-5:]],
            "active_setups": [asdict(s) for s in self.setups
                              if s.probability > 0.5],
            "timestamp": datetime.now().isoformat()
        }

    def _detect_swing_points(self, highs, lows, data):
        """Detect swing highs and lows with strength scoring"""
        self.swing_points = []

        for i in range(2, len(highs) - 2):
            # Swing High
            if (highs[i] > highs[i-1] and highs[i] > highs[i+1] and
                highs[i] > highs[i-2] and highs[i] > highs[i+2]):
                strength = min(10, (highs[i] - min(highs[i-2:i+3])) / highs[i] * 100)
                self.swing_points.append(MarketStructurePoint(
                    index=i, price=highs[i],
                    point_type="SH",  # Will classify HH/HL later
                    timestamp=data[i].get("time", ""),
                    strength=round(strength, 1)
                ))

            # Swing Low
            if (lows[i] < lows[i-1] and lows[i] < lows[i+1] and
                lows[i] < lows[i-2] and lows[i] < lows[i+2]):
                strength = min(10, (max(lows[i-2:i+3]) - lows[i]) / lows[i] * 100)
                self.swing_points.append(MarketStructurePoint(
                    index=i, price=lows[i],
                    point_type="SL",
                    timestamp=data[i].get("time", ""),
                    strength=round(strength, 1)
                ))

        # Classify as HH/HL/LH/LL
        highs_list = [sp for sp in self.swing_points if sp.point_type == "SH"]
        lows_list = [sp for sp in self.swing_points if sp.point_type == "SL"]

        for i in range(1, len(highs_list)):
            if highs_list[i].price > highs_list[i-1].price:
                highs_list[i].point_type = "HH"
            else:
                highs_list[i].point_type = "LH"

        for i in range(1, len(lows_list)):
            if lows_list[i].price > lows_list[i-1].price:
                lows_list[i].point_type = "HL"
            else:
                lows_list[i].point_type = "LL"

    def _determine_trend(self) -> str:
        """Determine trend from swing point classification"""
        if len(self.swing_points) < 4:
            return "neutral"

        recent = self.swing_points[-4:]
        hh_count = sum(1 for sp in recent if sp.point_type == "HH")
        hl_count = sum(1 for sp in recent if sp.point_type == "HL")
        lh_count = sum(1 for sp in recent if sp.point_type == "LH")
        ll_count = sum(1 for sp in recent if sp.point_type == "LL")

        if hh_count >= 2 and hl_count >= 1:
            return "bullish"
        elif lh_count >= 2 and ll_count >= 1:
            return "bearish"
        else:
            return "neutral"

    def _detect_order_blocks(self, closes, highs, lows, volumes, data):
        """Detect institutional order blocks with volume confirmation"""
        self.order_blocks = []

        for i in range(3, len(closes)):
            body = abs(closes[i] - data[i].get("open", closes[i]))
            prev_body = abs(closes[i-1] - data[i-1].get("open", closes[i-1]))

            if body > prev_body * 2:  # Impulse candle
                vol = volumes[i] if i < len(volumes) else 0
                avg_vol = sum(volumes[max(0,i-20):i]) / 20 if i >= 20 else vol
                vol_strength = min(1.0, vol / avg_vol) if avg_vol > 0 else 0.5

                if closes[i] > data[i].get("open", closes[i]):  # Bullish impulse
                    if closes[i-1] < data[i-1].get("open", closes[i-1]):
                        self.order_blocks.append(OrderBlock(
                            index=i-1,
                            high=highs[i-1],
                            low=lows[i-1],
                            ob_type="bullish_ob",
                            strength=round(vol_strength, 2)
                        ))
                else:  # Bearish impulse
                    if closes[i-1] > data[i-1].get("open", closes[i-1]):
                        self.order_blocks.append(OrderBlock(
                            index=i-1,
                            high=highs[i-1],
                            low=lows[i-1],
                            ob_type="bearish_ob",
                            strength=round(vol_strength, 2)
                        ))

    def _detect_fair_value_gaps(self, highs, lows, data):
        """Detect Fair Value Gaps (3-candle imbalances)"""
        self.fair_value_gaps = []

        for i in range(2, len(data)):
            # Bullish FVG: gap between candle[i-2].high and candle[i].low
            if lows[i] > highs[i-2]:
                self.fair_value_gaps.append(FairValueGap(
                    index=i-1,
                    top=lows[i],
                    bottom=highs[i-2],
                    fvg_type="bullish_fvg",
                    size=round(lows[i] - highs[i-2], 5)
                ))
            # Bearish FVG
            if highs[i] < lows[i-2]:
                self.fair_value_gaps.append(FairValueGap(
                    index=i-1,
                    top=lows[i-2],
                    bottom=highs[i],
                    fvg_type="bearish_fvg",
                    size=round(lows[i-2] - highs[i], 5)
                ))

    def _detect_liquidity_levels(self, highs, lows, data):
        """Detect liquidity pools at swing points and equal highs/lows"""
        self.liquidity_levels = []

        # Liquidity at swing points
        for sp in self.swing_points:
            liq_type = "buy_side" if sp.point_type in ("SH", "HH", "LH") else "sell_side"
            self.liquidity_levels.append(LiquidityLevel(
                price=sp.price,
                liq_type=liq_type,
                strength=sp.strength / 10
            ))

        # Equal highs/lows (strong liquidity pools)
        prices = [sp.price for sp in self.swing_points]
        for i, p1 in enumerate(prices):
            for j, p2 in enumerate(prices):
                if i != j and abs(p1 - p2) / p1 < 0.001:  # Within 0.1%
                    self.liquidity_levels.append(LiquidityLevel(
                        price=p1,
                        liq_type="equal_level",
                        strength=0.8  # Equal levels are strong pools
                    ))

    def _generate_setups(self, current_price: float, trend: str):
        """Generate trade setups based on SMC analysis"""
        self.setups = []

        # OTE (Optimal Trade Entry) setup
        active_obs = [ob for ob in self.order_blocks if not ob.mitigated]
        active_fvgs = [fvg for fvg in self.fair_value_gaps if not fvg.filled]

        # Bullish OTE setup
        if trend == "bullish" and active_obs:
            bullish_obs = [ob for ob in active_obs if ob.ob_type == "bullish_ob"]
            if bullish_obs:
                ob = bullish_obs[-1]
                entry = (ob.high + ob.low) / 2
                sl = ob.low - (ob.high - ob.low) * 0.1  # 10% buffer below OB
                tp1 = current_price  # Recent high
                tp2 = current_price + (entry - sl) * 2
                tp3 = current_price + (entry - sl) * 3

                confluences = ["Bullish OB"]
                if active_fvgs:
                    bull_fvgs = [f for f in active_fvgs if f.fvg_type == "bullish_fvg"]
                    if bull_fvgs:
                        confluences.append("Bullish FVG")
                confluences.append(f"Trend: {trend}")

                prob = min(0.9, 0.4 + len(confluences) * 0.1)

                self.setups.append(SmartMoneySetup(
                    setup_type="OTE",
                    direction="BULLISH",
                    entry_zone=(ob.low, ob.high),
                    stop_loss=round(sl, 5),
                    take_profit_1=round(tp1, 5),
                    take_profit_2=round(tp2, 5),
                    take_profit_3=round(tp3, 5),
                    probability=round(prob, 2),
                    confluences=confluences,
                    invalidation_level=round(ob.low, 5)
                ))

        # Bearish OTE setup
        if trend == "bearish" and active_obs:
            bearish_obs = [ob for ob in active_obs if ob.ob_type == "bearish_ob"]
            if bearish_obs:
                ob = bearish_obs[-1]
                entry = (ob.high + ob.low) / 2
                sl = ob.high + (ob.high - ob.low) * 0.1
                tp1 = current_price
                tp2 = current_price - (sl - entry) * 2
                tp3 = current_price - (sl - entry) * 3

                confluences = ["Bearish OB", f"Trend: {trend}"]
                prob = min(0.9, 0.4 + len(confluences) * 0.1)

                self.setups.append(SmartMoneySetup(
                    setup_type="OTE",
                    direction="BEARISH",
                    entry_zone=(ob.low, ob.high),
                    stop_loss=round(sl, 5),
                    take_profit_1=round(tp1, 5),
                    take_profit_2=round(tp2, 5),
                    take_profit_3=round(tp3, 5),
                    probability=round(prob, 2),
                    confluences=confluences,
                    invalidation_level=round(ob.high, 5)
                ))
