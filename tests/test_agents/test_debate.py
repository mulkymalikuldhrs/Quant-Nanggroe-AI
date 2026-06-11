"""Tests for Agent Debate System."""

import asyncio
from typing import Any, Dict

import pytest

from quant_nanggroe.agents.debate.research_debate import (
    BearResearcherNode,
    BullResearcherNode,
    DebateArgument,
    InvestmentDebateState,
)
from quant_nanggroe.agents.debate.risk_debate import (
    AggressiveDebatorNode,
    ConservativeDebatorNode,
    NeutralDebatorNode,
    RiskDebateState,
    RiskPosition,
)
from quant_nanggroe.agents.debate.graph import TradingDebateGraph, DebateResult


# ======================================================================
# Research Debate
# ======================================================================

class TestBullResearcher:
    @pytest.mark.asyncio
    async def test_generates_bull_arguments(self):
        bull = BullResearcherNode()
        state: InvestmentDebateState = {
            "symbol": "AAPL",
            "market_data": {"price": 150, "change_pct": 2.5},
            "bull_arguments": [],
            "bear_arguments": [],
            "debate_round": 0,
            "max_rounds": 3,
            "bull_score": 0.5,
            "bear_score": 0.5,
            "consensus_reached": False,
            "final_verdict": "",
            "key_factors": [],
        }
        result = await bull.run(state)
        assert len(result["bull_arguments"]) == 1
        assert result["bull_arguments"][0].stance == "bull"
        assert result["debate_round"] == 1

    @pytest.mark.asyncio
    async def test_updates_score(self):
        bull = BullResearcherNode()
        state: InvestmentDebateState = {
            "symbol": "AAPL",
            "market_data": {"price": 150, "change_pct": 2.5},
            "bull_arguments": [],
            "bear_arguments": [],
            "debate_round": 0,
            "max_rounds": 3,
            "bull_score": 0.5,
            "bear_score": 0.5,
            "consensus_reached": False,
            "final_verdict": "",
            "key_factors": [],
        }
        result = await bull.run(state)
        assert 0 <= result["bull_score"] <= 1.0


class TestBearResearcher:
    @pytest.mark.asyncio
    async def test_generates_bear_arguments(self):
        bear = BearResearcherNode()
        state: InvestmentDebateState = {
            "symbol": "AAPL",
            "market_data": {"price": 150, "change_pct": -1.5},
            "bull_arguments": [],
            "bear_arguments": [],
            "debate_round": 0,
            "max_rounds": 3,
            "bull_score": 0.5,
            "bear_score": 0.5,
            "consensus_reached": False,
            "final_verdict": "",
            "key_factors": [],
        }
        result = await bear.run(state)
        assert len(result["bear_arguments"]) == 1
        assert result["bear_arguments"][0].stance == "bear"


class TestDebateArgument:
    def test_construction(self):
        arg = DebateArgument(
            agent="bull_researcher",
            stance="bull",
            points=["Strong earnings", "Revenue growth"],
            confidence=0.8,
        )
        assert arg.agent == "bull_researcher"
        assert len(arg.points) == 2
        assert arg.confidence == 0.8


# ======================================================================
# Risk Debate
# ======================================================================

class TestConservativeDebator:
    @pytest.mark.asyncio
    async def test_generates_conservative_position(self):
        debator = ConservativeDebatorNode()
        state: RiskDebateState = {
            "symbol": "AAPL",
            "trade_direction": "BUY",
            "proposed_size": 5000,
            "current_portfolio": {"total_equity": 100000},
            "conservative_position": None,
            "neutral_position": None,
            "aggressive_position": None,
            "debate_round": 0,
            "final_risk_level": "medium",
            "approved_size": 0.0,
            "risk_score": 0.5,
            "conditions": [],
        }
        result = await debator.run(state)
        assert result["conservative_position"] is not None
        assert result["conservative_position"].risk_stance == "conservative"
        assert result["conservative_position"].max_position_pct == 0.5


class TestNeutralDebator:
    @pytest.mark.asyncio
    async def test_generates_neutral_position(self):
        debator = NeutralDebatorNode()
        state: RiskDebateState = {
            "symbol": "AAPL",
            "trade_direction": "BUY",
            "proposed_size": 5000,
            "current_portfolio": {"total_equity": 100000},
            "conservative_position": None,
            "neutral_position": None,
            "aggressive_position": None,
            "debate_round": 0,
            "final_risk_level": "medium",
            "approved_size": 0.0,
            "risk_score": 0.5,
            "conditions": [],
        }
        result = await debator.run(state)
        assert result["neutral_position"] is not None
        assert result["neutral_position"].max_position_pct == 1.0


class TestAggressiveDebator:
    @pytest.mark.asyncio
    async def test_generates_aggressive_position(self):
        debator = AggressiveDebatorNode()
        state: RiskDebateState = {
            "symbol": "AAPL",
            "trade_direction": "BUY",
            "proposed_size": 5000,
            "current_portfolio": {"total_equity": 100000},
            "conservative_position": None,
            "neutral_position": None,
            "aggressive_position": None,
            "debate_round": 0,
            "final_risk_level": "medium",
            "approved_size": 0.0,
            "risk_score": 0.5,
            "conditions": [],
        }
        result = await debator.run(state)
        assert result["aggressive_position"] is not None
        assert result["aggressive_position"].max_position_pct == 2.0


# ======================================================================
# Full Debate Graph
# ======================================================================

class TestTradingDebateGraph:
    @pytest.mark.asyncio
    async def test_full_debate(self):
        graph = TradingDebateGraph(max_research_rounds=2)
        result = await graph.run(
            symbol="AAPL",
            market_data={"price": 150, "change_pct": 1.5},
            trade_direction="BUY",
            proposed_size=5000,
        )

        assert isinstance(result, DebateResult)
        assert result.symbol == "AAPL"
        assert result.investment_verdict in ("BULLISH", "BEARISH")
        assert result.risk_level in ("low", "medium", "high")
        assert 0 <= result.approved_size_pct <= 3.0
        assert 0 <= result.bull_score <= 1.0
        assert 0 <= result.bear_score <= 1.0

    @pytest.mark.asyncio
    async def test_result_to_dict(self):
        graph = TradingDebateGraph(max_research_rounds=1)
        result = await graph.run(
            symbol="BTC",
            market_data={"price": 50000, "change_pct": -2.0},
        )
        d = result.to_dict()
        assert "symbol" in d
        assert "investment_verdict" in d
        assert "risk_level" in d
