"""Pydantic Request/Response Schemas
===================================
Comprehensive request and response models for all API routes.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════════════
# Market Data
# ══════════════════════════════════════════════════════════════════════

class OHLCVRequest(BaseModel):
    """Request schema for OHLCV data."""

    symbol: str
    timeframe: str = "1d"
    limit: int = Field(default=100, ge=1, le=1000)


class OHLCVCandle(BaseModel):
    """Single OHLCV candle."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class OHLCVResponse(BaseModel):
    """Response schema for OHLCV data."""

    symbol: str
    timeframe: str
    data: list[OHLCVCandle] = Field(default_factory=list)
    count: int = 0


class PriceResponse(BaseModel):
    """Response schema for latest price."""

    symbol: str
    price: float | None
    timestamp: datetime = Field(default_factory=datetime.now)


class MarketRegimeRequest(BaseModel):
    """Request schema for market regime detection."""

    symbol: str
    price_change_5d: float = 0.0
    price_change_1d: float = 0.0
    adx: float = Field(default=20.0, ge=0.0)
    rsi: float = Field(default=50.0, ge=0.0, le=100.0)
    atr_pct: float = Field(default=1.0, ge=0.0)
    volume_ratio: float = Field(default=1.0, ge=0.0)
    ema_trend: str = "neutral"


class MarketRegimeResponse(BaseModel):
    """Response schema for market regime detection."""

    symbol: str
    regime: str
    base_regime: str
    volatility: str
    liquidity: str
    no_trade_reasons: list[str] = Field(default_factory=list)
    trade_allowed: bool = False
    inputs: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


# ══════════════════════════════════════════════════════════════════════
# Trading
# ══════════════════════════════════════════════════════════════════════

class OrderRequest(BaseModel):
    """Request schema for placing a trade order."""

    symbol: str
    direction: str  # BUY / SELL
    quantity: float = Field(gt=0)
    order_type: str = "MARKET"
    price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None


class OrderResponse(BaseModel):
    """Response schema for a placed order."""

    order_id: str
    status: str
    symbol: str
    direction: str
    quantity: float
    filled_price: float | None = None
    timestamp: datetime = Field(default_factory=datetime.now)


class PositionResponse(BaseModel):
    """Response schema for an open position."""

    ticker: str
    amount: float
    avg_price: float
    current_price: float
    pnl: float = 0.0
    last_updated: datetime = Field(default_factory=datetime.now)


class PositionsResponse(BaseModel):
    """Response schema for all open positions."""

    positions: list[PositionResponse] = Field(default_factory=list)
    total_count: int = 0


class TradeHistoryItem(BaseModel):
    """Single trade history record."""

    id: str
    timestamp: datetime
    ticker: str
    action: str
    amount: float
    price: float
    total_value: float
    fees: float = 0.0
    realized_pnl: float | None = None


class TradeHistoryResponse(BaseModel):
    """Response schema for trade history."""

    trades: list[TradeHistoryItem] = Field(default_factory=list)
    total_count: int = 0
    limit: int = 50


class RiskCheckRequest(BaseModel):
    """Request schema for a risk check."""

    symbol: str
    direction: str
    entry: float = Field(gt=0)
    stop_loss: float | None = None
    take_profit: float | None = None
    lot_size: float = Field(default=0.01, gt=0)
    account_balance: float = Field(default=10000.0, gt=0)


class RiskCheckpointResult(BaseModel):
    """Individual risk checkpoint result."""

    name: str
    value: str
    limit: str
    passed: bool


class RiskCheckResponse(BaseModel):
    """Response schema for a risk check."""

    symbol: str
    direction: str
    lot_size: float
    entry: float
    stop_loss: float | None
    take_profit: float | None
    risk_pct: float
    rr_ratio: float = 0.0
    verdict: str  # APPROVED or VETOED
    checkpoints: dict[str, RiskCheckpointResult]
    veto_count_total: int = 0
    approval_count_total: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)


# ══════════════════════════════════════════════════════════════════════
# Backtest
# ══════════════════════════════════════════════════════════════════════

