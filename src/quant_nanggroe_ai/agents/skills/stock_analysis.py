"""
Stock Analysis Skill — Fundamental and technical stock analysis via MCP
======================================================================

Ported from mnemosyne MCP server pattern (TypeScript → Python).
Provides AI-powered stock analysis with access to the Quant-Nanggroe-AI
market data, technical analysis, and sentiment tools.

Adapted from:
  - mnemosyne/mcp-server/index.ts (MCP tool pattern)
  - mnemosyne/src/lib/agent/index.ts (AgentEngine tool registry)
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from quant_nanggroe_ai.agents.mcp_protocol import MCPTool, MCPToolResult

logger = logging.getLogger(__name__)


class StockMetrics(BaseModel):
    """Key stock metrics from analysis."""
    symbol: str
    current_price: float = 0.0
    price_change_pct: float = 0.0
    volume: float = 0.0
    market_cap: str = "N/A"
    pe_ratio: float = 0.0
    fifty_two_week_high: float = 0.0
    fifty_two_week_low: float = 0.0
    sma_20: float = 0.0
    sma_50: float = 0.0
    rsi_14: float = 0.0
    macd_signal: str = "neutral"
    sentiment_score: float = 0.0
    recommendation: str = "HOLD"


class StockAnalysisSkill(MCPTool):
    """
    MCP skill for comprehensive stock analysis.

    Combines market data, technical indicators, and sentiment analysis
    to provide a holistic view of a stock's current status and outlook.
    """

    @property
    def name(self) -> str:
        return "stock_analysis"

    @property
    def description(self) -> str:
        return (
            "Perform comprehensive stock analysis including price data, "
            "technical indicators (SMA, RSI, MACD), fundamental metrics, "
            "and sentiment analysis. Returns a structured StockMetrics result."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "analyze",
                        "compare",
                        "screener",
                        "sector_analysis",
                    ],
                    "description": "The stock analysis action to perform.",
                },
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol (e.g. 'AAPL', 'TSLA').",
                },
                "symbols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of symbols for comparison.",
                },
                "sector": {
                    "type": "string",
                    "description": "Market sector for sector analysis.",
                },
                "timeframe": {
                    "type": "string",
                    "enum": ["1d", "1w", "1m", "3m", "6m", "1y"],
                    "default": "3m",
                    "description": "Analysis timeframe.",
                },
                "metrics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific metrics to include (default: all).",
                },
            },
            "required": ["action"],
            "additionalProperties": False,
        }

    @property
    def tags(self) -> list[str]:
        return ["finance", "stock-analysis", "read-only", "market-data"]

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        """Execute a stock analysis action."""
        action = kwargs.get("action")
        if not action:
            from quant_nanggroe_ai.exceptions import AgentError
            raise AgentError("'action' is required for stock_analysis skill")

        if action == "analyze":
            return await self._analyze_stock(kwargs)
        elif action == "compare":
            return await self._compare_stocks(kwargs)
        elif action == "screener":
            return await self._screener(kwargs)
        elif action == "sector_analysis":
            return await self._sector_analysis(kwargs)
        else:
            from quant_nanggroe_ai.exceptions import AgentError
            raise AgentError(f"Unknown stock_analysis action: '{action}'")

    async def _analyze_stock(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Full analysis of a single stock."""
        symbol = kwargs.get("symbol")
        if not symbol:
            from quant_nanggroe_ai.exceptions import AgentError
            raise AgentError("'symbol' is required for analyze action")

        timeframe = kwargs.get("timeframe", "3m")
        result: dict[str, Any] = {"symbol": symbol, "timeframe": timeframe}

        # Fetch market data via existing tools
        try:
            from quant_nanggroe_ai.agents.tools.market_data import MarketDataTool
            mdt = MarketDataTool()
            ohlcv = await mdt.get_ohlcv(symbol=symbol, timeframe=timeframe, limit=100)
            result["ohlcv"] = ohlcv

            # Calculate basic metrics from OHLCV
            if isinstance(ohlcv, dict) and "data" in ohlcv:
                candles = ohlcv["data"]
                if candles and len(candles) > 0:
                    latest = candles[-1]
                    result["current_price"] = latest.get("close", 0)
                    if len(candles) >= 2:
                        prev_close = candles[-2].get("close", 0)
                        if prev_close > 0:
                            result["price_change_pct"] = round(
                                (latest.get("close", 0) - prev_close) / prev_close * 100, 2
                            )
                    result["volume"] = latest.get("volume", 0)
        except Exception as e:
            logger.warning("Market data fetch failed for %s: %s", symbol, e)
            result["ohlcv_error"] = str(e)

        # Fetch technical analysis
        try:
            from quant_nanggroe_ai.agents.tools.technical import TechnicalTool
            tt = TechnicalTool()
            tech = await tt.analyze(symbol=symbol, timeframe=timeframe)
            result["technical"] = tech
        except Exception as e:
            logger.warning("Technical analysis failed for %s: %s", symbol, e)
            result["technical_error"] = str(e)

        # Fetch sentiment
        try:
            from quant_nanggroe_ai.agents.tools.sentiment import SentimentTool
            st = SentimentTool()
            sentiment = await st.analyze(symbol=symbol)
            result["sentiment"] = sentiment
        except Exception as e:
            logger.warning("Sentiment analysis failed for %s: %s", symbol, e)
            result["sentiment_error"] = str(e)

        return result

    async def _compare_stocks(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Compare multiple stocks side-by-side."""
        symbols = kwargs.get("symbols")
        if not symbols or not isinstance(symbols, list):
            from quant_nanggroe_ai.exceptions import AgentError
            raise AgentError("'symbols' (list) is required for compare action")

        timeframe = kwargs.get("timeframe", "3m")
        comparisons = {}
        for sym in symbols[:10]:  # Limit to 10 symbols
            try:
                analysis = await self._analyze_stock({"symbol": sym, "timeframe": timeframe})
                comparisons[sym] = {
                    "current_price": analysis.get("current_price", 0),
                    "price_change_pct": analysis.get("price_change_pct", 0),
                    "technical": analysis.get("technical", {}),
                    "sentiment": analysis.get("sentiment", {}),
                }
            except Exception as e:
                comparisons[sym] = {"error": str(e)}

        return {"comparisons": comparisons, "count": len(comparisons)}

    async def _screener(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Screen stocks based on criteria."""
        # Placeholder for screener logic — would connect to data providers
        return {
            "message": "Stock screener — configure data providers for screening",
            "criteria": kwargs.get("metrics", []),
        }

    async def _sector_analysis(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Analyze a market sector."""
        sector = kwargs.get("sector", "technology")
        return {
            "sector": sector,
            "message": f"Sector analysis for {sector} — configure data providers for sector data",
        }
