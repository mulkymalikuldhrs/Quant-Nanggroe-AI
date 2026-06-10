"""Market detection helpers for symbol-to-engine routing.

Provides regex-based symbol classification shared by the engine factory,
CompositeEngine, and any caller that needs to route symbols to the correct
market engine.

Ported from Vibe-Trading's ``_market_hooks`` module.
"""

from __future__ import annotations

import re
from typing import List

# ── Symbol -> market classification patterns ──

_MARKET_PATTERNS = [
    (re.compile(r"^\d{6}\.(SZ|SH|BJ)$", re.I), "a_share"),
    (re.compile(r"^(51|15|56)\d{4}\.(SZ|SH)$", re.I), "a_share"),
    (re.compile(r"^[A-Z]+\.US$", re.I), "us_equity"),
    (re.compile(r"^\d{3,5}\.HK$", re.I), "hk_equity"),
    (re.compile(r"^[A-Z]+-USDT$", re.I), "crypto"),
    (re.compile(r"^[A-Z]+/USDT$", re.I), "crypto"),
    # China futures: product+delivery.exchange
    (re.compile(r"^[A-Za-z]{1,2}\d{3,4}\.(ZCE|DCE|SHFE|INE|CFFEX|GFEX)$", re.I), "futures"),
    # Global futures: product+month-code (e.g. ESZ4, CLF25)
    (re.compile(r"^[A-Z]{2,4}[FGHJKMNQUVXZ]\d{1,2}$", re.I), "futures"),
    # Global futures: product+YYMM (e.g. CL2412)
    (re.compile(r"^[A-Z]{2,4}\d{4}$", re.I), "futures"),
    # Global futures: bare product code with exchange
    (re.compile(r"^[A-Z]{2,4}\.(CME|CBOT|NYMEX|COMEX|ICE|EUREX)$", re.I), "futures"),
    # Forex pairs: XXX/YYY or XXXXXX.FX
    (re.compile(r"^[A-Z]{3}/[A-Z]{3}$"), "forex"),
    (re.compile(r"^[A-Z]{6}\.FX$"), "forex"),
]

_CHINA_EXCHANGES = {"CFFEX", "SHFE", "DCE", "ZCE", "INE", "GFEX"}

_CN_FUTURES_PRODUCTS = {
    "if", "ic", "ih", "im", "t", "tf", "ts", "tl",
    "au", "ag", "cu", "al", "zn", "pb", "ni", "sn", "ss",
    "rb", "hc", "i", "j", "jm",
    "sc", "fu", "lu", "bu", "nr",
    "c", "cs", "m", "y", "a", "p", "jd", "lh",
    "cf", "sr", "ta", "ma", "ap", "rm", "oi",
    "pp", "l", "v", "eg", "eb", "pf", "sa", "fg", "ur",
    "si", "lc",
}


def detect_market(code: str) -> str:
    """Infer market type from symbol format.

    Args:
        code: Ticker / symbol string.

    Returns:
        Market type (``a_share``, ``us_equity``, ``hk_equity``,
        ``crypto``, ``futures``, ``forex``).
        Unknown symbols default to ``us_equity``.
    """
    for pattern, market in _MARKET_PATTERNS:
        if pattern.match(code):
            return market
    return "us_equity"


def is_china_futures(code: str) -> bool:
    """Check whether a futures code belongs to a Chinese exchange.

    Recognises two forms:
      1. ``<product><delivery>.<exchange>`` where exchange is one of
         CFFEX/SHFE/DCE/ZCE/INE/GFEX.
      2. Bare ``<product><delivery>`` with no exchange suffix, matched
         against ``_CN_FUTURES_PRODUCTS``.

    Args:
        code: Symbol string.

    Returns:
        True if it looks like a Chinese futures contract.
    """
    parts = code.upper().split(".")
    if len(parts) == 2:
        return parts[1] in _CHINA_EXCHANGES
    m = re.match(r"([A-Za-z]+)\d+", parts[0])
    if m:
        product = m.group(1).lower()
        if product in _CN_FUTURES_PRODUCTS:
            return True
    return False


def detect_submarket(codes: List[str]) -> str:
    """Detect US vs HK vs China-A from symbol suffixes.

    Args:
        codes: Instrument codes.

    Returns:
        ``"hk"`` if any code ends with ``.HK``, ``"china_a"`` if A-share
        patterns are found, else ``"us"``.
    """
    for code in codes:
        if code.upper().endswith(".HK"):
            return "hk"
    for code in codes:
        if detect_market(code) == "a_share":
            return "china_a"
    return "us"
