from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import quote
from urllib.request import Request, urlopen

from quant_nanggroe.core.cache import TTLCache

logger = logging.getLogger(__name__)

_CACHE = TTLCache(default_ttl=1800)

_YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=5d&interval=1d"

_ETFS: list[dict[str, Any]] = [
    {"ticker": "IBIT", "group": "crypto", "label": "BlackRock BTC"},
    {"ticker": "FBTC", "group": "crypto", "label": "Fidelity BTC"},
    {"ticker": "ARKB", "group": "crypto", "label": "ARK BTC"},
    {"ticker": "BITB", "group": "crypto", "label": "Bitwise BTC"},
    {"ticker": "ETHA", "group": "crypto", "label": "BlackRock ETH"},
    {"ticker": "FETH", "group": "crypto", "label": "Fidelity ETH"},
    {"ticker": "GLD", "group": "gold", "label": "SPDR Gold"},
    {"ticker": "IAU", "group": "gold", "label": "iShares Gold"},
    {"ticker": "SLV", "group": "gold", "label": "iShares Silver"},
    {"ticker": "HYG", "group": "credit", "label": "Junk Bonds"},
    {"ticker": "JNK", "group": "credit", "label": "Junk Bonds (alt)"},
    {"ticker": "TLT", "group": "credit", "label": "Long Treasuries"},
    {"ticker": "ARKK", "group": "innovation", "label": "Innovation"},
    {"ticker": "IWM", "group": "smallcap", "label": "Small Caps (R2K)"},
    {"ticker": "SMH", "group": "semis", "label": "Semis"},
]


def _fetch_etf(ticker: str) -> Optional[dict[str, Any]]:
    url = _YAHOO_URL.format(ticker=quote(ticker, safe=""))
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode())
    except Exception as exc:
        logger.debug("Yahoo fetch failed for %s: %s", ticker, exc)
        return None
    try:
        result = payload["chart"]["result"][0]
        meta = result["meta"]
        quotes = result["indicators"]["quote"][0]
    except (KeyError, IndexError, TypeError):
        return None
    closes = [c for c in (quotes.get("close") or []) if c is not None]
    volumes = [v for v in (quotes.get("volume") or []) if v is not None]
    if not closes or not volumes:
        return None
    last = meta.get("regularMarketPrice")
    prev_close = meta.get("chartPreviousClose")
    if last is None or prev_close is None:
        return None
    volume_today = volumes[-1]
    volume_avg_5d = round(sum(volumes) / len(volumes)) if volumes else 0
    change_pct = round(((last - prev_close) / prev_close) * 100.0, 2) if prev_close else 0.0
    return {
        "price": last,
        "prev_close": prev_close,
        "change_pct": change_pct,
        "volume_today": volume_today,
        "volume_avg_5d": volume_avg_5d,
        "high_5d": max(closes) if closes else None,
        "low_5d": min(closes) if closes else None,
    }


def _flow_label(ratio: float) -> str:
    if ratio > 2.0:
        return "SURGE"
    if ratio > 1.5:
        return "HIGH"
    if ratio >= 0.5:
        return "NORMAL"
    return "LIGHT"


def _fetch_all_etfs() -> dict[str, dict[str, Any]]:
    cache_key = "etf_flows:raw"
    cached = _CACHE.get(cache_key)
    if cached is not None:
        return cached
    data: dict[str, dict[str, Any]] = {}
    for e in _ETFS:
        d = _fetch_etf(e["ticker"])
        if d is not None:
            d["label"] = e["label"]
            d["group"] = e["group"]
            d["ticker"] = e["ticker"]
            vol_avg = d["volume_avg_5d"]
            d["flow_ratio"] = round(d["volume_today"] / vol_avg, 2) if vol_avg > 0 else 1.0
            d["flow_label"] = _flow_label(d["flow_ratio"])
            data[e["ticker"]] = d
    _CACHE.set(cache_key, data)
    return data


