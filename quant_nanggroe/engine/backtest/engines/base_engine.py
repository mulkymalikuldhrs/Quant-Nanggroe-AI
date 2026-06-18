"""Abstract base engine with shared bar-by-bar execution loop.

All market engines inherit from BaseEngine and override market-rule methods.
The shared ``run()`` method handles: signal alignment → bar-by-bar execution
with market rule enforcement → metrics → results.

Ported from Vibe-Trading's ``BaseEngine`` with enhancements for the
Quant-Nanggroe-AI ecosystem.

Key design decisions:
  - Positions tracked internally (dict of Position dataclass)
  - Capital / margin / unrealised P&L tracked bar-by-bar
  - Market rules enforced via abstract methods (can_execute, round_size,
    calc_commission, apply_slippage, on_bar)
  - P&L / margin / sizing hooks are overridable (FuturesEngine injects
    contract multiplier)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.backtest.portfolio import TradeRecord
from quant_nanggroe.engine.backtest.metrics import PerformanceMetrics

logger = logging.getLogger(__name__)


# ── Data models ──


@dataclass(frozen=True)
class Position:
    """An open position in a single instrument.

    Attributes:
        symbol: Instrument identifier.
        direction: 1 for long, -1 for short.
        entry_price: Execution price at entry.
        entry_time: Timestamp when position was opened.
        size: Number of shares / coins / contracts.
        leverage: Effective leverage (1 for spot/stocks).
        entry_bar_idx: Index in the dates array at entry (for holding_bars).
        entry_commission: Commission paid at entry.
    """

    symbol: str
    direction: int
    entry_price: float
    entry_time: pd.Timestamp
    size: float
    leverage: float = 1.0
    entry_bar_idx: int = 0
    entry_commission: float = 0.0


@dataclass(frozen=True)
class EquitySnapshot:
    """Portfolio state at a single point in time.

    Attributes:
        timestamp: Bar timestamp.
        capital: Free cash.
        unrealized: Total unrealised P&L across all positions.
        equity: capital + margin_in_use + unrealized.
        positions: Number of open positions.
    """

    timestamp: pd.Timestamp
    capital: float
    unrealized: float
    equity: float
    positions: int


@dataclass
class EngineConfig:
    """Configuration for a market engine.

    Attributes:
        initial_cash: Starting capital.
        leverage: Default leverage.
        bars_per_year: Bars per year for annualisation (None = auto-detect).
        benchmark: Benchmark ticker for comparison.
        max_positions: Maximum simultaneous positions.
    """

    initial_cash: float = 1_000_000.0
    leverage: float = 1.0
    bars_per_year: Optional[int] = 252
    benchmark: Optional[str] = None
    max_positions: int = 20


# ── Base Engine ──


class BaseEngine(ABC):
    """Abstract base for all market engines.

    Subclasses override market-rule methods:
      - ``can_execute``: whether a trade is allowed by market rules
      - ``round_size``: lot-size rounding
      - ``calc_commission``: fee structure
      - ``apply_slippage``: slippage model
      - ``on_bar``: per-bar hooks (funding fees, liquidation, etc.)

    Usage::

        engine = EquityEngine(config, market="us")
        result = engine.run(prices, signals)
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialise the engine.

        Args:
            config: Backtest configuration dict. Recognised keys:
                - ``initial_cash``: Starting capital (default 1_000_000).
                - ``leverage``: Default leverage (default 1.0).
        """
        self.config = config
        self.initial_capital: float = float(config.get("initial_cash", 1_000_000))
        self.default_leverage: float = float(config.get("leverage", 1.0))
        self.capital: float = self.initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[TradeRecord] = []
        self.equity_snapshots: List[EquitySnapshot] = []
        self._bar_idx: int = 0
        self._active_symbol: str = ""

    # ── Abstract market rule interface (subclass must implement) ──

    @abstractmethod
    def can_execute(self, symbol: str, direction: int, bar: pd.Series) -> bool:
        """Whether market rules allow this trade.

        Args:
            symbol: Instrument identifier.
            direction: 1 (long), -1 (short), 0 (close).
            bar: Current bar data (OHLCV + extras).

        Returns:
            True if allowed.
        """

    @abstractmethod
    def round_size(self, raw_size: float, price: float) -> float:
        """Round position size per market lot rules.

        Args:
            raw_size: Desired size.
            price: Current price.

        Returns:
            Rounded size.
        """

    @abstractmethod
    def calc_commission(
        self, size: float, price: float, direction: int, is_open: bool
    ) -> float:
        """Calculate commission for a trade.

        Args:
            size: Trade size.
            price: Execution price.
            direction: 1 or -1.
            is_open: True for opening, False for closing.

        Returns:
            Commission amount.
        """

    @abstractmethod
    def apply_slippage(self, price: float, direction: int) -> float:
        """Apply slippage to execution price.

        Args:
            price: Raw price.
            direction: 1 (buying/covering short) or -1 (selling/shorting).

        Returns:
            Slipped price.
        """

    def on_bar(self, symbol: str, bar: pd.Series, timestamp: pd.Timestamp) -> None:
        """Per-bar market-rule hook (funding fees, liquidation, etc.).

        Default: no-op. Override in subclass as needed.
        """

    # ── P&L / margin calculation hooks ──

    def _calc_pnl(
        self,
        symbol: str,
        direction: int,
        size: float,
        entry_price: float,
        exit_price: float,
    ) -> float:
        """Realised P&L for a closed position.

        Override in FuturesEngine to inject contract multiplier.
        """
        return direction * size * (exit_price - entry_price)

    def _calc_margin(
        self,
        symbol: str,
        size: float,
        price: float,
        leverage: float,
    ) -> float:
        """Margin (collateral) required for a position."""
        return size * price / leverage

    def _calc_raw_size(
        self,
        symbol: str,
        target_notional: float,
        price: float,
    ) -> float:
        """Convert target notional exposure to number of units/contracts."""
        return target_notional / price

    # ── Main entry ──

    def run(
        self,
        prices: pd.DataFrame,
        signals: pd.DataFrame,
        position_sizer: Optional[Callable] = None,
        bars_per_year: Optional[int] = None,
        benchmark_returns: Optional[pd.Series] = None,
    ) -> Dict[str, Any]:
        """Run the backtest on price data with trading signals.

        The engine processes data bar-by-bar, executing trades based on
        signal-driven target weights with market-rule enforcement.

        Args:
            prices: DataFrame with DatetimeIndex and columns for each symbol.
                Values are close prices.
            signals: DataFrame with same index/columns as prices.
                Values are target position weights (-1 to 1).
            position_sizer: Optional callable for custom position sizing.
                Signature: (signal, capital, price) -> size.
            bars_per_year: Override for annualisation factor.
                None = use engine default (252 for equity, 365 for crypto).
            benchmark_returns: Optional benchmark return series.

        Returns:
            Dict with:
                - ``metrics``: Performance metrics dictionary.
                - ``equity_curve``: pd.Series of equity over time.
                - ``trades``: List of TradeRecord.
                - ``final_equity``: Final portfolio equity.
                - ``total_trades``: Number of completed trades.
        """
        # Reset state
        self._reset_state()

        # Align and shift signals (next-bar-open semantics)
        symbols = list(prices.columns)
        shifted_signals = signals.shift(1).fillna(0.0)

        # Bar-by-bar execution
        self._execute_bars(prices, shifted_signals, symbols, position_sizer)

        # Force close all remaining positions
        self._force_close_all(prices)

        # Build equity curve
        equity_series = pd.Series(
            [s.equity for s in self.equity_snapshots],
            index=[s.timestamp for s in self.equity_snapshots],
        )

        # Determine bars_per_year
        bpy = bars_per_year
        if bpy is None:
            bpy = 252  # Default; engines can override

        # Calculate metrics
        metrics_calc = PerformanceMetrics(bars_per_year=bpy)
        metrics = metrics_calc.calculate(
            equity_series=equity_series,
            trades=self.trades,
            initial_capital=self.initial_capital,
            benchmark_returns=benchmark_returns,
        )

        # Add by-symbol and by-exit-reason stats
        metrics["by_symbol"] = self._by_symbol_stats()
        metrics["by_exit_reason"] = self._by_exit_reason_stats()

        return {
            "metrics": metrics,
            "equity_curve": equity_series,
            "trades": self.trades,
            "final_equity": float(equity_series.iloc[-1]) if len(equity_series) > 0 else self.initial_capital,
            "total_trades": len(self.trades),
        }

    def _reset_state(self) -> None:
        """Reset engine state for a new backtest run."""
        self.capital = self.initial_capital
        self.positions = {}
        self.trades = []
        self.equity_snapshots = []
        self._bar_idx = 0
        self._active_symbol = ""

    def _execute_bars(
        self,
        prices: pd.DataFrame,
        shifted_signals: pd.DataFrame,
        symbols: List[str],
        position_sizer: Optional[Callable],
    ) -> None:
        """Bar-by-bar execution with market rule enforcement.

        Args:
            prices: Close price DataFrame.
            shifted_signals: Shifted signal DataFrame.
            symbols: List of symbol names.
            position_sizer: Optional position sizing callable.
        """
        for i, (timestamp, price_row) in enumerate(prices.iterrows()):
            self._bar_idx = i

            # a. Per-bar hooks (funding fees, liquidation checks)
            for symbol in symbols:
                if symbol in self.positions:
                    price = price_row.get(symbol, np.nan)
                    if pd.notna(price) and price > 0:
                        bar = pd.Series({"close": price, "open": price, "high": price, "low": price, "volume": 0})
                        self.on_bar(symbol, bar, timestamp)

            # b. Rebalance each symbol to target weight
            equity = self._calc_equity_from_prices(price_row)

            if timestamp not in shifted_signals.index:
                continue

            signal_row = shifted_signals.loc[timestamp]

            for symbol in symbols:
                try:
                    price = price_row.get(symbol, np.nan)
                    if pd.isna(price) or price <= 0:
                        continue

                    target_weight = float(signal_row.get(symbol, 0.0))
                    self._rebalance(symbol, target_weight, price, timestamp, equity, position_sizer)
                except Exception as exc:
                    logger.warning("Rebalance failed for %s at %s: %s", symbol, timestamp, exc)

            # c. Record equity snapshot
            snap_equity = self._calc_equity_from_prices(price_row)
            total_unrealized = 0.0
            for sym, pos in self.positions.items():
                cp = price_row.get(sym, pos.entry_price)
                if pd.isna(cp):
                    cp = pos.entry_price
                total_unrealized += self._calc_pnl(
                    sym, pos.direction, pos.size, pos.entry_price, float(cp)
                )
            self.equity_snapshots.append(
                EquitySnapshot(
                    timestamp=timestamp,
                    capital=self.capital,
                    unrealized=total_unrealized,
                    equity=snap_equity,
                    positions=len(self.positions),
                )
            )

    def _calc_equity_from_prices(self, price_row: pd.Series) -> float:
        """Total equity = free cash + sum(margin + unrealised) per position.

        Args:
            price_row: Series of current prices indexed by symbol.

        Returns:
            Total equity value.
        """
        equity = self.capital
        for sym, pos in self.positions.items():
            cp = price_row.get(sym, pos.entry_price)
            if pd.isna(cp):
                cp = pos.entry_price
            cp = float(cp)
            margin = self._calc_margin(sym, pos.size, pos.entry_price, pos.leverage)
            unrealized = self._calc_pnl(sym, pos.direction, pos.size, pos.entry_price, cp)
            equity += margin + unrealized
        return equity

    def _rebalance(
        self,
        symbol: str,
        target_weight: float,
        price: float,
        timestamp: pd.Timestamp,
        equity: float,
        position_sizer: Optional[Callable] = None,
    ) -> None:
        """Adjust position for *symbol* toward *target_weight*.

        Args:
            symbol: Instrument identifier.
            target_weight: Target weight (-1 to 1).
            price: Current price.
            timestamp: Current bar timestamp.
            equity: Current portfolio equity.
            position_sizer: Optional custom position sizer.
        """
        self._active_symbol = symbol
        target_dir = 1 if target_weight > 1e-9 else (-1 if target_weight < -1e-9 else 0)
        current_pos = self.positions.get(symbol)

        # Nothing to do
        if current_pos is None and target_dir == 0:
            return

        bar = pd.Series({"close": price, "open": price, "high": price, "low": price, "volume": 0})

        # Close if target is flat or direction changed
        if current_pos is not None:
            need_close = target_dir == 0 or target_dir != current_pos.direction
            if need_close:
                if self.can_execute(symbol, 0, bar):
                    exec_price = self.apply_slippage(price, -current_pos.direction)
                    self._close_position(symbol, exec_price, timestamp, "signal")
                else:
                    return  # Blocked by market rules (e.g. limit-down can't sell)

        # Open new if target non-zero and no remaining position
        if target_dir != 0 and symbol not in self.positions:
            if not self.can_execute(symbol, target_dir, bar):
                return  # Blocked (e.g. A-share no-short)

            if price <= 0:
                return

            slipped = self.apply_slippage(price, target_dir)
            leverage = self.default_leverage

            if position_sizer:
                size = position_sizer(target_weight, equity, slipped)
            else:
                target_notional = abs(target_weight) * equity * leverage
                size = self._calc_raw_size(symbol, target_notional, slipped)

            size = self.round_size(size, slipped)
            if size <= 0:
                return

            margin = self._calc_margin(symbol, size, slipped, leverage)
            comm = self.calc_commission(size, slipped, target_dir, is_open=True)

            # Capital check — reduce if insufficient
            if margin + comm > self.capital:
                available = self.capital - comm
                if available <= 0:
                    return
                size = self.round_size(
                    self._calc_raw_size(symbol, available * leverage, slipped),
                    slipped,
                )
                if size <= 0:
                    return
                margin = self._calc_margin(symbol, size, slipped, leverage)
                comm = self.calc_commission(size, slipped, target_dir, is_open=True)

            if margin + comm > self.capital:
                return

            self.capital -= (margin + comm)
            self.positions[symbol] = Position(
                symbol=symbol,
                direction=target_dir,
                entry_price=slipped,
                entry_time=timestamp,
                size=size,
                leverage=leverage,
                entry_bar_idx=self._bar_idx,
                entry_commission=comm,
            )

    def _close_position(
        self,
        symbol: str,
        exit_price: float,
        exit_time: pd.Timestamp,
        reason: str,
    ) -> None:
        """Close position, record trade, return capital.

        Args:
            symbol: Instrument identifier.
            exit_price: Execution price for closing.
            exit_time: Closing timestamp.
            reason: Reason for closing (``signal``, ``liquidation``,
                ``end_of_backtest``, etc.).
        """
        self._active_symbol = symbol
        pos = self.positions.pop(symbol, None)
        if pos is None:
            return

        pnl = self._calc_pnl(symbol, pos.direction, pos.size, pos.entry_price, exit_price)
        margin = self._calc_margin(symbol, pos.size, pos.entry_price, pos.leverage)
        pnl_pct = pnl / margin * 100 if margin > 1e-9 else 0.0
        exit_comm = self.calc_commission(pos.size, exit_price, pos.direction, is_open=False)

        self.capital += margin + pnl - exit_comm

        holding_bars = max(self._bar_idx - pos.entry_bar_idx, 0)

        self.trades.append(
            TradeRecord(
                symbol=symbol,
                direction=pos.direction,
                entry_price=pos.entry_price,
                exit_price=exit_price,
                entry_time=pos.entry_time,
                exit_time=exit_time,
                size=pos.size,
                pnl=pnl,
                pnl_pct=pnl_pct,
                exit_reason=reason,
                commission=pos.entry_commission + exit_comm,
                holding_bars=holding_bars,
            )
        )

    def _force_close_all(self, prices: pd.DataFrame) -> None:
        """Force close all remaining positions at end of backtest.

        Args:
            prices: Price DataFrame for exit price lookup.
        """
        if len(prices) == 0:
            return

        last_ts = prices.index[-1]
        last_prices = prices.iloc[-1]

        for symbol in list(self.positions.keys()):
            pos = self.positions.get(symbol)
            if pos is None:
                continue
            close_price = last_prices.get(symbol, pos.entry_price)
            if pd.isna(close_price):
                close_price = pos.entry_price
            self._close_position(symbol, float(close_price), last_ts, "end_of_backtest")

    # ── Statistics helpers ──

    def _by_symbol_stats(self) -> Dict[str, Dict[str, Any]]:
        """Per-symbol trade statistics.

        Returns:
            Mapping ``{symbol: {count, win_rate, total_pnl, avg_pnl}}``.
        """
        groups: Dict[str, list] = {}
        for t in self.trades:
            groups.setdefault(t.symbol, []).append(t)

        result: Dict[str, Dict[str, Any]] = {}
        for sym, sym_trades in groups.items():
            pnls = [t.pnl for t in sym_trades]
            wins = [p for p in pnls if p > 0]
            result[sym] = {
                "count": len(sym_trades),
                "win_rate": round(len(wins) / len(sym_trades), 4) if sym_trades else 0.0,
                "total_pnl": round(sum(pnls), 2),
                "avg_pnl": round(float(np.mean(pnls)), 2) if pnls else 0.0,
            }
        return result

    def _by_exit_reason_stats(self) -> Dict[str, Dict[str, Any]]:
        """Per-exit-reason trade statistics.

        Returns:
            Mapping ``{reason: {count, total_pnl}}``.
        """
        groups: Dict[str, list] = {}
        for t in self.trades:
            groups.setdefault(t.exit_reason, []).append(t)

        result: Dict[str, Dict[str, Any]] = {}
        for reason, reason_trades in groups.items():
            pnls = [t.pnl for t in reason_trades]
            result[reason] = {
                "count": len(reason_trades),
                "total_pnl": round(sum(pnls), 2),
            }
        return result
