#!/usr/bin/env python3
"""Minimal backtest gate — validates strategy pipeline can load and produce signals.

Called by hedge_fund/risk/gate.py and hedge_fund/portfolio/main.py.
Output MUST contain the literal string "pass": true for callers to proceed.
"""

import json
import sys
from pathlib import Path


def run_gate_check() -> tuple[bool, list[str]]:
    """Return (ok, errors) — True if all strategy pipelines import and instantiate cleanly."""
    errors = []

    # 1. Validate core strategy imports
    try:
        from quant_nanggroe.strategies.tsmom import TSMOM
        tsmom = TSMOM()
        # Smoke-test with minimal dummy candles
        dummy = [{"open": 100, "high": 101, "low": 99, "close": 100, "volume": 10, "timestamp": 0}] * 35
        result = tsmom.analyze([c["close"] for c in dummy])
        # Strategies may return str or dict with 'signal' key
        sig = result.get("signal") if isinstance(result, dict) else result
        if sig not in ("buy", "sell", "hold", None):
            errors.append(f"TSMOM returned unexpected signal: {result}")
    except Exception as e:
        errors.append(f"TSMOM: {e}")

    try:
        from quant_nanggroe.strategies.trend_follow import TrendFollow
        tf = TrendFollow()
        dummy = [{"open": 100, "high": 101, "low": 99, "close": 100, "volume": 10, "timestamp": 0}] * 35
        result = tf.analyze([c["close"] for c in dummy])
        sig = result.get("signal") if isinstance(result, dict) else result
        if sig not in ("buy", "sell", "hold", None):
            errors.append(f"TrendFollow returned unexpected signal: {result}")
    except Exception as e:
        errors.append(f"TrendFollow: {e}")

    # 2. Validate execution router can be imported
    try:
        from quant_nanggroe.pipeline.execution import UnifiedExecutionRouter
    except Exception as e:
        errors.append(f"UnifiedExecutionRouter: {e}")

    # 3. Validate engine risk constants are accessible
    try:
        from quant_nanggroe.engine.risk.constants import (
            MAX_DAILY_LOSS, MAX_WEEKLY_LOSS, MAX_DRAWDOWN_PCT
        )
    except Exception as e:
        errors.append(f"Risk constants: {e}")

    # 4. Validate engine bridge can be imported
    try:
        from quant_nanggroe.engine_bridge import EngineRiskManager, EnginePriceProvider
    except Exception as e:
        errors.append(f"Engine bridge: {e}")

    return len(errors) == 0, errors


def main():
    passed, errors = run_gate_check()
    result = {"pass": passed}
    if errors:
        result["errors"] = errors

    # Callers grep stdout+stderr for the literal string: "pass": true
    print(json.dumps(result))
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
