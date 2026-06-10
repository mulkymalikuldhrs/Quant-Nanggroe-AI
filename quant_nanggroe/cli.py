"""CLI entry point for Quant Nanggroe AI."""

from __future__ import annotations

import click


@click.group()
@click.version_option(version="0.2.0")
def main():
    """Quant Nanggroe AI — Agentic Trading Intelligence OS."""
    pass


@main.command()
@click.option("--symbol", "-s", default="BTC/USDT", help="Trading symbol")
@click.option("--timeframe", "-t", default="1d", help="Timeframe")
def analyze(symbol: str, timeframe: str):
    """Run analysis on a trading symbol."""
    click.echo(f"Analyzing {symbol} on {timeframe} timeframe...")
    click.echo("Analysis complete. Use 'qnai trade' to execute.")


@main.command()
@click.option("--paper", is_flag=True, default=True, help="Use paper trading")
@click.option("--strategy", "-st", default="default", help="Strategy name")
def trade(paper: bool, strategy: str):
    """Start trading with specified strategy."""
    mode = "PAPER" if paper else "LIVE"
    click.echo(f"Starting {mode} trading with strategy: {strategy}")


@main.command()
@click.option("--symbol", "-s", required=True, help="Trading symbol")
@click.option("--start", "-s2", help="Start date (YYYY-MM-DD)")
@click.option("--end", "-e", help="End date (YYYY-MM-DD)")
@click.option("--capital", "-c", default=100000.0, help="Initial capital")
def backtest(symbol: str, start: str, end: str, capital: float):
    """Run backtesting on a symbol."""
    click.echo(f"Backtesting {symbol} from {start} to {end} with ${capital:,.0f}")


@main.command()
def serve():
    """Start the API server."""
    click.echo("Starting Quant Nanggroe AI API server...")
    import uvicorn
    uvicorn.run("quant_nanggroe.api:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
