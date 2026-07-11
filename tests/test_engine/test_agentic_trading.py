"""Unit tests for agentic trading (Berkshire, Consensus)."""

from __future__ import annotations

import pytest

from quant_nanggroe.engine.agentic_trading import (
    AgentRole,
    AgentSignal,
    BerkshireAnalyzer,
    ConsensusEngine,
    DecisionAction,
    TradingDecision,
    ValueMetrics,
)


class TestBerkshireAnalyzer:
    def test_buy_signal(self):
        """Strong fundamentals via set_metrics → BUY."""
        analyzer = BerkshireAnalyzer()
        analyzer.set_metrics(ValueMetrics(roe=0.25, debt_to_equity=0.2, roic=0.18, moat_score=80))
        result = analyzer.buffett_assessment()
        assert result.action == DecisionAction.BUY
        assert result.confidence >= 0.7

    def test_sell_signal(self):
        """High debt + low ROE → NOTHING."""
        analyzer = BerkshireAnalyzer()
        analyzer.set_metrics(ValueMetrics(roe=0.05, debt_to_equity=2.5, roic=0.03, moat_score=10))
        result = analyzer.buffett_assessment()
        assert result.action == DecisionAction.NOTHING

    def test_lynch_assessment(self):
        """Lynch PEG assessment needs pe + growth."""
        analyzer = BerkshireAnalyzer()
        analyzer.set_metrics(ValueMetrics(pe_ratio=10, earnings_growth_5y=0.20))
        result = analyzer.lynch_assessment()
        assert result.role == AgentRole.VALUATION
        assert result.action in (DecisionAction.BUY, DecisionAction.ADD)
        assert result.confidence > 0.5

    def test_full_assessment(self):
        """Full multi-agent assessment produces TradingDecision."""
        analyzer = BerkshireAnalyzer()
        analyzer.set_metrics(ValueMetrics(roe=0.25, debt_to_equity=0.2))
        result = analyzer.full_assessment(symbol="AAPL")
        assert isinstance(result, TradingDecision)
        assert result.symbol == "AAPL"
        assert result.confidence > 0
        assert len(result.agents) == 3

    def test_default_metrics(self):
        """Default metrics produces NOTHING."""
        analyzer = BerkshireAnalyzer()
        result = analyzer.buffett_assessment()
        assert result.action == DecisionAction.NOTHING


class TestConsensusEngine:
    def test_simple_majority(self):
        engine = ConsensusEngine()
        signals = [
            AgentSignal(role=AgentRole.BERKSHIRE, action=DecisionAction.BUY, confidence=0.9, reasoning="a"),
            AgentSignal(role=AgentRole.VALUATION, action=DecisionAction.BUY, confidence=0.8, reasoning="b"),
            AgentSignal(role=AgentRole.RISK, action=DecisionAction.HOLD, confidence=0.5, reasoning="c"),
        ]
        decision = engine.reach_consensus(symbol="AAPL", signals=signals)
        assert decision.action == DecisionAction.BUY
        assert decision.confidence > 0

    def test_risk_veto(self):
        engine = ConsensusEngine(veto_roles=[AgentRole.RISK])
        signals = [
            AgentSignal(role=AgentRole.BERKSHIRE, action=DecisionAction.BUY, confidence=0.9, reasoning="a"),
            AgentSignal(role=AgentRole.RISK, action=DecisionAction.SELL, confidence=0.95, reasoning="risk detected"),
        ]
        decision = engine.reach_consensus(symbol="AAPL", signals=signals)
        assert decision.action == DecisionAction.NOTHING
        assert "Vetoed" in decision.reasoning

    def test_empty_signals(self):
        engine = ConsensusEngine()
        decision = engine.reach_consensus(symbol="AAPL", signals=[])
        assert decision.action == DecisionAction.NOTHING
        assert decision.confidence == 0.0
