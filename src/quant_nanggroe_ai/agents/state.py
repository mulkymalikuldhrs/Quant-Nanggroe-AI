"""
Agent State Schema — Shared state for the LangGraph trading graph
===================================================================
All agents communicate through this shared state.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from quant_nanggroe_ai.types import (
    MarketRegime,
    VolatilityLevel,
    LiquidityLevel,
    RiskClearance,
    DecisionAction,
    PressureState,
    MarketState,
    CandleData,
)


class AgentState(BaseModel):
    """
    Shared state schema for the LangGraph trading graph.

    This is the single source of truth that flows through all agent nodes.
    Each agent reads from and writes to this state.

    Flow: Researcher → Analyst → Strategist → Risk Manager → Trader → Portfolio Manager
    """

    # ── Input ────────────────────────────────────────────────────────
    symbol: str = ""
    timeframe: str = "1d"
    query: str = ""

    # ── Market Data ──────────────────────────────────────────────────
    market_data: list[dict[str, Any]] = Field(default_factory=list)
    candles: list[dict[str, Any]] = Field(default_factory=list)

    # ── Market State (from MarketStateEngine) ───────────────────────
    market_state: MarketState = Field(default_factory=MarketState)
    regime: MarketRegime = MarketRegime.UNKNOWN
    volatility: VolatilityLevel = VolatilityLevel.NORMAL
    liquidity: LiquidityLevel = LiquidityLevel.NORMAL

    # ── Pressure (from PressureNormalizationEngine) ─────────────────
    pressure: PressureState = Field(default_factory=PressureState)
    buy_pressure: float = 0.0
    sell_pressure: float = 0.0
    confidence: float = 0.0

    # ── Research ─────────────────────────────────────────────────────
    research_summary: str = ""
    news_items: list[dict[str, Any]] = Field(default_factory=list)
    macro_context: str = ""

    # ── Analysis ─────────────────────────────────────────────────────
    technical_analysis: dict[str, Any] = Field(default_factory=dict)
    sentiment_score: float = 0.0
    smc_signals: list[dict[str, Any]] = Field(default_factory=list)

    # ── Strategy ─────────────────────────────────────────────────────
    strategy_name: str = ""
    strategy_signal: str = ""  # BUY / SELL / HOLD
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: list[float] = Field(default_factory=list)
    position_size: float = 0.0
    risk_reward_ratio: float = 0.0

    # ── Risk ─────────────────────────────────────────────────────────
    risk_verdict: str = "VETOED"  # APPROVED / VETOED
    risk_clearance: RiskClearance = RiskClearance.BLOCKED
    risk_checkpoints: dict[str, Any] = Field(default_factory=dict)
    daily_pnl_pct: float = 0.0
    weekly_pnl_pct: float = 0.0

    # ── Decision ─────────────────────────────────────────────────────
    decision_action: DecisionAction = DecisionAction.NO_TRADE
    decision_reason: str = ""

    # ── Execution ────────────────────────────────────────────────────
    order_id: str = ""
    execution_status: str = ""  # PENDING, FILLED, REJECTED, CANCELLED
    execution_price: float = 0.0
    slippage: float = 0.0

    # ── Portfolio ────────────────────────────────────────────────────
    portfolio_decision: str = ""  # APPROVE / REJECT
    portfolio_rejection_reason: str = ""

    # ── Metadata ─────────────────────────────────────────────────────
    agent_trace: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
