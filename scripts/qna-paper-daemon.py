#!/usr/bin/env python3
"""qna-paper-daemon.py — persistent paper trading daemon.

Configurable cycle loop: fetch data → generate signals → risk gate →
execute on PaperExchangeBroker → log P&L → repeat.

Usage:
    python3 scripts/qna-paper-daemon.py --help
    python3 scripts/qna-paper-daemon.py --interval 3600 --capital 10000
    python3 scripts/qna-paper-daemon.py --dry-run --interval 1
"""

import argparse
import asyncio
import csv
import json
import logging
import os
import signal
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from quant_nanggroe.exchange.paper_broker import PaperExchangeBroker
from quant_nanggroe.engine.strategy.strategies import create_strategy
from quant_nanggroe.engine.risk.kill_switch import KillSwitch, KillSwitchLevel, KillSwitchTrigger
from quant_nanggroe.engine.risk.strategy_auto_disable import AutoDisableManager
from quant_nanggroe.engine.risk.correlation import StrategyCorrelationMonitor
from quant_nanggroe.types.orders import OrderSide, OrderType
from quant_nanggroe.types.market import OHLCV

logger = logging.getLogger("qna-paper-daemon")

DEFAULT_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT"]
DEFAULT_STRATEGIES = ["RegimeBased"]
BASE_PRICES = {"BTC/USDT": 67000.0, "ETH/USDT": 3400.0, "SOL/USDT": 145.0, "XRP/USDT": 0.62}
VOLATILITIES = {"BTC/USDT": 0.025, "ETH/USDT": 0.03, "SOL/USDT": 0.045, "XRP/USDT": 0.04}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="qna-paper-daemon",
        description="Persistent paper trading daemon for Quant Nanggroe AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/qna-paper-daemon.py
  python3 scripts/qna-paper-daemon.py --interval 3600 --capital 10000
  python3 scripts/qna-paper-daemon.py --dry-run --interval 1
  python3 scripts/qna-paper-daemon.py --symbols BTC/USDT ETH/USDT --strategies Momentum
  python3 scripts/qna-paper-daemon.py --state-dir /tmp/paper_state --verbose
        """,
    )
    parser.add_argument("--symbols", nargs="+", default=DEFAULT_SYMBOLS,
                        help=f"Symbols to trade (default: {' '.join(DEFAULT_SYMBOLS)})")
    parser.add_argument("--interval", type=int, default=3600,
                        help="Cycle interval in seconds (default: 3600)")
    parser.add_argument("--strategies", nargs="+", default=DEFAULT_STRATEGIES,
                        help=f"Strategies to run (default: {' '.join(DEFAULT_STRATEGIES)})")
    parser.add_argument("--capital", type=float, default=10000.0,
                        help="Initial capital in USDT (default: 10000)")
    parser.add_argument("--state-dir", default=None,
                        help="Directory for state/CSV files (default: ./paper_state)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simulate one cycle without executing or saving trades")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable debug logging")
    parser.add_argument("--vol-target", type=float, default=0.25,
                        help="Target volatility for Kelly position sizing (default: 0.25)")
    parser.add_argument("--max-leverage", type=float, default=1.0,
                        help="Maximum leverage (stub, default: 1.0)")
    parser.add_argument("--live-data", action="store_true",
                        help="Use cached OHLCV data instead of synthetic (default: False)")
    return parser.parse_args()


def generate_ohlcv(symbol: str, lookback: int = 300) -> list[OHLCV]:
    base = BASE_PRICES.get(symbol, 100.0)
    vol = VOLATILITIES.get(symbol, 0.03)
    now = datetime.now(timezone.utc)
    prices = [base]
    for _ in range(lookback - 1):
        ret = np.random.normal(0, vol)
        prices.append(max(prices[-1] * (1 + ret), base * 0.1))
    candles = []
    for i in range(lookback):
        ts = now - timedelta(hours=lookback - i)
        c = prices[i]
        o = prices[i - 1] if i > 0 else c * (1 + np.random.normal(0, vol * 0.3))
        h = max(c, o) * (1 + abs(np.random.normal(0, vol * 0.3)))
        l = min(c, o) * (1 - abs(np.random.normal(0, vol * 0.3)))
        v = max(0, np.random.normal(1000, 500))
        candles.append(OHLCV(
            symbol=symbol, timestamp=ts,
            open=round(float(o), 2), high=round(float(h), 2),
            low=round(float(l), 2), close=round(float(c), 2),
            volume=round(float(v), 2),
        ))
    return candles


def load_cached_ohlcv(symbol: str, days: int = 500) -> pd.DataFrame | None:
    base = symbol.split("/")[0]
    path = Path(_project_root) / "data" / "cached_ohlcv" / f"{base}.csv"
    if not path.exists():
        logger.warning("Cache miss for %s — falling back to synthetic", symbol)
        return None
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.iloc[-days:]
    df.index = pd.to_datetime(df["date"])
    return df


def ohlcv_to_df(candles: list[OHLCV]) -> pd.DataFrame:
    records = [{"open": c.open, "high": c.high, "low": c.low,
                "close": c.close, "volume": c.volume} for c in candles]
    return pd.DataFrame(records)


def load_state(path: Path) -> dict:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def save_state(path: Path, state: dict) -> None:
    with open(path, "w") as f:
        json.dump(state, f, indent=2, default=str)


def log_pnl_csv(path: Path, row: dict) -> None:
    exists = path.exists()
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not exists:
            w.writeheader()
        w.writerow(row)


async def run_cycle(
    broker: PaperExchangeBroker,
    strategies: list[str],
    symbols: list[str],
    kill_switch: KillSwitch,
    auto_disable: AutoDisableManager,
    state: dict,
    log_path: Path,
    state_path: Path,
    dry_run: bool,
    live_data: bool,
    vol_target: float,
    correlation_monitor: Optional[StrategyCorrelationMonitor] = None,
) -> dict:
    logger.info("=== Cycle %d ===", state["cycle_count"] + 1)
    total_signal_count = 0

    # Data freshness check (live-data mode only)
    if live_data:
        newest_ts = None
        for symbol in symbols:
            base = symbol.split("/")[0]
            path = Path(_project_root) / "data" / "cached_ohlcv" / f"{base}.csv"
            if path.exists():
                mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
                if newest_ts is None or mtime > newest_ts:
                    newest_ts = mtime
        if newest_ts is not None and (datetime.now(timezone.utc) - newest_ts) > timedelta(hours=48):
            kill_switch.activate(
                level=KillSwitchLevel.LEVEL_1,
                reason="data_stale",
                trigger=KillSwitchTrigger.DATA_STALE,
                auto_activated=True,
            )
            logger.critical("Kill switch activated: cached data >48h stale (file mtime=%s)", newest_ts.isoformat())
            return {}

    for symbol in symbols:
        if live_data:
            df = load_cached_ohlcv(symbol)
            if df is None:
                candles = generate_ohlcv(symbol)
                for c in candles:
                    broker.add_ohlcv(symbol, c)
                df = ohlcv_to_df(candles)
            else:
                for idx, row in df.iterrows():
                    broker.add_ohlcv(symbol, OHLCV(
                        symbol=symbol, timestamp=idx.to_pydatetime(),
                        open=row["open"], high=row["high"],
                        low=row["low"], close=row["close"],
                        volume=row["volume"],
                    ))
        else:
            candles = generate_ohlcv(symbol)
            for c in candles:
                broker.add_ohlcv(symbol, c)
            df = ohlcv_to_df(candles)
        current_price = broker.get_price(symbol)
        logger.info("  %s: price=%.2f candles=%d", symbol, current_price, len(df))

        for strat_name in strategies:
            try:
                if auto_disable.is_disabled(strat_name):
                    logger.debug("  %s on %s: skipped by AutoDisableManager", strat_name, symbol)
                    continue
                strat = create_strategy(strat_name, {"symbol": symbol})
                sig = strat.generate_signal(df)
            except Exception as e:
                logger.debug("  %s on %s skipped: %s", strat_name, symbol, e)
                continue

            if sig is None or sig.signal_type.value in ("hold", "exit_all", "close_long", "close_short"):
                logger.debug("  %s on %s: %s (no action)", strat_name, symbol,
                             sig.signal_type.value if sig else "none")
                continue

            # Feed returns to AutoDisableManager and correlation monitor
            daily_returns = df.close.pct_change().dropna()
            if len(daily_returns) > 0:
                auto_disable.update(strat_name, daily_returns)
                if correlation_monitor is not None:
                    correlation_monitor.update(strat_name, daily_returns.values)

            if not kill_switch.can_trade():
                logger.warning("  Kill switch active — skipping trades")
                continue

            total_signal_count += 1
            side = OrderSide.BUY if sig.signal_type.value == "buy" else OrderSide.SELL

            # Kelly fraction with volatility scaling
            vol = float(df.close.pct_change().std() * np.sqrt(252))
            fraction = min(sig.confidence * 0.25, 0.25)
            denominator = vol * current_price if vol > 0 else current_price
            qty = round(state["initial_capital"] * fraction / denominator, 6)

            if dry_run:
                logger.info("  [DRY-RUN] %s %s %s qty=%s conf=%.2f vol=%.4f kelly=%.4f",
                            strat_name, symbol, side.value, qty, sig.confidence, vol, fraction)
                continue

            try:
                order = await broker.place_order(
                    symbol=symbol, side=side, order_type=OrderType.MARKET,
                    quantity=qty, strategy_name=strat_name,
                )
                logger.info("  %s %s: %s qty=%s fill=%.2f status=%s",
                            strat_name, symbol, side.value, qty,
                            order.average_fill_price or 0.0, order.status.value)
            except Exception as e:
                logger.error("  Order failed %s %s: %s", strat_name, symbol, e)

    if correlation_monitor is not None:
        corr_status = correlation_monitor.check_and_act()
        if corr_status.get("avg_correlation") is not None:
            logger.info("  Correlation: avg=%.3f strategies=%d fired=%s",
                        corr_status["avg_correlation"], corr_status["num_strategies"],
                        corr_status["kill_switch_fired"])

    portfolio = await broker.get_portfolio()
    state["cycle_count"] += 1
    state["total_pnl"] = round(portfolio.total_realized_pnl + portfolio.total_unrealized_pnl, 2)
    state["peak_capital"] = max(state["peak_capital"], portfolio.total_value)

    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cycle": state["cycle_count"],
        "signals": total_signal_count,
        "cash": round(broker.cash, 2),
        "total_value": round(portfolio.total_value, 2),
        "unrealized_pnl": round(portfolio.total_unrealized_pnl, 2),
        "realized_pnl": round(portfolio.total_realized_pnl, 2),
        "total_pnl": state["total_pnl"],
        "positions": len(portfolio.positions),
        "drawdown_pct": round(
            ((portfolio.total_value - state["peak_capital"]) / state["peak_capital"]) * 100
            if state["peak_capital"] > 0 else 0.0, 4,
        ),
    }

    if not dry_run:
        log_pnl_csv(log_path, row)
        save_state(state_path, state)

    logger.info("  PnL: total=%.2f cash=%.2f value=%.2f positions=%d",
                state["total_pnl"], broker.cash, portfolio.total_value,
                len(portfolio.positions))
    return row


async def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    state_dir = Path(args.state_dir or "paper_state")
    state_dir.mkdir(parents=True, exist_ok=True)
    state_path = state_dir / "state.json"
    log_path = state_dir / "pnl.csv"

    state = load_state(state_path)
    state.setdefault("initial_capital", args.capital)
    state.setdefault("peak_capital", args.capital)
    state.setdefault("cycle_count", 0)
    state.setdefault("total_pnl", 0.0)

    broker = PaperExchangeBroker(initial_capital=args.capital)
    await broker.connect()
    kill_switch = KillSwitch()
    auto_disable = AutoDisableManager(
        kill_switch=kill_switch,
        sharpe_window=30,
        threshold=0.3,
        state_path=str(state_dir / "auto_disable_state.json"),
        paper_mode=not args.live_data,
    )

    correlation_monitor = StrategyCorrelationMonitor(
        kill_switch=kill_switch,
        state_dir=str(state_dir),
        paper_mode=not args.live_data,
    )

    stop_event = asyncio.Event()
    def _shutdown():
        logger.info("Shutdown signal received — stopping after current cycle")
        stop_event.set()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            asyncio.get_running_loop().add_signal_handler(sig, _shutdown)
        except NotImplementedError:
            pass

    logger.info(
        "Daemon started: capital=%.2f interval=%ds symbols=%s strategies=%s state=%s live_data=%s vol_target=%.2f",
        args.capital, args.interval, args.symbols, args.strategies, state_dir,
        args.live_data, args.vol_target,
    )

    row = {}
    try:
        while not stop_event.is_set():
            row = await run_cycle(
                broker, args.strategies, args.symbols, kill_switch, auto_disable,
                state, log_path, state_path, args.dry_run, args.live_data, args.vol_target,
                correlation_monitor=correlation_monitor,
            )
            if args.dry_run:
                break
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=args.interval)
            except asyncio.TimeoutError:
                pass
    finally:
        await broker.disconnect()
        logger.info("Daemon stopped: %d cycles completed", state["cycle_count"])


if __name__ == "__main__":
    asyncio.run(main())
