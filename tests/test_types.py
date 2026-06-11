"""
Tests for Shared Types — Pydantic Models & Enums
=================================================
Validates all Pydantic models and enums in types.py,
including field constraints, default values, and edge cases.
"""

from __future__ import annotations

import pytest
from datetime import datetime
from pydantic import ValidationError

from quant_nanggroe_ai.types import (
    MarketRegime,
    VolatilityLevel,
    LiquidityLevel,
    TradeDirection,
    RiskClearance,
    DecisionAction,
    StrategyStatus,
    NewsEventType,
    AgentCapability,
    CandleData,
    DataMetadata,
    TradingConstitution,
    PressureState,
    MarketState,
    RiskCheckpointResult,
    RiskVerdict,
    DecisionSynthesis,
    EntryParameters,
    QuantScannerOutput,
    SMCOutput,
    NewsSentinelOutput,
    FlowWhaleOutput,
    StrategyLifecycle,
    PortfolioPosition,
    TradeHistoryItem,
)


# ══════════════════════════════════════════════════════════════════════
# ENUM TESTS
# ══════════════════════════════════════════════════════════════════════


class TestMarketRegime:
    """Test MarketRegime enum."""

    def test_all_values(self) -> None:
        expected = {
            "TRENDING_UP", "TRENDING_DOWN", "TRENDING", "RANGE",
            "MEAN_REVERT", "RISK_OFF", "PANIC", "NO_TRADE",
            "CALM", "VOLATILE", "UNKNOWN",
        }
        assert {e.value for e in MarketRegime} == expected

    def test_string_comparison(self) -> None:
        assert MarketRegime.TRENDING_UP == "TRENDING_UP"
        assert MarketRegime.UNKNOWN == "UNKNOWN"


class TestVolatilityLevel:
    def test_values(self) -> None:
        assert {e.value for e in VolatilityLevel} == {"LOW", "NORMAL", "HIGH"}


class TestLiquidityLevel:
    def test_values(self) -> None:
        assert {e.value for e in LiquidityLevel} == {"THIN", "NORMAL", "DEEP"}


class TestTradeDirection:
    def test_values(self) -> None:
        assert {e.value for e in TradeDirection} == {"BUY", "SELL", "LONG", "SHORT"}


class TestRiskClearance:
    def test_values(self) -> None:
        assert {e.value for e in RiskClearance} == {"CLEAR", "BLOCKED", "PAUSE"}


class TestDecisionAction:
    def test_values(self) -> None:
        expected = {
            "ALLOW_LONG", "ALLOW_SHORT", "ALLOW_LONG_TRENDING",
            "ALLOW_SHORT_TRENDING", "WATCH_LONG", "WATCH_SHORT", "NO_TRADE",
        }
        assert {e.value for e in DecisionAction} == expected


class TestStrategyStatus:
    def test_values(self) -> None:
        expected = {"ACTIVE", "HIBERNATING", "KILLED", "INCUBATING"}
        assert {e.value for e in StrategyStatus} == expected


class TestNewsEventType:
    def test_values(self) -> None:
        assert {e.value for e in NewsEventType} == {"MACRO", "SCHEDULED", "SHOCK", "NOISE"}


class TestAgentCapability:
    def test_values(self) -> None:
        expected = {
            "portfolio-manager", "quant", "fundamental",
            "risk-manager", "algo-dev", "general",
        }
        assert {e.value for e in AgentCapability} == expected


# ══════════════════════════════════════════════════════════════════════
# MARKET DATA TYPES
# ══════════════════════════════════════════════════════════════════════


class TestCandleData:
    def test_valid_candle(self) -> None:
        now = datetime.now()
        candle = CandleData(
            timestamp=now, open=100.0, high=105.0, low=99.0,
            close=103.0, volume=5000.0,
        )
        assert candle.close == 103.0
        assert candle.volume == 5000.0

    def test_default_volume(self) -> None:
        now = datetime.now()
        candle = CandleData(
            timestamp=now, open=100.0, high=105.0, low=99.0, close=103.0,
        )
        assert candle.volume == 0.0

    def test_missing_required_field(self) -> None:
        with pytest.raises(ValidationError):
            CandleData(timestamp=datetime.now(), open=100.0)  # type: ignore[call-arg]


