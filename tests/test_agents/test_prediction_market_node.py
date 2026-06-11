"""
Tests for Prediction Market Agent Node
=======================================
Tests prediction market platform configuration, probability estimation,
cross-market hedging, trade validation, and the main prediction_market_node.
External dependencies (PolymarketBroker) are mocked.
"""

from __future__ import annotations

from unittest.mock import patch, AsyncMock

import pytest

from quant_nanggroe_ai.agents.nodes.prediction_market import (
    PredictionPlatform,
    PLATFORMS,
    MIN_PROBABILITY_EDGE,
    MIN_LIQUIDITY_USD,
    MIN_VOLUME_USD,
    CROSS_HEDGE_MIN_CORRELATION,
    TOPIC_INSTRUMENT_MAP,
    _is_prediction_market_query,
    _estimate_probability,
    _find_cross_hedge_opportunities,
    _validate_prediction_market_trade,
    prediction_market_node,
)
from quant_nanggroe_ai.agents.state import AgentState
from quant_nanggroe_ai.types import RiskClearance


# ══════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════


@pytest.fixture
def prediction_state() -> AgentState:
    """Agent state for prediction market analysis."""
    return AgentState(
        symbol="PREDICT_ELECTION",
        query="Will the Fed raise rates in 2024?",
        risk_clearance=RiskClearance.CLEAR,
        agent_trace=[],
        errors=[],
    )


@pytest.fixture
def standard_state() -> AgentState:
    """Agent state with standard symbol and no query."""
    return AgentState(
        symbol="AAPL",
        agent_trace=[],
        errors=[],
    )


# ══════════════════════════════════════════════════════════════════════
# PredictionPlatform TESTS
# ══════════════════════════════════════════════════════════════════════


class TestPredictionPlatform:
    def test_creation(self) -> None:
        platform = PredictionPlatform(
            name="TestPlatform",
            chain="ethereum",
            settlement_time_hours=2.0,
            min_bet=5.0,
            max_bet=10000.0,
            fee_pct=1.0,
            smart_contract_support=True,
        )
        assert platform.name == "TestPlatform"
        assert platform.chain == "ethereum"
        assert platform.smart_contract_support is True


class TestPreconfiguredPlatforms:
    def test_all_platforms_exist(self) -> None:
        expected = {"polymarket", "kalshi", "metaculus", "manifold"}
        assert set(PLATFORMS.keys()) == expected

    def test_polymarket_on_chain(self) -> None:
        assert PLATFORMS["polymarket"].chain == "polygon"
        assert PLATFORMS["polymarket"].smart_contract_support is True

    def test_kalshi_not_on_chain(self) -> None:
        assert PLATFORMS["kalshi"].chain == "none"
        assert PLATFORMS["kalshi"].smart_contract_support is False

    def test_metaculus_non_monetary(self) -> None:
        assert PLATFORMS["metaculus"].min_bet == 0.0
        assert PLATFORMS["metaculus"].max_bet == 0.0

    def test_constants(self) -> None:
        assert MIN_PROBABILITY_EDGE == 0.05
        assert MIN_LIQUIDITY_USD == 1000.0
        assert MIN_VOLUME_USD == 500.0
        assert CROSS_HEDGE_MIN_CORRELATION == 0.6


class TestTopicInstrumentMap:
    def test_has_expected_topics(self) -> None:
        expected_topics = {
            "fed_rate_hike", "recession_2024", "btc_100k",
            "election_outcome", "oil_price_100", "inflation_above_3",
        }
        assert set(TOPIC_INSTRUMENT_MAP.keys()) == expected_topics

    def test_entry_structure(self) -> None:
        for topic, mapping in TOPIC_INSTRUMENT_MAP.items():
            assert "traditional_instrument" in mapping
            assert "correlation" in mapping
            assert "direction" in mapping
            assert 0.0 <= mapping["correlation"] <= 1.0


# ══════════════════════════════════════════════════════════════════════
# PREDICTION MARKET QUERY DETECTION
# ══════════════════════════════════════════════════════════════════════


