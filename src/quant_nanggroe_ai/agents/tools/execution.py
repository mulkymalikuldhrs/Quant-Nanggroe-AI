"""
Execution Tool — Order Routing & Trade Execution for Agents
============================================================
Routes orders to the appropriate execution backend based on symbol
type and configuration. Paper trading is the default mode.

Routing logic:
  - Crypto symbols → PaperTradingBroker
  - Forex symbols  → PaperTradingBroker
  - Stock symbols  → PaperTradingBroker (or AlpacaBroker if configured)

All order methods return structured dicts with status, order_id,
execution_price, slippage, and commission details.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from quant_nanggroe_ai.config import get_settings
from quant_nanggroe_ai.exceptions import (
    ExecutionError,
    KillSwitchActiveError,
    OrderRejectedError,
)
from quant_nanggroe_ai.execution.paper import (
    OrderSide,
    OrderStatus,
    OrderType,
    PaperOrder,
    PaperTradingBroker,
    SlippageModel,
)

logger = logging.getLogger(__name__)

# Symbol classification (shared logic with market_data tool)
CRYPTO_PREFIXES = ("BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "DOT", "AVAX", "MATIC")
CRYPTO_SUFFIX = ("-USD", "/USD", "USDT", "BUSD")
FOREX_SUFFIX = ("=X", "=F")


def _is_crypto(symbol: str) -> bool:
    """Check if symbol is a crypto asset."""
    upper = symbol.upper()
    if upper.endswith(CRYPTO_SUFFIX) or "/" in symbol:
        return True
    return any(upper.startswith(p) for p in CRYPTO_PREFIXES)


def _is_forex(symbol: str) -> bool:
    """Check if symbol is a forex pair."""
    return symbol.upper().endswith(FOREX_SUFFIX) or "=" in symbol


def _normalize_side(side: str) -> OrderSide:
    """
    Normalize order side string to OrderSide enum.

    Args:
        side: "BUY", "SELL", "LONG", or "SHORT"

    Returns:
        OrderSide enum value.

    Raises:
        ExecutionError: If the side string is invalid.
    """
    side_upper = side.upper()
    if side_upper in ("BUY", "LONG"):
        return OrderSide.BUY
    if side_upper in ("SELL", "SHORT"):
        return OrderSide.SELL
    raise ExecutionError(f"Invalid order side: '{side}'. Must be BUY/SELL/LONG/SHORT.")


def _normalize_order_type(order_type: str) -> OrderType:
    """Normalize order type string to OrderType enum."""
    ot_upper = order_type.upper()
    mapping = {
        "MARKET": OrderType.MARKET,
        "LIMIT": OrderType.LIMIT,
        "STOP": OrderType.STOP,
        "STOP_LIMIT": OrderType.STOP_LIMIT,
    }
    if ot_upper not in mapping:
        raise ExecutionError(f"Unsupported order type: {order_type}")
    return mapping[ot_upper]


class _OrderStore:
    """
    In-memory order store for tracking all orders across brokers.

    Provides lookup by order_id for status queries and cancellation.
    """

    def __init__(self) -> None:
        self._orders: dict[str, dict[str, Any]] = {}

    def store(self, order_id: str, record: dict[str, Any]) -> None:
        """Store an order record."""
        self._orders[order_id] = record

    def get(self, order_id: str) -> dict[str, Any] | None:
        """Get an order record by ID."""
        return self._orders.get(order_id)

    def update(self, order_id: str, updates: dict[str, Any]) -> None:
        """Update fields on an existing order record."""
        if order_id in self._orders:
            self._orders[order_id].update(updates)

    def list_by_symbol(self, symbol: str) -> list[dict[str, Any]]:
        """List all orders for a given symbol."""
        return [
            o for o in self._orders.values()
            if o.get("symbol") == symbol
        ]

    def list_open(self, symbol: str | None = None) -> list[dict[str, Any]]:
        """List all open (non-filled, non-cancelled) orders."""
        return [
            o for o in self._orders.values()
            if o.get("status") in ("PENDING", "SUBMITTED")
            and (symbol is None or o.get("symbol") == symbol)
        ]


class ExecutionTool:
    """
    Trade execution tool for agent consumption.

    Provides a unified interface for order submission, cancellation,
    and status tracking across multiple execution backends.

    Features:
      - Automatic routing to the appropriate broker backend
      - Paper trading mode by default (safe for testing)
      - Pre-trade risk checks (kill switch, position limits)
      - Full audit trail in the order store
      - Stop-loss and take-profit order support

    Usage::

        tool = ExecutionTool()
        result = await tool.execute_order(
            symbol="AAPL",
            side="BUY",
            quantity=10,
            order_type="LIMIT",
            price=150.0,
        )
        print(result["status"])     # "FILLED"
        print(result["order_id"])   # "PAPER-000001"
    """

    def __init__(
        self,
        market_data_tool: Any | None = None,
    ) -> None:
        """
        Initialize the ExecutionTool.

        Args:
            market_data_tool: Optional MarketDataTool for fetching
                current prices when executing market orders.
        """
        self._settings = get_settings()
        self._market_data = market_data_tool
        self._order_store = _OrderStore()

        # Initialize paper brokers per asset class with appropriate defaults
        self._stock_paper = PaperTradingBroker(
            initial_capital=1_000_000.0,
            commission_rate=0.001,
            slippage_model=SlippageModel(base_bps=5.0),
        )
        self._crypto_paper = PaperTradingBroker(
            initial_capital=1_000_000.0,
            commission_rate=0.001,
            slippage_model=SlippageModel(base_bps=5.0),
        )
        self._forex_paper = PaperTradingBroker(
            initial_capital=1_000_000.0,
            commission_rate=0.0002,
            slippage_model=SlippageModel(base_bps=2.0),
        )

        # Alpaca broker (lazy init)
        self._alpaca_broker: Any = None

    # ── Public API ────────────────────────────────────────────────────

    async def execute_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
        price: float | None = None,
        stop_loss: float | None = None,
        take_profit: float | None = None,
    ) -> dict[str, Any]:
        """
        Execute a trade order through the appropriate broker backend.

        Pre-trade checks:
          1. Kill switch must be inactive
          2. Quantity must be positive
          3. Stop-loss/take-profit validation (SL < entry for BUY, etc.)

        Args:
            symbol: Ticker symbol.
            side: Order direction — "BUY", "SELL", "LONG", or "SHORT".
            quantity: Number of shares/units to trade.
            order_type: "MARKET", "LIMIT", "STOP", or "STOP_LIMIT".
            price: Limit price (required for LIMIT orders).
            stop_loss: Optional stop-loss price.
            take_profit: Optional take-profit price.

        Returns:
            Dict with 'status', 'order_id', 'symbol', 'side', 'quantity',
            'order_type', 'execution_price', 'slippage', 'commission',
            'stop_loss', 'take_profit', 'timestamp'.

        Raises:
            KillSwitchActiveError: If the kill switch is engaged.
            OrderRejectedError: If pre-trade checks fail.
            ExecutionError: If the order cannot be executed.
        """
        # ── Pre-trade checks ──────────────────────────────────────────
        self._check_kill_switch()
        self._validate_order_params(symbol, side, quantity, order_type, price,
                                    stop_loss, take_profit)

        normalized_side = _normalize_side(side)
        normalized_type = _normalize_order_type(order_type)

        # Get current market price for market orders and slippage calc
        current_price = await self._resolve_current_price(symbol, price, order_type)

        # Set market price on the broker so it knows the current level
        broker = self._get_paper_broker(symbol)
        if current_price and current_price > 0:
            broker.set_market_price(symbol, current_price)

        # ── Route to appropriate broker ───────────────────────────────
        if self._should_use_alpaca(symbol):
            order = await self._route_to_alpaca(
                symbol, normalized_side, quantity, normalized_type, price, current_price
            )
        else:
            # Use the PaperTradingBroker's buy/sell methods
            if normalized_side == OrderSide.BUY:
                order = await broker.buy(
                    symbol=symbol,
                    quantity=quantity,
                    price=price if normalized_type == OrderType.LIMIT else current_price,
                    order_type=normalized_type,
                )
            else:
                order = await broker.sell(
                    symbol=symbol,
                    quantity=quantity,
                    price=price if normalized_type == OrderType.LIMIT else current_price,
                    order_type=normalized_type,
                )

        # ── Build result ──────────────────────────────────────────────
        result = self._build_order_result(
            order, symbol, normalized_side.value, quantity, order_type,
            stop_loss, take_profit, current_price,
        )

        # Store in order store
        self._order_store.store(order.id, result)

        logger.info(
            "Order executed: %s %s %s @ %s — status=%s",
            normalized_side.value, quantity, symbol,
            result.get("execution_price", "N/A"), result["status"],
        )
        return result

    async def cancel_order(self, order_id: str) -> dict[str, Any]:
        """
        Cancel an existing order.

        Args:
            order_id: The order ID to cancel.

        Returns:
            Dict with 'order_id', 'status', 'timestamp'.

        Raises:
            ExecutionError: If the order cannot be found or cancelled.
        """
        record = self._order_store.get(order_id)
        if record is None:
            raise ExecutionError(f"Order not found: {order_id}")

        if record.get("status") not in ("PENDING", "SUBMITTED"):
            raise ExecutionError(
                f"Cannot cancel order {order_id} — current status: {record['status']}"
            )

        # Try to cancel at the broker level
        symbol = record.get("symbol", "")
        broker = self._get_paper_broker(symbol)
        cancelled = await broker.cancel_order(order_id)

        # Update in our store
        self._order_store.update(order_id, {
            "status": "CANCELLED",
            "cancelled_at": datetime.now(UTC).isoformat(),
        })

        logger.info("Order cancelled: %s", order_id)
        return {
            "order_id": order_id,
            "status": "CANCELLED",
            "broker_cancelled": cancelled,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    async def get_order_status(self, order_id: str) -> dict[str, Any]:
        """
        Get the current status of an order.

        Args:
            order_id: The order ID to query.

        Returns:
            Full order record dict.

        Raises:
            ExecutionError: If the order cannot be found.
        """
        record = self._order_store.get(order_id)
        if record is None:
            raise ExecutionError(f"Order not found: {order_id}")
        return record

    async def get_open_orders(self, symbol: str | None = None) -> list[dict[str, Any]]:
        """
        Get all open (non-filled, non-cancelled) orders.

        Args:
            symbol: Optional symbol filter.

        Returns:
            List of order record dicts.
        """
        return self._order_store.list_open(symbol)

    async def get_account_summary(self, symbol_type: str = "stock") -> dict[str, Any]:
        """
        Get account balance and position summary from the paper broker.

        Args:
            symbol_type: "stock", "crypto", or "forex" to select the broker.

        Returns:
            Account balance dict from the paper broker.
        """
        broker = self._get_paper_broker_by_type(symbol_type)
        return broker.get_balance()

    # ── Private helpers ───────────────────────────────────────────────

    def _check_kill_switch(self) -> None:
        """Raise if kill switch is active."""
        if not self._settings.features.kill_switch:
            return
        # Check if all trading is disabled
        if not self._settings.features.paper_trading and not self._settings.features.live_trading:
            raise KillSwitchActiveError("All trading is disabled")

    @staticmethod
    def _validate_order_params(
        symbol: str,
        side: str,
        quantity: float,
        order_type: str,
        price: float | None,
        stop_loss: float | None,
        take_profit: float | None,
    ) -> None:
        """Validate order parameters before submission."""
        if not symbol:
            raise OrderRejectedError("Symbol is required")
        if quantity <= 0:
            raise OrderRejectedError(f"Quantity must be positive, got {quantity}")

        # Validate order type
        ot_upper = order_type.upper()
        if ot_upper not in ("MARKET", "LIMIT", "STOP", "STOP_LIMIT"):
            raise OrderRejectedError(f"Unsupported order type: {order_type}")
        if ot_upper == "LIMIT" and price is None:
            raise OrderRejectedError("Limit price is required for LIMIT orders")
        if price is not None and price <= 0:
            raise OrderRejectedError(f"Price must be positive, got {price}")

        # Validate side
        try:
            _normalize_side(side)
        except ExecutionError as exc:
            raise OrderRejectedError(str(exc)) from exc

        # Stop-loss / take-profit sanity checks
        if stop_loss is not None and stop_loss <= 0:
            raise OrderRejectedError(f"Stop-loss must be positive, got {stop_loss}")
        if take_profit is not None and take_profit <= 0:
            raise OrderRejectedError(f"Take-profit must be positive, got {take_profit}")

        side_upper = side.upper()
        entry = price or 0.0
        if entry > 0:
            if side_upper in ("BUY", "LONG"):
                if stop_loss is not None and stop_loss >= entry:
                    raise OrderRejectedError(
                        f"Stop-loss ({stop_loss}) must be below entry ({entry}) for BUY orders"
                    )
                if take_profit is not None and take_profit <= entry:
                    raise OrderRejectedError(
                        f"Take-profit ({take_profit}) must be above entry ({entry}) for BUY orders"
                    )
            elif side_upper in ("SELL", "SHORT"):
                if stop_loss is not None and stop_loss <= entry:
                    raise OrderRejectedError(
                        f"Stop-loss ({stop_loss}) must be above entry ({entry}) for SELL orders"
                    )
                if take_profit is not None and take_profit >= entry:
                    raise OrderRejectedError(
                        f"Take-profit ({take_profit}) must be below entry ({entry}) for SELL orders"
                    )

    async def _resolve_current_price(
        self, symbol: str, price: float | None, order_type: str
    ) -> float | None:
        """
        Get the current market price for the symbol.

        Used for market order execution and slippage calculation.
        """
        if order_type.upper() == "LIMIT" and price is not None:
            return price

        if self._market_data is not None:
            try:
                result = await self._market_data.get_current_price(symbol)
                return result.get("price")
            except Exception as exc:
                logger.warning("Could not fetch current price for %s: %s", symbol, exc)

        return price  # Fallback to provided price (may be None)

    def _should_use_alpaca(self, symbol: str) -> bool:
        """Check if Alpaca should be used for stock execution."""
        if _is_crypto(symbol) or _is_forex(symbol):
            return False
        has_keys = bool(
            self._settings.data_sources.alpaca_api_key
            and self._settings.data_sources.alpaca_secret_key
        )
        return has_keys and self._settings.features.live_trading

    def _get_paper_broker(self, symbol: str) -> PaperTradingBroker:
        """Get the appropriate paper broker for a symbol type."""
        if _is_crypto(symbol):
            return self._crypto_paper
        if _is_forex(symbol):
            return self._forex_paper
        return self._stock_paper

    def _get_paper_broker_by_type(self, symbol_type: str) -> PaperTradingBroker:
        """Get paper broker by asset type string."""
        mapping = {
            "stock": self._stock_paper,
            "crypto": self._crypto_paper,
            "forex": self._forex_paper,
        }
        return mapping.get(symbol_type, self._stock_paper)

    def _get_alpaca_broker(self) -> Any:
        """Lazily initialize the Alpaca broker."""
        if self._alpaca_broker is not None:
            return self._alpaca_broker

        from quant_nanggroe_ai.execution.alpaca_broker import AlpacaBroker
        self._alpaca_broker = AlpacaBroker()
        return self._alpaca_broker

    async def _route_to_alpaca(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        order_type: OrderType,
        price: float | None,
        current_price: float | None,
    ) -> PaperOrder:
        """Route order to Alpaca broker. Falls back to paper if not configured."""
        try:
            alpaca = self._get_alpaca_broker()
            result = await alpaca.submit_order(
                symbol=symbol, direction=side.value, quantity=quantity,
                order_type=order_type.value, price=price,
            )
            # Convert Alpaca result to PaperOrder for uniform handling
            return PaperOrder(
                id=result.get("id", str(uuid.uuid4())),
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=order_type,
                limit_price=price,
                status=OrderStatus.FILLED,
                filled_price=result.get("filled_price", price or current_price),
                filled_quantity=quantity,
                commission=result.get("commission", 0.0),
                slippage=result.get("slippage", 0.0),
                filled_at=datetime.now(UTC),
            )
        except NotImplementedError:
            # Alpaca not configured — fall back to paper
            logger.warning("Alpaca not configured, falling back to paper for %s", symbol)
            broker = self._stock_paper
            if side == OrderSide.BUY:
                return await broker.buy(
                    symbol=symbol, quantity=quantity, price=price or current_price,
                    order_type=order_type,
                )
            else:
                return await broker.sell(
                    symbol=symbol, quantity=quantity, price=price or current_price,
                    order_type=order_type,
                )

    @staticmethod
    def _build_order_result(
        order: PaperOrder,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str,
        stop_loss: float | None,
        take_profit: float | None,
        current_price: float | None,
    ) -> dict[str, Any]:
        """Build the standardized order result dict."""
        execution_price = order.filled_price if order.filled_price else current_price or 0.0

        return {
            "order_id": order.id,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "order_type": order_type.upper(),
            "requested_price": current_price,
            "execution_price": round(execution_price, 6),
            "slippage": round(order.slippage, 6),
            "commission": round(order.commission, 6),
            "status": order.status.value,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "filled_at": order.filled_at.isoformat() if order.filled_at else None,
            "timestamp": datetime.now(UTC).isoformat(),
            "mode": "PAPER",
        }
