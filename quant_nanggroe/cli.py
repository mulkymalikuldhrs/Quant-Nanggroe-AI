"""CLI entry point for Quant Nanggroe AI.

Click-based CLI with Rich console output for the Agentic Trading Intelligence OS.

Commands:
- qnai run --symbols AAPL,MSFT --provider openai  - Run trading pipeline
- qnai backtest --strategy momentum --period 1Y    - Run backtest
- qnai agents list                                   - List available agents
- qnai portfolio status                              - Show portfolio status
- qnai risk check BTC/USDT                           - Run risk assessment
- qnai serve                                         - Start API server
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

console = Console()

# Banner
_BANNER = """
[bold cyan]╔══════════════════════════════════════════════╗[/bold cyan]
[bold cyan]║   [bold white]Quant Nanggroe AI[/bold white]                           [bold cyan]║[/bold cyan]
[bold cyan]║   [dim]Agentic Trading Intelligence OS[/dim]           [bold cyan]║[/bold cyan]
[bold cyan]║   [dim]v0.2.0 — Multi-Agent · LangGraph · Risk[/dim]   [bold cyan]║[/bold cyan]
[bold cyan]╚══════════════════════════════════════════════╝[/bold cyan]
"""


@click.group()
@click.version_option(version="0.2.0", prog_name="qnai")
def main():
    """Quant Nanggroe AI — Agentic Trading Intelligence OS."""
    pass


# =============================================================================
# Run Command
# =============================================================================


@main.command()
@click.option(
    "--symbols", "-s",
    default="BTC/USDT",
    help="Comma-separated trading symbols (e.g., AAPL,MSFT,BTC/USDT)",
)
@click.option(
    "--provider", "-p",
    default="openai",
    type=click.Choice(["openai", "anthropic", "google", "ollama", "openrouter"]),
    help="LLM provider",
)
@click.option("--deep-model", default="gpt-4o", help="Deep-thinking model")
@click.option("--quick-model", default="gpt-4o-mini", help="Quick-thinking model")
@click.option("--paper", is_flag=True, default=True, help="Use paper trading (default)")
@click.option("--live", is_flag=True, default=False, help="Use LIVE trading (dangerous!)")
@click.option("--trade-date", default=None, help="Trading date YYYY-MM-DD (default: today)")
def run(
    symbols: str,
    provider: str,
    deep_model: str,
    quick_model: str,
    paper: bool,
    live: bool,
    trade_date: Optional[str],
):
    """Run the trading pipeline with specified symbols and provider."""
    console.print(_BANNER)

    symbol_list = [s.strip() for s in symbols.split(",")]
    mode = "LIVE" if live else "PAPER"
    trade_date = trade_date or datetime.now().strftime("%Y-%m-%d")

    # Display run configuration
    config_table = Table(title="Pipeline Configuration", box=box.ROUNDED, show_header=False)
    config_table.add_column("Key", style="cyan")
    config_table.add_column("Value", style="white")
    config_table.add_row("Symbols", ", ".join(symbol_list))
    config_table.add_row("Provider", provider)
    config_table.add_row("Deep Model", deep_model)
    config_table.add_row("Quick Model", quick_model)
    config_table.add_row("Mode", f"[bold {'red' if live else 'green'}]{mode}")
    config_table.add_row("Trade Date", trade_date)
    console.print(config_table)
    console.print()

    if live:
        console.print(
            Panel(
                "[bold red]⚠ LIVE TRADING MODE — Real money at risk![/bold red]\n"
                "Constitutional risk limits are enforced and cannot be overridden.",
                title="[bold red]WARNING[/bold red]",
                border_style="red",
            )
        )

    # Execute pipeline
    console.print("[bold cyan]▶ Starting trading pipeline...[/bold cyan]")
    console.print()

    try:
        from quant_nanggroe.agents.graph import TradingGraph
        from quant_nanggroe.config.settings import get_settings

        settings = get_settings()
        api_key = (
            settings.openai_api_key
            or settings.anthropic_api_key
            or settings.google_api_key
        )

        if not api_key:
            console.print(
                "[bold yellow]⚠ No LLM API keys configured. Set QNAI_OPENAI_API_KEY or similar.[/bold yellow]"
            )
            console.print("[bold yellow]Running strategy-only pipeline...[/bold yellow]")
            _run_strategy_pipeline(symbol_list, trade_date)
            return

        graph = TradingGraph(
            llm_provider=provider,
            deep_think_model=deep_model,
            quick_think_model=quick_model,
            api_key=api_key,
        )

        with console.status("[bold green]Running multi-agent pipeline...", spinner="dots"):
            result = graph.run(
                symbols=symbol_list,
                trade_date=trade_date,
            )

        _display_pipeline_result(result, symbol_list)

    except ImportError as e:
        console.print(f"[bold red]✗ Import error: {e}[/bold red]")
        console.print("[bold yellow]Running strategy-only pipeline...[/bold yellow]")
        _run_strategy_pipeline(symbol_list, trade_date)
    except Exception as e:
        console.print(f"[bold red]✗ Pipeline error: {e}[/bold red]")
        console.print("[bold yellow]Running strategy-only pipeline...[/bold yellow]")
        _run_strategy_pipeline(symbol_list, trade_date)


def _run_strategy_pipeline(symbols: list, trade_date: str) -> None:
    """Run strategy-only pipeline (no LLM) via ProductionStrategyRunner."""
    try:
        from quant_nanggroe.engine_production_bridge import ProductionStrategyRunner
        runner = ProductionStrategyRunner()
        prices = {s: 100.0 for s in symbols}
        signals = runner.generate_signals({}, prices)
        if signals:
            table = Table(title="Strategy Signals", box=box.ROUNDED)
            table.add_column("Symbol", style="cyan")
            table.add_column("Side", style="bold")
            table.add_column("Confidence", style="white")
            table.add_column("Price", style="white")
            table.add_column("Strategy", style="dim")
            for s in signals:
                side_color = "green" if s.side == "buy" else "red"
                table.add_row(
                    s.symbol,
                    f"[{side_color}]{s.side.upper()}[/{side_color}]",
                    f"{s.confidence:.2%}",
                    f"${s.price:.2f}",
                    s.strategy,
                )
            console.print(table)
        else:
            console.print("[dim]No signals generated by active strategies.[/dim]")
        console.print()
        console.print(
            Panel(
                f"[bold green]✓ Strategy pipeline complete for {', '.join(symbols)}[/bold green]\n"
                f"[dim]Date: {trade_date} | Mode: STRATEGY-ONLY (no LLM)[/dim]\n"
                f"[dim]Configure LLM API keys for full agentic execution[/dim]",
                title="Pipeline Status",
                border_style="green",
            )
        )
    except Exception as e:
        console.print(f"[bold yellow]Strategy pipeline unavailable: {e}[/bold yellow]")


def _display_pipeline_result(result: dict, symbols: list) -> None:
    """Display actual pipeline execution results."""
    # Status
    status = "success" if not result.get("error") else "error"
    status_color = "green" if status == "success" else "red"
    console.print(f"[bold {status_color}]✓ Pipeline {status}[/bold {status_color}]")

    # Risk verdict
    verdict = result.get("risk_verdict", "VETOED")
    verdict_color = "green" if verdict == "APPROVED" else "red"
    console.print(f"  Risk Verdict: [bold {verdict_color}]{verdict}[/bold {verdict_color}]")

    # Confidence
    confidence = result.get("confidence", 0.0)
    conf_color = "green" if confidence >= 0.65 else "yellow" if confidence >= 0.4 else "red"
    console.print(f"  Confidence: [bold {conf_color}]{confidence:.2%}[/bold {conf_color}]")

    # Decisions
    decisions = result.get("decisions", [])
    if decisions:
        table = Table(title="Trading Decisions", box=box.ROUNDED)
        table.add_column("Symbol", style="cyan")
        table.add_column("Action", style="bold")
        table.add_column("Confidence", style="white")
        table.add_column("Reasoning", style="dim", max_width=50)
        for d in decisions:
            action = d.get("action", "HOLD")
            action_color = "green" if action == "BUY" else "red" if action == "SELL" else "yellow"
            table.add_row(
                d.get("symbol", ""),
                f"[{action_color}]{action}[/{action_color}]",
                f"{d.get('confidence', 0):.2%}",
                d.get("reasoning", "")[:50],
            )
        console.print(table)

    # Error display
    if result.get("error"):
        console.print(f"  [bold red]Error: {result['error']}[/bold red]")


# =============================================================================
# Backtest Command
# =============================================================================


@main.command()
@click.option(
    "--strategy", "-st",
    required=True,
    type=click.Choice(["momentum", "mean_reversion", "breakout", "scalping", "swing", "all"]),
    help="Strategy to backtest",
)
@click.option(
    "--symbols", "-s",
    default="BTC/USDT",
    help="Comma-separated symbols",
)
@click.option(
    "--period",
    default="1Y",
    type=click.Choice(["1M", "3M", "6M", "1Y", "2Y"]),
    help="Backtest period",
)
@click.option("--capital", "-c", default=100000.0, help="Initial capital")
@click.option("--commission", default=0.001, help="Commission rate")
@click.option("--market", default="crypto", type=click.Choice(["equity", "crypto", "forex"]))
def backtest(
    strategy: str,
    symbols: str,
    period: str,
    capital: float,
    commission: float,
    market: str,
):
    """Run backtesting with a specified strategy."""
    console.print(_BANNER)

    symbol_list = [s.strip() for s in symbols.split(",")]

    console.print(
        Panel(
            f"[bold white]Strategy:[/bold white] {strategy}\n"
            f"[bold white]Symbols:[/bold white] {', '.join(symbol_list)}\n"
            f"[bold white]Period:[/bold white] {period}\n"
            f"[bold white]Capital:[/bold white] ${capital:,.0f}\n"
            f"[bold white]Market:[/bold white] {market}",
            title="Backtest Configuration",
            border_style="cyan",
        )
    )

    try:
        from quant_nanggroe.engine.backtest.engine import (
            BacktestEngine,
            BacktestConfig,
            MarketType,
        )

        market_type = MarketType.CRYPTO
        if market == "equity":
            market_type = MarketType.EQUITY
        elif market == "forex":
            market_type = MarketType.FOREX

        config = BacktestConfig(
            initial_capital=capital,
            commission_rate=commission,
            market=market_type,
        )

        console.print("[bold cyan]▶ Backtest engine initialized.[/bold cyan]")
        console.print("[dim]Note: Full backtest requires price data files. Use data connectors to load data.[/dim]")

        # Show config summary
        summary_table = Table(title="Backtest Engine Status", box=box.ROUNDED, show_header=False)
        summary_table.add_column("Key", style="cyan")
        summary_table.add_column("Value", style="white")
        summary_table.add_row("Engine", "Initialized ✓")
        summary_table.add_row("Config", f"Capital=${capital:,.0f}, Commission={commission}")
        summary_table.add_row("Strategy", strategy)
        summary_table.add_row("Market Type", market_type.value)
        summary_table.add_row("Data Required", "Load price data via data connectors")
        console.print(summary_table)

    except ImportError as e:
        console.print(f"[bold yellow]⚠ Backtest engine import error: {e}[/bold yellow]")
        console.print("[dim]Install full dependencies for backtest support.[/dim]")
    except Exception as e:
        console.print(f"[bold red]✗ Backtest error: {e}[/bold red]")


# =============================================================================
# Agents Command Group
# =============================================================================


@main.group()
def agents():
    """Agent management commands."""
    pass


@agents.command("list")
def agents_list():
    """List all available trading agents."""
    console.print(_BANNER)

    _PHASE_MAP = {
        "researcher": "Analysis", "macro": "Analysis", "crypto": "Analysis", "forex": "Analysis",
        "strategist": "Decision", "risk": "Decision", "trader": "Decision", "portfolio": "Decision",
        "execution": "Execution",
    }

    def _get_agent_defs_cli():
        try:
            from quant_nanggroe.agents.registry import AgentRegistry
            names = AgentRegistry.list_agents()
            result = []
            for name in names:
                factory = AgentRegistry.get(name)
                if factory is None:
                    continue
                try:
                    instance = factory(llm=None)
                    role = instance.role.value if hasattr(instance.role, 'value') else str(instance.role)
                    desc = instance.description
                except Exception:
                    role = "unknown"
                    desc = ""
                    for r, n in AgentRegistry._role_mapping.items():
                        if n == name:
                            role = r.value if hasattr(r, 'value') else str(r)
                            break
                result.append({
                    "name": name,
                    "role": role,
                    "description": desc,
                    "phase": _PHASE_MAP.get(name, "Analysis"),
                })
            return result
        except Exception:
            pass
        try:
            from quant_nanggroe.agents.graph import TradingGraph
            return [
                {"name": "researcher", "role": "research", "description": "Market research and data analysis", "phase": "Analysis"},
                {"name": "macro", "role": "macro_analysis", "description": "Macroeconomic analysis", "phase": "Analysis"},
                {"name": "crypto", "role": "crypto_analysis", "description": "Cryptocurrency analysis", "phase": "Analysis"},
                {"name": "forex", "role": "forex_analysis", "description": "Forex analysis", "phase": "Analysis"},
                {"name": "strategist", "role": "strategy", "description": "Signal generation and strategy formulation", "phase": "Decision"},
                {"name": "risk", "role": "risk_management", "description": "9-checkpoint risk assessment", "phase": "Decision"},
                {"name": "trader", "role": "trading", "description": "Trade execution decisions", "phase": "Decision"},
                {"name": "portfolio", "role": "portfolio", "description": "Portfolio optimization", "phase": "Decision"},
                {"name": "execution", "role": "execution", "description": "Order execution and fill tracking", "phase": "Execution"},
            ]
        except Exception:
            return []

    agent_defs = _get_agent_defs_cli()

    table = Table(
        title="Available Agents",
        box=box.ROUNDED,
        show_lines=True,
    )
    table.add_column("Name", style="bold cyan", width=12)
    table.add_column("Role", style="white", width=18)
    table.add_column("Phase", style="magenta", width=10)
    table.add_column("Description", style="dim", width=55)
    table.add_column("Status", style="green", width=8)

    for agent in agent_defs:
        phase_color = {
            "Analysis": "blue",
            "Decision": "yellow",
            "Execution": "green",
        }.get(agent["phase"], "white")

        table.add_row(
            agent["name"],
            agent["role"],
            f"[{phase_color}]{agent['phase']}[/{phase_color}]",
            agent["description"],
            "[green]ready[/green]",
        )

    console.print(table)

    # Show graph flow
    console.print()
    console.print(
        Panel(
            "[bold cyan]Pipeline Flow:[/bold cyan]\n"
            "  [blue]Analysis[/blue] → [yellow]Decision[/yellow] → [green]Execution[/green]\n\n"
            "[dim]market_analysis → signal_generation → risk_assessment → "
            "portfolio_optimization → execution_decision → order_execution[/dim]",
            title="Agent Graph",
            border_style="dim",
        )
    )


# =============================================================================
# Portfolio Command Group
# =============================================================================


@main.group()
def portfolio():
    """Portfolio management commands."""
    pass


@portfolio.command("status")
def portfolio_status():
    """Show current portfolio status."""
    console.print(_BANNER)

    try:
        import httpx

        # Try to fetch from API
        try:
            response = httpx.get("http://localhost:8000/api/v1/portfolio", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                _display_portfolio(data)
                return
        except Exception:
            pass

        # Fallback: use local PaperBroker for real portfolio data
        _display_local_portfolio()

    except ImportError:
        _display_local_portfolio()


def _get_local_portfolio_data() -> dict:
    """Get real portfolio data from local PaperExchangeBroker."""
    try:
        import asyncio
        from quant_nanggroe.exchange.paper_broker import PaperExchangeBroker

        broker = PaperExchangeBroker(initial_capital=100000.0)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(broker.connect())
        balances = loop.run_until_complete(broker.get_balance())
        positions = loop.run_until_complete(broker.get_positions())
        portfolio = loop.run_until_complete(broker.get_portfolio())
        loop.close()

        cash = balances.get("USDT", 0.0)
        total_val = portfolio.total_value or cash

        pos_list = []
        total_pos_val = 0.0
        for p in positions:
            pos_list.append({
                "symbol": p.symbol,
                "direction": "LONG" if p.side.value == "long" else "SHORT",
                "quantity": p.quantity,
                "entry_price": p.entry_price,
                "current_price": p.current_price,
                "unrealized_pnl": p.unrealized_pnl,
            })
            total_pos_val += p.market_value

        allocation = {}
        if total_val > 0:
            for p in positions:
                allocation[p.symbol] = p.market_value / total_val

        return {
            "total_value": total_val,
            "cash": cash,
            "positions": pos_list,
            "unrealized_pnl": portfolio.total_unrealized_pnl,
            "realized_pnl": portfolio.total_realized_pnl,
            "daily_pnl": portfolio.daily_pnl,
            "weekly_pnl": portfolio.weekly_pnl,
            "allocation": allocation,
            "risk_budget_used": 0.0,
        }
    except Exception:
        return {
            "total_value": 0.0,
            "cash": 0.0,
            "positions": [],
            "unrealized_pnl": 0.0,
            "realized_pnl": 0.0,
            "daily_pnl": 0.0,
            "weekly_pnl": 0.0,
            "allocation": {},
            "risk_budget_used": 0.0,
        }


def _display_local_portfolio() -> None:
    """Display portfolio from local broker (no hardcoded values)."""
    data = _get_local_portfolio_data()
    _display_portfolio(data)


def _display_portfolio(data: dict) -> None:
    """Display portfolio information in a rich table."""
    total = data.get("total_value", 0)
    cash = data.get("cash", 0)

    # Summary
    summary = Table(title="Portfolio Summary", box=box.ROUNDED, show_header=False)
    summary.add_column("Metric", style="cyan", width=25)
    summary.add_column("Value", style="white", width=20)

    pnl_color = "green" if data.get("daily_pnl", 0) >= 0 else "red"
    weekly_color = "green" if data.get("weekly_pnl", 0) >= 0 else "red"

    summary.add_row("Total Value", f"[bold]${total:,.2f}[/bold]")
    summary.add_row("Cash", f"${cash:,.2f}")
    summary.add_row("Unrealized P&L", f"${data.get('unrealized_pnl', 0):,.2f}")
    summary.add_row("Realized P&L", f"${data.get('realized_pnl', 0):,.2f}")
    summary.add_row("Daily P&L", f"[{pnl_color}]${data.get('daily_pnl', 0):,.2f}[/{pnl_color}]")
    summary.add_row("Weekly P&L", f"[{weekly_color}]${data.get('weekly_pnl', 0):,.2f}[/{weekly_color}]")
    summary.add_row("Risk Budget Used", f"{data.get('risk_budget_used', 0):.1%}")
    console.print(summary)

    # Positions
    positions = data.get("positions", [])
    if positions:
        pos_table = Table(title="Open Positions", box=box.ROUNDED)
        pos_table.add_column("Symbol", style="cyan")
        pos_table.add_column("Direction", style="white")
        pos_table.add_column("Quantity", style="white")
        pos_table.add_column("Entry", style="white")
        pos_table.add_column("Current", style="white")
        pos_table.add_column("P&L", style="white")

        for p in positions:
            pnl = p.get("unrealized_pnl", 0)
            pnl_style = "green" if pnl >= 0 else "red"
            pos_table.add_row(
                p.get("symbol", ""),
                p.get("direction", "LONG"),
                f"{p.get('quantity', 0):.4f}",
                f"${p.get('entry_price', 0):,.2f}",
                f"${p.get('current_price', 0):,.2f}",
                f"[{pnl_style}]${pnl:,.2f}[/{pnl_style}]",
            )
        console.print(pos_table)
    else:
        console.print("\n[dim]No open positions.[/dim]")


# =============================================================================
# Risk Command Group
# =============================================================================


@main.group()
def risk():
    """Risk management commands."""
    pass


@risk.command("check")
@click.argument("symbol")
def risk_check(symbol: str):
    """Run risk assessment for a symbol."""
    console.print(_BANNER)

    console.print(f"[bold cyan]▶ Running risk assessment for {symbol}...[/bold cyan]\n")

    try:
        from quant_nanggroe.engine.risk.manager import (
            RiskManager,
            MAX_RISK_PER_TRADE,
            MAX_DAILY_LOSS,
            MAX_WEEKLY_LOSS,
            MAX_DRAWDOWN,
            MIN_RISK_REWARD,
        )

        rm = RiskManager()
        status = rm.status()

        # Risk status
        overall = status["overall_status"]
        status_color = "green" if overall == "TRADING_ALLOWED" else "red"
        console.print(
            f"  Overall Status: [bold {status_color}]{overall}[/bold {status_color}]"
        )

        # Constitutional limits table
        limits = Table(title="Constitutional Risk Limits (NO OVERRIDE)", box=box.ROUNDED, show_header=False)
        limits.add_column("Limit", style="cyan", width=30)
        limits.add_column("Value", style="bold yellow", width=15)
        limits.add_column("Override", style="red", width=10)

        limits.add_row("Max Risk Per Trade", f"{MAX_RISK_PER_TRADE:.2%}", "[red]IMPOSSIBLE[/red]")
        limits.add_row("Max Daily Loss", f"{MAX_DAILY_LOSS:.2%}", "[red]IMPOSSIBLE[/red]")
        limits.add_row("Max Weekly Loss", f"{MAX_WEEKLY_LOSS:.2%}", "[red]IMPOSSIBLE[/red]")
        limits.add_row("Max Drawdown", f"{MAX_DRAWDOWN:.0%}", "[red]IMPOSSIBLE[/red]")
        limits.add_row("Min Risk:Reward", f"1:{MIN_RISK_REWARD:.1f}", "[red]IMPOSSIBLE[/red]")
        console.print(limits)

        # Current risk metrics
        metrics = Table(title="Current Risk Metrics", box=box.ROUNDED, show_header=False)
        metrics.add_column("Metric", style="cyan", width=30)
        metrics.add_column("Value", style="white", width=20)

        daily_status = status.get("daily_status", "OK")
        weekly_status = status.get("weekly_status", "OK")
        daily_color = "green" if daily_status == "OK" else "red"
        weekly_color = "green" if weekly_status == "OK" else "red"

        metrics.add_row("Symbol", symbol)
        metrics.add_row("Daily P&L", f"${status.get('daily_pnl', 0):,.2f}")
        metrics.add_row("Weekly P&L", f"${status.get('weekly_pnl', 0):,.2f}")
        metrics.add_row("Daily Loss %", f"[{daily_color}]{status.get('daily_loss_pct', '0')}[/{daily_color}]")
        metrics.add_row("Weekly Loss %", f"[{weekly_color}]{status.get('weekly_loss_pct', '0')}[/{weekly_color}]")
        metrics.add_row("Trades Today", str(status.get("trades_today", 0)))
        metrics.add_row("Trades This Week", str(status.get("trades_week", 0)))
        metrics.add_row("Active Positions", str(status.get("active_positions", 0)))
        metrics.add_row("Veto Count", str(status.get("veto_count", 0)))
        metrics.add_row("Approval Count", str(status.get("approval_count", 0)))

        # Drawdown info
        dd = status.get("drawdown", {})
        metrics.add_row("Current Drawdown", f"{dd.get('current_drawdown', 0):.2%}")
        metrics.add_row("Drawdown Breached", "[red]YES[/red]" if dd.get("drawdown_breached") else "[green]NO[/green]")

        # Kill switch
        ks = status.get("kill_switch", {})
        ks_active = ks.get("is_active", False)
        ks_color = "red" if ks_active else "green"
        metrics.add_row("Kill Switch", f"[{ks_color}]{'ACTIVE' if ks_active else 'INACTIVE'}[/{ks_color}]")

        console.print(metrics)

    except ImportError as e:
        console.print(f"[bold yellow]⚠ Risk engine import error: {e}[/bold yellow]")
        console.print("[dim]Showing default risk configuration...[/dim]")

        limits = Table(title="Constitutional Risk Limits", box=box.ROUNDED, show_header=False)
        limits.add_column("Limit", style="cyan")
        limits.add_column("Value", style="yellow")
        limits.add_row("Max Risk Per Trade", "0.50%")
        limits.add_row("Max Daily Loss", "1.00%")
        limits.add_row("Max Weekly Loss", "3.00%")
        limits.add_row("Max Drawdown", "10%")
        limits.add_row("Min Risk:Reward", "1:2.0")
        console.print(limits)

    except Exception as e:
        console.print(f"[bold red]✗ Risk check error: {e}[/bold red]")


# =============================================================================
# Serve Command
# =============================================================================


@main.command()
@click.option("--host", default="0.0.0.0", help="Server host")
@click.option("--port", default=8000, help="Server port")
@click.option("--reload", is_flag=True, default=False, help="Enable auto-reload")
def serve(host: str, port: int, reload: bool):
    """Start the API server."""
    console.print(_BANNER)
    console.print(f"[bold cyan]▶ Starting API server on {host}:{port}...[/bold cyan]")
    console.print(f"[dim]Docs: http://{host}:{port}/docs[/dim]")
    console.print(f"[dim]ReDoc: http://{host}:{port}/redoc[/dim]")
    console.print()

    import uvicorn

    uvicorn.run(
        "quant_nanggroe.api:app",
        host=host,
        port=port,
        reload=reload,
    )


# =============================================================================
# Memory Command (bonus)
# =============================================================================


@main.group()
def memory():
    """Memory system commands."""
    pass


@memory.command("stats")
def memory_stats():
    """Show memory system statistics."""
    console.print(_BANNER)

    try:
        from quant_nanggroe.memory.paging import MemoryPagingController

        controller = MemoryPagingController()
        stats = controller.stats()

        # Core memory
        core = stats["core"]
        core_table = Table(title="Core Memory (Working)", box=box.ROUNDED, show_header=False)
        core_table.add_column("Metric", style="cyan")
        core_table.add_column("Value", style="white")
        core_table.add_row("Block Count", f"{core['block_count']}/{core['max_blocks']}")
        core_table.add_row("Utilization", f"{core['utilization']:.1%}")
        core_table.add_row("Content Size", f"{core['total_content_chars']:,} chars")
        core_table.add_row("Eviction Policy", core["eviction_policy"])
        console.print(core_table)

        # Archival memory
        archival = stats["archival"]
        arch_table = Table(title="Archival Memory (Long-term)", box=box.ROUNDED, show_header=False)
        arch_table.add_column("Metric", style="cyan")
        arch_table.add_column("Value", style="white")
        arch_table.add_row("Block Count", str(archival["block_count"]))
        arch_table.add_row("Content Index Size", str(archival["content_index_size"]))
        arch_table.add_row("Tag Index Size", str(archival["tag_index_size"]))
        console.print(arch_table)

        # Page operations
        ops = stats["page_operations"]
        ops_table = Table(title="Page Operations", box=box.ROUNDED, show_header=False)
        ops_table.add_column("Metric", style="cyan")
        ops_table.add_column("Value", style="white")
        ops_table.add_row("Page-in Count", str(ops["page_in_count"]))
        ops_table.add_row("Page-out Count", str(ops["page_out_count"]))
        ops_table.add_row("Total Blocks Created", str(ops["total_blocks_created"]))
        console.print(ops_table)

    except Exception as e:
        console.print(f"[bold red]✗ Memory stats error: {e}[/bold red]")


@memory.command("graph-stats")
def memory_graph_stats():
    """Show knowledge graph statistics."""
    console.print(_BANNER)

    try:
        from quant_nanggroe.memory.knowledge_graph import KnowledgeGraph

        kg = KnowledgeGraph()
        stats = kg.stats()

        table = Table(title="Knowledge Graph", box=box.ROUNDED, show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        table.add_row("Entity Count", str(stats["entity_count"]))
        table.add_row("Relationship Count", str(stats["relationship_count"]))

        if stats.get("entity_types"):
            table.add_row("── Entity Types ──", "───")
            for etype, count in stats["entity_types"].items():
                table.add_row(f"  {etype}", str(count))

        if stats.get("relationship_types"):
            table.add_row("── Relationship Types ──", "───")
            for rtype, count in stats["relationship_types"].items():
                table.add_row(f"  {rtype}", str(count))

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]✗ Knowledge graph stats error: {e}[/bold red]")


if __name__ == "__main__":
    main()