class TestIsPredictionMarketQuery:
    def test_election_keyword(self) -> None:
        assert _is_prediction_market_query("ELECTION_2024") is True

    def test_predict_keyword(self) -> None:
        assert _is_prediction_market_query("PREDICT_OUTCOME") is True

    def test_polymarket_keyword(self) -> None:
        assert _is_prediction_market_query("POLYMARKET_TRADE") is True

    def test_kalshi_keyword(self) -> None:
        assert _is_prediction_market_query("KALSHI_RATE") is True

    def test_rate_keyword(self) -> None:
        assert _is_prediction_market_query("RATE_HIKE") is True

    def test_yes_no_keywords(self) -> None:
        assert _is_prediction_market_query("YES_SHARE") is True
        assert _is_prediction_market_query("NO_SHARE") is True

    def test_standard_symbol_not_prediction(self) -> None:
        assert _is_prediction_market_query("AAPL") is False
        assert _is_prediction_market_query("BTCUSDT") is False


# ══════════════════════════════════════════════════════════════════════
# PROBABILITY ESTIMATION TESTS
# ══════════════════════════════════════════════════════════════════════


class TestEstimateProbability:
    @pytest.mark.asyncio
    async def test_basic_estimation(self) -> None:
        result = await _estimate_probability(
            market_question="Will BTC reach $100k?",
            market_yes_price=0.65,
        )
        assert "market_implied" in result
        assert "model_estimate" in result
        assert "blended_estimate" in result
        assert "confidence_lower" in result
        assert "confidence_upper" in result

    @pytest.mark.asyncio
    async def test_blended_estimate_in_range(self) -> None:
        result = await _estimate_probability(
            market_question="Test", market_yes_price=0.50,
        )
        assert 0.01 <= result["blended_estimate"] <= 0.99

    @pytest.mark.asyncio
    async def test_market_implied_equals_price(self) -> None:
        result = await _estimate_probability(
            market_question="Test", market_yes_price=0.75,
        )
        assert result["market_implied"] == 0.75

    @pytest.mark.asyncio
    async def test_confidence_interval_contains_estimate(self) -> None:
        result = await _estimate_probability(
            market_question="Test", market_yes_price=0.60,
        )
        assert result["confidence_lower"] <= result["blended_estimate"]
        assert result["confidence_upper"] >= result["blended_estimate"]

    @pytest.mark.asyncio
    async def test_sources_agree_when_close(self) -> None:
        result = await _estimate_probability(
            market_question="Test", market_yes_price=0.50,
        )
        # With same market and model estimate, sources should agree
        assert result["sources_agree"] is True

    @pytest.mark.asyncio
    async def test_extreme_price_clamped(self) -> None:
        # Price of 0.0 should be clamped
        result = await _estimate_probability(
            market_question="Test", market_yes_price=0.0,
        )
        assert result["blended_estimate"] >= 0.01

    @pytest.mark.asyncio
    async def test_price_of_1_clamped(self) -> None:
        result = await _estimate_probability(
            market_question="Test", market_yes_price=1.0,
        )
        assert result["blended_estimate"] <= 0.99


# ══════════════════════════════════════════════════════════════════════
# CROSS-MARKET HEDGING TESTS
# ══════════════════════════════════════════════════════════════════════


