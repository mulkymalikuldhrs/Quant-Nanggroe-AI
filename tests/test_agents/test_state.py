"""Comprehensive tests for Agent State module.

Tests:
- All enum values (TradeAction, SignalDirection, RiskVerdict, MarketRegime, AgentRole)
- Pydantic model validation (MarketData, Signal, Decision, RiskCheckpoint, etc.)
- create_initial_state function
- Constitutional constants defined in state.py
- TypedDict state structure
"""

from __future__ import annotations

import pytest
from datetime import datetime
from pydantic import ValidationError

from quant_nanggroe.agents.state import (
    TradeAction, SignalDirection, RiskVerdict, MarketRegime, AgentRole,
    MarketData, Signal, Decision, RiskCheckpoint, RiskAssessment,
    PortfolioState, PositionInfo, AgentOutput, DebateState, RiskDebateState,
    VoteResult, CouncilResult,
    AgentState,
    create_initial_state,
    MAX_RISK_PER_TRADE, MAX_DAILY_LOSS, MAX_WEEKLY_LOSS,
    MIN_RISK_REWARD, MAX_CORRELATED_POSITIONS,
    MAX_POSITION_SIZE_PCT, MAX_LEVERAGE, MAX_DRAWDOWN_PCT,
    MAX_TRADES_PER_DAY, CONFIDENCE_THRESHOLD,
)


# ═══════════════════════════════════════════════════════════════════════════
# Enum Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestTradeAction:
    def test_values(self):
        assert TradeAction.BUY.value == "BUY"
        assert TradeAction.SELL.value == "SELL"
        assert TradeAction.HOLD.value == "HOLD"
        assert TradeAction.CLOSE.value == "CLOSE"
        assert TradeAction.EMERGENCY_EXIT.value == "EMERGENCY_EXIT"

    def test_string_enum(self):
        assert TradeAction.BUY == "BUY"
        assert isinstance(TradeAction.BUY, str)

    def test_all_members(self):
        assert len(TradeAction) == 5

    def test_from_value(self):
        assert TradeAction("BUY") == TradeAction.BUY


class TestSignalDirection:
    def test_values(self):
        assert SignalDirection.BULLISH.value == "BULLISH"
        assert SignalDirection.BEARISH.value == "BEARISH"
        assert SignalDirection.NEUTRAL.value == "NEUTRAL"

    def test_all_members(self):
        assert len(SignalDirection) == 3


class TestRiskVerdict:
    def test_values(self):
        assert RiskVerdict.APPROVED.value == "APPROVED"
        assert RiskVerdict.VETOED.value == "VETOED"
        assert RiskVerdict.CONDITIONAL.value == "CONDITIONAL"
        assert RiskVerdict.KILL_SWITCH.value == "KILL_SWITCH"

    def test_all_members(self):
        assert len(RiskVerdict) == 4


class TestMarketRegime:
    def test_values(self):
        assert MarketRegime.RISK_ON.value == "RISK_ON"
        assert MarketRegime.RISK_OFF.value == "RISK_OFF"
        assert MarketRegime.TRANSITIONING.value == "TRANSITIONING"
        assert MarketRegime.CRISIS.value == "CRISIS"
        assert MarketRegime.RECOVERY.value == "RECOVERY"

    def test_all_members(self):
        assert len(MarketRegime) == 5


class TestAgentRole:
    def test_values(self):
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

    def test_all_members(self):
        assert len(AgentRole) == 11  # Added PREDICTION_MARKET role


# ═══════════════════════════════════════════════════════════════════════════
# Pydantic Model Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestMarketDataModel:
    def test_create_with_defaults(self):
        md = MarketData(symbol="BTC/USDT")
        assert md.symbol == "BTC/USDT"
        assert md.price == 0.0
        assert md.volume == 0.0
        assert md.timestamp is not None

    def test_create_with_all_fields(self):
        md = MarketData(
            symbol="BTC/USDT", price=50000.0, open=49500.0,
            high=50500.0, low=49000.0, close=50200.0,
            volume=1000.0, change_pct=2.5,
            bid=50100.0, ask=50200.0, vwap=50150.0,
        )
        assert md.price == 50000.0
        assert md.bid == 50100.0

    def test_extra_fields_allowed(self):
        md = MarketData(symbol="BTC/USDT", custom_field="test")
        assert md.custom_field == "test"

    def test_symbol_required(self):
        with pytest.raises(ValidationError):
            MarketData()


