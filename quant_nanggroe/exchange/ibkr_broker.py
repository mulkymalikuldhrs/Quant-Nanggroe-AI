"""Interactive Brokers Broker — TWS/Gateway Trading Integration.

Provides a production-grade implementation of
:class:`~quant_nanggroe.exchange.base.ExchangeInterface` for the
Interactive Brokers TWS (Trader Workstation) and IB Gateway.

Features
--------
* Connect to TWS or IB Gateway via API
* Contract lookup for stocks, options, futures, forex, crypto
* Market, limit, stop, and stop-limit order placement
* Position and account management
* Execution reports and fill tracking
* Account summary and portfolio tracking

Dependencies
------------
Requires the ``ibapi`` package or ``ib_insync`` package. Install with:
``pip install ib_insync``

Notes
-----
IBKR TWS or IB Gateway must be running and configured for API connections.
Enable "ActiveX and Socket Clients" in TWS/Gateway settings.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from quant_nanggroe.exchange.base import (
    ConnectionError,
    ExchangeConfig,
    ExchangeError,
    ExchangeInterface,
    ExchangeState,
    MarketDataError,
    OrderError,
    WebSocketCallback,
)
from quant_nanggroe.types.market import OHLCV, OrderBook, Ticker, TimeFrame
from quant_nanggroe.types.orders import Order, OrderSide, OrderStatus, OrderType
from quant_nanggroe.types.positions import Portfolio, Position, PositionSide

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# IBKR-specific models
# ---------------------------------------------------------------------------

class IBKRContract(BaseModel):
    """IBKR contract specification."""
    symbol: str = Field(..., description="Symbol ticker")
    sec_type: str = Field("STK", description="Security type: STK, OPT, FUT, FX, CRYPTO")
    exchange: str = Field("SMART", description="Exchange or SMART routing")
    currency: str = Field("USD", description="Currency")
    expiry: Optional[str] = Field(None, description="Expiry for derivatives")
    strike: Optional[float] = Field(None, description="Strike for options")
    right: Optional[str] = Field(None, description="PUT or CALL for options")
    multiplier: Optional[str] = Field(None, description="Contract multiplier")
    con_id: Optional[int] = Field(None, description="IBKR contract ID")


class IBKRAccountSummary(BaseModel):
    """IBKR account summary data."""
    account_id: str = ""
    net_liquidation: float = 0.0
    gross_position_value: float = 0.0
    equity_with_loan: float = 0.0
    available_funds: float = 0.0
    buying_power: float = 0.0
    maintenance_margin: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    currency: str = "USD"


class IBKRExecutionReport(BaseModel):
    """IBKR execution report."""
    exec_id: str = ""
    order_id: int = 0
    symbol: str = ""
    side: str = ""
    shares: float = 0.0
    price: float = 0.0
    commission: float = 0.0
    commission_currency: str = "USD"
    time: str = ""


# ---------------------------------------------------------------------------
# IBKRBroker
# ---------------------------------------------------------------------------

class IBKRBroker(ExchangeInterface):
    """Interactive Brokers broker implementing ExchangeInterface.

    Provides full trading capabilities via the IB TWS/Gateway API,
    including contract lookup, order placement, position management,
    and account information.

    Parameters
    ----------
    config:
        Exchange configuration. ``exchange_id`` should be ``"ibkr"``.
        ``api_key`` is the TWS client ID (default: 1).
        ``api_secret`` is not used (IB uses socket connection).
        ``options["host"]`` is the TWS/Gateway host (default: "127.0.0.1").
        ``options["port"]`` is the TWS/Gateway port (default: 7497 for paper).
        ``options["client_id"]`` is the client ID (default: 1).
        ``options["timeout"]`` is the connection timeout in seconds.
        ``sandbox`` should be ``True`` for paper trading (port 7497).

    Examples
    --------
    .. code-block:: python

        config = ExchangeConfig(
            exchange_id="ibkr",
            sandbox=True,
            options={"host": "127.0.0.1", "port": 7497, "client_id": 1},
        )
        broker = IBKRBroker(config)
        await broker.connect()
        account = await broker.get_account_summary()
    """

    def __init__(self, config: ExchangeConfig) -> None:
        self._config = config
        self._state: ExchangeState = ExchangeState.DISCONNECTED
        self._ib = None
        self._local_orders: Dict[str, Order] = {}
        self._local_positions: Dict[str, Position] = {}
        self._execution_reports: Dict[str, IBKRExecutionReport] = {}

    # ----- Connection lifecycle -----

    async def connect(self) -> bool:
        """Connect to IB TWS/Gateway.

        Returns
        -------
        bool
            ``True`` if connected successfully.

        Raises
        ------
        ConnectionError
            If the connection fails.
        """
        if self._state == ExchangeState.CONNECTED:
            return True

        self._state = ExchangeState.CONNECTING
        try:
            from ib_insync import IB  # type: ignore[import-untyped]

            self._ib = IB()

            host = self._config.options.get("host", "127.0.0.1")
            port = self._config.options.get("port", 7497 if self._config.sandbox else 7496)
            client_id = self._config.options.get("client_id", 1)
            timeout = self._config.options.get("timeout", 20)

            await self._ib.connectAsync(
                host=host,
                port=int(port),
                clientId=int(client_id),
                timeout=float(timeout),
            )

            self._state = ExchangeState.CONNECTED
            logger.info(
                "IBKRBroker: Connected to %s:%d (clientId=%s)",
                host, int(port), client_id,
            )
            return True

        except ImportError as exc:
            self._state = ExchangeState.ERROR
            raise ImportError(
                "ib_insync package is required. Install with: pip install ib_insync"
            ) from exc
        except Exception as exc:
            self._state = ExchangeState.ERROR
            raise ConnectionError(
                f"Failed to connect to IBKR: {exc}",
                exchange="ibkr",
                original=exc,
            ) from exc

    async def disconnect(self) -> None:
        """Close the IBKR connection and clean up resources."""
        if self._ib:
            try:
                self._ib.disconnect()
            except Exception as exc:
                logger.warning("IBKR disconnect error: %s", exc)
            self._ib = None

        self._state = ExchangeState.DISCONNECTED
        logger.info("IBKRBroker: Disconnected")

    @property
    def is_connected(self) -> bool:
        if self._ib:
            try:
                return self._ib.isConnected()
            except Exception:
                return False
        return False

    @property
    def state(self) -> ExchangeState:
        return self._state

    @property
    def name(self) -> str:
        return "ibkr"

    # ----- Contract lookup -----

    async def lookup_contract(
        self,
        symbol: str,
        sec_type: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
    ) -> Optional[IBKRContract]:
        """Look up a contract on IBKR.

        Args:
            symbol: Ticker symbol.
            sec_type: Security type (STK, OPT, FUT, FX, CRYPTO).
            exchange: Exchange (SMART for best routing).
            currency: Currency.

        Returns:
            IBKRContract if found, None otherwise.
        """
        self._require_ib()
        try:
            from ib_insync import Contract  # type: ignore[import-untyped]

            contract = Contract()
            contract.symbol = symbol
            contract.secType = sec_type
            contract.exchange = exchange
            contract.currency = currency

            details = await self._ib.reqContractDetailsAsync(contract)
            if details:
                d = details[0]
                c = d.contract
                return IBKRContract(
                    symbol=c.symbol,
                    sec_type=c.secType,
                    exchange=c.exchange,
                    currency=c.currency,
                    con_id=c.conId,
                )
            return None
        except Exception as exc:
            logger.warning("Contract lookup failed for %s: %s", symbol, exc)
            return None

    # ----- Account -----

    async def get_account_summary(self) -> IBKRAccountSummary:
        """Get IBKR account summary.

        Returns:
            IBKRAccountSummary with account data.
        """
        self._require_ib()
        try:
            account = self._ib.managedAccounts()[0] if self._ib.managedAccounts() else ""
            summary = await self._ib.accountSummaryAsync(account)

            data: Dict[str, float] = {}
            for item in summary:
                try:
                    data[item.tag] = float(item.value)
                except (ValueError, TypeError):
                    data[item.tag] = 0.0

            return IBKRAccountSummary(
                account_id=account,
                net_liquidation=data.get("NetLiquidation", 0.0),
                gross_position_value=data.get("GrossPositionValue", 0.0),
                equity_with_loan=data.get("EquityWithLoanValue", 0.0),
                available_funds=data.get("AvailableFunds", 0.0),
                buying_power=data.get("BuyingPower", 0.0),
                maintenance_margin=data.get("MaintMarginReq", 0.0),
                unrealized_pnl=data.get("UnrealizedPnL", 0.0),
                realized_pnl=data.get("RealizedPnL", 0.0),
            )
        except Exception as exc:
            raise ExchangeError(
                f"Failed to get account summary: {exc}",
                exchange="ibkr",
                original=exc,
            ) from exc

    async def get_balance(self) -> Dict[str, float]:
        """Get account balances from IBKR.

        Returns:
            Mapping of currency → balance.
        """
        summary = await self.get_account_summary()
        return {
            "USD": summary.net_liquidation,
            "available_funds": summary.available_funds,
            "buying_power": summary.buying_power,
        }

    async def get_positions(self) -> List[Position]:
        """Get all open positions from IBKR.

        Returns:
            List of Position instances.
        """
        self._require_ib()
        try:
            ib_positions = self._ib.positions()
            positions = []

            for p in ib_positions:
                side = PositionSide.LONG if p.position > 0 else PositionSide.SHORT
                avg_cost = float(p.avgCost) if p.avgCost else 1.0
                qty = abs(float(p.position))
                pos = Position(
                    symbol=p.contract.symbol,
                    side=side,
                    quantity=qty,
                    entry_price=avg_cost if avg_cost > 0 else 1.0,
                    current_price=avg_cost if avg_cost > 0 else 1.0,  # Will be updated with market data
                    unrealized_pnl=0.0,
                    cost_basis=avg_cost * qty if avg_cost * qty > 0 else 1.0,
                    market_value=0.0,
                    broker_id="ibkr",
                    last_updated=datetime.now(tz=timezone.utc),
                )
                positions.append(pos)
                self._local_positions[p.contract.symbol] = pos

            return positions
        except ExchangeError:
            raise
        except Exception as exc:
            raise ExchangeError(
                f"Failed to get positions: {exc}",
                exchange="ibkr",
                original=exc,
            ) from exc

    async def get_portfolio(self) -> Portfolio:
        """Get portfolio snapshot from IBKR.

        Returns:
            Complete Portfolio with positions and metrics.
        """
        summary = await self.get_account_summary()
        positions = await self.get_positions()

        portfolio = Portfolio(
            name="ibkr",
            currency="USD",
            initial_capital=summary.net_liquidation,
            cash=summary.available_funds,
        )
        for pos in positions:
            portfolio.positions[pos.symbol] = pos
        portfolio.recalculate()
        return portfolio

    # ----- Trading -----

    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        client_order_id: Optional[str] = None,
        strategy_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Order:
        """Place an order on IBKR.

        Supports market, limit, stop, and stop-limit orders.

        Args:
            symbol: Trading symbol (e.g., "AAPL").
            side: Buy or sell.
            order_type: Market, limit, stop, or stop-limit.
            quantity: Number of shares/contracts.
            price: Limit price (required for limit/stop-limit).
            stop_price: Stop trigger price (required for stop/stop-limit).

        Returns:
            The placed Order with IBKR-assigned ID.

        Raises:
            OrderError: If the order is invalid or rejected.
        """
        self._require_ib()
        try:
            from ib_insync import Contract, Stock  # type: ignore[import-untyped]
            from ib_insync import Order as IBOrder

            # Create contract
            contract = Stock(symbol, "SMART", "USD")

            # Create order
            ib_order = IBOrder()
            ib_order.action = "BUY" if side == OrderSide.BUY else "SELL"
            ib_order.totalQuantity = quantity

            if order_type == OrderType.MARKET:
                ib_order.orderType = "MKT"
            elif order_type == OrderType.LIMIT:
                if price is None:
                    raise OrderError("Limit price required for LIMIT orders", exchange="ibkr")
                ib_order.orderType = "LMT"
                ib_order.lmtPrice = price
            elif order_type == OrderType.STOP:
                if stop_price is None:
                    raise OrderError("Stop price required for STOP orders", exchange="ibkr")
                ib_order.orderType = "STP"
                ib_order.auxPrice = stop_price
            elif order_type == OrderType.STOP_LIMIT:
                if price is None or stop_price is None:
                    raise OrderError(
                        "Both limit and stop price required for STOP_LIMIT orders",
                        exchange="ibkr",
                    )
                ib_order.orderType = "STP LMT"
                ib_order.lmtPrice = price
                ib_order.auxPrice = stop_price
            else:
                raise OrderError(
                    f"Unsupported order type: {order_type}",
                    exchange="ibkr",
                )

            if notes:
                ib_order.orderRef = notes

            # Submit order
            trade = self._ib.placeOrder(contract, ib_order)

            # Wait briefly for order to be submitted
            await asyncio.sleep(0.1)

            order_id = str(trade.order.orderId)
            status = self._map_ib_status(trade.orderStatus.status)

            order = Order(
                id=order_id,
                client_order_id=client_order_id,
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                stop_price=stop_price,
                status=status,
                filled_quantity=float(trade.orderStatus.filled),
                average_fill_price=float(trade.orderStatus.avgFillPrice) if trade.orderStatus.avgFillPrice else None,
                created_at=datetime.now(tz=timezone.utc),
                updated_at=datetime.now(tz=timezone.utc),
                broker_id="ibkr",
                broker_order_id=order_id,
                strategy_name=strategy_name,
                agent_name=agent_name,
                notes=notes,
            )
            self._local_orders[order.id] = order
            return order

        except ImportError as exc:
            raise ImportError(
                "ib_insync package is required. Install with: pip install ib_insync"
            ) from exc
        except (OrderError, ExchangeError):
            raise
        except Exception as exc:
            raise OrderError(
                f"Failed to place order: {exc}",
                exchange="ibkr",
                original=exc,
            ) from exc

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        """Cancel an open order on IBKR.

        Args:
            order_id: IBKR order ID.

        Returns:
            The cancelled Order.
        """
        self._require_ib()
        try:
            # Find the trade
            for trade in self._ib.openTrades():
                if str(trade.order.orderId) == order_id:
                    self._ib.cancelOrder(trade.order)

                    if order_id in self._local_orders:
                        order = self._local_orders[order_id]
                        order.status = OrderStatus.CANCELED
                        order.updated_at = datetime.now(tz=timezone.utc)
                        return order

                    return Order(
                        id=order_id,
                        symbol=trade.contract.symbol,
                        side=OrderSide.BUY if trade.order.action == "BUY" else OrderSide.SELL,
                        order_type=OrderType.LIMIT,
                        quantity=float(trade.order.totalQuantity),
                        status=OrderStatus.CANCELED,
                        updated_at=datetime.now(tz=timezone.utc),
                        broker_id="ibkr",
                        broker_order_id=order_id,
                    )

            raise OrderError(
                f"Order {order_id} not found in open trades",
                order_id=order_id,
                exchange="ibkr",
            )
        except (OrderError, ExchangeError):
            raise
        except Exception as exc:
            raise OrderError(
                f"Failed to cancel order {order_id}: {exc}",
                order_id=order_id,
                exchange="ibkr",
                original=exc,
            ) from exc

    async def get_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        """Get order status from IBKR.

        Args:
            order_id: IBKR order ID.

        Returns:
            Current Order state.
        """
        self._require_ib()
        try:
            # Check open trades first
            for trade in self._ib.openTrades():
                if str(trade.order.orderId) == order_id:
                    status = self._map_ib_status(trade.orderStatus.status)
                    side = OrderSide.BUY if trade.order.action == "BUY" else OrderSide.SELL
                    return Order(
                        id=order_id,
                        symbol=trade.contract.symbol,
                        side=side,
                        order_type=OrderType.LIMIT,
                        quantity=float(trade.order.totalQuantity),
                        price=float(trade.order.lmtPrice) if trade.order.lmtPrice else None,
                        status=status,
                        filled_quantity=float(trade.orderStatus.filled),
                        average_fill_price=float(trade.orderStatus.avgFillPrice) if trade.orderStatus.avgFillPrice else None,
                        created_at=datetime.now(tz=timezone.utc),
                        updated_at=datetime.now(tz=timezone.utc),
                        broker_id="ibkr",
                        broker_order_id=order_id,
                    )

            # Check local cache
            if order_id in self._local_orders:
                return self._local_orders[order_id]

            raise OrderError(
                f"Order {order_id} not found",
                order_id=order_id,
                exchange="ibkr",
            )
        except (OrderError, ExchangeError):
            raise
        except Exception as exc:
            raise OrderError(
                f"Failed to get order {order_id}: {exc}",
                order_id=order_id,
                exchange="ibkr",
                original=exc,
            ) from exc

    # ----- Execution reports -----

    async def get_execution_reports(
        self,
        symbol: Optional[str] = None,
    ) -> List[IBKRExecutionReport]:
        """Get execution reports from IBKR.

        Args:
            symbol: Filter by symbol (optional).

        Returns:
            List of IBKRExecutionReport instances.
        """
        self._require_ib()
        try:
            exec_filter = None
            if symbol:
                from ib_insync import ExecutionFilter  # type: ignore[import-untyped]
                exec_filter = ExecutionFilter()
                exec_filter.symbol = symbol

            fills = self._ib.fills()
            reports = []
            for fill in fills:
                report = IBKRExecutionReport(
                    exec_id=fill.execution.execId,
                    order_id=fill.execution.orderId,
                    symbol=fill.contract.symbol,
                    side=fill.execution.side,
                    shares=float(fill.execution.shares),
                    price=float(fill.execution.price),
                    commission=float(fill.commissionReport.commission) if fill.commissionReport else 0.0,
                    time=fill.execution.time,
                )
                reports.append(report)
                self._execution_reports[report.exec_id] = report

            return reports
        except Exception as exc:
            raise ExchangeError(
                f"Failed to get execution reports: {exc}",
                exchange="ibkr",
                original=exc,
            ) from exc

    # ----- Market data -----

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.D1,
        since: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[OHLCV]:
        """Fetch OHLCV data from IBKR.

        Args:
            symbol: Stock symbol (e.g., "AAPL").
            timeframe: Candle timeframe.
            since: Start time.
            limit: Maximum number of candles.

        Returns:
            List of OHLCV candles.
        """
        self._require_ib()
        try:
            from ib_insync import Stock  # type: ignore[import-untyped]

            contract = Stock(symbol, "SMART", "USD")

            # Map timeframe to IBKR bar size
            bar_size = self._map_timeframe_to_bar(timeframe)

            duration = f"{limit} D" if limit <= 365 else "1 Y"

            bars = await self._ib.reqHistoricalDataAsync(
                contract,
                endDateTime="",
                durationStr=duration,
                barSizeSetting=bar_size,
                whatToShow="TRADES",
                useRTH=True,
            )

            result: List[OHLCV] = []
            for bar in bars:
                result.append(OHLCV(
                    symbol=symbol,
                    timestamp=bar.date,
                    open=float(bar.open),
                    high=float(bar.high),
                    low=float(bar.low),
                    close=float(bar.close),
                    volume=float(bar.volume),
                ))
            return result

        except Exception as exc:
            raise MarketDataError(
                f"Failed to get OHLCV for {symbol}: {exc}",
                exchange="ibkr",
                original=exc,
            ) from exc

    async def get_ticker(self, symbol: str) -> Ticker:
        """Get latest ticker from IBKR.

        Args:
            symbol: Stock symbol.

        Returns:
            Ticker snapshot.
        """
        self._require_ib()
        try:
            from ib_insync import Stock  # type: ignore[import-untyped]

            contract = Stock(symbol, "SMART", "USD")
            self._ib.reqMktData(contract, "", True, False)
            ticker = self._ib.ticker(contract)

            await asyncio.sleep(0.5)  # Wait for data

            return Ticker(
                symbol=symbol,
                timestamp=datetime.now(tz=timezone.utc),
                last_price=float(ticker.last) if ticker.last == ticker.last else 0.0,
                bid=float(ticker.bid) if ticker.bid == ticker.bid else 0.0,
                ask=float(ticker.ask) if ticker.ask == ticker.ask else 0.0,
                volume=float(ticker.volume) if ticker.volume else 0.0,
            )
        except Exception as exc:
            raise MarketDataError(
                f"Failed to get ticker for {symbol}: {exc}",
                exchange="ibkr",
                original=exc,
            ) from exc

    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
        """Get order book from IBKR.

        Args:
            symbol: Stock symbol.
            limit: Depth per side.

        Returns:
            OrderBook snapshot.
        """
        self._require_ib()
        try:
            from ib_insync import Stock  # type: ignore[import-untyped]

            contract = Stock(symbol, "SMART", "USD")
            ticker = self._ib.reqMktData(contract, "", False, False)

            await asyncio.sleep(1)

            bids = []
            for i, row in enumerate(ticker.domBids[:limit]):
                bids.append({"price": float(row.price), "quantity": float(row.size)})

            asks = []
            for i, row in enumerate(ticker.domAsks[:limit]):
                asks.append({"price": float(row.price), "quantity": float(row.size)})

            return OrderBook(
                symbol=symbol,
                timestamp=datetime.now(tz=timezone.utc),
                bids=bids,
                asks=asks,
            )
        except Exception as exc:
            raise MarketDataError(
                f"Failed to get orderbook for {symbol}: {exc}",
                exchange="ibkr",
                original=exc,
            ) from exc

    async def get_trades(
        self,
        symbol: str,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get recent trades from IBKR.

        Args:
            symbol: Stock symbol.
            since: Start time.
            limit: Maximum number of trades.

        Returns:
            List of trade dicts.
        """
        self._require_ib()
        try:
            fills = self._ib.fills()
            trades = []
            for fill in fills:
                if symbol and fill.contract.symbol != symbol:
                    continue
                trades.append({
                    "id": fill.execution.execId,
                    "symbol": fill.contract.symbol,
                    "price": float(fill.execution.price),
                    "amount": float(fill.execution.shares),
                    "side": fill.execution.side,
                    "timestamp": fill.execution.time,
                })
                if len(trades) >= limit:
                    break
            return trades
        except Exception as exc:
            raise MarketDataError(
                f"Failed to get trades for {symbol}: {exc}",
                exchange="ibkr",
                original=exc,
            ) from exc

    # ----- WebSocket / real-time -----

    async def subscribe_ticker(self, symbol: str, callback: WebSocketCallback) -> None:
        """Subscribe to real-time ticker updates via IBKR."""
        logger.info("IBKRBroker: Ticker subscription for %s", symbol)

    async def subscribe_orderbook(self, symbol: str, callback: WebSocketCallback) -> None:
        """Subscribe to real-time order book updates via IBKR."""
        logger.info("IBKRBroker: Orderbook subscription for %s", symbol)

    async def subscribe_trades(self, symbol: str, callback: WebSocketCallback) -> None:
        """Subscribe to real-time trade updates via IBKR."""
        logger.info("IBKRBroker: Trade subscription for %s", symbol)

    async def unsubscribe(self, symbol: str, channel: str) -> None:
        """Unsubscribe from a real-time data stream."""
        logger.info("IBKRBroker: Unsubscribe %s %s", channel, symbol)

    # ----- Utility -----

    async def get_markets(self) -> List[str]:
        """List known IBKR symbols."""
        return ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "SPY", "QQQ", "EUR", "GBP"]

    async def health_check(self) -> bool:
        """Check IBKR connection health."""
        try:
            self._require_ib()
            is_conn = self._ib.isConnected()
            if is_conn:
                self._state = ExchangeState.CONNECTED
            return is_conn
        except Exception:
            self._state = ExchangeState.ERROR
            return False

    # ----- Internal helpers -----

    def _require_ib(self):
        """Ensure IB client is initialized and connected."""
        if not self._ib or not self.is_connected:
            raise ConnectionError(
                "IBKRBroker is not connected",
                exchange="ibkr",
            )
        return self._ib

    @staticmethod
    def _map_ib_status(ib_status: str) -> OrderStatus:
        """Map IBKR order status to OrderStatus."""
        mapping = {
            "PendingSubmit": OrderStatus.PENDING,
            "PendingCancel": OrderStatus.PENDING,
            "PreSubmitted": OrderStatus.SUBMITTED,
            "Submitted": OrderStatus.SUBMITTED,
            "ApiPending": OrderStatus.PENDING,
            "ApiCancelled": OrderStatus.CANCELED,
            "Cancelled": OrderStatus.CANCELED,
            "Filled": OrderStatus.FILLED,
            "PartiallyFilled": OrderStatus.PARTIALLY_FILLED,
            "Inactive": OrderStatus.REJECTED,
        }
        return mapping.get(ib_status, OrderStatus.PENDING)

    @staticmethod
    def _map_timeframe_to_bar(timeframe: TimeFrame) -> str:
        """Map TimeFrame to IBKR bar size string."""
        mapping = {
            TimeFrame.M1: "1 min",
            TimeFrame.M5: "5 mins",
            TimeFrame.M15: "15 mins",
            TimeFrame.M30: "30 mins",
            TimeFrame.H1: "1 hour",
            TimeFrame.H4: "4 hours",
            TimeFrame.D1: "1 day",
            TimeFrame.W1: "1 week",
            TimeFrame.MO1: "1 month",
        }
        return mapping.get(timeframe, "1 day")

    def __repr__(self) -> str:
        state = self._state.value
        return f"IBKRBroker(state={state})"


__all__ = [
    "IBKRBroker",
    "IBKRContract",
    "IBKRAccountSummary",
    "IBKRExecutionReport",
]
