"""
Backtesting Engine
Historical simulation of trading strategies.
Based on Freqtrade's backtesting implementation.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from statistics import mean, stdev

import pandas as pd
import numpy as np

from src.strategies.quantitative_strategies import StrategySignal, AggregatedSignal, analyze_with_all_strategies
from src.agents.enhanced_agents import run_multi_agent_analysis


logger = logging.getLogger(__name__)


class PositionType(Enum):
    """Position types"""

    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


class OrderType(Enum):
    """Order types"""

    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(Enum):
    """Order statuses"""

    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"


@dataclass
class Order:
    """Trading order"""

    order_id: str
    pair: str
    order_type: OrderType
    side: str  # buy/sell
    amount: float
    price: float
    status: OrderStatus = OrderStatus.PENDING
    filled_at: Optional[datetime] = None
    filled_price: float = 0.0
    filled_amount: float = 0.0
    fee: float = 0.0

    def __post_init__(self):
        if self.status == OrderStatus.FILLED:
            self.filled_price = self.price
            self.filled_amount = self.amount


@dataclass
class Trade:
    """Completed trade"""

    trade_id: str
    pair: str
    position_type: PositionType
    entry_date: datetime
    entry_price: float
    entry_amount: float
    entry_fee: float
    exit_date: Optional[datetime] = None
    exit_price: float = 0.0
    exit_fee: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    hold_time: Optional[timedelta] = None
    orders: List[Order] = field(default_factory=list)

    @property
    def is_open(self) -> bool:
        """Check if trade is still open"""
        return self.exit_date is None

    @property
    def current_value(self, current_price: float) -> float:
        """Calculate current value of the trade"""
        if self.position_type == PositionType.LONG:
            return self.entry_amount * (current_price / self.entry_price)
        else:  # SHORT
            return self.entry_amount * (self.entry_price / current_price)

    def calculate_pnl(self, exit_price: float, fee_rate: float = 0.001):
        """Calculate PnL for the trade"""
        if self.position_type == PositionType.LONG:
            gross_pnl = (exit_price - self.entry_price) * self.entry_amount
        else:  # SHORT
            gross_pnl = (self.entry_price - exit_price) * self.entry_amount

        total_fee = self.entry_fee + (gross_pnl * fee_rate)
        self.pnl = gross_pnl - total_fee
        self.pnl_pct = (self.pnl / (self.entry_price * self.entry_amount)) * 100
        self.exit_price = exit_price
        self.exit_fee = total_fee

        if self.exit_date:
            self.hold_time = self.exit_date - self.entry_date


@dataclass
class BacktestResult:
    """Backtesting results"""

    strategy_name: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_pnl_pct: float
    avg_trade_pnl: float
    avg_trade_pnl_pct: float
    avg_hold_time: timedelta
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    profit_factor: float
    trades: List[Trade]
    equity_curve: pd.Series
    monthly_returns: Dict[str, float]

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "strategy_name": self.strategy_name,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "total_pnl": self.total_pnl,
            "total_pnl_pct": self.total_pnl_pct,
            "avg_trade_pnl": self.avg_trade_pnl,
            "avg_trade_pnl_pct": self.avg_trade_pnl_pct,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "profit_factor": self.profit_factor,
            "num_trades": len(self.trades),
        }


class BacktestingEngine:
    """
    Backtesting engine for historical simulation.

    Supports:
    - Multiple strategies
    - Long/Short positions
    - Various order types
    - Performance metrics calculation
    """

    def __init__(
        self,
        initial_capital: float = 10000,
        fee_rate: float = 0.001,
        position_sizing: float = 0.1,
        max_positions: int = 5,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ):
        """
        Initialize backtesting engine.

        Args:
            initial_capital: Starting capital
            fee_rate: Trading fee rate (default: 0.1%)
            position_sizing: Position size as fraction of capital (default: 10%)
            max_positions: Maximum number of concurrent positions
            stop_loss: Stop loss percentage (optional)
            take_profit: Take profit percentage (optional)
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.fee_rate = fee_rate
        self.position_sizing = position_sizing
        self.max_positions = max_positions
        self.stop_loss = stop_loss
        self.take_profit = take_profit

        self.trades: List[Trade] = []
        self.open_positions: Dict[str, Trade] = {}
        self.equity_curve: List[float] = []
        self.order_history: List[Order] = []

    def reset(self):
        """Reset backtesting state"""
        self.current_capital = self.initial_capital
        self.trades = []
        self.open_positions = {}
        self.equity_curve = [self.initial_capital]
        self.order_history = []

    def calculate_position_size(self, price: float) -> float:
        """Calculate position size based on current capital"""
        position_value = self.current_capital * self.position_sizing
        return position_value / price

    def generate_signals(self, data: pd.DataFrame, strategy_type: str = "all") -> pd.DataFrame:
        """
        Generate trading signals for the entire dataset.

        Args:
            data: OHLCV DataFrame with columns ['open', 'high', 'low', 'close', 'volume']
            strategy_type: Strategy to use ('all', 'strategies', 'agents')

        Returns:
            DataFrame with signal columns
        """
        signals = pd.DataFrame(index=data.index)
        signals["close"] = data["close"]

        closes = data["close"].tolist()

        if strategy_type == "all" or strategy_type == "strategies":
            # Generate signals from all strategies
            strategy_results = analyze_with_all_strategies("TEST", closes, {})

            signals["strategy_signal"] = strategy_results.final_signal
            signals["strategy_confidence"] = strategy_results.final_confidence
            signals["strategy_score"] = getattr(strategy_results, "weighted_score", 0)

        if strategy_type == "all" or strategy_type == "agents":
            # Generate signals from AI agents
            agent_results = run_multi_agent_analysis("TEST", closes, {})

            signals["agent_signal"] = agent_results.final_signal
            signals["agent_confidence"] = agent_results.final_confidence

        # Combined signal
        if "strategy_signal" in signals.columns and "agent_signal" in signals.columns:
            signals["combined_signal"] = self._combine_signals(signals["strategy_signal"], signals["agent_signal"], signals["strategy_confidence"], signals["agent_confidence"])

        return signals

    def _combine_signals(self, strategy_signals: pd.Series, agent_signals: pd.Series, strategy_confidence: pd.Series, agent_confidence: pd.Series) -> pd.Series:
        """Combine strategy and agent signals"""
        combined = []

        for i in range(len(strategy_signals)):
            strat_sig = strategy_signals.iloc[i]
            agent_sig = agent_signals.iloc[i]
            strat_conf = strategy_confidence.iloc[i]
            agent_conf = agent_confidence.iloc[i]

            # Weight the signals (BUY = +confidence, SELL = -confidence, HOLD = 0)
            strat_score = (1 if strat_sig == "BUY" else (-1 if strat_sig == "SELL" else 0)) * strat_conf
            agent_score = (1 if agent_sig == "BUY" else (-1 if agent_sig == "SELL" else 0)) * agent_conf

            total_score = (strat_score + agent_score) / 2

            if total_score > 10:
                combined.append("BUY")
            elif total_score < -10:
                combined.append("SELL")
            else:
                combined.append("HOLD")

        return pd.Series(combined, index=strategy_signals.index)

    def run_backtest(self, data: pd.DataFrame, signals: pd.DataFrame, strategy_name: str = "Test Strategy") -> BacktestResult:
        """
        Run backtesting simulation.

        Args:
            data: OHLCV DataFrame
            signals: DataFrame with trading signals
            strategy_name: Name of the strategy being tested

        Returns:
            BacktestResult with performance metrics
        """
        self.reset()

        # Ensure we have required columns
        required_cols = ["open", "high", "low", "close"]
        for col in required_cols:
            if col not in data.columns:
                raise ValueError(f"Missing required column: {col}")

        # Get signal column
        signal_col = None
        for col in ["combined_signal", "strategy_signal", "agent_signal", "signal"]:
            if col in signals.columns:
                signal_col = col
                break

        if signal_col is None:
            raise ValueError("No signal column found in signals DataFrame")

        # Run simulation
        for i, (idx, row) in enumerate(data.iterrows()):
            current_time = idx
            current_price = row["close"]
            current_signal = signals.loc[idx, signal_col]

            # Update equity curve
            self._update_equity(current_price)

            # Check existing positions
            self._check_positions(current_time, current_price, row)

            # Entry logic
            if current_signal == "BUY" and len(self.open_positions) < self.max_positions:
                self._enter_position(current_time, current_price, "long")
            elif current_signal == "SELL" and len(self.open_positions) < self.max_positions:
                self._enter_position(current_time, current_price, "short")

        # Close any remaining positions at final price
        final_price = data["close"].iloc[-1]
        for pair, trade in list(self.open_positions.items()):
            self._exit_position(trade, final_price, data.index[-1])

        # Calculate metrics
        result = self._calculate_metrics(strategy_name, data)

        return result

    def _update_equity(self, current_price: float):
        """Update equity curve with current portfolio value"""
        portfolio_value = self.current_capital

        for pair, trade in self.open_positions.items():
            if trade.position_type == PositionType.LONG:
                portfolio_value += trade.entry_amount * (current_price - trade.entry_price)
            else:  # SHORT
                portfolio_value += trade.entry_amount * (trade.entry_price - current_price)

        self.equity_curve.append(portfolio_value)

    def _check_positions(self, current_time: datetime, current_price: float, row: pd.Series):
        """Check and manage existing positions"""
        for pair, trade in list(self.open_positions.items()):
            # Check stop loss
            if self.stop_loss:
                if trade.position_type == PositionType.LONG:
                    if current_price <= trade.entry_price * (1 - self.stop_loss):
                        self._exit_position(trade, current_price, current_time)
                        continue
                else:  # SHORT
                    if current_price >= trade.entry_price * (1 + self.stop_loss):
                        self._exit_position(trade, current_price, current_time)
                        continue

            # Check take profit
            if self.take_profit:
                if trade.position_type == PositionType.LONG:
                    if current_price >= trade.entry_price * (1 + self.take_profit):
                        self._exit_position(trade, current_price, current_time)
                        continue
                else:  # SHORT
                    if current_price <= trade.entry_price * (1 - self.take_profit):
                        self._exit_position(trade, current_price, current_time)
                        continue

    def _enter_position(self, current_time: datetime, current_price: float, position_type: str, pair: str = "TEST"):
        """Enter a new position"""
        # Check if there's already an open position for this pair
        if pair in self.open_positions:
            return

        position_size = self.calculate_position_size(current_price)

        if position_size <= 0:
            return

        fee = current_price * position_size * self.fee_rate
        position_type_enum = PositionType.LONG if position_type == "long" else PositionType.SHORT

        trade = Trade(trade_id=f"trade_{len(self.trades) + 1}", pair=pair, position_type=position_type_enum, entry_date=current_time, entry_price=current_price, entry_amount=position_size, entry_fee=fee)

        self.open_positions[pair] = trade
        self.current_capital -= current_price * position_size + fee

    def _exit_position(self, trade: Trade, exit_price: float, exit_time: datetime):
        """Exit an existing position"""
        trade.exit_date = exit_time
        trade.calculate_pnl(exit_price, self.fee_rate)

        # Update capital
        gross_exit = trade.entry_amount * (exit_price / trade.entry_price)
        self.current_capital += gross_exit - trade.exit_fee

        # Add to completed trades
        self.trades.append(trade)

        # Remove from open positions
        if trade.pair in self.open_positions:
            del self.open_positions[trade.pair]

    def _calculate_metrics(self, strategy_name: str, data: pd.DataFrame) -> BacktestResult:
        """Calculate backtesting performance metrics"""
        if not self.trades:
            # Return empty result
            return BacktestResult(strategy_name=strategy_name, total_trades=0, winning_trades=0, losing_trades=0, win_rate=0, total_pnl=0, total_pnl_pct=0, avg_trade_pnl=0, avg_trade_pnl_pct=0, avg_hold_time=timedelta(0), max_drawdown=0, sharpe_ratio=0, sortino_ratio=0, profit_factor=0, trades=[], equity_curve=pd.Series(self.equity_curve), monthly_returns={})

        # Basic metrics
        total_trades = len(self.trades)
        winning_trades = sum(1 for t in self.trades if t.pnl > 0)
        losing_trades = sum(1 for t in self.trades if t.pnl <= 0)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        total_pnl = sum(t.pnl for t in self.trades)
        total_pnl_pct = sum(t.pnl_pct for t in self.trades)

        avg_trade_pnl = mean(t.pnl for t in self.trades)
        avg_trade_pnl_pct = mean(t.pnl_pct for t in self.trades)

        # Hold time
        hold_times = [t.hold_time.total_seconds() for t in self.trades if t.hold_time]
        if hold_times:
            avg_hold_time_seconds = mean(hold_times)
            avg_hold_time = timedelta(seconds=avg_hold_time_seconds)
        else:
            avg_hold_time = timedelta(0)

        # Max drawdown
        equity = np.array(self.equity_curve)
        peak = np.maximum.accumulate(equity)
        drawdown = (equity - peak) / peak
        max_drawdown = abs(min(drawdown))

        # Sharpe ratio
        returns = np.diff(equity) / equity[:-1]
        if len(returns) > 0 and np.std(returns) > 0:
            sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(252)  # Annualized
        else:
            sharpe_ratio = 0

        # Sortino ratio
        negative_returns = returns[returns < 0]
        if len(negative_returns) > 0 and np.std(negative_returns) > 0:
            sortino_ratio = (np.mean(returns) / np.std(negative_returns)) * np.sqrt(252)
        else:
            sortino_ratio = 0

        # Profit factor
        gross_profit = sum(t.pnl for t in self.trades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in self.trades if t.pnl <= 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        # Monthly returns
        trades_df = pd.DataFrame([{"date": t.exit_date, "pnl": t.pnl, "pnl_pct": t.pnl_pct} for t in self.trades])
        monthly_returns = {}
        if len(trades_df) > 0:
            trades_df["date"] = pd.to_datetime(trades_df["date"])
            trades_df["month"] = trades_df["date"].dt.to_period("M")
            monthly_pnl = trades_df.groupby("month")["pnl_pct"].sum()
            monthly_returns = {str(k): v for k, v in monthly_pnl.items()}

        return BacktestResult(
            strategy_name=strategy_name,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            avg_trade_pnl=avg_trade_pnl,
            avg_trade_pnl_pct=avg_trade_pnl_pct,
            avg_hold_time=avg_hold_time,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            profit_factor=profit_factor,
            trades=self.trades,
            equity_curve=pd.Series(self.equity_curve),
            monthly_returns=monthly_returns,
        )

    def run_multi_asset_backtest(self, data_dict: Dict[str, pd.DataFrame], strategy_type: str = "all") -> Dict[str, BacktestResult]:
        """
        Run backtesting on multiple assets.

        Args:
            data_dict: Dictionary of {pair: OHLCV DataFrame}
            strategy_type: Strategy to use

        Returns:
            Dictionary of {pair: BacktestResult}
        """
        results = {}

        for pair, data in data_dict.items():
            logger.info(f"Running backtest for {pair}")

            # Generate signals
            signals = self.generate_signals(data, strategy_type)
            signals["pair"] = pair

            # Run backtest
            result = self.run_backtest(data, signals, f"{strategy_type}_{pair}")
            results[pair] = result

        return results


def run_simple_backtest(data: pd.DataFrame, initial_capital: float = 10000, position_sizing: float = 0.1, fee_rate: float = 0.001) -> BacktestResult:
    """
    Simple backtest function for quick testing.

    Args:
        data: OHLCV DataFrame
        initial_capital: Starting capital
        position_sizing: Position size as fraction
        fee_rate: Trading fee rate

    Returns:
        BacktestResult
    """
    engine = BacktestingEngine(initial_capital=initial_capital, position_sizing=position_sizing, fee_rate=fee_rate)

    signals = engine.generate_signals(data)
    result = engine.run_backtest(data, signals, "Simple Strategy")

    return result


# Example usage
if __name__ == "__main__":
    import pandas as pd
    import numpy as np

    # Generate sample data
    np.random.seed(42)
    dates = pd.date_range(start="2023-01-01", periods=252, freq="D")
    closes = 100 + np.cumsum(np.random.randn(252))

    data = pd.DataFrame({"open": closes + np.random.randn(252) * 0.5, "high": closes + np.random.rand(252) * 2, "low": closes - np.random.rand(252) * 2, "close": closes, "volume": np.random.randint(1000000, 10000000, 252)}, index=dates)

    # Run backtest
    result = run_simple_backtest(data)

    print(f"Backtest Results:")
    print(f"  Total Trades: {result.total_trades}")
    print(f"  Win Rate: {result.win_rate:.2%}")
    print(f"  Total PnL: ${result.total_pnl:.2f}")
    print(f"  Max Drawdown: {result.max_drawdown:.2%}")
    print(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}")


# ============ FACTORY FUNCTION ============


def get_backtest_engine(initial_capital=10000, position_sizing=0.02, max_positions=5):
    return BacktestingEngine(
        initial_capital=initial_capital,
        position_sizing=position_sizing,
        max_positions=max_positions
    )

