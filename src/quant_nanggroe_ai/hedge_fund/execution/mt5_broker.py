"""
MT5 Broker Integration for AI Quant Hedge Fund
Provides order execution, position management, and account info via MetaTrader5
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class PositionStatus(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PENDING = "PENDING"


class MT5Broker:
    """
    MetaTrader 5 broker integration for autonomous trading.

    Provides:
    - Connection management
    - OHLC data retrieval
    - Order placement and management
    - Position tracking
    - Account information
    """

    def __init__(self, login: int = None, password: str = None, server: str = None, path: str = None, timeout: int = 60000, portable: bool = False):
        self.login = login
        self.password = password
        self.server = server
        self.path = path
        self.timeout = timeout
        self.portable = portable
        self.connected = False
        self._mt5_initialized = False

        self._timeframe_map = {
            "M1": 1,
            "M5": 5,
            "M15": 15,
            "M30": 30,
            "H1": 16399,
            "H4": 16388,
            "D1": 16408,
            "W1": 32769,
            "MN1": 49153,
        }

        self._reverse_timeframe_map = {v: k for k, v in self._timeframe_map.items()}

    def connect(self) -> bool:
        """
        Connect to MT5 terminal.

        Returns:
            bool: True if connected successfully
        """
        try:
            import MetaTrader5 as mt5

            initialize_params = {
                "timeout": self.timeout,
                "portable": self.portable,
            }

            if self.login is not None:
                initialize_params["login"] = self.login
            if self.server is not None:
                initialize_params["server"] = self.server
            if self.password is not None:
                initialize_params["password"] = self.password
            if self.path is not None:
                initialize_params["path"] = self.path

            if not mt5.initialize(**initialize_params):
                error = mt5.last_error()
                logger.error(f"MT5 initialization failed: {error}")
                return False

            self._mt5_initialized = True
            self.connected = True

            if self.login and self.server and self.password:
                if not mt5.login(login=self.login, server=self.server, password=self.password):
                    error = mt5.last_error()
                    logger.error(f"MT5 login failed: {error}")
                    self.connected = False
                    return False

            logger.info(f"Connected to MT5: {self.server or 'Local Terminal'}")
            return True

        except ImportError:
            logger.error("MetaTrader5 package not installed. Run: pip install MetaTrader5")
            return False
        except Exception as e:
            logger.error(f"MT5 connection error: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from MT5 terminal."""
        try:
            import MetaTrader5 as mt5

            mt5.shutdown()
            self.connected = False
            logger.info("Disconnected from MT5")
        except Exception as e:
            logger.error(f"MT5 disconnect error: {e}")

    def is_connected(self) -> bool:
        """Check if connected to MT5."""
        try:
            import MetaTrader5 as mt5

            return mt5.initialize() and self.connected
        except:
            return False

    def get_rates(self, symbol: str, timeframe: str = "H1", count: int = 1000) -> Optional[pd.DataFrame]:
        """
        Get OHLC data for a symbol.

        Args:
            symbol: Trading symbol (e.g., "EURUSD")
            timeframe: Timeframe (M1, M5, M15, M30, H1, H4, D1, W1, MN1)
            count: Number of candles to retrieve

        Returns:
            DataFrame with OHLC data or None if failed
        """
        try:
            import MetaTrader5 as mt5

            tf_enum = self._get_timeframe_enum(timeframe)
            if tf_enum is None:
                logger.error(f"Invalid timeframe: {timeframe}")
                return None

            rates = mt5.copy_rates_from_pos(symbol, tf_enum, 0, count)
            if rates is None:
                logger.warning(f"No rates available for {symbol}")
                return None

            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            df.set_index("time", inplace=True)

            return df

        except Exception as e:
            logger.error(f"Error getting rates for {symbol}: {e}")
            return None

    def get_latest_tick(self, symbol: str) -> Optional[Dict]:
        """
        Get latest tick data for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Dict with bid, ask, volume, time or None
        """
        try:
            import MetaTrader5 as mt5

            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return None

            return {"symbol": symbol, "bid": tick.bid, "ask": tick.ask, "last": tick.last, "volume": tick.volume, "time": datetime.fromtimestamp(tick.time)}

        except Exception as e:
            logger.error(f"Error getting tick for {symbol}: {e}")
            return None

    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """
        Get symbol information.

        Args:
            symbol: Trading symbol

        Returns:
            Dict with symbol info or None
        """
        try:
            import MetaTrader5 as mt5

            info = mt5.symbol_info(symbol)
            if info is None:
                return None

            return {
                "symbol": symbol,
                "bid": info.bid,
                "ask": info.ask,
                "last": info.last,
                "volume": info.volume,
                "volume_real": info.volume_real,
                "point": info.point,
                "spread": info.spread,
                "spread_float": info.spread_float,
                "trade_ticks_volume": info.trade_ticks_volume,
                "trade_stops_level": info.trade_stops_level,
                "margin_initial": info.margin_initial,
                "margin_maintenance": info.margin_maintenance,
                "leverage": info.leverage,
                "swap_long": info.swap_long,
                "swap_short": info.swap_short,
                "margin_mode": info.margin_mode,
                "exemode": info.exemode,
                "filling_mode": info.filling_mode,
                "order_mode": info.order_mode,
                "background_color": info.background_color,
                "chart_mode": info.chart_mode,
                "is_extradistributable": info.is_extradistributable,
                "is_stochastic": info.is_stochastic,
            }

        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol}: {e}")
            return None

    def place_order(self, symbol: str, action: str, volume: float, stop_loss: float = None, take_profit: float = None, magic: int = 9001, comment: str = "AI_HedgeFund", deviation: int = 10, order_type: str = "MARKET", price: float = None, expiration: datetime = None) -> Dict:
        """
        Place an order.

        Args:
            symbol: Trading symbol
            action: "BUY" or "SELL"
            volume: Position volume (lots)
            stop_loss: Stop loss price
            take_profit: Take profit price
            magic: Magic number for identification
            comment: Order comment
            deviation: Maximum price deviation
            order_type: Order type (MARKET, LIMIT, STOP)
            price: Limit/stop price (for pending orders)
            expiration: Order expiration time

        Returns:
            Dict with order result
        """
        try:
            import MetaTrader5 as mt5

            if not self.is_connected():
                return {"success": False, "error": "Not connected to MT5"}

            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return {"success": False, "error": f"Symbol {symbol} not available"}

            if action.upper() == "BUY":
                order_type_enum = mt5.ORDER_TYPE_BUY
                price = price or tick.ask
            elif action.upper() == "SELL":
                order_type_enum = mt5.ORDER_TYPE_SELL
                price = price or tick.bid
            else:
                return {"success": False, "error": f"Invalid action: {action}"}

            if order_type.upper() == "MARKET":
                action_enum = mt5.TRADE_ACTION_DEAL
            elif order_type.upper() == "LIMIT":
                action_enum = mt5.TRADE_ACTION_PENDING
                order_type_enum = mt5.ORDER_TYPE_BUY_LIMIT if action.upper() == "BUY" else mt5.ORDER_TYPE_SELL_LIMIT
            elif order_type.upper() == "STOP":
                action_enum = mt5.TRADE_ACTION_PENDING
                order_type_enum = mt5.ORDER_TYPE_BUY_STOP if action.upper() == "BUY" else mt5.ORDER_TYPE_SELL_STOP
            else:
                return {"success": False, "error": f"Invalid order type: {order_type}"}

            request = {
                "action": action_enum,
                "symbol": symbol,
                "volume": volume,
                "type": order_type_enum,
                "price": price,
                "deviation": deviation,
                "magic": magic,
                "comment": comment,
                "type_filling": mt5.ORDER_FILLING_IOC,
                "type_time": mt5.ORDER_TIME_GTC,
            }

            if stop_loss is not None:
                request["sl"] = stop_loss
            if take_profit is not None:
                request["tp"] = take_profit
            if expiration is not None:
                request["type_time"] = mt5.ORDER_TIME_SPECIFIED
                request["expiration"] = int(expiration.timestamp())

            result = mt5.order_send(request)

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                return {"success": False, "error": f"Order failed: {result.comment}", "retcode": result.retcode}

            return {"success": True, "order": result.order, "volume": result.volume, "price": result.price, "pnl": result.profit, "bid": result.bid, "ask": result.ask, "comment": result.comment}

        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {"success": False, "error": str(e)}

    def close_position(self, ticket: int, volume: float = None, comment: str = "AI_HedgeFund_Close") -> Dict:
        """
        Close a position by ticket.

        Args:
            ticket: Position ticket number
            volume: Volume to close (if less than position, partial close)
            comment: Close comment

        Returns:
            Dict with close result
        """
        try:
            import MetaTrader5 as mt5

            if not self.is_connected():
                return {"success": False, "error": "Not connected to MT5"}

            positions = mt5.positions_get(ticket=ticket)
            if not positions:
                return {"success": False, "error": f"Position {ticket} not found"}

            position = positions[0]

            tick = mt5.symbol_info_tick(position.symbol)
            if tick is None:
                return {"success": False, "error": f"Symbol {position.symbol} not available"}

            close_price = tick.bid if position.type == mt5.POSITION_TYPE_BUY else tick.ask

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": volume or position.volume,
                "type": mt5.ORDER_TYPE_SELL if position.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                "position": ticket,
                "price": close_price,
                "deviation": 10,
                "magic": position.magic,
                "comment": comment,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            result = mt5.order_send(request)

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                return {"success": False, "error": f"Close failed: {result.comment}", "retcode": result.retcode}

            return {"success": True, "order": result.order, "volume": result.volume, "price": result.price, "pnl": result.profit}

        except Exception as e:
            logger.error(f"Error closing position {ticket}: {e}")
            return {"success": False, "error": str(e)}

    def modify_position(self, ticket: int, stop_loss: float = None, take_profit: float = None) -> Dict:
        """
        Modify position SL/TP.

        Args:
            ticket: Position ticket
            stop_loss: New stop loss price
            take_profit: New take profit price

        Returns:
            Dict with modify result
        """
        try:
            import MetaTrader5 as mt5

            if not self.is_connected():
                return {"success": False, "error": "Not connected to MT5"}

            positions = mt5.positions_get(ticket=ticket)
            if not positions:
                return {"success": False, "error": f"Position {ticket} not found"}

            position = positions[0]

            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": position.symbol,
                "sl": stop_loss if stop_loss is not None else position.sl,
                "tp": take_profit if take_profit is not None else position.tp,
                "position": ticket,
            }

            result = mt5.order_send(request)

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                return {"success": False, "error": f"Modify failed: {result.comment}", "retcode": result.retcode}

            return {"success": True, "comment": result.comment}

        except Exception as e:
            logger.error(f"Error modifying position {ticket}: {e}")
            return {"success": False, "error": str(e)}

    def get_positions(self, symbol: str = None) -> List[Dict]:
        """
        Get open positions.

        Args:
            symbol: Filter by symbol (None for all)

        Returns:
            List of position dicts
        """
        try:
            import MetaTrader5 as mt5

            if not self.is_connected():
                return []

            if symbol:
                positions = mt5.positions_get(symbol=symbol)
            else:
                positions = mt5.positions_get()

            if not positions:
                return []

            return [{"ticket": p.ticket, "symbol": p.symbol, "type": "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL", "volume": p.volume, "open_price": p.price_open, "current_price": p.price_current, "sl": p.sl, "tp": p.tp, "pnl": p.profit, "swap": p.swap, "commission": p.commission, "magic": p.magic, "comment": p.comment, "time": datetime.fromtimestamp(p.time)} for p in positions]

        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []

    def get_orders(self, symbol: str = None) -> List[Dict]:
        """
        Get pending orders.

        Args:
            symbol: Filter by symbol (None for all)

        Returns:
            List of order dicts
        """
        try:
            import MetaTrader5 as mt5

            if not self.is_connected():
                return []

            if symbol:
                orders = mt5.orders_get(symbol=symbol)
            else:
                orders = mt5.orders_get()

            if not orders:
                return []

            return [{"ticket": o.ticket, "symbol": o.symbol, "type": "BUY" if o.type == mt5.ORDER_TYPE_BUY_LIMIT else "SELL", "volume": o.volume_initial, "price": o.price_open, "sl": o.sl, "tp": o.tp, "magic": o.magic, "comment": o.comment, "time_setup": datetime.fromtimestamp(o.time_setup), "time_done": datetime.fromtimestamp(o.time_done) if o.time_done > 0 else None} for o in orders]

        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return []

    def cancel_order(self, ticket: int) -> Dict:
        """
        Cancel a pending order.

        Args:
            ticket: Order ticket number

        Returns:
            Dict with cancel result
        """
        try:
            import MetaTrader5 as mt5

            if not self.is_connected():
                return {"success": False, "error": "Not connected to MT5"}

            orders = mt5.orders_get(ticket=ticket)
            if not orders:
                return {"success": False, "error": f"Order {ticket} not found"}

            order = orders[0]

            request = {"action": mt5.TRADE_ACTION_REMOVE, "order": ticket, "symbol": order.symbol, "magic": order.magic, "comment": "AI_HedgeFund_Cancel"}

            result = mt5.order_send(request)

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                return {"success": False, "error": f"Cancel failed: {result.comment}", "retcode": result.retcode}

            return {"success": True, "comment": result.comment}

        except Exception as e:
            logger.error(f"Error cancelling order {ticket}: {e}")
            return {"success": False, "error": str(e)}

    def get_account_info(self) -> Optional[Dict]:
        """
        Get account information.

        Returns:
            Dict with account info or None
        """
        try:
            import MetaTrader5 as mt5

            if not self.is_connected():
                return None

            info = mt5.account_info()
            if info is None:
                return None

            return {
                "login": info.login,
                "trade_mode": info.trade_mode,
                "leverage": info.leverage,
                "limit_orders": info.limit_orders,
                "margin_so_mode": info.margin_so_mode,
                "margin_initial": info.margin_initial,
                "margin_maintenance": info.margin_maintenance,
                "margin_type": info.margin_type,
                "margin_currency": info.margin_currency,
                "balance": info.balance,
                "credit": info.credit,
                "profit": info.profit,
                "equity": info.equity,
                "margin": info.margin,
                "margin_free": info.margin_free,
                "margin_level": info.margin_level,
                "so_margin": info.so_margin,
                "so_time": info.so_time,
                "so_actions": info.so_actions,
                "discount": info.discount,
                "company": info.company,
                "name": info.name,
                "server": info.server,
                "currency": info.currency,
                "currency_digits": info.currency_digits,
            }

        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None

    def get_trade_history(self, from_date: datetime = None, to_date: datetime = None) -> List[Dict]:
        """
        Get trade history.

        Args:
            from_date: Start date
            to_date: End date (defaults to now)

        Returns:
            List of closed trade dicts
        """
        try:
            import MetaTrader5 as mt5

            if not self.is_connected():
                return []

            if from_date is None:
                from_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            if to_date is None:
                to_date = datetime.now()

            deals = mt5.history_deals_get(from_date, to_date)
            if not deals:
                return []

            return [{"ticket": d.ticket, "order": d.order, "symbol": d.symbol, "type": "BUY" if d.type == mt5.DEAL_TYPE_BUY else "SELL", "entry": "IN" if d.entry == mt5.DEAL_ENTRY_IN else "OUT", "volume": d.volume, "price": d.price, "profit": d.profit, "swap": d.swap, "commission": d.commission, "fee": d.fee, "comment": d.comment, "time": datetime.fromtimestamp(d.time)} for d in deals]

        except Exception as e:
            logger.error(f"Error getting trade history: {e}")
            return []

    def _get_timeframe_enum(self, timeframe: str):
        """Get MT5 timeframe enum value."""
        import MetaTrader5 as mt5

        mapping = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1,
            "W1": mt5.TIMEFRAME_W1,
            "MN1": mt5.TIMEFRAME_MN1,
        }
        return mapping.get(timeframe.upper())

    def calculate_position_size(self, symbol: str, risk_percent: float, stop_loss: float, entry_price: float) -> float:
        """
        Calculate position size based on risk.

        Args:
            symbol: Trading symbol
            risk_percent: Risk percentage of account
            stop_loss: Stop loss price
            entry_price: Entry price

        Returns:
            Position size in lots
        """
        try:
            import MetaTrader5 as mt5

            account_info = self.get_account_info()
            if account_info is None:
                return 0.0

            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                return 0.0

            balance = account_info["equity"]
            risk_amount = balance * (risk_percent / 100)

            tick_size = symbol_info.tick_size
            tick_value = symbol_info.trade_tick_value

            if symbol_info.point == 0:
                return 0.0

            sl_distance = abs(entry_price - stop_loss)
            sl_pips = sl_distance / symbol_info.point

            if sl_pips == 0:
                return 0.0

            position_size = risk_amount / (sl_pips * tick_value)

            min_lot = symbol_info.volume_min
            max_lot = symbol_info.volume_max
            step = symbol_info.volume_step

            position_size = max(min_lot, min(position_size, max_lot))
            position_size = round(position_size / step) * step

            return position_size

        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0.0


def create_mt5_broker(login: int = None, password: str = None, server: str = None, path: str = None) -> MT5Broker:
    """
    Factory function to create MT5 broker instance.

    Args:
        login: MT5 account login
        password: MT5 account password
        server: MT5 server name
        path: MT5 terminal path

    Returns:
        MT5Broker instance
    """
    return MT5Broker(login=login, password=password, server=server, path=path)
