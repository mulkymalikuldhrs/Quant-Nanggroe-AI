#!/usr/bin/env python3
"""
Market State Engine (from Quant-Nanggroe-AI)
=============================================
Regime detection: TRENDING | RANGE | MEAN_REVERT | RISK_OFF | PANIC | NO_TRADE
Deterministic classification based on ADX, RSI, price change, volume
"""

import json
import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger("HermesQuantOS.MarketState")


class MarketStateEngine:
    """
    Determines current market regime for decision gating.
    If NO_TRADE → entire system stops.
    
    Source: Quant-Nanggroe-AI v15.2.0 Market State Engine
    Adapted for Hermes Quant OS.
    """

    def __init__(self):
        self.current_regime = "UNKNOWN"
        self.regime_history = []

    def detect_regime(self, symbol: str = "XAUUSD",
                       price_change_5d: float = 0.0,
                       adx: float = 20.0,
                       rsi: float = 50.0,
                       atr_pct: float = 1.0,
                       volume_ratio: float = 1.0) -> Dict:
        """
        Deterministic regime classification.
        
        Args:
            symbol: Trading symbol
            price_change_5d: 5-day price change percentage
            adx: Average Directional Index value
            rsi: RSI(14) value
            atr_pct: ATR as percentage of price
            volume_ratio: Current volume / average volume
            
        Returns:
            Dict with regime, volatility, liquidity, and details
        """
        # Regime determination (priority order)
        if price_change_5d < -5.0:
            regime = "PANIC"
        elif price_change_5d < -2.0:
            regime = "RISK_OFF"
        elif adx > 25:
            regime = "TRENDING"
        elif rsi > 75 or rsi < 25:
            regime = "MEAN_REVERT"
        else:
            regime = "RANGE"

        # Volatility classification
        if atr_pct > 2.5:
            volatility = "HIGH"
        elif atr_pct < 0.5:
            volatility = "LOW"
        else:
            volatility = "NORMAL"

        # Liquidity classification
        if volume_ratio < 0.4:
            liquidity = "THIN"
        elif volume_ratio > 1.8:
            liquidity = "DEEP"
        else:
            liquidity = "NORMAL"

        # NO_TRADE override conditions
        no_trade_reasons = []
        if regime == "PANIC":
            no_trade_reasons.append("Panic regime - extreme sell-off")
        if volatility == "HIGH" and liquidity == "THIN":
            no_trade_reasons.append("High volatility + thin liquidity = dangerous")
        if volume_ratio < 0.2:
            no_trade_reasons.append("Extremely low volume - no liquidity")

        if no_trade_reasons:
            final_regime = "NO_TRADE"
        else:
            final_regime = regime

        result = {
            "symbol": symbol,
            "regime": final_regime,
            "base_regime": regime,  # Before NO_TRADE override
            "volatility": volatility,
            "liquidity": liquidity,
            "no_trade_reasons": no_trade_reasons,
            "inputs": {
                "price_change_5d": f"{price_change_5d:.2f}%",
                "adx": round(adx, 2),
                "rsi": round(rsi, 2),
                "atr_pct": f"{atr_pct:.2f}%",
                "volume_ratio": f"{volume_ratio:.2f}x"
            },
            "trade_allowed": final_regime not in ["PANIC", "RISK_OFF", "NO_TRADE"],
            "timestamp": datetime.now().isoformat()
        }

        self.current_regime = final_regime
        self.regime_history.append(result)

        # Keep last 100 regime checks
        if len(self.regime_history) > 100:
            self.regime_history = self.regime_history[-100:]

        logger.info(f"REGIME: {final_regime} | Vol: {volatility} | Liq: {liquidity}")

        return result

    def auto_detect(self, symbol: str = "XAUUSD") -> Dict:
        """
        Auto-detect regime using market data.
        """
        try:
            from tools.shared_state import SharedState
            ss = SharedState()

            mdt = ss.market_data
            tat = ss.technical_analysis

            # Get market data
            raw = json.loads(mdt.get_ohlcv(symbol, "1d", 10))
            if "error" in raw:
                return self.detect_regime(symbol)

            data = raw.get("data", [])
            if len(data) < 5:
                return self.detect_regime(symbol)

            # Calculate 5-day price change
            price_now = data[-1]["close"]
            price_5d_ago = data[-5]["close"] if len(data) >= 5 else data[0]["close"]
            price_change_5d = ((price_now - price_5d_ago) / price_5d_ago) * 100

            # Get technical indicators
            analysis = json.loads(tat.analyze(symbol, "1d"))
            indicators = analysis.get("indicators", {})

            adx = indicators.get("adx_approx", 20)
            rsi = indicators.get("rsi_14", 50)
            atr = indicators.get("atr_14", price_now * 0.01)
            atr_pct = (atr / price_now) * 100

            # Volume ratio
            volumes = [d.get("volume", 0) for d in data[-20:]]
            avg_vol = sum(volumes) / len(volumes) if volumes else 1
            last_vol = volumes[-1] if volumes else 1
            volume_ratio = last_vol / avg_vol if avg_vol > 0 else 1.0

            return self.detect_regime(
                symbol, price_change_5d, adx, rsi, atr_pct, volume_ratio
            )

        except Exception as e:
            logger.warning(f"Auto-detect failed: {e}")
            return self.detect_regime(symbol)

    def get_regime(self) -> str:
        """Get current regime"""
        return self.current_regime
