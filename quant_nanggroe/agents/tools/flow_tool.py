"""Flow Tool — Whale Flow & COT Positioning Analysis.

Provides tools for analyzing Commitment of Traders (COT) data,
whale wallet tracking, flow direction scoring, and positioning
crowd analysis.

Features
--------
* CFTC Commitment of Traders data parsing
* Whale wallet tracking (large transaction alerts)
* Flow direction scoring (buy/sell pressure from institutional)
* Positioning crowd analysis (contrarian signals)
* LangChain @tool function for agent consumption

References
----------
CFTC COT reports: https://www.cftc.gov/MarketReports/CommitmentsofTraders/
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
        """Fallback no-op decorator when langchain is not installed."""
        if func is not None:
            return func
        def decorator(f):
            return f
        return decorator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums and models
# ---------------------------------------------------------------------------

class FlowDirection(str, Enum):
    """Flow direction classification."""
    STRONG_BUY = "STRONG_BUY"
    MODERATE_BUY = "MODERATE_BUY"
    NEUTRAL = "NEUTRAL"
    MODERATE_SELL = "MODERATE_SELL"
    STRONG_SELL = "STRONG_SELL"


class PositioningSignal(str, Enum):
    """Positioning crowd signal."""
    CROWDED_LONG = "CROWDED_LONG"
    CROWDED_SHORT = "CROWDED_SHORT"
    BALANCED = "BALANCED"
    CONTRARIAN_BUY = "CONTRARIAN_BUY"
    CONTRARIAN_SELL = "CONTRARIAN_SELL"


class COTReport(BaseModel):
    """CFTC Commitment of Traders report data."""
    symbol: str = Field(..., description="Trading symbol")
    report_date: str = Field("", description="Report date")
    commercial_long: int = Field(0, description="Commercial (hedger) long positions")
    commercial_short: int = Field(0, description="Commercial (hedger) short positions")
    non_commercial_long: int = Field(0, description="Non-commercial (speculator) long positions")
    non_commercial_short: int = Field(0, description="Non-commercial (speculator) short positions")
    non_reportable_long: int = Field(0, description="Non-reportable long positions")
    non_reportable_short: int = Field(0, description="Non-reportable short positions")
    open_interest: int = Field(0, description="Total open interest")


class WhaleTransaction(BaseModel):
    """Whale (large) transaction record."""
    tx_hash: str = Field("", description="Transaction hash")
    symbol: str = Field("", description="Trading symbol")
    side: str = Field("", description="BUY or SELL")
    amount: float = Field(0.0, description="Transaction amount in base currency")
    value_usd: float = Field(0.0, description="Transaction value in USD")
    timestamp: str = Field("", description="Transaction timestamp")
    wallet_address: str = Field("", description="Wallet address")
    exchange: str = Field("", description="Exchange involved")


class FlowScore(BaseModel):
    """Composite flow direction score."""
    symbol: str = Field(..., description="Trading symbol")
    score: float = Field(0.0, description="Flow score (-1.0 to +1.0)")
    direction: FlowDirection = Field(FlowDirection.NEUTRAL)
    institutional_pressure: float = Field(0.0, description="Institutional buy/sell pressure")
    retail_pressure: float = Field(0.0, description="Retail buy/sell pressure")
    whale_activity: float = Field(0.0, description="Whale activity level (0-1)")
    confidence: float = Field(0.0, description="Confidence level (0-1)")
    timestamp: str = Field("")


class PositioningAnalysis(BaseModel):
    """Positioning crowd analysis result."""
    symbol: str = Field(..., description="Trading symbol")
    signal: PositioningSignal = Field(PositioningSignal.BALANCED)
    commercial_net: float = Field(0.0, description="Commercial net positioning")
    speculative_net: float = Field(0.0, description="Speculative net positioning")
    z_score: float = Field(0.0, description="Z-score of current positioning vs history")
    percentile: float = Field(0.0, description="Percentile of current positioning (0-100)")
    contrarian_signal: Optional[str] = Field(None, description="Contrarian signal if extreme")
    timestamp: str = Field("")


# ---------------------------------------------------------------------------
# Flow Tool
# ---------------------------------------------------------------------------

class FlowTool:
    """Whale flow and COT positioning analysis tool for agent consumption.

    Provides institutional flow analysis, whale tracking, COT data parsing,
    and positioning crowd analysis for contrarian signals.

    When COT data or whale tracking APIs are unavailable, the tool gracefully
    degrades and returns low-confidence estimates.

    Usage::

        tool = FlowTool()
        flow = await tool.analyze_flow("EURUSD")
        positioning = await tool.analyze_positioning("GC")
    """

    def __init__(self, cache_ttl: int = 3600) -> None:
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._cache_ttl = cache_ttl

    # ----- COT Data -----

    async def fetch_cot_data(self, symbol: str) -> COTReport:
        """Fetch CFTC Commitment of Traders data for a symbol.

        Tries to fetch from the CFTC website or a data provider.
        Returns a placeholder with low-confidence estimates when
        data is not available.

        Args:
            symbol: Commodity or futures symbol (e.g., "GC", "CL", "EUR").

        Returns:
            COTReport with positioning data.
        """
        cache_key = f"cot:{symbol}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        try:
            data = await self._fetch_cot_from_provider(symbol)
            if data:
                self._set_cache(cache_key, data)
                return data
        except Exception as exc:
            logger.debug("COT fetch failed for %s: %s", symbol, exc)

        # Return placeholder
        report = COTReport(
            symbol=symbol,
            report_date=datetime.now(tz=timezone.utc).strftime("%Y-%m-%d"),
            commercial_long=0,
            commercial_short=0,
            non_commercial_long=0,
            non_commercial_short=0,
        )
        return report

    async def _fetch_cot_from_provider(self, symbol: str) -> Optional[COTReport]:
        """Fetch COT data from a data provider."""
        try:
            import urllib.request
            import json as _json

            # Try CFTC API or alternative provider
            url = f"https://api.cftc.gov/api/v1/cot?symbol={symbol}"
            req = urllib.request.Request(url, headers={"User-Agent": "QuantNanggroeAI/2.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = _json.loads(resp.read().decode())

            if data:
                item = data[0] if isinstance(data, list) else data
                return COTReport(
                    symbol=symbol,
                    report_date=item.get("report_date", ""),
                    commercial_long=int(item.get("commercial_long", 0)),
                    commercial_short=int(item.get("commercial_short", 0)),
                    non_commercial_long=int(item.get("non_commercial_long", 0)),
                    non_commercial_short=int(item.get("non_commercial_short", 0)),
                )
        except Exception:
            logger.exception("unhandled_error")
            pass

        return None

    # ----- Whale Tracking -----

    async def track_whales(
        self,
        symbol: str,
        min_value_usd: float = 100_000,
        limit: int = 20,
    ) -> List[WhaleTransaction]:
        """Track large (whale) transactions for a symbol.

        When blockchain/whale tracking APIs are unavailable, returns
        an empty list.

        Args:
            symbol: Trading symbol.
            min_value_usd: Minimum transaction value to qualify as whale.
            limit: Maximum number of transactions.

        Returns:
            List of WhaleTransaction records.
        """
        cache_key = f"whale:{symbol}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        try:
            transactions = await self._fetch_whale_transactions(symbol, min_value_usd, limit)
            if transactions:
                self._set_cache(cache_key, transactions)
                return transactions
        except Exception as exc:
            logger.debug("Whale tracking failed for %s: %s", symbol, exc)

        return []

    async def _fetch_whale_transactions(
        self,
        symbol: str,
        min_value_usd: float,
        limit: int,
    ) -> List[WhaleTransaction]:
        """Fetch whale transactions from provider."""
        # Placeholder - in production, connect to Whale Alert, Arkham, etc.
        return []

    # ----- Flow Analysis -----

    async def analyze_flow(self, symbol: str) -> FlowScore:
        """Analyze flow direction and institutional pressure for a symbol.

        Combines COT data, whale tracking, and market data to produce
        a composite flow score.

        Args:
            symbol: Trading symbol.

        Returns:
            FlowScore with composite analysis.
        """
        cache_key = f"flow:{symbol}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        # Fetch COT data
        cot = await self.fetch_cot_data(symbol)

        # Fetch whale transactions
        whales = await self.track_whales(symbol)

        # Calculate institutional pressure from COT
        institutional_pressure = 0.0
        if cot.non_commercial_long + cot.non_commercial_short > 0:
            net_spec = cot.non_commercial_long - cot.non_commercial_short
            total_spec = cot.non_commercial_long + cot.non_commercial_short
            institutional_pressure = net_spec / total_spec if total_spec > 0 else 0.0

        # Calculate retail pressure
        retail_pressure = 0.0
        if cot.non_reportable_long + cot.non_reportable_short > 0:
            net_retail = cot.non_reportable_long - cot.non_reportable_short
            total_retail = cot.non_reportable_long + cot.non_reportable_short
            retail_pressure = net_retail / total_retail if total_retail > 0 else 0.0

        # Calculate whale activity
        whale_buy_volume = sum(w.value_usd for w in whales if w.side == "BUY")
        whale_sell_volume = sum(w.value_usd for w in whales if w.side == "SELL")
        whale_total = whale_buy_volume + whale_sell_volume
        whale_activity = min(whale_total / 1_000_000, 1.0)  # Normalize to 0-1

        # Composite score
        score = (
            institutional_pressure * 0.5
            + retail_pressure * 0.2
            + (1 if whale_buy_volume > whale_sell_volume else -1) * 0.3 * min(whale_activity, 1.0)
        )
        score = max(-1.0, min(1.0, score))

        # Direction
        if score > 0.4:
            direction = FlowDirection.STRONG_BUY
        elif score > 0.15:
            direction = FlowDirection.MODERATE_BUY
        elif score < -0.4:
            direction = FlowDirection.STRONG_SELL
        elif score < -0.15:
            direction = FlowDirection.MODERATE_SELL
        else:
            direction = FlowDirection.NEUTRAL

        # Confidence
        confidence = 0.1  # Low default
        if cot.non_commercial_long + cot.non_commercial_short > 0:
            confidence += 0.3
        if whales:
            confidence += 0.2
        confidence = min(confidence, 0.8)

        result = FlowScore(
            symbol=symbol,
            score=round(score, 4),
            direction=direction,
            institutional_pressure=round(institutional_pressure, 4),
            retail_pressure=round(retail_pressure, 4),
            whale_activity=round(whale_activity, 4),
            confidence=round(confidence, 4),
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
        )

        self._set_cache(cache_key, result)
        return result

    # ----- Positioning Analysis -----

    async def analyze_positioning(self, symbol: str) -> PositioningAnalysis:
        """Analyze positioning crowd for contrarian signals.

        Uses COT data to identify extreme positioning that may
        indicate a contrarian opportunity.

        Args:
            symbol: Commodity or futures symbol.

        Returns:
            PositioningAnalysis with crowd signal.
        """
        cache_key = f"positioning:{symbol}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        cot = await self.fetch_cot_data(symbol)

        # Calculate net positioning
        commercial_net = float(cot.commercial_long - cot.commercial_short)
        speculative_net = float(cot.non_commercial_long - cot.non_commercial_short)

        # Calculate z-score (simplified)
        total_non_commercial = cot.non_commercial_long + cot.non_commercial_short
        z_score = 0.0
        percentile = 50.0

        if total_non_commercial > 0:
            # Simplified z-score based on ratio
            ratio = speculative_net / total_non_commercial
            z_score = ratio * 3.0  # Rough approximation
            percentile = max(0, min(100, 50 + ratio * 50))

        # Determine signal
        signal = PositioningSignal.BALANCED
        contrarian_signal = None

        if z_score > 2.0:
            signal = PositioningSignal.CROWDED_LONG
            contrarian_signal = "CONTRARIAN_SELL — Speculators are extremely long"
        elif z_score > 1.0:
            signal = PositioningSignal.CROWDED_LONG
        elif z_score < -2.0:
            signal = PositioningSignal.CROWDED_SHORT
            contrarian_signal = "CONTRARIAN_BUY — Speculators are extremely short"
        elif z_score < -1.0:
            signal = PositioningSignal.CROWDED_SHORT

        # Commercial hedgers are typically contrarian
        if commercial_net < 0 and speculative_net > 0 and abs(z_score) > 1.0:
            signal = PositioningSignal.CONTRARIAN_SELL
        elif commercial_net > 0 and speculative_net < 0 and abs(z_score) > 1.0:
            signal = PositioningSignal.CONTRARIAN_BUY

        result = PositioningAnalysis(
            symbol=symbol,
            signal=signal,
            commercial_net=commercial_net,
            speculative_net=speculative_net,
            z_score=round(z_score, 4),
            percentile=round(percentile, 2),
            contrarian_signal=contrarian_signal,
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
        )

        self._set_cache(cache_key, result)
        return result

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

_default_flow_tool: FlowTool | None = None


def _get_default_flow_tool() -> FlowTool:
    global _default_flow_tool
    if _default_flow_tool is None:
        _default_flow_tool = FlowTool()
    return _default_flow_tool


@tool
async def analyze_flow(symbol: str) -> str:
    """Analyze whale flow and institutional positioning for a trading symbol.

    Fetches CFTC Commitment of Traders data, tracks whale transactions,
    and produces a composite flow score with institutional/retail pressure
    and contrarian positioning signals.

    Args:
        symbol: Trading symbol to analyze (e.g., 'EURUSD', 'GC', 'CL')

    Returns:
        JSON string with flow score, direction, institutional pressure,
        whale activity, and positioning crowd analysis.
    """
    try:
        ft = _get_default_flow_tool()
        flow = await ft.analyze_flow(symbol)
        positioning = await ft.analyze_positioning(symbol)
        return json.dumps({
            "flow_score": flow.model_dump(),
            "positioning": positioning.model_dump(),
        }, indent=2, default=str)
    except Exception as exc:
        logger.error("analyze_flow tool error: %s", exc)
        return json.dumps({"error": f"Flow analysis failed: {exc}", "symbol": symbol})


__all__ = [
    "FlowTool",
    "FlowDirection",
    "PositioningSignal",
    "COTReport",
    "WhaleTransaction",
    "FlowScore",
    "PositioningAnalysis",
    "analyze_flow",
]
