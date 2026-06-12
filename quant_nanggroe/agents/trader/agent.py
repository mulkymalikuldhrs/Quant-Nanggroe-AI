"""
Trader Agent for Quant Nanggroe AI Trading Framework.

Makes final trading decisions based on comprehensive analysis from
all other agents. Synthesizes research, signals, risk assessment,
and portfolio state into actionable trade decisions.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

try:
    from langchain_core.language_models import BaseChatModel
except ImportError:
    BaseChatModel = None

from quant_nanggroe.agents.base import BaseAgent
from quant_nanggroe.agents.trader.prompts import (
    TRADER_SYSTEM_PROMPT,
    TRADER_TASK_TEMPLATE,
)
from quant_nanggroe.agents.trader.tools import TRADER_TOOLS
from quant_nanggroe.agents.registry import AgentRegistry
from quant_nanggroe.agents.state import AgentOutput, AgentRole, AgentState, TradeAction


logger = logging.getLogger(__name__)


@AgentRegistry.register("trader", AgentRole.TRADER)
class TraderAgent(BaseAgent):
    """
    Trader Agent that makes final trading decisions.

    Synthesizes all agent outputs into a final BUY/SELL/HOLD decision
    with precise entry, stop-loss, and take-profit levels. Respects
    risk verdicts and kill switch status unconditionally.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        tools: Optional[List] = None,
        system_prompt: Optional[str] = None,
    ) -> None:
        """
        Initialize the Trader Agent.

        Args:
            llm: Language model instance
            tools: Optional list of tools (defaults to trader tools)
            system_prompt: Optional custom system prompt
        """
        super().__init__(
            name="trader",
            role=AgentRole.TRADER,
            description=(
                "Makes final trading decisions based on comprehensive analysis "
                "from all agents. Synthesizes research, signals, risk assessment, "
                "and portfolio state into actionable trade decisions."
            ),
            llm=llm,
            tools=tools or TRADER_TOOLS,
            system_prompt=system_prompt or TRADER_SYSTEM_PROMPT,
        )

    def run(self, state: AgentState) -> Dict[str, Any]:
        """
        Execute the trading decision process.

        Args:
            state: Current agent state

        Returns:
            Dictionary with decisions, trader_output, and updated agent_outputs
        """
        # Check kill switch first - NO OVERRIDE
        if state.get("kill_switch_active", False):
            return self._emergency_exit(state)

        # Check risk verdict
        risk_verdict = state.get("risk_verdict", "VETOED")
        if risk_verdict in ("VETOED", "KILL_SWITCH"):
            return self._vetoed_decision(state, risk_verdict)

        # Build task with all agent outputs
        task = TRADER_TASK_TEMPLATE.format(
            symbols=", ".join(state.get("symbols", [])),
            research_output=state.get("research_output", "No research available")[:2000],
            macro_output=state.get("macro_output", "No macro analysis available")[:1000],
            strategist_output=state.get("strategist_output", "No strategy available")[:2000],
            risk_assessment=str(state.get("risk_assessment", {}))[:1000],
            risk_verdict=risk_verdict,
            portfolio_output=state.get("portfolio_output", "No portfolio info available")[:1000],
            kill_switch_active=state.get("kill_switch_active", False),
            confidence=state.get("confidence", 0.0),
        )

        # Invoke LLM
        messages = self.build_messages(state, user_content=task)
        response = self.invoke_llm(messages, use_tools=True)
        content = response.content

        # Handle tool calls
        tool_calls_made = []
        if hasattr(response, "tool_calls") and response.tool_calls:
            for tc in response.tool_calls:
                tool_calls_made.append({
                    "name": tc.get("name", ""),
                    "args": tc.get("args", {}),
                })

        # Parse the trading decision
        decisions = self._parse_decisions(content, state)
        confidence = self._extract_confidence(content)

        output = self.create_output(
            content=content,
            data={
                "decisions": [d if isinstance(d, dict) else str(d) for d in decisions],
                "risk_verdict": risk_verdict,
                "kill_switch_active": state.get("kill_switch_active", False),
            },
            confidence=confidence,
            tool_calls=tool_calls_made,
        )

        return {
            "decisions": [d if isinstance(d, dict) else str(d) for d in decisions],
            "trader_output": content,
            "agent_outputs": {
                **state.get("agent_outputs", {}),
                self.name: output.model_dump(),
            },
            "confidence": confidence,
            "sender": self.name,
        }

    def _emergency_exit(self, state: AgentState) -> Dict[str, Any]:
        """
        Handle emergency exit when kill switch is active.

        Args:
            state: Current agent state

        Returns:
            State updates with emergency exit decision
        """
        content = (
            "EMERGENCY EXIT: Kill switch is active. All positions must be closed immediately. "
            "No new trades allowed until kill switch is manually reset after review."
        )
        decisions = []
        for symbol in state.get("symbols", []):
            decisions.append({
                "symbol": symbol,
                "action": TradeAction.EMERGENCY_EXIT.value,
                "quantity": 0,
                "reasoning": "Kill switch active - emergency exit required",
                "confidence": 1.0,
            })

        output = self.create_output(
            content=content,
            data={"decisions": decisions, "emergency": True},
            confidence=1.0,
        )

        return {
            "decisions": decisions,
            "trader_output": content,
            "agent_outputs": {
                **state.get("agent_outputs", {}),
                self.name: output.model_dump(),
            },
            "should_halt": True,
            "sender": self.name,
        }

    def _vetoed_decision(self, state: AgentState, risk_verdict: str) -> Dict[str, Any]:
        """
        Handle vetoed risk assessment.

        Args:
            state: Current agent state
            risk_verdict: The risk verdict that caused the veto

        Returns:
            State updates with HOLD decision
        """
        content = (
            f"TRADE VETOED: Risk assessment returned {risk_verdict}. "
            f"No trade will be executed. Capital preservation prioritized. "
            f"Review risk assessment for details on which checkpoints failed."
        )
        decisions = []
        for symbol in state.get("symbols", []):
            decisions.append({
                "symbol": symbol,
                "action": TradeAction.HOLD.value,
                "quantity": 0,
                "reasoning": f"Risk assessment {risk_verdict}",
                "confidence": 0.0,
            })

        output = self.create_output(
            content=content,
            data={"decisions": decisions, "risk_verdict": risk_verdict},
            confidence=0.0,
        )

        return {
            "decisions": decisions,
            "trader_output": content,
            "agent_outputs": {
                **state.get("agent_outputs", {}),
                self.name: output.model_dump(),
            },
            "should_halt": True,
            "sender": self.name,
        }

    def _parse_decisions(self, content: str, state: AgentState) -> List[Dict[str, Any]]:
        """
        Parse trading decisions from the LLM output.

        Args:
            content: LLM output content
            state: Current agent state

        Returns:
            List of decision dictionaries
        """
        decisions = []
        symbols = state.get("symbols", [])

        # Extract action from content
        action = TradeAction.HOLD.value
        action_patterns = [
            (r"FINAL TRANSACTION PROPOSAL:\s*\*\*(\w+)\*\*", TradeAction),
            (r"Action:\s*(BUY|SELL|HOLD|CLOSE|EMERGENCY_EXIT)", None),
            (r"\b(BUY|SELL|HOLD)\b", None),
        ]

        for pattern, enum_cls in action_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                found_action = match.group(1).upper()
                if enum_cls:
                    try:
                        action = enum_cls(found_action).value
                    except ValueError:
                        action = found_action
                else:
                    action = found_action
                break

        # Build decisions for each symbol
        for symbol in symbols:
            decisions.append({
                "symbol": symbol,
                "action": action,
                "confidence": self._extract_confidence(content),
            })

        return decisions if decisions else [{"action": action, "confidence": 0.0}]

    def _extract_confidence(self, content: str) -> float:
        """
        Extract confidence level from content.

        Args:
            content: LLM output content

        Returns:
            Confidence level between 0.0 and 1.0
        """
        match = re.search(r"confidence[:\s]+([0-9]*\.?[0-9]+)", content, re.IGNORECASE)
        if match:
            try:
                conf = float(match.group(1))
                return min(max(conf, 0.0), 1.0)
            except ValueError:
                pass
        return 0.5
