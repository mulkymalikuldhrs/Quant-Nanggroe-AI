"""Hidden regime provider: COT regime data + signal attribution.

Extracts value from E:\\hidden-regime analysis package or falls back to CFTC API.
Returns dict with regime state, signal attribution scores.
Graceful fallback — no crashes if E:\\ not accessible or package missing.
"""
from __future__ import annotations

import importlib.util
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)

_HIDDEN_REGIME_DIR = r"E:\hidden-regime"
_HIDDEN_REGIME_FOUND: bool | None = None
"""None = not checked yet, True = spec found, False = not found."""

# ---------------------------------------------------------------------------
# Check package exists (find_spec avoids triggering full import / missing deps)
# ---------------------------------------------------------------------------


def _find_hidden_regime() -> bool:
    """Return True if hidden-regime is installable (pip or E:\\). Does NOT import it."""
    global _HIDDEN_REGIME_FOUND
    if _HIDDEN_REGIME_FOUND is not None:
        return _HIDDEN_REGIME_FOUND

    # Check pip-installed
    if importlib.util.find_spec("hidden_regime") is not None:
        _HIDDEN_REGIME_FOUND = True
        return True
    # Check E:\
    if os.path.isdir(_HIDDEN_REGIME_DIR) and os.path.isfile(
        os.path.join(_HIDDEN_REGIME_DIR, "hidden_regime", "__init__.py")
    ):
        if _HIDDEN_REGIME_DIR not in sys.path:
            sys.path.insert(0, _HIDDEN_REGIME_DIR)
        if importlib.util.find_spec("hidden_regime") is not None:
            _HIDDEN_REGIME_FOUND = True
            return True

    _HIDDEN_REGIME_FOUND = False
    return False


def _import_hr():
    """Import and return hidden_regime module or raise ImportError."""
    # This import happens inside try/except in callers, so transitive
    # dependency failures (seaborn, pyarrow, etc.) are caught there.
    import hidden_regime as _hr

    return _hr


def _try_hidden_regime_regime(symbol: str) -> Optional[dict[str, Any]]:
    """Run hidden-regime pipeline for *symbol*, return regime dict or None."""
    if not _find_hidden_regime():
        return None
    try:
        hr = _import_hr()
        pipeline = hr.create_simple_regime_pipeline(ticker=symbol, n_states=3)
        result = pipeline.update()
        if result and isinstance(result, dict):
            regime = result.get("current_regime", "unknown")
            conf = float(result.get("regime_confidence", 0.0))
            return {
                "current_regime": regime,
                "regime_confidence": min(conf, 1.0),
                "source": "hidden_regime",
                "analysis_timestamp": result.get("analysis_timestamp", datetime.now().isoformat()),
            }
    except Exception as exc:
        logger.debug("Hidden-regime regime failed for %s: %s", symbol, exc)
    return None


def _try_hidden_regime_attribution(symbol: str) -> Optional[dict[str, Any]]:
    """Run hidden-regime attribution analysis for *symbol*."""
    if not _find_hidden_regime():
        return None
    try:
        hr = _import_hr()
        pipeline = hr.create_trading_pipeline(ticker=symbol, n_states=4)
        result = pipeline.update()
        if result and isinstance(result, dict):
            signals = result.get("signal_performances") or result.get("signal_attribution", {})
            return {
                "symbol": symbol,
                "signals": signals,
                "attribution_quality": result.get("attribution_quality_score"),
                "source": "hidden_regime",
                "analysis_timestamp": result.get("analysis_timestamp", datetime.now().isoformat()),
            }
    except Exception as exc:
        logger.debug("Hidden-regime attribution failed for %s: %s", symbol, exc)
    return None


# ---------------------------------------------------------------------------
# CFTC API fallback (direct HTTP, no hidden-regime dependency)
# ---------------------------------------------------------------------------

_CFTC_API_URL = "https://publicreporting.cftc.gov/resource/yywx-7w5s.json"

_COT_SYMBOL_MAP: dict[str, str] = {
    "EURUSD": "EURO FX",
    "GBPUSD": "BRITISH POUND",
    "USDJPY": "JAPANESE YEN",
    "AUDUSD": "AUSTRALIAN DOLLAR",
    "USDCAD": "CANADIAN DOLLAR",
    "NZDUSD": "NEW ZEALAND DOLLAR",
    "USDCHF": "SWISS FRANC",
    "XAU": "GOLD",
    "GC": "GOLD",
    "SI": "SILVER",
    "XAG": "SILVER",
    "CL": "CRUDE OIL",
    "NG": "NATURAL GAS",
    "ES": "S&P 500",
    "NQ": "NASDAQ 100",
    "YM": "DOW JONES",
    "ZB": "US TREASURY BOND",
    "ZN": "US TREASURY NOTE",
    "ZF": "US TREASURY NOTE 5YR",
}