def _build_groups(data: dict[str, dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, dict[str, Any]] = {}
    for e in _ETFS:
        ticker = e["ticker"]
        d = data.get(ticker)
        if d is None:
            continue
        grp = e["group"]
        if grp not in groups:
            groups[grp] = {"tickers": [], "total_flow_ratio": 0.0, "avg_change_pct": 0.0, "surges": 0, "count": 0}
        groups[grp]["tickers"].append(ticker)
        groups[grp]["total_flow_ratio"] += d["flow_ratio"]
        groups[grp]["avg_change_pct"] += d["change_pct"]
        groups[grp]["count"] += 1
        if d["flow_label"] == "SURGE":
            groups[grp]["surges"] += 1
    for grp in groups:
        n = groups[grp]["count"]
        if n > 0:
            groups[grp]["avg_flow_ratio"] = round(groups[grp]["total_flow_ratio"] / n, 2)
            groups[grp]["avg_change_pct"] = round(groups[grp]["avg_change_pct"] / n, 2)
        del groups[grp]["total_flow_ratio"]
        del groups[grp]["count"]
    return groups


def _build_signals(
    data: dict[str, dict[str, Any]], groups: dict[str, Any]
) -> dict[str, Any]:
    signals: dict[str, Any] = {}

    crypto = groups.get("crypto", {})
    gold = groups.get("gold", {})
    credit = groups.get("credit", {})
    innovation = groups.get("innovation", {})
    smallcap = groups.get("smallcap", {})
    semis = groups.get("semis", {})

    signals["crypto_flow_score"] = round(crypto.get("avg_flow_ratio", 1.0) * 25.0 - 25.0, 1)
    signals["gold_flow_score"] = round(gold.get("avg_flow_ratio", 1.0) * 20.0 - 20.0, 1)
    signals["credit_flow_score"] = round(credit.get("avg_flow_ratio", 1.0) * 20.0 - 20.0, 1)
    signals["innovation_flow_score"] = round(innovation.get("avg_flow_ratio", 1.0) * 15.0 - 15.0, 1)
    signals["smallcap_flow_score"] = round(smallcap.get("avg_flow_ratio", 1.0) * 10.0 - 10.0, 1)
    signals["semis_flow_score"] = round(semis.get("avg_flow_ratio", 1.0) * 10.0 - 10.0, 1)

    raw = (
        signals["crypto_flow_score"]
        + signals["gold_flow_score"]
        + signals["credit_flow_score"]
        + signals["innovation_flow_score"]
        + signals["smallcap_flow_score"]
        + signals["semis_flow_score"]
    )
    signals["composite_institutional_flow"] = round(max(-100.0, min(100.0, raw)), 1)

    if signals["composite_institutional_flow"] > 30:
        signals["flow_regime"] = "INSTITUTIONAL_ACCUMULATION"
    elif signals["composite_institutional_flow"] > 10:
        signals["flow_regime"] = "CAUTIOUS_ACCUMULATION"
    elif signals["composite_institutional_flow"] < -30:
        signals["flow_regime"] = "INSTITUTIONAL_DISTRIBUTION"
    elif signals["composite_institutional_flow"] < -10:
        signals["flow_regime"] = "CAUTIOUS_DISTRIBUTION"
    else:
        signals["flow_regime"] = "NEUTRAL"

    return signals


class ETFFlowProvider:
    def __init__(self) -> None:
        self._cache = _CACHE

    def get_etf_flows(self) -> dict[str, Any]:
        cache_key = "etf_flows:all"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        data = _fetch_all_etfs()
        result: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "etfs": data,
        }
        result["groups"] = _build_groups(data)
        result["signals"] = _build_signals(data, result["groups"])
        self._cache.set(cache_key, result)
        return result

    def get_etf_pulse(self) -> dict[str, Any]:
        return self.get_etf_flows()

    def get_grouped_flows(self) -> dict[str, Any]:
        cache_key = "etf_flows:groups"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        data = _fetch_all_etfs()
        groups = _build_groups(data)
        self._cache.set(cache_key, groups)
        return groups

    def get_institutional_flow(self) -> dict[str, Any]:
        cache_key = "etf_flows:signal"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        data = _fetch_all_etfs()
        groups = _build_groups(data)
        signals = _build_signals(data, groups)
        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **signals,
        }
        self._cache.set(cache_key, result)
        return result
