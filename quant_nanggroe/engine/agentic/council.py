"""Council Debate Engine — multi-agent debate for low-confidence signals.

When the ensemble produces a signal below CONFIDENCE_THRESHOLD (0.65),
the Council convenes 3+ investor personas to debate the decision.
Each persona votes buy/sell/hold with reasoning. The council aggregates
and returns the debated signal with updated confidence.
"""

from __future__ import annotations

import logging
import random
from typing import Any

logger = logging.getLogger(__name__)

COUNCIL_PERSONAS: list[tuple[str, str, str]] = [
    ("warren_buffett", "Warren Buffett", "value"),
    ("peter_lynch", "Peter Lynch", "growth_at_reasonable_price"),
    ("ray_dalio", "Ray Dalio", "macro_economic"),
    ("michael_burry", "Michael Burry", "deep_value"),
    ("cathie_wood", "Cathie Wood", "disruptive_growth"),
    ("stanley_druckenmiller", "Stanley Druckenmiller", "macro_momentum"),
]

DEBATE_THRESHOLD = 0.65


class CouncilDebateResult:
    signal: str
    confidence: float
    votes: list[dict[str, Any]]
    debate_held: bool
    summary: str

    def __init__(
        self,
        signal: str,
        confidence: float,
        votes: list[dict[str, Any]],
        debate_held: bool,
        summary: str = "",
    ):
        self.signal = signal
        self.confidence = confidence
        self.votes = votes
        self.debate_held = debate_held
        self.summary = summary


def _load_persona(module_name: str, class_name: str):
    """Lazy-load a persona agent class by module/class name."""
    try:
        mod = __import__(f"quant_nanggroe.agents.personas.{module_name}", fromlist=[class_name])
        cls = getattr(mod, class_name)
        return cls()
    except Exception as exc:
        logger.warning("Failed to load persona %s/%s: %s", module_name, class_name, exc)
        return None


def _persona_class_name(module_name: str) -> str:
    """Derive class name from module name (peter_lynch -> PeterLynchAgent)."""
    parts = module_name.split("_")
    return "".join(p.capitalize() for p in parts) + "Agent"


def _aggregate_votes(votes: list[dict[str, Any]]) -> tuple[str, float, str]:
    """Aggregate persona votes into a final signal.

    buy = +1, sell = -1, hold/neutral = 0.
    Weighted by each persona's confidence.
    """
    score = 0.0
    total_weight = 0.0
    buy_reasons: list[str] = []
    sell_reasons: list[str] = []
    hold_reasons: list[str] = []

    for v in votes:
        sig = v.get("signal", "neutral")
        conf = v.get("confidence", 0.5)
        reasoning = v.get("reasoning", "")
        weight = conf

        if sig == "buy":
            score += weight
            buy_reasons.append(reasoning)
        elif sig == "sell":
            score -= weight
            sell_reasons.append(reasoning)
        else:
            hold_reasons.append(reasoning)
        total_weight += weight

    if total_weight == 0:
        return "hold", 0.0, "No consensus"

    normalized = score / total_weight  # -1.0 to +1.0

    if normalized > 0.2:
        signal = "buy"
        confidence = min(abs(normalized), 1.0)
        summary = f"Council leans buy ({len(buy_reasons)} of {len(votes)})"
    elif normalized < -0.2:
        signal = "sell"
        confidence = min(abs(normalized), 1.0)
        summary = f"Council leans sell ({len(sell_reasons)} of {len(votes)})"
    else:
        signal = "hold"
        confidence = 0.5
        summary = f"Council divided ({len(buy_reasons)} buy / {len(sell_reasons)} sell / {len(hold_reasons)} hold)"

    return signal, confidence, summary


def convene_council(
    symbol: str,
    proposed_signal: str,
    proposed_confidence: float,
    price: float | None = None,
    regime: str | None = None,
    council_size: int = 3,
) -> CouncilDebateResult:
    """Convene the council to debate a low-confidence signal.

    Args:
        symbol: Trading symbol.
        proposed_signal: The ensemble's proposed signal (buy/sell/hold).
        proposed_confidence: The ensemble's confidence (0-1).
        price: Current price (optional, for persona context).
        regime: Market regime (optional).
        council_size: Number of personas to convene (default 3, max 6).

    Returns:
        CouncilDebateResult with debated signal, confidence, and votes.
    """
    result = CouncilDebateResult(
        signal=proposed_signal,
        confidence=proposed_confidence,
        votes=[],
        debate_held=False,
    )

    if proposed_confidence >= DEBATE_THRESHOLD:
        result.summary = f"Confidence {proposed_confidence:.2%} >= {DEBATE_THRESHOLD:.0%}, council not needed"
        return result

    council_size = max(1, min(council_size, len(COUNCIL_PERSONAS)))

    # Select personas with diverse styles
    selected = random.sample(COUNCIL_PERSONAS, min(council_size, len(COUNCIL_PERSONAS)))
    votes: list[dict[str, Any]] = []

    for module_name, display_name, style in selected:
        cls_name = _persona_class_name(module_name)
        agent = _load_persona(module_name, cls_name)
        if agent is None:
            continue

        try:
            analysis = agent.analyze(symbol)
            persona_signal = analysis.get("signal", "neutral")
            persona_confidence = analysis.get("confidence", 0.5)
            reasoning = analysis.get("reasoning", f"{display_name} analyzed {symbol}")
        except Exception as exc:
            logger.warning("Persona %s failed: %s", display_name, exc)
            persona_signal = "neutral"
            persona_confidence = 0.3
            reasoning = f"{display_name} unavailable"

        votes.append({
            "persona": display_name,
            "style": style,
            "signal": persona_signal,
            "confidence": persona_confidence,
            "reasoning": reasoning,
        })

    if not votes:
        result.summary = "No council members could be convened"
        return result

    final_signal, final_confidence, summary = _aggregate_votes(votes)

    result.signal = final_signal
    result.confidence = final_confidence
    result.votes = votes
    result.debate_held = True
    result.summary = summary

    logger.info(
        "Council debate for %s: proposed=%s@%.0f%% → decided=%s@%.0f%% (%s)",
        symbol, proposed_signal, proposed_confidence * 100,
        final_signal, final_confidence * 100, summary,
    )

    return result
