"""Direct verification of macd_factor + ffn_adapter (no pytest startup overhead).

Mirrors the pytest assertions 1:1 — this is the fast path on a machine
where pytest startup costs ~3min due to AV real-time scanning.
"""

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"D:\repositories\Quant-Nanggroe-AI-worktree")

from quant_nanggroe.engine.factors.macd_factor import (
    compute_macd_histogram,
    compute_ppo,
    rolling_corr_forward_returns,
)
from quant_nanggroe.engine.analytics.ffn_adapter import (
    compute_stats,
    monthly_returns_table,
)


def synthetic_ohlcv() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    n = 200
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0005, 0.015, n)))
    high = close * (1 + np.abs(rng.normal(0, 0.005, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.005, n)))
    open_ = np.concatenate([[close[0]], close[:-1]])
    volume = rng.integers(100, 10_000, n)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=pd.date_range("2024-01-01", periods=n, freq="D"),
    )


passed = 0


def check(name, cond):
    global passed
    assert cond, f"FAIL: {name}"
    passed += 1
    print(f"  ok: {name}")


# --- MACD factor ---
df = synthetic_ohlcv()
r = compute_macd_histogram(df)
for col in ("macd_line", "signal_line", "macd_histogram"):
    check(f"column {col}", col in r.columns)
check(
    "hist = line - signal",
    np.allclose(
        r["macd_histogram"].dropna(),
        r["macd_line"].dropna() - r["signal_line"].dropna(),
        rtol=1e-10,
    ),
)
tail = r["macd_histogram"].dropna()
check(f"warmup values >= 150 (got {len(tail)})", len(tail) >= 150)
check("finite tail", np.isfinite(tail).all())

# constant price -> zero histogram
n = 120
flat = pd.DataFrame(
    {"open": [100.0] * n, "high": [101.0] * n, "low": [99.0] * n, "close": [100.0] * n, "volume": [1000] * n},
    index=pd.date_range("2024-01-01", periods=n, freq="D"),
)
rf = compute_macd_histogram(flat)
check("constant price -> zero histogram", np.allclose(rf["macd_histogram"].dropna(), 0.0, atol=1e-12))

# PPO
p = compute_ppo(df)
check("ppo column", "ppo" in p.columns)
ptail = p["ppo"].dropna()
check(f"ppo warmup >= 150 (got {len(ptail)})", len(ptail) >= 150)
check("ppo finite", np.isfinite(ptail).all())

# rolling corr
corr = rolling_corr_forward_returns(r["macd_histogram"], df["close"], window=30, forward=5)
check("corr series", isinstance(corr, pd.Series) and len(corr) > 0)
check("corr in [-1,1]", corr.dropna().between(-1.0, 1.0).all())
print(f"  info: mean rolling corr (synthetic) = {corr.dropna().mean():.4f}")

# --- ffn adapter ---
rng = np.random.default_rng(7)
rets = pd.Series(rng.normal(0.0004, 0.01, 500), index=pd.date_range("2024-01-01", periods=500, freq="B"))
stats = compute_stats(rets)
for key in ("total_return", "cagr", "sharpe", "sortino", "calmar", "max_drawdown", "volatility"):
    check(f"stats key {key}", key in stats and np.isfinite(stats[key]))
check("total_return > 0", stats["total_return"] > 0)
check("max_drawdown < 0", -1.0 < stats["max_drawdown"] <= 0.0)
check("sharpe > 0", stats["sharpe"] > 0)

table = monthly_returns_table(rets)
check("monthly table", isinstance(table, pd.DataFrame) and not table.empty)
check("month columns", "Jan" in table.columns and table.index.name is not None)

flat_rets = pd.Series([0.001] * 365, index=pd.date_range("2024-01-01", periods=365, freq="B"))
ftable = monthly_returns_table(flat_rets)
values = ftable.values[~np.isnan(ftable.values.astype(float))]
check("constant returns", np.allclose(values, 0.001, rtol=1e-6))

print(f"\nALL {passed} CHECKS PASSED")
