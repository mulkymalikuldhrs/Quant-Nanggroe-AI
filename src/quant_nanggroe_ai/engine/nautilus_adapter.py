"""
NautilusTrader Adapter — Backtest Engine Integration
=====================================================
Bridges the Quant-Nanggroe-AI monorepo with NautilusTrader's
high-performance backtest engine for institutional-grade simulation.

Features:
    - Graceful degradation: works even if nautilus_trader is not installed
    - Configuration via the existing Settings class from config.py
    - Standardized result format (NautilusResults) compatible with the
      monorepo's BacktestResult and metrics pipeline
    - StrategyAdapter base class for converting internal strategies
      to NautilusTrader's Strategy format
    - Lazy imports — nautilus_trader is only loaded when actually needed

Usage:
    from quant_nanggroe_ai.engine.nautilus_adapter import (
        NautilusAdapter,
        BacktestConfig,
        NautilusResults,
        StrategyAdapter,
    )

    config = BacktestConfig(
        symbols=["EURUSD"],
        timeframe="1-HOUR",
        start_date="2024-01-01",
        end_date="2024-12-31",
        initial_capital=100_000,
    )

    adapter = NautilusAdapter(config=config)
    result = adapter.run_backtest(my_strategy_adapter)

Dependencies:
    nautilus_trader (optional) — if not installed, all methods return
    graceful error states rather than raising ImportError at module level.
"""

from __future__ import annotations

import logging
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from quant_nanggroe_ai.config import Settings, get_settings

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════
# NAUTILUS TRADER AVAILABILITY CHECK
# ══════════════════════════════════════════════════════════════════════

_nautilus_available: bool | None = None


def is_nautilus_available() -> bool:
    """
    Check whether the nautilus_trader package is installed and importable.

    The result is cached after the first check so that repeated calls
    are essentially free.

    Returns:
        True if nautilus_trader can be imported, False otherwise.
    """
    global _nautilus_available
    if _nautilus_available is None:
        try:
            import nautilus_trader  # noqa: F401

            _nautilus_available = True
            logger.info("nautilus_trader v%s detected", getattr(nautilus_trader, "__version__", "unknown"))
        except ImportError:
            _nautilus_available = False
            logger.warning(
                "nautilus_trader is not installed — NautilusAdapter will operate "
                "in degraded mode. Install with: pip install nautilus_trader"
            )
    return _nautilus_available


# ══════════════════════════════════════════════════════════════════════
# BACKTEST CONFIGURATION
# ══════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class BacktestConfig:
    """
    Configuration for NautilusTrader backtest runs.

    All fields have sensible defaults aligned with the monorepo's
    constitutional risk limits. The dataclass is frozen to prevent
    accidental mutation after construction.

    Attributes:
        symbols: List of trading instrument symbols (e.g. ["EURUSD", "XAUUSD"]).
        timeframe: Bar aggregation timeframe in NautilusTrader format
            (e.g. "1-MINUTE", "5-MINUTE", "1-HOUR", "1-DAY").
        start_date: Backtest start date in ISO format (e.g. "2024-01-01").
        end_date: Backtest end date in ISO format (e.g. "2024-12-31").
        initial_capital: Starting capital in account currency.
        leverage: Account leverage multiplier (1 = no leverage).
        commission: Commission rate as a fraction of trade value
            (e.g. 0.0002 for 2 basis points).
        slippage: Simulated slippage in price units per trade.
        logging_level: NautilusTrader internal logging verbosity.
            One of "DEBUG", "INFO", "WARNING", "ERROR".
    """

    symbols: list[str] = field(default_factory=lambda: ["EURUSD"])
    timeframe: str = "1-HOUR"
    start_date: str = "2024-01-01"
    end_date: str = "2024-12-31"
    initial_capital: float = 100_000.0
    leverage: int = 1
    commission: float = 0.0002
    slippage: float = 0.0
    logging_level: str = "WARNING"

    def __post_init__(self) -> None:
        """Validate configuration values at construction time."""
        if not self.symbols:
            raise ValueError("BacktestConfig.symbols must contain at least one symbol")
        if self.initial_capital <= 0:
            raise ValueError(f"BacktestConfig.initial_capital must be positive, got {self.initial_capital}")
        if self.leverage < 1:
            raise ValueError(f"BacktestConfig.leverage must be >= 1, got {self.leverage}")
        if self.commission < 0:
            raise ValueError(f"BacktestConfig.commission must be non-negative, got {self.commission}")
        if self.slippage < 0:
            raise ValueError(f"BacktestConfig.slippage must be non-negative, got {self.slippage}")
        # Validate date ordering
        try:
            start = datetime.fromisoformat(self.start_date)
            end = datetime.fromisoformat(self.end_date)
            if start >= end:
                raise ValueError(
                    f"BacktestConfig.start_date ({self.start_date}) must be before "
                    f"end_date ({self.end_date})"
                )
        except ValueError as exc:
            if "must be before" in str(exc) or "must contain" in str(exc):
                raise
            raise ValueError(
                f"BacktestConfig dates must be valid ISO format: {exc}"
            ) from exc

    def to_nautilus_instrument_ids(self) -> list[str]:
        """Convert internal symbol names to NautilusTrader InstrumentId format."""
        return [s.replace("/", "") if "/" in s else s for s in self.symbols]

    def to_nautilus_bar_type(self) -> str:
        """
        Build a NautilusTrader BarType string from the configured timeframe.

        Returns:
            A bar type specification like "EURUSD-1-HOUR-BID-EXTERNAL".
        """
        symbol = self.to_nautilus_instrument_ids()[0]
        return f"{symbol}-{self.timeframe}-BID-EXTERNAL"


