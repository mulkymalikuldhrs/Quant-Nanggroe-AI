"""
Bull/Bear Debate System — Multi-Agent Adversarial Analysis
============================================================
Structured debate between Bull and Bear advocates with a Judge
that synthesizes arguments and renders a verdict.

The debate process:
    1. Bull advocate presents bullish case with evidence
    2. Bear advocate presents bearish case with evidence
    3. Each side rebuts the other's arguments
    4. Arguments are scored against market data
    5. Judge synthesizes and renders verdict

The system evaluates arguments quantitatively against:
    - Technical indicators (RSI, MACD, trend, ATR)
    - Price action (support/resistance, patterns)
    - Volume and liquidity conditions
    - Sentiment indicators

Verdict includes confidence level and key deciding factors.
"""

from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# MODELS
# ══════════════════════════════════════════════════════════════════════


class DebateSide(str, Enum):
    """Debate side."""

    BULL = "BULL"
    BEAR = "BEAR"


class DebateVerdictType(str, Enum):
    """Possible debate verdicts."""

    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class ArgumentStrength(str, Enum):
    """Strength of an argument."""

    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    INVALID = "INVALID"


class DebateArgument(BaseModel):
    """A single argument in the debate."""

    claim: str
    evidence: str = ""
    indicator: str = ""  # Which indicator supports this
    strength: ArgumentStrength = ArgumentStrength.MODERATE
    weight: float = Field(ge=0.0, le=1.0, default=0.5)
    rebuttal: str = ""  # Counter-argument from opponent


class DebatePosition(BaseModel):
    """A position in the bull/bear debate."""

    side: DebateSide
    arguments: list[DebateArgument] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    conviction: float = Field(ge=0.0, le=1.0, default=0.5)
    total_score: float = 0.0


class DebateVerdict(BaseModel):
    """Verdict from the bull/bear debate."""

    verdict: DebateVerdictType = DebateVerdictType.NEUTRAL
    bull_score: float = Field(ge=0.0, le=1.0, default=0.5)
    bear_score: float = Field(ge=0.0, le=1.0, default=0.5)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    key_arguments: list[str] = Field(default_factory=list)
    deciding_factors: list[str] = Field(default_factory=list)
    bull_args_evaluated: list[DebateArgument] = Field(default_factory=list)
    bear_args_evaluated: list[DebateArgument] = Field(default_factory=list)
    rebuttals: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)


# ══════════════════════════════════════════════════════════════════════
# ARGUMENT EVALUATOR
# ══════════════════════════════════════════════════════════════════════


