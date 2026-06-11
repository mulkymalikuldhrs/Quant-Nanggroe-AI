"""
Tests for Execution Agent Node
================================
Tests Smart Order Routing, venue selection, slippage estimation,
asset classification, latency monitoring, and pre-trade risk checks.
All external dependencies (ExecutionTool, KillSwitch, RiskGuard) are mocked.
"""

from __future__ import annotations

import time
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from quant_nanggroe_ai.agents.nodes.execution import (
    ExecutionVenue,
    VENUES,
    MAX_SLIPPAGE_BPS,
    LATENCY_WARNING_MS,
    LATENCY_CRITICAL_MS,
    MIN_VENUE_RELIABILITY,
    WEIGHT_COMMISSION,
    WEIGHT_SLIPPAGE,
    WEIGHT_LATENCY,
    WEIGHT_RELIABILITY,
    _classify_asset,
    _score_venue,
    _select_best_venue,
    _estimate_slippage,
    _monitor_latency,
    _pre_trade_risk_check,
    execution_node,
)
from quant_nanggroe_ai.agents.state import AgentState
from quant_nanggroe_ai.types import RiskClearance


# ══════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════


@pytest.fixture
def buy_state() -> AgentState:
    """Agent state with BUY signal and CLEAR risk."""
    return AgentState(
        symbol="AAPL",
        strategy_signal="BUY",
        risk_clearance=RiskClearance.CLEAR,
        entry_price=180.0,
        position_size=10.0,
        stop_loss=175.0,
        take_profit=[190.0, 195.0],
        agent_trace=[],
        errors=[],
    )


@pytest.fixture
def sell_state() -> AgentState:
    """Agent state with SELL signal and CLEAR risk."""
    return AgentState(
        symbol="BTCUSDT",
        strategy_signal="SELL",
        risk_clearance=RiskClearance.CLEAR,
        entry_price=50000.0,
        position_size=0.01,
        stop_loss=51000.0,
        take_profit=[48000.0],
        agent_trace=[],
        errors=[],
    )


@pytest.fixture
def blocked_state() -> AgentState:
    """Agent state with BLOCKED risk clearance."""
    return AgentState(
        symbol="EURUSD",
        strategy_signal="BUY",
        risk_clearance=RiskClearance.BLOCKED,
        agent_trace=[],
        errors=[],
    )


@pytest.fixture
def no_signal_state() -> AgentState:
    """Agent state with HOLD signal (no actionable signal)."""
    return AgentState(
        symbol="AAPL",
        strategy_signal="HOLD",
        risk_clearance=RiskClearance.CLEAR,
        agent_trace=[],
        errors=[],
    )


# ══════════════════════════════════════════════════════════════════════
# ExecutionVenue TESTS
# ══════════════════════════════════════════════════════════════════════


class TestExecutionVenue:
    def test_creation(self) -> None:
        venue = ExecutionVenue(
            name="TestExchange",
            asset_classes=["crypto", "equity"],
            avg_latency_ms=50.0,
            commission_bps=5.0,
            max_slippage_bps=3.0,
            reliability_score=0.99,
        )
        assert venue.name == "TestExchange"
        assert venue.reliability_score == 0.99

    def test_supports_asset(self) -> None:
        venue = ExecutionVenue(
            name="Test", asset_classes=["crypto"], avg_latency_ms=50.0,
            commission_bps=5.0, max_slippage_bps=3.0, reliability_score=0.99,
        )
        assert venue.supports_asset("crypto") is True
        assert venue.supports_asset("equity") is False


class TestPreconfiguredVenues:
    def test_all_venues_exist(self) -> None:
        expected = {"binance", "bybit", "alpaca", "jupiter", "polymarket", "paper"}
        assert set(VENUES.keys()) == expected

    def test_binance_supports_crypto(self) -> None:
        assert VENUES["binance"].supports_asset("crypto") is True

    def test_alpaca_supports_equity(self) -> None:
        assert VENUES["alpaca"].supports_asset("equity") is True

    def test_paper_supports_all(self) -> None:
        for asset_class in ["equity", "crypto", "forex", "prediction_market"]:
            assert VENUES["paper"].supports_asset(asset_class) is True

    def test_reliability_scores_valid(self) -> None:
        for key, venue in VENUES.items():
            assert 0.0 <= venue.reliability_score <= 1.0

    def test_sor_constants(self) -> None:
        assert MAX_SLIPPAGE_BPS == 50
        assert LATENCY_WARNING_MS == 200.0
        assert LATENCY_CRITICAL_MS == 1000.0
        assert MIN_VENUE_RELIABILITY == 0.90
        # Weight sums should be 1.0
        total = WEIGHT_COMMISSION + WEIGHT_SLIPPAGE + WEIGHT_LATENCY + WEIGHT_RELIABILITY
        assert abs(total - 1.0) < 0.001


