"""
Paper Trading Mode for AI Quant Hedge Fund
Simulates live trading without real money for testing strategies
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from enum import Enum
import json
import logging
import uuid

logger = logging.getLogger(__name__)


class OrderAction(Enum):
    BUY = "BUY"
    SELL = "SELL"
    CLOSE = "CLOSE"


class OrderStatus(Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class PositionSide(Enum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class PaperOrder:
    """Paper trading order."""
    order_id: str
    symbol: str
    action: str
    volume: float
    price: float
    sl: Optional[float]
    tp: Optional[float]
    status: str = OrderStatus.PENDING.value
    filled_price: float = 0.0
    filled_time: Optional[datetime] = None
    reason: str = ""
    strategy: str = ""
    confidence: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class PaperPosition:
    """Paper trading position."""
    position_id: str
    symbol: str
    side: str
    volume: float
    entry_price: float
    entry_time: datetime
    sl: Optional[float]
    tp: Optional[float]
    current_price: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    strategy: str = ""
    order_id: str = ""


@dataclass
class PaperTrade:
    """Completed paper trade."""
    trade_id: str
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    volume: float
    entry_time: datetime
    exit_time: datetime
    pnl: float
    pnl_pct: float
    duration_seconds: float
    strategy: str
    exit_reason: str


class PaperTradingConfig:
    """Configuration for paper trading."""
    
    def __init__(
        self,
        initial_capital: float = 100000.0,
        max_positions: int = 10,
        max_position_size: float = 0.20,
        max_daily_loss: float = 0.05,
        max_correlation: float = 0.7,
        allow_short: bool = True,
        allow_hedge: bool = False,
        commission_rate: float = 0.0001,
        slippage: float = 0.0001,
        tick_size: float = 0.00001
    ):
        self.initial_capital = initial_capital
        self.max_positions = max_positions
        self.max_position_size = max_position_size
        self.max_daily_loss = max_daily_loss
        self.max_correlation = max_correlation
        self.allow_short = allow_short
        self.allow_hedge = allow_hedge
        self.commission_rate = commission_rate
        self.slippage = slippage
        self.tick_size = tick_size


class PaperTrader:
    """
    Paper trading simulator for testing strategies.
    
    Features:
    - Simulates order execution with realistic slippage
    - Tracks positions and PnL
    - Risk management checks
    - Trade history and statistics
    - Event callbacks
    """
    
    def __init__(self, config: PaperTradingConfig = None):
        self.config = config or PaperTradingConfig()
        
        self.cash = self.config.initial_capital
        self.equity = self.config.initial_capital
        self.daily_pnl = 0.0
        self.daily_start_equity = self.config.initial_capital
        
        self.orders: Dict[str, PaperOrder] = {}
        self.positions: Dict[str, PaperPosition] = {}
        self.trades: List[PaperTrade] = []
        
        self.symbol_prices: Dict[str, float] = {}
        self.symbol_bid_ask: Dict[str, Dict] = {}
        
        self._callbacks: Dict[str, List[Callable]] = {
            "order_filled": [],
            "order_cancelled": [],
            "position_opened": [],
            "position_closed": [],
            "trade_closed": [],
            "tick": [],
            "error": []
        }
        
        self._trade_count = 0
        self._winning_trades = 0
        self._losing_trades = 0
        self._start_time = datetime.now()
    
    @property
    def available_cash(self) -> float:
        """Get available cash for trading."""
        margin_used = self._calculate_margin_used()
        return max(0, self.cash - margin_used)
    
    @property
    def margin_used(self) -> float:
        """Get used margin."""
        return self._calculate_margin_used()
    
    @property
    def margin_level(self) -> float:
        """Get current margin level."""
        if self.margin_used == 0:
            return 0.0
        return (self.equity / self.margin_used) * 100 if self.margin_used > 0 else 0.0
    
    @property
    def win_rate(self) -> float:
        """Get win rate."""
        total = self._winning_trades + self._losing_trades
        return (self._winning_trades / total * 100) if total > 0 else 0.0
    
    @property
    def profit_factor(self) -> float:
        """Calculate profit factor."""
        wins = [t.pnl for t in self.trades if t.pnl > 0]
        losses = [abs(t.pnl) for t in self.trades if t.pnl < 0]
        
        win_total = sum(wins) if wins else 0
        loss_total = sum(losses) if losses else 0
        
        return win_total / loss_total if loss_total > 0 else float('inf')
    
    def subscribe(self, event: str, callback: Callable) -> None:
        """Subscribe to trading events."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    def update_price(self, symbol: str, bid: float, ask: float) -> None:
        """Update price for a symbol."""
        self.symbol_prices[symbol] = (bid + ask) / 2
        self.symbol_bid_ask[symbol] = {"bid": bid, "ask": ask}
        
        self._check_orders(symbol)
        self._update_positions(symbol)
        
        for callback in self._callbacks.get("tick", []):
            try:
                callback(symbol, bid, ask)
            except Exception as e:
                logger.error(f"Tick callback error: {e}")
    
    def place_order(
        self,
        symbol: str,
        action: str,
        volume: float,
        sl: float = None,
        tp: float = None,
        strategy: str = "",
        confidence: float = 0.0,
        reason: str = ""
    ) -> Dict:
        """
        Place a paper trading order.
        
        Args:
            symbol: Trading symbol
            action: BUY, SELL, or CLOSE
            volume: Position volume
            sl: Stop loss price
            tp: Take profit price
            strategy: Strategy name
            confidence: Signal confidence
            reason: Order reason
            
        Returns:
            Dict with order details
        """
        order_id = str(uuid.uuid4())[:8]
        
        current_price = self.symbol_prices.get(symbol)
        if current_price is None:
            current_price = 100.0
        
        order = PaperOrder(
            order_id=order_id,
            symbol=symbol,
            action=action,
            volume=volume,
            price=current_price,
            sl=sl,
            tp=tp,
            strategy=strategy,
            confidence=confidence,
            reason=reason
        )
        
        validation = self._validate_order(order)
        if not validation["valid"]:
            order.status = OrderStatus.REJECTED.value
            order.reason = validation["reason"]
            self.orders[order_id] = order
            
            for callback in self._callbacks.get("error", []):
                try:
                    callback(order)
                except Exception as e:
                    logger.error(f"Error callback error: {e}")
            
            return {
                "order_id": order_id,
                "status": "REJECTED",
                "reason": validation["reason"]
            }
        
        self.orders[order_id] = order
        
        if action == OrderAction.CLOSE.value:
            return self._execute_close(order)
        
        return self._execute_order(order)
    
    def _validate_order(self, order: PaperOrder) -> Dict:
        """Validate order against risk rules."""
        if order.action == OrderAction.CLOSE.value:
            return {"valid": True, "reason": ""}
        
        if len(self.positions) >= self.config.max_positions:
            return {"valid": False, "reason": "Max positions reached"}
        
        if self.cash < 100:
            return {"valid": False, "reason": "Insufficient cash"}
        
        if order.volume <= 0:
            return {"valid": False, "reason": "Invalid volume"}
        
        if order.action == OrderAction.BUY.value:
            estimated_cost = order.volume * order.price * (1 + self.config.commission_rate)
            if estimated_cost > self.available_cash:
                return {"valid": False, "reason": "Insufficient funds"}
        
        if self.config.max_position_size > 0:
            position_value = order.volume * order.price
            max_value = self.equity * self.config.max_position_size
            if position_value > max_value:
                return {"valid": False, "reason": "Position size exceeds limit"}
        
        if not self.config.allow_short and order.action == OrderAction.SELL.value:
            return {"valid": False, "reason": "Short selling not allowed"}
        
        if order.sl and order.tp:
            if order.action == OrderAction.BUY.value:
                if order.sl >= order.price or order.tp <= order.price:
                    return {"valid": False, "reason": "Invalid SL/TP for BUY"}
            else:
                if order.sl <= order.price or order.tp >= order.price:
                    return {"valid": False, "reason": "Invalid SL/TP for SELL"}
        
        return {"valid": True, "reason": ""}
    
    def _execute_order(self, order: PaperOrder) -> Dict:
        """Execute an order immediately (market order simulation)."""
        bid = self.symbol_bid_ask.get(order.symbol, {}).get("bid", order.price)
        ask = self.symbol_bid_ask.get(order.symbol, {}).get("ask", order.price)
        
        if order.action == OrderAction.BUY.value:
            execution_price = ask * (1 + self.config.slippage)
        else:
            execution_price = bid * (1 - self.config.slippage)
        
        commission = execution_price * order.volume * self.config.commission_rate
        
        order.filled_price = round(execution_price, 5)
        order.filled_time = datetime.now()
        order.status = OrderStatus.FILLED.value
        
        self.cash -= (execution_price * order.volume + commission)
        
        position = PaperPosition(
            position_id=str(uuid.uuid4())[:8],
            symbol=order.symbol,
            side=PositionSide.LONG.value if order.action == OrderAction.BUY.value else PositionSide.SHORT.value,
            volume=order.volume,
            entry_price=execution_price,
            entry_time=datetime.now(),
            sl=order.sl,
            tp=order.tp,
            current_price=execution_price,
            strategy=order.strategy,
            order_id=order.order_id
        )
        
        self.positions[position.position_id] = position
        
        for callback in self._callbacks.get("order_filled", []):
            try:
                callback(order)
            except Exception as e:
                logger.error(f"Order filled callback error: {e}")
        
        for callback in self._callbacks.get("position_opened", []):
            try:
                callback(position)
            except Exception as e:
                logger.error(f"Position opened callback error: {e}")
        
        logger.info(f"Paper Order Filled: {order.action} {order.symbol} {order.volume} @ {execution_price:.5f}")
        
        return {
            "order_id": order.order_id,
            "status": "FILLED",
            "filled_price": execution_price,
            "filled_time": order.filled_time.isoformat(),
            "commission": commission
        }
    
    def _execute_close(self, order: PaperOrder) -> Dict:
        """Execute a close order."""
        positions_to_close = [
            p for p in self.positions.values()
            if p.symbol == order.symbol
        ]
        
        if not positions_to_close:
            order.status = OrderStatus.REJECTED.value
            order.reason = "No position to close"
            return {
                "order_id": order.order_id,
                "status": "REJECTED",
                "reason": "No position found"
            }
        
        position = positions_to_close[0]
        bid = self.symbol_bid_ask.get(order.symbol, {}).get("bid", position.current_price)
        ask = self.symbol_bid_ask.get(order.symbol, {}).get("ask", position.current_price)
        
        if position.side == PositionSide.LONG.value:
            exit_price = bid * (1 - self.config.slippage)
        else:
            exit_price = ask * (1 + self.config.slippage)
        
        commission = exit_price * position.volume * self.config.commission_rate
        
        if position.side == PositionSide.LONG.value:
            pnl = (exit_price - position.entry_price) * position.volume - commission
        else:
            pnl = (position.entry_price - exit_price) * position.volume - commission
        
        self.cash += (exit_price * position.volume - commission)
        
        self._trade_count += 1
        if pnl > 0:
            self._winning_trades += 1
        else:
            self._losing_trades += 1
        
        self.daily_pnl += pnl
        self.equity = self.cash + sum(p.current_price * p.volume for p in self.positions.values())
        
        trade = PaperTrade(
            trade_id=str(uuid.uuid4())[:8],
            symbol=position.symbol,
            side=position.side,
            entry_price=position.entry_price,
            exit_price=exit_price,
            volume=position.volume,
            entry_time=position.entry_time,
            exit_time=datetime.now(),
            pnl=pnl,
            pnl_pct=(pnl / (position.entry_price * position.volume)) * 100,
            duration_seconds=(datetime.now() - position.entry_time).total_seconds(),
            strategy=position.strategy,
            exit_reason=order.reason or "Manual close"
        )
        
        self.trades.append(trade)
        
        del self.positions[position.position_id]
        
        for callback in self._callbacks.get("trade_closed", []):
            try:
                callback(trade)
            except Exception as e:
                logger.error(f"Trade closed callback error: {e}")
        
        logger.info(f"Paper Trade Closed: {position.symbol} {position.side} PnL: ${pnl:.2f}")
        
        return {
            "order_id": order.order_id,
            "status": "FILLED",
            "exit_price": exit_price,
            "pnl": pnl,
            "pnl_pct": trade.pnl_pct
        }
    
    def _check_orders(self, symbol: str) -> None:
        """Check and execute pending orders."""
        for order in list(self.orders.values()):
            if order.symbol == symbol and order.status == OrderStatus.PENDING.value:
                self._execute_order(order)
    
    def _update_positions(self, symbol: str) -> None:
        """Update position PnL and check SL/TP."""
        positions_to_close = []
        
        for position in self.positions.values():
            if position.symbol != symbol:
                continue
            
            bid = self.symbol_bid_ask.get(symbol, {}).get("bid", position.current_price)
            ask = self.symbol_bid_ask.get(symbol, {}).get("ask", position.current_price)
            
            if position.side == PositionSide.LONG.value:
                position.current_price = ask
                position.pnl = (ask - position.entry_price) * position.volume
            else:
                position.current_price = bid
                position.pnl = (position.entry_price - bid) * position.volume
            
            position.pnl_pct = (position.pnl / (position.entry_price * position.volume)) * 100
            
            sl_hit = False
            tp_hit = False
            
            if position.sl and position.side == PositionSide.LONG.value and position.current_price <= position.sl:
                sl_hit = True
            elif position.sl and position.side == PositionSide.SHORT.value and position.current_price >= position.sl:
                sl_hit = True
            
            if position.tp and position.side == PositionSide.LONG.value and position.current_price >= position.tp:
                tp_hit = True
            elif position.tp and position.side == PositionSide.SHORT.value and position.current_price <= position.tp:
                tp_hit = True
            
            if sl_hit or tp_hit:
                positions_to_close.append((position, "SL" if sl_hit else "TP"))
        
        for position, reason in positions_to_close:
            self.close_position(position.position_id, reason)
    
    def close_position(self, position_id: str, reason: str = "Manual") -> Dict:
        """Close a specific position."""
        if position_id not in self.positions:
            return {"status": "ERROR", "reason": "Position not found"}
        
        position = self.positions[position_id]
        symbol = position.symbol
        
        bid = self.symbol_bid_ask.get(symbol, {}).get("bid", position.current_price)
        ask = self.symbol_bid_ask.get(symbol, {}).get("ask", position.current_price)
        
        if position.side == PositionSide.LONG.value:
            exit_price = bid * (1 - self.config.slippage)
        else:
            exit_price = ask * (1 + self.config.slippage)
        
        commission = exit_price * position.volume * self.config.commission_rate
        
        if position.side == PositionSide.LONG.value:
            pnl = (exit_price - position.entry_price) * position.volume - commission
        else:
            pnl = (position.entry_price - exit_price) * position.volume - commission
        
        self.cash += (exit_price * position.volume - commission)
        
        self._trade_count += 1
        if pnl > 0:
            self._winning_trades += 1
        else:
            self._losing_trades += 1
        
        self.daily_pnl += pnl
        self.equity = self.cash + sum(p.current_price * p.volume for p in self.positions.values())
        
        trade = PaperTrade(
            trade_id=str(uuid.uuid4())[:8],
            symbol=position.symbol,
            side=position.side,
            entry_price=position.entry_price,
            exit_price=exit_price,
            volume=position.volume,
            entry_time=position.entry_time,
            exit_time=datetime.now(),
            pnl=pnl,
            pnl_pct=(pnl / (position.entry_price * position.volume)) * 100,
            duration_seconds=(datetime.now() - position.entry_time).total_seconds(),
            strategy=position.strategy,
            exit_reason=reason
        )
        
        self.trades.append(trade)
        
        for callback in self._callbacks.get("position_closed", []):
            try:
                callback(position)
            except Exception as e:
                logger.error(f"Position closed callback error: {e}")
        
        del self.positions[position_id]
        
        logger.info(f"Position Closed: {symbol} {reason} PnL: ${pnl:.2f}")
        
        return {
            "position_id": position_id,
            "status": "CLOSED",
            "exit_price": exit_price,
            "pnl": pnl,
            "pnl_pct": trade.pnl_pct
        }
    
    def close_all_positions(self, reason: str = "Emergency") -> List[Dict]:
        """Close all open positions."""
        results = []
        for position_id in list(self.positions.keys()):
            result = self.close_position(position_id, reason)
            results.append(result)
        return results
    
    def reset(self) -> None:
        """Reset paper trader to initial state."""
        self.cash = self.config.initial_capital
        self.equity = self.config.initial_capital
        self.daily_pnl = 0.0
        self.daily_start_equity = self.config.initial_capital
        self.orders = {}
        self.positions = {}
        self.trades = []
        self._trade_count = 0
        self._winning_trades = 0
        self._losing_trades = 0
        self._start_time = datetime.now()
        logger.info("Paper trader reset")
    
    def _calculate_margin_used(self) -> float:
        """Calculate used margin."""
        return sum(
            p.volume * p.current_price * 0.1
            for p in self.positions.values()
        )
    
    def get_status(self) -> Dict:
        """Get current trading status."""
        self.equity = self.cash + sum(
            p.current_price * p.volume
            for p in self.positions.values()
        )
        
        return {
            "cash": self.cash,
            "equity": self.equity,
            "daily_pnl": self.daily_pnl,
            "daily_pnl_pct": (self.daily_pnl / self.daily_start_equity) * 100 if self.daily_start_equity > 0 else 0,
            "open_positions": len(self.positions),
            "pending_orders": len([o for o in self.orders.values() if o.status == OrderStatus.PENDING.value]),
            "completed_trades": self._trade_count,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "margin_level": self.margin_level,
            "session_duration_seconds": (datetime.now() - self._start_time).total_seconds()
        }
    
    def get_trade_history(self, days: int = None) -> List[Dict]:
        """Get trade history."""
        if days is None:
            return [t.__dict__ for t in self.trades]
        
        cutoff = datetime.now() - datetime.timedelta(days=days)
        return [
            t.__dict__ for t in self.trades
            if t.exit_time >= cutoff
        ]
    
    def get_statistics(self) -> Dict:
        """Get trading statistics."""
        if not self.trades:
            return {
                "total_trades": 0,
                "win_rate": 0,
                "profit_factor": 0,
                "avg_win": 0,
                "avg_loss": 0,
                "max_win": 0,
                "max_loss": 0,
                "avg_duration_hours": 0,
                "total_pnl": 0
            }
        
        pnl_values = [t.pnl for t in self.trades]
        wins = [p for p in pnl_values if p > 0]
        losses = [p for p in pnl_values if p < 0]
        
        durations = [t.duration_seconds / 3600 for t in self.trades]
        
        return {
            "total_trades": len(self.trades),
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "avg_win": np.mean(wins) if wins else 0,
            "avg_loss": np.mean(losses) if losses else 0,
            "max_win": max(wins) if wins else 0,
            "max_loss": min(losses) if losses else 0,
            "avg_duration_hours": np.mean(durations) if durations else 0,
            "total_pnl": sum(pnl_values),
            "avg_pnl": np.mean(pnl_values),
            "std_pnl": np.std(pnl_values) if len(pnl_values) > 1 else 0
        }
    
    def export_trades(self, filepath: str) -> None:
        """Export trades to JSON file."""
        trades_data = [
            {
                "trade_id": t.trade_id,
                "symbol": t.symbol,
                "side": t.side,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "volume": t.volume,
                "entry_time": t.entry_time.isoformat(),
                "exit_time": t.exit_time.isoformat(),
                "pnl": t.pnl,
                "pnl_pct": t.pnl_pct,
                "duration_seconds": t.duration_seconds,
                "strategy": t.strategy,
                "exit_reason": t.exit_reason
            }
            for t in self.trades
        ]
        
        with open(filepath, 'w') as f:
            json.dump(trades_data, f, indent=2)
        
        logger.info(f"Trades exported to {filepath}")


