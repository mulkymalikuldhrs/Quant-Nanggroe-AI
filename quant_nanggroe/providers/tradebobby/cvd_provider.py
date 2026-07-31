from __future__ import annotations

import logging
import math
import urllib.request
import json
from typing import Any, Optional

from quant_nanggroe.core.cache import TTLCache

logger = logging.getLogger(__name__)

_CACHE = TTLCache(default_ttl=120)

WATCHED_SYMBOLS = [
    "XAUUSD", "BTCUSD", "ETHUSD", "EURUSD", "GBPUSD",
    "USDJPY", "USDCAD", "AUDUSD", "GBPJPY", "XAGUSD",
    "SOLUSDT", "WTI", "SPX500", "NAS100", "NVDA",
]

# Binance spot klines + depth for true taker CVD + OBI
_BINANCE_SPOT = "https://api.binance.com"
_KLINE_WINDOW = 30  # 1m bars -> 30 min CVD window
_DEPTH_LIMIT = 500  # order-book levels per side
_OBI_BAND_PCT = 0.5  # sum resting liquidity within +/-0.5% of mid for OBI


def _safe_fetch(url: str) -> Optional[dict | list]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
            return data if resp.status == 200 else None
    except Exception as exc:
        logger.debug("fetch failed %s: %s", url, exc)
        return None


def _fetch_binance_ticker(symbol: str) -> Optional[dict[str, Any]]:
    url = f"https://fapi.binance.com/fapi/v1/ticker/24hr?symbol={symbol}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        logger.debug("Binance ticker failed %s: %s", symbol, exc)
        return None


# ── Kline-based CVD (true taker buy/sell from 1m bars, not 24h snapshot) ──
def _flow_from_klines(symbol: str) -> Optional[dict[str, Any]]:
    """CVD from 1m klines. Kline layout:
    [openTime,o,h,l,c,volume,closeTime,quoteVol,trades,takerBuyBase,takerBuyQuote,ignore]"""
    url = f"{_BINANCE_SPOT}/api/v3/klines?symbol={symbol}&interval=1m&limit={_KLINE_WINDOW + 1}"
    raw = _safe_fetch(url)
    if not isinstance(raw, list) or len(raw) == 0:
        return None
    # Drop last (still-forming) candle
    k = raw[:-1] if len(raw) > _KLINE_WINDOW else raw

    cvd = 0.0
    total_vol = 0.0
    taker_buy_total = 0.0
    cvd_series: list[float] = []
    for bar in k:
        vol = float(bar[5])
        taker_buy = float(bar[9])
        if not math.isfinite(vol) or not math.isfinite(taker_buy):
            continue
        taker_sell = vol - taker_buy
        delta = taker_buy - taker_sell
        cvd += delta
        cvd_series.append(round(cvd, 4))
        total_vol += vol
        taker_buy_total += taker_buy

    if not cvd_series:
        return None

    first_close = float(k[0][4])
    last_close = float(k[-1][4])
    price_change_pct = ((last_close - first_close) / first_close * 100) if first_close else 0.0
    last_delta = (cvd_series[-1] - cvd_series[-2]) if len(cvd_series) >= 2 else cvd_series[0]

    return {
        "price": last_close,
        "cvd": round(cvd, 4),
        "last_delta": round(last_delta, 4),
        "buy_ratio": round(taker_buy_total / total_vol, 4) if total_vol else 0.5,
        "price_change_pct": round(price_change_pct, 3),
    }


# ── Order Book Imbalance (resting bid vs ask within band of mid) ──
def _obi_from_depth(symbol: str) -> Optional[dict[str, Any]]:
    url = f"{_BINANCE_SPOT}/api/v3/depth?symbol={symbol}&limit={_DEPTH_LIMIT}"
    d = _safe_fetch(url)
    if not d or not d.get("bids") or not d.get("asks"):
        return None

    best_bid = float(d["bids"][0][0])
    best_ask = float(d["asks"][0][0])
    mid = (best_bid + best_ask) / 2
    lo = mid * (1 - _OBI_BAND_PCT / 100)
    hi = mid * (1 + _OBI_BAND_PCT / 100)

    bid_vol = 0.0
    ask_vol = 0.0
    for i, row in enumerate(d["bids"]):
        px = float(row[0])
        if i == 0 or px >= lo:
            bid_vol += float(row[1])
    for i, row in enumerate(d["asks"]):
        px = float(row[0])
        if i == 0 or px <= hi:
            ask_vol += float(row[1])

    tot = bid_vol + ask_vol
    obi = ((bid_vol - ask_vol) / tot) if (bid_vol > 0 and ask_vol > 0) else None
    spread_bps = ((best_ask - best_bid) / mid * 10000) if mid else 0.0

    return {
        "obi": round(obi, 4) if obi is not None else None,
        "bid_vol": round(bid_vol, 3),
        "ask_vol": round(ask_vol, 3),
        "spread_bps": round(spread_bps, 2),
    }


