"""
WEB TERMINAL - MetaTrader-style Web Interface
Professional trading terminal with charts, analysis, and execution
"""

import sys
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Try to import rich library
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None
    Table = None
    Panel = None

from src.integrations.analysis_display import analysis_display
from src.integrations.retail_strategies import retail_strategies
from src.integrations.quant_strategies_analysis import quant_strategies_analysis
from src.integrations.metatrader_bridge import mt4_bridge, mt5_bridge

class WebTerminal:
    """MetaTrader-style web terminal interface"""

    def __init__(self):
        self.active_charts: Dict[str, Dict] = {}
        self.watchlist: List[str] = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
        self.portfolio: Dict[str, Dict] = {}
        self.pending_orders: List[Dict] = []
        self.current_analysis: Dict[str, Any] = {}
        self.metatrader_connected = False

    def display_main_dashboard(self):
        """Display main terminal dashboard"""
        if RICH_AVAILABLE and console:
            # Create main dashboard layout
            console.print("\n[bold blue]📊 AI HEDGE FUND WEB TERMINAL[/bold blue]")
            console.print("=" * 80)

            # Portfolio Overview
            portfolio_panel = self._create_portfolio_panel()
            console.print(portfolio_panel)

            # Watchlist
            watchlist_panel = self._create_watchlist_panel()
            console.print(watchlist_panel)

            # Active Analysis
            if self.current_analysis:
                analysis_panel = self._create_analysis_panel()
                console.print(analysis_panel)

            # Pending Orders
            if self.pending_orders:
                orders_panel = self._create_orders_panel()
                console.print(orders_panel)

        else:
            self._display_basic_dashboard()

    def _create_portfolio_panel(self):
        """Create portfolio overview panel"""
        if not console or not Panel or not Table:
            return "Portfolio panel requires rich library"

        table = Table(title="💼 PORTFOLIO OVERVIEW")
        table.add_column("Asset", style="cyan")
        table.add_column("Shares", style="green")
        table.add_column("Avg Price", style="yellow")
        table.add_column("Current Price", style="magenta")
        table.add_column("P&L", style="red")

        total_value = 0
        total_pnl = 0

        for symbol, position in self.portfolio.items():
            shares = position.get('shares', 0)
            avg_price = position.get('avg_price', 0)
            current_price = position.get('current_price', avg_price)  # Mock
            pnl = (current_price - avg_price) * shares

            table.add_row(
                symbol,
                f"{shares:,}",
                f"${avg_price:.2f}",
                f"${current_price:.2f}",
                f"${pnl:+,.2f}" if pnl != 0 else "N/A"
            )

            total_value += current_price * shares
            total_pnl += pnl

        # Add total row
        table.add_row(
            "[bold]TOTAL[/bold]",
            "",
            "",
            "",
            f"[bold]${total_pnl:+,.2f}[/bold]",
            style="bold"
        )

        return Panel(table, title="[bold]📈 Portfolio Performance[/bold]", border_style="green")

    def _create_watchlist_panel(self) -> Panel:
        """Create watchlist panel"""
        from rich.panel import Panel
        from rich.table import Table

        table = Table(title="👀 WATCHLIST")
        table.add_column("Symbol", style="cyan")
        table.add_column("Price", style="green")
        table.add_column("Change", style="yellow")
        table.add_column("Volume", style="magenta")
        table.add_column("Signal", style="red")

        for symbol in self.watchlist[:8]:  # Show first 8
            # Mock data
            price = 100 + hash(symbol) % 200  # Deterministic mock price
            change = (hash(symbol + "change") % 20 - 10) / 100  # -10% to +10%
            volume = hash(symbol + "vol") % 1000000 + 100000
            signal = "BUY" if hash(symbol + "sig") % 2 == 0 else "HOLD"

            change_str = f"{change:+.2f}%" if change != 0 else "0.00%"
            change_style = "green" if change > 0 else "red" if change < 0 else "white"

            table.add_row(
                symbol,
                f"${price:.2f}",
                f"[{change_style}]{change_str}[/{change_style}]",
                f"{volume:,.0f}",
                signal
            )

        return Panel(table, title="[bold]📊 Market Watch[/bold]", border_style="blue")

    def _create_analysis_panel(self) -> Panel:
        """Create current analysis panel"""
        from rich.panel import Panel
        from rich.text import Text

        analysis_text = Text()

        for symbol, analysis in list(self.current_analysis.items())[:3]:  # Show first 3
            analysis_text.append(f"\n{symbol}: ", style="bold cyan")

            selected_entry = analysis.get('selected_entry', {})
            action = selected_entry.get('recommended_action', 'N/A')
            confidence = selected_entry.get('confidence', 0)

            if action == 'BUY':
                analysis_text.append(f"{action} ", style="green")
            elif action == 'SELL':
                analysis_text.append(f"{action} ", style="red")
            else:
                analysis_text.append(f"{action} ", style="yellow")

            analysis_text.append(f"({confidence:.1%})", style="white")

        return Panel(analysis_text, title="[bold]🎯 Active Analysis[/bold]", border_style="yellow")

    def _create_orders_panel(self) -> Panel:
        """Create pending orders panel"""
        from rich.panel import Panel
        from rich.table import Table

        table = Table(title="📋 PENDING ORDERS")
        table.add_column("Symbol", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Quantity", style="yellow")
        table.add_column("Price", style="magenta")
        table.add_column("Status", style="red")

        for order in self.pending_orders[:5]:  # Show first 5
            table.add_row(
                order.get('symbol', 'N/A'),
                order.get('type', 'N/A'),
                str(order.get('quantity', 0)),
                f"${order.get('price', 0):.2f}",
                order.get('status', 'Pending')
            )

        return Panel(table, title="[bold]⚡ Order Management[/bold]", border_style="red")

    def _display_basic_dashboard(self):
        """Fallback basic dashboard display"""
        print("\n📊 AI HEDGE FUND WEB TERMINAL")
        print("=" * 50)

        print("\n💼 PORTFOLIO OVERVIEW:")
        total_value = 0
        for symbol, position in self.portfolio.items():
            shares = position.get('shares', 0)
            avg_price = position.get('avg_price', 0)
            current_price = position.get('current_price', avg_price)
            value = current_price * shares
            total_value += value
            print(f"  {symbol}: {shares} shares @ ${avg_price:.2f} = ${value:.2f}")

        print(f"\n💰 Total Portfolio Value: ${total_value:.2f}")

        print("\n👀 WATCHLIST:")
        for symbol in self.watchlist[:5]:
            price = 100 + hash(symbol) % 200
            change = (hash(symbol + "change") % 20 - 10) / 100
            print(f"  {symbol}: ${price:.2f} ({change:+.2f}%)")

        if self.current_analysis:
            print("\n🎯 ACTIVE ANALYSIS:")
            for symbol, analysis in list(self.current_analysis.items())[:3]:
                selected_entry = analysis.get('selected_entry', {})
                action = selected_entry.get('recommended_action', 'N/A')
                confidence = selected_entry.get('confidence', 0)
                print(f"  {symbol}: {action} ({confidence:.1%})")

    def analyze_symbol(self, symbol: str, analysis_type: str = 'full'):
        """Analyze a symbol with full terminal capabilities"""
        print(f"\n🔍 Analyzing {symbol} with {analysis_type} analysis...")

        if analysis_type == 'full':
            # Full analysis with all components
            analysis = analysis_display.display_full_analysis(symbol)

            # Store for dashboard
            self.current_analysis[symbol] = analysis

        elif analysis_type == 'quant':
            # Quantitative strategies only
            signals = quant_strategies_analysis.analyze_all_strategies(symbol)
            print(f"\n📊 QUANTITATIVE ANALYSIS - {symbol}")
            for strategy_name, signal in signals.items():
                print(f"  {strategy_name}: {signal.action} ({signal.confidence:.1%})")

        elif analysis_type == 'retail':
            # Retail strategies only
            signal = retail_strategies.execute_strategy('scalping_momentum', None, 100.0, 10000)
            if signal:
                print(f"\n🛍️ RETAIL ANALYSIS - {symbol}")
                print(f"  Strategy: {signal.strategy_name}")
                print(f"  Action: {signal.action}")
                print(f"  Confidence: {signal.strength:.1%}")

        return self.current_analysis.get(symbol, {})

    def add_to_watchlist(self, symbol: str):
        """Add symbol to watchlist"""
        if symbol not in self.watchlist:
            self.watchlist.append(symbol)
            print(f"✅ Added {symbol} to watchlist")
        else:
            print(f"⚠️ {symbol} already in watchlist")

    def remove_from_watchlist(self, symbol: str):
        """Remove symbol from watchlist"""
        if symbol in self.watchlist:
            self.watchlist.remove(symbol)
            print(f"✅ Removed {symbol} from watchlist")
        else:
            print(f"⚠️ {symbol} not in watchlist")

    def place_order(self, symbol: str, order_type: str, quantity: int,
                   price: Optional[float] = None, stop_loss: Optional[float] = None,
                   take_profit: Optional[float] = None):
        """Place trading order"""
        order = {
            'symbol': symbol,
            'type': order_type,
            'quantity': quantity,
            'price': price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'timestamp': datetime.now().isoformat(),
            'status': 'Pending'
        }

        self.pending_orders.append(order)
        print(f"✅ Order placed: {order_type} {quantity} {symbol}")

        # Try to execute via MetaTrader if connected
        if self.metatrader_connected:
            if mt5_bridge.connected:
                result = mt5_bridge.place_market_order(symbol, order_type, quantity, stop_loss, take_profit)
                if result:
                    order['status'] = 'Executed'
                    print(f"✅ Order executed via MetaTrader 5: {result.ticket}")
                else:
                    print("❌ MetaTrader execution failed")

    def connect_metatrader(self, version: str = "5"):
        """Connect to MetaTrader"""
        if version == "5":
            success = mt5_bridge.connect()
        else:
            success = mt4_bridge.connect()

        if success:
            self.metatrader_connected = True
            print(f"✅ Connected to MetaTrader {version}")
        else:
            print(f"❌ Failed to connect to MetaTrader {version}")

    def run_terminal_loop(self):
        """Run the terminal main loop"""
        print("\n🚀 Starting AI Hedge Fund Web Terminal...")
        print("Type 'help' for commands, 'exit' to quit")

        while True:
            try:
                if console:
                    command = console.input("\n[bold green]Terminal>[/bold green] ").strip()
                else:
                    command = input("\nTerminal> ").strip()

                if not command:
                    continue

                if command.lower() in ['exit', 'quit', 'q']:
                    break
                elif command.lower() in ['help', 'h', '?']:
                    self._show_help()
                elif command.lower() in ['dashboard', 'd']:
                    self.display_main_dashboard()
                elif command.lower() in ['watchlist', 'w']:
                    self._show_watchlist_commands()
                elif command.startswith('analyze'):
                    self._handle_analyze_command(command)
                elif command.startswith('add'):
                    parts = command.split()
                    if len(parts) >= 2:
                        self.add_to_watchlist(parts[1].upper())
                elif command.startswith('remove'):
                    parts = command.split()
                    if len(parts) >= 2:
                        self.remove_from_watchlist(parts[1].upper())
                elif command.startswith('order'):
                    self._handle_order_command(command)
                elif command.startswith('connect'):
                    parts = command.split()
                    version = parts[1] if len(parts) > 1 else "5"
                    self.connect_metatrader(version)
                else:
                    print(f"Unknown command: {command}")
                    print("Type 'help' for available commands")

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")

        print("\n👋 Thank you for using AI Hedge Fund Web Terminal!")

    def _show_help(self):
        """Show help menu"""
        help_text = """
🤖 AI HEDGE FUND WEB TERMINAL COMMANDS:

📊 DASHBOARD COMMANDS:
  dashboard, d          Show main dashboard
  watchlist, w          Show watchlist management

🔍 ANALYSIS COMMANDS:
  analyze AAPL          Full analysis of AAPL
  analyze AAPL quant    Quantitative analysis only
  analyze AAPL retail   Retail strategies only

📋 WATCHLIST COMMANDS:
  add AAPL             Add AAPL to watchlist
  remove AAPL          Remove AAPL from watchlist

💰 TRADING COMMANDS:
  order buy AAPL 100   Place market buy order
  order sell AAPL 50   Place market sell order
  connect 5            Connect to MetaTrader 5
  connect 4            Connect to MetaTrader 4

🔧 SYSTEM COMMANDS:
  help, h              Show this help
  exit, quit, q        Exit terminal

💡 EXAMPLES:
  Terminal> analyze AAPL
  Terminal> add MSFT
  Terminal> order buy AAPL 100
  Terminal> dashboard
        """
        if console:
            from rich.panel import Panel
            console.print(Panel(help_text, title="[bold]📚 Help Menu[/bold]", border_style="blue"))
        else:
            print(help_text)

    def _show_watchlist_commands(self):
        """Show watchlist management"""
        if console:
            from rich.table import Table
            table = Table(title="👀 WATCHLIST MANAGEMENT")
            table.add_column("Command", style="cyan")
            table.add_column("Description", style="white")

            table.add_row("add SYMBOL", "Add symbol to watchlist")
            table.add_row("remove SYMBOL", "Remove symbol from watchlist")
            table.add_row("watchlist", "Show current watchlist")

            console.print(table)

            # Show current watchlist
            watchlist_table = Table(title="📊 CURRENT WATCHLIST")
            watchlist_table.add_column("Symbol", style="green")
            for symbol in self.watchlist:
                watchlist_table.add_row(symbol)

            console.print(watchlist_table)
        else:
            print("\n👀 WATCHLIST MANAGEMENT:")
            print("  add SYMBOL    - Add symbol to watchlist")
            print("  remove SYMBOL - Remove symbol from watchlist")
            print("\n📊 CURRENT WATCHLIST:")
            for symbol in self.watchlist:
                print(f"  {symbol}")

    def _handle_analyze_command(self, command: str):
        """Handle analyze command"""
        parts = command.split()
        if len(parts) < 2:
            print("Usage: analyze SYMBOL [type]")
            return

        symbol = parts[1].upper()
        analysis_type = parts[2] if len(parts) > 2 else 'full'

        if analysis_type not in ['full', 'quant', 'retail']:
            print("Invalid analysis type. Use: full, quant, or retail")
            return

        self.analyze_symbol(symbol, analysis_type)

    def _handle_order_command(self, command: str):
        """Handle order command"""
        parts = command.split()
        if len(parts) < 4:
            print("Usage: order buy/sell SYMBOL QUANTITY [PRICE]")
            return

        order_type = parts[1].lower()
        if order_type not in ['buy', 'sell']:
            print("Order type must be 'buy' or 'sell'")
            return

        symbol = parts[2].upper()
        try:
            quantity = int(parts[3])
            price = float(parts[4]) if len(parts) > 4 else None
        except ValueError:
            print("Invalid quantity or price")
            return

        self.place_order(symbol, order_type, quantity, price)

# Global instance
web_terminal = WebTerminal()