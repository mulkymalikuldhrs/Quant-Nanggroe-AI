"""Tests for quant_nanggroe.types — all type definitions."""

import os
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("CACHE_BACKEND", "memory")

from datetime import datetime, timezone

import pytest

from quant_nanggroe.types.market import (
    OHLCV, Ticker, OrderBook, OrderBookLevel, DataMetadata, Interval,
)
from quant_nanggroe.types.orders import (
    OrderSide, OrderType, OrderStatus, Order, MarketOrder,
    LimitOrder, StopOrder, StopLimitOrder,
)
from quant_nanggroe.types.positions import Position, PositionSide, PositionStatus
from quant_nanggroe.types.signals import SignalAction, Signal, StrategySignal, ConsensusReport
from quant_nanggroe.types.risk import (
    RiskMetrics, VaRResult, DrawdownResult, TradingConstitution, VaRMethod,
)
from quant_nanggroe.types.agents import (
    AgentState, AgentConfig, AgentCapability, AgentStatus, AgentContract,
)
from quant_nanggroe.types.decisions import (
    MarketRegime, VolatilityLevel, LiquidityLevel, PressureState,
    ConfluenceStatus, DecisionTableEntry, DecisionSynthesis,
)


# ── Market Types ──


class TestOHLCV:
    def test_create_valid_candle(self):
        candle = OHLCV(
            symbol="BTC/USDT",
            timestamp=datetime.now(tz=timezone.utc),
            open=42500.0,
            high=43100.0,
            low=42200.0,
            close=42800.0,
            volume=12345.67,
        )
        assert candle.symbol == "BTC/USDT"
        assert candle.open == 42500.0
        assert candle.close == 42800.0
        assert candle.interval == Interval.DAY_1

    def test_invalid_negative_price(self):
        with pytest.raises(Exception):
            OHLCV(
                symbol="BTC/USDT",
                timestamp=datetime.now(tz=timezone.utc),
                open=-1.0,
                high=43100.0,
                low=42200.0,
                close=42800.0,
                volume=1000.0,
            )

    def test_json_serialization(self):
        candle = OHLCV(
            symbol="BTC/USDT",
            timestamp=datetime(2024, 1, 15, tzinfo=timezone.utc),
            open=42500.0,
            high=43100.0,
            low=42200.0,
            close=42800.0,
            volume=12345.67,
        )
        json_str = candle.model_dump_json()
        restored = OHLCV.model_validate_json(json_str)
        assert restored.symbol == candle.symbol
        assert restored.close == candle.close


class TestTicker:
    def test_create_ticker(self):
        ticker = Ticker(
            symbol="BTC/USDT",
            current_price=42800.0,
            price_change_24h=800.0,
            price_change_pct_24h=1.9,
        )
        assert ticker.symbol == "BTC/USDT"
        assert ticker.current_price == 42800.0

    def test_zero_price_rejected(self):
        with pytest.raises(Exception):
            Ticker(symbol="TEST", current_price=0.0)


class TestOrderBook:
    def test_create_orderbook(self):
        book = OrderBook(
            symbol="BTC/USDT",
            timestamp=datetime.now(tz=timezone.utc),
            bids=[OrderBookLevel(price=42790.0, quantity=1.5)],
            asks=[OrderBookLevel(price=42810.0, quantity=1.2)],
        )
        assert book.best_bid == 42790.0
        assert book.best_ask == 42810.0
        assert book.spread == 20.0
        assert book.spread_pct is not None
        assert book.spread_pct > 0

    def test_empty_orderbook(self):
        book = OrderBook(
            symbol="BTC/USDT",
            timestamp=datetime.now(tz=timezone.utc),
        )
        assert book.best_bid is None
        assert book.best_ask is None
        assert book.spread is None


class TestDataMetadata:
    def test_default_trust_score(self):
        meta = DataMetadata(source="test")
        assert meta.trust_score == 1.0

    def test_invalid_trust_score(self):
        with pytest.raises(Exception):
            DataMetadata(source="test", trust_score=1.5)


# ── Order Types ──


class TestMarketOrder:
    def test_create_market_order(self):
        order = MarketOrder(symbol="BTC/USDT", side=OrderSide.BUY, quantity=0.5)
        assert order.order_type == OrderType.MARKET
        assert order.status == OrderStatus.PENDING

    def test_invalid_quantity(self):
        with pytest.raises(Exception):
            MarketOrder(symbol="BTC/USDT", side=OrderSide.BUY, quantity=-1.0)


class TestLimitOrder:
    def test_create_limit_order(self):
        order = LimitOrder(
            symbol="BTC/USDT", side=OrderSide.BUY, quantity=0.5, limit_price=42000.0,
        )
        assert order.order_type == OrderType.LIMIT
        assert order.limit_price == 42000.0


class TestStopOrder:
    def test_create_stop_order(self):
        order = StopOrder(
            symbol="BTC/USDT", side=OrderSide.SELL, quantity=0.5, stop_price=40000.0,
        )
        assert order.order_type == OrderType.STOP
        assert order.stop_price == 40000.0