class BacktestRequest(BaseModel):
    """Request schema for running a backtest."""

    symbol: str
    strategy: str
    start_date: str
    end_date: str
    initial_capital: float = Field(default=10000.0, gt=0)
    commission: float = Field(default=0.001, ge=0.0)
    slippage: float = Field(default=0.0005, ge=0.0)
    position_sizing: str = "fixed"


class BacktestSubmissionResponse(BaseModel):
    """Response schema for backtest submission."""

    backtest_id: str
    status: str = "QUEUED"
    symbol: str
    strategy: str
    submitted_at: datetime = Field(default_factory=datetime.now)
    message: str = "Backtest queued for execution"


class BacktestResultResponse(BaseModel):
    """Response schema for backtest results."""

    backtest_id: str
    status: str  # QUEUED, RUNNING, COMPLETED, FAILED
    symbol: str
    strategy: str
    total_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    profit_factor: float = 0.0
    avg_trade_pnl: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    equity_curve: list[float] = Field(default_factory=list)
    error: str | None = None


# ══════════════════════════════════════════════════════════════════════
# Agent
# ══════════════════════════════════════════════════════════════════════

class AgentRunRequest(BaseModel):
    """Request schema for running an agent pipeline."""

    symbol: str
    query: str = ""
    timeframe: str = "1d"


class AgentRunResponse(BaseModel):
    """Response schema for an agent run."""

    status: str
    symbol: str
    query: str
    agent_trace: list[dict[str, Any]] = Field(default_factory=list)
    decision_action: str = ""
    risk_verdict: str = ""
    strategy_signal: str = ""
    error: str | None = None


class AgentStatusResponse(BaseModel):
    """Response schema for agent status."""

    agents: list[dict[str, Any]] = Field(default_factory=list)
    active: bool = False
    kill_switch_active: bool = False
    timestamp: datetime = Field(default_factory=datetime.now)


class KillSwitchActivateRequest(BaseModel):
    """Request schema for activating the kill switch."""

    reason: str = "MANUAL"


class KillSwitchResetRequest(BaseModel):
    """Request schema for resetting the kill switch."""

    confirmation: str = ""


class KillSwitchStatusResponse(BaseModel):
    """Response schema for kill switch status."""

    is_active: bool
    activated_at: str | None = None
    activation_reason: str | None = None
    auto_triggers: int = 0
    manual_triggers: int = 0
    total_resets: int = 0
    message: str = ""


# ══════════════════════════════════════════════════════════════════════
# Portfolio
# ══════════════════════════════════════════════════════════════════════

class PortfolioSummaryResponse(BaseModel):
    """Response schema for portfolio summary."""

    total_value: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    positions: list[PositionResponse] = Field(default_factory=list)
    position_count: int = 0
    cash_balance: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)


class PortfolioRiskResponse(BaseModel):
    """Response schema for portfolio risk metrics."""

    var_95: float = 0.0
    cvar_95: float = 0.0
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    daily_pnl_pct: float = 0.0
    weekly_pnl_pct: float = 0.0
    daily_trades: int = 0
    risk_status: str = "OK"
    timestamp: datetime = Field(default_factory=datetime.now)


# ══════════════════════════════════════════════════════════════════════
# WebSocket
# ══════════════════════════════════════════════════════════════════════

class WSMarketDataMessage(BaseModel):
    """WebSocket market data message."""

    type: str = "market_data"
    symbol: str
    price: float
    volume: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)


class WSRegimeMessage(BaseModel):
    """WebSocket regime change message."""

    type: str = "regime_change"
    symbol: str
    regime: str
    trade_allowed: bool
    timestamp: datetime = Field(default_factory=datetime.now)


class WSCommandMessage(BaseModel):
    """WebSocket command message from client."""

    action: str  # subscribe, unsubscribe, ping
    symbols: list[str] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=list)  # price, regime, risk


class WSSubscriptionResponse(BaseModel):
    """WebSocket subscription confirmation."""

    type: str = "subscription"
    status: str  # confirmed, error
    symbols: list[str] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=list)
    message: str = ""


# ══════════════════════════════════════════════════════════════════════
# Common
# ══════════════════════════════════════════════════════════════════════

class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
    error_type: str = "unknown"


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    database: str = "unknown"
    redis: str = "unknown"
    timestamp: datetime = Field(default_factory=datetime.now)