# ══════════════════════════════════════════════════════════════════════
# ASSET CLASSIFICATION TESTS
# ══════════════════════════════════════════════════════════════════════


class TestClassifyAsset:
    def test_crypto_bitcoin(self) -> None:
        assert _classify_asset("BTCUSDT") == "crypto"

    def test_crypto_ethereum(self) -> None:
        assert _classify_asset("ETHUSD") == "crypto"

    def test_crypto_solana(self) -> None:
        assert _classify_asset("SOLUSDT") == "crypto_solana"

    def test_crypto_bonk(self) -> None:
        assert _classify_asset("BONKUSDT") == "crypto_solana"

    def test_forex_eurusd(self) -> None:
        assert _classify_asset("EURUSD") == "forex"

    def test_forex_gbpjpy(self) -> None:
        assert _classify_asset("GBPJPY") == "forex"

    def test_prediction_market(self) -> None:
        assert _classify_asset("PREDICT_ELECTION_2024") == "prediction_market"

    def test_prediction_polymarket(self) -> None:
        assert _classify_asset("POLYMARKET_YES") == "prediction_market"

    def test_prediction_kalshi(self) -> None:
        assert _classify_asset("KALSHI_RATE_HIKE") == "prediction_market"

    def test_equity_default(self) -> None:
        assert _classify_asset("AAPL") == "equity"

    def test_equity_spy(self) -> None:
        assert _classify_asset("SPY") == "equity"

    def test_usdt_suffix(self) -> None:
        assert _classify_asset("DOGEUSDT") == "crypto"


# ══════════════════════════════════════════════════════════════════════
# VENUE SCORING TESTS
# ══════════════════════════════════════════════════════════════════════


class TestScoreVenue:
    def test_zero_commission_venue_scores_higher(self) -> None:
        free_venue = ExecutionVenue(
            name="Free", asset_classes=["equity"], avg_latency_ms=50.0,
            commission_bps=0.0, max_slippage_bps=3.0, reliability_score=0.99,
        )
        paid_venue = ExecutionVenue(
            name="Paid", asset_classes=["equity"], avg_latency_ms=50.0,
            commission_bps=20.0, max_slippage_bps=3.0, reliability_score=0.99,
        )
        assert _score_venue(free_venue) > _score_venue(paid_venue)

    def test_lower_latency_scores_higher(self) -> None:
        fast_venue = ExecutionVenue(
            name="Fast", asset_classes=["crypto"], avg_latency_ms=10.0,
            commission_bps=5.0, max_slippage_bps=3.0, reliability_score=0.99,
        )
        slow_venue = ExecutionVenue(
            name="Slow", asset_classes=["crypto"], avg_latency_ms=500.0,
            commission_bps=5.0, max_slippage_bps=3.0, reliability_score=0.99,
        )
        assert _score_venue(fast_venue) > _score_venue(slow_venue)

    def test_higher_reliability_scores_higher(self) -> None:
        reliable = ExecutionVenue(
            name="Reliable", asset_classes=["equity"], avg_latency_ms=50.0,
            commission_bps=5.0, max_slippage_bps=3.0, reliability_score=0.99,
        )
        unreliable = ExecutionVenue(
            name="Unreliable", asset_classes=["equity"], avg_latency_ms=50.0,
            commission_bps=5.0, max_slippage_bps=3.0, reliability_score=0.91,
        )
        assert _score_venue(reliable) > _score_venue(unreliable)

    def test_estimated_slippage_affects_score(self) -> None:
        venue = VENUES["binance"]
        low_slip = _score_venue(venue, estimated_slippage_bps=1.0)
        high_slip = _score_venue(venue, estimated_slippage_bps=40.0)
        assert low_slip > high_slip

    def test_score_range(self) -> None:
        for key, venue in VENUES.items():
            score = _score_venue(venue)
            assert 0.0 <= score <= 100.0