class TestFindCrossHedgeOpportunities:
    def test_fed_rate_hike_hedge(self) -> None:
        opportunities = _find_cross_hedge_opportunities(
            market_question="Will the fed rate hike in 2024?",
            estimated_probability=0.70,
            market_yes_price=0.55,
        )
        assert len(opportunities) > 0
        # Should find the fed_rate_hike topic
        topics = [o["topic"] for o in opportunities]
        assert "fed_rate_hike" in topics

    def test_btc_100k_hedge(self) -> None:
        opportunities = _find_cross_hedge_opportunities(
            market_question="Will BTC reach 100k?",
            estimated_probability=0.40,
            market_yes_price=0.30,
        )
        topics = [o["topic"] for o in opportunities]
        assert "btc_100k" in topics

    def test_no_matching_topic(self) -> None:
        opportunities = _find_cross_hedge_opportunities(
            market_question="Will it rain tomorrow?",
            estimated_probability=0.50,
            market_yes_price=0.50,
        )
        assert len(opportunities) == 0

    def test_low_correlation_filtered(self) -> None:
        # election_outcome has correlation 0.50 < 0.60 threshold
        opportunities = _find_cross_hedge_opportunities(
            market_question="Election outcome prediction market",
            estimated_probability=0.60,
            market_yes_price=0.50,
        )
        # election_outcome should be filtered out (correlation 0.50 < 0.60)
        topics = [o["topic"] for o in opportunities]
        assert "election_outcome" not in topics

    def test_hedge_structure(self) -> None:
        opportunities = _find_cross_hedge_opportunities(
            market_question="Fed rate hike prediction",
            estimated_probability=0.70,
            market_yes_price=0.55,
        )
        if opportunities:
            opp = opportunities[0]
            assert "topic" in opp
            assert "prediction_market_side" in opp
            assert "traditional_instrument" in opp
            assert "traditional_side" in opp
            assert "correlation" in opp
            assert "edge" in opp
            assert "hedge_ratio" in opp
            assert "description" in opp

    def test_buy_yes_when_underpriced(self) -> None:
        opportunities = _find_cross_hedge_opportunities(
            market_question="Fed rate hike prediction",
            estimated_probability=0.70,  # Higher than price
            market_yes_price=0.50,  # Underpriced
        )
        fed_opps = [o for o in opportunities if o["topic"] == "fed_rate_hike"]
        if fed_opps:
            assert fed_opps[0]["prediction_market_side"] == "BUY_YES"

    def test_sell_yes_when_overpriced(self) -> None:
        opportunities = _find_cross_hedge_opportunities(
            market_question="Fed rate hike prediction",
            estimated_probability=0.30,  # Lower than price
            market_yes_price=0.70,  # Overpriced
        )
        fed_opps = [o for o in opportunities if o["topic"] == "fed_rate_hike"]
        if fed_opps:
            assert fed_opps[0]["prediction_market_side"] == "SELL_YES"

    def test_sorted_by_edge(self) -> None:
        opportunities = _find_cross_hedge_opportunities(
            market_question="Fed rate hike and BTC 100k prediction",
            estimated_probability=0.80,
            market_yes_price=0.30,
        )
        if len(opportunities) > 1:
            edges = [o["edge"] for o in opportunities]
            assert edges == sorted(edges, reverse=True)


# ══════════════════════════════════════════════════════════════════════
# TRADE VALIDATION TESTS
# ══════════════════════════════════════════════════════════════════════


class TestValidatePredictionMarketTrade:
    def test_valid_trade(self) -> None:
        result = _validate_prediction_market_trade(
            yes_price=0.50,
            estimated_probability=0.65,
            market_volume=5000.0,
            market_liquidity=5000.0,
        )
        assert result["all_passed"] is True
        assert result["verdict"] == "PASS"
        assert len(result["failed_checks"]) == 0

    def test_invalid_price_range_low(self) -> None:
        result = _validate_prediction_market_trade(
            yes_price=0.001,  # Below 0.01
            estimated_probability=0.50,
        )
        assert result["checks"]["price_range"]["passed"] is False

    def test_invalid_price_range_high(self) -> None:
        result = _validate_prediction_market_trade(
            yes_price=0.999,  # Above 0.99
            estimated_probability=0.50,
        )
        assert result["checks"]["price_range"]["passed"] is False

    def test_insufficient_edge(self) -> None:
        result = _validate_prediction_market_trade(
            yes_price=0.50,
            estimated_probability=0.52,  # Only 2% edge < 5% minimum
        )
        assert result["checks"]["edge"]["passed"] is False

    def test_sufficient_edge(self) -> None:
        result = _validate_prediction_market_trade(
            yes_price=0.50,
            estimated_probability=0.60,  # 10% edge > 5% minimum
        )
        assert result["checks"]["edge"]["passed"] is True

    def test_insufficient_liquidity(self) -> None:
        result = _validate_prediction_market_trade(
            yes_price=0.50,
            estimated_probability=0.60,
            market_liquidity=500.0,  # Below 1000 minimum
        )
        assert result["checks"]["liquidity"]["passed"] is False

    def test_insufficient_volume(self) -> None:
        result = _validate_prediction_market_trade(
            yes_price=0.50,
            estimated_probability=0.60,
            market_volume=200.0,  # Below 500 minimum
        )
        assert result["checks"]["volume"]["passed"] is False

    def test_all_checks_fail(self) -> None:
        result = _validate_prediction_market_trade(
            yes_price=0.001,
            estimated_probability=0.001,  # No edge
            market_volume=0.0,
            market_liquidity=0.0,
        )
        assert result["all_passed"] is False
        assert result["verdict"] == "FAIL"
        assert len(result["failed_checks"]) > 0

    def test_result_has_all_checks(self) -> None:
        result = _validate_prediction_market_trade(
            yes_price=0.50, estimated_probability=0.60,
        )
        expected_checks = {"price_range", "edge", "liquidity", "volume"}
        assert set(result["checks"].keys()) == expected_checks

    def test_edge_value_in_result(self) -> None:
        result = _validate_prediction_market_trade(
            yes_price=0.50, estimated_probability=0.65,
        )
        assert abs(result["edge"] - 0.15) < 0.001


