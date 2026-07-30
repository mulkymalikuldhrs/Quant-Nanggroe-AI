"""Currency strength provider — FX pair % change -> individual currency ranking.

Derives individual currency strength by averaging % change across all pairs
involving that currency. Falls back from provided prices -> MT5 -> Yahoo
Finance. Cached 300s. No comments.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import quote
from urllib.request import Request, urlopen

from quant_nanggroe.core.cache import TTLCache

logger = logging.getLogger(__name__)

_CACHE = TTLCache(default_ttl=300)

FX_PAIRS = [
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD",
    "AUDUSD", "NZDUSD", "EURJPY", "GBPJPY", "EURGBP",
]

FX_YAHOO = {
    "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "USDJPY=X",
    "USDCHF": "USDCHF=X", "USDCAD": "USDCAD=X", "AUDUSD": "AUDUSD=X",
    "NZDUSD": "NZDUSD=X", "EURJPY": "EURJPY=X", "GBPJPY": "GBPJPY=X",
    "EURGBP": "EURGBP=X",
}

_CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"]

_CURRENCY_PAIR_MAP: dict[str, list[tuple[str, float]]] = {
    "USD": [("EURUSD", -1.0), ("GBPUSD", -1.0), ("USDJPY", 1.0), ("USDCHF", 1.0),
            ("USDCAD", 1.0), ("AUDUSD", -1.0), ("NZDUSD", -1.0)],
    "EUR": [("EURUSD", 1.0), ("EURJPY", 1.0), ("EURGBP", 1.0)],
    "GBP": [("GBPUSD", 1.0), ("GBPJPY", 1.0), ("EURGBP", -1.0)],
    "JPY": [("USDJPY", -1.0), ("EURJPY", -1.0), ("GBPJPY", -1.0)],
    "CHF": [("USDCHF", -1.0)],
    "CAD": [("USDCAD", -1.0)],
    "AUD": [("AUDUSD", 1.0)],
    "NZD": [("NZDUSD", 1.0)],
}

_TIMEFRAMES = ["1d", "5d", "20d"]
_TF_WEIGHTS = {"1d": 0.5, "5d": 0.3, "20d": 0.2}


def _compute_pair_changes_from_closes(closes: list[float]) -> dict[str, float]:
    if len(closes) < 2:
        return {}
    changes = {}
    chg_1d = ((closes[-1] - closes[-2]) / closes[-2]) * 100.0
    changes["1d"] = round(chg_1d, 4)
    idx_5 = max(0, len(closes) - 6)
    if idx_5 < len(closes) - 1:
        chg_5d = ((closes[-1] - closes[idx_5]) / closes[idx_5]) * 100.0
        changes["5d"] = round(chg_5d, 4)
    if len(closes) >= 2:
        chg_20d = ((closes[-1] - closes[0]) / closes[0]) * 100.0
        changes["20d"] = round(chg_20d, 4)
    return changes


def _fetch_yahoo_chart(yahoo_ticker: str) -> Optional[list[float]]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(yahoo_ticker, safe='')}?range=1mo&interval=1d"
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode())
    except Exception as exc:
        logger.debug("Yahoo chart fetch failed for %s: %s", yahoo_ticker, exc)
        return None
    try:
        result = payload["chart"]["result"][0]
        closes = result["indicators"]["quote"][0]["close"]
        return [c for c in closes if c is not None]
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def _fetch_from_mt5() -> Optional[dict[str, dict[str, float]]]:
    try:
        import MetaTrader5 as mt5
    except ImportError:
        return None
    try:
        already_init = mt5.terminal_info() is not None
    except Exception:
        already_init = False
    if not already_init and not mt5.initialize():
        logger.debug("MT5 initialize failed")
        return None
    try:
        pair_changes: dict[str, dict[str, float]] = {}
        for pair in FX_PAIRS:
            rates = mt5.copy_rates_from_pos(pair, mt5.TIMEFRAME_D1, 0, 22)
            if rates is None or len(rates) < 2:
                continue
            closes = [r[4] for r in rates]
            changes = _compute_pair_changes_from_closes(closes)
            if changes:
                pair_changes[pair] = changes
        return pair_changes if pair_changes else None
    except Exception as exc:
        logger.debug("MT5 rates fetch failed: %s", exc)
        return None
    finally:
        if not already_init:
            mt5.shutdown()


def _fetch_from_yahoo() -> Optional[dict[str, dict[str, float]]]:
    pair_changes: dict[str, dict[str, float]] = {}
    for pair, yahoo_ticker in FX_YAHOO.items():
        closes = _fetch_yahoo_chart(yahoo_ticker)
        if closes is None or len(closes) < 2:
            continue
        changes = _compute_pair_changes_from_closes(closes)
        if changes:
            pair_changes[pair] = changes
    return pair_changes if pair_changes else {}


def _get_pair_changes(
    prices: Optional[dict[str, dict[str, float]]] = None,
) -> dict[str, dict[str, float]]:
    if prices is not None:
        return prices
    mt5_data = _fetch_from_mt5()
    if mt5_data is not None:
        return mt5_data
    return _fetch_from_yahoo()


def _compute_composite_strength(
    pair_changes: dict[str, dict[str, float]],
) -> dict[str, float]:
    strength: dict[str, float] = {}
    for currency in _CURRENCIES:
        weighted_sum = 0.0
        weight_total = 0.0
        for tf in _TIMEFRAMES:
            vals = []
            for pair, sign in _CURRENCY_PAIR_MAP[currency]:
                chg = pair_changes.get(pair, {}).get(tf)
                if chg is not None:
                    vals.append(chg * sign)
            if vals:
                tf_score = sum(vals) / len(vals)
                weighted_sum += tf_score * _TF_WEIGHTS[tf]
                weight_total += _TF_WEIGHTS[tf]
        strength[currency] = round(weighted_sum / weight_total, 4) if weight_total > 0 else 0.0
    return strength


def _find_best_worst_pair(
    strength: dict[str, float],
) -> tuple[Optional[str], Optional[str]]:
    pair_scores: dict[str, float] = {}
    for pair in FX_PAIRS:
        base = pair[:3]
        quote = pair[3:]
        base_str = strength.get(base, 0.0)
        quote_str = strength.get(quote, 0.0)
        pair_scores[pair] = base_str - quote_str
    if not pair_scores:
        return None, None
    best = max(pair_scores, key=pair_scores.get)
    worst = min(pair_scores, key=pair_scores.get)
    return best, worst


class CurrencyStrengthProvider:
    def __init__(self) -> None:
        self._cache = _CACHE

    def get_currency_strength(
        self,
        prices: Optional[dict[str, dict[str, float]]] = None,
    ) -> dict[str, Any]:
        if prices is None:
            cache_key = "currency_strength:result"
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        pair_changes = _get_pair_changes(prices)

        if not pair_changes:
            result = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "strength": {},
                "ranking": [],
                "best_pair": None,
                "worst_pair": None,
                "error": "no price data available from any source",
            }
            if prices is None:
                self._cache.set(cache_key, result)
            return result

        strength = _compute_composite_strength(pair_changes)
        ranking = sorted(strength, key=strength.get, reverse=True)
        best_pair, worst_pair = _find_best_worst_pair(strength)

        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "strength": strength,
            "ranking": ranking,
            "best_pair": best_pair,
            "worst_pair": worst_pair,
        }
        if prices is None:
            self._cache.set(cache_key, result)
        return result
