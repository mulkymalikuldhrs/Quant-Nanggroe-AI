"""
Crypto Agent for Quant Nanggroe AI Trading Framework.

Provides specialized cryptocurrency analysis including on-chain data,
DEX monitoring, and smart contract risk assessment.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

try:
    from langchain_core.language_models import BaseChatModel
except ImportError:
    BaseChatModel = None

from quant_nanggroe.agents.base import BaseAgent
from quant_nanggroe.agents.crypto.prompts import CRYPTO_SYSTEM_PROMPT, CRYPTO_TASK_TEMPLATE
from quant_nanggroe.agents.crypto.tools import CRYPTO_TOOLS
from quant_nanggroe.agents.registry import AgentRegistry
from quant_nanggroe.agents.state import AgentOutput, AgentRole, AgentState


logger = logging.getLogger(__name__)


@AgentRegistry.register("crypto", AgentRole.CRYPTO)
class CryptoAgent(BaseAgent):
    """
    Crypto Agent for specialized cryptocurrency analysis.

    Analyzes on-chain data, DEX activity, smart contract risks,
    and crypto-specific indicators to provide trading signals.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        tools: Optional[List] = None,
        system_prompt: Optional[str] = None,
    ) -> None:
        super().__init__(
            name="crypto",
            role=AgentRole.CRYPTO,
            description=(
                "Specialized crypto analysis including on-chain data, "
                "DEX monitoring, and smart contract risk assessment."
            ),
            llm=llm,
            tools=tools or CRYPTO_TOOLS,
            system_prompt=system_prompt or CRYPTO_SYSTEM_PROMPT,
        )

    def run(self, state: AgentState) -> Dict[str, Any]:
        """Execute crypto analysis."""
        symbols = state.get("symbols", [])

        task = CRYPTO_TASK_TEMPLATE.format(
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
            confidence=0.65,
            tool_calls=tool_calls_made,
        )

        return {
            "crypto_output": content,
            "agent_outputs": {
                **state.get("agent_outputs", {}),
                self.name: output.model_dump(),
            },
            "sender": self.name,
        }
