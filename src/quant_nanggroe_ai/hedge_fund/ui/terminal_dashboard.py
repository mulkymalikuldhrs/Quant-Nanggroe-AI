"""
Terminal Dashboard for AI Quant Hedge Fund
Real-time portfolio and trading dashboard for terminal
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

try:
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.align import Align
    from rich.style import Style
    from rich.color import Color
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


@dataclass
class DashboardConfig:
    """Configuration for terminal dashboard."""
    refresh_rate: float = 1.0
    show_positions: bool = True
    show_chart: bool = True
    chart_candles: int = 30
    show_signals: bool = True
    max_signals: int = 10
    auto_refresh: bool = True
    width: int = 100
    height: int = 40


class TerminalDashboard:
    """
    Terminal-based trading dashboard.
    
    Features:
    - Real-time portfolio display
    - Position tracking
    - Signal monitoring
    - ASCII candlestick charts
    - Color-coded PnL
    """
    
    def __init__(
        self,
        portfolio_monitor=None,
        config: DashboardConfig = None
    ):
        self.monitor = portfolio_monitor
        self.config = config or DashboardConfig()
        self.console = Console() if HAS_RICH else None
        self.running = False
        self._update_task = None
        
        self._pending_confirmations: Dict[str, Dict] = {}
        self._last_data = {}
    
    async def start(self) -> None:
        """Start the dashboard."""
        if self.running:
            return
        
        self.running = True
        
        if self.config.auto_refresh:
            self._update_task = asyncio.create_task(self._refresh_loop())
        
        await self._display_dashboard()
    
    async def stop(self) -> None:
        """Stop the dashboard."""
        self.running = False
        
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
    
    async def _refresh_loop(self) -> None:
        """Auto-refresh loop."""
        while self.running:
            try:
                await asyncio.sleep(self.config.refresh_rate)
                if HAS_RICH:
                    self.console.clear()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Refresh error: {e}")
    
    async def _display_dashboard(self) -> None:
        """Display the dashboard."""
        if HAS_RICH:
            await self._display_dashboard_rich()
        else:
            await self._display_dashboard_simple()
    
    async def _display_dashboard_rich(self) -> None:
        """Display dashboard using Rich library."""
        while self.running:
            try:
                snapshot = self.monitor.get_portfolio_snapshot() if self.monitor else self._get_demo_snapshot()
                
                layout = Layout()
                layout.split_column(
                    Layout(self._render_header(snapshot), size=6),
                    Layout(self._render_main(snapshot), size=30),
                    Layout(self._render_footer(snapshot), size=4)
                )
                
                self.console.print(layout)
                await asyncio.sleep(self.config.refresh_rate)
                
            except Exception as e:
                print(f"Display error: {e}")
                break
    
    async def _display_dashboard_simple(self) -> None:
        """Display dashboard using plain text."""
        while self.running:
            try:
                snapshot = self.monitor.get_portfolio_snapshot() if self.monitor else self._get_demo_snapshot()
                
                self._clear_screen()
                self._render_header_simple(snapshot)
                self._render_positions_simple(snapshot)
                self._render_chart_simple(snapshot)
                self._render_signals_simple(snapshot)
                self._render_footer_simple(snapshot)
                
                await asyncio.sleep(self.config.refresh_rate)
                
            except Exception as e:
                print(f"Display error: {e}")
                break
    
    def _render_header(self, snapshot: Dict) -> Panel:
        """Render dashboard header."""
        account = snapshot.get("account", {})
        performance = snapshot.get("performance", {})
        
        title = f"AI QUANT HEDGE FUND v2.0"
        subtitle = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Mode: SEMI_AUTO"
        
        table = Table(show_header=False, box=None)
        table.add_column()
        table.add_column()
        table.add_column()
        table.add_column()
        table.add_column()
        
        equity = account.get("equity", 0)
        balance = account.get("balance", 0)
        daily_pnl = performance.get("daily_pnl", 0)
        daily_pct = (daily_pnl / balance * 100) if balance > 0 else 0
        
        table.add_row(
            f"💰 BALANCE: ${balance:,.2f}",
            f"📈 EQUITY: ${equity:,.2f}",
            f"📊 DAILY PnL: ${daily_pnl:+,.2f} ({daily_pct:+.2f}%)",
            f"📍 MARGIN: {account.get('margin_level', 0):.1f}%",
            f"🎯 MODE: SEMI_AUTO"
        )
        
        return Panel(
            Align.center(table),
            title=title,
            subtitle=subtitle,
            style="blue"
        )
    
    def _render_main(self, snapshot: Dict) -> Layout:
        """Render main dashboard content."""
        layout = Layout()
        layout.split_row(
            Layout(self._render_positions_panel(snapshot), size=0.4),
            Layout(self._render_chart_panel(snapshot))
        )
        return layout
    
    def _render_positions_panel(self, snapshot: Dict) -> Panel:
        """Render positions panel."""
        positions = snapshot.get("positions", {})
        
        if not positions:
            return Panel("No open positions", title="📊 OPEN POSITIONS")
        
        table = Table(show_header=True)
        table.add_column("Symbol")
        table.add_column("Side")
        table.add_column("Volume")
        table.add_column("Entry")
        table.add_column("Current")
        table.add_column("PnL")
        table.add_column("SL/TP")
        
        for ticket, pos in positions.items():
            pnl = pos.get("pnl", 0)
            pnl_color = "green" if pnl >= 0 else "red"
            
            table.add_row(
                pos.get("symbol", ""),
                pos.get("side", ""),
                f"{pos.get('volume', 0):.2f}",
                f"{pos.get('open_price', 0):.5f}",
                f"{pos.get('current_price', 0):.5f}",
                Text(f"${pnl:+.2f}", style=pnl_color),
                f"{pos.get('sl', '-')}/{pos.get('tp', '-')}"
            )
        
        return Panel(table, title="📊 OPEN POSITIONS")
    
    def _render_chart_panel(self, snapshot: Dict) -> Panel:
        """Render chart panel."""
        chart = self._render_ascii_chart()
        return Panel(chart, title="🕯️ LIVE CHART (EURUSD, 1m)")
    
    def _render_ascii_chart(self) -> str:
        """Render ASCII candlestick chart."""
        if not HAS_RICH:
            return self._get_demo_chart()
        
        candles = self._get_demo_candles()
        
        if not candles:
            return "No data available"
        
        lines = []
        for candle in candles[-self.config.chart_candles:]:
            open_p = candle["open"]
            high = candle["high"]
            low = candle["low"]
            close = candle["close"]
            time = candle["time"]
            
            if close >= open:
                body_char = "🟢"
                wick_char = "│"
            else:
                body_char = "🔴"
                wick_char = "│"
            
            line = f"{body_char} {time} O:{open_p:.5f} H:{high:.5f} L:{low:.5f} C:{close:.5f}"
            lines.append(line)
        
        return "\n".join(lines)
    
    def _render_footer(self, snapshot: Dict) -> Panel:
        """Render dashboard footer."""
        signals = self._get_demo_signals()
        signal_summary = signals[:3]
        
        text = " | ".join([
            f"[A] Analyze All",
            f"[R] Refresh",
            f"[C] Confirm All",
            f"[S] Settings",
            f"[Q] Quit"
        ])
        
        status = "CONNECTED" if self.monitor else "DEMO MODE"
        
        return Panel(
            f"{text} | Status: {status}",
            style="dim"
        )
    
    def _render_header_simple(self, snapshot: Dict) -> None:
        """Render header (simple mode)."""
        account = snapshot.get("account", {})
        performance = snapshot.get("performance", {})
        
        equity = account.get("equity", 0)
        balance = account.get("balance", 0)
        daily_pnl = performance.get("daily_pnl", 0)
        margin = account.get("margin_level", 0)
        
        print("=" * 80)
        print(f"  AI QUANT HEDGE FUND v2.0  |  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  Mode: SEMI_AUTO")
        print("=" * 80)
        print(f"  Balance: ${balance:>15,.2f}  |  Equity: ${equity:>15,.2f}")
        print(f"  Daily PnL: ${daily_pnl:>+12,.2f}  |  Margin Level: {margin:>8.1f}%")
        print("-" * 80)
    
    def _render_positions_simple(self, snapshot: Dict) -> None:
        """Render positions (simple mode)."""
        positions = snapshot.get("positions", {})
        
        print("\n  OPEN POSITIONS")
        print("  " + "-" * 76)
        
        if not positions:
            print("  No open positions")
        else:
            print(f"  {'Ticket':<8} {'Symbol':<10} {'Side':<6} {'Volume':<8} {'Entry':<12} {'Current':<12} {'PnL':<12}")
            print("  " + "-" * 76)
            
            for ticket, pos in positions.items():
                pnl = pos.get("pnl", 0)
                pnl_str = f"${pnl:+.2f}"
                side = pos.get("side", "")
                
                print(f"  {ticket:<8} {pos.get('symbol', ''):<10} {side:<6} "
                      f"{pos.get('volume', 0):.2f}     {pos.get('open_price', 0):.5f}    "
                      f"{pos.get('current_price', 0):.5f}    {pnl_str}")
        
        print()
    
    def _render_chart_simple(self, snapshot: Dict) -> None:
        """Render chart (simple mode)."""
        candles = self._get_demo_candles()
        
        print("  LIVE CHART (EURUSD, 1m)")
        print("  " + "-" * 76)
        
        if not candles:
            print("  No chart data available")
        else:
            for candle in candles[-20:]:
                open_p = candle["open"]
                high = candle["high"]
                low = candle["low"]
                close = candle["close"]
                time = candle["time"]
                
                if close >= open_p:
                    char = "[+]"
                else:
                    char = "[-]"
                
                print(f"  {char} {time} O:{open_p:.5f} H:{high:.5f} L:{low:.5f} C:{close:.5f}")
        
        print()
    
    def _render_signals_simple(self, snapshot: Dict) -> None:
        """Render signals (simple mode)."""
        signals = self._get_demo_signals()
        
        print("  STRATEGY SIGNALS")
        print("  " + "-" * 76)
        
        buy_count = sum(1 for s in signals if s.get("signal") == "BUY")
        sell_count = sum(1 for s in signals if s.get("signal") == "SELL")
        hold_count = sum(1 for s in signals if s.get("signal") == "HOLD")
        
        print(f"  Retail/SMC (18): BUY:{buy_count} | HOLD:{hold_count} | SELL:{sell_count}")
        print()
        
        for signal in signals[:5]:
            s = signal.get("signal", "")
            conf = signal.get("confidence", 0)
            strat = signal.get("strategy", "")
            
            if s == "BUY":
                marker = "[BUY]"
            elif s == "SELL":
                marker = "[SELL]"
            else:
                marker = "[---]"
            
            print(f"  {marker} {strat:<30} Confidence: {conf:.0%}")
        
        print()
    
    def _render_footer_simple(self, snapshot: Dict) -> None:
        """Render footer (simple mode)."""
        print("-" * 80)
        print("  [A] Analyze All  [R] Refresh  [C] Confirm All  [S] Settings  [Q] Quit")
        print("=" * 80)
    
    def _clear_screen(self) -> None:
        """Clear terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def _get_demo_snapshot(self) -> Dict:
        """Get demo snapshot for testing."""
        return {
            "timestamp": datetime.now().isoformat(),
            "account": {
                "id": "demo",
                "balance": 125432.10,
                "equity": 126789.45,
                "currency": "USD",
                "margin_used": 15000.0,
                "margin_free": 110789.45,
                "margin_level": 845.0
            },
            "positions": {
                "123456": {
                    "symbol": "EURUSD",
                    "side": "BUY",
                    "volume": 1.0,
                    "open_price": 1.0850,
                    "current_price": 1.0875,
                    "pnl": 250.0,
                    "sl": 1.0750,
                    "tp": 1.1000
                },
                "123457": {
                    "symbol": "GBPUSD",
                    "side": "BUY",
                    "volume": 0.5,
                    "open_price": 1.2700,
                    "current_price": 1.2750,
                    "pnl": 125.0,
                    "sl": 1.2650,
                    "tp": 1.2800
                }
            },
            "performance": {
                "daily_pnl": 1234.56,
                "total_pnl": 26789.45,
                "win_rate": 68.5,
                "profit_factor": 2.34
            }
        }
    
    def _get_demo_candles(self) -> List[Dict]:
        """Get demo candle data."""
        import random
        
        candles = []
        base_price = 1.0850
        
        for i in range(40):
            time = f"{14 + i // 60:02d}:{(i % 60):02d}"
            open_p = base_price + random.uniform(-0.001, 0.001)
            close = open_p + random.uniform(-0.0005, 0.0005)
            high = max(open_p, close) + random.uniform(0, 0.0003)
            low = min(open_p, close) - random.uniform(0, 0.0003)
            
            candles.append({
                "time": time,
                "open": open_p,
                "high": high,
                "low": low,
                "close": close
            })
            
            base_price = close
        
        return candles
    
    def _get_demo_signals(self) -> List[Dict]:
        """Get demo signal data."""
        strategies = [
            ("ICT SMC", "BUY", 0.72),
            ("Price Action", "BUY", 0.68),
            ("RSI Divergence", "BUY", 0.65),
            ("Moving Average Crossover", "HOLD", 0.55),
            ("MACD Crossover", "BUY", 0.70),
            ("Bollinger Bands", "SELL", 0.62),
            ("Fibonacci Retracement", "BUY", 0.58),
            ("Volume Spike", "HOLD", 0.52),
            ("Order Block", "BUY", 0.75),
            ("Liquidity Sweep", "SELL", 0.60)
        ]
        
        return [
            {
                "strategy": name,
                "signal": signal,
                "confidence": conf,
                "reasoning": ["Reason 1", "Reason 2"]
            }
            for name, signal, conf in strategies
        ]
    
    def get_portfolio_display(self) -> str:
        """Get portfolio summary for display."""
        if self.monitor:
            snapshot = self.monitor.get_portfolio_snapshot()
        else:
            snapshot = self._get_demo_snapshot()
        
        account = snapshot.get("account", {})
        return f"Equity: ${account.get('equity', 0):,.2f} | Margin: {account.get('margin_level', 0):.1f}%"


async def run_dashboard_demo() -> None:
    """Run dashboard demo."""
    dashboard = TerminalDashboard()
    await dashboard.start()


if __name__ == "__main__":
    asyncio.run(run_dashboard_demo())
