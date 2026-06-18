"""
Structured Debate Mechanism for Quant Nanggroe AI Trading Framework.

Implements bull vs. bear researchers and conservative/neutral/aggressive
risk debaters, inspired by the TradingAgents multi-debate framework.
The debate produces structured arguments that feed into the voting mechanism.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from langchain_core.language_models import BaseChatModel
except ImportError:
    BaseChatModel = None
try:
    from langchain_core.messages import HumanMessage, SystemMessage
except ImportError:
    HumanMessage = SystemMessage = None

from quant_nanggroe.agents.state import (
    AgentState,
    DebateState,
    RiskDebateState,
)


logger = logging.getLogger(__name__)


# =============================================================================
# Debate Prompts
# =============================================================================

BULL_RESEARCHER_PROMPT = """You are a Bull Researcher advocating for investing. Build a strong, evidence-based case emphasizing growth potential, competitive advantages, and positive market indicators.

Key points to focus on:
- Growth Potential: Market opportunities, revenue projections, scalability
- Competitive Advantages: Unique products, strong branding, dominant positioning
- Positive Indicators: Financial health, industry trends, recent positive news
- Counter-Arguments: Critically analyze the bear argument with specific data

Resources:
Market research: {market_research}
Sentiment: {sentiment_report}
News: {news_report}
Fundamentals: {fundamentals_report}
Conversation history: {history}
Last bear argument: {bear_argument}

Deliver a compelling bull argument. Engage directly with bear points."""

BEAR_RESEARCHER_PROMPT = """You are a Bear Researcher advocating against investing. Build a strong, evidence-based case emphasizing risks, competitive threats, and negative indicators.

Key points to focus on:
- Risk Factors: Market threats, declining metrics, competitive pressures
- Negative Indicators: Weak financials, deteriorating trends, negative news
- Valuation Concerns: Overvaluation, unrealistic expectations, bubble signals
- Counter-Arguments: Critically analyze the bull argument with specific data

Resources:
Market research: {market_research}
Sentiment: {sentiment_report}
News: {news_report}
Fundamentals: {fundamentals_report}
Conversation history: {history}
Last bull argument: {bull_argument}

Deliver a compelling bear argument. Engage directly with bull points."""

INVEST_JUDGE_PROMPT = """You are the Investment Judge. Review the bull and bear debate and render a balanced investment decision.

Bull arguments: {bull_history}
Bear arguments: {bear_history}
Full debate: {history}

Provide:
1. Summary of key bull points
2. Summary of key bear points
3. Your assessment with specific reasoning
4. Final recommendation: BUY, SELL, or HOLD with confidence level

Format: INVESTMENT DECISION: **BUY/HOLD/SELL** (Confidence: X%)"""

CONSERVATIVE_DEBATER_PROMPT = """As the Conservative Risk Analyst, your primary objective is to protect assets and minimize volatility. You prioritize stability, security, and risk mitigation.

Trader's decision: {trader_decision}

Counter the Risky and Neutral Analysts by highlighting potential threats and sustainability concerns.

Market Research: {market_research}
Sentiment: {sentiment_report}
News: {news_report}
Fundamentals: {fundamentals_report}
Current conversation: {history}
Last risky argument: {aggressive_response}
Last neutral argument: {neutral_response}

Focus on why a conservative stance is the safest path."""

NEUTRAL_DEBATER_PROMPT = """As the Neutral Risk Analyst, you provide balanced analysis weighing both risks and rewards. You are the voice of moderation.

Trader's decision: {trader_decision}

Provide balanced assessment addressing both the risky and conservative viewpoints.

Market Research: {market_research}
Sentiment: {sentiment_report}
News: {news_report}
Fundamentals: {fundamentals_report}
Current conversation: {history}
Last conservative argument: {conservative_response}
Last aggressive argument: {aggressive_response}

Provide balanced, moderate analysis."""

AGGRESSIVE_DEBATER_PROMPT = """As the Aggressive Risk Analyst, you advocate for maximizing returns and are comfortable with higher risk for higher reward. You see opportunities where others see danger.

Trader's decision: {trader_decision}

Challenge the Conservative and Neutral Analysts by highlighting missed opportunities and being too cautious.

Market Research: {market_research}
Sentiment: {sentiment_report}
News: {news_report}
Fundamentals: {fundamentals_report}
Current conversation: {history}
Last conservative argument: {conservative_response}
Last neutral argument: {neutral_response}