# ══════════════════════════════════════════════════════════════════════
# VENUE SELECTION TESTS
# ══════════════════════════════════════════════════════════════════════


class TestSelectBestVenue:
    def test_equity_selects_venue(self) -> None:
        result = _select_best_venue("equity")
        assert result["selected_venue"] in ("alpaca", "paper")
        assert result["fallback"] is False or result["selected_venue"] == "paper"

    def test_crypto_selects_venue(self) -> None:
        result = _select_best_venue("crypto")
        assert result["selected_venue"] in ("binance", "bybit", "alpaca", "paper")

    def test_forex_selects_venue(self) -> None:
        result = _select_best_venue("forex")
        assert result["selected_venue"] == "paper"  # Only paper supports forex

    def test_prediction_market_selects_venue(self) -> None:
        result = _select_best_venue("prediction_market")
        assert result["selected_venue"] in ("polymarket", "paper")

    def test_result_has_required_fields(self) -> None:
        result = _select_best_venue("crypto")
        assert "selected_venue" in result
        assert "venue_name" in result
        assert "score" in result
        assert "reason" in result
        assert "alternatives" in result
        assert "fallback" in result

    def test_alternatives_are_sorted(self) -> None:
        result = _select_best_venue("crypto")
        if result["alternatives"]:
            scores = [a["score"] for a in result["alternatives"]]
            assert scores == sorted(scores, reverse=True)

    def test_unknown_asset_class_fallback(self) -> None:
        # Only paper supports all asset classes, so unknown class falls back
        result = _select_best_venue("nonexistent_class")
        assert result["selected_venue"] == "paper"
        assert result["fallback"] is True


# ══════════════════════════════════════════════════════════════════════
# SLIPPAGE ESTIMATION TESTS
# ══════════════════════════════════════════════════════════════════════


class TestEstimateSlippage:
    def test_small_order_slippage(self) -> None:
        slippage = _estimate_slippage("AAPL", 10.0, "alpaca")
        assert slippage >= 0
        assert slippage <= MAX_SLIPPAGE_BPS

    def test_large_order_more_slippage(self) -> None:
        small = _estimate_slippage("AAPL", 10.0, "alpaca")
        large = _estimate_slippage("AAPL", 1000.0, "alpaca")
        assert large >= small

    def test_unknown_venue_max_slippage(self) -> None:
        slippage = _estimate_slippage("AAPL", 10.0, "nonexistent_exchange")
        assert slippage == MAX_SLIPPAGE_BPS

    def test_slippage_capped(self) -> None:
        # Very large order should be capped at MAX_SLIPPAGE_BPS
        slippage = _estimate_slippage("AAPL", 100000.0, "alpaca")
        assert slippage <= MAX_SLIPPAGE_BPS


# ══════════════════════════════════════════════════════════════════════
# LATENCY MONITORING TESTS
# ══════════════════════════════════════════════════════════════════════


class TestMonitorLatency:
    def test_ok_latency(self) -> None:
        start = time.monotonic() - 0.001  # 1ms ago
        result = _monitor_latency(start)
        assert result["alert_level"] == "OK"
        assert result["latency_ms"] > 0

    def test_latency_result_fields(self) -> None:
        start = time.monotonic() - 0.001
        result = _monitor_latency(start)
        assert "latency_ms" in result
        assert "alert_level" in result
        assert "message" in result


# ══════════════════════════════════════════════════════════════════════
# PRE-TRADE RISK CHECK TESTS
# ══════════════════════════════════════════════════════════════════════


