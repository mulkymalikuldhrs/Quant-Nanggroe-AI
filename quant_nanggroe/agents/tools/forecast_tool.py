"""Forecast Tool — AI Forecast Engine for Multi-Day Market Predictions.

Provides multi-day market forecast synthesis combining technical,
fundamental, news, and COT sentiment analysis with confidence scoring
per timeframe and forecast accuracy tracking.

Features
--------
* Multi-day market forecast synthesis
* Technical + fundamental + news + COT sentiment combination
* Confidence scoring per timeframe
* Forecast accuracy tracking
* LangChain @tool function for agent consumption

References
----------
Trading-Plan-AI-Interactive Forecast Engine documentation
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func=None, **kwargs):
        if func is not None:
            return func
        def decorator(f):
            return f
        return decorator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ForecastTimeframe(str, Enum):
    """Forecast timeframe."""
    INTRADAY = "INTRADAY"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


class ForecastDirection(str, Enum):
    """Forecast price direction."""
    STRONGLY_BULLISH = "STRONGLY_BULLISH"
    BULLISH = "BULLISH"
    SLIGHTLY_BULLISH = "SLIGHTLY_BULLISH"
    NEUTRAL = "NEUTRAL"
    SLIGHTLY_BEARISH = "SLIGHTLY_BEARISH"
    BEARISH = "BEARISH"
    STRONGLY_BEARISH = "STRONGLY_BEARISH"


class ForecastConfidence(str, Enum):
    """Confidence level classification."""
    VERY_HIGH = "VERY_HIGH"
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"
    VERY_LOW = "VERY_LOW"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class TechnicalForecast(BaseModel):
    """Technical analysis forecast component."""
    trend: str = Field("NEUTRAL", description="Current trend direction")
    momentum: float = Field(0.0, description="Momentum score (-1 to +1)")
    support_levels: List[float] = Field(default_factory=list)
    resistance_levels: List[float] = Field(default_factory=list)
    pattern: str = Field("", description="Detected pattern")
    signal: str = Field("NEUTRAL", description="Technical signal")
    weight: float = Field(0.35, description="Weight in forecast")


class FundamentalForecast(BaseModel):
    """Fundamental analysis forecast component."""
    valuation: str = Field("FAIR", description="Valuation assessment")
    earnings_trend: str = Field("NEUTRAL", description="Earnings trend")
    revenue_growth: str = Field("MODERATE", description="Revenue growth")
    margin_trend: str = Field("STABLE", description="Margin trend")
    signal: str = Field("NEUTRAL", description="Fundamental signal")
    weight: float = Field(0.25, description="Weight in forecast")


class NewsSentimentForecast(BaseModel):
    """News and sentiment forecast component."""
    overall_sentiment: float = Field(0.0, description="Sentiment score (-1 to +1)")
    news_volume: str = Field("MODERATE", description="News volume level")
    key_events: List[str] = Field(default_factory=list)
    event_type: str = Field("NOISE", description="Dominant event type")
    signal: str = Field("NEUTRAL", description="Sentiment signal")
    weight: float = Field(0.20, description="Weight in forecast")


class COTForecast(BaseModel):
    """COT positioning forecast component."""
    commercial_positioning: str = Field("NEUTRAL", description="Commercial hedger positioning")
    speculative_positioning: str = Field("NEUTRAL", description="Speculator positioning")
    extreme_reading: bool = Field(False, description="Whether positioning is extreme")
    contrarian_signal: Optional[str] = Field(None, description="Contrarian signal if extreme")
    signal: str = Field("NEUTRAL", description="COT signal")
    weight: float = Field(0.20, description="Weight in forecast")


class TimeframeForecast(BaseModel):
    """Forecast for a specific timeframe."""
    timeframe: ForecastTimeframe = Field(..., description="Forecast timeframe")
    direction: ForecastDirection = Field(ForecastDirection.NEUTRAL)
    confidence: float = Field(0.0, description="Confidence level (0-1)")
    confidence_label: ForecastConfidence = Field(ForecastConfidence.MODERATE)
    target_price: Optional[float] = Field(None, description="Target price")
    stop_loss: Optional[float] = Field(None, description="Suggested stop loss")
    probability_up: float = Field(0.5, description="Probability of upward move")
    probability_down: float = Field(0.5, description="Probability of downward move")
    key_levels: Dict[str, float] = Field(default_factory=dict, description="Key price levels")
    reasoning: List[str] = Field(default_factory=list, description="Forecast reasoning")


class ForecastResult(BaseModel):
    """Complete forecast result."""
    symbol: str = Field(..., description="Forecasted symbol")
    current_price: float = Field(0.0, description="Current price at forecast time")
    technical: TechnicalForecast = Field(default_factory=TechnicalForecast)
    fundamental: FundamentalForecast = Field(default_factory=FundamentalForecast)
    sentiment: NewsSentimentForecast = Field(default_factory=NewsSentimentForecast)
    cot: COTForecast = Field(default_factory=COTForecast)
    timeframe_forecasts: List[TimeframeForecast] = Field(default_factory=list)
    composite_direction: ForecastDirection = Field(ForecastDirection.NEUTRAL)
    composite_confidence: float = Field(0.0)
    timestamp: str = Field("")


class ForecastAccuracy(BaseModel):
    """Forecast accuracy tracking record."""
    forecast_id: str = Field("", description="Forecast identifier")
    symbol: str = Field("", description="Forecasted symbol")
    forecast_direction: str = Field("", description="Predicted direction")
    actual_direction: str = Field("", description="Actual market direction")
    correct: bool = Field(False, description="Whether forecast was correct")
    price_error_pct: float = Field(0.0, description="Price error percentage")
    confidence_at_forecast: float = Field(0.0, description="Confidence when forecast was made")
    forecast_time: str = Field("")
    resolution_time: str = Field("")


# ---------------------------------------------------------------------------
# Forecast Tool
# ---------------------------------------------------------------------------

class ForecastTool:
    """AI Forecast Engine for agent consumption.

    Provides multi-day market forecast synthesis combining technical,
    fundamental, news, and COT sentiment analysis with confidence
    scoring per timeframe and forecast accuracy tracking.

    Usage::

        tool = ForecastTool()
        forecast = await tool.forecast("AAPL")
        accuracy = await tool.get_accuracy_stats()
    """

    def __init__(self, cache_ttl: int = 1800) -> None:
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._cache_ttl = cache_ttl
        self._accuracy_records: List[ForecastAccuracy] = []

    async def forecast(
        self,
        symbol: str,
        current_price: Optional[float] = None,
    ) -> ForecastResult:
        """Generate a comprehensive multi-timeframe forecast.

        Args:
            symbol: Trading symbol to forecast.
            current_price: Current price (fetched if not provided).

        Returns:
            ForecastResult with multi-factor analysis and timeframe forecasts.
        """
        cache_key = f"forecast:{symbol}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        # Fetch current price if not provided
        if current_price is None:
            current_price = await self._fetch_current_price(symbol)

        # Generate component forecasts
        technical = await self._generate_technical_forecast(symbol)
        fundamental = await self._generate_fundamental_forecast(symbol)
        sentiment = await self._generate_sentiment_forecast(symbol)
        cot = await self._generate_cot_forecast(symbol)

        # Generate timeframe forecasts
        timeframe_forecasts = self._synthesize_timeframe_forecasts(
            symbol, current_price, technical, fundamental, sentiment, cot,
        )

        # Calculate composite direction and confidence
        composite_direction, composite_confidence = self._calculate_composite(
            technical, fundamental, sentiment, cot,
        )

        result = ForecastResult(
            symbol=symbol,
            current_price=current_price,
            technical=technical,
            fundamental=fundamental,
            sentiment=sentiment,
            cot=cot,
            timeframe_forecasts=timeframe_forecasts,
            composite_direction=composite_direction,
            composite_confidence=round(composite_confidence, 4),
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
        )

        self._set_cache(cache_key, result)
        return result

    async def record_accuracy(
        self,
        forecast_id: str,
        symbol: str,
        forecast_direction: str,
        actual_direction: str,
        price_error_pct: float = 0.0,
        confidence_at_forecast: float = 0.0,
    ) -> ForecastAccuracy:
        """Record forecast accuracy for tracking.

        Args:
            forecast_id: Original forecast identifier.
            symbol: Forecasted symbol.
            forecast_direction: Predicted direction.
            actual_direction: Actual market direction.
            price_error_pct: Price error percentage.
            confidence_at_forecast: Confidence when forecast was made.

        Returns:
            ForecastAccuracy record.
        """
        record = ForecastAccuracy(
            forecast_id=forecast_id,
            symbol=symbol,
            forecast_direction=forecast_direction,
            actual_direction=actual_direction,
            correct=forecast_direction.split("_")[-1] == actual_direction.split("_")[-1],
            price_error_pct=price_error_pct,
            confidence_at_forecast=confidence_at_forecast,
            forecast_time="",
            resolution_time=datetime.now(tz=timezone.utc).isoformat(),
        )
        self._accuracy_records.append(record)
        return record

    async def get_accuracy_stats(self) -> Dict[str, Any]:
        """Get forecast accuracy statistics.

        Returns:
            Dict with accuracy statistics.
        """
        if not self._accuracy_records:
            return {"total_forecasts": 0, "accuracy": 0.0}

        total = len(self._accuracy_records)
        correct = sum(1 for r in self._accuracy_records if r.correct)
        avg_error = sum(abs(r.price_error_pct) for r in self._accuracy_records) / total

        # Accuracy by confidence level
        high_conf = [r for r in self._accuracy_records if r.confidence_at_forecast >= 0.7]
        high_conf_accuracy = (
            sum(1 for r in high_conf if r.correct) / len(high_conf)
            if high_conf else 0.0
        )

        return {
            "total_forecasts": total,
            "overall_accuracy": round(correct / total, 4),
            "average_price_error_pct": round(avg_error, 4),
            "high_confidence_accuracy": round(high_conf_accuracy, 4),
            "high_confidence_count": len(high_conf),
        }

    # ----- Component generators -----

    async def _generate_technical_forecast(self, symbol: str) -> TechnicalForecast:
        """Generate technical analysis forecast component.

        PRODUCTION: Wired to real engine via TechnicalAnalysisTool.
        Falls back to NEUTRAL with a warning.
        """
        try:
            from quant_nanggroe.agents.tools.technical import TechnicalAnalysisTool
            from quant_nanggroe.agents.tools.market_data import MarketDataTool
            mdt = MarketDataTool()
            tat = TechnicalAnalysisTool(market_data_tool=mdt)
            analysis = await tat.analyze(symbol, "1d")
            trend = analysis.get("trend", {}).get("direction", "NEUTRAL")
            momentum = analysis.get("trend", {}).get("strength", 0.0)
            support_levels = analysis.get("support_resistance", {}).get("support", [])
            resistance_levels = analysis.get("support_resistance", {}).get("resistance", [])
            signal = "BULLISH" if trend == "bullish" else ("BEARISH" if trend == "bearish" else "NEUTRAL")
            return TechnicalForecast(  # PRODUCTION: Wired to real engine
                trend=trend.upper(),
                momentum=momentum,
                support_levels=support_levels,
                resistance_levels=resistance_levels,
                signal=signal,
            )
        except Exception as exc:
            logger.warning("TechnicalForecast: real engine unavailable for %s: %s", symbol, exc)
            return TechnicalForecast(
                trend="NEUTRAL",
                momentum=0.0,
                support_levels=[],
                resistance_levels=[],
                signal="NEUTRAL",
            )

    async def _generate_fundamental_forecast(self, symbol: str) -> FundamentalForecast:
        """Generate fundamental analysis forecast component.

        PRODUCTION: Wired to real engine via yfinance.
        Falls back to NEUTRAL with a warning.
        """
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}
            pe = info.get("trailingPE")
            fwd_pe = info.get("forwardPE")
            if pe and fwd_pe:
                if fwd_pe < pe * 0.8:
                    signal = "BULLISH"
                    valuation = "UNDERVALUED"
                elif fwd_pe > pe * 1.2:
                    signal = "BEARISH"
                    valuation = "OVERVALUED"
                else:
                    signal = "NEUTRAL"
                    valuation = "FAIR"
            else:
                signal = "NEUTRAL"
                valuation = "UNKNOWN"
            return FundamentalForecast(  # PRODUCTION: Wired to real engine
                valuation=valuation,
                signal=signal,
            )
        except Exception as exc:
            logger.warning("FundamentalForecast: real engine unavailable for %s: %s", symbol, exc)
            return FundamentalForecast(
                signal="NEUTRAL",
            )

    async def _generate_sentiment_forecast(self, symbol: str) -> NewsSentimentForecast:
        """Generate news/sentiment forecast component.

        PRODUCTION: Wired to real engine via SentimentTool.
        Falls back to NEUTRAL with a warning.
        """
        try:
            from quant_nanggroe.agents.tools.sentiment import SentimentTool
            st = SentimentTool()
            result = await st.analyze(symbol)
            score = result.get("overall_score", 0.0)
            label = result.get("label", "NEUTRAL")
            signal = "BULLISH" if label == "BULLISH" else ("BEARISH" if label == "BEARISH" else "NEUTRAL")
            return NewsSentimentForecast(  # PRODUCTION: Wired to real engine
                overall_sentiment=score,
                signal=signal,
            )
        except Exception as exc:
            logger.warning("SentimentForecast: real engine unavailable for %s: %s", symbol, exc)
            return NewsSentimentForecast(
                signal="NEUTRAL",
            )

    async def _generate_cot_forecast(self, symbol: str) -> COTForecast:
        """Generate COT positioning forecast component.

        PRODUCTION: Wired to real engine via FlowTool.
        Falls back to NEUTRAL with a warning.
        """
        try:
            from quant_nanggroe.agents.tools.flow_tool import FlowTool
            ft = FlowTool()
            positioning = await ft.analyze_positioning(symbol)
            signal_str = positioning.signal.value if hasattr(positioning.signal, 'value') else str(positioning.signal)
            if "BUY" in signal_str.upper():
                signal = "BULLISH"
            elif "SELL" in signal_str.upper():
                signal = "BEARISH"
            else:
                signal = "NEUTRAL"
            return COTForecast(  # PRODUCTION: Wired to real engine
                contrarian_signal=positioning.contrarian_signal,
                signal=signal,
            )
        except Exception as exc:
            logger.warning("COTForecast: real engine unavailable for %s: %s", symbol, exc)
            return COTForecast(
                signal="NEUTRAL",
            )

    async def _fetch_current_price(self, symbol: str) -> float:
        """Fetch current price for a symbol."""
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            if not hist.empty:
                return float(hist["Close"].iloc[-1])
        except Exception:
            pass
        return 0.0

    # ----- Synthesis -----

    def _synthesize_timeframe_forecasts(
        self,
        symbol: str,
        current_price: float,
        technical: TechnicalForecast,
        fundamental: FundamentalForecast,
        sentiment: NewsSentimentForecast,
        cot: COTForecast,
    ) -> List[TimeframeForecast]:
        """Synthesize component forecasts into timeframe forecasts."""
        # Weighted signal score
        signal_score = (
            self._direction_to_score(technical.signal) * technical.weight
            + self._direction_to_score(fundamental.signal) * fundamental.weight
            + self._direction_to_score(sentiment.signal) * sentiment.weight
            + self._direction_to_score(cot.signal) * cot.weight
        )

        forecasts = []

        # Intraday
        intraday_dir = self._score_to_direction(signal_score * 1.2)  # More responsive
        intraday_conf = min(abs(signal_score) * 0.8, 0.7)
        forecasts.append(TimeframeForecast(
            timeframe=ForecastTimeframe.INTRADAY,
            direction=intraday_dir,
            confidence=round(intraday_conf, 4),
            confidence_label=self._confidence_from_value(intraday_conf),
            probability_up=round(0.5 + signal_score * 0.3, 4),
            probability_down=round(0.5 - signal_score * 0.3, 4),
            reasoning=["Weighted composite signal from all components"],
        ))

        # Daily
        daily_dir = self._score_to_direction(signal_score)
        daily_conf = min(abs(signal_score) * 0.6 + 0.1, 0.8)
        target_pct = signal_score * 0.03  # 3% move per unit signal
        forecasts.append(TimeframeForecast(
            timeframe=ForecastTimeframe.DAILY,
            direction=daily_dir,
            confidence=round(daily_conf, 4),
            confidence_label=self._confidence_from_value(daily_conf),
            target_price=round(current_price * (1 + target_pct), 2) if current_price else None,
            probability_up=round(0.5 + signal_score * 0.25, 4),
            probability_down=round(0.5 - signal_score * 0.25, 4),
            reasoning=["Daily composite with risk-adjusted target"],
        ))

        # Weekly
        weekly_dir = self._score_to_direction(signal_score * 0.8)
        weekly_conf = min(abs(signal_score) * 0.5 + 0.15, 0.75)
        weekly_target_pct = signal_score * 0.05
        forecasts.append(TimeframeForecast(
            timeframe=ForecastTimeframe.WEEKLY,
            direction=weekly_dir,
            confidence=round(weekly_conf, 4),
            confidence_label=self._confidence_from_value(weekly_conf),
            target_price=round(current_price * (1 + weekly_target_pct), 2) if current_price else None,
            probability_up=round(0.5 + signal_score * 0.2, 4),
            probability_down=round(0.5 - signal_score * 0.2, 4),
            reasoning=["Weekly forecast with fundamental emphasis"],
        ))

        # Monthly
        monthly_dir = self._score_to_direction(signal_score * 0.6)
        monthly_conf = min(abs(signal_score) * 0.4 + 0.2, 0.6)
        monthly_target_pct = signal_score * 0.08
        forecasts.append(TimeframeForecast(
            timeframe=ForecastTimeframe.MONTHLY,
            direction=monthly_dir,
            confidence=round(monthly_conf, 4),
            confidence_label=self._confidence_from_value(monthly_conf),
            target_price=round(current_price * (1 + monthly_target_pct), 2) if current_price else None,
            probability_up=round(0.5 + signal_score * 0.15, 4),
            probability_down=round(0.5 - signal_score * 0.15, 4),
            reasoning=["Monthly with macro/fundamental dominance"],
        ))

        return forecasts

    @staticmethod
    def _calculate_composite(
        technical: TechnicalForecast,
        fundamental: FundamentalForecast,
        sentiment: NewsSentimentForecast,
        cot: COTForecast,
    ) -> tuple[ForecastDirection, float]:
        """Calculate composite direction and confidence."""
        score = (
            ForecastTool._direction_to_score(technical.signal) * technical.weight
            + ForecastTool._direction_to_score(fundamental.signal) * fundamental.weight
            + ForecastTool._direction_to_score(sentiment.signal) * sentiment.weight
            + ForecastTool._direction_to_score(cot.signal) * cot.weight
        )
        direction = ForecastTool._score_to_direction(score)
        confidence = min(abs(score) + 0.1, 0.95)
        return direction, confidence

    @staticmethod
    def _direction_to_score(direction: str) -> float:
        """Convert direction string to numeric score."""
        mapping = {
            "STRONGLY_BULLISH": 1.0, "BULLISH": 0.6, "SLIGHTLY_BULLISH": 0.3,
            "NEUTRAL": 0.0,
            "SLIGHTLY_BEARISH": -0.3, "BEARISH": -0.6, "STRONGLY_BEARISH": -1.0,
        }
        return mapping.get(direction.upper(), 0.0)

    @staticmethod
    def _score_to_direction(score: float) -> ForecastDirection:
        """Convert numeric score to direction."""
        if score > 0.6:
            return ForecastDirection.STRONGLY_BULLISH
        elif score > 0.3:
            return ForecastDirection.BULLISH
        elif score > 0.1:
            return ForecastDirection.SLIGHTLY_BULLISH
        elif score < -0.6:
            return ForecastDirection.STRONGLY_BEARISH
        elif score < -0.3:
            return ForecastDirection.BEARISH
        elif score < -0.1:
            return ForecastDirection.SLIGHTLY_BEARISH
        return ForecastDirection.NEUTRAL

    @staticmethod
    def _confidence_from_value(value: float) -> ForecastConfidence:
        """Convert confidence value to label."""
        if value >= 0.8:
            return ForecastConfidence.VERY_HIGH
        elif value >= 0.6:
            return ForecastConfidence.HIGH
        elif value >= 0.4:
            return ForecastConfidence.MODERATE
        elif value >= 0.2:
            return ForecastConfidence.LOW
        return ForecastConfidence.VERY_LOW

    # ----- Cache helpers -----

    def _get_cache(self, key: str) -> Any | None:
        entry = self._cache.get(key)
        if entry is None:
            return None
        val, ts = entry
        if time.monotonic() - ts > self._cache_ttl:
            del self._cache[key]
            return None
        return val

    def _set_cache(self, key: str, val: Any) -> None:
        self._cache[key] = (val, time.monotonic())


# ---------------------------------------------------------------------------
# Singleton and LangChain @tool
# ---------------------------------------------------------------------------

_default_forecast: ForecastTool | None = None


def _get_default_forecast() -> ForecastTool:
    global _default_forecast
    if _default_forecast is None:
        _default_forecast = ForecastTool()
    return _default_forecast


@tool
async def forecast_symbol(symbol: str) -> str:
    """Generate a multi-timeframe market forecast for a trading symbol.

    Combines technical, fundamental, news sentiment, and COT positioning
    analysis into a comprehensive forecast with confidence scoring per
    timeframe (intraday, daily, weekly, monthly).

    Args:
        symbol: Trading symbol to forecast (e.g., 'AAPL', 'EURUSD')

    Returns:
        JSON string with composite forecast direction, confidence,
        timeframe-specific forecasts with target prices and probabilities.
    """
    try:
        ft = _get_default_forecast()
        result = await ft.forecast(symbol)
        return json.dumps(result.model_dump(), indent=2, default=str)
    except Exception as exc:
        logger.error("forecast_symbol tool error: %s", exc)
        return json.dumps({"error": f"Forecast failed: {exc}", "symbol": symbol})


__all__ = [
    "ForecastTool",
    "ForecastTimeframe",
    "ForecastDirection",
    "ForecastConfidence",
    "TechnicalForecast",
    "FundamentalForecast",
    "NewsSentimentForecast",
    "COTForecast",
    "TimeframeForecast",
    "ForecastResult",
    "ForecastAccuracy",
    "forecast_symbol",
]
