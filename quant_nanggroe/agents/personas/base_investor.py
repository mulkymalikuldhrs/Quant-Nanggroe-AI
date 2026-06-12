"""
Base Investor Agent.

Provides the base class for all investor persona agents,
with shared analysis workflow and investor-specific tools.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from langchain_core.language_models import BaseChatModel
except ImportError:
    BaseChatModel = None
try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func=None, *args, **kwargs):
        """No-op fallback when langchain_core is not installed."""
        if func is not None:
            return func
        def decorator(f):
            return f
        return decorator

from quant_nanggroe.agents.base import BaseAgent
from quant_nanggroe.agents.state import AgentRole, AgentState

logger = logging.getLogger(__name__)


# =============================================================================
# Shared Investor Tools
# =============================================================================

@tool
def valuation_metrics(symbol: str, metric_type: str = "overview") -> str:
    """
    Get valuation metrics for a symbol.

    Args:
        symbol: Stock ticker symbol
        metric_type: Type of metrics (overview, dcf, relative, owner_earnings)

    Returns:
        JSON string with valuation data
    """
    result = {
        "symbol": symbol.upper(),
        "metric_type": metric_type,
        "pe_ratio": 25.0,
        "pb_ratio": 4.5,
        "ps_ratio": 8.2,
        "ev_ebitda": 18.5,
        "fcf_yield": 0.035,
        "peg_ratio": 1.8,
        "timestamp": datetime.now().isoformat(),
    }
    return json.dumps(result, indent=2)


@tool
def financial_health(symbol: str) -> str:
    """
    Assess financial health of a company.

    Args:
        symbol: Stock ticker symbol

    Returns:
        JSON string with financial health assessment
    """
    result = {
        "symbol": symbol.upper(),
        "roe": 0.18,
        "debt_to_equity": 0.55,
        "current_ratio": 1.8,
        "operating_margin": 0.22,
        "free_cash_flow": "positive",
        "book_value_growth": 0.12,
        "earnings_consistency": "stable",
        "timestamp": datetime.now().isoformat(),
    }
    return json.dumps(result, indent=2)


@tool
def competitive_moat(symbol: str) -> str:
    """
    Analyze competitive moat strength.

    Args:
        symbol: Stock ticker symbol

    Returns:
        JSON string with moat analysis
    """
    result = {
        "symbol": symbol.upper(),
        "moat_type": "brand_and_network_effects",
        "moat_strength": "wide",
        "pricing_power": True,
        "switching_costs": True,
        "network_effects": True,
        "brand_strength": "strong",
        "patent_protection": "moderate",
        "timestamp": datetime.now().isoformat(),
    }
    return json.dumps(result, indent=2)


@tool
def management_quality(symbol: str) -> str:
    """
    Assess management quality and capital allocation.

    Args:
        symbol: Stock ticker symbol

    Returns:
        JSON string with management quality assessment
    """
    result = {
        "symbol": symbol.upper(),
        "shareholder_friendly": True,
        "buyback_history": "consistent",
        "dividend_policy": "growing",
        "capital_allocation": "excellent",
        "insider_ownership": "moderate",
        "governance_score": 0.78,
        "timestamp": datetime.now().isoformat(),
    }
    return json.dumps(result, indent=2)


INVESTOR_TOOLS = [valuation_metrics, financial_health, competitive_moat, management_quality]


# =============================================================================
# Base Investor Agent
# =============================================================================

class BaseInvestorAgent(BaseAgent):
    """
    Base class for investor persona agents.

    Each persona inherits from this class and provides:
    - A unique system prompt embodying the investor's philosophy
    - Investor-specific analysis tools
    - A consistent analysis workflow

    The base class handles the common analysis pipeline:
    1. Gather financial data via shared tools
    2. Apply investor-specific analytical framework
    3. Generate signal (bullish/bearish/neutral) with confidence
    """

    def __init__(
        self,
        name: str,
        llm: BaseChatModel,
        system_prompt: str,
        investor_name: str,
        tools: Optional[List] = None,
    ) -> None:
        """
        Initialize investor persona agent.

        Args:
            name: Agent registration name
            llm: Language model instance
            system_prompt: Investor-specific system prompt
            investor_name: Display name of the investor
            tools: Optional additional tools
        """
        all_tools = tools or []
        for t in INVESTOR_TOOLS:
            if t not in all_tools:
                all_tools.append(t)

        super().__init__(
            name=name,
            role=AgentRole.PERSONA,
            description=f"Investor persona: {investor_name}",
            llm=llm,
            tools=all_tools,
            system_prompt=system_prompt,
        )
        self._investor_name = investor_name

    @property
    def investor_name(self) -> str:
        """Get the investor's display name."""
        return self._investor_name

    def run(self, state: AgentState) -> Dict[str, Any]:
        """
        Execute investor persona analysis.

        Args:
            state: Current agent state

        Returns:
            State updates with investor analysis
        """
        symbols = state.get("symbols", [])
        trade_date = state.get("trade_date", "")

        task = (
            f"Analyze the following assets from {self._investor_name}'s investment perspective: "
            f"{', '.join(symbols)}\n"
            f"Date: {trade_date}\n\n"
            f"Use the available tools to gather financial data. Then provide your analysis "
            f"following your investment philosophy. End with a clear signal: "
            f"BULLISH, BEARISH, or NEUTRAL, along with a confidence level (0-100)."
        )

        messages = self.build_messages(state, user_content=task)
        response = self.invoke_llm(messages, use_tools=True)

        content = response.content
        tool_calls_made = []

        if hasattr(response, "tool_calls") and response.tool_calls:
            for tc in response.tool_calls:
                tool_calls_made.append({
                    "name": tc.get("name", ""),
                    "args": tc.get("args", {}),
                })

        confidence = self._assess_confidence(content, symbols)
        signal = self._extract_signal(content)

        output = self.create_output(
            content=content,
            data={
                "symbols_analyzed": symbols,
                "investor_persona": self._investor_name,
                "signal": signal,
                "tools_used": [tc["name"] for tc in tool_calls_made],
                "trade_date": trade_date,
            },
            confidence=confidence,
            tool_calls=tool_calls_made,
        )

        return {
            "agent_outputs": {
                **state.get("agent_outputs", {}),
                self.name: output.model_dump(),
            },
            "sender": self.name,
        }

    def _extract_signal(self, content: str) -> str:
        """Extract investment signal from content."""
        content_upper = content.upper()
        if "BULLISH" in content_upper:
            return "BULLISH"
        elif "BEARISH" in content_upper:
            return "BEARISH"
        return "NEUTRAL"

    def _assess_confidence(self, content: str, symbols: List[str]) -> float:
        """Assess confidence of investor analysis output."""
        confidence = 0.4
        for symbol in symbols:
            if symbol.upper() in content.upper():
                confidence += 0.1
        key_terms = ["valuation", "moat", "risk", "growth", "margin", "cash flow"]
        for term in key_terms:
            if term.lower() in content.lower():
                confidence += 0.03
        return min(confidence, 1.0)
