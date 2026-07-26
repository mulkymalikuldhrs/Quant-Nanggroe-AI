"""
Research Agent Tools for Quant Nanggroe AI Trading Framework.

PRODUCTION: Wired to real data providers:
- web_search: Uses real search API when configured
- sec_filing: Uses SEC EDGAR API for real filing data
- news_fetch: Uses SentimentTool for real news aggregation
- financial_data: Uses MarketDataTool + yfinance for real financial data
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Dict, Optional

try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func=None, *args, **kwargs):
        """No-op fallback when langchain_core is not installed."""
        if func is not None:
            return func
        def decorator(f):
            return f
        return decorator


logger = logging.getLogger(__name__)

# ── Lazy imports for real engine components ─────────────────────────────
def _get_sentiment_tool():
    """Lazy-load SentimentTool from shared tools."""
    try:
        from quant_nanggroe.agents.tools.sentiment import SentimentTool
        return SentimentTool()
    except Exception as exc:
        logger.warning("Failed to load SentimentTool: %s", exc)
        return None


def _get_market_data_tool():
    """Lazy-load MarketDataTool from shared tools."""
    try:
        from quant_nanggroe.agents.tools.market_data import MarketDataTool
        return MarketDataTool()
    except Exception as exc:
        logger.warning("Failed to load MarketDataTool: %s", exc)
        return None


def _get_settings():
    """Lazy-load settings for API keys."""
    try:
        from quant_nanggroe.config.settings import get_settings
        return get_settings()
    except Exception as exc:
        logger.warning("Failed to load settings: %s", exc)
        return None


# ── Real data fetchers ─────────────────────────────────────────────────

async def _real_sec_filing(symbol: str, filing_type: str, years: int) -> Optional[Dict]:
    """Fetch real SEC filing data from SEC EDGAR API."""
    try:
        import json as _json
        import urllib.request

        # SEC EDGAR full-text search API
        url = (
            f"https://efts.sec.gov/LATEST/search-index?q=%22{symbol}%22"
            f"&dateRange=custom&startdt=2020-01-01&category=form-type&"
            f"forms={filing_type}"
        )
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "QuantNanggroeAI/2.0 research@nanggroe.ai"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = _json.loads(resp.read().decode())

        filings = []
        for hit in data.get("hits", {}).get("hits", [])[:years]:
            source = hit.get("_source", {})
            filings.append({
                "date": source.get("file_date", ""),
                "type": source.get("form_type", filing_type),
                "summary": source.get("display_names", [f"Filing for {symbol}"])[0] if source.get("display_names") else f"Most recent {filing_type} filing for {symbol.upper()}",
                "key_metrics": {},  # Full metrics require separate filing download
            })

        if filings:
            return {
                "symbol": symbol.upper(),
                "filing_type": filing_type,
                "filings": filings,
                "years_requested": years,
                "_source": "SEC_EDGAR_API",  # PRODUCTION: Wired to real engine
            }
    except Exception as exc:
        logger.debug("SEC EDGAR fetch failed for %s: %s", symbol, exc)

    return None


async def _real_news_fetch(symbol: str, days_back: int, category: Optional[str]) -> Optional[Dict]:
    """Fetch real news using SentimentTool."""
    st = _get_sentiment_tool()
    if st is None:
        return None

    try:
        sentiment_result = await st.analyze(symbol)
        articles = []
        for item in sentiment_result.get("news_items", []):
            articles.append({
                "title": item.get("headline", ""),
                "source": item.get("source", "unknown"),
                "date": item.get("date", ""),
                "sentiment": item.get("sentiment", 0.0),
                "relevance_score": item.get("confidence", 0.0),
                "summary": item.get("headline", ""),
                "event_type": item.get("event_type", "NOISE"),
            })

        return {
            "symbol": symbol.upper(),
            "articles": articles,
            "overall_sentiment": sentiment_result.get("overall_score", 0.0),
            "sentiment_label": sentiment_result.get("label", "NEUTRAL"),
            "days_back": days_back,
            "category": category,
            "_source": "SentimentTool",  # PRODUCTION: Wired to real engine
        }
    except Exception as exc:
        logger.error("SentimentTool news fetch failed for %s: %s", symbol, exc)

    return None


async def _real_financial_data(symbol: str, data_type: str, period: str) -> Optional[Dict]:
    """Fetch real financial data using yfinance."""
    try:
        import yfinance as yf

        ticker = yf.Ticker(symbol)

        if data_type == "overview":
            info = ticker.info or {}
            return {
                "symbol": symbol.upper(),
                "data_type": data_type,
                "period": period,
                "metrics": {
                    "market_cap": info.get("marketCap", "N/A"),
                    "pe_ratio": info.get("trailingPE", "N/A"),
                    "eps": info.get("trailingEps", "N/A"),
                    "dividend_yield": f"{info.get('dividendYield', 0) * 100:.2f}%" if info.get("dividendYield") else "N/A",
                    "beta": info.get("beta", "N/A"),
                    "52_week_high": info.get("fiftyTwoWeekHigh", "N/A"),
                    "52_week_low": info.get("fiftyTwoWeekLow", "N/A"),
                    "avg_volume": info.get("averageVolume", "N/A"),
                    "forward_pe": info.get("forwardPE", "N/A"),
                    "price_to_book": info.get("priceToBook", "N/A"),
                    "revenue_growth": info.get("revenueGrowth", "N/A"),
                },
                "_source": "yfinance",  # PRODUCTION: Wired to real engine
            }
        elif data_type == "income":
            financials = ticker.financials
            if financials is not None and not financials.empty:
                return {
                    "symbol": symbol.upper(),
                    "data_type": data_type,
                    "period": period,
                    "data": financials.to_dict(),
                    "_source": "yfinance",
                }
        elif data_type == "balance":
            balance = ticker.balance_sheet
            if balance is not None and not balance.empty:
                return {
                    "symbol": symbol.upper(),
                    "data_type": data_type,
                    "period": period,
                    "data": balance.to_dict(),
                    "_source": "yfinance",
                }
        elif data_type == "cashflow":
            cashflow = ticker.cashflow
            if cashflow is not None and not cashflow.empty:
                return {
                    "symbol": symbol.upper(),
                    "data_type": data_type,
                    "period": period,
                    "data": cashflow.to_dict(),
                    "_source": "yfinance",
                }
    except Exception as exc:
        logger.error("yfinance financial data fetch failed for %s: %s", symbol, exc)

    return None


# ═══════════════════════════════════════════════════════════════════════
# LangChain @tool functions — PRODUCTION wired
# ═══════════════════════════════════════════════════════════════════════

@tool
def web_search(query: str, num_results: int = 5) -> str:
    """
    Search the web for financial information and market data.

    PRODUCTION: Uses configured search APIs (Tavily, SerpAPI).

    Args:
        query: Search query string
        num_results: Number of results to return (default: 5)

    Returns:
        JSON string with search results
    """
    settings = _get_settings()
    # Try Tavily search API
    tavily_key = getattr(settings, "tavily_api_key", None) if settings else None
    if tavily_key:
        try:
            import json as _json
            import urllib.request

            url = "https://api.tavily.com/search"
            payload = _json.dumps({
                "api_key": tavily_key,
                "query": query,
                "max_results": num_results,
            }).encode()
            req = urllib.request.Request(
                url, data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = _json.loads(resp.read().decode())

            results = []
            for r in data.get("results", []):
                results.append({
                    "title": r.get("title", ""),
                    "snippet": r.get("content", ""),
                    "source": "tavily",
                    "url": r.get("url", ""),
                })

            return json.dumps({  # PRODUCTION: Wired to real engine
                "query": query,
                "results": results,
                "num_results": len(results),
                "_source": "TavilyAPI",
            }, indent=2)
        except Exception as exc:
            logger.error("Tavily search failed: %s", exc)
            raise RuntimeError(
                f"Web search failed via Tavily: {exc}."
            ) from exc

    raise RuntimeError(
        "No search API key configured (tavily_api_key)."
    )


@tool
def sec_filing(symbol: str, filing_type: str = "10-K", years: int = 1) -> str:
    """
    Retrieve SEC filing data for a given symbol.

    PRODUCTION: Uses SEC EDGAR API for real filing data.

    Args:
        symbol: Stock ticker symbol (e.g., AAPL)
        filing_type: Type of SEC filing (10-K, 10-Q, 8-K, DEF 14A)
        years: Number of years of filings to retrieve

    Returns:
        JSON string with SEC filing data
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if not loop.is_running():
            result = loop.run_until_complete(
                _real_sec_filing(symbol, filing_type, years)
            )
            if result is not None:
                return json.dumps(result, indent=2, default=str)
        else:
            # Try synchronous SEC EDGAR request
            try:
                import json as _json
                import urllib.request
                url = (
                    f"https://efts.sec.gov/LATEST/search-index?"
                    f"q=%22{symbol}%22&forms={filing_type}"
                )
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "QuantNanggroeAI/2.0 research@nanggroe.ai"},
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = _json.loads(resp.read().decode())
                filings = []
                for hit in data.get("hits", {}).get("hits", [])[:years]:
                    source = hit.get("_source", {})
                    filings.append({
                        "date": source.get("file_date", ""),
                        "type": source.get("form_type", filing_type),
                        "summary": source.get("display_names", [symbol])[0] if source.get("display_names") else f"{filing_type} filing",
                    })
                return json.dumps({  # PRODUCTION: Wired to real engine
                    "symbol": symbol.upper(),
                    "filing_type": filing_type,
                    "filings": filings,
                    "years_requested": years,
                    "_source": "SEC_EDGAR_API",
                }, indent=2)
            except Exception as exc:
                logger.error("SEC EDGAR sync fetch failed: %s", exc)
    except Exception as exc:
        logger.error("SEC filing fetch failed for %s: %s", symbol, exc)
        raise RuntimeError(
            f"Failed to fetch SEC filings for {symbol}: {exc}."
        ) from exc

    raise RuntimeError(
        f"Cannot fetch SEC filings for {symbol}: real engine unavailable."
    )


