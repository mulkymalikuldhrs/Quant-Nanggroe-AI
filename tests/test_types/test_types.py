"""Comprehensive tests for Type definitions.

Tests all Pydantic models in the types package for:
- Valid construction
- Field validation
- Enum values
- Model-specific behavior (e.g., Position.update_price, Signal.compute_strength, ConfluenceScore)
"""

from __future__ import annotations

import pytest
from datetime import datetime
from pydantic import ValidationError

from quant_nanggroe.types.market import (
    OHLCV, Ticker, OrderBook, OrderBookLevel, MarketData, TimeFrame,
)
from quant_nanggroe.types.orders import (
    Order, OrderType, OrderSide, OrderStatus,
    MarketOrder, LimitOrder, StopOrder, StopLimitOrder,
)
from quant_nanggroe.types.positions import (
    Position, PositionSide, Portfolio,
)
from quant_nanggroe.types.signals import (
    Signal, SignalType, SignalStrength,
)
from quant_nanggroe.types.risk import (
    RiskAssessment, RiskLevel, VaRResult, DrawdownResult, PositionSizingResult,
)
from quant_nanggroe.types.decisions import (
    Decision, DecisionType, DecisionTable, ConfluenceScore,
)


# ═══════════════════════════════════════════════════════════════════════════
# Market Types Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestTimeFrame:
    def test_all_values(self):
        assert TimeFrame.M1.value == "1m"
        assert TimeFrame.H1.value == "1h"
        assert TimeFrame.D1.value == "1d"
        assert TimeFrame.W1.value == "1w"

    def test_from_string(self):
        assert TimeFrame("1d") == TimeFrame.D1


class TestOHLCV:
    def test_valid_creation(self):
        candle = OHLCV(
            symbol="BTC/USDT", timestamp=datetime.now(),
            open=50000, high=50500, low=49500, close=50200, volume=1000,
        )
        assert candle.close == 50200

    def test_positive_price_required(self):
        with pytest.raises(ValidationError):
            OHLCV(
                symbol="BTC/USDT", timestamp=datetime.now(),
                open=-1, high=50500, low=49500, close=50200, volume=1000,
            )

    def test_zero_volume_allowed(self):
        candle = OHLCV(
            symbol="BTC/USDT", timestamp=datetime.now(),
            open=50000, high=50500, low=49500, close=50200, volume=0,
        )
        assert candle.volume == 0

    def test_negative_volume_rejected(self):
        with pytest.raises(ValidationError):
            OHLCV(
                symbol="BTC/USDT", timestamp=datetime.now(),
                open=50000, high=50500, low=49500, close=50200, volume=-1,
            )

    def test_from_attributes(self):
        candle = OHLCV(
            symbol="BTC/USDT", timestamp=datetime.now(),
            open=50000, high=50500, low=49500, close=50200, volume=1000,
        )
        assert candle.model_config.get("from_attributes") is True


class TestTicker:
    def test_valid_creation(self):
        ticker = Ticker(
            symbol="BTC/USDT", timestamp=datetime.now(), last_price=50000.0,
        )
        assert ticker.last_price == 50000.0

    def test_positive_price_required(self):
        with pytest.raises(ValidationError):
            Ticker(symbol="BTC/USDT", timestamp=datetime.now(), last_price=0)

    def test_optional_fields(self):
        ticker = Ticker(symbol="BTC/USDT", timestamp=datetime.now(), last_price=50000.0)
        assert ticker.bid is None
        assert ticker.ask is None
        assert ticker.volume_24h is None


class TestOrderBookLevel:
    def test_valid(self):
        level = OrderBookLevel(price=50000.0, quantity=1.5)
        assert level.price == 50000.0

    def test_zero_rejected(self):
        with pytest.raises(ValidationError):
            OrderBookLevel(price=0, quantity=1.5)
        with pytest.raises(ValidationError):
            OrderBookLevel(price=50000.0, quantity=0)