# ── Divergence classification (from orderflow-crypto.js classify()) ──
#   BULL_DIV      -> price falling, CVD positive (buying the dip, reversal-up potential)
#   BEAR_DIV      -> price rising, CVD negative (selling into strength, reversal-down risk)
#   DISTRIBUTION  -> price up + CVD down (alias for BEAR_DIV regime)
#   ACCUMULATION  -> price down + CVD up (alias for BULL_DIV regime)
#   BULLISH_FLOW  -> CVD positive + OBI > 0.10 (buyers aggressive + bids stacked)
#   BEARISH_FLOW  -> CVD negative + OBI < -0.10 (sellers aggressive + asks stacked)
#   NEUTRAL       -> no clear signal
def _classify_regime(
    cvd: float,
    price_change_pct: float,
    obi: Optional[float] = None,
) -> tuple[str, Optional[str]]:
    """Returns (regime, divergence). divergence is BULL_DIV/BEAR_DIV/None."""
    if not math.isfinite(cvd):
        return "NEUTRAL", None

    cvd_up = cvd > 0
    price_up = price_change_pct > 0
    obi_val = obi if obi is not None else 0.0

    divergence: Optional[str] = None
    if price_up and cvd < 0:
        divergence = "BEAR_DIV"
    elif not price_up and cvd > 0:
        divergence = "BULL_DIV"

    if divergence == "BEAR_DIV":
        regime = "DISTRIBUTION"
    elif divergence == "BULL_DIV":
        regime = "ACCUMULATION"
    elif cvd_up and obi_val > 0.10:
        regime = "BULLISH_FLOW"
    elif not cvd_up and obi_val < -0.10:
        regime = "BEARISH_FLOW"
    else:
        regime = "NEUTRAL"

    return regime, divergence


# Legacy: simple 24h-snapshot fallback classification (used when klines unavailable)
def _classify_snapshot(cvd: float, price_change: float) -> tuple[str, Optional[str]]:
    if price_change > 0 and cvd < 0:
        return "DISTRIBUTION", "BEAR_DIV"
    if price_change < 0 and cvd > 0:
        return "ACCUMULATION", "BULL_DIV"
    if price_change > 0 and cvd > 0:
        return "BULLISH_FLOW", None
    if price_change < 0 and cvd < 0:
        return "BEARISH_FLOW", None
    return "NEUTRAL", None


def _build_notes(regime: str, obi: Optional[float]) -> str:
    parts: list[str] = []
    if regime == "DISTRIBUTION":
        parts.append("Price up but CVD down -- selling into strength (reversal-down risk)")
    elif regime == "ACCUMULATION":
        parts.append("Price down but CVD up -- buying the dip (reversal-up potential)")
    elif regime == "BULLISH_FLOW":
        parts.append("Aggressive buying + bid-heavy book")
    elif regime == "BEARISH_FLOW":
        parts.append("Aggressive selling + ask-heavy book")
    if obi is not None and abs(obi) > 0.35:
        parts.append(f"Strong book skew (OBI {obi})")
    return " | ".join(parts) or "--"


