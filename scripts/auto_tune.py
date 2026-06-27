#!/usr/bin/env python3
"""Auto-Tune: weekly grid search over strategy parameters.

Usage:
    python scripts/auto_tune.py
    python scripts/auto_tune.py --strategies Momentum,MeanReversion
    python scripts/auto_tune.py --metric sharpe --param-ranges my_ranges.json
"""

from __future__ import annotations

import argparse
import itertools
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies import list_strategies, create_strategy

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

N_OBS = 500
TUNED_PARAMS_PATH = os.path.join(_REPO_ROOT, "paper_state", "tuned_params.json")

DEFAULT_PARAM_RANGES: Dict[str, Dict[str, List[Any]]] = {
    "Momentum": {
        "lookback": [63, 126, 252],
        "signal_smoothing": [3, 5, 10],
    },
    "MeanReversion": {
        "lookback": [10, 20, 40],
        "entry_threshold": [1.0, 1.5, 2.0],
    },
    "PairsTrading": {
        "lookback": [30, 60, 120],
        "hedge_ratio_lookback": [60, 126, 252],
    },
    "VolatilityArbitrage": {
        "vol_lookback": [10, 20, 40],
        "entry_threshold": [1.5, 2.0, 2.5],
    },
    "StatisticalArbitrage": {
        "lookback": [30, 60, 120],
        "n_factors": [2, 3, 5],
    },
    "MarketMaking": {
        "gamma": [0.05, 0.1, 0.2],
        "spread_multiplier": [0.5, 1.0, 2.0],
    },
    "RegimeBased": {
        "n_regimes": [2, 3, 4],
        "hmm_lookback": [10, 20, 30, 50, 100, 252],
        "volatility_threshold": [0.5, 1.0, 1.5, 2.0, 2.5],
        "feature_ewma_span": [10, 21, 30, 50],
        "feature_min_periods": [5, 10, 15, 20],
    },
    "CryptoSpecific": {
        "lookback": [12, 24, 48],
        "entry_threshold": [0.0001, 0.0003, 0.0005],
    },
}


def _load_real_ohlcv(symbol: str = "BTC", max_bars: int = 500) -> pd.DataFrame | None:
    path = os.path.join(_REPO_ROOT, "data", "cached_ohlcv", f"{symbol}.csv")
    if not os.path.isfile(path):
        return None
    df = pd.read_csv(path, parse_dates=["date"])
    if len(df) < 200:
        return None
    df = df.iloc[-max_bars:]
    return df.rename(columns={"date": "index"}).set_index("index")


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


def _compute_sharpe(returns: np.ndarray) -> float:
    if len(returns) < 5:
        return 0.0
    std = float(np.std(returns))
    if std < 1e-10:
        return 0.0
    return float(np.mean(returns) / std * np.sqrt(365))


