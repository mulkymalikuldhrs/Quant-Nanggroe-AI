"""Comprehensive tests for agents core modules.

Tests cover:
- AgentState model validation (create valid state, reject invalid)
- AgentRegistry: register agents, create by type, factory
- BaseAgent: create agent with mocked LLM, test invoke with mocked response
- AgentRole enum values
- RiskAssessment model creation and validation
- AgentOutput model creation
- Constitutional limits consistency

Mock all LLM calls with unittest.mock. No real API calls.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime
from pydantic import ValidationError

from quant_nanggroe.agents.state import (
    AgentState,
    AgentRole,
    AgentOutput,
    TradeAction,
    SignalDirection,
    RiskVerdict,
    MarketRegime,
    MarketData,
    Signal,
    Decision,
    RiskCheckpoint,
    RiskAssessment as StateRiskAssessment,
    PortfolioState,
    PositionInfo,
    VoteResult,
    CouncilResult,
    DebateState,
    RiskDebateState,
    create_initial_state,
    MAX_RISK_PER_TRADE,
    MAX_DAILY_LOSS,
    MAX_WEEKLY_LOSS,
    MIN_RISK_REWARD,
    MAX_CORRELATED_POSITIONS,
    MAX_POSITION_SIZE_PCT,
    MAX_LEVERAGE,
    MAX_DRAWDOWN_PCT,
    MAX_TRADES_PER_DAY,
    CONFIDENCE_THRESHOLD,
    KILL_SWITCH_DAILY_PNL,
    KILL_SWITCH_WEEKLY_PNL,
)
from quant_nanggroe.agents.registry import AgentRegistry, AgentFactory
from quant_nanggroe.agents.base import BaseAgent, create_llm
from quant_nanggroe.config.settings import get_settings


# ═══════════════════════════════════════════════════════════════════════
# 1. AgentRole Enum Tests
# ═══════════════════════════════════════════════════════════════════════


class TestAgentRole:
    """Test AgentRole enum values and behavior."""

    def test_all_role_values(self):
        expected = [
            "researcher", "trader", "strategist", "risk",
            "portfolio", "execution", "macro", "crypto",
            "forex", "council",
        ]
        actual = [r.value for r in AgentRole]
        for val in expected:
            assert val in actual, f"Missing role: {val}"

    def test_role_is_string_enum(self):
        assert isinstance(AgentRole.RESEARCHER, str)
        assert AgentRole.RESEARCHER == "researcher"

    def test_role_from_value(self):
        assert AgentRole("trader") == AgentRole.TRADER
        assert AgentRole("risk") == AgentRole.RISK

    def test_role_invalid_value_raises(self):
        with pytest.raises(ValueError):
            AgentRole("nonexistent_role")

    def test_all_roles_are_unique(self):
        values = [r.value for r in AgentRole]
        assert len(values) == len(set(values))


# ═══════════════════════════════════════════════════════════════════════
# 2. AgentState Validation Tests
# ═══════════════════════════════════════════════════════════════════════


class TestAgentState:
    """Test AgentState TypedDict creation and validation."""

    def test_create_valid_state(self):
        state = create_initial_state(["AAPL", "MSFT"], "2024-01-15")
        assert state["symbols"] == ["AAPL", "MSFT"]
        assert state["trade_date"] == "2024-01-15"
        assert state["market_data"] == {}
        assert state["signals"] == []
        assert state["decisions"] == []
        assert state["kill_switch_active"] is False
        assert state["should_halt"] is False
        assert state["confidence"] == 0.0
        assert state["iteration"] == 0
        assert state["sender"] == "system"

    def test_state_has_constitutional_limits(self):
        state = create_initial_state(["AAPL"], "2024-01-15")
        limits = state["metadata"]["constitutional_limits"]
        assert limits["max_risk_per_trade"] == MAX_RISK_PER_TRADE
        assert limits["max_daily_loss"] == MAX_DAILY_LOSS
        assert limits["max_weekly_loss"] == MAX_WEEKLY_LOSS
        assert limits["min_risk_reward"] == MIN_RISK_REWARD
        assert limits["max_correlated_positions"] == MAX_CORRELATED_POSITIONS
        assert limits["max_position_size_pct"] == MAX_POSITION_SIZE_PCT
        assert limits["max_leverage"] == MAX_LEVERAGE
        assert limits["max_drawdown_pct"] == MAX_DRAWDOWN_PCT
        assert limits["max_trades_per_day"] == MAX_TRADES_PER_DAY
        assert limits["override_possible"] is False

    def test_state_has_debate_state(self):
        state = create_initial_state(["AAPL"], "2024-01-15")
        assert "debate_state" in state
        assert state["debate_state"]["count"] == 0
        assert state["debate_state"]["bull_history"] == ""
        assert state["debate_state"]["bear_history"] == ""

    def test_state_default_risk_verdict_is_vetoed(self):
        """Default risk verdict should be VETOED (safe default)."""
        state = create_initial_state(["AAPL"], "2024-01-15")
        assert state["risk_verdict"] == RiskVerdict.VETOED.value

    def test_state_empty_agent_outputs(self):
        state = create_initial_state(["BTC"], "2024-01-15")
        assert state["agent_outputs"] == {}

    def test_state_empty_orders(self):
        state = create_initial_state(["BTC"], "2024-01-15")
        assert state["orders_placed"] == []

    def test_state_metadata_created_at(self):
        state = create_initial_state(["AAPL"], "2024-01-15")
        assert "created_at" in state["metadata"]


# ═══════════════════════════════════════════════════════════════════════
# 3. Enum Tests
# ═══════════════════════════════════════════════════════════════════════


class TestTradeAction:

    def test_all_actions(self):
        expected = ["BUY", "SELL", "HOLD", "CLOSE", "EMERGENCY_EXIT"]
        actual = [a.value for a in TradeAction]
        for val in expected:
            assert val in actual

    def test_action_from_string(self):
        assert TradeAction("BUY") == TradeAction.BUY
        assert TradeAction("EMERGENCY_EXIT") == TradeAction.EMERGENCY_EXIT


class TestSignalDirection:

    def test_all_directions(self):
        expected = ["BULLISH", "BEARISH", "NEUTRAL"]
        actual = [d.value for d in SignalDirection]
        assert set(actual) == set(expected)


class TestRiskVerdict:

    def test_all_verdicts(self):
        expected = ["APPROVED", "VETOED", "CONDITIONAL", "KILL_SWITCH"]
        actual = [v.value for v in RiskVerdict]
        assert set(actual) == set(expected)


class TestMarketRegime:

    def test_all_regimes(self):
        expected = ["RISK_ON", "RISK_OFF", "TRANSITIONING", "CRISIS", "RECOVERY"]
        actual = [r.value for r in MarketRegime]
        assert set(actual) == set(expected)


# ═══════════════════════════════════════════════════════════════════════
# 4. Core Data Model Tests
# ═══════════════════════════════════════════════════════════════════════


class TestMarketDataModel:

    def test_valid_market_data(self):
        md = MarketData(symbol="AAPL", price=150.0)
        assert md.symbol == "AAPL"
        assert md.price == 150.0

    def test_default_values(self):
        md = MarketData(symbol="AAPL")
        assert md.open == 0.0
        assert md.high == 0.0
        assert md.low == 0.0
        assert md.close == 0.0
        assert md.volume == 0.0
        assert md.change_pct == 0.0
        assert md.bid is None
        assert md.ask is None
        assert md.vwap is None

    def test_extra_fields_allowed(self):
        md = MarketData(symbol="AAPL", price=150.0, custom_field="test")
        assert md.custom_field == "test"

    def test_serialization_round_trip(self):
        md = MarketData(symbol="AAPL", price=150.0, volume=1000.0)
        data = md.model_dump()
        md2 = MarketData(**data)
        assert md2.symbol == md.symbol
        assert md2.price == md.price
        assert md2.volume == md.volume

    def test_missing_symbol_rejected(self):
        with pytest.raises(ValidationError):
            MarketData(price=150.0)


class TestSignalModel:

    def test_valid_signal(self):
        signal = Signal(
            symbol="AAPL",
            direction=SignalDirection.BULLISH,
            action=TradeAction.BUY,
            confidence=0.8,
        )
        assert signal.symbol == "AAPL"
        assert signal.direction == SignalDirection.BULLISH
        assert signal.action == TradeAction.BUY
        assert signal.confidence == 0.8

    def test_confidence_out_of_range_high(self):
        with pytest.raises(ValidationError):
            Signal(
                symbol="AAPL",
                direction=SignalDirection.BULLISH,
                action=TradeAction.BUY,
                confidence=1.5,
            )

    def test_confidence_out_of_range_negative(self):
        with pytest.raises(ValidationError):
            Signal(
                symbol="AAPL",
                direction=SignalDirection.BULLISH,
                action=TradeAction.BUY,
                confidence=-0.1,
            )

    def test_confidence_boundary_zero(self):
        signal = Signal(
            symbol="AAPL",
            direction=SignalDirection.NEUTRAL,
            action=TradeAction.HOLD,
            confidence=0.0,
        )
        assert signal.confidence == 0.0

    def test_confidence_boundary_one(self):
        signal = Signal(
            symbol="AAPL",
            direction=SignalDirection.BULLISH,
            action=TradeAction.BUY,
            confidence=1.0,
        )
        assert signal.confidence == 1.0

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            Signal(symbol="AAPL")

    def test_optional_fields(self):
        signal = Signal(
            symbol="AAPL",
            direction=SignalDirection.BULLISH,
            action=TradeAction.BUY,
            confidence=0.8,
            entry_price=150.0,
            stop_loss=148.0,
            take_profit=155.0,
            timeframe="4h",
            risk_reward_ratio=3.5,
        )
        assert signal.entry_price == 150.0
        assert signal.stop_loss == 148.0
        assert signal.take_profit == 155.0
        assert signal.risk_reward_ratio == 3.5

    def test_serialization_round_trip(self):
        signal = Signal(
            symbol="AAPL",
            direction=SignalDirection.BULLISH,
            action=TradeAction.BUY,
            confidence=0.8,
        )
        data = signal.model_dump()
        signal2 = Signal(**data)
        assert signal2.symbol == signal.symbol
        assert signal2.direction == signal.direction
        assert signal2.confidence == signal.confidence


class TestDecisionModel:

    def test_valid_decision(self):
        d = Decision(
            symbol="AAPL",
            action=TradeAction.BUY,
            quantity=100.0,
            confidence=0.7,
        )
        assert d.action == TradeAction.BUY
        assert d.quantity == 100.0

    def test_default_values(self):
        d = Decision(
            symbol="AAPL",
            action=TradeAction.HOLD,
        )
        assert d.quantity == 0.0
        assert d.confidence == 0.0
        assert d.position_size_pct == 0.0
        assert d.reasoning == ""

    def test_confidence_validation(self):
        with pytest.raises(ValidationError):
            Decision(symbol="AAPL", action=TradeAction.BUY, confidence=2.0)


class TestRiskCheckpointModel:

    def test_valid_checkpoint(self):
        cp = RiskCheckpoint(
            name="risk_per_trade",
            value="0.005",
            limit="0.005",
            passed=True,
        )
        assert cp.passed is True
        assert cp.details == ""

    def test_failed_checkpoint(self):
        cp = RiskCheckpoint(
            name="daily_loss",
            value="0.02",
            limit="0.01",
            passed=False,
            details="Exceeded daily loss limit",
        )
        assert cp.passed is False
        assert cp.details == "Exceeded daily loss limit"

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            RiskCheckpoint(name="test")


class TestRiskAssessmentModel:

    def test_default_all_checks_pass(self):
        ra = StateRiskAssessment(verdict=RiskVerdict.VETOED)
        assert ra.verdict == RiskVerdict.VETOED
        assert ra.checkpoints == []
        assert ra.var_95 is None
        assert ra.var_99 is None
        assert ra.cvar_95 is None
        assert ra.max_drawdown is None
        assert ra.kelly_fraction is None
        assert ra.position_sizing_approved is False
        assert ra.correlation_risk is None
        assert ra.kill_switch_active is False
        assert ra.daily_pnl_pct == 0.0
        assert ra.weekly_pnl_pct == 0.0
        assert ra.trade_count_today == 0
        assert ra.override_possible is False

    def test_approved_assessment(self):
        ra = StateRiskAssessment(
            verdict=RiskVerdict.APPROVED,
            position_sizing_approved=True,
            var_95=-0.01,
        )
        assert ra.verdict == RiskVerdict.APPROVED

    def test_kill_switch_assessment(self):
        ra = StateRiskAssessment(
            verdict=RiskVerdict.KILL_SWITCH,
            kill_switch_active=True,
            daily_pnl_pct=-0.03,
        )
        assert ra.kill_switch_active is True

    def test_override_impossible(self):
        """Constitutional limits cannot be overridden."""
        ra = StateRiskAssessment(override_possible=False)
        assert ra.override_possible is False

    def test_with_checkpoints(self):
        checkpoints = [
            RiskCheckpoint(name="per_trade_risk", value="0.003", limit="0.005", passed=True),
            RiskCheckpoint(name="daily_loss", value="0.02", limit="0.01", passed=False),
        ]
        ra = StateRiskAssessment(
            verdict=RiskVerdict.VETOED,
            checkpoints=checkpoints,
        )
        assert len(ra.checkpoints) == 2
        assert ra.checkpoints[1].passed is False

    def test_serialization_round_trip(self):
        ra = StateRiskAssessment(
            verdict=RiskVerdict.APPROVED,
            var_95=-0.015,
            daily_pnl_pct=0.005,
        )
        data = ra.model_dump()
        ra2 = StateRiskAssessment(**data)
        assert ra2.verdict == ra.verdict
        assert ra2.var_95 == ra.var_95


class TestPortfolioStateModel:

    def test_default_portfolio_state(self):
        ps = PortfolioState()
        assert ps.total_value == 0.0
        assert ps.cash == 0.0
        assert ps.positions == {}
        assert ps.unrealized_pnl == 0.0
        assert ps.realized_pnl == 0.0

    def test_with_position(self):
        pos = PositionInfo(
            symbol="AAPL",
            quantity=100,
            entry_price=150.0,
            current_price=155.0,
        )
        ps = PortfolioState(
            total_value=100000,
            cash=84500,
            positions={"AAPL": pos},
        )
        assert "AAPL" in ps.positions
        assert ps.positions["AAPL"].quantity == 100


class TestPositionInfoModel:

    def test_valid_position(self):
        pi = PositionInfo(
            symbol="AAPL",
            quantity=100,
            entry_price=150.0,
            current_price=155.0,
        )
        assert pi.symbol == "AAPL"
        assert pi.direction == "LONG"

    def test_default_direction_long(self):
        pi = PositionInfo(symbol="AAPL")
        assert pi.direction == "LONG"


# ═══════════════════════════════════════════════════════════════════════
# 5. AgentOutput Model Tests
# ═══════════════════════════════════════════════════════════════════════


class TestAgentOutputModel:

    def test_valid_output(self):
        output = AgentOutput(
            agent_name="researcher",
            agent_role=AgentRole.RESEARCHER,
            content="Analysis complete",
            confidence=0.8,
        )
        assert output.agent_name == "researcher"
        assert output.agent_role == AgentRole.RESEARCHER
        assert output.confidence == 0.8
        assert output.success is True

    def test_failed_output(self):
        output = AgentOutput(
            agent_name="researcher",
            agent_role=AgentRole.RESEARCHER,
            content="Failed",
            success=False,
            error="API timeout",
        )
        assert output.success is False
        assert output.error == "API timeout"

    def test_confidence_validation(self):
        with pytest.raises(ValidationError):
            AgentOutput(
                agent_name="test",
                agent_role=AgentRole.RESEARCHER,
                confidence=1.5,
            )

    def test_confidence_negative_rejected(self):
        with pytest.raises(ValidationError):
            AgentOutput(
                agent_name="test",
                agent_role=AgentRole.RESEARCHER,
                confidence=-0.1,
            )

    def test_default_values(self):
        output = AgentOutput(
            agent_name="test",
            agent_role=AgentRole.TRADER,
        )
        assert output.content == ""
        assert output.data == {}
        assert output.confidence == 0.0
        assert output.success is True
        assert output.error is None
        assert output.tool_calls == []

    def test_serialization_round_trip(self):
        output = AgentOutput(
            agent_name="researcher",
            agent_role=AgentRole.RESEARCHER,
            content="Test",
            data={"key": "value"},
            confidence=0.7,
        )
        data = output.model_dump()
        output2 = AgentOutput(**data)
        assert output2.agent_name == output.agent_name
        assert output2.confidence == output.confidence
        assert output2.data == output.data

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            AgentOutput()


# ═══════════════════════════════════════════════════════════════════════
# 6. VoteResult and CouncilResult Tests
# ═══════════════════════════════════════════════════════════════════════


class TestVoteResultModel:

    def test_valid_vote(self):
        vote = VoteResult(
            voter="researcher",
            vote=TradeAction.BUY,
            reasoning="Strong momentum",
        )
        assert vote.voter == "researcher"
        assert vote.weight == 1.0
        assert vote.confidence == 0.0

    def test_vote_with_weight(self):
        vote = VoteResult(
            voter="strategist",
            vote=TradeAction.SELL,
            weight=2.5,
            confidence=0.9,
        )
        assert vote.weight == 2.5
        assert vote.confidence == 0.9


class TestCouncilResultModel:

    def test_default_hold(self):
        result = CouncilResult()
        assert result.final_decision == TradeAction.HOLD

    def test_buy_decision(self):
        result = CouncilResult(
            final_decision=TradeAction.BUY,
            consensus_level=0.8,
        )
        assert result.consensus_level == 0.8

    def test_requires_human_review(self):
        result = CouncilResult(requires_human_review=True)
        assert result.requires_human_review is True


# ═══════════════════════════════════════════════════════════════════════
# 7. Debate State Tests
# ═══════════════════════════════════════════════════════════════════════


class TestDebateState:

    def test_debate_state_structure(self):
        state = create_initial_state(["AAPL"], "2024-01-15")
        ds = state["debate_state"]
        assert "bull_history" in ds
        assert "bear_history" in ds
        assert "history" in ds
        assert "current_response" in ds
        assert "judge_decision" in ds
        assert "count" in ds


# ═══════════════════════════════════════════════════════════════════════
# 8. Agent Registry Tests
# ═══════════════════════════════════════════════════════════════════════


class TestAgentRegistry:

    def setup_method(self):
        """Clear registry before each test."""
        AgentRegistry.clear()

    def test_register_agent(self):
        mock_class = MagicMock()
        decorator = AgentRegistry.register("test_agent", AgentRole.RESEARCHER)
        decorated = decorator(mock_class)
        assert decorated is mock_class

    def test_get_registered_agent(self):
        mock_class = MagicMock()
        AgentRegistry.register("test_agent", AgentRole.RESEARCHER)(mock_class)
        result = AgentRegistry.get("test_agent")
        assert result is mock_class

    def test_get_nonexistent_agent(self):
        result = AgentRegistry.get("nonexistent")
        assert result is None

    def test_get_by_role(self):
        mock_class = MagicMock()
        AgentRegistry.register("researcher", AgentRole.RESEARCHER)(mock_class)
        result = AgentRegistry.get_by_role(AgentRole.RESEARCHER)
        assert result is mock_class

    def test_get_by_role_not_found(self):
        result = AgentRegistry.get_by_role(AgentRole.CRYPTO)
        assert result is None

    def test_list_agents(self):
        AgentRegistry.register("agent1", AgentRole.RESEARCHER)(MagicMock())
        AgentRegistry.register("agent2", AgentRole.TRADER)(MagicMock())
        agents = AgentRegistry.list_agents()
        assert "agent1" in agents
        assert "agent2" in agents
        assert len(agents) == 2

    def test_list_roles(self):
        AgentRegistry.register("researcher", AgentRole.RESEARCHER)(MagicMock())
        roles = AgentRegistry.list_roles()
        assert AgentRole.RESEARCHER in roles
        assert roles[AgentRole.RESEARCHER] == "researcher"

    def test_clear_registry(self):
        AgentRegistry.register("test", AgentRole.RESEARCHER)(MagicMock())
        AgentRegistry.clear()
        assert AgentRegistry.list_agents() == []
        assert AgentRegistry.list_roles() == {}

    def test_register_multiple_agents_same_role(self):
        """Last registration wins for the same role."""
        AgentRegistry.register("first", AgentRole.RESEARCHER)(MagicMock())
        mock_second = MagicMock()
        AgentRegistry.register("second", AgentRole.RESEARCHER)(mock_second)
        # Role mapping should point to last registered
        result = AgentRegistry.get_by_role(AgentRole.RESEARCHER)
        assert result is mock_second

    def test_register_preserves_class(self):
        """Decorator should return the original class unchanged."""
        class MyAgent(BaseAgent):
            def run(self, state):
                return {}

        decorated = AgentRegistry.register("my_agent", AgentRole.TRADER)(MyAgent)
        assert decorated is MyAgent


# ═══════════════════════════════════════════════════════════════════════
# 9. Agent Factory Tests
# ═══════════════════════════════════════════════════════════════════════


class TestAgentFactory:

    def setup_method(self):
        AgentRegistry.clear()

    def test_factory_creation(self):
        factory = AgentFactory(
            llm_provider="openai",
            deep_think_model="gpt-4o",
            quick_think_model="gpt-4o-mini",
            api_key="<placeholder>",
        )
        assert factory.llm_provider == "openai"
        assert factory.deep_think_model == "gpt-4o"
        assert factory.quick_think_model == "gpt-4o-mini"

    def test_create_unregistered_agent_raises(self):
        factory = AgentFactory(api_key="<placeholder>")
        with pytest.raises(ValueError, match="not registered"):
            factory.create_agent("nonexistent")

    @patch("quant_nanggroe.agents.base.create_llm")
    def test_create_registered_agent(self, mock_create_llm):
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm

        class TestAgent(BaseAgent):
            def run(self, state):
                return {}

        AgentRegistry.register("test_agent", AgentRole.RESEARCHER)(TestAgent)

        factory = AgentFactory(
            llm_provider="openai",
            api_key="<placeholder>",
        )
        agent = factory.create_agent("test_agent")
        assert isinstance(agent, BaseAgent)
        assert agent.name == "test_agent"
        assert agent.role == AgentRole.RESEARCHER

    @patch("quant_nanggroe.agents.registry.create_llm")
    def test_deep_llm_creation(self, mock_create_llm):
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm

        factory = AgentFactory(
            llm_provider="openai",
            deep_think_model="gpt-4o",
            quick_think_model="gpt-4o-mini",
            api_key="<placeholder>",
        )
        llm = factory.get_deep_llm()
        assert mock_create_llm.called
        mock_create_llm.assert_called_with(
            provider="openai",
            model="gpt-4o",
            base_url=None,
            api_key="<placeholder>",
            temperature=0.0,
        )

    @patch("quant_nanggroe.agents.registry.create_llm")
    def test_quick_llm_creation(self, mock_create_llm):
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm

        factory = AgentFactory(
            llm_provider="openai",
            quick_think_model="gpt-4o-mini",
            api_key="<placeholder>",
        )
        llm = factory.get_quick_llm()
        assert mock_create_llm.called

    @patch("quant_nanggroe.agents.registry.create_llm")
    def test_llm_lazy_initialization(self, mock_create_llm):
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm

        factory = AgentFactory(api_key="<placeholder>")
        # LLM should not be created until requested
        assert factory._deep_llm is None
        assert factory._quick_llm is None

    @patch("quant_nanggroe.agents.registry.create_llm")
    def test_llm_cached(self, mock_create_llm):
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm

        factory = AgentFactory(api_key="<placeholder>")
        llm1 = factory.get_deep_llm()
        llm2 = factory.get_deep_llm()
        # Should only call create_llm once
        assert mock_create_llm.call_count == 1
        assert llm1 is llm2

    @patch("quant_nanggroe.agents.registry.create_llm")
    def test_create_agent_with_deep_llm(self, mock_create_llm):
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm

        class TestAgent(BaseAgent):
            def run(self, state):
                return {}

        AgentRegistry.register("test_agent", AgentRole.RESEARCHER)(TestAgent)

        factory = AgentFactory(api_key="<placeholder>")
        agent = factory.create_agent("test_agent", use_deep_llm=True)
        assert isinstance(agent, BaseAgent)


# ═══════════════════════════════════════════════════════════════════════
# 10. Base Agent Tests (Mocked LLM)
# ═══════════════════════════════════════════════════════════════════════


class TestBaseAgent:

    def _make_agent(self, name="test_agent", role=AgentRole.RESEARCHER, **kwargs):
        """Helper to create a concrete agent with mocked LLM."""
        mock_llm = MagicMock()

        class TestAgent(BaseAgent):
            def run(self, state):
                return {"research_output": "done"}

        return TestAgent(
            name=name,
            role=role,
            description="Test agent",
            llm=mock_llm,
            **kwargs,
        )

    def test_agent_creation(self):
        agent = self._make_agent()
        assert agent.name == "test_agent"
        assert agent.role == AgentRole.RESEARCHER
        assert agent.description == "Test agent"

    def test_agent_properties(self):
        agent = self._make_agent()
        assert isinstance(agent.llm, MagicMock)
        assert agent.tools == []
        assert agent.tool_node is None

    def test_agent_run(self):
        agent = self._make_agent()
        state = create_initial_state(["AAPL"], "2024-01-15")
        result = agent(state)
        assert "research_output" in result

    def test_agent_error_handling(self):
        """Agent __call__ should handle exceptions gracefully."""
        mock_llm = MagicMock()

        class FailingAgent(BaseAgent):
            def run(self, state):
                raise RuntimeError("Agent failed")

        agent = FailingAgent(
            name="failing_agent",
            role=AgentRole.RESEARCHER,
            description="Fails",
            llm=mock_llm,
        )
        state = create_initial_state(["AAPL"], "2024-01-15")
        result = agent(state)
        # Should not raise, but include error output
        assert "agent_outputs" in result
        assert "failing_agent" in result["agent_outputs"]
        assert result["agent_outputs"]["failing_agent"]["success"] is False

    def test_agent_create_output(self):
        agent = self._make_agent(name="test")
        output = agent.create_output(
            content="Test output",
            confidence=0.9,
        )
        assert isinstance(output, AgentOutput)
        assert output.agent_name == "test"
        assert output.confidence == 0.9
        assert output.success is True

    def test_agent_create_output_with_error(self):
        agent = self._make_agent(name="test")
        output = agent.create_output(
            content="Failed",
            success=False,
            error="Something went wrong",
        )
        assert output.success is False
        assert output.error == "Something went wrong"

    def test_agent_format_state_for_prompt(self):
        agent = self._make_agent()
        state = create_initial_state(["AAPL"], "2024-01-15")
        formatted = agent.format_state_for_prompt(state)
        assert "AAPL" in formatted
        assert "2024-01-15" in formatted

    def test_agent_format_state_with_market_data(self):
        agent = self._make_agent()
        state = create_initial_state(["AAPL"], "2024-01-15")
        state["market_data"] = {
            "AAPL": {"price": 150.0, "change_pct": 1.5},
        }
        formatted = agent.format_state_for_prompt(state)
        assert "150" in formatted

    def test_agent_format_state_with_agent_outputs(self):
        agent = self._make_agent()
        state = create_initial_state(["AAPL"], "2024-01-15")
        state["agent_outputs"] = {
            "researcher": {"content": "Strong bullish signal"},
        }
        formatted = agent.format_state_for_prompt(state)
        assert "researcher" in formatted

    def test_agent_default_system_prompt(self):
        mock_llm = MagicMock()

        class TestAgent(BaseAgent):
            def run(self, state):
                return {}

        agent = TestAgent(
            name="test",
            role=AgentRole.RESEARCHER,
            description="Does research",
            llm=mock_llm,
        )
        prompt = agent.default_system_prompt()
        assert "test" in prompt
        assert "researcher" in prompt
        assert "Quant Nanggroe" in prompt

    def test_agent_custom_system_prompt(self):
        mock_llm = MagicMock()

        class TestAgent(BaseAgent):
            def run(self, state):
                return {}

        agent = TestAgent(
            name="test",
            role=AgentRole.RESEARCHER,
            description="Test",
            llm=mock_llm,
            system_prompt="Custom prompt",
        )
        assert agent._system_prompt == "Custom prompt"

    def test_agent_with_tools(self):
        mock_llm = MagicMock()

        # Create a proper LangChain tool instead of MagicMock
        from langchain_core.tools import tool

        @tool
        def test_tool(query: str) -> str:
            """A test tool."""
            return f"Result for: {query}"

        class TestAgent(BaseAgent):
            def run(self, state):
                return {}

        agent = TestAgent(
            name="test",
            role=AgentRole.RESEARCHER,
            description="Test",
            llm=mock_llm,
            tools=[test_tool],
        )
        assert len(agent.tools) == 1
        assert agent.tool_node is not None
        mock_llm.bind_tools.assert_called_once_with([test_tool])

    def test_agent_invoke_llm(self):
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_llm.invoke.return_value = mock_response

        class TestAgent(BaseAgent):
            def run(self, state):
                return {}

        agent = TestAgent(
            name="test",
            role=AgentRole.RESEARCHER,
            description="Test",
            llm=mock_llm,
        )
        from langchain_core.messages import HumanMessage
        messages = [HumanMessage(content="Test")]
        response = agent.invoke_llm(messages)
        mock_llm.invoke.assert_called_once_with(messages)
        assert response is mock_response

    def test_agent_build_messages(self):
        mock_llm = MagicMock()

        class TestAgent(BaseAgent):
            def run(self, state):
                return {}

        agent = TestAgent(
            name="test",
            role=AgentRole.RESEARCHER,
            description="Test",
            llm=mock_llm,
        )
        state = create_initial_state(["AAPL"], "2024-01-15")
        messages = agent.build_messages(state, user_content="What do you think?")
        assert len(messages) == 3  # System + Context + User
        assert messages[0].type == "system"
        assert messages[2].content == "What do you think?"

    def test_agent_repr(self):
        agent = self._make_agent()
        repr_str = repr(agent)
        assert "TestAgent" in repr_str
        assert "test_agent" in repr_str
        assert "researcher" in repr_str


# ═══════════════════════════════════════════════════════════════════════
# 11. create_llm Function Tests
# ═══════════════════════════════════════════════════════════════════════


class TestCreateLLM:

    @patch("quant_nanggroe.agents.base.ChatOpenAI")
    def test_openai_provider(self, mock_chat_openai):
        mock_instance = MagicMock()
        mock_chat_openai.return_value = mock_instance
        result = create_llm(provider="openai", model="gpt-4o", api_key="<placeholder>")
        mock_chat_openai.assert_called_once()
        assert result is mock_instance

    @patch("quant_nanggroe.agents.base.ChatOpenAI")
    def test_ollama_provider(self, mock_chat_openai):
        mock_instance = MagicMock()
        mock_chat_openai.return_value = mock_instance
        result = create_llm(provider="ollama", model="llama3", base_url="http://localhost:11434")
        mock_chat_openai.assert_called_once()

    @patch("quant_nanggroe.agents.base.ChatOpenAI")
    def test_openrouter_provider(self, mock_chat_openai):
        mock_instance = MagicMock()
        mock_chat_openai.return_value = mock_instance
        result = create_llm(provider="openrouter", model="auto", api_key="<placeholder>")
        mock_chat_openai.assert_called_once()

    @patch("quant_nanggroe.agents.base.ChatAnthropic")
    def test_anthropic_provider(self, mock_chat_anthropic):
        mock_instance = MagicMock()
        mock_chat_anthropic.return_value = mock_instance
        result = create_llm(provider="anthropic", model="claude-3", api_key="<placeholder>")
        mock_chat_anthropic.assert_called_once()

    @patch("quant_nanggroe.agents.base.ChatGoogleGenerativeAI")
    def test_google_provider(self, mock_chat_google):
        mock_instance = MagicMock()
        mock_chat_google.return_value = mock_instance
        result = create_llm(provider="google", model="gemini-pro", api_key="<placeholder>")
        mock_chat_google.assert_called_once()

    def test_unsupported_provider_raises(self):
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            create_llm(provider="invalid_provider", model="test")

    @patch("quant_nanggroe.agents.base.ChatOpenAI")
    def test_case_insensitive_provider(self, mock_chat_openai):
        mock_instance = MagicMock()
        mock_chat_openai.return_value = mock_instance
        result = create_llm(provider="OpenAI", model="gpt-4o", api_key="<placeholder>")
        mock_chat_openai.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════
# 12. Constitutional Limits Consistency Tests
# ═══════════════════════════════════════════════════════════════════════


class TestConstitutionalLimits:
    """Verify constitutional limit values are correctly set."""

    # ponytail: demo tier (default) scales four live limits 10x (risk/daily/weekly/drawdown)
    _tier_scale = 10.0 if get_settings().risk_tier == "demo" else 1.0

    def test_max_risk_per_trade(self):
        assert MAX_RISK_PER_TRADE == 0.005 * self._tier_scale

    def test_max_daily_loss(self):
        assert MAX_DAILY_LOSS == 0.01 * self._tier_scale

    def test_max_weekly_loss(self):
        assert MAX_WEEKLY_LOSS == 0.03 * self._tier_scale

    def test_min_risk_reward(self):
        assert MIN_RISK_REWARD == 2.0

    def test_max_correlated_positions(self):
        assert MAX_CORRELATED_POSITIONS == 3

    def test_max_position_size_pct(self):
        assert MAX_POSITION_SIZE_PCT == 0.10

    def test_max_leverage(self):
        assert MAX_LEVERAGE == 3.0

    def test_max_drawdown_pct(self):
        assert MAX_DRAWDOWN_PCT == 0.10 * self._tier_scale  # engine constants: 10% max drawdown

    def test_max_trades_per_day(self):
        assert MAX_TRADES_PER_DAY == 5

    def test_confidence_threshold(self):
        assert CONFIDENCE_THRESHOLD == 0.65

    def test_kill_switch_daily_pnl(self):
        # Kill switch triggers at -0.8% (early warning before 1% hard limit)
        assert KILL_SWITCH_DAILY_PNL == -0.008

    def test_kill_switch_weekly_pnl(self):
        # Kill switch triggers at -2.5% (early warning before 3% hard limit)
        assert KILL_SWITCH_WEEKLY_PNL == -0.025

    def test_limits_in_initial_state(self):
        """Verify constitutional limits are embedded in the initial state."""
        state = create_initial_state(["AAPL"], "2024-01-15")
        limits = state["metadata"]["constitutional_limits"]
        assert limits["max_risk_per_trade"] == 0.005 * self._tier_scale
        assert limits["override_possible"] is False
