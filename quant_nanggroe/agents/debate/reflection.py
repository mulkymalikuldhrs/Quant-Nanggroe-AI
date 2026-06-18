"""
Debate Reflection, Propagation, and Signal Processing.

Ported from TradingAgents — Reflector analyzes debate quality,
Propagator passes insights between rounds, SignalProcessor
extracts actionable signals from debates.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

try:
    from langchain_core.language_models import BaseChatModel
except ImportError:
    BaseChatModel = None
try:
    from langchain_core.messages import HumanMessage, SystemMessage
except ImportError:
    HumanMessage = SystemMessage = None

logger = logging.getLogger(__name__)


# =============================================================================
# Reflector — Analyzes debate quality and identifies gaps
# =============================================================================

REFLECTOR_SYSTEM_PROMPT = """You are an expert financial analyst tasked with reviewing trading debates and providing comprehensive analysis.

Your goal is to:
1. Identify the strongest arguments from each side
2. Find gaps or weaknesses in reasoning
3. Detect logical fallacies or unsupported claims
4. Assess overall debate quality and completeness
5. Suggest areas that need further investigation

Be specific, data-driven, and concise. Focus on actionable insights."""


class Reflector:
    """
    Handles reflection on debate quality and identifies gaps.

    Analyzes the output of research and risk debates to determine
    what information is missing, what arguments need strengthening,
    and whether the debate has reached sufficient depth.
    """

    def __init__(self, llm: BaseChatModel) -> None:
        self._llm = llm

    def reflect_on_research_debate(
        self,
        bull_history: str,
        bear_history: str,
        judge_decision: str,
    ) -> Dict[str, Any]:
        """
        Reflect on the research debate quality.

        Args:
            bull_history: Bull arguments
            bear_history: Bear arguments
            judge_decision: Judge's decision

        Returns:
            Reflection analysis dictionary
        """
        prompt = f"""Analyze this investment debate for quality and completeness:

BULL ARGUMENTS:
{bull_history[:2000]}

BEAR ARGUMENTS:
{bear_history[:2000]}

JUDGE DECISION:
{judge_decision[:500]}

Provide:
1. Strongest bull argument
2. Strongest bear argument
3. Missing information or gaps
4. Logical fallacies detected
5. Debate quality score (0-1)
6. Areas needing further research"""

        response = self._llm.invoke([
            SystemMessage(content=REFLECTOR_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])

        return {
            "reflection": response.content,
            "debate_type": "research",
            "quality_score": self._estimate_quality(bull_history, bear_history),
        }

    def reflect_on_risk_debate(
        self,
        conservative_history: str,
        neutral_history: str,
        aggressive_history: str,
        judge_decision: str,
    ) -> Dict[str, Any]:
        """
        Reflect on the risk debate quality.

        Args:
            conservative_history: Conservative arguments
            neutral_history: Neutral arguments
            aggressive_history: Aggressive arguments
            judge_decision: Risk judge's decision

        Returns:
            Reflection analysis dictionary
        """
        prompt = f"""Analyze this risk debate for quality and completeness:

CONSERVATIVE ARGUMENTS:
{conservative_history[:1500]}

NEUTRAL ARGUMENTS:
{neutral_history[:1500]}

AGGRESSIVE ARGUMENTS:
{aggressive_history[:1500]}

RISK JUDGE DECISION:
{judge_decision[:500]}

