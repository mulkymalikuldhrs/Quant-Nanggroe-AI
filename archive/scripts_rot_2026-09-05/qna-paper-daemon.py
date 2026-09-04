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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from quant_nanggroe.agents.compliance.agent import ComplianceAgent

from quant_nanggroe.agents.risk.agent import RiskAgent
from quant_nanggroe.data.warehouse import DataWarehouse
from quant_nanggroe.engine.audit import AuditLogger
from quant_nanggroe.engine.monitor_hub import MonitorHub
from quant_nanggroe.engine.regime.strategy_selector import RegimeStrategySelector
from quant_nanggroe.engine.risk.constants import MAX_DRAWDOWN_PCT
from quant_nanggroe.engine.risk.correlation import StrategyCorrelationMonitor
from quant_nanggroe.engine.risk.drawdown import DrawdownMonitor
from quant_nanggroe.engine.risk.kill_switch import KillSwitch, KillSwitchLevel, KillSwitchTrigger
from quant_nanggroe.engine.risk.strategy_auto_disable import AutoDisableManager
from quant_nanggroe.engine.strategy.strategies import create_strategy, list_strategies
from quant_nanggroe.exchange.paper_broker import PaperExchangeBroker
from quant_nanggroe.types.market import OHLCV
from quant_nanggroe.types.orders import OrderSide, OrderType

logger = logging.getLogger("qna-paper-daemon")

DEFAULT_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT"]
DEFAULT_STRATEGIES = ["RegimeBased"]
BASE_PRICES = {"BTC/USDT": 67000.0, "ETH/USDT": 3400.0, "SOL/USDT": 145.0, "XRP/USDT": 0.62}
VOLATILITIES = {"BTC/USDT": 0.025, "ETH/USDT": 0.03, "SOL/USDT": 0.045, "XRP/USDT": 0.04}

# ponytail: normalize BTCUSDT->BTC/USDT once at intake so BASE_PRICES lookup never
# silently falls back to 100.0 (670x price distortion). One guard, all callers route through.
def _norm_symbol(symbol: str) -> str:
    return symbol.replace("", "").replace("USDT", "/USDT") if "USDT" in symbol and "/" not in symbol else symbol


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
                        help="Fetch live OHLCV from Alpha Vantage API, fall back to cached CSV, then synthetic (default: False)")
    return parser.parse_args()


_SYNTHETIC_WARNING_LOGGED: set[str] = set()


def generate_ohlcv(symbol: str, lookback: int = 300) -> list[OHLCV]:
    if symbol not in _SYNTHETIC_WARNING_LOGGED:
        logger.warning(
            "⚠️  SYNTHETIC DATA for %s — PnL from synthetic candles is MEANINGLESS. "
            "Use --live-data with a valid QNAI_ALPHA_VANTAGE_API_KEY for real prices.",
            symbol,
        )
        _SYNTHETIC_WARNING_LOGGED.add(symbol)
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


def fetch_alpha_vantage_ohlcv(symbol: str, days: int = 500) -> pd.DataFrame | None:
    """Fetch OHLCV from Alpha Vantage API. Requires QNAI_ALPHA_VANTAGE_API_KEY in env."""
    import requests
    key = os.environ.get("QNAI_ALPHA_VANTAGE_API_KEY")
    if not key:
        logger.warning("QNAI_ALPHA_VANTAGE_API_KEY not set — skipping Alpha Vantage fetch for %s", symbol)
        return None
    base = symbol.split("/")[0]
    url = f"https://www.alphavantage.co/query?function=DIGITAL_CURRENCY_DAILY&symbol={base}&market=USD&apikey={key}"
    try:
        resp = requests.get(url, timeout=15).json()
        series = resp.get("Time Series (Digital Currency Daily)", {})
        if not series:
            logger.warning("Alpha Vantage returned no data for %s", symbol)
            return None
        records = []
        for date, vals in sorted(series.items()):
            records.append({
                "date": date,
                "open": float(vals["1. open"]),
                "high": float(vals["2. high"]),
                "low": float(vals["3. low"]),
                "close": float(vals["4. close"]),
                "volume": float(vals["5. volume"]),
            })
        df = pd.DataFrame(records[-days:])
        df.index = pd.to_datetime(df["date"])
        cache_path = Path(_project_root) / "data" / "cached_ohlcv" / f"{base}.csv"
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(cache_path, index=False)
        logger.info("Alpha Vantage fetch succeeded for %s: %d bars", symbol, len(df))
        return df
    except Exception as e:
        logger.warning("Alpha Vantage fetch failed for %s: %s", symbol, e)
        return None


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