class TestDataMetadata:
    def test_valid_metadata(self) -> None:
        meta = DataMetadata(source="binance", trust_score=0.95)
        assert meta.source == "binance"
        assert meta.trust_score == 0.95
        assert meta.update_frequency == "realtime"

    def test_trust_score_bounds(self) -> None:
        DataMetadata(source="test", trust_score=0.0)
        DataMetadata(source="test", trust_score=1.0)
        with pytest.raises(ValidationError):
            DataMetadata(source="test", trust_score=-0.1)
        with pytest.raises(ValidationError):
            DataMetadata(source="test", trust_score=1.1)


# ══════════════════════════════════════════════════════════════════════
# ENGINE TYPES
# ══════════════════════════════════════════════════════════════════════


class TestTradingConstitution:
    def test_defaults(self) -> None:
        tc = TradingConstitution()
        assert tc.risk_greater_than_opportunity is True
        assert tc.max_leverage == 1
        assert tc.max_correlation == 0.7
        assert tc.daily_drawdown_limit == 0.01

    def test_custom_values(self) -> None:
        tc = TradingConstitution(max_leverage=2, daily_drawdown_limit=0.02)
        assert tc.max_leverage == 2
        assert tc.daily_drawdown_limit == 0.02


class TestPressureState:
    def test_defaults(self) -> None:
        ps = PressureState()
        assert ps.buy_pressure == 0.0
        assert ps.sell_pressure == 0.0
        assert ps.volatility_risk == VolatilityLevel.NORMAL
        assert ps.confidence_score == 0.0

    def test_pressure_bounds(self) -> None:
        PressureState(buy_pressure=0.0, sell_pressure=1.0)
        with pytest.raises(ValidationError):
            PressureState(buy_pressure=-0.1)
        with pytest.raises(ValidationError):
            PressureState(sell_pressure=1.1)

    def test_confidence_score_bounds(self) -> None:
        PressureState(confidence_score=0.0)
        PressureState(confidence_score=1.0)
        with pytest.raises(ValidationError):
            PressureState(confidence_score=1.5)


class TestMarketStateModel:
    def test_defaults(self) -> None:
        ms = MarketState()
        assert ms.regime == MarketRegime.UNKNOWN
        assert ms.volatility == VolatilityLevel.NORMAL
        assert ms.liquidity == LiquidityLevel.NORMAL

    def test_custom_regime(self) -> None:
        ms = MarketState(regime=MarketRegime.TRENDING_UP)
        assert ms.regime == MarketRegime.TRENDING_UP


class TestRiskCheckpointResult:
    def test_creation(self) -> None:
        rcr = RiskCheckpointResult(
            name="test_check", value="0.5%", limit="1.0%", passed=True,
        )
        assert rcr.passed is True

    def test_failed_check(self) -> None:
        rcr = RiskCheckpointResult(
            name="test_check", value="2.0%", limit="1.0%", passed=False,
        )
        assert rcr.passed is False


class TestRiskVerdict:
    def test_creation(self) -> None:
        rv = RiskVerdict(
            symbol="EURUSD", direction="BUY", verdict="APPROVED", risk_pct=0.005,
            checkpoints={
                "1_test": RiskCheckpointResult(
                    name="1_test", value="ok", limit="1", passed=True,
                )
            },
        )
        assert rv.verdict == "APPROVED"
        assert rv.symbol == "EURUSD"

    def test_default_counters(self) -> None:
        rv = RiskVerdict(
            symbol="X", direction="BUY", verdict="VETOED", risk_pct=0.01,
            checkpoints={},
        )
        assert rv.veto_count_total == 0
        assert rv.approval_count_total == 0


class TestDecisionSynthesis:
    def test_defaults(self) -> None:
        ds = DecisionSynthesis(
            regime=MarketRegime.UNKNOWN,
            pressures=PressureState(),
        )
        assert ds.risk_clearance == RiskClearance.BLOCKED
        assert ds.action == DecisionAction.NO_TRADE
        assert ds.confidence == 0.0

    def test_with_action(self) -> None:
        ds = DecisionSynthesis(
            regime=MarketRegime.TRENDING_UP,
            pressures=PressureState(),
            risk_clearance=RiskClearance.CLEAR,
            action=DecisionAction.ALLOW_LONG,
            confidence=0.85,
            reason="Strong uptrend",
        )
        assert ds.action == DecisionAction.ALLOW_LONG
        assert ds.confidence == 0.85


