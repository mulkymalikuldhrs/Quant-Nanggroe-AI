"""Tests for TradingAgents-inspired Debate Engine."""

import pytest

from quant_nanggroe.agents.debate import (
    AgentOpinion,
    DebateEngine,
    DebateResult,
    RiskManager,
    RiskMetrics,
    Signal,
)


class TestSignalEnum:
    def test_signal_values(self):
        assert Signal.BUY.value == "buy"
        assert Signal.SELL.value == "sell"
        assert Signal.HOLD.value == "hold"

    def test_signal_comparison(self):
        assert Signal.BUY != Signal.SELL
        assert Signal.HOLD == Signal.HOLD


class TestAgentOpinion:
    def test_creation_minimal(self):
        opinion = AgentOpinion(
            agent_id="agent1",
            signal=Signal.BUY,
            confidence=0.8,
            reasoning="Strong fundamentals",
        )
        assert opinion.agent_id == "agent1"
        assert opinion.signal == Signal.BUY
        assert opinion.confidence == 0.8
        assert opinion.reasoning == "Strong fundamentals"
        assert opinion.weight == 1.0

    def test_creation_with_weight(self):
        opinion = AgentOpinion(
            agent_id="agent2",
            signal=Signal.SELL,
            confidence=0.6,
            reasoning="Overbought",
            weight=2.0,
        )
        assert opinion.weight == 2.0


class TestRiskManager:
    def test_default_config(self):
        rm = RiskManager()
        assert rm.config["max_position_pct"] == 25.0
        assert rm.config["max_leverage"] == 2.0
        assert rm.config["stop_loss_pct"] == 5.0
        assert rm.config["take_profit_pct"] == 15.0
        assert rm.config["max_drawdown_pct"] == 20.0

    def test_custom_config(self):
        custom = {
            "max_position_pct": 10.0,
            "max_leverage": 3.0,
            "stop_loss_pct": 3.0,
            "take_profit_pct": 10.0,
            "max_drawdown_pct": 15.0,
        }
        rm = RiskManager(custom)
        assert rm.config == custom

    def test_assess_empty_opinions(self):
        rm = RiskManager()
        risk = rm.assess([], volatility=0.2)
        assert isinstance(risk, RiskMetrics)
        assert risk.max_position_size == 12.5  # 25 * 0.5 (default confidence)
        assert risk.max_leverage == 2.0
        assert risk.stop_loss_pct == 5.0
        assert risk.take_profit_pct == 15.0
        assert abs(risk.var_95 - 0.329) < 0.001  # 0.2 * 1.645
        assert risk.max_drawdown == 20.0

    def test_assess_with_opinions(self):
        rm = RiskManager()
        opinions = [
            AgentOpinion("a1", Signal.BUY, 0.9, "bullish"),
            AgentOpinion("a2", Signal.BUY, 0.7, "bullish"),
        ]
        risk = rm.assess(opinions, volatility=0.25)
        avg_conf = (0.9 + 0.7) / 2
        assert abs(risk.max_position_size - 25.0 * avg_conf) < 0.001
        assert risk.max_leverage == min(2.0, 1.0 / 0.25) == 2.0
        assert abs(risk.var_95 - 0.41125) < 0.001  # 0.25 * 1.645

    def test_assess_high_volatility_reduces_leverage(self):
        rm = RiskManager()
        opinions = [AgentOpinion("a1", Signal.BUY, 0.8, "test")]
        risk = rm.assess(opinions, volatility=0.5)
        assert risk.max_leverage == min(2.0, 1.0 / 0.5) == 2.0

        risk2 = rm.assess(opinions, volatility=0.8)
        assert risk2.max_leverage == min(2.0, 1.0 / 0.8) == 1.25


