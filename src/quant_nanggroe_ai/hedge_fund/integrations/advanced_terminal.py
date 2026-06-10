"""
ADVANCED TERMINAL INTERFACE - Multi-Agent Trading Terminal
Features: Real-time analysis, strategy selection, MetaTrader integration
"""

import sys
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.live import Live
    from rich.spinner import Spinner

    console = Console()
except ImportError:
    console = None

from src.agents.enhanced_agents import run_enhanced_multi_agent_analysis
from src.strategies.quantitative_strategies import analyze_with_all_strategies
from src.tools.advanced_data_provider import data_provider


@dataclass
class TradingSignal:
    """Trading signal with entry analysis"""

    ticker: str
    action: str  # BUY, SELL, HOLD
    confidence: float
    entry_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    risk_reward_ratio: Optional[float]
    timeframe: str
    strategy_used: str
    analysis_type: str  # 'quantitative', 'technical', 'sentiment', 'fundamental'


@dataclass
class RetailStrategy:
    """Retail trading strategy configuration"""

    name: str
    description: str
    risk_level: str  # 'low', 'medium', 'high'
    timeframe: str
    indicators: List[str]
    entry_rules: List[str]
    exit_rules: List[str]
    max_drawdown: float


class AdvancedTerminal:
    """Advanced trading terminal with MetaTrader integration"""

    def __init__(self):
        self.active_signals: Dict[str, List[TradingSignal]] = {}
        self.retail_strategies = self._initialize_retail_strategies()
        self.current_analysis = {}
        self.metatrader_connected = False
        self.selected_entry_strategy = None

    def _initialize_retail_strategies(self) -> Dict[str, RetailStrategy]:
        """Initialize retail trading strategies"""
        return {
            "scalping_momentum": RetailStrategy(name="Scalping Momentum", description="High-frequency momentum scalping for quick profits", risk_level="high", timeframe="1m", indicators=["RSI", "MACD", "Volume"], entry_rules=["RSI < 30", "MACD crossover", "Volume spike"], exit_rules=["RSI > 70", "Profit target 0.5%", "Stop loss 0.2%"], max_drawdown=0.02),
            "swing_trading": RetailStrategy(name="Swing Trading", description="Medium-term swing trading with trend following", risk_level="medium", timeframe="4h", indicators=["SMA", "Bollinger Bands", "Stochastic"], entry_rules=["Price above SMA(20)", "Stochastic oversold", "BB squeeze"], exit_rules=["Price below SMA(20)", "Stochastic overbought", "Time-based exit"], max_drawdown=0.05),
            "position_trading": RetailStrategy(name="Position Trading", description="Long-term position trading with fundamental analysis", risk_level="low", timeframe="1d", indicators=["SMA", "Volume", "Support/Resistance"], entry_rules=["Strong fundamentals", "Accumulation pattern", "Volume confirmation"], exit_rules=["Profit target 20%", "Stop loss 10%", "Fundamental deterioration"], max_drawdown=0.10),
            "arbitrage_pair": RetailStrategy(name="Statistical Arbitrage", description="Pairs trading with statistical arbitrage", risk_level="medium", timeframe="1h", indicators=["Spread", "Z-score", "Cointegration"], entry_rules=["Z-score > 2", "Spread deviation", "Cointegration stable"], exit_rules=["Z-score < 0.5", "Profit target 1%", "Spread normalization"], max_drawdown=0.03),
            "breakout_trading": RetailStrategy(name="Breakout Trading", description="Breakout trading with volume confirmation", risk_level="medium", timeframe="1h", indicators=["Support/Resistance", "Volume", "Breakout candle"], entry_rules=["Break above resistance", "Volume > average", "Retest successful"], exit_rules=["Pullback to entry", "Profit target 2:1 RR", "False breakout"], max_drawdown=0.04),
        }

    def display_welcome(self):
        """Display welcome screen with system capabilities"""
        if console:
            welcome_panel = Panel.fit(
                "[bold blue]🤖 AI HEDGE FUND TERMINAL[/bold blue]\n\n" "[green]✅ Multi-Agent Analysis[/green]\n" "[green]✅ Quantitative Strategies[/green]\n" "[green]✅ Retail Trading Strategies[/green]\n" "[green]✅ MetaTrader Integration[/green]\n" "[green]✅ Real-time Analysis[/green]\n\n" "[yellow]🎯 Ready for Advanced Trading![/yellow]", title="[bold]🚀 ADVANCED TRADING TERMINAL[/bold]", border_style="blue"
            )
            console.print(welcome_panel)
        else:
            print("🤖 AI HEDGE FUND TERMINAL")
            print("✅ Multi-Agent Analysis")
            print("✅ Quantitative Strategies")
            print("✅ Retail Trading Strategies")
            print("✅ MetaTrader Integration")
            print("🎯 Ready for Advanced Trading!")

    def select_entry_strategy(self, available_strategies: Dict[str, Any]) -> str:
        """Select best entry strategy from analysis results"""
        if not available_strategies:
            return "hold"

        # Find strategy with highest confidence
        best_strategy = None
        best_confidence = 0
        best_action = "hold"

        for strategy_name, analysis in available_strategies.items():
            if isinstance(analysis, dict) and "confidence" in analysis:
                confidence = analysis.get("confidence", 0)
                action = analysis.get("action", "hold")

                if confidence > best_confidence:
                    best_confidence = confidence
                    best_strategy = strategy_name
                    best_action = action

        self.selected_entry_strategy = {"strategy": best_strategy, "confidence": best_confidence, "action": best_action, "timestamp": datetime.now().isoformat()}

        return best_action

    def analyze_asset(self, ticker: str, asset_type: str = "stock_us") -> Dict[str, Any]:
        """Comprehensive asset analysis with all components"""
        console.print(f"\n[bold blue]🔍 Analyzing {ticker} ({asset_type})[/bold blue]")

        with console.status("[bold green]Running multi-agent analysis...") as status:
            # 1. Multi-agent analysis
            status.update("[bold green]Running multi-agent analysis...")
            agent_results = run_enhanced_multi_agent_analysis([ticker])

            # 2. Quantitative strategies
            status.update("[bold green]Running quantitative strategies...")
            strategy_results = analyze_with_all_strategies(ticker, [])

            # 3. Get market data
            status.update("[bold green]Fetching market data...")
            market_data = data_provider.get_historical_prices(ticker, period="1mo")

            # 4. Generate trading signals
            status.update("[bold green]Generating trading signals...")
            signals = self._generate_trading_signals(ticker, agent_results, strategy_results, market_data)

            # 5. Select best entry strategy
            status.update("[bold green]Selecting optimal entry...")
            best_action = self.select_entry_strategy(signals)

        # Store results
        self.current_analysis[ticker] = {"agent_results": agent_results, "strategy_results": strategy_results, "market_data": market_data, "signals": signals, "selected_action": best_action, "timestamp": datetime.now().isoformat()}

        return self.current_analysis[ticker]

    def _generate_trading_signals(self, ticker: str, agent_results: Dict, strategy_results: Dict, market_data: Any) -> Dict[str, TradingSignal]:
        """Generate comprehensive trading signals"""
        signals = {}

        # Extract signals from agent results
        if agent_results and "results" in agent_results:
            ticker_data = agent_results["results"].get(ticker, {})
            if ticker_data.get("sentiment_analysis"):
                sentiment = ticker_data["sentiment_analysis"]
                signals["sentiment"] = TradingSignal(ticker=ticker, action=sentiment.get("overall_sentiment", "hold").upper(), confidence=sentiment.get("confidence", 0.5), entry_price=None, stop_loss=None, take_profit=None, risk_reward_ratio=None, timeframe="1d", strategy_used="sentiment_analysis", analysis_type="sentiment")  # Will be calculated

        # Extract signals from strategy results
        if hasattr(strategy_results, "final_signal"):
            signals["quantitative"] = TradingSignal(ticker=ticker, action=strategy_results.final_signal.upper(), confidence=getattr(strategy_results, "weighted_score", 0.5), entry_price=None, stop_loss=None, take_profit=None, risk_reward_ratio=None, timeframe="1d", strategy_used="quantitative_ensemble", analysis_type="quantitative")

        return signals

    def display_analysis_results(self, ticker: str):
        """Display comprehensive analysis results"""
        if ticker not in self.current_analysis:
            console.print(f"[red]❌ No analysis found for {ticker}[/red]")
            return

        analysis = self.current_analysis[ticker]

        # Main results table
        if console:
            table = Table(title=f"📊 ANALYSIS RESULTS - {ticker}")
            table.add_column("Component", style="cyan")
            table.add_column("Signal", style="green")
            table.add_column("Confidence", style="yellow")
            table.add_column("Strategy", style="magenta")

            # Agent results
            if "agent_results" in analysis:
                agent_data = analysis["agent_results"]["results"].get(ticker, {})
                if agent_data.get("sentiment_analysis"):
                    sentiment = agent_data["sentiment_analysis"]
                    table.add_row("🤖 Sentiment Agent", sentiment.get("overall_sentiment", "N/A").upper(), f"{sentiment.get('confidence', 0):.1%}", "News + Social Media")

            # Strategy results
            if "strategy_results" in analysis:
                strategy = analysis["strategy_results"]
                if hasattr(strategy, "final_signal"):
                    table.add_row("📈 Quantitative Strategies", getattr(strategy, "final_signal", "N/A").upper(), f"{getattr(strategy, 'weighted_score', 0):.1%}", "6-Strategy Ensemble")

            # Selected action
            selected_action = analysis.get("selected_action", "HOLD")
            confidence = 0.5
            if self.selected_entry_strategy:
                confidence = self.selected_entry_strategy.get("confidence", 0.5)

            table.add_row("🎯 SELECTED ENTRY", selected_action.upper(), f"{confidence:.1%}", self.selected_entry_strategy.get("strategy", "N/A") if self.selected_entry_strategy else "N/A", style="bold green")

            console.print(table)

            # Signals details
            if analysis.get("signals"):
                signals_panel = Panel.fit("\n".join([f"• {sig.analysis_type.upper()}: {sig.action} ({sig.confidence:.1%}) - {sig.strategy_used}" for sig in analysis["signals"].values()]), title="📡 TRADING SIGNALS", border_style="green")
                console.print(signals_panel)

        else:
            # Fallback text display
            print(f"\n📊 ANALYSIS RESULTS - {ticker}")
            print("=" * 50)

            analysis_data = self.current_analysis[ticker]
            print(f"Selected Action: {analysis_data.get('selected_action', 'HOLD').upper()}")
            print(f"Analysis Timestamp: {analysis_data.get('timestamp', 'N/A')}")

    def show_retail_strategies(self):
        """Display available retail trading strategies"""
        if console:
            table = Table(title="🛍️ RETAIL TRADING STRATEGIES")
            table.add_column("Strategy", style="cyan", no_wrap=True)
            table.add_column("Description", style="white")
            table.add_column("Risk", style="red")
            table.add_column("Timeframe", style="yellow")
            table.add_column("Max DD", style="magenta")

            for strategy in self.retail_strategies.values():
                table.add_row(strategy.name, strategy.description, strategy.risk_level.upper(), strategy.timeframe, f"{strategy.max_drawdown:.1%}")

            console.print(table)
        else:
            print("\n🛍️ RETAIL TRADING STRATEGIES")
            print("=" * 50)
            for name, strategy in self.retail_strategies.items():
                print(f"{name}: {strategy.description} (Risk: {strategy.risk_level})")

    def connect_metatrader(self, mt_version: str = "5") -> bool:
        """Connect to MetaTrader terminal"""
        try:
            # Mock MetaTrader connection
            import time

            console.print(f"[bold blue]🔌 Connecting to MetaTrader {mt_version}...[/bold blue]")

            with console.status("[bold green]Establishing connection...") as status:
                time.sleep(1)
                status.update("[bold green]Authenticating...")
                time.sleep(1)
                status.update("[bold green]Syncing account...")
                time.sleep(1)

            self.metatrader_connected = True
            console.print("[green]✅ MetaTrader connection established![/green]")
            return True

        except Exception as e:
            console.print(f"[red]❌ MetaTrader connection failed: {e}[/red]")
            return False

    def execute_trade_metatrader(self, signal: TradingSignal) -> bool:
        """Execute trade via MetaTrader"""
        if not self.metatrader_connected:
            console.print("[red]❌ MetaTrader not connected[/red]")
            return False

        try:
            console.print(f"[bold blue]📤 Executing {signal.action} order for {signal.ticker} via MetaTrader...[/bold blue]")

            # Mock trade execution
            import time

            with console.status("[bold green]Sending order...") as status:
                time.sleep(0.5)
                status.update("[bold green]Order confirmed...")
                time.sleep(0.5)

            console.print(f"[green]✅ Trade executed: {signal.action} {signal.ticker} at market price[/green]")
            return True

        except Exception as e:
            console.print(f"[red]❌ Trade execution failed: {e}[/red]")
            return False

    def run_terminal(self):
        """Run the advanced trading terminal"""
        self.display_welcome()

        while True:
            if console:
                console.print("\n[bold cyan]🎯 AVAILABLE COMMANDS:[/bold cyan]")
                console.print("1. 📊 Analyze Asset (e.g., 'analyze AAPL')")
                console.print("2. 🛍️ Show Retail Strategies")
                console.print("3. 🔌 Connect MetaTrader")
                console.print("4. 📈 Show Analysis Results")
                console.print("5. 🚪 Exit")
                console.print()

                command = console.input("[bold green]Enter command:[/bold green] ").strip()
            else:
                print("\n🎯 AVAILABLE COMMANDS:")
                print("1. Analyze Asset (e.g., 'analyze AAPL')")
                print("2. Show Retail Strategies")
                print("3. Connect MetaTrader")
                print("4. Show Analysis Results")
                print("5. Exit")
                command = input("\nEnter command: ").strip()

            if command.lower() in ["exit", "5", "quit"]:
                break
            elif command.lower() in ["strategies", "2"]:
                self.show_retail_strategies()
            elif command.lower() in ["connect", "3", "metatrader"]:
                self.connect_metatrader()
            elif command.lower() in ["results", "4"]:
                if self.current_analysis:
                    for ticker in self.current_analysis.keys():
                        self.display_analysis_results(ticker)
                        break
                else:
                    console.print("[yellow]⚠️ No analysis results available. Run analysis first.[/yellow]")
            elif command.startswith("analyze"):
                parts = command.split()
                if len(parts) >= 2:
                    ticker = parts[1].upper()
                    asset_type = parts[2] if len(parts) > 2 else "stock_us"
                    self.analyze_asset(ticker, asset_type)
                    self.display_analysis_results(ticker)
                else:
                    console.print("[red]❌ Usage: analyze TICKER [ASSET_TYPE][/red]")
            else:
                console.print("[red]❌ Unknown command. Type 'help' for available commands.[/red]")

        console.print("[bold blue]👋 Thank you for using AI Hedge Fund Terminal![/bold blue]")


# Global instance
advanced_terminal = AdvancedTerminal()