# ══════════════════════════════════════════════════════════════════════
# STANDARDIZED BACKTEST RESULTS
# ══════════════════════════════════════════════════════════════════════


class NautilusResults(BaseModel):
    """
    Standardized backtest results from the NautilusTrader adapter.

    This model is intentionally compatible with the monorepo's
    BacktestResult format, allowing downstream consumers (metrics,
    reporting, walk-forward analysis) to work seamlessly regardless
    of which backtest engine produced the results.

    Attributes:
        total_return: Absolute return in currency units.
        sharpe_ratio: Annualized Sharpe ratio.
        max_drawdown: Maximum drawdown as a decimal (e.g. 0.15 = 15%).
        win_rate: Fraction of trades that were profitable (0.0 - 1.0).
        total_trades: Total number of completed trades.
        equity_curve: List of (timestamp, equity) pairs for the equity curve.
        total_return_pct: Return as a percentage of initial capital.
        sortino_ratio: Annualized Sortino ratio.
        profit_factor: Gross profit / gross loss.
        avg_trade_pnl: Average PnL per trade.
        total_commission: Total commission paid during the backtest.
        total_slippage: Total slippage cost during the backtest.
        backtest_config: The BacktestConfig used for this run (serialized).
        engine: Name of the engine that produced these results.
        run_timestamp: When the backtest was executed.
        error: Error message if the backtest failed, None otherwise.
    """

    total_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    equity_curve: list[tuple[str, float]] = Field(default_factory=list)
    total_return_pct: float = 0.0
    sortino_ratio: float = 0.0
    profit_factor: float = 0.0
    avg_trade_pnl: float = 0.0
    total_commission: float = 0.0
    total_slippage: float = 0.0
    backtest_config: dict[str, Any] = Field(default_factory=dict)
    engine: str = "nautilus_adapter"
    run_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None

    def to_backtest_result_compatible(self) -> dict[str, Any]:
        """
        Convert to a dict compatible with the monorepo's BacktestResult.

        This allows seamless integration with the existing metrics
        pipeline and reporting infrastructure.
        """
        from quant_nanggroe_ai.backtest.engine import EquityPoint

        equity_points = [
            EquityPoint(timestamp=ts, equity=eq, cash=eq, positions_value=0.0)
            for ts, eq in self.equity_curve
        ]

        return {
            "initial_capital": self.backtest_config.get("initial_capital", 0),
            "final_equity": self.backtest_config.get("initial_capital", 0) + self.total_return,
            "total_return": self.total_return,
            "total_return_pct": self.total_return_pct,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_pct": self.max_drawdown * 100,
            "total_trades": self.total_trades,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "equity_curve": equity_points,
            "total_commission": self.total_commission,
            "total_slippage": self.total_slippage,
        }

    @property
    def is_successful(self) -> bool:
        """Whether the backtest completed without errors."""
        return self.error is None


# ══════════════════════════════════════════════════════════════════════
# STRATEGY ADAPTER — INTERNAL → NAUTILUSTRADER BRIDGE
# ══════════════════════════════════════════════════════════════════════


@runtime_checkable
class StrategyAdapter(Protocol):
    """
    Protocol (structural subtyping) for converting internal strategies
    to the NautilusTrader Strategy interface.

    Instead of forcing inheritance, this uses Python's Protocol so that
    any object implementing the three callback methods can be used.
    This is more Pythonic and avoids tight coupling to NautilusTrader's
    class hierarchy when nautilus_trader is not installed.

    Implementations must provide:
        - on_bar(): Called on each new bar (OHLCV candle).
        - on_quote_tick(): Called on each quote tick (bid/ask update).
        - on_trade_tick(): Called on each trade tick (last price update).

    Example::

        class MyStrategy:
            def on_bar(self, bar: dict[str, Any]) -> dict[str, Any] | None:
                if bar["close"] > bar["open"]:
                    return {"action": "BUY", "symbol": "EURUSD", "quantity": 1000}
                return None

            def on_quote_tick(self, tick: dict[str, Any]) -> dict[str, Any] | None:
                return None

            def on_trade_tick(self, tick: dict[str, Any]) -> dict[str, Any] | None:
                return None
    """

    def on_bar(self, bar: dict[str, Any]) -> dict[str, Any] | None:
        """
        Process a completed bar (OHLCV candle) and optionally return a signal.

        Args:
            bar: Dict with keys: open, high, low, close, volume, timestamp,
                 and any additional indicators computed by the data pipeline.

        Returns:
            Signal dict with keys:
                - action: "BUY" or "SELL"
                - symbol: str
                - quantity: float (optional)
                - stop_loss: float (optional)
                - take_profit: float (optional)
            Or None for no action.
        """
        ...

    def on_quote_tick(self, tick: dict[str, Any]) -> dict[str, Any] | None:
        """
        Process a quote tick (bid/ask update) and optionally return a signal.

        Args:
            tick: Dict with keys: bid, ask, bid_size, ask_size, timestamp.

        Returns:
            Signal dict or None.
        """
        ...

    def on_trade_tick(self, tick: dict[str, Any]) -> dict[str, Any] | None:
        """
        Process a trade tick (last price update) and optionally return a signal.

        Args:
            tick: Dict with keys: price, size, side, timestamp.

        Returns:
            Signal dict or None.
        """
        ...


