"""
Forex Agent for Quant Nanggroe AI Trading Framework.

Analyzes currency markets, central bank policies, and carry trade
opportunities. Provides forex-specific signals and cross-currency
impact assessment.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

try:
    from langchain_core.language_models import BaseChatModel
except ImportError:
    BaseChatModel = None

from quant_nanggroe.agents.base import BaseAgent
from quant_nanggroe.agents.forex.prompts import FOREX_SYSTEM_PROMPT, FOREX_TASK_TEMPLATE
from quant_nanggroe.agents.forex.tools import FOREX_TOOLS
from quant_nanggroe.agents.registry import AgentRegistry
from quant_nanggroe.agents.state import AgentRole, AgentState

logger = logging.getLogger(__name__)


@AgentRegistry.register("forex", AgentRole.FOREX)
class ForexAgent(BaseAgent):
    """
    Forex Agent for currency market analysis.

    Analyzes currency pairs, central bank policies, carry trade
    opportunities, and cross-currency dynamics.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        tools: Optional[List] = None,
        system_prompt: Optional[str] = None,
    ) -> None:
        super().__init__(
            name="forex",
            role=AgentRole.FOREX,
            description=(
                "Analyzes currency markets, central bank policies, "
                "and carry trade opportunities."
            ),
            llm=llm,
            tools=tools or FOREX_TOOLS,
            system_prompt=system_prompt or FOREX_SYSTEM_PROMPT,
        )

    def run(self, state: AgentState) -> Dict[str, Any]:
        """Execute forex analysis."""
        symbols = state.get("symbols", [])

        task = FOREX_TASK_TEMPLATE.format(
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
            data={"symbols_analyzed": symbols},
            confidence=0.7,
            tool_calls=tool_calls_made,
        )

        return {
            "forex_output": content,
            "agent_outputs": {
                **state.get("agent_outputs", {}),
                self.name: output.model_dump(),
            },
            "sender": self.name,
        }