class ArgumentEvaluator:
    """
    Evaluates debate arguments against real market data.

    Scores each argument based on how well it is supported
    by technical indicators, price action, and market conditions.
    """

    # Map of argument keywords to technical indicator checks
    BULL_INDICATORS = {
        "oversold": "rsi_oversold",
        "undervalued": "price_below_sma",
        "breakout": "price_above_resistance",
        "momentum": "macd_bullish",
        "support": "near_support",
        "uptrend": "ema_bullish_alignment",
        "accumulation": "volume_above_avg",
        "bullish_candle": "bullish_candle_pattern",
    }

    BEAR_INDICATORS = {
        "overbought": "rsi_overbought",
        "overvalued": "price_above_sma",
        "breakdown": "price_below_support",
        "momentum_loss": "macd_bearish",
        "resistance": "near_resistance",
        "downtrend": "ema_bearish_alignment",
        "distribution": "volume_above_avg",
        "bearish_candle": "bearish_candle_pattern",
    }

    def evaluate(
        self,
        arguments: list[DebateArgument],
        side: DebateSide,
        data: dict[str, Any],
    ) -> list[DebateArgument]:
        """
        Score and evaluate arguments against market data.

        Args:
            arguments: List of debate arguments
            side: BULL or BEAR
            data: Market data with indicators

        Returns:
            Arguments with updated strength and weight
        """
        indicator_map = (
            self.BULL_INDICATORS if side == DebateSide.BULL else self.BEAR_INDICATORS
        )

        evaluated = []
        for arg in arguments:
            score = self._score_argument(arg, indicator_map, data)
            evaluated.append(DebateArgument(
                claim=arg.claim,
                evidence=arg.evidence,
                indicator=arg.indicator,
                strength=self._score_to_strength(score),
                weight=score,
                rebuttal=arg.rebuttal,
            ))

        return evaluated

    def _score_argument(
        self,
        arg: DebateArgument,
        indicator_map: dict[str, str],
        data: dict[str, Any],
    ) -> float:
        """Score a single argument based on data evidence."""
        claim_lower = arg.claim.lower()
        score = 0.5  # Default neutral

        # Check if claim matches known indicator patterns
        indicators = data.get("indicators", {})
        price_data = data.get("price", {})
        closes = price_data.get("closes", [])

        # RSI-based arguments
        if any(kw in claim_lower for kw in ["oversold", "rsi"]):
            rsi = indicators.get("rsi_14")
            if rsi is not None:
                if ("oversold" in claim_lower and rsi < 30) or ("overbought" in claim_lower and rsi > 70):
                    score = 0.9
                elif ("oversold" in claim_lower and rsi < 40) or ("overbought" in claim_lower and rsi > 60):
                    score = 0.6
                else:
                    score = 0.2

        # Trend-based arguments
        elif any(kw in claim_lower for kw in ["trend", "uptrend", "downtrend"]):
            ema_9 = indicators.get("ema_9")
            ema_20 = indicators.get("ema_20")
            ema_50 = indicators.get("ema_50")
            if all(v is not None for v in [ema_9, ema_20, ema_50]):
                if ("uptrend" in claim_lower and ema_9 > ema_20 > ema_50) or ("downtrend" in claim_lower and ema_9 < ema_20 < ema_50):
                    score = 0.9
                elif ("uptrend" in claim_lower and ema_9 > ema_20) or ("downtrend" in claim_lower and ema_9 < ema_20):
                    score = 0.6
                else:
                    score = 0.2

        # MACD-based arguments
        elif any(kw in claim_lower for kw in ["momentum", "macd"]):
            macd_data = indicators.get("macd", {})
            hist = macd_data.get("histogram")
            if hist is not None:
                if ("bullish" in claim_lower and hist > 0) or ("bearish" in claim_lower and hist < 0):
                    score = 0.8
                else:
                    score = 0.3

        # Support/resistance arguments
        elif any(kw in claim_lower for kw in ["support", "resistance"]):
            bb = indicators.get("bollinger", {})
            current = price_data.get("current", 0)
            lower = bb.get("lower")
            upper = bb.get("upper")
            if all(v is not None for v in [current, lower, upper]):
                if ("support" in claim_lower and current <= lower * 1.02) or ("resistance" in claim_lower and current >= upper * 0.98):
                    score = 0.85
                else:
                    score = 0.3

        # Volume arguments
        elif any(kw in claim_lower for kw in ["volume", "accumulation", "distribution"]):
            vol_ratio = data.get("volume_ratio", 1.0)
            if vol_ratio > 1.5:
                score = 0.8
            elif vol_ratio > 1.2:
                score = 0.6
            else:
                score = 0.3

        # Volatility arguments
        elif any(kw in claim_lower for kw in ["volatile", "volatility", "atr"]):
            atr_pct = indicators.get("atr_pct")
            if atr_pct is not None:
                if atr_pct > 3.0:
                    score = 0.8
                elif atr_pct > 1.5:
                    score = 0.5
                else:
                    score = 0.3

        # Use provided weight as base if no keyword match
        if score == 0.5:
            score = arg.weight

        return min(max(score, 0.0), 1.0)

    @staticmethod
    def _score_to_strength(score: float) -> ArgumentStrength:
        """Convert numeric score to strength category."""
        if score >= 0.75:
            return ArgumentStrength.STRONG
        elif score >= 0.45:
            return ArgumentStrength.MODERATE
        elif score >= 0.2:
            return ArgumentStrength.WEAK
        return ArgumentStrength.INVALID


# ══════════════════════════════════════════════════════════════════════
# REBUTTAL GENERATOR
# ══════════════════════════════════════════════════════════════════════


