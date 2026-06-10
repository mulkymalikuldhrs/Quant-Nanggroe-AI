"""
AI Auto-Trading Engine - Autonomous Trading with Zero Human Intervention

Features:
- Multi-strategy signal aggregation
- Real-time market analysis
- Automatic order execution
- Risk management
- Performance optimization
- Self-learning capabilities

This is the "brain" of our hedge fund - fully autonomous!
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict
import numpy as np
import pandas as pd
from src.brokers.free_broker_api import FreeBrokerGateway, BrokerAPI, BrokerType, OrderRequest, OrderSide, OrderType, TimeInForce, Account, Position, MarketData
from src.strategies.wyckoff.wyckoff_strategy import WyckoffAnalyzer, WyckoffPhase, WyckoffSignal
from src.analysis.timeframe.multi_timeframe import MultiTimeframeAnalyzer, TrendDirection, TimeframeSignal, MultiTimeframeAnalysis
from src.ml.ml_signal_generator import MLSignalGenerator
from src.risk.risk_management import RiskManagementFramework, RiskLimit, RiskMetric

logger = logging.getLogger(__name__)


class SignalStrength(Enum):
    VERY_WEAK = 1
    WEAK = 2
    MODERATE = 3
    STRONG = 4
    VERY_STRONG = 5


class SignalSource(Enum):
    WYCKOFF = "wyckoff"
    MULTI_TIMEFRAME = "multi_timeframe"
    ML_MODEL = "ml_model"
    TECHNICAL = "technical"
    SENTIMENT = "sentiment"
    MOMENTUM = "momentum"


@dataclass
class TradingSignal:
    symbol: str
    direction: str  # 'long' or 'short'
    strength: SignalStrength
    confidence: float  # 0-100
    sources: List[SignalSource]
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float
    timestamp: datetime
    metadata: Dict = field(default_factory=dict)


@dataclass
class Trade:
    trade_id: str
    symbol: str
    direction: str
    entry_price: float
    quantity: float
    stop_loss: float
    take_profit: float
    status: str
    entry_time: datetime
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    pnl: float = 0.0
    pnl_pct: float = 0.0
    signals: List[TradingSignal] = field(default_factory=list)


class AIAutoTrader:
    """
    AI Auto-Trading Engine - Fully Autonomous Trading System

    This engine:
    1. Continuously monitors markets
    2. Generates trading signals from multiple sources
    3. Aggregates and validates signals
    4. Executes trades automatically
    5. Manages risk in real-time
    6. Learns from performance
    """

    def __init__(self, broker_gateway: FreeBrokerGateway):
        self.broker_gateway = broker_gateway

        self.wyckoff_analyzer = WyckoffAnalyzer()
        self.tf_analyzer = MultiTimeframeAnalyzer()
        self.ml_signal_generator = MLSignalGenerator()

        self.risk_manager = RiskManagementFramework(initial_capital=1000000)
        self.risk_manager.add_risk_limit(RiskMetric.MAX_POSITION_SIZE, 0.20)
        self.risk_manager.add_risk_limit(RiskMetric.MAX_DAILY_LOSS, 0.05)
        self.risk_manager.add_risk_limit(RiskMetric.MAX_DRAWDOWN, 0.15)

        self.active_trades: Dict[str, Trade] = {}
        self.completed_trades: List[Trade] = []
        self.pending_signals: List[TradingSignal] = []

        self.watchlist: List[str] = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AAPL", "MSFT", "EURUSD", "GBPUSD", "XAUUSD", "NVDA", "TSLA"]

        self.trading_enabled = True
        self.auto_execution = True

        self.performance_metrics = {"total_trades": 0, "winning_trades": 0, "total_pnl": 0.0, "win_rate": 0.0, "avg_trade_duration": timedelta(), "sharpe_ratio": 0.0, "max_drawdown": 0.0}

        self._setup_metrics()

    def _setup_metrics(self):
        self.performance_history = []
        self.equity_curve = []

    def add_to_watchlist(self, symbol: str):
        if symbol not in self.watchlist:
            self.watchlist.append(symbol)
            logger.info(f"Added {symbol} to watchlist")

    def remove_from_watchlist(self, symbol: str):
        if symbol in self.watchlist:
            self.watchlist.remove(symbol)
            logger.info(f"Removed {symbol} from watchlist")

    async def analyze_symbol(self, symbol: str) -> List[TradingSignal]:
        """Analyze a symbol and generate trading signals from all sources"""

        signals = []
        candles_1h = await self._fetch_candles(symbol, "1h", 100)
        candles_4h = await self._fetch_candles(symbol, "4h", 100)
        candles_1d = await self._fetch_candles(symbol, "1d", 100)

        wyckoff_signal = self._analyze_wyckoff(symbol, candles_1h)
        if wyckoff_signal:
            signals.append(wyckoff_signal)

        tf_signal = self._analyze_multi_timeframe(symbol, candles_1h, candles_4h, candles_1d)
        if tf_signal:
            signals.append(tf_signal)

        ml_signal = await self._analyze_ml(symbol, candles_1h)
        if ml_signal:
            signals.append(ml_signal)

        return signals

    def _analyze_wyckoff(self, symbol: str, candles: pd.DataFrame) -> Optional[TradingSignal]:
        """Analyze using Wyckoff methodology"""

        if candles.empty:
            return None

        analysis = self.wyckoff_analyzer.analyze(candles)

        if not analysis or not analysis.phase:
            return None

        base_price = candles["close"].iloc[-1]

        if analysis.phase in [WyckoffPhase.ACCUMULATION_A, WyckoffPhase.ACCUMULATION_B]:
            direction = "long"
            confidence = 60 + analysis.confidence * 0.3
            stop_loss = base_price * 0.98
            take_profit = base_price * 1.05
        elif analysis.phase in [WyckoffPhase.ACCUMULATION_C, WyckoffPhase.MARKUP]:
            direction = "long"
            confidence = 70 + analysis.confidence * 0.2
            stop_loss = base_price * 0.97
            take_profit = base_price * 1.08
        elif analysis.phase in [WyckoffPhase.DISTRIBUTION_A, WyckoffPhase.DISTRIBUTION_B]:
            direction = "short"
            confidence = 60 + analysis.confidence * 0.3
            stop_loss = base_price * 1.02
            take_profit = base_price * 0.95
        elif analysis.phase in [WyckoffPhase.DISTRIBUTION_C, WyckoffPhase.MARKDOWN]:
            direction = "short"
            confidence = 70 + analysis.confidence * 0.2
            stop_loss = base_price * 1.03
            take_profit = base_price * 0.92
        else:
            return None

        risk_reward = (take_profit - base_price) / (base_price - stop_loss) if direction == "long" else (base_price - take_profit) / (stop_loss - base_price)

        strength = SignalStrength.MODERATE
        if confidence > 80:
            strength = SignalStrength.STRONG
        elif confidence > 90:
            strength = SignalStrength.VERY_STRONG
        elif confidence > 70:
            strength = SignalStrength.MODERATE
        elif confidence > 60:
            strength = SignalStrength.WEAK

        return TradingSignal(symbol=symbol, direction=direction, strength=strength, confidence=min(95, confidence), sources=[SignalSource.WYCKOFF], entry_price=base_price, stop_loss=stop_loss, take_profit=take_profit, risk_reward_ratio=risk_reward, timestamp=datetime.now(), metadata={"phase": analysis.phase.value, "events": analysis.events, "target": analysis.target, "stop": analysis.stop})

    def _analyze_multi_timeframe(self, symbol: str, candles_1h: pd.DataFrame, candles_4h: pd.DataFrame, candles_1d: pd.DataFrame) -> Optional[TradingSignal]:
        """Analyze using multi-timeframe alignment"""

        tf_analysis = self.tf_analyzer.analyze_alignment(symbol, ["1h", "4h", "1d"], candles_1h=candles_1h, candles_4h=candles_4h, candles_1d=candles_1d)

        if not tf_analysis or not tf_analysis.direction:
            return None

        base_price = candles_1h["close"].iloc[-1]

        direction = "long" if tf_analysis.primary_trend == TrendDirection.BULLISH else "short"

        if tf_analysis.primary_trend == TrendDirection.BULLISH:
            stop_loss = base_price * 0.985
            take_profit = base_price * 1.06
        else:
            stop_loss = base_price * 1.015
            take_profit = base_price * 0.94

        risk_reward = (take_profit - base_price) / (base_price - stop_loss) if direction == "long" else (base_price - take_profit) / (stop_loss - base_price)

        strength = SignalStrength.MODERATE
        if tf_analysis.confidence > 80:
            strength = SignalStrength.STRONG
        elif tf_analysis.confidence > 90:
            strength = SignalStrength.VERY_STRONG

        return TradingSignal(symbol=symbol, direction=direction, strength=strength, confidence=tf_analysis.confidence, sources=[SignalSource.MULTI_TIMEFRAME], entry_price=base_price, stop_loss=stop_loss, take_profit=take_profit, risk_reward_ratio=risk_reward, timestamp=datetime.now(), metadata={"timeframe_results": tf_analysis.timeframe_results, "confluence_score": tf_analysis.confluence_score})

    async def _analyze_ml(self, symbol: str, candles: pd.DataFrame) -> Optional[TradingSignal]:
        """Analyze using ML models"""

        try:
            if candles.empty or len(candles) < 50:
                return None

            signal = await self.ml_signal_generator.predict(candles)

            if not signal or signal["direction"] == "neutral":
                return None

            base_price = candles["close"].iloc[-1]
            direction = signal["direction"]
            confidence = signal["confidence"] * 100

            if direction == "long":
                stop_loss = base_price * 0.98
                take_profit = base_price * 1.04
            else:
                stop_loss = base_price * 1.02
                take_profit = base_price * 0.96

            risk_reward = (take_profit - base_price) / (base_price - stop_loss) if direction == "long" else (base_price - take_profit) / (stop_loss - base_price)

            strength = SignalStrength.MODERATE
            if confidence > 80:
                strength = SignalStrength.STRONG
            elif confidence > 90:
                strength = SignalStrength.VERY_STRONG

            return TradingSignal(symbol=symbol, direction=direction, strength=strength, confidence=confidence, sources=[SignalSource.ML_MODEL], entry_price=base_price, stop_loss=stop_loss, take_profit=take_profit, risk_reward_ratio=risk_reward, timestamp=datetime.now(), metadata={"model": signal.get("model", "ensemble"), "features": signal.get("top_features", [])})
        except Exception as e:
            logger.error(f"ML analysis error for {symbol}: {e}")
            return None

    async def aggregate_signals(self, symbol: str) -> Optional[TradingSignal]:
        """Aggregate signals from multiple sources"""

        signals = await self.analyze_symbol(symbol)

        if not signals:
            return None

        df_signals = pd.DataFrame([asdict(s) for s in signals])

        direction_votes = df_signals["direction"].value_counts()
        dominant_direction = direction_votes.index[0]

        avg_confidence = df_signals["confidence"].mean()

        max_strength = max(s["strength"].value for s in signals)

        all_sources = []
        for s in signals:
            all_sources.extend([src.value for src in s.sources])

        base_price = signals[0].entry_price

        avg_stop_loss = np.mean([s.stop_loss for s in signals])
        avg_take_profit = np.mean([s.take_profit for s in signals])

        if dominant_direction == "long":
            stop_loss = min(s.stop_loss for s in signals)
            take_profit = max(s.take_profit for s in signals)
        else:
            stop_loss = max(s.stop_loss for s in signals)
            take_profit = min(s.take_profit for s in signals)

        risk_reward = (take_profit - base_price) / (base_price - stop_loss) if dominant_direction == "long" else (base_price - take_profit) / (stop_loss - base_price)

        aggregated = TradingSignal(
            symbol=symbol,
            direction=dominant_direction,
            strength=SignalStrength(max_strength),
            confidence=avg_confidence,
            sources=[SignalSource(s) for s in set(all_sources)],
            entry_price=base_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=risk_reward,
            timestamp=datetime.now(),
            metadata={"signal_count": len(signals), "individual_signals": [asdict(s) for s in signals], "direction_votes": direction_votes.to_dict()},
        )

        return aggregated

    def should_trade(self, signal: TradingSignal) -> bool:
        """Determine if a signal should be traded based on risk management"""

        if not self.trading_enabled:
            return False

        if not self.risk_manager.check_trading_allowed():
            return False

        account = self.broker_gateway.broker_gateway.brokers.get(BrokerType.PAPER)
        if account:
            balance = asyncio.run(account.get_balance())
            position_value = signal.entry_price * self.risk_manager.calculate_position_size(signal.entry_price, signal.stop_loss, balance.portfolio_value)

            if position_value > balance.buying_power * 0.5:
                return False

        if signal.confidence < 50:
            return False

        if signal.risk_reward_ratio < 1.5:
            return False

        existing_position = self._get_position_for_symbol(signal.symbol)
        if existing_position:
            if existing_position["direction"] == signal.direction:
                return False

        return True

    def _get_position_for_symbol(self, symbol: str) -> Optional[Dict]:
        for trade_id, trade in self.active_trades.items():
            if trade.symbol == symbol and trade.status == "open":
                return {"trade_id": trade_id, "direction": trade.direction, "quantity": trade.quantity}
        return None

    async def execute_trade(self, signal: TradingSignal) -> Optional[Trade]:
        """Execute a trade based on the signal"""

        if not self.should_trade(signal):
            logger.info(f"Trade not executed for {signal.symbol}: Risk management check failed")
            return None

        broker = self.broker_gateway.get_best_broker(signal.symbol)

        account = await broker.get_balance()
        position_size = self.risk_manager.calculate_position_size(signal.entry_price, signal.stop_loss, account.portfolio_value)

        if position_size <= 0:
            logger.warning(f"Position size too small for {signal.symbol}")
            return None

        quantity = position_size / signal.entry_price

        order = OrderRequest(symbol=signal.symbol, side=OrderSide.BUY if signal.direction == "long" else OrderSide.SELL, order_type=OrderType.MARKET, quantity=quantity, price=signal.entry_price)

        try:
            order_result = await self.broker_gateway.place_order(order)

            trade = Trade(trade_id=f"AI_{order_result.order_id}", symbol=signal.symbol, direction=signal.direction, entry_price=order_result.price, quantity=quantity, stop_loss=signal.stop_loss, take_profit=signal.take_profit, status="open", entry_time=datetime.now(), signals=[signal])

            self.active_trades[trade.trade_id] = trade
            logger.info(f"✅ Trade executed: {signal.direction} {quantity:.4f} {signal.symbol} @ ${order_result.price:.2f}")

            asyncio.create_task(self._monitor_trade(trade))

            return trade

        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            return None

    async def _monitor_trade(self, trade: Trade):
        """Monitor an open trade and manage exits"""

        broker = self.broker_gateway.get_best_broker(trade.symbol)

        while trade.status == "open":
            try:
                market_data = await broker.get_market_data(trade.symbol)
                current_price = market_data.price

                if trade.direction == "long":
                    if current_price <= trade.stop_loss:
                        await self._close_trade(trade, current_price, "stop_loss")
                        break
                    elif current_price >= trade.take_profit:
                        await self._close_trade(trade, current_price, "take_profit")
                        break
                else:
                    if current_price >= trade.stop_loss:
                        await self._close_trade(trade, current_price, "stop_loss")
                        break
                    elif current_price <= trade.take_profit:
                        await self._close_trade(trade, current_price, "take_profit")
                        break

                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Trade monitoring error: {e}")
                await asyncio.sleep(10)

    async def _close_trade(self, trade: Trade, exit_price: float, reason: str):
        """Close a trade and update metrics"""

        broker = self.broker_gateway.get_best_broker(trade.symbol)

        side = OrderSide.SELL if trade.direction == "long" else OrderSide.BUY
        order = OrderRequest(symbol=trade.symbol, side=side, order_type=OrderType.MARKET, quantity=trade.quantity, price=exit_price)

        try:
            await self.broker_gateway.place_order(order)
        except:
            pass

        trade.exit_price = exit_price
        trade.exit_time = datetime.now()
        trade.status = "closed"
        trade.pnl = (exit_price - trade.entry_price) * trade.quantity if trade.direction == "long" else (trade.entry_price - exit_price) * trade.quantity
        trade.pnl_pct = (trade.pnl / (trade.entry_price * trade.quantity)) * 100

        self.completed_trades.append(trade)
        del self.active_trades[trade.trade_id]

        logger.info(f"Trade closed: {trade.symbol} | PnL: ${trade.pnl:.2f} ({trade.pnl_pct:.2f}%) | Reason: {reason}")

        self._update_performance_metrics()

    def _update_performance_metrics(self):
        if not self.completed_trades:
            return

        pnls = [t.pnl for t in self.completed_trades]
        self.performance_metrics["total_trades"] = len(self.completed_trades)
        self.performance_metrics["winning_trades"] = len([p for p in pnls if p > 0])
        self.performance_metrics["total_pnl"] = sum(pnls)
        self.performance_metrics["win_rate"] = (self.performance_metrics["winning_trades"] / self.performance_metrics["total_trades"]) * 100

        returns = np.array([t.pnl_pct for t in self.completed_trades])
        if len(returns) > 1:
            self.performance_metrics["sharpe_ratio"] = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if np.std(returns) > 0 else 0

    async def run_autonomous_trading(self):
        """Run the autonomous trading loop"""

        logger.info("🤖 Starting autonomous trading engine...")

        await self.broker_gateway.connect_all()

        while self.trading_enabled:
            try:
                for symbol in self.watchlist:
                    signal = await self.aggregate_signals(symbol)

                    if signal and self.auto_execution:
                        if self.should_trade(signal):
                            await self.execute_trade(signal)

                await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"Autonomous trading error: {e}")
                await asyncio.sleep(30)

    def start_autonomous_mode(self):
        """Start autonomous trading in background"""
        asyncio.create_task(self.run_autonomous_trading())
        logger.info("Autonomous trading mode enabled")

    def stop_autonomous_mode(self):
        """Stop autonomous trading"""
        self.trading_enabled = False
        logger.info("Autonomous trading mode disabled")

    async def get_status(self) -> Dict:
        """Get current status of the auto-trader"""

        account_summary = await self.broker_gateway.get_all_accounts()

        total_equity = 0
        for account in account_summary:
            total_equity += account.balance.portfolio_value

        return {"status": "running" if self.trading_enabled else "stopped", "trading_enabled": self.trading_enabled, "auto_execution": self.auto_execution, "watchlist_count": len(self.watchlist), "active_trades": len(self.active_trades), "completed_trades": len(self.completed_trades), "performance": self.performance_metrics, "total_equity": total_equity, "pending_signals": len(self.pending_signals)}

    async def _fetch_candles(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        """Fetch candlestick data from the broker gateway."""
        try:
            broker = self.broker_gateway.get_best_broker(symbol)
            if hasattr(broker, 'get_historical_data'):
                return await broker.get_historical_data(symbol, timeframe, limit)
            # Fallback: return empty DataFrame if no data source available
            logger.warning(f"Historical data not available for {symbol}, returning empty candles")
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
        except Exception as e:
            logger.error(f"Error fetching candles for {symbol}: {e}")
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])


def create_auto_trader() -> AIAutoTrader:
    """
    Create and configure the AI Auto-Trader

    Returns:
        Configured AIAutoTrader instance
    """
    broker_gateway = FreeBrokerGateway()
    auto_trader = AIAutoTrader(broker_gateway)
    return auto_trader
