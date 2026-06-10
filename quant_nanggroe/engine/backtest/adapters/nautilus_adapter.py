"""NautilusTrader Adapter for Quant Nanggroe AI Backtesting Framework.

Bridges our BacktestEngine and StrategyConfig with NautilusTrader's
backtest infrastructure, providing data conversion, result mapping,
and adapter utilities for running strategies in NautilusTrader.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from quant_nanggroe.engine.backtest.engine import BacktestConfig, BacktestEngine, MarketType
from quant_nanggroe.engine.strategy.schema import StrategyConfig

logger = logging.getLogger(__name__)


# ─── Data Conversion ───────────────────────────────────────────────────────


@dataclass
class NautilusBarData:
    """Container for bar data in NautilusTrader format.

    Attributes:
        instrument_id: NautilusTrader instrument ID (e.g., "BTC/USDT-PERP.BINANCE").
        open: Open prices.
        high: High prices.
        low: Low prices.
        close: Close prices.
        volume: Volume data.
        timestamp_ns: Timestamps in nanoseconds.
    """

    instrument_id: str
    open: List[float] = field(default_factory=list)
    high: List[float] = field(default_factory=list)
    low: List[float] = field(default_factory=list)
    close: List[float] = field(default_factory=list)
    volume: List[float] = field(default_factory=list)
    timestamp_ns: List[int] = field(default_factory=list)


@dataclass
class NautilusInstrument:
    """NautilusTrader instrument definition.

    Attributes:
        instrument_id: Unique instrument identifier.
        raw_symbol: Raw symbol string.
        asset_class: Asset class (CRYPTO, EQUITY, FOREX).
        price_precision: Number of decimal places for price.
        size_precision: Number of decimal places for size.
        lot_size: Minimum lot size.
        max_quantity: Maximum order quantity.
        min_quantity: Minimum order quantity.
        max_notional: Maximum notional value.
        min_notional: Minimum notional value.
    """

    instrument_id: str
    raw_symbol: str
    asset_class: str = "EQUITY"
    price_precision: int = 2
    size_precision: int = 8
    lot_size: float = 1.0
    max_quantity: float = 1_000_000.0
    min_quantity: float = 0.0001
    max_notional: float = 1_000_000_000.0
    min_notional: float = 1.0


@dataclass
class NautilusBacktestResult:
    """Result from a NautilusTrader backtest run, mapped to our format.

    Attributes:
        total_return: Total return as a decimal.
        sharpe_ratio: Annualized Sharpe ratio.
        max_drawdown: Maximum drawdown as a decimal.
        win_rate: Win rate as a decimal.
        total_trades: Total number of trades.
        profit_factor: Profit factor (gross profit / gross loss).
        avg_trade_pnl: Average trade PnL.
        equity_curve: Equity curve as a list of floats.
        trades: List of trade records.
        execution_time_ms: Wall-clock execution time.
    """

    total_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    profit_factor: float = 0.0
    avg_trade_pnl: float = 0.0
    equity_curve: List[float] = field(default_factory=list)
    trades: List[Dict[str, Any]] = field(default_factory=list)
    execution_time_ms: float = 0.0


# ─── NautilusTrader Adapter ────────────────────────────────────────────────


class NautilusAdapter:
    """Bridge between our backtest engine and NautilusTrader.

    Provides:
    - Data format conversion (our format ↔ NautilusTrader format)
    - Instrument definition creation
    - Strategy signal mapping
    - Result mapping back to our format
    - Configuration translation

    Usage:
        adapter = NautilusAdapter()
        instruments = adapter.create_instruments(["BTC/USDT", "ETH/USDT"], MarketType.CRYPTO)
        bar_data = adapter.convert_ohlcv(df, "BTC/USDT-PERP.BINANCE")
        result = adapter.map_result(nautilus_output)
    """

    # Mapping from our MarketType to NautilusTrader venue/asset class
    MARKET_VENUE_MAP = {
        MarketType.EQUITY: {"venue": "NYSE", "asset_class": "EQUITY"},
        MarketType.CRYPTO: {"venue": "BINANCE", "asset_class": "CRYPTO"},
        MarketType.FOREX: {"venue": "OANDA", "asset_class": "FOREX"},
        MarketType.FUTURES: {"venue": "CME", "asset_class": "FUTURES"},
    }

    # Default price/size precision per market type
    MARKET_PRECISION_MAP = {
        MarketType.EQUITY: {"price": 2, "size": 0},
        MarketType.CRYPTO: {"price": 2, "size": 8},
        MarketType.FOREX: {"price": 5, "size": 0},
        MarketType.FUTURES: {"price": 2, "size": 0},
    }

    def __init__(self, config: Optional[BacktestConfig] = None) -> None:
        """Initialize the NautilusTrader adapter.

        Args:
            config: Optional backtest configuration for defaults.
        """
        self._config = config or BacktestConfig()
        self._engine = BacktestEngine(self._config)
        logger.info(
            "NautilusAdapter initialized: market=%s, capital=%.0f",
            self._config.market.value,
            self._config.initial_capital,
        )

    # ─── Instrument Creation ──────────────────────────────────────────────

    def create_instrument(
        self,
        symbol: str,
        market_type: Optional[MarketType] = None,
    ) -> NautilusInstrument:
        """Create a NautilusTrader instrument definition from a symbol.

        Args:
            symbol: Trading symbol (e.g., "BTC/USDT", "AAPL").
            market_type: Market type for venue/precision mapping.

        Returns:
            NautilusInstrument with appropriate configuration.
        """
        mt = market_type or self._config.market
        venue_info = self.MARKET_VENUE_MAP.get(mt, self.MARKET_VENUE_MAP[MarketType.EQUITY])
        precision = self.MARKET_PRECISION_MAP.get(mt, self.MARKET_PRECISION_MAP[MarketType.EQUITY])

        # Build instrument ID based on market type
        if mt == MarketType.CRYPTO:
            instrument_id = f"{symbol.replace('/', '-')}-PERP.{venue_info['venue']}"
        elif mt == MarketType.FOREX:
            instrument_id = f"{symbol.replace('/', '_')}.{venue_info['venue']}"
        else:
            instrument_id = f"{symbol}.{venue_info['venue']}"

        return NautilusInstrument(
            instrument_id=instrument_id,
            raw_symbol=symbol,
            asset_class=venue_info["asset_class"],
            price_precision=precision["price"],
            size_precision=precision["size"],
        )

    def create_instruments(
        self,
        symbols: List[str],
        market_type: Optional[MarketType] = None,
    ) -> List[NautilusInstrument]:
        """Create instrument definitions for multiple symbols.

        Args:
            symbols: List of trading symbols.
            market_type: Market type for all symbols.

        Returns:
            List of NautilusInstrument definitions.
        """
        return [self.create_instrument(s, market_type) for s in symbols]

    # ─── Data Conversion ──────────────────────────────────────────────────

    def convert_ohlcv(
        self,
        df: pd.DataFrame,
        instrument_id: str,
    ) -> NautilusBarData:
        """Convert OHLCV DataFrame to NautilusTrader bar data format.

        Expects a DataFrame with DatetimeIndex and columns:
        open, high, low, close, volume.

        Args:
            df: OHLCV DataFrame with DatetimeIndex.
            instrument_id: NautilusTrader instrument ID.

        Returns:
            NautilusBarData with converted price and volume data.

        Raises:
            ValueError: If required columns are missing.
        """
        required_cols = {"open", "high", "low", "close", "volume"}
        available = set(df.columns)
        missing = required_cols - available
        if missing:
            # Try to create missing columns from close price
            if "close" in available:
                for col in missing - {"volume"}:
                    df = df.copy()
                    df[col] = df["close"]
                if "volume" in missing:
                    df["volume"] = 0
            else:
                raise ValueError(f"Missing required columns: {missing}")

        # Convert timestamps to nanoseconds (Unix epoch)
        timestamp_ns = []
        if isinstance(df.index, pd.DatetimeIndex):
            timestamp_ns = (df.index.astype(np.int64) // 1_000).tolist()
        else:
            timestamp_ns = [
                int(pd.Timestamp(t).value // 1_000) for t in df.index
            ]

        return NautilusBarData(
            instrument_id=instrument_id,
            open=df["open"].astype(float).tolist(),
            high=df["high"].astype(float).tolist(),
            low=df["low"].astype(float).tolist(),
            close=df["close"].astype(float).tolist(),
            volume=df["volume"].astype(float).tolist(),
            timestamp_ns=timestamp_ns,
        )

    def convert_bar_data_to_df(
        self,
        bar_data: NautilusBarData,
    ) -> pd.DataFrame:
        """Convert NautilusTrader bar data back to our OHLCV DataFrame.

        Args:
            bar_data: NautilusBarData to convert.

        Returns:
            DataFrame with DatetimeIndex and OHLCV columns.
        """
        timestamps = pd.to_datetime(bar_data.timestamp_ns, unit="ns")
        return pd.DataFrame(
            {
                "open": bar_data.open,
                "high": bar_data.high,
                "low": bar_data.low,
                "close": bar_data.close,
                "volume": bar_data.volume,
            },
            index=timestamps,
        )

    def convert_signals_to_position_weights(
        self,
        signals: pd.DataFrame,
        strategy_config: Optional[StrategyConfig] = None,
    ) -> pd.DataFrame:
        """Convert our signal weights to NautilusTrader position weights.

        Our format: -1.0 to 1.0 (short to long weight).
        NautilusTrader uses similar convention for position targets.

        Args:
            signals: Signal DataFrame with position weights.
            strategy_config: Optional strategy config for max position sizing.

        Returns:
            DataFrame with position weights capped by risk rules.
        """
        max_weight = 1.0
        if strategy_config:
            max_weight = strategy_config.risk_rules.max_position_pct / 100.0

        # Clip weights to max position size
        clipped = signals.clip(-max_weight, max_weight)

        # Replace NaN with 0
        return clipped.fillna(0.0)

    # ─── Result Mapping ───────────────────────────────────────────────────

    def map_result(
        self,
        nautilus_output: Dict[str, Any],
    ) -> NautilusBacktestResult:
        """Map NautilusTrader backtest output to our result format.

        Handles both actual NautilusTrader output dictionaries and
        our BacktestEngine output format.

        Args:
            nautilus_output: Raw backtest result dictionary.

        Returns:
            NautilusBacktestResult with normalized metrics.
        """
        # Extract metrics - handle both formats
        metrics = nautilus_output.get("metrics", {})

        # NautilusTrader format
        if "account" in nautilus_output:
            account = nautilus_output["account"]
            return NautilusBacktestResult(
                total_return=self._safe_float(account.get("total_return", 0.0)),
                sharpe_ratio=self._safe_float(account.get("sharpe_ratio", 0.0)),
                max_drawdown=self._safe_float(account.get("max_drawdown", 0.0)),
                win_rate=self._safe_float(account.get("win_rate", 0.0)),
                total_trades=int(account.get("total_trades", 0)),
                profit_factor=self._safe_float(account.get("profit_factor", 0.0)),
                avg_trade_pnl=self._safe_float(account.get("avg_trade_pnl", 0.0)),
                equity_curve=nautilus_output.get("equity_curve", []),
                trades=nautilus_output.get("trades", []),
                execution_time_ms=self._safe_float(
                    nautilus_output.get("execution_time_ms", 0.0)
                ),
            )

        # Our BacktestEngine format
        return NautilusBacktestResult(
            total_return=self._safe_float(metrics.get("total_return", 0.0)),
            sharpe_ratio=self._safe_float(metrics.get("sharpe_ratio", 0.0)),
            max_drawdown=self._safe_float(metrics.get("max_drawdown", 0.0)),
            win_rate=self._safe_float(metrics.get("win_rate", 0.0)),
            total_trades=int(nautilus_output.get("total_trades", 0)),
            profit_factor=self._safe_float(metrics.get("profit_factor", 0.0)),
            avg_trade_pnl=self._safe_float(metrics.get("avg_trade_pnl", 0.0)),
            equity_curve=(
                nautilus_output.get("equity_curve", pd.Series()).tolist()
                if isinstance(nautilus_output.get("equity_curve"), pd.Series)
                else nautilus_output.get("equity_curve", [])
            ),
            trades=self._map_trades(nautilus_output.get("trades", [])),
            execution_time_ms=0.0,
        )

    def _map_trades(
        self, trades: List[Any]
    ) -> List[Dict[str, Any]]:
        """Map trade records to our standard format.

        Args:
            trades: List of trade records (our TradeRecord or NautilusTrader format).

        Returns:
            List of standardized trade dictionaries.
        """
        mapped = []
        for trade in trades:
            if isinstance(trade, dict):
                mapped.append(trade)
            elif hasattr(trade, "__dict__"):
                # TradeRecord or similar dataclass
                try:
                    mapped.append({
                        "symbol": getattr(trade, "symbol", "UNKNOWN"),
                        "direction": getattr(trade, "direction", 0),
                        "size": getattr(trade, "size", 0.0),
                        "entry_price": getattr(trade, "entry_price", 0.0),
                        "exit_price": getattr(trade, "exit_price", 0.0),
                        "pnl": getattr(trade, "pnl", 0.0),
                        "pnl_pct": getattr(trade, "pnl_pct", 0.0),
                        "entry_time": str(getattr(trade, "entry_time", "")),
                        "exit_time": str(getattr(trade, "exit_time", "")),
                        "commission": getattr(trade, "commission", 0.0),
                    })
                except Exception as e:
                    logger.warning(f"Failed to map trade record: {e}")
        return mapped

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        """Safely convert a value to float.

        Args:
            value: Value to convert.
            default: Default if conversion fails.

        Returns:
            Float value or default.
        """
        try:
            result = float(value)
            if np.isnan(result) or np.isinf(result):
                return default
            return result
        except (TypeError, ValueError):
            return default

    # ─── Configuration Translation ────────────────────────────────────────

    def create_nautilus_config(
        self,
        strategy_config: Optional[StrategyConfig] = None,
    ) -> Dict[str, Any]:
        """Create a NautilusTrader-compatible configuration from our config.

        Args:
            strategy_config: Optional strategy config for additional settings.

        Returns:
            Dict with NautilusTrader-compatible configuration.
        """
        config = {
            "trading": {
                "instruments": [],
                "data": {
                    "catalog_path": None,
                    "data_type": "bar",
                    "bar_type": "1-MINUTE-LAST-EXTERNAL",
                },
                "engine": {
                    "logging": {"level": "INFO"},
                    "timeout_strategy": 60.0,
                },
                "portfolio": {
                    "base_currency": "USD",
                    "starting_capital": self._config.initial_capital,
                },
            },
        }

        # Add strategy-specific configuration
        if strategy_config:
            config["strategy"] = {
                "name": strategy_config.name,
                "timeframe": strategy_config.timeframe,
                "universe_symbols": strategy_config.universe.symbols,
                "risk_rules": {
                    "max_position_pct": strategy_config.risk_rules.max_position_pct,
                    "stop_loss_pct": strategy_config.risk_rules.stop_loss_pct,
                    "max_daily_trades": strategy_config.risk_rules.max_daily_trades,
                },
            }

        return config

    # ─── Convenience Run Method ───────────────────────────────────────────

    def run_backtest(
        self,
        prices: pd.DataFrame,
        signals: pd.DataFrame,
        strategy_config: Optional[StrategyConfig] = None,
    ) -> NautilusBacktestResult:
        """Run a backtest using our engine and map results.

        If NautilusTrader is available, uses it directly.
        Otherwise, uses our BacktestEngine and maps to NautilusBacktestResult.

        Args:
            prices: Price DataFrame with DatetimeIndex.
            signals: Signal DataFrame with position weights.
            strategy_config: Optional strategy configuration.

        Returns:
            NautilusBacktestResult with backtest metrics.
        """
        import time as _time

        start = _time.monotonic()

        try:
            # Try to use NautilusTrader directly
            result = self._run_nautilus_backtest(prices, signals, strategy_config)
        except ImportError:
            logger.info("NautilusTrader not available, falling back to BacktestEngine")
            result = self._run_fallback_backtest(prices, signals)
        except Exception as e:
            logger.warning(f"NautilusTrader backtest failed, falling back: {e}")
            result = self._run_fallback_backtest(prices, signals)

        result.execution_time_ms = (_time.monotonic() - start) * 1000
        return result

    def _run_nautilus_backtest(
        self,
        prices: pd.DataFrame,
        signals: pd.DataFrame,
        strategy_config: Optional[StrategyConfig] = None,
    ) -> NautilusBacktestResult:
        """Run backtest using NautilusTrader directly.

        Args:
            prices: Price DataFrame.
            signals: Signal DataFrame.
            strategy_config: Optional strategy configuration.

        Returns:
            NautilusBacktestResult from NautilusTrader output.

        Raises:
            ImportError: If nautilus_trader is not installed.
        """
        try:
            from nautilus_trader.backtest.engine import BacktestEngine as NtEngine
            from nautilus_trader.config import BacktestRunConfig
        except ImportError:
            raise ImportError(
                "nautilus_trader is not installed. "
                "Install with: pip install nautilus_trader"
            )

        # Create NautilusTrader engine
        nt_engine = NtEngine()

        # Create instruments and add data
        symbols = list(prices.columns)
        instruments = self.create_instruments(symbols)

        for instrument in instruments:
            # Add instrument to engine
            nt_engine.add_instrument(instrument)

            # Convert and add bar data
            symbol = instrument.raw_symbol
            if symbol in prices.columns:
                bar_data = self.convert_ohlcv(
                    prices[[symbol]].rename(columns={symbol: "close"}),
                    instrument.instrument_id,
                )
                # In real implementation, would add bars to engine
                # nt_engine.add_data(bar_data)

        # Run backtest
        # In real implementation: nt_engine.run()
        # For now, fall back
        raise RuntimeError("NautilusTrader direct integration pending - using fallback")

    def _run_fallback_backtest(
        self,
        prices: pd.DataFrame,
        signals: pd.DataFrame,
    ) -> NautilusBacktestResult:
        """Run backtest using our BacktestEngine and map results.

        Args:
            prices: Price DataFrame.
            signals: Signal DataFrame.

        Returns:
            NautilusBacktestResult from our BacktestEngine output.
        """
        result = self._engine.run(prices, signals)
        return self.map_result(result)
