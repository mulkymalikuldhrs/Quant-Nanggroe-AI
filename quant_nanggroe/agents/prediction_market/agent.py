"""Prediction Market Agent for Quant Nanggroe AI Trading Framework.

Provides specialized analysis of prediction markets (Polymarket, Kalshi),
event contract pricing, probability estimation, and Kelly-optimal
position sizing for outcome-based trading instruments.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from langchain_core.language_models import BaseChatModel

from quant_nanggroe.agents.base import BaseAgent
from quant_nanggroe.agents.prediction_market.prompts import (
    PREDICTION_MARKET_SYSTEM_PROMPT,
    PREDICTION_MARKET_TASK_TEMPLATE,
)
from quant_nanggroe.agents.prediction_market.tools import PREDICTION_MARKET_TOOLS
from quant_nanggroe.agents.registry import AgentRegistry
from quant_nanggroe.agents.state import AgentOutput, AgentRole, AgentState


logger = logging.getLogger(__name__)


@AgentRegistry.register("prediction_market", AgentRole.PREDICTION_MARKET)
class PredictionMarketAgent(BaseAgent):
    """
    Prediction Market Agent for specialized event contract analysis.

    Analyzes prediction markets, calculates implied probabilities,
    detects mispricing opportunities, computes Kelly-optimal stakes,
    and assesses resolution risk. Requires human approval for all trades.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        tools: Optional[List] = None,
        system_prompt: Optional[str] = None,
    ) -> None:
        super().__init__(
            name="prediction_market",
            role=AgentRole.PREDICTION_MARKET,
            description=(
                "Specialized prediction market analysis including Polymarket integration, "
                "probability estimation, Kelly criterion sizing, and resolution risk assessment."
            ),
            llm=llm,
            tools=tools or PREDICTION_MARKET_TOOLS,
            system_prompt=system_prompt or PREDICTION_MARKET_SYSTEM_PROMPT,
        )

    def run(self, state: AgentState) -> Dict[str, Any]:
        """Execute prediction market analysis."""
        symbols = state.get("symbols", [])

        task = PREDICTION_MARKET_TASK_TEMPLATE.format(
            symbols=", ".join(symbols),
            trade_date=state.get("trade_date", ""),
            research_output=state.get("research_output", "")[:1500],
            macro_output=state.get("macro_output", "")[:1000],
        )

        messages = self.build_messages(state, user_content=task)
        response = self.invoke_llm(messages, use_tools=True)
        content = response.content

        tool_calls_made = []
        if hasattr(response, "tool_calls") and response.tool_calls:
            for tc in response.tool_calls:
                tool_calls_made.append({"name": tc.get("name", ""), "args": tc.get("args", {})})
            final_response = self.invoke_llm(messages, use_tools=False)
            content = final_response.content

        output = self.create_output(
            content=content,
            data={
                "symbols_analyzed": symbols,
                "requires_human_approval": True,
                "market_type": "prediction_market",
            },
            confidence=0.55,
            tool_calls=tool_calls_made,
        )

        return {
            "prediction_market_output": content,
            "agent_outputs": {
                **state.get("agent_outputs", {}),
                self.name: output.model_dump(),
            },
            "sender": self.name,
        }
