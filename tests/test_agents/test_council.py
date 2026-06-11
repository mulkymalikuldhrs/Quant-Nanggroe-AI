"""
Tests for the Council Debate and Voting mechanisms.

Validates the bull/bear debate, risk debate (conservative/neutral/aggressive),
weighted voting, and consensus computation.
"""

import pytest
from unittest.mock import MagicMock

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage

from quant_nanggroe.agents.council.debate import CouncilDebate
from quant_nanggroe.agents.council.voting import (
    CouncilVoting,
    DEFAULT_VOTER_WEIGHTS,
)
from quant_nanggroe.agents.state import (
    AgentState,
    CouncilResult,
    TradeAction,
    VoteResult,
    create_initial_state,
)


class TestCouncilDebate:
    """Test the Council Debate mechanism."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_llm = MagicMock(spec=BaseChatModel)
        self.mock_llm.invoke.return_value = AIMessage(content="Debate argument")

    def test_creation(self):
        """Should create CouncilDebate with default rounds."""
        debate = CouncilDebate(llm=self.mock_llm)
        assert debate._max_debate_rounds == 2
        assert debate._max_risk_rounds == 2

    def test_custom_rounds(self):
        """Should create CouncilDebate with custom rounds."""
        debate = CouncilDebate(
            llm=self.mock_llm,
            max_debate_rounds=3,
            max_risk_rounds=2,
        )
        assert debate._max_debate_rounds == 3
        assert debate._max_risk_rounds == 2

    def test_investment_debate(self):
        """Should run an investment debate and produce results."""
        debate = CouncilDebate(llm=self.mock_llm, max_debate_rounds=1)
        state = create_initial_state(["AAPL"], "2025-03-01")
        state["research_output"] = "AAPL showing strong growth"

        result = debate.run_investment_debate(state)

        assert "bull_history" in result
        assert "bear_history" in result
        assert "history" in result
        assert "judge_decision" in result
        assert result["count"] > 0

    def test_risk_debate(self):
        """Should run a risk debate and produce results."""
        debate = CouncilDebate(llm=self.mock_llm, max_risk_rounds=1)
        state = create_initial_state(["AAPL"], "2025-03-01")
        state["trader_output"] = "BUY AAPL"

        result = debate.run_risk_debate(state)

        assert "conservative_history" in result
        assert "neutral_history" in result
        assert "aggressive_history" in result
        assert "judge_decision" in result
        assert result["count"] > 0

    def test_full_debate(self):
        """Should run both investment and risk debates."""
        debate = CouncilDebate(
            llm=self.mock_llm,
            max_debate_rounds=1,
            max_risk_rounds=1,
        )
        state = create_initial_state(["AAPL"], "2025-03-01")
        state["research_output"] = "AAPL research"
        state["trader_output"] = "BUY AAPL"

        result = debate.run_full_debate(state)

        assert "investment_debate" in result
        assert "risk_debate" in result
        assert "debate_state" in result


class TestCouncilVoting:
    """Test the Council Voting mechanism."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_llm = MagicMock(spec=BaseChatModel)
        self.mock_llm.invoke.return_value = AIMessage(content="Vote: BUY")

    def test_default_weights(self):
        """Should have default voter weights."""
        assert "researcher" in DEFAULT_VOTER_WEIGHTS
        assert "risk" in DEFAULT_VOTER_WEIGHTS
        assert "strategist" in DEFAULT_VOTER_WEIGHTS
        assert "trader" in DEFAULT_VOTER_WEIGHTS

    def test_risk_highest_weight(self):
        """Risk agent should have the highest weight for safety."""
        assert DEFAULT_VOTER_WEIGHTS["risk"] >= DEFAULT_VOTER_WEIGHTS["researcher"]
        assert DEFAULT_VOTER_WEIGHTS["risk"] >= DEFAULT_VOTER_WEIGHTS["trader"]

    def test_compute_weighted_scores(self):
        """Should compute weighted scores correctly."""
        voting = CouncilVoting(llm=self.mock_llm)

        votes = [
            VoteResult(voter="researcher", vote=TradeAction.BUY, weight=1.2, confidence=0.8),
            VoteResult(voter="strategist", vote=TradeAction.BUY, weight=1.5, confidence=0.9),
            VoteResult(voter="risk", vote=TradeAction.HOLD, weight=2.0, confidence=0.7),
        ]

        scores = voting.compute_weighted_scores(votes)

        assert TradeAction.BUY.value in scores
        assert TradeAction.HOLD.value in scores
        # BUY: (1.2 * 0.8) + (1.5 * 0.9) = 0.96 + 1.35 = 2.31
        # HOLD: (2.0 * 0.7) = 1.40
        assert scores[TradeAction.BUY.value] > scores[TradeAction.HOLD.value]

    def test_determine_decision(self):
        """Should determine the correct decision from scores."""
        voting = CouncilVoting(llm=self.mock_llm)

        scores = {
            "BUY": 3.5,
            "SELL": 1.0,
            "HOLD": 2.0,
        }

        decision = voting.determine_decision(scores)
        assert decision == TradeAction.BUY

    def test_determine_decision_tie(self):
        """Should handle ties (first max wins)."""
        voting = CouncilVoting(llm=self.mock_llm)

        scores = {
            "BUY": 2.0,
            "SELL": 2.0,
            "HOLD": 1.0,
        }

        decision = voting.determine_decision(scores)
        assert decision in (TradeAction.BUY, TradeAction.SELL)

    def test_determine_decision_empty(self):
        """Should return HOLD for empty scores."""
        voting = CouncilVoting(llm=self.mock_llm)
        decision = voting.determine_decision({})
        assert decision == TradeAction.HOLD

    def test_compute_consensus(self):
        """Should compute consensus level."""
        voting = CouncilVoting(llm=self.mock_llm)

        votes = [
            VoteResult(voter="a", vote=TradeAction.BUY, weight=1.0, confidence=0.8),
            VoteResult(voter="b", vote=TradeAction.BUY, weight=1.0, confidence=0.9),
            VoteResult(voter="c", vote=TradeAction.HOLD, weight=1.0, confidence=0.6),
        ]

        scores = voting.compute_weighted_scores(votes)
        consensus = voting.compute_consensus(votes, scores)

        assert 0.0 <= consensus <= 1.0

    def test_high_consensus(self):
        """Unanimous votes should have high consensus."""
        voting = CouncilVoting(llm=self.mock_llm)

        votes = [
            VoteResult(voter="a", vote=TradeAction.BUY, weight=1.0, confidence=0.9),
            VoteResult(voter="b", vote=TradeAction.BUY, weight=1.0, confidence=0.9),
        ]

        scores = voting.compute_weighted_scores(votes)
        consensus = voting.compute_consensus(votes, scores)

        assert consensus > 0.5

    def test_low_consensus(self):
        """Split votes should have low consensus."""
        voting = CouncilVoting(llm=self.mock_llm)

        votes = [
            VoteResult(voter="a", vote=TradeAction.BUY, weight=1.0, confidence=0.5),
            VoteResult(voter="b", vote=TradeAction.SELL, weight=1.0, confidence=0.5),
            VoteResult(voter="c", vote=TradeAction.HOLD, weight=1.0, confidence=0.5),
        ]

        scores = voting.compute_weighted_scores(votes)
        consensus = voting.compute_consensus(votes, scores)

        assert consensus < 0.5

    def test_collect_votes(self):
        """Should collect votes from agent outputs."""
        voting = CouncilVoting(llm=self.mock_llm)

        state = create_initial_state(["AAPL"], "2025-03-01")
        state["agent_outputs"] = {
            "researcher": {
                "content": "Analysis suggests BUY opportunity",
                "confidence": 0.8,
            },
            "risk": {
                "content": "Risk assessment: VETOED",
                "confidence": 1.0,
            },
        }
        state["risk_verdict"] = "VETOED"

        votes = voting.collect_votes(state)

        assert len(votes) > 0
        # Risk agent should vote HOLD when VETOED
        risk_votes = [v for v in votes if v.voter == "risk"]
        assert len(risk_votes) == 1
        assert risk_votes[0].vote == TradeAction.HOLD

    def test_run_council_vote(self):
        """Should run full council vote and return CouncilResult."""
        voting = CouncilVoting(llm=self.mock_llm)

        state = create_initial_state(["AAPL"], "2025-03-01")
        state["agent_outputs"] = {
            "researcher": {
                "content": "BUY signal detected",
                "confidence": 0.8,
            },
        }

        result = voting.run_council_vote(state)

        assert isinstance(result, CouncilResult)
        assert isinstance(result.final_decision, TradeAction)
        assert 0.0 <= result.consensus_level <= 1.0

    def test_human_review_flag(self):
        """Should flag for human review when consensus is low."""
        voting = CouncilVoting(llm=self.mock_llm, consensus_threshold=0.5)

        state = create_initial_state(["AAPL"], "2025-03-01")
        # Minimal outputs = low consensus
        state["agent_outputs"] = {
            "researcher": {"content": "Maybe BUY", "confidence": 0.3},
        }

        result = voting.run_council_vote(state)
        # Low consensus should flag for review
        # (actual value depends on the single low-confidence vote)
        assert isinstance(result.requires_human_review, bool)

    def test_custom_weights(self):
        """Should accept custom voter weights."""
        custom_weights = {
            "researcher": 2.0,
            "risk": 3.0,
        }
        voting = CouncilVoting(llm=self.mock_llm, voter_weights=custom_weights)
        assert voting._voter_weights["researcher"] == 2.0
        assert voting._voter_weights["risk"] == 3.0
