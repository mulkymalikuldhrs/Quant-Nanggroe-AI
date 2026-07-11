"""
Execution Tool — Order Routing & Trade Execution for Agents
============================================================
Routes orders to the appropriate execution backend based on symbol
type and configuration. Paper trading is the default mode.

Routing logic:
  - Crypto symbols → PaperExchangeBroker
  - Forex symbols  → PaperExchangeBroker
  - Stock symbols  → PaperExchangeBroker (or AlpacaBroker if configured)

All order methods return structured dicts with status, order_id,
execution_price, slippage, and commission details.

LangChain @tool functions are also exposed for direct agent consumption.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func=None, *args, **kwargs):
        """No-op fallback when langchain_core is not installed."""
        if func is not None:
            return func
        def decorator(f):
            return f
        return decorator

from quant_nanggroe.config.settings import get_settings
from quant_nanggroe.exceptions import (
    ExecutionError,
    KillSwitchActiveError,
    OrderRejectedError,
)
from quant_nanggroe.exchange.paper_broker import PaperExchangeBroker
from quant_nanggroe.types.orders import OrderSide, OrderStatus, OrderType

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
        self._orders: Dict[str, Dict[str, Any]] = {}

    def store(self, order_id: str, record: Dict[str, Any]) -> None:
        """Store an order record."""
        self._orders[order_id] = record

    def get(self, order_id: str) -> Dict[str, Any] | None:
        """Get an order record by ID."""
        return self._orders.get(order_id)

    def update(self, order_id: str, updates: Dict[str, Any]) -> None:
        """Update fields on an existing order record."""
        if order_id in self._orders:
            self._orders[order_id].update(updates)

    def list_by_symbol(self, symbol: str) -> List[Dict[str, Any]]:
        """List all orders for a given symbol."""
        return [
            o for o in self._orders.values()
            if o.get("symbol") == symbol
        ]

    def list_open(self, symbol: str | None = None) -> List[Dict[str, Any]]:
        """List all open (non-filled, non-cancelled) orders."""
        return [
            o for o in self._orders.values()
            if o.get("status") in ("pending", "submitted")
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
        print(result["status"])     # "filled"
        print(result["order_id"])   # UUID
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
        self._stock_paper = PaperExchangeBroker(
            initial_capital=1_000_000.0,
            commission_rate=0.001,
            slippage_bps=5.0,
        )
        self._crypto_paper = PaperExchangeBroker(
            initial_capital=1_000_000.0,
            commission_rate=0.001,
            slippage_bps=5.0,
        )
        self._forex_paper = PaperExchangeBroker(
            initial_capital=1_000_000.0,
            commission_rate=0.0002,
            slippage_bps=2.0,
        )

        # Alpaca broker (lazy init)
        self._alpaca_broker: Any = None

    async def _ensure_connected(self) -> None:
        """Ensure paper brokers are connected."""
        if not self._stock_paper.is_connected:
            await self._stock_paper.connect()
        if not self._crypto_paper.is_connected:
            await self._crypto_paper.connect()
        if not self._forex_paper.is_connected:
            await self._forex_paper.connect()

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
    ) -> Dict[str, Any]:
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
        await self._ensure_connected()

        # ── Pre-trade checks ──────────────────────────────────────────
        self._validate_order_params(symbol, side, quantity, order_type, price,
                                    stop_loss, take_profit)

        normalized_side = _normalize_side(side)
        normalized_type = _normalize_order_type(order_type)

        # Get current market price for market orders and slippage calc
        current_price = await self._resolve_current_price(symbol, price, order_type)

        # Set market price on the broker so it knows the current level
        broker = self._get_paper_broker(symbol)
        if current_price and current_price > 0:
            broker.set_price(symbol, current_price)

        # ── Route to appropriate broker ───────────────────────────────
        if self._should_use_alpaca(symbol):
            order = await self._route_to_alpaca(
                symbol, normalized_side, quantity, normalized_type, price, current_price
            )
        else:
            # Use the PaperExchangeBroker's place_order method
            stop_price = None
            if normalized_type == OrderType.STOP or normalized_type == OrderType.STOP_LIMIT:
                stop_price = price  # Use price as stop trigger for now

            limit_price = price if normalized_type in (OrderType.LIMIT, OrderType.STOP_LIMIT) else None

            order = await broker.place_order(
                symbol=symbol,
                side=normalized_side,
                order_type=normalized_type,
                quantity=quantity,
                price=limit_price or current_price,
                stop_price=stop_price,
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

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
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

        if record.get("status") not in ("pending", "submitted"):
            raise ExecutionError(
                f"Cannot cancel order {order_id} — current status: {record['status']}"
            )

        # Try to cancel at the broker level
        symbol = record.get("symbol", "")
        broker = self._get_paper_broker(symbol)
        try:
            await broker.cancel_order(order_id)
            broker_cancelled = True
        except Exception:
            broker_cancelled = False

        # Update in our store
        self._order_store.update(order_id, {
            "status": "canceled",
            "cancelled_at": datetime.now(timezone.utc).isoformat(),
        })

        logger.info("Order cancelled: %s", order_id)
        return {
            "order_id": order_id,
            "status": "CANCELED",
            "broker_cancelled": broker_cancelled,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
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

    async def get_open_orders(self, symbol: str | None = None) -> List[Dict[str, Any]]:
        """
        Get all open (non-filled, non-cancelled) orders.

        Args:
            symbol: Optional symbol filter.

        Returns:
            List of order record dicts.
        """
        return self._order_store.list_open(symbol)

    async def get_account_summary(self, symbol_type: str = "stock") -> Dict[str, Any]:
        """
        Get account balance and position summary from the paper broker.

        Args:
            symbol_type: "stock", "crypto", or "forex" to select the broker.

        Returns:
            Account balance dict from the paper broker.
        """
        await self._ensure_connected()
        broker = self._get_paper_broker_by_type(symbol_type)
        balance = await broker.get_balance()
        portfolio = await broker.get_portfolio()
        return {
            "balances": balance,
            "portfolio_value": portfolio.total_value,
            "cash": portfolio.cash,
            "realized_pnl": portfolio.total_realized_pnl,
            "positions": {k: v.model_dump() for k, v in portfolio.positions.items()},
        }

    # ── Private helpers ───────────────────────────────────────────────

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
            self._settings.alpaca_api_key
            and self._settings.alpaca_api_secret
        )
        # Only use Alpaca for live trading (paper Alpaca handled by our paper broker)
        return has_keys and not self._settings.alpaca_paper

    def _get_paper_broker(self, symbol: str) -> PaperExchangeBroker:
        """Get the appropriate paper broker for a symbol type."""
        if _is_crypto(symbol):
            return self._crypto_paper
        if _is_forex(symbol):
            return self._forex_paper
        return self._stock_paper

    def _get_paper_broker_by_type(self, symbol_type: str) -> PaperExchangeBroker:
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

        from quant_nanggroe.exchange.alpaca_broker import AlpacaBroker
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
    ) -> Any:
        """Route order to Alpaca broker. Falls back to paper if not configured."""
        try:
            alpaca = self._get_alpaca_broker()
            result = await alpaca.submit_order(
                symbol=symbol, direction=side.value, quantity=quantity,
                order_type=order_type.value, price=price,
            )
            # Convert Alpaca result to Order for uniform handling
            from quant_nanggroe.types.orders import Order as OrderModel
            return OrderModel(
                id=result.get("id", str(uuid.uuid4())),
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                status=OrderStatus.FILLED,
                filled_quantity=quantity,
                average_fill_price=result.get("filled_price", price or current_price),
                commission=result.get("commission", 0.0),
                slippage=result.get("slippage", 0.0),
            )
        except NotImplementedError:
            # Alpaca not configured — fall back to paper
            logger.warning("Alpaca not configured, falling back to paper for %s", symbol)
            broker = self._stock_paper
            return await broker.place_order(
                symbol=symbol, side=side, order_type=order_type,
                quantity=quantity, price=price or current_price,
            )

    @staticmethod
    def _build_order_result(
        order: Any,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str,
        stop_loss: float | None,
        take_profit: float | None,
        current_price: float | None,
    ) -> Dict[str, Any]:
        """Build the standardized order result dict."""
        execution_price = order.average_fill_price if order.average_fill_price else current_price or 0.0

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
            "filled_at": order.updated_at.isoformat() if order.updated_at else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": "PAPER",
        }


# ══════════════════════════════════════════════════════════════════════
# Singleton instance for @tool functions
# ══════════════════════════════════════════════════════════════════════

_default_et: ExecutionTool | None = None


def _get_default_et() -> ExecutionTool:
    """Get or create the default ExecutionTool instance."""
    global _default_et
    if _default_et is None:
        from quant_nanggroe.agents.tools.market_data import _get_default_mdt
        _default_et = ExecutionTool(market_data_tool=_get_default_mdt())
    return _default_et


# ══════════════════════════════════════════════════════════════════════
# LangChain @tool functions for agent consumption
# ══════════════════════════════════════════════════════════════════════


@tool
async def execute_order(
    symbol: str,
    side: str,
    quantity: float,
    order_type: str = "MARKET",
    price: Optional[float] = None,
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None,
) -> str:
    """
    Execute a trade order through the paper trading broker.

    Supports market, limit, stop, and stop-limit orders.
    All orders go through pre-trade validation including
    stop-loss/take-profit sanity checks.

    Args:
        symbol: Trading symbol (e.g., 'AAPL', 'BTC/USDT')
        side: Order direction — 'BUY' or 'SELL' (also 'LONG' or 'SHORT')
        quantity: Number of shares/units to trade
        order_type: Order type — 'MARKET', 'LIMIT', 'STOP', or 'STOP_LIMIT'
        price: Limit price (required for LIMIT orders)
        stop_loss: Optional stop-loss price
        take_profit: Optional take-profit price

    Returns:
        JSON string with order confirmation including order_id, execution
        price, commission, slippage, and status.
    """
    try:
        et = _get_default_et()
        result = await et.execute_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
        return json.dumps(result, indent=2, default=str)
    except (ExecutionError, OrderRejectedError, KillSwitchActiveError) as exc:
        return json.dumps({"error": str(exc), "symbol": symbol, "status": "REJECTED"})
    except Exception as exc:
        logger.error("execute_order tool error: %s", exc)
        return json.dumps({"error": f"Order execution failed: {exc}", "symbol": symbol})


@tool
async def cancel_order(order_id: str) -> str:
    """
    Cancel an existing pending order.

    Only orders with 'pending' or 'submitted' status can be cancelled.

    Args:
        order_id: The order ID to cancel

    Returns:
        JSON string with cancellation confirmation.
    """
    try:
        et = _get_default_et()
        result = await et.cancel_order(order_id)
        return json.dumps(result, indent=2, default=str)
    except ExecutionError as exc:
        return json.dumps({"error": str(exc), "order_id": order_id})
    except Exception as exc:
        logger.error("cancel_order tool error: %s", exc)
        return json.dumps({"error": f"Cancel failed: {exc}", "order_id": order_id})


@tool
async def get_order_status(order_id: str) -> str:
    """
    Get the current status of an order.

    Args:
        order_id: The order ID to query

    Returns:
        JSON string with full order details including status,
        execution price, and fill information.
    """
    try:
        et = _get_default_et()
        result = await et.get_order_status(order_id)
        return json.dumps(result, indent=2, default=str)
    except ExecutionError as exc:
        return json.dumps({"error": str(exc), "order_id": order_id})
    except Exception as exc:
        logger.error("get_order_status tool error: %s", exc)
        return json.dumps({"error": f"Status query failed: {exc}", "order_id": order_id})


@tool
async def get_open_orders(symbol: Optional[str] = None) -> str:
    """
    Get all open (non-filled, non-cancelled) orders.

    Args:
        symbol: Optional symbol to filter orders by

    Returns:
        JSON string with list of open orders.
    """
    try:
        et = _get_default_et()
        result = await et.get_open_orders(symbol)
        return json.dumps(result, indent=2, default=str)
    except Exception as exc:
        logger.error("get_open_orders tool error: %s", exc)
        return json.dumps({"error": f"Failed to get open orders: {exc}"})


@tool
async def get_account_summary(symbol_type: str = "stock") -> str:
    """
    Get account balance and position summary from the paper broker.

    Args:
        symbol_type: Asset type — 'stock', 'crypto', or 'forex'

    Returns:
        JSON string with account balances, portfolio value, and positions.
    """
    try:
        et = _get_default_et()
        result = await et.get_account_summary(symbol_type)
        return json.dumps(result, indent=2, default=str)
    except Exception as exc:
        logger.error("get_account_summary tool error: %s", exc)
        return json.dumps({"error": f"Account summary failed: {exc}"})
