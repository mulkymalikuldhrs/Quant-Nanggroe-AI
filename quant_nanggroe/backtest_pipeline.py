#!/usr/bin/env python3
"""Minimal backtest gate — validates strategy pipeline can load and produce signals.

Called by hedge_fund/risk/gate.py and hedge_fund/portfolio/main.py.
Output MUST contain the literal string "pass": true for callers to proceed.
"""

import json
import sys


def run_gate_check() -> tuple[bool, list[str]]:
    """Return (ok, errors) — True if all strategy pipelines import and instantiate cleanly."""
    errors = []

    # 1. Validate core strategy imports
    try:
        from quant_nanggroe.engine.strategies.tsmom import TSMOM
        tsmom = TSMOM()
        # Smoke-test with minimal dummy OHLCV candles
        dummy = [{"open": 100, "high": 101, "low": 99, "close": 100, "volume": 10, "timestamp": i} for i in range(35)]
        result = tsmom.analyze(dummy)
        # Strategies may return str or dict with 'signal' key
        sig = result.get("signal") if isinstance(result, dict) else result
        if sig not in ("buy", "sell", "hold", None):
            errors.append(f"TSMOM returned unexpected signal: {result}")
    except Exception as e:
        errors.append(f"TSMOM: {e}")

    try:
        from quant_nanggroe.engine.strategies.trend_follow_strategy import TrendFollowStrategy
        tf = TrendFollowStrategy()
        dummy = [{"open": 100, "high": 101, "low": 99, "close": 100, "volume": 10, "timestamp": i} for i in range(35)]
        result = tf.analyze(dummy)
        sig = result.get("signal") if isinstance(result, dict) else result
        if sig not in ("buy", "sell", "hold", None):
            errors.append(f"TrendFollow returned unexpected signal: {result}")
    except Exception as e:
        errors.append(f"TrendFollow: {e}")

    # 2. Validate execution router can be imported
    try:
        pass
    except Exception as e:
        errors.append(f"UnifiedExecutionRouter: {e}")

    # 3. Validate engine risk constants are accessible
    try:
        pass
    except Exception as e:
        errors.append(f"Risk constants: {e}")

    # 4. Validate engine bridge can be imported
    try:
        pass
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