# ── Position Types ──


class TestPosition:
    def test_long_position_unrealized_pnl(self):
        pos = Position(
            id="pos_1",
            symbol="BTC/USDT",
            side=PositionSide.LONG,
            entry_price=42000.0,
            current_price=42800.0,
            quantity=0.5,
            entry_time=datetime.now(tz=timezone.utc),
        )
        assert pos.unrealized_pnl == 400.0
        assert pos.unrealized_pnl_pct > 0

    def test_short_position_unrealized_pnl(self):
        pos = Position(
            id="pos_2",
            symbol="BTC/USDT",
            side=PositionSide.SHORT,
            entry_price=42000.0,
            current_price=41000.0,
            quantity=0.5,
            entry_time=datetime.now(tz=timezone.utc),
        )
        assert pos.unrealized_pnl == 500.0

    def test_closed_position_realized_pnl(self):
        pos = Position(
            id="pos_3",
            symbol="BTC/USDT",
            side=PositionSide.LONG,
            status=PositionStatus.CLOSED,
            entry_price=42000.0,
            current_price=42800.0,
            exit_price=42800.0,
            quantity=0.5,
            entry_time=datetime.now(tz=timezone.utc),
        )
        assert pos.realized_pnl == 400.0

    def test_notional_value(self):
        pos = Position(
            id="pos_4",
            symbol="BTC/USDT",
            side=PositionSide.LONG,
            entry_price=42000.0,
            current_price=42800.0,
            quantity=1.0,
            leverage=2.0,
            entry_time=datetime.now(tz=timezone.utc),
        )
        assert pos.notional_value == 85600.0


# ── Signal Types ──


class TestSignal:
    def test_create_signal(self):
        signal = Signal(
            id="sig_1",
            symbol="BTC/USDT",
            action=SignalAction.BUY,
            confidence=0.85,
            source="quant_scanner",
        )
        assert signal.action == SignalAction.BUY
        assert signal.confidence == 0.85

    def test_invalid_confidence(self):
        with pytest.raises(Exception):
            Signal(
                id="sig_1",
                symbol="BTC/USDT",
                action=SignalAction.BUY,
                confidence=1.5,
                source="test",
            )


class TestConsensusReport:
    def test_create_consensus(self):
        report = ConsensusReport(
            score=0.65,
            verdict="BUY",
            total_signals=5,
            bullish_count=4,
            bearish_count=1,
            top_factors=["RSI oversold"],
        )
        assert report.verdict == "BUY"
        assert report.total_signals == 5


# ── Risk Types ──


class TestVaRResult:
    def test_create_var_result(self):
        result = VaRResult(
            method=VaRMethod.PARAMETRIC,
            confidence_level=0.95,
            var=0.0234,
            expected_shortfall=0.0312,
            confidence_interval=(-0.04, 0.02),
        )
        assert result.method == VaRMethod.PARAMETRIC
        assert result.confidence_level == 0.95


class TestTradingConstitution:
    def test_default_constitution(self):
        constitution = TradingConstitution()
        assert constitution.no_trade_is_valid_decision is True
        assert constitution.max_leverage == 3.0
        assert constitution.daily_drawdown_limit == 0.05


# ── Agent Types ──


class TestAgentConfig:
    def test_create_agent_config(self):
        config = AgentConfig(
            agent_id="quant_01",
            name="Quant Scanner",
            capability=AgentCapability.QUANT,
        )
        assert config.capability == AgentCapability.QUANT
        assert config.enabled is True


class TestAgentState:
    def test_signal_success_rate(self):
        state = AgentState(
            agent_id="quant_01",
            total_signals=100,
            successful_signals=62,
        )
        assert state.signal_success_rate == 0.62

    def test_zero_signals_rate(self):
        state = AgentState(agent_id="quant_01")
        assert state.signal_success_rate == 0.0


# ── Decision Types ──


class TestMarketRegime:
    def test_all_regimes(self):
        regimes = [r.value for r in MarketRegime]
        assert "TRENDING" in regimes
        assert "NO_TRADE" in regimes
        assert "PANIC" in regimes


class TestPressureState:
    def test_create_pressure_state(self):
        state = PressureState(
            buy_pressure=0.72,
            sell_pressure=0.28,
            confidence_score=0.72,
        )
        assert abs(state.net_pressure - 0.44) < 0.001
        assert state.total_pressure == 1.0

    def test_invalid_pressure_range(self):
        with pytest.raises(Exception):
            PressureState(buy_pressure=1.5, sell_pressure=0.28, confidence_score=0.5)


class TestDecisionSynthesis:
    def test_create_decision(self):
        decision = DecisionSynthesis(
            regime=MarketRegime.TRENDING,
            pressures=PressureState(buy_pressure=0.72, sell_pressure=0.28, confidence_score=0.72),
            confluence=ConfluenceStatus(is_allowed=True, score=0.82),
            risk_clearance="CLEAR",
            action="BUY",
        )
        assert decision.action == "BUY"
        assert decision.regime == MarketRegime.TRENDING
