"""Fundamental analysis trading strategy.

Generates signals based on:
- Economic calendar (high-impact events, surprises)
- Macro analysis (GDP, inflation, employment trends)
- Central bank policy expectations
- Market sentiment and risk appetite
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType


class FundamentalStrategy(BaseStrategy):
    """Fundamental analysis strategy using economic calendar and macro data.

    Parameters:
        event_proximity_hours (int): Hours before high-impact event to reduce risk (default 24)
        surprise_threshold (float): Min absolute surprise to act on (default 0.3)
        vol_mult (float): ATR multiplier for SL/TP (default 2.0)
        risk_reduction_pct (float): Reduce position size before events (default 0.5)
    """

    def __init__(self, name: str = "Fundamental", params: Optional[Dict] = None):
        params = params or {}
        super().__init__(name, params)
        self.proximity_hours = params.get("event_proximity_hours", 24)
        self.surprise_thresh = params.get("surprise_threshold", 0.3)
        self.vol_mult = params.get("vol_mult", 2.0)
        self.risk_reduction = params.get("risk_reduction_pct", 0.5)
        self._calendar = None

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return 20

    def _get_calendar(self):
        if self._calendar is None:
            try:
                from quant_nanggroe.engine.data.economic_calendar import EconomicCalendar
                self._calendar = EconomicCalendar()
                self._calendar.fetch(days_ahead=30)
            except ImportError:
                return None
        return self._calendar

    def _check_calendar_events(self, currency: str = "USD") -> Dict:
        """Check economic calendar for upcoming events and recent surprises."""
        cal = self._get_calendar()
        if cal is None:
            return {"high_impact_soon": False, "volatility_score": 0.0, "recent_surprise": None}
        upcoming = cal.get_upcoming(hours=self.proximity_hours)
        surprises = cal.get_recent_surprises(hours=self.proximity_hours)

        # Find events relevant to this currency/asset
        relevant_upcoming = [e for e in upcoming if e.currency == currency]
        relevant_surprises = [e for e in surprises if e.currency == currency]

        high_impact_soon = any(e.impact == "high" for e in relevant_upcoming)
        volatility_score = cal.upcoming_volatility_score(currency, hours=self.proximity_hours)

        # Recent surprise direction
        surprise_bullish = any(
            e.surprise_direction() == "positive" and e.impact == "high"
            for e in relevant_surprises
        )
        surprise_bearish = any(
            e.surprise_direction() == "negative" and e.impact == "high"
            for e in relevant_surprises
        )

        return {
            "high_impact_soon": high_impact_soon,
            "volatility_score": volatility_score,
            "surprise_bullish": surprise_bullish,
            "surprise_bearish": surprise_bearish,
            "upcoming_count": len(relevant_upcoming),
            "surprise_count": len(relevant_surprises),
            "market_risk": cal.analyze_market_risk(),
        }

    def _analyze_sentiment(self, data: pd.DataFrame) -> Dict:
        """Analyze market sentiment from price action."""
        close = data["close"].values
        if len(close) < 20:
            return {"trend": "neutral", "strength": 0.0}

        returns = np.diff(close[-21:]) / close[-21:-1]
        avg_return = np.mean(returns)
        volatility = np.std(returns)
        sharpe_20d = avg_return / (volatility + 1e-10) * np.sqrt(252)

        # Volume-weighted sentiment
        if "volume" in data.columns:
            vol = data["volume"].values[-20:]
            recent_vol_ratio = np.mean(vol[-5:]) / (np.mean(vol) + 1e-10)
        else:
            recent_vol_ratio = 1.0

        return {
            "trend": "bullish" if sharpe_20d > 0.5 else "bearish" if sharpe_20d < -0.5 else "neutral",
            "momentum_sharpe": round(sharpe_20d, 2),
            "recent_volatility": round(volatility, 4),
            "volume_ratio": round(recent_vol_ratio, 2),
        }

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None

        calendar = self._check_calendar_events()
        sentiment = self._analyze_sentiment(data)
        latest_price = float(data["close"].iloc[-1])
        atr_val = float(self.compute_atr(
            data["high"], data["low"], data["close"]
        ).iloc[-1]) if all(c in data.columns for c in ["high", "low", "close"]) else latest_price * 0.02

        # HIGH IMPACT: avoid trading before major events
        if calendar["high_impact_soon"]:
            return Signal(
                symbol=data.get("symbol", "UNKNOWN") if "symbol" in data.columns else "UNKNOWN",
                signal_type=SignalType.HOLD,
                confidence=0.9,
                price=latest_price,
                source_strategy=self.name,
                reasoning=f"HOLD: {calendar['upcoming_count']} high-impact events in {self.proximity_hours}h. Market risk: {calendar['market_risk']['overall_risk_score']:.0%}",
            )

        # SURPRISE BULLISH: positive economic surprise
        if calendar.get("surprise_bullish", False) and sentiment.get("trend") != "bearish":
            conf = min(0.5 + calendar.get("surprise_count", 0) * 0.1 + sentiment.get("momentum_sharpe", 0.0) * 0.1, 0.9)
            return Signal(
                symbol=data.get("symbol", "UNKNOWN") if "symbol" in data.columns else "UNKNOWN",
                signal_type=SignalType.BUY,
                confidence=round(conf, 2),
                price=latest_price,
                stop_loss=latest_price - atr_val * self.vol_mult,
                take_profit=latest_price + atr_val * self.vol_mult * 2,
                source_strategy=self.name,
                reasoning=f"BUY: Positive economic surprise. Sentiment={sentiment.get('trend')} Sharpe={sentiment.get('momentum_sharpe')}",
            )

        # SURPRISE BEARISH: negative economic surprise
        if calendar.get("surprise_bearish", False) and sentiment.get("trend") != "bullish":
            conf = min(0.5 + calendar.get("surprise_count", 0) * 0.1 + abs(sentiment.get("momentum_sharpe", 0.0)) * 0.1, 0.9)
            return Signal(
                symbol=data.get("symbol", "UNKNOWN") if "symbol" in data.columns else "UNKNOWN",
                signal_type=SignalType.SELL,
                confidence=round(conf, 2),
                price=latest_price,
                stop_loss=latest_price + atr_val * self.vol_mult,
                take_profit=latest_price - atr_val * self.vol_mult * 2,
                source_strategy=self.name,
                reasoning=f"SELL: Negative economic surprise. Sentiment={sentiment.get('trend')} Sharpe={sentiment.get('momentum_sharpe')}",
            )

        # TREND + VOLATILITY: adjust position sizing based on calendar
        if calendar.get("volatility_score", 0.0) > 0.6:
            return Signal(
                symbol=data.get("symbol", "UNKNOWN") if "symbol" in data.columns else "UNKNOWN",
                signal_type=SignalType.HOLD,
                confidence=round(calendar["volatility_score"], 2),
                price=latest_price,
                source_strategy=self.name,
                reasoning=f"HOLD: Elevated volatility ({calendar.get('volatility_score', 0.0):.0%}) from upcoming economic data. Reducing risk.",
            )

        return None
