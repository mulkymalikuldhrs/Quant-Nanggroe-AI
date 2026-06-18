"""Shadow Account — Virtual trading account with P&L tracking.

Simulates a trading account for strategy validation before live deployment.
Tracks positions, P&L, and computes performance metrics.

Ported from Vibe-Trading/agent/src/shadow_account/models.py
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class PositionSide(str, Enum):
    """Position side."""

    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


@dataclass
class Position:
    """A single position in the shadow account."""

    symbol: str
    side: PositionSide
    quantity: float
    entry_price: float
    entry_time: str = ""
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def market_value(self, current_price: float) -> float:
        """Calculate current market value of the position."""
        if self.side == PositionSide.LONG:
            return self.quantity * current_price
        else:
            return -self.quantity * current_price

    def unrealized_pnl(self, current_price: float) -> float:
        """Calculate unrealized P&L."""
        if self.side == PositionSide.LONG:
            return self.quantity * (current_price - self.entry_price)
        else:
            return self.quantity * (self.entry_price - current_price)


@dataclass
class TradeRecord:
    """A completed trade record."""

    symbol: str
    side: PositionSide
    quantity: float
    entry_price: float
    exit_price: float
    entry_time: str
    exit_time: str
    realized_pnl: float
    fees: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Performance metrics for the shadow account."""

    total_return: float = 0.0
    total_return_pct: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_trade_return: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_holding_time: float = 0.0


