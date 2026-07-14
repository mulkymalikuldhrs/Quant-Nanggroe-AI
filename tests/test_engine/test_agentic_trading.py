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


class TestAgentSignalRegression:
    def test_reasoning_default(self):
        """Regression: AgentSignal must be constructible without `reasoning`
        (API/quick-signal callers omit it)."""
        sig = AgentSignal(role=AgentRole.RESEARCH, action=DecisionAction.HOLD, confidence=0.5)
        assert sig.reasoning == ""
        assert sig.timestamp  # auto-filled

    def test_to_dict_serializes(self):
        sig = AgentSignal(role=AgentRole.RISK, action=DecisionAction.SELL,
                          confidence=0.9, reasoning="risk")
        d = sig.__dict__
        assert d["role"] == AgentRole.RISK
        assert d["reasoning"] == "risk"


class TestValueMetricsRegression:
    def test_has_market_cap(self):
        """Regression: ValueMetrics must expose `market_cap` for valuation callers."""
        m = ValueMetrics(roe=0.2, market_cap=3.0e12)
        assert hasattr(m, "market_cap")
        assert m.market_cap == 3.0e12
        assert m.buffett_score >= 0

    def test_default_market_cap_zero(self):
        assert ValueMetrics().market_cap == 0.0


class TestConsensusEngineEdge:
    def test_weighted_consensus(self):
        engine = ConsensusEngine()
        signals = [
            AgentSignal(role=AgentRole.BERKSHIRE, action=DecisionAction.BUY, confidence=0.9, reasoning="r"),
            AgentSignal(role=AgentRole.VALUATION, action=DecisionAction.SELL, confidence=0.8, reasoning="v"),
        ]
        decision = engine.reach_consensus(
            symbol="AAPL", signals=signals,
            weights={"berkshire": 0.9, "valuation": 0.1},
        )
        assert decision.action == DecisionAction.BUY  # berkshire dominates
        assert 0 < decision.position_size_pct <= 0.25

    def test_strong_sell_veto(self):
        engine = ConsensusEngine(veto_roles=[AgentRole.RISK])
        signals = [
            AgentSignal(role=AgentRole.BERKSHIRE, action=DecisionAction.BUY, confidence=0.9, reasoning="b"),
            AgentSignal(role=AgentRole.RISK, action=DecisionAction.STRONG_SELL, confidence=0.99, reasoning="bad"),
        ]
        decision = engine.reach_consensus(symbol="AAPL", signals=signals)
        assert decision.action == DecisionAction.NOTHING