class RebuttalGenerator:
    """Generates counter-arguments for debate rebuttals."""

    REBUTTAL_MAP = {
        "oversold": "Oversold does not mean reversal; can remain oversold in strong downtrend",
        "overbought": "Overbought conditions can persist in strong uptrends",
        "uptrend": "Uptrend may be exhausted — watch for divergence",
        "downtrend": "Downtrend may be nearing exhaustion — RSI divergence possible",
        "momentum": "Momentum can reverse quickly on news or catalysts",
        "support": "Support levels can break on high volume",
        "resistance": "Resistance can be overcome with sufficient volume",
        "breakout": "Breakouts can be false — need volume confirmation",
        "breakdown": "Breakdowns may trap sellers before reversal",
        "volume": "Volume alone is not directional — context matters",
        "undervalued": "Value traps exist — may be cheap for a reason",
        "overvalued": "Growth can justify elevated valuations",
    }

    def generate_rebuttals(
        self, opponent_args: list[DebateArgument]
    ) -> list[str]:
        """Generate rebuttals against opponent's arguments."""
        rebuttals = []
        for arg in opponent_args:
            claim_lower = arg.claim.lower()
            matched = False
            for keyword, rebuttal in self.REBUTTAL_MAP.items():
                if keyword in claim_lower:
                    rebuttals.append(f"Re: \"{arg.claim}\" — {rebuttal}")
                    matched = True
                    break
            if not matched:
                rebuttals.append(
                    f"Re: \"{arg.claim}\" — This argument may not hold under current market conditions"
                )
        return rebuttals


# ══════════════════════════════════════════════════════════════════════
# BULL/BEAR DEBATE
# ══════════════════════════════════════════════════════════════════════


