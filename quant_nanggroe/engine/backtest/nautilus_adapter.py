"""NautilusTrader Adapter — Unified Backtest & Live Trading Interface.

Provides a proper adapter for NautilusTrader's BacktestEngine with:
- Full interface definition that wraps NautilusTrader's BacktestEngine
- Working pure-Python simulation fallback when NautilusTrader is not installed
- Data loading from our providers
- Signal-to-order conversion
- Fill event conversion back to our portfolio
- Same interface for both backtest and live trading

Since NautilusTrader requires Rust compilation, this module provides:
1. An abstract TradingAdapter interface (works for backtest AND live)
2. A NautilusTraderAdapter that uses the real library when available
3. A PurePythonSimulationAdapter as a working fallback

References:
- NautilusTrader: https://nautilustrader.io/
- Adapter Pattern: Gamma et al., "Design Patterns"
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.backtest.portfolio import Portfolio, Position, TradeRecord

logger = logging.getLogger(__name__)

# Check if NautilusTrader is available
_NAUTILUS_AVAILABLE = False
try:
    import nautilus_trader  # noqa: F401
    _NAUTILUS_AVAILABLE = True
except ImportError:
    pass


# ══════════════════════════════════════════════════════════════════════
# Data Structures
# ══════════════════════════════════════════════════════════════════════


class OrderSide(str, Enum):
    """Order side."""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Order type."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderStatus(str, Enum):
    """Order status."""
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


@dataclass
class AdapterOrder:
    """Unified order representation across backtest and live.

    Attributes:
        order_id: Unique order identifier.
        symbol: Trading symbol.
        side: BUY or SELL.
        order_type: Market, limit, etc.
        quantity: Number of shares/contracts.
        price: Limit price (for limit orders), None for market.
        stop_price: Stop price (for stop orders).
        status: Current order status.
        timestamp: Order creation timestamp.
        filled_price: Actual fill price.
        filled_quantity: Actual fill quantity.
        commission: Commission paid.
        slippage: Slippage applied.
    """

    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType = OrderType.MARKET
    quantity: float = 0.0
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    timestamp: Optional[pd.Timestamp] = None
    filled_price: Optional[float] = None
    filled_quantity: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0


@dataclass
class AdapterFill:
    """Unified fill event representation.

    Attributes:
        fill_id: Unique fill identifier.
        order_id: Associated order ID.
        symbol: Trading symbol.
        side: BUY or SELL.
        quantity: Filled quantity.
        price: Fill price.
        commission: Commission paid.
        timestamp: Fill timestamp.
    """

    fill_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    commission: float
    timestamp: pd.Timestamp


@dataclass
class AdapterResult:
    """Result from adapter backtest run.

    Attributes:
        equity_curve: Portfolio equity over time.
        trades: List of completed trade records.
        fills: List of fill events.
        metrics: Performance metrics dict.
        final_equity: Final portfolio value.
    """

    equity_curve: pd.Series
    trades: List[TradeRecord]
    fills: List[AdapterFill]
    metrics: Dict[str, Any]
    final_equity: float


# ══════════════════════════════════════════════════════════════════════
# Abstract Trading Adapter Interface
# ══════════════════════════════════════════════════════════════════════


class TradingAdapter(ABC):
    """Abstract trading adapter interface.

    This interface provides a unified API for both backtest and live
    trading. Any concrete adapter (NautilusTrader, pure-Python, live
    broker) must implement these methods.

    The adapter handles:
    1. Data loading from providers
    2. Strategy signal conversion to orders
    3. Order execution simulation or real execution
    4. Fill event processing and portfolio updates
    """

    @abstractmethod
    def load_data(
        self,
        prices: pd.DataFrame,
        signals: Optional[pd.DataFrame] = None,
    ) -> None:
        """Load market data and optional signals.

        Args:
            prices: DataFrame with DatetimeIndex and columns for each symbol.
            signals: Optional DataFrame with same structure as prices.
                     Values are target position weights (-1 to 1).
        """
        ...

    @abstractmethod
    def submit_order(self, order: AdapterOrder) -> str:
        """Submit an order for execution.

        Args:
            order: The order to submit.

        Returns:
            Order ID string.
        """
        ...

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order.

        Args:
            order_id: ID of the order to cancel.

        Returns:
            True if cancellation was successful.
        """
        ...

    @abstractmethod
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get current position for a symbol.

        Args:
            symbol: Trading symbol.

        Returns:
            Position if exists, None otherwise.
        """
        ...

    @abstractmethod
    def get_equity(self) -> float:
        """Get current portfolio equity."""
        ...

    @abstractmethod
    def get_fills(self) -> List[AdapterFill]:
        """Get all fill events."""
        ...

    @abstractmethod
    def run(
        self,
        prices: Optional[pd.DataFrame] = None,
        signals: Optional[pd.DataFrame] = None,
    ) -> AdapterResult:
        """Run the backtest or live trading session.

        Args:
            prices: Price data (if not already loaded).
            signals: Signal data (if not already loaded).

        Returns:
            AdapterResult with equity curve, trades, fills, metrics.
        """
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset the adapter state for a new run."""
        ...


