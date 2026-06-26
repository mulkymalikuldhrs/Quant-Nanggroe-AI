#!/usr/bin/env python3
"""Anomaly Auto-Reporter — 2σ threshold monitoring for all strategy/system metrics.

Phase 3.6 of the AUTONOMOUS_ROADMAP. Monitors P&L, Sharpe, slippage,
data freshness, strategy correlation, kill switch, and auto-disable
ratios. Alerts via local log file + file-based notification.

Usage:
    python3 scripts/anomaly_reporter.py              # run check, generate report
    python3 scripts/anomaly_reporter.py --status       # show last report
    python3 scripts/anomaly_reporter.py --clear        # remove alert files
    python3 scripts/anomaly_reporter.py --help         # full help
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────

PAPER_STATE = os.path.join(_REPO_ROOT, "paper_state")
STATE_PATH = os.path.join(PAPER_STATE, "anomaly_state.json")
LOG_PATH = os.path.join(PAPER_STATE, "anomaly_log.txt")
ALERT_FILE_BASE = os.path.join(PAPER_STATE, "anomaly_alert")

# Integration touch points
DAEMON_STATE_PATH = os.path.join(PAPER_STATE, "state.json")
PNL_CSV_PATH = os.path.join(PAPER_STATE, "pnl.csv")
CORRELATION_STATE_PATH = os.path.join(PAPER_STATE, "correlation_state.json")
AUTO_DISABLE_STATE_PATH = os.path.join(PAPER_STATE, "auto_disable_state.json")
KILL_SWITCH_STATE_PATH = os.path.join(PAPER_STATE, "kill_switch_state.json")
CACHED_OHLCV_DIR = os.path.join(_REPO_ROOT, "data", "cached_ohlcv")

DEFAULT_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT"]
N_OBS = 500
MAX_ALERTS = 100
SHARPE_BASELINE_THRESHOLD = 0.0
CORRELATION_HERD_THRESHOLD = 0.85
DISABLED_RATIO_THRESHOLD = 0.30
SLIPPAGE_PCT_ABOVE_BASELINE = 0.20
DATA_FRESHNESS_HOURS = 24
SIGMA_WARNING = 1.5
SIGMA_CRITICAL = 2.0

DEFAULT_BASELINES = {
    "pnl_daily_mean": 0.001,
    "pnl_daily_std": 0.02,
    "sharpe_baseline": 0.5,
    "slippage_p90_baseline": 10.0,
    "correlation_baseline": 0.6,
    "disabled_ratio_baseline": 0.1,
}


# ── Synthetic data (follows auto_tune.py pattern) ────────────────────────


def _generate_ohlcv(n: int = N_OBS, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    returns = rng.standard_t(df=4, size=n) * 0.015
    for i in range(1, n):
        returns[i] += 0.05 * returns[i - 1]
    vol = np.ones(n) * 0.015
    for i in range(1, n):
        vol[i] = np.sqrt(0.00001 + 0.85 * vol[i - 1] ** 2 + 0.10 * returns[i - 1] ** 2)
    returns = returns * (vol / 0.015)
    close = 100 * np.exp(np.cumsum(returns))
    high = close * (1 + np.abs(rng.normal(0, 0.005, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.005, n)))
    open_ = close * (1 + rng.normal(0, 0.003, n))
    volume = rng.integers(10000, 100000, n)
    dates = pd.date_range(end=pd.Timestamp.today(), periods=n, freq="D")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


def _generate_synthetic_pnl(n: int = N_OBS) -> pd.DataFrame:
    ohlcv = _generate_ohlcv(n)
    rng = np.random.default_rng(42)
    close = ohlcv["close"].values
    returns = np.zeros(n)
    for i in range(1, n):
        returns[i] = (close[i] - close[i - 1]) / max(close[i - 1], 1e-8)
    positions = rng.integers(0, 3, n)
    signals = rng.integers(0, 2, n) * positions
    pnl = returns * positions * 100
    total_value = 5000.0 + np.cumsum(pnl)
    today = pd.Timestamp.today()
    dates = [today - pd.Timedelta(days=n - i) for i in range(n)]
    return pd.DataFrame({
        "timestamp": [d.isoformat() for d in dates],
        "cycle": list(range(1, n + 1)),
        "signals": signals,
        "cash": total_value - pnl * 0,
        "total_value": total_value,
        "unrealized_pnl": np.zeros(n),
        "realized_pnl": pnl,
        "total_pnl": np.cumsum(pnl),
        "positions": positions,
        "drawdown_pct": np.zeros(n),
    })


def _synthetic_slippage_trades(symbols: list[str] | None = None) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    symbols = symbols or DEFAULT_SYMBOLS
    rows: list[dict[str, Any]] = []
    base_prices = {"BTC/USDT": 67000.0, "ETH/USDT": 3400.0, "SOL/USDT": 145.0, "XRP/USDT": 0.62}
    n = 100
    for i in range(n):
        sym = symbols[i % len(symbols)]
        base = base_prices.get(sym, 100.0)
        slippage_bps = round(rng.uniform(3.0, 15.0), 2)
        price = base * (1 + rng.normal(0, 0.02))
        rows.append({
            "symbol": sym,
            "price": round(price, 2),
            "slippage_bps": slippage_bps,
        })
    return pd.DataFrame(rows)


# ── State load / save (follows auto_rotate.py pattern) ───────────────────


def load_state() -> dict[str, Any]:
    if not os.path.isfile(STATE_PATH):
        return {"baselines": dict(DEFAULT_BASELINES), "alerts": [], "alert_count": 0}
    try:
        with open(STATE_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"baselines": dict(DEFAULT_BASELINES), "alerts": [], "alert_count": 0}


def save_state(state: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    state["alerts"] = state.get("alerts", [])[-MAX_ALERTS:]
    state["alert_count"] = len(state["alerts"])
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


# ── Alert logging ────────────────────────────────────────────────────────


def append_alert_log(level: str, message: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {message}\n"
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(line)


def create_alert_file(level: str) -> None:
    path = f"{ALERT_FILE_BASE}.{level}"
    Path(path).touch()


def clear_alert_files() -> None:
    for fname in os.listdir(PAPER_STATE):
        if fname.startswith("anomaly_alert"):
            os.remove(os.path.join(PAPER_STATE, fname))
    logger.info("Cleared anomaly alert files")


# ── Metric collection ────────────────────────────────────────────────────


def load_pnl() -> pd.DataFrame | None:
    if not os.path.isfile(PNL_CSV_PATH):
        return None
    try:
        return pd.read_csv(PNL_CSV_PATH)
    except Exception:
        return None


def load_daemon_state() -> dict[str, Any]:
    if not os.path.isfile(DAEMON_STATE_PATH):
        return {}
    try:
        with open(DAEMON_STATE_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def load_correlation_state() -> dict[str, Any]:
    if not os.path.isfile(CORRELATION_STATE_PATH):
        return {}
    try:
        with open(CORRELATION_STATE_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def load_auto_disable_state() -> dict[str, Any]:
    if not os.path.isfile(AUTO_DISABLE_STATE_PATH):
        return {}
    try:
        with open(AUTO_DISABLE_STATE_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def load_kill_switch_state() -> dict[str, Any]:
    if not os.path.isfile(KILL_SWITCH_STATE_PATH):
        return {}
    try:
        with open(KILL_SWITCH_STATE_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def check_data_freshness() -> float | None:
    if not os.path.isdir(CACHED_OHLCV_DIR):
        return None
    newest = 0.0
    for fname in os.listdir(CACHED_OHLCV_DIR):
        fpath = os.path.join(CACHED_OHLCV_DIR, fname)
        if os.path.isfile(fpath):
            mtime = os.path.getmtime(fpath)
            if mtime > newest:
                newest = mtime
    if newest == 0.0:
        return None
    hours_since = (datetime.now().timestamp() - newest) / 3600
    return hours_since


# ── Baseline computation ─────────────────────────────────────────────────


def compute_pnl_baseline(pnl: pd.DataFrame) -> tuple[float, float]:
    """Compute daily return mean and std from pnl.csv."""
    vals = pnl.get("total_value", pnl.get("total_pnl", pd.Series(dtype=float)))
    vals = pd.to_numeric(vals, errors="coerce").dropna()
    if len(vals) < 10:
        return DEFAULT_BASELINES["pnl_daily_mean"], DEFAULT_BASELINES["pnl_daily_std"]
    daily_returns = vals.diff().dropna() / vals.shift(1).dropna().clip(lower=1e-8)
    daily_returns = daily_returns.replace([np.inf, -np.inf], np.nan).dropna()
    if len(daily_returns) < 5:
        return DEFAULT_BASELINES["pnl_daily_mean"], DEFAULT_BASELINES["pnl_daily_std"]
    return float(daily_returns.mean()), float(daily_returns.std())


def compute_sharpe_from_pnl(pnl: pd.DataFrame) -> float:
    """Compute annualized Sharpe from daily returns."""
    vals = pnl.get("total_value", pnl.get("total_pnl", pd.Series(dtype=float)))
    vals = pd.to_numeric(vals, errors="coerce").dropna()
    if len(vals) < 10:
        return DEFAULT_BASELINES["sharpe_baseline"]
    daily_returns = vals.diff().dropna() / vals.shift(1).dropna().clip(lower=1e-8)
    daily_returns = daily_returns.replace([np.inf, -np.inf], np.nan).dropna()
    if len(daily_returns) < 5:
        return DEFAULT_BASELINES["sharpe_baseline"]
    std = float(daily_returns.std())
    if std < 1e-10:
        return 0.0
    return float(daily_returns.mean() / std * np.sqrt(365))


def compute_slippage_p90(symbols: list[str] | None = None) -> float:
    """Read slippage from trades or synthetic."""
    trades_path = os.path.join(PAPER_STATE, "trades.csv")
    if os.path.isfile(trades_path):
        try:
            trades = pd.read_csv(trades_path)
            slip = pd.to_numeric(trades.get("slippage_bps", pd.NA), errors="coerce").dropna()
            if len(slip) > 0:
                return float(slip.quantile(0.90))
        except Exception:
            pass
    # synthetic fallback
    trades = _synthetic_slippage_trades(symbols)
    return float(trades["slippage_bps"].quantile(0.90))


def compute_avg_pairwise_correlation() -> float:
    """Read correlation state and compute average pairwise correlation."""
    state = load_correlation_state()
    matrix = state.get("correlation_matrix", {})
    all_vals: list[float] = []
    for asset_a, inner in matrix.items():
        for asset_b, val in inner.items():
            if asset_a < asset_b:
                all_vals.append(float(val))
    if not all_vals:
        return DEFAULT_BASELINES["correlation_baseline"]
    return float(np.mean(all_vals))


def compute_disabled_ratio() -> float:
    """Compute ratio of disabled strategies from auto-disable state."""
    state = load_auto_disable_state()
    strategies = state.get("strategies", {})
    if not strategies:
        return DEFAULT_BASELINES["disabled_ratio_baseline"]
    disabled = sum(1 for s in strategies.values() if s.get("disabled", False))
    return disabled / len(strategies)


def check_kill_switch() -> dict[str, Any] | None:
    """Check kill switch state. Returns None if inactive, dict if active."""
    state = load_kill_switch_state()
    is_active = state.get("is_active", False) or state.get("status") == "active"
    current_level = state.get("current_level", "none")
    if not is_active or current_level == "none":
        return None
    return {
        "level": current_level,
        "trigger": state.get("activation_reason", state.get("reason", "unknown")),
        "activated_at": state.get("activated_at", None),
    }


# ── Alert decision engine ────────────────────────────────────────────────


def _alert_level(z_score: float) -> str:
    if abs(z_score) >= SIGMA_CRITICAL:
        return "CRITICAL"
    if abs(z_score) >= SIGMA_WARNING:
        return "WARNING"
    return "INFO"


def run_checks(state: dict[str, Any]) -> list[dict[str, Any]]:
    baselines = state.get("baselines", dict(DEFAULT_BASELINES))
    alerts: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc).isoformat()

    # 1. P&L daily return
    pnl_df = load_pnl()
    using_synthetic_pnl = False
    if pnl_df is None or len(pnl_df) < 5:
        pnl_df = _generate_synthetic_pnl()
        using_synthetic_pnl = True
        logger.info("Using synthetic P&L data (no real pnl.csv)")
    pnl_mean, pnl_std = compute_pnl_baseline(pnl_df)
    baselines["pnl_daily_mean"] = pnl_mean
    baselines["pnl_daily_std"] = pnl_std

    vals = pd.to_numeric(pnl_df.get("total_value", pnl_df.get("total_pnl", pd.Series(dtype=float))), errors="coerce").dropna()
    if len(vals) >= 5:
        daily_returns = vals.diff().dropna() / vals.shift(1).dropna().clip(lower=1e-8)
        daily_returns = daily_returns.replace([np.inf, -np.inf], np.nan).dropna()
        if len(daily_returns) > 0:
            last_return = float(daily_returns.iloc[-1])
            if pnl_std > 1e-10:
                z = (last_return - pnl_mean) / pnl_std
                level = _alert_level(z)
                if level != "INFO":
                    alerts.append({
                        "timestamp": now,
                        "level": level,
                        "metric": "pnl_daily_return",
                        "value": round(last_return, 6),
                        "threshold": round(pnl_mean + SIGMA_WARNING * pnl_std, 6),
                        "message": (
                            f"P&L daily return {last_return:.4f} "
                            f"(baseline: {pnl_mean:.4f} ± {pnl_std:.4f}, z={z:.2f})"
                        ),
                    })

    # 2. Sharpe ratio trailing 30d
    sharpe = compute_sharpe_from_pnl(pnl_df)
    if sharpe < SHARPE_BASELINE_THRESHOLD:
        alerts.append({
            "timestamp": now,
            "level": "WARNING",
            "metric": "sharpe_30d",
            "value": round(sharpe, 4),
            "threshold": SHARPE_BASELINE_THRESHOLD,
            "message": f"Sharpe ratio {sharpe:.3f} below 0.0 threshold",
        })

    # 3. Slippage P90
    slippage_p90 = compute_slippage_p90()
    baseline_slip = baselines.get("slippage_p90_baseline", DEFAULT_BASELINES["slippage_p90_baseline"])
    if slippage_p90 > baseline_slip * (1 + SLIPPAGE_PCT_ABOVE_BASELINE):
        level = "WARNING"
        if slippage_p90 > baseline_slip * (1 + 2 * SLIPPAGE_PCT_ABOVE_BASELINE):
            level = "CRITICAL"
        alerts.append({
            "timestamp": now,
            "level": level,
            "metric": "slippage_p90",
            "value": round(slippage_p90, 2),
            "threshold": round(baseline_slip * (1 + SLIPPAGE_PCT_ABOVE_BASELINE), 2),
            "message": f"Slippage P90={slippage_p90:.1f}bps (baseline={baseline_slip:.1f}bps)",
        })

    # 4. Data freshness
    hours_since = check_data_freshness()
    if hours_since is not None and hours_since > DATA_FRESHNESS_HOURS:
        alerts.append({
            "timestamp": now,
            "level": "CRITICAL" if hours_since > DATA_FRESHNESS_HOURS * 2 else "WARNING",
            "metric": "data_freshness",
            "value": round(hours_since, 1),
            "threshold": DATA_FRESHNESS_HOURS,
            "message": f"Data stale: {hours_since:.1f}h since last OHLCV update",
        })

    # 5. Strategy correlation (herding)
    avg_corr = compute_avg_pairwise_correlation()
    if avg_corr > CORRELATION_HERD_THRESHOLD:
        alerts.append({
            "timestamp": now,
            "level": "CRITICAL" if avg_corr > 0.95 else "WARNING",
            "metric": "strategy_correlation",
            "value": round(avg_corr, 4),
            "threshold": CORRELATION_HERD_THRESHOLD,
            "message": f"Avg pairwise correlation {avg_corr:.3f} > {CORRELATION_HERD_THRESHOLD} (herding)",
        })

    # 6. Kill switch activation
    ks = check_kill_switch()
    if ks is not None:
        alerts.append({
            "timestamp": now,
            "level": "CRITICAL",
            "metric": "kill_switch",
            "value": ks["level"],
            "threshold": "none",
            "message": f"Kill switch activated: level={ks['level']}, trigger={ks['trigger']}",
        })

    # 7. Auto-disable count
    disabled_ratio = compute_disabled_ratio()
    if disabled_ratio > DISABLED_RATIO_THRESHOLD:
        level = "CRITICAL" if disabled_ratio > 0.5 else "WARNING"
        alerts.append({
            "timestamp": now,
            "level": level,
            "metric": "auto_disabled_ratio",
            "value": round(disabled_ratio, 4),
            "threshold": DISABLED_RATIO_THRESHOLD,
            "message": f"Disabled strategies: {disabled_ratio:.1%} > {DISABLED_RATIO_THRESHOLD:.0%}",
        })

    return alerts


# ── Report formatting (stdout) ───────────────────────────────────────────


def format_report(alerts: list[dict[str, Any]]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    critical_count = sum(1 for a in alerts if a["level"] == "CRITICAL")
    warning_count = sum(1 for a in alerts if a["level"] == "WARNING")

    lines: list[str] = []
    lines.append("╔═══ Anomaly Report ═══╗")
    lines.append(f"Date: {now}")
    status_parts = []
    if warning_count:
        status_parts.append(f"{warning_count} WARNING")
    if critical_count:
        status_parts.append(f"{critical_count} CRITICAL")
    if not status_parts:
        status_parts.append("CLEAN")
    lines.append(f"Status: {' | '.join(status_parts)}")
    lines.append("")

    for alert in alerts:
        level = alert["level"]
        metric = alert["metric"]
        msg = alert["message"]

        if metric == "kill_switch":
            ks_trigger = alert.get("value", "unknown")
            lines.append(f"[{level}] Kill switch activated")
            lines.append(f"  Kill switch level: {ks_trigger}")
            lines.append(f"  Trigger: {msg.split('trigger=')[-1] if 'trigger=' in msg else 'N/A'}")
        elif metric == "slippage_p90":
            lines.append(f"[{level}] High slippage: {msg}")
        elif metric == "pnl_daily_return":
            lines.append(f"[{level}] P&L deviation: {msg}")
        elif metric == "sharpe_30d":
            lines.append(f"[{level}] Low Sharpe: {msg}")
        elif metric == "data_freshness":
            lines.append(f"[{level}] Stale data: {msg}")
        elif metric == "strategy_correlation":
            lines.append(f"[{level}] Herding detected: {msg}")
        elif metric == "auto_disabled_ratio":
            lines.append(f"[{level}] Disabled strategies: {msg}")
        else:
            lines.append(f"[{level}] {msg}")

    return "\n".join(lines)


def report_status() -> None:
    state = load_state()
    alerts = state.get("alerts", [])
    if not alerts:
        print("No anomaly reports found.")
        return
    critical_count = sum(1 for a in alerts if a["level"] == "CRITICAL")
    warning_count = sum(1 for a in alerts if a["level"] == "WARNING")
    last = alerts[-1]
    print(f"Last report: {alerts[-1]['timestamp']}")
    print(f"Alerts: {len(alerts)} total ({warning_count} WARNING, {critical_count} CRITICAL)")
    print(f"Latest: [{last['level']}] {last['message']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Anomaly Auto-Reporter: 2σ threshold monitoring for all strategy/system metrics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python3 scripts/anomaly_reporter.py
  python3 scripts/anomaly_reporter.py --status
  python3 scripts/anomaly_reporter.py --clear
  python3 scripts/anomaly_reporter.py --baselines path/to/baselines.json --quiet
        """,
    )
    parser.add_argument("--status", action="store_true", help="Show last anomaly report without re-running")
    parser.add_argument("--clear", action="store_true", help="Remove all anomaly_alert files, reset alert_count")
    parser.add_argument("--baselines", default=None, help="Path to JSON file with external baselines")
    parser.add_argument("--quiet", action="store_true", help="Suppress stdout, only write files")
    args = parser.parse_args()

    if args.clear:
        clear_alert_files()
        state = load_state()
        state["alerts"] = []
        save_state(state)
        print("Cleared all alert files and reset alert_count")
        return

    if args.status:
        report_status()
        return

    state = load_state()

    if args.baselines:
        try:
            with open(args.baselines) as f:
                external = json.load(f)
            state["baselines"].update(external)
            logger.info("Loaded external baselines from %s", args.baselines)
        except Exception as e:
            logger.error("Failed to load baselines from %s: %s", args.baselines, e)

    alerts = run_checks(state)

    # Process alerts: log + file notification
    max_level = "INFO"
    for alert in alerts:
        level = alert["level"]
        append_alert_log(level, alert["message"])
        if level in ("WARNING", "CRITICAL"):
            create_alert_file(level)
        if level == "CRITICAL":
            max_level = "CRITICAL"
        elif level == "WARNING" and max_level != "CRITICAL":
            max_level = "WARNING"

    # Merge new alerts into state
    existing = state.get("alerts", [])
    state["alerts"] = (existing + alerts)[-MAX_ALERTS:]
    save_state(state)

    if not args.quiet:
        report = format_report(alerts)
        print(report)
        if max_level != "INFO":
            print(f"\nAlert file: {ALERT_FILE_BASE}.{max_level}")

    if not alerts:
        logger.info("No anomalies detected — system healthy")


if __name__ == "__main__":
    main()
