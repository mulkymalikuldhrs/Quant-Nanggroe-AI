"""Tests for Trading Council module."""

from __future__ import annotations

import pytest

from quant_nanggroe_ai.agents.council.trading_council import (
    CouncilConfig,
    CouncilResult,
    TradingCouncil,
)


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def council_config() -> CouncilConfig:
    return CouncilConfig(
        max_debate_rounds=2,
        consensus_threshold=0.6,
        risk_veto_enabled=True,
    )


@pytest.fixture
def sample_market_data() -> dict:
    return {
        "price": 65000.0,
        "change_24h": 2.5,
        "volume_24h": 1_500_000_000,
        "volatility_30d": 0.45,
        "rsi_14": 62.0,
        "macd_signal": "bullish",
        "market_regime": "TRENDING_UP",
        "fear_greed_index": 72,
    }


# ── CouncilConfig ─────────────────────────────────────────────────────────

class TestCouncilConfig:
    def test_defaults(self):
        config = CouncilConfig()
        assert config.max_debate_rounds == 3
        assert config.consensus_threshold == 0.7
        assert config.risk_veto_enabled is True

    def test_custom_config(self, council_config):
        assert council_config.max_debate_rounds == 2
        assert council_config.consensus_threshold == 0.6


# ── CouncilResult ─────────────────────────────────────────────────────────

class TestCouncilResult:
    def test_create_result(self):
        result = CouncilResult(
            action="BUY",
            confidence=0.85,
            reasoning="Strong bullish consensus",
            risk_score=0.3,
            position_size_pct=5.0,
            agent_votes={"researcher": "BUY", "risk": "BUY"},
        )
        assert result.action == "BUY"
        assert result.confidence == 0.85
        assert result.risk_score == 0.3


# ── TradingCouncil ────────────────────────────────────────────────────────

class TestTradingCouncil:
    def test_create_council_default(self):
        council = TradingCouncil()
        assert council is not None

    def test_create_council_with_config(self, council_config):
        council = TradingCouncil(council_config)
        assert council is not None

    @pytest.mark.asyncio
    async def test_run_with_sample_data(self, council_config, sample_market_data):
        council = TradingCouncil(council_config)
        result = await council.run(symbol="BTC/USDT", data=sample_market_data)
        assert isinstance(result, CouncilResult)
        assert result.action in ("BUY", "SELL", "HOLD")
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.agent_votes, dict)