class CVDProvider:
    def __init__(self) -> None:
        self._cache = _CACHE

    def get_cvd_snapshot(self) -> dict[str, Any]:
        """CVD snapshot with full divergence classification.

        For crypto symbols (BTC, ETH, SOL, etc.): uses 1m klines for true
        taker CVD + live order-book OBI. For non-Binance symbols: falls back
        to 24h ticker snapshot with simplified classification.

        Returns dict with keys: timestamp, symbols[], summary{}.
        Each symbol: {symbol, price, cvd, last_delta, buy_ratio,
                      price_change_pct, obi, spread_bps, regime, divergence, notes}.
        Legacy callers expecting 'classification' or 'cvd_delta' still work
        via 'regime' and 'cvd' aliases in each symbol dict.
        """
        cache_key = "cvd:snapshot"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        results: list[dict[str, Any]] = []
        for sym in WATCHED_SYMBOLS:
            entry = self._snapshot_symbol(sym)
            results.append(entry)

        # Summary bias (crypto-only)
        crypto = [r for r in results if r.get("regime") != "NO_DATA"]
        bullish = sum(1 for r in crypto if r["regime"] in ("BULLISH_FLOW", "ACCUMULATION"))
        bearish = sum(1 for r in crypto if r["regime"] in ("BEARISH_FLOW", "DISTRIBUTION"))
        divergences = [f"{r['symbol']}:{r['divergence']}" for r in crypto if r.get("divergence")]
        net_bias = "NET_BULLISH" if bullish > bearish else "NET_BEARISH" if bearish > bullish else "MIXED"

        output = {
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "symbols": results,
            "summary": {
                "count": len(results),
                "bullish": bullish,
                "bearish": bearish,
                "divergences": divergences,
                "net_bias": net_bias,
            },
        }
        self._cache.set(cache_key, output)
        return output

    def _snapshot_symbol(self, sym: str) -> dict[str, Any]:
        # Crypto symbols on Binance: true kline CVD + OBI
        binance_sym = sym.replace("USD", "USDT") if sym not in ("SOLUSDT",) else sym
        if "BTC" in sym:
            binance_sym = "BTCUSDT"
        elif "ETH" in sym:
            binance_sym = "ETHUSDT"

        flow = _flow_from_klines(binance_sym)
        if flow is not None:
            book = _obi_from_depth(binance_sym)
            obi_val = book["obi"] if book else None
            regime, divergence = _classify_regime(flow["cvd"], flow["price_change_pct"], obi_val)
            notes = _build_notes(regime, obi_val)
            return {
                "symbol": sym,
                "price": round(flow["price"], 2),
                "cvd": round(flow["cvd"], 2),
                "cvd_delta": round(flow["cvd"], 2),  # legacy alias
                "last_delta": round(flow["last_delta"], 2),
                "buy_ratio": flow["buy_ratio"],
                "price_change_pct": flow["price_change_pct"],
                "obi": obi_val,
                "spread_bps": book["spread_bps"] if book else None,
                "regime": regime,
                "divergence": divergence,
                "classification": regime,  # legacy alias
                "notes": notes,
                "source": "klines",
            }

        # Fallback: 24h ticker snapshot (non-Binance symbols)
        ticker = _fetch_binance_ticker(binance_sym)
        if ticker is None:
            return {
                "symbol": sym, "price": 0.0, "cvd": 0.0, "cvd_delta": 0.0,
                "last_delta": 0.0, "buy_ratio": 0.5, "price_change_pct": 0.0,
                "obi": None, "spread_bps": None,
                "regime": "NO_DATA", "divergence": None,
                "classification": "NO_DATA", "notes": "--", "source": "none",
            }

        price = float(ticker.get("lastPrice", 0))
        volume = float(ticker.get("quoteVolume", 0))
        change_pct = float(ticker.get("priceChangePercent", 0))
        taker_buy_vol = float(ticker.get("takerBuyQuoteAssetVolume", 0))
        taker_sell_vol = volume - taker_buy_vol if volume > taker_buy_vol else 0
        cvd = taker_buy_vol - taker_sell_vol

        regime, divergence = _classify_snapshot(cvd, change_pct)
        notes = _build_notes(regime, None)

        return {
            "symbol": sym,
            "price": round(price, 2),
            "cvd": round(cvd, 2),
            "cvd_delta": round(cvd, 2),  # legacy alias
            "last_delta": 0.0,
            "buy_ratio": round(taker_buy_vol / volume, 4) if volume else 0.5,
            "price_change_pct": round(change_pct, 2),
            "obi": None,
            "spread_bps": None,
            "regime": regime,
            "divergence": divergence,
            "classification": regime,  # legacy alias
            "notes": notes,
            "source": "ticker_24h",
        }
