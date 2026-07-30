from __future__ import annotations

import logging
from typing import Any, Optional

from quant_nanggroe.core.scoring.base import BaseScorer, ScorerResult, _clamp
from quant_nanggroe.core.scoring.cot_advanced import COTAdvancedScorer, COTAdvancedScore
from quant_nanggroe.providers import cot_provider

logger = logging.getLogger(__name__)


def _try_hidden_regime_regime(symbol: str) -> Optional[dict[str, Any]]:
    try:
        import hidden_regime as hr

        pipeline = hr.create_simple_regime_pipeline(ticker=symbol, n_states=3)
        result = pipeline.update()
        if result and isinstance(result, dict):
            regime = result.get("current_regime", "unknown")
            conf = float(result.get("regime_confidence", 0.0))
            return {
                "current_regime": regime,
                "regime_confidence": min(conf, 1.0),
                "source": "hidden_regime",
            }
    except Exception as exc:
        logger.debug("Hidden-regime pipeline failed for %s: %s", symbol, exc)
    return None


class PositioningScorer(BaseScorer):
    weight: float = 0.10

    def __init__(self, use_hidden_regime: bool = True):
        self._use_hidden_regime = use_hidden_regime
        self._advanced_scorer = COTAdvancedScorer()

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

        result, adv_meta = self._score_cot(cot, regime)
        meta = dict(result.metadata)
        meta["symbol"] = symbol
        if regime:
            meta["regime"] = regime
        meta.update(adv_meta)

        return ScorerResult(
            score=_clamp(result.score, -100.0, 100.0),
            confidence=_clamp(result.confidence, 0.0, 1.0),
            metadata=meta,
        )

    def _fetch_cot(self, symbol: str) -> Optional[dict[str, Any]]:
        try:
            result = cot_provider.fetch_cot(symbol)
            if result is None:
                return None
            latest = result["latest"]
            return {
                "symbol": symbol,
                "report_date": latest["date"],
                "commercial_long": latest["comm_long"],
                "commercial_short": latest["comm_short"],
                "non_commercial_long": latest["spec_long"],
                "non_commercial_short": latest["spec_short"],
                "open_interest": latest["open_interest"],
                "source": "cot_provider",
                "signal": result.get("signal"),
                "history": result.get("history"),
            }
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
        # Fallback ke HiddenRegimeProvider (3-tier)
        try:
            from quant_nanggroe.providers.hidden_regime_provider import HiddenRegimeProvider
            _reg_provider = HiddenRegimeProvider()
            return _reg_provider.get_regime(symbol)
        except Exception:
            pass
        return None

    def _normalize_cot(self, cot: dict[str, Any]) -> dict[str, Any]:
        cl = int(cot.get("commercial_long", cot.get("long_commercial", 0)))
        cs = int(cot.get("commercial_short", cot.get("short_commercial", 0)))
        nl = int(cot.get("non_commercial_long", cot.get("long_noncom", cot.get("long_form", 0))))
        ns = int(cot.get("non_commercial_short", cot.get("short_noncom", cot.get("short_form", 0))))
        nr_l = int(cot.get("non_reportable_long", cot.get("long_nonreport", 0)))
        nr_s = int(cot.get("non_reportable_short", cot.get("short_nonreport", 0)))
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
    ) -> tuple[ScorerResult, dict[str, Any]]:
        n = self._normalize_cot(cot)
        hist = cot.get("history")
        latest_for_scorer: Optional[dict[str, Any]] = None
        if isinstance(hist, list) and len(hist) > 0:
            latest_for_scorer = hist[-1]
            latest_for_scorer.setdefault("open_interest", n["open_interest"])
            latest_for_scorer.setdefault("report_date", n["report_date"])
        else:
            latest_for_scorer = n

        adv: COTAdvancedScore = self._advanced_scorer.score(
            history=hist if isinstance(hist, list) else [],
            latest=latest_for_scorer,
        )

        score = (_clamp(adv.score, 0.0, 100.0) - 50.0) * 2.0
        confidence = _clamp(adv.confidence, 0.0, 1.0)
        meta = adv.metadata
        meta["cot_source"] = cot.get("source", "ctx")
        meta["report_date"] = adv.metadata.get("report_date", n["report_date"])

        regime_mod = 1.0
        regime_conf = 0.0
        if regime:
            current_regime = str(regime.get("current_regime", "")).lower()
            regime_conf = float(regime.get("regime_confidence", 0.0))
            meta["regime_name"] = current_regime
            meta["regime_conf"] = regime_conf

            if any(b in current_regime for b in ("bull", "euphoric")):
                if score < 0:
                    regime_mod = max(0.5, 1.0 - regime_conf * 0.5)
            elif any(b in current_regime for b in ("bear", "crisis")):
                if score > 0:
                    regime_mod = max(0.5, 1.0 - regime_conf * 0.5)

        final_score = _clamp(score * regime_mod, -100.0, 100.0)
        final_conf = min(confidence + regime_conf * 0.1, 0.99)

        base_meta = {
            "net_commercial_pct": round(
                (n["commercial_long"] - n["commercial_short"]) / n["open_interest"] * 100.0, 2
            ),
            "net_spec_pct": round(
                (n["non_commercial_long"] - n["non_commercial_short"]) / n["open_interest"] * 100.0, 2
            ),
        }
        meta.update(base_meta)

        return (
            ScorerResult(score=final_score, confidence=final_conf, metadata=meta),
            meta,
        )
