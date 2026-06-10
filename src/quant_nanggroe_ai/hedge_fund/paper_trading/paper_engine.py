"""
Paper Trading System
Real-time simulation of trading without risking real capital.
Supports live data feeds, order execution simulation, and P&L tracking.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod
from collections import defaultdict
import uuid
import json

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Order types"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    STOP_LIMIT = "STOP_LIMIT"


class OrderSide(Enum):
    """Order sides"""
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    """Order statuses"""
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class PositionSide(Enum):
    """Position sides"""
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class Order:
    """Trading order"""
    order_id: str
    ticker: str
    order_type: OrderType
    side: OrderSide
    quantity: float
    price: Optional[float] = None  # For limit orders
    stop_price: Optional[float] = None  # For stop orders
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0
    filled_price: float = 0
    commission: float = 0
    created_at: datetime = field(default_factory=datetime.now)
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    notes: str = ""
    
    @property
    def remaining_quantity(self) -> float:
        return self.quantity - self.filled_quantity
    
    @property
    def is_active(self) -> bool:
        return self.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]


@dataclass
class Position:
    """Open position"""
    ticker: str
    side: PositionSide
    quantity: float
    entry_price: float
    entry_date: datetime
    entry_order_id: str
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    trailing_stop: Optional[float] = None
    unrealized_pnl: float = 0
    unrealized_pnl_pct: float = 0
    last_price: float = 0
    
    def update_market_value(self, current_price: float):
        """Update unrealized P&L"""
        self.last_price = current_price
        
        if self.side == PositionSide.LONG:
            self.unrealized_pnl = (current_price - self.entry_price) * self.quantity
            self.unrealized_pnl_pct = (current_price / self.entry_price - 1) * 100
        else:  # SHORT
            self.unrealized_pnl = (self.entry_price - current_price) * self.quantity
            self.unrealized_pnl_pct = (self.entry_price / current_price - 1) * 100
    
    @property
    def market_value(self) -> float:
        return self.quantity * self.last_price


@dataclass
class Trade:
    """Completed trade"""
    trade_id: str
    ticker: str
    side: OrderSide
    quantity: float
    entry_price: float
    entry_date: datetime
    exit_price: float
    exit_date: datetime
    pnl: float
    pnl_pct: float
    commission: float
    hold_time: timedelta
    strategy: str = ""
    notes: str = ""


@dataclass
class PortfolioSummary:
    """Portfolio summary snapshot"""
    timestamp: datetime
    total_value: float
    cash_balance: float
    market_value: float
    unrealized_pnl: float
    realized_pnl: float
    total_pnl: float
    day_change: float
    day_change_pct: float
    open_positions: int
    open_orders: int


class DataFeed(ABC):
    """Abstract data feed for paper trading"""
    
    @abstractmethod
    def get_latest_price(self, ticker: str) -> Optional[float]:
        pass
    
    @abstractmethod
    def subscribe(self, tickers: List[str], callback: Callable):
        pass


class PaperTradingEngine:
    """
    Paper Trading Engine for simulation.
    
    Features:
    - Order management (market, limit, stop, take profit)
    - Position tracking
    - Real-time P&L calculation
    - Trade logging
    - Performance analytics
    - Strategy framework
    """
    
    def __init__(
        self,
        initial_capital: float = 100000,
        fee_rate: float = 0.001,
        slippage: float = 0.0005,
        data_feed: DataFeed = None
    ):
        """
        Initialize paper trading engine.
        
        Args:
            initial_capital: Starting capital
            fee_rate: Trading fee as fraction
            slippage: Slippage as fraction
            data_feed: Data feed for price updates
        """
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.fee_rate = fee_rate
        self.slippage = slippage
        self.data_feed = data_feed
        
        # Trading state
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, Order] = {}
        self.trades: List[Trade] = []
        self.portfolio_history: List[PortfolioSummary] = []
        
        # Strategy registry
        self.strategies: Dict[str, Callable] = {}
        self.strategy_state: Dict[str, Any] = {}
        
        # Callbacks
        self.on_order_fill: List[Callable] = []
        self.on_position_change: List[Callable] = []
        self.on_trade: List[Callable] = []
        
        # Tracking
        self.day_open_value = initial_capital
        self.realized_pnl = 0
        
        # Start data feed if provided
        if data_feed:
            data_feed.subscribe(list(self.strategies.keys()), self._on_price_update)
    
    def register_strategy(self, name: str, strategy_func: Callable, tickers: List[str]):
        """
        Register a trading strategy.
        
        Args:
            name: Strategy name
            strategy_func: Strategy function (receives engine instance)
            tickers: List of tickers to trade
        """
        self.strategies[name] = strategy_func
        self.strategy_state[name] = {
            'tickers': tickers,
            'last_signals': {},
            'positions': {}
        }
        
        logger.info(f"Registered strategy: {name} for {tickers}")
    
    def submit_order(
        self,
        ticker: str,
        order_type: OrderType,
        side: OrderSide,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        strategy: str = ""
    ) -> Order:
        """
        Submit a trading order.
        
        Args:
            ticker: Asset ticker
            order_type: Type of order
            side: Buy or sell
            quantity: Order quantity
            limit_price: Limit price (for limit orders)
            stop_price: Stop price (for stop orders)
            strategy: Source strategy
            
        Returns:
            Order object
        """
        order = Order(
            order_id=str(uuid.uuid4())[:8],
            ticker=ticker,
            order_type=order_type,
            side=side,
            quantity=quantity,
            price=price,
            stop_price=stop_price
        )
        
        # Validate order
        if order_type == OrderType.LIMIT and price is None:
            order.status = OrderStatus.REJECTED
            order.notes = "Limit order requires price"
            return order
        
        if order_type in [OrderType.STOP_LOSS, OrderType.STOP_LIMIT] and stop_price is None:
            order.status = OrderStatus.REJECTED
            order.notes = "Stop order requires stop_price"
            return order
        
        # Check capital for buy orders
        if side == OrderSide.BUY:
            estimated_cost = quantity * (price or 0) * (1 + self.fee_rate)
            if estimated_cost > self.cash:
                order.status = OrderStatus.REJECTED
                order.notes = "Insufficient funds"
                return order
        
        self.orders[order.order_id] = order
        order.status = OrderStatus.SUBMITTED
        
        logger.info(f"Order submitted: {order.order_id} {order.side} {order.quantity} {order.ticker} @ {order.price or 'MKT'}")
        
        # Try to fill immediately if market order
        if order_type == OrderType.MARKET:
            self._fill_market_order(order)
        
        return order
    
    def _fill_market_order(self, order: Order):
        """Fill a market order"""
        # Get current price (would come from data feed in real trading)
        current_price = self._get_current_price(order.ticker)
        
        if current_price is None:
            return
        
        # Apply slippage
        if order.side == OrderSide.BUY:
            fill_price = current_price * (1 + self.slippage)
        else:
            fill_price = current_price * (1 - self.slippage)
        
        self._execute_order(order, fill_price)
    
    def _execute_order(self, order: Order, fill_price: float):
        """Execute an order at given price"""
        # Calculate fees
        notional = fill_price * order.quantity
        commission = notional * self.fee_rate
        
        order.filled_price = fill_price
        order.filled_quantity = order.quantity
        order.commission = commission
        order.status = OrderStatus.FILLED
        order.filled_at = datetime.now()
        
        # Update cash
        if order.side == OrderSide.BUY:
            self.cash -= (notional + commission)
        else:
            self.cash += (notional - commission)
        
        # Update or create position
        self._update_position(order)
        
        # Remove from active orders
        if order.order_id in self.orders:
            del self.orders[order.order_id]
        
        # Notify callbacks
        for callback in self.on_order_fill:
            try:
                callback(order)
            except Exception as e:
                logger.error(f"Order fill callback error: {e}")
        
        logger.info(f"Order filled: {order.order_id} @ {fill_price:.2f}")
    
    def _update_position(self, order: Order):
        """Update position after order fill"""
        ticker = order.ticker
        
        if ticker not in self.positions:
            # Create new position
            side = PositionSide.LONG if order.side == OrderSide.BUY else PositionSide.SHORT
            self.positions[ticker] = Position(
                ticker=ticker,
                side=side,
                quantity=order.quantity,
                entry_price=order.filled_price,
                entry_date=order.filled_at,
                entry_order_id=order.order_id,
                last_price=order.filled_price
            )
        else:
            position = self.positions[ticker]
            
            # Check if same side or opposite
            position_side = PositionSide.LONG if order.side == OrderSide.BUY else PositionSide.SHORT
            
            if position.side == position_side:
                # Add to position (average in)
                total_cost = position.entry_price * position.quantity + order.filled_price * order.quantity
                total_qty = position.quantity + order.quantity
                position.entry_price = total_cost / total_qty
                position.quantity = total_qty
            else:
                # Reduce or close position
                if order.quantity >= position.quantity:
                    # Close position
                    realized = self._calculate_realized_pnl(position, order.filled_price)
                    self.realized_pnl += realized
                    
                    # Create trade record
                    trade = self._create_trade(position, order.filled_price)
                    self.trades.append(trade)
                    
                    # Notify callbacks
                    for callback in self.on_trade:
                        try:
                            callback(trade)
                        except Exception as e:
                            logger.error(f"Trade callback error: {e}")
                    
                    del self.positions[ticker]
                else:
                    # Partial close
                    realized = self._calculate_realized_pnl(position, order.filled_price, order.quantity)
                    self.realized_pnl += realized
                    
                    position.quantity -= order.quantity
                    position.entry_price = order.filled_price  # Simplified
        
        # Notify callbacks
        for callback in self.on_position_change:
            try:
                callback(ticker, self.positions.get(ticker))
            except Exception as e:
                logger.error(f"Position change callback error: {e}")
    
    def _calculate_realized_pnl(
        self, 
        position: Position, 
        exit_price: float,
        quantity: float = None
    ) -> float:
        """Calculate realized P&L"""
        qty = quantity or position.quantity
        
        if position.side == PositionSide.LONG:
            return (exit_price - position.entry_price) * qty
        else:
            return (position.entry_price - exit_price) * qty
    
    def _create_trade(self, position: Position, exit_price: float) -> Trade:
        """Create trade record"""
        hold_time = position.entry_date - datetime.now()
        
        pnl = self._calculate_realized_pnl(position, exit_price)
        pnl_pct = (exit_price / position.entry_price - 1) * 100 if position.side == PositionSide.LONG else (position.entry_price / exit_price - 1) * 100
        
        return Trade(
            trade_id=str(uuid.uuid4())[:8],
            ticker=position.ticker,
            side=OrderSide.BUY if position.side == PositionSide.LONG else OrderSide.SELL,
            quantity=position.quantity,
            entry_price=position.entry_price,
            entry_date=position.entry_date,
            exit_price=exit_price,
            exit_date=datetime.now(),
            pnl=pnl,
            pnl_pct=pnl_pct,
            commission=0,
            hold_time=hold_time
        )
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        if order_id in self.orders:
            order = self.orders[order_id]
            if order.is_active:
                order.status = OrderStatus.CANCELLED
                order.cancelled_at = datetime.now()
                del self.orders[order_id]
                logger.info(f"Order cancelled: {order_id}")
                return True
        return False
    
    def set_stop_loss(self, ticker: str, stop_price: float):
        """Set stop loss for a position"""
        if ticker in self.positions:
            self.positions[ticker].stop_loss = stop_price
            logger.info(f"Stop loss set for {ticker}: {stop_price}")
    
    def set_take_profit(self, ticker: str, take_price: float):
        """Set take profit for a position"""
        if ticker in self.positions:
            self.positions[ticker].take_profit = take_price
            logger.info(f"Take profit set for {ticker}: {take_price}")
    
    def _get_current_price(self, ticker: str) -> Optional[float]:
        """Get current price for a ticker"""
        if self.data_feed:
            return self.data_feed.get_latest_price(ticker)
        
        # Default: use last known price from positions
        if ticker in self.positions:
            return self.positions[ticker].last_price
        
        return None
    
    def _on_price_update(self, ticker: str, price: float):
        """Handle price update from data feed"""
        # Update position values
        if ticker in self.positions:
            self.positions[ticker].update_market_value(price)
        
        # Check stop losses and take profits
        if ticker in self.positions:
            position = self.positions[ticker]
            
            # Check stop loss
            if position.stop_loss:
                if position.side == PositionSide.LONG and price <= position.stop_loss:
                    self.submit_order(
                        ticker, OrderType.MARKET, OrderSide.SELL, 
                        position.quantity, strategy="STOP_LOSS"
                    )
                elif position.side == PositionSide.SHORT and price >= position.stop_loss:
                    self.submit_order(
                        ticker, OrderType.MARKET, OrderSide.BUY,
                        position.quantity, strategy="STOP_LOSS"
                    )
            
            # Check take profit
            if position.take_profit:
                if position.side == PositionSide.LONG and price >= position.take_profit:
                    self.submit_order(
                        ticker, OrderType.MARKET, OrderSide.SELL,
                        position.quantity, strategy="TAKE_PROFIT"
                    )
                elif position.side == PositionSide.SHORT and price <= position.take_profit:
                    self.submit_order(
                        ticker, OrderType.MARKET, OrderSide.BUY,
                        position.quantity, strategy="TAKE_PROFIT"
                    )
    
    def update_prices(self, prices: Dict[str, float]):
        """Update prices for multiple tickers"""
        for ticker, price in prices.items():
            self._on_price_update(ticker, price)
        
        # Record portfolio state
        self._record_portfolio_state()
    
    def _record_portfolio_state(self):
        """Record current portfolio state"""
        summary = self.get_portfolio_summary()
        self.portfolio_history.append(summary)
    
    def run_strategies(self):
        """Run all registered strategies"""
        for name, strategy in self.strategies.items():
            try:
                strategy(self)
            except Exception as e:
                logger.error(f"Strategy {name} error: {e}")
    
    def get_portfolio_summary(self) -> PortfolioSummary:
        """Get current portfolio summary"""
        market_value = sum(p.market_value for p in self.positions.values())
        unrealized_pnl = sum(p.unrealized_pnl for p in self.positions.values())
        total_value = self.cash + market_value
        
        day_change = total_value - self.day_open_value
        day_change_pct = (day_change / self.day_open_value) * 100 if self.day_open_value > 0 else 0
        
        total_pnl = self.realized_pnl + unrealized_pnl
        
        return PortfolioSummary(
            timestamp=datetime.now(),
            total_value=total_value,
            cash_balance=self.cash,
            market_value=market_value,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=self.realized_pnl,
            total_pnl=total_pnl,
            day_change=day_change,
            day_change_pct=day_change_pct,
            open_positions=len(self.positions),
            open_orders=len([o for o in self.orders.values() if o.is_active])
        )
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate performance report"""
        summary = self.get_portfolio_summary()
        
        if not self.trades:
            return {
                'status': 'No trades yet',
                'total_value': summary.total_value,
                'return_pct': (summary.total_value / self.initial_capital - 1) * 100
            }
        
        trades_df = pd.DataFrame([
            {
                'date': t.exit_date,
                'pnl': t.pnl,
                'pnl_pct': t.pnl_pct,
                'hold_time': t.hold_time.total_seconds() / 86400  # Days
            }
            for t in self.trades
        ])
        
        winning_trades = trades_df[trades_df['pnl'] > 0]
        losing_trades = trades_df[trades_df['pnl'] <= 0]
        
        # Calculate metrics
        total_return = (summary.total_value / self.initial_capital - 1) * 100
        
        if len(trades_df) > 0:
            win_rate = len(winning_trades) / len(trades_df) * 100
            avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
            avg_loss = losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0
            profit_factor = (winning_trades['pnl'].sum() / abs(losing_trades['pnl'].sum())) if len(losing_trades) > 0 and losing_trades['pnl'].sum() != 0 else float('inf')
            
            # Drawdown
            cumulative_pnl = trades_df['pnl'].cumsum()
            peak = cumulative_pnl.cummax()
            drawdown = cumulative_pnl - peak
            max_drawdown = drawdown.min()
            
            # Average hold time
            avg_hold_time = trades_df['hold_time'].mean()
        else:
            win_rate = 0
            avg_win = 0
            avg_loss = 0
            profit_factor = 0
            max_drawdown = 0
            avg_hold_time = 0
        
        return {
            'total_value': summary.total_value,
            'total_return_pct': total_return,
            'cash_balance': summary.cash_balance,
            'market_value': summary.market_value,
            'realized_pnl': summary.realized_pnl,
            'unrealized_pnl': summary.unrealized_pnl,
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'avg_hold_time_days': avg_hold_time,
            'open_positions': len(self.positions),
            'day_change': summary.day_change,
            'day_change_pct': summary.day_change_pct
        }
    
    def export_trades(self, filepath: str = "trades.csv"):
        """Export trades to CSV"""
        if not self.trades:
            logger.warning("No trades to export")
            return
        
        trades_data = []
        for t in self.trades:
            trades_data.append({
                'trade_id': t.trade_id,
                'ticker': t.ticker,
                'side': t.side.value,
                'quantity': t.quantity,
                'entry_price': t.entry_price,
                'entry_date': t.entry_date,
                'exit_price': t.exit_price,
                'exit_date': t.exit_date,
                'pnl': t.pnl,
                'pnl_pct': t.pnl_pct,
                'hold_time_days': t.hold_time.total_seconds() / 86400,
                'strategy': t.strategy
            })
        
        df = pd.DataFrame(trades_data)
        df.to_csv(filepath, index=False)
        logger.info(f"Trades exported to {filepath}")
    
    def reset(self, new_capital: float = None):
        """Reset paper trading state"""
        if new_capital:
            self.initial_capital = new_capital
        self.cash = self.initial_capital
        self.positions = {}
        self.orders = {}
        self.trades = []
        self.portfolio_history = []
        self.day_open_value = self.initial_capital
        self.realized_pnl = 0
        
        logger.info(f"Paper trading reset. Capital: ${self.initial_capital:,.2f}")