Argue why the aggressive approach offers the best risk-adjusted returns."""

RISK_JUDGE_PROMPT = """You are the Risk Judge. Review the risk debate between Conservative, Neutral, and Aggressive analysts and make a final risk assessment.

Conservative arguments: {conservative_history}
Neutral arguments: {neutral_history}
Aggressive arguments: {aggressive_history}
Full debate: {history}

Provide:
1. Summary of each position
2. Your balanced risk assessment
3. Final verdict: APPROVED (with conditions) or VETOED
4. Specific risk parameters to enforce

Format: RISK VERDICT: **APPROVED/VETOED**"""


class CouncilDebate:
    """
    Structured debate mechanism for the trading council.

    Implements two debate formats:
    1. Bull vs. Bear researchers for investment analysis
    2. Conservative vs. Neutral vs. Aggressive risk debaters

    Inspired by the TradingAgents multi-debate framework.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        max_debate_rounds: int = 2,
        max_risk_rounds: int = 2,
    ) -> None:
        """
        Initialize the council debate.

        Args:
            llm: Language model for debate participants
            max_debate_rounds: Maximum bull/bear debate rounds
            max_risk_rounds: Maximum risk debate rounds
        """
        self._llm = llm
        self._max_debate_rounds = max_debate_rounds
        self._max_risk_rounds = max_risk_rounds

    def run_investment_debate(self, state: AgentState) -> DebateState:
        """
        Run the bull vs. bear investment debate.

        Args:
            state: Current agent state with research outputs

        Returns:
            Updated DebateState with debate history and judge decision
        """
        debate_state: DebateState = {
            "bull_history": "",
            "bear_history": "",
            "history": "",
            "current_response": "",
            "judge_decision": "",
            "count": 0,
        }

        # Extract research from state
        market_research = state.get("research_output", "No research available")
        macro_analysis = state.get("macro_output", "")
        sentiment_report = state.get("agent_outputs", {}).get("researcher", {}).get("content", "")
        news_report = state.get("agent_outputs", {}).get("researcher", {}).get("content", "")
        fundamentals_report = state.get("agent_outputs", {}).get("researcher", {}).get("content", "")

        # Run debate rounds
        for round_num in range(self._max_debate_rounds):
            # Bull argues
            bull_prompt = BULL_RESEARCHER_PROMPT.format(
                market_research=market_research[:1500],
                sentiment_report=sentiment_report[:500],
                news_report=news_report[:500],
                fundamentals_report=fundamentals_report[:500],
                history=debate_state["history"][:2000],
                bear_argument=debate_state["current_response"][:500],
            )

            bull_response = self._llm.invoke([HumanMessage(content=bull_prompt)])
            bull_argument = f"Bull Analyst: {bull_response.content}"

            debate_state["bull_history"] += "\n" + bull_argument
            debate_state["history"] += "\n" + bull_argument
            debate_state["current_response"] = bull_argument
            debate_state["count"] += 1

            # Bear argues
            bear_prompt = BEAR_RESEARCHER_PROMPT.format(
                market_research=market_research[:1500],
                sentiment_report=sentiment_report[:500],
                news_report=news_report[:500],
                fundamentals_report=fundamentals_report[:500],
                history=debate_state["history"][:2000],
                bull_argument=debate_state["current_response"][:500],
            )

            bear_response = self._llm.invoke([HumanMessage(content=bear_prompt)])
            bear_argument = f"Bear Analyst: {bear_response.content}"

            debate_state["bear_history"] += "\n" + bear_argument
            debate_state["history"] += "\n" + bear_argument
            debate_state["current_response"] = bear_argument
            debate_state["count"] += 1

        # Judge decision
        judge_prompt = INVEST_JUDGE_PROMPT.format(
            bull_history=debate_state["bull_history"][:2000],
            bear_history=debate_state["bear_history"][:2000],
            history=debate_state["history"][:3000],
        )

        judge_response = self._llm.invoke([HumanMessage(content=judge_prompt)])
        debate_state["judge_decision"] = judge_response.content

        logger.info(
            f"Investment debate completed: {debate_state['count']} exchanges, "
            f"judge decision rendered"
        )

        return debate_state

    def run_risk_debate(self, state: AgentState) -> RiskDebateState:
        """
        Run the conservative/neutral/aggressive risk debate.

        Args:
            state: Current agent state with trader decision

        Returns:
            Updated RiskDebateState with debate history and judge decision
        """
        risk_state: RiskDebateState = {
            "conservative_history": "",
            "neutral_history": "",
            "aggressive_history": "",
            "history": "",
            "latest_speaker": "",
            "current_conservative_response": "",
            "current_neutral_response": "",
            "current_aggressive_response": "",
            "judge_decision": "",
            "count": 0,
        }

        # Extract trader decision and research
        trader_decision = state.get("trader_output", "No trader decision available")
        market_research = state.get("research_output", "")
        sentiment_report = state.get("agent_outputs", {}).get("researcher", {}).get("content", "")
        news_report = state.get("agent_outputs", {}).get("researcher", {}).get("content", "")
        fundamentals_report = state.get("agent_outputs", {}).get("researcher", {}).get("content", "")

        # Run risk debate rounds
        for round_num in range(self._max_risk_rounds):
            # Conservative argues
            cons_prompt = CONSERVATIVE_DEBATER_PROMPT.format(
                trader_decision=trader_decision[:1000],
                market_research=market_research[:1000],
                sentiment_report=sentiment_report[:300],
                news_report=news_report[:300],
                fundamentals_report=fundamentals_report[:300],
                history=risk_state["history"][:2000],
                aggressive_response=risk_state["current_aggressive_response"][:500],
                neutral_response=risk_state["current_neutral_response"][:500],
            )

            cons_response = self._llm.invoke([HumanMessage(content=cons_prompt)])
            cons_argument = f"Conservative Analyst: {cons_response.content}"

            risk_state["conservative_history"] += "\n" + cons_argument
            risk_state["history"] += "\n" + cons_argument
            risk_state["current_conservative_response"] = cons_argument
            risk_state["latest_speaker"] = "Conservative"
            risk_state["count"] += 1

            # Neutral argues
            neutral_prompt = NEUTRAL_DEBATER_PROMPT.format(
                trader_decision=trader_decision[:1000],
                market_research=market_research[:1000],
                sentiment_report=sentiment_report[:300],
                news_report=news_report[:300],
                fundamentals_report=fundamentals_report[:300],
                history=risk_state["history"][:2000],
                conservative_response=risk_state["current_conservative_response"][:500],
                aggressive_response=risk_state["current_aggressive_response"][:500],
            )

            neutral_response = self._llm.invoke([HumanMessage(content=neutral_prompt)])
            neutral_argument = f"Neutral Analyst: {neutral_response.content}"

            risk_state["neutral_history"] += "\n" + neutral_argument
            risk_state["history"] += "\n" + neutral_argument
            risk_state["current_neutral_response"] = neutral_argument
            risk_state["latest_speaker"] = "Neutral"
            risk_state["count"] += 1

            # Aggressive argues
            aggr_prompt = AGGRESSIVE_DEBATER_PROMPT.format(
                trader_decision=trader_decision[:1000],
                market_research=market_research[:1000],
                sentiment_report=sentiment_report[:300],
                news_report=news_report[:300],
                fundamentals_report=fundamentals_report[:300],
                history=risk_state["history"][:2000],
                conservative_response=risk_state["current_conservative_response"][:500],
                neutral_response=risk_state["current_neutral_response"][:500],
            )

            aggr_response = self._llm.invoke([HumanMessage(content=aggr_prompt)])
            aggr_argument = f"Aggressive Analyst: {aggr_response.content}"

            risk_state["aggressive_history"] += "\n" + aggr_argument
            risk_state["history"] += "\n" + aggr_argument
            risk_state["current_aggressive_response"] = aggr_argument
            risk_state["latest_speaker"] = "Aggressive"
            risk_state["count"] += 1

        # Risk judge decision
        judge_prompt = RISK_JUDGE_PROMPT.format(
            conservative_history=risk_state["conservative_history"][:2000],
            neutral_history=risk_state["neutral_history"][:2000],
            aggressive_history=risk_state["aggressive_history"][:2000],
            history=risk_state["history"][:3000],
        )

        judge_response = self._llm.invoke([HumanMessage(content=judge_prompt)])
        risk_state["judge_decision"] = judge_response.content

        logger.info(
            f"Risk debate completed: {risk_state['count']} exchanges, "
            f"risk judge decision rendered"
        )

        return risk_state

    def run_full_debate(self, state: AgentState) -> Dict[str, Any]:
        """
        Run both investment and risk debates.

        Args:
            state: Current agent state

        Returns:
            Dictionary with both debate results
        """
        investment_debate = self.run_investment_debate(state)
        risk_debate = self.run_risk_debate(state)

        return {
            "investment_debate": investment_debate,
            "risk_debate": risk_debate,
            "debate_state": {
                **state.get("debate_state", {}),
                "investment_debate": investment_debate,
                "risk_debate": risk_debate,
            },
        }
