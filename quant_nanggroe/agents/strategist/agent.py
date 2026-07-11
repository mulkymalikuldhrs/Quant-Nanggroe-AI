"""
Strategist Agent for Quant Nanggroe AI Trading Framework.

Generates trading signals by combining technical, fundamental, and
sentiment analysis from multiple agents. Produces structured signals
with entry, stop-loss, and take-profit levels.
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
from quant_nanggroe.agents.registry import AgentRegistry
from quant_nanggroe.agents.state import AgentRole, AgentState, SignalDirection, TradeAction
from quant_nanggroe.agents.strategist.prompts import (
    STRATEGIST_SYSTEM_PROMPT,
    STRATEGIST_TASK_TEMPLATE,
)
from quant_nanggroe.agents.strategist.tools import STRATEGIST_TOOLS

logger = logging.getLogger(__name__)


@AgentRegistry.register("strategist", AgentRole.STRATEGIST)
class StrategistAgent(BaseAgent):
    """
    Strategist Agent that generates trading signals.

    Combines analysis from researcher, macro, crypto, and forex agents
    into structured trading signals with proper risk management levels.
    Uses multi-factor weighting to determine signal strength.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        tools: Optional[List] = None,
        system_prompt: Optional[str] = None,
    ) -> None:
        super().__init__(
            name="strategist",
            role=AgentRole.STRATEGIST,
            description=(
                "Generates trading signals by combining technical, fundamental, "
                "and sentiment analysis. Produces structured signals with entry, "
                "stop-loss, and take-profit levels."
            ),
            llm=llm,
            tools=tools or STRATEGIST_TOOLS,
            system_prompt=system_prompt or STRATEGIST_SYSTEM_PROMPT,
        )

    def run(self, state: AgentState) -> Dict[str, Any]:
        """Execute signal generation based on analysis inputs."""
        symbols = state.get("symbols", [])

        # Build market data summary
        market_data_summary = self._summarize_market_data(state)

        task = STRATEGIST_TASK_TEMPLATE.format(
            symbols=", ".join(symbols),
            research_output=state.get("research_output", "No research available")[:2000],
            macro_output=state.get("macro_output", "No macro analysis available")[:1500],
            crypto_output=state.get("crypto_output", "No crypto analysis available")[:1500],
            forex_output=state.get("forex_output", "No forex analysis available")[:1500],
            market_data_summary=market_data_summary,
        )

        messages = self.build_messages(state, user_content=task)
        response = self.invoke_llm(messages, use_tools=True)
        content = response.content

        # Handle tool calls
        tool_calls_made = []
        if hasattr(response, "tool_calls") and response.tool_calls:
            for tc in response.tool_calls:
                tool_calls_made.append({"name": tc.get("name", ""), "args": tc.get("args", {})})

            final_response = self.invoke_llm(messages, use_tools=False)
            content = final_response.content

        # Parse signals from content
        signals = self._parse_signals(content, symbols)

        # Calculate overall confidence
        confidence = self._calculate_confidence(signals)

        output = self.create_output(
            content=content,
            data={"signals": [s if isinstance(s, dict) else str(s) for s in signals]},
            confidence=confidence,
            tool_calls=tool_calls_made,
        )

        return {
            "signals": [s if isinstance(s, dict) else str(s) for s in signals],
            "strategist_output": content,
            "agent_outputs": {
                **state.get("agent_outputs", {}),
                self.name: output.model_dump(),
            },
            "confidence": confidence,
            "sender": self.name,
        }

    def _summarize_market_data(self, state: AgentState) -> str:
        """Summarize available market data for the prompt."""
        market_data = state.get("market_data", {})
        if not market_data:
            return "No market data available"

        parts = []
        for symbol, data in market_data.items():
            if isinstance(data, dict):
                parts.append(
                    f"  {symbol}: Price={data.get('close', data.get('price', 'N/A'))}, "
                    f"Change={data.get('change_pct', 'N/A')}%, "
                    f"Volume={data.get('volume', 'N/A')}"
                )
        return "\n".join(parts) if parts else "No detailed market data available"

    def _parse_signals(self, content: str, symbols: List[str]) -> List[Dict[str, Any]]:
        """Parse trading signals from LLM output."""
        signals = []

        for symbol in symbols:
            signal = {
                "symbol": symbol,
                "direction": SignalDirection.NEUTRAL.value,
                "action": TradeAction.HOLD.value,
                "confidence": 0.5,
                "entry_price": None,
                "stop_loss": None,
                "take_profit": None,
                "risk_reward_ratio": None,
                "reasoning": content[:500],
                "source_agents": ["strategist"],
            }

            # Try to extract direction
            if re.search(rf"{symbol}.*BULLISH|BULLISH.*{symbol}", content, re.IGNORECASE):
                signal["direction"] = SignalDirection.BULLISH.value
                signal["action"] = TradeAction.BUY.value
            elif re.search(rf"{symbol}.*BEARISH|BEARISH.*{symbol}", content, re.IGNORECASE):
                signal["direction"] = SignalDirection.BEARISH.value
                signal["action"] = TradeAction.SELL.value

            # Try to extract confidence
            conf_match = re.search(rf"{symbol}.*confidence[:\s]+([0-9]*\.?[0-9]+)", content, re.IGNORECASE)
            if conf_match:
                try:
                    signal["confidence"] = min(max(float(conf_match.group(1)), 0.0), 1.0)
                except ValueError:
                    pass

            # Try to extract prices
            entry_match = re.search(r"entry[:\s]+\$?([0-9]*\.?[0-9]+)", content, re.IGNORECASE)
            if entry_match:
                try:
                    signal["entry_price"] = float(entry_match.group(1))
                except ValueError:
                    pass

            sl_match = re.search(r"stop[\s-]?loss[:\s]+\$?([0-9]*\.?[0-9]+)", content, re.IGNORECASE)
            if sl_match:
                try:
                    signal["stop_loss"] = float(sl_match.group(1))
                except ValueError:
                    pass

            tp_match = re.search(r"take[\s-]?profit[:\s]+\$?([0-9]*\.?[0-9]+)", content, re.IGNORECASE)
            if tp_match:
                try:
                    signal["take_profit"] = float(tp_match.group(1))
                except ValueError:
                    pass

            # Calculate risk:reward
            if signal["entry_price"] and signal["stop_loss"] and signal["take_profit"]:
                entry = signal["entry_price"]
                sl = signal["stop_loss"]
                tp = signal["take_profit"]
                risk = abs(entry - sl)
                reward = abs(tp - entry)
                if risk > 0:
                    signal["risk_reward_ratio"] = round(reward / risk, 2)

            signals.append(signal)

        return signals if signals else [{"action": TradeAction.HOLD.value, "confidence": 0.3}]

    def _calculate_confidence(self, signals: List[Dict[str, Any]]) -> float:
        """Calculate overall confidence from signals."""
        if not signals:
            return 0.0
        confidences = [s.get("confidence", 0.5) for s in signals if isinstance(s, dict)]
        return sum(confidences) / len(confidences) if confidences else 0.5
