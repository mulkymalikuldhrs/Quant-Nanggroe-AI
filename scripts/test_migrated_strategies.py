"""Smoke test for the 4 WAVE-5 migrated HF strategies.

Imports each migrated strategy module and runs ``generate_signal`` on a
synthetic OHLCV DataFrame (500 bars), printing OK/FAIL per strategy.

Run:
    python scripts/test_migrated_strategies.py

Exits non-zero if any strategy fails to import or raises during signal gen.
"""

from __future__ import annotations

import sys
import traceback

import numpy as np
import pandas as pd

# Ensure repo root is importable
sys.path.insert(0, str(__file__) if False else ".")

STRATEGIES = [
    ("dhaher_system", "DhaherSystem"),
    ("kronos", "KronosSignalProvider"),
    ("kronos_ensemble", "KronosEnsembleStrategy"),
    ("tradebobby_smc", "TradeBobbySMCStrategy"),
]


def make_ohlcv(n: int = 500) -> pd.DataFrame:
    np.random.seed(7)
    dates = pd.date_range("2025-01-01", periods=n, freq="15min")
    # Random-walk price with mild trend + intrabar wicks
    price = 100.0 + np.cumsum(np.random.randn(n)) * 0.2 + np.linspace(0, 5, n)
    opens = price + np.random.randn(n) * 0.05
    closes = price + np.random.randn(n) * 0.05
    highs = np.maximum(opens, closes) + np.abs(np.random.randn(n)) * 0.15
    lows = np.minimum(opens, closes) - np.abs(np.random.randn(n)) * 0.15
    return pd.DataFrame(
        {
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": np.abs(np.random.randn(n) * 100 + 1000),
        },
        index=dates,
    )


def main() -> int:
    from quant_nanggroe.engine.strategy.strategies import create_strategy

    df = make_ohlcv(500)
    failures = 0

    for name, class_name in STRATEGIES:
        try:
            strat = create_strategy(name)
            assert type(strat).__name__ == class_name, (
                f"class mismatch: got {type(strat).__name__}, expected {class_name}"
            )
            sig = strat.generate_signal(df)
            status = "OK"
            detail = f"signal={'None' if sig is None else sig.signal_type.value}"
        except Exception as exc:  # noqa: BLE001
            failures += 1
            status = "FAIL"
            detail = f"{type(exc).__name__}: {exc}"
            traceback.print_exc()

        print(f"[{status}] {name:18s} ({class_name:24s}) {detail}")

    print("\nSummary:")
    print(f"  total={len(STRATEGIES)}  failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
