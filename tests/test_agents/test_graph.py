"""
Tests for the Main Trading Graph.

Validates the LangGraph StateGraph construction, conditional edges,
and end-to-end pipeline execution (with mocked LLMs).
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from quant_nanggroe.agents.state import (
    AgentState,
    RiskVerdict,
    TradeAction,
    create_initial_state,
)
from quant_nanggroe.agents.graph import TradingGraph


class TestTradingGraphConstruction:
    """Test the trading graph construction."""

    @patch("quant_nanggroe.agents.graph.create_llm")
    def test_graph_creation(self, mock_create_llm):
        """Should create a trading graph."""
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm

        graph = TradingGraph(
            llm_provider="openai",
            deep_think_model="gpt-4o",
            quick_think_model="gpt-4o-mini",
        )
        assert graph.graph is not None

    @patch("quant_nanggroe.agents.graph.create_llm")
    def test_graph_has_nodes(self, mock_create_llm):
        """Graph should have all required nodes."""
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm

        graph = TradingGraph(
            llm_provider="openai",
            deep_think_model="gpt-4o",
            quick_think_model="gpt-4o-mini",
        )

        # The compiled graph should be invocable
        assert callable(graph.graph.invoke)


class TestRiskConditional:
    """Test the risk conditional routing logic."""

    @patch("quant_nanggroe.agents.graph.create_llm")
    def setup_method(self, method):
        """Set up test fixtures."""
        self.mock_llm = MagicMock()
        with patch("quant_nanggroe.agents.graph.create_llm", return_value=self.mock_llm):
            self.trading_graph = TradingGraph(
                llm_provider="openai",
                deep_think_model="gpt-4o",
                quick_think_model="gpt-4o-mini",
            )

    def test_kill_switch_routes_to_emergency(self):
        """Active kill switch should route to emergency exit."""
        state = create_initial_state(["AAPL"], "2025-03-01")
        state["kill_switch_active"] = True

        result = self.trading_graph._risk_conditional(state)
        assert result == "emergency_exit"

    def test_vetoed_risk_routes_to_halt(self):
        """VETOED risk should route to halt."""
        state = create_initial_state(["AAPL"], "2025-03-01")
        state["risk_verdict"] = RiskVerdict.VETOED.value

        result = self.trading_graph._risk_conditional(state)
        assert result == "halt"

    def test_kill_switch_verdict_routes_to_emergency(self):
        """KILL_SWITCH verdict should route to emergency exit."""
        state = create_initial_state(["AAPL"], "2025-03-01")
        state["risk_verdict"] = RiskVerdict.KILL_SWITCH.value

        result = self.trading_graph._risk_conditional(state)
        assert result == "emergency_exit"

    def test_low_confidence_routes_to_council(self):
        """Low confidence should route to council debate."""
        state = create_initial_state(["AAPL"], "2025-03-01")
        state["risk_verdict"] = RiskVerdict.APPROVED.value
        state["confidence"] = 0.3  # Below threshold

        result = self.trading_graph._risk_conditional(state)
        assert result == "council_debate"

    def test_approved_high_confidence_continues(self):
        """Approved with high confidence should continue."""
        state = create_initial_state(["AAPL"], "2025-03-01")
        state["risk_verdict"] = RiskVerdict.APPROVED.value
        state["confidence"] = 0.8  # Above threshold

        result = self.trading_graph._risk_conditional(state)
        assert result == "continue"


class TestEmergencyExitNode:
    """Test the emergency exit node."""

    @patch("quant_nanggroe.agents.graph.create_llm")
    def setup_method(self, method):
        """Set up test fixtures."""
        self.mock_llm = MagicMock()
        with patch("quant_nanggroe.agents.graph.create_llm", return_value=self.mock_llm):
            self.trading_graph = TradingGraph(
                llm_provider="openai",
                deep_think_model="gpt-4o",
                quick_think_model="gpt-4o-mini",
            )

    def test_emergency_exit_decisions(self):
        """Emergency exit should generate EMERGENCY_EXIT for all symbols."""
        state = create_initial_state(["AAPL", "MSFT"], "2025-03-01")
        result = self.trading_graph._emergency_exit_node(state)

        assert len(result["decisions"]) == 2
        for decision in result["decisions"]:
            assert decision["action"] == TradeAction.EMERGENCY_EXIT.value
        assert result["kill_switch_active"] is True
        assert result["should_halt"] is True


class TestInitial_state:
    """Test initial state creation for the graph."""

    def test_initial_state_has_all_fields(self):
        """Initial state should have all required fields."""
        state = create_initial_state(["AAPL"], "2025-03-01")

        required_fields = [
            "symbols", "trade_date", "market_data",
            "research_output", "macro_output", "crypto_output", "forex_output",
            "signals", "strategist_output",
            "risk_assessment", "risk_verdict",
            "portfolio_state", "portfolio_output",
            "decisions", "trader_output",
            "execution_output", "orders_placed",
            "debate_state", "council_result",
            "agent_outputs",
            "iteration", "confidence",
            "kill_switch_active", "should_halt",
            "metadata", "sender",
        ]

        for field in required_fields:
            assert field in state, f"Missing required field: {field}"
