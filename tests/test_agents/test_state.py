"""
Tests for Agent State Models.

Validates all Pydantic models, TypedDict classes, and constitutional
limits defined in the state module.
"""

import pytest
from datetime import datetime

from quant_nanggroe.agents.state import (
    AgentOutput,
    AgentRole,
    CouncilResult,
    Decision,
    DebateState,
    MarketData,
    MarketRegime,
    PortfolioState,
    PositionInfo,
    RiskAssessment,
    RiskCheckpoint,
    RiskDebateState,
    RiskVerdict,
    Signal,
    SignalDirection,
    TradeAction,
    VoteResult,
    create_initial_state,
    # Constitutional limits
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


class TestConstitutionalLimits:
    """Test that constitutional limits are properly defined and immutable."""

    def test_max_risk_per_trade(self):
        """Max risk per trade should be 0.5%."""
        assert MAX_RISK_PER_TRADE == 0.005

    def test_max_daily_loss(self):
        """Max daily loss should be 1%."""
        assert MAX_DAILY_LOSS == 0.01

    def test_max_weekly_loss(self):
        """Max weekly loss should be 3%."""
        assert MAX_WEEKLY_LOSS == 0.03

    def test_min_risk_reward(self):
        """Min risk:reward should be 1:2."""
        assert MIN_RISK_REWARD == 2.0

    def test_max_correlated_positions(self):
        """Max correlated positions should be 3."""
        assert MAX_CORRELATED_POSITIONS == 3

    def test_max_position_size(self):
        """Max position size should be 10%."""
        assert MAX_POSITION_SIZE_PCT == 0.10

    def test_max_leverage(self):
        """Max leverage should be 3x."""
        assert MAX_LEVERAGE == 3.0

    def test_max_drawdown(self):
        """Max drawdown should be 15%."""
        assert MAX_DRAWDOWN_PCT == 0.15

    def test_max_trades_per_day(self):
        """Max trades per day should be 5."""
        assert MAX_TRADES_PER_DAY == 5

    def test_confidence_threshold(self):
        """Confidence threshold should be 0.65."""
        assert CONFIDENCE_THRESHOLD == 0.65

    def test_kill_switch_daily(self):
        """Kill switch daily threshold should be -2%."""
        assert KILL_SWITCH_DAILY_PNL == -0.02

    def test_kill_switch_weekly(self):
        """Kill switch weekly threshold should be -5%."""
        assert KILL_SWITCH_WEEKLY_PNL == -0.05


class TestEnumerations:
    """Test enum definitions."""

    def test_trade_actions(self):
        """All trade actions should be defined."""
        assert TradeAction.BUY.value == "BUY"
        assert TradeAction.SELL.value == "SELL"
        assert TradeAction.HOLD.value == "HOLD"
        assert TradeAction.CLOSE.value == "CLOSE"
        assert TradeAction.EMERGENCY_EXIT.value == "EMERGENCY_EXIT"

    def test_signal_directions(self):
        """All signal directions should be defined."""
        assert SignalDirection.BULLISH.value == "BULLISH"
        assert SignalDirection.BEARISH.value == "BEARISH"
        assert SignalDirection.NEUTRAL.value == "NEUTRAL"

    def test_risk_verdicts(self):
        """All risk verdicts should be defined."""
        assert RiskVerdict.APPROVED.value == "APPROVED"
        assert RiskVerdict.VETOED.value == "VETOED"
        assert RiskVerdict.CONDITIONAL.value == "CONDITIONAL"
        assert RiskVerdict.KILL_SWITCH.value == "KILL_SWITCH"

    def test_market_regimes(self):
        """All market regimes should be defined."""
        assert MarketRegime.RISK_ON.value == "RISK_ON"
        assert MarketRegime.RISK_OFF.value == "RISK_OFF"
        assert MarketRegime.CRISIS.value == "CRISIS"
        assert MarketRegime.RECOVERY.value == "RECOVERY"
        assert MarketRegime.TRANSITIONING.value == "TRANSITIONING"

    def test_agent_roles(self):
        """All agent roles should be defined."""
        assert AgentRole.RESEARCHER.value == "researcher"
        assert AgentRole.TRADER.value == "trader"
        assert AgentRole.STRATEGIST.value == "strategist"
        assert AgentRole.RISK.value == "risk"
        assert AgentRole.PORTFOLIO.value == "portfolio"
        assert AgentRole.EXECUTION.value == "execution"
        assert AgentRole.MACRO.value == "macro"
        assert AgentRole.CRYPTO.value == "crypto"
        assert AgentRole.FOREX.value == "forex"
        assert AgentRole.COUNCIL.value == "council"


class TestMarketData:
    """Test MarketData model."""

    def test_basic_creation(self):
        """Should create MarketData with required fields."""
        md = MarketData(symbol="AAPL", price=150.0)
        assert md.symbol == "AAPL"
        assert md.price == 150.0

    def test_full_creation(self):
        """Should create MarketData with all fields."""
        md = MarketData(
            symbol="BTCUSDT",
            price=45000.0,
            open=44800.0,
            high=45500.0,
            low=44700.0,
            close=45000.0,
            volume=12345.6,
            change_pct=2.5,
            bid=44999.0,
            ask=45001.0,
        )
        assert md.symbol == "BTCUSDT"
        assert md.high == 45500.0
        assert md.change_pct == 2.5

    def test_default_values(self):
        """Default values should be set correctly."""
        md = MarketData(symbol="ETHUSDT")
        assert md.price == 0.0
        assert md.volume == 0.0
        assert md.bid is None


class TestSignal:
    """Test Signal model."""

    def test_basic_creation(self):
        """Should create Signal with required fields."""
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

    def test_confidence_range(self):
        """Confidence should be bounded between 0 and 1."""
        # Valid
        Signal(symbol="AAPL", direction=SignalDirection.NEUTRAL, action=TradeAction.HOLD, confidence=0.0)
        Signal(symbol="AAPL", direction=SignalDirection.NEUTRAL, action=TradeAction.HOLD, confidence=1.0)

        # Invalid - should raise
        with pytest.raises(Exception):
            Signal(symbol="AAPL", direction=SignalDirection.NEUTRAL, action=TradeAction.HOLD, confidence=1.5)
        with pytest.raises(Exception):
            Signal(symbol="AAPL", direction=SignalDirection.NEUTRAL, action=TradeAction.HOLD, confidence=-0.1)

    def test_with_risk_management(self):
        """Signal should support entry/SL/TP."""
        signal = Signal(
            symbol="AAPL",
            direction=SignalDirection.BULLISH,
            action=TradeAction.BUY,
            confidence=0.75,
            entry_price=150.0,
            stop_loss=145.0,
            take_profit=160.0,
            risk_reward_ratio=2.0,
        )
        assert signal.entry_price == 150.0
        assert signal.stop_loss == 145.0
        assert signal.take_profit == 160.0
        assert signal.risk_reward_ratio == 2.0


class TestDecision:
    """Test Decision model."""

    def test_basic_creation(self):
        """Should create Decision with required fields."""
        decision = Decision(
            symbol="AAPL",
            action=TradeAction.BUY,
            confidence=0.8,
        )
        assert decision.symbol == "AAPL"
        assert decision.action == TradeAction.BUY

    def test_confidence_range(self):
        """Decision confidence should be bounded."""
        with pytest.raises(Exception):
            Decision(symbol="AAPL", action=TradeAction.BUY, confidence=2.0)


class TestRiskCheckpoint:
    """Test RiskCheckpoint model."""

    def test_passing_checkpoint(self):
        """Should create a passing checkpoint."""
        cp = RiskCheckpoint(
            name="1_risk_per_trade",
            value="0.0030",
            limit="0.0050",
            passed=True,
        )
        assert cp.passed is True

    def test_failing_checkpoint(self):
        """Should create a failing checkpoint."""
        cp = RiskCheckpoint(
            name="4_risk_reward",
            value="1:1.5",
            limit="1:2.0",
            passed=False,
            details="Risk:reward ratio below minimum",
        )
        assert cp.passed is False
        assert "below minimum" in cp.details


class TestRiskAssessment:
    """Test RiskAssessment model."""

    def test_default_vetoed(self):
        """Default verdict should be VETOED (safe default)."""
        assessment = RiskAssessment()
        assert assessment.verdict == RiskVerdict.VETOED

    def test_approved_assessment(self):
        """Should create an approved assessment."""
        assessment = RiskAssessment(
            verdict=RiskVerdict.APPROVED,
            position_sizing_approved=True,
            override_possible=False,
        )
        assert assessment.verdict == RiskVerdict.APPROVED
        assert assessment.override_possible is False

    def test_kill_switch_assessment(self):
        """Should create a kill switch assessment."""
        assessment = RiskAssessment(
            verdict=RiskVerdict.KILL_SWITCH,
            kill_switch_active=True,
            override_possible=False,
        )
        assert assessment.kill_switch_active is True
        assert assessment.override_possible is False


class TestPortfolioState:
    """Test PortfolioState model."""

    def test_basic_creation(self):
        """Should create PortfolioState."""
        ps = PortfolioState(total_value=100000.0, cash=50000.0)
        assert ps.total_value == 100000.0
        assert ps.cash == 50000.0

    def test_default_values(self):
        """Default values should be zero/empty."""
        ps = PortfolioState()
        assert ps.total_value == 0.0
        assert ps.positions == {}
        assert ps.open_orders == []


class TestAgentOutput:
    """Test AgentOutput model."""

    def test_basic_creation(self):
        """Should create AgentOutput."""
        output = AgentOutput(
            agent_name="researcher",
            agent_role=AgentRole.RESEARCHER,
            content="Analysis complete",
            confidence=0.8,
        )
        assert output.agent_name == "researcher"
        assert output.agent_role == AgentRole.RESEARCHER
        assert output.success is True
        assert output.error is None


class TestVoteResult:
    """Test VoteResult model."""

    def test_basic_creation(self):
        """Should create VoteResult."""
        vote = VoteResult(
            voter="researcher",
            vote=TradeAction.BUY,
            weight=1.2,
            confidence=0.8,
        )
        assert vote.voter == "researcher"
        assert vote.vote == TradeAction.BUY
        assert vote.weight == 1.2


class TestCouncilResult:
    """Test CouncilResult model."""

    def test_basic_creation(self):
        """Should create CouncilResult."""
        result = CouncilResult()
        assert result.final_decision == TradeAction.HOLD
        assert result.consensus_level == 0.0
        assert result.requires_human_review is False


class TestCreateInitialState:
    """Test the create_initial_state function."""

    def test_basic_creation(self):
        """Should create initial state with required fields."""
        state = create_initial_state(["AAPL", "MSFT"], "2025-03-01")
        assert state["symbols"] == ["AAPL", "MSFT"]
        assert state["trade_date"] == "2025-03-01"
        assert state["iteration"] == 0
        assert state["kill_switch_active"] is False
        assert state["should_halt"] is False

    def test_default_values(self):
        """Initial state should have proper defaults."""
        state = create_initial_state(["AAPL"], "2025-03-01")
        assert state["signals"] == []
        assert state["decisions"] == []
        assert state["orders_placed"] == []
        assert state["confidence"] == 0.0
        assert state["research_output"] == ""
        assert state["risk_verdict"] == RiskVerdict.VETOED.value

    def test_constitutional_limits_in_metadata(self):
        """Constitutional limits should be stored in metadata."""
        state = create_initial_state(["AAPL"], "2025-03-01")
        limits = state["metadata"]["constitutional_limits"]
        assert limits["max_risk_per_trade"] == MAX_RISK_PER_TRADE
        assert limits["max_daily_loss"] == MAX_DAILY_LOSS
        assert limits["override_possible"] is False

    def test_debate_state_initialized(self):
        """Debate state should be properly initialized."""
        state = create_initial_state(["AAPL"], "2025-03-01")
        debate = state["debate_state"]
        assert debate["bull_history"] == ""
        assert debate["count"] == 0
        assert debate["judge_decision"] == ""


class TestDebateState:
    """Test DebateState TypedDict."""

    def test_creation(self):
        """Should create a DebateState."""
        state: DebateState = {
            "bull_history": "Bull argues growth",
            "bear_history": "Bear argues risk",
            "history": "Full debate",
            "current_response": "Bull Analyst: Growth is strong",
            "judge_decision": "",
            "count": 2,
        }
        assert state["count"] == 2
        assert "Bull" in state["bull_history"]


class TestRiskDebateState:
    """Test RiskDebateState TypedDict."""

    def test_creation(self):
        """Should create a RiskDebateState."""
        state: RiskDebateState = {
            "conservative_history": "Protect assets",
            "neutral_history": "Balanced view",
            "aggressive_history": "Maximize returns",
            "history": "Full debate",
            "latest_speaker": "Conservative",
            "current_conservative_response": "Safe Analyst: Protect",
            "current_neutral_response": "Neutral Analyst: Balance",
            "current_aggressive_response": "Risky Analyst: Grow",
            "judge_decision": "",
            "count": 3,
        }
        assert state["count"] == 3
        assert state["latest_speaker"] == "Conservative"
