from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from typing import Any, Optional

from quant_nanggroe.core.scoring.base import BaseScorer, ScorerResult, _clamp

logger = logging.getLogger(__name__)

CFTC_API_URL = "https://publicreporting.cftc.gov/resource/yywx-7w5s.json"

COT_SYMBOL_MAP: dict[str, str] = {
    "EURUSD": "EURO FX",
    "GBPUSD": "BRITISH POUND",
    "USDJPY": "JAPANESE YEN",
    "AUDUSD": "AUSTRALIAN DOLLAR",
    "USDCAD": "CANADIAN DOLLAR",
    "NZDUSD": "NEW ZEALAND DOLLAR",
    "USDCHF": "SWISS FRANC",
    "XAU": "GOLD",
    "XAG": "SILVER",
    "GC": "GOLD",
    "SI": "SILVER",
    "CL": "CRUDE OIL",
    "NG": "NATURAL GAS",
    "ES": "S&P 500",
    "NQ": "NASDAQ 100",
    "YM": "DOW JONES",
    "ZB": "US TREASURY BOND",
    "ZN": "US TREASURY NOTE",
    "ZF": "US TREASURY NOTE 5YR",
}


def _fetch_cot_from_cftc(symbol: str) -> Optional[dict[str, Any]]:
    market_name = None
    for sym_prefix, mkt_name in COT_SYMBOL_MAP.items():
        if symbol.upper().startswith(sym_prefix):
            market_name = mkt_name
            break
    if market_name is None:
        return None

    where = f"market_and_exchange_names like '%25{urllib.parse.quote(market_name)}%25'"
    url = f"{CFTC_API_URL}?$where={where}&$order=report_date_as_yyyy_mm_dd desc&$limit=1"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
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
                "source": "cftc",
            }
    except Exception as exc:
        logger.debug("COT CFTC fetch failed for %s: %s", symbol, exc)

    return None


def _try_hidden_regime_regime(symbol: str) -> Optional[dict[str, Any]]:
    try:
        import hidden_regime as hr

        pipeline = hr.create_simple_regime_pipeline(ticker=symbol, n_states=3)
        result = pipeline.update()
        if result and isinstance(result, dict):
            regime = result.get("current_regime", "unknown")
            conf = float(result.get("regime_confidence", 0.0))
            return {"current_regime": regime, "regime_confidence": min(conf, 1.0), "source": "hidden_regime"}
    except Exception as exc:
        logger.debug("Hidden-regime pipeline failed for %s: %s", symbol, exc)
    return None


