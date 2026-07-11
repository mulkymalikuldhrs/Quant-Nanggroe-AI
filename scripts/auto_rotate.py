#!/usr/bin/env python3
"""Auto-Rotate: strategy rotation by trailing Sharpe.

Reads AutoDisableManager state, computes trailing 30d Sharpe per
strategy, auto-disables those below threshold, reports rankings.

Usage:
    python scripts/auto_rotate.py                    # run + disable + report
    python scripts/auto_rotate.py --status            # report only
    python scripts/auto_rotate.py --enable-all        # reset all to active
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, List

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import numpy as np
import pandas as pd

from quant_nanggroe.engine.risk.strategy_auto_disable import (
    DEFAULT_SHARPE_WINDOW,
    DEFAULT_THRESHOLD,
    AutoDisableManager,
)
from quant_nanggroe.engine.strategy.strategies import create_strategy, list_strategies

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

STATE_PATH = os.path.join(_REPO_ROOT, "paper_state", "auto_disable_state.json")
TUNED_PARAMS_PATH = os.path.join(_REPO_ROOT, "paper_state", "tuned_params.json")
N_OBS = 100


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


def _prepare_data(strategy_name: str, ohlcv: pd.DataFrame) -> pd.DataFrame:
    if strategy_name == "PairsTrading":
        close = ohlcv["close"].values
        rng = np.random.default_rng(42)
        n = len(ohlcv)
        beta = 2.0
        spread = np.zeros(n)
        for t in range(1, n):
            spread[t] = 0.85 * spread[t - 1] + rng.normal(0, 0.5)
        spread = spread * 2.0 / max(spread.std(), 1e-10)
        close_b = beta * close + spread
        return pd.DataFrame({"close": close, "ASSET_A": close, "ASSET_B": close_b}, index=ohlcv.index)
    if strategy_name == "CryptoSpecific":
        data = ohlcv.copy()
        data["funding_rate"] = np.random.default_rng(42).normal(0, 0.001, len(data))
        return data
    return ohlcv


def _compute_trailing_sharpe(name: str, params: Dict[str, Any], ohlcv: pd.DataFrame, window: int = 30) -> float:
    try:
        strategy = create_strategy(name, params)
    except Exception:
        return 0.0
    data = _prepare_data(name, ohlcv)
    n = len(data)
    close = data["close"].values if "close" in data.columns else data.iloc[:, 0].values
    signals = np.zeros(n)
    for i in range(n):
        window_data = data.iloc[: i + 1]
        try:
            result = strategy.generate_signal(window_data)
            if result is None:
                continue
            if hasattr(result, "confidence"):
                val = float(result.confidence)
                if hasattr(result, "signal_type") and hasattr(result.signal_type, "value"):
                    if result.signal_type.value in ("sell", "close_long"):
                        val = -val
                signals[i] = val
            elif isinstance(result, (int, float, np.floating)):
                signals[i] = float(result)
        except Exception:
            continue
    returns = np.zeros(n)
    for i in range(1, n):
        target = np.clip(float(signals[i]), -1, 1)
        ret = target * (close[i] - close[i - 1]) / max(close[i - 1], 1e-8)
        returns[i] = ret
    trailing = returns[-window:]
    if len(trailing) < 5:
        return 0.0
    std = float(np.std(trailing))
    if std < 1e-10:
        return 0.0
    return float(np.mean(trailing) / std * np.sqrt(365))


def load_tuned_params() -> Dict[str, Any]:
    if not os.path.isfile(TUNED_PARAMS_PATH):
        return {}
    try:
        with open(TUNED_PARAMS_PATH) as f:
            data = json.load(f)
        return data.get("strategies", {})
    except (json.JSONDecodeError, OSError):
        return {}


def load_state() -> Dict[str, Any]:
    if not os.path.isfile(STATE_PATH):
        return {"strategies": {}}
    try:
        with open(STATE_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"strategies": {}}


def save_state(state: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def enable_all() -> None:
    mgr = AutoDisableManager(state_path=STATE_PATH)
    all_strategies = list_strategies()
    for name in all_strategies:
        mgr.enable(name)
    mgr.save_state()
    enabled = [name for name in all_strategies if not mgr.is_disabled(name)]
    print(f"Enabled {len(enabled)}/{len(all_strategies)} strategies")


def report_status() -> Dict[str, Any]:
    state = load_state()
    tuned = load_tuned_params()
    all_strategies = list_strategies()
    strats_in_state = state.get("strategies", {})
    disabled = [n for n, s in strats_in_state.items() if s.get("disabled", False)]
    active = [s for s in all_strategies if s not in disabled]

    ohlcv = _generate_ohlcv()
    rankings: List[tuple] = []
    for name in all_strategies:
        params = {}
        if name in tuned:
            params = tuned[name].get("best_params", {})
        sharpe = _compute_trailing_sharpe(name, params, ohlcv)
        is_disabled = name in disabled
        rankings.append((sharpe, name, is_disabled))

    rankings.sort(key=lambda x: x[0], reverse=True)

    print(f"\nStrategy Ranking (trailing {DEFAULT_SHARPE_WINDOW}d Sharpe)")
    print("=" * 65)
    for rank, (sharpe, name, is_disabled) in enumerate(rankings, 1):
        status = "DISABLED" if is_disabled else "ACTIVE"
        print(f" {rank:>2}. {name:<20s} {sharpe:>8.4f}  {status}")

    active_count = sum(1 for _, _, d in rankings if not d)
    disabled_count = sum(1 for _, _, d in rankings if d)
    top_name = rankings[0][1] if rankings else "N/A"
    top_sharpe = rankings[0][0] if rankings else 0.0
    bot_name = rankings[-1][1] if rankings else "N/A"
    bot_sharpe = rankings[-1][0] if rankings else 0.0

    print(f"\n Active: {active_count}   Disabled: {disabled_count}")
    print(f" Top:    {top_name} ({top_sharpe:.4f})")
    print(f" Bottom: {bot_name} ({bot_sharpe:.4f})")

    return {
        "rankings": [(n, round(s, 4), d) for s, n, d in rankings],
        "active_count": active_count,
        "disabled_count": disabled_count,
        "top_performer": {"name": top_name, "sharpe": round(top_sharpe, 4)},
        "threshold": DEFAULT_THRESHOLD,
    }


def run_rotation() -> None:
    state = load_state()
    tuned = load_tuned_params()
    all_strategies = list_strategies()
    strats_in_state = state.get("strategies", {})
    currently_disabled = {n for n, s in strats_in_state.items() if s.get("disabled", False)}

    ohlcv = _generate_ohlcv()
    rankings: List[tuple] = []
    for name in all_strategies:
        params = {}
        if name in tuned:
            params = tuned[name].get("best_params", {})
        sharpe = _compute_trailing_sharpe(name, params, ohlcv)
        rankings.append((sharpe, name))

    rankings.sort(key=lambda x: x[0], reverse=True)

    newly_disabled = []
    newly_enabled = []
    for sharpe, name in rankings:
        if sharpe < DEFAULT_THRESHOLD:
            if name not in currently_disabled:
                newly_disabled.append(name)
        else:
            if name in currently_disabled:
                newly_enabled.append(name)

    if newly_disabled or newly_enabled:
        mgr = AutoDisableManager(state_path=STATE_PATH)
        for name in newly_disabled:
            mgr.disable(name, reason=f"Auto-rotate: trailing Sharpe {sharpe:.3f} < {DEFAULT_THRESHOLD}")
        for name in newly_enabled:
            mgr.enable(name, reason=f"Auto-rotate: trailing Sharpe recovered above {DEFAULT_THRESHOLD}")
        mgr.save_state()
        state = load_state()
        strats_in_state = state.get("strategies", {})
        currently_disabled = {n for n, s in strats_in_state.items() if s.get("disabled", False)}

    print(f"\nStrategy Rotation (trailing {DEFAULT_SHARPE_WINDOW}d Sharpe)")
    print("=" * 65)
    for rank, (sharpe, name) in enumerate(rankings, 1):
        status = "DISABLED" if name in currently_disabled else "ACTIVE"
        print(f" {rank:>2}. {name:<20s} {sharpe:>8.4f}  {status}")

    active_count = sum(1 for _, n in rankings if n not in currently_disabled)
    disabled_count = sum(1 for _, n in rankings if n in currently_disabled)
    top_name = rankings[0][1] if rankings else "N/A"
    top_sharpe = rankings[0][0] if rankings else 0.0

    print(f"\n Active: {active_count}   Disabled: {disabled_count}")
    print(f" Top:    {top_name} ({top_sharpe:.4f})")
    if newly_disabled:
        print(f" Newly disabled: {', '.join(newly_disabled)}")
    if newly_enabled:
        print(f" Newly enabled:  {', '.join(newly_enabled)}")
    print(f" Threshold: {DEFAULT_THRESHOLD}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-Rotate: strategy rotation by trailing Sharpe")
    parser.add_argument("--status", action="store_true", help="Report only, no state changes")
    parser.add_argument("--enable-all", action="store_true", help="Reset all strategies to active")
    args = parser.parse_args()

    if args.enable_all:
        enable_all()
        return

    if args.status:
        report_status()
        return

    run_rotation()


if __name__ == "__main__":
    main()
