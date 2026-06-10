"""Position types — open, closed, and tracked positions.

A position represents a held asset with entry/exit tracking,
unrealized and realized P&L, and risk metrics.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PositionSide(str, Enum):
    """Position direction."""

    LONG = "LONG"
    SHORT = "SHORT"


class PositionStatus(str, Enum):
    """Position lifecycle status."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"
    LIQUIDATED = "LIQUIDATED"


class Position(BaseModel):
    """A trading position with full P&L tracking.

    Tracks entry, current state, and derived metrics like
    unrealized P&L, return percentage, and holding duration.
    """

    id: str = Field(description="Unique position identifier")
    symbol: str = Field(description="Trading pair / ticker symbol")
    side: PositionSide = Field(description="LONG or SHORT")
    status: PositionStatus = Field(default=PositionStatus.OPEN)
    entry_price: float = Field(gt=0, description="Average entry price")
    current_price: float = Field(gt=0, description="Current market price")
    quantity: float = Field(gt=0, description="Position size")
    entry_time: datetime = Field(description="When the position was opened")
    exit_price: Optional[float] = Field(default=None, description="Exit price (if closed)")
    exit_time: Optional[datetime] = Field(default=None, description="When the position was closed")
    stop_loss: Optional[float] = Field(default=None, description="Stop-loss price")
    take_profit: Optional[float] = Field(default=None, description="Take-profit price")
    strategy_id: Optional[str] = Field(default=None, description="Strategy that opened this position")
    commission: float = Field(default=0.0, ge=0, description="Total commission paid")
    leverage: float = Field(default=1.0, ge=1.0, description="Leverage multiplier")
    notes: Optional[str] = Field(default=None, description="Free-form notes")

    @property
    def unrealized_pnl(self) -> float:
        """Unrealized profit and loss."""
        if self.side == PositionSide.LONG:
            return (self.current_price - self.entry_price) * self.quantity
        return (self.entry_price - self.current_price) * self.quantity

    @property
    def unrealized_pnl_pct(self) -> float:
        """Unrealized P&L as percentage of entry value."""
        entry_value = self.entry_price * self.quantity
        if entry_value == 0:
            return 0.0
        return (self.unrealized_pnl / entry_value) * 100

    @property
    def realized_pnl(self) -> Optional[float]:
        """Realized P&L (only available for closed positions)."""
        if self.status != PositionStatus.CLOSED or self.exit_price is None:
            return None
        if self.side == PositionSide.LONG:
            return (self.exit_price - self.entry_price) * self.quantity - self.commission
        return (self.entry_price - self.exit_price) * self.quantity - self.commission

    @property
    def notional_value(self) -> float:
        """Current notional value of the position."""
        return self.current_price * self.quantity * self.leverage

    @property
    def holding_duration_hours(self) -> Optional[float]:
        """Duration the position has been / was held in hours."""
        end = self.exit_time or datetime.now()
        delta = end - self.entry_time
        return delta.total_seconds() / 3600

    model_config = {"json_schema_extra": {
        "examples": [{
            "id": "pos_001",
            "symbol": "BTC/USDT",
            "side": "LONG",
            "status": "OPEN",
            "entry_price": 42000.0,
            "current_price": 42800.0,
            "quantity": 0.5,
            "entry_time": "2024-01-15T10:00:00Z",
            "stop_loss": 41000.0,
            "take_profit": 45000.0,
            "leverage": 1.0,
        }]
    }}