class PositioningScorer(BaseScorer):
    weight: float = 0.10

    def __init__(self, use_hidden_regime: bool = True):
        self._use_hidden_regime = use_hidden_regime

    def score(self, ctx: dict[str, Any]) -> ScorerResult:
        symbol = ctx.get("symbol", "EURUSD")

        cot = ctx.get("cot_data")
        if not cot or not isinstance(cot, dict):
            cot = self._fetch_cot(symbol)

        regime = self._get_regime_context(ctx, symbol)

        if not cot:
            return ScorerResult(
                score=0.0,
                confidence=0.0,
                metadata={"symbol": symbol, "source": "unavailable"},
            )

        score, confidence, meta = self._score_cot(cot, regime)
        meta["symbol"] = symbol
        if regime:
            meta["regime"] = regime

        return ScorerResult(
            score=_clamp(score, -100.0, 100.0),
            confidence=_clamp(confidence, 0.0, 1.0),
            metadata=meta,
        )

    def _fetch_cot(self, symbol: str) -> Optional[dict[str, Any]]:
        try:
            return _fetch_cot_from_cftc(symbol)
        except Exception:
            return None

    def _get_regime_context(
        self, ctx: dict[str, Any], symbol: str
    ) -> Optional[dict[str, Any]]:
        regime = ctx.get("regime")
        if regime and isinstance(regime, dict) and "current_regime" in regime:
            return regime

        if self._use_hidden_regime:
            try:
                return _try_hidden_regime_regime(symbol)
            except Exception:
                pass
        return None

    def _normalize_cot(self, cot: dict[str, Any]) -> dict[str, Any]:
        cl = int(cot.get("commercial_long", cot.get("long_commercial", 0)))
        cs = int(cot.get("commercial_short", cot.get("short_commercial", 0)))
        nl = int(
            cot.get(
                "non_commercial_long",
                cot.get("long_noncom", cot.get("long_form", 0)),
            )
        )
        ns = int(
            cot.get(
                "non_commercial_short",
                cot.get("short_noncom", cot.get("short_form", 0)),
            )
        )
        nr_l = int(
            cot.get("non_reportable_long", cot.get("long_nonreport", 0))
        )
        nr_s = int(
            cot.get("non_reportable_short", cot.get("short_nonreport", 0))
        )
        oi = int(cot.get("open_interest", cot.get("open_interest_all", 0))) or 1
        return {
            "commercial_long": cl,
            "commercial_short": cs,
            "non_commercial_long": nl,
            "non_commercial_short": ns,
            "non_reportable_long": nr_l,
            "non_reportable_short": nr_s,
            "open_interest": oi,
            "report_date": str(cot.get("report_date", "")),
        }

    def _score_cot(
        self, cot: dict[str, Any], regime: Optional[dict[str, Any]]
    ) -> tuple[float, float, dict[str, Any]]:
        n = self._normalize_cot(cot)
        meta: dict[str, Any] = {
            "cot_source": cot.get("source", "ctx"),
            "report_date": n["report_date"],
        }

        cl, cs = n["commercial_long"], n["commercial_short"]
        nl, ns = n["non_commercial_long"], n["non_commercial_short"]
        oi = n["open_interest"]

        net_commercial_pct = (cl - cs) / oi * 100.0
        net_spec_pct = (nl - ns) / oi * 100.0

        meta["net_commercial_pct"] = round(net_commercial_pct, 2)
        meta["net_spec_pct"] = round(net_spec_pct, 2)

        extreme = abs(net_spec_pct)

        if net_spec_pct > 15:
            base_score = -50.0
            base_conf = min(extreme / 30.0, 0.8)
        elif net_spec_pct > 8:
            base_score = -25.0
            base_conf = min(extreme / 25.0, 0.6)
        elif net_spec_pct < -15:
            base_score = 50.0
            base_conf = min(extreme / 30.0, 0.8)
        elif net_spec_pct < -8:
            base_score = 25.0
            base_conf = min(extreme / 25.0, 0.6)
        else:
            base_score = 0.0
            base_conf = 0.2

        divergence = abs(net_commercial_pct - net_spec_pct)
        divergence_bonus = min(divergence / 20.0, 0.3)
        agreement = (net_commercial_pct > 0 and net_spec_pct > 0) or (
            net_commercial_pct < 0 and net_spec_pct < 0
        )
        if agreement:
            divergence_bonus = -divergence_bonus * 0.5

        meta["divergence"] = round(divergence, 2)
        meta["agreement"] = agreement

        regime_mod = 1.0
        regime_conf = 0.0
        if regime:
            current_regime = str(regime.get("current_regime", "")).lower()
            regime_conf = float(regime.get("regime_confidence", 0.0))
            meta["regime_name"] = current_regime
            meta["regime_conf"] = regime_conf

            if any(b in current_regime for b in ("bull", "euphoric")):
                if base_score < 0:
                    regime_mod = max(0.5, 1.0 - regime_conf * 0.5)
            elif any(b in current_regime for b in ("bear", "crisis")):
                if base_score > 0:
                    regime_mod = max(0.5, 1.0 - regime_conf * 0.5)

        final_score = base_score * regime_mod
        final_conf = min(base_conf + divergence_bonus + regime_conf * 0.1, 0.99)

        return final_score, final_conf, meta
