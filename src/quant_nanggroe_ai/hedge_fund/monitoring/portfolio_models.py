"""
Portfolio Data Models for AI Quant Hedge Fund
Provides Position, Trade, and Portfolio classes for tracking trading activity
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import pandas as pd
import numpy as np
import uuid


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class PositionStatus(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PENDING = "PENDING"


class TradeStatus(Enum):
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


@dataclass
class Position:
    """
    Represents an open trading position.
    """
    ticket: int
    symbol: str
    side: OrderSide
    volume: float
    open_price: float
    open_time: datetime
    sl: Optional[float] = None
    tp: Optional[float] = None
    current_price: Optional[float] = None
    commission: float = 0.0
    swap: float = 0.0
    magic: int = 9001
    comment: str = ""
    order_type: OrderType = OrderType.MARKET
    status: PositionStatus = PositionStatus.OPEN
    hedging_volume: float = 0.0
    
    @property
    def is_long(self) -> bool:
        return self.side == OrderSide.BUY
    
    @property
    def is_short(self) -> bool:
        return self.side == OrderSide.SELL
    
    @property
    def current_value(self) -> float:
        if self.current_price is None:
            return self.volume * self.open_price
        return self.volume * self.current_price
    
    @property
    def cost_basis(self) -> float:
        return self.volume * self.open_price
    
    @property
    def pnl(self) -> float:
        if self.current_price is None:
            return 0.0
        if self.side == OrderSide.BUY:
            return (self.current_price - self.open_price) * self.volume
        else:
            return (self.open_price - self.current_price) * self.volume
    
    @property
    def pnl_pct(self) -> float:
        if self.open_price == 0:
            return 0.0
        return (self.pnl / self.cost_basis) * 100
    
    @property
    def risk_reward_ratio(self) -> float:
        if self.sl is None or self.tp is None or self.sl == self.open_price:
            return 0.0
        if self.side == OrderSide.BUY:
            potential_profit = self.tp - self.open_price
            potential_loss = self.open_price - self.sl
        else:
            potential_profit = self.open_price - self.tp
            potential_loss = self.sl - self.open_price
        if potential_loss == 0:
            return 0.0
        return potential_profit / potential_loss
    
    @property
    def distance_to_sl(self) -> float:
        if self.sl is None or self.current_price is None:
            return 0.0
        if self.side == OrderSide.BUY:
            return self.current_price - self.sl
        else:
            return self.sl - self.current_price
    
    @property
    def distance_to_tp(self) -> float:
        if self.tp is None or self.current_price is None:
            return 0.0
        if self.side == OrderSide.BUY:
            return self.tp - self.current_price
        else:
            return self.current_price - self.tp
    
    @property
    def is_profitable(self) -> bool:
        return self.pnl > 0
    
    @property
    def is_at_sl(self) -> bool:
        if self.sl is None or self.current_price is None:
            return False
        if self.side == OrderSide.BUY:
            return self.current_price <= self.sl
        else:
            return self.current_price >= self.sl
    
    @property
    def is_at_tp(self) -> bool:
        if self.tp is None or self.current_price is None:
            return False
        if self.side == OrderSide.BUY:
            return self.current_price >= self.tp
        else:
            return self.current_price <= self.tp
    
    def to_dict(self) -> Dict:
        return {
            "ticket": self.ticket,
            "symbol": self.symbol,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "volume": self.volume,
            "open_price": self.open_price,
            "open_time": self.open_time.isoformat(),
            "current_price": self.current_price,
            "sl": self.sl,
            "tp": self.tp,
            "pnl": self.pnl,
            "pnl_pct": self.pnl_pct,
            "commission": self.commission,
            "swap": self.swap,
            "magic": self.magic,
            "comment": self.comment,
            "status": self.status.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Position":
        return cls(
            ticket=data["ticket"],
            symbol=data["symbol"],
            side=OrderSide(data["side"]),
            volume=data["volume"],
            open_price=data["open_price"],
            open_time=datetime.fromisoformat(data["open_time"]),
            sl=data.get("sl"),
            tp=data.get("tp"),
            current_price=data.get("current_price"),
            commission=data.get("commission", 0.0),
            swap=data.get("swap", 0.0),
            magic=data.get("magic", 9001),
            comment=data.get("comment", ""),
            order_type=OrderType(data.get("order_type", "MARKET")),
            status=PositionStatus(data.get("status", "OPEN")),
            hedging_volume=data.get("hedging_volume", 0.0)
        )


@dataclass
class Trade:
    """
    Represents a completed trade record.
    """
    ticket: int
    symbol: str
    side: OrderSide
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    volume: float = 1.0
    commission: float = 0.0
    swap: float = 0.0
    fee: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    duration_seconds: float = 0.0
    magic: int = 9001
    comment: str = ""
    entry_reason: str = ""
    exit_reason: str = ""
    max_favorable: float = 0.0
    max_adverse: float = 0.0
    order_type: OrderType = OrderType.MARKET
    status: TradeStatus = TradeStatus.FILLED
    
    def __post_init__(self):
        if self.entry_price != 0:
            self.pnl_pct = ((self.exit_price - self.entry_price) / self.entry_price) * 100
            if self.side == OrderSide.SELL:
                self.pnl_pct = -self.pnl_pct
        self.duration_seconds = (self.exit_time - self.entry_time).total_seconds()
    
    @property
    def is_win(self) -> bool:
        return self.pnl > 0
    
    @property
    def is_loss(self) -> bool:
        return self.pnl < 0
    
    @property
    def is_breakeven(self) -> bool:
        return self.pnl == 0
    
    @property
    def duration_hours(self) -> float:
        return self.duration_seconds / 3600
    
    @property
    def duration_days(self) -> float:
        return self.duration_seconds / 86400
    
    @property
    def roi(self) -> float:
        return self.pnl_pct
    
    @property
    def risk_reward_actual(self) -> float:
        if self.max_adverse <= 0:
            return 0.0
        return abs(self.max_favorable / self.max_adverse) if self.max_adverse != 0 else 0.0
    
    @classmethod
    def from_position(
        cls,
        position: Position,
        exit_price: float,
        exit_time: datetime,
        exit_reason: str = ""
    ) -> "Trade":
        if position.side == OrderSide.BUY:
            pnl = (exit_price - position.open_price) * position.volume
        else:
            pnl = (position.open_price - exit_price) * position.volume
        
        total_cost = position.commission + position.swap + cls._estimate_fee(exit_price * position.volume)
        
        return cls(
            ticket=position.ticket,
            symbol=position.symbol,
            side=position.side,
            entry_price=position.open_price,
            exit_price=exit_price,
            entry_time=position.open_time,
            exit_time=exit_time,
            volume=position.volume,
            commission=position.commission,
            swap=position.swap,
            fee=total_cost - position.commission - position.swap,
            pnl=pnl - total_cost,
            magic=position.magic,
            comment=position.comment,
            exit_reason=exit_reason,
            order_type=position.order_type
        )
    
    @staticmethod
    def _estimate_fee(volume_value: float, fee_rate: float = 0.0001) -> float:
        """Estimate trading fee."""
        return volume_value * fee_rate
    
    def to_dict(self) -> Dict:
        return {
            "ticket": self.ticket,
            "symbol": self.symbol,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "entry_time": self.entry_time.isoformat(),
            "exit_time": self.exit_time.isoformat(),
            "volume": self.volume,
            "commission": self.commission,
            "swap": self.swap,
            "fee": self.fee,
            "pnl": self.pnl,
            "pnl_pct": self.pnl_pct,
            "duration_seconds": self.duration_seconds,
            "duration_hours": self.duration_hours,
            "magic": self.magic,
            "comment": self.comment,
            "entry_reason": self.entry_reason,
            "exit_reason": self.exit_reason,
            "max_favorable": self.max_favorable,
            "max_adverse": self.max_adverse,
            "status": self.status.value,
            "is_win": self.is_win
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Trade":
        return cls(
            ticket=data["ticket"],
            symbol=data["symbol"],
            side=OrderSide(data["side"]),
            entry_price=data["entry_price"],
            exit_price=data["exit_price"],
            entry_time=datetime.fromisoformat(data["entry_time"]),
            exit_time=datetime.fromisoformat(data["exit_time"]),
            volume=data.get("volume", 1.0),
            commission=data.get("commission", 0.0),
            swap=data.get("swap", 0.0),
            fee=data.get("fee", 0.0),
            pnl=data.get("pnl", 0.0),
            pnl_pct=data.get("pnl_pct", 0.0),
            duration_seconds=data.get("duration_seconds", 0.0),
            magic=data.get("magic", 9001),
            comment=data.get("comment", ""),
            entry_reason=data.get("entry_reason", ""),
            exit_reason=data.get("exit_reason", ""),
            max_favorable=data.get("max_favorable", 0.0),
            max_adverse=data.get("max_adverse", 0.0),
            order_type=OrderType(data.get("order_type", "MARKET")),
            status=TradeStatus(data.get("status", "FILLED"))
        )


@dataclass
class Order:
    """
    Represents a pending or submitted order.
    """
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    volume: float
    price: float
    sl: Optional[float] = None
    tp: Optional[float] = None
    created_time: datetime = field(default_factory=datetime.now)
    submitted_time: Optional[datetime] = None
    filled_time: Optional[datetime] = None
    cancelled_time: Optional[datetime] = None
    magic: int = 9001
    comment: str = ""
    deviation: int = 10
    expiration: Optional[datetime] = None
    status: str = "CREATED"
    filled_price: Optional[float] = None
    filled_volume: float = 0.0
    
    @property
    def is_pending(self) -> bool:
        return self.status in ["CREATED", "SUBMITTED", "PARTIAL"]
    
    @property
    def is_filled(self) -> bool:
        return self.status == "FILLED"
    
    @property
    def is_cancelled(self) -> bool:
        return self.status == "CANCELLED"
    
    @property
    def is_active(self) -> bool:
        return self.status in ["CREATED", "SUBMITTED"]
    
    def to_dict(self) -> Dict:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "volume": self.volume,
            "price": self.price,
            "sl": self.sl,
            "tp": self.tp,
            "created_time": self.created_time.isoformat(),
            "submitted_time": self.submitted_time.isoformat() if self.submitted_time else None,
            "filled_time": self.filled_time.isoformat() if self.filled_time else None,
            "cancelled_time": self.cancelled_time.isoformat() if self.cancelled_time else None,
            "magic": self.magic,
            "comment": self.comment,
            "status": self.status,
            "filled_price": self.filled_price,
            "filled_volume": self.filled_volume
        }


@dataclass
class Portfolio:
    """
    Portfolio state containing all positions, trades, and account info.
    """
    account_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    account_balance: float = 100000.0
    account_equity: float = 100000.0
    account_currency: str = "USD"
    
    positions: Dict[int, Position] = field(default_factory=dict)
    trades: List[Trade] = field(default_factory=list)
    orders: Dict[str, Order] = field(default_factory=dict)
    
    daily_pnl: float = 0.0
    daily_pnl_pct: float = 0.0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    
    margin_used: float = 0.0
    margin_free: float = 100000.0
    margin_level: float = 0.0
    margin_call_level: float = 100.0
    stop_out_level: float = 50.0
    
    commission_paid: float = 0.0
    swap_paid: float = 0.0
    fees_paid: float = 0.0
    
    win_count: int = 0
    loss_count: int = 0
    breakeven_count: int = 0
    
    last_update: datetime = field(default_factory=datetime.now)
    last_equity_update: datetime = field(default_factory=datetime.now)
    
    starting_balance: float = 100000.0
    
    @property
    def open_positions_count(self) -> int:
        return len(self.positions)
    
    @property
    def closed_trades_count(self) -> int:
        return len(self.trades)
    
    @property
    def pending_orders_count(self) -> int:
        return len([o for o in self.orders.values() if o.is_active])
    
    @property
    def long_exposure(self) -> float:
        return sum(p.current_value for p in self.positions.values() if p.is_long)
    
    @property
    def short_exposure(self) -> float:
        return sum(p.current_value for p in self.positions.values() if p.is_short)
    
    @property
    def net_exposure(self) -> float:
        return self.long_exposure - self.short_exposure
    
    @property
    def gross_exposure(self) -> float:
        return self.long_exposure + self.short_exposure
    
    @property
    def exposure_ratio(self) -> float:
        if self.account_equity == 0:
            return 0.0
        return self.gross_exposure / self.account_equity
    
    @property
    def leverage_used(self) -> float:
        if self.margin_used == 0:
            return 0.0
        return self.gross_exposure / self.margin_used if self.margin_used > 0 else 0.0
    
    @property
    def win_rate(self) -> float:
        total = self.win_count + self.loss_count
        if total == 0:
            return 0.0
        return self.win_count / total * 100
    
    @property
    def profit_factor(self) -> float:
        wins = [t.pnl for t in self.trades if t.is_win]
        losses = [abs(t.pnl) for t in self.trades if t.is_loss]
        wins_sum = sum(wins) if wins else 0
        losses_sum = sum(losses) if losses else 0
        if losses_sum == 0:
            return float('inf') if wins_sum > 0 else 0.0
        return wins_sum / losses_sum
    
    @property
    def expectancy(self) -> float:
        if not self.trades:
            return 0.0
        win_rate = self.win_rate / 100
        avg_win = np.mean([t.pnl for t in self.trades if t.is_win]) if self.win_count > 0 else 0
        avg_loss = np.mean([abs(t.pnl) for t in self.trades if t.is_loss]) if self.loss_count > 0 else 0
        return (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
    
    @property
    def is_margin_call(self) -> bool:
        return self.margin_level < self.margin_call_level
    
    @property
    def is_stop_out(self) -> bool:
        return self.margin_level < self.stop_out_level
    
    def calculate_statistics(
        self,
        period_start: datetime = None,
        period_end: datetime = None
    ) -> Dict:
        """
        Calculate portfolio statistics.
        
        Args:
            period_start: Start of period for statistics
            period_end: End of period for statistics
            
        Returns:
            Dict with statistics
        """
        trades_filtered = self.trades
        
        if period_start:
            trades_filtered = [t for t in trades_filtered if t.exit_time >= period_start]
        if period_end:
            trades_filtered = [t for t in trades_filtered if t.exit_time <= period_end]
        
        if not trades_filtered:
            return {
                "total_trades": 0,
                "win_rate": 0,
                "profit_factor": 0,
                "avg_win": 0,
                "avg_loss": 0,
                "max_win": 0,
                "max_loss": 0,
                "avg_trade_duration_hours": 0,
                "win_streak": 0,
                "loss_streak": 0,
                "consecutive_wins": 0,
                "consecutive_losses": 0
            }
        
        pnl_values = [t.pnl for t in trades_filtered]
        wins = [p for p in pnl_values if p > 0]
        losses = [p for p in pnl_values if p < 0]
        
        win_streak = self._calculate_streak([t.is_win for t in trades_filtered], True)
        loss_streak = self._calculate_streak([t.is_win for t in trades_filtered], False)
        
        return {
            "total_trades": len(trades_filtered),
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "expectancy": self.expectancy,
            "avg_win": np.mean(wins) if wins else 0,
            "avg_loss": np.mean(losses) if losses else 0,
            "max_win": max(wins) if wins else 0,
            "max_loss": min(losses) if losses else 0,
            "std_dev": np.std(pnl_values) if len(pnl_values) > 1 else 0,
            "avg_trade_duration_hours": np.mean([t.duration_hours for t in trades_filtered]) if trades_filtered else 0,
            "longest_trade_hours": max([t.duration_hours for t in trades_filtered]) if trades_filtered else 0,
            "shortest_trade_hours": min([t.duration_hours for t in trades_filtered]) if trades_filtered else 0,
            "total_commission": sum(t.commission for t in trades_filtered),
            "total_swap": sum(t.swap for t in trades_filtered),
            "net_pnl": sum(pnl_values),
            "win_streak": win_streak,
            "loss_streak": loss_streak,
            "consecutive_wins": self.win_count,
            "consecutive_losses": self.loss_count
        }
    
    def _calculate_streak(
        self,
        results: List[bool],
        is_win: bool
    ) -> int:
        """Calculate longest streak of wins or losses."""
        if not results:
            return 0
        max_streak = current_streak = 0
        for result in results:
            if result == is_win:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
        return max_streak
    
    def get_equity_curve(self, interval: str = "1h") -> pd.DataFrame:
        """
        Generate equity curve data.
        
        Args:
            interval: Time interval for resampling
            
        Returns:
            DataFrame with equity values
        """
        if not self.trades:
            return pd.DataFrame()
        
        data_points = []
        base_equity = self.starting_balance
        
        trades_sorted = sorted(self.trades, key=lambda t: t.exit_time)
        
        for trade in trades_sorted:
            base_equity += trade.pnl
            data_points.append({
                "time": trade.exit_time,
                "equity": base_equity,
                "pnl": trade.pnl
            })
        
        df = pd.DataFrame(data_points)
        df.set_index("time", inplace=True)
        
        if interval:
            df = df.resample(interval).last().fillna(method="ffill")
        
        return df
    
    def get_positions_by_symbol(self, symbol: str) -> List[Position]:
        """Get all positions for a symbol."""
        return [p for p in self.positions.values() if p.symbol == symbol]
    
    def get_positions_by_side(self, side: OrderSide) -> List[Position]:
        """Get all positions by side."""
        return [p for p in self.positions.values() if p.side == side]
    
    def add_position(self, position: Position) -> None:
        """Add a position to the portfolio."""
        self.positions[position.ticket] = position
        self.last_update = datetime.now()
    
    def remove_position(self, ticket: int) -> Optional[Position]:
        """Remove a position from the portfolio."""
        removed = self.positions.pop(ticket, None)
        if removed:
            self.last_update = datetime.now()
        return removed
    
    def add_trade(self, trade: Trade) -> None:
        """Add a completed trade."""
        self.trades.append(trade)
        self.total_pnl += trade.pnl
        self.total_pnl_pct = (self.total_pnl / self.starting_balance) * 100
        
        if trade.is_win:
            self.win_count += 1
            self.daily_pnl += trade.pnl
        elif trade.is_loss:
            self.loss_count += 1
            self.daily_pnl += trade.pnl
        else:
            self.breakeven_count += 1
        
        self.commission_paid += trade.commission
        self.swap_paid += trade.swap
        self.fees_paid += trade.fee
        
        self.last_update = datetime.now()
    
    def add_order(self, order: Order) -> None:
        """Add a pending order."""
        self.orders[order.order_id] = order
    
    def remove_order(self, order_id: str) -> Optional[Order]:
        """Remove an order from the portfolio."""
        removed = self.orders.pop(order_id, None)
        return removed
    
    def update_from_broker(self, account_info: Dict, positions: List[Dict]) -> None:
        """
        Update portfolio from broker data.
        
        Args:
            account_info: Account information from broker
            positions: Open positions from broker
        """
        if account_info:
            self.account_balance = account_info.get("balance", self.account_balance)
            self.account_equity = account_info.get("equity", self.account_equity)
            self.margin_used = account_info.get("margin", 0)
            self.margin_free = account_info.get("margin_free", 0)
            self.margin_level = account_info.get("margin_level", 0)
            self.last_equity_update = datetime.now()
        
        for pos_data in positions:
            ticket = pos_data["ticket"]
            if ticket in self.positions:
                position = self.positions[ticket]
                position.current_price = pos_data.get("current_price", position.current_price)
                position.pnl = pos_data.get("pnl", position.pnl)
        
        self.last_update = datetime.now()
    
    def to_dict(self) -> Dict:
        """Convert portfolio to dictionary."""
        return {
            "account_id": self.account_id,
            "account_balance": self.account_balance,
            "account_equity": self.account_equity,
            "account_currency": self.account_currency,
            "positions_count": self.open_positions_count,
            "trades_count": self.closed_trades_count,
            "daily_pnl": self.daily_pnl,
            "daily_pnl_pct": self.daily_pnl_pct,
            "total_pnl": self.total_pnl,
            "total_pnl_pct": self.total_pnl_pct,
            "margin_used": self.margin_used,
            "margin_free": self.margin_free,
            "margin_level": self.margin_level,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "long_exposure": self.long_exposure,
            "short_exposure": self.short_exposure,
            "net_exposure": self.net_exposure,
            "last_update": self.last_update.isoformat()
        }
    
    def to_snapshot(self) -> Dict:
        """Get full portfolio snapshot for monitoring."""
        stats = self.calculate_statistics()
        
        return {
            "timestamp": self.last_update.isoformat(),
            "account": {
                "id": self.account_id,
                "balance": self.account_balance,
                "equity": self.account_equity,
                "currency": self.account_currency,
                "margin_used": self.margin_used,
                "margin_free": self.margin_free,
                "margin_level": self.margin_level
            },
            "positions": {
                str(ticket): pos.to_dict()
                for ticket, pos in self.positions.items()
            },
            "statistics": stats,
            "exposure": {
                "long": self.long_exposure,
                "short": self.short_exposure,
                "net": self.net_exposure,
                "gross": self.gross_exposure,
                "ratio": self.exposure_ratio
            },
            "performance": {
                "daily_pnl": self.daily_pnl,
                "total_pnl": self.total_pnl,
                "win_rate": self.win_rate,
                "profit_factor": self.profit_factor,
                "expectancy": self.expectancy
            }
        }
