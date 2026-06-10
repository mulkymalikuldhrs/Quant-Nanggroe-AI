#!/usr/bin/env python3
"""
Enhanced CLI Terminal for AI Hedge Fund v2.2
==============================================

Interactive command-line interface for trading operations.
Supports real-time monitoring, trade execution, and system control.

Usage:
    python3 src/dashboard/cli_terminal.py
    python3 -m src.dashboard.cli_terminal
"""

import sys
import os
import json
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import logging

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from colorama import Fore, Style, init
from termcolor import colored

init(autoreset=True)

logger = logging.getLogger(__name__)


class MenuAction(Enum):
    BACK = "back"
    EXIT = "exit"
    REFRESH = "refresh"


@dataclass
class MenuItem:
    key: str
    title: str
    description: str = ""
    color: str = "white"
    icon: str = ""


class CLITerminal:
    """Interactive CLI Terminal for AI Hedge Fund"""

    def __init__(self):
        self.memory = None
        self.trading_plan = None
        self.mt_bridge = None
        self.data_provider = None
        self.running = True
        self.current_menu = "main"
        self.history = []
        self.trading_mode = "manual"
        self.auto_refresh = False
        self.refresh_thread = None

    def initialize(self):
        """Initialize all components"""
        try:
            from src.memory.enhanced_memory_system import get_memory_system

            self.memory = get_memory_system()
            print(f"{Fore.GREEN}✓ Memory system initialized{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}✗ Memory system error: {e}{Style.RESET_ALL}")

        try:
            from src.trading_plan.trading_plan import get_trading_plan_manager

            self.trading_plan = get_trading_plan_manager()
            print(f"{Fore.GREEN}✓ Trading plan loaded: {self.trading_plan.plan.name}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}✗ Trading plan error: {e}{Style.RESET_ALL}")

        try:
            from src.data.free_data_provider import get_free_data_provider

            self.data_provider = get_free_data_provider()
            print(f"{Fore.GREEN}✓ Data provider initialized{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}✗ Data provider error: {e}{Style.RESET_ALL}")

        try:
            from src.execution.metatrader_bridge import get_metatrader_bridge

            self.mt_bridge = get_metatrader_bridge(simulate=True)
            print(f"{Fore.GREEN}✓ MetaTrader bridge ready (simulator mode){Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.YELLOW}⚠ MetaTrader bridge: {e} (using simulator){Style.RESET_ALL}")

    def clear_screen(self):
        os.system("cls" if os.name == "nt" else "clear")

    def print_header(self, title: str = "AI HEDGE FUND v2.2"):
        self.clear_screen()
        width = 80
        print(f"{Fore.CYAN}{'=' * width}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{Style.BRIGHT}{title:^{width}}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'=' * width}{Style.RESET_ALL}")
        print()

    def print_menu(
        self,
        title: str,
        items: List[MenuItem],
        show_back: bool = True,
        show_exit: bool = True,
    ):
        print(f"{Fore.YELLOW}{Style.BRIGHT}═══ {title} ═══{Style.RESET_ALL}")
        print()

        for item in items:
            color = getattr(Fore, item.color.upper(), Fore.WHITE)
            icon = item.icon + " " if item.icon else ""
            print(f"  {color}[{item.key}]{Style.RESET_ALL} {icon}{item.title}")

        print()
        options = []

        if show_back:
            options.append(MenuItem("B", "Back", "", "blue", "◀"))
        if show_exit:
            options.append(MenuItem("X", "Exit", "", "red", "✗"))

        for item in options:
            color = getattr(Fore, item.color.upper(), Fore.WHITE)
            print(f"  {color}[{item.key}]{Style.RESET_ALL} {item.icon} {item.title}")

        print()

    def get_input(self, prompt: str = "Enter option: ") -> str:
        return input(f"{Fore.GREEN}{prompt}{Style.RESET_ALL}").strip().upper()

    def print_status_bar(self):
        portfolio = self.get_portfolio_summary()
        mode_color = Fore.GREEN if self.trading_mode == "full-auto" else Fore.YELLOW if self.trading_mode == "semi-auto" else Fore.BLUE
        print(f"{Fore.CYAN}{'─' * 80}{Style.RESET_ALL}")
        print(
            f"  {mode_color}Mode: {self.trading_mode.upper()}{Style.RESET_ALL} | ",
            end="",
        )
        print(
            f"{Fore.CYAN}Balance: ${portfolio['balance']:,.2f}{Style.RESET_ALL} | ",
            end="",
        )
        print(
            f"{Fore.GREEN}Equity: ${portfolio['equity']:,.2f}{Style.RESET_ALL} | ",
            end="",
        )
        pnl_emoji = "🟢" if portfolio["floating_pnl"] >= 0 else "🔴"
        print(f"{pnl_emoji} P&L: ${portfolio['floating_pnl']:,.2f} | ", end="")
        print(f"📍 Positions: {portfolio['open_positions']} | ", end="")
        print(f"🕐 {datetime.now().strftime('%H:%M:%S')}")
        print(f"{Fore.CYAN}{'─' * 80}{Style.RESET_ALL}")

    def get_portfolio_summary(self) -> Dict[str, float]:
        try:
            if self.memory:
                status = self.memory.get_system_status()
                portfolio = status.get("portfolio", {})
                return {
                    "balance": portfolio.get("balance", 10000.0),
                    "equity": portfolio.get("equity", 10000.0),
                    "floating_pnl": portfolio.get("floating_pnl", 0.0),
                    "open_positions": portfolio.get("open_positions", 0),
                }
        except:
            pass
        return {
            "balance": 10000.0,
            "equity": 10000.0,
            "floating_pnl": 0.0,
            "open_positions": 0,
        }

    def main_menu(self):
        while self.running:
            self.print_header("AI HEDGE FUND v2.2 - MAIN MENU")
            self.print_status_bar()

            items = [
                MenuItem("1", "📊 Portfolio & Positions", "View portfolio and open positions"),
                MenuItem("2", "📈 Market Analysis", "Analyze symbols and generate signals"),
                MenuItem("3", "📝 Trade Management", "Execute and manage trades"),
                MenuItem("4", "📜 Trade History", "View past trades and performance"),
                MenuItem("5", "⚙️ Configuration", "System settings and parameters"),
                MenuItem("6", "🎮 Trading Mode", "Change trading mode (Manual/Semi/Full)"),
                MenuItem("7", "🔄 Auto-Refresh", "Toggle auto-refresh mode"),
            ]

            self.print_menu("MAIN MENU", items)

            choice = self.get_input()

            if choice == "1":
                self.portfolio_menu()
            elif choice == "2":
                self.analysis_menu()
            elif choice == "3":
                self.trade_menu()
            elif choice == "4":
                self.history_menu()
            elif choice == "5":
                self.config_menu()
            elif choice == "6":
                self.mode_menu()
            elif choice == "7":
                self.toggle_auto_refresh()
            elif choice == "X":
                self.running = False
                print(f"\n{Fore.CYAN}👋 Goodbye!{Style.RESET_ALL}\n")
                break

    def portfolio_menu(self):
        while True:
            self.print_header("PORTFOLIO OVERVIEW")
            self.print_status_bar()

            portfolio = self.get_portfolio_summary()

            print(f"{Fore.CYAN}{Style.BRIGHT}═══ PORTFOLIO SUMMARY ═══{Style.RESET_ALL}")
            print()
            print(f"  {Fore.WHITE}Balance:    {Fore.CYAN}${portfolio['balance']:>15,.2f}{Style.RESET_ALL}")
            print(f"  {Fore.WHITE}Equity:     {Fore.GREEN}${portfolio['equity']:>15,.2f}{Style.RESET_ALL}")
            print(f"  {Fore.WHITE}Floating P&L: {Fore.GREEN if portfolio['floating_pnl'] >= 0 else Fore.RED}${portfolio['floating_pnl']:>14,.2f}{Style.RESET_ALL}")
            print(f"  {Fore.WHITE}Positions:  {Fore.CYAN}{portfolio['open_positions']:>15}{Style.RESET_ALL}")
            print()

            positions = self.get_positions()
            if positions:
                print(f"{Fore.CYAN}{Style.BRIGHT}═══ OPEN POSITIONS ═══{Style.RESET_ALL}")
                for i, pos in enumerate(positions, 1):
                    pnl = pos.get("pnl", 0)
                    pnl_color = Fore.GREEN if pnl >= 0 else Fore.RED
                    print(f"  {i}. {Fore.WHITE}{pos.get('symbol', 'Unknown')}{Style.RESET_ALL} - {pos.get('direction', '').upper()}")
                    print(f"     Entry: ${pos.get('entry_price', 0):.5f} | Current: ${pos.get('current_price', 0):.5f}")
                    print(f"     Size: {pos.get('position_size', 0):.2f} | P&L: {pnl_color}${pnl:,.2f}{Style.RESET_ALL}")
                print()
            else:
                print(f"{Fore.YELLOW}  No open positions{Style.RESET_ALL}")
                print()

            print(f"{Fore.CYAN}{Style.BRIGHT}═══ QUICK ACTIONS ═══{Style.RESET_ALL}")
            items = [
                MenuItem("R", "Refresh", "Refresh portfolio data", "cyan", "🔄"),
                MenuItem("C", "Close All", "Close all positions", "red", "✗"),
            ]
            self.print_menu("", items, show_back=True, show_exit=False)

            choice = self.get_input()

            if choice == "R":
                continue
            elif choice == "C":
                print(f"\n{Fore.YELLOW}⚠ Closing all positions... (simulator){Style.RESET_ALL}\n")
            elif choice == "B":
                break

    def analysis_menu(self):
        while True:
            self.print_header("MARKET ANALYSIS")
            self.print_status_bar()

            symbol = input(f"{Fore.GREEN}Enter symbol to analyze (or 'B' to back): {Style.RESET_ALL}").strip().upper()

            if symbol == "B":
                break
            if not symbol:
                continue

            print(f"\n{Fore.CYAN}Analyzing {symbol}...{Style.RESET_ALL}\n")

            try:
                if self.data_provider:
                    price_data = self.data_provider.get_current_price(symbol)
                    print(f"  {Fore.WHITE}Current Price: {Fore.CYAN}${price_data.current_price:,.5f}{Style.RESET_ALL}")
                    print(f"  {Fore.WHITE}Daily Change: {Fore.GREEN if price_data.daily_change_pct >= 0 else Fore.RED}{price_data.daily_change_pct:+.2f}%{Style.RESET_ALL}")
                    print(f"  {Fore.WHITE}24h High: {Fore.CYAN}${price_data.high_24h:,.5f}{Style.RESET_ALL}")
                    print(f"  {Fore.WHITE}24h Low: {Fore.CYAN}${price_data.low_24h:,.5f}{Style.RESET_ALL}")
                    print(f"  {Fore.WHITE}Asset Type: {Fore.CYAN}{price_data.asset_type}{Style.RESET_ALL}\n")

                historical = []
                if self.data_provider:
                    historical = self.data_provider.get_historical_data(symbol, days=30)

                if historical:
                    closes = [ohlcv.close for ohlcv in historical]
                    ma_7 = sum(closes[-7:]) / 7 if len(closes) >= 7 else 0
                    ma_14 = sum(closes[-14:]) / 14 if len(closes) >= 14 else 0

                    print(f"{Fore.CYAN}{Style.BRIGHT}═══ TECHNICAL SUMMARY ═══{Style.RESET_ALL}")
                    print(f"  {Fore.WHITE}MA(7):  {Fore.CYAN}${ma_7:,.5f}{Style.RESET_ALL}")
                    print(f"  {Fore.WHITE}MA(14): {Fore.CYAN}${ma_14:,.5f}{Style.RESET_ALL}")
                    print(f"  {Fore.WHITE}Price:  {Fore.CYAN}${closes[-1] if closes else 0:,.5f}{Style.RESET_ALL}\n")

                    trend = "BULLISH" if closes[-1] > ma_7 else "BEARISH"
                    trend_color = Fore.GREEN if trend == "BULLISH" else Fore.RED
                    print(f"  {Fore.WHITE}Trend:  {trend_color}{trend}{Style.RESET_ALL}\n")

                print(f"{Fore.CYAN}{Style.BRIGHT}═══ SIGNAL ═══{Style.RESET_ALL}")
                print(f"  {Fore.WHITE}Signal: {Fore.YELLOW}HOLD (Analysis simulation){Style.RESET_ALL}")
                print(f"  {Fore.WHITE}Confidence: {Fore.YELLOW}50%{Style.RESET_ALL}\n")

            except Exception as e:
                print(f"\n{Fore.RED}Error analyzing {symbol}: {e}{Style.RESET_ALL}\n")

    def trade_menu(self):
        while True:
            self.print_header("TRADE MANAGEMENT")
            self.print_status_bar()

            items = [
                MenuItem("1", "Market Order", "Execute market order", "green", "📈"),
                MenuItem("2", "Pending Order", "Set pending order", "yellow", "📝"),
                MenuItem("3", "Modify Position", "Modify SL/TP levels", "blue", "✏️"),
                MenuItem("4", "Close Position", "Close specific position", "red", "✗"),
            ]

            self.print_menu("TRADE OPERATIONS", items)

            choice = self.get_input()

            if choice == "1":
                self.execute_market_order()
            elif choice == "2":
                self.execute_pending_order()
            elif choice == "3":
                self.modify_position()
            elif choice == "4":
                self.close_position()
            elif choice == "B":
                break

    def execute_market_order(self):
        print(f"\n{Fore.CYAN}{Style.BRIGHT}═══ MARKET ORDER ═══{Style.RESET_ALL}\n")

        symbol = input(f"  Symbol (e.g., EURUSD): ").strip().upper()
        direction = input(f"  Direction (BUY/SELL): ").strip().upper()
        lots = input(f"  Lot Size (0.01-100): ").strip()

        if not all([symbol, direction in ["BUY", "SELL"], lots]):
            print(f"\n{Fore.RED}Invalid input{Style.RESET_ALL}\n")
            return

        try:
            lots = float(lots)
            if lots < 0.01 or lots > 100:
                raise ValueError("Invalid lot size")
        except:
            print(f"\n{Fore.RED}Invalid lot size{Style.RESET_ALL}\n")
            return

        print(f"\n{Fore.YELLOW}📋 Order Summary:{Style.RESET_ALL}")
        print(f"  Symbol: {symbol}")
        print(f"  Direction: {direction}")
        print(f"  Lot Size: {lots}")
        print(f"  Mode: {self.trading_mode}\n")

        confirm = input(f"Execute order? (Y/N): ").strip().upper()

        if confirm == "Y":
            print(f"\n{Fore.GREEN}✓ Order executed (simulator): {direction} {lots} lots {symbol}{Style.RESET_ALL}\n")
        else:
            print(f"\n{Fore.YELLOW}Order cancelled{Style.RESET_ALL}\n")

    def execute_pending_order(self):
        print(f"\n{Fore.CYAN}{Style.BRIGHT}═══ PENDING ORDER ═══{Style.RESET_ALL}\n")
        print(f"{Fore.YELLOW}Pending order feature coming soon...{Style.RESET_ALL}\n")

    def modify_position(self):
        print(f"\n{Fore.CYAN}{Style.BRIGHT}═══ MODIFY POSITION ═══{Style.RESET_ALL}\n")
        print(f"{Fore.YELLOW}Position modification feature coming soon...{Style.RESET_ALL}\n")

    def close_position(self):
        print(f"\n{Fore.CYAN}{Style.BRIGHT}═══ CLOSE POSITION ═══{Style.RESET_ALL}\n")
        print(f"{Fore.YELLOW}Position closing feature coming soon...{Style.RESET_ALL}\n")

    def history_menu(self):
        while True:
            self.print_header("TRADE HISTORY")
            self.print_status_bar()

            try:
                if self.memory:
                    trades = self.memory.get_trade_history(days=30)
                    closed_trades = [t for t in trades if t.get("status") == "closed"]

                    print(f"{Fore.CYAN}{Style.BRIGHT}═══ PERFORMANCE METRICS ═══{Style.RESET_ALL}\n")

                    if closed_trades:
                        total_pnl = sum(t.get("pnl", 0) for t in closed_trades)
                        wins = sum(1 for t in closed_trades if t.get("pnl", 0) > 0)
                        losses = len(closed_trades) - wins
                        win_rate = (wins / len(closed_trades) * 100) if closed_trades else 0

                        print(f"  {Fore.WHITE}Total Trades: {Fore.CYAN}{len(closed_trades)}{Style.RESET_ALL}")
                        print(f"  {Fore.WHITE}Wins: {Fore.GREEN}{wins}{Style.RESET_ALL}")
                        print(f"  {Fore.WHITE}Losses: {Fore.RED}{losses}{Style.RESET_ALL}")
                        print(f"  {Fore.WHITE}Win Rate: {Fore.CYAN}{win_rate:.1f}%{Style.RESET_ALL}")
                        print(f"  {Fore.WHITE}Total P&L: {Fore.GREEN if total_pnl >= 0 else Fore.RED}${total_pnl:,.2f}{Style.RESET_ALL}\n")

                        print(f"{Fore.CYAN}{Style.BRIGHT}═══ RECENT TRADES ═══{Style.RESET_ALL}\n")
                        for i, trade in enumerate(closed_trades[-10:], 1):
                            pnl = trade.get("pnl", 0)
                            pnl_color = Fore.GREEN if pnl >= 0 else Fore.RED
                            print(
                                f"  {i}. {trade.get('symbol', 'Unknown')} | {trade.get('direction', '').upper()} | ",
                                end="",
                            )
                            print(f"P&L: {pnl_color}${pnl:,.2f}{Style.RESET_ALL} | {trade.get('exit_time', '')[:10]}")
                    else:
                        print(f"  {Fore.YELLOW}No closed trades yet{Style.RESET_ALL}\n")

            except Exception as e:
                print(f"\n{Fore.RED}Error loading history: {e}{Style.RESET_ALL}\n")

            items = [
                MenuItem("E", "Export History", "Export trade history to CSV", "cyan", "📊"),
            ]
            self.print_menu("", items, show_back=True, show_exit=False)

            choice = self.get_input()

            if choice == "E":
                print(f"\n{Fore.YELLOW}Export feature coming soon...{Style.RESET_ALL}\n")
            elif choice == "B":
                break

    def config_menu(self):
        while True:
            self.print_header("CONFIGURATION")
            self.print_status_bar()

            plan = self.trading_plan.plan if self.trading_plan else None

            print(f"{Fore.CYAN}{Style.BRIGHT}═══ TRADING PLAN ═══{Style.RESET_ALL}\n")
            if plan:
                print(f"  {Fore.WHITE}Plan Name: {Fore.CYAN}{plan.name}{Style.RESET_ALL}")
                print(f"  {Fore.WHITE}Max Risk/Trade: {Fore.YELLOW}{plan.max_risk_per_trade * 100}%{Style.RESET_ALL}")
                print(f"  {Fore.WHITE}Max Daily Loss: {Fore.RED}{plan.max_daily_loss * 100}%{Style.RESET_ALL}")
                print(f"  {Fore.WHITE}Max Drawdown: {Fore.RED}{plan.max_drawdown_limit * 100}%{Style.RESET_ALL}")
                print(f"  {Fore.WHITE}Min R:R Ratio: {Fore.CYAN}1:{plan.min_risk_reward_ratio}{Style.RESET_ALL}")
                print(f"  {Fore.WHITE}Kelly Fraction: {Fore.YELLOW}{plan.kelly_fraction * 100}%{Style.RESET_ALL}")
                print(f"  {Fore.WHITE}Max Position: {Fore.CYAN}{plan.max_position_size * 100}%{Style.RESET_ALL}\n")
            else:
                print(f"  {Fore.RED}Trading plan not loaded{Style.RESET_ALL}\n")

            print(f"{Fore.CYAN}{Style.BRIGHT}═══ ACCOUNT INFO ═══{Style.RESET_ALL}\n")
            print(f"  {Fore.WHITE}Account: {Fore.CYAN}DEMO-123456{Style.RESET_ALL}")
            print(f"  {Fore.WHITE}Broker: {Fore.CYAN}MetaTrader Simulator{Style.RESET_ALL}")
            print(f"  {Fore.WHITE}Mode: {Fore.GREEN}{self.trading_mode.upper()}{Style.RESET_ALL}\n")

            items = [
                MenuItem("1", "Edit Risk Parameters", "Modify risk settings", "yellow", "⚠️"),
                MenuItem(
                    "2",
                    "Edit Account Settings",
                    "Modify account configuration",
                    "blue",
                    "👤",
                ),
                MenuItem("3", "Reset Memory", "Clear all trading data", "red", "🗑️"),
            ]
            self.print_menu("", items, show_back=True, show_exit=False)

            choice = self.get_input()

            if choice == "1":
                print(f"\n{Fore.YELLOW}Risk parameter editing coming soon...{Style.RESET_ALL}\n")
            elif choice == "2":
                print(f"\n{Fore.YELLOW}Account settings coming soon...{Style.RESET_ALL}\n")
            elif choice == "3":
                print(f"\n{Fore.RED}⚠ Memory reset feature requires confirmation...{Style.RESET_ALL}\n")
            elif choice == "B":
                break

    def mode_menu(self):
        while True:
            self.print_header("TRADING MODE")
            self.print_status_bar()

            print(f"{Fore.CYAN}{Style.BRIGHT}═══ SELECT MODE ═══{Style.RESET_ALL}\n")
            print(f"  {Fore.BLUE}[1] MANUAL{Style.RESET_ALL}     - System analyzes, you execute all trades")
            print(f"  {Fore.YELLOW}[2] SEMI-AUTO{Style.RESET_ALL} - Auto position sizing, you confirm entries")
            print(f"  {Fore.GREEN}[3] FULL-AUTO{Style.RESET_ALL} - Autonomous trading, auto-execution\n")

            current_idx = ["manual", "semi-auto", "full-auto"].index(self.trading_mode)
            print(f"  {Fore.WHITE}Current: {['MANUAL', 'SEMI-AUTO', 'FULL-AUTO'][current_idx]}{Style.RESET_ALL}\n")

            choice = self.get_input("Select mode (1-3): ")

            if choice in ["1", "2", "3"]:
                modes = ["manual", "semi-auto", "full-auto"]
                self.trading_mode = modes[int(choice) - 1]
                print(f"\n{Fore.GREEN}✓ Trading mode set to: {self.trading_mode.upper()}{Style.RESET_ALL}\n")
            elif choice == "B":
                break

    def toggle_auto_refresh(self):
        self.auto_refresh = not self.auto_refresh
        status = "ENABLED" if self.auto_refresh else "DISABLED"
        color = Fore.GREEN if self.auto_refresh else Fore.RED
        print(f"\n{color}✓ Auto-refresh {status}{Style.RESET_ALL}\n")

    def get_positions(self) -> List[Dict]:
        try:
            if self.memory:
                status = self.memory.get_system_status()
                return status.get("open_positions", [])
        except:
            pass
        return []

    def run(self):
        self.print_header("AI HEDGE FUND v2.2")
        print(f"{Fore.CYAN}{Style.BRIGHT}Initializing system...{Style.RESET_ALL}\n")

        self.initialize()

        print()
        print(f"{Fore.GREEN}{Style.BRIGHT}System ready!{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Press Enter to continue...{Style.RESET_ALL}")
        input()

        self.main_menu()


def main():
    terminal = CLITerminal()
    terminal.run()


if __name__ == "__main__":
    main()
