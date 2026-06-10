"""
⚡ QUANTA AI - Strategist Agent
================================
Advanced strategy generation and signal production with
ensemble methods and adaptive optimization.

Features:
- Multi-strategy signal generation
- Ensemble combination
- Regime-adaptive positioning
- Risk-adjusted sizing
- Strategy optimization

Author: Quanta AI Team
Version: 2.0.0
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from scipy.optimize import minimize, differential_evolution
from .base import BaseAgent, AgentMessage, MessageType, AgentState, AgentType
import logging


class SignalDirection(Enum):
    """Trading signal directions."""
    STRONG_BUY = 2
    BUY = 1
    HOLD = 0
    SELL = -1
    STRONG_SELL = -2


class StrategyType(Enum):
    """Strategy types."""
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    TREND_FOLLOWING = "trend_following"
    GRID_TRADING = "grid_trading"
    PAIRS = "pairs"
    SCALPING = "scalping"
    SWING = "swing"
    ENSEMBLE = "ensemble"


@dataclass
class TradingSignal:
    """Trading signal with full details."""
    symbol: str
    direction: SignalDirection
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    timestamp: datetime
    strategy: str
    risk_reward_ratio: float = 2.0
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'direction': self.direction.value,
            'direction_name': self.direction.name,
            'confidence': float(self.confidence),
            'entry_price': float(self.entry_price),
            'stop_loss': float(self.stop_loss),
            'take_profit': float(self.take_profit),
            'position_size': float(self.position_size),
            'timestamp': self.timestamp.isoformat(),
            'strategy': self.strategy,
            'risk_reward_ratio': float(self.risk_reward_ratio),
            'metadata': self.metadata or {}
        }


class StrategistAgent(BaseAgent):
    """Agent responsible for generating and optimizing trading strategies."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(
            agent_id="quanta_strategy_001",
            name="Strategist",
            agent_type=AgentType.STRATEGIC
        )
        self.capabilities = [
            "signal_generation",
            "strategy_optimization",
            "parameter_tuning",
            "ensemble_combination",
            "risk_adjusted_positioning",
            "regime_adaptation"
        ]
        self.config = config or {}
        self.active_strategies: Dict[str, Dict[str, Any]] = {}
        self.signal_history: List[TradingSignal] = []
        self.strategy_performance: Dict[str, Dict[str, float]] = {}
        
    def _initialize_impl(self) -> bool:
        """Initialize strategist agent."""
        self.logger.info("Strategist initializing...")
        self.subscribe(MessageType.ANALYSIS_REQUEST)
        self._setup_default_strategies()
        self.logger.info("Strategist initialized")
        return True
    
    def _setup_default_strategies(self) -> None:
        """Setup default strategy configurations."""
        self.active_strategies = {
            'momentum': {
                'enabled': True,
                'lookback_period': 20,
                'threshold': 0.03,
                'exit_threshold': -0.02,
                'max_hold_days': 30,
                'min_confidence': 0.5,
                'weight': 0.25
            },
            'mean_reversion': {
                'enabled': True,
                'lookback_period': 20,
                'std_deviations': 2.0,
                'exit_threshold': 0.5,
                'zscore_entry': -2.0,
                'zscore_exit': 0.0,
                'min_confidence': 0.5,
                'weight': 0.25
            },
            'breakout': {
                'enabled': True,
                'breakout_period': 20,
                'volume_multiplier': 1.5,
                'confirmation_bars': 2,
                'min_confidence': 0.55,
                'weight': 0.20
            },
            'trend_following': {
                'enabled': True,
                'fast_ema': 12,
                'slow_ema': 26,
                'signal_ema': 9,
                'adx_threshold': 25,
                'min_confidence': 0.5,
                'weight': 0.20
            },
            'grid_trading': {
                'enabled': True,
                'grid_levels': 10,
                'grid_spacing': 0.02,
                'take_profit_grid': 0.01,
                'min_confidence': 0.4,
                'weight': 0.10
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
        elif task_type == 'adapt':
            return self._adapt_to_regime(task)
        elif task_type == 'performance':
            return self._get_strategy_performance(task)
        else:
            return {
                'status': 'error',
                'message': f'Unknown task type: {task_type}',
                'task_type': task_type
            }
    
    def _generate_signals(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Generate trading signals from analysis."""
        analysis = task.get('analysis', {})
        data = task.get('data', {})
        regime = task.get('regime', 'unknown')
        portfolio_value = task.get('portfolio_value', 100000)
        risk_tolerance = task.get('risk_tolerance', 0.02)
        
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
            
            trend_signal = self._generate_trend_signal(symbol, symbol_analysis, data)
            if trend_signal:
                symbol_signals.append(trend_signal)
            
            # Adjust signals based on regime
            adjusted_signals = self._adjust_for_regime(symbol_signals, regime)
            
            if adjusted_signals:
                # Combine signals with weights
                combined = self._combine_signals(symbol, adjusted_signals, data, portfolio_value, risk_tolerance)
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
        
        config = self.active_strategies['momentum']
        scores = analysis.get('scores', {})
        
        # Get key indicators
        trend_score = scores.get('trend', 0)
        rsi = analysis.get('indicators', {}).get('rsi', {}).get('value', 50)
        macd_score = scores.get('macd', 0)
        
        # Calculate momentum score
        momentum_score = (trend_score * 0.4 + macd_score * 0.3 + 
                         (1 - rsi/100) * 0.3 if rsi > 50 else rsi/100 * 0.3)
        
        if momentum_score < config.get('min_confidence', 0.5):
            return None
        
        current_price = analysis.get('current_price', 0)
        
        if momentum_score > 0.3:
            direction = SignalDirection.BUY
        elif momentum_score < -0.3:
            direction = SignalDirection.SELL
        else:
            return None
        
        stop_loss_pct = config.get('exit_threshold', 0.02)
        take_profit_pct = config.get('threshold', 0.03)
        
        if direction == SignalDirection.BUY:
            stop_loss = current_price * (1 - stop_loss_pct)
            take_profit = current_price * (1 + take_profit_pct)
        else:
            stop_loss = current_price * (1 + stop_loss_pct)
            take_profit = current_price * (1 - take_profit_pct)
        
        return TradingSignal(
            symbol=symbol,
            direction=direction,
            confidence=min(abs(momentum_score), 1.0),
            entry_price=current_price,
            stop_loss=float(stop_loss),
            take_profit=float(take_profit),
            position_size=0.1,
            timestamp=datetime.now(),
            strategy='momentum',
            metadata={'momentum_score': momentum_score, **config}
        )
    
    def _generate_mean_reversion_signal(self, symbol: str, analysis: Dict,
                                        data: Dict) -> Optional[TradingSignal]:
        """Generate mean reversion signal."""
        if not self.active_strategies.get('mean_reversion', {}).get('enabled', False):
            return None
        
        config = self.active_strategies['mean_reversion']
        indicators = analysis.get('indicators', {})
        
        rsi = indicators.get('rsi', {}).get('value', 50)
        bb = indicators.get('bollinger', {})
        bb_position = bb.get('position', 0.5)
        current_price = analysis.get('current_price', 0)
        
        # Mean reversion score
        if rsi < 30 or bb_position < 0.1:
            direction = SignalDirection.BUY
            confidence = 0.7 if rsi < 30 else 0.6
        elif rsi > 70 or bb_position > 0.9:
            direction = SignalDirection.SELL
            confidence = 0.7 if rsi > 70 else 0.6
        else:
            return None
        
        stop_loss_pct = config.get('exit_threshold', 0.05)
        take_profit_pct = config.get('std_deviations', 2.0) * 0.01
        
        if direction == SignalDirection.BUY:
            stop_loss = current_price * (1 - stop_loss_pct)
            take_profit = current_price * (1 + take_profit_pct)
        else:
            stop_loss = current_price * (1 + stop_loss_pct)
            take_profit = current_price * (1 - take_profit_pct)
        
        return TradingSignal(
            symbol=symbol,
            direction=direction,
            confidence=confidence,
            entry_price=current_price,
            stop_loss=float(stop_loss),
            take_profit=float(take_profit),
            position_size=0.08,
            timestamp=datetime.now(),
            strategy='mean_reversion',
            metadata={'rsi': rsi, 'bb_position': bb_position, **config}
        )
    
    def _generate_breakout_signal(self, symbol: str, analysis: Dict,
                                  data: Dict) -> Optional[TradingSignal]:
        """Generate breakout signal."""
        if not self.active_strategies.get('breakout', {}).get('enabled', False):
            return None
        
        config = self.active_strategies['breakout']
        indicators = analysis.get('indicators', {})
        trend = indicators.get('trend', {})
        volume = indicators.get('volume', {})
        
        # Check for breakout conditions
        trend_signal = trend.get('signal', 'sideways')
        vol_ratio = volume.get('ratio', 1)
        
        if trend_signal == 'bullish' and vol_ratio > config.get('volume_multiplier', 1.5):
            direction = SignalDirection.BUY
            confidence = 0.65 * min(vol_ratio / 2, 1)
        elif trend_signal == 'bearish' and vol_ratio > config.get('volume_multiplier', 1.5):
            direction = SignalDirection.SELL
            confidence = 0.65 * min(vol_ratio / 2, 1)
        else:
            return None
        
        current_price = analysis.get('current_price', 0)
        sr = indicators.get('support_resistance', {})
        resistance = sr.get('resistance', [current_price * 1.05])[0] if direction == SignalDirection.BUY else current_price
        support = sr.get('support', [current_price * 0.95])[0] if direction == SignalDirection.SELL else current_price
        
        return TradingSignal(
            symbol=symbol,
            direction=direction,
            confidence=confidence,
            entry_price=current_price,
            stop_loss=float(support),
            take_profit=float(resistance),
            position_size=0.12,
            timestamp=datetime.now(),
            strategy='breakout',
            metadata={'trend': trend_signal, 'volume_ratio': vol_ratio, **config}
        )
    
    def _generate_trend_signal(self, symbol: str, analysis: Dict,
                              data: Dict) -> Optional[TradingSignal]:
        """Generate trend following signal."""
        if not self.active_strategies.get('trend_following', {}).get('enabled', False):
            return None
        
        config = self.active_strategies['trend_following']
        indicators = analysis.get('indicators', {})
        
        macd = indicators.get('macd', {})
        adx = indicators.get('adx', {}).get('value', 0)
        trend = indicators.get('trend', {})
        
        # Check trend conditions
        macd_hist = macd.get('histogram', 0)
        trend_signal = trend.get('signal', 'sideways')
        adx_value = adx if isinstance(adx, (int, float)) else indicators.get('adx', {}).get('value', 0)
        
        if adx_value < config.get('adx_threshold', 25):
            return None  # Not trending
        
        if macd_hist > 0 and trend_signal in ['bullish', 'strong_bullish']:
            direction = SignalDirection.BUY
            confidence = min(adx_value / 100 + 0.3, 0.85)
        elif macd_hist < 0 and trend_signal in ['bearish', 'strong_bearish']:
            direction = SignalDirection.SELL
            confidence = min(adx_value / 100 + 0.3, 0.85)
        else:
            return None
        
        current_price = analysis.get('current_price', 0)
        stop_loss_pct = 0.03
        
        if direction == SignalDirection.BUY:
            stop_loss = current_price * (1 - stop_loss_pct)
            take_profit = current_price * (1 + stop_loss_pct * 2)
        else:
            stop_loss = current_price * (1 + stop_loss_pct)
            take_profit = current_price * (1 - stop_loss_pct * 2)
        
        return TradingSignal(
            symbol=symbol,
            direction=direction,
            confidence=confidence,
            entry_price=current_price,
            stop_loss=float(stop_loss),
            take_profit=float(take_profit),
            position_size=0.15,
            timestamp=datetime.now(),
            strategy='trend_following',
            metadata={'adx': adx_value, 'trend': trend_signal, **config}
        )
    
    def _adjust_for_regime(self, signals: List[TradingSignal],
                          regime: str) -> List[TradingSignal]:
        """Adjust signals based on market regime."""
        adjusted = []
        
        regime_modifiers = {
            'bull_calm': {'momentum': 1.2, 'mean_reversion': 0.7, 'breakout': 1.1, 'trend_following': 1.3},
            'bull_normal': {'momentum': 1.1, 'mean_reversion': 0.8, 'breakout': 1.0, 'trend_following': 1.1},
            'bull_volatile': {'momentum': 1.0, 'mean_reversion': 1.2, 'breakout': 1.2, 'trend_following': 0.8},
            'bear_calm': {'momentum': 0.6, 'mean_reversion': 1.4, 'breakout': 0.4, 'trend_following': 0.5},
            'bear_normal': {'momentum': 0.5, 'mean_reversion': 1.3, 'breakout': 0.3, 'trend_following': 0.4},
            'bear_volatile': {'momentum': 0.4, 'mean_reversion': 1.1, 'breakout': 0.2, 'trend_following': 0.3},
            'range_calm': {'momentum': 0.6, 'mean_reversion': 1.5, 'breakout': 0.5, 'trend_following': 0.4},
            'range_chop': {'momentum': 0.4, 'mean_reversion': 1.2, 'breakout': 0.3, 'trend_following': 0.3},
            'unknown': {'momentum': 1.0, 'mean_reversion': 1.0, 'breakout': 1.0, 'trend_following': 1.0}
        }
        
        modifiers = regime_modifiers.get(regime, regime_modifiers['unknown'])
        
        for signal in signals:
            modifier = modifiers.get(signal.strategy, 1.0)
            new_confidence = min(signal.confidence * modifier, 1.0)
            
            # Adjust position size based on regime
            base_size = signal.position_size
            adjusted_size = base_size * modifier
            
            if new_confidence > 0.4:
                signal.confidence = new_confidence
                signal.position_size = min(adjusted_size, 0.20)  # Max 20%
                adjusted.append(signal)
        
        return adjusted
    
    def _combine_signals(self, symbol: str, signals: List[TradingSignal],
                        data: Dict, portfolio_value: float, 
                        risk_tolerance: float) -> Optional[TradingSignal]:
        """Combine multiple signals into one."""
        if not signals:
            return None
        
        # Weight by strategy weights
        total_weight = 0
        weighted_direction = 0
        weighted_confidence = 0
        total_size = 0
        
        for signal in signals:
            strategy_config = self.active_strategies.get(signal.strategy, {})
            weight = strategy_config.get('weight', 0.2)
            
            weighted_direction += signal.direction.value * weight
            weighted_confidence += signal.confidence * weight
            total_size += signal.position_size * weight
            total_weight += weight
        
        if total_weight == 0:
            return None
        
        avg_direction = weighted_direction / total_weight
        avg_confidence = weighted_confidence / total_weight
        avg_size = total_size / total_weight
        
        # Determine final direction
        if avg_direction > 0.3:
            direction = SignalDirection.BUY
        elif avg_direction > 0.1:
            direction = SignalDirection.BUY
        elif avg_direction < -0.3:
            direction = SignalDirection.SELL
        elif avg_direction < -0.1:
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
        
        # Risk-adjusted sizing
        risk_per_trade = portfolio_value * risk_tolerance
        risk_amount = abs(entry_price - avg_stop_loss)
        if risk_amount > 0:
            position_size = min(risk_per_trade / risk_amount, avg_size)
        else:
            position_size = avg_size
        
        return TradingSignal(
            symbol=symbol,
            direction=direction,
            confidence=avg_confidence,
            entry_price=entry_price,
            stop_loss=float(avg_stop_loss),
            take_profit=float(avg_take_profit),
            position_size=float(min(position_size, 0.20)),
            timestamp=datetime.now(),
            strategy='ensemble',
            metadata={
                'individual_signals': [s.strategy for s in signals],
                'regime_adjusted': True
            }
        )
    
    def _generate_ensemble_signals(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Generate ensemble signals with advanced combination."""
        # Similar to _generate_signals but with more sophisticated combination
        return self._generate_signals(task)
    
    def _optimize_strategy(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize strategy parameters."""
        strategy_name = task.get('strategy', 'momentum')
        data = task.get('data', {})
        objective = task.get('objective', 'sharpe')
        
        if strategy_name not in self.active_strategies:
            return {
                'status': 'error',
                'message': f'Unknown strategy: {strategy_name}'
            }
        
        # Simplified optimization - would use backtesting data
        current_params = self.active_strategies[strategy_name]
        
        return {
            'status': 'success',
            'strategy': strategy_name,
            'current_parameters': current_params,
            'optimized_parameters': current_params,  # Would be optimized
            'objective': objective,
            'note': 'Full optimization requires historical backtesting data'
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
                'win_rate': 0.0,
                'profit_factor': 0.0
            },
            'note': 'Full backtesting engine coming soon'
        }
    
    def _adapt_to_regime(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt strategies to current regime."""
        regime = task.get('regime', 'unknown')
        
        regime_adaptations = {
            'bull_calm': {
                'momentum': {'weight': 0.30, 'threshold': 0.025},
                'mean_reversion': {'weight': 0.15, 'threshold': 0.6},
                'breakout': {'weight': 0.25, 'volume_multiplier': 1.3},
                'trend_following': {'weight': 0.30, 'adx_threshold': 20}
            },
            'bull_volatile': {
                'momentum': {'weight': 0.20, 'threshold': 0.035},
                'mean_reversion': {'weight': 0.35, 'threshold': 0.4},
                'breakout': {'weight': 0.25, 'volume_multiplier': 1.8},
                'trend_following': {'weight': 0.20, 'adx_threshold': 30}
            },
            'bear_volatile': {
                'momentum': {'weight': 0.10, 'threshold': 0.04},
                'mean_reversion': {'weight': 0.40, 'threshold': 0.3},
                'breakout': {'weight': 0.10, 'volume_multiplier': 2.0},
                'trend_following': {'weight': 0.10, 'adx_threshold': 35}
            },
            'range_calm': {
                'momentum': {'weight': 0.15, 'threshold': 0.03},
                'mean_reversion': {'weight': 0.45, 'threshold': 0.2},
                'breakout': {'weight': 0.15, 'volume_multiplier': 1.2},
                'trend_following': {'weight': 0.10, 'adx_threshold': 25}
            }
        }
        
        adaptations = regime_adaptations.get(regime, {})
        
        # Apply adaptations
        for strategy, params in adaptations.items():
            if strategy in self.active_strategies:
                self.active_strategies[strategy].update(params)
        
        return {
            'status': 'success',
            'regime': regime,
            'adaptations': adaptations,
            'updated_strategies': list(adaptations.keys()),
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_strategy_performance(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Get strategy performance metrics."""
        strategy = task.get('strategy', None)
        
        if strategy:
            return {
                'status': 'success',
                'performance': self.strategy_performance.get(strategy, {
                    'total_return': 0,
                    'sharpe_ratio': 0,
                    'win_rate': 0,
                    'max_drawdown': 0
                })
            }
        
        return {
            'status': 'success',
            'performance': self.strategy_performance,
            'active_strategies': list(self.active_strategies.keys())
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
    
    def _process_message(self, message: AgentMessage) -> bool:
        """Process incoming message."""
        if message.msg_type == MessageType.ANALYSIS_REQUEST:
            task = message.payload
            result = self.execute(task)
            
            response = AgentMessage(
                msg_type=MessageType.ANALYSIS_RESPONSE,
                sender_id=self.agent_id,
                receiver_id=message.sender_id,
                payload=result,
                priority=message.priority,
                correlation_id=message.correlation_id
            )
            return self.send_message(response)
        
        elif message.msg_type == MessageType.SIGNAL_GENERATED:
            # Forward signals to trader
            response = AgentMessage(
                msg_type=MessageType.SIGNAL_GENERATED,
                sender_id=self.agent_id,
                receiver_id='quanta_trader_001',
                payload=message.payload,
                priority=message.priority
            )
            return self.send_message(response)
        
        elif message.msg_type == MessageType.HEARTBEAT:
            self.heartbeat()
            self.state = AgentState.RUNNING
        
        return True