def create_paper_trader(
    initial_capital: float = 100000.0,
    max_positions: int = 10,
    max_position_size: float = 0.20
) -> PaperTrader:
    """Factory function to create paper trader."""
    config = PaperTradingConfig(
        initial_capital=initial_capital,
        max_positions=max_positions,
        max_position_size=max_position_size
    )
    return PaperTrader(config)


if __name__ == "__main__":
    trader = create_paper_trader()
    
    print("Paper Trading Demo")
    print("=" * 50)
    
    trader.update_price("EURUSD", 1.0850, 1.0855)
    trader.update_price("GBPUSD", 1.2700, 1.2705)
    trader.update_price("USDJPY", 149.50, 149.55)
    
    result = trader.place_order(
        symbol="EURUSD",
        action="BUY",
        volume=1.0,
        sl=1.0800,
        tp=1.1000,
        strategy="ICT SMC",
        confidence=0.75,
        reason="Order block breakout"
    )
    
    print(f"Order Result: {result}")
    
    status = trader.get_status()
    print(f"\nStatus: {status}")
    
    for i in range(10):
        trader.update_price("EURUSD", 1.0850 + i * 0.0001, 1.0855 + i * 0.0001)
    
    stats = trader.get_statistics()
    print(f"\nStatistics: {stats}")