class TestSignalModel:
    def test_create_basic(self):
        signal = Signal(
            symbol="BTC/USDT",
            direction=SignalDirection.BULLISH,
            action=TradeAction.BUY,
            confidence=0.8,
        )
        assert signal.symbol == "BTC/USDT"
        assert signal.confidence == 0.8

    def test_confidence_range_validation(self):
        with pytest.raises(ValidationError):
            Signal(
                symbol="BTC/USDT",
                direction=SignalDirection.BULLISH,
                action=TradeAction.BUY,
                confidence=1.5,  # Out of range
            )

    def test_confidence_zero(self):
        signal = Signal(
            symbol="BTC/USDT",
            direction=SignalDirection.NEUTRAL,
            action=TradeAction.HOLD,
            confidence=0.0,
        )
        assert signal.confidence == 0.0

    def test_with_optional_fields(self):
        signal = Signal(
            symbol="BTC/USDT",
            direction=SignalDirection.BULLISH,
            action=TradeAction.BUY,
            confidence=0.8,
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit=52000.0,
            risk_reward_ratio=2.0,
        )
        assert signal.risk_reward_ratio == 2.0


class TestDecisionModel:
    def test_create_basic(self):
        decision = Decision(
            symbol="BTC/USDT",
            action=TradeAction.BUY,
        )
        assert decision.symbol == "BTC/USDT"
        assert decision.confidence == 0.0

    def test_confidence_validation(self):
        with pytest.raises(ValidationError):
            Decision(symbol="BTC/USDT", action=TradeAction.BUY, confidence=-0.1)

    def test_with_all_fields(self):
        decision = Decision(
            symbol="BTC/USDT",
            action=TradeAction.BUY,
            quantity=0.5,
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit=52000.0,
            confidence=0.85,
            position_size_pct=0.05,
        )
        assert decision.quantity == 0.5


class TestRiskCheckpointModel:
    def test_create(self):
        cp = RiskCheckpoint(
            name="per_trade_risk",
            value="0.0040",
            limit="0.0050",
            passed=True,
        )
        assert cp.passed is True

    def test_failed_checkpoint(self):
        cp = RiskCheckpoint(
            name="daily_loss",
            value="0.0150",
            limit="0.0100",
            passed=False,
            details="Daily loss exceeds 1% limit",
        )
        assert cp.passed is False


class TestRiskAssessmentModel:
    def test_create_default(self):
        ra = RiskAssessment()
        assert ra.verdict == RiskVerdict.VETOED
        assert ra.checkpoints == []
        assert ra.kill_switch_active is False
        assert ra.override_possible is False

    def test_with_checkpoints(self):
        ra = RiskAssessment(
            verdict=RiskVerdict.APPROVED,
            checkpoints=[
                RiskCheckpoint(name="test", value="ok", limit="ok", passed=True),
            ],
        )
        assert len(ra.checkpoints) == 1


class TestPositionInfoModel:
    def test_create(self):
        pi = PositionInfo(
            symbol="BTC/USDT",
            quantity=0.5,
            entry_price=50000.0,
            current_price=51000.0,
        )
        assert pi.quantity == 0.5

    def test_direction_default(self):
        pi = PositionInfo(symbol="BTC/USDT", quantity=0.5, entry_price=50000.0, current_price=51000.0)
        assert pi.direction == "LONG"


class TestPortfolioStateModel:
    def test_create_default(self):
        ps = PortfolioState()
        assert ps.total_value == 0.0
        assert ps.positions == {}

    def test_with_positions(self):
        ps = PortfolioState(
            total_value=100_000.0,
            cash=50_000.0,
            positions={
                "BTC/USDT": PositionInfo(
                    symbol="BTC/USDT", quantity=0.5,
                    entry_price=50000.0, current_price=51000.0,
                ),
            },
        )
        assert len(ps.positions) == 1


class TestAgentOutputModel:
    def test_create(self):
        ao = AgentOutput(
            agent_name="researcher",
            agent_role=AgentRole.RESEARCHER,
            content="Analysis complete",
            confidence=0.8,
        )
        assert ao.agent_name == "researcher"
        assert ao.confidence == 0.8

    def test_confidence_validation(self):
        with pytest.raises(ValidationError):
            AgentOutput(
                agent_name="researcher",
                agent_role=AgentRole.RESEARCHER,
                confidence=2.0,
            )

    def test_default_success(self):
        ao = AgentOutput(
            agent_name="researcher",
            agent_role=AgentRole.RESEARCHER,
        )
        assert ao.success is True


class TestVoteResultModel:
    def test_create(self):
        vr = VoteResult(
            voter="researcher",
            vote=TradeAction.BUY,
            weight=1.5,
        )
        assert vr.weight == 1.5


