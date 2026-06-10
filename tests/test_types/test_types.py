"""Tests for shared type definitions."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from quant_nanggroe.types.market import OHLCV, Ticker, TimeFrame
from quant_nanggroe.types.orders import Order, OrderType, OrderSide, MarketOrder, LimitOrder
from quant_nanggroe.types.positions import Position, PositionSide, Portfolio
from quant_nanggroe.types.signals import Signal, SignalType, SignalStrength
from quant_nanggroe.types.risk import RiskAssessment, RiskLevel
from quant_nanggroe.types.decisions import Decision, DecisionType, ConfluenceScore


class TestOHLCV:
    def test_valid_ohlcv(self):
        ohlcv = OHLCV(
            symbol="BTC/USDT",
            timestamp=datetime.now(),
            open=42000.0,
            high=42500.0,
            low=41800.0,
            close=42300.0,
            volume=1000.0,
        )
        assert ohlcv.symbol == "BTC/USDT"
        assert ohlcv.close == 42300.0

    def test_negative_price_rejected(self):
        with pytest.raises(ValidationError):
            OHLCV(
                symbol="BTC/USDT",
                timestamp=datetime.now(),
                open=-1.0,
                high=42500.0,
                low=41800.0,
                close=42300.0,
                volume=1000.0,
            )

    def test_zero_volume_accepted(self):
        ohlcv = OHLCV(
            symbol="BTC/USDT",
            timestamp=datetime.now(),
            open=42000.0,
            high=42500.0,
            low=41800.0,
            close=42300.0,
            volume=0.0,
        )
        assert ohlcv.volume == 0.0


class TestOrder:
    def test_market_order(self):
        order = MarketOrder(symbol="BTC/USDT", side=OrderSide.BUY, quantity=0.1)
        assert order.order_type == OrderType.MARKET
        assert order.status == OrderStatus.PENDING

    def test_limit_order_requires_price(self):
        order = LimitOrder(
            symbol="BTC/USDT",
            side=OrderSide.SELL,
            quantity=0.1,
            price=45000.0,
        )
        assert order.price == 45000.0
        assert order.order_type == OrderType.LIMIT


class TestPosition:
    def test_position_update_price_long(self):
        pos = Position(
            symbol="BTC/USDT",
            side=PositionSide.LONG,
            quantity=0.1,
            entry_price=42000.0,
            current_price=42000.0,
            cost_basis=4200.0,
        )
        pos.update_price(42500.0)
        assert pos.unrealized_pnl == pytest.approx(50.0)
        assert pos.unrealized_pnl_pct > 0

    def test_position_update_price_short(self):
        pos = Position(
            symbol="BTC/USDT",
            side=PositionSide.SHORT,
            quantity=0.1,
            entry_price=42000.0,
            current_price=42000.0,
            cost_basis=4200.0,
        )
        pos.update_price(41500.0)
        assert pos.unrealized_pnl == pytest.approx(50.0)


class TestPortfolio:
    def test_portfolio_recalculate(self):
        portfolio = Portfolio(initial_capital=100000.0, cash=95800.0)
        pos = Position(
            symbol="BTC/USDT",
            side=PositionSide.LONG,
            quantity=0.1,
            entry_price=42000.0,
            current_price=42500.0,
            cost_basis=4200.0,
            market_value=4250.0,
        )
        portfolio.positions["BTC/USDT"] = pos
        portfolio.recalculate()
        assert portfolio.total_unrealized_pnl == pytest.approx(50.0)
        assert portfolio.position_value == 4250.0


class TestSignal:
    def test_signal_strength_computation(self):
        signal = Signal(
            symbol="BTC/USDT",
            signal_type=SignalType.BUY,
            confidence=0.85,
            source_agent="test",
        )
        assert signal.compute_strength() == SignalStrength.VERY_STRONG

    def test_weak_signal(self):
        signal = Signal(
            symbol="BTC/USDT",
            signal_type=SignalType.BUY,
            confidence=0.2,
            source_agent="test",
        )
        assert signal.compute_strength() == SignalStrength.WEAK


class TestConfluenceScore:
    def test_bullish_consensus(self):
        cs = ConfluenceScore(total_agents=5, bullish_agents=4, bearish_agents=1)
        assert cs.compute_consensus() == "bullish"

    def test_bearish_consensus(self):
        cs = ConfluenceScore(total_agents=5, bullish_agents=1, bearish_agents=4)
        assert cs.compute_consensus() == "bearish"

    def test_conflicted_consensus(self):
        cs = ConfluenceScore(total_agents=5, bullish_agents=2, bearish_agents=2, neutral_agents=1)
        assert cs.compute_consensus() == "conflicted"


class TestRiskAssessment:
    def test_approved_assessment(self):
        ra = RiskAssessment(
            symbol="BTC/USDT",
            risk_level=RiskLevel.LOW,
            approved=True,
            confidence=0.8,
        )
        assert ra.approved is True
        assert ra.veto is False

    def test_veto_assessment(self):
        ra = RiskAssessment(
            symbol="BTC/USDT",
            risk_level=RiskLevel.BREACH,
            approved=False,
            veto=True,
            veto_reason="Daily loss limit exceeded",
        )
        assert ra.veto is True
        assert ra.approved is False
