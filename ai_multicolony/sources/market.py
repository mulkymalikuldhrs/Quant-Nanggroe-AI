"""Market data feeds for the AI-MultiColony ecosystem.

Provides the :class:`MarketSource` that fetches real-time and historical
market data across equities, cryptocurrencies, and foreign exchange.

Each market segment has its own data model and normalisation logic,
ensuring consistent interfaces for downstream agents.

**Live data mode** – When ``_LIVE_MODE = True`` (default), the source
calls real APIs (yfinance, CoinGecko, Binance).  If every live call
fails, the module falls back to :data:`SAMPLE_EQUITY_DATA` /
:data:`SAMPLE_CRYPTO_DATA` / :data:`SAMPLE_FOREX_DATA` and emits a
``logging.warning`` so operators are never silently served stale data.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiohttp
from cachetools import TTLCache
from pydantic import BaseModel, Field, ConfigDict

from .base import (
    SourceCategory,
    SourceConfig,
    SourceItem,
    SourceProvider,
    SourceReliability,
    SourceResult,
)

logger = logging.getLogger(__name__)

# ── Feature flag ──────────────────────────────────────────────────────────

_LIVE_MODE: bool = True
"""When ``True`` the source calls real APIs.  Set to ``False`` to force
SAMPLE_DATA usage (useful in offline tests)."""

_API_TIMEOUT: float = 10.0
"""Default timeout in seconds for every outbound HTTP call."""

_UA = "Quant-Nanggroe-AI/1.0 (market-source; +https://github.com/quant-nanggroe)"

# ── Data models ──────────────────────────────────────────────────────────────


class EquityQuote(BaseModel):
    """Stock/equity price quote."""
    symbol: str = ""
    name: str = ""
    price: float = 0.0
    change: float = 0.0
    change_pct: float = 0.0
    volume: int = 0
    market_cap_bn: float = 0.0
    pe_ratio: float = 0.0
    high_52w: float = 0.0
    low_52w: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    _source: str = ""
    _fetched_at: str = ""


class CryptoQuote(BaseModel):
    """Cryptocurrency price quote."""
    symbol: str = ""
    name: str = ""
    price_usd: float = 0.0
    change_24h_pct: float = 0.0
    volume_24h_bn: float = 0.0
    market_cap_bn: float = 0.0
    dominance_pct: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    _source: str = ""
    _fetched_at: str = ""


class ForexQuote(BaseModel):
    """Foreign exchange rate quote."""
    pair: str = ""
    rate: float = 0.0
    change: float = 0.0
    change_pct: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    _source: str = ""
    _fetched_at: str = ""


# ── Sample / fallback data ──────────────────────────────────────────────────

SAMPLE_EQUITY_DATA: Dict[str, Dict[str, Any]] = {
    "AAPL": {"name": "Apple Inc.", "price": 189.84, "change": 2.45, "change_pct": 1.31, "volume": 54_200_000, "market_cap_bn": 2940, "pe_ratio": 29.8, "high_52w": 199.62, "low_52w": 124.17},
    "MSFT": {"name": "Microsoft Corp.", "price": 425.52, "change": -1.23, "change_pct": -0.29, "volume": 22_100_000, "market_cap_bn": 3160, "pe_ratio": 36.2, "high_52w": 430.82, "low_52w": 309.45},
    "GOOGL": {"name": "Alphabet Inc.", "price": 175.98, "change": 3.12, "change_pct": 1.80, "volume": 28_500_000, "market_cap_bn": 2180, "pe_ratio": 25.1, "high_52w": 180.40, "low_52w": 115.35},
    "AMZN": {"name": "Amazon.com Inc.", "price": 185.07, "change": 1.89, "change_pct": 1.03, "volume": 48_300_000, "market_cap_bn": 1920, "pe_ratio": 58.7, "high_52w": 189.77, "low_52w": 118.35},
    "NVDA": {"name": "NVIDIA Corp.", "price": 878.36, "change": 15.67, "change_pct": 1.82, "volume": 41_700_000, "market_cap_bn": 2170, "pe_ratio": 72.3, "high_52w": 974.00, "low_52w": 373.56},
    "META": {"name": "Meta Platforms", "price": 502.30, "change": -3.45, "change_pct": -0.68, "volume": 18_200_000, "market_cap_bn": 1280, "pe_ratio": 26.4, "high_52w": 531.49, "low_52w": 274.38},
    "TSLA": {"name": "Tesla Inc.", "price": 175.21, "change": -5.82, "change_pct": -3.22, "volume": 112_500_000, "market_cap_bn": 558, "pe_ratio": 42.1, "high_52w": 299.29, "low_52w": 138.80},
    "BRK.B": {"name": "Berkshire Hathaway", "price": 415.80, "change": 0.95, "change_pct": 0.23, "volume": 3_400_000, "market_cap_bn": 895, "pe_ratio": 9.2, "high_52w": 425.30, "low_52w": 317.30},
}

SAMPLE_CRYPTO_DATA: Dict[str, Dict[str, Any]] = {
    "BTC": {"name": "Bitcoin", "price_usd": 67250.00, "change_24h_pct": 1.45, "volume_24h_bn": 32.5, "market_cap_bn": 1320, "dominance_pct": 52.3},
    "ETH": {"name": "Ethereum", "price_usd": 3520.00, "change_24h_pct": 2.12, "volume_24h_bn": 18.7, "market_cap_bn": 423, "dominance_pct": 16.8},
    "BNB": {"name": "BNB", "price_usd": 595.00, "change_24h_pct": -0.85, "volume_24h_bn": 2.1, "market_cap_bn": 92, "dominance_pct": 3.6},
    "SOL": {"name": "Solana", "price_usd": 148.50, "change_24h_pct": 3.45, "volume_24h_bn": 4.2, "market_cap_bn": 65, "dominance_pct": 2.6},
    "XRP": {"name": "XRP", "price_usd": 0.62, "change_24h_pct": -1.23, "volume_24h_bn": 1.8, "market_cap_bn": 34, "dominance_pct": 1.3},
    "ADA": {"name": "Cardano", "price_usd": 0.48, "change_24h_pct": 0.78, "volume_24h_bn": 0.6, "market_cap_bn": 17, "dominance_pct": 0.7},
    "AVAX": {"name": "Avalanche", "price_usd": 38.20, "change_24h_pct": 4.12, "volume_24h_bn": 1.2, "market_cap_bn": 15, "dominance_pct": 0.6},
    "DOT": {"name": "Polkadot", "price_usd": 7.35, "change_24h_pct": 1.98, "volume_24h_bn": 0.5, "market_cap_bn": 10, "dominance_pct": 0.4},
}

SAMPLE_FOREX_DATA: Dict[str, Dict[str, Any]] = {
    "EUR/USD": {"rate": 1.0845, "change": 0.0023, "change_pct": 0.21, "bid": 1.0844, "ask": 1.0846},
    "GBP/USD": {"rate": 1.2715, "change": -0.0015, "change_pct": -0.12, "bid": 1.2714, "ask": 1.2716},
    "USD/JPY": {"rate": 154.82, "change": 0.45, "change_pct": 0.29, "bid": 154.81, "ask": 154.83},
    "USD/CHF": {"rate": 0.8912, "change": 0.0018, "change_pct": 0.20, "bid": 0.8911, "ask": 0.8913},
    "AUD/USD": {"rate": 0.6623, "change": -0.0032, "change_pct": -0.48, "bid": 0.6622, "ask": 0.6624},
    "USD/CAD": {"rate": 1.3645, "change": 0.0025, "change_pct": 0.18, "bid": 1.3644, "ask": 1.3646},
    "NZD/USD": {"rate": 0.6098, "change": -0.0018, "change_pct": -0.29, "bid": 0.6097, "ask": 0.6099},
    "EUR/GBP": {"rate": 0.8528, "change": 0.0012, "change_pct": 0.14, "bid": 0.8527, "ask": 0.8529},
}

# Backward-compatible aliases (referenced by __init__.py and tests)
EQUITY_DATA = SAMPLE_EQUITY_DATA
CRYPTO_DATA = SAMPLE_CRYPTO_DATA
FOREX_DATA = SAMPLE_FOREX_DATA

# ── Live API helpers ────────────────────────────────────────────────────────

# yfinance symbol -> canonical symbol mapping
_YF_EQUITY_SYMBOLS: List[str] = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
]

_YF_FOREX_PAIRS: Dict[str, str] = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X",
    "USD/CHF": "USDCHF=X",
    "AUD/USD": "AUDUSD=X",
    "USD/CAD": "USDCAD=X",
    "NZD/USD": "NZDUSD=X",
    "EUR/GBP": "EURGBP=X",
}

# CoinGecko id -> symbol mapping
_CG_CRYPTO_IDS: Dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "BNB": "binancecoin",
    "SOL": "solana",
    "XRP": "ripple",
    "ADA": "cardano",
    "AVAX": "avalanche-2",
    "DOT": "polkadot",
}

# Binance symbol -> symbol mapping (fallback)
_BINANCE_SYMBOLS: Dict[str, str] = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "BNB": "BNBUSDT",
    "SOL": "SOLUSDT",
    "XRP": "XRPUSDT",
    "ADA": "ADAUSDT",
    "AVAX": "AVAXUSDT",
    "DOT": "DOTUSDT",
}


async def _fetch_yfinance_equity(
    session: aiohttp.ClientSession,
    symbol: str,
    yf_symbol: str,
) -> Optional[Dict[str, Any]]:
    """Fetch a single equity quote via yfinance REST-like endpoint.

    yfinance doesn't have a native async HTTP API – we use their
    internal v8 finance API directly to avoid blocking the event loop.
    """
    url = "https://query1.finance.yahoo.com/v8/finance/chart"
    params = {
        "symbol": yf_symbol,
        "range": "1d",
        "interval": "1d",
        "includePrePost": "false",
    }
    headers = {"User-Agent": _UA}
    try:
        async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=_API_TIMEOUT)) as resp:
            if resp.status != 200:
                logger.debug("yfinance equity HTTP %d for %s", resp.status, yf_symbol)
                return None
            data = await resp.json(content_type=None)
    except Exception as exc:
        logger.debug("yfinance equity fetch failed for %s: %s", yf_symbol, exc)
        return None

    try:
        result = data["chart"]["result"][0]
        meta = result["meta"]
        close = meta.get("regularMarketPrice", 0.0)
        prev = meta.get("chartPreviousClose", close)
        change = close - prev if prev else 0.0
        change_pct = (change / prev * 100) if prev else 0.0
        return {
            "name": meta.get("shortName", symbol),
            "price": close,
            "change": round(change, 4),
            "change_pct": round(change_pct, 2),
            "volume": meta.get("regularMarketVolume", 0),
            "market_cap_bn": round(meta.get("marketCap", 0) / 1e9, 1),
            "pe_ratio": meta.get("trailingPE", 0.0),
            "high_52w": meta.get("fiftyTwoWeekHigh", 0.0),
            "low_52w": meta.get("fiftyTwoWeekLow", 0.0),
            "_source": "yfinance",
            "_timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except (KeyError, IndexError, TypeError) as exc:
        logger.debug("yfinance equity parse error for %s: %s", yf_symbol, exc)
        return None


async def _fetch_coingecko_market(
    session: aiohttp.ClientSession,
) -> Optional[Dict[str, Dict[str, Any]]]:
    """Fetch top crypto market data from CoinGecko free API."""
    ids = ",".join(_CG_CRYPTO_IDS.values())
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": ids,
        "order": "market_cap_desc",
        "per_page": 20,
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "24h",
    }
    headers = {"User-Agent": _UA, "Accept": "application/json"}
    try:
        async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=_API_TIMEOUT)) as resp:
            if resp.status != 200:
                logger.debug("CoinGecko HTTP %d", resp.status)
                return None
            items = await resp.json(content_type=None)
    except Exception as exc:
        logger.debug("CoinGecko fetch failed: %s", exc)
        return None

    # Invert the id -> symbol mapping
    id_to_sym: Dict[str, str] = {v: k for k, v in _CG_CRYPTO_IDS.items()}
    result: Dict[str, Dict[str, Any]] = {}
    for coin in items:
        sym = id_to_sym.get(coin.get("id", ""), coin.get("symbol", "").upper())
        result[sym] = {
            "name": coin.get("name", sym),
            "price_usd": coin.get("current_price", 0.0),
            "change_24h_pct": coin.get("price_change_percentage_24h", 0.0) or 0.0,
            "volume_24h_bn": round((coin.get("total_volume", 0) or 0) / 1e9, 1),
            "market_cap_bn": round((coin.get("market_cap", 0) or 0) / 1e9, 1),
            "dominance_pct": 0.0,  # computed below
            "_source": "coingecko",
            "_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # Compute dominance
    total_mcap = sum(v["market_cap_bn"] for v in result.values())
    if total_mcap > 0:
        for v in result.values():
            v["dominance_pct"] = round(v["market_cap_bn"] / total_mcap * 100, 1)

    return result


async def _fetch_binance_prices(
    session: aiohttp.ClientSession,
) -> Optional[Dict[str, Dict[str, Any]]]:
    """Fetch crypto prices from Binance public API as fallback."""
    url = "https://api.binance.com/api/v3/ticker/price"
    headers = {"User-Agent": _UA}
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=_API_TIMEOUT)) as resp:
            if resp.status != 200:
                return None
            tickers = await resp.json(content_type=None)
    except Exception as exc:
        logger.debug("Binance fetch failed: %s", exc)
        return None

    result: Dict[str, Dict[str, Any]] = {}
    price_map: Dict[str, float] = {}
    for t in tickers:
        symbol = t.get("symbol", "")
        try:
            price_map[symbol] = float(t.get("price", 0))
        except (ValueError, TypeError):
            continue

    for sym, binance_sym in _BINANCE_SYMBOLS.items():
        price = price_map.get(binance_sym, 0.0)
        if price <= 0:
            continue
        result[sym] = {
            "name": sym,
            "price_usd": price,
            "change_24h_pct": 0.0,
            "volume_24h_bn": 0.0,
            "market_cap_bn": 0.0,
            "dominance_pct": 0.0,
            "_source": "binance",
            "_timestamp": datetime.now(timezone.utc).isoformat(),
        }
    return result


async def _fetch_yfinance_forex(
    session: aiohttp.ClientSession,
) -> Dict[str, Dict[str, Any]]:
    """Fetch forex rates via yfinance chart API."""
    results: Dict[str, Dict[str, Any]] = {}
    for pair, yf_sym in _YF_FOREX_PAIRS.items():
        data = await _fetch_yfinance_equity(session, pair, yf_sym)
        if data is not None:
            rate = data["price"]
            change = data["change"]
            change_pct = data["change_pct"]
            results[pair] = {
                "rate": rate,
                "change": round(change, 6),
                "change_pct": round(change_pct, 2),
                "bid": round(rate - 0.0001, 4),
                "ask": round(rate + 0.0001, 4),
                "_source": "yfinance",
                "_timestamp": data.get("_timestamp", datetime.now(timezone.utc).isoformat()),
            }
    return results


# ── Source Provider ──────────────────────────────────────────────────────────


class MarketSource(SourceProvider):
    """Market data feed provider.

    Fetches equity quotes, cryptocurrency prices, and forex rates
    from **live APIs** when ``_LIVE_MODE`` is ``True`` (default).
    Falls back to :data:`SAMPLE_EQUITY_DATA` / :data:`SAMPLE_CRYPTO_DATA`
    / :data:`SAMPLE_FOREX_DATA` only when every live API call fails,
    logging a warning each time so stale data is never silent.

    Usage::

        source = MarketSource()
        result = await source.fetch("AAPL", max_items=5)
        result = await source.scan(max_items=50)
    """

    def __init__(
        self,
        config: Optional[SourceConfig] = None,
        segments: Optional[List[str]] = None,
    ):
        super().__init__(
            name="market",
            category=SourceCategory.MARKET,
            reliability=SourceReliability.RELIABLE,
            config=config,
        )
        self._segments = segments or ["equities", "crypto", "forex"]
        # TTL caches for each segment
        self._equity_cache: TTLCache = TTLCache(maxsize=64, ttl=300)   # 5 min
        self._crypto_cache: TTLCache = TTLCache(maxsize=64, ttl=60)    # 1 min (crypto moves fast)
        self._forex_cache: TTLCache = TTLCache(maxsize=64, ttl=300)    # 5 min
        # In-memory caches populated by live calls
        self._live_equities: Dict[str, Dict[str, Any]] = {}
        self._live_crypto: Dict[str, Dict[str, Any]] = {}
        self._live_forex: Dict[str, Dict[str, Any]] = {}

    # ── Public async API ────────────────────────────────────────────────

    async def fetch(self, query: str, max_items: int = 50, **kwargs: Any) -> SourceResult:
        """Fetch market data matching a query.

        Parameters
        ----------
        query:
            Search query (symbol, name, or segment).
        max_items:
            Maximum items to return.

        Returns
        -------
        SourceResult
            Matched market data items.
        """
        start = time.monotonic()
        self._record_fetch()
        items: List[SourceItem] = []
        errors: List[str] = []
        query_lower = query.lower()

        try:
            await self._refresh_live_data()

            if "equities" in self._segments:
                items.extend(self._fetch_equities(query_lower, max_items))
            if "crypto" in self._segments and len(items) < max_items:
                items.extend(self._fetch_crypto(query_lower, max_items - len(items)))
            if "forex" in self._segments and len(items) < max_items:
                items.extend(self._fetch_forex(query_lower, max_items - len(items)))
        except Exception as exc:
            errors.append(str(exc))
            self._record_error()

        items = items[:max_items]
        elapsed = (time.monotonic() - start) * 1000
        return self._make_result(
            items=items,
            total_available=len(items),
            errors=errors,
            elapsed_ms=elapsed,
        )

    async def scan(self, max_items: int = 100, **kwargs: Any) -> SourceResult:
        """Scan all market data across segments.

        Parameters
        ----------
        max_items:
            Maximum items to return.

        Returns
        -------
        SourceResult
            Latest market data from all segments.
        """
        start = time.monotonic()
        self._record_scan()
        items: List[SourceItem] = []
        errors: List[str] = []

        try:
            await self._refresh_live_data()

            if "equities" in self._segments:
                items.extend(self._fetch_equities("", max_items))
            if "crypto" in self._segments and len(items) < max_items:
                items.extend(self._fetch_crypto("", max_items - len(items)))
            if "forex" in self._segments and len(items) < max_items:
                items.extend(self._fetch_forex("", max_items - len(items)))
        except Exception as exc:
            errors.append(str(exc))
            self._record_error()

        items = items[:max_items]
        elapsed = (time.monotonic() - start) * 1000
        return self._make_result(
            items=items,
            total_available=len(items),
            errors=errors,
            elapsed_ms=elapsed,
        )

    # ── Live data refresh ───────────────────────────────────────────────

    async def _refresh_live_data(self) -> None:
        """Call live APIs and populate ``_live_*`` caches.

        If ``_LIVE_MODE`` is ``False`` or all API calls fail, the caches
        are populated from SAMPLE_DATA and a warning is logged.

        TTLCache is checked first – if a segment's cache is still valid
        the API call for that segment is skipped entirely.
        """
        if not _LIVE_MODE:
            self._live_equities = dict(SAMPLE_EQUITY_DATA)
            self._live_crypto = dict(SAMPLE_CRYPTO_DATA)
            self._live_forex = dict(SAMPLE_FOREX_DATA)
            logger.warning("Using SAMPLE_DATA - live API disabled (_LIVE_MODE=False)")
            return

        # ── Check TTL caches first ────────────────────────────────────
        need_equities = "equities" not in self._equity_cache
        need_crypto = "crypto" not in self._crypto_cache
        need_forex = "forex" not in self._forex_cache

        if not need_equities:
            self._live_equities = self._equity_cache["equities"]
            logger.debug("equity_cache hit – skipping API call")
        if not need_crypto:
            self._live_crypto = self._crypto_cache["crypto"]
            logger.debug("crypto_cache hit – skipping API call")
        if not need_forex:
            self._live_forex = self._forex_cache["forex"]
            logger.debug("forex_cache hit – skipping API call")

        if not need_equities and not need_crypto and not need_forex:
            return  # All segments served from cache

        async with aiohttp.ClientSession() as session:
            # Equities
            if need_equities:
                eq_tasks = []
                for sym in _YF_EQUITY_SYMBOLS:
                    yf_sym = sym.replace("BRK-B", "BRK-B")
                    eq_tasks.append(_fetch_yfinance_equity(session, sym, yf_sym))
                eq_results = await asyncio.gather(*eq_tasks, return_exceptions=True)
                live_eq: Dict[str, Dict[str, Any]] = {}
                canonical_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B"]
                for idx, res in enumerate(eq_results):
                    if isinstance(res, Exception) or res is None:
                        continue
                    sym = canonical_symbols[idx] if idx < len(canonical_symbols) else f"UNK{idx}"
                    live_eq[sym] = res
                if live_eq:
                    self._live_equities = live_eq
                    self._equity_cache["equities"] = live_eq
                else:
                    self._live_equities = dict(SAMPLE_EQUITY_DATA)
                    logger.warning("Using SAMPLE_DATA - live API unavailable for equities (yfinance)")

            # Crypto – try CoinGecko, fall back to Binance
            if need_crypto:
                live_crypto = await _fetch_coingecko_market(session)
                if live_crypto:
                    self._live_crypto = live_crypto
                    self._crypto_cache["crypto"] = live_crypto
                else:
                    live_crypto = await _fetch_binance_prices(session)
                    if live_crypto:
                        self._live_crypto = live_crypto
                        self._crypto_cache["crypto"] = live_crypto
                    else:
                        self._live_crypto = dict(SAMPLE_CRYPTO_DATA)
                        logger.warning("Using SAMPLE_DATA - live API unavailable for crypto (coingecko/binance)")

            # Forex
            if need_forex:
                live_fx = await _fetch_yfinance_forex(session)
                if live_fx:
                    self._live_forex = live_fx
                    self._forex_cache["forex"] = live_fx
                else:
                    self._live_forex = dict(SAMPLE_FOREX_DATA)
                    logger.warning("Using SAMPLE_DATA - live API unavailable for forex (yfinance)")

    # ── Segment-specific fetch ──────────────────────────────────────────

    def _fetch_equities(self, query: str, max_items: int) -> List[SourceItem]:
        """Fetch equity quotes matching query."""
        items: List[SourceItem] = []
        data_source = self._live_equities if self._live_equities else SAMPLE_EQUITY_DATA
        for symbol, data in data_source.items():
            text = f"{symbol} {data.get('name', '')}".lower()
            if not query or query in text:
                quote = EquityQuote(symbol=symbol, **{k: v for k, v in data.items() if k in EquityQuote.model_fields})
                items.append(self._equity_to_item(quote, data.get("_source", "sample_data"), data.get("_timestamp", "")))
                if len(items) >= max_items:
                    break
        return items

    def _fetch_crypto(self, query: str, max_items: int) -> List[SourceItem]:
        """Fetch crypto quotes matching query."""
        items: List[SourceItem] = []
        data_source = self._live_crypto if self._live_crypto else SAMPLE_CRYPTO_DATA
        for symbol, data in data_source.items():
            text = f"{symbol} {data.get('name', '')}".lower()
            if not query or query in text:
                quote = CryptoQuote(symbol=symbol, **{k: v for k, v in data.items() if k in CryptoQuote.model_fields})
                items.append(self._crypto_to_item(quote, data.get("_source", "sample_data"), data.get("_timestamp", "")))
                if len(items) >= max_items:
                    break
        return items

    def _fetch_forex(self, query: str, max_items: int) -> List[SourceItem]:
        """Fetch forex quotes matching query."""
        items: List[SourceItem] = []
        data_source = self._live_forex if self._live_forex else SAMPLE_FOREX_DATA
        for pair, data in data_source.items():
            text = pair.lower()
            if not query or query in text:
                quote = ForexQuote(pair=pair, **{k: v for k, v in data.items() if k in ForexQuote.model_fields})
                items.append(self._forex_to_item(quote, data.get("_source", "sample_data"), data.get("_timestamp", "")))
                if len(items) >= max_items:
                    break
        return items

    # ── Converters ──────────────────────────────────────────────────────

    def _equity_to_item(self, quote: EquityQuote, source: str = "", fetched_at: str = "") -> SourceItem:
        """Convert equity quote to SourceItem."""
        now_iso = fetched_at or datetime.now(timezone.utc).isoformat()
        return self._make_item(
            title=f"{quote.symbol} – {quote.name}: ${quote.price:.2f}",
            summary=f"{quote.name} trading at ${quote.price:.2f} ({quote.change_pct:+.2f}%)",
            content=(
                f"{quote.name} ({quote.symbol})\n"
                f"Price: ${quote.price:.2f} | Change: {quote.change:+.2f} ({quote.change_pct:+.2f}%)\n"
                f"Volume: {quote.volume:,} | Market Cap: ${quote.market_cap_bn:.0f}B\n"
                f"P/E: {quote.pe_ratio:.1f} | 52w Range: ${quote.low_52w:.2f} - ${quote.high_52w:.2f}\n"
                f"_source: {source} | _timestamp: {now_iso}"
            ),
            category=SourceCategory.MARKET,
            reliability=SourceReliability.RELIABLE,
            relevance_score=0.8,
            confidence=0.95,
            tags=["equity", quote.symbol.lower(), f"src:{source}"],
            raw_data={"_source": source, "_timestamp": now_iso},
        )

    def _crypto_to_item(self, quote: CryptoQuote, source: str = "", fetched_at: str = "") -> SourceItem:
        """Convert crypto quote to SourceItem."""
        now_iso = fetched_at or datetime.now(timezone.utc).isoformat()
        return self._make_item(
            title=f"{quote.symbol} – {quote.name}: ${quote.price_usd:,.2f}",
            summary=f"{quote.name} at ${quote.price_usd:,.2f} ({quote.change_24h_pct:+.2f}% 24h)",
            content=(
                f"{quote.name} ({quote.symbol})\n"
                f"Price: ${quote.price_usd:,.2f} | 24h Change: {quote.change_24h_pct:+.2f}%\n"
                f"Volume (24h): ${quote.volume_24h_bn:.1f}B | Market Cap: ${quote.market_cap_bn:.0f}B\n"
                f"Dominance: {quote.dominance_pct:.1f}%\n"
                f"_source: {source} | _timestamp: {now_iso}"
            ),
            category=SourceCategory.MARKET,
            reliability=SourceReliability.USUALLY_RELIABLE,
            relevance_score=0.7,
            confidence=0.90,
            tags=["crypto", quote.symbol.lower(), f"src:{source}"],
            raw_data={"_source": source, "_timestamp": now_iso},
        )

    def _forex_to_item(self, quote: ForexQuote, source: str = "", fetched_at: str = "") -> SourceItem:
        """Convert forex quote to SourceItem."""
        now_iso = fetched_at or datetime.now(timezone.utc).isoformat()
        return self._make_item(
            title=f"{quote.pair}: {quote.rate:.4f}",
            summary=f"{quote.pair} at {quote.rate:.4f} ({quote.change_pct:+.2f}%)",
            content=(
                f"{quote.pair}\n"
                f"Rate: {quote.rate:.4f} | Change: {quote.change:+.4f} ({quote.change_pct:+.2f}%)\n"
                f"Bid: {quote.bid:.4f} | Ask: {quote.ask:.4f} | Spread: {quote.ask - quote.bid:.4f}\n"
                f"_source: {source} | _timestamp: {now_iso}"
            ),
            category=SourceCategory.MARKET,
            reliability=SourceReliability.RELIABLE,
            relevance_score=0.6,
            confidence=0.95,
            tags=["forex", quote.pair.lower().replace("/", ""), f"src:{source}"],
            raw_data={"_source": source, "_timestamp": now_iso},
        )

    # ── Direct access methods ───────────────────────────────────────────

    def get_equity_quote(self, symbol: str) -> Optional[EquityQuote]:
        """Get a quote for a specific equity symbol."""
        data = (self._live_equities or SAMPLE_EQUITY_DATA).get(symbol.upper())
        if data is None:
            return None
        return EquityQuote(symbol=symbol.upper(), **{k: v for k, v in data.items() if k in EquityQuote.model_fields})

    def get_crypto_quote(self, symbol: str) -> Optional[CryptoQuote]:
        """Get a quote for a specific crypto symbol."""
        data = (self._live_crypto or SAMPLE_CRYPTO_DATA).get(symbol.upper())
        if data is None:
            return None
        return CryptoQuote(symbol=symbol.upper(), **{k: v for k, v in data.items() if k in CryptoQuote.model_fields})

    def get_forex_quote(self, pair: str) -> Optional[ForexQuote]:
        """Get a quote for a specific forex pair."""
        data = (self._live_forex or SAMPLE_FOREX_DATA).get(pair.upper())
        if data is None:
            return None
        return ForexQuote(pair=pair.upper(), **{k: v for k, v in data.items() if k in ForexQuote.model_fields})

    @property
    def available_symbols(self) -> Dict[str, List[str]]:
        """Available symbols by segment."""
        return {
            "equities": list((self._live_equities or SAMPLE_EQUITY_DATA).keys()),
            "crypto": list((self._live_crypto or SAMPLE_CRYPTO_DATA).keys()),
            "forex": list((self._live_forex or SAMPLE_FOREX_DATA).keys()),
        }
