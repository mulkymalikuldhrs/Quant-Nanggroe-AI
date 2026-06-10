"""
⚡ QUANTA AI - Main Orchestrator
=================================
Central coordinator for all agents and trading operations.

Features:
- Agent lifecycle management
- Workflow orchestration
- Message routing
- Portfolio management
- System monitoring

Author: Quanta AI Team
Version: 2.0.0
"""

import threading
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from .config import QuantaConfig, get_config, MarketRegime
from ..agents.base import AgentCoordinator, AgentMessage, MessageType, BaseAgent
from ..agents.data_agent import DataAgent
from ..agents.analyst_agent import AnalystAgent
from ..agents.strategist_agent import StrategistAgent
from ..agents.risk_agent import RiskAgent
import pandas as pd
import numpy as np


class QuantaOrchestrator:
    """Main orchestrator for the Quanta AI trading system."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or get_config()
        self.coordinator = AgentCoordinator()
        self.agents: Dict[str, BaseAgent] = {}
        self.running = False
        self.heartbeat_thread = None
        self.execution_thread = None
        self.logger = self._setup_logging()
        self.portfolio_value = self.config.trading.initial_capital
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.trade_history: List[Dict[str, Any]] = []
        self.cumulative_pnl: List[float] = []
        self._lock = threading.Lock()
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger("QuantaOrchestrator")
        logger.setLevel(getattr(logging, self.config.log_level))
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s | Quanta | %(levelname)s | %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def initialize(self) -> bool:
        """Initialize the trading system."""
        self.logger.info("=" * 60)
        self.logger.info("⚡ QUANTA AI SYSTEM INITIALIZING")
        self.logger.info("=" * 60)
        
        try:
            # Create agents
            self._create_agents()
            
            # Register agents with coordinator
            self._register_agents()
            
            # Setup message routing
            self._setup_message_routing()
            
            self.logger.info("✅ Quanta AI initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _create_agents(self) -> None:
        """Create all agents."""
        self.agents = {
            'data_agent': DataAgent(),
            'analyst_agent': AnalystAgent(),
            'strategist_agent': StrategistAgent(),
            'risk_agent': RiskAgent(),
        }
        
        self.logger.info(f"Created {len(self.agents)} agents")
    
    def _register_agents(self) -> None:
        """Register agents with coordinator."""
        for agent_id, agent in self.agents.items():
            agent.initialize(self.config.__dict__ if hasattr(self.config, '__dict__') else {})
            self.coordinator.register_agent(agent)
        
        self.logger.info("All agents registered")
    
    def _setup_message_routing(self) -> None:
        """Setup message routing between agents."""
        # Data Agent handles data requests
        self.agents['data_agent'].subscribe(MessageType.DATA_REQUEST)
        
        # Analyst Agent handles analysis requests
        self.agents['analyst_agent'].subscribe(MessageType.ANALYSIS_REQUEST)
        
        # Strategist Agent handles strategy requests
        self.agents['strategist_agent'].subscribe(MessageType.ANALYSIS_REQUEST)
        
        # Risk Agent handles risk assessments
        self.agents['risk_agent'].subscribe(MessageType.RISK_ASSESSMENT)
        self.agents['risk_agent'].subscribe(MessageType.ORDER_REQUEST)
        
        self.logger.info("Message routing configured")
    
    def start(self) -> None:
        """Start the trading system."""
        if self.running:
            self.logger.warning("System already running")
            return
        
        self.running = True
        self.logger.info("🚀 Starting Quanta AI Trading System")
        self.logger.info("=" * 60)
        
        # Start all agents
        for agent in self.agents.values():
            agent.start()
        
        # Start heartbeat monitor
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        
        # Start main execution loop
        self.execution_thread = threading.Thread(target=self._execution_loop, daemon=True)
        self.execution_thread.start()
        
        self.logger.info("✅ Quanta AI Trading System Started")
    
    def stop(self) -> None:
        """Stop the trading system."""
        if not self.running:
            return
        
        self.running = False
        self.logger.info("🛑 Stopping Quanta AI...")
        
        # Stop all agents
        for agent in self.agents.values():
            agent.stop()
        
        # Shutdown coordinator
        self.coordinator.shutdown_all()
        
        self.logger.info("✅ Quanta AI Stopped")
    
    def _heartbeat_loop(self) -> None:
        """Heartbeat monitoring loop."""
        while self.running:
            try:
                # Send heartbeat to all agents
                heartbeat = AgentMessage(
                    msg_type=MessageType.HEARTBEAT,
                    sender_id='quanta_orchestrator',
                    receiver_id='broadcast',
                    payload={'timestamp': datetime.now().isoformat()}
                )
                self.coordinator.broadcast_message(heartbeat, MessageType.HEARTBEAT)
                
                time.sleep(self.config.agents.heartbeat_interval)
                
            except Exception as e:
                self.logger.error(f"Heartbeat error: {e}")
    
    def _execution_loop(self) -> None:
        """Main execution loop."""
        last_cycle = datetime.now()
        cycle_interval = 60  # 1 minute cycles
        
        while self.running:
            try:
                now = datetime.now()
                
                if (now - last_cycle).total_seconds() >= cycle_interval:
                    self._run_cycle()
                    last_cycle = now
                
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Execution loop error: {e}")
                time.sleep(5)
    
    def _run_cycle(self) -> None:
        """Run a trading cycle."""
        self.logger.info("🔄 Running trading cycle...")
        
        # Step 1: Collect data
        data = self._collect_data()
        
        # Step 2: Analyze
        analysis = self._analyze(data)
        
        # Step 3: Generate signals
        signals = self._generate_signals(analysis)
        
        # Step 4: Assess risk
        risk = self._assess_risk()
        
        # Step 5: Execute trades
        trades = self._execute_trades(signals, risk)
        
        # Step 6: Update portfolio
        self._update_portfolio()
        
        self.logger.info(f"✅ Cycle complete: {len(trades)} trades executed")
    
    def _collect_data(self) -> Dict[str, Any]:
        """Collect market data."""
        data_agent = self.agents['data_agent']
        
        # Default symbols
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'BTC-USD', 'ETH-USD']
        
        task = {
            'type': 'fetch',
            'symbols': symbols,
            'data_type': 'price',
            'period': '3mo',
            'interval': '1d'
        }
        
        result = data_agent.execute(task)
        
        # Generate features
        feature_task = {
            'type': 'feature',
            'data': result.get('data', {}),
            'features': 'all'
        }
        
        feature_result = data_agent.execute(feature_task)
        
        return {
            'raw_data': result.get('data', {}),
            'features': feature_result.get('features', {}),
            'symbols': symbols
        }
    
    def _analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market data."""
        analyst = self.agents['analyst_agent']
        
        # Technical analysis
        analysis_task = {
            'type': 'comprehensive',
            'data': data.get('features', {}),
            'symbols': data.get('symbols', [])
        }
        
        analysis_result = analyst.execute(analysis_task)
        
        # Regime detection
        regime_task = {
            'type': 'regime',
            'data': data.get('features', {}),
            'symbols': data.get('symbols', [])
        }
        
        regime_result = analyst.execute(regime_task)
        
        return {
            'technical': analysis_result.get('analysis', {}),
            'regimes': regime_result.get('regimes', {}),
            'symbols': data.get('symbols', [])
        }
    
    def _generate_signals(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate trading signals."""
        strategist = self.agents['strategist_agent']
        
        # Combine analysis
        combined_analysis = {}
        for symbol in analysis.get('symbols', []):
            tech = analysis.get('technical', {}).get(symbol, {})
            combined_analysis[symbol] = tech
        
        # Get dominant regime
        regimes = analysis.get('regimes', {})
        regime_counts = {}
        for symbol, reg_data in regimes.items():
            regime = reg_data.get('regime', 'unknown')
            regime_counts[regime] = regime_counts.get(regime, 0) + 1
        
        dominant_regime = max(regime_counts, key=regime_counts.get) if regime_counts else 'unknown'
        
        signal_task = {
            'type': 'generate',
            'analysis': combined_analysis,
            'regime': dominant_regime,
            'portfolio_value': self.portfolio_value,
            'data': analysis.get('technical', {})
        }
        
        result = strategist.execute(signal_task)
        
        return result.get('signals', {})
    
    def _assess_risk(self) -> Dict[str, Any]:
        """Assess portfolio risk."""
        risk_agent = self.agents['risk_agent']
        
        # Get positions
        positions_list = list(self.positions.values())
        
        # Generate simulated P&L history
        historical_pnl = self.cumulative_pnl[-30:] if len(self.cumulative_pnl) >= 30 else []
        if len(historical_pnl) < 30:
            historical_pnl = list(np.random.normal(0, self.portfolio_value * 0.01, 30))
        
        risk_task = {
            'type': 'assess',
            'positions': positions_list,
            'historical_pnl': historical_pnl
        }
        
        result = risk_agent.execute(risk_task)
        
        return result
    
    def _execute_trades(self, signals: Dict[str, Any], 
                       risk: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute trades based on signals."""
        trades = []
        
        risk_metrics = risk.get('risk_metrics', {})
        risk_level = risk_metrics.get('overall_risk_level', 'medium')
        
        # Skip trading if risk is critical
        if risk_level == 'critical':
            self.logger.warning("⚠️  Skipping trades - Risk level CRITICAL")
            return trades
        
        for symbol, signal in signals.items():
            direction = signal.get('direction', 0)
            
            if direction == 0 or abs(direction) < 1:
                continue  # No clear signal
            
            # Validate trade with risk
            trade = {
                'symbol': symbol,
                'side': 'buy' if direction > 0 else 'sell',
                'size': signal.get('position_size', 0.1),
                'price': signal.get('entry_price', 100)
            }
            
            validation = self._validate_trade(trade)
            
            if validation.get('passed', False):
                # Execute trade (simulated)
                trade_result = self._simulate_trade(trade)
                if trade_result:
                    trades.append(trade_result)
                    
                    # Update portfolio
                    self._apply_trade(trade_result)
            
        return trades
    
    def _validate_trade(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a trade."""
        risk_agent = self.agents['risk_agent']
        
        task = {
            'type': 'validate_trade',
            'trade': trade,
            'positions': list(self.positions.values()),
            'portfolio_value': self.portfolio_value
        }
        
        return risk_agent.execute(task)
    
    def _simulate_trade(self, trade: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Simulate trade execution."""
        symbol = trade.get('symbol', '')
        side = trade.get('side', 'buy')
        size = trade.get('size', 0.1)
        price = trade.get('price', 100)
        
        # Calculate trade value
        trade_value = self.portfolio_value * size
        
        # Simulate execution (with spread)
        spread = price * 0.001  # 0.1% spread
        if side == 'buy':
            fill_price = price + spread
        else:
            fill_price = price - spread
        
        # Calculate commission
        commission = trade_value * self.config.trading.transaction_cost
        
        return {
            'symbol': symbol,
            'side': side,
            'quantity': trade_value / fill_price,
            'entry_price': fill_price,
            'commission': commission,
            'timestamp': datetime.now().isoformat()
        }
    
    def _apply_trade(self, trade: Dict[str, Any]) -> None:
        """Apply trade to portfolio."""
        symbol = trade.get('symbol', '')
        side = trade.get('side', 'buy')
        quantity = trade.get('quantity', 0)
        price = trade.get('entry_price', 0)
        
        with self._lock:
            if symbol not in self.positions:
                self.positions[symbol] = {
                    'symbol': symbol,
                    'quantity': 0,
                    'avg_price': 0,
                    'market_value': 0,
                    'unrealized_pnl': 0,
                    'weight': 0
                }
            
            position = self.positions[symbol]
            
            if side == 'buy':
                total_cost = position['quantity'] * position['avg_price'] + quantity * price
                total_qty = position['quantity'] + quantity
                position['avg_price'] = total_cost / total_qty if total_qty > 0 else 0
                position['quantity'] = total_qty
            else:
                realized_pnl = (price - position['avg_price']) * quantity
                position['quantity'] -= quantity
                
                if position['quantity'] < 0.01:
                    del self.positions[symbol]
            
            # Update trade history
            self.trade_history.append(trade)
            
            self.logger.info(f"Trade applied: {side} {quantity:.2f} {symbol} @ {price:.2f}")
    
    def _update_portfolio(self) -> None:
        """Update portfolio values."""
        total_value = 0
        
        for symbol, position in self.positions.items():
            quantity = position['quantity']
            avg_price = position['avg_price']
            
            # Simulate current price (would fetch from market)
            current_price = avg_price * (1 + np.random.uniform(-0.01, 0.01))
            
            market_value = quantity * current_price
            unrealized_pnl = (current_price - avg_price) * quantity
            
            position['market_value'] = market_value
            position['unrealized_pnl'] = unrealized_pnl
            position['current_price'] = current_price
            
            total_value += market_value
        
        # Add cash component
        cash = self.config.trading.initial_capital
        for trade in self.trade_history[-100:]:
            if trade.get('side') == 'sell':
                cash += trade.get('entry_price', 0) * trade.get('quantity', 0)
            else:
                cash -= trade.get('entry_price', 0) * trade.get('quantity', 0)
        
        total_value += cash
        
        # Update portfolio value
        self.portfolio_value = total_value
        
        # Update cumulative P&L
        initial = self.config.trading.initial_capital
        cumulative = (total_value - initial) / initial
        self.cumulative_pnl.append(cumulative)
    
    def run_once(self, symbols: List[str] = None) -> Dict[str, Any]:
        """Run a single analysis cycle."""
        if symbols is None:
            symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
        
        self.logger.info(f"🔍 Running analysis for {symbols}")
        
        # Collect data
        data = self._collect_data()
        
        # Analyze
        analysis = self._analyze(data)
        
        # Generate signals
        signals = self._generate_signals(analysis)
        
        # Assess risk
        risk = self._assess_risk()
        
        # Get positions
        positions = list(self.positions.values())
        
        return {
            'timestamp': datetime.now().isoformat(),
            'symbols_analyzed': len(data.get('symbols', [])),
            'signals_generated': len(signals),
            'risk_metrics': risk.get('risk_metrics', {}),
            'active_positions': len(positions),
            'portfolio_value': self.portfolio_value,
            'signals': signals
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get system status."""
        agent_status = self.coordinator.get_all_agents()
        coordinator_stats = self.coordinator.get_coordinator_stats()
        
        return {
            'running': self.running,
            'agents': agent_status,
            'coordinator': coordinator_stats,
            'portfolio_value': self.portfolio_value,
            'positions_count': len(self.positions),
            'trade_history_count': len(self.trade_history)
        }
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary."""
        positions = list(self.positions.values())
        
        total_market_value = sum(p.get('market_value', 0) for p in positions)
        total_unrealized = sum(p.get('unrealized_pnl', 0) for p in positions)
        
        return {
            'positions': positions,
            'total_market_value': total_market_value,
            'total_unrealized_pnl': total_unrealized,
            'position_count': len(positions),
            'portfolio_value': self.portfolio_value
        }