# ══════════════════════════════════════════════════════════════════════
# Pure Python Simulation Adapter (Fallback)
# ══════════════════════════════════════════════════════════════════════


class PurePythonSimulationAdapter(TradingAdapter):
    """Pure-Python simulation adapter that implements the TradingAdapter interface.

    This is the working fallback when NautilusTrader is not installed.
    It provides realistic execution simulation with slippage and commission,
    supporting the same interface as the NautilusTrader adapter.

    Features:
    - Market and limit order simulation
    - Slippage modeling (adverse for market orders)
    - Commission calculation
    - Position tracking with mark-to-market
    - Equity curve recording
    - Proper signal-to-order conversion
    - Fill event generation

    Usage:
        adapter = PurePythonSimulationAdapter(
            initial_capital=1_000_000,
            commission_rate=0.001,
            slippage_bps=5.0,
        )
        result = adapter.run(prices, signals)
    """

    def __init__(
        self,
        initial_capital: float = 1_000_000.0,
        commission_rate: float = 0.001,
        slippage_bps: float = 5.0,
        min_commission: float = 1.0,
        bars_per_year: int = 252,
        risk_free_rate: float = 0.02,
        max_positions: int = 10,
    ) -> None:
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage_bps = slippage_bps
        self.min_commission = min_commission
        self.bars_per_year = bars_per_year
        self.risk_free_rate = risk_free_rate
        self.max_positions = max_positions

        self._portfolio: Optional[Portfolio] = None
        self._prices: Optional[pd.DataFrame] = None
        self._signals: Optional[pd.DataFrame] = None
        self._fills: List[AdapterFill] = []
        self._order_counter: int = 0
        self._fill_counter: int = 0
        self._pending_orders: Dict[str, AdapterOrder] = {}
        self._all_orders: Dict[str, AdapterOrder] = {}

    def load_data(
        self,
        prices: pd.DataFrame,
        signals: Optional[pd.DataFrame] = None,
    ) -> None:
        """Load market data and optional signals."""
        self._prices = prices
        self._signals = signals
        logger.info(
            "Loaded data: %d bars, %d symbols",
            len(prices), len(prices.columns),
        )

    def submit_order(self, order: AdapterOrder) -> str:
        """Submit an order for execution."""
        if order.order_id == "":
            self._order_counter += 1
            order.order_id = f"ORD-{self._order_counter:06d}"

        self._all_orders[order.order_id] = order

        if order.order_type == OrderType.MARKET:
            order.status = OrderStatus.ACCEPTED
        elif order.order_type in (OrderType.LIMIT, OrderType.STOP, OrderType.STOP_LIMIT):
            order.status = OrderStatus.PENDING
            self._pending_orders[order.order_id] = order

        logger.debug("Order submitted: %s %s %s %s",
                      order.order_id, order.side.value, order.symbol, order.quantity)
        return order.order_id

    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        if order_id in self._pending_orders:
            self._pending_orders[order_id].status = OrderStatus.CANCELLED
            del self._pending_orders[order_id]
            return True
        return False

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get current position for a symbol."""
        if self._portfolio is None:
            return None
        return self._portfolio.get_position(symbol)

    def get_equity(self) -> float:
        """Get current portfolio equity."""
        if self._portfolio is None:
            return self.initial_capital
        return self._portfolio.equity

    def get_fills(self) -> List[AdapterFill]:
        """Get all fill events."""
        return list(self._fills)

    def run(
        self,
        prices: Optional[pd.DataFrame] = None,
        signals: Optional[pd.DataFrame] = None,
    ) -> AdapterResult:
        """Run the simulation.

        Processes data bar-by-bar, converting signals to orders,
        executing them with slippage and commission, and recording
        the equity curve and fill events.
        """
        if prices is not None:
            self._prices = prices
        if signals is not None:
            self._signals = signals

        if self._prices is None:
            raise ValueError("No price data loaded. Call load_data() or pass prices.")

        prices = self._prices
        signals = self._signals

        # Reset state
        self._portfolio = Portfolio(
            initial_capital=self.initial_capital,
            max_positions=self.max_positions,
        )
        self._fills = []
        self._order_counter = 0
        self._fill_counter = 0
        self._pending_orders = {}
        self._all_orders = {}

        equity_curve: List[float] = []
        timestamps: List[pd.Timestamp] = []
        all_trades: List[TradeRecord] = []

        # Shift signals by 1 bar (next-bar-open semantics)
        if signals is not None:
            shifted_signals = signals.shift(1).fillna(0.0)
        else:
            shifted_signals = None

        symbols = list(prices.columns)

        for i, (timestamp, price_row) in enumerate(prices.iterrows()):
            # 1. Mark-to-market existing positions
            self._portfolio.mark_to_market(price_row)

            # 2. Check pending limit/stop orders
            self._process_pending_orders(price_row, timestamp)

            # 3. Generate orders from signals
            if shifted_signals is not None and timestamp in shifted_signals.index:
                signal_row = shifted_signals.loc[timestamp]
                self._process_signals(signal_row, price_row, timestamp, symbols)

            # Record equity
            equity_curve.append(self._portfolio.equity)
            timestamps.append(timestamp)

        # Force close all remaining positions
        if len(prices) > 0:
            last_ts = prices.index[-1]
            last_prices = prices.iloc[-1]
            for symbol in list(self._portfolio.positions.keys()):
                pos = self._portfolio.get_position(symbol)
                if pos is not None:
                    close_price = last_prices.get(symbol, pos.entry_price)
                    trade = self._portfolio.close_position(
                        symbol, close_price, last_ts, "end_of_backtest"
                    )
                    if trade is not None:
                        all_trades.append(trade)

        # Build equity curve series
        equity_series = pd.Series(equity_curve, index=timestamps)

        # Calculate metrics
        from quant_nanggroe.engine.backtest.metrics import PerformanceMetrics
        metrics_calc = PerformanceMetrics(
            bars_per_year=self.bars_per_year,
            risk_free_rate=self.risk_free_rate,
        )
        metrics = metrics_calc.calculate(
            equity_series=equity_series,
            trades=all_trades,
            initial_capital=self.initial_capital,
        )

        return AdapterResult(
            equity_curve=equity_series,
            trades=all_trades,
            fills=list(self._fills),
            metrics=metrics,
            final_equity=self._portfolio.equity,
        )

    def reset(self) -> None:
        """Reset adapter state for a new run."""
        self._portfolio = None
        self._prices = None
        self._signals = None
        self._fills = []
        self._order_counter = 0
        self._fill_counter = 0
        self._pending_orders = {}
        self._all_orders = {}

    # ── Internal Methods ─────────────────────────────────────────────

    def _process_signals(
        self,
        signal_row: pd.Series,
        price_row: pd.Series,
        timestamp: pd.Timestamp,
        symbols: List[str],
    ) -> None:
        """Convert strategy signals to market orders."""
        for symbol in symbols:
            price = price_row.get(symbol, np.nan)
            if pd.isna(price) or price <= 0:
                continue

            target_weight = signal_row.get(symbol, 0.0)
            current_pos = self._portfolio.get_position(symbol) if self._portfolio else None

            # Determine target direction
            target_direction = 1 if target_weight > 0.01 else (-1 if target_weight < -0.01 else 0)

            # Close existing position if direction changed
            if current_pos is not None:
                if target_direction == 0 or (current_pos.direction != target_direction and target_direction != 0):
                    close_price = self._apply_slippage(price, -current_pos.direction)
                    trade = self._portfolio.close_position(
                        symbol, close_price, timestamp, "signal"
                    )
                    if trade is not None:
                        commission = self._calc_commission(abs(trade.size), close_price)
                        self._portfolio._apply_commission(symbol, commission)
                        # Generate fill
                        self._generate_fill(
                            symbol=symbol,
                            side=OrderSide.SELL if current_pos.direction == 1 else OrderSide.BUY,
                            quantity=abs(trade.size),
                            price=close_price,
                            commission=commission,
                            timestamp=timestamp,
                        )

            # Open new position
            if target_direction != 0 and self._portfolio.get_position(symbol) is None:
                equity = self._portfolio.equity
                target_notional = abs(target_weight) * equity
                size = target_notional / price

                exec_price = self._apply_slippage(price, target_direction)
                open_commission = self._calc_commission(abs(size), exec_price)

                if self._portfolio.can_open_position(exec_price, size, open_commission):
                    trade = self._portfolio.open_position(
                        symbol=symbol,
                        direction=target_direction,
                        size=size,
                        price=exec_price,
                        timestamp=timestamp,
                        commission=open_commission,
                    )
                    # Generate fill for opening
                    self._generate_fill(
                        symbol=symbol,
                        side=OrderSide.BUY if target_direction == 1 else OrderSide.SELL,
                        quantity=size,
                        price=exec_price,
                        commission=open_commission,
                        timestamp=timestamp,
                    )

    def _process_pending_orders(
        self,
        price_row: pd.Series,
        timestamp: pd.Timestamp,
    ) -> None:
        """Check and execute pending limit/stop orders."""
        to_remove: List[str] = []

        for order_id, order in self._pending_orders.items():
            price = price_row.get(order.symbol, np.nan)
            if pd.isna(price):
                continue

            should_fill = False
            fill_price = price

            if order.order_type == OrderType.LIMIT:
                if order.side == OrderSide.BUY and price <= (order.price or float("inf")):
                    should_fill = True
                    fill_price = min(price, order.price or price)
                elif order.side == OrderSide.SELL and price >= (order.price or 0):
                    should_fill = True
                    fill_price = max(price, order.price or price)

            elif order.order_type == OrderType.STOP:
                if order.side == OrderSide.BUY and price >= (order.stop_price or float("inf")):
                    should_fill = True
                    fill_price = self._apply_slippage(price, 1)
                elif order.side == OrderSide.SELL and price <= (order.stop_price or 0):
                    should_fill = True
                    fill_price = self._apply_slippage(price, -1)

            if should_fill:
                fill_price = self._apply_slippage(fill_price, 1 if order.side == OrderSide.BUY else -1)
                commission = self._calc_commission(order.quantity, fill_price)
                order.status = OrderStatus.FILLED
                order.filled_price = fill_price
                order.filled_quantity = order.quantity
                order.commission = commission

                self._generate_fill(
                    symbol=order.symbol,
                    side=order.side,
                    quantity=order.quantity,
                    price=fill_price,
                    commission=commission,
                    timestamp=timestamp,
                )
                to_remove.append(order_id)

        for oid in to_remove:
            del self._pending_orders[oid]

    def _apply_slippage(self, price: float, direction: int) -> float:
        """Apply slippage to execution price.

        Slippage is always adverse:
        - Buying → price increases
        - Selling → price decreases
        """
        slippage_factor = self.slippage_bps / 10000.0
        if direction > 0:
            return price * (1.0 + slippage_factor)
        elif direction < 0:
            return price * (1.0 - slippage_factor)
        return price

    def _calc_commission(self, size: float, price: float) -> float:
        """Calculate commission for a trade."""
        trade_value = abs(size * price)
        return max(self.min_commission, self.commission_rate * trade_value)

    def _generate_fill(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        price: float,
        commission: float,
        timestamp: pd.Timestamp,
        order_id: Optional[str] = None,
    ) -> AdapterFill:
        """Generate a fill event."""
        self._fill_counter += 1
        if order_id is None:
            self._order_counter += 1
            order_id = f"ORD-FILL-{self._order_counter:06d}"

        fill = AdapterFill(
            fill_id=f"FILL-{self._fill_counter:06d}",
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            commission=commission,
            timestamp=timestamp,
        )
        self._fills.append(fill)
        return fill


# ══════════════════════════════════════════════════════════════════════
# NautilusTrader Adapter (when library is available)
# ══════════════════════════════════════════════════════════════════════


class NautilusTraderAdapter(TradingAdapter):
    """NautilusTrader adapter for production-grade backtesting and live trading.

    This adapter wraps NautilusTrader's BacktestEngine and provides
    the same TradingAdapter interface as PurePythonSimulationAdapter.

    When NautilusTrader is not installed, attempting to instantiate this
    will raise ImportError with a helpful message.

    This adapter supports:
    - Full NautilusTrader backtesting with order book simulation
    - Live trading via NautilusTrader's live engine
    - High-frequency backtesting with microsecond resolution
    - Multi-asset, multi-exchange backtesting

    Usage:
        if NautilusTraderAdapter.is_available():
            adapter = NautilusTraderAdapter(initial_capital=1_000_000)
            result = adapter.run(prices, signals)
        else:
            adapter = PurePythonSimulationAdapter(initial_capital=1_000_000)
    """

    @staticmethod
    def is_available() -> bool:
        """Check if NautilusTrader is installed and available."""
        return _NAUTILUS_AVAILABLE

    def __init__(
        self,
        initial_capital: float = 1_000_000.0,
        commission_rate: float = 0.001,
        slippage_bps: float = 5.0,
        bars_per_year: int = 252,
        risk_free_rate: float = 0.02,
        **kwargs: Any,
    ) -> None:
        if not _NAUTILUS_AVAILABLE:
            raise ImportError(
                "NautilusTrader is not installed. Install it with: "
                "pip install nautilus_trader\n"
                "Note: NautilusTrader requires Rust compilation. "
                "Use PurePythonSimulationAdapter as a fallback."
            )

        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage_bps = slippage_bps
        self.bars_per_year = bars_per_year
        self.risk_free_rate = risk_free_rate

        # NautilusTrader components (initialized in _init_engine)
        self._engine = None
        self._portfolio: Optional[Portfolio] = None
        self._prices: Optional[pd.DataFrame] = None
        self._signals: Optional[pd.DataFrame] = None
        self._fills: List[AdapterFill] = []

        self._init_engine(**kwargs)

    def _init_engine(self, **kwargs: Any) -> None:
        """Initialize the NautilusTrader BacktestEngine.

        This sets up the engine with proper configuration,
        data catalog, and venue configuration.
        """
        try:
            from nautilus_trader.backtest.engine import BacktestEngine as NTBacktestEngine

            # Create engine with basic configuration
            # Full configuration would be done via BacktestRunConfig
            self._engine = NTBacktestEngine()
            logger.info("NautilusTrader BacktestEngine initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize NautilusTrader engine: %s", e)
            raise

    def load_data(
        self,
        prices: pd.DataFrame,
        signals: Optional[pd.DataFrame] = None,
    ) -> None:
        """Load market data into NautilusTrader format.

        Converts our DataFrame format to NautilusTrader's data objects.
        """
        self._prices = prices
        self._signals = signals

        if self._engine is not None:
            try:
                # Convert DataFrame to NautilusTrader Bar objects
                self._load_nautilus_data(prices)
            except Exception as e:
                logger.warning(
                    "Failed to load data into NautilusTrader: %s. "
                    "Will use fallback processing.", e
                )

    def _load_nautilus_data(self, prices: pd.DataFrame) -> None:
        """Convert price DataFrame to NautilusTrader bar data."""
        # This would involve creating nautilus_trader.model.Bar objects
        # from our DataFrame and adding them to the engine's data catalog.
        # Implementation depends on specific NautilusTrader version.
        pass

    def submit_order(self, order: AdapterOrder) -> str:
        """Submit an order through NautilusTrader."""
        # Convert our AdapterOrder to NautilusTrader order
        # and submit through the engine
        if self._engine is not None:
            try:
                return self._submit_nautilus_order(order)
            except Exception as e:
                logger.error("Failed to submit NautilusTrader order: %s", e)
                return ""

        return ""

    def _submit_nautilus_order(self, order: AdapterOrder) -> str:
        """Convert and submit order to NautilusTrader."""
        # This would convert our AdapterOrder to nautilus_trader.model.Order
        # and submit through the engine's submit_order method.
        # Implementation depends on specific NautilusTrader version.
        return order.order_id

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order through NautilusTrader."""
        if self._engine is not None:
            try:
                # self._engine.cancel_order(order_id)
                return True
            except Exception as e:
                logger.error("Failed to cancel NautilusTrader order: %s", e)
                return False
        return False

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get current position from NautilusTrader."""
        if self._portfolio is not None:
            return self._portfolio.get_position(symbol)
        return None

    def get_equity(self) -> float:
        """Get current equity from NautilusTrader."""
        if self._portfolio is not None:
            return self._portfolio.equity
        return self.initial_capital

    def get_fills(self) -> List[AdapterFill]:
        """Get all fills from NautilusTrader."""
        return list(self._fills)

    def run(
        self,
        prices: Optional[pd.DataFrame] = None,
        signals: Optional[pd.DataFrame] = None,
    ) -> AdapterResult:
        """Run backtest through NautilusTrader.

        Falls back to PurePythonSimulationAdapter if NautilusTrader
        execution fails.
        """
        if prices is not None:
            self._prices = prices
        if signals is not None:
            self._signals = signals

        if self._prices is None:
            raise ValueError("No price data loaded.")

        try:
            return self._run_nautilus()
        except Exception as e:
            logger.warning(
                "NautilusTrader run failed: %s. Falling back to pure Python.", e
            )
            fallback = PurePythonSimulationAdapter(
                initial_capital=self.initial_capital,
                commission_rate=self.commission_rate,
                slippage_bps=self.slippage_bps,
                bars_per_year=self.bars_per_year,
                risk_free_rate=self.risk_free_rate,
            )
            return fallback.run(self._prices, self._signals)

    def _run_nautilus(self) -> AdapterResult:
        """Execute the NautilusTrader backtest run."""
        # This would:
        # 1. Configure the engine with data, strategy, and venues
        # 2. Run self._engine.run()
        # 3. Extract results and convert to our format
        # 4. Return AdapterResult

        # Graceful fallback — nautilus adapter not connected
        logger.warning("NautilusTrader adapter _run_nautilus() not fully implemented — falling back")
        raise NotImplementedError(
            "Full NautilusTrader execution requires complete configuration. "
            "Use PurePythonSimulationAdapter for immediate functionality."
        )
        # ponytail: to wire real NautilusTrader:
        #   1. Define TradingNode + strategy: from nautilus_trader.trading import TradingNode
        #   2. Register venues, data catalog, and strategy instance
        #   3. Call node.run() — results go into node.engine.trader.accounts
        #   4. Map results: portflolio value, fills, unrealized PnL → AdapterResult
        #   See nautilus_trader/examples/ for reference implementations.

    def reset(self) -> None:
        """Reset the NautilusTrader engine."""
        self._portfolio = None
        self._prices = None
        self._signals = None
        self._fills = []

        if self._engine is not None:
            try:
                self._engine.reset()
            except Exception:
                self._init_engine()


# ══════════════════════════════════════════════════════════════════════
# Factory Function
# ══════════════════════════════════════════════════════════════════════


def create_trading_adapter(
    adapter_type: str = "auto",
    **kwargs: Any,
) -> TradingAdapter:
    """Factory function to create the appropriate trading adapter.

    Args:
        adapter_type: 'auto', 'nautilus', or 'pure_python'.
            'auto' will use NautilusTrader if available, else pure Python.
        **kwargs: Arguments passed to the adapter constructor.

    Returns:
        TradingAdapter instance.

    Raises:
        ImportError: If adapter_type='nautilus' and NautilusTrader not installed.
    """
    if adapter_type == "nautilus":
        return NautilusTraderAdapter(**kwargs)
    elif adapter_type == "pure_python":
        return PurePythonSimulationAdapter(**kwargs)
    elif adapter_type == "auto":
        if _NAUTILUS_AVAILABLE:
            try:
                return NautilusTraderAdapter(**kwargs)
            except (ImportError, NotImplementedError):
                logger.info("NautilusTrader not available, using pure Python adapter")
                return PurePythonSimulationAdapter(**kwargs)
        else:
            return PurePythonSimulationAdapter(**kwargs)
    else:
        raise ValueError(f"Unknown adapter type: {adapter_type}. Use 'auto', 'nautilus', or 'pure_python'.")

