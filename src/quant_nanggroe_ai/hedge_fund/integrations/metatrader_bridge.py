"""
METATRADER INTEGRATION - MetaTrader 4/5 Bridge
Connects AI Hedge Fund with MetaTrader terminals for automated trading
"""

import sys
import os
import socket
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from rich.console import Console
    console = Console()
except ImportError:
    console = None

@dataclass
class MTOrder:
    """MetaTrader order structure"""
    ticket: int
    symbol: str
    type: str  # BUY, SELL, BUY_LIMIT, SELL_LIMIT, etc.
    lots: float
    price: float
    stop_loss: float
    take_profit: float
    comment: str
    magic_number: int
    timestamp: str

@dataclass
class MTAccount:
    """MetaTrader account information"""
    account_number: str
    balance: float
    equity: float
    margin: float
    free_margin: float
    leverage: int
    currency: str

class MetaTraderBridge:
    """MetaTrader 4/5 integration bridge"""

    def __init__(self, host: str = "localhost", port: int = 8888, version: str = "5"):
        self.host = host
        self.port = port
        self.version = version
        self.connected = False
        self.socket = None
        self.account_info = None
        self.active_orders: Dict[int, MTOrder] = {}
        self.connection_attempts = 0
        self.max_retries = 3

    def connect(self) -> bool:
        """Establish connection to MetaTrader terminal"""
        if console:
            console.print(f"[bold blue]🔌 Connecting to MetaTrader {self.version} at {self.host}:{self.port}...[/bold blue]")
        else:
            print(f"🔌 Connecting to MetaTrader {self.version} at {self.host}:{self.port}...")

        for attempt in range(self.max_retries):
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(5.0)
                self.socket.connect((self.host, self.port))

                # Send handshake
                handshake = {
                    "command": "handshake",
                    "version": self.version,
                    "client": "ai_hedge_fund",
                    "timestamp": datetime.now().isoformat()
                }

                self._send_command(handshake)
                response = self._receive_response()

                if response and response.get("status") == "connected":
                    self.connected = True
                    self.account_info = response.get("account", {})

                    if console:
                        console.print("[green]✅ MetaTrader connection established![/green]")
                        console.print(f"[blue]📊 Account: {self.account_info.get('account_number', 'N/A')}[/blue]")
                        console.print(f"[blue]💰 Balance: ${self.account_info.get('balance', 0):.2f}[/blue]")
                    else:
                        print("✅ MetaTrader connection established!")
                        print(f"📊 Account: {self.account_info.get('account_number', 'N/A')}")
                        print(f"💰 Balance: ${self.account_info.get('balance', 0):.2f}")

                    return True
                else:
                    if console:
                        console.print(f"[yellow]⚠️ Handshake failed (attempt {attempt + 1}/{self.max_retries})[/yellow]")
                    else:
                        print(f"⚠️ Handshake failed (attempt {attempt + 1}/{self.max_retries})")

            except socket.error as e:
                if console:
                    console.print(f"[yellow]⚠️ Connection attempt {attempt + 1} failed: {e}[/yellow]")
                else:
                    print(f"⚠️ Connection attempt {attempt + 1} failed: {e}")

            time.sleep(1)

        if console:
            console.print("[red]❌ Failed to connect to MetaTrader after all attempts[/red]")
        else:
            print("❌ Failed to connect to MetaTrader after all attempts")

        return False

    def disconnect(self):
        """Disconnect from MetaTrader"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        self.connected = False
        self.socket = None
        self.account_info = None
        self.active_orders.clear()

        if console:
            console.print("[yellow]🔌 Disconnected from MetaTrader[/yellow]")
        else:
            print("🔌 Disconnected from MetaTrader")

    def get_account_info(self) -> Optional[MTAccount]:
        """Get current account information"""
        if not self.connected:
            return None

        try:
            command = {"command": "get_account_info"}
            self._send_command(command)
            response = self._receive_response()

            if response and response.get("status") == "success":
                account_data = response.get("account", {})
                return MTAccount(
                    account_number=str(account_data.get("account_number", "")),
                    balance=float(account_data.get("balance", 0)),
                    equity=float(account_data.get("equity", 0)),
                    margin=float(account_data.get("margin", 0)),
                    free_margin=float(account_data.get("free_margin", 0)),
                    leverage=int(account_data.get("leverage", 100)),
                    currency=account_data.get("currency", "USD")
                )
        except Exception as e:
            if console:
                console.print(f"[red]❌ Failed to get account info: {e}[/red]")
            else:
                print(f"❌ Failed to get account info: {e}")

        return None

    def place_market_order(self, symbol: str, order_type: str, volume: float,
                          stop_loss: float = 0, take_profit: float = 0,
                          comment: str = "AI_HF") -> Optional[MTOrder]:
        """Place market order"""
        if not self.connected:
            if console:
                console.print("[red]❌ Not connected to MetaTrader[/red]")
            else:
                print("❌ Not connected to MetaTrader")
            return None

        try:
            command = {
                "command": "place_order",
                "type": "market",
                "symbol": symbol,
                "order_type": order_type,
                "volume": volume,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "comment": comment
            }

            self._send_command(command)
            response = self._receive_response()

            if response and response.get("status") == "success":
                order_data = response.get("order", {})
                order = MTOrder(
                    ticket=int(order_data.get("ticket", 0)),
                    symbol=symbol,
                    type=order_type,
                    lots=volume,
                    price=float(order_data.get("price", 0)),
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    comment=comment,
                    magic_number=int(order_data.get("magic_number", 0)),
                    timestamp=datetime.now().isoformat()
                )

                self.active_orders[order.ticket] = order

                if console:
                    console.print(f"[green]✅ Order placed: {order_type} {volume} lots of {symbol} at {order.price}[/green]")
                else:
                    print(f"✅ Order placed: {order_type} {volume} lots of {symbol} at {order.price}")

                return order

        except Exception as e:
            if console:
                console.print(f"[red]❌ Failed to place order: {e}[/red]")
            else:
                print(f"❌ Failed to place order: {e}")

        return None

    def place_pending_order(self, symbol: str, order_type: str, volume: float,
                           price: float, stop_loss: float = 0, take_profit: float = 0,
                           comment: str = "AI_HF") -> Optional[MTOrder]:
        """Place pending order (limit/stop orders)"""
        if not self.connected:
            if console:
                console.print("[red]❌ Not connected to MetaTrader[/red]")
            else:
                print("❌ Not connected to MetaTrader")
            return None

        try:
            command = {
                "command": "place_order",
                "type": "pending",
                "symbol": symbol,
                "order_type": order_type,
                "volume": volume,
                "price": price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "comment": comment
            }

            self._send_command(command)
            response = self._receive_response()

            if response and response.get("status") == "success":
                order_data = response.get("order", {})
                order = MTOrder(
                    ticket=int(order_data.get("ticket", 0)),
                    symbol=symbol,
                    type=order_type,
                    lots=volume,
                    price=price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    comment=comment,
                    magic_number=int(order_data.get("magic_number", 0)),
                    timestamp=datetime.now().isoformat()
                )

                self.active_orders[order.ticket] = order

                if console:
                    console.print(f"[green]✅ Pending order placed: {order_type} {volume} lots of {symbol} at {price}[/green]")
                else:
                    print(f"✅ Pending order placed: {order_type} {volume} lots of {symbol} at {price}")

                return order

        except Exception as e:
            if console:
                console.print(f"[red]❌ Failed to place pending order: {e}[/red]")
            else:
                print(f"❌ Failed to place pending order: {e}")

        return None

    def close_order(self, ticket: int) -> bool:
        """Close position by ticket"""
        if not self.connected:
            if console:
                console.print("[red]❌ Not connected to MetaTrader[/red]")
            else:
                print("❌ Not connected to MetaTrader")
            return False

        try:
            command = {
                "command": "close_order",
                "ticket": ticket
            }

            self._send_command(command)
            response = self._receive_response()

            if response and response.get("status") == "success":
                if ticket in self.active_orders:
                    del self.active_orders[ticket]

                if console:
                    console.print(f"[green]✅ Order {ticket} closed successfully[/green]")
                else:
                    print(f"✅ Order {ticket} closed successfully")

                return True

        except Exception as e:
            if console:
                console.print(f"[red]❌ Failed to close order: {e}[/red]")
            else:
                print(f"❌ Failed to close order: {e}")

        return False

    def get_open_positions(self) -> List[MTOrder]:
        """Get all open positions"""
        if not self.connected:
            return []

        try:
            command = {"command": "get_positions"}
            self._send_command(command)
            response = self._receive_response()

            if response and response.get("status") == "success":
                positions_data = response.get("positions", [])
                positions = []

                for pos_data in positions_data:
                    position = MTOrder(
                        ticket=int(pos_data.get("ticket", 0)),
                        symbol=pos_data.get("symbol", ""),
                        type=pos_data.get("type", ""),
                        lots=float(pos_data.get("lots", 0)),
                        price=float(pos_data.get("price", 0)),
                        stop_loss=float(pos_data.get("stop_loss", 0)),
                        take_profit=float(pos_data.get("take_profit", 0)),
                        comment=pos_data.get("comment", ""),
                        magic_number=int(pos_data.get("magic_number", 0)),
                        timestamp=pos_data.get("timestamp", "")
                    )
                    positions.append(position)

                return positions

        except Exception as e:
            if console:
                console.print(f"[red]❌ Failed to get positions: {e}[/red]")
            else:
                print(f"❌ Failed to get positions: {e}")

        return []

    def _send_command(self, command: Dict[str, Any]):
        """Send command to MetaTrader"""
        if self.socket:
            message = json.dumps(command).encode('utf-8')
            # Add message length prefix for proper parsing
            length_prefix = len(message).to_bytes(4, byteorder='big')
            self.socket.send(length_prefix + message)

    def _receive_response(self) -> Optional[Dict[str, Any]]:
        """Receive response from MetaTrader"""
        if not self.socket:
            return None

        try:
            # Read message length
            length_bytes = self.socket.recv(4)
            if len(length_bytes) != 4:
                return None

            message_length = int.from_bytes(length_bytes, byteorder='big')
            if message_length <= 0 or message_length > 1024 * 1024:  # 1MB max
                return None

            # Read message
            message_bytes = self.socket.recv(message_length)
            if len(message_bytes) != message_length:
                return None

            response = json.loads(message_bytes.decode('utf-8'))
            return response

        except Exception as e:
            if console:
                console.print(f"[red]❌ Communication error: {e}[/red]")
            else:
                print(f"❌ Communication error: {e}")
            return None

# Global instances
mt4_bridge = MetaTraderBridge(version="4")
mt5_bridge = MetaTraderBridge(version="5")