class TestOrderBook:
    def test_valid(self):
        ob = OrderBook(symbol="BTC/USDT", timestamp=datetime.now())
        assert ob.bids == []
        assert ob.asks == []

    def test_with_levels(self):
        ob = OrderBook(
            symbol="BTC/USDT", timestamp=datetime.now(),
            bids=[OrderBookLevel(price=49999.0, quantity=1.0)],
            asks=[OrderBookLevel(price=50001.0, quantity=2.0)],
        )
        assert len(ob.bids) == 1


class TestMarketData:
    def test_default_timeframe(self):
        md = MarketData(symbol="BTC/USDT")
        assert md.timeframe == TimeFrame.D1

    def test_with_ohlcv(self):
        md = MarketData(
            symbol="BTC/USDT",
            ohlcv=[OHLCV(
                symbol="BTC/USDT", timestamp=datetime.now(),
                open=50000, high=50500, low=49500, close=50200, volume=1000,
            )],
        )
        assert len(md.ohlcv) == 1


# ═══════════════════════════════════════════════════════════════════════════
# Order Types Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestOrderType:
    def test_all_values(self):
        assert OrderType.MARKET.value == "market"
        assert OrderType.LIMIT.value == "limit"
        assert OrderType.STOP.value == "stop"
        assert OrderType.STOP_LIMIT.value == "stop_limit"
        assert OrderType.TRAILING_STOP.value == "trailing_stop"
        assert OrderType.TAKE_PROFIT.value == "take_profit"


class TestOrderSide:
    def test_values(self):
        assert OrderSide.BUY.value == "buy"
        assert OrderSide.SELL.value == "sell"


class TestOrderStatus:
    def test_all_values(self):
        assert OrderStatus.PENDING.value == "pending"
        assert OrderStatus.FILLED.value == "filled"
        assert OrderStatus.CANCELED.value == "canceled"
        assert OrderStatus.REJECTED.value == "rejected"


class TestOrder:
    def test_basic_order(self):
        order = Order(
            symbol="BTC/USDT", side=OrderSide.BUY,
            order_type=OrderType.MARKET, quantity=0.5,
        )
        assert order.quantity == 0.5
        assert order.status == OrderStatus.PENDING

    def test_quantity_must_be_positive(self):
        with pytest.raises(ValidationError):
            Order(symbol="BTC/USDT", side=OrderSide.BUY,
                  order_type=OrderType.MARKET, quantity=0)

    def test_symbol_required(self):
        with pytest.raises(ValidationError):
            Order(side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=0.5)

    def test_price_must_be_positive(self):
        with pytest.raises(ValidationError):
            Order(symbol="BTC/USDT", side=OrderSide.BUY,
                  order_type=OrderType.LIMIT, quantity=0.5, price=-1)


class TestMarketOrder:
    def test_type_set_automatically(self):
        order = MarketOrder(symbol="BTC/USDT", side=OrderSide.BUY, quantity=0.5)
        assert order.order_type == OrderType.MARKET


class TestLimitOrder:
    def test_requires_price(self):
        order = LimitOrder(symbol="BTC/USDT", side=OrderSide.BUY, quantity=0.5, price=50000.0)
        assert order.order_type == OrderType.LIMIT
        assert order.price == 50000.0

    def test_price_required(self):
        with pytest.raises(ValidationError):
            LimitOrder(symbol="BTC/USDT", side=OrderSide.BUY, quantity=0.5)


class TestStopOrder:
    def test_requires_stop_price(self):
        order = StopOrder(symbol="BTC/USDT", side=OrderSide.SELL, quantity=0.5, stop_price=49000.0)
        assert order.order_type == OrderType.STOP
        assert order.stop_price == 49000.0


class TestStopLimitOrder:
    def test_requires_both_prices(self):
        order = StopLimitOrder(
            symbol="BTC/USDT", side=OrderSide.BUY, quantity=0.5,
            price=50000.0, stop_price=49900.0,
        )
        assert order.order_type == OrderType.STOP_LIMIT


# ═══════════════════════════════════════════════════════════════════════════
# Position Types Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestPositionSide:
    def test_values(self):
        assert PositionSide.LONG.value == "long"
        assert PositionSide.SHORT.value == "short"
        assert PositionSide.FLAT.value == "flat"


