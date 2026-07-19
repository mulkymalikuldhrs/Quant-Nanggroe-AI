"""
Integration Test — Dhaher Hedge Fund pipeline (mock mode, no MT5 required)
Verifies:
  1. All modules import
  2. Wyckoff signal generation
  3. Risk module (Kelly + Monte Carlo)
  4. Multi-pair scanner in mock mode
Run:  cd /e/trading && .venv/Scripts/python.exe integration_test.py
"""
import sys, traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import pandas as pd

RESULTS = []
def check(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))

# ── 1. Imports ──────────────────────────────
def test_imports():
    mods = ["strategy_registry", "risk_module", "multi_pair_scanner", "hedge_fund_mtf"]
    for m in mods:
        try:
            __import__(m)
            check(f"import {m}", True)
        except Exception as e:
            check(f"import {m}", False, f"{type(e).__name__}: {e}")

# ── 2. Wyckoff signal generation ────────────
def test_wyckoff():
    try:
        from strategy_registry import WyckoffStrategy
        n = 200
        idx = pd.date_range("2024-01-01", periods=n, freq="15min")
        rng = np.random.default_rng(7)
        close = 1.10 + np.cumsum(rng.normal(0, 0.0005, n))
        # inject a selling-climax spike (wide spread down + volume spike)
        vol = rng.integers(800, 1500, n).astype(float)
        high = close + np.abs(rng.normal(0, 0.0003, n)) + 0.0002
        low = close - np.abs(rng.normal(0, 0.0003, n)) - 0.0002
        vol[120] = 6000.0
        close[120] -= 0.0010
        low[120] -= 0.0015
        high[120] += 0.0003
        df = pd.DataFrame({"open": close, "high": high, "low": low,
                           "close": close, "tick_volume": vol}, index=idx)
        s = WyckoffStrategy(lookback=20, volume_mult=1.5)
        out = s.generate_signals(df)
        sigs = out["entry"].to_numpy()
        n_buy = int((sigs == 1).sum())
        n_sell = int((sigs == -1).sum())
        has_signal = (n_buy + n_sell) > 0
        check("wyckoff generate_signals", has_signal,
              f"buy={n_buy} sell={n_sell}")
    except Exception as e:
        check("wyckoff generate_signals", False, f"{type(e).__name__}: {e}")
        traceback.print_exc()

# ── 3. Risk module ──────────────────────────
def test_risk():
    try:
        from risk_module import kelly_fraction, kelly_lot_size, monte_carlo_simulation
        k = kelly_fraction(0.55, 200, 100)
        check("risk kelly_fraction", 0 <= k <= 0.25, f"f*={k:.4f}")
        lot = kelly_lot_size(1000, k, 50)
        check("risk kelly_lot_size", lot >= 0.01, f"lot={lot}")
        rng = np.random.default_rng(1)
        trades = [{"pnl": float(rng.uniform(-50, 150))} for _ in range(100)]
        mc = monte_carlo_simulation(trades, simulations=2000, confidence=0.95)
        ok = "var_95pct" in mc and "prob_profit" in mc
        check("risk monte_carlo", ok,
              f"VaR95={mc.get('var_95pct')} profit%={mc.get('prob_profit')}")
    except Exception as e:
        check("risk kelly/monte_carlo", False, f"{type(e).__name__}: {e}")
        traceback.print_exc()

# ── 4. Multi-pair scanner (mock mode) ───────
def test_scanner():
    try:
        import multi_pair_scanner as mps
        mps.set_mock_mode(True)  # task requires mock mode (no MT5)
        mode = "MOCK" if mps.MOCK_MODE else "MT5"
        valid, skipped = mps.scan_all_pairs()
        total = len(valid) + len(skipped)
        check("scanner scan_all_pairs", total == 37,
              f"mode={mode} valid={len(valid)}/{total}")
        # spot-check a known SL-jilat pair is skipped
        skipped_syms = {s["symbol"] for s in skipped}
        check("scanner SL-jilat filter", "XAUUSD" in skipped_syms,
              f"XAUUSD skipped={ 'XAUUSD' in skipped_syms}")
    except Exception as e:
        check("scanner scan_all_pairs", False, f"{type(e).__name__}: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    print("=== DHAHER HEDGE FUND — INTEGRATION TEST ===\n")
    test_imports(); print()
    test_wyckoff(); print()
    test_risk(); print()
    test_scanner(); print()
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f"=== SUMMARY: {passed}/{total} checks passed ===")
    sys.exit(0 if passed == total else 1)
