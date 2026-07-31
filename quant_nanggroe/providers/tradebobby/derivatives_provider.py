"""Derivatives Provider — Binance fapi + Hyperliquid cross-venue funding.

Ported from TradeBobby Terminal's derivatives.js. Fetches per-symbol:
funding rate, open interest + 24h trend, global/top L/S ratios, taker
ratio via Binance Futures (keyless). Optional Hyperliquid funding gap.
Results cached for 60s (derivative microstructure moves fast).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from quant_nanggroe.core.cache import TTLCache

logger = logging.getLogger(__name__)

_CACHE = TTLCache(default_ttl=60)

_FAPI = "https://fapi.binance.com"
_HL_API = "https://api.hyperliquid.xyz/info"

# Binance perp names — mirrors TradeBobby watchlist.
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT",
    "XRPUSDT", "DOGEUSDT", "ADAUSDT", "AVAXUSDT",
]

# Hyperliquid name -> Binance symbol mapping for cross-venue.
_HL_MAP = {"BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT"}

_TIMEOUT = httpx.Timeout(9.0, connect=5.0)


# ---------------------------------------------------------------------------
# Low-level fetch helpers
# ---------------------------------------------------------------------------

async def _ag(client: httpx.AsyncClient, url: str) -> Optional[Any]:
    """GET JSON from Binance fapi. Returns parsed dict or None."""
    try:
        r = await client.get(url, timeout=_TIMEOUT)
        if r.status_code == 200:
            return r.json()
        logger.debug("Binance %s returned %d", url, r.status_code)
    except Exception as exc:
        logger.debug("Binance fetch failed %s: %s", url, exc)
    return None


async def _fetch_symbol(client: httpx.AsyncClient, sym: str) -> dict[str, Any]:
    """Fetch all derivatives data for one symbol (6 parallel Binance fapi calls)."""
    premium, oi_now, oi_hist, g_ls, t_ls, taker_ls = await asyncio.gather(
        _ag(client, f"{_FAPI}/fapi/v1/premiumIndex?symbol={sym}"),
        _ag(client, f"{_FAPI}/fapi/v1/openInterest?symbol={sym}"),
        _ag(client, f"{_FAPI}/futures/data/openInterestHist?symbol={sym}&period=1h&limit=24"),
        _ag(client, f"{_FAPI}/futures/data/globalLongShortAccountRatio?symbol={sym}&period=5m&limit=1"),
        _ag(client, f"{_FAPI}/futures/data/topLongShortPositionRatio?symbol={sym}&period=5m&limit=1"),
        _ag(client, f"{_FAPI}/futures/data/takerlongshortRatio?symbol={sym}&period=5m&limit=1"),
    )

    funding = float(premium["lastFundingRate"]) if premium and "lastFundingRate" in premium else None
    mark = float(premium["markPrice"]) if premium and "markPrice" in premium else None
    next_funding_time = int(premium["nextFundingTime"]) if premium and "nextFundingTime" in premium else None

    oi = float(oi_now["openInterest"]) if oi_now and "openInterest" in oi_now else None
    oi_value = (oi * mark) if oi is not None and mark is not None else None

    oi_series: list[float] = []
    if isinstance(oi_hist, list):
        oi_series = [float(h.get("sumOpenInterestValue", 0)) for h in oi_hist]
    oi_change_pct: Optional[float] = None
    if len(oi_series) >= 2 and oi_series[0] > 0:
        oi_change_pct = round(((oi_series[-1] - oi_series[0]) / oi_series[0]) * 100, 2)

    global_ls = float(g_ls[0]["longShortRatio"]) if isinstance(g_ls, list) and g_ls else None
    top_ls = float(t_ls[0]["longShortRatio"]) if isinstance(t_ls, list) and t_ls else None
    taker_ratio = float(taker_ls[0]["buySellRatio"]) if isinstance(taker_ls, list) and taker_ls else None

    # Annualized funding: rate * 3 periods/day * 365 days * 100 (pct).
    funding_annual = round(funding * 3 * 365 * 100, 1) if funding is not None else None
    funding_state = "neutral"
    if funding_annual is not None:
        if funding_annual > 30:
            funding_state = "longs_crowded"
        elif funding_annual > 10:
            funding_state = "longs_lean"
        elif funding_annual < -30:
            funding_state = "shorts_crowded"
        elif funding_annual < -10:
            funding_state = "shorts_lean"

    return {
        "symbol": sym,
        "mark": mark,
        "funding": funding,
        "funding_annual_pct": funding_annual,
        "funding_state": funding_state,
        "next_funding_time": next_funding_time,
        "oi": oi,
        "oi_value": oi_value,
        "oi_change_24h_pct": oi_change_pct,
        "oi_series": [round(v / 1e9, 3) for v in oi_series],  # $B for sparkline
        "ls_global": global_ls,
        "ls_top": top_ls,
        "taker_ratio": taker_ratio,
    }


async def _fetch_hl(client: httpx.AsyncClient) -> dict[str, dict[str, Any]]:
    """Hyperliquid cross-venue funding (keyless POST). Graceful skip on failure."""
    try:
        r = await client.post(
            _HL_API,
            json={"type": "metaAndAssetCtxs"},
            timeout=_TIMEOUT,
        )
        if r.status_code != 200:
            return {}
        data = r.json()
    except Exception as exc:
        logger.debug("Hyperliquid fetch failed: %s", exc)
        return {}

    if not isinstance(data, list) or len(data) < 2:
        return {}

    universe = data[0].get("universe", []) if isinstance(data[0], dict) else []
    ctxs = data[1] if isinstance(data[1], list) else []
    out: dict[str, dict[str, Any]] = {}
    for i, asset in enumerate(universe):
        name = asset.get("name", "")
        if name in _HL_MAP and i < len(ctxs) and isinstance(ctxs[i], dict):
            ctx = ctxs[i]
            out[_HL_MAP[name]] = {
                "funding": float(ctx.get("funding", 0)),
                "oi": float(ctx.get("openInterest", 0)),
                "mark": float(ctx.get("markPx", 0)),
            }
    return out


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def get_derivatives(symbol: str) -> dict[str, Any]:
    """Synchronous entry — runs the async fetch loop. Returns derivatives snapshot for one symbol."""
    cache_key = f"derivatives:{symbol}"
    cached = _CACHE.get(cache_key)
    if cached is not None:
        return cached
    result = asyncio.run(_get_derivatives_async(symbol))
    return result


async def _get_derivatives_async(symbol: str) -> dict[str, Any]:
    async with httpx.AsyncClient(verify=False) as client:
        sym_data = await _fetch_symbol(client, symbol)
        if not sym_data:
            return {"symbol": symbol, "error": "fetch_failed"}
        hl = await _fetch_hl(client)
        if symbol in hl:
            sym_data["hl_funding"] = hl[symbol]["funding"]
            if sym_data["funding"] is not None and sym_data["hl_funding"] is not None:
                sym_data["funding_venue_gap_bps"] = round(
                    (sym_data["funding"] - sym_data["hl_funding"]) * 10_000, 2
                )
        _CACHE.set(f"derivatives:{symbol}", sym_data)
        return sym_data


def get_all_derivatives() -> dict[str, Any]:
    """Fetch derivatives for all watched symbols. Returns {symbol: data} dict."""
    cache_key = "derivatives:all"
    cached = _CACHE.get(cache_key)
    if cached is not None:
        return cached
    result = asyncio.run(_get_all_derivatives_async())
    return result


async def _get_all_derivatives_async() -> dict[str, Any]:
    """Fetch all symbols sequentially (avoids Binance rate-limit burst)."""
    results: dict[str, dict[str, Any]] = {}
    async with httpx.AsyncClient(verify=False) as client:
        for sym in SYMBOLS:
            data = await _fetch_symbol(client, sym)
            if data:
                results[sym] = data
            # Small delay between symbols to respect rate limits.
            await asyncio.sleep(0.12)

        # Hyperliquid cross-venue check (one call for all).
        hl = await _fetch_hl(client)

    # Merge HL funding where available.
    for sym, data in results.items():
        if sym in hl:
            data["hl_funding"] = hl[sym]["funding"]
            if data["funding"] is not None and data["hl_funding"] is not None:
                data["funding_venue_gap_bps"] = round(
                    (data["funding"] - data["hl_funding"]) * 10_000, 2
                )

    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbols": results,
    }
    _CACHE.set("derivatives:all", output)
    return output


class DerivativesProvider:
    """Derivatives microstructure provider.

    Fetches crypto futures data from Binance fapi (keyless):
    funding rate, open interest + 24h trend, long/short ratios, taker ratio.
    Optional Hyperliquid cross-venue funding gap.

    Results cached for 60s. Graceful fallback on API failures.
    """

    def __init__(self) -> None:
        self._cache = _CACHE

    def get_derivatives(self, symbol: str) -> dict[str, Any]:
        """Get derivatives snapshot for a single symbol."""
        return get_derivatives(symbol)

    def get_all(self) -> dict[str, Any]:
        """Get derivatives for all watched symbols."""
        return get_all_derivatives()

    def get_funding_regime(self, symbol: str = "BTCUSDT") -> dict[str, Any]:
        """Quick funding regime summary for pipeline consumption."""
        cache_key = f"derivatives:funding_regime:{symbol}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        data = get_derivatives(symbol)
        result: dict[str, Any] = {
            "symbol": symbol,
            "funding_rate": data.get("funding"),
            "funding_annual_pct": data.get("funding_annual_pct"),
            "funding_state": data.get("funding_state"),
            "venue_gap_bps": data.get("funding_venue_gap_bps"),
        }
        self._cache.set(cache_key, result)
        return result