class TestPreTradeRiskCheck:
    def test_passes_with_valid_trade(self) -> None:
        with patch("quant_nanggroe_ai.agents.nodes.execution._get_kill_switch") as mock_ks, \
             patch("quant_nanggroe_ai.agents.nodes.execution._get_risk_guard") as mock_rg:
            mock_ks_inst = MagicMock()
            mock_ks_inst.is_active = False
            mock_ks.return_value = mock_ks_inst

            mock_rg_inst = MagicMock()
            mock_result = MagicMock()
            mock_result.verdict = "APPROVED"
            mock_rg_inst.check_trade.return_value = mock_result
            mock_rg.return_value = mock_rg_inst

            result = _pre_trade_risk_check(
                symbol="AAPL", direction="BUY",
                quantity=10.0, entry_price=180.0,
                stop_loss=175.0, take_profit=190.0,
            )
            assert result["passed"] is True

    def test_fails_with_kill_switch_active(self) -> None:
        with patch("quant_nanggroe_ai.agents.nodes.execution._get_kill_switch") as mock_ks:
            mock_ks_inst = MagicMock()
            mock_ks_inst.is_active = True
            mock_ks.return_value = mock_ks_inst

            result = _pre_trade_risk_check(
                symbol="AAPL", direction="BUY",
                quantity=10.0, entry_price=180.0,
                stop_loss=175.0, take_profit=190.0,
            )
            assert result["passed"] is False
            assert result["check"] == "kill_switch"

    def test_fails_with_risk_veto(self) -> None:
        with patch("quant_nanggroe_ai.agents.nodes.execution._get_kill_switch") as mock_ks, \
             patch("quant_nanggroe_ai.agents.nodes.execution._get_risk_guard") as mock_rg:
            mock_ks_inst = MagicMock()
            mock_ks_inst.is_active = False
            mock_ks.return_value = mock_ks_inst

            mock_rg_inst = MagicMock()
            mock_result = MagicMock()
            mock_result.verdict = "VETOED"
            mock_result.checkpoints = {"1_risk": MagicMock(passed=False)}
            mock_rg_inst.check_trade.return_value = mock_result
            mock_rg.return_value = mock_rg_inst

            result = _pre_trade_risk_check(
                symbol="AAPL", direction="BUY",
                quantity=10.0, entry_price=180.0,
                stop_loss=175.0, take_profit=190.0,
            )
            assert result["passed"] is False
            assert result["check"] == "risk_guard"

    def test_handles_risk_guard_exception(self) -> None:
        with patch("quant_nanggroe_ai.agents.nodes.execution._get_kill_switch") as mock_ks, \
             patch("quant_nanggroe_ai.agents.nodes.execution._get_risk_guard") as mock_rg:
            mock_ks_inst = MagicMock()
            mock_ks_inst.is_active = False
            mock_ks.return_value = mock_ks_inst

            mock_rg_inst = MagicMock()
            mock_rg_inst.check_trade.side_effect = Exception("Risk guard crashed")
            mock_rg.return_value = mock_rg_inst

            result = _pre_trade_risk_check(
                symbol="AAPL", direction="BUY",
                quantity=10.0, entry_price=180.0,
                stop_loss=175.0, take_profit=190.0,
            )
            assert result["passed"] is False
            assert result["check"] == "risk_guard_error"


# ══════════════════════════════════════════════════════════════════════
# EXECUTION NODE INTEGRATION TESTS
# ══════════════════════════════════════════════════════════════════════


