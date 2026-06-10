"""
MetaTrader MT4/MT5 Web API Integration
Connects to MetaTrader Web Terminal for order execution.
Supports both MT4 and MT5 platforms.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod
from dataclasses import dataclass
import asyncio
import aiohttp
import json
import hmac
import hashlib
import time
from urllib.parse import urlencode, quote

import pandas as pd

logger = logging.getLogger(__name__)


class BrokerType(Enum):
    """Broker platform types"""

    MT4 = "mt4"
    MT5 = "mt5"


class OrderType(Enum):
    """Order types for MetaTrader"""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    """Order sides"""

    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """Order statuses"""

    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class PositionSide(Enum):
    """Position sides"""

    LONG = "long"
    SHORT = "short"


@dataclass
class Order:
    """Trading order"""

    order_id: str
    broker_order_id: str
    ticker: str
    order_type: OrderType
    side: OrderSide
    quantity: float
    price: Optional[float]
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_price: float = 0
    filled_quantity: float = 0
    commission: float = 0
    created_at: datetime = field(default_factory=datetime.now)
    filled_at: Optional[datetime] = None
    error_message: str = ""


@dataclass
class Position:
    """Open position"""

    position_id: str
    ticker: str
    side: PositionSide
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    open_time: datetime


@dataclass
class AccountInfo:
    """Trading account information"""

    account_id: str
    broker_type: BrokerType
    balance: float
    equity: float
    margin: float
    free_margin: float
    margin_level: float
    leverage: float
    currency: str


@dataclass
class Tick:
    """Market tick data"""

    ticker: str
    bid: float
    ask: float
    last: float
    volume: float
    timestamp: datetime


class MetaTraderAPIError(Exception):
    """Custom exception for API errors"""

    def __init__(self, message, code=None):
        self.message = message
        self.code = code
        super().__init__(message)


class MetaTraderWebAPI(ABC):
    """Abstract base class for MetaTrader Web API."""

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the API."""
        pass

    @abstractmethod
    async def authenticate(self, credentials: Dict) -> bool:
        """Authenticate with the broker."""
        pass

    @abstractmethod
    async def get_account_info(self) -> AccountInfo:
        """Get account information."""
        pass

    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Get open positions."""
        pass

    @abstractmethod
    async def get_orders(self, pending_only: bool = True) -> List[Order]:
        """Get pending orders."""
        pass

    @abstractmethod
    async def place_order(self, order: Order) -> Order:
        """Place a new order."""
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        pass

    @abstractmethod
    async def modify_position(self, position_id: str, stop_loss: float = None, take_profit: float = None) -> bool:
        """Modify position SL/TP."""
        pass

    @abstractmethod
    async def close_position(self, position_id: str, quantity: float = None) -> bool:
        """Close a position."""
        pass

    @abstractmethod
    async def get_tick(self, ticker: str) -> Tick:
        """Get current market tick."""
        pass

    @abstractmethod
    async def get_historical_data(self, ticker: str, timeframe: str, count: int) -> pd.DataFrame:
        """Get historical OHLC data."""
        pass


class MetaTraderMT5API(MetaTraderWebAPI):
    """
    MetaTrader 5 Web API implementation.

    Uses the official MT5 Web API or compatible API endpoints.
    """

    def __init__(self, server_url: str, account: str, password: str, broker_type: BrokerType = BrokerType.MT5):
        """
        Initialize MT5 API.

        Args:
            server_url: Web API server URL
            account: Account number
            password: Account password
            broker_type: MT4 or MT5
        """
        self.server_url = server_url.rstrip("/")
        self.account = account
        self.password = password
        self.broker_type = broker_type

        self.session_token = None
        self.is_connected = False

        self._session = None
        self._last_request_time = 0
        self._min_request_interval = 0.1  # 100ms between requests

    async def connect(self) -> bool:
        """Establish connection to the API."""
        try:
            self._session = aiohttp.ClientSession()
            self.is_connected = True
            logger.info(f"Connected to MetaTrader {self.broker_type.value} API")
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False

    async def authenticate(self, credentials: Dict = None) -> bool:
        """Authenticate with the broker."""
        auth_data = {"action": "auth", "account": credentials.get("account", self.account), "password": credentials.get("password", self.password), "broker_type": self.broker_type.value}

        try:
            result = await self._request("auth", auth_data)
            if result.get("retcode") == 0:
                self.session_token = result.get("token")
                logger.info(f"Authenticated successfully")
                return True
            else:
                logger.error(f"Authentication failed: {result.get('comment')}")
                return False
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False

    async def get_account_info(self) -> AccountInfo:
        """Get account information."""
        result = await self._request("account_info", {})

        return AccountInfo(account_id=str(result.get("login", self.account)), broker_type=self.broker_type, balance=result.get("balance", 0), equity=result.get("equity", 0), margin=result.get("margin", 0), free_margin=result.get("margin_free", 0), margin_level=result.get("margin_level", 0), leverage=result.get("leverage", 100), currency=result.get("currency", "USD"))

    async def get_positions(self) -> List[Position]:
        """Get open positions."""
        result = await self._request("positions", {})
        positions = []

        for pos in result.get("positions", []):
            positions.append(
                Position(
                    position_id=str(pos.get("ticket", "")),
                    ticker=pos.get("symbol", ""),
                    side=PositionSide.LONG if pos.get("type", 0) == 0 else PositionSide.SHORT,
                    quantity=pos.get("volume", 0) / 10000,  # MT5 uses lots * 10000
                    entry_price=pos.get("price_open", 0),
                    current_price=pos.get("price_current", 0),
                    unrealized_pnl=pos.get("profit", 0),
                    unrealized_pnl_pct=pos.get("profit", 0) / pos.get("price_open", 1) * 100,
                    stop_loss=pos.get("sl", 0) if pos.get("sl", 0) > 0 else None,
                    take_profit=pos.get("tp", 0) if pos.get("tp", 0) > 0 else None,
                    open_time=datetime.fromtimestamp(pos.get("time", 0)),
                )
            )

        return positions

    async def get_orders(self, pending_only: bool = True) -> List[Order]:
        """Get pending orders."""
        params = {"pending_only": pending_only}
        result = await self._request("orders", params)
        orders = []

        for ord in result.get("orders", []):
            order_type_map = {0: OrderType.MARKET, 1: OrderType.LIMIT, 2: OrderType.STOP, 3: OrderType.STOP_LIMIT}

            side_map = {0: OrderSide.BUY, 1: OrderSide.SELL}

            orders.append(
                Order(
                    order_id=str(ord.get("ticket", "")),
                    broker_order_id=str(ord.get("ticket", "")),
                    ticker=ord.get("symbol", ""),
                    order_type=order_type_map.get(ord.get("type", 0), OrderType.MARKET),
                    side=side_map.get(ord.get("type", 0) % 2, OrderSide.BUY),
                    quantity=ord.get("volume", 0) / 10000,
                    price=ord.get("price_open", 0),
                    stop_loss=ord.get("sl", 0) if ord.get("sl", 0) > 0 else None,
                    take_profit=ord.get("tp", 0) if ord.get("tp", 0) > 0 else None,
                    status=OrderStatus.PENDING if ord.get("state", "") == "ORDER_STATE_PLACED" else OrderStatus.OPEN,
                )
            )

        return orders

    async def place_order(self, order: Order) -> Order:
        """Place a new order."""
        order_type_map = {OrderType.MARKET: 0, OrderType.LIMIT: 1, OrderType.STOP: 2, OrderType.STOP_LIMIT: 3}

        side_map = {OrderSide.BUY: 0, OrderSide.SELL: 1}

        request_data = {
            "action": "trade",
            "symbol": order.ticker,
            "type": order_type_map.get(order.order_type, 0),
            "side": side_map.get(order.side, 0),
            "volume": order.quantity * 10000,  # Convert to MT5 lots
            "price": order.price,
            "sl": order.stop_loss if order.stop_loss and order.stop_loss > 0 else 0,
            "tp": order.take_profit if order.take_profit and order.take_profit > 0 else 0,
            "deviation": 10,  # Slippage deviation in points
            "comment": f"AI Hedge Fund",
        }

        result = await self._request("trade", request_data)

        if result.get("retcode") == 0:
            order.broker_order_id = str(result.get("order", ""))
            order.status = OrderStatus.PENDING
            logger.info(f"Order placed successfully: {order.broker_order_id}")
        else:
            order.status = OrderStatus.REJECTED
            order.error_message = result.get("comment", "Unknown error")
            logger.error(f"Order rejected: {order.error_message}")

        return order

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        request_data = {"action": "trade", "order": int(order_id), "type": 1}  # Order delete

        result = await self._request("trade", request_data)
        return result.get("retcode") == 0

    async def modify_position(self, position_id: str, stop_loss: float = None, take_profit: float = None) -> bool:
        """Modify position SL/TP."""
        request_data = {"action": "trade", "position": int(position_id), "sl": stop_loss if stop_loss else 0, "tp": take_profit if take_profit else 0}

        result = await self._request("trade", request_data)
        return result.get("retcode") == 0

    async def close_position(self, position_id: str, quantity: float = None) -> bool:
        """Close a position."""
        request_data = {
            "action": "trade",
            "position": int(position_id),
            "volume": (quantity * 10000) if quantity else 0,  # 0 = close all
        }

        result = await self._request("trade", request_data)
        return result.get("retcode") == 0

    async def get_tick(self, ticker: str) -> Tick:
        """Get current market tick."""
        result = await self._request("tick", {"symbol": ticker})

        tick_data = result.get("tick", {})

        return Tick(ticker=ticker, bid=tick_data.get("bid", 0), ask=tick_data.get("ask", 0), last=tick_data.get("last", 0), volume=tick_data.get("volume", 0), timestamp=datetime.fromtimestamp(tick_data.get("time", 0)))

    async def get_historical_data(self, ticker: str, timeframe: str, count: int) -> pd.DataFrame:
        """Get historical OHLC data."""
        timeframe_map = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440, "1w": 10080, "1M": 43200}

        params = {"symbol": ticker, "timeframe": timeframe_map.get(timeframe, 60), "count": count}

        result = await self._request("rates", params)

        rates = result.get("rates", [])

        if not rates:
            return pd.DataFrame()

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df.set_index("time", inplace=True)

        return df.rename(columns={"open": "open", "high": "high", "low": "low", "close": "close", "tick_volume": "volume"})

    async def _request(self, endpoint: str, params: Dict) -> Dict:
        """Make API request with rate limiting."""
        # Rate limiting
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._min_request_interval:
            await asyncio.sleep(self._min_request_interval - elapsed)

        url = f"{self.server_url}/{endpoint}"

        headers = {}
        if self.session_token:
            headers["Authorization"] = f"Bearer {self.session_token}"

        try:
            async with self._session.post(url, json=params, headers=headers) as response:
                result = await response.json()
                self._last_request_time = time.time()
                return result
        except Exception as e:
            logger.error(f"API request failed: {e}")
            raise MetaTraderAPIError(str(e))


class MetaTraderMT4API(MetaTraderMT5API):
    """
    MetaTrader 4 Web API implementation.

    Inherits from MT5 with minor adjustments for MT4 differences.
    """

    def __init__(self, server_url: str, account: str, password: str):
        """Initialize MT4 API."""
        super().__init__(server_url, account, password, BrokerType.MT4)

    async def place_order(self, order: Order) -> Order:
        """Place order (MT4 specific)."""
        # MT4 uses different order types
        order_type_map = {OrderType.MARKET: 0, OrderType.LIMIT: 2, OrderType.STOP: 3}  # MT4 uses 2 for buy limit  # MT4 uses 3 for buy stop

        side_map = {OrderSide.BUY: 0, OrderSide.SELL: 1}

        # Adjust for MT4
        if order.order_type in [OrderType.LIMIT, OrderType.STOP]:
            if order.side == OrderSide.SELL:
                order_type_map[order.order_type] += 1  # Sell limit/stop

        request_data = {"action": "trade", "symbol": order.ticker, "type": order_type_map.get(order.order_type, 0), "volume": order.quantity, "price": order.price, "sl": order.stop_loss if order.stop_loss else 0, "tp": order.take_profit if order.take_profit else 0, "comment": "AI Hedge Fund"}  # MT4 uses lots directly

        result = await self._request("trade", request_data)

        if result.get("retcode") == 0:
            order.broker_order_id = str(result.get("order", ""))
            order.status = OrderStatus.PENDING
        else:
            order.status = OrderStatus.REJECTED
            order.error_message = result.get("comment", "Unknown error")

        return order


class MetaTraderBroker:
    """
    High-level broker interface for MetaTrader.

    Handles:
    - Order management
    - Position management
    - Risk management
    - Multi-account support
    """

    def __init__(self, api: MetaTraderWebAPI):
        """
        Initialize broker.

        Args:
            api: MetaTrader API instance
        """
        self.api = api
        self.is_connected = False

    async def connect(self, credentials: Dict = None) -> bool:
        """Connect and authenticate."""
        connected = await self.api.connect()
        if connected:
            self.is_connected = await self.api.authenticate(credentials)
        return self.is_connected

    async def get_account(self) -> AccountInfo:
        """Get account information."""
        return await self.api.get_account_info()

    async def get_balance(self) -> float:
        """Get current balance."""
        account = await self.get_account()
        return account.balance

    async def get_equity(self) -> float:
        """Get current equity."""
        account = await self.get_account()
        return account.equity

    async def place_trade(self, ticker: str, side: OrderSide, quantity: float, order_type: OrderType = OrderType.MARKET, price: float = None, stop_loss: float = None, take_profit: float = None) -> Order:
        """Place a trade."""
        order = Order(order_id="", broker_order_id="", ticker=ticker, order_type=order_type, side=side, quantity=quantity, price=price, stop_loss=stop_loss, take_profit=take_profit)

        return await self.api.place_order(order)

    async def close_all_positions(self) -> bool:
        """Close all open positions."""
        positions = await self.api.get_positions()
        success = True

        for position in positions:
            if not await self.api.close_position(position.position_id):
                success = False

        return success

    async def set_sl_tp(self, position_id: str, stop_loss: float = None, take_profit: float = None) -> bool:
        """Modify position SL/TP."""
        return await self.api.modify_position(position_id, stop_loss, take_profit)

    async def get_positions(self) -> List[Position]:
        """Get all open positions."""
        return await self.api.get_positions()

    async def get_market_price(self, ticker: str) -> Tuple[float, float]:
        """Get current bid/ask prices."""
        tick = await self.api.get_tick(ticker)
        return tick.bid, tick.ask


class HedgeFundBrokerManager:
    """
    Multi-account hedge fund broker manager.

    Manages multiple broker accounts and executes trades across them.
    """

    def __init__(self):
        self.brokers: Dict[str, MetaTraderBroker] = {}
        self.master_positions: Dict[str, List[Position]] = {}
        self.execution_mode: str = "AUTO"  # AUTO, MANUAL_CONFIRM

    def add_broker(self, name: str, broker: MetaTraderBroker):
        """Add a broker account."""
        self.brokers[name] = broker
        logger.info(f"Added broker: {name}")

    async def connect_all(self, credentials: Dict[str, Dict] = None) -> Dict[str, bool]:
        """Connect to all brokers."""
        results = {}

        for name, broker in self.brokers.items():
            creds = credentials.get(name, {}) if credentials else None
            connected = await broker.connect(creds)
            results[name] = connected
            logger.info(f"Broker {name}: {'Connected' if connected else 'Failed'}")

        return results

    async def execute_master_signal(self, ticker: str, side: OrderSide, quantity: float, stop_loss: float = None, take_profit: float = None, split_mode: str = "EQUAL") -> Dict[str, Order]:  # EQUAL, WEIGHTED, SINGLE
        """
        Execute signal across multiple accounts.

        Args:
            ticker: Asset to trade
            side: Buy or sell
            quantity: Total quantity
            stop_loss: Optional stop loss
            take_profit: Optional take profit
            split_mode: How to split between accounts

        Returns:
            Dict of {broker_name: Order}
        """
        results = {}

        if split_mode == "SINGLE":
            # Execute on primary broker only
            primary = list(self.brokers.keys())[0]
            order = await self.brokers[primary].place_trade(ticker, side, quantity, stop_loss=stop_loss, take_profit=take_profit)
            results[primary] = order
        else:
            # Calculate allocation
            active_brokers = {k: v for k, v in self.brokers.items() if v.is_connected}
            n_brokers = len(active_brokers)

            if n_brokers == 0:
                raise Exception("No connected brokers")

            if split_mode == "EQUAL":
                allocated_qty = quantity / n_brokers
            elif split_mode == "WEIGHTED":
                # Could implement weighted allocation based on account size
                allocated_qty = quantity / n_brokers
            else:
                allocated_qty = quantity / n_brokers

            # Execute on all brokers
            for name, broker in active_brokers.items():
                try:
                    order = await broker.place_trade(ticker, side, allocated_qty, stop_loss=stop_loss, take_profit=take_profit)
                    results[name] = order
                except Exception as e:
                    logger.error(f"Execution failed for {name}: {e}")
                    results[name] = None

        return results

    async def close_all_positions_all_accounts(self) -> Dict[str, bool]:
        """Close all positions across all accounts."""
        results = {}

        for name, broker in self.brokers.items():
            success = await broker.close_all_positions()
            results[name] = success

        return results

    async def get_total_exposure(self) -> Dict[str, float]:
        """Calculate total exposure across all accounts."""
        total_long = 0
        total_short = 0
        by_ticker = {}

        for broker in self.brokers.values():
            positions = await broker.get_positions()

            for pos in positions:
                if pos.ticker not in by_ticker:
                    by_ticker[pos.ticker] = {"long": 0, "short": 0}

                if pos.side == PositionSide.LONG:
                    by_ticker[pos.ticker]["long"] += pos.quantity
                    total_long += pos.quantity * pos.current_price
                else:
                    by_ticker[pos.ticker]["short"] += pos.quantity
                    total_short += pos.quantity * pos.current_price

        return {"total_long": total_long, "total_short": total_short, "net_exposure": total_long - total_short, "by_ticker": by_ticker}

    async def sync_positions(self):
        """Sync positions across all broker accounts."""
        all_positions = {}

        for name, broker in self.brokers.items():
            positions = await broker.get_positions()
            for pos in positions:
                key = f"{pos.ticker}_{pos.side.value}"
                if key not in all_positions:
                    all_positions[key] = []
                all_positions[key].append({"broker": name, "position": pos})

        self.master_positions = all_positions


# Factory functions
def create_mt5_broker(server_url: str, account: str, password: str) -> MetaTraderBroker:
    """Create MT5 broker instance."""
    api = MetaTraderMT5API(server_url, account, password)
    return MetaTraderBroker(api)


def create_mt4_broker(server_url: str, account: str, password: str) -> MetaTraderBroker:
    """Create MT4 broker instance."""
    api = MetaTraderMT4API(server_url, account, password)
    return MetaTraderBroker(api)


# Example usage
if __name__ == "__main__":
    import asyncio

    async def test_api():
        # This is a test - would need real broker credentials
        print("MetaTrader API Module")
        print("=" * 50)
        print("Available classes:")
        print("  - MetaTraderMT5API: MT5 Web API")
        print("  - MetaTraderMT4API: MT4 Web API")
        print("  - MetaTraderBroker: High-level broker interface")
        print("  - HedgeFundBrokerManager: Multi-account manager")
        print("\nUsage:")
        print("  broker = create_mt5_broker('https://api.broker.com', '12345', 'password')")
        print("  await broker.connect()")
        print("  order = await broker.place_trade('EURUSD', OrderSide.BUY, 1.0)")
        print("\nNote: Requires actual broker API credentials and endpoint")

    asyncio.run(test_api())
