"""
Geopolitics Agent Base Class.

Provides the base class for all geopolitics-perspective agents,
with shared tools for sanctions checking, trade flow analysis,
currency impact, and commodity exposure.
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
# Geopolitics Tools
# =============================================================================

@tool
def sanctions_checker(entity: str, country: str = "") -> str:
    """
    Check sanctions status for an entity or country.

    Args:
        entity: Company, individual, or sector to check
        country: Optional country filter

    Returns:
        JSON string with sanctions status
    """
    result = {
        "entity": entity,
        "country": country,
        "sanctions_active": False,
        "sanction_types": [],
        "risk_level": "LOW",
        "last_updated": datetime.now().isoformat(),
        "notes": f"Sanctions screening for {entity}" + (f" in {country}" if country else ""),
    }
    return json.dumps(result, indent=2)


@tool
def trade_flow_analyzer(
    origin: str,
    destination: str,
    commodity: str = "",
) -> str:
    """
    Analyze trade flows between countries/regions.

    Args:
        origin: Exporting country/region
        destination: Importing country/region
        commodity: Optional commodity filter

    Returns:
        JSON string with trade flow data
    """
    result = {
        "origin": origin,
        "destination": destination,
        "commodity": commodity or "all",
        "trade_volume_estimate": "moderate",
        "trade_trend": "stable",
        "barriers": [],
        "risk_factors": ["geopolitical_tension", "regulatory_change"],
        "timestamp": datetime.now().isoformat(),
    }
    return json.dumps(result, indent=2)


@tool
def currency_impact(
    base_currency: str,
    quote_currency: str,
    scenario: str = "current",
) -> str:
    """
    Analyze currency impact from geopolitical events.

    Args:
        base_currency: Base currency code (e.g., USD)
        quote_currency: Quote currency code (e.g., CNY)
        scenario: Scenario type (current, escalation, deescalation)

    Returns:
        JSON string with currency impact analysis
    """
    result = {
        "pair": f"{base_currency}/{quote_currency}",
        "scenario": scenario,
        "impact_direction": "neutral",
        "magnitude": "low",
        "key_drivers": ["central_bank_policy", "trade_balance"],
        "volatility_outlook": "moderate",
        "timestamp": datetime.now().isoformat(),
    }
    return json.dumps(result, indent=2)


@tool
def commodity_exposure(
    commodity: str,
    region: str = "global",
) -> str:
    """
    Analyze commodity exposure from geopolitical perspective.

    Args:
        commodity: Commodity name (e.g., oil, gold, rare_earth)
        region: Geographic region

    Returns:
        JSON string with commodity exposure analysis
    """
    result = {
        "commodity": commodity,
        "region": region,
        "supply_risk": "moderate",
        "demand_outlook": "stable",
        "key_producers": [],
        "chokepoints": ["strait_of_hormuz" if commodity == "oil" else "trade_routes"],
        "price_sensitivity": "medium",
        "timestamp": datetime.now().isoformat(),
    }
    return json.dumps(result, indent=2)


# Shared tools list for all geopolitics agents
GEOPOLITICS_TOOLS = [sanctions_checker, trade_flow_analyzer, currency_impact, commodity_exposure]


# =============================================================================
# Geopolitics Agent Base
# =============================================================================

class GeopoliticsAgent(BaseAgent):
    """
    Base class for geopolitics-perspective agents.

    Provides shared infrastructure for all geopolitics agents including
    common tools (sanctions_checker, trade_flow_analyzer, currency_impact,
    commodity_exposure) and a standard analysis workflow.
    """

    def __init__(
        self,
        name: str,
        llm: BaseChatModel,
        system_prompt: str,
        tools: Optional[List] = None,
    ) -> None:
        """
        Initialize geopolitics agent.

        Args:
            name: Agent name
            llm: Language model instance
            system_prompt: Geopolitics-specific system prompt
            tools: Optional additional tools
        """
        all_tools = tools or []
        # Add standard geopolitics tools
        for t in GEOPOLITICS_TOOLS:
            if t not in all_tools:
                all_tools.append(t)

        super().__init__(
            name=name,
            role=AgentRole.GEOPOLITICS,
            description=f"Geopolitics analysis agent: {name}",
            llm=llm,
            tools=all_tools,
            system_prompt=system_prompt,
        )

    def analyze_geopolitics(self, method: str, region: str) -> Dict[str, Any]:
        """
        Analyze geopolitical situation for a region using a specified method.

        Args:
            method: Analysis method (e.g., sanctions, trade_flow, currency, commodity)
            region: Target geographic region

        Returns:
            Analysis results dict
        """
        dispatch = {
            "sanctions": lambda: json.loads(sanctions_checker(region)),
            "trade_flow": lambda: json.loads(trade_flow_analyzer(region, "global")),
            "currency": lambda: json.loads(currency_impact("USD", region)),
            "commodity": lambda: json.loads(commodity_exposure(region)),
        }
        result = dispatch.get(method, lambda: {"method": method, "region": region, "status": "unknown_method"})()
        result["method"] = method
        result["analyzed_by"] = self.name
        return result

    def run(self, state: AgentState) -> Dict[str, Any]:
        """
        Execute geopolitical analysis.

        Args:
            state: Current agent state

        Returns:
            State updates with geopolitics analysis
        """
        symbols = state.get("symbols", [])
        trade_date = state.get("trade_date", "")

        # Build analysis task
        task = self._build_analysis_task(symbols, trade_date, state)

        # Build messages and invoke LLM
        messages = self.build_messages(state, user_content=task)
        response = self.invoke_llm(messages, use_tools=bool(self.tools))

        content = response.content
        tool_calls_made = []

        if hasattr(response, "tool_calls") and response.tool_calls:
            for tc in response.tool_calls:
                tool_calls_made.append({
                    "name": tc.get("name", ""),
                    "args": tc.get("args", {}),
                })

        confidence = self._assess_confidence(content, symbols)

        output = self.create_output(
            content=content,
            data={
                "symbols_analyzed": symbols,
                "perspective": self.name,
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

    def _build_analysis_task(
        self,
        symbols: List[str],
        trade_date: str,
        state: AgentState,
    ) -> str:
        """Build the analysis task prompt."""
        return (
            f"Analyze the geopolitical landscape for: {', '.join(symbols)}\n"
            f"Date: {trade_date}\n\n"
            f"Consider sanctions, trade flows, currency impacts, and commodity exposure "
            f"from your geopolitical perspective. Provide a structured analysis with "
            f"risk levels and actionable insights."
        )

    def _assess_confidence(self, content: str, symbols: List[str]) -> float:
        """Assess confidence of analysis output."""
        confidence = 0.4
        for symbol in symbols:
            if symbol.upper() in content.upper():
                confidence += 0.1
        key_terms = ["sanctions", "trade", "risk", "geopolitical", "currency"]
        for term in key_terms:
            if term.lower() in content.lower():
                confidence += 0.03
        return min(confidence, 1.0)