class AbstractStrategyAdapter(ABC):
    """
    Abstract base class for strategy adapters that provides a scaffold
    with sensible no-op defaults for quote_tick and trade_tick.

    Subclasses only need to implement on_bar() in most cases, as
    bar-based strategies are the most common pattern.

    Example::

        class MomentumStrategy(AbstractStrategyAdapter):
            def __init__(self, lookback: int = 20):
                self.lookback = lookback
                self._bars: list[dict] = []

            def on_bar(self, bar: dict[str, Any]) -> dict[str, Any] | None:
                self._bars.append(bar)
                if len(self._bars) < self.lookback:
                    return None
                recent = self._bars[-self.lookback:]
                momentum = recent[-1]["close"] - recent[0]["close"]
                if momentum > 0:
                    return {"action": "BUY", "symbol": bar.get("symbol", "EURUSD"), "quantity": 1000}
                elif momentum < 0:
                    return {"action": "SELL", "symbol": bar.get("symbol", "EURUSD"), "quantity": 1000}
                return None
    """

    @abstractmethod
    def on_bar(self, bar: dict[str, Any]) -> dict[str, Any] | None:
        """Process a completed bar and optionally return a trading signal."""
        ...

    def on_quote_tick(self, tick: dict[str, Any]) -> dict[str, Any] | None:
        """
        Process a quote tick. Default implementation returns None (no action).

        Override this for tick-based strategies that react to bid/ask changes.
        """
        return None

    def on_trade_tick(self, tick: dict[str, Any]) -> dict[str, Any] | None:
        """
        Process a trade tick. Default implementation returns None (no action).

        Override this for tick-based strategies that react to last-price changes.
        """
        return None


# ══════════════════════════════════════════════════════════════════════
# INTERNAL HELPERS — METRICS COMPUTATION
# ══════════════════════════════════════════════════════════════════════


def _compute_sharpe(
    returns: list[float],
    risk_free_rate: float = 0.02,
    periods_per_year: int = 252,
) -> float:
    """
    Compute annualized Sharpe ratio from a list of period returns.

    This is a standalone implementation so that NautilusResults can be
    computed even without nautilus_trader installed.
    """
    if len(returns) < 2:
        return 0.0

    mean_r = sum(returns) / len(returns)
    variance = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
    std_r = math.sqrt(variance) if variance > 0 else 0.0

    if std_r == 0:
        return 0.0

    rf_per_period = (1 + risk_free_rate) ** (1 / periods_per_year) - 1
    excess = mean_r - rf_per_period
    sharpe = excess / std_r * math.sqrt(periods_per_year)

    return sharpe if math.isfinite(sharpe) else 0.0


def _compute_sortino(
    returns: list[float],
    risk_free_rate: float = 0.02,
    periods_per_year: int = 252,
) -> float:
    """
    Compute annualized Sortino ratio from a list of period returns.
    """
    if len(returns) < 2:
        return 0.0

    mean_r = sum(returns) / len(returns)
    rf_per_period = (1 + risk_free_rate) ** (1 / periods_per_year) - 1

    downside = [r - rf_per_period for r in returns if r < rf_per_period]
    if not downside:
        return float("inf") if mean_r > rf_per_period else 0.0

    downside_var = sum(d ** 2 for d in downside) / len(downside)
    downside_std = math.sqrt(downside_var) if downside_var > 0 else 0.0

    if downside_std == 0:
        return 0.0

    sortino = (mean_r - rf_per_period) / downside_std * math.sqrt(periods_per_year)
    return sortino if math.isfinite(sortino) else 0.0


def _compute_max_drawdown(equity_curve: list[float]) -> float:
    """
    Compute maximum drawdown from an equity curve as a decimal fraction.

    Returns 0.0 for empty or single-point curves.
    """
    if len(equity_curve) < 2:
        return 0.0

    peak = equity_curve[0]
    max_dd = 0.0

    for value in equity_curve:
        if value > peak:
            peak = value
        if peak > 0:
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd

    return max_dd


def _compute_equity_returns(equity_curve: list[float]) -> list[float]:
    """
    Compute period returns from an equity curve.

    Returns empty list if the curve has fewer than 2 points.
    """
    if len(equity_curve) < 2:
        return []

    returns: list[float] = []
    for i in range(1, len(equity_curve)):
        prev = equity_curve[i - 1]
        if prev > 0:
            returns.append((equity_curve[i] - prev) / prev)
        else:
            returns.append(0.0)

    return returns


# ══════════════════════════════════════════════════════════════════════
# NAUTILUS ADAPTER — MAIN CLASS
# ══════════════════════════════════════════════════════════════════════