def _fetch_cftc_cot(symbol: str) -> Optional[dict[str, Any]]:
    """Fetch COT data from CFTC API. No auth required (public Socrata)."""
    import urllib.parse
    from urllib.request import Request, urlopen

    market_name = None
    for sym_prefix, mkt_name in _COT_SYMBOL_MAP.items():
        if symbol.upper().startswith(sym_prefix):
            market_name = mkt_name
            break
    if market_name is None:
        return None

    where = f"market_and_exchange_names like '%25{urllib.parse.quote(market_name)}%25'"
    url = f"{_CFTC_API_URL}?$where={where}&$order=report_date_as_yyyy_mm_dd desc&$limit=1"
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=10) as resp:
            rows = json.loads(resp.read().decode())
            if not rows:
                return None
            r = rows[0]
            return {
                "symbol": symbol,
                "report_date": r.get("report_date_as_yyyy_mm_dd", ""),
                "commercial_long": int(r.get("long_commercial", 0)),
                "commercial_short": int(r.get("short_commercial", 0)),
                "non_commercial_long": int(r.get("long_noncom", 0)),
                "non_commercial_short": int(r.get("short_noncom", 0)),
                "non_reportable_long": int(r.get("long_nonreport", 0)),
                "non_reportable_short": int(r.get("short_nonreport", 0)),
                "open_interest": int(r.get("open_interest_all", 0)),
                "source": "cftc_public_api",
            }
    except Exception as exc:
        logger.debug("CFTC API fetch failed for %s: %s", symbol, exc)
    return None


def _score_cot_fallback(cot: dict[str, Any]) -> dict[str, Any]:
    """Derive regime-like signal from raw COT numbers (standalone)."""
    cl = int(cot.get("commercial_long", 0))
    cs = int(cot.get("commercial_short", 0))
    nl = int(cot.get("non_commercial_long", 0))
    ns = int(cot.get("non_commercial_short", 0))
    oi = int(cot.get("open_interest", 1)) or 1

    net_spec = (nl - ns) / oi * 100.0
    net_comm = (cl - cs) / oi * 100.0

    if net_spec > 12:
        regime = "crowded_long"
        confidence = min(abs(net_spec) / 25.0, 0.8)
    elif net_spec < -12:
        regime = "crowded_short"
        confidence = min(abs(net_spec) / 25.0, 0.8)
    elif net_spec > 5:
        regime = "bullish"
        confidence = min(abs(net_spec) / 20.0, 0.5)
    elif net_spec < -5:
        regime = "bearish"
        confidence = min(abs(net_spec) / 20.0, 0.5)
    else:
        regime = "neutral"
        confidence = 0.2

    divergence = abs(net_comm - net_spec)
    return {
        "current_regime": regime,
        "regime_confidence": round(confidence, 3),
        "net_speculative_pct": round(net_spec, 2),
        "net_commercial_pct": round(net_comm, 2),
        "divergence": round(divergence, 2),
        "report_date": cot.get("report_date", ""),
        "source": "cftc_derived",
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class HiddenRegimeProvider:
    """Provider for COT regime data and signal attribution.

    Tiers:
        1. hidden-regime Python package (pip or E:\\ source)
        2. CFTC public API (no auth required)
        3. Static fallback dict (never crashes)
    """

    def __init__(self) -> None:
        self._hr_available = _find_hidden_regime()

    def is_available(self) -> bool:
        return self._hr_available

    def get_regime(self, symbol: str = "EURUSD") -> dict[str, Any]:
        """Return regime state dict for *symbol*.

        Returns keys: current_regime, regime_confidence, source, optional details.
        Never raises — returns fallback dict on failure.
        """
        try:
            result = _try_hidden_regime_regime(symbol)
            if result is not None:
                return result
        except Exception as exc:
            logger.debug("HiddenRegimeProvider.get_regime(%s) err: %s", symbol, exc)

        # Fallback: CFTC COT → derived regime
        try:
            cot = _fetch_cftc_cot(symbol)
            if cot is not None:
                regime = _score_cot_fallback(cot)
                regime["cot_raw"] = {
                    k: cot[k] for k in ("commercial_long", "commercial_short",
                                        "non_commercial_long", "non_commercial_short",
                                        "open_interest", "report_date")
                }
                return regime
        except Exception as exc:
            logger.debug("CFTC fallback failed for %s: %s", symbol, exc)

        return {
            "current_regime": "unknown",
            "regime_confidence": 0.0,
            "source": "fallback",
            "symbol": symbol,
        }

    def get_attribution(self, symbol: str = "EURUSD") -> dict[str, Any]:
        """Return signal attribution breakdown for *symbol*.

        Requires hidden-regime package. Returns fallback dict if unavailable.
        """
        try:
            result = _try_hidden_regime_attribution(symbol)
            if result is not None:
                return result
        except Exception as exc:
            logger.debug("HiddenRegimeProvider.get_attribution(%s) err: %s", symbol, exc)

        return {
            "symbol": symbol,
            "signals": {},
            "attribution_quality": None,
            "source": "unavailable",
        }

    def get_cot(self, symbol: str = "EURUSD") -> Optional[dict[str, Any]]:
        """Fetch raw COT data. No hidden-regime needed. Returns None on failure."""
        try:
            return _fetch_cftc_cot(symbol)
        except Exception as exc:
            logger.debug("HiddenRegimeProvider.get_cot(%s) err: %s", symbol, exc)
        return None
