"""
Tests for Investor Persona Agents.

Tests cover:
- BaseInvestorAgent
- WarrenBuffettAgent
- PeterLynchAgent
- MichaelBurryAgent
- CathieWoodAgent
- StanleyDruckenmillerAgent
- RayDalioAgent
- Investor tools (valuation_metrics, financial_health, etc.)
- Agent registration

All LLM calls are mocked.
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import MagicMock

from quant_nanggroe.agents.personas.base_investor import (
    BaseInvestorAgent,
    valuation_metrics,
    financial_health,
    competitive_moat,
    management_quality,
    INVESTOR_TOOLS,
)
from quant_nanggroe.agents.personas.warren_buffett import WarrenBuffettAgent
from quant_nanggroe.agents.personas.peter_lynch import PeterLynchAgent
from quant_nanggroe.agents.personas.michael_burry import MichaelBurryAgent
from quant_nanggroe.agents.personas.cathie_wood import CathieWoodAgent
from quant_nanggroe.agents.personas.stanley_druckenmiller import StanleyDruckenmillerAgent
from quant_nanggroe.agents.personas.ray_dalio import RayDalioAgent
from quant_nanggroe.agents.registry import AgentRegistry
from quant_nanggroe.agents.state import AgentRole, create_initial_state


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════

def _mock_llm(response_text: str = "Investor analysis complete. Signal: NEUTRAL"):
    """Create a mock LLM."""
    mock = MagicMock()
    mock.invoke.return_value = MagicMock(content=response_text)
    mock.bind_tools.return_value = mock
    return mock


# ═══════════════════════════════════════════════════════════════════════
# Investor Tools Tests
# ═══════════════════════════════════════════════════════════════════════


class TestValuationMetrics:
    """Test valuation_metrics tool."""

    def test_returns_json(self):
        result = valuation_metrics.invoke({"symbol": "AAPL", "metric_type": "overview"})
        data = json.loads(result)
        assert data["symbol"] == "AAPL"
        assert "pe_ratio" in data
        assert "peg_ratio" in data

    def test_dcf_metrics(self):
        result = valuation_metrics.invoke({"symbol": "MSFT", "metric_type": "dcf"})
        data = json.loads(result)
        assert data["metric_type"] == "dcf"


class TestFinancialHealth:
    """Test financial_health tool."""

    def test_returns_json(self):
        result = financial_health.invoke({"symbol": "GOOGL"})
        data = json.loads(result)
        assert data["symbol"] == "GOOGL"
        assert "roe" in data
        assert "debt_to_equity" in data


class TestCompetitiveMoat:
    """Test competitive_moat tool."""

    def test_returns_json(self):
        result = competitive_moat.invoke({"symbol": "AAPL"})
        data = json.loads(result)
        assert data["symbol"] == "AAPL"
        assert "moat_strength" in data
        assert "pricing_power" in data


class TestManagementQuality:
    """Test management_quality tool."""

    def test_returns_json(self):
        result = management_quality.invoke({"symbol": "BRK.B"})
        data = json.loads(result)
        assert data["symbol"] == "BRK.B"
        assert "shareholder_friendly" in data
        assert "governance_score" in data


class TestInvestorToolsList:
    """Test that all investor tools are available."""

    def test_all_tools_present(self):
        tool_names = [t.name for t in INVESTOR_TOOLS]
        assert "valuation_metrics" in tool_names
        assert "financial_health" in tool_names
        assert "competitive_moat" in tool_names
        assert "management_quality" in tool_names


# ═══════════════════════════════════════════════════════════════════════
# Base Investor Agent Tests
# ═══════════════════════════════════════════════════════════════════════


class TestBaseInvestorAgent:
    """Test BaseInvestorAgent base class."""

    def test_agent_has_tools(self):
        llm = _mock_llm()
        agent = BaseInvestorAgent(
            name="test_investor",
            llm=llm,
            system_prompt="You are a test investor.",
            investor_name="Test Investor",
        )
        tool_names = [t.name for t in agent.tools]
        assert "valuation_metrics" in tool_names
        assert "financial_health" in tool_names

    def test_agent_role(self):
        llm = _mock_llm()
        agent = BaseInvestorAgent(
            name="test_investor",
            llm=llm,
            system_prompt="Test",
            investor_name="Test",
        )
        assert agent.role == AgentRole.PERSONA

    def test_investor_name_property(self):
        llm = _mock_llm()
        agent = BaseInvestorAgent(
            name="test_investor",
            llm=llm,
            system_prompt="Test",
            investor_name="Warren Buffett",
        )
        assert agent.investor_name == "Warren Buffett"

    def test_extract_signal_bullish(self):
        llm = _mock_llm()
        agent = BaseInvestorAgent(
            name="test", llm=llm, system_prompt="Test", investor_name="Test",
        )
        assert agent._extract_signal("The stock is BULLISH with strong prospects") == "BULLISH"

    def test_extract_signal_bearish(self):
        llm = _mock_llm()
        agent = BaseInvestorAgent(
            name="test", llm=llm, system_prompt="Test", investor_name="Test",
        )
        assert agent._extract_signal("BEARISH outlook due to overvaluation") == "BEARISH"

    def test_extract_signal_neutral(self):
        llm = _mock_llm()
        agent = BaseInvestorAgent(
            name="test", llm=llm, system_prompt="Test", investor_name="Test",
        )
        assert agent._extract_signal("Mixed signals, wait for clarity") == "NEUTRAL"

    def test_agent_run(self):
        llm = _mock_llm("Strong BULLISH signal based on value analysis")
        agent = BaseInvestorAgent(
            name="test_investor",
            llm=llm,
            system_prompt="You are a test investor.",
            investor_name="Test Investor",
        )
        state = create_initial_state(["AAPL"], "2024-01-15")
        result = agent(state)
        assert "agent_outputs" in result
        assert "test_investor" in result["agent_outputs"]
        assert result["agent_outputs"]["test_investor"]["success"] is True


# ═══════════════════════════════════════════════════════════════════════
# Individual Persona Agent Tests
# ═══════════════════════════════════════════════════════════════════════


class TestWarrenBuffettAgent:
    """Test WarrenBuffettAgent."""

    def test_agent_creation(self):
        llm = _mock_llm()
        agent = WarrenBuffettAgent(llm=llm)
        assert agent.name == "warren_buffett"
        assert agent.investor_name == "Warren Buffett"
        assert agent.role == AgentRole.PERSONA

    def test_system_prompt_content(self):
        llm = _mock_llm()
        agent = WarrenBuffettAgent(llm=llm)
        assert "Circle of Competence" in agent._system_prompt
        assert "Competitive Moat" in agent._system_prompt
        assert "Margin of Safety" in agent._system_prompt


class TestPeterLynchAgent:
    """Test PeterLynchAgent."""

    def test_agent_creation(self):
        llm = _mock_llm()
        agent = PeterLynchAgent(llm=llm)
        assert agent.name == "peter_lynch"
        assert agent.investor_name == "Peter Lynch"

    def test_system_prompt_content(self):
        llm = _mock_llm()
        agent = PeterLynchAgent(llm=llm)
        assert "PEG Ratio" in agent._system_prompt
        assert "Ten-Bagger" in agent._system_prompt
        assert "GARP" in agent._system_prompt


class TestMichaelBurryAgent:
    """Test MichaelBurryAgent."""

    def test_agent_creation(self):
        llm = _mock_llm()
        agent = MichaelBurryAgent(llm=llm)
        assert agent.name == "michael_burry"
        assert agent.investor_name == "Michael Burry"

    def test_system_prompt_content(self):
        llm = _mock_llm()
        agent = MichaelBurryAgent(llm=llm)
        assert "Deep Value" in agent._system_prompt
        assert "Contrarian" in agent._system_prompt
        assert "FCF yield" in agent._system_prompt


class TestCathieWoodAgent:
    """Test CathieWoodAgent."""

    def test_agent_creation(self):
        llm = _mock_llm()
        agent = CathieWoodAgent(llm=llm)
        assert agent.name == "cathie_wood"
        assert agent.investor_name == "Cathie Wood"

    def test_system_prompt_content(self):
        llm = _mock_llm()
        agent = CathieWoodAgent(llm=llm)
        assert "Disruptive Innovation" in agent._system_prompt
        assert "5-Year Time Horizon" in agent._system_prompt


class TestStanleyDruckenmillerAgent:
    """Test StanleyDruckenmillerAgent."""

    def test_agent_creation(self):
        llm = _mock_llm()
        agent = StanleyDruckenmillerAgent(llm=llm)
        assert agent.name == "stanley_druckenmiller"
        assert agent.investor_name == "Stanley Druckenmiller"

    def test_system_prompt_content(self):
        llm = _mock_llm()
        agent = StanleyDruckenmillerAgent(llm=llm)
        assert "Capital Preservation" in agent._system_prompt
        assert "Macro-First" in agent._system_prompt
        assert "Asymmetric" in agent._system_prompt


class TestRayDalioAgent:
    """Test RayDalioAgent."""

    def test_agent_creation(self):
        llm = _mock_llm()
        agent = RayDalioAgent(llm=llm)
        assert agent.name == "ray_dalio"
        assert agent.investor_name == "Ray Dalio"

    def test_system_prompt_content(self):
        llm = _mock_llm()
        agent = RayDalioAgent(llm=llm)
        assert "Risk Parity" in agent._system_prompt
        assert "All-Weather" in agent._system_prompt
        assert "Economic Machine" in agent._system_prompt


# ═══════════════════════════════════════════════════════════════════════
# Agent Registration Tests
# ═══════════════════════════════════════════════════════════════════════


class TestPersonaRegistration:
    """Test that persona agents are properly registered."""

    def test_warren_buffett_registered(self):
        AgentRegistry.register("warren_buffett", AgentRole.PERSONA)(WarrenBuffettAgent)
        assert AgentRegistry.get("warren_buffett") is not None

    def test_peter_lynch_registered(self):
        AgentRegistry.register("peter_lynch", AgentRole.PERSONA)(PeterLynchAgent)
        assert AgentRegistry.get("peter_lynch") is not None

    def test_michael_burry_registered(self):
        AgentRegistry.register("michael_burry", AgentRole.PERSONA)(MichaelBurryAgent)
        assert AgentRegistry.get("michael_burry") is not None

    def test_cathie_wood_registered(self):
        AgentRegistry.register("cathie_wood", AgentRole.PERSONA)(CathieWoodAgent)
        assert AgentRegistry.get("cathie_wood") is not None

    def test_stanley_druckenmiller_registered(self):
        AgentRegistry.register("stanley_druckenmiller", AgentRole.PERSONA)(StanleyDruckenmillerAgent)
        assert AgentRegistry.get("stanley_druckenmiller") is not None

    def test_ray_dalio_registered(self):
        AgentRegistry.register("ray_dalio", AgentRole.PERSONA)(RayDalioAgent)
        assert AgentRegistry.get("ray_dalio") is not None


# ═══════════════════════════════════════════════════════════════════════
# Cross-Persona Integration Tests
# ═══════════════════════════════════════════════════════════════════════


class TestPersonaDiversity:
    """Test that different personas produce different analysis perspectives."""

    def test_unique_prompts(self):
        """Each persona should have a unique system prompt."""
        llm = _mock_llm()
        agents = [
            WarrenBuffettAgent(llm=llm),
            PeterLynchAgent(llm=llm),
            MichaelBurryAgent(llm=llm),
            CathieWoodAgent(llm=llm),
            StanleyDruckenmillerAgent(llm=llm),
            RayDalioAgent(llm=llm),
        ]
        prompts = [a._system_prompt for a in agents]
        # All prompts should be unique
        assert len(set(prompts)) == len(prompts)

    def test_unique_names(self):
        """Each persona should have a unique name."""
        llm = _mock_llm()
        agents = [
            WarrenBuffettAgent(llm=llm),
            PeterLynchAgent(llm=llm),
            MichaelBurryAgent(llm=llm),
            CathieWoodAgent(llm=llm),
            StanleyDruckenmillerAgent(llm=llm),
            RayDalioAgent(llm=llm),
        ]
        names = [a.name for a in agents]
        assert len(set(names)) == len(names)