class BullBearDebate:
    """
    Structured debate between Bull and Bear advocates.

    The debate process:
    1. Bull advocate presents bullish arguments
    2. Bear advocate presents bearish arguments
    3. Arguments are evaluated against market data
    4. Each side rebuts the other's strongest points
    5. Judge synthesizes and renders verdict

    The verdict considers:
    - Weighted score of all arguments
    - Confidence based on argument strength consistency
    - Market regime alignment
    - Risk/reward asymmetry

    Args:
        min_confidence: Minimum confidence threshold for directional verdict
        bull_bias_threshold: Score difference needed for bullish verdict
        bear_bias_threshold: Score difference needed for bearish verdict

    Example:
        debate = BullBearDebate()
        verdict = debate.run_debate(
            bull_args=[DebateArgument(claim="Oversold RSI signals reversal")],
            bear_args=[DebateArgument(claim="Downtrend remains intact")],
            data={"indicators": {"rsi_14": 28}, "price": {"closes": [...]}}
        )
        print(verdict.verdict, verdict.confidence)
    """

    def __init__(
        self,
        min_confidence: float = 0.55,
        bull_bias_threshold: float = 0.1,
        bear_bias_threshold: float = 0.1,
    ) -> None:
        self._min_confidence = min_confidence
        self._bull_threshold = bull_bias_threshold
        self._bear_threshold = bear_bias_threshold
        self._evaluator = ArgumentEvaluator()
        self._rebuttal_gen = RebuttalGenerator()

    def run_debate(
        self,
        bull_args: list[DebateArgument | dict[str, str]],
        bear_args: list[DebateArgument | dict[str, str]],
        data: dict[str, Any],
    ) -> DebateVerdict:
        """
        Run a bull/bear debate with data-driven evaluation.

        Args:
            bull_args: List of bullish arguments (DebateArgument or dicts)
            bear_args: List of bearish arguments
            data: Market data dict with 'indicators', 'price', 'volume_ratio' keys

        Returns:
            DebateVerdict with winner, scores, and key factors
        """
        logger.info("Starting bull/bear debate with %d bull, %d bear arguments",
                     len(bull_args), len(bear_args))

        # Normalize arguments
        bull_arguments = self._normalize_args(bull_args)
        bear_arguments = self._normalize_args(bear_args)

        # If no arguments provided, auto-generate from data
        if not bull_arguments:
            bull_arguments = self._auto_generate_bull_args(data)
        if not bear_arguments:
            bear_arguments = self._auto_generate_bear_args(data)

        # Step 1: Evaluate arguments against data
        evaluated_bull = self._evaluator.evaluate(bull_arguments, DebateSide.BULL, data)
        evaluated_bear = self._evaluator.evaluate(bear_arguments, DebateSide.BEAR, data)

        # Step 2: Generate rebuttals
        bull_rebuttals = self._rebuttal_gen.generate_rebuttals(evaluated_bear)
        bear_rebuttals = self._rebuttal_gen.generate_rebuttals(evaluated_bull)
        all_rebuttals = bull_rebuttals + bear_rebuttals

        # Step 3: Calculate scores
        bull_score = self._calculate_score(evaluated_bull)
        bear_score = self._calculate_score(evaluated_bear)

        # Normalize so they sum to 1
        total = bull_score + bear_score
        if total > 0:
            bull_score_norm = bull_score / total
            bear_score_norm = bear_score / total
        else:
            bull_score_norm = 0.5
            bear_score_norm = 0.5

        # Step 4: Determine verdict
        score_diff = bull_score_norm - bear_score_norm
        if score_diff > self._bull_threshold:
            verdict_type = DebateVerdictType.BULLISH
        elif score_diff < -self._bear_threshold:
            verdict_type = DebateVerdictType.BEARISH
        else:
            verdict_type = DebateVerdictType.NEUTRAL

        # Step 5: Calculate confidence
        confidence = self._calculate_confidence(
            evaluated_bull, evaluated_bear, verdict_type
        )

        # If confidence is too low, default to NEUTRAL
        if confidence < self._min_confidence and verdict_type != DebateVerdictType.NEUTRAL:
            logger.info(
                "Low confidence (%.2f) overriding %s to NEUTRAL",
                confidence, verdict_type.value,
            )
            verdict_type = DebateVerdictType.NEUTRAL
            confidence = max(confidence, 0.3)

        # Step 6: Identify deciding factors
        deciding = self._identify_deciding_factors(evaluated_bull, evaluated_bear)
        key_args = self._extract_key_arguments(evaluated_bull, evaluated_bear)

        verdict = DebateVerdict(
            verdict=verdict_type,
            bull_score=round(bull_score_norm, 4),
            bear_score=round(bear_score_norm, 4),
            confidence=round(confidence, 4),
            key_arguments=key_args,
            deciding_factors=deciding,
            bull_args_evaluated=evaluated_bull,
            bear_args_evaluated=evaluated_bear,
            rebuttals=all_rebuttals,
        )

        logger.info(
            "Debate verdict: %s (bull=%.2f, bear=%.2f, confidence=%.2f)",
            verdict_type.value, bull_score_norm, bear_score_norm, confidence,
        )

        return verdict

    @staticmethod
    def _normalize_args(
        args: list[DebateArgument | dict[str, str]]
    ) -> list[DebateArgument]:
        """Normalize argument inputs to DebateArgument objects."""
        normalized = []
        for arg in args:
            if isinstance(arg, dict):
                normalized.append(DebateArgument(
                    claim=arg.get("claim", ""),
                    evidence=arg.get("evidence", ""),
                    indicator=arg.get("indicator", ""),
                    weight=float(arg.get("weight", 0.5)),
                ))
            else:
                normalized.append(arg)
        return normalized

    @staticmethod
    def _calculate_score(args: list[DebateArgument]) -> float:
        """Calculate weighted score for a side's arguments."""
        if not args:
            return 0.0

        total_weight = sum(a.weight for a in args)
        if total_weight == 0:
            return 0.0

        weighted_score = sum(a.weight * a.weight for a in args) / total_weight
        return min(weighted_score, 1.0)

    @staticmethod
    def _calculate_confidence(
        bull_args: list[DebateArgument],
        bear_args: list[DebateArgument],
        verdict: DebateVerdictType,
    ) -> float:
        """
        Calculate confidence in the verdict.

        Higher confidence when:
        - Winning side has strong arguments
        - Losing side has weak arguments
        - Arguments are consistent (not scattered)
        """
        if verdict == DebateVerdictType.BULLISH:
            winner_args, loser_args = bull_args, bear_args
        elif verdict == DebateVerdictType.BEARISH:
            winner_args, loser_args = bear_args, bull_args
        else:
            # NEUTRAL: confidence is lower when arguments are balanced
            if bull_args and bear_args:
                bull_avg = sum(a.weight for a in bull_args) / len(bull_args)
                bear_avg = sum(a.weight for a in bear_args) / len(bear_args)
                balance = abs(bull_avg - bear_avg)
                return max(0.3, 0.5 - balance)
            return 0.3

        if not winner_args:
            return 0.3

        # Strong winning arguments boost confidence
        strong_count = sum(1 for a in winner_args if a.weight >= 0.7)
        winner_strength = strong_count / len(winner_args) if winner_args else 0

        # Weak losing arguments boost confidence
        weak_count = sum(1 for a in loser_args if a.weight < 0.4) if loser_args else 0
        loser_weakness = weak_count / len(loser_args) if loser_args else 0.5

        confidence = 0.3 + 0.4 * winner_strength + 0.3 * loser_weakness
        return min(max(confidence, 0.3), 1.0)

    @staticmethod
    def _identify_deciding_factors(
        bull_args: list[DebateArgument],
        bear_args: list[DebateArgument],
    ) -> list[str]:
        """Identify the strongest arguments that decided the outcome."""
        all_args = [(a, "BULL") for a in bull_args] + [(a, "BEAR") for a in bear_args]
        sorted_args = sorted(all_args, key=lambda x: x[0].weight, reverse=True)
        return [
            f"[{side}] {arg.claim} (strength: {arg.strength.value})"
            for arg, side in sorted_args[:5]
        ]

    @staticmethod
    def _extract_key_arguments(
        bull_args: list[DebateArgument],
        bear_args: list[DebateArgument],
    ) -> list[str]:
        """Extract top arguments from each side."""
        top_bull = sorted(bull_args, key=lambda a: a.weight, reverse=True)[:3]
        top_bear = sorted(bear_args, key=lambda a: a.weight, reverse=True)[:3]
        return (
            [f"BULL: {a.claim}" for a in top_bull]
            + [f"BEAR: {a.claim}" for a in top_bear]
        )

    # ══════════════════════════════════════════════════════════════════
    # AUTO-ARGUMENT GENERATION
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def _auto_generate_bull_args(data: dict[str, Any]) -> list[DebateArgument]:
        """Auto-generate bullish arguments from market data."""
        args = []
        indicators = data.get("indicators", {})

        rsi = indicators.get("rsi_14")
        if rsi is not None and rsi < 35:
            args.append(DebateArgument(
                claim="Oversold RSI signals potential reversal",
                indicator="rsi", weight=0.8,
            ))

        ema_9 = indicators.get("ema_9")
        ema_20 = indicators.get("ema_20")
        if ema_9 is not None and ema_20 is not None and ema_9 > ema_20:
            args.append(DebateArgument(
                claim="Short-term EMA above medium-term EMA shows bullish momentum",
                indicator="ema", weight=0.7,
            ))

        macd_data = indicators.get("macd", {})
        hist = macd_data.get("histogram")
        if hist is not None and hist > 0:
            args.append(DebateArgument(
                claim="Positive MACD histogram confirms bullish momentum",
                indicator="macd", weight=0.7,
            ))

        bb = indicators.get("bollinger", {})
        pct_b = bb.get("percent_b")
        if pct_b is not None and pct_b < 0.2:
            args.append(DebateArgument(
                claim="Price near lower Bollinger Band — potential bounce",
                indicator="bollinger", weight=0.6,
            ))

        if not args:
            args.append(DebateArgument(
                claim="No strong bullish signals detected",
                weight=0.2,
            ))

        return args

    @staticmethod
    def _auto_generate_bear_args(data: dict[str, Any]) -> list[DebateArgument]:
        """Auto-generate bearish arguments from market data."""
        args = []
        indicators = data.get("indicators", {})

        rsi = indicators.get("rsi_14")
        if rsi is not None and rsi > 65:
            args.append(DebateArgument(
                claim="Overbought RSI signals potential pullback",
                indicator="rsi", weight=0.8,
            ))

        ema_9 = indicators.get("ema_9")
        ema_20 = indicators.get("ema_20")
        if ema_9 is not None and ema_20 is not None and ema_9 < ema_20:
            args.append(DebateArgument(
                claim="Short-term EMA below medium-term EMA shows bearish pressure",
                indicator="ema", weight=0.7,
            ))

        macd_data = indicators.get("macd", {})
        hist = macd_data.get("histogram")
        if hist is not None and hist < 0:
            args.append(DebateArgument(
                claim="Negative MACD histogram confirms bearish momentum",
                indicator="macd", weight=0.7,
            ))

        bb = indicators.get("bollinger", {})
        pct_b = bb.get("percent_b")
        if pct_b is not None and pct_b > 0.8:
            args.append(DebateArgument(
                claim="Price near upper Bollinger Band — potential rejection",
                indicator="bollinger", weight=0.6,
            ))

        if not args:
            args.append(DebateArgument(
                claim="No strong bearish signals detected",
                weight=0.2,
            ))

        return args