class TestPosition:
    def test_create(self):
        pos = Position(
            symbol="BTC/USDT", side=PositionSide.LONG,
            quantity=0.5, entry_price=50000.0, current_price=51000.0,
            cost_basis=25000.0,
        )
        assert pos.quantity == 0.5

    def test_quantity_must_be_positive(self):
        with pytest.raises(ValidationError):
            Position(
                symbol="BTC/USDT", side=PositionSide.LONG,
                quantity=0, entry_price=50000.0, current_price=51000.0,
                cost_basis=25000.0,
            )

    def test_update_price_long(self):
        pos = Position(
            symbol="BTC/USDT", side=PositionSide.LONG,
            quantity=0.5, entry_price=50000.0, current_price=50000.0,
            cost_basis=25000.0,
        )
        pos.update_price(52000.0)
        expected_pnl = (52000.0 - 50000.0) * 0.5  # 1000
        assert abs(pos.unrealized_pnl - expected_pnl) < 1e-6

    def test_update_price_short(self):
        pos = Position(
            symbol="BTC/USDT", side=PositionSide.SHORT,
            quantity=0.5, entry_price=50000.0, current_price=50000.0,
            cost_basis=25000.0,
        )
        pos.update_price(48000.0)
        expected_pnl = (50000.0 - 48000.0) * 0.5  # 1000
        assert abs(pos.unrealized_pnl - expected_pnl) < 1e-6

    def test_update_price_market_value(self):
        pos = Position(
            symbol="BTC/USDT", side=PositionSide.LONG,
            quantity=0.5, entry_price=50000.0, current_price=50000.0,
            cost_basis=25000.0,
        )
        pos.update_price(52000.0)
        assert pos.market_value == 0.5 * 52000.0

    def test_update_price_max_min_tracking(self):
        pos = Position(
            symbol="BTC/USDT", side=PositionSide.LONG,
            quantity=0.5, entry_price=50000.0, current_price=50000.0,
            cost_basis=25000.0,
        )
        pos.update_price(52000.0)
        assert pos.max_price == 52000.0
        pos.update_price(48000.0)
        assert pos.min_price == 48000.0


class TestPortfolio:
    def test_create(self):
        portfolio = Portfolio(initial_capital=100000.0, cash=100000.0)
        assert portfolio.initial_capital == 100000.0

    def test_position_value_empty(self):
        portfolio = Portfolio(initial_capital=100000.0, cash=100000.0)
        assert portfolio.position_value == 0.0

    def test_is_invested_false(self):
        portfolio = Portfolio(initial_capital=100000.0, cash=100000.0)
        assert not portfolio.is_invested

    def test_is_invested_true(self):
        portfolio = Portfolio(
            initial_capital=100000.0, cash=50000.0,
            positions={
                "BTC/USDT": Position(
                    symbol="BTC/USDT", side=PositionSide.LONG,
                    quantity=0.5, entry_price=50000.0, current_price=51000.0,
                    cost_basis=25000.0, market_value=25500.0,
                ),
            },
        )
        assert portfolio.is_invested

    def test_recalculate(self):
        portfolio = Portfolio(
            initial_capital=100000.0, cash=50000.0,
            positions={
                "BTC/USDT": Position(
                    symbol="BTC/USDT", side=PositionSide.LONG,
                    quantity=0.5, entry_price=50000.0, current_price=52000.0,
                    cost_basis=25000.0, unrealized_pnl=1000.0, market_value=26000.0,
                ),
            },
        )
        portfolio.recalculate()
        assert portfolio.total_unrealized_pnl == 1000.0
        assert portfolio.total_value == 76000.0  # cash + position_value


# ═══════════════════════════════════════════════════════════════════════════
# Signal Types Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestSignalType:
    def test_all_values(self):
        assert SignalType.BUY.value == "buy"
        assert SignalType.SELL.value == "sell"
        assert SignalType.HOLD.value == "hold"
        assert SignalType.CLOSE_LONG.value == "close_long"
        assert SignalType.CLOSE_SHORT.value == "close_short"
        assert SignalType.EXIT_ALL.value == "exit_all"


