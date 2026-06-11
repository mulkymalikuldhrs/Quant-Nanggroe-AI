"""Shared test fixtures for Quant Nanggroe AI."""

import pytest
from datetime import datetime
from quant_nanggroe.types.market import OHLCV, Ticker, MarketData, TimeFrame
from quant_nanggroe.types.orders import Order, OrderType, OrderSide, OrderStatus, MarketOrder
from quant_nanggroe.types.positions import Position, PositionSide, Portfolio
from quant_nanggroe.types.signals import Signal, SignalType
from quant_nanggroe.types.risk import RiskAssessment, RiskLevel
from quant_nanggroe.types.decisions import Decision, DecisionType


@pytest.fixture
def sample_ohlcv():
    """Sample OHLCV candlestick data."""
    return OHLCV(
        symbol="BTC/USDT",
        timestamp=datetime(2024, 1, 1, 0, 0, 0),
        open=42000.0,
        high=42500.0,
        low=41800.0,
        close=42300.0,
        volume=1000.0,
    )


@pytest.fixture
def sample_ohlcv_series():
    """Series of OHLCV data for testing."""
    candles = []
    base_price = 42000.0
    for i in range(100):
        candles.append(
            OHLCV(
                symbol="BTC/USDT",
                timestamp=datetime(2024, 1, 1, 0, 0, 0),
                open=base_price + i * 10,
                high=base_price + i * 10 + 100,
                low=base_price + i * 10 - 80,
                close=base_price + i * 10 + 50,
                volume=500.0 + i * 5,
            )
        )
    return candles


@pytest.fixture
def sample_ticker():
    """Sample ticker data."""
    return Ticker(
        symbol="BTC/USDT",
        timestamp=datetime.now(),
        last_price=42300.0,
        bid=42295.0,
        ask=42305.0,
        high_24h=42500.0,
        low_24h=41800.0,
        volume_24h=50000.0,
        change_pct_24h=1.2,
    )


@pytest.fixture
def sample_market_data(sample_ohlcv_series, sample_ticker):
    """Sample aggregated market data."""
    return MarketData(
        symbol="BTC/USDT",
        timeframe=TimeFrame.D1,
        ohlcv=sample_ohlcv_series,
        ticker=sample_ticker,
        provider="test",
    )


@pytest.fixture
def sample_order():
    """Sample market order."""
    return MarketOrder(
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        quantity=0.1,
        strategy_name="test_strategy",
        agent_name="test_agent",
    )


@pytest.fixture
def sample_position():
    """Sample open position."""
    return Position(
        symbol="BTC/USDT",
        side=PositionSide.LONG,
        quantity=0.1,
        entry_price=42000.0,
        current_price=42300.0,
        cost_basis=4200.0,
        market_value=4230.0,
    )


@pytest.fixture
def sample_portfolio(sample_position):
    """Sample portfolio with position."""
    portfolio = Portfolio(
        initial_capital=100000.0,
        cash=95770.0,
    )
    portfolio.positions["BTC/USDT"] = sample_position
    portfolio.recalculate()
    return portfolio


@pytest.fixture
def sample_signal():
    """Sample trading signal."""
    return Signal(
        symbol="BTC/USDT",
        signal_type=SignalType.BUY,
        confidence=0.75,
        price=42300.0,
        target_price=45000.0,
        stop_loss=41000.0,
        source_agent="strategist",
        reasoning="Strong uptrend with volume confirmation",
    )


@pytest.fixture
def sample_risk_assessment():
    """Sample risk assessment."""
    return RiskAssessment(
        symbol="BTC/USDT",
        risk_level=RiskLevel.LOW,
        approved=True,
        confidence=0.8,
        per_trade_risk_pct=0.4,
        daily_loss_pct=0.3,
        weekly_loss_pct=1.2,
        current_drawdown_pct=2.1,
    )


@pytest.fixture
def sample_decision():
    """Sample trading decision."""
    return Decision(
        symbol="BTC/USDT",
        decision_type=DecisionType.EXECUTE_BUY,
        confidence=0.75,
        reasoning="Bullish confluence from multiple agents",
    )
