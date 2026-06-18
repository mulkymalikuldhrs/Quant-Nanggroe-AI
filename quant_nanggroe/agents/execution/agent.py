"""
Execution Agent for Quant Nanggroe AI Trading Framework.

Handles smart order routing, order management, and fill tracking.
Ensures best execution quality and monitors slippage.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

try:
    from langchain_core.language_models import BaseChatModel
except ImportError:
    BaseChatModel = None

from quant_nanggroe.agents.base import BaseAgent
from quant_nanggroe.agents.execution.prompts import (
    EXECUTION_SYSTEM_PROMPT,
    EXECUTION_TASK_TEMPLATE,
)
from quant_nanggroe.agents.execution.tools import EXECUTION_TOOLS
from quant_nanggroe.agents.registry import AgentRegistry
from quant_nanggroe.agents.state import AgentOutput, AgentRole, AgentState, TradeAction


logger = logging.getLogger(__name__)


@AgentRegistry.register("execution", AgentRole.EXECUTION)
class ExecutionAgent(BaseAgent):
    """
    Execution Agent for order routing and management.

    Handles smart order routing, order submission, cancellation,
    and fill tracking. Monitors execution quality and slippage.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        tools: Optional[List] = None,
        system_prompt: Optional[str] = None,
    ) -> None:
        super().__init__(
            name="execution",
            role=AgentRole.EXECUTION,
            description=(
                "Handles smart order routing, order management, and fill tracking. "
                "Ensures best execution quality and monitors slippage."
            ),
            llm=llm,
            tools=tools or EXECUTION_TOOLS,
            system_prompt=system_prompt or EXECUTION_SYSTEM_PROMPT,
        )

    def run(self, state: AgentState) -> Dict[str, Any]:
        """Execute trading decisions as orders."""
        decisions = state.get("decisions", [])

        # Filter out non-actionable decisions
        actionable = [
            d for d in decisions
            if isinstance(d, dict) and d.get("action") in (
                TradeAction.BUY.value, TradeAction.SELL.value, TradeAction.CLOSE.value
            )
        ]

        if not actionable:
            content = "No actionable trades to execute. All decisions are HOLD or VETOED."
            output = self.create_output(content=content, data={}, confidence=1.0)
            return {
                "execution_output": content,
                "orders_placed": [],
                "agent_outputs": {
                    **state.get("agent_outputs", {}),
                    self.name: output.model_dump(),
                },
                "sender": self.name,
            }

        task = EXECUTION_TASK_TEMPLATE.format(
            decisions=str(actionable)[:2000],
            portfolio_state=str(state.get("portfolio_state", {}))[:1000],
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

        # Build orders placed list
        orders_placed = []
        for decision in actionable:
            orders_placed.append({
                "symbol": decision.get("symbol", ""),
                "action": decision.get("action", ""),
                "quantity": decision.get("quantity", 0),
                "status": "SUBMITTED",
                "timestamp": datetime.now().isoformat(),
            })

        output = self.create_output(
            content=content,
            data={"orders_placed": len(orders_placed)},
            confidence=0.8,
            tool_calls=tool_calls_made,
        )

        return {
            "execution_output": content,
            "orders_placed": orders_placed,
            "agent_outputs": {
                **state.get("agent_outputs", {}),
                self.name: output.model_dump(),
            },
            "sender": self.name,
        }

    def _summarize_market_data(self, state: AgentState) -> str:
        """Summarize market data."""
        market_data = state.get("market_data", {})
        if not market_data:
            return "No market data available"
        return str(market_data)[:1000]
