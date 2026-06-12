"""
Portfolio Agent for Quant Nanggroe AI Trading Framework.

Optimizes portfolio allocation, determines position sizing, and manages
portfolio rebalancing within constitutional risk limits.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

try:
    from langchain_core.language_models import BaseChatModel
except ImportError:
    BaseChatModel = None

from quant_nanggroe.agents.base import BaseAgent
from quant_nanggroe.agents.portfolio.prompts import (
    PORTFOLIO_SYSTEM_PROMPT,
    PORTFOLIO_TASK_TEMPLATE,
)
from quant_nanggroe.agents.portfolio.tools import PORTFOLIO_TOOLS
from quant_nanggroe.agents.registry import AgentRegistry
from quant_nanggroe.agents.state import AgentOutput, AgentRole, AgentState


logger = logging.getLogger(__name__)


@AgentRegistry.register("portfolio", AgentRole.PORTFOLIO)
class PortfolioAgent(BaseAgent):
    """
    Portfolio Agent for portfolio optimization and position sizing.

    Determines optimal allocation, calculates position sizes using
    Kelly criterion and risk budgets, and manages portfolio rebalancing.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        tools: Optional[List] = None,
        system_prompt: Optional[str] = None,
    ) -> None:
        super().__init__(
            name="portfolio",
            role=AgentRole.PORTFOLIO,
            description=(
                "Optimizes portfolio allocation, determines position sizing, "
                "and manages rebalancing within constitutional risk limits."
            ),
            llm=llm,
            tools=tools or PORTFOLIO_TOOLS,
            system_prompt=system_prompt or PORTFOLIO_SYSTEM_PROMPT,
        )

    def run(self, state: AgentState) -> Dict[str, Any]:
        """Execute portfolio optimization."""
        signals = state.get("signals", [])
        risk_verdict = state.get("risk_verdict", "VETOED")

        # If risk vetoed, no portfolio changes
        if risk_verdict != "APPROVED":
            content = "Portfolio optimization skipped: risk assessment did not approve any trades."
            output = self.create_output(content=content, data={}, confidence=0.0)
            return {
                "portfolio_output": content,
                "agent_outputs": {
                    **state.get("agent_outputs", {}),
                    self.name: output.model_dump(),
                },
                "sender": self.name,
            }

        task = PORTFOLIO_TASK_TEMPLATE.format(
            signals=str(signals)[:2000],
            portfolio_state=str(state.get("portfolio_state", {}))[:1500],
            risk_assessment=str(state.get("risk_assessment", {}))[:1000],
            market_data_summary=self._summarize_market_data(state),
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
            data={"signals_processed": len(signals)},
            confidence=0.7,
            tool_calls=tool_calls_made,
        )

        return {
            "portfolio_output": content,
            "agent_outputs": {
                **state.get("agent_outputs", {}),
                self.name: output.model_dump(),
            },
            "sender": self.name,
        }

    def _summarize_market_data(self, state: AgentState) -> str:
        """Summarize market data for the prompt."""
        market_data = state.get("market_data", {})
        if not market_data:
            return "No market data available"
        parts = []
        for symbol, data in market_data.items():
            if isinstance(data, dict):
                parts.append(f"  {symbol}: {data}")
        return "\n".join(parts) if parts else "No detailed data"
