"""
🌟 ORCHID QUANTUM AI - Trader Agent
=====================================
Specialized agent for trade execution.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from .base import BaseAgent, AgentMessage, MessageType, AgentState
import logging


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    """Order definition."""
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    order_id: str = field(default_factory=lambda: str(datetime.now().timestamp()))
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    filled_price: Optional[float] = None
    commission: float = 0.0
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'order_id': self.order_id,
            'symbol': self.symbol,
            'side': self.side.value,
            'order_type': self.order_type.value,
            'quantity': self.quantity,
            'price': self.price,
            'stop_price': self.stop_price,
            'timestamp': self.timestamp.isoformat(),
            'status': self.status.value,
            'filled_quantity': self.filled_quantity,
            'filled_price': self.filled_price,
            'commission': self.commission
        }


class TraderAgent(BaseAgent):
    """Agent responsible for trade execution and management."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(
            agent_id="trader_agent_001",
            name="Trader Agent"
        )
        self.capabilities = [
            "order_execution",
            "position_management",
            "execution_optimization",
            "slippage_control",
            "trade_logging"
        ]
        self.config = config or {
            'max_slippage': 0.002,
            'execution_style': 'TWAP',
            'max_retry': 3,
            'transaction_cost': 0.001
        }
        self.orders: Dict[str, Order] = {}
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.order_history: List[Order] = []
        self.execution_log: List[Dict[str, Any]] = []
        
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the trader agent."""
        self.config.update(config)
        self.logger.info("Trader Agent initialized")
        return True
    
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute trading task."""
        task_type = task.get('type', 'trade')
        
        if task_type == 'trade':
            return self._execute_trade(task)
        elif task_type == 'place_order':
            return self._place_order(task)
        elif task_type == 'cancel_order':
            return self._cancel_order(task)
        elif task_type == 'get_positions':
            return self._get_positions(task)
        elif task_type == 'get_orders':
            return self._get_orders(task)
        elif task_type == 'close_position':
            return self._close_position(task)
        else:
            return {'status': 'error', 'message': f'Unknown task type: {task_type}'}
    
    def _execute_trade(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a trade from signal."""
        signal = task.get('signal', {})
        symbol = signal.get('symbol', '')
        direction = signal.get('direction', 'HOLD')
        confidence = signal.get('confidence', 0.5)
        entry_price = signal.get('entry_price', 0)
        stop_loss = signal.get('stop_loss', 0)
        take_profit = signal.get('take_profit', 0)
        position_size = signal.get('position_size', 0.1)
        
        if direction == 'HOLD':
            return {
                'status': 'success',
                'message': 'Hold signal - no trade executed',
                'signal': signal
            }
        
        # Convert direction to order side
        if direction == 'BUY':
            side = OrderSide.BUY
        elif direction == 'SELL':
            side = OrderSide.SELL
        else:
            return {
                'status': 'success',
                'message': 'Unknown direction - no trade executed',
                'signal': signal
            }
        
        # Get current price (simulated)
        current_price = self._get_market_price(symbol)
        
        if current_price == 0:
            current_price = entry_price
        
        # Calculate quantity
        portfolio_value = task.get('portfolio_value', 100000)
        quantity = (portfolio_value * position_size) / current_price
        
        # Create order
        order = Order(
            symbol=symbol,
            side=side,
            order_type=OrderType.MARKET,
            quantity=quantity,
            price=current_price,
            metadata={
                'signal': signal,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'confidence': confidence
            }
        )
        
        # Execute order
        result = self._submit_order(order)
        
        # If filled, create stop loss and take profit orders
        if result.get('status') == 'filled':
            if stop_loss > 0:
                self._create_stop_order(symbol, side, quantity, stop_loss)
            if take_profit > 0:
                self._create_take_profit_order(symbol, side, quantity, take_profit)
        
        return result
    
    def _place_order(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Place an order."""
        symbol = task.get('symbol', '')
        side = task.get('side', 'buy')
        order_type = task.get('order_type', 'market')
        quantity = task.get('quantity', 0)
        price = task.get('price', None)
        stop_price = task.get('stop_price', None)
        
        if side == 'buy':
            order_side = OrderSide.BUY
        elif side == 'sell':
            order_side = OrderSide.SELL
        else:
            order_side = OrderSide.HOLD
        
        if order_type == 'market':
            order_type_enum = OrderType.MARKET
        elif order_type == 'limit':
            order_type_enum = OrderType.LIMIT
        elif order_type == 'stop':
            order_type_enum = OrderType.STOP
        else:
            order_type_enum = OrderType.MARKET
        
        order = Order(
            symbol=symbol,
            side=order_side,
            order_type=order_type_enum,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            metadata=task.get('metadata', {})
        )
        
        return self._submit_order(order)
    
    def _submit_order(self, order: Order) -> Dict[str, Any]:
        """Submit and execute order."""
        # Validate order
        if order.quantity <= 0:
            order.status = OrderStatus.REJECTED
            return {
                'status': 'error',
                'message': 'Invalid quantity',
                'order': order.to_dict()
            }
        
        # Simulate order execution
        current_price = self._get_market_price(order.symbol)
        if current_price == 0:
            current_price = order.price or 100
        
        # Check slippage
        if order.price:
            slippage = abs(current_price - order.price) / current_price
            if slippage > self.config.get('max_slippage', 0.002):
                order.status = OrderStatus.REJECTED
                self.execution_log.append({
                    'timestamp': datetime.now().isoformat(),
                    'action': 'rejected',
                    'reason': 'Slippage too high',
                    'order': order.to_dict()
                })
                return {
                    'status': 'rejected',
                    'message': 'Slippage exceeds limit',
                    'slippage': slippage,
                    'order': order.to_dict()
                }
        
        # Simulate fill (in real implementation, this would be async)
        fill_price = current_price * (1 + np.random.uniform(-0.0005, 0.0005))
        commission = fill_price * order.quantity * self.config.get('transaction_cost', 0.001)
        
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.filled_price = fill_price
        order.commission = commission
        
        # Update positions
        self._update_position(order)
        
        # Add to history
        self.orders[order.order_id] = order
        self.order_history.append(order)
        
        # Log execution
        self.execution_log.append({
            'timestamp': datetime.now().isoformat(),
            'action': 'filled',
            'order_id': order.order_id,
            'symbol': order.symbol,
            'side': order.side.value,
            'quantity': order.quantity,
            'fill_price': fill_price,
            'commission': commission
        })
        
        self.logger.info(f"Order filled: {order.symbol} {order.side.value} {order.quantity} @ {fill_price}")
        
        return {
            'status': 'filled',
            'order': order.to_dict(),
            'execution': {
                'fill_price': fill_price,
                'commission': commission,
                'slippage': slippage if order.price else 0
            }
        }
    
    def _update_position(self, order: Order) -> None:
        """Update position after order fill."""
        symbol = order.symbol
        
        if symbol not in self.positions:
            self.positions[symbol] = {
                'symbol': symbol,
                'quantity': 0,
                'avg_price': 0,
                'realized_pnl': 0,
                'unrealized_pnl': 0
            }
        
        position = self.positions[symbol]
        
        if order.side == OrderSide.BUY:
            total_cost = position['quantity'] * position['avg_price'] + order.filled_quantity * order.filled_price
            total_quantity = position['quantity'] + order.filled_quantity
            position['avg_price'] = total_cost / total_quantity if total_quantity > 0 else 0
            position['quantity'] = total_quantity
        else:
            # Sell - calculate realized P&L
            realized = (order.filled_price - position['avg_price']) * order.filled_quantity
            position['realized_pnl'] += realized
            position['quantity'] -= order.filled_quantity
            
            if position['quantity'] < 0.001:
                del self.positions[symbol]
    
    def _create_stop_order(self, symbol: str, side: OrderSide, 
                          quantity: float, stop_price: float) -> Order:
        """Create stop loss order."""
        # For long position, stop sell; for short position, stop buy
        if side == OrderSide.BUY:
            stop_side = OrderSide.SELL
        else:
            stop_side = OrderSide.BUY
        
        order = Order(
            symbol=symbol,
            side=stop_side,
            order_type=OrderType.STOP,
            quantity=quantity,
            stop_price=stop_price,
            metadata={'type': 'stop_loss'}
        )
        
        self.orders[order.order_id] = order
        return order
    
    def _create_take_profit_order(self, symbol: str, side: OrderSide,
                                  quantity: float, take_profit: float) -> Order:
        """Create take profit order."""
        if side == OrderSide.BUY:
            tp_side = OrderSide.SELL
        else:
            tp_side = OrderSide.BUY
        
        order = Order(
            symbol=symbol,
            side=tp_side,
            order_type=OrderType.LIMIT,
            quantity=quantity,
            price=take_profit,
            metadata={'type': 'take_profit'}
        )
        
        self.orders[order.order_id] = order
        return order
    
    def _cancel_order(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Cancel an order."""
        order_id = task.get('order_id', '')
        
        if order_id in self.orders:
            order = self.orders[order_id]
            if order.status == OrderStatus.PENDING:
                order.status = OrderStatus.CANCELLED
                self.execution_log.append({
                    'timestamp': datetime.now().isoformat(),
                    'action': 'cancelled',
                    'order_id': order_id
                })
                return {
                    'status': 'cancelled',
                    'order_id': order_id
                }
            else:
                return {
                    'status': 'error',
                    'message': f'Cannot cancel order in status: {order.status.value}'
                }
        else:
            return {
                'status': 'error',
                'message': 'Order not found'
            }
    
    def _get_positions(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Get current positions."""
        positions = []
        
        for symbol, position in self.positions.items():
            current_price = self._get_market_price(symbol)
            position['market_price'] = current_price
            position['market_value'] = position['quantity'] * current_price
            position['unrealized_pnl'] = (current_price - position['avg_price']) * position['quantity']
            position['unrealized_pnl_pct'] = (current_price / position['avg_price'] - 1) if position['avg_price'] > 0 else 0
            positions.append(position)
        
        total_value = sum(p['market_value'] for p in positions)
        total_unrealized = sum(p['unrealized_pnl'] for p in positions)
        
        return {
            'status': 'success',
            'positions': positions,
            'count': len(positions),
            'total_value': total_value,
            'total_unrealized_pnl': total_unrealized
        }
    
    def _get_orders(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Get order history."""
        status_filter = task.get('status', None)
        symbol_filter = task.get('symbol', None)
        
        orders = list(self.order_history)
        
        if status_filter:
            orders = [o for o in orders if o.status.value == status_filter]
        
        if symbol_filter:
            orders = [o for o in orders if o.symbol == symbol_filter]
        
        return {
            'status': 'success',
            'orders': [o.to_dict() for o in orders],
            'count': len(orders)
        }
    
    def _close_position(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Close a position."""
        symbol = task.get('symbol', '')
        
        if symbol not in self.positions:
            return {
                'status': 'error',
                'message': f'No position for {symbol}'
            }
        
        position = self.positions[symbol]
        quantity = position['quantity']
        current_price = self._get_market_price(symbol)
        
        # Create market sell order
        order = Order(
            symbol=symbol,
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=quantity,
            price=current_price,
            metadata={'type': 'close_position'}
        )
        
        return self._submit_order(order)
    
    def _get_market_price(self, symbol: str) -> float:
        """Get current market price (simulated)."""
        # In real implementation, this would fetch from broker API
        return 100.0  # Simulated price
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get execution summary."""
        filled_orders = [o for o in self.order_history if o.status == OrderStatus.FILLED]
        
        total_commission = sum(o.commission for o in filled_orders)
        total_volume = sum(o.filled_quantity * o.filled_price for o in filled_orders)
        
        return {
            'total_orders': len(self.order_history),
            'filled_orders': len(filled_orders),
            'pending_orders': len([o for o in self.orders.values() if o.status == OrderStatus.PENDING]),
            'total_commission': total_commission,
            'total_volume': total_volume,
            'positions': len(self.positions)
        }
    
    def _process_message(self, message: AgentMessage) -> None:
        """Process incoming message."""
        if message.msg_type == MessageType.TRADING_SIGNAL:
            task = {'type': 'trade', 'signal': message.payload}
            result = self.execute(task)
            
            response = AgentMessage(
                msg_type=MessageType.DATA_RESPONSE,
                sender_id=self.agent_id,
                receiver_id=message.sender_id,
                payload=result,
                priority=message.priority
            )
            self._deliver_message(response)
        
        elif message.msg_type == MessageType.HEARTBEAT:
            self.heartbeat()
            self.state = AgentState.RUNNING
