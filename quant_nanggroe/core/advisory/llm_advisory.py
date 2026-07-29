from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from typing import Any, Optional

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)

_NARRATIVE_RULES: dict[str, str] = {
    "fusion_override": "FusionEngine confidence {conf:.2f} overrides aggregator bias {old_bias} -> {new_bias} due to {reason}",
    "mtf_hold": "Multi-timeframe conflict: HTF={htf_bias} vs LTF={ltf_bias} -> HOLD. Conflicting timeframes signal uncertainty.",
    "mtf_reduce": "Multi-timeframe partial alignment -> reducing position size. HTF={htf_bias} LTF={ltf_bias}",
    "vetoed": "Risk guard veto: {reason}",
    "executed": "Trade executed: {bias} {volume:.2f} lots. Reasoning: {narrative}",
    "no_trade": "No trade: {reason}",
}


@dataclass
class AdvisoryResult:
    narrative: str
    confidence_label: str
    risk_warning: str
    recommendation: str
    llm_generated: bool


class LLMAdvisor:
    _llm_endpoint: str = "http://localhost:20128/v1/chat/completions"
    _llm_models: list[str] = ["kimi-k2.6", "deepseek-v4-flash-free"]

    def _try_llm(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        if httpx is None:
            return None
        for model in self._llm_models:
            try:
                with httpx.Client(timeout=5.0) as client:
                    resp = client.post(
                        self._llm_endpoint,
                        json={
                            "model": model,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                            "max_tokens": 200,
                            "temperature": 0.3,
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        choice = data.get("choices", [{}])[0]
                        content = choice.get("message", {}).get("content", "")
                        if content:
                            logger.info("LLM advisory from %s", model)
                            return content.strip()
            except Exception as exc:
                logger.debug("LLM %s failed: %s", model, exc)
        return None

    def _fusion_override_narrative(
        self,
        fusion_result: Any,
        signal: dict,
    ) -> str:
        old_bias = signal.get("bias", "?")
        new_bias = getattr(fusion_result, "bias", old_bias)
        conf = getattr(fusion_result, "confidence", 0.0)
        composite = getattr(fusion_result, "composite_score", 0.0)
        if composite > 0:
            reason = f"bullish conviction score={composite:.1f}"
        elif composite < 0:
            reason = f"bearish conviction score={composite:.1f}"
        else:
            reason = "scoring engine divergence"
        return _NARRATIVE_RULES["fusion_override"].format(
            conf=conf, old_bias=old_bias, new_bias=new_bias, reason=reason,
        )

    def _mtf_narrative(self, mtf_result: Any) -> str:
        htf = getattr(mtf_result, "htf_bias", "neutral")
        ltf = getattr(mtf_result, "ltf_bias", "neutral")
        msg = getattr(mtf_result, "message", "")
        resolution = getattr(mtf_result, "resolution", None)
        resolution_str = resolution.value if resolution else "hold"
        if resolution_str == "hold":
            return _NARRATIVE_RULES["mtf_hold"].format(htf_bias=htf, ltf_bias=ltf)
        elif resolution_str == "reduce":
            return _NARRATIVE_RULES["mtf_reduce"].format(htf_bias=htf, ltf_bias=ltf)
        return f"MTF aligned {htf}: {msg}"

    def _confidence_label(self, confidence: float) -> str:
        if confidence >= 0.70:
            return "high"
        elif confidence >= 0.40:
            return "medium"
        return "low"

    def _rule_based_advisory(
        self,
        fusion_result: Optional[Any],
        mtf_result: Optional[Any],
        signal: Optional[dict],
        confluence: Optional[Any],
        ctx: Optional[dict],
    ) -> AdvisoryResult:
        signal = signal or {}
        bias = signal.get("bias", "neutral")
        confidence = signal.get("confidence", 0.0)
        conf_label = self._confidence_label(confidence)
        risk_warning = ""
        recommendation = "no_trade"
        narrative_parts: list[str] = []

        offset = ctx or {}

        if fusion_result is not None and getattr(fusion_result, "override_aggregator", False):
            narrative_parts.append(self._fusion_override_narrative(fusion_result, signal))
            bias = getattr(fusion_result, "bias", bias)
            confidence = getattr(fusion_result, "confidence", confidence)
            conf_label = self._confidence_label(confidence)

        if mtf_result is not None:
            resolution = getattr(mtf_result, "resolution", None)
            resolution_str = resolution.value if resolution else None
            if resolution_str == "hold":
                narrative_parts.append(self._mtf_narrative(mtf_result))
                recommendation = "hold"
                bias = "hold"
                confidence = 0.0
                conf_label = "low"
            elif resolution_str == "reduce":
                narrative_parts.append(self._mtf_narrative(mtf_result))
                recommendation = "reduce"
            else:
                narrative_parts.append(self._mtf_narrative(mtf_result))

        if confluence is not None:
            cs = getattr(confluence, "overall_signal", None)
            if cs == "hold":
                narrative_parts.append("Confluence veto: all signals fused to HOLD")
                recommendation = "hold"

        risk_factors: list[str] = []
        if confidence < 0.40:
            risk_factors.append("low confidence")
        macro = offset.get("macro_regime", "")
        if macro and "crisis" in str(macro).lower():
            risk_factors.append("crisis macro regime detected")
        dxy = offset.get("dxy_pct", 0)
        if isinstance(dxy, (int, float)) and abs(dxy) > 2.0:
            risk_factors.append(f"sharp DXY move ({dxy:+.1f}%)")
        if risk_factors:
            risk_warning = "; ".join(risk_factors)

        if bias in ("buy", "sell") and recommendation not in ("hold",):
            recommendation = "execute"
            if narrative_parts:
                narrative = " | ".join(narrative_parts)
            else:
                narrative = _NARRATIVE_RULES["executed"].format(
                    bias=bias, volume=signal.get("volume", 0.0),
                    narrative=f"bias={bias} conf={confidence:.2f}",
                )
        else:
            if not narrative_parts:
                if bias == "hold":
                    reason = "signal bias is HOLD"
                elif bias == "neutral":
                    reason = "signal bias is NEUTRAL"
                else:
                    reason = f"bias={bias} insufficient confidence"
                narrative = _NARRATIVE_RULES["no_trade"].format(reason=reason)
            else:
                narrative = " | ".join(narrative_parts)

        return AdvisoryResult(
            narrative=narrative,
            confidence_label=conf_label,
            risk_warning=risk_warning,
            recommendation=recommendation,
            llm_generated=False,
        )

    def _llm_advisory(
        self,
        fusion_result: Optional[Any],
        mtf_result: Optional[Any],
        signal: Optional[dict],
        confluence: Optional[Any],
        ctx: Optional[dict],
    ) -> Optional[AdvisoryResult]:
        payload = {
            "fusion": {
                "composite_score": getattr(fusion_result, "composite_score", None),
                "confidence": getattr(fusion_result, "confidence", None),
                "bias": getattr(fusion_result, "bias", None),
                "override_aggregator": getattr(fusion_result, "override_aggregator", False),
            } if fusion_result else None,
            "mtf": {
                "htf_bias": getattr(mtf_result, "htf_bias", None),
                "ltf_bias": getattr(mtf_result, "ltf_bias", None),
                "resolution": getattr(mtf_result, "resolution", None),
            } if mtf_result else None,
            "signal": signal,
            "confluence": {
                "overall_signal": getattr(confluence, "overall_signal", None),
                "overall_confidence": getattr(confluence, "overall_confidence", None),
                "confluence_score": getattr(confluence, "confluence_score", None),
            } if confluence else None,
            "ctx": ctx,
        }
        user_prompt = json.dumps(payload, indent=2, default=str)
        system_prompt = (
            "You are a trading analyst. Analyze the scoring data and provide "
            "a concise 2-3 sentence narrative. Never override decisions."
        )
        narrative = self._try_llm(system_prompt, user_prompt)
        if narrative is None:
            return None

        signal_d = signal or {}
        bias = signal_d.get("bias", "neutral")
        confidence = signal_d.get("confidence", 0.0)
        if bias in ("buy", "sell") and confidence >= 0.40:
            recommendation = "execute"
        else:
            recommendation = "hold" if bias == "hold" else "no_trade"

        return AdvisoryResult(
            narrative=narrative,
            confidence_label=self._confidence_label(confidence),
            risk_warning="",
            recommendation=recommendation,
            llm_generated=True,
        )

    def advisory(
        self,
        fusion_result: Optional[Any] = None,
        mtf_result: Optional[Any] = None,
        signal: Optional[dict] = None,
        confluence: Optional[Any] = None,
        ctx: Optional[dict] = None,
    ) -> AdvisoryResult:
        llm_result = self._llm_advisory(fusion_result, mtf_result, signal, confluence, ctx)
        if llm_result is not None:
            return llm_result
        return self._rule_based_advisory(fusion_result, mtf_result, signal, confluence, ctx)