class TestSignalStrength:
    def test_all_values(self):
        assert SignalStrength.WEAK.value == "weak"
        assert SignalStrength.MODERATE.value == "moderate"
        assert SignalStrength.STRONG.value == "strong"
        assert SignalStrength.VERY_STRONG.value == "very_strong"


class TestSignalModel:
    def test_create(self):
        signal = Signal(
            symbol="BTC/USDT", signal_type=SignalType.BUY,
            confidence=0.8, source_agent="researcher",
        )
        assert signal.confidence == 0.8

    def test_confidence_range(self):
        with pytest.raises(ValidationError):
            Signal(symbol="BTC/USDT", signal_type=SignalType.BUY,
                   confidence=1.5, source_agent="researcher")

    def test_compute_strength_very_strong(self):
        signal = Signal(
            symbol="BTC/USDT", signal_type=SignalType.BUY,
            confidence=0.85, source_agent="researcher",
        )
        assert signal.compute_strength() == SignalStrength.VERY_STRONG

    def test_compute_strength_strong(self):
        signal = Signal(
            symbol="BTC/USDT", signal_type=SignalType.BUY,
            confidence=0.7, source_agent="researcher",
        )
        assert signal.compute_strength() == SignalStrength.STRONG

    def test_compute_strength_moderate(self):
        signal = Signal(
            symbol="BTC/USDT", signal_type=SignalType.BUY,
            confidence=0.45, source_agent="researcher",
        )
        assert signal.compute_strength() == SignalStrength.MODERATE

    def test_compute_strength_weak(self):
        signal = Signal(
            symbol="BTC/USDT", signal_type=SignalType.BUY,
            confidence=0.2, source_agent="researcher",
        )
        assert signal.compute_strength() == SignalStrength.WEAK

    def test_symbol_required(self):
        with pytest.raises(ValidationError):
            Signal(signal_type=SignalType.BUY, confidence=0.8, source_agent="researcher")

    def test_source_agent_required(self):
        with pytest.raises(ValidationError):
            Signal(symbol="BTC/USDT", signal_type=SignalType.BUY, confidence=0.8)


# ═══════════════════════════════════════════════════════════════════════════
# Risk Types Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestRiskLevel:
    def test_all_values(self):
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MODERATE.value == "moderate"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"
        assert RiskLevel.BREACH.value == "breach"


class TestRiskAssessmentModel:
    def test_create_default(self):
        ra = RiskAssessment(symbol="BTC/USDT")
        assert ra.risk_level == RiskLevel.LOW
        assert ra.approved is True
        assert ra.veto is False

    def test_all_checks_default_true(self):
        ra = RiskAssessment(symbol="BTC/USDT")
        assert ra.check_per_trade_risk is True
        assert ra.check_daily_loss is True
        assert ra.check_weekly_loss is True
        assert ra.check_max_drawdown is True

    def test_veto_with_reason(self):
        ra = RiskAssessment(
            symbol="BTC/USDT", approved=False, veto=True,
            veto_reason="Daily loss exceeded",
        )
        assert ra.veto is True


class TestVaRResultModel:
    def test_create(self):
        result = VaRResult(
            var_value=0.02, cvar_value=0.03,
            confidence_level=0.95, time_horizon=1,
            method="parametric", portfolio_value=1_000_000,
            var_pct=2.0, cvar_pct=3.0,
        )
        assert result.cvar_value >= result.var_value

    def test_confidence_level_range(self):
        with pytest.raises(ValidationError):
            VaRResult(
                var_value=0.02, cvar_value=0.03,
                confidence_level=0.5, time_horizon=1,
                method="parametric", portfolio_value=1_000_000,
                var_pct=2.0, cvar_pct=3.0,
            )


class TestDrawdownResultModel:
    def test_create(self):
        result = DrawdownResult(
            current_drawdown=0.05, max_drawdown=0.10,
            peak_value=1_100_000, current_value=1_045_000,
        )
        assert result.current_drawdown == 0.05


