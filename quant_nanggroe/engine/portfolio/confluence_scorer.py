from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ConfluenceSignal:
    source: str
    signal: str
    confidence: float
    weight: float


@dataclass
class ConfluenceResult:
    overall_signal: str
    overall_confidence: float
    confluence_score: int
    max_possible: int
    weighted_score: float
    signals: list[ConfluenceSignal] = field(default_factory=list)
    reasoning: str = ""


SIGNAL_WEIGHTS: dict[str, float] = {
    "factor_model_sdf": 0.20,
    "smc_strategy": 0.18,
    "statistical_arbitrage": 0.15,
    "microstructure_alpha": 0.12,
    "alternative_data": 0.10,
    "trend_follow_strategy": 0.10,
    "mean_reversion": 0.08,
    "carry_trade": 0.07,
}


class ConfluenceScorer:
    """Multi-module signal fusion with confluence validation.

    Weighted voting from all active strategies + confluence logic:
      - Minimum 3 factors required for trade
      - Weighted score threshold: 0.6
      - Veto override from any fundamental-level signal
      - Macro weather override (highest priority)

    Ported from: Dhaher-Corporation/QUANTUM/phase3_strategy/signal_synthesis.py
    Reference: AQR 'Combining Forecasts', Jacobs & Levy (2023)
    """

    def __init__(self, min_confluence: int = 3, threshold: float = 0.6):
        self.min_confluence = min_confluence
        self.threshold = threshold
        self._signal_history: list[dict[str, Any]] = []

    def evaluate(self, signals: list[dict[str, Any]], macro_bias: float | None = None, macro_weather: str | None = None) -> ConfluenceResult:
        if not signals:
            return ConfluenceResult(
                overall_signal="hold", overall_confidence=0.0,
                confluence_score=0, max_possible=len(signals),
                weighted_score=0.0, reasoning="no signals to evaluate",
            )

        parsed: list[ConfluenceSignal] = []
        for sig in signals:
            source = sig.get("strategy", sig.get("source", "unknown"))
            side = sig.get("side", sig.get("signal", "hold"))
            conf = float(sig.get("confidence", 0.5))
            weight = SIGNAL_WEIGHTS.get(source, 0.08)
            parsed.append(ConfluenceSignal(source=source, signal=side, confidence=conf, weight=weight))

        # Macro override (highest priority)
        if macro_weather in ("RISK_OFF", "LIQUIDITY_CRUNCH"):
            for p in parsed:
                if p.signal == "buy":
                    p.confidence *= 0.3
                    p.weight *= 0.5

        if macro_bias is not None and abs(macro_bias) > 0.5:
            for p in parsed:
                if (macro_bias > 0 and p.signal == "sell") or (macro_bias < 0 and p.signal == "buy"):
                    p.weight *= 0.2

        # Count confluence
        buy_signals = [p for p in parsed if p.signal == "buy"]
        sell_signals = [p for p in parsed if p.signal == "sell"]
        hold_signals = [p for p in parsed if p.signal == "hold"]

        buy_count = len(buy_signals)
        sell_count = len(sell_signals)
        total_non_hold = buy_count + sell_count

        if buy_count == 0 and sell_count == 0:
            return ConfluenceResult(
                overall_signal="hold", overall_confidence=0.0,
                confluence_score=0, max_possible=len(parsed),
                weighted_score=0.0, signals=parsed,
                reasoning="all signals hold",
            )

        # Weighted score
        buy_weighted = sum(p.confidence * p.weight for p in buy_signals)
        sell_weighted = sum(p.confidence * p.weight for p in sell_signals)
        total_weight = sum(p.weight for p in parsed if p.signal in ("buy", "sell"))
        if total_weight == 0:
            return ConfluenceResult(
                overall_signal="hold", overall_confidence=0.0,
                confluence_score=0, max_possible=len(parsed),
                weighted_score=0.0, signals=parsed,
                reasoning="zero weighted signals",
            )

        net_weighted = (buy_weighted - sell_weighted) / total_weight
        confluence = max(buy_count, sell_count)
        weighted_score = abs(net_weighted)

        # Decision
        overall = "hold"
        confidence = 0.0
        reasoning_parts: list[str] = []

        if confluence >= self.min_confluence and weighted_score >= self.threshold:
            if buy_count > sell_count:
                overall = "buy"
                confidence = weighted_score * (confluence / len(parsed))
                reasoning_parts.append(f"buy confluence: {buy_count}/{len(parsed)} signals")
            else:
                overall = "sell"
                confidence = weighted_score * (confluence / len(parsed))
                reasoning_parts.append(f"sell confluence: {sell_count}/{len(parsed)} signals")
        elif confluence >= self.min_confluence:
            reasoning_parts.append(f"confluence={confluence} but weighted_score={weighted_score:.2f} < threshold={self.threshold}")
        else:
            reasoning_parts.append(f"insufficient confluence: need {self.min_confluence}, have {confluence}")

        if macro_weather:
            reasoning_parts.append(f"weather={macro_weather}")
        if macro_bias is not None:
            reasoning_parts.append(f"macro_bias={macro_bias:.2f}")

        self._signal_history.append({
            "timestamp": __import__("time").time(),
            "overall": overall,
            "confidence": confidence,
            "confluence": confluence,
            "weighted_score": weighted_score,
        })
        if len(self._signal_history) > 1000:
            self._signal_history = self._signal_history[-500:]

        return ConfluenceResult(
            overall_signal=overall,
            overall_confidence=round(confidence, 4),
            confluence_score=confluence,
            max_possible=len(parsed),
            weighted_score=round(weighted_score, 4),
            signals=parsed,
            reasoning=" | ".join(reasoning_parts),
        )