def log_attribution_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    exists = path.exists()
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        if not exists:
            w.writeheader()
        w.writerows(rows)


_selector = RegimeStrategySelector()


def _detect_regime_heuristic(df: pd.DataFrame) -> tuple[str, float]:
    close = df["close"].values
    n = len(close)
    if n < 63:
        return "sideways", 0.4
    sma_21 = np.mean(close[-21:]) if n >= 21 else np.mean(close)
    sma_63 = np.mean(close[-63:]) if n >= 63 else np.mean(close)
    vol_21 = np.std(close[-21:] / np.mean(close[-21:])) if n >= 21 else 0.02
    last_close = close[-1]
    if last_close > sma_63 and vol_21 < 0.015:
        return "bull_trend", min(0.8, 0.5 + (last_close - sma_63) / sma_63 * 5)
    elif last_close < sma_63 and vol_21 > 0.01:
        return "bear_trend", min(0.8, 0.5 + vol_21 * 10)
    elif vol_21 > 0.025:
        return "high_volatility", min(0.8, 0.5 + vol_21 * 8)
    else:
        return "sideways", 0.5


def _select_strategies_for_regime(df: pd.DataFrame, user_strategies: list[str]) -> tuple[list[dict], float, str, float]:
    all_qna = list_strategies()
    regime, confidence = _detect_regime_heuristic(df)
    rm = _selector.select_strategies(regime, confidence)
    multiplier = rm.risk_multiplier
    selected_names = [s.name for s in rm.active_strategies if s.name in all_qna]
    if user_strategies:
        selected_names = [n for n in selected_names if n in user_strategies]
    logger.info("Regime: %s (conf=%.2f) risk_mult=%.2f strategies=%s",
                regime, confidence, multiplier, selected_names)
    result = []
    regime_map = {s.name: s for s in rm.active_strategies}
    for name in selected_names:
        sc = regime_map.get(name)
        if sc:
            result.append({
                "name": name,
                "params": dict(sc.params),
                "kelly_fraction": min(sc.Kelly.get("fraction", 0.25) * multiplier, 0.25),
                "weight": sc.weight,
            })
    if not result:
        fallback = user_strategies or all_qna
        for s in fallback:
            result.append({"name": s, "params": {}, "kelly_fraction": 0.25 * multiplier, "weight": 1.0})

    return result, multiplier, regime, confidence


def _compute_atr(df: pd.DataFrame, period: int = 14) -> float:
    close, high, low = df["close"].values, df["high"].values, df["low"].values
    n = len(close)
    if n < period + 1:
        return float(np.std(close[-min(n, 20):]) * 0.5)
    tr = np.zeros(n)
    for i in range(1, n):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
    return float(np.mean(tr[-period:]))


def _apply_toggle_config(cli_strategies: list[str], config_path: Path) -> list[str]:
    if not config_path.exists():
        return cli_strategies
    try:
        with open(config_path) as f:
            config = json.load(f)
        disabled = set(config.get("disabled", []))
        result = [s for s in cli_strategies if s not in disabled]
        return result if result else cli_strategies[:1]
    except Exception:
        return cli_strategies


async def _check_trailing_stops(
    broker: PaperExchangeBroker,
    trailing_stops: dict[str, dict],
    current_prices: dict[str, float],
    state_path: Path,
) -> None:
    for symbol, stop_info in list(trailing_stops.items()):
        entry_price = stop_info["entry_price"]
        stop_price = stop_info["stop_price"]
        highest = stop_info.get("highest_since_entry", entry_price)
        atr_mult = stop_info.get("atr_multiplier", 2.5)
        current_price = current_prices.get(symbol)
        if current_price is None:
            continue
        if current_price > highest:
            highest = current_price
            stop_info["highest_since_entry"] = highest
            stop_info["stop_price"] = highest - atr_mult * stop_info["atr_value"]
        if current_price <= stop_info["stop_price"]:
            side = OrderSide.SELL if stop_info["side"] == "long" else OrderSide.BUY
            try:
                qty = abs(broker.get_position(symbol))
                if qty > 0:
                    await broker.place_order(
                        symbol=symbol, side=side, order_type=OrderType.MARKET,
                        quantity=qty, strategy_name="trailing_stop",
                    )
                    logger.info("Trailing stop triggered: %s at %.2f (stop=%.2f)",
                                symbol, current_price, stop_info["stop_price"])
            except Exception as e:
                logger.error("Trailing stop failed %s: %s", symbol, e)
            del trailing_stops[symbol]
    save_state(state_path.parent / "trailing_stops.json", trailing_stops)