# ══════════════════════════════════════════════════════════════════════
# PREDICTION MARKET NODE INTEGRATION TESTS
# ══════════════════════════════════════════════════════════════════════


class TestPredictionMarketNode:
    @pytest.mark.asyncio
    async def test_basic_execution(
        self, prediction_state: AgentState
    ) -> None:
        """Test that prediction_market_node runs and returns valid output."""
        with patch(
            "quant_nanggroe_ai.agents.nodes.prediction_market._discover_markets",
            new_callable=AsyncMock,
        ) as mock_discover:
            mock_discover.return_value = [
                {
                    "platform": "placeholder",
                    "question": "Will the Fed raise rates?",
                    "yes_price": 0.60,
                    "condition_id": "",
                    "status": "no_results",
                }
            ]
            result = await prediction_market_node(prediction_state)

        assert "macro_context" in result
        assert "agent_trace" in result
        assert len(result["agent_trace"]) == 1
        assert result["agent_trace"][0]["agent"] == "prediction_market"

    @pytest.mark.asyncio
    async def test_with_live_markets(
        self, prediction_state: AgentState
    ) -> None:
        """Test with simulated live market data."""
        with patch(
            "quant_nanggroe_ai.agents.nodes.prediction_market._discover_markets",
            new_callable=AsyncMock,
        ) as mock_discover:
            mock_discover.return_value = [
                {
                    "platform": "polymarket",
                    "question": "Will the fed rate hike in 2024?",
                    "yes_price": 0.55,
                    "condition_id": "cond_123",
                    "volume": 50000.0,
                    "liquidity": 25000.0,
                    "category": "economics",
                    "end_date": "2024-12-31",
                    "active": True,
                }
            ]
            result = await prediction_market_node(prediction_state)

        trace = result["agent_trace"][0]
        assert trace["markets_discovered"] == 1
        assert trace["probabilities_estimated"] == 1

    @pytest.mark.asyncio
    async def test_with_discovery_error(
        self, prediction_state: AgentState
    ) -> None:
        """Test graceful handling of market discovery errors."""
        with patch(
            "quant_nanggroe_ai.agents.nodes.prediction_market._discover_markets",
            new_callable=AsyncMock,
        ) as mock_discover:
            mock_discover.side_effect = Exception("API unavailable")
            result = await prediction_market_node(prediction_state)

        # Should still return valid output with errors
        assert "macro_context" in result
        assert any("Market discovery" in e for e in result["errors"])

    @pytest.mark.asyncio
    async def test_default_symbol_and_query(
        self, standard_state: AgentState
    ) -> None:
        """Test fallback when no query is provided."""
        with patch(
            "quant_nanggroe_ai.agents.nodes.prediction_market._discover_markets",
            new_callable=AsyncMock,
        ) as mock_discover:
            mock_discover.return_value = [
                {
                    "platform": "placeholder",
                    "question": "Test market",
                    "status": "no_results",
                }
            ]
            result = await prediction_market_node(standard_state)

        # Should use symbol as query fallback
        assert "macro_context" in result

    @pytest.mark.asyncio
    async def test_multiple_markets(
        self, prediction_state: AgentState
    ) -> None:
        """Test handling of multiple discovered markets."""
        with patch(
            "quant_nanggroe_ai.agents.nodes.prediction_market._discover_markets",
            new_callable=AsyncMock,
        ) as mock_discover:
            mock_discover.return_value = [
                {
                    "platform": "polymarket",
                    "question": f"Question {i}",
                    "yes_price": 0.5 + i * 0.05,
                    "condition_id": f"cond_{i}",
                    "volume": 10000.0,
                    "liquidity": 5000.0,
                }
                for i in range(8)  # More than the 5-market limit
            ]
            result = await prediction_market_node(prediction_state)

        trace = result["agent_trace"][0]
        # Should limit to top 5 markets for probability estimation
        assert trace["probabilities_estimated"] <= 5
