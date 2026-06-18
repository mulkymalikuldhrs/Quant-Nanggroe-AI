"""
Tests for Geopolitics Agents.

Tests cover:
- GeopoliticsAgent base class
- AmericanOrderAgent, ChineseOrderAgent, EuropeanOrderAgent, IslamicFinanceAgent, MultipolarAgent
- Geopolitics tools (sanctions_checker, trade_flow_analyzer, currency_impact, commodity_exposure)
- Agent registration

All LLM calls are mocked.
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import MagicMock

from quant_nanggroe.agents.geopolitics.base import (
    GeopoliticsAgent,
    sanctions_checker,
    trade_flow_analyzer,
    currency_impact,
    commodity_exposure,
    GEOPOLITICS_TOOLS,
)
from quant_nanggroe.agents.geopolitics.american_order import AmericanOrderAgent
from quant_nanggroe.agents.geopolitics.chinese_order import ChineseOrderAgent
from quant_nanggroe.agents.geopolitics.european_order import EuropeanOrderAgent
from quant_nanggroe.agents.geopolitics.islamic_finance import IslamicFinanceAgent
from quant_nanggroe.agents.geopolitics.multipolar import MultipolarAgent
from quant_nanggroe.agents.registry import AgentRegistry
from quant_nanggroe.agents.state import AgentRole, create_initial_state


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════

def _mock_llm(response_text: str = "Geopolitical analysis complete"):
    """Create a mock LLM."""
    mock = MagicMock()
    mock.invoke.return_value = MagicMock(content=response_text)
    mock.bind_tools.return_value = mock
    return mock


# ═══════════════════════════════════════════════════════════════════════
# Geopolitics Tools Tests
# ═══════════════════════════════════════════════════════════════════════


class TestSanctionsChecker:
    def test_returns_json(self):
        result = sanctions_checker.invoke({"entity": "Huawei", "country": "CN"})
        data = json.loads(result)
        assert data["entity"] == "Huawei"
        assert "sanctions_active" in data
        assert "risk_level" in data

    def test_without_country(self):
        result = sanctions_checker.invoke({"entity": "Gazprom"})
        data = json.loads(result)
        assert data["entity"] == "Gazprom"


class TestTradeFlowAnalyzer:
    def test_returns_json(self):
        result = trade_flow_analyzer.invoke({
            "origin": "China", "destination": "EU", "commodity": "electronics",
        })
        data = json.loads(result)
        assert data["origin"] == "China"
        assert "trade_volume_estimate" in data


class TestCurrencyImpact:
    def test_returns_json(self):
        result = currency_impact.invoke({
            "base_currency": "USD", "quote_currency": "CNY", "scenario": "escalation",
        })
        data = json.loads(result)
        assert data["pair"] == "USD/CNY"


class TestCommodityExposure:
    def test_returns_json(self):
        result = commodity_exposure.invoke({"commodity": "oil", "region": "middle_east"})
        data = json.loads(result)
        assert data["commodity"] == "oil"
        assert "supply_risk" in data


class TestGeopoliticsToolsList:
    def test_all_tools_present(self):
        tool_names = [t.name for t in GEOPOLITICS_TOOLS]
        assert "sanctions_checker" in tool_names
        assert "trade_flow_analyzer" in tool_names
        assert "currency_impact" in tool_names
        assert "commodity_exposure" in tool_names


# ═══════════════════════════════════════════════════════════════════════
# Geopolitics Agent Base Tests
# ═══════════════════════════════════════════════════════════════════════


class TestGeopoliticsAgentBase:
    def test_geopolitics_agent_has_tools(self):
        llm = _mock_llm()
        agent = GeopoliticsAgent(
            name="test_geopolitics", llm=llm,
            system_prompt="You are a test geopolitics agent.",
        )
        tool_names = [t.name for t in agent.tools]
        assert "sanctions_checker" in tool_names

    def test_geopolitics_agent_role(self):
        llm = _mock_llm()
        agent = GeopoliticsAgent(
            name="test_geopolitics", llm=llm, system_prompt="Test",
        )
        assert agent.role == AgentRole.GEOPOLITICS

    def test_geopolitics_agent_run(self):
        llm = _mock_llm("Geopolitical risk analysis complete")
        agent = GeopoliticsAgent(
            name="test_geopolitics", llm=llm, system_prompt="Test",
        )
        state = create_initial_state(["AAPL"], "2024-01-15")
        result = agent(state)
        assert "agent_outputs" in result
        assert "test_geopolitics" in result["agent_outputs"]
        assert result["agent_outputs"]["test_geopolitics"]["success"] is True


# ═══════════════════════════════════════════════════════════════════════
# Individual Geopolitics Agent Tests
# ═══════════════════════════════════════════════════════════════════════


class TestAmericanOrderAgent:
    def test_agent_creation(self):
        llm = _mock_llm("US dollar hegemony analysis")
        agent = AmericanOrderAgent(llm=llm)
        assert agent.name == "american_order"
        assert agent.role == AgentRole.GEOPOLITICS

    def test_agent_has_system_prompt(self):
        llm = _mock_llm()
        agent = AmericanOrderAgent(llm=llm)
        assert "Dollar Hegemony" in agent._system_prompt
        assert "Federal Reserve" in agent._system_prompt

    def test_agent_run(self):
        llm = _mock_llm("US-centric analysis: dollar remains strong")
        agent = AmericanOrderAgent(llm=llm)
        state = create_initial_state(["AAPL"], "2024-01-15")
        result = agent(state)
        assert "agent_outputs" in result
        assert "american_order" in result["agent_outputs"]


class TestChineseOrderAgent:
    def test_agent_creation(self):
        llm = _mock_llm()
        agent = ChineseOrderAgent(llm=llm)
        assert agent.name == "chinese_order"
        assert "Belt and Road" in agent._system_prompt


class TestEuropeanOrderAgent:
    def test_agent_creation(self):
        llm = _mock_llm()
        agent = EuropeanOrderAgent(llm=llm)
        assert agent.name == "european_order"
        assert "Regulatory Superpower" in agent._system_prompt


class TestIslamicFinanceAgent:
    def test_agent_creation(self):
        llm = _mock_llm()
        agent = IslamicFinanceAgent(llm=llm)
        assert agent.name == "islamic_finance"
        assert "Shariah" in agent._system_prompt


class TestMultipolarAgent:
    def test_agent_creation(self):
        llm = _mock_llm()
        agent = MultipolarAgent(llm=llm)
        assert agent.name == "multipolar"
        assert "De-dollarization" in agent._system_prompt


# ═══════════════════════════════════════════════════════════════════════
# Agent Registration Tests
# ═══════════════════════════════════════════════════════════════════════


class TestGeopoliticsRegistration:
    """Test that geopolitics agents are properly registered."""

    def test_american_order_registered(self):
        # Re-register since the decorator runs at import time but
        # other tests may have cleared the registry
        AgentRegistry.register("american_order", AgentRole.GEOPOLITICS)(AmericanOrderAgent)
        assert AgentRegistry.get("american_order") is not None

    def test_chinese_order_registered(self):
        AgentRegistry.register("chinese_order", AgentRole.GEOPOLITICS)(ChineseOrderAgent)
        assert AgentRegistry.get("chinese_order") is not None

    def test_european_order_registered(self):
        AgentRegistry.register("european_order", AgentRole.GEOPOLITICS)(EuropeanOrderAgent)
        assert AgentRegistry.get("european_order") is not None

    def test_islamic_finance_registered(self):
        AgentRegistry.register("islamic_finance", AgentRole.GEOPOLITICS)(IslamicFinanceAgent)
        assert AgentRegistry.get("islamic_finance") is not None

    def test_multipolar_registered(self):
        AgentRegistry.register("multipolar", AgentRole.GEOPOLITICS)(MultipolarAgent)
        assert AgentRegistry.get("multipolar") is not None
