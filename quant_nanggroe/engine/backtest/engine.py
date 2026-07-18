"""Core Backtesting Engine.

Implements the main backtest loop with realistic execution simulation,
supporting multiple markets and strategy types.

Features:
- Single and multi-strategy backtesting
- Parameter sensitivity analysis
- Benchmark comparison
- Trade-level analytics
- Custom execution models

Extracted from Vibe-Trading's BaseEngine with enhancements from ai-hedge-fund.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.backtest.execution import ExecutionConfig, ExecutionSimulator
from quant_nanggroe.engine.backtest.metrics import PerformanceMetrics
from quant_nanggroe.engine.backtest.portfolio import Portfolio, TradeRecord

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
    vol_target_ann: float = 0.30  # ponytail: target annualized vol; notional scaled down for high-vol assets


class BacktestEngine:
    """Core backtesting engine with realistic execution simulation.

    Supports:
    - Multiple markets (equity, crypto, forex, futures)
    - Realistic execution with slippage and commission
    - Multiple strategy types
    - Position sizing and risk management
    - Performance metrics calculation
    - Multi-strategy backtesting
    - Parameter sensitivity analysis
    - Benchmark comparison
    - Trade-level analytics
    - Custom execution models

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
        execution_model: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """Run a backtest on price data with trading signals.

        Args:
            prices: DataFrame with DatetimeIndex and columns for each symbol.
                     Values are close prices.
            signals: DataFrame with same index/columns as prices.
                     Values are target position weights (-1 to 1).
            position_sizer: Optional callable for custom position sizing.
                Signature: (signal, capital, price) -> size
            execution_model: Optional callable for custom execution simulation.
                Signature: (price, direction, size, timestamp) -> fill_price

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

        # ponytail: strategies emit lowercase OHLCV columns; normalize prices once
        # so symbol lookup in _execute_bar matches (Close->close etc.) regardless of source.
        prices = prices.rename(columns={c: c.lower() for c in prices.columns})
        symbols = list(prices.columns)

        # ponytail: precompute annualized vol per symbol once (O(n)); notional scaled to vol_target
        # infer bars/year from actual index spacing (1h -> ~8760, daily -> 252)
        if len(prices) > 1:
            med_delta = prices.index.to_series().diff().median()
            bars_per_year = max(1, int(pd.Timedelta(days=365) / med_delta)) if med_delta is not None and med_delta.total_seconds() > 0 else self.config.bars_per_year
        else:
            bars_per_year = self.config.bars_per_year
        ann_factor = np.sqrt(bars_per_year)
        vol_by_symbol = {}
        for sym in symbols:
            if sym in prices.columns:
                rets = prices[sym].pct_change().dropna()
                vol_by_symbol[sym] = rets.std() * ann_factor if len(rets) > 1 else 0.0

        for i, (timestamp, price_row) in enumerate(prices.iterrows()):
            if timestamp not in shifted_signals.index:
                continue

            signal_row = shifted_signals.loc[timestamp]

            # 1. Mark-to-market existing positions
            portfolio.mark_to_market(price_row)

            # 2. Execute trades based on signals
            self._execute_bar(
                symbols, signal_row, price_row, timestamp,
                portfolio, vol_by_symbol, shifted_signals,
                position_sizer, execution_model, all_trades,
            )

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

        # Add trade-level analytics
        trade_analytics = self._compute_trade_analytics(all_trades)

        return {
            "metrics": metrics,
            "equity_curve": equity_series,
            "trades": all_trades,
            "final_equity": portfolio.equity,
            "total_trades": len(all_trades),
            "trade_analytics": trade_analytics,
        }

    def run_multi_strategy(
        self,
        prices: pd.DataFrame,
        strategy_signals: Dict[str, pd.DataFrame],
        strategy_weights: Optional[Dict[str, float]] = None,
        position_sizer: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """Run a multi-strategy backtest with portfolio-level aggregation.

        Each strategy produces its own signals, which are combined using
        the specified weights. The combined signal is then executed.

        Args:
            prices: Price data DataFrame.
            strategy_signals: Dict mapping strategy name to signal DataFrame.
            strategy_weights: Optional dict mapping strategy name to weight.
                            Defaults to equal weight for all strategies.
            position_sizer: Optional position sizer callable.

        Returns:
            Dict with:
                - combined: Combined backtest result
                - per_strategy: Dict of per-strategy backtest results
                - strategy_correlation: Correlation matrix of strategy returns
        """
        if not strategy_signals:
            raise ValueError("At least one strategy must be provided")

        n_strategies = len(strategy_signals)

        # Default to equal weights
        if strategy_weights is None:
            strategy_weights = {name: 1.0 / n_strategies for name in strategy_signals}
        else:
            # Normalize weights
            total_weight = sum(strategy_weights.values())
            if total_weight <= 0:
                raise ValueError("Strategy weights must sum to a positive value")
            strategy_weights = {
                name: w / total_weight
                for name, w in strategy_weights.items()
            }

        # Run individual strategy backtests
        per_strategy: Dict[str, Dict[str, Any]] = {}
        strategy_equity_curves: Dict[str, pd.Series] = {}

        for name, signals_df in strategy_signals.items():
            try:
                result = self.run(prices, signals_df, position_sizer)
                per_strategy[name] = result
                if "equity_curve" in result:
                    strategy_equity_curves[name] = result["equity_curve"]
            except Exception as e:
                logger.error(f"Strategy '{name}' backtest failed: {e}")
                per_strategy[name] = {"error": str(e), "metrics": {}}

        # Combine signals using weights
        combined_signal = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
        for name, signals_df in strategy_signals.items():
            weight = strategy_weights.get(name, 0.0)
            # Align indices
            aligned = signals_df.reindex(prices.index).fillna(0.0)
            for col in combined_signal.columns:
                if col in aligned.columns:
                    combined_signal[col] += aligned[col] * weight

        # Run combined backtest
        combined_result = self.run(prices, combined_signal, position_sizer)

        # Calculate strategy correlation matrix
        strategy_correlation = self._compute_strategy_correlation(strategy_equity_curves)

        # Benchmark comparison
        benchmark_comparison = {}
        if self.config.benchmark and len(prices.columns) > 0:
            benchmark_prices = prices.iloc[:, 0]  # Use first column as proxy
            benchmark_returns = benchmark_prices.pct_change().fillna(0.0)
            strategy_returns = combined_result.get("equity_curve", pd.Series()).pct_change().fillna(0.0)

            from quant_nanggroe.engine.backtest.benchmarks import BenchmarkManager
            benchmark_comparison = BenchmarkManager.compare(
                strategy_returns, benchmark_returns,
                bars_per_year=self.config.bars_per_year,
            )

        return {
            "combined": combined_result,
            "per_strategy": per_strategy,
            "strategy_correlation": strategy_correlation,
            "strategy_weights": strategy_weights,
            "benchmark_comparison": benchmark_comparison,
        }

    def run_sensitivity_analysis(
        self,
        prices: pd.DataFrame,
        signals: pd.DataFrame,
        param_name: str,
        param_values: List[Any],
        param_applier: Optional[Callable] = None,
        position_sizer: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """Run parameter sensitivity analysis.

        Tests how backtest results change as a parameter varies.

        Args:
            prices: Price data.
            signals: Signal data.
            param_name: Name of the parameter to vary.
            param_values: List of parameter values to test.
            param_applier: Optional callable that takes (config, param_name, param_value)
                          and returns a modified BacktestConfig.
            position_sizer: Optional position sizer.

        Returns:
            Dict with:
                - results: Dict mapping param_value to backtest result
                - metrics_summary: DataFrame of key metrics across parameter values
                - optimal: Dict with optimal parameter value and metrics
        """
        results: Dict[str, Dict[str, Any]] = {}

        for value in param_values:
            # Create modified config
            if param_applier:
                config = param_applier(self.config, param_name, value)
            else:
                config = self._apply_param(self.config, param_name, value)

            # Create engine with modified config
            engine = BacktestEngine(config)

            try:
                result = engine.run(prices, signals, position_sizer)
                results[str(value)] = result
            except Exception as e:
                logger.error(f"Sensitivity analysis failed for {param_name}={value}: {e}")
                results[str(value)] = {"error": str(e), "metrics": {}}

        # Build metrics summary
        metrics_summary = self._build_sensitivity_summary(results, param_name)

        # Find optimal parameter value
        optimal = self._find_optimal_param(results, param_name)

        return {
            "param_name": param_name,
            "results": results,
            "metrics_summary": metrics_summary,
            "optimal": optimal,
        }

    def run_with_benchmark(
        self,
        prices: pd.DataFrame,
        signals: pd.DataFrame,
        benchmark_prices: Optional[pd.Series] = None,
        position_sizer: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """Run backtest with benchmark comparison.

        Args:
            prices: Price data.
            signals: Signal data.
            benchmark_prices: Optional benchmark price series. If not provided,
                            the first column of prices is used.
            position_sizer: Optional position sizer.

        Returns:
            Dict with backtest results and benchmark comparison.
        """
        result = self.run(prices, signals, position_sizer)

        # Determine benchmark
        if benchmark_prices is None:
            if self.config.benchmark and self.config.benchmark in prices.columns:
                benchmark_prices = prices[self.config.benchmark]
            elif len(prices.columns) > 0:
                benchmark_prices = prices.iloc[:, 0]

        # Add benchmark comparison
        if benchmark_prices is not None and len(benchmark_prices) > 0:
            from quant_nanggroe.engine.backtest.benchmarks import BenchmarkManager

            strategy_returns = result["equity_curve"].pct_change().fillna(0.0)
            benchmark_returns = benchmark_prices.pct_change().fillna(0.0)

            benchmark_comparison = BenchmarkManager.compare(
                strategy_returns, benchmark_returns,
                bars_per_year=self.config.bars_per_year,
            )
            result["benchmark_comparison"] = benchmark_comparison

            # Re-calculate metrics with benchmark
            metrics = self.metrics_calculator.calculate(
                equity_series=result["equity_curve"],
                trades=result["trades"],
                initial_capital=self.config.initial_capital,
                benchmark_returns=benchmark_returns,
            )
            result["metrics"] = metrics

        return result

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

    # ── Private helpers ───────────────────────────────────────────────

    def _execute_bar(
        self,
        symbols: List[str],
        signal_row: Any,
        price_row: pd.Series,
        timestamp: pd.Timestamp,
        portfolio: Portfolio,
        vol_by_symbol: Dict[str, float],
        shifted_signals: pd.DataFrame,
        position_sizer: Optional[Callable],
        execution_model: Optional[Callable],
        all_trades: List[TradeRecord],
    ) -> None:
        """Execute one bar: for each symbol, close stale and open target positions."""
        for symbol in symbols:
            price = price_row.get(symbol, np.nan)
            if pd.isna(price) or price <= 0:
                continue

            # ponytail: signals may be named by first OHLCV col, not 'close'; align
            if isinstance(signal_row, pd.Series) and symbol not in shifted_signals.columns:
                target_weight = float(signal_row.get(shifted_signals.columns[0], 0.0)) \
                    if hasattr(signal_row, "get") else 0.0
            else:
                target_weight = float(signal_row.get(symbol, 0.0)) \
                    if hasattr(signal_row, "get") else 0.0

            target_direction = 1 if target_weight > 0.01 else (-1 if target_weight < -0.01 else 0)
            current_pos = portfolio.get_position(symbol)

            # Check stop-loss and take-profit before signal-based logic
            if current_pos is not None:
                bar_high = price_row.get("high", price) if isinstance(price_row, pd.Series) else price
                bar_low = price_row.get("low", price) if isinstance(price_row, pd.Series) else price
                close_price = None
                close_reason = None
                if current_pos.direction == 1:  # long
                    if current_pos.stop_loss is not None and bar_low <= current_pos.stop_loss:
                        close_price = current_pos.stop_loss
                        close_reason = "stop_loss"
                    elif current_pos.take_profit is not None and bar_high >= current_pos.take_profit:
                        close_price = current_pos.take_profit
                        close_reason = "take_profit"
                elif current_pos.direction == -1:  # short
                    if current_pos.stop_loss is not None and bar_high >= current_pos.stop_loss:
                        close_price = current_pos.stop_loss
                        close_reason = "stop_loss"
                    elif current_pos.take_profit is not None and bar_low <= current_pos.take_profit:
                        close_price = current_pos.take_profit
                        close_reason = "take_profit"
                if close_price is not None:
                    fill_price = self._get_fill_price(
                        execution_model, close_price, -current_pos.direction,
                        abs(current_pos.size), timestamp,
                    )
                    trade = portfolio.close_position(symbol, fill_price, timestamp, close_reason)
                    if trade is not None:
                        commission = self.execution.calc_commission(
                            abs(trade.size), fill_price, is_closing=True
                        )
                        portfolio._apply_commission(symbol, commission)
                        all_trades.append(trade)
                    current_pos = portfolio.get_position(symbol)

            # Close when flat-target or direction flipped
            if current_pos is not None and (
                target_direction == 0
                or current_pos.direction != target_direction
            ):
                close_price = self._get_fill_price(
                    execution_model, price, -current_pos.direction,
                    abs(current_pos.size), timestamp,
                )
                trade = portfolio.close_position(symbol, close_price, timestamp, "signal")
                if trade is not None:
                    commission = self.execution.calc_commission(
                        abs(trade.size), close_price, is_closing=True
                    )
                    portfolio._apply_commission(symbol, commission)
                    all_trades.append(trade)

            # Open when target non-zero and no open position
            if target_direction != 0 and portfolio.get_position(symbol) is None:
                if not self.config.short_enabled and target_direction == -1:
                    continue  # shorts disabled: open path blocks this too, guard kept for symmetry
                size = self._size_position(
                    target_weight, price, portfolio.equity,
                    vol_by_symbol.get(symbol, 0.0), position_sizer,
                )
                exec_price = self._get_fill_price(
                    execution_model, price, target_direction, size, timestamp
                )
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

    def _size_position(
        self,
        target_weight: float,
        price: float,
        equity: float,
        sym_vol: float,
        position_sizer: Optional[Callable],
    ) -> float:
        """Resolve target position size: custom sizer, else vol-scaled notional with risk cap."""
        if position_sizer:
            return position_sizer(target_weight, equity, price)
        # ponytail: scale notional by target vol so high-vol assets (SOL) don't get 1.0 leverage blowups
        vol_mult = 1.0 if sym_vol <= 0 else min(1.0, self.config.vol_target_ann / sym_vol)
        size = (abs(target_weight) * equity * self.config.leverage * vol_mult) / price
        # Risk limit: 20:1 reward-to-risk threshold
        max_risk_amount = equity * self.config.risk_per_trade
        if abs(size * price) > max_risk_amount * 20:
            size = max_risk_amount * 20 / price
        return size

    def _get_fill_price(
        self,
        execution_model: Optional[Callable],
        price: float,
        direction: int,
        size: float,
        timestamp: pd.Timestamp,
    ) -> float:
        """Get execution fill price, using custom model or default slippage."""
        if execution_model is not None:
            try:
                fill = execution_model(price, direction, size, timestamp)
                if fill is not None and fill > 0:
                    return float(fill)
            except Exception as e:
                logger.warning(f"Custom execution model failed: {e}, using default")

        # Use simulate_fill() when available (applies market impact + slippage + commission)
        if isinstance(self.execution, ExecutionSimulator):
            fill_result = self.execution.simulate_fill(
                price=price, direction=direction, size=size
            )
            return float(fill_result["fill_price"])

        return self.execution.apply_slippage(price, direction)

    @staticmethod
    def _apply_param(
        config: BacktestConfig,
        param_name: str,
        param_value: Any,
    ) -> BacktestConfig:
        """Apply a parameter value to a BacktestConfig.

        Args:
            config: Original config.
            param_name: Parameter name.
            param_value: New value.

        Returns:
            Modified BacktestConfig.
        """
        config_dict = {
            "initial_capital": config.initial_capital,
            "market": config.market,
            "strategy_type": config.strategy_type,
            "commission_rate": config.commission_rate,
            "slippage_bps": config.slippage_bps,
            "leverage": config.leverage,
            "risk_per_trade": config.risk_per_trade,
            "max_positions": config.max_positions,
            "bars_per_year": config.bars_per_year,
            "benchmark": config.benchmark,
            "short_enabled": config.short_enabled,
        }

        if param_name in config_dict:
            config_dict[param_name] = param_value

        return BacktestConfig(**config_dict)

    @staticmethod
    def _build_sensitivity_summary(
        results: Dict[str, Dict[str, Any]],
        param_name: str,
    ) -> pd.DataFrame:
        """Build a summary DataFrame of metrics across parameter values."""
        rows = []
        for param_value, result in results.items():
            metrics = result.get("metrics", {})
            row = {param_name: param_value}
            for key in [
                "total_return", "annual_return", "sharpe_ratio",
                "sortino_ratio", "max_drawdown", "win_rate",
                "profit_factor", "total_trades",
            ]:
                row[key] = metrics.get(key, None)
            rows.append(row)

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        df = df.set_index(param_name)
        return df

    @staticmethod
    def _find_optimal_param(
        results: Dict[str, Dict[str, Any]],
        param_name: str,
        metric: str = "sharpe_ratio",
    ) -> Dict[str, Any]:
        """Find the optimal parameter value based on a given metric.

        Args:
            results: Dict mapping param_value to backtest result.
            param_name: Parameter name.
            metric: Metric to optimize (higher is better).

        Returns:
            Dict with optimal param value and associated metrics.
        """
        best_value = None
        best_metric = float("-inf")
        best_metrics = {}

        for param_value, result in results.items():
            metrics = result.get("metrics", {})
            m = metrics.get(metric, float("-inf"))
            if isinstance(m, (int, float)) and m > best_metric:
                best_metric = m
                best_value = param_value
                best_metrics = metrics

        return {
            "param_name": param_name,
            "optimal_value": best_value,
            "optimal_metric": best_metric,
            "metric_name": metric,
            "metrics": best_metrics,
        }

    @staticmethod
    def _compute_trade_analytics(trades: List[TradeRecord]) -> Dict[str, Any]:
        """Compute trade-level analytics.

        Args:
            trades: List of completed trade records.

        Returns:
            Dict of trade analytics.
        """
        if not trades:
            return {
                "by_symbol": {},
                "by_direction": {"long": {}, "short": {}},
                "by_exit_reason": {},
                "time_analysis": {},
            }

        # By symbol
        by_symbol: Dict[str, List[TradeRecord]] = {}
        for t in trades:
            by_symbol.setdefault(t.symbol, []).append(t)

        symbol_analytics = {}
        for symbol, symbol_trades in by_symbol.items():
            pnls = [t.pnl for t in symbol_trades]
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p < 0]
            symbol_analytics[symbol] = {
                "trade_count": len(symbol_trades),
                "total_pnl": round(sum(pnls), 4),
                "win_rate": round(len(wins) / len(pnls), 4) if pnls else 0.0,
                "avg_pnl": round(float(np.mean(pnls)), 4) if pnls else 0.0,
                "avg_win": round(float(np.mean(wins)), 4) if wins else 0.0,
                "avg_loss": round(float(np.mean(losses)), 4) if losses else 0.0,
                "max_win": round(max(pnls), 4) if pnls else 0.0,
                "max_loss": round(min(pnls), 4) if pnls else 0.0,
            }

        # By direction
        long_trades = [t for t in trades if t.direction == 1]
        short_trades = [t for t in trades if t.direction == -1]

        def _direction_stats(trade_list: List[TradeRecord]) -> Dict[str, Any]:
            if not trade_list:
                return {"count": 0, "total_pnl": 0.0, "win_rate": 0.0, "avg_pnl": 0.0}
            pnls = [t.pnl for t in trade_list]
            wins = [p for p in pnls if p > 0]
            return {
                "count": len(trade_list),
                "total_pnl": round(sum(pnls), 4),
                "win_rate": round(len(wins) / len(pnls), 4) if pnls else 0.0,
                "avg_pnl": round(float(np.mean(pnls)), 4) if pnls else 0.0,
            }

        # By exit reason
        by_reason: Dict[str, List[TradeRecord]] = {}
        for t in trades:
            by_reason.setdefault(t.exit_reason, []).append(t)

        reason_analytics = {}
        for reason, reason_trades in by_reason.items():
            pnls = [t.pnl for t in reason_trades]
            reason_analytics[reason] = {
                "count": len(reason_trades),
                "total_pnl": round(sum(pnls), 4),
                "avg_pnl": round(float(np.mean(pnls)), 4) if pnls else 0.0,
            }

        # Time analysis
        holding_bars = [t.holding_bars for t in trades if t.holding_bars > 0]
        time_analysis = {
            "avg_holding_bars": round(float(np.mean(holding_bars)), 1) if holding_bars else 0.0,
            "median_holding_bars": round(float(np.median(holding_bars)), 1) if holding_bars else 0.0,
            "max_holding_bars": max(holding_bars) if holding_bars else 0,
            "min_holding_bars": min(holding_bars) if holding_bars else 0,
        }

        return {
            "by_symbol": symbol_analytics,
            "by_direction": {
                "long": _direction_stats(long_trades),
                "short": _direction_stats(short_trades),
            },
            "by_exit_reason": reason_analytics,
            "time_analysis": time_analysis,
        }

    @staticmethod
    def _compute_strategy_correlation(
        equity_curves: Dict[str, pd.Series],
    ) -> pd.DataFrame:
        """Compute correlation matrix between strategy equity curves.

        Args:
            equity_curves: Dict mapping strategy name to equity curve Series.

        Returns:
            Correlation matrix DataFrame.
        """
        if len(equity_curves) < 2:
            return pd.DataFrame()

        # Convert to returns
        returns_dict = {}
        for name, eq in equity_curves.items():
            if len(eq) > 1:
                returns_dict[name] = eq.pct_change().fillna(0.0)

        if len(returns_dict) < 2:
            return pd.DataFrame()

        returns_df = pd.DataFrame(returns_dict)
        return returns_df.corr()
