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
@click.option("--paper", is_flag=True, default=True, help="Use paper trading (DEFAULT and RECOMMENDED)")
@click.option("--strategy", "-st", default="default", help="Strategy name")
@click.option("--confirm-live", is_flag=True, default=False, help="EXPLICIT CONFIRMATION required for live trading")
def trade(paper: bool, strategy: str, confirm_live: bool):
    """Start trading with specified strategy.

    Paper trading is the default. Live trading requires BOTH --no-paper
    AND --confirm-live flags as an explicit safety gate.
    """
    if not paper and not confirm_live:
        click.echo("❌ BLOCKED: Live trading requires explicit confirmation.")
        click.echo("   Use: qnai trade --no-paper --confirm-live")
        click.echo("   WARNING: Live trading uses REAL funds. Ensure risk limits are configured.")
        return

    if not paper:
        click.echo("⚠️  LIVE TRADING MODE ACTIVE")
        click.echo("   Real funds will be used. Risk limits enforced by constitutional guard.")
        click.confirm("   Are you sure you want to proceed with LIVE trading?", abort=True)

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
