"""Portfolio State Tracking.

Manages portfolio positions, cash, and P&L tracking during backtests.
Extracted from Vibe-Trading's position models and portfolio tracking.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Position:
    """An open position in a single instrument.

    Attributes:
        symbol: Instrument identifier.
        direction: 1 for long, -1 for short.
        entry_price: Execution price at entry.
        entry_time: Timestamp when position was opened.
        size: Number of shares / coins / contracts.
        leverage: Effective leverage (1 for spot/stocks).
        commission: Commission paid at entry.
        stop_loss: Optional stop-loss price level.
        take_profit: Optional take-profit price level.
    """

    symbol: str
    direction: int
    entry_price: float
    entry_time: pd.Timestamp
    size: float
    leverage: float = 1.0
    commission: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


@dataclass(frozen=True)
class TradeRecord:
    """A completed round-trip trade.

    Attributes:
        symbol: Instrument identifier.
        direction: 1 for long, -1 for short.
        entry_price: Entry execution price.
        exit_price: Exit execution price.
        entry_time: Entry timestamp.
        exit_time: Exit timestamp.
        size: Number of shares / coins traded.
        pnl: Realised profit/loss in cash terms.
        pnl_pct: Realised P&L as percentage of entry value.
        exit_reason: Why closed (signal / stop_loss / end_of_backtest).
        commission: Total commission (entry + exit).
        holding_bars: Number of bars held.
    """

    symbol: str
    direction: int
    entry_price: float
    exit_price: float
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    size: float
    pnl: float
    pnl_pct: float
    exit_reason: str
    commission: float
    holding_bars: int


class Portfolio:
    """Portfolio state manager for backtesting.

    Tracks positions, cash, and equity throughout a backtest.
    Supports multiple positions, commission tracking, and P&L calculation.
    """

    def __init__(
        self,
        initial_capital: float = 1_000_000.0,
        max_positions: int = 10,
    ) -> None:
        self.initial_capital = initial_capital
        self.max_positions = max_positions
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self._current_prices: Dict[str, float] = {}
        self._bar_count = 0
        self._entry_bar: Dict[str, int] = {}

    @property
    def equity(self) -> float:
        """Total portfolio equity (cash + position market values).

        For a long position the market value is +size × current_price.
        For a short position the liability is  −size × current_price.
        """
        total = self.cash
        for symbol, pos in self.positions.items():
            current_price = self._current_prices.get(symbol, pos.entry_price)
            total += pos.direction * pos.size * current_price
        return total

    @property
    def unrealized_pnl(self) -> float:
        """Total unrealized P&L across all positions."""
        total = 0.0
        for symbol, pos in self.positions.items():
            current_price = self._current_prices.get(symbol, pos.entry_price)
            total += self._calc_unrealized_pnl(pos, current_price)
        return total

    @property
    def position_count(self) -> int:
        """Number of open positions."""
        return len(self.positions)

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get the current position for a symbol."""
        return self.positions.get(symbol)

    def can_open_position(self, price: float, size: float, commission: float, direction: int = 1) -> bool:
        """Check if a new position can be opened.

        Args:
            price: Entry price.
            size: Position size.
            commission: Commission for the trade.
            direction: 1 for long, -1 for short.

        Returns:
            True if the position can be opened.
        """
        if len(self.positions) >= self.max_positions:
            return False
        if direction == 1:
            # Long: need cash to buy the shares
            required = abs(size * price) + commission
            if required > self.cash:
                return False
        else:
            # Short: sale proceeds increase cash; only commission costs cash
            if commission > self.cash:
                return False
        return True

    def open_position(
        self,
        symbol: str,
        direction: int,
        size: float,
        price: float,
        timestamp: pd.Timestamp,
        commission: float = 0.0,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Optional[TradeRecord]:
        """Open a new position.

        Args:
            symbol: Instrument identifier.
            direction: 1 for long, -1 for short.
            size: Position size in units.
            price: Entry price.
            timestamp: Entry timestamp.
            commission: Commission for opening.
            stop_loss: Optional stop-loss price level.
            take_profit: Optional take-profit price level.

        Returns:
            TradeRecord for the opening (or None if failed).
        """
        if symbol in self.positions:
            logger.warning("Position already exists for %s, closing first", symbol)
            self.close_position(symbol, price, timestamp, "replacement")

        cost = abs(size * price) + commission
        if cost > self.cash and direction == 1:
            # Reduce size to fit available capital (long only)
            available = self.cash - commission
            if available <= 0:
                return None
            size = available / price
            cost = abs(size * price) + commission

        if direction == 1:
            self.cash -= cost
        else:
            # Short: receive sale proceeds (abs(size*price)) minus commission
            self.cash += abs(size * price) - commission

        pos = Position(
            symbol=symbol,
            direction=direction,
            entry_price=price,
            entry_time=timestamp,
            size=size,
            commission=commission,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
        self.positions[symbol] = pos
        self._entry_bar[symbol] = self._bar_count
        return TradeRecord(
            symbol=symbol,
            direction=direction,
            entry_price=price,
            exit_price=price,
            entry_time=timestamp,
            exit_time=timestamp,
            size=size,
            pnl=-commission,
            pnl_pct=-commission / (abs(size * price) + 1e-10) * 100.0,
            exit_reason="open",
            commission=commission,
            holding_bars=0,
        )

    def close_position(
        self,
        symbol: str,
        price: float,
        timestamp: pd.Timestamp,
        reason: str,
    ) -> Optional[TradeRecord]:
        """Close an existing position.

        Args:
            symbol: Instrument identifier.
            price: Exit price.
            timestamp: Exit timestamp.
            reason: Reason for closing.

        Returns:
            TradeRecord for the closed position, or None if no position exists.
        """
        pos = self.positions.pop(symbol, None)
        if pos is None:
            return None

        pnl = self._calc_unrealized_pnl(pos, price)
        entry_value = abs(pos.size * pos.entry_price)
        pnl_pct = pnl / entry_value * 100.0 if entry_value > 0 else 0.0

        # Return capital + P&L
        if pos.direction == 1:
            # Long: sell shares → cash increases by sale proceeds
            self.cash += entry_value + pnl
        else:
            # Short: buy back shares → cash decreases by cost to close
            self.cash -= abs(pos.size * price)

        holding_bars = self._bar_count - self._entry_bar.get(symbol, self._bar_count)

        return TradeRecord(
            symbol=symbol,
            direction=pos.direction,
            entry_price=pos.entry_price,
            exit_price=price,
            entry_time=pos.entry_time,
            exit_time=timestamp,
            size=pos.size,
            pnl=pnl,
            pnl_pct=pnl_pct,
            exit_reason=reason,
            commission=pos.commission,
            holding_bars=holding_bars,
        )

    def _apply_commission(self, symbol: str, commission: float) -> None:
        """Apply additional commission to a trade (for exit commission)."""
        self.cash -= commission

    def mark_to_market(self, price_row: pd.Series) -> None:
        """Update current prices for all held positions.

        Args:
            price_row: Series of current prices indexed by symbol.
        """
        self._bar_count += 1
        for symbol in self.positions:
            if symbol in price_row.index:
                self._current_prices[symbol] = price_row[symbol]

    @staticmethod
    def _calc_unrealized_pnl(pos: Position, current_price: float) -> float:
        """Calculate unrealized P&L for a position."""
        return pos.direction * pos.size * (current_price - pos.entry_price)