class TestEntryParameters:
    def test_creation(self) -> None:
        ep = EntryParameters(
            location="DISCOUNT_ZONE", trigger="fvg", execution="LIMIT",
            entry=1.1000, sl=1.0950, tp=[1.1100, 1.1200],
        )
        assert ep.entry == 1.1000
        assert len(ep.tp) == 2


# ══════════════════════════════════════════════════════════════════════
# AGENT TYPES
# ══════════════════════════════════════════════════════════════════════


class TestQuantScannerOutput:
    def test_defaults(self) -> None:
        qs = QuantScannerOutput()
        assert qs.trend_strength == 0.5
        assert qs.structure_state == "NEUTRAL"
        assert qs.volatility_expansion is False

    def test_bounds(self) -> None:
        with pytest.raises(ValidationError):
            QuantScannerOutput(trend_strength=1.5)
        with pytest.raises(ValidationError):
            QuantScannerOutput(trend_strength=-0.1)


class TestSMCOutput:
    def test_defaults(self) -> None:
        smc = SMCOutput()
        assert smc.liquidity_sweep is False
        assert smc.displacement_strength == 0.0

    def test_bounds(self) -> None:
        with pytest.raises(ValidationError):
            SMCOutput(displacement_strength=1.5)


class TestNewsSentinelOutput:
    def test_defaults(self) -> None:
        ns = NewsSentinelOutput()
        assert ns.event_type == NewsEventType.NOISE
        assert ns.impact_score == 0.0

    def test_bounds(self) -> None:
        with pytest.raises(ValidationError):
            NewsSentinelOutput(impact_score=1.5)


class TestFlowWhaleOutput:
    def test_defaults(self) -> None:
        fw = FlowWhaleOutput()
        assert fw.positioning_bias == "NEUTRAL"
        assert fw.flow_imbalance == 0.0


class TestStrategyLifecycle:
    def test_creation(self) -> None:
        sl = StrategyLifecycle(id="s1", name="test_strategy")
        assert sl.status == StrategyStatus.ACTIVE
        assert sl.death_threshold == 20

    def test_custom_values(self) -> None:
        sl = StrategyLifecycle(
            id="s2", name="momentum",
            status=StrategyStatus.HIBERNATING,
            sharpe_ratio=1.5,
            win_rate=0.6,
        )
        assert sl.status == StrategyStatus.HIBERNATING
        assert sl.sharpe_ratio == 1.5


# ══════════════════════════════════════════════════════════════════════
# PORTFOLIO TYPES
# ══════════════════════════════════════════════════════════════════════


class TestPortfolioPosition:
    def test_creation(self) -> None:
        pos = PortfolioPosition(
            ticker="AAPL", amount=100, avg_price=150.0, current_price=155.0,
        )
        assert pos.ticker == "AAPL"
        assert pos.pnl == 0.0

    def test_with_pnl(self) -> None:
        pos = PortfolioPosition(
            ticker="AAPL", amount=100, avg_price=150.0,
            current_price=155.0, pnl=500.0,
        )
        assert pos.pnl == 500.0


class TestTradeHistoryItem:
    def test_creation(self) -> None:
        now = datetime.now()
        item = TradeHistoryItem(
            id="t1", timestamp=now, ticker="EURUSD",
            action=TradeDirection.BUY, amount=0.01,
            price=1.1000, total_value=1100.0,
        )
        assert item.action == TradeDirection.BUY
        assert item.fees == 0.0
        assert item.realized_pnl is None
        assert item.triggered_by_signals == []

    def test_with_all_fields(self) -> None:
        now = datetime.now()
        item = TradeHistoryItem(
            id="t2", timestamp=now, ticker="BTCUSDT",
            action=TradeDirection.SELL, amount=0.5,
            price=50000.0, total_value=25000.0,
            fees=25.0, realized_pnl=500.0,
            triggered_by_signals=["rsi_overbought", "macd_cross"],
        )
        assert item.fees == 25.0
        assert item.realized_pnl == 500.0
        assert len(item.triggered_by_signals) == 2
