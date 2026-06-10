"""
🌟 ORCHID QUANTUM AI - Strategist Agent
=========================================
Specialized agent for strategy generation and optimization.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from scipy.optimize import minimize
from .base import BaseAgent, AgentMessage, MessageType, AgentState
import logging


class StrategyType(Enum):
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    PAIRS_TRADING = "pairs_trading"
    GRID_TRADING = "grid_trading"
    BREAKOUT = "breakout"
    TREND_FOLLOWING = "trend_following"


class SignalDirection(Enum):
    BUY = 1
    SELL = -1
    HOLD = 0


@dataclass
class TradingSignal:
    """Trading signal from strategy."""
    symbol: str
    direction: SignalDirection
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    timestamp: datetime
    strategy: str
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'direction': self.direction.value,
            'confidence': self.confidence,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'position_size': self.position_size,
            'timestamp': self.timestamp.isoformat(),
            'strategy': self.strategy,
            'metadata': self.metadata or {}
        }


class StrategistAgent(BaseAgent):
    """Agent responsible for generating and optimizing trading strategies."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(
            agent_id="strategist_001",
            name="Strategist Agent"
        )
        self.capabilities = [
            "signal_generation",
            "strategy_optimization",
            "parameter_tuning",
            "ensemble_combination",
            "risk_adjusted_positioning"
        ]
        self.config = config or {}
        self.active_strategies: Dict[str, Any] = {}
        self.signal_history: List[TradingSignal] = []
        
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the strategist agent."""
        self.config.update(config)
        self._setup_default_strategies()
        self.logger.info("Strategist Agent initialized")
        return True
    
    def _setup_default_strategies(self) -> None:
        """Setup default strategy configurations."""
        self.active_strategies = {
            'momentum': {
                'enabled': True,
                'lookback_period': 20,
                'threshold': 0.05,
                'exit_threshold': -0.02,
                'max_hold_days': 30
            },
            'mean_reversion': {
                'enabled': True,
                'lookback_period': 20,
                'std_deviations': 2.0,
                'exit_threshold': 0.5
            },
            'breakout': {
                'enabled': True,
                'breakout_period': 20,
                'volume_multiplier': 1.5
            },
            'trend_following': {
                'enabled': True,
                'fast_ema': 12,
                'slow_ema': 26,
                'signal_ema': 9
            }
        }
    
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute strategy task."""
        task_type = task.get('type', 'generate')
        
        if task_type == 'generate':
            return self._generate_signals(task)
        elif task_type == 'optimize':
            return self._optimize_strategy(task)
        elif task_type == 'backtest':
            return self._backtest_strategy(task)
        elif task_type == 'ensemble':
            return self._generate_ensemble_signals(task)
        else:
            return {'status': 'error', 'message': f'Unknown task type: {task_type}'}
    
    def _generate_signals(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Generate trading signals."""
        analysis = task.get('analysis', {})
        data = task.get('data', {})
        regime = task.get('regime', 'unknown')
        
        signals = []
        signals_dict = {}
        
        for symbol, symbol_analysis in analysis.items():
            symbol_signals = []
            
            # Get technical signals
            technical_signal = self._generate_momentum_signal(symbol, symbol_analysis, data)
            if technical_signal:
                symbol_signals.append(technical_signal)
            
            mean_reversion_signal = self._generate_mean_reversion_signal(symbol, symbol_analysis, data)
            if mean_reversion_signal:
                symbol_signals.append(mean_reversion_signal)
            
            breakout_signal = self._generate_breakout_signal(symbol, symbol_analysis, data)
            if breakout_signal:
                symbol_signals.append(breakout_signal)
            
            # Adjust signals based on regime
            adjusted_signals = self._adjust_for_regime(symbol_signals, regime)
            
            if adjusted_signals:
                # Combine signals
                combined = self._combine_signals(symbol, adjusted_signals, data)
                if combined:
                    signals.append(combined)
                    signals_dict[symbol] = combined.to_dict()
        
        self.signal_history.extend(signals)
        
        return {
            'status': 'success',
            'signals': signals_dict,
            'count': len(signals),
            'regime': regime,
            'timestamp': datetime.now().isoformat()
        }
    
    def _generate_momentum_signal(self, symbol: str, analysis: Dict, 
                                  data: Dict) -> Optional[TradingSignal]:
        """Generate momentum-based signal."""
        if not self.active_strategies.get('momentum', {}).get('enabled', False):
            return None
        
        score = analysis.get('score', 0)
        recommendation = analysis.get('recommendation', 'HOLD')
        current_price = analysis.get('current_price', 0)
        
        if recommendation == 'BUY' and score > 0.3:
            config = self.active_strategies['momentum']
            stop_loss = current_price * (1 - config.get('exit_threshold', 0.02))
            take_profit = current_price * (1 + config.get('threshold', 0.05))
            
            return TradingSignal(
                symbol=symbol,
                direction=SignalDirection.BUY,
                confidence=min(abs(score), 1.0),
                entry_price=current_price,
                stop_loss=float(stop_loss),
                take_profit=float(take_profit),
                position_size=0.1,
                timestamp=datetime.now(),
                strategy='momentum',
                metadata={'score': score}
            )
        
        elif recommendation == 'SELL' and score < -0.3:
            config = self.active_strategies['momentum']
            stop_loss = current_price * (1 + config.get('exit_threshold', 0.02))
            take_profit = current_price * (1 - config.get('threshold', 0.05))
            
            return TradingSignal(
                symbol=symbol,
                direction=SignalDirection.SELL,
                confidence=min(abs(score), 1.0),
                entry_price=current_price,
                stop_loss=float(stop_loss),
                take_profit=float(take_profit),
                position_size=0.1,
                timestamp=datetime.now(),
                strategy='momentum',
                metadata={'score': score}
            )
        
        return None
    
    def _generate_mean_reversion_signal(self, symbol: str, analysis: Dict,
                                        data: Dict) -> Optional[TradingSignal]:
        """Generate mean reversion signal."""
        if not self.active_strategies.get('mean_reversion', {}).get('enabled', False):
            return None
        
        indicators = analysis.get('indicators', {})
        rsi = indicators.get('rsi', {}).get('value', 50)
        bb = indicators.get('bollinger', {})
        bb_position = bb.get('position', 0.5)
        current_price = analysis.get('current_price', 0)
        
        config = self.active_strategies['mean_reversion']
        
        # Buy when oversold
        if rsi < 30 or bb_position < 0.1:
            stop_loss = current_price * 0.95
            take_profit = current_price * 1.08
            
            return TradingSignal(
                symbol=symbol,
                direction=SignalDirection.BUY,
                confidence=0.7 if rsi < 30 else 0.6,
                entry_price=current_price,
                stop_loss=float(stop_loss),
                take_profit=float(take_profit),
                position_size=0.08,
                timestamp=datetime.now(),
                strategy='mean_reversion',
                metadata={'rsi': rsi, 'bb_position': bb_position}
            )
        
        # Sell when overbought
        elif rsi > 70 or bb_position > 0.9:
            stop_loss = current_price * 1.05
            take_profit = current_price * 0.92
            
            return TradingSignal(
                symbol=symbol,
                direction=SignalDirection.SELL,
                confidence=0.7 if rsi > 70 else 0.6,
                entry_price=current_price,
                stop_loss=float(stop_loss),
                take_profit=float(take_profit),
                position_size=0.08,
                timestamp=datetime.now(),
                strategy='mean_reversion',
                metadata={'rsi': rsi, 'bb_position': bb_position}
            )
        
        return None
    
    def _generate_breakout_signal(self, symbol: str, analysis: Dict,
                                  data: Dict) -> Optional[TradingSignal]:
        """Generate breakout signal."""
        if not self.active_strategies.get('breakout', {}).get('enabled', False):
            return None
        
        indicators = analysis.get('indicators', {})
        trend = indicators.get('trend', {})
        trend_signal = trend.get('signal', 'sideways')
        current_price = analysis.get('current_price', 0)
        volatility = indicators.get('volatility', {}).get('value', 1)
        
        config = self.active_strategies['breakout']
        
        # Buy on bullish breakout
        if trend_signal == 'bullish' and volatility > 1.5:
            stop_loss = current_price * 0.97
            take_profit = current_price * 1.12
            
            return TradingSignal(
                symbol=symbol,
                direction=SignalDirection.BUY,
                confidence=0.65,
                entry_price=current_price,
                stop_loss=float(stop_loss),
                take_profit=float(take_profit),
                position_size=0.12,
                timestamp=datetime.now(),
                strategy='breakout',
                metadata={'trend': trend_signal, 'volatility': volatility}
            )
        
        return None
    
    def _adjust_for_regime(self, signals: List[TradingSignal], 
                          regime: str) -> List[TradingSignal]:
        """Adjust signals based on market regime."""
        adjusted = []
        
        regime_modifiers = {
            'bull_boring': {'momentum': 1.2, 'mean_reversion': 0.8, 'breakout': 1.1},
            'bull_volatile': {'momentum': 1.1, 'mean_reversion': 1.2, 'breakout': 1.0},
            'bear_boring': {'momentum': 0.7, 'mean_reversion': 1.3, 'breakout': 0.5},
            'bear_volatile': {'momentum': 0.5, 'mean_reversion': 1.1, 'breakout': 0.3},
            'range_bound': {'momentum': 0.7, 'mean_reversion': 1.4, 'breakout': 0.6},
            'chop': {'momentum': 0.5, 'mean_reversion': 1.2, 'breakout': 0.4},
            'unknown': {'momentum': 1.0, 'mean_reversion': 1.0, 'breakout': 1.0}
        }
        
        modifiers = regime_modifiers.get(regime, regime_modifiers['unknown'])
        
        for signal in signals:
            modifier = modifiers.get(signal.strategy, 1.0)
            new_confidence = min(signal.confidence * modifier, 1.0)
            
            if new_confidence > 0.5:
                signal.confidence = new_confidence
                adjusted.append(signal)
        
        return adjusted
    
    def _combine_signals(self, symbol: str, signals: List[TradingSignal],
                        data: Dict) -> Optional[TradingSignal]:
        """Combine multiple signals into one."""
        if not signals:
            return None
        
        # Average position sizes
        avg_position = np.mean([s.position_size for s in signals])
        
        # Weighted average confidence
        total_confidence = sum(s.confidence for s in signals)
        
        # Determine direction by voting
        buy_votes = sum(1 for s in signals if s.direction == SignalDirection.BUY)
        sell_votes = sum(1 for s in signals if s.direction == SignalDirection.SELL)
        
        if buy_votes > sell_votes:
            direction = SignalDirection.BUY
        elif sell_votes > buy_votes:
            direction = SignalDirection.SELL
        else:
            return None  # No clear signal
        
        # Get price from first signal
        entry_price = signals[0].entry_price
        
        # Calculate average stop loss and take profit
        stop_losses = [s.stop_loss for s in signals]
        take_profits = [s.take_profit for s in signals]
        
        avg_stop_loss = np.mean(stop_losses)
        avg_take_profit = np.mean(take_profits)
        
        return TradingSignal(
            symbol=symbol,
            direction=direction,
            confidence=total_confidence / len(signals),
            entry_price=entry_price,
            stop_loss=float(avg_stop_loss),
            take_profit=float(avg_take_profit),
            position_size=float(avg_position),
            timestamp=datetime.now(),
            strategy='ensemble',
            metadata={'individual_signals': [s.strategy for s in signals]}
        )
    
    def _generate_ensemble_signals(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Generate ensemble signals combining multiple strategies."""
        # Similar to _generate_signals but with more sophisticated combination
        return self._generate_signals(task)
    
    def _optimize_strategy(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize strategy parameters."""
        strategy_name = task.get('strategy', 'momentum')
        data = task.get('data', {})
        objective = task.get('objective', 'sharpe')
        
        # Placeholder for optimization
        return {
            'status': 'success',
            'strategy': strategy_name,
            'optimized_parameters': self.active_strategies.get(strategy_name, {}),
            'objective': objective
        }
    
    def _backtest_strategy(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Backtest a strategy."""
        strategy = task.get('strategy', 'momentum')
        data = task.get('data', {})
        initial_capital = task.get('initial_capital', 100000)
        
        # Placeholder for backtesting
        return {
            'status': 'success',
            'strategy': strategy,
            'results': {
                'total_return': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 0.0
            }
        }
    
    def update_strategy_parameters(self, strategy_name: str, 
                                  parameters: Dict[str, Any]) -> bool:
        """Update strategy parameters."""
        if strategy_name in self.active_strategies:
            self.active_strategies[strategy_name].update(parameters)
            return True
        return False
    
    def get_active_strategies(self) -> Dict[str, Any]:
        """Get active strategies configuration."""
        return self.active_strategies
    
    def get_signal_history(self, symbol: str = None, 
                          limit: int = 100) -> List[Dict[str, Any]]:
        """Get signal history."""
        signals = self.signal_history
        
        if symbol:
            signals = [s for s in signals if s.symbol == symbol]
        
        signals = signals[-limit:]
        
        return [s.to_dict() for s in signals]
    
    def _process_message(self, message: AgentMessage) -> None:
        """Process incoming message."""
        if message.msg_type == MessageType.ANALYSIS_REQUEST:
            task = message.payload
            result = self.execute(task)
            
            response = AgentMessage(
                msg_type=MessageType.ANALYSIS_RESPONSE,
                sender_id=self.agent_id,
                receiver_id=message.sender_id,
                payload=result,
                priority=message.priority
            )
            self._deliver_message(response)
        
        elif message.msg_type == MessageType.TRADING_SIGNAL:
            # Forward trading signals to trader agent
            response = AgentMessage(
                msg_type=MessageType.TRADING_SIGNAL,
                sender_id=self.agent_id,
                receiver_id='trader_agent_001',
                payload=message.payload,
                priority=message.priority
            )
            self._deliver_message(response)
        
        elif message.msg_type == MessageType.HEARTBEAT:
            self.heartbeat()
            self.state = AgentState.RUNNING
