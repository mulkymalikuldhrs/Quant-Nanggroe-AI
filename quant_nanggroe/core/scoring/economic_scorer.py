from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any, Optional

from quant_nanggroe.core.cache import TTLCache, cached
from quant_nanggroe.core.scoring.base import BaseScorer, ScorerResult, _clamp

logger = logging.getLogger(__name__)

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

_FRED_CACHE = TTLCache(default_ttl=600)

SERIES = {
    "cpi": "CPIAUCSL",
    "unemployment": "UNRATE",
    "nonfarm_payrolls": "PAYEMS",
    "industrial_production": "INDPRO",
    "fed_funds": "DFF",
    "gdp": "GDPC1",
}


@cached(_FRED_CACHE, key_prefix="fred", ttl=600)
def _fred_fetch(series_id: str, api_key: str) -> Optional[list[dict]]:
    url = f"{FRED_BASE}?series_id={series_id}&api_key={api_key}&file_type=json&sort_order=desc&limit=13"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data.get("observations", [])
    except Exception as exc:
        logger.debug("FRED fetch failed for %s: %s", series_id, exc)
        return None


def _parse_value(v: str) -> Optional[float]:
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


class EconomicScorer(BaseScorer):
    weight: float = 0.20

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.environ.get("FRED_API_KEY", "")

    def _score_cpi(self, api_key: str) -> tuple[float, float]:
        obs = _fred_fetch(SERIES["cpi"], api_key)
        if not obs or len(obs) < 2:
            return 0.0, 0.0
        values = [_parse_value(o["value"]) for o in obs[:13]]
        values = [v for v in values if v is not None]
        if len(values) < 2:
            return 0.0, 0.0
        current = values[0]
        yoy = (current / values[-1] - 1.0) * 100
        if yoy > 5:
            return -30.0, min((yoy - 5) / 5, 0.8)
        if yoy > 3:
            return -15.0, (yoy - 3) / 2
        if yoy < 1:
            return -10.0, min((1 - yoy) / 2, 0.6)
        return 15.0, max(0.3, 1.0 - abs(yoy - 2.0) / 2.0)

    def _score_unemployment(self, api_key: str) -> tuple[float, float]:
        obs = _fred_fetch(SERIES["unemployment"], api_key)
        if not obs or len(obs) < 2:
            return 0.0, 0.0
        vals = [_parse_value(o["value"]) for o in obs[:2]]
        vals = [v for v in vals if v is not None]
        if len(vals) < 2:
            return 0.0, 0.0
        current = vals[0]
        if current < 3.5:
            return -10.0, min((3.5 - current) / 2, 0.5)
        if current > 6:
            return -30.0, min((current - 6) / 2, 0.7)
        if current > 4.5:
            return -5.0, (current - 4.5) / 1.5
        return 10.0, max(0.3, 1.0 - abs(current - 4.0) / 2.0)

    def _score_payrolls(self, api_key: str) -> tuple[float, float]:
        obs = _fred_fetch(SERIES["nonfarm_payrolls"], api_key)
        if not obs or len(obs) < 2:
            return 0.0, 0.0
        vals = [_parse_value(o["value"]) for o in obs[:2]]
        vals = [v for v in vals if v is not None]
        if len(vals) < 2:
            return 0.0, 0.0
        change = (vals[0] - vals[1]) / vals[1] * 100
        annualized = change * 12
        if annualized > 2:
            return 20.0, min((annualized - 2) / 3, 0.7)
        if annualized > 1:
            return 10.0, (annualized - 1) / 1
        if annualized > 0:
            return 0.0, annualized
        return -20.0, min(abs(annualized), 0.7)

    def _score_fed_funds(self, api_key: str) -> tuple[float, float]:
        obs = _fred_fetch(SERIES["fed_funds"], api_key)
        if not obs or len(obs) < 2:
            return 0.0, 0.0
        vals = [_parse_value(o["value"]) for o in obs[:2]]
        vals = [v for v in vals if v is not None]
        if len(vals) < 2:
            return 0.0, 0.0
        rate = vals[0]
        if rate > 5.5:
            return -30.0, min((rate - 5.5) / 2, 0.8)
        if rate > 3:
            return -15.0, (rate - 3) / 2.5
        if rate < 0.5:
            return -5.0, max(0.2, (0.5 - rate) / 0.5)
        return 10.0, max(0.2, 1.0 - abs(rate - 2.5) / 2.5)

    def score(self, ctx: dict[str, Any]) -> ScorerResult:
        api_key = ctx.get("fred_api_key", self._api_key)
        if not api_key:
            return ScorerResult(score=0.0, confidence=0.0, metadata={"error": "no_fred_api_key"})
        components = {}
        total_score = 0.0
        total_conf = 0.0
        n = 0
        for name, func in [
            ("cpi", self._score_cpi),
            ("unemployment", self._score_unemployment),
            ("payrolls", self._score_payrolls),
            ("fed_funds", self._score_fed_funds),
        ]:
            try:
                s, c = func(api_key)
                components[name] = {"score": round(s, 1), "confidence": round(c, 2)}
                total_score += s
                total_conf += c
                n += 1
            except Exception as exc:
                logger.debug("EconomicScorer %s failed: %s", name, exc)
                components[name] = {"error": str(exc)}
        if n == 0:
            return ScorerResult(score=0.0, confidence=0.0, metadata={"error": "all_failed"})
        return ScorerResult(
            score=_clamp(total_score / n, -100.0, 100.0),
            confidence=_clamp(total_conf / n, 0.0, 1.0),
            metadata={"components": components, "fred_api_key_set": bool(api_key)},
        )
