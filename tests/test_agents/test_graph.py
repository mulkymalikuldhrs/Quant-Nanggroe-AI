"""Comprehensive tests for Trading Graph conditional routing.

Tests the _risk_conditional method and graph construction without
requiring actual LLM connections (mocks where needed).
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from quant_nanggroe.agents.state import (
    AgentState, RiskVerdict, TradeAction, CONFIDENCE_THRESHOLD,
    create_initial_state,
)


class TestRiskConditionalRouting:
    """Test the _risk_conditional routing logic in isolation.

    These tests verify the decision logic without needing a full graph
    or LLM connection.
    """

    @pytest.fixture
    def mock_graph(self):
        """Create a TradingGraph with mocked LLMs."""
        with patch("quant_nanggroe.agents.graph.create_llm") as mock_create_llm, \
             patch("quant_nanggroe.agents.graph.AgentFactory") as mock_factory, \
             patch("quant_nanggroe.agents.graph.CouncilDebate") as mock_debate, \
             patch("quant_nanggroe.agents.graph.CouncilVoting") as mock_voting:
            mock_llm = MagicMock()
            mock_create_llm.return_value = mock_llm
            mock_factory_instance = MagicMock()
            mock_factory.return_value = mock_factory_instance
            mock_debate_instance = MagicMock()
            mock_debate.return_value = mock_debate_instance
            mock_voting_instance = MagicMock()
            mock_voting.return_value = mock_voting_instance

            from quant_nanggroe.agents.graph import TradingGraph
            graph = TradingGraph(
                llm_provider="openai",
                deep_think_model="gpt-4o",
                quick_think_model="gpt-4o-mini",
                api_key="test-key",
            )
            return graph

    def test_route_to_emergency_exit_when_kill_switch_active(self, mock_graph):
        """Kill switch active → emergency exit."""
        state = create_initial_state(["BTC/USDT"], "2024-01-15")
        state["kill_switch_active"] = True
        result = mock_graph._risk_conditional(state)
        assert result == "emergency_exit"

    def test_route_to_halt_when_vetoed(self, mock_graph):
        """Risk VETOED → halt."""
        state = create_initial_state(["BTC/USDT"], "2024-01-15")
        state["risk_verdict"] = RiskVerdict.VETOED.value
        state["kill_switch_active"] = False
        result = mock_graph._risk_conditional(state)
        assert result == "halt"

    def test_route_to_emergency_exit_on_kill_switch_verdict(self, mock_graph):
        """Risk KILL_SWITCH verdict → emergency exit."""
        state = create_initial_state(["BTC/USDT"], "2024-01-15")
        state["risk_verdict"] = RiskVerdict.KILL_SWITCH.value
        state["kill_switch_active"] = False
        result = mock_graph._risk_conditional(state)
        assert result == "emergency_exit"

    def test_route_to_council_debate_on_low_confidence(self, mock_graph):
        """Low confidence → council debate."""
        state = create_initial_state(["BTC/USDT"], "2024-01-15")
        state["risk_verdict"] = RiskVerdict.APPROVED.value
        state["kill_switch_active"] = False
        state["confidence"] = 0.3  # Below threshold
        result = mock_graph._risk_conditional(state)
        assert result == "council_debate"

    def test_route_to_continue_on_high_confidence(self, mock_graph):
        """High confidence → continue."""
        state = create_initial_state(["BTC/USDT"], "2024-01-15")
        state["risk_verdict"] = RiskVerdict.APPROVED.value
        state["kill_switch_active"] = False
        state["confidence"] = 0.8  # Above threshold
        result = mock_graph._risk_conditional(state)
        assert result == "continue"

    def test_route_to_continue_on_conditional_verdict(self, mock_graph):
        """CONDITIONAL verdict with high confidence → continue."""
        state = create_initial_state(["BTC/USDT"], "2024-01-15")
        state["risk_verdict"] = RiskVerdict.CONDITIONAL.value
        state["kill_switch_active"] = False
        state["confidence"] = 0.8
        result = mock_graph._risk_conditional(state)
        assert result == "continue"

    def test_kill_switch_takes_priority_over_veto(self, mock_graph):
        """Kill switch should take priority over veto."""
        state = create_initial_state(["BTC/USDT"], "2024-01-15")
        state["kill_switch_active"] = True
        state["risk_verdict"] = RiskVerdict.VETOED.value
        result = mock_graph._risk_conditional(state)
        assert result == "emergency_exit"

    def test_kill_switch_takes_priority_over_approved(self, mock_graph):
        state = create_initial_state(["BTC/USDT"], "2024-01-15")
        state["kill_switch_active"] = True
        state["risk_verdict"] = RiskVerdict.APPROVED.value
        state["confidence"] = 1.0
        result = mock_graph._risk_conditional(state)
        assert result == "emergency_exit"

    def test_veto_takes_priority_over_low_confidence(self, mock_graph):
        """Veto should take priority over low confidence routing."""
        state = create_initial_state(["BTC/USDT"], "2024-01-15")
        state["kill_switch_active"] = False
        state["risk_verdict"] = RiskVerdict.VETOED.value
        state["confidence"] = 0.1  # Very low
        result = mock_graph._risk_conditional(state)
        assert result == "halt"

    def test_confidence_at_threshold(self, mock_graph):
        """Confidence exactly at threshold → council debate."""
        state = create_initial_state(["BTC/USDT"], "2024-01-15")
        state["risk_verdict"] = RiskVerdict.APPROVED.value
        state["kill_switch_active"] = False
        state["confidence"] = CONFIDENCE_THRESHOLD  # Exactly at threshold
        result = mock_graph._risk_conditional(state)
        # At threshold, not strictly less than, so should continue
        assert result == "continue"

    def test_confidence_just_below_threshold(self, mock_graph):
        """Confidence just below threshold → council debate."""
        state = create_initial_state(["BTC/USDT"], "2024-01-15")
        state["risk_verdict"] = RiskVerdict.APPROVED.value
        state["kill_switch_active"] = False
        state["confidence"] = CONFIDENCE_THRESHOLD - 0.001
        result = mock_graph._risk_conditional(state)
        assert result == "council_debate"


class TestTradingGraphConstruction:
    """Test TradingGraph construction and properties."""

    @pytest.fixture
    def mock_graph(self):
        with patch("quant_nanggroe.agents.graph.create_llm") as mock_create_llm, \
             patch("quant_nanggroe.agents.graph.AgentFactory") as mock_factory, \
             patch("quant_nanggroe.agents.graph.CouncilDebate") as mock_debate, \
             patch("quant_nanggroe.agents.graph.CouncilVoting") as mock_voting:
            mock_llm = MagicMock()
            mock_create_llm.return_value = mock_llm
            mock_factory_instance = MagicMock()
            mock_factory.return_value = mock_factory_instance
            mock_debate_instance = MagicMock()
            mock_debate.return_value = mock_debate_instance
            mock_voting_instance = MagicMock()
            mock_voting.return_value = mock_voting_instance

            from quant_nanggroe.agents.graph import TradingGraph
            return TradingGraph(
                llm_provider="openai",
                api_key="test-key",
            )

    def test_graph_compiled(self, mock_graph):
        """Graph should be compiled after construction."""
        assert mock_graph.graph is not None

    def test_custom_confidence_threshold(self):
        with patch("quant_nanggroe.agents.graph.create_llm") as mock_create_llm, \
             patch("quant_nanggroe.agents.graph.AgentFactory") as mock_factory, \
             patch("quant_nanggroe.agents.graph.CouncilDebate") as mock_debate, \
             patch("quant_nanggroe.agents.graph.CouncilVoting") as mock_voting:
            mock_llm = MagicMock()
            mock_create_llm.return_value = mock_llm
            mock_factory_instance = MagicMock()
            mock_factory.return_value = mock_factory_instance
            mock_debate_instance = MagicMock()
            mock_debate.return_value = mock_debate_instance
            mock_voting_instance = MagicMock()
            mock_voting.return_value = mock_voting_instance

            from quant_nanggroe.agents.graph import TradingGraph
            graph = TradingGraph(
                llm_provider="openai",
                api_key="test-key",
                confidence_threshold=0.8,
            )
            assert graph._confidence_threshold == 0.8


class TestEmergencyExitNode:
    """Test the emergency exit node logic."""

    @pytest.fixture
    def mock_graph(self):
        with patch("quant_nanggroe.agents.graph.create_llm") as mock_create_llm, \
             patch("quant_nanggroe.agents.graph.AgentFactory") as mock_factory, \
             patch("quant_nanggroe.agents.graph.CouncilDebate") as mock_debate, \
             patch("quant_nanggroe.agents.graph.CouncilVoting") as mock_voting:
            mock_llm = MagicMock()
            mock_create_llm.return_value = mock_llm
            mock_factory_instance = MagicMock()
            mock_factory.return_value = mock_factory_instance
            mock_debate_instance = MagicMock()
            mock_debate.return_value = mock_debate_instance
            mock_voting_instance = MagicMock()
            mock_voting.return_value = mock_voting_instance

            from quant_nanggroe.agents.graph import TradingGraph
            return TradingGraph(llm_provider="openai", api_key="test-key")

    def test_emergency_exit_closes_all_symbols(self, mock_graph):
        state = create_initial_state(["BTC/USDT", "ETH/USDT"], "2024-01-15")
        result = mock_graph._emergency_exit_node(state)
        assert len(result["decisions"]) == 2
        for decision in result["decisions"]:
            assert decision["action"] == TradeAction.EMERGENCY_EXIT.value
        assert result["should_halt"] is True
        assert result["kill_switch_active"] is True

    def test_emergency_exit_no_symbols(self, mock_graph):
        state = create_initial_state([], "2024-01-15")
        result = mock_graph._emergency_exit_node(state)
        assert len(result["decisions"]) == 0
        assert result["should_halt"] is True
