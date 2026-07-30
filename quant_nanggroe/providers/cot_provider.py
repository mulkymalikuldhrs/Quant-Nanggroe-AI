"""COT Provider — unified CFTC Commitment of Traders data.

Single source of truth for all COT fetching and analysis.
Resolves duplication between hidden_regime_provider.py and positioning_scorer.py.
Modeled on TradeBobby's approach: 8-week history, percentile rank,
week/month change, extreme flags.

API: https://publicreporting.cftc.gov/resource/6dca-aqww.json (Legacy Futures-Only)
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)

_CFTC_API_URL = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"

COT_SYMBOL_MAP: dict[str, str] = {
    # Forex
    "EURUSD": "EURO FX",
    "GBPUSD": "BRITISH POUND",
    "USDJPY": "JAPANESE YEN",
    "AUDUSD": "AUSTRALIAN DOLLAR",
    "USDCAD": "CANADIAN DOLLAR",
    "NZDUSD": "NEW ZEALAND DOLLAR",
    "USDCHF": "SWISS FRANC",
    # Metals
    "XAUUSD": "GOLD",
    "XAU": "GOLD",
    "GC": "GOLD",
    "XAGUSD": "SILVER",
    "XAG": "SILVER",
    "SI": "SILVER",
    "COPPER": "COPPER",
    "XPTUSD": "PLATINUM",
    "PLATINUM": "PLATINUM",
    # Energy
    "USOIL": "CRUDE OIL, LIGHT SWEET",
    "CL": "CRUDE OIL, LIGHT SWEET",
    "WTI": "CRUDE OIL, LIGHT SWEET",
    "NATGAS": "NAT GAS",
    "NG": "NAT GAS",
    # Indices
    "SPX500": "E-MINI S&P 500",
    "ES": "E-MINI S&P 500",
    "NAS100": "E-MINI NASDAQ-100",
    "NQ": "E-MINI NASDAQ-100",
    "DJI": "DJIA",
    "YM": "DJIA",
    # Crypto
    "BTCUSD": "BITCOIN",
    "BTC": "BITCOIN",
    # Agriculture
    "WHEAT": "WHEAT",
    "CORN": "CORN",
    "SOYBEAN": "SOYBEAN",
    # Treasuries
    "ZB": "US TREASURY BOND",
    "ZN": "US TREASURY NOTE",
    "ZF": "US TREASURY NOTE 5YR",
}


def resolve_match_string(symbol: str) -> str | None:
    upper = symbol.upper()
    for prefix, match in COT_SYMBOL_MAP.items():
        if upper.startswith(prefix):
            return match
    return None


@dataclass
class CotRecord:
    date: str
    market: str
    open_interest: int
    spec_long: int
    spec_short: int
    spec_spread: int
    spec_net: int
    spec_pct_long: float
    comm_long: int
    comm_short: int
    comm_net: int

    @classmethod
    def from_api_row(cls, row: dict[str, Any]) -> Optional["CotRecord"]:
        if not row:
            return None
        try:
            long_n = int(row.get("noncomm_positions_long_all", 0))
            short_n = int(row.get("noncomm_positions_short_all", 0))
            spread_n = int(
                row.get("noncomm_postions_spread_all",
                        row.get("noncomm_positions_spread", 0))
            )
            oi = int(row.get("open_interest_all", 0))
            comm_long = int(row.get("comm_positions_long_all", 0))
            comm_short = int(row.get("comm_positions_short_all", 0))
        except (ValueError, TypeError):
            return None

        net = long_n - short_n
        total = long_n + short_n
        pct_long = (long_n / total * 100.0) if total > 0 else 50.0

        return cls(
            date=str(row.get("report_date_as_yyyy_mm_dd", ""))[:10],
            market=str(row.get("contract_market_name", "")),
            open_interest=oi,
            spec_long=long_n,
            spec_short=short_n,
            spec_spread=spread_n,
            spec_net=net,
            spec_pct_long=round(pct_long, 1),
            comm_long=comm_long,
            comm_short=comm_short,
            comm_net=comm_long - comm_short,
        )


@dataclass
class CotSignal:
    # DEPRECATED — use quant_nanggroe.types.signals.Signal instead.
    # bias -> signal_type, COT-specific fields map to evidence/indicators in canonical.
    bias: str
    spec_net: int
    pct_long: float
    week_change: int
    month_change: int
    percentile_8w: int
    extreme: bool


# ---------------------------------------------------------------------------
# Internal fetchers
# ---------------------------------------------------------------------------


def _fetch_raw(match_string: str, weeks: int = 8) -> list[dict[str, Any]]:
    import urllib.parse
    from urllib.request import Request, urlopen

    where = (
        f"market_and_exchange_names like '%25"
        f"{urllib.parse.quote(match_string)}%25'"
    )
    url = (
        f"{_CFTC_API_URL}?$limit={weeks}&$where={where}"
        f"&$order=report_date_as_yyyy_mm_dd desc"
    )
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        logger.debug("COT API fetch failed for %s: %s", match_string, exc)
        return []


def _build_signal(history: list[CotRecord]) -> CotSignal:
    if not history:
        return CotSignal(
            bias="UNKNOWN", spec_net=0, pct_long=50.0,
            week_change=0, month_change=0, percentile_8w=50, extreme=False,
        )

    cur = history[0]
    wk1 = history[1] if len(history) > 1 else None
    wk4 = history[3] if len(history) > 3 else None

    nets = [h.spec_net for h in history]
    mn, mx = min(nets), max(nets)
    pct = ((cur.spec_net - mn) / (mx - mn) * 100) if mx > mn else 50.0

    cur_pct = cur.spec_pct_long
    if cur_pct > 70:
        bias = "CROWDED LONG"
    elif cur_pct < 30:
        bias = "CROWDED SHORT"
    elif cur_pct > 60:
        bias = "NET LONG"
    elif cur_pct < 40:
        bias = "NET SHORT"
    else:
        bias = "NEUTRAL"

    wk_change = cur.spec_net - wk1.spec_net if wk1 else 0
    mo_change = cur.spec_net - wk4.spec_net if wk4 else 0

    return CotSignal(
        bias=bias,
        spec_net=cur.spec_net,
        pct_long=cur_pct,
        week_change=wk_change,
        month_change=mo_change,
        percentile_8w=int(round(pct)),
        extreme=pct > 90 or pct < 10,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_cot(symbol: str, weeks: int = 8) -> Optional[dict[str, Any]]:
    """Fetch COT data for *symbol* with 8-week trend analysis.

    Returns structured dict or None if unmapped / fetch fails::

        {
            "symbol": "EURUSD",
            "match_string": "EURO FX",
            "latest": CotRecord-fields,
            "signal": {bias, spec_net, pct_long, week_change,
                       month_change, percentile_8w, extreme},
            "history": [{date, spec_net, spec_pct_long, comm_net}, ...],
            "report_date": "2026-07-28",
        }
    """
    match = resolve_match_string(symbol)
    if match is None:
        return None

    rows = _fetch_raw(match, weeks)
    if not rows:
        return None

    records = [r for r in (CotRecord.from_api_row(row) for row in rows) if r]
    if not records:
        return None

    signal = _build_signal(records)
    cur = records[0]

    return {
        "symbol": symbol,
        "match_string": match,
        "latest": {
            "date": cur.date,
            "market": cur.market,
            "open_interest": cur.open_interest,
            "spec_long": cur.spec_long,
            "spec_short": cur.spec_short,
            "spec_spread": cur.spec_spread,
            "spec_net": cur.spec_net,
            "spec_pct_long": cur.spec_pct_long,
            "comm_long": cur.comm_long,
            "comm_short": cur.comm_short,
            "comm_net": cur.comm_net,
        },
        "signal": {
            "bias": signal.bias,
            "spec_net": signal.spec_net,
            "pct_long": signal.pct_long,
            "week_change": signal.week_change,
            "month_change": signal.month_change,
            "percentile_8w": signal.percentile_8w,
            "extreme": signal.extreme,
        },
        "history": [
            {
                "date": r.date,
                "spec_net": r.spec_net,
                "spec_pct_long": r.spec_pct_long,
                "comm_net": r.comm_net,
            }
            for r in records
        ],
        "report_date": cur.date,
    }
