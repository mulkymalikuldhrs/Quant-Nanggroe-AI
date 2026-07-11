#!/usr/bin/env python3
"""
Macro/Fundamental + Sentiment Agent (L2 - Analysis Layer)
Risk-on/off regime detection, sentiment analysis
"""

import json
import logging
from datetime import datetime

logger = logging.getLogger("HermesQuantOS.MacroSentiment")


class MacroSentimentTool:
    """L2 Agent: Macro/Sentiment - Regime detection & sentiment analysis"""

    def __init__(self):
        self.regime_cache = {}
        self.sentiment_cache = {}

    def get_regime(self) -> str:
        """Detect current risk-on/risk-off regime"""
        try:
            import yfinance as yf

            # Use proxy assets to determine regime
            proxies = {
                "SPX": "^GSPC",    # Equities (risk-on)
                "VIX": "^VIX",     # Volatility (risk-off)
                "DXY": "DX-Y.NYB", # Dollar (mixed)
                "GOLD": "GC=F",    # Gold (risk-off hedge)
                "US10Y": "^TNX",   # Yields (context)
            }

            results = {}
            for name, sym in proxies.items():
                try:
                    ticker = yf.Ticker(sym)
                    hist = ticker.history(period="5d")
                    if not hist.empty:
                        current = float(hist["Close"].iloc[-1])
                        prev = float(hist["Close"].iloc[0]) if len(hist) > 1 else current
                        change = ((current - prev) / prev) * 100
                        results[name] = {"price": round(current, 2), "change_5d": round(change, 2)}
                except Exception:
                    results[name] = {"price": "N/A", "change_5d": "N/A"}

            # Determine regime
            spx_change = results.get("SPX", {}).get("change_5d", 0)
            vix_level = results.get("VIX", {}).get("price", 20)

            if spx_change and vix_level:
                if spx_change > 1.0 and vix_level < 18:
                    regime = "RISK-ON"
                    bias = "Favor risk assets, equities, crypto"
                elif spx_change < -1.0 or vix_level > 25:
                    regime = "RISK-OFF"
                    bias = "Favor safe havens, gold, bonds"
                else:
                    regime = "NEUTRAL"
                    bias = "Balanced approach, selective entries"
            else:
                regime = "UNKNOWN"
                bias = "Insufficient data for regime detection"

            return json.dumps({
                "regime": regime,
                "bias": bias,
                "proxies": results,
                "timestamp": datetime.now().isoformat()
            }, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e), "regime": "UNKNOWN"})

    def get_sentiment(self, symbol: str = "XAUUSD") -> str:
        """Get sentiment analysis (placeholder for API integration)"""
        return json.dumps({
            "symbol": symbol,
            "sentiment": "neutral",
            "confidence": 0.5,
            "sources": ["technical", "volume"],
            "note": "Full sentiment requires news API integration",
            "suggested_integrations": ["Fear & Greed Index", "News API", "Social Sentiment"],
            "timestamp": datetime.now().isoformat()
        }, indent=2)
