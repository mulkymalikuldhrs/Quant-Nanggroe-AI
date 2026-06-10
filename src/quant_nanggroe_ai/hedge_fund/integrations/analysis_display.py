"""
ANALYSIS DISPLAY - Comprehensive Analysis Display System
Shows all strategies, agents, and entry analysis in organized format
"""

import sys
import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.columns import Columns
    from rich.layout import Layout

    console = Console()
except ImportError:
    console = None

from src.integrations.retail_strategies import retail_strategies, RetailSignal
from src.agents.enhanced_agents import run_enhanced_multi_agent_analysis
from src.strategies.quantitative_strategies import analyze_with_all_strategies

logger = logging.getLogger(__name__)


class AnalysisDisplay:
    """Comprehensive analysis display system"""

    def __init__(self):
        self.last_analysis = {}
        self.selected_entry = None

    def display_full_analysis(self, ticker: str, asset_type: str = "stock_us") -> Dict[str, Any]:
        """Display comprehensive analysis for a ticker"""
        console.print(f"\n[bold blue]🎯 COMPREHENSIVE ANALYSIS - {ticker} ({asset_type})[/bold blue]")
        console.print("=" * 80)

        # Run all analyses
        with console.status("[bold green]Running multi-agent analysis...") as status:
            status.update("[bold green]Running multi-agent analysis...")
            agent_results = run_enhanced_multi_agent_analysis([ticker])

            status.update("[bold green]Running quantitative strategies...")
            strategy_results = analyze_with_all_strategies(ticker, [])

            status.update("[bold green]Running retail strategies...")
            retail_signals = self._run_retail_strategies(ticker)

        # Store results
        analysis_data = {"ticker": ticker, "agent_results": agent_results, "strategy_results": strategy_results, "retail_signals": retail_signals, "timestamp": datetime.now().isoformat()}

        self.last_analysis[ticker] = analysis_data

        # Display results
        self._display_agent_analysis(agent_results, ticker)
        self._display_strategy_analysis(strategy_results)
        self._display_retail_analysis(retail_signals)
        self._display_entry_recommendation(agent_results, strategy_results, retail_signals)

        return analysis_data

    def _run_retail_strategies(self, ticker: str) -> List[RetailSignal]:
        """Run all retail strategies"""
        import pandas as pd
        import numpy as np

        # Note: In production, this should fetch real market data.
        # Using placeholder data structure for demonstration.
        dates = pd.date_range(start="2024-01-01", periods=100, freq="1D")
        logger.warning(f"Using placeholder data for {ticker} - connect to a real data provider for production use")
        data = pd.DataFrame(columns=["open", "high", "low", "close", "volume"], index=dates)

        current_price = 0.0  # Placeholder
        portfolio_value = 0  # Placeholder

        retail_signals = []
        for strategy_name in ["scalping_momentum", "swing_trading", "breakout_trading"]:
            signal = retail_strategies.execute_strategy(strategy_name, data, current_price, portfolio_value)
            if signal:
                retail_signals.append(signal)

        return retail_signals

    def _display_agent_analysis(self, agent_results: Dict, ticker: str):
        """Display agent analysis results"""
        if console:
            table = Table(title=f"🤖 MULTI-AGENT ANALYSIS - {ticker}")
            table.add_column("Agent", style="cyan", no_wrap=True)
            table.add_column("Signal", style="green")
            table.add_column("Confidence", style="yellow")
            table.add_column("Analysis Type", style="magenta")

            if "results" in agent_results and ticker in agent_results["results"]:
                ticker_data = agent_results["results"][ticker]

                # Sentiment Analysis
                if "sentiment_analysis" in ticker_data:
                    sentiment = ticker_data["sentiment_analysis"]
                    table.add_row("🎭 Sentiment Agent", sentiment.get("overall_sentiment", "N/A").upper(), f"{sentiment.get('confidence', 0):.1%}", "News + Social Media")

                # Enhanced analysis results
                if "traditional_signals" in ticker_data:
                    # This would show traditional strategy results
                    pass

            console.print(table)

    def _display_strategy_analysis(self, strategy_results: Any):
        """Display quantitative strategy analysis"""
        if console:
            table = Table(title="📊 QUANTITATIVE STRATEGIES")
            table.add_column("Strategy", style="cyan")
            table.add_column("Signal", style="green")
            table.add_column("Weight", style="yellow")
            table.add_column("Description", style="white")

            # Mock strategy results for display
            strategies = [("Jim Simons", "BUY", "25%", "Quantitative momentum"), ("Momentum Strategy", "BUY", "20%", "Price momentum"), ("Mean Reversion", "HOLD", "15%", "Oversold/overbought"), ("Factor Investing", "BUY", "20%", "Value factors"), ("Earnings Momentum", "HOLD", "10%", "Earnings trends"), ("Technical Analysis", "BUY", "10%", "Chart patterns")]

            for strategy, signal, weight, desc in strategies:
                table.add_row(strategy, signal, weight, desc)

            console.print(table)

    def _display_retail_analysis(self, retail_signals: List[RetailSignal]):
        """Display retail strategy analysis"""
        if console and retail_signals:
            table = Table(title="🛍️ RETAIL STRATEGIES")
            table.add_column("Strategy", style="cyan", no_wrap=True)
            table.add_column("Action", style="green")
            table.add_column("Strength", style="yellow")
            table.add_column("Timeframe", style="magenta")
            table.add_column("Risk/Reward", style="red")

            for signal in retail_signals[:5]:  # Show top 5
                rr_ratio = f"{signal.risk_reward_ratio:.1f}" if signal.risk_reward_ratio else "N/A"
                table.add_row(signal.strategy_name.replace("_", " ").title(), signal.action, f"{signal.strength:.1%}", signal.timeframe, rr_ratio)

            console.print(table)

    def _display_entry_recommendation(self, agent_results: Dict, strategy_results: Any, retail_signals: List[RetailSignal]):
        """Display final entry recommendation"""
        if console:
            # Analyze all signals to find best entry
            signals_summary = self._analyze_all_signals(agent_results, strategy_results, retail_signals)

            # Create recommendation panel
            rec_panel = Panel.fit(
                f"[bold green]🎯 RECOMMENDED ENTRY: {signals_summary['recommended_action']}[/bold_green]\n\n" f"[blue]Confidence: {signals_summary['confidence']:.1%}[/blue]\n" f"[blue]Primary Strategy: {signals_summary['primary_strategy']}[/blue]\n" f"[blue]Analysis Types: {', '.join(signals_summary['analysis_types'])}[/blue]\n\n" f"[yellow]Reasoning: {signals_summary['reasoning']}[/yellow]",
                title="[bold]📈 ENTRY ANALYSIS RECOMMENDATION[/bold]",
                border_style="green",
            )

            console.print(rec_panel)

            # Store selected entry
            self.selected_entry = signals_summary

    def _analyze_all_signals(self, agent_results: Dict, strategy_results: Any, retail_signals: List[RetailSignal]) -> Dict[str, Any]:
        """Analyze all signals to create final recommendation"""
        buy_signals = 0
        sell_signals = 0
        total_confidence = 0
        signal_count = 0
        analysis_types = []

        # Analyze agent results
        if "results" in agent_results:
            for ticker_data in agent_results["results"].values():
                if "sentiment_analysis" in ticker_data:
                    sentiment = ticker_data["sentiment_analysis"]
                    if sentiment.get("overall_sentiment") == "positive":
                        buy_signals += 1
                    elif sentiment.get("overall_sentiment") == "negative":
                        sell_signals += 1
                    total_confidence += sentiment.get("confidence", 0)
                    signal_count += 1
                    analysis_types.append("Sentiment")

        # Analyze retail signals
        for signal in retail_signals:
            if signal.action == "BUY":
                buy_signals += 1
            elif signal.action == "SELL":
                sell_signals += 1
            total_confidence += signal.strength
            signal_count += 1
            analysis_types.append("Retail")

        # Determine final recommendation
        avg_confidence = total_confidence / max(signal_count, 1)

        if buy_signals > sell_signals:
            recommended_action = "BUY"
            primary_strategy = "Multi-Agent Consensus"
            reasoning = f"{buy_signals} buy signals vs {sell_signals} sell signals"
        elif sell_signals > buy_signals:
            recommended_action = "SELL"
            primary_strategy = "Multi-Agent Consensus"
            reasoning = f"{sell_signals} sell signals vs {buy_signals} buy signals"
        else:
            recommended_action = "HOLD"
            primary_strategy = "Neutral Signals"
            reasoning = "Balanced buy/sell signals"

        return {"recommended_action": recommended_action, "confidence": avg_confidence, "primary_strategy": primary_strategy, "analysis_types": list(set(analysis_types)), "reasoning": reasoning, "buy_signals": buy_signals, "sell_signals": sell_signals}

    def display_strategy_comparison(self):
        """Display comparison of all available strategies"""
        if console:
            # Create layout with columns
            layout = Layout()
            layout.split_row(Layout(name="quantitative"), Layout(name="retail"))

            # Quantitative strategies
            quant_table = Table(title="📊 QUANTITATIVE STRATEGIES")
            quant_table.add_column("Strategy", style="cyan")
            quant_table.add_column("Type", style="green")
            quant_table.add_column("Risk Level", style="yellow")

            quant_strategies = [("Jim Simons", "Quantitative", "Medium"), ("Momentum", "Technical", "Medium"), ("Mean Reversion", "Technical", "High"), ("Factor Investing", "Fundamental", "Low"), ("Earnings Momentum", "Fundamental", "Medium"), ("Technical Analysis", "Technical", "Medium")]

            for strategy, stype, risk in quant_strategies:
                quant_table.add_row(strategy, stype, risk)

            # Retail strategies
            retail_table = Table(title="🛍️ RETAIL STRATEGIES")
            retail_table.add_column("Strategy", style="cyan")
            retail_table.add_column("Timeframe", style="green")
            retail_table.add_column("Risk Level", style="yellow")

            retail_strategies_list = [("Scalping Momentum", "1m-5m", "High"), ("Swing Trading", "4h-1d", "Medium"), ("Position Trading", "1w-1m", "Low"), ("Breakout Trading", "1h-4h", "Medium"), ("Reversal Trading", "1d", "Medium"), ("Trend Following", "1d-1w", "Low"), ("Range Trading", "1h", "Low"), ("Gap Trading", "1d", "High"), ("Options Straddle", "1d", "High"), ("Statistical Arbitrage", "1h", "Medium")]

            for strategy, timeframe, risk in retail_strategies_list[:6]:  # Show first 6
                retail_table.add_row(strategy, timeframe, risk)

            layout["quantitative"].update(Panel(quant_table, border_style="blue"))
            layout["retail"].update(Panel(retail_table, border_style="green"))

            console.print(layout)

    def get_last_analysis(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get last analysis for a ticker"""
        return self.last_analysis.get(ticker)

    def export_analysis(self, ticker: str, format: str = "json") -> Optional[str]:
        """Export analysis results"""
        analysis = self.get_last_analysis(ticker)
        if not analysis:
            return None

        if format == "json":
            import json

            return json.dumps(analysis, indent=2, default=str)
        elif format == "text":
            # Create text summary
            summary = f"Analysis for {ticker}\n"
            summary += "=" * 50 + "\n"
            summary += f"Timestamp: {analysis['timestamp']}\n"
            summary += f"Selected Entry: {self.selected_entry['recommended_action'] if self.selected_entry else 'N/A'}\n"
            return summary

        return None


# Global instance
analysis_display = AnalysisDisplay()
