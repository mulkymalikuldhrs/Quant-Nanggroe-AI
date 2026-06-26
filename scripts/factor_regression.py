#!/usr/bin/env python3
"""Factor Regression Harness — Decompose strategy P&L into alpha vs factor exposure.

Time-series OLS:  P&L_t = alpha + Σ(beta_i × Factor_i,t) + ε_t

- Alpha = intercept interpreted as strategy-specific return (residual)
- R²    = % of variance explained by factors
- t-stat of alpha = is alpha statistically different from zero?
- Factor betas = which factors drive the strategy

Sources:
  - P&L series: CSV with columns ``date, pnl`` (daily portfolio P&L in % or cash)
  - Factor returns: CSV with columns ``date, factor1, factor2, ...``

Usage::
    python scripts/factor_regression.py --pnl pnl.csv --factors factors.csv
    python scripts/factor_regression.py --example
    python scripts/factor_regression.py --help
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from typing import Any

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import numpy as np


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def _read_csv(path: str) -> tuple[list[str], list[list[float]]]:
    """Read CSV with header row, return (headers, rows).  Skips bad rows."""
    with open(path, newline="") as f:
        reader = csv.reader(f)
        try:
            headers = next(reader)
        except StopIteration:
            raise ValueError(f"Empty CSV: {path}")
        rows: list[list[float]] = []
        for i, row in enumerate(reader, start=2):
            if not row or all(c.strip() == "" for c in row):
                continue
            try:
                parsed = [float(c) for c in row]
                if len(parsed) != len(headers):
                    continue
                rows.append(parsed)
            except ValueError:
                continue
        if not rows:
            raise ValueError(f"No numeric data in {path}")
        return headers, rows


def _detect_date_col(headers: list[str]) -> int | None:
    """Return index of a likely date column, or None."""
    lower = [h.strip().lower() for h in headers]
    for idx, name in enumerate(lower):
        if name in ("date", "timestamp", "datetime", "time", "index"):
            return idx
    return None


# ---------------------------------------------------------------------------
# Core regression
# ---------------------------------------------------------------------------

def _ols(X: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    """Multi-factor OLS via numpy.linalg.lstsq.

    Returns dict with keys: alpha, beta, r_squared, n_obs, n_factors,
    alpha_tstat, alpha_pvalue, factor_tstats, factor_pvalues, resid_std.
    """
    n, k = X.shape

    # Add intercept column
    X_with_intercept = np.column_stack([np.ones(n), X])
    coeffs, residuals, rank, singular = np.linalg.lstsq(
        X_with_intercept, y, rcond=None
    )

    alpha = float(coeffs[0])
    betas = coeffs[1:].tolist()

    # Fitted values & residuals
    fitted = X_with_intercept @ coeffs
    residuals_vec = y - fitted
    n_parms = k + 1  # intercept + k factors

    # R²
    ss_res = float(residuals_vec @ residuals_vec)
    ss_tot = float((y - y.mean()) @ (y - y.mean()))
    r_squared = 1.0 - ss_res / ss_tot if abs(ss_tot) > 1e-15 else 0.0

    # Standard error of residuals
    dof = n - n_parms
    if dof <= 0:
        return _nan_result(n, k)

    resid_var = ss_res / dof
    resid_std = float(math.sqrt(resid_var))

    # Covariance matrix of coefficients: Var(β) = σ² (X'X)⁻¹
    try:
        xtx_inv = np.linalg.inv(X_with_intercept.T @ X_with_intercept)
    except np.linalg.LinAlgError:
        return _nan_result(n, k, partial=(alpha, betas, r_squared, resid_std))

    se = np.sqrt(np.diag(xtx_inv) * resid_var)  # standard errors
    t_stats = coeffs / se
    # Two-tailed p-values from t-distribution
    p_values = [2.0 * _t_distribution_tail(abs(t), dof) for t in t_stats]

    return {
        "alpha": alpha,
        "beta": betas,
        "r_squared": round(r_squared, 6),
        "n_obs": n,
        "n_factors": k,
        "alpha_tstat": round(float(t_stats[0]), 4),
        "alpha_pvalue": round(float(p_values[0]), 6),
        "factor_tstats": [round(float(t), 4) for t in t_stats[1:]],
        "factor_pvalues": [round(float(p), 6) for p in p_values[1:]],
        "residual_std": round(resid_std, 6),
        "dof": dof,
    }


def _t_distribution_tail(t: float, dof: int) -> float:
    """Survival function P(T > |t|) for Student's t with dof degrees of freedom.

    Uses the regularised incomplete beta function via math.gamma-based
    computation as a stand-in for scipy.stats.t.sf.  Falls back to
    normal approximation when dof is large (> 1000).
    """
    if dof > 1000:
        # Normal approximation
        return _normal_sf(abs(t))

    x = dof / (t * t + dof)
    if x <= 0 or x >= 1:
        return 1.0
    tail = 0.5 * _betainc(dof / 2.0, 0.5, x)
    # betainc returns P(B <= x) where B ~ Beta(a,b).
    # For t-dist: P(T <= t) = 1 - 0.5 * I(dof/(dof+t²), dof/2, 1/2)
    # So P(T > |t|) = 2 * (1 - P(T <= |t|)) = I(dof/(dof+t²), dof/2, 1/2)
    # Actually: P(T > t) = 0.5 * I(dof/(dof+t²), dof/2, 1/2) for t > 0
    # So two-tailed: P(|T| > t) = I(dof/(dof+t²), dof/2, 1/2)
    return float(min(1.0, max(0.0, tail)))


def _betainc(a: float, b: float, x: float) -> float:
    """Regularised incomplete beta function I_x(a,b).

    Implemented via continued fraction expansion (Lentz method).
    Pure Python fallback when scipy is unavailable for t-distribution.
    """
    # Use scipy if available (more accurate)
    try:
        from scipy.special import betainc as sp_betainc
        return float(sp_betainc(a, b, x))
    except ImportError:
        pass

    if x < 0 or x > 1:
        return float("nan")
    if x == 0 or x == 1:
        return float(x)

    # Lentz continued fraction
    y = x
    if x > (a + 1) / (a + b + 2):
        # Use symmetry: I_x(a,b) = 1 - I_{1-x}(b,a)
        y = 1.0 - _betainc(b, a, 1.0 - x)
        return y

    # Compute ln(Beta(a,b))
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(x) * a + math.log(1 - x) * b - lbeta - math.log(a))
    if front == 0:
        return 0.0

    # Continued fraction
    f = 1.0
    C = 1.0
    D = 1.0 - (a + b) * x / (a + 1)
    if abs(D) < 1e-30:
        D = 1e-30
    D = 1.0 / D
    C = 1.0 + (a + b) * x / (a + 1)
    if abs(C) < 1e-30:
        C = 1e-30
    f = C / D * f

    for m in range(1, 501):
        # Even step
        numer_e = m * (b - m) * x / ((a + 2 * m - 1) * (a + 2 * m))
        D = 1.0 + numer_e * D
        if abs(D) < 1e-30:
            D = 1e-30
        C = 1.0 + numer_e / C
        if abs(C) < 1e-30:
            C = 1e-30
        D = 1.0 / D
        delta = C * D
        f *= delta

        # Odd step
        numer_o = -(a + m) * (a + b + m) * x / ((a + 2 * m) * (a + 2 * m + 1))
        D = 1.0 + numer_o * D
        if abs(D) < 1e-30:
            D = 1e-30
        C = 1.0 + numer_o / C
        if abs(C) < 1e-30:
            C = 1e-30
        D = 1.0 / D
        delta = C * D
        f *= delta

        if abs(delta - 1.0) < 1e-10:
            break

    return min(1.0, max(0.0, float(front * f)))


def _normal_sf(z: float) -> float:
    """Standard normal survival function P(Z > z)."""
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def _nan_result(n: int, k: int, partial: tuple | None = None) -> dict[str, Any]:
    """Return degenerate results when OLS is infeasible."""
    result = {
        "alpha": 0.0,
        "beta": [],
        "r_squared": 0.0,
        "n_obs": n,
        "n_factors": k,
        "alpha_tstat": 0.0,
        "alpha_pvalue": 1.0,
        "factor_tstats": [],
        "factor_pvalues": [],
        "residual_std": 0.0,
        "dof": 0,
        "warning": "Insufficient degrees of freedom or singular design matrix",
    }
    if partial is not None:
        a, b, r2, rs = partial
        result.update({
            "alpha": a, "beta": b, "r_squared": r2,
            "residual_std": rs, "dof": 0,
        })
    return result


# ---------------------------------------------------------------------------
# User-facing runner
# ---------------------------------------------------------------------------

def run_regression(
    pnl_path: str,
    factors_path: str,
    output_path: str | None = None,
    pnl_col: str = "pnl",
    factor_cols: list[str] | None = None,
) -> dict[str, Any]:
    """Load CSV data, run OLS, optionally write JSON, return result dict.

    Args:
        pnl_path: Path to CSV with daily P&L (must have ``date`` and ``pnl`` columns).
        factors_path: Path to CSV with factor returns (``date`` + factor columns).
        output_path: Optional JSON output path.
        pnl_col: Name of the P&L column (default ``pnl``).
        factor_cols: Subset of factor columns to use.  ``None`` = all.

    Returns:
        Dict with regression results.
    """
    import pandas as pd  # only used here for convenience

    # Load
    pnl_df = pd.read_csv(pnl_path, parse_dates=True)
    fac_df = pd.read_csv(factors_path, parse_dates=True)

    # Infer date column
    pnl_date_col = "date" if "date" in pnl_df.columns else pnl_df.columns[0]
    fac_date_col = "date" if "date" in fac_df.columns else fac_df.columns[0]

    # Ensure date is str for merge (handle both Timestamp and str)
    pnl_df[pnl_date_col] = pd.to_datetime(pnl_df[pnl_date_col]).astype(str)
    fac_df[fac_date_col] = pd.to_datetime(fac_df[fac_date_col]).astype(str)

    # Merge on date
    pnl_rename = {pnl_date_col: "_date_"}
    fac_rename = {fac_date_col: "_date_"}
    merged = pnl_df.rename(columns=pnl_rename).merge(
        fac_df.rename(columns=fac_rename), on="_date_", how="inner"
    )

    if len(merged) == 0:
        raise ValueError("P&L and factors have no overlapping dates")

    pnl_series = merged[pnl_col].values.astype(float)

    # Select factor columns
    factor_names: list[str]
    if factor_cols is not None:
        factor_names = [c for c in factor_cols if c in merged.columns]
    else:
        factor_names = [c for c in merged.columns
                        if c not in ("_date_", pnl_col, fac_date_col, pnl_date_col)]

    if not factor_names:
        raise ValueError("No factor columns found in factors file")

    factor_data = merged[factor_names].values.astype(float)

    # Handle NaN — drop rows where any variable is NaN
    mask = ~(np.isnan(pnl_series) | np.isnan(factor_data).any(axis=1))
    y = pnl_series[mask]
    X = factor_data[mask]
    n_dropped = int((~mask).sum())

    if len(y) < len(factor_names) + 2:
        raise ValueError(
            f"Only {len(y)} complete observations with {len(factor_names)} factors. "
            f"Need at least {len(factor_names) + 2}."
        )

    result = _ols(X, y)
    result["factor_names"] = factor_names
    result["n_dropped_nan"] = n_dropped
    result["alpha_significant"] = result["alpha_pvalue"] < 0.05

    if output_path:
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)

    return result


def _generate_example_data(n: int = 500, seed: int = 42) -> tuple[str, str]:
    """Generate synthetic P&L and factor CSV files, return their paths."""
    rng = np.random.default_rng(seed)

    # 4 factor return series with realistic properties
    dates = [f"2024-01-{d:02d}" if d <= 31 else f"2024-02-{d - 31:02d}"
             for d in range(1, min(n + 1, 366))]
    if len(dates) < n:
        import datetime
        start = datetime.date(2024, 1, 1)
        dates = [(start + datetime.timedelta(days=i)).isoformat()
                 for i in range(n)]

    # Factor returns: slightly correlated, different means/vols
    t = np.arange(n, dtype=float)
    fac1 = rng.normal(0.0005, 0.01, n) + 0.0001 * np.sin(t / 20)  # market-like
    fac2 = rng.normal(0.0002, 0.008, n) + 0.5 * fac1 * 0.3         # size-like
    fac3 = rng.normal(-0.0001, 0.006, n)                           # value-like
    fac4 = rng.normal(0.0003, 0.012, n)                             # momentum-like
    # fac5 has some missing data (NaN injection)
    fac5 = rng.normal(0.0, 0.005, n)
    fac5[rng.random(n) < 0.03] = float("nan")

    # True parameters: alpha = 5 bps/day, betas = [0.6, -0.3, 0.1, 0.4, 0.0]
    true_alpha = 0.0005
    true_betas = [0.6, -0.3, 0.1, 0.4, 0.0]
    factors = np.column_stack([fac1, fac2, fac3, fac4, fac5])

    # P&L with noise
    noise = rng.normal(0, 0.005, n)
    pnl = true_alpha + factors @ np.array(true_betas) + noise

    # Write factor CSV
    fac_path = os.path.join(_REPO_ROOT, "data", "_factor_regression_factors.csv")
    fac_cols = ["date", "market", "size", "value", "momentum", "quality"]
    with open(fac_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(fac_cols)
        for i, d in enumerate(dates):
            row = [d] + [fmt(v) for v in [fac1[i], fac2[i], fac3[i], fac4[i], fac5[i]]]
            w.writerow(row)

    # Write P&L CSV
    pnl_path = os.path.join(_REPO_ROOT, "data", "_factor_regression_pnl.csv")
    with open(pnl_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "pnl"])
        for i, d in enumerate(dates):
            w.writerow([d, fmt(pnl[i])])

    print(f"  Generated {n} rows of synthetic data", file=sys.stderr)
    print(f"  True alpha: {true_alpha}, True betas: {true_betas}", file=sys.stderr)

    return pnl_path, fac_path


def fmt(v: float) -> str:
    """Format float for CSV output."""
    return f"{v:.10f}" if abs(v) >= 1e-6 else "0.0"


def _print_human_report(result: dict[str, Any]) -> None:
    """Print regression results to stdout in human-readable format."""
    print("\n" + "=" * 60)
    print("  FACTOR REGRESSION RESULTS")
    print("=" * 60)
    print(f"  Observations:       {result['n_obs']}")
    print(f"  Factors:            {result['n_factors']}")
    if result.get("n_dropped_nan"):
        print(f"  Dropped (NaN):      {result['n_dropped_nan']}")
    print(f"  Degrees of freedom: {result['dof']}")
    print(f"  R-squared:          {result['r_squared']:.6f}")
    print(f"  Adj. R-squared:     {_adj_r2(result):.6f}")
    print()
    print(f"  Alpha (intercept):  {result['alpha']:.8f}")
    print(f"  Alpha t-stat:       {result['alpha_tstat']:.4f}")
    print(f"  Alpha p-value:      {result['alpha_pvalue']:.6f}")
    sig = "YES" if result.get("alpha_significant") else "NO"
    print(f"  Alpha significant:  {sig}  (p < 0.05)")
    print()
    print("  Factor Exposures:")
    print(f"  {'Factor':<20} {'Beta':>12} {'t-stat':>10} {'p-value':>10}")
    print(f"  {'-'*20} {'-'*12} {'-'*10} {'-'*10}")
    for name, beta, tstat, pval in zip(
        result.get("factor_names", []),
        result.get("beta", []),
        result.get("factor_tstats", []),
        result.get("factor_pvalues", []),
    ):
        sig_mark = " *" if pval < 0.05 else "  "
        print(f"  {name:<20} {beta:>12.6f} {tstat:>10.4f} {pval:>8.6f}{sig_mark}")
    print(f"  {'-'*20} {'-'*12} {'-'*10} {'-'*10}")
    print(f"  Residual std:       {result.get('residual_std', 0):.6f}")

    if result.get("r_squared", 0) > 0.7:
        interp = "strong"
    elif result.get("r_squared", 0) > 0.3:
        interp = "moderate"
    else:
        interp = "weak"
    print(f"\n  Interpretation: {interp} factor exposure "
          f"(R² = {result['r_squared']:.1%})")
    alpha_annual = result.get("alpha", 0) * 252
    print(f"  Annualized alpha:   {alpha_annual:.4f} ({alpha_annual*100:.2f}%)")
    print("=" * 60 + "\n")


def _adj_r2(result: dict[str, Any]) -> float:
    """Adjusted R-squared."""
    r2 = result.get("r_squared", 0)
    n = result.get("n_obs", 1)
    k = result.get("n_factors", 0)
    if n <= k + 1:
        return 0.0
    return 1.0 - (1.0 - r2) * (n - 1) / (n - k - 1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Factor Regression Harness — decompose P&L into alpha + factor exposure",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/factor_regression.py --pnl pnl.csv --factors factors.csv\n"
            "  python scripts/factor_regression.py --pnl pnl.csv --factors factors.csv --output results.json\n"
            "  python scripts/factor_regression.py --pnl pnl.csv --factors factors.csv --pnl-col strategy_pnl\n"
            "  python scripts/factor_regression.py --example\n"
        ),
    )
    parser.add_argument("--pnl", help="CSV with P&L series (columns: date, pnl)")
    parser.add_argument("--factors", help="CSV with factor returns (columns: date, factor1, factor2, ...)")
    parser.add_argument("--output", help="JSON output path")
    parser.add_argument("--pnl-col", default="pnl", help="P&L column name (default: pnl)")
    parser.add_argument(
        "--factor-cols", default=None,
        help="Comma-separated factor column subset (default: all except date/pnl)"
    )
    parser.add_argument(
        "--example", action="store_true",
        help="Run on synthetic data with known alpha/betas to demonstrate"
    )
    args = parser.parse_args()

    if args.example:
        print("Generating synthetic example data...", file=sys.stderr)
        pnl_path, fac_path = _generate_example_data()
        factor_cols = None
        if args.factor_cols:
            factor_cols = [c.strip() for c in args.factor_cols.split(",")]
        result = run_regression(
            pnl_path, fac_path, output_path=args.output,
            pnl_col=args.pnl_col, factor_cols=factor_cols,
        )
        _print_human_report(result)
        if args.output:
            print(f"Results written to: {args.output}", file=sys.stderr)
        # Cleanup temp files
        try:
            os.remove(pnl_path)
            os.remove(fac_path)
        except OSError:
            pass
        return

    if not args.pnl or not args.factors:
        parser.print_help()
        sys.exit(1)

    factor_cols = None
    if args.factor_cols:
        factor_cols = [c.strip() for c in args.factor_cols.split(",")]

    result = run_regression(
        args.pnl, args.factors, output_path=args.output,
        pnl_col=args.pnl_col, factor_cols=factor_cols,
    )
    _print_human_report(result)
    if args.output:
        print(f"Results written to: {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
