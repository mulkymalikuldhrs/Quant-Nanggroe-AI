"""
Research Agent for Quant Nanggroe AI Trading Framework.

Performs deep financial research using web search, SEC filings,
news analysis, and financial data retrieval. Generates comprehensive
research reports that feed into the Strategist agent.
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

from quant_nanggroe.agents.base import BaseAgent
from quant_nanggroe.agents.researcher.prompts import (
    RESEARCHER_SYSTEM_PROMPT,
    RESEARCHER_TASK_TEMPLATE,
)
from quant_nanggroe.agents.researcher.tools import RESEARCH_TOOLS
from quant_nanggroe.agents.registry import AgentRegistry
from quant_nanggroe.agents.state import AgentOutput, AgentRole, AgentState


logger = logging.getLogger(__name__)


@AgentRegistry.register("researcher", AgentRole.RESEARCHER)
class ResearcherAgent(BaseAgent):
    """
    Research Agent that conducts deep financial research.

    Uses web search, SEC filings, news analysis, and financial data
    to produce comprehensive research reports on requested symbols.
    These reports feed into the Strategist agent for signal generation.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        tools: Optional[List] = None,
        system_prompt: Optional[str] = None,
    ) -> None:
        """
        Initialize the Researcher Agent.

        Args:
            llm: Language model instance
            tools: Optional list of tools (defaults to research tools)
            system_prompt: Optional custom system prompt
        """
        super().__init__(
            name="researcher",
            role=AgentRole.RESEARCHER,
            description=(
                "Conducts deep financial research using web search, SEC filings, "
                "news analysis, and financial data. Produces comprehensive research "
                "reports for the trading pipeline."
            ),
            llm=llm,
            tools=tools or RESEARCH_TOOLS,
            system_prompt=system_prompt or RESEARCHER_SYSTEM_PROMPT,
        )

    def run(self, state: AgentState) -> Dict[str, Any]:
        """
        Execute research on the requested symbols.

        Gathers information from multiple sources using available tools,
        then synthesizes findings into a structured research report.

        Args:
            state: Current agent state

        Returns:
            Dictionary with research_output and updated agent_outputs
        """
        symbols = state.get("symbols", [])
        trade_date = state.get("trade_date", "")

        # Build the research task
        task = RESEARCHER_TASK_TEMPLATE.format(
            symbols=", ".join(symbols),
            trade_date=trade_date,
            additional_context=self._build_additional_context(state),
        )

        # Build messages
        messages = self.build_messages(state, user_content=task)

        # Invoke LLM with tools
        response = self.invoke_llm(messages, use_tools=True)

        # Handle tool calls if present
        content = response.content
        tool_calls_made = []

        if hasattr(response, "tool_calls") and response.tool_calls:
            # Process tool calls through the tool node
            for tc in response.tool_calls:
                tool_calls_made.append({
                    "name": tc.get("name", ""),
                    "args": tc.get("args", {}),
                })
                # Execute tool and add result to context
                try:
                    tool_result = self._execute_tool(tc)
                    messages.append(HumanMessage(
                        content=f"Tool result for {tc.get('name', '')}: {tool_result}"
                    ))
                except Exception as e:
                    logger.warning(f"Tool execution failed: {e}")

            # Get final synthesis after tool results
            final_response = self.invoke_llm(messages, use_tools=False)
            content = final_response.content

        # Calculate confidence based on research completeness
        confidence = self._assess_confidence(content, symbols)

        # Create structured output
        output = self.create_output(
            content=content,
            data={
                "symbols_researched": symbols,
                "tools_used": [tc["name"] for tc in tool_calls_made],
                "trade_date": trade_date,
            },
            confidence=confidence,
            tool_calls=tool_calls_made,
        )

        return {
            "research_output": content,
            "agent_outputs": {
                **state.get("agent_outputs", {}),
                self.name: output.model_dump(),
            },
            "sender": self.name,
        }

    def _execute_tool(self, tool_call: Dict[str, Any]) -> str:
        """
        Execute a single tool call.

        Args:
            tool_call: Tool call dictionary with 'name' and 'args'

        Returns:
            Tool execution result as string
        """
        tool_name = tool_call.get("name", "")
        tool_args = tool_call.get("args", {})

        # Find and execute the matching tool
        for t in self.tools:
            if t.name == tool_name:
                return str(t.invoke(tool_args))

        return f"Tool '{tool_name}' not found"

    def _build_additional_context(self, state: AgentState) -> str:
        """
        Build additional context string from existing state.

        Args:
            state: Current agent state

        Returns:
            Additional context string
        """
        parts = []

        # Add previous research if available
        existing_research = state.get("agent_outputs", {}).get(self.name, {})
        if existing_research:
            prev_content = existing_research.get("content", "")
            if prev_content:
                parts.append(f"Previous research (for reference):\n{prev_content[:1000]}")

        # Add any market data already available
        market_data = state.get("market_data", {})
        if market_data:
            parts.append(f"Available market data symbols: {list(market_data.keys())}")

        return "\n\n".join(parts) if parts else ""

    def _assess_confidence(self, content: str, symbols: List[str]) -> float:
        """
        Assess the confidence level of the research output.

        Args:
            content: Research output content
            symbols: Symbols that were researched

        Returns:
            Confidence level between 0.0 and 1.0
        """
        confidence = 0.5  # Base confidence

        # Increase confidence for each symbol covered
        for symbol in symbols:
            if symbol.upper() in content.upper():
                confidence += 0.1

        # Increase confidence for key analysis terms
        key_terms = ["revenue", "earnings", "growth", "risk", "valuation", "margin"]
        for term in key_terms:
            if term.lower() in content.lower():
                confidence += 0.02

        # Cap at 1.0
        return min(confidence, 1.0)