class ShadowAccount:
    """Shadow Account — Virtual trading account.

    Simulates a trading account for strategy validation:
    - Virtual trading with paper money
    - P&L tracking (realized and unrealized)
    - Position management
    - Performance metrics calculation

    Ported from Vibe-Trading/agent/src/shadow_account/
    """

    def __init__(
        self,
        initial_capital: float = 100_000.0,
        fee_rate: float = 0.001,
        slippage_rate: float = 0.0005,
    ) -> None:
        """Initialize shadow account.

        Args:
            initial_capital: Starting capital.
            fee_rate: Trading fee rate (0.001 = 0.1%).
            slippage_rate: Slippage rate.
        """
        self._initial_capital = initial_capital
        self._cash = initial_capital
        self._fee_rate = fee_rate
        self._slippage_rate = slippage_rate
        self._positions: Dict[str, Position] = {}
        self._trades: List[TradeRecord] = []
        self._equity_history: List[Tuple[str, float]] = []
        self._realized_pnl: float = 0.0

    @property
    def cash(self) -> float:
        """Current cash balance."""
        return self._cash

    @property
    def positions(self) -> Dict[str, Position]:
        """Open positions."""
        return self._positions

    @property
    def trades(self) -> List[TradeRecord]:
        """Completed trade records."""
        return self._trades

    @property
    def realized_pnl(self) -> float:
        """Total realized P&L."""
        return self._realized_pnl

    def open_position(
        self,
        symbol: str,
        side: PositionSide,
        quantity: float,
        price: float,
        timestamp: str = "",
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Position:
        """Open a new position.

        Args:
            symbol: Trading symbol.
            side: LONG or SHORT.
            quantity: Number of shares/contracts.
            price: Entry price.
            timestamp: Entry timestamp.
            stop_loss: Stop-loss price.
            take_profit: Take-profit price.
            metadata: Additional metadata.

        Returns:
            Position object.

        Raises:
            ValueError: If insufficient capital or position already exists.
        """
        if symbol in self._positions:
            raise ValueError(f"Position already exists for {symbol}")

        # Apply slippage
        if side == PositionSide.LONG:
            fill_price = price * (1 + self._slippage_rate)
        else:
            fill_price = price * (1 - self._slippage_rate)

        # Calculate cost
        cost = quantity * fill_price
        fee = cost * self._fee_rate

        if cost + fee > self._cash:
            raise ValueError(f"Insufficient capital: need {cost + fee:.2f}, have {self._cash:.2f}")

        self._cash -= cost + fee

        position = Position(
            symbol=symbol,
            side=side,
            quantity=quantity,
            entry_price=fill_price,
            entry_time=timestamp or datetime.now().isoformat(),
            stop_loss=stop_loss,
            take_profit=take_profit,
            metadata=metadata or {},
        )
        self._positions[symbol] = position

        return position

    def close_position(
        self,
        symbol: str,
        price: float,
        timestamp: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TradeRecord:
        """Close an existing position.

        Args:
            symbol: Symbol to close.
            price: Exit price.
            timestamp: Exit timestamp.
            metadata: Additional metadata.

        Returns:
            TradeRecord with realized P&L.

        Raises:
            ValueError: If no position exists for the symbol.
        """
        if symbol not in self._positions:
            raise ValueError(f"No position for {symbol}")

        position = self._positions.pop(symbol)

        # Apply slippage
        if position.side == PositionSide.LONG:
            fill_price = price * (1 - self._slippage_rate)
        else:
            fill_price = price * (1 + self._slippage_rate)

        # Calculate proceeds
        proceeds = position.quantity * fill_price
        fee = proceeds * self._fee_rate

        self._cash += proceeds - fee

        # Calculate realized P&L
        realized_pnl = position.unrealized_pnl(fill_price) - fee
        self._realized_pnl += realized_pnl

        trade = TradeRecord(
            symbol=symbol,
            side=position.side,
            quantity=position.quantity,
            entry_price=position.entry_price,
            exit_price=fill_price,
            entry_time=position.entry_time,
            exit_time=timestamp or datetime.now().isoformat(),
            realized_pnl=realized_pnl,
            fees=fee,
            metadata={**(position.metadata), **(metadata or {})},
        )
        self._trades.append(trade)

        return trade

    def equity(self, prices: Optional[Dict[str, float]] = None) -> float:
        """Calculate total equity (cash + positions).

        Args:
            prices: Dict mapping symbol -> current price.

        Returns:
            Total equity value.
        """
        total = self._cash
        if prices:
            for symbol, position in self._positions.items():
                if symbol in prices:
                    total += position.quantity * prices[symbol]
                else:
                    total += position.quantity * position.entry_price
        return total

    def unrealized_pnl(self, prices: Optional[Dict[str, float]] = None) -> float:
        """Calculate total unrealized P&L."""
        total = 0.0
        if prices:
            for symbol, position in self._positions.items():
                if symbol in prices:
                    total += position.unrealized_pnl(prices[symbol])
        return total

    def record_equity(self, timestamp: str, prices: Optional[Dict[str, float]] = None) -> None:
        """Record equity at a point in time."""
        self._equity_history.append((timestamp, self.equity(prices)))

    def compute_metrics(self) -> PerformanceMetrics:
        """Compute comprehensive performance metrics.

        Returns:
            PerformanceMetrics with all calculated metrics.
        """
        if not self._trades:
            return PerformanceMetrics()

        # Total return
        total_pnl = self._realized_pnl
        total_return_pct = (total_pnl / self._initial_capital) * 100

        # Win/loss
        winning = [t for t in self._trades if t.realized_pnl > 0]
        losing = [t for t in self._trades if t.realized_pnl <= 0]
        total_trades = len(self._trades)

        win_rate = len(winning) / total_trades if total_trades > 0 else 0

        # Profit factor
        gross_profit = sum(t.realized_pnl for t in winning) if winning else 0
        gross_loss = abs(sum(t.realized_pnl for t in losing)) if losing else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        # Average trade return
        avg_trade = total_pnl / total_trades if total_trades > 0 else 0

        # Max drawdown from equity curve
        max_dd = 0.0
        max_dd_pct = 0.0
        if self._equity_history:
            equity_values = [e[1] for e in self._equity_history]
            peak = equity_values[0]
            for eq in equity_values:
                if eq > peak:
                    peak = eq
                dd = peak - eq
                dd_pct = dd / peak if peak > 0 else 0
                if dd > max_dd:
                    max_dd = dd
                if dd_pct > max_dd_pct:
                    max_dd_pct = dd_pct

        # Sharpe ratio approximation
        sharpe = 0.0
        if self._equity_history and len(self._equity_history) > 2:
            returns = np.diff([e[1] for e in self._equity_history]) / np.array(
                [e[1] for e in self._equity_history[:-1]]
            )
            returns = returns[np.isfinite(returns)]
            if len(returns) > 0 and np.std(returns) > 0:
                sharpe = float(np.mean(returns) / np.std(returns) * np.sqrt(252))

        return PerformanceMetrics(
            total_return=total_pnl,
            total_return_pct=total_return_pct,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            max_drawdown_pct=max_dd_pct,
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_trade_return=avg_trade,
            total_trades=total_trades,
            winning_trades=len(winning),
            losing_trades=len(losing),
        )

    def reset(self) -> None:
        """Reset the account to initial state."""
        self._cash = self._initial_capital
        self._positions.clear()
        self._trades.clear()
        self._equity_history.clear()
        self._realized_pnl = 0.0