class TestExecutionNode:
    """Test the main execution_node async function."""

    @pytest.mark.asyncio
    async def test_skipped_when_risk_blocked(self, blocked_state: AgentState) -> None:
        result = await execution_node(blocked_state)
        assert result["execution_status"] == "SKIPPED"
        assert len(result["agent_trace"]) == 1
        assert result["agent_trace"][0]["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_skipped_when_no_actionable_signal(
        self, no_signal_state: AgentState
    ) -> None:
        result = await execution_node(no_signal_state)
        assert result["execution_status"] == "SKIPPED"
        assert any("No actionable signal" in e for e in result["errors"])

    @pytest.mark.asyncio
    async def test_successful_execution(self, buy_state: AgentState) -> None:
        with patch("quant_nanggroe_ai.agents.nodes.execution._get_kill_switch") as mock_ks, \
             patch("quant_nanggroe_ai.agents.nodes.execution._get_risk_guard") as mock_rg, \
             patch("quant_nanggroe_ai.agents.nodes.execution.ExecutionTool") as mock_et:

            # Mock kill switch
            mock_ks_inst = MagicMock()
            mock_ks_inst.is_active = False
            mock_ks_inst.check_auto_trigger.return_value = {"status": "OK"}
            mock_ks.return_value = mock_ks_inst

            # Mock risk guard
            mock_rg_inst = MagicMock()
            mock_result = MagicMock()
            mock_result.verdict = "APPROVED"
            mock_rg_inst.check_trade.return_value = mock_result
            mock_rg.return_value = mock_rg_inst

            # Mock execution tool
            mock_et_inst = MagicMock()
            mock_et_inst.execute_order = AsyncMock(return_value={
                "status": "FILLED",
                "order_id": "ORD-123",
                "execution_price": 180.50,
                "slippage": 0.5,
            })
            mock_et.return_value = mock_et_inst

            result = await execution_node(buy_state)

            assert result["execution_status"] == "FILLED"
            assert result["order_id"] == "ORD-123"
            assert result["execution_price"] == 180.50
            assert len(result["agent_trace"]) == 1
            assert result["agent_trace"][0]["agent"] == "execution"
            assert result["agent_trace"][0]["selected_venue"] is not None

    @pytest.mark.asyncio
    async def test_rejected_by_risk_guard(self, buy_state: AgentState) -> None:
        with patch("quant_nanggroe_ai.agents.nodes.execution._get_kill_switch") as mock_ks, \
             patch("quant_nanggroe_ai.agents.nodes.execution._get_risk_guard") as mock_rg:

            mock_ks_inst = MagicMock()
            mock_ks_inst.is_active = False
            mock_ks.return_value = mock_ks_inst

            mock_rg_inst = MagicMock()
            mock_result = MagicMock()
            mock_result.verdict = "VETOED"
            mock_result.checkpoints = {"1_risk": MagicMock(passed=False)}
            mock_rg_inst.check_trade.return_value = mock_result
            mock_rg.return_value = mock_rg_inst

            result = await execution_node(buy_state)
            assert result["execution_status"] == "REJECTED"

    @pytest.mark.asyncio
    async def test_execution_tool_failure(self, buy_state: AgentState) -> None:
        with patch("quant_nanggroe_ai.agents.nodes.execution._get_kill_switch") as mock_ks, \
             patch("quant_nanggroe_ai.agents.nodes.execution._get_risk_guard") as mock_rg, \
             patch("quant_nanggroe_ai.agents.nodes.execution.ExecutionTool") as mock_et:

            mock_ks_inst = MagicMock()
            mock_ks_inst.is_active = False
            mock_ks_inst.check_auto_trigger.return_value = {"status": "OK"}
            mock_ks.return_value = mock_ks_inst

            mock_rg_inst = MagicMock()
            mock_result = MagicMock()
            mock_result.verdict = "APPROVED"
            mock_rg_inst.check_trade.return_value = mock_result
            mock_rg.return_value = mock_rg_inst

            mock_et_inst = MagicMock()
            mock_et_inst.execute_order = AsyncMock(
                side_effect=Exception("Connection refused")
            )
            mock_et.return_value = mock_et_inst

            result = await execution_node(buy_state)
            assert result["execution_status"] == "REJECTED"
            assert any("Connection refused" in e for e in result["errors"])

    @pytest.mark.asyncio
    async def test_crypto_symbol_routes_correctly(
        self, sell_state: AgentState
    ) -> None:
        """BTCUSDT should route to a crypto venue."""
        with patch("quant_nanggroe_ai.agents.nodes.execution._get_kill_switch") as mock_ks, \
             patch("quant_nanggroe_ai.agents.nodes.execution._get_risk_guard") as mock_rg, \
             patch("quant_nanggroe_ai.agents.nodes.execution.ExecutionTool") as mock_et:

            mock_ks_inst = MagicMock()
            mock_ks_inst.is_active = False
            mock_ks_inst.check_auto_trigger.return_value = {"status": "OK"}
            mock_ks.return_value = mock_ks_inst

            mock_rg_inst = MagicMock()
            mock_result = MagicMock()
            mock_result.verdict = "APPROVED"
            mock_rg_inst.check_trade.return_value = mock_result
            mock_rg.return_value = mock_rg_inst

            mock_et_inst = MagicMock()
            mock_et_inst.execute_order = AsyncMock(return_value={
                "status": "FILLED", "order_id": "O1",
                "execution_price": 50000.0, "slippage": 1.0,
            })
            mock_et.return_value = mock_et_inst

            result = await execution_node(sell_state)
            trace = result["agent_trace"][0]
            assert trace["asset_class"] == "crypto"

    @pytest.mark.asyncio
    async def test_default_symbol(self) -> None:
        """When symbol is empty, should default to SPY."""
        state = AgentState(
            symbol="",
            strategy_signal="BUY",
            risk_clearance=RiskClearance.CLEAR,
            entry_price=500.0,
            position_size=1.0,
            stop_loss=495.0,
            take_profit=[510.0],
            agent_trace=[],
            errors=[],
        )
        with patch("quant_nanggroe_ai.agents.nodes.execution._get_kill_switch") as mock_ks, \
             patch("quant_nanggroe_ai.agents.nodes.execution._get_risk_guard") as mock_rg, \
             patch("quant_nanggroe_ai.agents.nodes.execution.ExecutionTool") as mock_et:

            mock_ks_inst = MagicMock()
            mock_ks_inst.is_active = False
            mock_ks_inst.check_auto_trigger.return_value = {"status": "OK"}
            mock_ks.return_value = mock_ks_inst

            mock_rg_inst = MagicMock()
            mock_result = MagicMock()
            mock_result.verdict = "APPROVED"
            mock_rg_inst.check_trade.return_value = mock_result
            mock_rg.return_value = mock_rg_inst

            mock_et_inst = MagicMock()
            mock_et_inst.execute_order = AsyncMock(return_value={
                "status": "FILLED", "order_id": "O1",
                "execution_price": 500.0, "slippage": 0.0,
            })
            mock_et.return_value = mock_et_inst

            result = await execution_node(state)
            trace = result["agent_trace"][0]
            assert trace["symbol"] == "SPY"

    @pytest.mark.asyncio
    async def test_kill_switch_auto_activation(
        self, buy_state: AgentState
    ) -> None:
        with patch("quant_nanggroe_ai.agents.nodes.execution._get_kill_switch") as mock_ks, \
             patch("quant_nanggroe_ai.agents.nodes.execution._get_risk_guard") as mock_rg, \
             patch("quant_nanggroe_ai.agents.nodes.execution.ExecutionTool") as mock_et:

            mock_ks_inst = MagicMock()
            mock_ks_inst.is_active = False
            mock_ks_inst.check_auto_trigger.return_value = {"status": "ACTIVATED"}
            mock_ks.return_value = mock_ks_inst

            mock_rg_inst = MagicMock()
            mock_result = MagicMock()
            mock_result.verdict = "APPROVED"
            mock_rg_inst.check_trade.return_value = mock_result
            mock_rg.return_value = mock_rg_inst

            mock_et_inst = MagicMock()
            mock_et_inst.execute_order = AsyncMock(return_value={
                "status": "FILLED", "order_id": "O1",
                "execution_price": 180.0, "slippage": 0.0,
            })
            mock_et.return_value = mock_et_inst

            result = await execution_node(buy_state)
            assert any("Kill switch auto-activated" in e for e in result["errors"])

    @pytest.mark.asyncio
    async def test_latency_in_trace(self, buy_state: AgentState) -> None:
        with patch("quant_nanggroe_ai.agents.nodes.execution._get_kill_switch") as mock_ks, \
             patch("quant_nanggroe_ai.agents.nodes.execution._get_risk_guard") as mock_rg, \
             patch("quant_nanggroe_ai.agents.nodes.execution.ExecutionTool") as mock_et:

            mock_ks_inst = MagicMock()
            mock_ks_inst.is_active = False
            mock_ks_inst.check_auto_trigger.return_value = {"status": "OK"}
            mock_ks.return_value = mock_ks_inst

            mock_rg_inst = MagicMock()
            mock_result = MagicMock()
            mock_result.verdict = "APPROVED"
            mock_rg_inst.check_trade.return_value = mock_result
            mock_rg.return_value = mock_rg_inst

            mock_et_inst = MagicMock()
            mock_et_inst.execute_order = AsyncMock(return_value={
                "status": "FILLED", "order_id": "O1",
                "execution_price": 180.0, "slippage": 0.0,
            })
            mock_et.return_value = mock_et_inst

            result = await execution_node(buy_state)
            trace = result["agent_trace"][0]
            assert "latency_ms" in trace
            assert "latency_alert" in trace
            assert trace["latency_ms"] >= 0