def _run_strategy(strategy_name: str, params: Dict[str, Any], ohlcv: pd.DataFrame) -> float:
    try:
        strategy = create_strategy(strategy_name, params)
    except Exception:
        return 0.0
    data = _prepare_data(strategy_name, ohlcv)
    close = data["close"].values if "close" in data.columns else data.iloc[:, 0].values
    if len(close) < 60:
        return 0.0

    step = max(5, len(close) // 30)
    positions = list(range(60, len(close), step))
    if len(positions) < 3:
        return 0.0

    forward_rets = []
    for pos in positions:
        window = data.iloc[:pos]
        try:
            result = strategy.generate_signal(window)
        except Exception:
            continue
        if result is None:
            continue
        direction = 1
        if hasattr(result, "signal_type") and hasattr(result.signal_type, "value"):
            if result.signal_type.value in ("sell", "close_long"):
                direction = -1
        confidence = float(result.confidence) if hasattr(result, "confidence") else 0.5
        horizon = 1
        if pos + horizon < len(close):
            ret = (close[pos + horizon] - close[pos]) / max(abs(close[pos]), 1e-10)
            forward_rets.append(direction * confidence * ret)

    if len(forward_rets) < 3:
        return 0.0
    return _compute_sharpe(np.array(forward_rets))


def tune_strategy(
    strategy_name: str,
    ohlcv: pd.DataFrame,
    param_ranges: Dict[str, List[Any]],
) -> tuple:
    default_sharpe = _run_strategy(strategy_name, {}, ohlcv)
    best_sharpe = default_sharpe
    best_params: Dict[str, Any] = {}
    keys = list(param_ranges.keys())
    values = list(param_ranges.values())
    total = 1
    for v in values:
        total *= len(v)
    evaluated = 0
    for combo in itertools.product(*values):
        params = dict(zip(keys, combo))
        sharpe = _run_strategy(strategy_name, params, ohlcv)
        evaluated += 1
        if sharpe > best_sharpe:
            best_sharpe = sharpe
            best_params = params
    return best_params, best_sharpe, default_sharpe, evaluated


def load_param_ranges(path: Optional[str]) -> Dict[str, Dict[str, List[Any]]]:
    if path is None:
        return dict(DEFAULT_PARAM_RANGES)
    with open(path) as f:
        return json.load(f)


def load_existing_tuned() -> Dict[str, Any]:
    if not os.path.isfile(TUNED_PARAMS_PATH):
        return {}
    try:
        with open(TUNED_PARAMS_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_tuned_params(results: Dict[str, dict]) -> None:
    os.makedirs(os.path.dirname(TUNED_PARAMS_PATH), exist_ok=True)
    payload = {
        "version": 1,
        "metric": "sharpe",
        "strategies": results,
    }
    with open(TUNED_PARAMS_PATH, "w") as f:
        json.dump(payload, f, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-Tune: strategy parameter grid search on real data")
    parser.add_argument("--strategies", default=None, help="Comma-separated strategy names (default: all)")
    parser.add_argument("--symbol", default="BTC", help="Symbol for real data tuning (default: BTC)")
    parser.add_argument("--metric", default="sharpe", choices=["sharpe"], help="Optimization metric (default: sharpe)")
    parser.add_argument("--param-ranges", default=None, help="Path to JSON file with custom param ranges")
    args = parser.parse_args()

    all_strategies = list_strategies()
    if not all_strategies:
        logger.error("No strategies registered")
        sys.exit(1)

    if args.strategies:
        selected = [s.strip() for s in args.strategies.split(",")]
        selected = [s for s in selected if s in all_strategies]
        if not selected:
            logger.error("No valid strategies in --strategies. Available: %s", all_strategies)
            sys.exit(1)
    else:
        selected = all_strategies

    param_ranges = load_param_ranges(args.param_ranges)
    existing = load_existing_tuned()

    logger.info("Auto-Tune: %d strategies, metric=%s", len(selected), args.metric)
    real_data = _load_real_ohlcv(getattr(args, 'symbol', None) or "BTC")
    ohlcv = real_data if real_data is not None else _generate_ohlcv()
    if real_data is not None:
        logger.info("Using real data (%d bars) for tuning", len(real_data))

    results: Dict[str, dict] = {}
    improvements = []

    for name in selected:
        if name not in param_ranges:
            logger.info("  %s: no param ranges defined, skipping", name)
            continue
        ranges = param_ranges[name]
        best_params, best_sharpe, default_sharpe, evaluated = tune_strategy(name, ohlcv, ranges)
        improvement_pct = ((best_sharpe - default_sharpe) / max(abs(default_sharpe), 1e-10) * 100) if abs(default_sharpe) > 1e-10 else 0.0
        results[name] = {
            "default_params": {},
            "default_sharpe": round(default_sharpe, 4),
            "best_params": best_params,
            "best_sharpe": round(best_sharpe, 4),
            "improvement_pct": round(improvement_pct, 1),
            "combinations_evaluated": evaluated,
        }
        improvements.append((name, default_sharpe, best_sharpe, improvement_pct, evaluated))

    save_tuned_params(results)

    print("\nStrategy          Default Sharpe   Best Sharpe   Improvement   Combos")
    print("─" * 75)
    for name, default_sharpe, best_sharpe, imp, evaled in improvements:
        params_str = ", ".join(f"{k}={v}" for k, v in results[name]["best_params"].items())
        print(f"{name:<18s} {default_sharpe:<15.4f} {best_sharpe:<13.4f} {imp:>+7.1f}%   {evaled}")
        if results[name]["best_params"]:
            print(f"{'':>18s}  tuned: {params_str}")

    print(f"\nBest params saved to {TUNED_PARAMS_PATH}")


if __name__ == "__main__":
    main()