@tool
def news_fetch(
    symbol: str,
    days_back: int = 7,
    category: Optional[str] = None,
) -> str:
    """
    Fetch recent news articles for a given symbol.

    PRODUCTION: Uses SentimentTool for real news aggregation from
    Alpha Vantage, Polygon, and yfinance APIs.

    Args:
        symbol: Stock ticker symbol
        days_back: Number of days to look back (default: 7)
        category: Optional news category filter (earnings, mergers, regulatory, etc.)

    Returns:
        JSON string with news articles
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if not loop.is_running():
            result = loop.run_until_complete(
                _real_news_fetch(symbol, days_back, category)
            )
            if result is not None:
                return json.dumps(result, indent=2, default=str)
    except Exception as exc:
        logger.error("News fetch failed for %s: %s", symbol, exc)
        raise RuntimeError(
            f"Failed to fetch news for {symbol}: {exc}."
        ) from exc

    raise RuntimeError(
        f"Cannot fetch news for {symbol}: real engine unavailable."
    )


@tool
def financial_data(
    symbol: str,
    data_type: str = "overview",
    period: str = "annual",
) -> str:
    """
    Retrieve financial data for a given symbol.

    PRODUCTION: Uses yfinance for real financial data (overview, income,
    balance, cashflow, metrics).

    Args:
        symbol: Stock ticker symbol
        data_type: Type of financial data (overview, income, balance, cashflow, metrics)
        period: Data period (annual, quarterly)

    Returns:
        JSON string with financial data
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if not loop.is_running():
            result = loop.run_until_complete(
                _real_financial_data(symbol, data_type, period)
            )
            if result is not None:
                return json.dumps(result, indent=2, default=str)
    except Exception as exc:
        logger.error("Financial data fetch failed for %s: %s", symbol, exc)
        raise RuntimeError(
            f"Failed to fetch financial data for {symbol}: {exc}."
        ) from exc

    raise RuntimeError(
        f"Cannot fetch financial data for {symbol}: real engine unavailable."
    )


# List of all research tools for easy import
RESEARCH_TOOLS = [web_search, sec_filing, news_fetch, financial_data]
