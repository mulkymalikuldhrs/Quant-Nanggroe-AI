"""
Unified Backtesting Framework
Integrates all strategies (Wyckoff, Quant, ML) into a single backtesting system.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


class SignalSource(Enum):
    """Sources of trading signals"""

    WYCKOFF = "wyckoff"
    QUANTITATIVE = "quantitative"
    ML = "ml"
    MULTI_TIMEFRAME = "multi_timeframe"
    TECHNICAL = "technical"
    COMBINED = "combined"


@dataclass
class BacktestConfig:
    """Backtesting configuration"""

    initial_capital: float = 100000
    fee_rate: float = 0.001
    slippage: float = 0.0005
    position_size: float = 0.1
    max_positions: int = 5
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    trailing_stop: Optional[float] = None
    use_stop_loss: bool = True
    use_take_profit: bool = True
    use_trailing_stop: bool = False
    risk_per_trade: float = 0.02
    max_drawdown_limit: float = 0.20


@dataclass
class Trade:
    """Backtest trade record"""

    trade_id: str
    ticker: str
    entry_date: datetime
    entry_price: float
    exit_date: datetime
    exit_price: float
    quantity: float
    direction: str  # LONG, SHORT
    pnl: float
    pnl_pct: float
    commission: float
    source: SignalSource
    signal_confidence: float
    hold_time: timedelta
    setup_type: str


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
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    profit_factor: float
    avg_hold_time: timedelta
    trades: List[Trade]
    equity_curve: pd.DataFrame
    monthly_returns: pd.DataFrame
    trade_analysis: Dict[str, Any]
    signals_generated: int
    signals_used: int


class StrategyWrapper:
    """Wrapper for any strategy to work with backtester."""

    def __init__(self, strategy_func: Callable, name: str, source: SignalSource):
        """
        Initialize strategy wrapper.

        Args:
            strategy_func: Function that takes price data and returns signal
            name: Strategy name
            source: Signal source enum
        """
        self.strategy_func = strategy_func
        self.name = name
        self.source = source

    def generate_signal(self, ticker: str, high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, current_bar: int) -> Optional[Dict]:
        """Generate signal for current bar."""
        try:
            signal = self.strategy_func(high, low, close, volume)
            return signal
        except Exception as e:
            logger.warning(f"Error generating signal from {self.name}: {e}")
            return None


class UnifiedBacktester:
    """
    Unified backtesting engine for all strategies.

    Features:
    - Multi-strategy support
    - Walk-forward analysis
    - Monte Carlo simulation
    - Performance metrics
    - Trade journaling
    """

    def __init__(self, config: BacktestConfig = None):
        """
        Initialize backtester.

        Args:
            config: BacktestConfig with settings
        """
        self.config = config or BacktestConfig()
        self.strategies: Dict[str, StrategyWrapper] = {}
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = []
        self.dates: List[datetime] = []
        self.signals: List[Dict] = []

    def add_strategy(self, name: str, strategy_func: Callable, source: SignalSource):
        """Add a strategy to the backtester."""
        self.strategies[name] = StrategyWrapper(strategy_func, name, source)
        logger.info(f"Added strategy: {name} ({source.value})")

    def run_backtest(self, data: Dict[str, pd.DataFrame], strategy_name: str = "Combined", start_date: datetime = None, end_date: datetime = None) -> BacktestResult:
        """
        Run backtest on data.

        Args:
            data: Dict of {ticker: OHLCV DataFrame}
            strategy_name: Name for results
            start_date: Start date for backtest
            end_date: End date for backtest

        Returns:
            BacktestResult with all metrics
        """
        # Reset state
        self.trades = []
        self.equity_curve = [self.config.initial_capital]
        self.dates = [datetime.now()]
        self.signals = []

        capital = self.config.initial_capital
        positions: Dict[str, Dict] = {}  # {ticker: position_info}

        # Get common date range
        all_dates = []
        for ticker, df in data.items():
            all_dates.extend(df.index.tolist())
        all_dates = sorted(set(all_dates))

        if start_date:
            all_dates = [d for d in all_dates if d >= start_date]
        if end_date:
            all_dates = [d for d in all_dates if d <= end_date]

        # Run backtest for each date
        for date in all_dates:
            current_capital = self._calculate_portfolio_value(capital, positions, data)
            self.equity_curve.append(current_capital)
            self.dates.append(date)

            # Check each ticker
            for ticker, df in data.items():
                if ticker not in df.index:
                    continue

                # Get data up to current date
                df_history = df[df.index <= date]
                if len(df_history) < 50:
                    continue

                current_idx = len(df_history) - 1
                bar_date = df_history.index[current_idx]

                high = df_history["high"]
                low = df_history["low"]
                close = df_history["close"]
                volume = df_history.get("volume", pd.Series([1] * len(close)))
                current_price = close.iloc[-1]

                # Generate signals from all strategies
                for name, strategy in self.strategies.items():
                    signal = strategy.generate_signal(ticker, high, low, close, volume, current_idx)

                    if signal:
                        self.signals.append({"date": date, "ticker": ticker, "strategy": name, "signal": signal})

                        # Execute signal
                        self._execute_signal(signal, ticker, current_price, date, capital, positions)

                # Update open positions
                self._update_positions(positions, ticker, current_price, date, data)

        # Close remaining positions
        for ticker, pos in list(positions.items()):
            if pos["quantity"] > 0:
                self._close_position(pos, data[ticker]["close"].iloc[-1], data[ticker].index[-1], capital, positions)

        # Calculate metrics
        result = self._calculate_results(strategy_name, data)

        return result

    def run_walk_forward(self, data: Dict[str, pd.DataFrame], train_period: int = 252, test_period: int = 21, strategy_name: str = "WalkForward") -> List[BacktestResult]:  # Days  # Days
        """
        Run walk-forward analysis.

        Args:
            data: Dict of {ticker: OHLCV DataFrame}
            train_period: Training period in days
            test_period: Testing period in days
            strategy_name: Base name for results

        Returns:
            List of BacktestResult for each walk-forward period
        """
        results = []

        # Get all dates
        all_dates = []
        for ticker, df in data.items():
            all_dates.extend(df.index.tolist())
        all_dates = sorted(set(all_dates))

        start_idx = train_period
        while start_idx < len(all_dates) - test_period:
            train_end = start_idx
            test_end = min(start_idx + test_period, len(all_dates))

            train_dates = all_dates[train_end - train_period : train_end]
            test_dates = all_dates[train_end:test_end]

            # Filter data for training and test periods
            train_data = {}
            test_data = {}

            for ticker, df in data.items():
                train_mask = df.index.isin(train_dates)
                test_mask = df.index.isin(test_dates)

                if train_mask.sum() >= train_period * 0.8:
                    train_data[ticker] = df[train_mask]
                if test_mask.sum() >= test_period * 0.5:
                    test_data[ticker] = df[test_mask]

            # Run backtest on test period
            result = self.run_backtest(test_data, strategy_name=f"{strategy_name}_{len(results)+1}")
            results.append(result)

            # Move forward
            start_idx += test_period

        return results

    def run_monte_carlo(self, result: BacktestResult, n_simulations: int = 1000, random_seed: int = 42) -> Dict[str, Any]:
        """
        Run Monte Carlo simulation on backtest results.

        Args:
            result: Original BacktestResult
            n_simulations: Number of simulations
            random_seed: Random seed

        Returns:
            Dict with Monte Carlo statistics
        """
        np.random.seed(random_seed)

        trades = result.trades
        if not trades:
            return {"error": "No trades to simulate"}

        pnls = np.array([t.pnl_pct for t in trades])

        # Simulate equity curves
        simulated_returns = []
        final_returns = []
        max_drawdowns = []

        for _ in range(n_simulations):
            # Resample with replacement
            indices = np.random.choice(len(pnls), size=len(pnls), replace=True)
            sampled_pnls = pnls[indices]

            # Calculate equity curve
            equity = 1 + sampled_pnls / 100
            equity_curve = np.cumprod(equity)

            # Calculate max drawdown
            peak = np.maximum.accumulate(equity_curve)
            drawdown = (equity_curve - peak) / peak
            max_dd = abs(min(drawdown))

            simulated_returns.append(equity_curve)
            final_returns.append(equity_curve[-1])
            max_drawdowns.append(max_dd)

        return {
            "n_simulations": n_simulations,
            "final_return_mean": np.mean(final_returns),
            "final_return_std": np.std(final_returns),
            "final_return_5pct": np.percentile(final_returns, 5),
            "final_return_95pct": np.percentile(final_returns, 95),
            "max_drawdown_mean": np.mean(max_drawdowns),
            "max_drawdown_5pct": np.percentile(max_drawdowns, 5),
            "max_drawdown_95pct": np.percentile(max_drawdowns, 95),
            "probability_profit": np.mean(np.array(final_returns) > 1),
            "equity_curves": simulated_returns,
        }

    def _execute_signal(self, signal: Dict, ticker: str, price: float, date: datetime, capital: float, positions: Dict):
        """Execute a trading signal."""
        action = signal.get("action", "").upper()

        if action not in ["BUY", "SELL"]:
            return

        # Calculate position size
        position_value = capital * self.config.position_size
        if self.config.risk_per_trade:
            if signal.get("stop_loss"):
                risk_amount = capital * self.config.risk_per_trade
                risk_per_share = abs(price - signal["stop_loss"])
                position_value = min(position_value, risk_amount / risk_per_share * price)

        quantity = position_value / price

        if action == "BUY" and ticker not in positions:
            # Open long position
            fee = position_value * self.config.fee_rate
            positions[ticker] = {"quantity": quantity, "entry_price": price, "entry_date": date, "direction": "LONG", "source": signal.get("source", SignalSource.COMBINED), "confidence": signal.get("confidence", 0.5)}
            self.trades.append(Trade(trade_id=f"T{len(self.trades)+1}", ticker=ticker, entry_date=date, entry_price=price, exit_date=date, exit_price=price, quantity=quantity, direction="LONG", pnl=-fee, pnl_pct=-fee / position_value * 100, commission=fee, source=signal.get("source", SignalSource.COMBINED), signal_confidence=signal.get("confidence", 0.5), hold_time=timedelta(0)))

        elif action == "SELL" and ticker in positions:
            self._close_position(positions[ticker], price, date, capital, positions)

    def _close_position(self, position: Dict, price: float, date: datetime, capital: float, positions: Dict):
        """Close an open position."""
        ticker = None
        for k, v in positions.items():
            if v == position:
                ticker = k
                break

        if ticker is None:
            return

        entry_price = position["entry_price"]
        quantity = position["quantity"]
        direction = position["direction"]

        # Calculate PnL
        if direction == "LONG":
            pnl = (price - entry_price) * quantity
        else:
            pnl = (entry_price - price) * quantity

        notional = price * quantity
        fee = notional * self.config.fee_rate
        pnl_after_fee = pnl - fee
        pnl_pct = pnl_after_fee / (entry_price * quantity) * 100

        # Update trade record
        if self.trades:
            last_trade = [t for t in self.trades if t.ticker == ticker and t.exit_date == t.entry_date]
            if last_trade:
                last_trade[0].exit_date = date
                last_trade[0].exit_price = price
                last_trade[0].pnl = pnl_after_fee
                last_trade[0].pnl_pct = pnl_pct
                last_trade[0].hold_time = date - position["entry_date"]

        del positions[ticker]

    def _update_positions(self, positions: Dict, ticker: str, price: float, date: datetime, data: Dict):
        """Update open positions (check stops, etc.)."""
        if ticker not in positions:
            return

        position = positions[ticker]

        # Check stop loss
        if self.config.use_stop_loss and position.get("stop_loss"):
            if position["direction"] == "LONG" and price <= position["stop_loss"]:
                self._close_position(position, price, date, 0, positions)
                return
            elif position["direction"] == "SHORT" and price >= position["stop_loss"]:
                self._close_position(position, price, date, 0, positions)
                return

        # Check take profit
        if self.config.use_take_profit and position.get("take_profit"):
            if position["direction"] == "LONG" and price >= position["take_profit"]:
                self._close_position(position, price, date, 0, positions)
                return
            elif position["direction"] == "SHORT" and price <= position["take_profit"]:
                self._close_position(position, price, date, 0, positions)
                return

    def _calculate_portfolio_value(self, cash: float, positions: Dict, data: Dict) -> float:
        """Calculate current portfolio value."""
        value = cash

        for ticker, position in positions.items():
            if ticker in data:
                current_price = data[ticker]["close"].iloc[-1]
                value += current_price * position["quantity"]

        return value

    def _calculate_results(self, strategy_name: str, data: Dict) -> BacktestResult:
        """Calculate backtest metrics."""
        trades = [t for t in self.trades if t.exit_date != t.entry_date]

        if not trades:
            return BacktestResult(
                strategy_name=strategy_name,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0,
                total_pnl=0,
                total_pnl_pct=0,
                avg_trade_pnl=0,
                avg_trade_pnl_pct=0,
                max_drawdown=0,
                sharpe_ratio=0,
                sortino_ratio=0,
                profit_factor=0,
                avg_hold_time=timedelta(0),
                trades=[],
                equity_curve=pd.DataFrame(),
                monthly_returns=pd.DataFrame(),
                trade_analysis={},
                signals_generated=len(self.signals),
                signals_used=len(trades),
            )

        # Basic metrics
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.pnl > 0)
        losing_trades = sum(1 for t in trades if t.pnl <= 0)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        total_pnl = sum(t.pnl for t in trades)
        total_pnl_pct = sum(t.pnl_pct for t in trades)

        avg_trade_pnl = total_pnl / total_trades
        avg_trade_pnl_pct = total_pnl_pct / total_trades

        # Hold time
        hold_times = [t.hold_time for t in trades if t.hold_time]
        avg_hold_time = sum(hold_times, timedelta(0)) / len(hold_times) if hold_times else timedelta(0)

        # Max drawdown
        equity = np.array(self.equity_curve)
        peak = np.maximum.accumulate(equity)
        drawdown = (equity - peak) / peak
        max_drawdown = abs(min(drawdown))

        # Sharpe ratio
        returns = np.diff(equity) / equity[:-1]
        if len(returns) > 0 and np.std(returns) > 0:
            sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(252)
        else:
            sharpe_ratio = 0

        # Sortino ratio
        negative_returns = returns[returns < 0]
        if len(negative_returns) > 0 and np.std(negative_returns) > 0:
            sortino_ratio = (np.mean(returns) / np.std(negative_returns)) * np.sqrt(252)
        else:
            sortino_ratio = 0

        # Profit factor
        gross_profit = sum(t.pnl for t in trades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in trades if t.pnl <= 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        # Monthly returns
        trade_df = pd.DataFrame([{"date": t.exit_date, "pnl": t.pnl} for t in trades])
        if len(trade_df) > 0:
            trade_df["month"] = trade_df["date"].dt.to_period("M")
            monthly_returns = trade_df.groupby("month")["pnl"].sum()
            monthly_returns_df = pd.DataFrame({"return": monthly_returns})
        else:
            monthly_returns_df = pd.DataFrame()

        # Trade analysis by source
        trade_by_source = {}
        for t in trades:
            source = t.source.value if hasattr(t.source, "value") else str(t.source)
            if source not in trade_by_source:
                trade_by_source[source] = []
            trade_by_source[source].append(t.pnl)

        trade_analysis = {source: {"count": len(pnls), "total_pnl": sum(pnls), "win_rate": sum(1 for p in pnls if p > 0) / len(pnls)} for source, pnls in trade_by_source.items()}

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
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            profit_factor=profit_factor,
            avg_hold_time=avg_hold_time,
            trades=trades,
            equity_curve=pd.DataFrame({"date": self.dates, "equity": self.equity_curve}),
            monthly_returns=monthly_returns_df,
            trade_analysis=trade_analysis,
            signals_generated=len(self.signals),
            signals_used=len(trades),
        )


# Example usage
if __name__ == "__main__":
    import pandas as pd
    import numpy as np
    from src.strategies.wyckoff.wyckoff_strategy import WyckoffStrategy

    np.random.seed(42)

    # Generate sample data
    dates = pd.date_range(start="2022-01-01", periods=500, freq="D")
    returns = np.random.randn(500) * 0.02 + 0.0005
    close = 100 * np.cumprod(1 + returns)

    data = {"AAPL": pd.DataFrame({"open": close * (1 + np.random.randn(500) * 0.001), "high": close * (1 + np.random.rand(500) * 0.02), "low": close * (1 - np.random.rand(500) * 0.02), "close": close, "volume": np.random.randint(1000000, 10000000, 500)}, index=dates)}

    # Initialize backtester
    config = BacktestConfig(initial_capital=100000, position_size=0.1, risk_per_trade=0.02)
    backtester = UnifiedBacktester(config)

    # Add Wyckoff strategy
    def wyckoff_signal(high, low, close, volume):
        strategy = WyckoffStrategy()
        return {"action": strategy.calculate(high, low, close, volume).action, "confidence": strategy.calculate(high, low, close, volume).confidence, "stop_loss": strategy.calculate(high, low, close, volume).stop_loss, "take_profit": strategy.calculate(high, low, close, volume).take_profit, "source": SignalSource.WYCKOFF}

    backtester.add_strategy("Wyckoff", wyckoff_signal, SignalSource.WYCKOFF)

    # Run backtest
    print("Running Backtest...")
    result = backtester.run_backtest(data, "Wyckoff Strategy")

    print(f"\nBacktest Results:")
    print(f"  Total Trades: {result.total_trades}")
    print(f"  Win Rate: {result.win_rate:.1%}")
    print(f"  Total PnL: ${result.total_pnl:,.2f} ({result.total_pnl_pct:.2f}%)")
    print(f"  Max Drawdown: {result.max_drawdown:.2%}")
    print(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}")
    print(f"  Profit Factor: {result.profit_factor:.2f}")
    print(f"  Avg Hold Time: {result.avg_hold_time}")

    # Walk-forward test
    print("\nRunning Walk-Forward Analysis...")
    wf_results = backtester.run_walk_forward(data, train_period=252, test_period=21)
    print(f"  Walk-Forward Periods: {len(wf_results)}")

    # Monte Carlo simulation
    print("\nRunning Monte Carlo Simulation...")
    mc_results = backtester.run_monte_carlo(result, n_simulations=100)
    print(f"  Mean Final Return: {mc_results['final_return_mean']:.2%}")
    print(f"  5th Percentile: {mc_results['final_return_5pct']:.2%}")
    print(f"  95th Percentile: {mc_results['final_return_95pct']:.2%}")
    print(f"  Probability of Profit: {mc_results['probability_profit']:.1%}")
