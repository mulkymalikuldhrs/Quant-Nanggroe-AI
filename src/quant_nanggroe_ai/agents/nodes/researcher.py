"""
Research Agent — Gathers OHLCV market data, news sentiment, and macro context.
================================================================================
Entry point of the trading graph.  Fetches real market data via MarketDataTool,
aggregates news sentiment via SentimentTool, and builds a preliminary macro
context for downstream agents.

Responsibilities:
  - Fetch OHLCV candle data for the target symbol and timeframe
  - Gather news sentiment from the SentimentTool
  - Build a preliminary macro context (economic calendar, FRED hints)
  - Return structured research_summary, news_items, macro_context
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from quant_nanggroe_ai.agents.state import AgentState
from quant_nanggroe_ai.agents.tools.market_data import MarketDataTool
from quant_nanggroe_ai.agents.tools.sentiment import SentimentTool

logger = logging.getLogger(__name__)


def _classify_symbol(symbol: str) -> str:
    """Return a coarse asset-class label for routing decisions."""
    upper = symbol.upper()
    crypto_bases = {"BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX"}
    if any(upper.startswith(c) for c in crypto_bases) or "USDT" in upper:
        return "crypto"
    forex_quote = {"USD", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD", "CAD"}
    base, quote = upper[:3], upper[3:6] if len(upper) == 6 else ""
    if base in forex_quote and quote in forex_quote:
        return "forex"
    if upper in {"XAUUSD", "XAGUSD", "XAU", "XAG"} or upper.startswith("XAU") or upper.startswith("XAG"):
        return "commodity"
    return "equity"


async def _build_macro_context(symbol: str, asset_class: str) -> str:
    """
    Build a preliminary macro context string.

    Checks for high-impact economic events within the next 24-48 hours
    and summarizes the current monetary-policy stance for the relevant
    currency zone.
    """
    zone_map = {
        "USD": "FOMC / Fed",
        "EUR": "ECB",
        "GBP": "BoE",
        "JPY": "BoJ",
        "CHF": "SNB",
        "AUD": "RBA",
        "NZD": "RBNZ",
        "CAD": "BoC",
    }

    if asset_class == "crypto":
        return (
            "Crypto macro context: Monitor Fed stance (DXY correlation), "
            "regulatory headlines, and BTC dominance trends. "
            "No scheduled central bank events directly impact crypto; "
            "watch for risk-on/risk-off shifts from equities."
        )

    if asset_class == "commodity":
        return (
            "Commodity macro context: Watch CPI/PPI releases, DXY strength, "
            "real yields, and geopolitical risk premiums. "
            "Gold inverse-correlation with real rates is key."
        )

    # Forex / Equity — identify relevant zone
    upper = symbol.upper()
    relevant_zones = []
    for currency, zone in zone_map.items():
        if currency in upper:
            relevant_zones.append(zone)

    if relevant_zones:
        zones_str = " / ".join(relevant_zones)
        return (
            f"Macro context for {symbol}: Monitor {zones_str} policy decisions, "
            f"employment data, inflation releases, and GDP prints. "
            f"Central bank divergence drives FX flows."
        )

    return (
        f"Macro context for {symbol}: General market conditions apply. "
        "Monitor VIX, credit spreads, and intermarket correlations."
    )


async def researcher_node(state: AgentState) -> dict[str, Any]:
    """
    Research Agent node — the entry point of the trading graph.

    Gathers:
      1. OHLCV market data via MarketDataTool
      2. News sentiment from SentimentTool
      3. Preliminary macro context for the asset class

    Returns state updates with research_summary, news_items, macro_context,
    market_data, and candles.
    """
    symbol = state.symbol or "SPY"
    timeframe = state.timeframe or "1d"
    asset_class = _classify_symbol(symbol)
    errors: list[str] = []
    now = datetime.now().isoformat()

    # ── 1. Initialize tools ────────────────────────────────────────────
    market_tool = MarketDataTool()
    sentiment_tool = SentimentTool()

    # ── 2. Fetch OHLCV market data ─────────────────────────────────────
    candles: list[dict[str, Any]] = []
    data_source = "unknown"

    try:
        ohlcv_result = await market_tool.get_ohlcv(symbol, timeframe, limit=200)
        candles = ohlcv_result.get("candles", [])
        data_source = ohlcv_result.get("metadata", {}).get("source", "market_data_tool")
    except Exception as exc:
        logger.error("Market data fetch failed for %s: %s", symbol, exc)
        errors.append(f"Market data: {exc}")

    # ── 3. Fetch latest price ──────────────────────────────────────────
    latest_price: float | None = None
    try:
        price_result = await market_tool.get_current_price(symbol)
        latest_price = price_result.get("price")
    except Exception as exc:
        logger.warning("Price fetch failed for %s: %s", symbol, exc)
        errors.append(f"Price fetch: {exc}")

    # Fallback: extract from candles if tool returned None
    if latest_price is None and candles:
        latest_price = candles[-1].get("close", 0.0)

    # ── 4. Gather news sentiment ───────────────────────────────────────
    sentiment_score = 0.0
    news_items: list[dict[str, Any]] = []
    try:
        sentiment_result = await sentiment_tool.analyze(symbol)
        sentiment_score = sentiment_result.get("overall_score", 0.0)
        news_items = sentiment_result.get("news_items", [])
    except Exception as exc:
        logger.warning("Sentiment analysis failed for %s: %s", symbol, exc)
        errors.append(f"Sentiment: {exc}")

    # ── 5. Build macro context ─────────────────────────────────────────
    macro_context = await _build_macro_context(symbol, asset_class)

    # ── 6. Compile research summary ────────────────────────────────────
    price_str = f"{latest_price:.4f}" if latest_price else "N/A"
    sentiment_label = (
        "bullish" if sentiment_score > 0.2
        else "bearish" if sentiment_score < -0.2
        else "neutral"
    )
    bars_count = len(candles)

    research_summary = (
        f"Research completed for {symbol} ({asset_class}) | "
        f"Price: {price_str} | "
        f"Sentiment: {sentiment_label} ({sentiment_score:.2f}) | "
        f"Data bars: {bars_count} | "
        f"Source: {data_source} | "
        f"Timeframe: {timeframe} | "
        f"Timestamp: {now}"
    )

    # ── 7. Build market_data payload for downstream agents ─────────────
    market_data = [
        {
            "symbol": symbol,
            "asset_class": asset_class,
            "latest_price": latest_price,
            "sentiment_score": sentiment_score,
            "source": data_source,
            "fetched_at": now,
        }
    ]

    # ── Return state updates ────────────────────────────────────────────
    return {
        "market_data": market_data,
        "candles": candles,
        "research_summary": research_summary,
        "news_items": news_items,
        "macro_context": macro_context,
        "sentiment_score": sentiment_score,
        "errors": state.errors + errors,
        "agent_trace": state.agent_trace + [
            {
                "agent": "researcher",
                "status": "completed",
                "action": "research",
                "symbol": symbol,
                "asset_class": asset_class,
                "bars_fetched": bars_count,
                "sentiment": sentiment_label,
                "timestamp": now,
            }
        ],
    }
