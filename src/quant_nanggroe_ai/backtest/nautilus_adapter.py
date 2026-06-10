"""
NautilusTrader Adapter — Bridge between existing backtest engine and NautilusTrader
====================================================================================
Provides a compatibility layer that allows the existing backtest engine to
leverage NautilusTrader's Rust-core backtesting infrastructure for
high-performance simulation.

NautilusTrader provides:
  - Rust-core event-driven backtesting engine
  - Realistic order book simulation with depth
  - Multi-asset, multi-currency portfolio simulation
  - Microsecond-level resolution
  - Actor model for strategy implementation

This adapter:
  - Converts existing BacktestEngine data formats to NautilusTrader format
  - Wraps NautilusTrader's BacktestEngine with a compatible API
  - Falls back gracefully when NautilusTrader is not installed
  - Provides configuration translation between the two systems

Requirements:
    pip install nautilus_trader

Reference:
    https://nautilustrader.io/docs/
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# Data Models
# ══════════════════════════════════════════════════════════════════════


@dataclass
class NautilusConfig:
    """Configuration for the NautilusTrader adapter."""

    # Core engine settings
    log_level: str = "INFO"
    cache_database: bool = False

    # Simulation settings
    simulate_fills: bool = True
    fill_model: str = "last"  # last, mid, worse
    slippage_ticks: float = 0.0
    commission_rate: float = 0.001  # 0.1%

    # Data settings
    bar_type: str = "1-MINUTE"  # e.g., "1-MINUTE", "5-MINUTE", "1-HOUR", "1-DAY"
    use_tick_data: bool = False
    order_book_depth: int = 0  # 0 = no order book simulation

    # Portfolio settings
    default_currency: str = "USD"
    starting_capital: float = 100_000.0
    leverage: float = 1.0

    # Performance settings
    max_retries: int = 3
    timeout_seconds: float = 300.0


@dataclass
class NautilusBacktestResult:
    """Result from a NautilusTrader backtest run."""

    # Performance metrics
    total_return: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    avg_trade_pnl: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0

    # Time series
    equity_curve: list[float] = field(default_factory=list)
    drawdown_curve: list[float] = field(default_factory=list)

    # Trade data
    trades: list[dict[str, Any]] = field(default_factory=list)
    positions: list[dict[str, Any]] = field(default_factory=list)

    # Metadata
    backtest_id: str = ""
    symbol: str = ""
    strategy_name: str = ""
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    engine_type: str = "nautilus"


# ══════════════════════════════════════════════════════════════════════
# Data Conversion Utilities
# ══════════════════════════════════════════════════════════════════════


def dataframe_to_nautilus_bars(
    df: pd.DataFrame,
    symbol: str = "EURUSD",
    bar_type: str = "1-MINUTE",
) -> list[dict[str, Any]]:
    """
    Convert a pandas DataFrame to NautilusTrader bar data format.

    The DataFrame should have columns: open, high, low, close, volume
    and a datetime index.

    Args:
        df: OHLCV DataFrame with datetime index.
        symbol: Instrument symbol.
        bar_type: NautilusTrader bar type string.

    Returns:
        List of bar dicts in NautilusTrader-compatible format.
    """
    required_cols = {"open", "high", "low", "close"}
    if not required_cols.issubset(df.columns):
        raise ValueError(
            f"DataFrame must have columns: {required_cols}. "
            f"Got: {set(df.columns)}"
        )

    bars: list[dict[str, Any]] = []
    for timestamp, row in df.iterrows():
        bar = {
            "bar_type": bar_type,
            "instrument_id": symbol,
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": int(row.get("volume", 0)),
            "ts_event": int(pd.Timestamp(timestamp).value / 1_000),  # microseconds
            "ts_init": int(pd.Timestamp(timestamp).value / 1_000),
        }
        bars.append(bar)

    logger.info("Converted %d bars for %s", len(bars), symbol)
    return bars


def nautilus_result_to_backtest_result(
    nautilus_result: Any,
    symbol: str = "",
    strategy_name: str = "",
) -> NautilusBacktestResult:
    """
    Convert NautilusTrader backtest result to our standard format.

    Handles both live NautilusTrader result objects and dict-based results.

    Args:
        nautilus_result: Result from NautilusTrader backtest engine.
        symbol: Trading symbol.
        strategy_name: Strategy name.

    Returns:
        NautilusBacktestResult with standardized metrics.
    """
    result = NautilusBacktestResult(
        symbol=symbol,
        strategy_name=strategy_name,
        engine_type="nautilus",
    )

    if isinstance(nautilus_result, dict):
        result.total_return = nautilus_result.get("total_return", 0.0)
        result.sharpe_ratio = nautilus_result.get("sharpe_ratio", 0.0)
        result.sortino_ratio = nautilus_result.get("sortino_ratio", 0.0)
        result.max_drawdown = nautilus_result.get("max_drawdown", 0.0)
        result.win_rate = nautilus_result.get("win_rate", 0.0)
        result.profit_factor = nautilus_result.get("profit_factor", 0.0)
        result.total_trades = nautilus_result.get("total_trades", 0)
        result.avg_trade_pnl = nautilus_result.get("avg_trade_pnl", 0.0)
        result.avg_win = nautilus_result.get("avg_win", 0.0)
        result.avg_loss = nautilus_result.get("avg_loss", 0.0)
        result.equity_curve = nautilus_result.get("equity_curve", [])
        result.trades = nautilus_result.get("trades", [])
    elif hasattr(nautilus_result, "total_return"):
        result.total_return = getattr(nautilus_result, "total_return", 0.0)
        result.sharpe_ratio = getattr(nautilus_result, "sharpe_ratio", 0.0)
        result.sortino_ratio = getattr(nautilus_result, "sortino_ratio", 0.0)
        result.max_drawdown = getattr(nautilus_result, "max_drawdown", 0.0)
        result.win_rate = getattr(nautilus_result, "win_rate", 0.0)
        result.profit_factor = getattr(nautilus_result, "profit_factor", 0.0)
        result.total_trades = getattr(nautilus_result, "total_trades", 0)

    return result


# ══════════════════════════════════════════════════════════════════════
# NautilusTrader Adapter
# ══════════════════════════════════════════════════════════════════════


class NautilusAdapter:
    """
    Adapter bridging the existing backtest engine with NautilusTrader.

    Provides:
      - Data format conversion (DataFrame → NautilusTrader bars)
      - Configuration translation
      - Strategy wrapper for executing in NautilusTrader
      - Result normalization
      - Graceful fallback when NautilusTrader is not installed

    Usage::

        adapter = NautilusAdapter(config=NautilusConfig())

        # Convert data
        bars = adapter.convert_data(df, symbol="EURUSD")

        # Run backtest (requires nautilus_trader installed)
        result = adapter.run_backtest(
            data=df,
            symbol="EURUSD",
            strategy=my_strategy,
        )

        # Or use fallback mode
        result = adapter.run_backtest_fallback(
            data=df,
            symbol="EURUSD",
            signal_fn=my_signal_function,
        )
    """

    def __init__(self, config: NautilusConfig | None = None) -> None:
        self.config = config or NautilusConfig()
        self._nautilus_available = self._check_nautilus()

    def _check_nautilus(self) -> bool:
        """Check if NautilusTrader is installed and importable."""
        try:
            import nautilus_trader  # noqa: F401
            logger.info("NautilusTrader is available (version: %s)", nautilus_trader.__version__)
            return True
        except ImportError:
            logger.warning(
                "NautilusTrader not installed. Using fallback backtesting. "
                "Install with: pip install nautilus_trader"
            )
            return False

    @property
    def is_available(self) -> bool:
        """Whether NautilusTrader is available for use."""
        return self._nautilus_available

    # ══════════════════════════════════════════════════════════════════
    # Data Conversion
    # ══════════════════════════════════════════════════════════════════

    def convert_data(
        self,
        data: pd.DataFrame,
        symbol: str = "EURUSD",
    ) -> list[dict[str, Any]]:
        """
        Convert OHLCV DataFrame to NautilusTrader bar format.

        Args:
            data: DataFrame with OHLCV columns and datetime index.
            symbol: Instrument symbol.

        Returns:
            List of bar dicts in NautilusTrader format.
        """
        return dataframe_to_nautilus_bars(
            df=data,
            symbol=symbol,
            bar_type=self.config.bar_type,
        )

    # ══════════════════════════════════════════════════════════════════
    # Backtest Execution (with NautilusTrader)
    # ══════════════════════════════════════════════════════════════════

    def run_backtest(
        self,
        data: pd.DataFrame,
        symbol: str = "EURUSD",
        strategy: Any = None,
        strategy_name: str = "unknown",
    ) -> NautilusBacktestResult:
        """
        Run a backtest using NautilusTrader.

        Falls back to the internal engine if NautilusTrader is not available.

        Args:
            data: OHLCV DataFrame with datetime index.
            symbol: Instrument symbol.
            strategy: Strategy object or function.
            strategy_name: Name of the strategy.

        Returns:
            NautilusBacktestResult with performance metrics.
        """
        if not self._nautilus_available:
            logger.info("NautilusTrader unavailable, using fallback engine")
            return self.run_backtest_fallback(data, symbol, strategy, strategy_name)

        try:
            return self._run_nautilus_backtest(data, symbol, strategy, strategy_name)
        except Exception as exc:
            logger.error("NautilusTrader backtest failed: %s", exc)
            logger.info("Falling back to internal engine")
            return self.run_backtest_fallback(data, symbol, strategy, strategy_name)

    def _run_nautilus_backtest(
        self,
        data: pd.DataFrame,
        symbol: str,
        strategy: Any,
        strategy_name: str,
    ) -> NautilusBacktestResult:
        """
        Execute a NautilusTrader backtest.

        This creates a NautilusTrader BacktestEngine, configures it with
        the provided data and strategy, and runs the simulation.
        """
        from nautilus_trader.backtest.engine import BacktestEngine as NTBacktestEngine
        from nautilus_trader.config import BacktestRunConfig, BacktestVenueConfig, BacktestDataConfig
        from nautilus_trader.model.currencies import USD
        from nautilus_trader.model.data import BarType, BarSpecification, AggregationSource
        from nautilus_trader.model.identifiers import Venue, InstrumentId
        from nautilus_trader.persistence.catalog import ParquetDataCatalog
        from nautilus_trader.test_kit.providers import TestInstrumentProvider

        # Create engine
        engine = NTBacktestEngine(config=self._build_engine_config())

        # Add venue
        venue = Venue("SIM")
        engine.add_venue(
            venue=venue,
            oms_type="NETTING",
            account_type="MARGIN",
            base_currency=USD,
            starting_balances=[self.config.starting_capital],
            default_leverage=self.config.leverage,
        )

        # Add instrument
        instrument = TestInstrumentProvider.default_fx_ccy(
            instrument_id=InstrumentId.from_str(symbol),
        )
        engine.add_instrument(instrument)

        # Add data
        bars = self.convert_data(data, symbol)
        engine.add_data(bars)

        # Add strategy if provided
        if strategy is not None:
            engine.add_strategy(strategy)

        # Run
        engine.run()

        # Extract results
        result = self._extract_nautilus_results(engine, symbol, strategy_name)
        return result

    def _build_engine_config(self) -> Any:
        """Build NautilusTrader engine configuration from our config."""
        try:
            from nautilus_trader.config import BacktestEngineConfig
            return BacktestEngineConfig(
                logging={"log_level": self.config.log_level},
                cache_database=self.config.cache_database,
            )
        except ImportError:
            return None

    def _extract_nautilus_results(
        self,
        engine: Any,
        symbol: str,
        strategy_name: str,
    ) -> NautilusBacktestResult:
        """Extract results from a NautilusTrader BacktestEngine."""
        try:
            account = engine.portfolio.account(engine.venues_list()[0])

            # Get fills/trades
            fills = engine.cache.fills()
            total_trades = len(fills)

            # Calculate metrics from fills
            pnls = [float(fill.last_px) for fill in fills] if fills else []
            wins = [p for p in pnls if p > 0] if pnls else []
            losses = [p for p in pnls if p < 0] if pnls else []

            total_return = float(account.balance_total(USD).as_double())
            starting = self.config.starting_capital
            return_pct = (total_return - starting) / starting if starting > 0 else 0.0

            return NautilusBacktestResult(
                total_return=return_pct,
                sharpe_ratio=0.0,  # Would need equity curve for precise calc
                sortino_ratio=0.0,
                max_drawdown=0.0,
                win_rate=len(wins) / total_trades if total_trades > 0 else 0.0,
                profit_factor=sum(wins) / abs(sum(losses)) if losses and sum(losses) != 0 else 0.0,
                total_trades=total_trades,
                avg_win=np.mean(wins) if wins else 0.0,
                avg_loss=np.mean(losses) if losses else 0.0,
                symbol=symbol,
                strategy_name=strategy_name,
                engine_type="nautilus",
                started_at=datetime.now(),
                finished_at=datetime.now(),
            )
        except Exception as exc:
            logger.error("Failed to extract NautilusTrader results: %s", exc)
            return NautilusBacktestResult(
                symbol=symbol,
                strategy_name=strategy_name,
                engine_type="nautilus",
            )

    # ══════════════════════════════════════════════════════════════════
    # Fallback Backtest (using existing BacktestEngine)
    # ══════════════════════════════════════════════════════════════════

    def run_backtest_fallback(
        self,
        data: pd.DataFrame,
        symbol: str = "EURUSD",
        signal_fn: Any = None,
        strategy_name: str = "unknown",
    ) -> NautilusBacktestResult:
        """
        Run a backtest using the existing internal BacktestEngine.

        This is the fallback when NautilusTrader is not installed.
        It uses the same data but routes through our Python-based
        event-driven backtest engine.

        Args:
            data: OHLCV DataFrame with datetime index.
            symbol: Instrument symbol.
            signal_fn: Signal generation function or strategy.
            strategy_name: Name of the strategy.

        Returns:
            NautilusBacktestResult with performance metrics.
        """
        from quant_nanggroe_ai.backtest.engine import BacktestEngine
        from quant_nanggroe_ai.backtest.metrics import BacktestMetrics

        logger.info("Running fallback backtest for %s", symbol)

        # Create internal engine
        engine = BacktestEngine(
            initial_capital=self.config.starting_capital,
            commission=self.config.commission_rate,
            slippage=self.config.slippage_ticks,
        )

        # Prepare data
        if isinstance(data, pd.DataFrame):
            ohlcv_data = self._prepare_data(data, symbol)
        else:
            ohlcv_data = data

        # Run the backtest
        try:
            result = engine.run(ohlcv_data, signal_fn)
        except Exception as exc:
            logger.error("Fallback backtest failed: %s", exc)
            return NautilusBacktestResult(
                symbol=symbol,
                strategy_name=strategy_name,
                engine_type="fallback",
            )

        # Calculate metrics
        metrics = BacktestMetrics()
        try:
            sharpe = metrics.sharpe_ratio(result.returns) if hasattr(result, 'returns') else 0.0
            sortino = metrics.sortino_ratio(result.returns) if hasattr(result, 'returns') else 0.0
            max_dd = metrics.max_drawdown(result.equity_curve) if hasattr(result, 'equity_curve') else 0.0
        except Exception:
            sharpe = 0.0
            sortino = 0.0
            max_dd = 0.0

        # Map to our result format
        total_return = 0.0
        if hasattr(result, 'total_pnl') and self.config.starting_capital > 0:
            total_return = result.total_pnl / self.config.starting_capital

        win_rate = 0.0
        profit_factor = 0.0
        avg_win = 0.0
        avg_loss = 0.0
        total_trades = 0

        if hasattr(result, 'trades') and result.trades:
            total_trades = len(result.trades)
            wins = [t for t in result.trades if getattr(t, 'pnl', 0) > 0]
            losses = [t for t in result.trades if getattr(t, 'pnl', 0) < 0]
            win_rate = len(wins) / total_trades if total_trades > 0 else 0.0
            avg_win = np.mean([t.pnl for t in wins]) if wins else 0.0
            avg_loss = np.mean([t.pnl for t in losses]) if losses else 0.0
            total_wins = sum(t.pnl for t in wins) if wins else 0.0
            total_losses = abs(sum(t.pnl for t in losses)) if losses else 0.0
            profit_factor = total_wins / total_losses if total_losses > 0 else 0.0

        equity_curve = []
        if hasattr(result, 'equity_curve') and result.equity_curve is not None:
            equity_curve = list(result.equity_curve)

        return NautilusBacktestResult(
            total_return=total_return,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=max_dd,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=total_trades,
            avg_trade_pnl=total_return * self.config.starting_capital / max(total_trades, 1),
            avg_win=avg_win,
            avg_loss=avg_loss,
            equity_curve=equity_curve,
            symbol=symbol,
            strategy_name=strategy_name,
            engine_type="fallback",
            started_at=datetime.now(),
            finished_at=datetime.now(),
        )

    def _prepare_data(
        self,
        df: pd.DataFrame,
        symbol: str,
    ) -> list[dict[str, Any]]:
        """
        Prepare DataFrame data for the internal backtest engine.

        Converts the DataFrame to a list of OHLCV dictionaries
        compatible with BacktestEngine.
        """
        records = []
        for timestamp, row in df.iterrows():
            record = {
                "symbol": symbol,
                "timestamp": pd.Timestamp(timestamp).isoformat(),
                "open": float(row.get("open", 0)),
                "high": float(row.get("high", 0)),
                "low": float(row.get("low", 0)),
                "close": float(row.get("close", 0)),
                "volume": float(row.get("volume", 0)),
            }
            records.append(record)
        return records
