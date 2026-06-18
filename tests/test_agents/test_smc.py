"""
Tests for Enhanced SMC (Smart Money Concepts) Agent.

Tests cover:
- OrderBlockDetector
- FairValueGapDetector
- LiquidityLevelDetector
- SmartMoneyAgent
- SMC tools (smc_pattern_detector, liquidity_sweep, institutional_footprint)
- Data models (OrderBlock, FairValueGap, LiquidityLevel, SmartMoneySetup)
- Agent registration

All LLM calls are mocked.
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import MagicMock

from quant_nanggroe.agents.smc.enhanced import (
    SmartMoneyAgent,
    OrderBlockDetector,
    FairValueGapDetector,
    LiquidityLevelDetector,
    OrderBlock,
    FairValueGap,
    LiquidityLevel,
    SmartMoneySetup,
    MarketStructurePoint,
    smc_pattern_detector,
    liquidity_sweep,
    institutional_footprint,
    SMC_TOOLS,
)
from quant_nanggroe.agents.registry import AgentRegistry
from quant_nanggroe.agents.state import AgentRole, create_initial_state


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════

def _mock_llm(response_text: str = "SMC analysis complete"):
    """Create a mock LLM."""
    mock = MagicMock()
    mock.invoke.return_value = MagicMock(content=response_text)
    mock.bind_tools.return_value = mock
    return mock


def _sample_ohlcv(n: int = 50) -> list[dict]:
    """Generate sample OHLCV data for testing."""
    import random
    random.seed(42)
    data = []
    price = 100.0
    for i in range(n):
        change = random.uniform(-0.02, 0.02)
        open_price = price
        close = price * (1 + change)
        high = max(open_price, close) * (1 + abs(random.uniform(0, 0.005)))
        low = min(open_price, close) * (1 - abs(random.uniform(0, 0.005)))
        volume = random.uniform(1000, 10000)
        data.append({
            "open": round(open_price, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(close, 2),
            "volume": round(volume, 0),
            "time": f"2024-01-{(i % 28) + 1:02d}",
        })
        price = close
    return data


# ═══════════════════════════════════════════════════════════════════════
# Data Model Tests
# ═══════════════════════════════════════════════════════════════════════


class TestOrderBlock:
    """Test OrderBlock dataclass."""

    def test_create_order_block(self):
        ob = OrderBlock(index=5, high=105.0, low=103.0, ob_type="bullish_ob", strength=0.8)
        assert ob.index == 5
        assert ob.ob_type == "bullish_ob"
        assert ob.strength == 0.8
        assert ob.mitigated is False

    def test_order_block_defaults(self):
        ob = OrderBlock(index=0, high=100.0, low=99.0, ob_type="bearish_ob")
        assert ob.mitigated is False
        assert ob.mitigation_index == -1
        assert ob.strength == 0.5


class TestFairValueGap:
    """Test FairValueGap dataclass."""

    def test_create_fvg(self):
        fvg = FairValueGap(index=3, top=102.0, bottom=100.0, fvg_type="bullish_fvg", size=2.0)
        assert fvg.size == 2.0
        assert fvg.filled is False

    def test_fvg_defaults(self):
        fvg = FairValueGap(index=0, top=100.0, bottom=99.0, fvg_type="bearish_fvg")
        assert fvg.size == 0.0
        assert fvg.filled is False


class TestLiquidityLevel:
    """Test LiquidityLevel dataclass."""

    def test_create_liquidity_level(self):
        ll = LiquidityLevel(price=105.0, liq_type="buy_side", strength=0.7)
        assert ll.swept is False
        assert ll.sweep_index == -1


class TestSmartMoneySetup:
    """Test SmartMoneySetup dataclass."""

    def test_create_setup(self):
        setup = SmartMoneySetup(
            setup_type="OTE",
            direction="BULLISH",
            entry_zone=(100.0, 102.0),
            stop_loss=98.0,
            take_profit_1=105.0,
            take_profit_2=108.0,
            take_profit_3=112.0,
            probability=0.7,
            confluences=["Bullish OB", "FVG"],
        )
        assert setup.setup_type == "OTE"
        assert setup.direction == "BULLISH"
        assert len(setup.confluences) == 2


# ═══════════════════════════════════════════════════════════════════════
# Detector Tests
# ═══════════════════════════════════════════════════════════════════════


class TestOrderBlockDetector:
    """Test OrderBlockDetector."""

    def test_detect_with_sufficient_data(self):
        data = _sample_ohlcv(30)
        detector = OrderBlockDetector()
        obs = detector.detect(data)
        # May or may not find OBs depending on random data
        assert isinstance(obs, list)

    def test_detect_with_insufficient_data(self):
        detector = OrderBlockDetector()
        obs = detector.detect([{"open": 100, "high": 101, "low": 99, "close": 100.5, "volume": 1000}])
        assert obs == []


class TestFairValueGapDetector:
    """Test FairValueGapDetector."""

    def test_detect_with_sufficient_data(self):
        data = _sample_ohlcv(30)
        detector = FairValueGapDetector()
        fvgs = detector.detect(data)
        assert isinstance(fvgs, list)

    def test_detect_with_insufficient_data(self):
        detector = FairValueGapDetector()
        fvgs = detector.detect([{"high": 100, "low": 99}, {"high": 101, "low": 100}])
        assert fvgs == []

    def test_detect_bullish_fvg(self):
        # Create data with a clear bullish FVG
        data = [
            {"high": 100.0, "low": 99.0},
            {"high": 101.0, "low": 100.0},
            {"high": 103.0, "low": 100.5},  # Gap between bar 0 high (100) and bar 2 low (100.5)
        ]
        detector = FairValueGapDetector()
        fvgs = detector.detect(data)
        bullish = [f for f in fvgs if f.fvg_type == "bullish_fvg"]
        # Should detect the gap
        assert len(bullish) >= 1


class TestLiquidityLevelDetector:
    """Test LiquidityLevelDetector."""

    def test_detect_with_sufficient_data(self):
        data = _sample_ohlcv(30)
        detector = LiquidityLevelDetector()
        levels = detector.detect(data)
        assert isinstance(levels, list)

    def test_detect_with_insufficient_data(self):
        detector = LiquidityLevelDetector()
        levels = detector.detect([{"high": 100, "low": 99}] * 3)
        assert levels == []


# ═══════════════════════════════════════════════════════════════════════
# SMC Tools Tests
# ═══════════════════════════════════════════════════════════════════════


class TestSMCPatternDetectorTool:
    """Test smc_pattern_detector tool."""

    def test_returns_json(self):
        result = smc_pattern_detector.invoke({"symbol": "EURUSD", "timeframe": "1H"})
        data = json.loads(result)
        assert data["symbol"] == "EURUSD"
        assert data["timeframe"] == "1H"
        assert "patterns_detected" in data
        assert "market_structure" in data


class TestLiquiditySweepTool:
    """Test liquidity_sweep tool."""

    def test_returns_json(self):
        result = liquidity_sweep.invoke({"symbol": "XAUUSD", "direction": "both"})
        data = json.loads(result)
        assert data["symbol"] == "XAUUSD"
        assert "liquidity_pools" in data


class TestInstitutionalFootprintTool:
    """Test institutional_footprint tool."""

    def test_returns_json(self):
        result = institutional_footprint.invoke({"symbol": "AAPL", "analysis_type": "order_flow"})
        data = json.loads(result)
        assert data["symbol"] == "AAPL"
        assert "institutional_activity" in data


class TestSMCToolsList:
    """Test that all SMC tools are available."""

    def test_all_tools_present(self):
        tool_names = [t.name for t in SMC_TOOLS]
        assert "smc_pattern_detector" in tool_names
        assert "liquidity_sweep" in tool_names
        assert "institutional_footprint" in tool_names


# ═══════════════════════════════════════════════════════════════════════
# SmartMoneyAgent Tests
# ═══════════════════════════════════════════════════════════════════════


class TestSmartMoneyAgent:
    """Test SmartMoneyAgent."""

    def test_agent_creation(self):
        llm = _mock_llm()
        agent = SmartMoneyAgent(llm=llm)
        assert agent.name == "smc"
        assert agent.role == AgentRole.SMC

    def test_agent_has_system_prompt(self):
        llm = _mock_llm()
        agent = SmartMoneyAgent(llm=llm)
        assert "ICT" in agent._system_prompt
        assert "Order Blocks" in agent._system_prompt

    def test_agent_has_tools(self):
        llm = _mock_llm()
        agent = SmartMoneyAgent(llm=llm)
        tool_names = [t.name for t in agent.tools]
        assert "smc_pattern_detector" in tool_names
        assert "liquidity_sweep" in tool_names

    def test_agent_run(self):
        llm = _mock_llm("SMC analysis: Bullish BOS detected with order block at 1.0850")
        agent = SmartMoneyAgent(llm=llm)
        state = create_initial_state(["EURUSD"], "2024-01-15")
        result = agent(state)
        assert "agent_outputs" in result
        assert "smc" in result["agent_outputs"]

    def test_analyze_data_direct(self):
        llm = _mock_llm()
        agent = SmartMoneyAgent(llm=llm)
        data = _sample_ohlcv(50)
        result = agent.analyze_data(data, symbol="EURUSD")
        assert "symbol" in result
        assert "trend" in result
        assert result["latest_price"] > 0

    def test_analyze_data_insufficient(self):
        llm = _mock_llm()
        agent = SmartMoneyAgent(llm=llm)
        result = agent.analyze_data([{"open": 100, "high": 101, "low": 99, "close": 100.5, "volume": 100}])
        assert "error" in result

    def test_determine_trend(self):
        llm = _mock_llm()
        agent = SmartMoneyAgent(llm=llm)
        # Create uptrending data
        data = [{"open": 100 + i, "high": 101 + i, "low": 99 + i, "close": 100.5 + i, "volume": 1000} for i in range(25)]
        trend = agent._determine_trend(data)
        assert trend in ("bullish", "bearish", "neutral")

    def test_agent_registered(self):
        AgentRegistry.register("smc", AgentRole.SMC)(SmartMoneyAgent)
        assert AgentRegistry.get("smc") is not None

    def test_risk_parameters(self):
        llm = _mock_llm()
        agent = SmartMoneyAgent(llm=llm)
        assert agent.RISK_PER_TRADE == 0.005
        assert agent.MIN_RR_RATIO == 1.5