class NautilusAdapter:
    """
    Wraps NautilusTrader's backtest engine for the Quant-Nanggroe-AI monorepo.

    This adapter provides a clean, monorepo-compatible interface to
    NautilusTrader's powerful backtesting infrastructure while handling
    the case where nautilus_trader is not installed with graceful
    degradation.

    Configuration is loaded from the monorepo's Settings class, with
    per-run overrides provided via BacktestConfig.

    Workflow:
        1. Instantiate with a BacktestConfig
        2. Optionally load a strategy via load_strategy()
        3. Run the backtest via run_backtest()
        4. Retrieve standardized results via get_results()

    Example::

        config = BacktestConfig(
            symbols=["EURUSD"],
            timeframe="1-HOUR",
            start_date="2024-01-01",
            end_date="2024-06-30",
            initial_capital=100_000,
        )

        adapter = NautilusAdapter(config=config)
        adapter.load_strategy(my_momentum_strategy)

        result = adapter.run_backtest()
        if result.is_successful:
            print(f"Return: {result.total_return_pct:.2f}%")
            print(f"Sharpe: {result.sharpe_ratio:.2f}")
            print(f"Max DD: {result.max_drawdown:.2%}")
        else:
            print(f"Backtest failed: {result.error}")
    """

    def __init__(
        self,
        config: BacktestConfig | None = None,
        settings: Settings | None = None,
    ) -> None:
        """
        Initialize the NautilusTrader adapter.

        Args:
            config: Backtest configuration. If None, a default BacktestConfig
                is created with EURUSD on 1-HOUR timeframe.
            settings: Application settings. If None, loaded from get_settings().

        Raises:
            ValueError: If the configuration is invalid.
        """
        self._config = config or BacktestConfig()
        self._settings = settings or get_settings()
        self._strategy: StrategyAdapter | AbstractStrategyAdapter | None = None
        self._last_results: NautilusResults | None = None
        self._nautilus_engine: Any | None = None
        self._nautilus_cache: Any | None = None

        # Validate that constitutional risk limits are respected
        self._validate_config_against_risk_limits()

        logger.info(
            "NautilusAdapter initialized: symbols=%s, timeframe=%s, "
            "capital=%.2f, leverage=%d",
            self._config.symbols,
            self._config.timeframe,
            self._config.initial_capital,
            self._config.leverage,
        )

    def _validate_config_against_risk_limits(self) -> None:
        """
        Validate that the backtest configuration respects constitutional limits.

        While backtests are simulations and cannot cause real losses,
        validating configuration against risk limits ensures that
        strategies tested under specific risk parameters will also
        be viable under the constitutional limits when deployed live.
        """
        from quant_nanggroe_ai.config import MAX_RISK_PER_TRADE

        # Leverage check: constitutional max is 1 (no leverage)
        if self._config.leverage > 1:
            logger.warning(
                "BacktestConfig.leverage=%d exceeds constitutional max_leverage=1. "
                "This is acceptable for simulation but will be enforced at live trading.",
                self._config.leverage,
            )

    # ──────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────

    def load_strategy(
        self,
        strategy: StrategyAdapter | AbstractStrategyAdapter,
    ) -> None:
        """
        Load a strategy adapter for the next backtest run.

        The strategy must implement the StrategyAdapter protocol
        (on_bar, on_quote_tick, on_trade_tick methods).

        Args:
            strategy: A strategy object implementing the StrategyAdapter protocol.

        Raises:
            TypeError: If the strategy does not implement the required methods.
        """
        required_methods = ("on_bar", "on_quote_tick", "on_trade_tick")
        for method_name in required_methods:
            if not callable(getattr(strategy, method_name, None)):
                raise TypeError(
                    f"Strategy {type(strategy).__name__} must implement "
                    f"a callable '{method_name}' method. "
                    f"See StrategyAdapter protocol for the required interface."
                )

        self._strategy = strategy
        logger.info(
            "Strategy loaded: %s", type(strategy).__name__
        )

    def run_backtest(
        self,
        data: list[dict[str, Any]] | None = None,
        strategy: StrategyAdapter | AbstractStrategyAdapter | None = None,
    ) -> NautilusResults:
        """
        Run a backtest through NautilusTrader's engine.

        If nautilus_trader is not installed, falls back to a built-in
        simplified backtest engine that uses the same StrategyAdapter
        interface, ensuring the monorepo can always execute backtests.

        Args:
            data: Historical OHLCV data as a list of bar dicts. Each dict
                should contain: open, high, low, close, volume, timestamp.
                If None and nautilus_trader is available, data will be loaded
                via NautilusTrader's data catalog.
            strategy: Optional strategy override. If provided, this is used
                instead of the strategy loaded via load_strategy().

        Returns:
            NautilusResults with standardized performance metrics.

        Raises:
            RuntimeError: If no strategy has been loaded and none is provided.
        """
        # Resolve strategy
        active_strategy = strategy or self._strategy
        if active_strategy is None:
            error_msg = (
                "No strategy loaded. Call load_strategy() first or pass "
                "a strategy argument to run_backtest()."
            )
            logger.error(error_msg)
            return NautilusResults(
                error=error_msg,
                backtest_config=self._serialize_config(),
                engine="nautilus_adapter",
            )

        # Attempt NautilusTrader path
        if is_nautilus_available():
            result = self._run_nautilus_backtest(active_strategy, data)
        else:
            result = self._run_fallback_backtest(active_strategy, data)

        self._last_results = result
        return result

    def get_results(self) -> NautilusResults | None:
        """
        Retrieve the results from the most recent backtest run.

        Returns:
            NautilusResults if a backtest has been run, None otherwise.
        """
        return self._last_results

    # ──────────────────────────────────────────────────────────────────
    # NAUTILUSTRADER BACKTEST PATH
    # ──────────────────────────────────────────────────────────────────

    def _run_nautilus_backtest(
        self,
        strategy: StrategyAdapter | AbstractStrategyAdapter,
        data: list[dict[str, Any]] | None,
    ) -> NautilusResults:
        """
        Execute a backtest using the full NautilusTrader engine.

        This method performs lazy imports of nautilus_trader modules
        and sets up the engine, venue, data catalog, and strategy
        wrapper before running the simulation.

        Args:
            strategy: The strategy adapter to wrap and run.
            data: Optional bar data to feed into the engine.

        Returns:
            NautilusResults with metrics extracted from NautilusTrader's
            post-simulation account and fill reports.
        """
        try:
            # ── Lazy imports ──────────────────────────────────────
            from nautilus_trader.backtest.engine import BacktestEngine as NtBacktestEngine
            from nautilus_trader.backtest.engine import BacktestEngineConfig as NtEngineConfig
            from nautilus_trader.config import LoggingConfig
            from nautilus_trader.model.currencies import USD
            from nautilus_trader.model.data import BarType
            from nautilus_trader.model.enums import AccountType, OmsType
            from nautilus_trader.model.identifiers import Venue
            from nautilus_trader.persistence.catalog import ParquetDataCatalog
            from nautilus_trader.test_kit.providers import TestInstrumentProvider

            # ── Build engine ─────────────────────────────────────
            nt_config = NtEngineConfig(
                logging=LoggingConfig(level=self._config.logging_level),
            )
            engine = NtBacktestEngine(config=nt_config)

            # ── Add venue ────────────────────────────────────────
            venue = Venue("SIM")
            engine.add_venue(
                venue=venue,
                oms_type=OmsType.NETTING,
                account_type=AccountType.MARGIN,
                base_currency=None,  # Multi-currency
                starting_balances=[USD(self._config.initial_capital)],
                default_leverage=self._config.leverage,
            )

            # ── Add instruments ──────────────────────────────────
            for symbol in self._config.to_nautilus_instrument_ids():
                instrument = TestInstrumentProvider.default_fx_ccy(
                    symbol.replace("/", ""),
                )
                engine.add_instrument(instrument)

            # ── Wrap our strategy into NautilusTrader Strategy ───
            wrapped = self._wrap_strategy_for_nautilus(strategy, venue)
            engine.add_strategy(wrapped)

            # ── Load data if provided ────────────────────────────
            if data is not None:
                self._load_data_into_engine(engine, data)

            # ── Run ──────────────────────────────────────────────
            logger.info(
                "Starting NautilusTrader backtest: %s symbols, %s → %s",
                self._config.symbols,
                self._config.start_date,
                self._config.end_date,
            )
            engine.run()

            # ── Extract results ──────────────────────────────────
            result = self._extract_nautilus_results(engine)

            self._nautilus_engine = engine
            self._nautilus_cache = engine.cache

            logger.info(
                "NautilusTrader backtest complete: return=%.2f%%, sharpe=%.2f, "
                "max_dd=%.2f%%, trades=%d",
                result.total_return_pct,
                result.sharpe_ratio,
                result.max_drawdown * 100,
                result.total_trades,
            )

            return result

        except Exception as exc:
            logger.error("NautilusTrader backtest failed: %s", exc, exc_info=True)
            # Fall back to simplified engine on NautilusTrader errors
            logger.info("Falling back to simplified backtest engine...")
            return self._run_fallback_backtest(strategy, data)

    def _wrap_strategy_for_nautilus(self, strategy: StrategyAdapter | AbstractStrategyAdapter, venue: Any) -> Any:
        """
        Wrap our StrategyAdapter into a NautilusTrader Strategy subclass.

        This dynamically creates a NautilusTrader-compatible Strategy
        that delegates to our adapter's on_bar/on_quote_tick/on_trade_tick.

        Args:
            strategy: Our internal strategy adapter.
            venue: The NautilusTrader venue identifier.

        Returns:
            A nautilus_trader Strategy instance.
        """
        from nautilus_trader.trading.strategy import Strategy as NtStrategy

        class QNAStrategyWrapper(NtStrategy):
            """NautilusTrader Strategy that delegates to our StrategyAdapter."""

            def __init__(
                self,
                inner_strategy: StrategyAdapter | AbstractStrategyAdapter,
                bar_type_str: str,
                nt_venue: Any,
            ) -> None:
                super().__init__()
                self._inner = inner_strategy
                self._bar_type_str = bar_type_str
                self._venue = nt_venue
                self._bar_type: Any | None = None

            def on_start(self) -> None:
                """Subscribe to bar data on engine start."""
                try:
                    bar_type = BarType.from_str(self._bar_type_str)
                    self._bar_type = bar_type
                    self.subscribe_bars(bar_type)
                except Exception as exc:
                    logger.warning("Could not subscribe to bars: %s", exc)

            def on_bar(self, bar: Any) -> None:
                """Process bar through our adapter and submit orders."""
                bar_dict = {
                    "open": float(bar.open),
                    "high": float(bar.high),
                    "low": float(bar.low),
                    "close": float(bar.close),
                    "volume": float(bar.volume) if bar.volume else 0.0,
                    "timestamp": str(bar.ts_event),
                }

                signal = self._inner.on_bar(bar_dict)
                if signal is not None:
                    self._submit_signal(signal)

            def on_quote_tick(self, tick: Any) -> None:
                """Process quote tick through our adapter."""
                tick_dict = {
                    "bid": float(tick.bid_price),
                    "ask": float(tick.ask_price),
                    "bid_size": float(tick.bid_size) if hasattr(tick, "bid_size") else 0.0,
                    "ask_size": float(tick.ask_size) if hasattr(tick, "ask_size") else 0.0,
                    "timestamp": str(tick.ts_event),
                }
                signal = self._inner.on_quote_tick(tick_dict)
                if signal is not None:
                    self._submit_signal(signal)

            def on_trade_tick(self, tick: Any) -> None:
                """Process trade tick through our adapter."""
                tick_dict = {
                    "price": float(tick.price),
                    "size": float(tick.size) if hasattr(tick, "size") else 0.0,
                    "side": str(tick.aggressor_side) if hasattr(tick, "aggressor_side") else "",
                    "timestamp": str(tick.ts_event),
                }
                signal = self._inner.on_trade_tick(tick_dict)
                if signal is not None:
                    self._submit_signal(signal)

            def _submit_signal(self, signal: dict[str, Any]) -> None:
                """Convert our signal dict into NautilusTrader orders."""
                try:
                    from nautilus_trader.model.enums import OrderSide
                    from nautilus_trader.model.identifiers import InstrumentId
                    from nautilus_trader.model.orders import MarketOrder

                    action = signal.get("action", "").upper()
                    symbol_str = signal.get("symbol", "")
                    quantity = signal.get("quantity", 1.0)

                    if not action or not symbol_str:
                        return

                    side = OrderSide.BUY if action in ("BUY", "LONG") else OrderSide.SELL
                    instrument_id = InstrumentId.from_str(f"{symbol_str}.{self._venue}")

                    order = MarketOrder(
                        instrument_id=instrument_id,
                        order_side=side,
                        quantity=self.instrument.make_qty(quantity),
                    )
                    self.submit_order(order)

                except Exception as exc:
                    logger.warning("Failed to submit order: %s", exc)

            def on_stop(self) -> None:
                """Unsubscribe on engine stop."""
                if self._bar_type is not None:
                    self.unsubscribe_bars(self._bar_type)

        return QNAStrategyWrapper(
            inner_strategy=strategy,
            bar_type_str=self._config.to_nautilus_bar_type(),
            nt_venue=venue,
        )

    def _load_data_into_engine(
        self,
        engine: Any,
        data: list[dict[str, Any]],
    ) -> None:
        """
        Load bar data into the NautilusTrader engine.

        Converts our internal bar format into NautilusTrader Bar objects
        and adds them to the engine's data catalog.

        Args:
            engine: NautilusTrader BacktestEngine instance.
            data: List of bar dicts with OHLCV data.
        """
        try:
            from nautilus_trader.model.data import Bar, BarType, BarSpecification
            from nautilus_trader.model.identifiers import InstrumentId, Venue
            from nautilus_trader.core.datetime import dt_to_unix_nanos

            symbol = self._config.to_nautilus_instrument_ids()[0]
            venue = Venue("SIM")
            instrument_id = InstrumentId.from_str(f"{symbol}.{venue}")
            bar_type = BarType.from_str(self._config.to_nautilus_bar_type())

            bars: list[Any] = []
            for bar_dict in data:
                try:
                    ts = bar_dict.get("timestamp", "")
                    if isinstance(ts, str) and ts:
                        dt = datetime.fromisoformat(ts)
                    else:
                        dt = datetime.now(timezone.utc)

                    bar = Bar(
                        bar_type=bar_type,
                        open=self.instrument.make_price(bar_dict.get("open", 0)),
                        high=self.instrument.make_price(bar_dict.get("high", 0)),
                        low=self.instrument.make_price(bar_dict.get("low", 0)),
                        close=self.instrument.make_price(bar_dict.get("close", 0)),
                        volume=self.instrument.make_qty(bar_dict.get("volume", 0)),
                        ts_event=dt_to_unix_nanos(dt),
                        ts_init=dt_to_unix_nanos(dt),
                    )
                    bars.append(bar)
                except Exception as exc:
                    logger.warning("Skipping malformed bar: %s", exc)
                    continue

            if bars:
                engine.add_data(bars)

        except Exception as exc:
            logger.warning(
                "Could not load data into NautilusTrader engine: %s. "
                "Engine will run without pre-loaded data.",
                exc,
            )

    def _extract_nautilus_results(self, engine: Any) -> NautilusResults:
        """
        Extract standardized results from a NautilusTrader engine after a run.

        Args:
            engine: The completed NautilusTrader BacktestEngine.

        Returns:
            NautilusResults with metrics computed from the engine's state.
        """
        try:
            # Extract account info
            account = engine.portfolio.account(venue=None)

            # Build equity curve from the account's balance history
            equity_curve: list[tuple[str, float]] = []
            if hasattr(account, "balance"):
                balance = float(account.balance_as_double())
                equity_curve.append(
                    (datetime.now(timezone.utc).isoformat(), balance)
                )

            # Extract fill/trade statistics
            fills = engine.cache.fills() if hasattr(engine.cache, "fills") else []
            total_trades = len(fills)

            # Compute PnL
            total_pnl = 0.0
            winning = 0
            losing = 0
            total_commission = 0.0

            for fill in fills:
                try:
                    pnl = float(fill.last_px) - float(fill.avg_px) if hasattr(fill, "last_px") else 0.0
                    total_pnl += pnl
                    commission = float(fill.commission) if hasattr(fill, "commission") else 0.0
                    total_commission += commission
                    if pnl > 0:
                        winning += 1
                    else:
                        losing += 1
                except (TypeError, ValueError):
                    continue

            win_rate = winning / total_trades if total_trades > 0 else 0.0
            initial = self._config.initial_capital
            total_return = total_pnl
            total_return_pct = (total_return / initial * 100) if initial > 0 else 0.0

            # Compute equity-only values for metrics
            equity_values = [eq for _, eq in equity_curve]
            returns = _compute_equity_returns(equity_values) if len(equity_values) > 1 else []

            return NautilusResults(
                total_return=round(total_return, 2),
                sharpe_ratio=round(_compute_sharpe(returns), 4) if returns else 0.0,
                max_drawdown=round(_compute_max_drawdown(equity_values), 4) if len(equity_values) > 1 else 0.0,
                win_rate=round(win_rate, 4),
                total_trades=total_trades,
                equity_curve=equity_curve,
                total_return_pct=round(total_return_pct, 4),
                sortino_ratio=round(_compute_sortino(returns), 4) if returns else 0.0,
                avg_trade_pnl=round(total_pnl / total_trades, 2) if total_trades > 0 else 0.0,
                total_commission=round(total_commission, 2),
                backtest_config=self._serialize_config(),
                engine="nautilus_trader",
            )

        except Exception as exc:
            logger.error("Failed to extract NautilusTrader results: %s", exc)
            return NautilusResults(
                error=f"Result extraction failed: {exc}",
                backtest_config=self._serialize_config(),
                engine="nautilus_trader",
            )

    # ──────────────────────────────────────────────────────────────────
    # FALLBACK BACKTEST PATH (no nautilus_trader required)
    # ──────────────────────────────────────────────────────────────────

    def _run_fallback_backtest(
        self,
        strategy: StrategyAdapter | AbstractStrategyAdapter,
        data: list[dict[str, Any]] | None,
    ) -> NautilusResults:
        """
        Execute a simplified bar-by-bar backtest when NautilusTrader
        is not available.

        This fallback engine iterates through bars, calls the strategy's
        on_bar method, and simulates order fills with commission and
        slippage. It is NOT as accurate as NautilusTrader but provides
        a usable backtest in any environment.

        Args:
            strategy: The strategy adapter to run.
            data: OHLCV bar data as a list of dicts.

        Returns:
            NautilusResults with metrics from the simplified simulation.
        """
        if data is None or len(data) == 0:
            return NautilusResults(
                error="No data provided and nautilus_trader not available for data catalog",
                backtest_config=self._serialize_config(),
                engine="nautilus_adapter_fallback",
            )

        initial_capital = self._config.initial_capital
        commission_rate = self._config.commission
        slippage_amount = self._config.slippage

        cash = initial_capital
        positions: dict[str, dict[str, Any]] = {}  # symbol → {side, qty, entry_price, entry_time}
        equity_curve: list[tuple[str, float]] = []
        closed_pnls: list[float] = []
        total_commission = 0.0
        total_slippage = 0.0

        logger.info(
            "Running fallback backtest: %d bars, capital=%.2f",
            len(data), initial_capital,
        )

        for bar_idx, bar in enumerate(data):
            # Update unrealized PnL for open positions
            current_prices: dict[str, float] = {}
            for sym in list(positions.keys()):
                if sym in bar:
                    current_prices[sym] = bar[sym]
                elif "close" in bar:
                    current_prices[sym] = float(bar["close"])

            # Calculate current equity
            positions_value = 0.0
            for sym, pos in positions.items():
                price = current_prices.get(sym, pos["entry_price"])
                if pos["side"] in ("BUY", "LONG"):
                    positions_value += pos["qty"] * price
                else:
                    positions_value += pos["qty"] * (2 * pos["entry_price"] - price)

            equity = cash + positions_value

            # Enrich bar with symbol info for the strategy
            enriched_bar = {
                **bar,
                "_bar_idx": bar_idx,
                "_equity": equity,
                "_open_positions": len(positions),
            }

            # Call strategy
            try:
                signal = strategy.on_bar(enriched_bar)
            except Exception as exc:
                logger.warning("Strategy error at bar %d: %s", bar_idx, exc)
                signal = None

            # Process signal
            if signal is not None:
                action = signal.get("action", "").upper()
                symbol = signal.get("symbol", self._config.symbols[0])
                quantity = signal.get("quantity", 1.0)
                stop_loss = signal.get("stop_loss")
                take_profit = signal.get("take_profit")

                current_price = float(
                    bar.get("close", bar.get(symbol, 0))
                )
                if current_price <= 0:
                    continue

                if action in ("BUY", "LONG"):
                    # Close existing short position if any
                    if symbol in positions and positions[symbol]["side"] in ("SELL", "SHORT"):
                        pos = positions.pop(symbol)
                        fill_price = current_price + slippage_amount
                        pnl = (pos["entry_price"] - fill_price) * pos["qty"]
                        comm = fill_price * pos["qty"] * commission_rate
                        total_commission += comm
                        pnl -= comm
                        total_slippage += slippage_amount * pos["qty"]
                        cash += pos["entry_price"] * pos["qty"] + pnl
                        closed_pnls.append(pnl)

                    # Open long position if not already holding
                    if symbol not in positions:
                        fill_price = current_price + slippage_amount
                        cost = fill_price * quantity
                        comm = cost * commission_rate
                        total_commission += comm
                        total_slippage += slippage_amount * quantity

                        if cash >= cost + comm:
                            cash -= cost + comm
                            positions[symbol] = {
                                "side": "BUY",
                                "qty": quantity,
                                "entry_price": fill_price,
                                "entry_time": bar.get("timestamp", str(bar_idx)),
                                "stop_loss": stop_loss,
                                "take_profit": take_profit,
                            }

                elif action in ("SELL", "SHORT"):
                    # Close existing long position if any
                    if symbol in positions and positions[symbol]["side"] in ("BUY", "LONG"):
                        pos = positions.pop(symbol)
                        fill_price = current_price - slippage_amount
                        pnl = (fill_price - pos["entry_price"]) * pos["qty"]
                        comm = fill_price * pos["qty"] * commission_rate
                        total_commission += comm
                        pnl -= comm
                        total_slippage += slippage_amount * pos["qty"]
                        cash += fill_price * pos["qty"] - comm
                        closed_pnls.append(pnl)

            # Check stop loss / take profit for open positions
            for sym in list(positions.keys()):
                pos = positions[sym]
                current_price = float(
                    bar.get("close", bar.get(sym, pos["entry_price"]))
                )

                exit_triggered = False
                exit_reason = ""

                if pos["stop_loss"] is not None:
                    if pos["side"] in ("BUY", "LONG") and current_price <= pos["stop_loss"]:
                        exit_triggered = True
                        exit_reason = "stop_loss"
                    elif pos["side"] in ("SELL", "SHORT") and current_price >= pos["stop_loss"]:
                        exit_triggered = True
                        exit_reason = "stop_loss"

                if not exit_triggered and pos["take_profit"] is not None:
                    if pos["side"] in ("BUY", "LONG") and current_price >= pos["take_profit"]:
                        exit_triggered = True
                        exit_reason = "take_profit"
                    elif pos["side"] in ("SELL", "SHORT") and current_price <= pos["take_profit"]:
                        exit_triggered = True
                        exit_reason = "take_profit"

                if exit_triggered:
                    pos = positions.pop(sym)
                    if pos["side"] in ("BUY", "LONG"):
                        fill_price = current_price - slippage_amount
                        pnl = (fill_price - pos["entry_price"]) * pos["qty"]
                    else:
                        fill_price = current_price + slippage_amount
                        pnl = (pos["entry_price"] - fill_price) * pos["qty"]

                    comm = fill_price * pos["qty"] * commission_rate
                    total_commission += comm
                    pnl -= comm
                    total_slippage += slippage_amount * pos["qty"]
                    cash += fill_price * pos["qty"] - comm
                    closed_pnls.append(pnl)

            # Record equity curve point
            # Recalculate equity after processing
            positions_value = 0.0
            for sym, pos in positions.items():
                price = float(bar.get("close", bar.get(sym, pos["entry_price"])))
                if pos["side"] in ("BUY", "LONG"):
                    positions_value += pos["qty"] * price
                else:
                    positions_value += pos["qty"] * (2 * pos["entry_price"] - price)

            equity = cash + positions_value
            ts = bar.get("timestamp", str(bar_idx))
            if not isinstance(ts, str):
                ts = str(ts)
            equity_curve.append((ts, round(equity, 2)))

        # ── Close remaining positions at last bar ────────────────
        if data:
            last_bar = data[-1]
            for sym in list(positions.keys()):
                pos = positions.pop(sym)
                current_price = float(
                    last_bar.get("close", last_bar.get(sym, pos["entry_price"]))
                )
                if pos["side"] in ("BUY", "LONG"):
                    fill_price = current_price - slippage_amount
                    pnl = (fill_price - pos["entry_price"]) * pos["qty"]
                else:
                    fill_price = current_price + slippage_amount
                    pnl = (pos["entry_price"] - fill_price) * pos["qty"]

                comm = fill_price * pos["qty"] * commission_rate
                total_commission += comm
                pnl -= comm
                total_slippage += slippage_amount * pos["qty"]
                cash += fill_price * pos["qty"] - comm
                closed_pnls.append(pnl)

        # ── Compute final metrics ────────────────────────────────
        final_equity = cash
        total_return = final_equity - initial_capital
        total_return_pct = (total_return / initial_capital * 100) if initial_capital > 0 else 0.0

        equity_values = [eq for _, eq in equity_curve]
        returns = _compute_equity_returns(equity_values)

        total_trades = len(closed_pnls)
        winning = sum(1 for p in closed_pnls if p > 0)
        win_rate = winning / total_trades if total_trades > 0 else 0.0

        gross_profit = sum(p for p in closed_pnls if p > 0)
        gross_loss = abs(sum(p for p in closed_pnls if p < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0)

        avg_trade_pnl = sum(closed_pnls) / total_trades if total_trades > 0 else 0.0

        result = NautilusResults(
            total_return=round(total_return, 2),
            sharpe_ratio=round(_compute_sharpe(returns), 4),
            max_drawdown=round(_compute_max_drawdown(equity_values), 4),
            win_rate=round(win_rate, 4),
            total_trades=total_trades,
            equity_curve=equity_curve,
            total_return_pct=round(total_return_pct, 4),
            sortino_ratio=round(_compute_sortino(returns), 4),
            profit_factor=round(profit_factor, 4) if math.isfinite(profit_factor) else 0.0,
            avg_trade_pnl=round(avg_trade_pnl, 2),
            total_commission=round(total_commission, 2),
            total_slippage=round(total_slippage, 4),
            backtest_config=self._serialize_config(),
            engine="nautilus_adapter_fallback",
        )

        logger.info(
            "Fallback backtest complete: return=%.2f%%, sharpe=%.2f, "
            "max_dd=%.2f%%, trades=%d",
            result.total_return_pct,
            result.sharpe_ratio,
            result.max_drawdown * 100,
            result.total_trades,
        )

        return result

    # ──────────────────────────────────────────────────────────────────
    # INTERNAL HELPERS
    # ──────────────────────────────────────────────────────────────────

    def _serialize_config(self) -> dict[str, Any]:
        """
        Serialize the current BacktestConfig into a plain dict for
        inclusion in NautilusResults.
        """
        return {
            "symbols": self._config.symbols,
            "timeframe": self._config.timeframe,
            "start_date": self._config.start_date,
            "end_date": self._config.end_date,
            "initial_capital": self._config.initial_capital,
            "leverage": self._config.leverage,
            "commission": self._config.commission,
            "slippage": self._config.slippage,
        }

    def status(self) -> dict[str, Any]:
        """
        Get the current adapter status.

        Returns:
            Dict with adapter state including nautilus availability,
            loaded strategy, and last results summary.
        """
        return {
            "nautilus_available": is_nautilus_available(),
            "strategy_loaded": self._strategy is not None,
            "strategy_name": type(self._strategy).__name__ if self._strategy else None,
            "config": self._serialize_config(),
            "last_run": (
                {
                    "engine": self._last_results.engine,
                    "total_return_pct": self._last_results.total_return_pct,
                    "sharpe_ratio": self._last_results.sharpe_ratio,
                    "total_trades": self._last_results.total_trades,
                    "is_successful": self._last_results.is_successful,
                    "error": self._last_results.error,
                }
                if self._last_results is not None
                else None
            ),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
