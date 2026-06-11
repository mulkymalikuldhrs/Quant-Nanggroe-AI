"""Core Backtesting Engine.

Implements the main backtest loop with realistic execution simulation,
supporting multiple markets and strategy types.

Extracted from Vibe-Trading's BaseEngine with enhancements from ai-hedge-fund.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable

import numpy as np
import pandas as pd

from quant_nanggroe.engine.backtest.portfolio import Portfolio, Position, TradeRecord
from quant_nanggroe.engine.backtest.execution import ExecutionSimulator, ExecutionConfig
from quant_nanggroe.engine.backtest.metrics import PerformanceMetrics

logger = logging.getLogger(__name__)


class MarketType(str, Enum):
    """Supported market types for backtesting."""

    EQUITY = "equity"
    CRYPTO = "crypto"
    FOREX = "forex"
    FUTURES = "futures"


class StrategyType(str, Enum):
    """Supported strategy types."""

    SIGNAL_BASED = "signal_based"
    FACTOR_BASED = "factor_based"
    ML_BASED = "ml_based"


@dataclass
class BacktestConfig:
    """Configuration for a backtest run.

    Attributes:
        initial_capital: Starting capital.
        market: Market type (affects execution rules).
        strategy_type: Type of strategy being tested.
        commission_rate: Commission rate as decimal (e.g. 0.001 = 0.1%).
        slippage_bps: Slippage in basis points (e.g. 5 = 0.05%).
        leverage: Maximum leverage allowed.
        risk_per_trade: Maximum risk per trade as fraction of capital.
        max_positions: Maximum number of simultaneous positions.
        bars_per_year: Number of bars per year for annualisation.
        benchmark: Benchmark ticker for comparison.
        short_enabled: Whether short selling is allowed.
    """

    initial_capital: float = 1_000_000.0
    market: MarketType = MarketType.EQUITY
    strategy_type: StrategyType = StrategyType.SIGNAL_BASED
    commission_rate: float = 0.001
    slippage_bps: float = 5.0
    leverage: float = 1.0
    risk_per_trade: float = 0.005
    max_positions: int = 10
    bars_per_year: int = 252
    benchmark: Optional[str] = None
    short_enabled: bool = False


class BacktestEngine:
    """Core backtesting engine with realistic execution simulation.

    Supports:
    - Multiple markets (equity, crypto, forex, futures)
    - Realistic execution with slippage and commission
    - Multiple strategy types
    - Position sizing and risk management
    - Performance metrics calculation

    Usage:
        engine = BacktestEngine(BacktestConfig())
        results = engine.run(prices_df, signals_df)
    """

    def __init__(self, config: Optional[BacktestConfig] = None) -> None:
        self.config = config or BacktestConfig()
        self.execution = ExecutionSimulator(
            ExecutionConfig(
                commission_rate=self.config.commission_rate,
                slippage_bps=self.config.slippage_bps,
                market=self.config.market.value,
            )
        )
        self.metrics_calculator = PerformanceMetrics(
            bars_per_year=self.config.bars_per_year
        )

    def run(
        self,
        prices: pd.DataFrame,
        signals: pd.DataFrame,
        position_sizer: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """Run a backtest on price data with trading signals.

        Args:
            prices: DataFrame with DatetimeIndex and columns for each symbol.
                     Values are close prices.
            signals: DataFrame with same index/columns as prices.
                     Values are target position weights (-1 to 1).
            position_sizer: Optional callable for custom position sizing.
                Signature: (signal, capital, price) -> size

        Returns:
            Dict with performance metrics, equity curve, and trade records.
        """
        portfolio = Portfolio(
            initial_capital=self.config.initial_capital,
            max_positions=self.config.max_positions,
        )

        equity_curve: List[float] = []
        timestamps: List[pd.Timestamp] = []
        all_trades: List[TradeRecord] = []

        # Shift signals by 1 bar (next-bar-open semantics)
        shifted_signals = signals.shift(1).fillna(0.0)

        symbols = list(prices.columns)

        for i, (timestamp, price_row) in enumerate(prices.iterrows()):
            if timestamp not in shifted_signals.index:
                continue

            signal_row = shifted_signals.loc[timestamp]

            # 1. Mark-to-market existing positions
            portfolio.mark_to_market(price_row)

            # 2. Execute trades based on signals
            for symbol in symbols:
                price = price_row.get(symbol, np.nan)
                if pd.isna(price) or price <= 0:
                    continue

                target_weight = signal_row.get(symbol, 0.0)
                current_pos = portfolio.get_position(symbol)

                # Determine target action
                target_direction = 1 if target_weight > 0.01 else (-1 if target_weight < -0.01 else 0)

                # Close existing position if direction changed
                if current_pos is not None:
                    if target_direction == 0 or (current_pos.direction != target_direction and target_direction != 0):
                        if not self.config.short_enabled and current_pos.direction == -1:
                            pass  # Can't close short if shorts disabled (shouldn't happen)
                        close_price = self.execution.apply_slippage(price, -current_pos.direction)
                        trade = portfolio.close_position(
                            symbol, close_price, timestamp, "signal"
                        )
                        if trade is not None:
                            commission = self.execution.calc_commission(
                                abs(trade.size), close_price, is_closing=True
                            )
                            portfolio._apply_commission(symbol, commission)
                            all_trades.append(trade)

                # Open new position if target non-zero
                if target_direction != 0 and portfolio.get_position(symbol) is None:
                    if not self.config.short_enabled and target_direction == -1:
                        continue

                    equity = portfolio.equity
                    target_notional = abs(target_weight) * equity * self.config.leverage

                    if position_sizer:
                        size = position_sizer(target_weight, equity, price)
                    else:
                        size = target_notional / price

                    # Apply risk limit
                    max_risk_amount = equity * self.config.risk_per_trade
                    if abs(size * price) > max_risk_amount * 20:  # 20:1 R:R threshold
                        size = max_risk_amount * 20 / price

                    exec_price = self.execution.apply_slippage(price, target_direction)
                    open_commission = self.execution.calc_commission(
                        abs(size), exec_price, is_closing=False
                    )

                    if portfolio.can_open_position(exec_price, size, open_commission):
                        trade = portfolio.open_position(
                            symbol=symbol,
                            direction=target_direction,
                            size=size,
                            price=exec_price,
                            timestamp=timestamp,
                            commission=open_commission,
                        )
                        if trade is not None:
                            all_trades.append(trade)

            # Record equity
            equity_curve.append(portfolio.equity)
            timestamps.append(timestamp)

        # Force close all remaining positions
        if len(prices) > 0:
            last_ts = prices.index[-1]
            last_prices = prices.iloc[-1]
            for symbol in list(portfolio.positions.keys()):
                pos = portfolio.get_position(symbol)
                if pos is not None:
                    close_price = last_prices.get(symbol, pos.entry_price)
                    trade = portfolio.close_position(symbol, close_price, last_ts, "end_of_backtest")
                    if trade is not None:
                        all_trades.append(trade)

        # Build equity curve series
        equity_series = pd.Series(equity_curve, index=timestamps)

        # Calculate performance metrics
        metrics = self.metrics_calculator.calculate(
            equity_series=equity_series,
            trades=all_trades,
            initial_capital=self.config.initial_capital,
        )

        return {
            "metrics": metrics,
            "equity_curve": equity_series,
            "trades": all_trades,
            "final_equity": portfolio.equity,
            "total_trades": len(all_trades),
        }

    def run_walk_forward(
        self,
        prices: pd.DataFrame,
        signals: pd.DataFrame,
        train_window: int = 252,
        test_window: int = 63,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Run walk-forward analysis.

        Args:
            prices: Price data.
            signals: Signal data.
            train_window: Training window in bars.
            test_window: Test window in bars.

        Returns:
            Walk-forward analysis results.
        """
        from quant_nanggroe.engine.backtest.walk_forward import WalkForwardAnalyzer

        analyzer = WalkForwardAnalyzer(
            engine=self,
            train_window=train_window,
            test_window=test_window,
        )
        return analyzer.analyze(prices, signals, **kwargs)
