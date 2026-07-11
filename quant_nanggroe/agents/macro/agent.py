"""
Macro Agent for Quant Nanggroe AI Trading Framework.

Analyzes macroeconomic conditions, detects market regimes, and assesses
intermarket relationships. Provides regime-aware context for trading decisions.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

try:
    from langchain_core.language_models import BaseChatModel
except ImportError:
    BaseChatModel = None

from quant_nanggroe.agents.base import BaseAgent
from quant_nanggroe.agents.macro.prompts import MACRO_SYSTEM_PROMPT, MACRO_TASK_TEMPLATE
from quant_nanggroe.agents.macro.tools import MACRO_TOOLS
from quant_nanggroe.agents.registry import AgentRegistry
from quant_nanggroe.agents.state import AgentRole, AgentState

logger = logging.getLogger(__name__)


@AgentRegistry.register("macro", AgentRole.MACRO)
class MacroAgent(BaseAgent):
    """
    Macro Agent for macroeconomic analysis and regime detection.

    Analyzes GDP, inflation, employment, monetary policy, and intermarket
    correlations to classify the current market regime and assess its
    impact on trading decisions.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        tools: Optional[List] = None,
        system_prompt: Optional[str] = None,
    ) -> None:
        super().__init__(
            name="macro",
            role=AgentRole.MACRO,
            description=(
                "Analyzes macroeconomic conditions, detects market regimes, "
                "and assesses intermarket relationships for trading context."
            ),
            llm=llm,
            tools=tools or MACRO_TOOLS,
            system_prompt=system_prompt or MACRO_SYSTEM_PROMPT,
        )

    def run(self, state: AgentState) -> Dict[str, Any]:
        """Execute macroeconomic analysis."""
        symbols = state.get("symbols", [])
        trade_date = state.get("trade_date", "")

        task = MACRO_TASK_TEMPLATE.format(
            symbols=", ".join(symbols),
            trade_date=trade_date,
            research_output=state.get("research_output", "")[:1500],
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
            "macro_output": content,
            "agent_outputs": {
                **state.get("agent_outputs", {}),
                self.name: output.model_dump(),
            },
            "sender": self.name,
        }
