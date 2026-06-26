#!/usr/bin/env python3
"""Regime-Adaptive Execution: HMM regime detection → strategy params → position sizing.

Phase 3.4 of the AUTONOMOUS_ROADMAP.

Reads cached regime from paper_state/regime_state.json, or runs HMM on synthetic
GARCH data to detect market regime.  Adjusts ALL 8 strategy parameter sets and
computes a regime_multiplier for position sizing (full/half/0.8 Kelly).

Usage:
    python scripts/regime_adaptive_execution.py              # detect → adapt → save
    python scripts/regime_adaptive_execution.py --status      # report only
    python scripts/regime_adaptive_execution.py --strategies Momentum,MeanReversion
    python scripts/regime_adaptive_execution.py --force-recompute
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone, timedelta
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
REGIME_STATE_PATH = os.path.join(_REPO_ROOT, "paper_state", "regime_state.json")
ADAPTED_PARAMS_PATH = os.path.join(_REPO_ROOT, "paper_state", "regime_adapted_params.json")
STALE_DAYS = 7

# ---------------------------------------------------------------------------
# Regime → parameter mapping for ALL 8 strategies
# ---------------------------------------------------------------------------
REGIME_PARAMS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "bull": {
        "Momentum": {"lookback": 126, "signal_smoothing": 10},
        "MeanReversion": {"entry_threshold": 2.5},
        "PairsTrading": {"lookback": 60, "hedge_ratio_lookback": 126},
        "VolatilityArbitrage": {"entry_threshold": 2.5},
        "StatisticalArbitrage": {"lookback": 60, "n_factors": 5},
        "MarketMaking": {"gamma": 0.2, "spread_multiplier": 2.0},
        "RegimeBased": {"n_regimes": 4, "hmm_lookback": 378},
        "CryptoSpecific": {"lookback": 12, "entry_threshold": 0.0005},
    },
    "bear": {
        "Momentum": {"lookback": 63, "signal_smoothing": 5},
        "MeanReversion": {"entry_threshold": 3.0},
        "PairsTrading": {"lookback": 120, "hedge_ratio_lookback": 252},
        "VolatilityArbitrage": {"entry_threshold": 3.0},
        "StatisticalArbitrage": {"lookback": 120, "n_factors": 3},
        "MarketMaking": {"gamma": 0.05, "spread_multiplier": 3.0},
        "RegimeBased": {"n_regimes": 3, "hmm_lookback": 252},
        "CryptoSpecific": {"lookback": 24, "entry_threshold": 0.0003},
    },
    "ranging": {
        "Momentum": {"lookback": 252, "signal_smoothing": 3},
        "MeanReversion": {"lookback": 20, "entry_threshold": 1.5},
        "PairsTrading": {"lookback": 30, "hedge_ratio_lookback": 60},
        "VolatilityArbitrage": {"lookback": 20, "entry_threshold": 1.5},
        "StatisticalArbitrage": {"lookback": 30, "n_factors": 2},
        "MarketMaking": {"gamma": 0.1, "spread_multiplier": 1.0},
        "RegimeBased": {"n_regimes": 2, "hmm_lookback": 126},
        "CryptoSpecific": {"lookback": 48, "entry_threshold": 0.0001},
    },
}

REGIME_MULTIPLIERS = {
    "bull": 1.0,
    "bear": 0.5,
    "ranging": 0.8,
}

# Map 6-regime HMMDetector to our 3-regime schema
REGIME_MAP_6TO3 = {
    "BULL": "bull",
    "BEAR": "bear",
    "SIDEWAYS": "ranging",
    "CRISIS": "bear",
    "HIGH_VOL": "bear",
    "LOW_VOL": "ranging",
}


# ---------------------------------------------------------------------------
# Synthetic data generators (mirror auto_tune.py / auto_rotate.py)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Regime detection
# ---------------------------------------------------------------------------
def _detect_regime_hmm(ohlcv: pd.DataFrame) -> tuple:
    """Use HMMRegimeDetector if available, else fallback to trend heuristic."""
    try:
        from quant_nanggroe.engine.regime.hmm_detector import HMMRegimeDetector, Regime
        detector = HMMRegimeDetector(n_regimes=4, lookback=252)
        returns = ohlcv["close"].pct_change().dropna().tolist()
        volumes = ohlcv["volume"].tolist()
        detector.fit(returns[:504], volumes[:504])
        state = detector.predict(returns, volumes)
        regime_6 = state.regime.value if hasattr(state.regime, "value") else str(state.regime)
        regime_3 = REGIME_MAP_6TO3.get(regime_6, "ranging")
        confidence = float(state.confidence)
        logger.info("HMM detect: %s → %s (conf=%.3f)", regime_6, regime_3, confidence)
        return regime_3, confidence
    except Exception as exc:
        logger.warning("HMM detector failed (%s), falling back to heuristic", exc)
        return _detect_regime_heuristic(ohlcv)


def _detect_regime_heuristic(ohlcv: pd.DataFrame) -> tuple:
    """Simple SMA + volatility heuristic fallback."""
    close = ohlcv["close"].values
    n = len(close)
    sma_21 = np.full(n, np.nan)
    sma_63 = np.full(n, np.nan)
    vol_21 = np.full(n, np.nan)
    for i in range(20, n):
        sma_21[i] = np.mean(close[i - 20:i + 1])
    for i in range(62, n):
        sma_63[i] = np.mean(close[i - 62:i + 1])
    for i in range(20, n):
        vol_21[i] = np.std(close[i - 20:i + 1] / close[i - 20:i + 1].mean())
    last_close = close[-1]
    last_sma_21 = sma_21[-1]
    last_sma_63 = sma_63[-1]
    last_vol = vol_21[-1]
    if np.isnan(last_sma_63) or np.isnan(last_sma_21) or np.isnan(last_vol):
        return "ranging", 0.4
    med_vol = np.nanmedian(vol_21[20:]) if np.any(~np.isnan(vol_21[20:])) else 0.015
    vol_ratio = last_vol / max(med_vol, 1e-10)
    price_above_sma63 = last_close > last_sma_63
    price_below_sma63 = last_close < last_sma_63
    sma_distance = abs(last_close - last_sma_63) / max(last_sma_63, 1e-10)
    if price_above_sma63 and vol_ratio < 1.5:
        regime = "bull"
        confidence = min(0.85, 0.5 + max(0, (last_close - last_sma_63) / last_sma_63) * 10)
    elif price_below_sma63 and vol_ratio > 1.0:
        regime = "bear"
        confidence = min(0.85, 0.5 + vol_ratio * 0.2)
    elif sma_distance < 0.03 or vol_ratio < 0.8:
        regime = "ranging"
        confidence = 0.6
    else:
        regime = "ranging"
        confidence = 0.5
    return regime, round(confidence, 4)


def load_cached_regime() -> Optional[dict]:
    if not os.path.isfile(REGIME_STATE_PATH):
        return None
    try:
        with open(REGIME_STATE_PATH) as f:
            data = json.load(f)
        ts_str = data.get("timestamp", "")
        if ts_str:
            ts = datetime.fromisoformat(ts_str)
            age = datetime.now(timezone.utc) - ts.replace(tzinfo=timezone.utc) if ts.tzinfo else datetime.now() - ts
            if age.days > STALE_DAYS:
                logger.info("Cached regime stale (%d days old)", age.days)
                return None
        return data
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        logger.warning("Failed to read cached regime: %s", exc)
        return None


def save_regime_state(regime: str, confidence: float, n_regimes: int) -> None:
    os.makedirs(os.path.dirname(REGIME_STATE_PATH), exist_ok=True)
    payload = {
        "regime": regime,
        "probability": round(confidence, 4),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_regimes": n_regimes,
    }
    with open(REGIME_STATE_PATH, "w") as f:
        json.dump(payload, f, indent=2)


# ---------------------------------------------------------------------------
# Parameter adaptation
# ---------------------------------------------------------------------------
def adapt_params(regime: str, strategies: Optional[List[str]] = None) -> Dict[str, Any]:
    adapted: Dict[str, Dict[str, Any]] = {}
    all_strategies = list_strategies()
    if strategies:
        targets = [s for s in all_strategies if s in strategies]
    else:
        targets = all_strategies
    regime_params = REGIME_PARAMS.get(regime, REGIME_PARAMS["ranging"])
    for name in targets:
        if name in regime_params:
            adapted[name] = dict(regime_params[name])
        else:
            adapted[name] = {}
    return adapted


def save_adapted_params(regime: str, confidence: float, multiplier: float, adapted: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(ADAPTED_PARAMS_PATH), exist_ok=True)
    payload = {
        "regime": regime,
        "confidence": round(confidence, 4),
        "regime_multiplier": multiplier,
        "adapted_params": adapted,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with open(ADAPTED_PARAMS_PATH, "w") as f:
        json.dump(payload, f, indent=2)


# ---------------------------------------------------------------------------
# Report (stdout table)
# ---------------------------------------------------------------------------
def print_report(regime: str, confidence: float, multiplier: float, adapted: Dict[str, Any]) -> None:
    print(f"Regime: {regime} (conf: {confidence * 100:.1f}%)  |  Multiplier: {multiplier:.1f}x")
    print("\u2500" * 60)
    for strategy, params in adapted.items():
        if not params:
            print(f"{strategy:<18s}  (no adapted params)")
            continue
        parts = [f"{k}={v}" for k, v in params.items()]
        print(f"{strategy:<18s}  {parts[0]}")
        for p in parts[1:]:
            print(f"{'':>18s}  {p}")


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------
def detect_and_adapt(force_recompute: bool = False, strategies: Optional[List[str]] = None) -> dict:
    if not force_recompute:
        cached = load_cached_regime()
        if cached is not None:
            regime = cached.get("regime", "ranging")
            confidence = cached.get("probability", 0.5)
            n_regimes = cached.get("n_regimes", 3)
            logger.info("Using cached regime: %s (conf=%.3f)", regime, confidence)
            multiplier = REGIME_MULTIPLIERS.get(regime, 0.8)
            adapted = adapt_params(regime, strategies)
            save_adapted_params(regime, confidence, multiplier, adapted)
            return {"regime": regime, "confidence": confidence, "regime_multiplier": multiplier, "adapted_params": adapted}
    ohlcv = _generate_ohlcv(N_OBS)
    regime, confidence = _detect_regime_hmm(ohlcv)
    n_regimes = 4
    save_regime_state(regime, confidence, n_regimes)
    multiplier = REGIME_MULTIPLIERS.get(regime, 0.8)
    adapted = adapt_params(regime, strategies)
    save_adapted_params(regime, confidence, multiplier, adapted)
    return {"regime": regime, "confidence": confidence, "regime_multiplier": multiplier, "adapted_params": adapted}


def report_status(strategies: Optional[List[str]] = None) -> dict:
    cached = load_cached_regime()
    if cached is None:
        print("No cached regime state found. Run without --status to detect.")
        return {"regime": "unknown", "confidence": 0.0, "regime_multiplier": 1.0, "adapted_params": {}}
    regime = cached.get("regime", "ranging")
    confidence = cached.get("probability", 0.5)
    multiplier = REGIME_MULTIPLIERS.get(regime, 0.8)
    adapted = adapt_params(regime, strategies)
    print_report(regime, confidence, multiplier, adapted)
    return {"regime": regime, "confidence": confidence, "regime_multiplier": multiplier, "adapted_params": adapted}


def main() -> None:
    parser = argparse.ArgumentParser(description="Regime-Adaptive Execution: HMM → params → position sizing")
    parser.add_argument("--status", action="store_true", help="Report current regime state without changes")
    parser.add_argument("--strategies", default=None, help="Comma-separated strategy subset (default: all)")
    parser.add_argument("--force-recompute", action="store_true", help="Ignore cached regime state, force fresh HMM detection")
    args = parser.parse_args()
    selected: Optional[List[str]] = None
    if args.strategies:
        selected = [s.strip() for s in args.strategies.split(",")]
    if args.status:
        report_status(selected)
        return
    result = detect_and_adapt(force_recompute=args.force_recompute, strategies=selected)
    print_report(result["regime"], result["confidence"], result["regime_multiplier"], result["adapted_params"])
    print(f"\nAdapted params saved to {ADAPTED_PARAMS_PATH}")


if __name__ == "__main__":
    main()
