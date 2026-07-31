"""Macro Pulse Provider — Yahoo Finance macro market data.

Ported from TradeBobby Terminal's macro-pulse.js.
Fetches 52+ tickers covering FX, rates, vols, sectors, Mag-7,
commodities, credit, and world indices. Computes regime classification,
VIX term structure, yield curve inversion, sector rotation scores.
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

_YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1d&interval=5m"
_YAHOO_URL_5D = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=5d&interval=1d"
_FNG_URL = "https://api.alternative.me/fng/?limit=1&format=json"

_TICKERS: list[dict[str, Any]] = [
    # US Treasury yields
    {"y": "^TNX", "k": "us10y", "label": "US 10Y", "group": "rates"},
    {"y": "^FVX", "k": "us5y", "label": "US 5Y", "group": "rates"},
    {"y": "^IRX", "k": "us3m", "label": "US 3M", "group": "rates"},
    {"y": "^TYX", "k": "us30y", "label": "US 30Y", "group": "rates"},
    # Volatility indices
    {"y": "^VIX", "k": "vix", "label": "VIX", "group": "vol"},
    {"y": "^VIX9D", "k": "vix9d", "label": "VIX 9d", "group": "vol"},
    {"y": "^VIX3M", "k": "vix3m", "label": "VIX 3m", "group": "vol"},
    {"y": "^VIX6M", "k": "vix6m", "label": "VIX 6m", "group": "vol"},
    {"y": "^MOVE", "k": "move", "label": "MOVE Index", "group": "vol"},
    {"y": "^VVIX", "k": "vvix", "label": "VVIX", "group": "vol"},
    # FX
    {"y": "DX-Y.NYB", "k": "dxy", "label": "DXY", "group": "fx"},
    # Bond / credit ETFs
    {"y": "IEF", "k": "ief", "label": "IG Bonds (IEF)", "group": "credit"},
    {"y": "LQD", "k": "lqd", "label": "IG Corp (LQD)", "group": "credit"},
    {"y": "JNK", "k": "jnk", "label": "Junk (JNK)", "group": "credit"},
    {"y": "HYG", "k": "hyg", "label": "Junk Bonds (HYG)", "group": "credit"},
    # Commodities futures
    {"y": "GC=F", "k": "gold_f", "label": "Gold Fut", "group": "commodity"},
    {"y": "SI=F", "k": "silver_f", "label": "Silver Fut", "group": "commodity"},
    {"y": "CL=F", "k": "oil_f", "label": "WTI Fut", "group": "commodity"},
    {"y": "BZ=F", "k": "brent_f", "label": "Brent Fut", "group": "commodity"},
    {"y": "HG=F", "k": "copper_f", "label": "Copper Fut", "group": "commodity"},
    # Sector ETFs
    {"y": "XLK", "k": "xlk", "label": "Tech (XLK)", "group": "sector"},
    {"y": "XLF", "k": "xlf", "label": "Finance (XLF)", "group": "sector"},
    {"y": "XLE", "k": "xle", "label": "Energy (XLE)", "group": "sector"},
    {"y": "XLV", "k": "xlv", "label": "Health (XLV)", "group": "sector"},
    {"y": "XLI", "k": "xli", "label": "Industrial (XLI)", "group": "sector"},
    {"y": "XLY", "k": "xly", "label": "Cons Disc (XLY)", "group": "sector"},
    {"y": "XLP", "k": "xlp", "label": "Cons Stap (XLP)", "group": "sector"},
    {"y": "XLU", "k": "xlu", "label": "Utilities (XLU)", "group": "sector"},
    {"y": "XLB", "k": "xlb", "label": "Materials (XLB)", "group": "sector"},
    {"y": "XLRE", "k": "xlre", "label": "Real Est (XLRE)", "group": "sector"},
    {"y": "XLC", "k": "xlc", "label": "Comm (XLC)", "group": "sector"},
    # Mag-7
    {"y": "AAPL", "k": "aapl", "label": "Apple", "group": "mag7"},
    {"y": "MSFT", "k": "msft", "label": "Microsoft", "group": "mag7"},
    {"y": "GOOGL", "k": "googl", "label": "Alphabet", "group": "mag7"},
    {"y": "AMZN", "k": "amzn", "label": "Amazon", "group": "mag7"},
    {"y": "NVDA", "k": "nvda", "label": "Nvidia", "group": "mag7"},
    {"y": "META", "k": "meta", "label": "Meta", "group": "mag7"},
    {"y": "TSLA", "k": "tsla", "label": "Tesla", "group": "mag7"},
    # World indices
    {"y": "^GSPC", "k": "spx", "label": "S&P 500", "group": "index"},
    {"y": "^NDX", "k": "ndx", "label": "NASDAQ 100", "group": "index"},
    {"y": "^DJI", "k": "dji", "label": "Dow Jones", "group": "index"},
    {"y": "^FTSE", "k": "ftse", "label": "FTSE 100", "group": "index"},
    {"y": "^GDAXI", "k": "dax", "label": "DAX", "group": "index"},
    {"y": "^FCHI", "k": "cac", "label": "CAC 40", "group": "index"},
    {"y": "^N225", "k": "nky", "label": "Nikkei 225", "group": "index"},
    {"y": "^HSI", "k": "hsi", "label": "Hang Seng", "group": "index"},
]

_RISK_ON_SECTORS = {"xlk", "xly", "xlc", "xlf", "xli"}
_RISK_OFF_SECTORS = {"xlu", "xlp", "xlv"}


def _fetch_yahoo(ticker: str) -> Optional[dict[str, Any]]:
    url = _YAHOO_URL.format(ticker=quote(ticker, safe=""))
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode())
    except Exception as exc:
        logger.debug("Yahoo fetch failed for %s: %s", ticker, exc)
        return None
    meta = None
    try:
        meta = payload["chart"]["result"][0]["meta"]
    except (KeyError, IndexError, TypeError):
        return None
    close = meta.get("regularMarketPrice")
    prev_close = meta.get("chartPreviousClose") or meta.get("previousClose")
    if close is None or prev_close is None:
        return None
    change = close - prev_close
    change_pct = (change / prev_close) * 100.0 if prev_close else 0.0
    return {
        "price": close,
        "prev_close": prev_close,
        "change": round(change, 4),
        "change_pct": round(change_pct, 4),
        "high": meta.get("regularMarketDayHigh"),
        "low": meta.get("regularMarketDayLow"),
        "time": meta.get("regularMarketTime"),
    }


def _fetch_all_tickers() -> dict[str, dict[str, Any]]:
    cache_key = "macro_pulse:raw_data"
    cached = _CACHE.get(cache_key)
    if cached is not None:
        return cached
    data: dict[str, dict[str, Any]] = {}
    for t in _TICKERS:
        d = _fetch_yahoo(t["y"])
        if d is not None:
            d["label"] = t["label"]
            d["group"] = t["group"]
            data[t["k"]] = d
    _CACHE.set(cache_key, data)
    return data


def _fetch_yahoo5d(ticker: str) -> Optional[list[float]]:
    """Fetch 5-day daily closes for cumulative return calculation."""
    url = _YAHOO_URL_5D.format(ticker=quote(ticker, safe=""))
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode())
        result = payload["chart"]["result"][0]
        closes = result["indicators"]["quote"][0].get("close", [])
        return [c for c in closes if c is not None]
    except Exception:
        return None


def _fetch_fear_greed() -> Optional[dict[str, Any]]:
    """Fetch Fear & Greed Index from alternative.me (crypto F&G as macro proxy)."""
    cache_key = "macro_pulse:fng"
    cached = _CACHE.get(cache_key)
    if cached is not None:
        return cached
    try:
        req = Request(_FNG_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode())
        entry = payload["data"][0]
        result = {
            "value": int(entry["value"]),
            "label": entry["value_classification"],
        }
        _CACHE.set(cache_key, result)
        return result
    except Exception as exc:
        logger.debug("Fear & Greed fetch failed: %s", exc)
        return None


class MacroPulseProvider:
    """Yahoo Finance macro market data provider.

    Fetches 52+ tickers across rates, vols, FX, sectors, Mag-7,
    commodities, credit, and world indices. Computes derived metrics
    and regime classifications. Results cached for 300s.
    """

    def __init__(self) -> None:
        self._cache = _CACHE

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def fetch_all(self) -> dict[str, Any]:
        cache_key = "macro_pulse:all"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        data = _fetch_all_tickers()
        result: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        result["derived"] = self._compute_derived(data)
        self._cache.set(cache_key, result)
        return result

    def get_vix_term(self) -> dict[str, Any]:
        cache_key = "macro_pulse:vix_term"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        data = _fetch_all_tickers()
        vix = data.get("vix", {}).get("price")
        vix9d = data.get("vix9d", {}).get("price")
        vix3m = data.get("vix3m", {}).get("price")
        vix6m = data.get("vix6m", {}).get("price")
        vvix = data.get("vvix", {}).get("price")
        result: dict[str, Any] = {}
        if vix is not None:
            result["vix"] = vix
            result["vix_change_pct"] = data["vix"]["change_pct"]
        if vix9d is not None:
            result["vix9d"] = vix9d
        if vix3m is not None:
            result["vix3m"] = vix3m
        if vix6m is not None:
            result["vix6m"] = vix6m
        if vix is not None and vix3m is not None:
            ts = vix - vix3m
            result["term_structure"] = round(ts, 2)
            result["term_state"] = "BACKWARDATION" if ts > 0 else "CONTANGO"
        if vix9d is not None and vix is not None and vix != 0:
            result["vix_short_ratio"] = round(vix9d / vix, 2)
        if vvix is not None:
            result["vvix"] = vvix
            if vix is not None and vix != 0:
                result["vvix_vix_ratio"] = round(vvix / vix, 2)
        self._cache.set(cache_key, result)
        return result

    def get_yield_curve(self) -> dict[str, Any]:
        cache_key = "macro_pulse:yield_curve"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        data = _fetch_all_tickers()
        us3m = data.get("us3m", {}).get("price")
        us5y = data.get("us5y", {}).get("price")
        us10y = data.get("us10y", {}).get("price")
        us30y = data.get("us30y", {}).get("price")
        result: dict[str, Any] = {}
        if us3m is not None:
            result["us3m"] = us3m
        if us5y is not None:
            result["us5y"] = us5y
        if us10y is not None:
            result["us10y"] = us10y
        if us30y is not None:
            result["us30y"] = us30y
        if us10y is not None and us3m is not None:
            spread = round(us10y - us3m, 2)
            result["spread_10y_3m"] = spread
            result["inversion_flag"] = spread < 0
            result["curve_state"] = "INVERTED" if spread < 0 else ("FLAT" if spread < 0.5 else "NORMAL")
        if us10y is not None and us5y is not None:
            result["spread_10y_5y"] = round(us10y - us5y, 2)
        if us30y is not None and us10y is not None:
            result["spread_30y_10y"] = round(us30y - us10y, 2)
        self._cache.set(cache_key, result)
        return result

    def get_sector_rotation(self) -> dict[str, Any]:
        cache_key = "macro_pulse:sector_rotation"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        data = _fetch_all_tickers()
        sectors = [
            {"key": t["k"], "label": t["label"], "chg": data.get(t["k"], {}).get("change_pct")}
            for t in _TICKERS if t["group"] == "sector"
        ]
        sectors = [s for s in sectors if s["chg"] is not None]
        sectors.sort(key=lambda s: s["chg"], reverse=True)
        risk_on = sum(s["chg"] for s in sectors if s["key"] in _RISK_ON_SECTORS)
        risk_off = sum(s["chg"] for s in sectors if s["key"] in _RISK_OFF_SECTORS)
        result = {
            "leaders": sectors[:3],
            "laggards": list(reversed(sectors[-3:])),
            "risk_on_score": round(risk_on, 2),
            "risk_off_score": round(risk_off, 2),
            "rotation_bias": "risk_on" if risk_on > risk_off else "risk_off",
        }
        self._cache.set(cache_key, result)
        return result

    def get_macro_regime(self) -> dict[str, Any]:
        cache_key = "macro_pulse:regime"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        data = _fetch_all_tickers()
        result = self._compute_derived(data)
        self._cache.set(cache_key, result)
        return result

    def get_mag7(self) -> dict[str, Any]:
        cache_key = "macro_pulse:mag7"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        data = _fetch_all_tickers()
        mag7 = {t["k"]: data[t["k"]] for t in _TICKERS if t["group"] == "mag7" and t["k"] in data}
        prices = {k: v["price"] for k, v in mag7.items()}
        changes = {k: v["change_pct"] for k, v in mag7.items()}
        avg_chg = round(sum(changes.values()) / len(changes), 2) if changes else 0.0
        result = {
            "prices": prices,
            "change_pcts": changes,
            "average_change_pct": avg_chg,
            "count": len(mag7),
        }
        self._cache.set(cache_key, result)
        return result

    def get_commodities(self) -> dict[str, Any]:
        cache_key = "macro_pulse:commodities"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        data = _fetch_all_tickers()
        gold = data.get("gold_f", {}).get("price")
        silver = data.get("silver_f", {}).get("price")
        oil = data.get("oil_f", {}).get("price")
        brent = data.get("brent_f", {}).get("price")
        copper = data.get("copper_f", {}).get("price")
        result: dict[str, Any] = {}
        if gold is not None:
            result["gold"] = gold
            result["gold_change_pct"] = data["gold_f"]["change_pct"]
        if silver is not None:
            result["silver"] = silver
            result["silver_change_pct"] = data["silver_f"]["change_pct"]
        if oil is not None:
            result["wti"] = oil
            result["wti_change_pct"] = data["oil_f"]["change_pct"]
        if brent is not None:
            result["brent"] = brent
            result["brent_change_pct"] = data["brent_f"]["change_pct"]
        if copper is not None:
            result["copper"] = copper
            result["copper_change_pct"] = data["copper_f"]["change_pct"]
        if gold is not None and silver is not None and silver != 0:
            result["gold_silver_ratio"] = round(gold / silver, 2)
        if brent is not None and oil is not None:
            result["brent_wti_spread"] = round(brent - oil, 2)
        self._cache.set(cache_key, result)
        return result

    def get_sector_rotation5d(self) -> dict[str, Any]:
        """5-day cumulative sector rotation for robust risk-on vs risk-off signal."""
        cache_key = "macro_pulse:sector_rotation_5d"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        sectors_5d: list[dict[str, Any]] = []
        for t in _TICKERS:
            if t["group"] != "sector":
                continue
            closes = _fetch_yahoo5d(t["y"])
            if closes and len(closes) >= 2:
                ret = (closes[-1] - closes[0]) / closes[0] * 100.0 if closes[0] != 0 else 0.0
                sectors_5d.append({"key": t["k"], "label": t["label"], "ret_5d": round(ret, 2)})
        sectors_5d.sort(key=lambda s: s["ret_5d"], reverse=True)
        risk_on = sum(s["ret_5d"] for s in sectors_5d if s["key"] in _RISK_ON_SECTORS)
        risk_off = sum(s["ret_5d"] for s in sectors_5d if s["key"] in _RISK_OFF_SECTORS)
        result: dict[str, Any] = {
            "leaders": sectors_5d[:3],
            "laggards": list(reversed(sectors_5d[-3:])) if len(sectors_5d) >= 3 else [],
            "risk_on_5d": round(risk_on, 2),
            "risk_off_5d": round(risk_off, 2),
            "bias_5d": "risk_on" if risk_on > risk_off else "risk_off",
        }
        self._cache.set(cache_key, result)
        return result

    def get_composite_risk_index(self) -> dict[str, Any]:
        """9-factor Composite Risk Index. 0 = risk-on, 100 = risk-off.

        Factors (equal weight unless noted):
          1. VIX level (high = risk)
          2. Yield curve (inverted = risk)
          3. Sector rotation (risk-off bias = risk)
          4. Fear & Greed (low/extreme fear = opportunity)
          5. DXY (strong USD = risk-off for EM)
          6. Gold (safe-haven bid = risk)
          7. Credit spread (HYG/IEF ratio stress)
          8. MOVE index (bond vol)
          9. Oil (high = stagflation risk)
        """
        cache_key = "macro_pulse:composite_risk_index"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        data = _fetch_all_tickers()
        factors: dict[str, dict[str, Any]] = {}
        total_weight = 0.0
        weighted_sum = 0.0

        def _add(name: str, weight: float, value: Any, score: float, **extra: Any) -> None:
            nonlocal total_weight, weighted_sum
            s = max(0.0, min(score, 100.0))
            factors[name] = {"value": value, "score": round(s, 1), "weight": weight, **extra}
            weighted_sum += s * weight
            total_weight += weight

        # 1. VIX level (10-50 mapped to 0-100)
        vix = data.get("vix", {}).get("price")
        if vix is not None:
            _add("vix", 0.15, vix, (vix - 10) / 40 * 100, change_pct=data["vix"]["change_pct"])

        # 2. Yield curve (spread -1..+2 mapped to risk 100..0)
        us10y = data.get("us10y", {}).get("price")
        us3m = data.get("us3m", {}).get("price")
        if us10y is not None and us3m is not None:
            spread = round(us10y - us3m, 2)
            _add("yield_curve", 0.10, spread, (1 - spread) / 3 * 100)

        # 3. Sector rotation (use existing daily rotation score)
        rot = self.get_sector_rotation()
        ro = rot.get("risk_on_score", 0.0)
        rf = rot.get("risk_off_score", 0.0)
        rot_diff = rf - ro
        _add("sector_rotation", 0.12, {"risk_on": ro, "risk_off": rf}, 50 + rot_diff * 10)

        # 4. Fear & Greed (0=extreme fear, 100=extreme greed; high greed = risk)
        fng = _fetch_fear_greed()
        if fng is not None:
            _add("fear_greed", 0.10, fng["value"], fng["value"], label=fng["label"])

        # 5. DXY (90-115 mapped to 0-100)
        dxy_price = data.get("dxy", {}).get("price")
        if dxy_price is not None:
            _add("dxy", 0.10, dxy_price, (dxy_price - 90) / 25 * 100)

        # 6. Gold (surge = safe-haven bid = risk-off)
        gold_chg = data.get("gold_f", {}).get("change_pct")
        if gold_chg is not None:
            _add("gold", 0.10, data.get("gold_f", {}).get("price"), 50 + gold_chg * 10, change_pct=gold_chg)

        # 7. Credit spread (HYG/IEF ratio; low ratio = stress)
        hyg_price = data.get("hyg", {}).get("price")
        ief_price = data.get("ief", {}).get("price")
        if hyg_price is not None and ief_price is not None and ief_price != 0:
            ratio = round(hyg_price / ief_price, 3)
            _add("credit_spread", 0.10, ratio, (1 - ratio) / 0.3 * 100)

        # 8. MOVE index (50-200 mapped to 0-100)
        move_price = data.get("move", {}).get("price")
        if move_price is not None:
            _add("move", 0.11, move_price, (move_price - 50) / 150 * 100)

        # 9. Oil (40-120 mapped to 0-100; high oil = stagflation risk)
        oil_price = data.get("oil_f", {}).get("price")
        if oil_price is not None:
            _add("oil", 0.12, oil_price, (oil_price - 40) / 80 * 100)

        score = round(weighted_sum / total_weight, 1) if total_weight > 0 else 50.0

        if score < 30:
            regime = "RISK-ON"
        elif score < 60:
            regime = "MIXED"
        else:
            regime = "RISK-OFF"

        result: dict[str, Any] = {
            "score": score,
            "regime": regime,
            "factors": factors,
            "weight_coverage": round(total_weight, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._cache.set(cache_key, result)
        return result

    def get_macro_pulse(self) -> dict[str, Any]:
        """Unified macro pulse: VIX term + yield curve + sector rotation + CRI + commodities + mag7."""
        cache_key = "macro_pulse:pulse"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        result: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "vix_term": self.get_vix_term(),
            "yield_curve": self.get_yield_curve(),
            "sector_rotation": self.get_sector_rotation(),
            "sector_rotation_5d": self.get_sector_rotation5d(),
            "composite_risk_index": self.get_composite_risk_index(),
            "commodities": self.get_commodities(),
            "mag7": self.get_mag7(),
        }
        self._cache.set(cache_key, result)
        return result

    # ------------------------------------------------------------------
    # Derived computation
    # ------------------------------------------------------------------

    def _compute_derived(self, data: dict[str, dict[str, Any]]) -> dict[str, Any]:
        derived: dict[str, Any] = {}
        d = data

        # VIX regime
        vix = d.get("vix", {}).get("price")
        if vix is not None:
            if vix < 15:
                vol_regime = "COMPLACENT"
            elif vix < 20:
                vol_regime = "NORMAL"
            elif vix < 25:
                vol_regime = "ELEVATED"
            elif vix < 35:
                vol_regime = "HIGH"
            else:
                vol_regime = "EXTREME"
            derived["vol_regime"] = vol_regime
            derived["vix"] = vix

        # Yield curve
        us10y = d.get("us10y", {}).get("price")
        us3m = d.get("us3m", {}).get("price")
        if us10y is not None and us3m is not None:
            spread = round(us10y - us3m, 2)
            derived["spread_10y_3m"] = spread
            derived["yield_curve_state"] = "INVERTED" if spread < 0 else ("FLAT" if spread < 0.5 else "NORMAL")

        # VIX term structure
        vix3m_price = d.get("vix3m", {}).get("price")
        if vix is not None and vix3m_price is not None:
            ts = round(vix - vix3m_price, 2)
            derived["vix_term_structure"] = ts
            derived["vix_term_state"] = "BACKWARDATION" if ts > 0 else "CONTANGO"

        # Credit risk
        hyg = d.get("hyg", {}).get("price")
        ief = d.get("ief", {}).get("price")
        lqd = d.get("lqd", {}).get("price")
        jnk = d.get("jnk", {}).get("price")
        if hyg is not None and ief is not None and ief != 0:
            derived["credit_ratio_hyg_ief"] = round(hyg / ief, 3)
        if hyg is not None and lqd is not None and lqd != 0:
            derived["junk_ig_ratio"] = round(hyg / lqd, 3)
        if jnk is not None and lqd is not None and lqd != 0:
            derived["jnk_lqd_ratio"] = round(jnk / lqd, 3)

        # Gold / silver ratio
        gold = d.get("gold_f", {}).get("price")
        silver = d.get("silver_f", {}).get("price")
        if gold is not None and silver is not None and silver != 0:
            derived["gold_silver_ratio"] = round(gold / silver, 2)

        # Composite risk score (0=risk-on, 100=risk-off)
        score = 50.0
        if vix is not None:
            vix_score = min(vix / 40.0 * 100.0, 100.0)
            score = score * 0.5 + vix_score * 0.5
        if derived.get("yield_curve_state") == "INVERTED":
            score = score * 0.7 + 100.0 * 0.3
        elif derived.get("yield_curve_state") == "NORMAL":
            score = score * 0.7 + 0.0 * 0.3
        dxy_price = d.get("dxy", {}).get("price")
        if dxy_price is not None:
            dxy_score = min((dxy_price - 90) / 20.0 * 100.0, 100.0) if dxy_price > 90 else 0.0
            score = score * 0.8 + max(0, dxy_score) * 0.2
        derived["composite_risk_score"] = round(score, 1)
        if score < 30:
            derived["composite_classification"] = "RISK_ON"
        elif score < 50:
            derived["composite_classification"] = "CAUTIOUS"
        elif score < 70:
            derived["composite_classification"] = "RISK_OFF"
        else:
            derived["composite_classification"] = "CRISIS"

        # Sector rotation score
        sectors = [
            d.get(t["k"], {}).get("change_pct")
            for t in _TICKERS if t["group"] == "sector"
        ]
        sectors = [s for s in sectors if s is not None]
        if sectors:
            derived["sector_avg_change"] = round(sum(sectors) / len(sectors), 2)

        return derived