Provide:
1. Strongest conservative point
2. Strongest aggressive point
3. Risk assessment gaps
4. Overlooked risk factors
5. Debate quality score (0-1)
6. Recommended risk adjustments"""

        response = self._llm.invoke([
            SystemMessage(content=REFLECTOR_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])

        return {
            "reflection": response.content,
            "debate_type": "risk",
            "quality_score": self._estimate_quality(
                conservative_history + aggressive_history,
                neutral_history,
            ),
        }

    def _estimate_quality(self, side_a: str, side_b: str) -> float:
        """
        Estimate debate quality based on argument length and presence.

        Args:
            side_a: One side's arguments
            side_b: Other side's arguments

        Returns:
            Quality score between 0 and 1
        """
        score = 0.3  # Base score
        if len(side_a) > 200:
            score += 0.15
        if len(side_b) > 200:
            score += 0.15
        if len(side_a) > 500:
            score += 0.1
        if len(side_b) > 500:
            score += 0.1
        # Both sides present
        if len(side_a) > 100 and len(side_b) > 100:
            score += 0.2
        return min(score, 1.0)


# =============================================================================
# Propagator — Passes insights between debate rounds
# =============================================================================

class Propagator:
    """
    Handles state propagation and insight passing between debate rounds.

    Manages the flow of information from one round to the next,
    ensuring that key insights are preserved and debated arguments
    build upon previous rounds.
    """

    def __init__(self, max_recur_limit: int = 100) -> None:
        self._max_recur_limit = max_recur_limit
        self._propagation_history: List[Dict[str, Any]] = []

    def propagate_research_insights(
        self,
        debate_state: Dict[str, Any],
        reflection: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Propagate research debate insights to the next round.

        Args:
            debate_state: Current debate state
            reflection: Reflection analysis

        Returns:
            Updated state with propagated insights
        """
        propagated = {
            "insights_from_previous_round": reflection.get("reflection", ""),
            "quality_score": reflection.get("quality_score", 0.5),
            "round_number": debate_state.get("count", 0),
        }

        self._propagation_history.append({
            "type": "research",
            "round": debate_state.get("count", 0),
            "quality_score": reflection.get("quality_score", 0.5),
        })

        return propagated

    def propagate_risk_insights(
        self,
        debate_state: Dict[str, Any],
        reflection: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Propagate risk debate insights to the next round.

        Args:
            debate_state: Current debate state
            reflection: Reflection analysis

        Returns:
            Updated state with propagated insights
        """
        propagated = {
            "risk_insights_from_previous_round": reflection.get("reflection", ""),
            "risk_quality_score": reflection.get("quality_score", 0.5),
            "round_number": debate_state.get("count", 0),
        }

        self._propagation_history.append({
            "type": "risk",
            "round": debate_state.get("count", 0),
            "quality_score": reflection.get("quality_score", 0.5),
        })

        return propagated

    def should_continue_debate(
        self,
        current_round: int,
        max_rounds: int,
        quality_score: float,
        quality_threshold: float = 0.7,
    ) -> bool:
        """
        Determine if debate should continue based on quality and rounds.

        Args:
            current_round: Current debate round
            max_rounds: Maximum allowed rounds
            quality_score: Current debate quality score
            quality_threshold: Minimum quality threshold

        Returns:
            True if debate should continue, False if consensus reached
        """
        if current_round >= max_rounds:
            return False
        if quality_score >= quality_threshold:
            return False
        return True

    @property
    def propagation_history(self) -> List[Dict[str, Any]]:
        """Get the history of propagations."""
        return self._propagation_history


# =============================================================================
# SignalProcessor — Extracts actionable signals from debates
# =============================================================================

SIGNAL_PROCESSOR_PROMPT = """You are an efficient assistant designed to analyze financial debate output and extract the core investment decision.

Your task is to extract the investment decision: SELL, BUY, or HOLD.
Provide only the extracted decision (SELL, BUY, or HOLD) as your output, without adding any additional text or information."""


class SignalProcessor:
    """
    Processes debate output to extract actionable trading signals.

    Takes the raw debate output (judge decisions, summaries) and
    extracts clear BUY/SELL/HOLD signals with confidence levels.
    """

    def __init__(self, llm: BaseChatModel) -> None:
        self._llm = llm

    def process_investment_signal(self, judge_decision: str) -> str:
        """
        Process a research debate judge decision into a core signal.

        Args:
            judge_decision: Judge's decision text

        Returns:
            BUY, SELL, or HOLD
        """
        messages = [
            SystemMessage(content=SIGNAL_PROCESSOR_PROMPT),
            HumanMessage(content=judge_decision),
        ]

        result = self._llm.invoke(messages).content.strip().upper()

        # Normalize to valid signals
        for signal in ["BUY", "SELL", "HOLD"]:
            if signal in result:
                return signal

        return "HOLD"  # Default to HOLD if unclear

    def process_risk_signal(self, judge_decision: str) -> Dict[str, Any]:
        """
        Process a risk debate judge decision into a structured signal.

        Args:
            judge_decision: Risk judge's decision text

        Returns:
            Dictionary with risk verdict and conditions
        """
        decision_upper = judge_decision.upper()

        if "APPROVED" in decision_upper:
            verdict = "APPROVED"
        elif "VETOED" in decision_upper:
            verdict = "VETOED"
        else:
            verdict = "CONDITIONAL"

        return {
            "risk_verdict": verdict,
            "raw_decision": judge_decision,
            "conditions": self._extract_conditions(judge_decision),
        }

    def _extract_conditions(self, decision: str) -> List[str]:
        """
        Extract conditions from a risk decision.

        Args:
            decision: Risk judge decision text

        Returns:
            List of condition strings
        """
        conditions = []
        lines = decision.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith(("-", "*", "•")) and len(line) > 2:
                conditions.append(line.lstrip("-*• ").strip())
        return conditions[:5]  # Limit to top 5 conditions
