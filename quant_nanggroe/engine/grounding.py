"""Market Data Grounding for LLM Workers (from Vibe-Trading pattern).

LLMs cite stale training-data prices by default. This module:
1. Pre-fetches real OHLCV data before any LLM call
2. Formats it as a "Ground Truth" block
3. Injects it into the worker prompt with explicit instructions
   to cite ONLY these prices, not training data

This prevents the critical bug where LLMs hallucinate prices
from their training data, which could lead to catastrophic
trading decisions based on stale or incorrect information.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# Common stopwords that look like tickers but aren't
_TICKER_STOPWORDS = frozenset({
    "ETF", "CEO", "GDP", "CPI", "PPI", "FOMC", "SEC", "FDA",
    "USA", "UK", "EU", "AP", "BBC", "CNN", "NBC", "CBS",
    "AND", "FOR", "NOT", "ARE", "BUT", "ALL", "CAN", "HAS",
    "THE", "NEW", "ONE", "OUR", "OUT", "DAY", "GET", "HAS",
    "HIS", "HOW", "ITS", "MAY", "NOW", "OLD", "SEE", "WAY",
    "WHO", "DID", "LET", "SAY", "SHE", "TOO", "USE",
})

# Suffix patterns for different markets
_SUFFIX_PATTERNS = {
    ".US": "equity_us",
    ".HK": "equity_hk",
    ".SH": "equity_china",
    ".SZ": "equity_china",
    "-USDT": "crypto",
    "-USD": "crypto",
    "-BUSD": "crypto",
    ".L": "equity_london",
    ".DE": "equity_frankfurt",
    ".JP": "equity_tokyo",
    ".SI": "equity_singapore",
    ".AX": "equity_australia",
    ".TO": "equity_toronto",
}


def extract_symbols_from_text(text: str) -> Set[str]:
    """Extract trading symbols from text.

    Detects:
    - Suffixed symbols (NVDA.US, 700.HK, BTC-USDT)
    - Bare US tickers (1-5 uppercase letters)
    - Forex pairs (EUR/USD, GBP/JPY)
    - Crypto pairs (BTC/USDT, ETH/ETH)

    Parameters
    ----------
    text:
        Input text to scan for symbols.

    Returns
    -------
    set[str]
        Extracted symbols.
    """
    symbols = set()

    # 1. Suffixed symbols (highest confidence)
    for suffix in _SUFFIX_PATTERNS:
        pattern = rf'\b([A-Z0-9]{{1,6}}{re.escape(suffix)})\b'
        for match in re.finditer(pattern, text):
            symbols.add(match.group(1))

    # 2. Crypto with dash (BTC-USDT)
    for match in re.finditer(r'\b([A-Z]{2,6}-(?:USDT|USD|BUSD|BTC|ETH))\b', text):
        symbols.add(match.group(1))

    # 3. Slash-separated pairs (EUR/USD, BTC/USDT)
    for match in re.finditer(r'\b([A-Z]{2,6}/[A-Z]{2,6})\b', text):
        symbols.add(match.group(1))

    # 4. Bare US tickers (1-5 uppercase letters, not stopwords)
    for match in re.finditer(r'\b([A-Z]{1,5})\b', text):
        candidate = match.group(1)
        if candidate not in _TICKER_STOPWORDS and len(candidate) >= 2:
            # Only add if it looks like a real ticker (not a common word)
            symbols.add(candidate + ".US")

    return symbols


async def fetch_grounding_data(
    symbols: Set[str],
    data_manager: Any = None,
    window_days: int = 30,
) -> Dict[str, Any]:
    """Pre-fetch real market data for grounding.

    Parameters
    ----------
    symbols:
        Set of symbols to fetch data for.
    data_manager:
        Data provider manager instance.
    window_days:
        Number of days of history to fetch.

    Returns
    -------
    dict
        Mapping of symbol → OHLCV data.
    """
    grounding: Dict[str, Any] = {}

    for symbol in symbols:
        try:
            if data_manager is not None:
                # Use real data provider
                ohlcv = await data_manager.get_ohlcv(
                    symbol=symbol,
                    timeframe="1d",
                    limit=window_days,
                )
                if ohlcv is not None and len(ohlcv) > 0:
                    latest = ohlcv.iloc[-1] if hasattr(ohlcv, 'iloc') else ohlcv[-1]
                    grounding[symbol] = {
                        "latest_price": float(latest.get("close", 0)),
                        "latest_volume": float(latest.get("volume", 0)),
                        "latest_date": str(latest.name) if hasattr(latest, 'name') else "N/A",
                        "period_high": float(ohlcv["high"].max()) if hasattr(ohlcv, 'max') else 0,
                        "period_low": float(ohlcv["low"].min()) if hasattr(ohlcv, 'min') else 0,
                        "data_source": "live",
                    }
                    continue

            # Fallback: mark as unavailable (NO fake prices)
            grounding[symbol] = {
                "latest_price": None,
                "data_source": "unavailable",
                "warning": "Real-time price data not available. Do NOT cite prices from memory.",
            }

        except Exception as e:
            logger.warning("Grounding data fetch failed for %s: %s", symbol, e)
            grounding[symbol] = {
                "latest_price": None,
                "data_source": "error",
                "error": str(e),
            }

    return grounding


def format_grounding_block(grounding: Dict[str, Any]) -> str:
    """Format grounding data as a markdown block for LLM prompt injection.

    Parameters
    ----------
    grounding:
        Symbol → price data mapping from fetch_grounding_data().

    Returns
    -------
    str
        Markdown-formatted grounding block.
    """
    lines = [
        "## Ground Truth — Recent Market Data",
        "",
        "**These are the authoritative current prices for this run.**",
        "Do NOT cite prices from your training data — they are stale and unreliable.",
        "If a symbol shows 'unavailable', state that you cannot provide a price for it.",
        "",
    ]

    for symbol, data in sorted(grounding.items()):
        source = data.get("data_source", "unknown")
        if source == "live":
            price = data.get("latest_price", "N/A")
            volume = data.get("latest_volume", "N/A")
            date = data.get("latest_date", "N/A")
            lines.append(f"- **{symbol}**: ${price:,.2f}" if isinstance(price, (int, float)) else f"- **{symbol}**: {price}")
            lines.append(f"  - Volume: {volume:,.0f}" if isinstance(volume, (int, float)) else f"  - Volume: {volume}")
            lines.append(f"  - As of: {date}")
        elif source in ("unavailable", "error"):
            lines.append(f"- **{symbol}**: ⚠️ PRICE DATA UNAVAILABLE — do not cite a price")
        else:
            lines.append(f"- **{symbol}**: unknown state")

    lines.append("")
    lines.append("**End of Ground Truth block.**")

    return "\n".join(lines)


def create_grounding_prompt(
    user_prompt: str,
    data_manager: Any = None,
    window_days: int = 30,
) -> str:
    """Create a grounded version of a prompt with real market data.

    Synchronous wrapper for use in non-async contexts.

    Parameters
    ----------
    user_prompt:
        Original user prompt.
    data_manager:
        Data provider manager.
    window_days:
        Days of history for grounding data.

    Returns
    -------
    str
        Enhanced prompt with grounding block prepended.
    """
    import asyncio

    symbols = extract_symbols_from_text(user_prompt)
    if not symbols:
        return user_prompt

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're in an async context, can't use run()
            grounding = {}
            for symbol in symbols:
                grounding[symbol] = {
                    "latest_price": None,
                    "data_source": "unavailable",
                    "warning": "Cannot fetch in async context",
                }
        else:
            grounding = loop.run_until_complete(
                fetch_grounding_data(symbols, data_manager, window_days)
            )
    except RuntimeError:
        grounding = {}
        for symbol in symbols:
            grounding[symbol] = {
                "latest_price": None,
                "data_source": "unavailable",
            }

    grounding_block = format_grounding_block(grounding)
    return f"{grounding_block}\n\n---\n\n{user_prompt}"