async def run_cycle(
    broker: PaperExchangeBroker,
    strategies: list[str],
    symbols: list[str],
    kill_switch: KillSwitch,
    auto_disable: AutoDisableManager,
    state: dict,
    log_path: Path,
    attribution_path: Path,
    state_path: Path,
    dry_run: bool,
    live_data: bool,
    vol_target: float,
    warehouse: Optional[DataWarehouse] = None,
    correlation_monitor: Optional[StrategyCorrelationMonitor] = None,
    drawdown_monitor: Optional[DrawdownMonitor] = None,
    audit: Optional[AuditLogger] = None,
    monitor: Optional[MonitorHub] = None,
    risk_agent: Optional[RiskAgent] = None,
    compliance_agent: Optional[ComplianceAgent] = None,
) -> dict:
    logger.info("=== Cycle %d ===", state["cycle_count"] + 1)
    symbols = [_norm_symbol(s) for s in symbols]  # ponytail: fix symbol format once
    total_signal_count = 0
    regime_strategies: list[dict] | None = None
    regime_multiplier: float = 1.0

    trailing_stops_path = state_path.parent / "trailing_stops.json"
    trailing_stops: dict = load_state(trailing_stops_path) or {}
    current_prices: dict[str, float] = {}
    await _check_trailing_stops(broker, trailing_stops, current_prices, state_path)
    if monitor:
        monitor.record_cycle()

    # Log cache staleness warning (API tried first; kill switch only if both fail)
    if live_data:
        stale_symbols = []
        for symbol in symbols:
            base = symbol.split("/")[0]
            path = Path(_project_root) / "data" / "cached_ohlcv" / f"{base}.csv"
            if path.exists():
                mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
                if (datetime.now(timezone.utc) - mtime) > timedelta(hours=48):
                    stale_symbols.append(symbol)
        if stale_symbols:
            logger.warning("Cached data stale >48h for %s — will try API first", stale_symbols)

    for idx, symbol in enumerate(symbols):
        if live_data:
            df = fetch_alpha_vantage_ohlcv(symbol)
            if df is None:
                df = load_cached_ohlcv(symbol)
            if df is None:
                candles = generate_ohlcv(symbol)
                for c in candles:
                    broker.add_ohlcv(symbol, c)
                df = ohlcv_to_df(candles)
            else:
                for _i, row in df.iterrows():
                    broker.add_ohlcv(symbol, OHLCV(
                        symbol=symbol, timestamp=_i.to_pydatetime(),
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
        current_prices[symbol] = current_price
        logger.info("  %s: price=%.2f candles=%d", symbol, current_price, len(df))

        if idx == 0:
            regime_strategies, regime_multiplier, regime_name, regime_conf = _select_strategies_for_regime(df, strategies)
            state["regime"] = regime_strategies[0]["name"] if regime_strategies else "unknown"
            state["regime_name"] = regime_name if regime_strategies else "unknown"

            regime_state_path = state_path.parent / "regime_state.json"
            detected_at = datetime.now(timezone.utc).isoformat()
            regime_state = {
                "regime": regime_name,
                "confidence": regime_conf,
                "risk_multiplier": regime_multiplier,
                "selected_strategies": [s["name"] for s in regime_strategies],
                "detected_at": detected_at,
            }
            try:
                with open(regime_state_path, "w") as f:
                    json.dump(regime_state, f, indent=2)
            except Exception as e:
                logger.debug("Regime state not saved: %s", e)
            if warehouse and not dry_run:
                warehouse.write_regime({
                    "detected_at": detected_at,
                    "cycle_number": state.get("cycle_count", 0),
                    "regime": regime_name,
                    "confidence": regime_conf,
                    "risk_multiplier": regime_multiplier,
                })

        for strat_cfg in (regime_strategies or [{"name": s, "params": {}, "kelly_fraction": 0.25} for s in strategies]):
            strat_name = strat_cfg["name"]
            try:
                if auto_disable.is_disabled(strat_name):
                    logger.debug("  %s on %s: skipped by AutoDisableManager", strat_name, symbol)
                    continue
                strat_params = dict(strat_cfg.get("params", {}))
                strat_params["symbol"] = symbol
                strat = create_strategy(strat_name, strat_params)
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

            vol = float(df.close.pct_change().std() * np.sqrt(252))
            kelly_frac = strat_cfg.get("kelly_fraction", 0.25)
            fraction = min(sig.confidence * kelly_frac, kelly_frac)
            denominator = vol * current_price if vol > 0 else current_price
            qty = round(state["initial_capital"] * fraction / denominator, 6)

            if dry_run:
                logger.info("  [DRY-RUN] %s %s %s qty=%s conf=%.2f vol=%.4f kelly=%.4f",
                            strat_name, symbol, side.value, qty, sig.confidence, vol, fraction)
                continue

            # Agent gate: Compliance check
            if compliance_agent is not None:
                c_verdict = compliance_agent.check_trade(
                    symbol=symbol, side=side.value, qty=qty,
                    strategy=strat_name, equity=state.get("initial_capital", 10000.0),
                    price=current_price,
                    positions={p.symbol: {"quantity": p.quantity, "current_price": p.current_price}
                               for p in (await broker.get_positions())},
                )
                if c_verdict.status == "REJECT":
                    logger.warning("  Compliance REJECTED %s %s: %s", strat_name, symbol, c_verdict.reason)
                    if audit:
                        audit.log("RISK", "WARNING", f"Compliance rejected {strat_name} {symbol}", {
                            "reason": c_verdict.reason, "check": c_verdict.check_name, "qty": qty,
                        })
                    continue

            # Agent gate: Risk check
            if risk_agent is not None:
                portfolio = await broker.get_portfolio()
                positions_map = {p.symbol: p.quantity for p in (await broker.get_positions())}
                r_verdict = risk_agent.check_trade(
                    symbol=symbol, side=side.value, qty=qty, price=current_price,
                    strategy=strat_name, portfolio_value=portfolio.total_value,
                    current_positions=positions_map,
                )
                if r_verdict.status == "REJECTED":
                    logger.warning("  Risk REJECTED %s %s: %s", strat_name, symbol, r_verdict.reason)
                    if audit:
                        audit.log("RISK", "WARNING", f"Risk rejected {strat_name} {symbol}", {
                            "reason": r_verdict.reason, "check": r_verdict.check_name,
                        })
                    continue

            try:
                order = await broker.place_order(
                    symbol=symbol, side=side, order_type=OrderType.MARKET,
                    quantity=qty, strategy_name=strat_name,
                )
                logger.info("  %s %s: %s qty=%s fill=%.2f status=%s",
                            strat_name, symbol, side.value, qty,
                            order.average_fill_price or 0.0, order.status.value)
                if audit:
                    audit.log("EXECUTION", "INFO", f"{strat_name} {symbol} {side.value}", {
                        "qty": qty, "fill": order.average_fill_price,
                        "status": order.status.value, "regime": state.get("regime"),
                    })
                state.setdefault("regime_at_entry", {})
                state["regime_at_entry"][symbol] = state.get("regime_name", "unknown")
                if monitor:
                    monitor.record_signal()
                fill_price = order.average_fill_price or current_price
                if symbol not in trailing_stops:
                    atr_val = _compute_atr(df)
                    stop_dist = 2.5 * atr_val
                    stop_px = fill_price - stop_dist if side == OrderSide.BUY else fill_price + stop_dist
                    trailing_stops[symbol] = {
                        "entry_price": fill_price,
                        "stop_price": stop_px,
                        "highest_since_entry": fill_price,
                        "atr_value": atr_val,
                        "atr_multiplier": 2.5,
                        "side": "long" if side == OrderSide.BUY else "short",
                    }
            except Exception as e:
                logger.error("  Order failed %s %s: %s", strat_name, symbol, e)

    if correlation_monitor is not None:
        corr_status = correlation_monitor.check_and_act()
        if corr_status.get("avg_correlation") is not None:
            logger.info("  Correlation: avg=%.3f strategies=%d fired=%s",
                        corr_status["avg_correlation"], corr_status["num_strategies"],
                        corr_status["kill_switch_fired"])

    portfolio = await broker.get_portfolio()
    equity = portfolio.total_value
    positions = await broker.get_positions()
    attribution_rows = []
    state_regime_at_entry = state.get("regime_at_entry", {})
    for pos in positions:
        regime = state_regime_at_entry.get(pos.symbol, "unknown")
        total_pnl = pos.unrealized_pnl + pos.realized_pnl
        row = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cycle": state["cycle_count"],
            "symbol": pos.symbol,
            "strategy": pos.strategy_name or "unknown",
            "unrealized_pnl": round(pos.unrealized_pnl, 2),
            "realized_pnl": round(pos.realized_pnl, 2),
            "total_pnl": round(total_pnl, 2),
            "entry_price": round(pos.entry_price, 2),
            "current_price": round(pos.current_price, 2),
            "position_qty": round(pos.quantity, 6),
            "regime_at_entry": regime,
        }
        attribution_rows.append(row)
    for sym in list(state_regime_at_entry.keys()):
        if sym not in {p.symbol for p in positions}:
            del state_regime_at_entry[sym]
    if not dry_run:
        state["regime_at_entry"] = state_regime_at_entry

    if not dry_run and attribution_rows:
        log_attribution_csv(attribution_path, attribution_rows)

    if warehouse and not dry_run and attribution_rows:
        warehouse.write_attribution(attribution_rows)

    if audit:
        for sym_pnl in attribution_rows:
            audit.log("DECISION", "INFO", f"P&L attribution: {sym_pnl['symbol']}", sym_pnl)

    if monitor:
        for sym_pnl in attribution_rows:
            monitor.record_attribution(sym_pnl)
        current_total = portfolio.total_realized_pnl + portfolio.total_unrealized_pnl
        prev_total = state.get("total_pnl", 0.0)
        monitor.record_pnl(current_total - prev_total)
        corr_val = correlation_monitor.check_and_act().get("avg_correlation") if correlation_monitor else None
        if corr_val is not None:
            monitor.record_correlation(corr_val)
    if drawdown_monitor is not None:
            drawdown_monitor.update(equity)
            if drawdown_monitor.is_breached:
                kill_switch.activate(
                    level=KillSwitchLevel.LEVEL_2,
                    reason=f"Max drawdown breached: {drawdown_monitor.current_drawdown:.2%}",
                    trigger=KillSwitchTrigger.DRAWDOWN_EXCEEDED,
                    auto_activated=True,
                )
                logger.critical("Kill switch triggered: drawdown=%.2f%% exceeds max=%.2f%%",
                                drawdown_monitor.current_drawdown * 100, MAX_DRAWDOWN_PCT)
                if audit:
                    audit.log("RISK", "CRITICAL", "Max drawdown breached", {
                        "drawdown": drawdown_monitor.current_drawdown,
                        "max": MAX_DRAWDOWN_PCT, "equity": equity,
                    })

    # Agent checks after portfolio update
    if compliance_agent is not None and not dry_run:
        positions_dict = {p.symbol: {"quantity": p.quantity, "current_price": p.current_price} for p in positions}
        port_check = compliance_agent.check_portfolio(positions_dict, equity)
        if port_check.get("limit_breaches"):
            for breach in port_check["limit_breaches"]:
                logger.warning("  Compliance breach: %s (%.2f%% > %.2f%%)",
                               breach["type"], breach["exposure_pct"], breach["limit_pct"])
                if audit:
                    audit.log("RISK", "WARNING", f"Compliance breach: {breach['type']}", breach)
        if audit:
            audit.log("RISK", "INFO", "Compliance portfolio check", port_check)

    if risk_agent is not None and not dry_run:
        risk_agent.update_pnl(portfolio.total_realized_pnl, portfolio.total_unrealized_pnl, equity)

    state["cycle_count"] += 1
    state["total_pnl"] = round(portfolio.total_realized_pnl + portfolio.total_unrealized_pnl, 2)
    state["peak_capital"] = max(state["peak_capital"], equity)

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
        save_state(trailing_stops_path, trailing_stops)

    if warehouse and not dry_run:
        warehouse.write_cycle(row)
        pos_data = [
            {"symbol": p.symbol, "side": "long" if p.quantity > 0 else "short",
             "qty": p.quantity, "entry_price": p.entry_price,
             "current_price": p.current_price, "unrealized_pnl": p.unrealized_pnl,
             "timestamp": row.get("timestamp"), "cycle_number": state["cycle_count"]}
            for p in positions
        ]
        warehouse.write_positions(pos_data)

    logger.info("  PnL: total=%.2f cash=%.2f value=%.2f positions=%d regime=%s",
                state["total_pnl"], broker.cash, portfolio.total_value,
                len(portfolio.positions), state.get("regime", "unknown"))
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
    toggle_config_path = state_dir / "strategy_config.json"
    state_path = state_dir / "state.json"
    log_path = state_dir / "pnl.csv"
    attribution_path = state_dir / "pnl_attribution.csv"

    state = load_state(state_path)
    state.setdefault("initial_capital", args.capital)
    state.setdefault("peak_capital", args.capital)
    state.setdefault("cycle_count", 0)
    state.setdefault("total_pnl", 0.0)

    active_strategies = _apply_toggle_config(args.strategies, toggle_config_path)

    broker = PaperExchangeBroker(initial_capital=args.capital)
    await broker.connect()
    kill_switch = KillSwitch()
    configure_kill_switch_file()  # C5: daemon + API + bridge share one kill-switch file
    auto_disable = AutoDisableManager(
        kill_switch=kill_switch,
        sharpe_window=30,
        threshold=0.3,
        state_path=str(state_dir / "auto_disable_state.json"),
        paper_mode=True,
    )

    correlation_monitor = StrategyCorrelationMonitor(
        kill_switch=kill_switch,
        state_dir=str(state_dir),
        paper_mode=True,
    )

    drawdown_monitor = DrawdownMonitor(max_drawdown=MAX_DRAWDOWN_PCT, initial_equity=args.capital)

    audit = AuditLogger(log_dir=str(state_dir))
    audit.log("SYSTEM", "INFO", "Daemon started", {"capital": args.capital, "interval": args.interval, "live_data": args.live_data})
    if active_strategies != args.strategies:
        audit.log("SYSTEM", "INFO", "Toggle config applied on startup", {
            "cli": list(args.strategies), "active": list(active_strategies),
        })
    monitor = MonitorHub(log_dir=str(state_dir))
    warehouse = DataWarehouse(state_dir)
    logger.info("DataWarehouse initialized at %s", state_dir / "warehouse")

    # Dedicated Risk Agent + Compliance Agent (P1-8)
    risk_agent = RiskAgent()
    compliance_agent = ComplianceAgent()
    logger.info("RiskAgent + ComplianceAgent initialized (dedicated agent loop)")
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
        "Daemon started: capital=%.2f interval=%ds symbols=%s strategies=%s active=%s state=%s live_data=%s vol_target=%.2f regime_aware=True",
        args.capital, args.interval, args.symbols, args.strategies, active_strategies, state_dir,
        args.live_data, args.vol_target,
    )

    row = {}
    _prev_toggle_strategies = active_strategies
    try:
        while not stop_event.is_set():
            active_strategies = _apply_toggle_config(args.strategies, toggle_config_path)
            if active_strategies != _prev_toggle_strategies:
                audit.log("SYSTEM", "INFO", "Toggle config changed mid-run", {
                    "previous": list(_prev_toggle_strategies), "active": list(active_strategies),
                })
                _prev_toggle_strategies = active_strategies
            row = await run_cycle(
                broker, active_strategies, args.symbols, kill_switch, auto_disable,
                state, log_path, attribution_path, state_path, args.dry_run, args.live_data, args.vol_target,
                warehouse=warehouse,
                correlation_monitor=correlation_monitor,
                drawdown_monitor=drawdown_monitor,
                audit=audit, monitor=monitor,
                risk_agent=risk_agent, compliance_agent=compliance_agent,
            )
            if args.dry_run:
                break
            if monitor and state["cycle_count"] % 10 == 0:
                snap = monitor.snapshot()
                monitor.log_metric(snap)
                if warehouse:
                    warehouse.write_metrics(snap)
                logger.info("MonitorHub: lat=%.1fms err=%.4f pnl=%.2f corr=%.3f",
                            snap.execution_latency_ms, snap.error_rate,
                            snap.pnl_per_cycle, snap.correlation)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=args.interval)
            except asyncio.TimeoutError:
                pass
    finally:
        audit.log("SYSTEM", "INFO", "Daemon stopped", {"cycles": state["cycle_count"], "total_pnl": state.get("total_pnl")})
        audit.save_to_file()
        warehouse.close()
        await broker.disconnect()
        logger.info("Daemon stopped: %d cycles completed", state["cycle_count"])


if __name__ == "__main__":
    # ponytail: self-check — symbol normalization must never regress (670x price bug)
    assert _norm_symbol("BTCUSDT") == "BTC/USDT", "symbol normalization broken"
    assert _norm_symbol("ETH/USDT") == "ETH/USDT", "symbol normalization broke valid fmt"
    asyncio.run(main())