# Example usage
if __name__ == "__main__":
    # Create mock data feed
    class MockDataFeed(DataFeed):
        def __init__(self):
            self.prices = {'AAPL': 150.0, 'GOOG': 2800.0, 'MSFT': 300.0}
            self.subscribers = []
        
        def get_latest_price(self, ticker):
            # Add some noise
            noise = np.random.randn() * 0.5
            return self.prices.get(ticker) + noise
        
        def subscribe(self, tickers, callback):
            self.subscribers.append((tickers, callback))
    
    # Initialize paper trading
    engine = PaperTradingEngine(
        initial_capital=100000,
        fee_rate=0.001,
        data_feed=MockDataFeed()
    )
    
    # Define a simple strategy
    def moving_average_strategy(engine):
        ticker = 'AAPL'
        price = engine._get_current_price(ticker)
        
        # Simple logic: buy if cash available, sell if position
        if ticker not in engine.positions and price:
            engine.submit_order(
                ticker, OrderType.MARKET, OrderSide.BUY,
                100, strategy="MA_Strategy"
            )
        elif ticker in engine.positions:
            engine.submit_order(
                ticker, OrderType.MARKET, OrderSide.SELL,
                50, strategy="MA_Strategy"
            )
    
    engine.register_strategy("ma_strategy", moving_average_strategy, ['AAPL'])
    
    # Run for a few iterations
    print("Running Paper Trading Simulation...")
    for i in range(5):
        engine.run_strategies()
        engine.update_prices({
            'AAPL': 150 + i * 2,
            'GOOG': 2800 + i * 10,
            'MSFT': 300 + i * 5
        })
        print(f"Step {i+1}: Value=${engine.get_portfolio_summary().total_value:,.2f}, Positions={len(engine.positions)}")
    
    # Get performance report
    report = engine.get_performance_report()
    
    print("\nPerformance Report:")
    print("=" * 60)
    for key, value in report.items():
        print(f"{key:25}: {value}")
    
    # Export trades
    engine.export_trades("paper_trades.csv")