class TestDebateEngine:
    def test_init_default(self):
        engine = DebateEngine()
        assert engine.min_agents == 2
        assert isinstance(engine.risk_manager, RiskManager)

    def test_init_custom(self):
        rm = RiskManager({"max_position_pct": 10.0})
        engine = DebateEngine(min_agents=3, risk_manager=rm)
        assert engine.min_agents == 3
        assert engine.risk_manager.config["max_position_pct"] == 10.0

    def test_insufficient_agents_raises(self):
        engine = DebateEngine(min_agents=3)
        opinions = [
            AgentOpinion("a1", Signal.BUY, 0.8, "test"),
            AgentOpinion("a2", Signal.SELL, 0.6, "test"),
        ]
        with pytest.raises(ValueError, match="Need at least 3 agents"):
            engine.debate(opinions)

    def test_clear_buy_consensus(self):
        engine = DebateEngine()
        opinions = [
            AgentOpinion("a1", Signal.BUY, 0.9, "strong buy"),
            AgentOpinion("a2", Signal.BUY, 0.8, "buy"),
            AgentOpinion("a3", Signal.BUY, 0.7, "buy"),
        ]
        result = engine.debate(opinions)
        assert result.consensus_signal == Signal.BUY
        assert result.consensus_confidence > 0.7
        assert result.disagreement is False
        assert len(result.opinions) == 3
        assert isinstance(result.risk, RiskMetrics)

    def test_clear_sell_consensus(self):
        engine = DebateEngine()
        opinions = [
            AgentOpinion("a1", Signal.SELL, 0.9, "strong sell"),
            AgentOpinion("a2", Signal.SELL, 0.8, "sell"),
        ]
        result = engine.debate(opinions)
        assert result.consensus_signal == Signal.SELL
        assert result.disagreement is False

    def test_hold_consensus(self):
        engine = DebateEngine()
        opinions = [
            AgentOpinion("a1", Signal.HOLD, 0.8, "uncertain"),
            AgentOpinion("a2", Signal.HOLD, 0.7, "wait"),
        ]
        result = engine.debate(opinions)
        assert result.consensus_signal == Signal.HOLD

    def test_disagreement_detected(self):
        engine = DebateEngine()
        opinions = [
            AgentOpinion("a1", Signal.BUY, 0.9, "bullish"),
            AgentOpinion("a2", Signal.SELL, 0.9, "bearish"),
        ]
        result = engine.debate(opinions)
        assert result.disagreement is True
        assert result.consensus_confidence <= 0.5

    def test_weighted_voting(self):
        engine = DebateEngine()
        opinions = [
            AgentOpinion("a1", Signal.BUY, 0.9, "strong", weight=3.0),
            AgentOpinion("a2", Signal.SELL, 0.9, "strong", weight=1.0),
            AgentOpinion("a3", Signal.SELL, 0.8, "moderate", weight=1.0),
        ]
        result = engine.debate(opinions)
        assert result.consensus_signal == Signal.BUY

    def test_confidence_affects_result(self):
        engine = DebateEngine()
        # Mixed signals: different confidence levels should affect consensus
        high_conf = [
            AgentOpinion("a1", Signal.BUY, 0.9, "strong buy", weight=3.0),
            AgentOpinion("a2", Signal.SELL, 0.5, "weak sell", weight=1.0),
        ]
        low_conf = [
            AgentOpinion("a1", Signal.BUY, 0.5, "weak buy", weight=3.0),
            AgentOpinion("a2", Signal.SELL, 0.9, "strong sell", weight=1.0),
        ]
        high_result = engine.debate(high_conf)
        low_result = engine.debate(low_conf)
        # BUY should win with high_conf (a1 confident), but not necessarily with low_conf
        assert high_result.consensus_signal == Signal.BUY
        assert low_result.consensus_confidence != high_result.consensus_confidence or low_result.consensus_signal != Signal.BUY

    def test_risk_metrics_attached(self):
        engine = DebateEngine()
        opinions = [
            AgentOpinion("a1", Signal.BUY, 0.8, "test"),
            AgentOpinion("a2", Signal.BUY, 0.7, "test"),
        ]
        result = engine.debate(opinions, volatility=0.3)
        assert result.risk is not None
        assert result.risk.max_position_size > 0
        assert result.risk.max_leverage > 0
        assert result.risk.stop_loss_pct == 5.0
        assert result.risk.take_profit_pct == 15.0
        assert result.risk.var_95 > 0
        assert result.risk.max_drawdown == 20.0

    def test_summary_format(self):
        engine = DebateEngine()
        opinions = [
            AgentOpinion("a1", Signal.BUY, 0.8, "test"),
            AgentOpinion("a2", Signal.BUY, 0.7, "test"),
        ]
        result = engine.debate(opinions)
        assert "Debate:" in result.summary
        assert "buy" in result.summary.lower()
        assert "%" in result.summary


class TestDebateResult:
    def test_defaults(self):
        result = DebateResult(
            consensus_signal=Signal.BUY,
            consensus_confidence=0.8,
        )
        assert result.opinions == []
        assert result.disagreement is False
        assert result.risk is None
        assert result.summary == ""

    def test_with_all_fields(self):
        opinions = [AgentOpinion("a1", Signal.BUY, 0.8, "test")]
        risk = RiskMetrics(10.0, 2.0, 5.0, 15.0, 0.3, 20.0)
        result = DebateResult(
            consensus_signal=Signal.BUY,
            consensus_confidence=0.8,
            opinions=opinions,
            disagreement=True,
            risk=risk,
            summary="Test summary",
        )
        assert result.disagreement is True
        assert result.risk is not None
        assert result.summary == "Test summary"


class TestEdgeCases:
    def test_single_agent_allowed_with_min_agents_1(self):
        engine = DebateEngine(min_agents=1)
        opinions = [AgentOpinion("a1", Signal.BUY, 0.8, "test")]
        result = engine.debate(opinions)
        assert result.consensus_signal == Signal.BUY

    def test_zero_weight_opinions(self):
        engine = DebateEngine()
        opinions = [
            AgentOpinion("a1", Signal.BUY, 0.8, "test", weight=0.0),
            AgentOpinion("a2", Signal.SELL, 0.8, "test", weight=1.0),
        ]
        result = engine.debate(opinions)
        assert result.consensus_signal == Signal.SELL

    def test_mixed_signals_buy_wins(self):
        engine = DebateEngine()
        opinions = [
            AgentOpinion("a1", Signal.BUY, 0.7, "test", weight=2.0),
            AgentOpinion("a2", Signal.HOLD, 0.9, "test", weight=1.0),
            AgentOpinion("a3", Signal.SELL, 0.6, "test", weight=1.0),
        ]
        result = engine.debate(opinions)
        assert result.consensus_signal == Signal.BUY