class TestPositionSizingResultModel:
    def test_create(self):
        result = PositionSizingResult(
            symbol="BTC/USDT", position_size=0.5,
            position_value=25000.0, risk_amount=500.0,
            risk_pct=0.5, method="kelly",
        )
        assert result.method == "kelly"


# ═══════════════════════════════════════════════════════════════════════════
# Decision Types Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestDecisionType:
    def test_all_values(self):
        assert DecisionType.EXECUTE_BUY.value == "execute_buy"
        assert DecisionType.EXECUTE_SELL.value == "execute_sell"
        assert DecisionType.HOLD_POSITION.value == "hold_position"
        assert DecisionType.CLOSE_POSITION.value == "close_position"
        assert DecisionType.VETO.value == "veto"
        assert DecisionType.DEFER.value == "defer"
        assert DecisionType.EMERGENCY_EXIT.value == "emergency_exit"


class TestConfluenceScore:
    def test_create_default(self):
        cs = ConfluenceScore()
        assert cs.total_agents == 0
        assert cs.avg_confidence == 0.0

    def test_compute_consensus_no_data(self):
        cs = ConfluenceScore(total_agents=0)
        assert cs.compute_consensus() == "no_data"

    def test_compute_consensus_bullish(self):
        cs = ConfluenceScore(total_agents=10, bullish_agents=7, bearish_agents=2, neutral_agents=1)
        assert cs.compute_consensus() == "bullish"

    def test_compute_consensus_bearish(self):
        cs = ConfluenceScore(total_agents=10, bullish_agents=2, bearish_agents=7, neutral_agents=1)
        assert cs.compute_consensus() == "bearish"

    def test_compute_consensus_conflicted(self):
        cs = ConfluenceScore(total_agents=10, bullish_agents=4, bearish_agents=4, neutral_agents=2)
        assert cs.compute_consensus() == "conflicted"

    def test_compute_consensus_neutral(self):
        cs = ConfluenceScore(total_agents=10, bullish_agents=2, bearish_agents=2, neutral_agents=6)
        assert cs.compute_consensus() == "neutral"

    def test_confidence_validation(self):
        with pytest.raises(ValidationError):
            ConfluenceScore(avg_confidence=1.5)

    def test_weighted_score_range(self):
        with pytest.raises(ValidationError):
            ConfluenceScore(weighted_score=2.0)


class TestDecisionTable:
    def test_create(self):
        dt = DecisionTable(
            name="Buy Signal",
            conditions={"momentum": "positive", "rsi": "< 70"},
            action=DecisionType.EXECUTE_BUY,
        )
        assert dt.action == DecisionType.EXECUTE_BUY

    def test_priority_default(self):
        dt = DecisionTable(name="Test", conditions={}, action=DecisionType.HOLD_POSITION)
        assert dt.priority == 0

    def test_priority_validation(self):
        with pytest.raises(ValidationError):
            DecisionTable(name="Test", conditions={}, action=DecisionType.HOLD_POSITION, priority=-1)


class TestDecisionModel:
    def test_create(self):
        decision = Decision(
            symbol="BTC/USDT",
            decision_type=DecisionType.EXECUTE_BUY,
            confidence=0.8,
        )
        assert decision.confidence == 0.8

    def test_confidence_validation(self):
        with pytest.raises(ValidationError):
            Decision(symbol="BTC/USDT", decision_type=DecisionType.EXECUTE_BUY, confidence=1.5)

    def test_with_confluence(self):
        cs = ConfluenceScore(total_agents=5, bullish_agents=4, avg_confidence=0.8)
        decision = Decision(
            symbol="BTC/USDT",
            decision_type=DecisionType.EXECUTE_BUY,
            confluence=cs,
        )
        assert decision.confluence.total_agents == 5

    def test_with_agent_votes(self):
        decision = Decision(
            symbol="BTC/USDT",
            decision_type=DecisionType.EXECUTE_BUY,
            agent_votes={"researcher": "bullish", "risk": "neutral"},
        )
        assert len(decision.agent_votes) == 2