class TestCouncilResultModel:
    def test_create_default(self):
        cr = CouncilResult()
        assert cr.final_decision == TradeAction.HOLD
        assert cr.consensus_level == 0.0

    def test_with_votes(self):
        cr = CouncilResult(
            final_decision=TradeAction.BUY,
            votes=[
                VoteResult(voter="researcher", vote=TradeAction.BUY, weight=1.0),
                VoteResult(voter="risk", vote=TradeAction.HOLD, weight=1.5),
            ],
            consensus_level=0.7,
        )
        assert len(cr.votes) == 2


# ═══════════════════════════════════════════════════════════════════════════
# create_initial_state Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestCreateInitialState:
    def test_creates_dict(self):
        state = create_initial_state(["BTC/USDT"], "2024-01-15")
        assert isinstance(state, dict)

    def test_symbols_set(self):
        state = create_initial_state(["BTC/USDT", "ETH/USDT"], "2024-01-15")
        assert state["symbols"] == ["BTC/USDT", "ETH/USDT"]

    def test_trade_date_set(self):
        state = create_initial_state(["BTC/USDT"], "2024-01-15")
        assert state["trade_date"] == "2024-01-15"

    def test_default_values(self):
        state = create_initial_state(["BTC/USDT"], "2024-01-15")
        assert state["market_data"] == {}
        assert state["signals"] == []
        assert state["decisions"] == []
        assert state["confidence"] == 0.0
        assert state["kill_switch_active"] is False
        assert state["should_halt"] is False
        assert state["iteration"] == 0

    def test_default_risk_verdict_vetoed(self):
        state = create_initial_state(["BTC/USDT"], "2024-01-15")
        assert state["risk_verdict"] == "VETOED"

    def test_metadata_contains_constitutional_limits(self):
        state = create_initial_state(["BTC/USDT"], "2024-01-15")
        limits = state["metadata"]["constitutional_limits"]
        assert limits["max_risk_per_trade"] == MAX_RISK_PER_TRADE
        assert limits["max_daily_loss"] == MAX_DAILY_LOSS
        assert limits["max_weekly_loss"] == MAX_WEEKLY_LOSS
        assert limits["override_possible"] is False

    def test_debate_state_initialized(self):
        state = create_initial_state(["BTC/USDT"], "2024-01-15")
        assert state["debate_state"]["count"] == 0
        assert state["debate_state"]["bull_history"] == ""

    def test_sender_is_system(self):
        state = create_initial_state(["BTC/USDT"], "2024-01-15")
        assert state["sender"] == "system"

    def test_empty_symbols(self):
        state = create_initial_state([], "2024-01-15")
        assert state["symbols"] == []

    def test_all_required_keys_present(self):
        state = create_initial_state(["BTC/USDT"], "2024-01-15")
        required_keys = [
            "symbols", "trade_date", "market_data",
            "research_output", "macro_output", "crypto_output", "forex_output",
            "signals", "strategist_output",
            "risk_assessment", "risk_verdict",
            "portfolio_state", "portfolio_output",
            "decisions", "trader_output",
            "execution_output", "orders_placed",
            "debate_state", "council_result",
            "agent_outputs", "iteration", "confidence",
            "kill_switch_active", "should_halt",
            "metadata", "sender",
        ]
        for key in required_keys:
            assert key in state, f"Missing key: {key}"


# ═══════════════════════════════════════════════════════════════════════════
# Constitutional Constants in State Module
# ═══════════════════════════════════════════════════════════════════════════

class TestStateConstitutionalConstants:
    """Verify constitutional constants defined in state.py."""

    def test_max_risk_per_trade(self):
        assert MAX_RISK_PER_TRADE == 0.005

    def test_max_daily_loss(self):
        assert MAX_DAILY_LOSS == 0.01

    def test_max_weekly_loss(self):
        assert MAX_WEEKLY_LOSS == 0.03

    def test_min_risk_reward(self):
        assert MIN_RISK_REWARD == 2.0

    def test_max_correlated_positions(self):
        assert MAX_CORRELATED_POSITIONS == 3

    def test_max_position_size_pct(self):
        assert MAX_POSITION_SIZE_PCT == 0.10

    def test_max_leverage(self):
        assert MAX_LEVERAGE == 3.0

    def test_max_drawdown_pct(self):
        assert MAX_DRAWDOWN_PCT == 0.15

    def test_max_trades_per_day(self):
        assert MAX_TRADES_PER_DAY == 5

    def test_confidence_threshold(self):
        assert CONFIDENCE_THRESHOLD == 0.65

    def test_constants_are_positive(self):
        for const in [MAX_RISK_PER_TRADE, MAX_DAILY_LOSS, MAX_WEEKLY_LOSS,
                       MIN_RISK_REWARD, MAX_LEVERAGE, CONFIDENCE_THRESHOLD]:
            assert const > 0, f"Constitutional constant should be positive"
