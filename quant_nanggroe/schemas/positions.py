"""Position types for Quant Nanggroe AI.

Defines position, portfolio, and PnL tracking structures.
Positions are tracked in real-time and used by the risk engine.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class PositionSide(str, Enum):
    """Position direction."""
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


class Position(BaseModel):
    """
    A single trading position with full tracking.

    Tracks entry, current state, PnL, and risk metrics.
    """
    symbol: str
    side: PositionSide
    quantity: float = Field(..., gt=0)
    entry_price: float = Field(..., gt=0)
    current_price: float = Field(..., gt=0)
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    cost_basis: float = Field(..., gt=0)
    market_value: float = 0.0
    entry_time: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    stop_loss: Optional[float] = Field(None, gt=0)
    take_profit: Optional[float] = Field(None, gt=0)
    trailing_stop: Optional[float] = None
    max_drawdown: float = 0.0
    max_price: float = 0.0
    min_price: float = Field(default=float("inf"))
    broker_id: Optional[str] = None
    strategy_name: Optional[str] = None
    agent_name: Optional[str] = None
    metadata: Dict = Field(default_factory=dict)

    model_config = {"from_attributes": True}

    def update_price(self, price: float) -> None:
        """Update current price and recalculate PnL."""
        self.current_price = price
        self.market_value = self.quantity * price
        if self.side == PositionSide.LONG:
            self.unrealized_pnl = (price - self.entry_price) * self.quantity
        else:
            self.unrealized_pnl = (self.entry_price - price) * self.quantity
        self.unrealized_pnl_pct = (self.unrealized_pnl / self.cost_basis) * 100
        self.max_price = max(self.max_price, price)
        self.min_price = min(self.min_price, price)
        if self.max_price > 0:
            self.max_drawdown = max(
                self.max_drawdown,
                (self.max_price - price) / self.max_price * 100,
            )
        self.last_updated = datetime.now()


class Portfolio(BaseModel):
    """
    Portfolio state with all positions and aggregate metrics.

    The portfolio is the single source of truth for position state,
    PnL, and risk calculations across all agents.
    """
    id: Optional[str] = None
    name: str = "default"
    currency: str = "USD"
    initial_capital: float = Field(..., gt=0)
    cash: float = Field(..., ge=0)
    positions: Dict[str, Position] = Field(default_factory=dict)
    total_value: float = 0.0
    total_unrealized_pnl: float = 0.0
    total_realized_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    daily_pnl: float = 0.0
    weekly_pnl: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: Optional[float] = None
    win_rate: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = {"from_attributes": True}

    @property
    def position_value(self) -> float:
        """Total value of all open positions."""
        return sum(p.market_value for p in self.positions.values())

    @property
    def is_invested(self) -> bool:
        """Whether the portfolio has any open positions."""
        return len(self.positions) > 0

    def recalculate(self) -> None:
        """Recalculate all derived portfolio metrics."""
        self.total_unrealized_pnl = sum(
            p.unrealized_pnl for p in self.positions.values()
        )
        position_value = self.position_value
        self.total_value = self.cash + position_value
        self.total_pnl_pct = (
            ((self.total_value - self.initial_capital) / self.initial_capital) * 100
            if self.initial_capital > 0
            else 0.0
        )
        self.updated_at = datetime.now()
